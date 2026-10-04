"""The WebSocket commands the dashboard card calls."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.israel_transit.api import (
    Arrival,
    IsraelTransitError,
    RouteStop,
    Stop,
)
from custom_components.israel_transit.const import DATA_CLIENTS, DOMAIN

from .conftest import DANKAL, STOP, TRAM_ROUTE, stop_subentry


async def test_search_stops_backs_the_visual_editor(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
) -> None:
    mock_index.async_search.return_value = [STOP, DANKAL]
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/search_stops", "query": "הקומ", "limit": 5}
    )
    result = await client.receive_json()

    assert result["success"]
    assert [row["code"] for row in result["result"]] == [STOP.code, DANKAL.code]
    assert result["result"][0]["name"] == STOP.name


async def test_search_reports_a_broken_index_instead_of_hanging(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
) -> None:
    mock_index.async_search.side_effect = IsraelTransitError("index not built")
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": f"{DOMAIN}/search_stops", "query": "abc"})
    result = await client.receive_json()

    assert not result["success"]
    assert result["error"]["code"] == "search_failed"


async def test_the_stop_board_is_served_from_the_coordinator(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_curlbus: AsyncMock,
) -> None:
    """A configured stop must not cost an extra upstream request."""
    calls_before = mock_curlbus.arrivals.call_count
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": f"{DOMAIN}/stop", "stop_code": 21023})
    result = await client.receive_json()

    assert result["success"]
    assert result["result"]["stop"]["code"] == 21023
    assert result["result"]["arrivals"][0]["line_name"] == "36"
    assert mock_curlbus.arrivals.call_count == calls_before


async def test_an_unknown_stop_is_an_error_not_an_empty_board(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
) -> None:
    mock_index.async_stop.return_value = None
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": f"{DOMAIN}/stop", "stop_code": 999999})
    result = await client.receive_json()

    assert not result["success"]
    assert result["error"]["code"] == "unknown_stop"


async def test_stop_routes_lists_every_line(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
) -> None:
    mock_index.async_routes_at_stop.return_value = [TRAM_ROUTE]
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/stop_routes", "stop_code": 35962}
    )
    result = await client.receive_json()

    assert result["success"]
    route = result["result"][0]
    assert route["line_name"] == "1"
    assert route["destination"] == "בת ים_הקוממיות"
    # Light rail publishes nothing to SIRI, and the card labels it accordingly.
    assert route["has_realtime"] is False


async def test_route_stops_uses_the_vehicle_departure_for_absolute_times(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
) -> None:
    mock_index.async_route_stops.return_value = [
        RouteStop(sequence=1, stop=STOP, offset_seconds=0),
        RouteStop(sequence=2, stop=DANKAL, offset_seconds=600),
    ]
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/route_stops",
            "line_ref": 960,
            "departed": "2026-08-30T22:00:00+03:00",
        }
    )
    result = await client.receive_json()

    assert result["success"]
    first, second = result["result"]
    assert first["arrival_time"].startswith("2026-08-30T22:00:00")
    assert second["arrival_time"].startswith("2026-08-30T22:10:00")
    assert second["offset_seconds"] == 600


async def test_route_stops_without_a_departure_returns_offsets_only(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
) -> None:
    mock_index.async_route_stops.return_value = [
        RouteStop(sequence=1, stop=STOP, offset_seconds=420)
    ]
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": f"{DOMAIN}/route_stops", "line_ref": 960})
    result = await client.receive_json()

    assert result["success"]
    assert result["result"][0]["arrival_time"] is None
    assert result["result"][0]["offset_seconds"] == 420


async def test_a_stop_whose_first_read_failed_is_fetched_rather_than_crashed_on(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
) -> None:
    """A stop is set up even when its first read fails, so its board is None.

    The card asks by stop code and is answered from the coordinator that
    already polls that stop, which would hand over that None and crash on it.
    """

    async def arrivals(code: int) -> tuple[Stop, list[Arrival]]:
        if code == DANKAL.code:
            raise IsraelTransitError("curlbus returned 500")
        return (STOP, [])

    mock_curlbus.arrivals = AsyncMock(side_effect=arrivals)
    mock_index.async_stop = AsyncMock(
        side_effect=lambda code: None if code == DANKAL.code else STOP
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={},
        subentries_data=[stop_subentry(STOP.code), stop_subentry(DANKAL.code)],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # The sick stop can be read again now; its coordinator still holds nothing.
    mock_index.async_stop = AsyncMock(return_value=DANKAL)
    mock_curlbus.arrivals = AsyncMock(return_value=(DANKAL, []))

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/stop", "stop_code": DANKAL.code})
    result = await client.receive_json()

    assert result["success"], result.get("error")
    assert result["result"]["stop"]["code"] == DANKAL.code


async def test_a_card_only_stop_gets_its_timetable_indexed(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
) -> None:
    """A card names a stop code directly, with no subentry behind it.

    Timetables are only stored for the stops the build is told about, so
    without this a stop SIRI cannot answer for shows an empty board forever:
    no real-time, and no timetable to fall back on.
    """
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    mock_index.async_stop.return_value = DANKAL
    mock_index.indexed_stops = frozenset()
    mock_index.async_refresh.reset_mock()
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": f"{DOMAIN}/stop", "stop_code": DANKAL.code})
    result = await client.receive_json()

    assert result["success"], result.get("error")
    assert result["result"]["arrivals"] == []
    clients = hass.data[DOMAIN][DATA_CLIENTS]
    assert DANKAL.code in clients.stops.codes

    # Past both the delay that batches a dashboard's cards into one build and
    # the registry's delayed save, so neither is left pending.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    mock_index.async_refresh.assert_awaited()
    assert DANKAL.code in mock_index.async_refresh.await_args.args[0]


async def test_the_board_cache_does_not_mix_rail_destinations(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    loaded_entry: MockConfigEntry,
    mock_curlbus: AsyncMock,
) -> None:
    """The destination changes the board, so it cannot share a cache entry."""
    client = await hass_ws_client(hass)
    calls = mock_curlbus.arrivals.call_count

    for destination in (None, "3700"):
        await client.send_json_auto_id(
            {
                "type": f"{DOMAIN}/stop",
                "stop_code": DANKAL.code,
                "rail_destination": destination,
            }
        )
        assert (await client.receive_json())["success"]
    assert mock_curlbus.arrivals.call_count == calls + 2

    # The same question again inside the window is answered from the cache.
    await client.send_json_auto_id({"type": f"{DOMAIN}/stop", "stop_code": DANKAL.code})
    assert (await client.receive_json())["success"]
    assert mock_curlbus.arrivals.call_count == calls + 2


@pytest.mark.parametrize(
    ("configured", "asked", "served_by_coordinator"),
    [
        (None, None, True),
        ("3700", "3700", True),
        ("3700", None, False),  # the card wants no train rows
        (None, "3700", False),  # the coordinator has no live trains
        ("3700", "680", False),  # another destination entirely
    ],
)
async def test_a_configured_stop_serves_only_the_board_the_card_asked_for(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    configured: str | None,
    asked: str | None,
    served_by_coordinator: bool,
) -> None:
    """The train destination shapes the board, so a mismatch fetches its own."""
    data = {"rail_destination": configured} if configured else {}
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={},
        subentries_data=[stop_subentry(**data)],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    calls = mock_curlbus.arrivals.call_count
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/stop", "stop_code": STOP.code, "rail_destination": asked}
    )
    result = await client.receive_json()

    assert result["success"], result.get("error")
    assert (mock_curlbus.arrivals.call_count == calls) is served_by_coordinator
