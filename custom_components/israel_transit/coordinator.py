"""Fetching and polling for a single stop.

:func:`async_fetch_stop` holds the whole merge policy -- real-time first, the
local timetable for what SIRI does not carry -- so the polling coordinator and
the card's WebSocket command cannot drift apart.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    Arrival,
    CurlbusClient,
    IsraelTransitError,
    RailClient,
    RouteInfo,
    Stop,
    line_sort_key,
)
from .const import (
    CONF_RAIL_DESTINATION,
    CONF_SCAN_INTERVAL,
    CONF_STOP_CODE,
    DEFAULT_SCAN_INTERVAL,
    DEPARTED_GRACE,
    DOMAIN,
    ISSUE_REALTIME_UNAVAILABLE,
    MAX_ARRIVALS,
    NEW_STOP_INDEX_DELAY,
    RAIL_MATCH_WINDOW,
    REALTIME_OUTAGE_ISSUE_AFTER,
    REALTIME_ROUTE_TYPES,
    ROUTE_TYPE_RAIL,
    TIMETABLE_REQUEST_COOLDOWN,
)
from .index import GtfsIndex
from .stop_registry import StopRegistry

_LOGGER = logging.getLogger(__name__)

# One coordinator per stop subentry, keyed by subentry_id.
type IsraelTransitConfigEntry = ConfigEntry[dict[str, IsraelTransitCoordinator]]


def signal_stop_updated(stop_code: int) -> str:
    """האות שנשלח אחרי כל רענון של תחנה, לטריגרים שמאזינים לה.

    טריגר מאזין לאות ולא לאובייקט ה-coordinator, כי טעינה מחדש של הרשומה מחליפה
    את ה-coordinator, וטריגר שהחזיק את הישן היה מתחרש בשקט.
    """
    return f"{DOMAIN}_stop_updated_{stop_code}"


@dataclass(slots=True)
class StopData:
    """Everything the entities and the card need about one stop."""

    stop: Stop
    arrivals: list[Arrival] = field(default_factory=list)
    routes: list[RouteInfo] = field(default_factory=list)
    has_realtime: bool = False
    realtime_error: str | None = None

    def upcoming(self, now: datetime | None = None) -> list[Arrival]:
        """The arrivals that have not left yet.

        A board is read for up to a whole polling interval after it was fetched
        -- longer when real-time is down and the last board is kept -- so the
        vehicles that have since left are dropped at read time, not fetch time.
        """
        cutoff = (now or dt_util.utcnow()) - DEPARTED_GRACE
        return [a for a in self.arrivals if a.eta >= cutoff]

    def for_line(self, line_name: str, now: datetime | None = None) -> list[Arrival]:
        return [a for a in self.upcoming(now) if a.line_name == line_name]

    def as_dict(self, lang: str = "he", now: datetime | None = None) -> dict[str, Any]:
        return {
            "stop": self.stop.as_dict(),
            "arrivals": [a.as_dict(lang, now) for a in self.upcoming(now)],
            "routes": [r.as_dict() for r in self.routes],
            "has_realtime": self.has_realtime,
            "realtime_error": self.realtime_error,
        }


class Clients:
    """The live sources plus the local index, shared across all config entries.

    Held once per Home Assistant instance so the GTFS index is opened and
    refreshed a single time rather than once per configured stop.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        session = async_get_clientsession(hass)
        self.hass = hass
        self.curlbus = CurlbusClient(session)
        self.rail = RailClient(session)
        self.index = GtfsIndex(hass)
        self.stops = StopRegistry(hass)
        self._pending_index: CALLBACK_TYPE | None = None
        # monotonic() מתחיל סמוך לאתחול המכונה, ולכן 0 היה חוסם את הבקשה הראשונה
        # בחצי השעה הראשונה אחרי הפעלה.
        self._last_timetable_request = -TIMETABLE_REQUEST_COOLDOWN
        # תחנה -> מתי היה לה זמן אמת לאחרונה. נמדד מההפעלה: תקלה שהתחילה לפניה
        # אינה ידועה, ואין סיבה לפתוח עליה תקלה ברגע הראשון.
        self._started = monotonic()
        self._realtime_ok_at: dict[int, float] = {}

    @callback
    def async_note_stop(self, stop_code: int) -> None:
        """מסמן תחנה שכרטיס שאל עליה, כדי שהבנייה הבאה תכלול את לוח הזמנים שלה.

        זו הדרך היחידה שתחנה שהוגדרה רק בכרטיס, בלי תת-רשומה, נכנסת לאינדקס
        בכלל -- ובלעדיה היא מציגה לוח ריק בכל פעם ש-SIRI לא עונה עליה.
        """
        self.stops.async_note(stop_code)

    @callback
    def async_request_timetable(self, stop_code: int) -> None:
        """בונה את האינדקס מחדש עבור תחנה שנשארה בלי כלום להציג.

        נקרא רק כשאין זמן אמת וגם אין לוח זמנים, ולכן תחנה ש-curlbus עונה עליה
        כרגיל לא גוררת בנייה מחדש של 90MB.
        """
        if (
            stop_code in self.index.indexed_stops
            or self._pending_index is not None
            # בנייה שכבר רצה תכלול את התחנה; בלי זה כל רענון של כרטיס היה מוסיף
            # עוד משימה שממתינה על אותו מנעול.
            or self.index.building
        ):
            return
        # בנייה שנכשלה משאירה את התחנה בלי לוח, והכרטיס ישאל שוב בעוד חצי דקה.
        now = monotonic()
        if now - self._last_timetable_request < TIMETABLE_REQUEST_COOLDOWN:
            return
        self._last_timetable_request = now

        @callback
        def _async_build(_now: Any) -> None:
            self._pending_index = None
            self.index.async_schedule_refresh(self.async_stop_codes)

        _LOGGER.info(
            "Stop %s has neither real-time nor a timetable; indexing its timetable",
            stop_code,
        )
        self._pending_index = async_call_later(
            self.hass, NEW_STOP_INDEX_DELAY, _async_build
        )

    @callback
    def async_stop_codes(self) -> frozenset[int]:
        """נקרא בתוך הרענון עצמו, ולכן רואה גם תחנות שנוספו בזמן שהמתין בתור."""
        return async_wanted_stop_codes(self.hass, self)

    @property
    def rebuilding(self) -> bool:
        return self.index.building or self.index.build_task is not None

    async def async_rebuild_index(self) -> None:
        """Rebuild the timetable now, whatever the feed's version says.

        Shared by the action and the repair flow. Raises
        :class:`IsraelTransitError` with the build's own error when it fails,
        so neither can report success for a build that did not happen.
        """
        await self.index.async_schedule_refresh(self.async_stop_codes, force=True)
        if self.index.last_error:
            raise IsraelTransitError(self.index.last_error)

    @callback
    def async_note_realtime(self, stop_code: int, data: StopData) -> None:
        """Raise, or clear, the repair issue for a real-time outage.

        One stop without real-time is that stop; every bus stop without it for
        half an hour is the service being down, and the user should hear that
        the board is a timetable for now. Stops served only by modes SIRI does
        not carry never count either way.
        """
        if not any(r.route_type in REALTIME_ROUTE_TYPES for r in data.routes):
            return
        now = monotonic()
        if data.realtime_error is None:
            self._realtime_ok_at[stop_code] = now
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_REALTIME_UNAVAILABLE)
            return
        self._realtime_ok_at.setdefault(stop_code, self._started)
        watched = [
            code
            for code in async_configured_stop_codes(self.hass)
            if code in self._realtime_ok_at
        ]
        if watched and all(
            now - self._realtime_ok_at[code] >= REALTIME_OUTAGE_ISSUE_AFTER
            for code in watched
        ):
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_REALTIME_UNAVAILABLE,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_REALTIME_UNAVAILABLE,
                translation_placeholders={"error": data.realtime_error},
            )

    @callback
    def async_cancel_pending(self) -> None:
        if self._pending_index is not None:
            self._pending_index()
            self._pending_index = None


