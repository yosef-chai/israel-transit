"""Clients for the live Israeli public-transport data sources.

The split is deliberate, and follows what each source can actually do:

* curlbus -- real-time SIRI arrivals. Buses and shared taxis only; light rail,
  cable tram and rail report nothing to SIRI. curlbus also answers with a
  plain-text HTTP 500 for stop codes its older static database does not know
  (the Dankal platforms, for instance), so it is never used to establish the
  identity of a stop.
* rail.co.il -- Israel Railways, which is absent from SIRI entirely.

Stop identity, stop search, the lines serving a stop, stop patterns and
timetables all come from the local GTFS index instead; see :mod:`.gtfs`.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import monotonic
from typing import Any, Final
from zoneinfo import ZoneInfo

import aiohttp

from .const import (
    CURLBUS_BASE,
    CURLBUS_BURST,
    CURLBUS_MAX_WAIT,
    CURLBUS_TIMEOUT,
    CURLBUS_WINDOW,
    MAX_ARRIVALS,
    RAIL_API_KEY,
    RAIL_BASE,
    RAIL_TIMEOUT,
    REALTIME_BACKOFF_BASE,
    REALTIME_BACKOFF_MAX,
    REALTIME_FAILURES_BEFORE_BACKOFF,
    REALTIME_ROUTE_TYPES,
    USER_AGENT,
)
from .rail_stations import RAIL_STATIONS, rail_station_id

_LOGGER = logging.getLogger(__name__)

# Transit data is Israel-local regardless of how the Home Assistant host is set.
ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

_LANG_KEYS = {"he": "HE", "iw": "HE", "en": "EN", "ar": "AR"}


class IsraelTransitError(Exception):
    """Base error for this integration."""


class RealtimeUnavailable(IsraelTransitError):
    """Real-time data could not be obtained; fall back to the timetable."""


class InvalidStop(IsraelTransitError):
    """The stop code is not known to the data source."""


class RateLimited(RealtimeUnavailable):
    """curlbus ענה 429: השירות מגביל, התחנה עצמה בסדר."""


def _retry_after_header(value: str | None) -> float:
    """Retry-After בשניות, בין 1 ל-60. תאריך HTTP או ערך משובש נחשבים לחלון אחד."""
    try:
        return float(min(max(int(value or ""), 1), 60))
    except ValueError:
        return CURLBUS_WINDOW


def localized(value: Any, lang: str = "he", default: str = "") -> str:
    """Return one string from either a plain string or an HE/EN/AR mapping."""
    if value is None:
        return default
    if isinstance(value, str):
        return value or default
    if not isinstance(value, dict):
        return default
    key = _LANG_KEYS.get(lang.lower()[:2], "HE")
    for candidate in (key, "HE", "EN", "AR"):
        if value.get(candidate):
            return str(value[candidate])
    return default


def parse_dt(raw: Any) -> datetime | None:
    """Parse the datetime shapes these APIs emit, tolerating their junk values.

    curlbus sends the string ``"None"`` where a timestamp belongs, and Stride
    has been seen emitting out-of-range years, so this never raises.
    """
    if not raw or not isinstance(raw, str) or raw in ("None", "null"):
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ISRAEL_TZ)
    return parsed


def minutes_until(when: datetime, now: datetime | None = None) -> int:
    """Whole minutes from now until ``when``; never negative.

    לפי timestamp ולא בחיסור datetime: שני זמנים עם אותו ZoneInfo מחוסרים כשעון
    קיר, ובימים שהשעון זז זה מוסיף או מוריד שעה.
    """
    now = now or datetime.now(ISRAEL_TZ)
    return max(0, int((when.timestamp() - now.timestamp()) // 60))


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_train_number(value: Any) -> str | None:
    """מספר רכבת בלי אפסים מובילים, כדי ש-SIRI ו-rail.co.il יתאימו זה לזה."""
    text = str(value).strip() if value is not None else ""
    return (text.lstrip("0") or "0") if text else None


CANCELLED_STATUSES: Final = frozenset({"cancelled", "canceled"})


def line_sort_key(name: str) -> tuple[int, str]:
    """Sort line 5 before line 41, and both before line 5-aleph."""
    digits = "".join(c for c in str(name) if c.isdigit())
    return (int(digits) if digits else 9_999, str(name))


@dataclass(slots=True)
class Stop:
    """A Ministry of Transport stop, as published in the GTFS feed."""

    code: int
    name: str
    city: str | None = None
    lat: float | None = None
    lon: float | None = None
    # Both come out of stop_desc; the street is what makes "city + street"
    # searchable, since a stop is usually named for a landmark rather than
    # for the road it stands on.
    street: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "city": self.city,
            "street": self.street,
            "lat": self.lat,
            "lon": self.lon,
        }


@dataclass(slots=True)
class Arrival:
    """One upcoming vehicle at a stop, real-time or scheduled."""

    line_name: str
    eta: datetime
    is_realtime: bool
    destination: Any = None
    operator: Any = None
    line_ref: str | None = None
    route_type: str | None = None
    vehicle_ref: str | None = None
    vehicle_lat: float | None = None
    vehicle_lon: float | None = None
    departed: datetime | None = None
    platform: str | None = None
    delay_minutes: int | None = None
    # מתי curlbus ראה את הרכב לאחרונה, כדי שהכרטיס ידע כמה המיקום ישן.
    vehicle_seen: datetime | None = None
    # זמן ההגעה המתוכנן לתחנה, כשהנסיעה זוהתה בלוח הזמנים.
    scheduled: datetime | None = None
    # שעת היציאה המתוכננת מתחנת המוצא לפי GTFS. בשורה חיה התפקיד הזה של departed.
    origin: datetime | None = None
    cancelled: bool = False
    train_number: str | None = None
    # מזהה המפעיל ותחנת היעד, לזיהוי נסיעה כשה-route_id לא מוכר.
    operator_id: str | None = None
    dest_code: int | None = None

    def as_dict(self, lang: str = "he", now: datetime | None = None) -> dict[str, Any]:
        return {
            "line_name": self.line_name,
            "line_ref": self.line_ref,
            "eta": self.eta.isoformat(),
            "minutes": minutes_until(self.eta, now),
            "is_realtime": self.is_realtime,
            "destination": localized(self.destination, lang) or None,
            "operator": localized(self.operator, lang) or None,
            "route_type": self.route_type,
            "vehicle_ref": self.vehicle_ref,
            "vehicle_lat": self.vehicle_lat,
            "vehicle_lon": self.vehicle_lon,
            "departed": self.departed.isoformat() if self.departed else None,
            "platform": self.platform,
            "delay_minutes": self.delay_minutes,
            "vehicle_seen": (
                self.vehicle_seen.isoformat() if self.vehicle_seen else None
            ),
            "scheduled": self.scheduled.isoformat() if self.scheduled else None,
            "cancelled": self.cancelled,
            "train_number": self.train_number,
        }


@dataclass(slots=True)
class RouteInfo:
    """A GTFS route -- one direction / alternative of a line."""

    route_id: int
    line_ref: str
    short_name: str
    long_name: str
    agency: str
    route_type: str
    headsign: str = ""

    @property
    def destination(self) -> str:
        """What the vehicle shows on the front.

        ``trip_headsign`` is written for riders and is preferred. Falling back
        to ``route_long_name`` means unpicking
        ``origin-city<->destination-city-direction``
        (``נווה יעקב - צפון-ירושלים<->הדסה עין כרם-ירושלים-20``), whose far half
        still carries a city and a direction code nobody sees on the vehicle.
        """
        if self.headsign:
            return self.headsign
        if "<->" not in self.long_name:
            return self.long_name
        tail = self.long_name.split("<->", 1)[1].strip()
        parts = [part.strip() for part in tail.split("-") if part.strip()]
        if parts and parts[-1].rstrip("#").isdigit():
            parts.pop()  # direction code
        if len(parts) > 1:
            parts.pop()  # city qualifier
        return "-".join(parts) or tail

    def as_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "line_ref": self.line_ref,
            "line_name": self.short_name or self.line_ref,
            "long_name": self.long_name,
            "destination": self.destination,
            "operator": self.agency,
            "route_type": self.route_type,
            "has_realtime": self.route_type in REALTIME_ROUTE_TYPES,
        }


@dataclass(slots=True)
class RouteStop:
    """One stop in a line's ordered stop sequence.

    Times are stored as an offset from the start of the run, not as wall clock,
    so the detail view can show times for the vehicle actually being tracked
    rather than for whichever sample trip happened to be indexed.
    """

    sequence: int
    stop: Stop
    offset_seconds: int = 0

    def as_dict(self, departed: datetime | None = None) -> dict[str, Any]:
        arrival = (
            departed + timedelta(seconds=self.offset_seconds) if departed else None
        )
        return {
            "sequence": self.sequence,
            **self.stop.as_dict(),
            "offset_seconds": self.offset_seconds,
            "arrival_time": arrival.isoformat() if arrival else None,
        }


# ---------------------------------------------------------------------------
# curlbus -- real-time arrivals
# ---------------------------------------------------------------------------


def parse_curlbus(payload: dict[str, Any]) -> tuple[Stop | None, list[Arrival]]:
    """Turn a curlbus JSON body into a stop and its real-time arrivals.

    An empty ``visits`` list is a valid answer meaning "nothing due right now",
    which is different from an invalid stop code.
    """
    errors = payload.get("errors")
    if errors:
        raise InvalidStop("; ".join(str(e) for e in errors))

    stop: Stop | None = None
    info = payload.get("stop_info") or {}
    if info:
        location = info.get("location") or {}
        address = info.get("address") or {}
        city = address.get("city_multilingual") or address.get("city")
        stop = Stop(
            code=int(info.get("code") or 0),
            name=localized(info.get("name")),
            city=localized(city) or None,
            lat=location.get("lat"),
            lon=location.get("lon"),
        )

    arrivals: list[Arrival] = []
    for visits in (payload.get("visits") or {}).values():
        for visit in visits or []:
            cancelled = str(visit.get("status") or "").lower() in CANCELLED_STATUSES
            departed = parse_dt(visit.get("departed"))
            eta = parse_dt(visit.get("eta"))
            # ביטול בלי ETA נשמר כסימון, בזמן היציאה מהמוצא ובלי is_realtime:
            # המיזוג מצמיד אותו לשורת לוח הזמנים שלו, או משמיט אותו.
            when = eta if eta is not None else (departed if cancelled else None)
            if when is None:
                continue
            route = ((visit.get("static_info") or {}).get("route")) or {}
            location = visit.get("location") or {}
            destination_id = str(visit.get("destination_id") or "")
            arrivals.append(
                Arrival(
                    line_name=str(visit.get("line_name") or "?"),
                    eta=when,
                    is_realtime=eta is not None,
                    destination=(route.get("destination") or {}).get("name"),
                    operator=(route.get("agency") or {}).get("name"),
                    line_ref=str(visit["line_id"]) if visit.get("line_id") else None,
                    vehicle_ref=visit.get("vehicle_ref"),
                    vehicle_lat=_as_float(location.get("lat")),
                    vehicle_lon=_as_float(location.get("lon")),
                    departed=departed,
                    vehicle_seen=parse_dt(visit.get("timestamp")),
                    cancelled=cancelled,
                    operator_id=str(visit["operator_id"])
                    if visit.get("operator_id")
                    else None,
                    dest_code=int(destination_id) if destination_id.isdigit() else None,
                )
            )

    arrivals.sort(key=lambda a: a.eta)
    return stop, _without_duplicates(arrivals)[:MAX_ARRIVALS]


# שני ביקורים של אותה נסיעה בהפרש קטן מזה הם אותו ביקור שדווח פעמיים.
_DUPLICATE_WINDOW: Final = timedelta(minutes=2)


def _without_duplicates(arrivals: list[Arrival]) -> list[Arrival]:
    """מסיר ביקור שדווח פעמיים, למשל כשאוטובוס הוחלף באמצע הנסיעה.

    אותו קו ואותה יציאה מהמוצא עם ETA רחוק יותר הם ביקור שני אמיתי, כמו קו מעגלי
    שעובר בתחנה בתחילת הנסיעה ובסופה, ונשארים. מבין הכפולים נשאר העדכני.
    """
    kept: list[Arrival] = []
    for arrival in arrivals:
        twin = next(
            (
                other
                for other in kept
                if arrival.departed is not None
                and other.line_ref == arrival.line_ref
                and other.departed == arrival.departed
                and abs(other.eta - arrival.eta) < _DUPLICATE_WINDOW
            ),
            None,
        )
        if twin is None:
            kept.append(arrival)
        elif _seen(arrival) > _seen(twin):
            kept[kept.index(twin)] = arrival
    return kept


def _seen(arrival: Arrival) -> float:
    return arrival.vehicle_seen.timestamp() if arrival.vehicle_seen else 0.0


class CurlbusClient:
    """Real-time arrivals. Fails soft so callers can use the timetable."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        # קוד תחנה -> (מספר כישלונות רצופים, מתי מותר לנסות שוב).
        self._failures: dict[int, tuple[int, float]] = {}
        # מתי יצאו, או ייצאו, הבקשות האחרונות, ועד מתי curlbus ביקש שלא נשאל.
        self._sent: deque[float] = deque(maxlen=CURLBUS_BURST)
        self._blocked_until = 0.0

    async def _wait_for_slot(self, stop_code: int) -> None:
        """ממתין לתור בחלון של curlbus, או זורק כשהתור ארוך מ-CURLBUS_MAX_WAIT."""
        now = monotonic()
        start = max(now, self._blocked_until)
        if len(self._sent) == CURLBUS_BURST:
            start = max(start, self._sent[0] + CURLBUS_WINDOW)
        if start - now > CURLBUS_MAX_WAIT:
            raise RealtimeUnavailable(
                f"curlbus is rate limiting; skipped stop {stop_code} this round"
            )
        # נרשם לפני ההמתנה ובלי await באמצע, כדי שקריאות מקבילות יקבלו תורות שונים.
        self._sent.append(start)
        if start > now:
            await asyncio.sleep(start - now)

    def _retry_after(self, stop_code: int) -> float:
        """כמה שניות נותרו עד שמותר לשאול שוב על התחנה הזו. 0 אם מותר עכשיו."""
        failures, until = self._failures.get(stop_code, (0, 0.0))
        if failures < REALTIME_FAILURES_BEFORE_BACKOFF:
            return 0.0
        return max(0.0, until - monotonic())

    def _note_failure(self, stop_code: int) -> None:
        failures = self._failures.get(stop_code, (0, 0.0))[0] + 1
        delay = min(
            REALTIME_BACKOFF_BASE * 2 ** (failures - REALTIME_FAILURES_BEFORE_BACKOFF),
            REALTIME_BACKOFF_MAX,
        )
        self._failures[stop_code] = (failures, monotonic() + delay)

    async def arrivals(self, stop_code: int) -> tuple[Stop | None, list[Arrival]]:
        """Fetch live arrivals, or raise :class:`RealtimeUnavailable`.

        תחנה שנכשלה כמה פעמים ברציפות לא נשאלת שוב עד שחלון ההמתנה שלה נגמר:
        curlbus הוא שירות קהילתי אחד, וקוד שהוא לא מכיר לא ילמד להכיר תוך דקה.
        """
        if (wait := self._retry_after(stop_code)) > 0:
            raise RealtimeUnavailable(
                f"curlbus has no data for stop {stop_code}; retrying in {int(wait)}s"
            )
        try:
            return await self._fetch(stop_code)
        except RateLimited:
            # פעם אחת, אחרי ה-Retry-After: חסימה של 10 שניות לא שווה סבב בלי זמן אמת.
            return await self._fetch(stop_code)

    async def _fetch(self, stop_code: int) -> tuple[Stop | None, list[Arrival]]:
        await self._wait_for_slot(stop_code)
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        try:
            async with self._session.get(
                f"{CURLBUS_BASE}/{stop_code}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=CURLBUS_TIMEOUT),
            ) as response:
                if response.status == 429:
                    retry = _retry_after_header(response.headers.get("Retry-After"))
                    self._blocked_until = max(self._blocked_until, monotonic() + retry)
                    raise RateLimited(f"curlbus HTTP 429 for stop {stop_code}")
                # Seen in the wild: HTTP 500 with a plain-text body for stop
                # codes curlbus does not know, so check both the status and the
                # content type before trusting the body.
                if response.status >= 400:
                    raise RealtimeUnavailable(
                        f"curlbus HTTP {response.status} for stop {stop_code}"
                    )
                if "json" not in (response.content_type or ""):
                    raise RealtimeUnavailable(
                        f"curlbus sent {response.content_type!r} for stop {stop_code}"
                    )
                payload = await response.json(content_type=None)

            if not isinstance(payload, dict):
                raise RealtimeUnavailable("curlbus sent an unexpected payload")
            result = parse_curlbus(payload)
        except (TimeoutError, aiohttp.ClientError) as err:
            self._note_failure(stop_code)
            raise RealtimeUnavailable(f"curlbus unreachable: {err}") from err
        except (ValueError, TypeError, AttributeError, KeyError) as err:
            self._note_failure(stop_code)
            raise RealtimeUnavailable(f"curlbus sent malformed JSON: {err}") from err
        except RateLimited:
            raise
        except IsraelTransitError:
            # RealtimeUnavailable מלמעלה, ו-InvalidStop מהפענוח: שניהם תשובה
            # שלילית על התחנה הזו, ושניהם ראויים להאטה.
            self._note_failure(stop_code)
            raise

        self._failures.pop(stop_code, None)
        return result


