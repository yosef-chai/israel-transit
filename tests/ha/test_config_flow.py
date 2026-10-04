"""The config flow, and the stop subentry flow that does the real work.

The integration itself takes no configuration; a stop is a subentry, added
from the "Add stop" button on the integration page. That split exists because
the stop table lives in a locally built index: a setup that demanded a stop up
front could only fail on a fresh install.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.israel_transit.api import IsraelTransitError, RouteInfo
from custom_components.israel_transit.const import (
    CONF_LINES,
    CONF_QUERY,
    CONF_RAIL_DESTINATION,
    CONF_SCAN_INTERVAL,
    CONF_STOP_CODE,
    CONF_STOP_NAME,
    DOMAIN,
    SUBENTRY_TYPE_STOP,
)

from .conftest import DANKAL, STOP, stop_subentry

RAIL_ROUTE = RouteInfo(
    route_id=29950,
    line_ref="29950",
    short_name="",
    long_name="א<->נהריה-נהריה",
    agency="רכבת ישראל",
    route_type="2",
)


async def _add_integration(hass: HomeAssistant) -> MockConfigEntry:
    """Walk the one-click config flow, stopping before the chained subentry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    return result["result"]


async def _add_stop(hass: HomeAssistant, entry: MockConfigEntry):
    """Start the "Add stop" flow the integration page offers."""
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_STOP), context={"source": SOURCE_USER}
    )


# --- the integration itself -------------------------------------------------


async def test_adding_the_integration_asks_for_nothing(
    hass: HomeAssistant, mock_index: AsyncMock
) -> None:
    """A stop cannot be chosen before the stop table exists, so it is not."""
    entry = await _add_integration(hass)

    assert entry.data == {}
    assert entry.unique_id == DOMAIN
    assert entry.subentries == {}


async def test_the_integration_is_added_only_once(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_setup_leads_straight_into_adding_a_stop(
    hass: HomeAssistant, mock_index: AsyncMock
) -> None:
    """Otherwise setup finishes on an integration with nothing in it."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    flow_type, flow_id = result["next_flow"]
    assert flow_type == "config_subentries_flow"
    assert any(
        flow["flow_id"] == flow_id
        for flow in hass.config_entries.subentries.async_progress()
    )


# --- adding a stop ----------------------------------------------------------


async def test_a_single_match_is_added_straight_away(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    # The fixture entry already holds 21023, so add a different stop.
    mock_index.async_search.return_value = [DANKAL]
    config_entry.add_to_hass(hass)
    result = await _add_stop(hass, config_entry)
    assert result["step_id"] == "user"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_QUERY: "35962"}
    )
    assert result["step_id"] == "settings"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_LINES: ["1"], CONF_SCAN_INTERVAL: 90}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_STOP_CODE] == DANKAL.code
    assert result["data"][CONF_LINES] == ["1"]
    assert result["unique_id"] == str(DANKAL.code)


async def test_several_matches_offer_a_choice(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    mock_index.async_search.return_value = [STOP, DANKAL]
    config_entry.add_to_hass(hass)

    result = await _add_stop(hass, config_entry)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_QUERY: "ה"}
    )
    assert result["step_id"] == "pick_stop"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_STOP_CODE: str(DANKAL.code)}
    )
    assert result["step_id"] == "settings"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 60}
    )
    assert result["data"][CONF_STOP_CODE] == DANKAL.code


async def test_a_search_with_no_results_asks_again(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    mock_index.async_search.return_value = []
    config_entry.add_to_hass(hass)

    result = await _add_stop(hass, config_entry)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_QUERY: "שדרות הבלתי אפשרי"}
    )

    assert result["step_id"] == "user"
    assert result["errors"] == {CONF_QUERY: "no_stops_found"}


async def test_a_broken_index_read_is_reported_not_swallowed(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    mock_index.async_search.side_effect = IsraelTransitError("database is locked")
    config_entry.add_to_hass(hass)

    result = await _add_stop(hass, config_entry)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_QUERY: "השלום"}
    )

    assert result["errors"] == {"base": "cannot_connect"}


async def test_the_same_stop_cannot_be_added_twice(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The fixture entry already carries stop 21023."""
    config_entry.add_to_hass(hass)

    result = await _add_stop(hass, config_entry)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_QUERY: "21023"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# --- reconfiguring one ------------------------------------------------------


async def test_reconfigure_updates_the_stop_in_place(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    subentry = next(iter(config_entry.subentries.values()))

    result = await hass.config_entries.subentries.async_init(
        (config_entry.entry_id, SUBENTRY_TYPE_STOP),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_LINES: ["36", "91"], CONF_SCAN_INTERVAL: 120}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    updated = config_entry.subentries[subentry.subentry_id]
    assert updated.data[CONF_LINES] == ["36", "91"]
    assert updated.data[CONF_SCAN_INTERVAL] == 120
    # The stop itself is untouched; only its settings changed.
    assert updated.data[CONF_STOP_CODE] == 21023


async def test_reconfigure_can_clear_the_train_destination(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
) -> None:
    """An emptied optional field is absent from the answer, so merging kept it.

    Replacing the settings whole must still leave the stop's identity, and the
    device and entities hanging off it, exactly as they were.
    """
    mock_index.async_routes_at_stop.return_value = [RAIL_ROUTE]
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={},
        subentries_data=[stop_subentry(**{CONF_RAIL_DESTINATION: "3700"})],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    subentry = next(iter(entry.subentries.values()))
    assert subentry.data[CONF_RAIL_DESTINATION] == "3700"
    devices = dr.async_get(hass)
    device = devices.async_get_device(identifiers={(DOMAIN, "21023")})
    assert device is not None

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_STOP),
        context={"source": "reconfigure", "subentry_id": subentry.subentry_id},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_LINES: [], CONF_SCAN_INTERVAL: 60}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    updated = entry.subentries[subentry.subentry_id]
    assert CONF_RAIL_DESTINATION not in updated.data
    assert updated.data[CONF_STOP_CODE] == 21023
    assert updated.data[CONF_STOP_NAME] == STOP.name
    assert (updated.unique_id, updated.title) == (subentry.unique_id, subentry.title)
    after = devices.async_get_device(identifiers={(DOMAIN, "21023")})
    assert after is not None and after.id == device.id
    assert subentry.subentry_id in after.config_entries_subentries[entry.entry_id]