@callback
def async_configured_stop_codes(hass: HomeAssistant) -> frozenset[int]:
    """The stops set up as subentries."""
    return frozenset(
        int(subentry.data[CONF_STOP_CODE])
        for entry in hass.config_entries.async_entries(DOMAIN)
        for subentry in entry.subentries.values()
        if CONF_STOP_CODE in subentry.data
    )


@callback
def async_wanted_stop_codes(hass: HomeAssistant, clients: Clients) -> frozenset[int]:
    """כל התחנות שכדאי לשמור להן לוח זמנים: המוגדרות, ואלה שכרטיס שאל עליהן."""
    return async_configured_stop_codes(hass) | clients.stops.codes


@callback
def async_find_coordinator(
    hass: HomeAssistant, stop_code: int
) -> IsraelTransitCoordinator | None:
    """The coordinator polling a stop, if one is loaded."""
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinators: dict[str, IsraelTransitCoordinator] = entry.runtime_data
        for coordinator in coordinators.values():
            if coordinator.stop_code == stop_code:
                return coordinator
    return None


async def async_fetch_stop(
    clients: Clients,
    stop_code: int,
    rail_destination: str | None = None,
) -> StopData:
    """Build one stop's arrival board.

    Raises :class:`IsraelTransitError` only when the stop itself cannot be
    identified. Everything else degrades: losing real-time falls back to the
    timetable rather than emptying the board.
    """
    routes: list[RouteInfo] = []
    stop: Stop | None = None
    try:
        stop = await clients.index.async_stop(stop_code)
        routes = await clients.index.async_routes_at_stop(stop_code)
    except IsraelTransitError as err:
        _LOGGER.debug("GTFS index lookup failed for stop %s: %s", stop_code, err)

    realtime: list[Arrival] = []
    realtime_error: str | None = None
    try:
        curlbus_stop, realtime = await clients.curlbus.arrivals(stop_code)
        # Identity comes from GTFS first: curlbus does not know the newer stops
        # at all and answers with an error for them.
        stop = stop or curlbus_stop
    except IsraelTransitError as err:
        realtime_error = str(err)
        _LOGGER.debug("No real-time for stop %s: %s", stop_code, err)

    if stop is None:
        raise IsraelTransitError(f"Stop {stop_code} is not in the GTFS feed")

    _enrich(realtime, routes)
    scheduled = await _async_scheduled(clients, stop_code, routes, bool(realtime_error))
    rail = await _async_rail(clients, stop, routes, rail_destination)
    arrivals = [*realtime, *_without_live_trains(scheduled, rail), *rail]
    arrivals.sort(key=lambda a: (a.eta, line_sort_key(a.line_name)))

    return StopData(
        stop=stop,
        arrivals=arrivals[:MAX_ARRIVALS],
        routes=routes,
        # An empty answer is still a real-time answer: nothing is due.
        has_realtime=realtime_error is None,
        realtime_error=realtime_error,
    )


