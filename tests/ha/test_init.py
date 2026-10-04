"""Setup, teardown, entities and the response action."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.israel_transit.api import IsraelTransitError
from custom_components.israel_transit.const import (
    CONF_LINES,
    CONF_STOP_CODE,
    DOMAIN,
    SERVICE_GET_ARRIVALS,
)
from custom_components.israel_transit.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import STOP, make_arrival


def _set_stop_data(
    hass: HomeAssistant, entry: MockConfigEntry, updates: dict[str, object]
) -> None:
    """Edit the stop subentry, the way the reconfigure flow does."""
    subentry = next(iter(entry.subentries.values()))
    hass.config_entries.async_update_subentry(
        entry, subentry, data={**subentry.data, **updates}
    )


async def test_the_entry_loads_and_unloads_cleanly(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    assert loaded_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED


async def test_a_stop_becomes_a_device_with_its_sensors(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    timestamp = hass.states.get("sensor.t_rkbt_hshlvm_next_arrival")
    minutes = hass.states.get("sensor.t_rkbt_hshlvm_next_arrival_in")
    if timestamp is None:  # entity ids are slugified from a Hebrew name
        candidates = [
            state
            for state in hass.states.async_all("sensor")
            if state.entity_id.endswith("_next_arrival")
        ]
        assert candidates, "no next-arrival sensor was created"
        timestamp = candidates[0]
        minutes = hass.states.get(f"{timestamp.entity_id}_in")

    assert timestamp.attributes["device_class"] == "timestamp"
    assert timestamp.attributes["line"] == "36"
    assert timestamp.attributes["is_realtime"] is True
    assert minutes is not None
    assert minutes.attributes["unit_of_measurement"] == "min"
    assert int(minutes.state) in (2, 3)


async def test_tracked_lines_get_their_own_pair_of_sensors(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    config_entry.add_to_hass(hass)
    _set_stop_data(hass, config_entry, {CONF_LINES: ["36"]})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    line_sensors = [
        state
        for state in hass.states.async_all("sensor")
        if "36" in (state.attributes.get("friendly_name") or "")
    ]
    assert len(line_sensors) >= 2


async def test_setup_is_retried_when_the_stop_cannot_be_identified(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """test-before-setup: a stop nobody can resolve must not load as if fine."""
    mock_index.async_stop.return_value = None
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_losing_realtime_falls_back_to_the_timetable(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    mock_index.async_departures.return_value = [make_arrival(9, realtime=False)]

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    arrivals = [
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.endswith("_arrivals")
    ]
    assert arrivals and arrivals[0].state == "1"
    assert arrivals[0].attributes["has_realtime"] is False


async def test_the_action_returns_arrivals(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_ARRIVALS,
        {CONF_STOP_CODE: 21023},
        blocking=True,
        return_response=True,
    )

    assert response["stop"]["code"] == 21023
    assert response["arrivals"][0]["line_name"] == "36"
    assert response["arrivals"][0]["is_realtime"] is True


async def test_the_action_filters_by_line(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_ARRIVALS,
        {CONF_STOP_CODE: 21023, CONF_LINES: ["999"]},
        blocking=True,
        return_response=True,
    )
    assert response["arrivals"] == []


async def test_an_unknown_stop_is_the_callers_mistake(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
) -> None:
    """action-exceptions: a code a complete index does not know is a user error."""
    mock_index.async_stop.return_value = None
    mock_curlbus.arrivals.side_effect = IsraelTransitError("unknown stop")

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_ARRIVALS,
            {CONF_STOP_CODE: 999999},
            blocking=True,
            return_response=True,
        )
    assert err.value.translation_key == "unknown_stop"


async def test_a_stop_that_cannot_be_looked_up_yet_is_an_outage(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
) -> None:
    """Without an index nobody can tell a wrong code from a missing timetable."""
    mock_index.available = False
    mock_index.async_stop.side_effect = IsraelTransitError("not built")
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_ARRIVALS,
            {CONF_STOP_CODE: 21023},
            blocking=True,
            return_response=True,
        )
    assert not isinstance(err.value, ServiceValidationError)
    assert err.value.translation_key == "stop_unavailable"


async def test_vehicles_that_have_left_are_not_shown(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """A board is read long after it was fetched; the departed must drop off."""
    gone, coming = make_arrival(-5), make_arrival(4)
    mock_curlbus.arrivals.return_value = (STOP, [gone, coming])

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    arrivals = next(
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.endswith("_arrivals")
    )
    assert arrivals.state == "1"
    assert arrivals.attributes["arrivals"][0]["eta"] == coming.eta.isoformat()
    timestamp = next(
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.endswith("_next_arrival")
    )
    # Home Assistant drops the microseconds from a timestamp sensor's state.
    expected = coming.eta.astimezone(UTC).replace(microsecond=0)
    assert timestamp.state == expected.isoformat()


async def test_diagnostics_describe_the_stop_and_the_index(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    report = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert len(report["stops"]) == 1
    stop = report["stops"][0]
    assert stop["code"] == 21023
    assert stop["has_realtime"] is True
    assert stop["last_update_success"] is True
    assert report["gtfs_index"]["available"] is True


async def test_diagnostics_work_for_an_entry_that_failed_to_load(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """A failed load is exactly when someone downloads diagnostics."""
    mock_index.async_stop.return_value = None
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    report = await async_get_config_entry_diagnostics(hass, config_entry)

    assert report["stops"] == []
    assert report["gtfs_index"]["available"] is True


async def test_untracking_a_line_removes_its_sensors(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """Otherwise they sit in the registry as `unavailable` forever."""
    config_entry.add_to_hass(hass)
    _set_stop_data(hass, config_entry, {CONF_LINES: ["36", "91"]})
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.t_rkbt_hshlvm_tl_byb_ypv_21023_line_91_next_arrival")

    _set_stop_data(hass, config_entry, {CONF_LINES: ["36"]})
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    remaining = {
        entity.unique_id
        for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id)
    }
    assert "21023_line_36_next_arrival" in remaining
    assert not any("line_91" in unique_id for unique_id in remaining)
