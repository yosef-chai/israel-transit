"""Automation conditions on a stop's board.

Both read the board the stop's coordinator already holds, so checking one never
waits on the network. With several stops targeted, a condition holds when any
of them satisfies it. A stop with no board yet -- not loaded, or never read --
satisfies neither.
"""

from __future__ import annotations

from typing import Any, Unpack, cast, override

import voluptuous as vol
from homeassistant.const import CONF_OPTIONS, CONF_TARGET
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.condition import (
    Condition,
    ConditionCheckParams,
    ConditionConfig,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .api import minutes_until
from .automation_helpers import async_resolve_stops
from .const import CONF_LINE, CONF_MINUTES
from .coordinator import StopData, async_find_coordinator

_ARRIVING_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default=dict): {
            vol.Optional(CONF_LINE): vol.Any(None, cv.string),
            vol.Required(CONF_MINUTES, default=5): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=180)
            ),
        },
    }
)

_REALTIME_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default=dict): {},
    }
)


class _StopCondition(Condition):
    """A condition on the boards of the targeted stops."""

    _schema: vol.Schema

    @override
    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        return cast(ConfigType, cls._schema(config))

    def __init__(self, hass: HomeAssistant, config: ConditionConfig) -> None:
        super().__init__(hass, config)
        self._target: dict[str, Any] = config.target or {}
        self._options: dict[str, Any] = config.options or {}

    def _boards(self) -> list[StopData]:
        """The current boards, resolved now: stops can be added or removed."""
        boards: list[StopData] = []
        for code in sorted(async_resolve_stops(self._hass, self._target)):
            coordinator = async_find_coordinator(self._hass, code)
            if coordinator is not None and coordinator.data is not None:
                boards.append(coordinator.data)
        return boards


class IsArrivingWithinCondition(_StopCondition):
    """A vehicle -- of one line, or any -- is due within a number of minutes."""

    _schema = _ARRIVING_SCHEMA

    @override
    def _async_check(self, **kwargs: Unpack[ConditionCheckParams]) -> bool:
        line = str(self._options.get(CONF_LINE) or "").strip() or None
        limit = int(self._options[CONF_MINUTES])
        now = dt_util.utcnow()
        return any(
            minutes_until(arrival.eta, now) <= limit
            for board in self._boards()
            for arrival in board.upcoming(now)
            if line is None or arrival.line_name == line
        )


class IsRealtimeAvailableCondition(_StopCondition):
    """The board is live rather than a timetable fallback."""

    _schema = _REALTIME_SCHEMA

    @override
    def _async_check(self, **kwargs: Unpack[ConditionCheckParams]) -> bool:
        return any(board.realtime_error is None for board in self._boards())


CONDITIONS: dict[str, type[Condition]] = {
    "is_arriving_within": IsArrivingWithinCondition,
    "is_realtime_available": IsRealtimeAvailableCondition,
}


async def async_get_conditions(hass: HomeAssistant) -> dict[str, type[Condition]]:
    """Return the conditions this integration provides."""
    return CONDITIONS
