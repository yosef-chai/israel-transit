"""זמן הגעה משוער ממיקום הרכב: החישוב עצמו, והשיבוץ של רכבים לנסיעות."""

from __future__ import annotations

import importlib
from array import array
from datetime import UTC, datetime

import pytest
from conftest import PACKAGE

estimate_mod = importlib.import_module(f"{PACKAGE}.estimate")
api = importlib.import_module(f"{PACKAGE}.api")
Profile, Target, Vehicle = (
    estimate_mod.Profile,
    estimate_mod.Target,
    estimate_mod.Vehicle,
)
estimate = estimate_mod.estimate

# נסיעה של חמש עצירות, כל אחת 5 דק' וקילומטר אחרי הקודמת.
SEQS = [1, 2, 3, 4, 5]
DISTS = [0, 1000, 2000, 3000, 4000]
ARRS = [0, 300, 600, 900, 1200]
# היעד הוא העצירה החמישית, בשעה S לפי הלוח.
S = 1_800_000_000
ORIGIN = S - 1200


def profile(seqs=SEQS, dists=DISTS, arrs=ARRS, deps=None) -> object:
    blob = lambda values: array("i", values).tobytes()  # noqa: E731
    return Profile.from_blobs(
        blob(seqs), blob(dists), blob(arrs), blob(deps) if deps else None
    )


def vehicle(recorded, order=None, dist=None, origin=ORIGIN, ref="v1", journey=None):
    return Vehicle(origin, recorded, order, dist, 32.0, 34.8, ref, journey)


def target(seq=5, scheduled=S, origin=ORIGIN):
    return Target(seq, scheduled, origin)


@pytest.fixture
def constant_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """בלי הקצב: העיכוב של עכשיו נשאר עד התחנה."""
    monkeypatch.setattr(estimate_mod, "PACE_CAP", 1.0)


def test_a_late_bus_keeps_its_slow_pace_to_the_stop():
    # 450 שנ' לפי הלוח נסע ב-570: הקטע שנשאר, 750 שנ', יארך באותו יחס.
    recorded = S - 750 + 120
    result = estimate(profile(), target(), vehicle(recorded, 2, 1500), recorded)
    assert (result.eta, result.delay_s) == (recorded + 950, 120)


def test_the_pace_is_capped():
    recorded = S - 750 + 900
    result = estimate(profile(), target(), vehicle(recorded, 2, 1500), recorded)
    assert result.eta == recorded + round(750 * estimate_mod.PACE_CAP)


def test_the_pace_is_ignored_right_after_the_origin():
    # 150 שנ' לפי הלוח: מוקדם מכדי לדעת אם האיחור הוא קצב או יציאה מאוחרת.
    recorded = S - 1050 + 120
    result = estimate(profile(), target(), vehicle(recorded, 1, 500), recorded)
    assert result.eta == S + 120


def test_a_late_bus_is_late_by_where_it_is_against_the_timetable(constant_delay):
    # במרחק 1500 הלוח אומר 450 שנ' מהמוצא, כלומר S-750; הדיווח מאחר בשתי דקות.
    recorded = S - 750 + 120
    result = estimate(profile(), target(), vehicle(recorded, 2, 1500), recorded + 30)
    assert (result.status, result.eta, result.delay_s, result.by_dist) == (
        "ok",
        S + 120,
        120,
        True,
    )


def test_an_early_bus_is_early():
    recorded = S - 750 - 180
    result = estimate(profile(), target(), vehicle(recorded, 2, 1500), recorded)
    assert (result.status, result.eta) == ("ok", S - 180)


def test_without_a_distance_the_last_stop_passed_is_used(constant_delay):
    # Order=3 בלי מרחק: הזמן הוא היציאה מעצירה 3 (600), הערכת חסר מכוונת.
    recorded = S - 600 + 60
    result = estimate(profile(), target(), vehicle(recorded, 3), recorded)
    assert (result.status, result.eta, result.by_dist) == ("ok", S + 60, False)


def test_a_bus_waiting_at_its_origin_is_on_time_not_early():
    recorded = ORIGIN - 300
    result = estimate(profile(), target(), vehicle(recorded, 1, 0), recorded)
    assert (result.status, result.eta) == ("ok", S)


def test_a_bus_past_the_stop_by_distance_has_passed():
    recorded = S
    result = estimate(profile(), target(seq=3), vehicle(recorded, 3, 2100), recorded)
    assert (result.status, result.by_dist) == ("passed", True)


def test_a_bus_past_a_truncated_profile_has_passed():
    """הפרופיל נגמר בתחנה; רכב בעצירה 25 עם מרחק מעבר לסוף עבר אותה."""
    result = estimate(profile(), target(), vehicle(S, 25, 9000), S)
    assert result.status == "passed"


