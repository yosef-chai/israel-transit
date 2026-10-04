"""Fixtures for the tests that run against a real Home Assistant instance."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.israel_transit.api import Arrival, RouteInfo, Stop
from custom_components.israel_transit.const import (
    CONF_STOP_CODE,
    CONF_STOP_NAME,
    DOMAIN,
    INTEGRATION_TITLE,
    SUBENTRY_TYPE_STOP,
)

StopCodes = frozenset[int] | Callable[[], frozenset[int]]

STOP = Stop(code=21023, name="ת. רכבת השלום", city="תל אביב יפו", lat=32.07, lon=34.79)
DANKAL = Stop(code=35962, name="הקוממיות", city="בת ים", lat=32.01, lon=34.75)

BUS_ROUTE = RouteInfo(
    route_id=960,
    line_ref="960",
    short_name="36",
    long_name="א<->ב-1#",
    agency="מטרופולין",
    route_type="3",
    headsign="אור יהודה_מסוף אור יהודה",
)
TRAM_ROUTE = RouteInfo(
    route_id=34447,
    line_ref="34447",
    short_name="1",
    long_name="ג<->ד-1#",
    agency="תבל",
    route_type="0",
    headsign="בת ים_הקוממיות",
)


def make_arrival(minutes: int, realtime: bool = True, line: str = "36") -> Arrival:
    return Arrival(
        line_name=line,
        eta=datetime.now().astimezone() + timedelta(minutes=minutes),
        is_realtime=realtime,
        destination="אור יהודה",
        operator="מטרופולין",
        line_ref="960" if line == "36" else "34447",
        route_type="3" if realtime else "0",
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Home Assistant only loads custom components in tests when asked to."""
    yield


@pytest.fixture
def mock_index() -> Generator[AsyncMock]:
    """A GTFS index that is already built, with one bus stop in it."""
    with patch(
        "custom_components.israel_transit.coordinator.GtfsIndex", autospec=True
    ) as factory:
        index = factory.return_value
        index.available = True
        index.building = False
        # autospec הופך property ל-Mock, ו-Mock לא ניתן לאיטרציה ולא ל-in.
        index.indexed_stops = frozenset({STOP.code})
        index.last_build = {"stops": 35302, "departures": 182891}
        index.last_error = None
        index.async_load = AsyncMock(return_value=True)
        index.async_close = AsyncMock()
        index.async_refresh = AsyncMock(return_value=False)
        _schedule_like_the_real_index(index)
        index.async_stop = AsyncMock(return_value=STOP)
        index.async_search = AsyncMock(return_value=[STOP])
        index.async_routes_at_stop = AsyncMock(return_value=[BUS_ROUTE])
        index.async_route_stops = AsyncMock(return_value=[])
        index.async_departures = AsyncMock(return_value=[])
        yield index


def _schedule_like_the_real_index(index: AsyncMock) -> None:
    """Give the mock the task GtfsIndex hands out, since flows wait on it.

    autospec makes ``build_task`` a plain truthy attribute, which would leave
    every flow waiting on a build nobody started.
    """

    async def _run(codes: frozenset[int], force: bool = False) -> bool:
        try:
            return bool(await index.async_refresh(codes, force))
        finally:
            index.build_task = None

    def _schedule(codes: StopCodes, force: bool = False) -> asyncio.Task[bool]:
        # GtfsIndex האמיתי מקבל גם פונקציה ופותח אותה בתוך async_refresh, כדי
        # שתחנות שנוספו בזמן ההמתנה ייכנסו לאותה בנייה.
        wanted = codes() if callable(codes) else codes
        index.build_task = asyncio.get_running_loop().create_task(_run(wanted, force))
        return index.build_task

    index.build_task = None
    index.async_schedule_refresh = Mock(side_effect=_schedule)


@pytest.fixture
def mock_curlbus() -> Generator[AsyncMock]:
    """Real-time arrivals, without touching the network."""
    with patch(
        "custom_components.israel_transit.coordinator.CurlbusClient", autospec=True
    ) as factory:
        client = factory.return_value
        client.arrivals = AsyncMock(return_value=(STOP, [make_arrival(3)]))
        yield client


@pytest.fixture
def mock_card_registration() -> Generator[None]:
    """The card is served over HTTP, which these tests do not exercise."""
    with patch(
        "custom_components.israel_transit._async_register_card", return_value=None
    ):
        yield


def stop_subentry(code: int = 21023, **data: Any) -> ConfigSubentryData:
    """One stop, in the shape the subentry flow produces."""
    return ConfigSubentryData(
        data={CONF_STOP_CODE: code, CONF_STOP_NAME: STOP.name, **data},
        subentry_type=SUBENTRY_TYPE_STOP,
        title=f"ת. רכבת השלום, תל אביב יפו ({code})",
        unique_id=str(code),
    )


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """The integration, with one stop added to it."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=INTEGRATION_TITLE,
        unique_id=DOMAIN,
        data={},
        subentries_data=[stop_subentry()],
    )


@pytest.fixture
async def loaded_entry(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> MockConfigEntry:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
