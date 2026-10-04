"""Removal, card registration, and the rail merge inside the coordinator."""

from __future__ import annotations

import logging
import struct
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.israel_transit import (
    _async_register_card,
    async_remove_config_entry_device,
)
from custom_components.israel_transit.api import (
    Arrival,
    IsraelTransitError,
    RouteInfo,
    Stop,
)
from custom_components.israel_transit.const import (
    BRAND_URL,
    CARD_FILENAME,
    CARD_URL,
    CONF_RAIL_DESTINATION,
    DOMAIN,
    GTFS_DB_FILENAME,
    INTEGRATION_TITLE,
)

from .conftest import STOP, make_arrival, stop_device, stop_subentry

RAIL_ROUTE = RouteInfo(
    route_id=29950,
    line_ref="29950",
    short_name="",
    long_name="א<->נהריה-נהריה",
    agency="רכבת ישראל",
    route_type="2",
    headsign="",
)


# --- removal ----------------------------------------------------------------


async def test_removing_the_last_stop_deletes_the_local_index(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """A 20 MB index has no business outliving the integration."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    index_dir = Path(hass.config.path(DOMAIN))
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / GTFS_DB_FILENAME).write_bytes(b"not really a database")

    await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not index_dir.exists()
    assert mock_index.async_close.called


async def test_the_index_survives_while_another_stop_still_needs_it(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    other = MockConfigEntry(domain=DOMAIN, unique_id="40001", data={"stop_code": 40001})
    for entry in (config_entry, other):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    index_dir = Path(hass.config.path(DOMAIN))
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / GTFS_DB_FILENAME).write_bytes(b"kept")

    await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()

    assert (index_dir / GTFS_DB_FILENAME).exists()


# --- the dashboard card -----------------------------------------------------


class _Resources:
    """Stands in for Lovelace's storage-mode resource collection."""

    def __init__(self, items: list[dict[str, str]] | None = None) -> None:
        self.loaded = True
        self._items = items or []
        self.created: list[dict[str, str]] = []
        self.updated: list[tuple[str, dict[str, str]]] = []

    def async_items(self) -> list[dict[str, str]]:
        return self._items

    async def async_create_item(self, item: dict[str, str]) -> None:
        self.created.append(item)

    async def async_update_item(self, item_id: str, item: dict[str, str]) -> None:
        self.updated.append((item_id, item))


async def _register_card(hass: HomeAssistant, resources: object | None) -> AsyncMock:
    """Run the resource registration against a stand-in Lovelace collection."""
    await async_setup_component(hass, "http", {})
    hass.data["lovelace"] = type("Lovelace", (), {"resources": resources})()
    static = AsyncMock()
    with patch.object(hass.http, "async_register_static_paths", static):
        await _async_register_card(hass)
    return static


async def test_the_card_and_the_brand_are_both_served(hass: HomeAssistant) -> None:
    """The editor shows the same mark Home Assistant reads out of brand/."""
    static = await _register_card(hass, _Resources())

    served = {config.url_path: Path(config.path) for config in static.await_args[0][0]}
    assert served.keys() == {CARD_URL, BRAND_URL}
    assert served[CARD_URL].name == CARD_FILENAME
    # Home Assistant itself looks for exactly this directory, and the icon in
    # it, when it renders the integration.
    assert served[BRAND_URL].name == "brand"
    assert (served[BRAND_URL] / "icon.png").is_file()


def _png_header(path: Path) -> tuple[int, int, int]:
    """Width, height and colour type, straight out of the PNG IHDR chunk."""
    header = path.read_bytes()[:26]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    width, height = struct.unpack(">II", header[16:24])
    return width, height, header[25]


async def test_home_assistant_finds_the_brand_images(hass: HomeAssistant) -> None:
    """Since 2026.3 a custom integration carries its own icon in brand/.

    Home Assistant decides whether to look for one purely by the presence of
    that directory, so this asserts the shape the brands component requires
    rather than merely that some files exist.
    """
    integration = await async_get_integration(hass, DOMAIN)
    assert integration.has_branding is True

    brand = Path(integration.file_path) / "brand"
    for name, expected in (
        ("icon.png", 256),
        ("icon@2x.png", 512),
        ("dark_icon.png", 256),
        ("dark_icon@2x.png", 512),
    ):
        width, height, colour_type = _png_header(brand / name)
        assert (width, height) == (expected, expected), name
        assert colour_type == 6, f"{name} has no alpha channel"

    # No logo files on purpose: the mark is square, and the specification says
    # a square brand ships the icon alone and lets the logo fall back to it.
    assert not list(brand.glob("*logo*"))


async def test_the_card_registers_itself_as_a_resource(hass: HomeAssistant) -> None:
    """Nobody should have to paste a resource URL by hand."""
    resources = _Resources()
    await _register_card(hass, resources)

    assert len(resources.created) == 1
    assert resources.created[0]["res_type"] == "module"
    assert resources.created[0]["url"].startswith(f"/{DOMAIN}/israel-transit-card.js")


async def test_an_existing_resource_is_updated_rather_than_duplicated(
    hass: HomeAssistant,
) -> None:
    """An upgrade changes the cache buster; it must not add a second entry."""
    stale = {"id": "abc", "url": f"/{DOMAIN}/israel-transit-card.js?v=0.0.1"}
    resources = _Resources([stale])

    await _register_card(hass, resources)

    assert resources.created == []
    assert len(resources.updated) == 1
    assert resources.updated[0][0] == "abc"


async def test_an_up_to_date_resource_is_left_alone(hass: HomeAssistant) -> None:
    integration = await async_get_integration(hass, DOMAIN)
    current = {
        "id": "abc",
        "url": f"/{DOMAIN}/israel-transit-card.js?v={integration.version}",
    }
    resources = _Resources([current])

    await _register_card(hass, resources)

    assert resources.created == [] and resources.updated == []


async def test_yaml_dashboards_are_told_what_to_add(hass: HomeAssistant) -> None:
    """Resources cannot be written in YAML mode, so log the one line needed.

    The log is captured by hand: the harness wraps pytest's caplog fixture and
    requesting it from here trips a fixture recursion inside the plugin.
    """
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger("custom_components.israel_transit")
    handler = _Capture()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        await _register_card(hass, None)
    finally:
        logger.removeHandler(handler)

    assert any("YAML mode" in record.getMessage() for record in records)


# --- trains -----------------------------------------------------------------


async def test_a_rail_destination_brings_in_live_train_departures(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """rail.co.il answers per route, which is why a destination is required."""
    mock_index.async_routes_at_stop.return_value = [RAIL_ROUTE]
    mock_curlbus.arrivals.return_value = (STOP, [])
    train = make_arrival(12, realtime=True)
    train.route_type = "2"
    train.platform = "3"
    train.delay_minutes = 4

    config_entry.add_to_hass(hass)
    subentry = next(iter(config_entry.subentries.values()))
    hass.config_entries.async_update_subentry(
        config_entry,
        subentry,
        data={**subentry.data, CONF_RAIL_DESTINATION: "680"},
    )
    with (
        patch(
            "custom_components.israel_transit.coordinator.RailClient.station_id",
            return_value="3700",
        ),
        patch(
            "custom_components.israel_transit.coordinator.RailClient.departures",
            AsyncMock(return_value=[train]),
        ),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    arrivals = next(
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.endswith("_arrivals")
    )
    assert arrivals.state == "1"
    assert arrivals.attributes["arrivals"][0]["platform"] == "3"
    assert arrivals.attributes["arrivals"][0]["delay_minutes"] == 4


async def test_a_stop_that_is_not_a_known_station_skips_the_rail_lookup(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """The Eastern Railway stops are in GTFS but not in the station table."""
    mock_index.async_routes_at_stop.return_value = [RAIL_ROUTE]
    mock_curlbus.arrivals.return_value = (STOP, [])
    departures = AsyncMock()

    config_entry.add_to_hass(hass)
    subentry = next(iter(config_entry.subentries.values()))
    hass.config_entries.async_update_subentry(
        config_entry,
        subentry,
        data={**subentry.data, CONF_RAIL_DESTINATION: "680"},
    )
    with (
        patch(
            "custom_components.israel_transit.coordinator.RailClient.station_id",
            return_value=None,
        ),
        patch(
            "custom_components.israel_transit.coordinator.RailClient.departures",
            departures,
        ),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    departures.assert_not_called()


async def test_a_failing_rail_lookup_does_not_break_the_board(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    mock_index.async_routes_at_stop.return_value = [RAIL_ROUTE]
    mock_curlbus.arrivals.return_value = (STOP, [make_arrival(5)])

    config_entry.add_to_hass(hass)
    subentry = next(iter(config_entry.subentries.values()))
    hass.config_entries.async_update_subentry(
        config_entry,
        subentry,
        data={**subentry.data, CONF_RAIL_DESTINATION: "680"},
    )
    with (
        patch(
            "custom_components.israel_transit.coordinator.RailClient.station_id",
            return_value="3700",
        ),
        patch(
            "custom_components.israel_transit.coordinator.RailClient.departures",
            AsyncMock(side_effect=IsraelTransitError("rail.co.il unreachable")),
        ),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    arrivals = next(
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.endswith("_arrivals")
    )
    assert arrivals.state == "1"  # the bus survived


async def test_only_trains_reported_live_leave_the_timetable(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """rail.co.il answers for one destination, and sometimes only in part.

    A timetabled train it reported live is the same train twice; every other
    timetabled train -- to elsewhere, or simply missing from its answer --
    has to stay on the board rather than vanish with the duplicates.
    """
    now = dt_util.utcnow()

    def timetabled(minutes: int) -> Arrival:
        return Arrival(
            line_name="",
            eta=now + timedelta(minutes=minutes),
            is_realtime=False,
            line_ref=RAIL_ROUTE.line_ref,
            route_type="2",
        )

    mock_index.async_routes_at_stop.return_value = [RAIL_ROUTE]
    mock_index.async_departures.return_value = [timetabled(12), timetabled(40)]
    mock_curlbus.arrivals.return_value = (STOP, [])
    live = Arrival(
        line_name="171",
        eta=now + timedelta(minutes=16),
        is_realtime=True,
        route_type="2",
        delay_minutes=4,
    )

    config_entry.add_to_hass(hass)
    subentry = next(iter(config_entry.subentries.values()))
    hass.config_entries.async_update_subentry(
        config_entry, subentry, data={**subentry.data, CONF_RAIL_DESTINATION: "680"}
    )
    with (
        patch(
            "custom_components.israel_transit.coordinator.RailClient.station_id",
            return_value="3700",
        ),
        patch(
            "custom_components.israel_transit.coordinator.RailClient.departures",
            AsyncMock(return_value=[live]),
        ),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    board = next(iter(config_entry.runtime_data.values())).data
    assert [(a.is_realtime, a.eta) for a in board.arrivals] == [
        (True, live.eta),  # the 12-minute train, four minutes late
        (False, now + timedelta(minutes=40)),  # no live counterpart: kept
    ]


# --- enrichment -------------------------------------------------------------


async def test_a_live_arrival_inherits_its_mode_from_the_route(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """curlbus reports a line id but no mode, and the card colours by mode."""
    bare = Arrival(
        line_name="36",
        eta=make_arrival(4).eta,
        is_realtime=True,
        line_ref="960",
    )
    mock_curlbus.arrivals.return_value = (STOP, [bare])

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    arrivals = next(
        state
        for state in hass.states.async_all("sensor")
        if state.entity_id.endswith("_arrivals")
    )
    row = arrivals.attributes["arrivals"][0]
    assert row["route_type"] == "3"
    assert row["operator"] == "מטרופולין"
    assert row["destination"] == "אור יהודה_מסוף אור יהודה"


async def test_the_build_is_told_which_stops_are_configured(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """Bus timetables are only stored for stops the build is told about.

    Without this the documented fallback -- add the stop, get a timetable when
    curlbus cannot answer for it -- silently never happens.
    """
    mock_index.available = False
    mock_index.async_load = AsyncMock(return_value=False)
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    mock_index.async_refresh.assert_awaited()
    assert mock_index.async_refresh.await_args.args[0] == frozenset({21023})


async def test_adding_a_stop_asks_the_index_to_catch_up(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """The feed does not change when a stop is added, so nothing else would."""
    config_entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    mock_index.async_refresh.reset_mock()

    hass.config_entries.async_add_subentry(
        config_entry, ConfigSubentry(**stop_subentry(35962))
    )
    await hass.async_block_till_done()

    mock_index.async_refresh.assert_awaited()
    assert 35962 in mock_index.async_refresh.await_args.args[0]


async def test_a_rebuild_does_not_empty_the_board_it_cannot_look_up(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> None:
    """Rebuilding closes the index for minutes, once a week.

    A stop curlbus refuses cannot be identified while that is happening, and
    failing it would log an error and blank every entity for a stop that has
    not moved.
    """
    config_entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    coordinator = next(iter(config_entry.runtime_data.values()))
    before = coordinator.data

    mock_index.building = True
    mock_index.async_stop.side_effect = IsraelTransitError("index is not built yet")
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data is before


# --- one stop is one stop ---------------------------------------------------


def _three_stops() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=INTEGRATION_TITLE,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            stop_subentry(21023),
            stop_subentry(20092),
            stop_subentry(26544),
        ],
    )


def _stops_with_entities(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    registry = er.async_get(hass)
    return {
        entity.unique_id.split("_")[0]
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    }


async def test_a_stop_that_cannot_be_read_leaves_the_others_alone(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
) -> None:
    """Setting up used to raise ConfigEntryNotReady for the whole entry.

    One stop curlbus will not answer for -- and there is a real one, 26544 --
    then took every other stop's entities down with it, which on the dashboard
    is indistinguishable from having lost the lot.
    """

    async def arrivals(code: int) -> tuple[Stop, list[Arrival]]:
        if code == 20092:
            raise IsraelTransitError("curlbus returned 500")
        return (STOP, [make_arrival(3)])

    mock_curlbus.arrivals = AsyncMock(side_effect=arrivals)
    mock_index.async_stop = AsyncMock(
        side_effect=lambda code: None if code == 20092 else STOP
    )

    entry = _three_stops()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert _stops_with_entities(hass, entry) == {"21023", "20092", "26544"}

    registry = er.async_get(hass)
    sick = registry.async_get_entity_id("sensor", DOMAIN, "20092_next_arrival")
    healthy = registry.async_get_entity_id("sensor", DOMAIN, "21023_next_arrival")
    # The one that failed reads unavailable; the others carry a real time.
    assert sick and hass.states.get(sick).state == STATE_UNAVAILABLE
    assert healthy and hass.states.get(healthy).state not in (
        STATE_UNAVAILABLE,
        STATE_UNKNOWN,
    )


async def test_every_stop_failing_retries_the_whole_entry(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
) -> None:
    """Nothing answering at all is the integration being down, not a stop."""
    mock_curlbus.arrivals = AsyncMock(side_effect=IsraelTransitError("no network"))
    mock_index.async_stop = AsyncMock(return_value=None)

    entry = _three_stops()
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_deleting_a_stops_device_deletes_only_that_stop(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
) -> None:
    """The delete button on a stop's own page has to mean that stop.

    Without async_remove_config_entry_device Home Assistant offers no delete
    there at all, and the only one in reach is the integration's, which takes
    every stop with it.
    """
    entry = _three_stops()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # This is the flag Home Assistant reads to decide whether to offer the
    # delete at all; without it the stop's page has no way out.
    assert entry.supports_remove_device

    device = stop_device(hass, "20092")
    assert device is not None

    assert await async_remove_config_entry_device(hass, entry, device)
    await hass.async_block_till_done()

    assert {sub.unique_id for sub in entry.subentries.values()} == {"21023", "26544"}
    assert _stops_with_entities(hass, entry) == {"21023", "26544"}
    assert stop_device(hass, "20092") is None


async def test_deleting_a_stops_device_from_the_ui_succeeds(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
) -> None:
    """Through Home Assistant's own handler, which runs after ours.

    Removing the subentry already takes the device away, and the handler has
    to cope with that rather than fail the delete the user asked for.
    """
    assert await async_setup_component(hass, "config", {})
    entry = _three_stops()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    devices = dr.async_get(hass)
    device = stop_device(hass, "20092")
    assert device is not None

    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "config/device_registry/remove_config_entry",
            "config_entry_id": entry.entry_id,
            "device_id": device.id,
        }
    )
    result = await client.receive_json()
    await hass.async_block_till_done()

    assert result["success"], result.get("error")
    assert devices.async_get(device.id) is None
    assert {sub.unique_id for sub in entry.subentries.values()} == {"21023", "26544"}
    assert entry.state is ConfigEntryState.LOADED
