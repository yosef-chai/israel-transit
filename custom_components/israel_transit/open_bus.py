"""תמונת ה-SIRI הארצית של הסדנא לידע ציבורי: גיבוי כש-curlbus נכשל לתחנה.

הדמון של הסדנא (hasadna/open-bus-siri-requester, רישיון MIT) מושך כל כ-60 שנ'
את SIRI-SM של משרד התחבורה עם AllActiveTripsFilter, ושומר את התמונה ב-brotli
כ-YYYY/MM/DD/HH/MM.br לפי UTC. הקובץ daemon_status.json מצביע על האחרונה.

התמונה נותנת לכל רכב פעיל קו, שעת יציאה מתוכננת מהמוצא, מיקום, העצירה האחרונה
(Order) והמרחק מתחילת הנסיעה (DistanceFromStop, שהסדנא עצמה קוראת לו
distance_from_journey_start). אין בה ETA: הוא נגזר ב-:mod:`.estimate`.

תמונה אחת לכל המערכת, ורק כשיש תחנה שצריכה אותה. הפענוח (2–5MB של JSON) רץ
ב-executor, כמו שכללי HA דורשים לחישוב כבד.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Final

import aiohttp

from .api import RealtimeUnavailable, _retry_after_header
from .const import (
    OPEN_BUS_AFTER_NEW,
    OPEN_BUS_AFTER_SAME,
    OPEN_BUS_BACKOFF,
    OPEN_BUS_BASE,
    OPEN_BUS_CONNECT_TIMEOUT,
    OPEN_BUS_MAX_AGE,
    OPEN_BUS_MAX_BODY_BYTES,
    OPEN_BUS_MAX_JSON_BYTES,
    OPEN_BUS_MAX_STATUS_BYTES,
    OPEN_BUS_TIMEOUT,
    USER_AGENT,
)
from .estimate import MAX_FUTURE_S, MAX_REPORT_AGE_S, Vehicle

try:  # ב-HA תמיד קיימים; בענף הטסטים בלי HA אולי לא.
    import brotli
except ImportError:  # pragma: no cover
    brotli = None
try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None  # type: ignore[assignment]

_LOGGER = logging.getLogger(__name__)

SNAPSHOT_ID_RE: Final = re.compile(r"^\d{4}/\d{2}/\d{2}/\d{2}/\d{2}$")
_CHUNK: Final = 65536
_DECOMPRESS_STEP: Final = 1024 * 1024
# גבולות ישראל, בערך: מה שמחוץ להם (כולל 0,0) הוא מיקום שבור.
_LAT: Final = (29.0, 34.0)
_LON: Final = (34.0, 36.0)


@dataclass(slots=True)
class Snapshot:
    """הרכבים הפעילים בתמונה, לפי קו. taken_at הוא ResponseTimestamp ב-epoch."""

    taken_at: int
    by_line: dict[str, list[Vehicle]] = field(default_factory=dict)
    seen: int = 0
    dropped: int = 0


def _loads(raw: bytes) -> Any:
    try:
        return orjson.loads(raw) if orjson is not None else json.loads(raw)
    except (ValueError, TypeError) as err:
        raise RealtimeUnavailable(f"open-bus sent malformed JSON: {err}") from err


def decompress(raw: bytes, limit: int = OPEN_BUS_MAX_JSON_BYTES) -> bytes:
    """פריסת brotli עם תקרה, כך שקובץ מנופח לא ימלא את הזיכרון.

    לפי התיעוד של brotli 1.2.0: אחרי שהמגבלה נחצתה, הפונקציה process נקראת רק עם קלט ריק
    עד ש-can_accept_more_data() מחזיר True. כל קריאה מקבלת מגבלה, גם הריקות,
    אחרת ברירת המחדל (PY_SSIZE_T_MAX) פורסת הכל בבת אחת.
    """
    if brotli is None:  # pragma: no cover
        raise RealtimeUnavailable("brotli is not installed")
    decoder = brotli.Decompressor()
    parts: list[bytes] = []
    total = 0

    def take(data: bytes) -> int:
        nonlocal total
        out = decoder.process(
            data, output_buffer_limit=max(1, min(_DECOMPRESS_STEP, limit - total + 1))
        )
        total += len(out)
        if total > limit:
            raise RealtimeUnavailable("open-bus snapshot is larger than expected")
        parts.append(out)
        return len(out)

    try:
        view = memoryview(raw)
        for start in range(0, len(raw), _CHUNK):
            take(bytes(view[start : start + _CHUNK]))
            while not decoder.can_accept_more_data():
                take(b"")
        # כשהקלט נגמר can_accept_more_data כבר True, אבל פלט עוד ממתין בפנים.
        while not decoder.is_finished() and take(b""):
            pass
    except brotli.error as err:
        raise RealtimeUnavailable(
            f"open-bus snapshot is not valid brotli: {err}"
        ) from err
    if not decoder.is_finished():
        raise RealtimeUnavailable("open-bus snapshot is truncated")
    return b"".join(parts)


def _epoch(text: Any, cache: dict[str, int | None]) -> int | None:
    """ISO 8601 עם אזור זמן ל-epoch. בלי אזור זמן או משובש: None."""
    if not isinstance(text, str):
        return None
    if text in cache:
        return cache[text]
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        value = None
    else:
        value = int(parsed.timestamp()) if parsed.tzinfo is not None else None
    cache[text] = value
    return value


def _number(text: Any) -> int | None:
    if isinstance(text, int):
        return text
    if isinstance(text, str):
        text = text.strip()
        if text.isdigit():
            return int(text)
        try:
            return round(float(text))
        except ValueError:
            return None
    return None


def _coord(value: Any, bounds: tuple[float, float]) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if bounds[0] <= number <= bounds[1] else None


def _as_list(value: Any) -> list[Any]:
    """SIRI ב-JSON הופך רשימה של איבר אחד לאובייקט בודד."""
    if isinstance(value, list):
        return value
    return [] if value is None else [value]


def parse_open_bus(raw: bytes, now: float) -> Snapshot:
    """פורס ומפענח תמונה. חוסם: רק מתוך ה-executor.

    ביקור פגום מדולג ונספר ב-dropped; תמונה תקינה בלי רכבים (לילה, שבת) היא
    Snapshot ריק, לא שגיאה.
    """
    payload = _loads(decompress(raw))
    delivery = (
        payload.get("Siri", {}).get("ServiceDelivery")
        if isinstance(payload, dict)
        else None
    )
    if not isinstance(delivery, dict):
        raise RealtimeUnavailable("open-bus snapshot has no ServiceDelivery")
    if str(delivery.get("Status", "")).lower() != "true":
        raise RealtimeUnavailable("open-bus snapshot reports a failed request")
    cache: dict[str, int | None] = {}
    taken_at = _epoch(delivery.get("ResponseTimestamp"), cache)
    if taken_at is None:
        raise RealtimeUnavailable("open-bus snapshot has no ResponseTimestamp")
    snapshot = Snapshot(taken_at)
    newest: dict[tuple[str, int, str], Vehicle] = {}
    for part in _as_list(delivery.get("StopMonitoringDelivery")):
        if not isinstance(part, dict):
            continue
        for visit in _as_list(part.get("MonitoredStopVisit")):
            snapshot.seen += 1
            vehicle = _vehicle(visit, now, cache)
            if vehicle is None:
                snapshot.dropped += 1
                continue
            line, item = vehicle
            key = (line, item.origin, item.vehicle_ref)
            held = newest.get(key)
            if held is None or item.recorded_at > held.recorded_at:
                newest[key] = item
    for (line, _, _), item in newest.items():
        snapshot.by_line.setdefault(line, []).append(item)
    return snapshot


def _vehicle(
    visit: Any, now: float, cache: dict[str, int | None]
) -> tuple[str, Vehicle] | None:
    if not isinstance(visit, dict):
        return None
    journey = visit.get("MonitoredVehicleJourney")
    if not isinstance(journey, dict):
        return None
    line = journey.get("LineRef")
    origin = _epoch(journey.get("OriginAimedDepartureTime"), cache)
    recorded = _epoch(visit.get("RecordedAtTime"), cache)
    if (
        not isinstance(line, str)
        or not line.strip()
        or origin is None
        or recorded is None
    ):
        return None
    age = now - recorded
    if age > MAX_REPORT_AGE_S or age < -MAX_FUTURE_S:
        return None
    call = journey.get("MonitoredCall")
    call = call if isinstance(call, dict) else {}
    order = _number(call.get("Order"))
    dist = _number(call.get("DistanceFromStop"))
    # מרחק 0 אחרי העצירה הראשונה הוא "אין מיקום", לא חזרה למוצא (מדידת FreeBus).
    if dist is not None and (dist < 0 or (dist == 0 and order != 1)):
        dist = None
    location = journey.get("VehicleLocation")
    location = location if isinstance(location, dict) else {}
    lat = _coord(location.get("Latitude"), _LAT)
    lon = _coord(location.get("Longitude"), _LON)
    if lat is None or lon is None:
        lat = lon = None
    framed = journey.get("FramedVehicleJourneyRef")
    journey_ref = (
        _number(framed.get("DatedVehicleJourneyRef"))
        if isinstance(framed, dict)
        else None
    )
    return line.strip(), Vehicle(
        origin=origin,
        recorded_at=recorded,
        order=order,
        dist=dist,
        lat=lat,
        lon=lon,
        vehicle_ref=str(journey.get("VehicleRef") or ""),
        journey_ref=journey_ref,
    )


def parse_status(payload: Any) -> tuple[str, float]:
    """מזהה התמונה האחרונה וזמן כתיבתה (epoch), מתוך daemon_status.json."""
    if not isinstance(payload, dict):
        raise RealtimeUnavailable("open-bus status is not an object")
    snapshot_id = payload.get("last_snapshot_id")
    if not isinstance(snapshot_id, str) or not SNAPSHOT_ID_RE.match(snapshot_id):
        raise RealtimeUnavailable("open-bus status has no valid snapshot id")
    try:
        # הדמון כותב UTC בלי אזור זמן ("%Y-%m-%d %H:%M:%S").
        written = datetime.fromisoformat(str(payload.get("last_datetime_utc")))
    except ValueError as err:
        raise RealtimeUnavailable("open-bus status has no valid time") from err
    if written.tzinfo is None:
        written = written.replace(tzinfo=UTC)
    return snapshot_id, written.timestamp()


type Executor = Callable[..., Awaitable[Any]]


class OpenBusClient:
    """מוריד את התמונה לכל היותר פעם בדקה, משותף לכל התחנות."""

    def __init__(self, session: aiohttp.ClientSession, executor: Executor) -> None:
        self._session = session
        self._executor = executor
        self._lock = asyncio.Lock()
        self._snapshot: Snapshot | None = None
        self._last_id: str | None = None
        self._next_status = 0.0
        self._blocked_until = 0.0
        self._failures = 0
        self.last_error: str | None = None

    @property
    def snapshot(self) -> Snapshot | None:
        return self._snapshot

    def _fresh(self) -> Snapshot | None:
        """התמונה המוחזקת אם היא עדיין בתוקף; אחרת משחרר אותה."""
        if (
            self._snapshot is not None
            and time.time() - self._snapshot.taken_at > OPEN_BUS_MAX_AGE
        ):
            self._snapshot = None
        return self._snapshot

    async def async_snapshot(self) -> Snapshot:
        """התמונה העדכנית, או RealtimeUnavailable. קריאות במקביל חולקות הורדה אחת."""
        async with self._lock:
            now = monotonic()
            held = self._fresh()
            if held is not None and now < self._next_status:
                return held
            if now < self._blocked_until:
                # ב-backoff: בלי רשת, ובלי לקדם את המדרגה.
                if held is not None:
                    return held
                raise RealtimeUnavailable(self.last_error or "open-bus is backing off")
            try:
                await self._refresh()
            except RealtimeUnavailable as err:
                self._note_failure(str(err))
                if (held := self._fresh()) is not None:
                    return held
                raise
            if (held := self._fresh()) is None:
                raise RealtimeUnavailable("open-bus snapshot is too old")
            return held

    def _note_failure(self, message: str) -> None:
        self.last_error = message
        self._failures += 1
        step = OPEN_BUS_BACKOFF[min(self._failures, len(OPEN_BUS_BACKOFF)) - 1]
        self._blocked_until = max(
            self._blocked_until, monotonic() + step * (1 + random.uniform(0, 0.1))
        )
        if self._failures == 1:
            _LOGGER.info("Open Bus snapshot unavailable: %s", message)

    async def _refresh(self) -> None:
        status = _loads(
            await self._get("daemon_status.json", OPEN_BUS_MAX_STATUS_BYTES)
        )
        snapshot_id, written = parse_status(status)
        if time.time() - written > OPEN_BUS_MAX_AGE:
            raise RealtimeUnavailable(
                f"open-bus has not written a snapshot since {snapshot_id}"
            )
        if snapshot_id == self._last_id:
            self._next_status = monotonic() + OPEN_BUS_AFTER_SAME
            return
        raw = await self._get(f"{snapshot_id}.br", OPEN_BUS_MAX_BODY_BYTES)
        snapshot: Snapshot = await self._executor(parse_open_bus, raw, time.time())
        if time.time() - snapshot.taken_at > OPEN_BUS_MAX_AGE:
            raise RealtimeUnavailable(f"open-bus snapshot {snapshot_id} is too old")
        # ה-id נשמר רק אחרי הצלחה מלאה, כך ש-404 על קובץ טרי ינוסה שוב.
        self._snapshot = snapshot
        self._last_id = snapshot_id
        self._next_status = monotonic() + OPEN_BUS_AFTER_NEW
        if self._failures:
            _LOGGER.info("Open Bus snapshot available again")
        self._failures = 0
        self._blocked_until = 0.0
        self.last_error = None

    async def _get(self, path: str, limit: int) -> bytes:
        """גוף התשובה עד ``limit`` בתים. כל כשל הופך ל-RealtimeUnavailable."""
        try:
            async with self._session.get(
                f"{OPEN_BUS_BASE}/{path}",
                headers={"User-Agent": USER_AGENT},
                timeout=aiohttp.ClientTimeout(
                    total=OPEN_BUS_TIMEOUT, connect=OPEN_BUS_CONNECT_TIMEOUT
                ),
            ) as response:
                if response.status in (429, 503):
                    retry = _retry_after_header(response.headers.get("Retry-After"))
                    self._blocked_until = max(self._blocked_until, monotonic() + retry)
                    raise RealtimeUnavailable(f"open-bus HTTP {response.status}")
                if response.status >= 400:
                    raise RealtimeUnavailable(
                        f"open-bus HTTP {response.status} for {path}"
                    )
                parts: list[bytes] = []
                total = 0
                async for chunk in response.content.iter_chunked(_CHUNK):
                    total += len(chunk)
                    if total > limit:
                        raise RealtimeUnavailable(
                            f"open-bus {path} is larger than expected"
                        )
                    parts.append(chunk)
                return b"".join(parts)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise RealtimeUnavailable(f"open-bus unreachable: {err}") from err
