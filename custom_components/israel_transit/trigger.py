"""Automation triggers: a line reaching a stop, and a train running late.

Both follow the stop's own polling rather than polling themselves: every
coordinator refresh is announced on a dispatcher signal, and a trigger
re-reads the board when it hears one. Listening to the signal rather than to a
coordinator object is what keeps a trigger alive across a reload of the
integration, which replaces every coordinator.

The arrival trigger has one rule that everything else serves: each trip fires
once, at its moment, or not at all. Its moment moves with the live ETA; a trip
that turns from a timetable row into a live one is still the same trip; and a
moment that slipped past by more than a couple of minutes is dropped rather
than fired late, since "the bus is coming" ten minutes late is worse than
silence. Nothing is stored across a restart: a moment that falls while Home
Assistant is down does not fire afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import count
from typing import Any, cast, override

import voluptuous as vol
from homeassistant.const import CONF_OFFSET, CONF_OPTIONS, CONF_TARGET
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.trigger import (
    NotTriggeredInfo,
    Trigger,
    TriggerActionRunner,
    TriggerConfig,
    TriggerNotTriggeredReporter,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .api import Arrival, localized, minutes_until
from .automation_helpers import async_resolve_stops
from .const import (
    CONF_LINE,
    CONF_MIN_DELAY,
    DEPARTED_GRACE,
    DOMAIN,
    TRIGGER_GRACE,
    TRIGGER_MATCH_WINDOW,
    TRIGGER_MAX_AGE,
    TRIGGER_MAX_OFFSET,
)
from .coordinator import (
    IsraelTransitCoordinator,
    StopData,
    async_configured_stop_codes,
    async_find_coordinator,
    signal_stop_updated,
)

CONF_OFFSET_TYPE = "offset_type"
OFFSET_TYPE_BEFORE = "before"
OFFSET_TYPE_AFTER = "after"

# The same vehicle can come round again on its next run an hour or two later,
# so a shared vehicle_ref only means the same trip within this window.
_VEHICLE_MATCH_WINDOW = timedelta(minutes=30)

_LINE = vol.Any(None, cv.string)

_ARRIVAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default=dict): {
            vol.Optional(CONF_LINE): _LINE,
            vol.Required(CONF_OFFSET, default=timedelta(0)): vol.All(
                cv.positive_time_period, vol.Range(max=TRIGGER_MAX_OFFSET)
            ),
            vol.Required(CONF_OFFSET_TYPE, default=OFFSET_TYPE_BEFORE): vol.In(
                (OFFSET_TYPE_BEFORE, OFFSET_TYPE_AFTER)
            ),
        },
    }
)

_DELAY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default=dict): {
            vol.Optional(CONF_LINE): _LINE,
            vol.Required(CONF_MIN_DELAY, default=5): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=180)
            ),
        },
    }
)


def _line_option(options: dict[str, Any]) -> str | None:
    """The line to follow, or None for every line. The UI sends "" for none."""
    line = str(options.get(CONF_LINE) or "").strip()
    return line or None


@dataclass(slots=True)
class _Trip:
    """One vehicle's visit to a stop, as followed across refreshes."""

    stop_code: int
    arrival: Arrival
    fire_at: datetime

    def same_as(self, stop_code: int, other: Arrival) -> bool:
        """Whether a row from a newer board is this same trip.

        The vehicle is the strongest evidence. Without it -- a timetable row,
        or a live one that has not been assigned a vehicle yet -- the same line
        within a few minutes of the same time is taken to be the same run.
        """
        if stop_code != self.stop_code:
            return False
        mine = self.arrival
        gap = abs(other.eta - mine.eta)
        if mine.vehicle_ref and other.vehicle_ref:
            return (
                mine.vehicle_ref == other.vehicle_ref and gap <= _VEHICLE_MATCH_WINDOW
            )
        return mine.line_name == other.line_name and gap <= TRIGGER_MATCH_WINDOW


