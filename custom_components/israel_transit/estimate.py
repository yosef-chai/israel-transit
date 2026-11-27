"""זמן הגעה משוער מהמיקום החי של הרכב, כשאין ETA מהמפעיל.

תמונת ה-SIRI של הסדנא לידע ציבורי (AllActiveTripsFilter) נותנת לכל רכב את
המרחק שעבר מתחילת הנסיעה ואת העצירה האחרונה (Order), בלי זמן הגעה. כאן
המיקום מתורגם לזמן המתוכנן באותה נקודה, ההפרש מזמן הדיווח הוא העיכוב, והעיכוב
מוסף לזמן המתוכנן בתחנה.

הכל בהפרשי שניות מתוך הפרופיל, מעוגן ב-scheduled_target (UTC) של השורה, ולכן
חצות, תאריך השירות ומעבר שעון לא נכנסים לחישוב. אין כאן I/O.
"""

from __future__ import annotations

from array import array
from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from .api import Arrival

# שורה חיה ושורת לוח זמנים הן אותה נסיעה כשהיציאה מהמוצא קרובה עד כדי זה.
ORIGIN_WINDOW_S: Final = 60
# רכבת ישראל מקבלת עיכוב מ-rail.co.il, ולא מהערכה לפי מיקום.
_RAIL: Final = "2"

# רכב שעבר את התחנה במרחק כזה מעבר לה כבר לא יגיע אליה.
PASSED_MARGIN_M: Final = 50
# Order סוטה לפעמים מהמרחק בעצירה או שתיים; מעבר לזה אחד מהם שגוי.
ORDER_TOLERANCE: Final = 2
# דיווח ישן מזה, או מהעתיד יותר מזה, לא מתאר את הרכב עכשיו.
MAX_REPORT_AGE_S: Final = 420
MAX_FUTURE_S: Final = 120
# הקדמה של יותר מ-20 דק' או איחור של יותר מ-90 הם כמעט תמיד שיבוץ שגוי.
MAX_EARLY_S: Final = 20 * 60
MAX_LATE_S: Final = 90 * 60
# ETA שעבר לפני פחות מזה מוצמד לעכשיו; לפני יותר, הרכב כנראה כבר עבר.
GRACE_S: Final = 90
# רכב שמאחר נוסע לאט מהלוח, והקטע שנשאר יארך באותו יחס. נמדד מול הגעה בפועל:
# הקטע שנשאר ארך פי 1.5 ויותר מהלוח. התקרה שמרנית, כי חלק מהאיחור הוא יציאה
# מאוחרת מהמוצא ולא קצב; ואחרי פחות מ-5 דק' נסיעה הקצב עוד לא אומר כלום.
PACE_CAP: Final = 1.3
PACE_MIN_ELAPSED_S: Final = 300


@dataclass(slots=True, frozen=True)
class Profile:
    """הזמנים המתוכננים של נסיעה אחת, מהמוצא ועד התחנה המבוקשת האחרונה בה."""

    seqs: array[int]
    dists: array[int]
    arrs: array[int]
    deps: array[int]
    # האינדקסים שיש להם מרחק, ואם המרחקים עליהם לא יורדים (ולפחות שניים).
    vidx: tuple[int, ...]
    dists_valid: bool

    @classmethod
    def from_blobs(
        cls, seqs: bytes, dists: bytes, arrs: bytes, deps: bytes | None
    ) -> Profile:
        s, d, a = array("i"), array("i"), array("i")
        s.frombytes(seqs)
        d.frombytes(dists)
        a.frombytes(arrs)
        p = a
        if deps is not None:
            p = array("i")
            p.frombytes(deps)
        if not len(s) == len(d) == len(a) == len(p):
            raise ValueError("profile arrays differ in length")
        vidx = tuple(i for i, value in enumerate(d) if value >= 0)
        valid = len(vidx) >= 2 and all(
            d[vidx[k]] <= d[vidx[k + 1]] for k in range(len(vidx) - 1)
        )
        return cls(s, d, a, p, vidx, valid)

    def index_of(self, seq: int) -> int | None:
        """האינדקס של stop_sequence בפרופיל, או None כשאינו בו."""
        i = bisect_left(self.seqs, seq)
        return i if i < len(self.seqs) and self.seqs[i] == seq else None


@dataclass(slots=True, frozen=True)
class Vehicle:
    """רכב אחד מתמונת ה-SIRI. זמנים ב-epoch שניות."""

    origin: int
    recorded_at: int
    order: int | None
    dist: int | None
    lat: float | None
    lon: float | None
    vehicle_ref: str
    journey_ref: int | None