def test_order_beyond_the_stop_without_distance_has_passed():
    result = estimate(profile(), target(seq=3), vehicle(S, 5), S)
    assert result.status == "passed"


def test_order_on_the_stop_without_distance_is_unknown():
    """בלי מרחק אי אפשר לדעת אם הרכב לפני התחנה או אחריה."""
    assert estimate(profile(), target(seq=3), vehicle(S, 3), S).status == "unknown"
    assert estimate(profile(), target(seq=3), vehicle(S, None), S).status == "unknown"


def test_no_order_but_a_distance_beyond_the_stop_has_passed():
    result = estimate(profile(), target(seq=3), vehicle(S, None, 2600), S)
    assert (result.status, result.by_dist) == ("passed", True)


def test_a_distance_that_contradicts_order_falls_back_to_order():
    """קפיצה במד המרחק: Order אמין יותר."""
    recorded = S - 1200
    result = estimate(profile(), target(), vehicle(recorded, 1, 3900), recorded)
    # לפי Order=1 הזמן הוא 0, כלומר S-1200, ולכן בזמן.
    assert (result.status, result.eta, result.by_dist) == ("ok", S, False)


def test_a_flat_segment_does_not_divide_by_zero():
    p = profile(dists=[0, 1000, 1000, 3000, 4000])
    result = estimate(p, target(), vehicle(S - 600, 2, 1000), S - 600)
    assert result.status == "ok"


def test_a_distance_before_the_first_stop_is_clamped():
    p = profile(dists=[100, 1000, 2000, 3000, 4000])
    result = estimate(p, target(), vehicle(ORIGIN, 1, 50), ORIGIN)
    assert (result.status, result.eta) == ("ok", S)


def test_a_distance_just_past_the_profile_end_is_clamped():
    # היעד הוא העצירה האחרונה; 20 מ' מעבר לה עוד לא "עבר" (סף 50 מ').
    result = estimate(profile(), target(), vehicle(S, 5, 4020), S)
    assert (result.status, result.eta) == ("ok", S)


def test_a_missing_distance_in_the_middle_does_not_break_the_search():
    p = profile(dists=[0, 1000, -1, 3000, 4000])
    recorded = S - 750
    result = estimate(p, target(), vehicle(recorded, 2, 1500), recorded)
    assert result.status == "ok"
    assert p.vidx == (0, 1, 3, 4)


def test_one_known_distance_is_not_enough_to_interpolate():
    p = profile(dists=[0, -1, -1, -1, -1])
    assert not p.dists_valid
    result = estimate(p, target(), vehicle(S - 600, 3, 2000), S - 600)
    assert (result.status, result.by_dist) == ("ok", False)


def test_gaps_in_the_stop_sequence_are_counted_in_stops():
    p = profile(seqs=[1, 2, 10, 11, 12])
    result = estimate(p, target(seq=12), vehicle(S - 600, 10), S - 600)
    assert (result.status, result.eta) == ("ok", S)
    # Order שאינו בפרופיל (קפיצה): העצירה שלפניו.
    assert estimate(p, target(seq=12), vehicle(S - 300, 5), S - 300).status == "ok"


def test_order_on_the_last_profile_stop_does_not_index_past_the_end():
    result = estimate(profile(), target(seq=5), vehicle(S, 5), S)
    assert result.status == "unknown"


def test_a_layover_departs_later_than_it_arrives():
    """בעצירה 3 הרכב מחכה 3 דק': אחריה הזמן נמדד מהיציאה."""
    p = profile(arrs=[0, 300, 600, 1080, 1380], deps=[0, 300, 780, 1080, 1380])
    recorded = S - 1380 + 780
    result = estimate(p, target(scheduled=S), vehicle(recorded, 3), recorded)
    assert (result.status, result.eta) == ("ok", S)


@pytest.mark.parametrize("early", [5 * 60, 30 * 60])
def test_an_implausible_early_running_is_rejected(early):
    recorded = S - 750 - early
    result = estimate(profile(), target(), vehicle(recorded, 2, 1500), recorded)
    assert result.status == ("ok" if early <= 20 * 60 else "unknown")


def test_an_implausible_delay_is_rejected():
    recorded = S - 750 + 100 * 60
    result = estimate(profile(), target(), vehicle(recorded, 2, 1500), recorded)
    assert result.status == "unknown"


def test_a_slightly_stale_eta_is_held_at_now_and_an_old_one_dropped():
    # 100 מ' לפני התחנה, בזמן, כך שזמן ההגעה הוא S. דקה אחרי, הרכב "מגיע עכשיו".
    bus = vehicle(S - 30, 4, 3900)
    ok = estimate(profile(), target(), bus, S + 60)
    assert (ok.status, ok.eta) == ("ok", S + 60)
    # יותר מ-90 שנ' אחרי: הרכב כנראה כבר עבר, ולא נשאר "עכשיו".
    assert estimate(profile(), target(), bus, S + 120).status == "unknown"


