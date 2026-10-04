"""The Israel Transit integration.

Ships its own dashboard card and registers it as a Lovelace resource, so a user
who installs this never has to add a resource URL by hand, and keeps a local
index of the Ministry of Transport GTFS feed so that everything real-time data
cannot answer is still instant and works offline.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import (
    CALLBACK_TYPE,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import IsraelTransitError
from .automation_helpers import async_resolve_stops
from .const import (
    BRAND_URL,
    CARD_FILENAME,
    CARD_URL,
    CONF_LIMIT,
    CONF_LINES,
    CONF_QUERY,
    CONF_RAIL_DESTINATION,
    CONF_STOP_CODE,
    DATA_CLIENTS,
    DOMAIN,
    GTFS_CHECK_INTERVAL_HOURS,
    ISSUE_INDEX_FAILED,
    ISSUE_REALTIME_UNAVAILABLE,
    SERVICE_GET_ARRIVALS,
    SERVICE_REBUILD_TIMETABLE,
    SERVICE_REFRESH_STOP,
    SERVICE_SEARCH_STOPS,
    SUBENTRY_TYPE_STOP,
)
from .coordinator import (
    Clients,
    IsraelTransitConfigEntry,
    IsraelTransitCoordinator,
    async_fetch_stop,
    async_find_coordinator,
)
from .websocket_api import async_register as async_register_websocket

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

GET_ARRIVALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_CODE): vol.Coerce(int),
        vol.Optional(CONF_LINES): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_RAIL_DESTINATION): cv.string,
    }
)
REFRESH_STOP_SCHEMA = vol.Schema(cv.TARGET_SERVICE_FIELDS)
SEARCH_STOPS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_QUERY): vol.All(cv.string, vol.Length(min=1, max=64)),
        vol.Optional(CONF_LIMIT, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=50)
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register everything that must exist whether or not a stop is set up."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    clients = Clients(hass)
    domain_data[DATA_CLIENTS] = clients
    # התחנות שכרטיסים שאלו עליהן בהרצות קודמות, כדי שהאינדקס ייבנה איתן מראש.
    await clients.stops.async_load()
    async_register_websocket(hass)
    _async_register_actions(hass)
    await _async_register_card(hass)

    cancel_check = await _async_prepare_index(hass, clients)

    async def _async_close(_event: Any) -> None:
        cancel_check()
        clients.async_cancel_pending()
        await clients.index.async_close()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_close)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: IsraelTransitConfigEntry
) -> bool:
    """Start one coordinator per stop subentry."""
    clients: Clients = hass.data[DOMAIN][DATA_CLIENTS]
    coordinators: dict[str, IsraelTransitCoordinator] = {}

    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_STOP:
            continue
        coordinators[subentry.subentry_id] = IsraelTransitCoordinator(
            hass, entry, subentry, clients
        )
    # Deliberately not async_config_entry_first_refresh: that raises
    # ConfigEntryNotReady, which fails the whole entry. One stop curlbus will
    # not answer for would then take every other stop's entities down with it
    # -- indistinguishable, from the dashboard, from having lost them all. A
    # stop that cannot be read is unavailable on its own. All at once, since
    # each can wait out a 25 s timeout.
    await asyncio.gather(*(c.async_refresh() for c in coordinators.values()))

    if coordinators and not any(c.last_update_success for c in coordinators.values()):
        # Nothing answered at all: that is the integration being down rather
        # than a stop, so let Home Assistant retry the entry with backoff.
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key="no_stop_readable"
        )

    entry.runtime_data = coordinators
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: IsraelTransitConfigEntry
) -> bool:
    """Unload one stop."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> bool:
    """Delete the stop a device stands for, and only that stop.

    Without this Home Assistant offers no delete at all on a stop's own page,
    and the only one within reach is the integration's -- which takes every
    other stop with it.
    """
    codes = {value for domain, value in device.identifiers if domain == DOMAIN}
    subentry_id = next(
        (sid for sid, sub in entry.subentries.items() if sub.unique_id in codes),
        None,
    )
    if subentry_id is not None:
        # This removes the device and its entities as well, so nothing is left
        # for the caller to clean up.
        hass.config_entries.async_remove_subentry(entry, subentry_id)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the local index once the last stop is removed."""
    if hass.config_entries.async_entries(DOMAIN):
        return
    for issue_id in (ISSUE_INDEX_FAILED, ISSUE_REALTIME_UNAVAILABLE):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
    clients: Clients | None = hass.data.get(DOMAIN, {}).get(DATA_CLIENTS)
    if clients is None:
        return
    await clients.index.async_close()
    await hass.async_add_executor_job(
        shutil.rmtree, Path(hass.config.path(DOMAIN)), True
    )
    _LOGGER.debug("Removed the local GTFS index")


async def _async_reload_entry(
    hass: HomeAssistant, entry: IsraelTransitConfigEntry
) -> None:
    """A stop was added, removed or edited; its entities follow from that."""
    # A stop that was just added has no bus timetable in the index, and the
    # feed itself has not changed, so the daily check is the only other thing
    # that would ever go and fetch one. Editing a stop's lines or interval
    # leaves the set of codes alone and costs one small request.
    _async_index_check(hass)
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_index_check(hass: HomeAssistant) -> None:
    """Bring the index up to date with the feed and the configured stops."""
    clients: Clients | None = hass.data.get(DOMAIN, {}).get(DATA_CLIENTS)
    if clients is not None:
        clients.index.async_schedule_refresh(clients.async_stop_codes)


async def _async_prepare_index(hass: HomeAssistant, clients: Clients) -> CALLBACK_TYPE:
    """Open the local timetable index, and keep it current in the background.

    This belongs to the integration rather than to a stop, because the config
    flow searches the stop table: an index that only appeared once a stop
    existed would leave no way to add the first one. Building it downloads
    about 90 MB, so it runs as a background task and the config flow waits on
    that task instead of failing.
    """
    if not await clients.index.async_load():
        _LOGGER.info("Building the local GTFS index for the first time")

    @callback
    def _async_check(_now: Any = None) -> None:
        _async_index_check(hass)

    _async_check()
    return async_track_time_interval(
        hass, _async_check, timedelta(hours=GTFS_CHECK_INTERVAL_HOURS)
    )


def _clients(hass: HomeAssistant) -> Clients:
    clients: Clients = hass.data[DOMAIN][DATA_CLIENTS]
    return clients


@callback
def _async_register_actions(hass: HomeAssistant) -> None:
    """Register every action, here rather than per entry (action-setup).

    Registered with the integration rather than with a stop, so automations
    that use them validate even while no stop is loaded.
    """

    async def async_get_arrivals(call: ServiceCall) -> ServiceResponse:
        clients = _clients(hass)
        stop_code: int = call.data[CONF_STOP_CODE]
        clients.async_note_stop(stop_code)
        try:
            data = await async_fetch_stop(
                clients,
                stop_code,
                rail_destination=call.data.get(CONF_RAIL_DESTINATION),
            )
        except IsraelTransitError as err:
            placeholders = {"stop_code": str(stop_code), "error": str(err)}
            if clients.index.available and not clients.rebuilding:
                # A complete index that does not know the code: the code is
                # wrong, which is the caller's to fix, not an outage.
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="unknown_stop",
                    translation_placeholders=placeholders,
                ) from err
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="stop_unavailable",
                translation_placeholders=placeholders,
            ) from err
        if data.realtime_error and not data.arrivals:
            clients.async_request_timetable(stop_code)

        payload = data.as_dict(hass.config.language)
        if wanted := set(call.data.get(CONF_LINES) or []):
            payload["arrivals"] = [
                arrival
                for arrival in payload["arrivals"]
                if arrival["line_name"] in wanted
            ]
        return payload

    async def async_refresh_stop(call: ServiceCall) -> None:
        codes = async_resolve_stops(hass, call.data)
        coordinators = [
            coordinator
            for code in sorted(codes)
            if (coordinator := async_find_coordinator(hass, code)) is not None
        ]
        if not coordinators:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_target"
            )
        await asyncio.gather(*(c.async_request_refresh() for c in coordinators))

    async def async_search_stops(call: ServiceCall) -> ServiceResponse:
        clients = _clients(hass)
        if not clients.index.available:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="index_unavailable"
            )
        try:
            stops = await clients.index.async_search(
                call.data[CONF_QUERY], call.data[CONF_LIMIT]
            )
        except IsraelTransitError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="search_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        return {"stops": [stop.as_dict() for stop in stops]}

    async def async_rebuild_timetable(call: ServiceCall) -> None:
        clients = _clients(hass)
        if clients.rebuilding:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="rebuild_in_progress"
            )
        try:
            await clients.async_rebuild_index()
        except IsraelTransitError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="rebuild_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_ARRIVALS,
        async_get_arrivals,
        schema=GET_ARRIVALS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH_STOP, async_refresh_stop, schema=REFRESH_STOP_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_STOPS,
        async_search_stops,
        schema=SEARCH_STOPS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REBUILD_TIMETABLE, async_rebuild_timetable
    )


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and add it to the dashboard resources.

    Resources can only be written when Lovelace is in storage mode; a user on
    YAML-configured dashboards gets a log line with the one line to add.
    """
    integration = await async_get_integration(hass, DOMAIN)
    here = Path(__file__).parent
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL,
                str(here / "www" / CARD_FILENAME),
                cache_headers=False,
            ),
            # The same files Home Assistant serves as this integration's brand.
            # The card reaches them here rather than through /api/brands, which
            # needs a rotating token the card would have to keep chasing.
            StaticPathConfig(BRAND_URL, str(here / "brand"), cache_headers=True),
        ]
    )

    url = f"{CARD_URL}?v={integration.version}"
    resources = getattr(hass.data.get("lovelace"), "resources", None)
    if resources is None or not hasattr(resources, "async_create_item"):
        _LOGGER.info(
            "Dashboards are in YAML mode; add this resource manually: %s (module)",
            url,
        )
        return

    try:
        await _async_add_resource(resources, url)
    except HomeAssistantError as err:
        # The card is still served; only the automatic resource failed. Losing
        # the sensors and actions over a dashboard setting would be worse.
        _LOGGER.warning(
            "Could not add the card to the dashboard resources (%s); "
            "add it manually: %s (module)",
            err,
            url,
        )


async def _async_add_resource(resources: Any, url: str) -> None:
    """Add the card's resource, or bump its cache buster after an upgrade."""
    # Loading first matters: creating an item in a collection that has not
    # loaded yet would write it over every resource the user already has.
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    for item in resources.async_items():
        if str(item.get("url", "")).startswith(CARD_URL):
            if item["url"] != url:  # version bumped: refresh the cache buster
                await resources.async_update_item(item["id"], {"url": url})
            return

    await resources.async_create_item({"res_type": "module", "url": url})
    _LOGGER.info("Registered the Israel Transit card at %s", url)