def _without_live_trains(
    scheduled: list[Arrival], rail: list[Arrival]
) -> list[Arrival]:
    """Drop the timetabled trains that rail.co.il reported live.

    rail.co.il only answers for the destination asked about, so only the trains
    it actually returned are replaced. Every other train -- to other
    destinations, or missing from a partial answer -- stays on the timetable.
    The two sources share no trip id, so a train is matched on its timetabled
    departure: the live time less the delay.
    """
    if not rail:
        return scheduled
    live = [a.eta - timedelta(minutes=a.delay_minutes or 0) for a in rail]
    return [
        a
        for a in scheduled
        if a.route_type != ROUTE_TYPE_RAIL
        or not any(abs(a.eta - when) <= RAIL_MATCH_WINDOW for when in live)
    ]


def _enrich(arrivals: list[Arrival], routes: list[RouteInfo]) -> None:
    """Fill in what SIRI leaves out, from the route the arrival belongs to.

    curlbus reports a line id but not its mode, so without this every live bus
    would render in the card's "unknown mode" colour instead of the bus one.
    The GTFS route_id and the curlbus line_id are the same number, which is what
    makes the join possible.
    """
    by_line = {route.line_ref: route for route in routes}
    for arrival in arrivals:
        route = by_line.get(arrival.line_ref or "")
        if route is None:
            continue
        if arrival.route_type is None:
            arrival.route_type = route.route_type
        if not arrival.destination:
            arrival.destination = route.destination
        if not arrival.operator:
            arrival.operator = route.agency