# --- the very first run -----------------------------------------------------


async def test_the_first_stop_can_be_added_while_the_index_is_still_building(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The stop table lives in the index, and the search reads it.

    Regression: the index used to be built by async_setup_entry, so on a fresh
    install it was never built, the search always failed, and there was no way
    to add a stop at all.
    """
    release = asyncio.Event()

    async def _build(_codes: frozenset[int], _force: bool = False) -> bool:
        await release.wait()
        mock_index.available = True
        return True

    mock_index.available = False
    mock_index.async_load = AsyncMock(return_value=False)
    mock_index.async_refresh = AsyncMock(side_effect=_build)

    assert await async_setup_component(hass, DOMAIN, {})
    assert mock_index.async_schedule_refresh.called
    config_entry.add_to_hass(hass)

    result = await _add_stop(hass, config_entry)
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["progress_action"] == "building_index"

    release.set()
    await hass.async_block_till_done()

    result = await hass.config_entries.subentries.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_a_build_that_failed_says_so_instead_of_offering_a_search(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Searching a table that will never exist is worse than an honest abort."""
    mock_index.available = False
    mock_index.async_load = AsyncMock(return_value=False)
    mock_index.async_refresh = AsyncMock(return_value=False)
    mock_index.last_error = "feed unreachable"

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    config_entry.add_to_hass(hass)

    result = await _add_stop(hass, config_entry)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "index_unavailable"
    assert result["description_placeholders"] == {"error": "feed unreachable"}


async def test_the_index_is_prepared_without_any_stop(
    hass: HomeAssistant, mock_index: AsyncMock
) -> None:
    """Setting the integration up is enough; it must not wait for a stop."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert mock_index.async_load.await_count == 1


async def test_a_stop_can_be_added_after_the_index_was_removed_with_an_entry(
    hass: HomeAssistant, mock_index: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Removing the integration deletes the index; re-adding must rebuild it.

    Regression: the build only ever ran from async_setup, which runs once per
    Home Assistant start. So after a removal the index was gone and nothing
    would build another until a restart, and every attempt to add a stop
    answered "there are no stops to search: unknown" -- with no error to name,
    because nothing had failed. Nothing had been tried.
    """
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    async def _rebuild(_codes: frozenset[int], _force: bool = False) -> bool:
        mock_index.available = True
        return True

    # The state left behind by async_remove_entry: no index, and no failure to
    # report either.
    mock_index.available = False
    mock_index.last_error = None
    mock_index.async_refresh = AsyncMock(side_effect=_rebuild)
    mock_index.async_schedule_refresh.reset_mock()

    config_entry.add_to_hass(hass)
    result = await _add_stop(hass, config_entry)
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["progress_action"] == "building_index"
    await hass.async_block_till_done()

    result = await hass.config_entries.subentries.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert mock_index.async_schedule_refresh.called
