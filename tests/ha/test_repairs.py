"""Repair issues: the timetable's fix flow, and the real-time outage notice."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.repairs import repairs_flow_manager
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.israel_transit.api import IsraelTransitError
from custom_components.israel_transit.const import (
    DOMAIN,
    ISSUE_INDEX_FAILED,
    ISSUE_REALTIME_UNAVAILABLE,
    REALTIME_OUTAGE_ISSUE_AFTER,
)

from .conftest import TRAM_ROUTE, stop_subentry

# --- the timetable fix flow -------------------------------------------------


def _raise_index_issue(hass: HomeAssistant) -> None:
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_INDEX_FAILED,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_INDEX_FAILED,
        translation_placeholders={"error": "GTFS feed unreachable"},
    )


async def _run_fix_flow(hass: HomeAssistant) -> dict:
    """Open the issue's fix flow, submit it, and follow it to where it lands."""
    assert await async_setup_component(hass, "repairs", {})
    manager = repairs_flow_manager(hass)
    assert manager is not None
    result = await manager.async_init(DOMAIN, data={"issue_id": ISSUE_INDEX_FAILED})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await manager.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.SHOW_PROGRESS
    assert result["progress_action"] == "rebuilding"
    await hass.async_block_till_done()
    return await manager.async_configure(result["flow_id"])


async def test_the_fix_flow_rebuilds_and_closes_the_issue(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
    issue_registry: ir.IssueRegistry,
) -> None:
    _raise_index_issue(hass)
    mock_index.async_refresh.reset_mock()

    result = await _run_fix_flow(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_index.async_refresh.await_args.args[1] is True  # forced
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_INDEX_FAILED) is None


async def test_a_fix_that_fails_says_so_and_leaves_the_issue_open(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
    issue_registry: ir.IssueRegistry,
) -> None:
    async def failing(codes: frozenset[int], force: bool = False) -> bool:
        mock_index.last_error = "No space left on device"
        return False

    mock_index.async_refresh.side_effect = failing
    _raise_index_issue(hass)

    result = await _run_fix_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["errors"] == {"base": "rebuild_failed"}
    assert "No space" in result["description_placeholders"]["error"]
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_INDEX_FAILED) is not None

    # A second attempt that works still closes it from the same dialog.
    mock_index.async_refresh.side_effect = None
    mock_index.last_error = None
    manager = repairs_flow_manager(hass)
    assert manager is not None
    result = await manager.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    result = await manager.async_configure(result["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_INDEX_FAILED) is None


# --- the real-time outage notice -------------------------------------------


@pytest.fixture
def clock() -> Callable[[float], None]:
    """Drive the monotonic clock the outage is measured with."""
    now = [1000.0]
    with patch(
        "custom_components.israel_transit.coordinator.monotonic", lambda: now[0]
    ):

        def _set(seconds: float) -> None:
            now[0] = 1000.0 + seconds

        yield _set


def _two_stops() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={},
        subentries_data=[stop_subentry(21023), stop_subentry(20092)],
    )


async def _refresh_all(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    for coordinator in entry.runtime_data.values():
        await coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_every_stop_without_realtime_for_half_an_hour_raises_the_issue(
    hass: HomeAssistant,
    clock: Callable[[float], None],
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    issue_registry: ir.IssueRegistry,
) -> None:
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus unreachable")
    entry = _two_stops()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_REALTIME_UNAVAILABLE) is None

    clock(REALTIME_OUTAGE_ISSUE_AFTER + 1)
    await _refresh_all(hass, entry)

    issue = issue_registry.async_get_issue(DOMAIN, ISSUE_REALTIME_UNAVAILABLE)
    assert issue is not None
    assert issue.translation_placeholders == {"error": "curlbus unreachable"}

    # One stop answering again is the service being back.
    mock_curlbus.arrivals.side_effect = None
    await next(iter(entry.runtime_data.values())).async_refresh()
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_REALTIME_UNAVAILABLE) is None


async def test_one_stop_without_realtime_is_not_an_outage(
    hass: HomeAssistant,
    clock: Callable[[float], None],
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    issue_registry: ir.IssueRegistry,
) -> None:
    async def arrivals(code: int):
        if code == 20092:
            raise IsraelTransitError("curlbus HTTP 500")
        return (None, [])

    mock_curlbus.arrivals = AsyncMock(side_effect=arrivals)
    entry = _two_stops()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    clock(REALTIME_OUTAGE_ISSUE_AFTER * 3)
    await _refresh_all(hass, entry)

    assert issue_registry.async_get_issue(DOMAIN, ISSUE_REALTIME_UNAVAILABLE) is None


async def test_stops_without_buses_never_count_toward_an_outage(
    hass: HomeAssistant,
    clock: Callable[[float], None],
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Light rail publishes nothing to SIRI; that is normal, not an outage."""
    mock_index.async_routes_at_stop.return_value = [TRAM_ROUTE]
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    clock(REALTIME_OUTAGE_ISSUE_AFTER * 3)
    await _refresh_all(hass, config_entry)

    assert issue_registry.async_get_issue(DOMAIN, ISSUE_REALTIME_UNAVAILABLE) is None


async def test_an_outage_notice_from_before_a_restart_clears_once_realtime_answers(
    hass: HomeAssistant,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Issues are stored, so one raised before a restart outlives it."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_REALTIME_UNAVAILABLE,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_REALTIME_UNAVAILABLE,
        translation_placeholders={"error": "curlbus unreachable"},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert issue_registry.async_get_issue(DOMAIN, ISSUE_REALTIME_UNAVAILABLE) is None


async def test_losing_and_regaining_realtime_is_logged_once_each(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mock_curlbus: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """log-when-unavailable, for the part the coordinator cannot see."""
    coordinator = next(iter(loaded_entry.runtime_data.values()))
    mock_curlbus.arrivals.side_effect = IsraelTransitError("curlbus HTTP 500")
    for _ in range(3):
        await coordinator.async_refresh()
    mock_curlbus.arrivals.side_effect = None
    for _ in range(3):
        await coordinator.async_refresh()

    assert caplog.text.count("Real-time is unavailable for stop 21023") == 1
    assert caplog.text.count("Real-time is back for stop 21023") == 1