async def _async_scheduled(
    clients: Clients,
    stop_code: int,
    routes: list[RouteInfo],
    realtime_failed: bool,
) -> list[Arrival]:
    """Timetable rows for the modes SIRI does not carry.

    Light rail, cable tram and rail publish nothing to SIRI, so their lines are
    always filled from the index. If curlbus itself failed, every line the index
    knows about is filled instead, so the card degrades to a timetable rather
    than to an empty box.
    """
    wanted = {
        route.line_ref
        for route in routes
        if realtime_failed or route.route_type not in REALTIME_ROUTE_TYPES
    }
    if not wanted and not realtime_failed:
        return []
    try:
        scheduled = await clients.index.async_departures(stop_code)
    except IsraelTransitError as err:
        _LOGGER.debug("No timetable for stop %s: %s", stop_code, err)
        return []
    if not routes:  # unknown line mix -- show everything the index has
        return scheduled
    return [a for a in scheduled if a.line_ref in wanted]


async def _async_rail(
    clients: Clients,
    stop: Stop,
    routes: list[RouteInfo],
    destination: str | None,
) -> list[Arrival]:
    """Real departures with live delays, when a rail destination is set.

    rail.co.il only answers for an origin/destination pair, so this is the one
    part of the card that needs the user to say where they are going. Without
    it the rail rows still appear, from the timetable.
    """
    if not destination or not any(r.route_type == ROUTE_TYPE_RAIL for r in routes):
        return []
    origin = RailClient.station_id(stop.name)
    if origin is None:
        _LOGGER.debug("Stop %s (%s) is not a known rail station", stop.code, stop.name)
        return []
    try:
        return await clients.rail.departures(origin, destination)
    except IsraelTransitError as err:
        _LOGGER.debug("Rail lookup failed for stop %s: %s", stop.code, err)
        return []


class IsraelTransitCoordinator(DataUpdateCoordinator[StopData]):
    """Poll one stop on the interval configured for it."""

    config_entry: IsraelTransitConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: IsraelTransitConfigEntry,
        subentry: ConfigSubentry,
        clients: Clients,
    ) -> None:
        self.clients = clients
        self.subentry = subentry
        self.stop_code = int(subentry.data[CONF_STOP_CODE])
        # None until the first read, so the first one is not logged as news.
        self._realtime_ok: bool | None = None
        interval = subentry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self.stop_code}",
            config_entry=entry,
            update_interval=timedelta(seconds=int(interval)),
        )

    @property
    def rail_destination(self) -> str | None:
        destination: str | None = self.subentry.data.get(CONF_RAIL_DESTINATION)
        return destination or None

    @callback
    def async_update_listeners(self) -> None:
        """Tell the entities, and then any trigger listening for this stop."""
        super().async_update_listeners()
        async_dispatcher_send(self.hass, signal_stop_updated(self.stop_code), self)

    async def _async_update_data(self) -> StopData:
        # Routes and the timetable are local SQLite reads, so an update is one
        # curlbus call and nothing else over the network.
        try:
            data = await async_fetch_stop(
                self.clients, self.stop_code, rail_destination=self.rail_destination
            )
        except IsraelTransitError as err:
            # The index answers throughout a rebuild now, but not through the
            # swap at the end of one, nor through the very first build. A stop
            # curlbus will not answer for cannot be identified without it, and
            # it has not gone anywhere, so this is not worth an error and a
            # screen full of unavailable entities.
            if self.clients.index.building and self.data is not None:
                _LOGGER.debug(
                    "Keeping the last board for stop %s while the index rebuilds",
                    self.stop_code,
                )
                return self.data
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="stop_update_failed",
                translation_placeholders={
                    "stop_code": str(self.stop_code),
                    "error": str(err),
                },
            ) from err

        self._async_log_realtime(data)
        self.clients.async_note_realtime(self.stop_code, data)
        return data

    @callback
    def _async_log_realtime(self, data: StopData) -> None:
        """Log losing real-time once, and getting it back once.

        Losing it is not a failed update -- the board falls back to the
        timetable -- so the coordinator's own unavailable logging never sees it.
        """
        ok = data.realtime_error is None
        if ok == self._realtime_ok:
            return
        if not ok:
            _LOGGER.info(
                "Real-time is unavailable for stop %s, showing the timetable: %s",
                self.stop_code,
                data.realtime_error,
            )
        elif self._realtime_ok is not None:
            _LOGGER.info("Real-time is back for stop %s", self.stop_code)
        self._realtime_ok = ok
