"""Repair flows: fixing what a repair issue reports, from the issue itself.

Only the timetable issue has a fix the user can start -- rebuilding the index.
The flow runs the build and reports its outcome: a build that fails sends the
user back to the form with the error and leaves the issue open, rather than
closing it on a confirmation that fixed nothing.
"""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow, RepairsFlowResult
from homeassistant.core import HomeAssistant

from .api import IsraelTransitError
from .const import DATA_CLIENTS, DOMAIN, ISSUE_INDEX_FAILED
from .coordinator import Clients


class RebuildIndexRepairFlow(RepairsFlow):
    """Rebuild the GTFS index, showing progress while it downloads."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._error: str | None = None

    def _clients(self) -> Clients:
        clients: Clients = self.hass.data[DOMAIN][DATA_CLIENTS]
        return clients

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not self._clients().rebuilding:
                return await self.async_step_rebuild()
            errors["base"] = "rebuild_in_progress"
        elif self._error is not None:
            errors["base"] = "rebuild_failed"
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"error": self._error or ""},
        )

    async def async_step_rebuild(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        if self._task is None:
            self._task = self.hass.async_create_task(
                self._clients().async_rebuild_index()
            )
        if not self._task.done():
            return self.async_show_progress(
                step_id="rebuild",
                progress_action="rebuilding",
                progress_task=self._task,
            )
        task, self._task = self._task, None
        try:
            task.result()
        except IsraelTransitError as err:
            self._error = str(err)
            return self.async_show_progress_done(next_step_id="confirm")
        self._error = None
        return self.async_show_progress_done(next_step_id="done")

    async def async_step_done(
        self, user_input: dict[str, Any] | None = None
    ) -> RepairsFlowResult:
        # Finishing the flow is what deletes the issue.
        return self.async_create_entry(data={})


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Create the flow that fixes an issue."""
    if issue_id != ISSUE_INDEX_FAILED:
        raise ValueError(f"Issue {issue_id} has no fix flow")
    return RebuildIndexRepairFlow()
