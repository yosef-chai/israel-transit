"""The board policy: live rows matched to their timetabled trips.

Each test builds the inputs by hand -- what curlbus, the index and rail.co.il
would hand over -- and checks the board that comes out.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta

from conftest import PACKAGE

api = importlib.import_module(f"{PACKAGE}.api")
merge = importlib.import_module(f"{PACKAGE}.merge")

TZ = api.ISRAEL_TZ
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=TZ)


def at(hour: int, minute: int) -> datetime:
    return NOW.replace(hour=hour, minute=minute)


DUE = at(12, 5)
SET_OUT = at(11, 40)


def live(line_ref="960", eta=DUE, departed=SET_OUT, **extra):
    return api.Arrival(
        line_name=extra.pop("line_name", "36"),
        eta=eta,
        is_realtime=extra.pop("is_realtime", True),
        line_ref=line_ref,
        departed=departed,
        **extra,
    )


def planned(line_ref="960", when=DUE, origin=SET_OUT, **extra):
    return api.Arrival(
        line_name=extra.pop("line_name", "36"),
        eta=when,
        is_realtime=False,
        line_ref=line_ref,
        route_type=extra.pop("route_type", "3"),
        scheduled=when,
        origin=origin,
        **extra,
    )


def board(live_rows, scheduled, rail=(), routes=(), now=NOW):
    return merge.merge_board(
        list(live_rows), list(scheduled), list(rail), list(routes), now
    )


# --- matching by trip -------------------------------------------------------


def test_a_late_bus_gets_its_real_delay():
    """The 12:00 that is due at 12:20: matched by its 11:40 departure."""
    rows = board(
        [live(eta=at(12, 20), departed=at(11, 40))],
        [planned(when=at(12, 0), origin=at(11, 40))],
        now=at(12, 15),
    )
    assert len(rows) == 1
    assert rows[0].is_realtime is True
    assert rows[0].scheduled == at(12, 0)
    assert rows[0].delay_minutes == 20


def test_an_early_bus_has_a_negative_delay():
    rows = board([live(eta=at(11, 58))], [planned(when=at(12, 0))])
    assert rows[0].delay_minutes == -2


def test_an_on_time_bus_has_zero_delay_not_none():
    rows = board([live(eta=at(12, 0))], [planned(when=at(12, 0))])
    assert rows[0].delay_minutes == 0


def test_a_live_row_without_a_departure_matches_without_a_delay():
    rows = board([live(eta=at(12, 7), departed=None)], [planned(when=at(12, 5))])
    assert len(rows) == 1
    assert rows[0].scheduled == at(12, 5)
    assert rows[0].delay_minutes is None


def test_a_trip_siri_does_not_list_stays_on_the_board_as_timetable():
    rows = board(
        [live(eta=at(12, 5))],
        [planned(when=at(12, 5)), planned(when=at(12, 35), origin=at(12, 10))],
    )
    assert [(r.eta, r.is_realtime) for r in rows] == [
        (at(12, 5), True),
        (at(12, 35), False),
    ]


def test_an_imprecise_row_does_not_take_the_slot_of_a_precise_one():
    """B (no departure) is nearer to the 12:00 run, but A is that run for sure."""
    a = live(eta=at(12, 3), departed=at(11, 40))
    b = live(eta=at(12, 1), departed=None, vehicle_ref="b")
    rows = board(
        [a, b],
        [
            planned(when=at(12, 0), origin=at(11, 40)),
            planned(when=at(12, 10), origin=at(11, 50)),
        ],
    )
    assert a.scheduled == at(12, 0) and a.delay_minutes == 3
    assert b.scheduled == at(12, 10) and b.delay_minutes is None
    assert len(rows) == 2


def test_two_extra_buses_a_minute_apart_each_find_their_own_trip():
    first = live(eta=at(12, 6), departed=at(11, 40))
    second = live(eta=at(12, 6), departed=at(11, 41), vehicle_ref="2")
    board(
        [first, second],
        [
            planned(when=at(12, 5), origin=at(11, 40)),
            planned(when=at(12, 6), origin=at(11, 41)),
        ],
    )
    assert (first.delay_minutes, second.delay_minutes) == (1, 0)


def test_a_loop_line_passing_twice_matches_each_visit():
    """Same trip, same departure, two visits: each takes the nearer one."""
    out = live(eta=at(12, 1))
    back = live(eta=at(12, 52))
    rows = board(
        [out, back],
        [planned(when=at(12, 0)), planned(when=at(12, 50))],
    )
    assert (out.scheduled, back.scheduled) == (at(12, 0), at(12, 50))
    assert len(rows) == 2


def test_a_timetabled_row_already_gone_is_not_shown():
    rows = board([], [planned(when=at(11, 50))])
    assert rows == []


def test_without_real_time_the_board_is_the_future_timetable():
    rows = board([], [planned(when=at(11, 50)), planned(when=at(12, 10))])
    assert [r.eta for r in rows] == [at(12, 10)]


# --- route_id that changed (the v4 switch) ----------------------------------


def _rail(line_ref, dest, **extra):
    return planned(
        line_ref=line_ref,
        when=extra.pop("when", at(12, 24)),
        origin=at(11, 31),
        route_type="2",
        line_name=line_ref,
        operator_id="2",
        dest_code=dest,
        **extra,
    )


def test_a_train_with_an_unknown_line_matches_by_operator_and_destination():
    train = live(
        line_ref="38505",
        line_name="6702",
        eta=at(12, 30),
        departed=at(11, 31),
        operator_id="2",
        dest_code=17034,
    )
    rows = board([train], [_rail("59424", 17034)])
    assert len(rows) == 1
    assert train.line_ref == "59424"
    assert train.line_name == "59424"
    assert train.train_number == "6702"
    assert train.delay_minutes == 6


def test_a_train_the_other_way_in_the_same_minute_is_not_its_match():
    train = live(
        line_ref="38505",
        line_name="6702",
        eta=at(12, 30),
        departed=at(11, 31),
        operator_id="2",
        dest_code=17034,
    )
    rows = board([train], [_rail("59425", 17118, when=at(12, 29))])
    assert train.scheduled is None
    assert len(rows) == 2


def test_a_train_of_a_known_line_is_named_like_the_timetable():
    route = api.RouteInfo(38505, "38505", "", 'ירושלים - נתב"ג', "רכבת ישראל", "2")
    train = live(line_ref="38505", line_name="06702", departed=None, eta=at(13, 0))
    board([train], [], routes=[route])
    assert (train.line_name, train.train_number, train.route_type) == (
        "38505",
        "6702",
        "2",
    )


# --- cancellations ----------------------------------------------------------


def test_a_cancellation_without_an_eta_takes_its_timetabled_time():
    marker = live(eta=at(11, 40), is_realtime=False, cancelled=True)
    rows = board([marker], [planned(when=at(12, 5))])
    assert len(rows) == 1
    assert rows[0].cancelled is True
    assert rows[0].eta == at(12, 5)
    assert rows[0].delay_minutes is None


def test_a_cancellation_with_nothing_to_match_is_dropped():
    marker = live(eta=at(11, 40), is_realtime=False, cancelled=True)
    assert board([marker], []) == []


def test_a_cancelled_live_row_with_an_eta_is_kept():
    rows = board([live(cancelled=True)], [])
    assert rows[0].cancelled is True


# --- rail.co.il -------------------------------------------------------------


def test_rail_co_il_adds_the_platform_to_the_same_train():
    route = api.RouteInfo(38505, "38505", "", "", "רכבת ישראל", "2")
    train = live(line_ref="38505", line_name="6702", departed=None, eta=at(12, 30))
    extra = api.Arrival(
        line_name="6702",
        eta=at(12, 30),
        is_realtime=True,
        route_type="2",
        platform="3",
        delay_minutes=2,
        scheduled=at(12, 28),
        train_number="6702",
    )
    rows = board([train], [], rail=[extra], routes=[route])
    assert len(rows) == 1
    assert rows[0].platform == "3"


def test_rail_co_il_makes_a_timetabled_train_live():
    timetable = _rail("38505", 17034, when=at(12, 28))
    extra = api.Arrival(
        line_name="6702",
        eta=at(12, 31),
        is_realtime=True,
        route_type="2",
        delay_minutes=3,
        scheduled=at(12, 28),
        train_number="6702",
    )
    rows = board([], [timetable], rail=[extra])
    assert len(rows) == 1
    assert (rows[0].eta, rows[0].is_realtime, rows[0].delay_minutes) == (
        at(12, 31),
        True,
        3,
    )


# --- the cap ----------------------------------------------------------------


def test_a_rare_line_keeps_its_place_on_a_crowded_board():
    busy = [
        planned(line_ref="1", line_name="1", when=NOW + timedelta(minutes=i))
        for i in range(50)
    ]
    rare = planned(line_ref="999", line_name="999", when=NOW + timedelta(hours=2))
    rows = board([], [*busy, rare])
    assert len(rows) == merge.MAX_ARRIVALS
    assert rows[-1] is rare


def test_the_reserved_place_goes_to_a_trip_that_is_running():
    busy = [
        planned(line_ref="1", line_name="1", when=NOW + timedelta(minutes=i))
        for i in range(50)
    ]
    cancelled = planned(
        line_ref="999", line_name="999", when=NOW + timedelta(hours=1), cancelled=True
    )
    running = planned(line_ref="999", line_name="999", when=NOW + timedelta(hours=2))
    rows = board([], [*busy, cancelled, running])
    assert running in rows
    assert cancelled not in rows
