"""Config flow.

The integration itself takes no configuration: adding it is one click, and
that is deliberate. The stop table lives in a local index built from the
Ministry feed, which is a 90 MB download the first time, so a setup that
demanded a stop up front could only fail on a fresh install -- there was
nothing to search yet.

Stops are subentries instead. They appear as "Add stop" on the integration
page, each one gets its own device and entities, and each can be reconfigured
or removed on its own.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    FlowType,
    SubentryFlowContext,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import IsraelTransitError, Stop
from .const import (
    CONF_LINES,
    CONF_QUERY,
    CONF_RAIL_DESTINATION,
    CONF_SCAN_INTERVAL,
    CONF_STOP_CODE,
    CONF_STOP_NAME,
    DATA_CLIENTS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INTEGRATION_TITLE,
    MIN_SCAN_INTERVAL,
    SUBENTRY_TYPE_STOP,
)
from .coordinator import Clients
from .index import GtfsIndex
from .rail_stations import RAIL_STATIONS

_LOGGER = logging.getLogger(__name__)

# What the settings form edits. Anything else in a stop's data is its identity.
_SETTINGS_KEYS = frozenset({CONF_LINES, CONF_SCAN_INTERVAL, CONF_RAIL_DESTINATION})


def _stop_title(stop: Stop) -> str:
    """`Name, City (12345)` -- the subentry title, kept short."""
    city = f", {stop.city}" if stop.city else ""
    return f"{stop.name}{city} ({stop.code})"


def _stop_option(stop: Stop) -> str:
    """The same, plus the street: one city can hold several stops of a name."""
    parts = [stop.name, stop.street, stop.city]
    return f"{' · '.join(part for part in parts if part)} ({stop.code})"


def _rail_options() -> list[selector.SelectOptionDict]:
    return [
        selector.SelectOptionDict(value=station_id, label=name)
        for station_id, name in sorted(RAIL_STATIONS.items(), key=lambda kv: kv[1])
    ]


class IsraelTransitConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry for the integration; every stop is a subentry of it."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm, and nothing more: the integration has no settings.

        The one thing worth saying first is that accepting starts a 90 MB
        download, so this is a confirmation rather than a silent create.
        """
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title=INTEGRATION_TITLE, data={})

    async def async_on_create_entry(self, result: ConfigFlowResult) -> ConfigFlowResult:
        """Go straight on to adding the first stop, rather than stopping dead."""
        subentry = await self.hass.config_entries.subentries.async_init(
            (result["result"].entry_id, SUBENTRY_TYPE_STOP),
            context=SubentryFlowContext(source=SOURCE_USER),
        )
        result["next_flow"] = (FlowType.CONFIG_SUBENTRIES_FLOW, subentry["flow_id"])
        return result

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Stops are what the user adds inside this integration."""
        return {SUBENTRY_TYPE_STOP: StopSubentryFlowHandler}


class StopSubentryFlowHandler(ConfigSubentryFlow):
    """Add or reconfigure one stop."""

    def __init__(self) -> None:
        self._matches: list[Stop] = []
        self._stop: Stop | None = None
        self._waiting = False
        self._built = False

    # -- shared plumbing ------------------------------------------------------

    def _clients(self) -> Clients:
        shared: Clients | None = self.hass.data.get(DOMAIN, {}).get(DATA_CLIENTS)
        return shared if shared else Clients(self.hass)

    def _index(self) -> GtfsIndex:
        return self._clients().index

    def _async_index_step(self, step_id: str) -> SubentryFlowResult | None:
        """Hold the flow while the index is built, or None to carry on.

        The stop table lives in that index, so until a build finishes there is
        nothing to search. It downloads about 90 MB, which is a progress step
        rather than an error.

        A flow showing progress may only move to progress or progress-done, so
        finishing that handshake comes before anything else.
        """
        index = self._index()

        if self._waiting:
            if (task := index.build_task) is not None:
                return self._async_progress(step_id, task)
            self._waiting = False
            self._built = True
            return self.async_show_progress_done(next_step_id=step_id)

        if index.available:
            return None

        if self._built or index.last_error:
            # A build has already run and still left nothing to search, so
            # waiting for another would only repeat it in front of the user.
            return self.async_abort(
                reason="index_unavailable",
                description_placeholders={"error": index.last_error or "unknown"},
            )

        # No index, and nothing building one. That is a fresh install, or one
        # whose index went with a config entry the user removed: either way the
        # answer is to build it, not to report that there is nothing to search.
        self._waiting = True
        task = index.build_task or index.async_schedule_refresh(
            self._clients().async_stop_codes
        )
        return self._async_progress(step_id, task)

    def _async_progress(self, step_id: str, task: Any) -> SubentryFlowResult:
        return self.async_show_progress(
            step_id=step_id,
            progress_action="building_index",
            progress_task=task,
        )

    # -- adding a stop --------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Search for a stop by name, city, street or code."""
        if (waiting := self._async_index_step("user")) is not None:
            return waiting

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self._matches = await self._index().async_search(
                    user_input[CONF_QUERY].strip(), limit=25
                )
            except IsraelTransitError as err:
                _LOGGER.warning("Stop search failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not self._matches:
                    errors[CONF_QUERY] = "no_stops_found"
                elif len(self._matches) == 1:
                    return await self._async_chosen(self._matches[0])
                else:
                    return await self.async_step_pick_stop()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_QUERY): selector.TextSelector()}),
            errors=errors,
        )

    async def async_step_pick_stop(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Choose one stop out of the search results."""
        if user_input is not None:
            code = int(user_input[CONF_STOP_CODE])
            chosen = next((s for s in self._matches if s.code == code), None)
            if chosen is not None:
                return await self._async_chosen(chosen)

        return self.async_show_form(
            step_id="pick_stop",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STOP_CODE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=str(stop.code), label=_stop_option(stop)
                                )
                                for stop in self._matches
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def _async_chosen(self, stop: Stop) -> SubentryFlowResult:
        """A stop was picked; refuse a duplicate, then ask for its settings."""
        entry = self._get_entry()
        if any(
            subentry.unique_id == str(stop.code)
            for subentry in entry.subentries.values()
        ):
            return self.async_abort(reason="already_configured")
        self._stop = stop
        return await self.async_step_settings()

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Which lines get their own entities, and how often to poll."""
        assert self._stop is not None
        if user_input is not None:
            return self.async_create_entry(
                title=_stop_title(self._stop),
                data={
                    CONF_STOP_CODE: self._stop.code,
                    CONF_STOP_NAME: self._stop.name,
                    **user_input,
                },
                unique_id=str(self._stop.code),
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=await self._async_settings_schema(self._stop.code, {}),
            description_placeholders={"stop": _stop_title(self._stop)},
        )

    # -- reconfiguring one --------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change the tracked lines, the interval or the rail destination."""
        if (waiting := self._async_index_step("reconfigure")) is not None:
            return waiting

        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            # The stop's identity stays as it was; the settings are replaced
            # whole, since merging could never clear one -- an emptied train
            # destination is simply absent from the form's answer.
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                data={
                    **{
                        k: v
                        for k, v in subentry.data.items()
                        if k not in _SETTINGS_KEYS
                    },
                    **{k: v for k, v in user_input.items() if k in _SETTINGS_KEYS},
                },
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=await self._async_settings_schema(
                int(subentry.data[CONF_STOP_CODE]), dict(subentry.data)
            ),
            description_placeholders={"stop": subentry.title},
        )

    async def _async_settings_schema(
        self, stop_code: int, current: dict[str, Any]
    ) -> vol.Schema:
        """The per-stop settings, with the line list read from the stop itself."""
        try:
            routes = await self._index().async_routes_at_stop(stop_code)
        except IsraelTransitError:
            routes = []
        lines = sorted({route.short_name or route.line_ref for route in routes})
        has_rail = any(route.route_type == "2" for route in routes)

        schema: dict[Any, Any] = {
            vol.Optional(
                CONF_LINES, default=list(current.get(CONF_LINES, []))
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=lines,
                    multiple=True,
                    custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=600,
                    step=10,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
        # Only trains have a destination to choose, and asking everyone else
        # for one is noise.
        if has_rail:
            schema[
                vol.Optional(
                    CONF_RAIL_DESTINATION,
                    description={"suggested_value": current.get(CONF_RAIL_DESTINATION)},
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_rail_options(),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        return vol.Schema(schema)
