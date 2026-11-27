"""Fetching and polling for a single stop.

:func:`async_fetch_stop` holds the whole merge policy -- real-time first, the
local timetable for what SIRI does not carry -- so the polling coordinator and
the card's WebSocket command cannot drift apart. The policy itself, which needs
no Home Assistant, is in :mod:`.merge`.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
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
)
from .const import (
    CONF_RAIL_DESTINATION,
    CONF_SCAN_INTERVAL,
    CONF_STOP_CODE,
    CONF_WALK_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DEPARTED_GRACE,
    DOMAIN,
    IDLE_POLL_MAX,
    IDLE_WAKE_LEAD,
    NEW_STOP_INDEX_DELAY,
    ROUTE_TYPE_RAIL,
    SPARSE_GAP,
    SPARSE_POLL,
    TIMETABLE_REQUEST_COOLDOWN,
)
from .index import GtfsIndex
from .merge import merge_board
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
    # מתי הלוח נשלף, ב-UTC. לוח ישן מוגש לפעמים בכוונה, ואז זה מה שמסגיר אותו.
    updated_at: datetime = field(default_factory=dt_util.utcnow)
    # הנסיעה המתוכננת הבאה, רק כשאין כלום בשעות הקרובות (לילה, שבת, חג).
    next_service: Arrival | None = None
    # מתי הלוח יתעדכן שוב, כדי שהכרטיס לא יקרא "ישן" ללוח שמתעדכן לאט בכוונה.
    refresh_seconds: int = DEFAULT_SCAN_INTERVAL

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

    def running(self, now: datetime | None = None) -> list[Arrival]:
        """מה שבאמת עוד יגיע: בלי מה שכבר עבר ובלי נסיעות מבוטלות."""
        return [a for a in self.upcoming(now) if not a.cancelled]

    def as_dict(self, lang: str = "he", now: datetime | None = None) -> dict[str, Any]:
        return {
            "stop": self.stop.as_dict(),
            "arrivals": [a.as_dict(lang, now) for a in self.upcoming(now)],
            "routes": [r.as_dict() for r in self.routes],
            "has_realtime": self.has_realtime,
            "realtime_error": self.realtime_error,
            "updated_at": self.updated_at.isoformat(),
            "next_service": (
                self.next_service.as_dict(lang, now) if self.next_service else None
            ),
            "refresh_seconds": self.refresh_seconds,
        }


def poll_interval(base: timedelta, data: StopData, now: datetime) -> timedelta:
    """כמה לחכות לרענון הבא של תחנה. אף פעם לא פחות מ-``base``.

    בלי שום נסיעה בשעות הקרובות מחכים עד עשר דקות לפני הנסיעה הבאה בלוח
    הזמנים, ולא יותר מרבע שעה, כדי שגם אוטובוס שאינו בלוח יופיע בסוף. כשהנסיעה
    הקרובה רחוקה מחצי שעה, חמש דקות מספיקות. לוח ריק בלי לוח זמנים ידוע לא
    אומר כלום, ולכן נשאר בקצב הרגיל.
    """
    rows = data.running(now)
    if rows:
        return max(base, SPARSE_POLL) if rows[0].eta - now >= SPARSE_GAP else base
    if data.next_service is None:
        return base
    return max(base, min(data.next_service.eta - now - IDLE_WAKE_LEAD, IDLE_POLL_MAX))


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
        כרגיל לא גוררת בנייה מחדש של 150MB.
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
    def async_cancel_pending(self) -> None:
        self.index.async_cancel_retry()
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


@callback
def async_walk_minutes(hass: HomeAssistant, stop_code: int) -> int:
    """דקות ההליכה שהוגדרו לתחנה, או 0 לתחנה שלא הוגדרה או בלי זמן הליכה."""
    coordinator = async_find_coordinator(hass, stop_code)
    return coordinator.walk_minutes if coordinator is not None else 0


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

    # שני המקורות במקביל, כך ש-rail.co.il איטי לא מעכב את הלוח. כל אחד בולע
    # רק את השגיאות הצפויות שלו, ולכן ביטול משימה (כיבוי HA) עובר כרגיל.
    async with asyncio.TaskGroup() as group:
        live_task = group.create_task(_async_live(clients, stop_code))
        rail_task = (
            group.create_task(_async_rail(clients, stop, routes, rail_destination))
            if stop is not None
            else None
        )
    curlbus_stop, realtime, realtime_error = live_task.result()
    # Identity comes from GTFS first: curlbus does not know the newer stops
    # at all and answers with an error for them.
    stop = stop or curlbus_stop
    if stop is None:
        raise IsraelTransitError(f"Stop {stop_code} is not in the GTFS feed")
    rail = (
        rail_task.result()
        if rail_task is not None
        else await _async_rail(clients, stop, routes, rail_destination)
    )

    try:
        scheduled = await clients.index.async_departures(stop_code)
    except IsraelTransitError as err:
        _LOGGER.debug("No timetable for stop %s: %s", stop_code, err)
        scheduled = []

    data = StopData(
        stop=stop,
        arrivals=merge_board(realtime, scheduled, rail, routes, dt_util.utcnow()),
        routes=routes,
        # An empty answer is still a real-time answer: nothing is due.
        has_realtime=realtime_error is None,
        realtime_error=realtime_error,
    )
    # רק לתחנה שלוח הזמנים המלא שלה באינדקס: באחרת לוח ריק לא אומר שאין שירות,
    # כי האוטובוסים שלה בכלל לא נשמרו.
    if not data.running() and stop_code in clients.index.indexed_stops:
        try:
            data.next_service = await clients.index.async_next_departure(stop_code)
        except IsraelTransitError as err:
            _LOGGER.debug("No next service for stop %s: %s", stop_code, err)
    return data


async def _async_live(
    clients: Clients, stop_code: int
) -> tuple[Stop | None, list[Arrival], str | None]:
    """curlbus, או השגיאה שלו כטקסט. לא זורק על כשל של המקור עצמו."""
    try:
        curlbus_stop, realtime = await clients.curlbus.arrivals(stop_code)
    except IsraelTransitError as err:
        _LOGGER.debug("No real-time for stop %s: %s", stop_code, err)
        return None, [], str(err)
    return curlbus_stop, realtime, None


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
        # הקצב שהמשתמש בחר. update_interval זז ממנו למעלה כשאין מה לראות.
        self.base_interval = timedelta(seconds=int(interval))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self.stop_code}",
            config_entry=entry,
            update_interval=self.base_interval,
        )

    @property
    def rail_destination(self) -> str | None:
        destination: str | None = self.subentry.data.get(CONF_RAIL_DESTINATION)
        return destination or None

    @property
    def walk_minutes(self) -> int:
        return int(self.subentry.data.get(CONF_WALK_MINUTES) or 0)

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
            self.update_interval = self.base_interval
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
        # נקבע לפני החזרה: DataUpdateCoordinator מתזמן את הרענון הבא אחרי העדכון,
        # לפי update_interval של אותו רגע.
        self.update_interval = poll_interval(self.base_interval, data, dt_util.utcnow())
        data.refresh_seconds = int(self.update_interval.total_seconds())
        if self.update_interval != self.base_interval:
            _LOGGER.debug(
                "Stop %s has nothing due soon; next refresh in %s",
                self.stop_code,
                self.update_interval,
            )
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