def test_a_report_too_old_or_from_the_future_is_unknown():
    assert (
        estimate(profile(), target(), vehicle(S - 1000, 2, 1500), S).status == "unknown"
    )
    assert (
        estimate(profile(), target(), vehicle(S + 300, 2, 1500), S).status == "unknown"
    )


@pytest.mark.parametrize(
    "scheduled",
    [
        # 27.03.2026 02:00 (שעון קיץ נכנס) ו-25.10.2026 01:30 (חוזר).
        int(datetime(2026, 3, 27, 0, 10, tzinfo=UTC).timestamp()),
        int(datetime(2026, 10, 24, 22, 40, tzinfo=UTC).timestamp()),
        int(datetime(2026, 11, 27, 22, 10, tzinfo=UTC).timestamp()),  # אחרי חצות
    ],
)
def test_the_estimate_is_anchored_to_the_scheduled_time_not_the_date(
    scheduled, constant_delay
):
    recorded = scheduled - 750 + 60
    result = estimate(
        profile(),
        target(scheduled=scheduled, origin=scheduled - 1200),
        vehicle(recorded, 2, 1500, origin=scheduled - 1200),
        recorded,
    )
    assert (result.status, result.eta) == ("ok", scheduled + 60)


# --- שיבוץ רכבים ---------------------------------------------------------------


def _row(trip_idx=7, seq=5, scheduled=S, line="3266", journey=None, origin=None):
    when = datetime.fromtimestamp(scheduled, UTC)
    return api.Arrival(
        line_name="1",
        eta=when,
        is_realtime=False,
        line_ref=line,
        route_type="3",
        scheduled=when,
        origin=datetime.fromtimestamp(origin or scheduled - 1200, UTC),
        trip_idx=trip_idx,
        stop_seq=seq,
        journey_ref=journey,
    )


def test_the_board_gets_an_estimated_row_with_the_timetable_origin(constant_delay):
    row = _row()
    recorded = S - 750 + 120
    # המוצא ב-SIRI סוטה ב-40 שנ' מהלוח: עדיין אותה נסיעה.
    bus = vehicle(recorded, 2, 1500, origin=ORIGIN + 40)
    estimated, passed = estimate_mod.estimate_board(
        [row], {"3266": [bus]}, {7: profile()}, recorded
    )
    assert passed == set()
    [live] = estimated
    assert live.estimated and live.is_realtime
    assert live.departed == row.origin
    assert live.eta.timestamp() == S + 120
    assert live.vehicle_seen.timestamp() == recorded


def test_a_circular_trip_uses_one_vehicle_for_both_passes():
    first, second = _row(seq=1, scheduled=ORIGIN, origin=ORIGIN), _row(seq=5)
    recorded = S - 750
    estimated, passed = estimate_mod.estimate_board(
        [first, second],
        {"3266": [vehicle(recorded, 2, 1500)]},
        {7: profile()},
        recorded,
    )
    assert passed == {id(first)}
    assert [row.stop_seq for row in estimated] == [5]


def test_relief_buses_are_assigned_the_same_way_every_minute():
    """שני רכבים על אותו קו ואותה יציאה: השיבוץ לא תלוי בסדר בתמונה."""
    rows = [_row(trip_idx=7), _row(trip_idx=8, scheduled=S + 30)]
    profiles = {7: profile(), 8: profile()}
    recorded = S - 750
    a = vehicle(recorded, 2, 1500, ref="a")
    b = vehicle(recorded, 2, 1600, ref="b", origin=ORIGIN + 30)
    first, _ = estimate_mod.estimate_board(rows, {"3266": [a, b]}, profiles, recorded)
    again, _ = estimate_mod.estimate_board(rows, {"3266": [b, a]}, profiles, recorded)
    assert [(r.trip_idx, r.vehicle_ref) for r in first] == [
        (r.trip_idx, r.vehicle_ref) for r in again
    ]
    assert {r.vehicle_ref for r in first} == {"a", "b"}


def test_a_matching_journey_ref_wins_over_a_closer_origin():
    rows = [_row(journey=111)]
    recorded = S - 750
    near = vehicle(recorded, 2, 1500, ref="near")
    right = vehicle(recorded, 2, 1500, ref="right", origin=ORIGIN + 50, journey=111)
    estimated, _ = estimate_mod.estimate_board(
        rows, {"3266": [near, right]}, {7: profile()}, recorded
    )
    assert [r.vehicle_ref for r in estimated] == ["right"]


def test_rail_and_rows_without_a_trip_are_not_estimated():
    rail = _row()
    rail.route_type = "2"
    bare = _row()
    bare.trip_idx = None
    assert not estimate_mod.estimable(rail)
    assert not estimate_mod.estimable(bare)
