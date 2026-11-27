"""כש-curlbus נכשל: זמנים משוערים ממיקום הרכבים בתמונת הסדנא."""

from __future__ import annotations

from array import array
from datetime import timedelta
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.israel_transit.api import Arrival, IsraelTransitError
from custom_components.israel_transit.estimate import Profile, Vehicle
from custom_components.israel_transit.open_bus import Snapshot

from .common import MockConfigEntry

TRIP = 7


def _profile() -> Profile:
    # שלוש עצירות, 10 דק' וקילומטר ביניהן; התחנה שלנו היא השלישית.
    blob = lambda values: array("i", values).tobytes()  # noqa: E731
    return Profile.from_blobs(
        blob([1, 2, 3]), blob([0, 1000, 2000]), blob([0, 600, 1200]), None
    )


def _planned(route_type: str = "3", seq: int = 3, minutes: int = 5) -> Arrival:
    when = dt_util.now() + timedelta(minutes=minutes)
    return Arrival(
        line_name="36",
        eta=when,
        is_realtime=False,
        destination="אור יהודה",
        line_ref="960",
        route_type=route_type,
        scheduled=when,
        origin=when - timedelta(minutes=20),
        trip_idx=TRIP,
        stop_seq=seq,
    )


def _snapshot(row: Arrival, *vehicles: Vehicle) -> Snapshot:
    now = int(dt_util.utcnow().timestamp())
    return Snapshot(now, {"960": list(vehicles)}, seen=len(vehicles))


def _bus(row: Arrival) -> Vehicle:
    """בעצירה 2, שלפי הלוח עבר בה לפני 5 דק'; מדווח עכשיו, כלומר 5 דק' איחור."""
    assert row.origin is not None
    return Vehicle(
        origin=int(row.origin.timestamp()),
        recorded_at=int(dt_util.utcnow().timestamp()),
        order=2,
        dist=1000,
        lat=32.07,
        lon=34.79,
        vehicle_ref="7733",
        journey_ref=None,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> dict:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    [state] = [
        s for s in hass.states.async_all("sensor") if s.entity_id.endswith("_arrivals")
    ]
    return dict(state.attributes)


async def test_a_failed_curlbus_is_filled_in_from_vehicle_positions(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_open_bus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    row = _planned()
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    mock_index.async_departures.return_value = [row]
    mock_index.async_trip_profiles = AsyncMock(return_value={TRIP: _profile()})
    mock_open_bus.async_snapshot.side_effect = None
    mock_open_bus.async_snapshot.return_value = _snapshot(row, _bus(row))

    attributes = await _setup(hass, config_entry)

    assert attributes["has_realtime"] is True
    assert attributes["realtime_source"] == "open_bus"
    [arrival] = attributes["arrivals"]
    assert arrival["estimated"] is True
    assert arrival["is_realtime"] is True
    # 5 דק' איחור אחרי 10 דק' נסיעה, והקטע שנשאר ארוך פי 1.3 (התקרה).
    assert arrival["delay_minutes"] == 8
    assert arrival["vehicle_ref"] == "7733"


async def test_a_working_curlbus_never_asks_open_bus(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_open_bus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    mock_index.async_departures.return_value = [_planned()]
    attributes = await _setup(hass, config_entry)
    assert attributes["realtime_source"] == "curlbus"
    mock_open_bus.async_snapshot.assert_not_awaited()


async def test_when_both_sources_fail_the_timetable_is_shown(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_open_bus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    mock_index.async_departures.return_value = [_planned()]
    mock_index.async_trip_profiles = AsyncMock(return_value={TRIP: _profile()})

    attributes = await _setup(hass, config_entry)

    assert attributes["has_realtime"] is False
    assert attributes["realtime_source"] is None
    [arrival] = attributes["arrivals"]
    assert (arrival["estimated"], arrival["is_realtime"]) == (False, False)


async def test_a_valid_snapshot_without_this_line_still_counts_as_realtime(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_open_bus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """כמו curlbus שעונה 200 ריק: אין רכב פעיל עדיין, ואין סיבה לבאנר."""
    row = _planned()
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    mock_index.async_departures.return_value = [row]
    mock_index.async_trip_profiles = AsyncMock(return_value={TRIP: _profile()})
    mock_open_bus.async_snapshot.side_effect = None
    mock_open_bus.async_snapshot.return_value = _snapshot(row)

    attributes = await _setup(hass, config_entry)

    assert (attributes["has_realtime"], attributes["realtime_source"]) == (
        True,
        "open_bus",
    )
    assert attributes["arrivals"][0]["is_realtime"] is False


async def test_a_bus_that_already_passed_leaves_the_board(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_open_bus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    row = _planned(minutes=1)
    bus = _bus(row)
    passed = Vehicle(
        **{**{s: getattr(bus, s) for s in Vehicle.__slots__}, "dist": 2100}
    )
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    mock_index.async_departures.return_value = [row]
    mock_index.async_trip_profiles = AsyncMock(return_value={TRIP: _profile()})
    mock_open_bus.async_snapshot.side_effect = None
    mock_open_bus.async_snapshot.return_value = _snapshot(row, passed)

    attributes = await _setup(hass, config_entry)
    assert attributes["arrivals"] == []


async def test_a_rail_only_board_does_not_download_the_snapshot(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_open_bus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    mock_index.async_departures.return_value = [_planned(route_type="2")]
    await _setup(hass, config_entry)
    mock_open_bus.async_snapshot.assert_not_awaited()