Status = Literal["ok", "passed", "unknown"]


@dataclass(slots=True, frozen=True)
class EstimateResult:
    status: Status
    eta: int | None = None
    delay_s: int | None = None
    by_dist: bool = False


UNKNOWN: Final = EstimateResult("unknown")


def _order_index(profile: Profile, order: int) -> int | None:
    """העצירה של Order בפרופיל. בקפיצה במספור: העצירה שלפניה."""
    i = bisect_left(profile.seqs, order)
    if i < len(profile.seqs) and profile.seqs[i] == order:
        return i
    return i - 1 if i > 0 else None


def _dist_position(profile: Profile, dist: int) -> tuple[int, int]:
    """(הזמן המתוכנן במרחק הזה, אינדקס העצירה האחרונה לפניו)."""
    vidx = profile.vidx
    d, arrs, deps = profile.dists, profile.arrs, profile.deps
    if dist <= d[vidx[0]]:
        return deps[vidx[0]], vidx[0]
    if dist >= d[vidx[-1]]:
        return arrs[vidx[-1]], vidx[-1]
    keys = [d[i] for i in vidx]
    k = bisect_right(keys, dist) - 1
    i0, i1 = vidx[k], vidx[k + 1]
    d0, d1 = d[i0], d[i1]
    if d1 == d0:
        return arrs[i1], i0
    s0, s1 = deps[i0], arrs[i1]
    return round(s0 + (s1 - s0) * (dist - d0) / (d1 - d0)), i0


@dataclass(slots=True, frozen=True)
class Target:
    """התחנה בנסיעה: stop_sequence, וזמן ההגעה והיציאה מהמוצא לפי הלוח (epoch)."""

    seq: int
    scheduled: int
    origin: int


def _locate(
    profile: Profile, target: int, vehicle: Vehicle
) -> EstimateResult | tuple[int, bool]:
    """(הזמן המתוכנן במיקום הרכב, האם לפי מרחק), או passed / unknown."""
    order = vehicle.order
    order_i = _order_index(profile, order) if order is not None else None
    if order is not None and order > profile.seqs[-1]:
        # מעבר לסוף הפרופיל, שנגמר בתחנה המבוקשת האחרונה: עבר את כולן.
        return EstimateResult("passed")
    dist = vehicle.dist if profile.dists_valid else None
    target_dist = profile.dists[target]
    # עבר את התחנה לפי המרחק, לפני ההצלבה: הפרופיל קטוע אחרי התחנה.
    if (
        dist is not None
        and target_dist >= 0
        and dist >= target_dist + PASSED_MARGIN_M
        and (order_i is None or order_i >= target - ORDER_TOLERANCE)
    ):
        return EstimateResult("passed", by_dist=True)
    if dist is not None:
        pos_sec, at = _dist_position(profile, dist)
        # מרחק שסותר את Order ביותר משתי עצירות הוא קפיצה במד; Order אמין יותר.
        if order_i is None or abs(at - order_i) <= ORDER_TOLERANCE:
            return pos_sec, True
    if order_i is None:
        return UNKNOWN
    if order_i >= target:
        # בלי מרחק, Order על התחנה עצמה לא אומר אם הרכב לפניה או אחריה.
        return (
            EstimateResult("passed") if order_i >= target + ORDER_TOLERANCE else UNKNOWN
        )
    return profile.deps[order_i], False


def _delay(
    profile: Profile, target: int, stop: Target, vehicle: Vehicle, pos_sec: int
) -> int:
    """העיכוב בשניות, מעוגן בזמן המתוכנן של התחנה ולא בתאריך השירות."""
    pos_utc = stop.scheduled - (profile.arrs[target] - pos_sec)
    delay = vehicle.recorded_at - pos_utc
    order = vehicle.order
    # רכב שממתין במוצא לפני היציאה נחשב בזמן, לא מקדים.
    if (
        order is not None
        and order <= profile.seqs[0]
        and vehicle.recorded_at < stop.origin
    ):
        delay = max(0, delay)
    return delay