class _StopRunner:
    """What one attached trigger keeps between refreshes, and how it ends.

    One instance per attachment, so turning an automation off and on again
    starts clean, and detaching takes every listener and timer with it.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        stop_codes: set[int],
        line: str | None,
        run_action: TriggerActionRunner,
        did_not_trigger: TriggerNotTriggeredReporter | None,
    ) -> None:
        self.hass = hass
        self.stop_codes = stop_codes
        self.line = line
        self.run_action = run_action
        self.did_not_trigger = did_not_trigger
        # Every trip followed gets an id from here, fired or not, so the two
        # can be matched against a new board together.
        self.ids = count()
        # Trips already fired for, and when, so that none fires twice.
        self.fired: dict[int, tuple[_Trip, datetime]] = {}
        self._unsubs: list[CALLBACK_TYPE] = []

    @callback
    def async_start(self) -> None:
        for code in self.stop_codes:
            self._unsubs.append(
                async_dispatcher_connect(
                    self.hass,
                    signal_stop_updated(code),
                    self._async_handle_update,
                )
            )
        now = dt_util.utcnow()
        for code in self.stop_codes:
            if (coordinator := async_find_coordinator(self.hass, code)) is not None:
                self.async_evaluate(coordinator, now, initial=True)

    @callback
    def async_stop(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()
        self.fired.clear()

    @callback
    def _async_handle_update(self, coordinator: IsraelTransitCoordinator) -> None:
        self.async_evaluate(coordinator, dt_util.utcnow(), initial=False)

    def arrivals(
        self, coordinator: IsraelTransitCoordinator, now: datetime
    ) -> list[Arrival]:
        # None until the stop's first read succeeds, whatever the type says.
        data: StopData | None = coordinator.data
        if data is None:
            return []
        return [
            a
            for a in data.upcoming(now)
            if self.line is None or a.line_name == self.line
        ]

    @staticmethod
    def match(
        stop_code: int, rows: list[Arrival], trips: dict[int, _Trip]
    ) -> dict[int, int]:
        """Pair each row of a new board with the trip it continues, if any.

        One to one, nearest first. Without that, two vehicles of a frequent
        line -- timetable rows a few minutes apart, with no vehicle to tell
        them by -- would both claim the first one's trip, and the second
        would either never fire or take the first one's moment.
        """
        pairs = sorted(
            (abs(row.eta - trip.arrival.eta), index, trip_id)
            for index, row in enumerate(rows)
            for trip_id, trip in trips.items()
            if trip.same_as(stop_code, row)
        )
        matched: dict[int, int] = {}
        taken: set[int] = set()
        for _gap, index, trip_id in pairs:
            if index not in matched and trip_id not in taken:
                matched[index] = trip_id
                taken.add(trip_id)
        return matched

    def fired_trips(self) -> dict[int, _Trip]:
        return {trip_id: trip for trip_id, (trip, _) in self.fired.items()}

    def prune(self, now: datetime) -> None:
        self.fired = {
            trip_id: (trip, at)
            for trip_id, (trip, at) in self.fired.items()
            if now - at < TRIGGER_MAX_AGE
        }

    @callback
    def async_fire(self, trip: _Trip, now: datetime, description: str) -> None:
        self.fired[next(self.ids)] = (trip, now)
        a = trip.arrival
        lang = self.hass.config.language
        self.run_action(
            {
                "stop_code": trip.stop_code,
                "line": a.line_name,
                "line_ref": a.line_ref,
                "destination": localized(a.destination, lang) or None,
                "operator": localized(a.operator, lang) or None,
                "eta": a.eta,
                "minutes": minutes_until(a.eta, now),
                "is_realtime": a.is_realtime,
                "vehicle_ref": a.vehicle_ref,
                "platform": a.platform,
                "delay_minutes": a.delay_minutes,
            },
            description,
        )

    @callback
    def async_evaluate(
        self, coordinator: IsraelTransitCoordinator, now: datetime, initial: bool
    ) -> None:
        raise NotImplementedError


class _ArrivalRunner(_StopRunner):
    """Fire once per trip, at its arrival plus the offset."""

    def __init__(self, *args: Any, offset: timedelta) -> None:
        super().__init__(*args)
        self.offset = offset
        self.pending: dict[int, _Trip] = {}
        self._unsub_timer: CALLBACK_TYPE | None = None

    @override
    @callback
    def async_stop(self) -> None:
        super().async_stop()
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        self.pending.clear()

    @override
    @callback
    def async_evaluate(
        self, coordinator: IsraelTransitCoordinator, now: datetime, initial: bool
    ) -> None:
        code = coordinator.stop_code
        rows = self.arrivals(coordinator, now)
        matched = self.match(code, rows, {**self.fired_trips(), **self.pending})
        seen: set[int] = set()
        for index, arrival in enumerate(rows):
            trip_id = matched.get(index)
            if trip_id is not None and trip_id in self.fired:
                # Fired already; keep following it, so that a time drifting
                # on later boards is still recognised as the same trip.
                self.fired[trip_id][0].arrival = arrival
                continue
            fire_at = arrival.eta + self.offset
            if trip_id is None:
                if initial and fire_at <= now:
                    # Already past when the automation came up: that moment
                    # belonged to before it existed, and is not news now.
                    self.fired[next(self.ids)] = (_Trip(code, arrival, fire_at), now)
                    continue
                trip_id = next(self.ids)
                self.pending[trip_id] = _Trip(code, arrival, fire_at)
            else:
                self.pending[trip_id].arrival = arrival
                self.pending[trip_id].fire_at = fire_at
            seen.add(trip_id)

        # Rows missing from a board that did load. A vehicle that had reached
        # the stop has simply left the list, and an offset "after" its
        # arrival still has to fire; one that vanished early was cancelled or
        # lost, and has no moment left to fire at.
        if coordinator.last_update_success:
            for trip_id, trip in list(self.pending.items()):
                if (
                    trip.stop_code == code
                    and trip_id not in seen
                    and trip.arrival.eta > now + DEPARTED_GRACE
                ):
                    del self.pending[trip_id]

        self._async_process(now)

    @callback
    def _async_on_timer(self, _now: datetime) -> None:
        self._unsub_timer = None
        self._async_process(dt_util.utcnow())

    @callback
    def _async_process(self, now: datetime) -> None:
        configured = async_configured_stop_codes(self.hass)
        for trip_id, trip in sorted(self.pending.items(), key=lambda i: i[1].fire_at):
            if trip.fire_at > now:
                continue
            del self.pending[trip_id]
            late = now - trip.fire_at
            if trip.stop_code not in configured:
                continue
            if late <= TRIGGER_GRACE:
                self.async_fire(trip, now, self._description(trip))
            elif self.did_not_trigger is not None:
                self.did_not_trigger(
                    NotTriggeredInfo(
                        reason="missed",
                        data={
                            "stop_code": trip.stop_code,
                            "line": trip.arrival.line_name,
                            "late_seconds": int(late.total_seconds()),
                        },
                    )
                )
        self.prune(now)
        self._async_schedule()

    @callback
    def _async_schedule(self) -> None:
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        if self.pending:
            when = min(trip.fire_at for trip in self.pending.values())
            self._unsub_timer = async_track_point_in_utc_time(
                self.hass, self._async_on_timer, when
            )

    def _description(self, trip: _Trip) -> str:
        line = trip.arrival.line_name
        if not self.offset:
            return f"line {line} arriving at stop {trip.stop_code}"
        when = "before" if self.offset < timedelta(0) else "after"
        return (
            f"line {line} {abs(self.offset)} {when} arriving at stop {trip.stop_code}"
        )


class _DelayRunner(_StopRunner):
    """Fire once per trip, when its reported delay reaches the threshold."""

    def __init__(self, *args: Any, min_delay: int) -> None:
        super().__init__(*args)
        self.min_delay = min_delay

    @override
    @callback
    def async_evaluate(
        self, coordinator: IsraelTransitCoordinator, now: datetime, initial: bool
    ) -> None:
        code = coordinator.stop_code
        rows = self.arrivals(coordinator, now)
        matched = self.match(code, rows, self.fired_trips())
        for index, arrival in enumerate(rows):
            if (trip_id := matched.get(index)) is not None:
                self.fired[trip_id][0].arrival = arrival
                continue
            if (arrival.delay_minutes or 0) < self.min_delay:
                continue
            self.async_fire(
                _Trip(code, arrival, now),
                now,
                f"line {arrival.line_name} delayed {arrival.delay_minutes} min "
                f"at stop {code}",
            )
        self.prune(now)


class _StopTrigger(Trigger):
    """A trigger on one or more configured stops."""

    _schema: vol.Schema

    @override
    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        return cast(ConfigType, cls._schema(config))

    def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
        super().__init__(hass, config)
        self._target: dict[str, Any] = config.target or {}
        self._options: dict[str, Any] = config.options or {}

    def _make_runner(
        self,
        stop_codes: set[int],
        run_action: TriggerActionRunner,
        did_not_trigger: TriggerNotTriggeredReporter | None,
    ) -> _StopRunner:
        raise NotImplementedError

    @override
    async def async_attach_runner(
        self,
        run_action: TriggerActionRunner,
        did_not_trigger: TriggerNotTriggeredReporter | None = None,
    ) -> CALLBACK_TYPE:
        stop_codes = async_resolve_stops(self._hass, self._target)
        if not stop_codes:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="invalid_target"
            )
        runner = self._make_runner(stop_codes, run_action, did_not_trigger)
        runner.async_start()
        return runner.async_stop


class ArrivalTrigger(_StopTrigger):
    """A line reaching a stop, or a set time before or after it does."""

    _schema = _ARRIVAL_SCHEMA

    @override
    def _make_runner(
        self,
        stop_codes: set[int],
        run_action: TriggerActionRunner,
        did_not_trigger: TriggerNotTriggeredReporter | None,
    ) -> _StopRunner:
        offset: timedelta = self._options.get(CONF_OFFSET) or timedelta(0)
        if self._options.get(CONF_OFFSET_TYPE) == OFFSET_TYPE_BEFORE:
            offset = -offset
        return _ArrivalRunner(
            self._hass,
            stop_codes,
            _line_option(self._options),
            run_action,
            did_not_trigger,
            offset=offset,
        )


class DelayTrigger(_StopTrigger):
    """A vehicle reported running late by at least a set number of minutes."""

    _schema = _DELAY_SCHEMA

    @override
    def _make_runner(
        self,
        stop_codes: set[int],
        run_action: TriggerActionRunner,
        did_not_trigger: TriggerNotTriggeredReporter | None,
    ) -> _StopRunner:
        return _DelayRunner(
            self._hass,
            stop_codes,
            _line_option(self._options),
            run_action,
            did_not_trigger,
            min_delay=int(self._options[CONF_MIN_DELAY]),
        )


TRIGGERS: dict[str, type[Trigger]] = {
    "arrival": ArrivalTrigger,
    "delay": DelayTrigger,
}


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    """Return the triggers this integration provides."""
    return TRIGGERS