# ---------------------------------------------------------------------------
# Israel Railways
# ---------------------------------------------------------------------------


def parse_rail(payload: Any) -> list[Arrival]:
    """Turn a searchTrain response into arrivals carrying real delays.

    לא זורק לעולם: זו העשרה בלבד, ונסיעה עם שדה משובש פשוט מדולגת.
    """
    result = payload.get("result") if isinstance(payload, dict) else None
    travels = result.get("travels") if isinstance(result, dict) else None
    arrivals: list[Arrival] = []
    for travel in travels if isinstance(travels, list) else []:
        try:
            arrival = _rail_arrival(travel)
        except (AttributeError, TypeError, ValueError, IndexError):
            continue
        if arrival is not None:
            arrivals.append(arrival)
    arrivals.sort(key=lambda a: a.eta)
    return arrivals


def _rail_arrival(travel: dict[str, Any]) -> Arrival | None:
    trains = travel.get("trains") or []
    if not trains:
        return None
    first = trains[0]
    departure = parse_dt(travel.get("departureTime")) or parse_dt(
        first.get("departureTime")
    )
    if departure is None:
        return None
    origin = first.get("orignStation")  # the API's own spelling
    delay = next(
        (
            _as_int(e.get("difMin"))
            for e in first.get("etaDiffTimes") or []
            if e.get("stationId") == origin
        ),
        None,
    )
    destination_id = str(trains[-1].get("destinationStation") or "")
    train_number = normalize_train_number(first.get("trainNumber"))
    return Arrival(
        line_name=train_number or "רכבת",
        eta=departure + timedelta(minutes=delay or 0),
        is_realtime=delay is not None,
        destination=RAIL_STATIONS.get(destination_id, destination_id),
        operator="רכבת ישראל",
        route_type="2",
        platform=str(first.get("originPlatform") or "") or None,
        delay_minutes=delay,
        scheduled=departure,
        train_number=train_number,
    )


class RailClient:
    """Israel Railways timetable, including its real-time departure delays."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    @staticmethod
    def station_id(name: str) -> str | None:
        """Map a GTFS rail stop name to a rail.co.il station id."""
        return rail_station_id(name)

    async def departures(
        self,
        from_station: str,
        to_station: str,
        when: datetime | None = None,
    ) -> list[Arrival]:
        when = when or datetime.now(ISRAEL_TZ)
        body = {
            "fromStation": str(from_station),
            "toStation": str(to_station),
            "date": when.strftime("%Y-%m-%d"),
            "hour": when.strftime("%H:%M"),
            "scheduleType": "ByDeparture",
            "systemType": "2",
            "languageId": "Hebrew",
        }
        headers = {
            "ocp-apim-subscription-key": RAIL_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        try:
            async with self._session.post(
                f"{RAIL_BASE}/timetable/searchTrain",
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=RAIL_TIMEOUT),
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise RealtimeUnavailable(f"rail.co.il unreachable: {err}") from err
        except ValueError as err:
            raise RealtimeUnavailable(f"rail.co.il sent malformed JSON: {err}") from err
        return parse_rail(payload)