def estimate(
    profile: Profile, stop: Target, vehicle: Vehicle, now: int
) -> EstimateResult:
    """כמה הרכב מאחר, ומתי יגיע לתחנה. ראו את תיעוד המודול."""
    target = profile.index_of(stop.seq)
    age = now - vehicle.recorded_at
    if target is None or age > MAX_REPORT_AGE_S or age < -MAX_FUTURE_S:
        return UNKNOWN
    located = _locate(profile, target, vehicle)
    if isinstance(located, EstimateResult):
        return located
    pos_sec, by_dist = located
    delay = _delay(profile, target, stop, vehicle, pos_sec)
    eta = stop.scheduled + delay
    remaining = profile.arrs[target] - pos_sec
    elapsed = stop.scheduled - remaining - stop.origin
    if delay > 0 and elapsed >= PACE_MIN_ELAPSED_S:
        pace = min(PACE_CAP, (elapsed + delay) / elapsed)
        eta = vehicle.recorded_at + round(remaining * pace)
    # עיכוב לא סביר הוא שיבוץ שגוי. ETA שעבר מזמן: הרכב כנראה כבר חלף.
    if delay < -MAX_EARLY_S or delay > MAX_LATE_S or eta < now - GRACE_S:
        return UNKNOWN
    return EstimateResult("ok", max(eta, now), delay, by_dist)


def estimable(row: Arrival) -> bool:
    """שורת לוח זמנים שאפשר להעריך: יש לה נסיעה, מקום בנסיעה ושעת מוצא."""
    return (
        row.trip_idx is not None
        and row.stop_seq is not None
        and row.origin is not None
        and row.scheduled is not None
        and row.line_ref is not None
        and row.route_type != _RAIL
    )


def estimate_board(
    scheduled: Sequence[Arrival],
    by_line: Mapping[str, Sequence[Vehicle]],
    profiles: Mapping[int, Profile],
    now: int,
) -> tuple[list[Arrival], set[int]]:
    """שורות משוערות לנסיעות שיש להן רכב, ו-id() של השורות שהרכב כבר עבר.

    השיבוץ הוא רכב לנסיעה (trip_idx), אחד לאחד, כך שבקו מעגלי שני המעברים
    בתחנה נמדדים מול אותו רכב. סדר העדיפות דטרמיניסטי -- journey_ref זהה,
    הפרש מוצא קטן, ואז vehicle_ref -- כדי שה-ETA לא יקפוץ בין רכבי תגבור.
    """
    trips: dict[int, list[Arrival]] = {}
    for row in scheduled:
        if estimable(row) and row.trip_idx in profiles:
            trips.setdefault(row.trip_idx, []).append(row)  # type: ignore[arg-type]
    pairs: list[tuple[int, int, str, int, int]] = []
    vehicles: dict[int, Vehicle] = {}
    for trip_idx, rows in trips.items():
        head = rows[0]
        assert head.origin is not None and head.line_ref is not None
        origin = int(head.origin.timestamp())
        for vehicle in by_line.get(head.line_ref, ()):
            gap = abs(vehicle.origin - origin)
            if gap > ORIGIN_WINDOW_S:
                continue
            same = (
                head.journey_ref is not None and vehicle.journey_ref == head.journey_ref
            )
            key = id(vehicle)
            vehicles[key] = vehicle
            pairs.append((0 if same else 1, gap, vehicle.vehicle_ref, trip_idx, key))
    pairs.sort()
    taken_trips: set[int] = set()
    taken_vehicles: set[int] = set()
    estimated: list[Arrival] = []
    passed: set[int] = set()
    for _, _, _, trip_idx, key in pairs:
        if trip_idx in taken_trips or key in taken_vehicles:
            continue
        taken_trips.add(trip_idx)
        taken_vehicles.add(key)
        vehicle = vehicles[key]
        profile = profiles[trip_idx]
        for row in trips[trip_idx]:
            assert row.scheduled is not None and row.origin is not None
            assert row.stop_seq is not None
            stop = Target(
                row.stop_seq,
                int(row.scheduled.timestamp()),
                int(row.origin.timestamp()),
            )
            result = estimate(profile, stop, vehicle, now)
            if result.status == "passed":
                passed.add(id(row))
            elif result.status == "ok" and result.eta is not None:
                estimated.append(_estimated_row(row, vehicle, result.eta))
    return estimated, passed


def _estimated_row(row: Arrival, vehicle: Vehicle, eta: int) -> Arrival:
    """השורה המתוכננת כשורה חיה משוערת. departed הוא המוצא שבלוח, לא של SIRI."""
    tz = row.scheduled.tzinfo if row.scheduled else UTC
    return replace(
        row,
        eta=datetime.fromtimestamp(eta, UTC).astimezone(tz),
        is_realtime=True,
        estimated=True,
        departed=row.origin,
        vehicle_ref=vehicle.vehicle_ref or None,
        vehicle_lat=vehicle.lat,
        vehicle_lon=vehicle.lon,
        vehicle_seen=datetime.fromtimestamp(vehicle.recorded_at, UTC).astimezone(tz),
    )
