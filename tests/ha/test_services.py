"""The actions, and the descriptions the automation editor builds them from."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import condition as condition_helper
from homeassistant.helpers import service as service_helper
from homeassistant.helpers import trigger as trigger_helper
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.israel_transit.api import IsraelTransitError
from custom_components.israel_transit.const import (
    DOMAIN,
    SERVICE_REBUILD_TIMETABLE,
    SERVICE_REFRESH_STOP,
    SERVICE_SEARCH_STOPS,
)

from .conftest import DANKAL, STOP, stop_device


def _stop_device_id(hass: HomeAssistant) -> str:
    device = stop_device(hass, "21023")
    assert device is not None
    return device.id


# --- refresh_stop -----------------------------------------------------------


async def test_refresh_stop_reads_the_stop_now(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mock_curlbus: AsyncMock
) -> None:
    calls = mock_curlbus.arrivals.call_count

    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH_STOP,
        {"device_id": _stop_device_id(hass)},
        blocking=True,
    )

    assert mock_curlbus.arrivals.call_count == calls + 1


async def test_refresh_stop_accepts_one_of_the_stops_entities(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mock_curlbus: AsyncMock
) -> None:
    entity_id = next(
        state.entity_id
        for state in hass.states.async_all("sensor")
        if state.entity_id.endswith("_next_arrival")
    )
    calls = mock_curlbus.arrivals.call_count

    await hass.services.async_call(
        DOMAIN, SERVICE_REFRESH_STOP, {"entity_id": entity_id}, blocking=True
    )

    assert mock_curlbus.arrivals.call_count == calls + 1


async def test_refresh_stop_refuses_a_target_that_is_not_a_stop(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH_STOP,
            {"entity_id": "sun.sun"},
            blocking=True,
        )
    assert err.value.translation_key == "invalid_target"


# --- search_stops -----------------------------------------------------------


async def test_search_stops_returns_the_matches(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mock_index: AsyncMock
) -> None:
    mock_index.async_search.return_value = [STOP, DANKAL]

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_SEARCH_STOPS,
        {"query": "הקוממיות", "limit": 5},
        blocking=True,
        return_response=True,
    )

    assert [stop["code"] for stop in response["stops"]] == [STOP.code, DANKAL.code]
    mock_index.async_search.assert_awaited_with("הקוממיות", 5)


async def test_search_stops_says_when_there_is_nothing_to_search_yet(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mock_index: AsyncMock
) -> None:
    mock_index.available = False

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEARCH_STOPS,
            {"query": "abc"},
            blocking=True,
            return_response=True,
        )
    assert err.value.translation_key == "index_unavailable"


# --- rebuild_timetable ------------------------------------------------------


async def test_rebuild_timetable_forces_a_build(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mock_index: AsyncMock
) -> None:
    mock_index.async_refresh.reset_mock()

    await hass.services.async_call(DOMAIN, SERVICE_REBUILD_TIMETABLE, {}, blocking=True)

    mock_index.async_refresh.assert_awaited_once()
    assert mock_index.async_refresh.await_args.args[1] is True  # force


async def test_rebuild_timetable_reports_a_build_that_failed(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mock_index: AsyncMock
) -> None:
    async def failing(codes: frozenset[int], force: bool = False) -> bool:
        mock_index.last_error = "GTFS feed unreachable"
        return False

    mock_index.async_refresh.side_effect = failing

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            DOMAIN, SERVICE_REBUILD_TIMETABLE, {}, blocking=True
        )
    assert err.value.translation_key == "rebuild_failed"
    assert "unreachable" in err.value.translation_placeholders["error"]


async def test_rebuild_timetable_refuses_to_start_a_second_build(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, mock_index: AsyncMock
) -> None:
    release = asyncio.Event()

    async def slow(codes: frozenset[int], force: bool = False) -> bool:
        await release.wait()
        return True

    mock_index.async_refresh.side_effect = slow
    first = hass.async_create_task(
        hass.services.async_call(DOMAIN, SERVICE_REBUILD_TIMETABLE, {}, blocking=True)
    )
    await asyncio.sleep(0)

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, SERVICE_REBUILD_TIMETABLE, {}, blocking=True
        )
    assert err.value.translation_key == "rebuild_in_progress"

    release.set()
    await first


async def test_get_arrivals_from_an_unknown_stop_code_is_a_validation_error(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
) -> None:
    mock_index.async_stop.return_value = None
    mock_curlbus.arrivals.side_effect = IsraelTransitError("unknown")

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "get_arrivals",
            {"stop_code": 1},
            blocking=True,
            return_response=True,
        )


# --- what the automation editor reads --------------------------------------


async def test_every_action_trigger_and_condition_has_a_description(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """A YAML mistake here leaves the editor with a nameless, fieldless block."""
    services = (await service_helper.async_get_all_descriptions(hass))[DOMAIN]
    assert set(services) == {
        "get_arrivals",
        "refresh_stop",
        "search_stops",
        "rebuild_timetable",
    }
    assert "target" in services["refresh_stop"]

    triggers = await trigger_helper.async_get_all_descriptions(hass)
    assert {f"{DOMAIN}.arrival", f"{DOMAIN}.delay"} <= set(triggers)
    arrival = triggers[f"{DOMAIN}.arrival"]
    assert arrival is not None
    assert set(arrival["fields"]) == {"line", "offset", "offset_type"}
    assert "target" in arrival

    conditions = await condition_helper.async_get_all_descriptions(hass)
    arriving = conditions[f"{DOMAIN}.is_arriving_within"]
    assert arriving is not None
    assert set(arriving["fields"]) == {"line", "minutes"}
    assert conditions[f"{DOMAIN}.is_realtime_available"] is not None
