"""Repair issues: the timetable's fix flows.

There is no real-time outage issue: "Repair issues must be actionable", and
there is nothing to do about curlbus being down. Losing it is logged instead.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.components.repairs import repairs_flow_manager
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from custom_components.israel_transit.api import IsraelTransitError
from custom_components.israel_transit.const import (
    DOMAIN,
    ISSUE_INDEX_FAILED,
    ISSUE_INDEX_STALE,
)

from .common import MockConfigEntry

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


# --- the timetable that is about to run out ---------------------------------


async def test_the_stale_timetable_issue_opens_the_same_rebuild_with_its_date(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mock_index: AsyncMock,
    issue_registry: ir.IssueRegistry,
) -> None:
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_INDEX_STALE,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_INDEX_STALE,
        translation_placeholders={"date": "2026-12-01"},
        data={"date": "2026-12-01"},
    )
    assert await async_setup_component(hass, "repairs", {})
    manager = repairs_flow_manager(hass)
    assert manager is not None
    result = await manager.async_init(DOMAIN, data={"issue_id": ISSUE_INDEX_STALE})

    assert result["step_id"] == "confirm"
    assert result["description_placeholders"]["date"] == "2026-12-01"

    result = await manager.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    result = await manager.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_INDEX_STALE) is None


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
