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

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import monotonic
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp

from .const import (
    CURLBUS_BASE,
    MAX_ARRIVALS,
    RAIL_API_KEY,
    RAIL_BASE,
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
    """Whole minutes from now until ``when``; never negative."""
    now = now or datetime.now(ISRAEL_TZ)
    return max(0, int((when - now).total_seconds() // 60))


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
            eta = parse_dt(visit.get("eta"))
            if eta is None:
                continue
            route = ((visit.get("static_info") or {}).get("route")) or {}
            location = visit.get("location") or {}
            arrivals.append(
                Arrival(
                    line_name=str(visit.get("line_name") or "?"),
                    eta=eta,
                    is_realtime=True,
                    destination=(route.get("destination") or {}).get("name"),
                    operator=(route.get("agency") or {}).get("name"),
                    line_ref=str(visit["line_id"]) if visit.get("line_id") else None,
                    vehicle_ref=visit.get("vehicle_ref"),
                    vehicle_lat=_as_float(location.get("lat")),
                    vehicle_lon=_as_float(location.get("lon")),
                    departed=parse_dt(visit.get("departed")),
                )
            )

    arrivals.sort(key=lambda a: a.eta)
    return stop, arrivals[:MAX_ARRIVALS]


class CurlbusClient:
    """Real-time arrivals. Fails soft so callers can use the timetable."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        # קוד תחנה -> (מספר כישלונות רצופים, מתי מותר לנסות שוב).
        self._failures: dict[int, tuple[int, float]] = {}

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

        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
        try:
            async with self._session.get(
                f"{CURLBUS_BASE}/{stop_code}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=25),
            ) as response:
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
        except ValueError as err:
            self._note_failure(stop_code)
            raise RealtimeUnavailable(f"curlbus sent malformed JSON: {err}") from err
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


def parse_rail(payload: dict[str, Any]) -> list[Arrival]:
    """Turn a searchTrain response into arrivals carrying real delays."""
    result = (payload or {}).get("result") or {}
    arrivals: list[Arrival] = []
    for travel in result.get("travels") or []:
        trains = travel.get("trains") or []
        if not trains:
            continue
        first = trains[0]
        departure = parse_dt(travel.get("departureTime")) or parse_dt(
            first.get("departureTime")
        )
        if departure is None:
            continue
        origin = first.get("orignStation")  # the API's own spelling
        delay = next(
            (
                e.get("difMin")
                for e in first.get("etaDiffTimes") or []
                if e.get("stationId") == origin
            ),
            None,
        )
        destination_id = str(trains[-1].get("destinationStation") or "")
        arrivals.append(
            Arrival(
                line_name=str(first.get("trainNumber") or "רכבת"),
                eta=departure + timedelta(minutes=int(delay or 0)),
                is_realtime=delay is not None,
                destination=RAIL_STATIONS.get(destination_id, destination_id),
                operator="רכבת ישראל",
                route_type="2",
                platform=str(first.get("originPlatform") or "") or None,
                delay_minutes=int(delay) if delay is not None else None,
            )
        )
    arrivals.sort(key=lambda a: a.eta)
    return arrivals


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
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise RealtimeUnavailable(f"rail.co.il unreachable: {err}") from err
        except ValueError as err:
            raise RealtimeUnavailable(f"rail.co.il sent malformed JSON: {err}") from err
        return parse_rail(payload)
