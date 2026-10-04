"""Build a real index from a miniature GTFS feed, then query it.

``build_index`` is the most intricate code in the project: one streaming pass
over stop_times has to produce both the per-route stop patterns and the
timetables, while keeping only the modes that need them. These tests build a
tiny feed in the same on-disk shape the downloader produces -- raw deflate
streams of BOM-prefixed CRLF CSV -- and check what comes out the other end.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from conftest import PACKAGE
from gtfs_fixture import write_feed

gtfs = importlib.import_module(f"{PACKAGE}.gtfs")

IL = timezone(timedelta(hours=3))


@pytest.fixture
def built(tmp_path: Path):
    """An index built with no configured stops."""
    files = write_feed(tmp_path)
    db = tmp_path / "gtfs.sqlite"
    stats = gtfs.build_index(files, db, frozenset(), "v1")
    return db, stats


@pytest.fixture
def built_with_bus_stop(tmp_path: Path):
    """An index where stop 21023 was configured, so its buses are timetabled."""
    files = write_feed(tmp_path)
    db = tmp_path / "gtfs.sqlite"
    stats = gtfs.build_index(files, db, frozenset({21023}), "v1")
    return db, stats


# --- what the build produces ------------------------------------------------


def test_the_build_reports_what_it_indexed(built):
    _, stats = built
    assert stats["routes"] == 3
    assert stats["stops"] == 4
    assert stats["stop_times_scanned"] == 10
    # One representative trip per route.
    assert stats["pattern_trips"] == 3
    # Every trip of the two light rail routes, and none of the bus trips.
    assert stats["timetable_trips"] == 3
    assert stats["calendar"] == 2
    assert stats["db_bytes"] > 0


def test_stops_keep_their_name_and_city(built):
    db, _ = built
    connection = gtfs.connect(db)
    stop = gtfs.get_stop(connection, 35962)
    assert stop is not None
    assert stop.name == "הקוממיות"
    assert stop.city == "בת ים"
    assert stop.lat == pytest.approx(32.01)


def test_a_stop_without_a_city_still_indexes(built):
    db, _ = built
    stop = gtfs.get_stop(gtfs.connect(db), 99999)
    assert stop is not None and stop.city is None


def test_an_unknown_stop_code_is_none(built):
    assert gtfs.get_stop(gtfs.connect(built[0]), 12345) is None


def test_the_feed_version_is_recorded_so_it_is_not_rebuilt(built):
    assert gtfs.stored_version(gtfs.connect(built[0])) == "v1"


def test_the_stops_that_got_a_timetable_are_recorded(built_with_bus_stop):
    """Adding a stop has to force a rebuild, and this is what tells us it did."""
    db, _ = built_with_bus_stop
    assert gtfs.stored_stop_codes(gtfs.connect(db)) == frozenset({21023})


def test_an_index_built_for_no_stops_records_an_empty_set(built):
    assert gtfs.stored_stop_codes(gtfs.connect(built[0])) == frozenset()


# --- patterns ---------------------------------------------------------------


def test_a_route_pattern_is_the_ordered_stop_list(built):
    db, _ = built
    stops = gtfs.route_stops(gtfs.connect(db), 34447)

    assert [s.stop.code for s in stops] == [35962, 36307, 21023]
    assert [s.sequence for s in stops] == [1, 2, 3]


def test_pattern_offsets_are_measured_from_the_start_of_the_run(built):
    """This is what lets the card show times for the vehicle being tracked."""
    stops = gtfs.route_stops(gtfs.connect(built[0]), 34447)
    assert [s.offset_seconds for s in stops] == [0, 8 * 60, 22 * 60]


def test_every_route_gets_a_pattern_including_the_realtime_ones(built):
    db, _ = built
    connection = gtfs.connect(db)
    assert len(gtfs.route_stops(connection, 960)) == 2
    assert len(gtfs.route_stops(connection, 34448)) == 2


def test_the_lines_at_a_stop_come_from_the_patterns(built):
    db, _ = built
    routes = gtfs.routes_at_stop(gtfs.connect(db), 35962)

    assert {r.route_id for r in routes} == {34447, 34448, 960}
    tram = next(r for r in routes if r.route_id == 34447)
    assert tram.agency == "תבל"
    assert tram.route_type == "0"
    assert tram.destination == "בת ים הקוממיות"  # from trip_headsign
    assert tram.as_dict()["has_realtime"] is False


# --- timetables -------------------------------------------------------------


def test_only_the_modes_without_realtime_are_timetabled(built):
    """Indexing 14.5M bus rows would cost ~500 MB for data SIRI already gives."""
    db, _ = built
    connection = gtfs.connect(db)
    rows = connection.execute(
        "SELECT DISTINCT route_id FROM departures ORDER BY route_id"
    ).fetchall()
    assert [r["route_id"] for r in rows] == [34447, 34448]


def test_a_configured_stop_also_gets_its_buses_timetabled(built_with_bus_stop):
    """So the card degrades to a timetable when curlbus is unreachable."""
    db, _ = built_with_bus_stop
    connection = gtfs.connect(db)
    rows = connection.execute(
        "SELECT DISTINCT route_id FROM departures WHERE stop_code = 21023"
    ).fetchall()
    assert 960 in {r["route_id"] for r in rows}


def test_departures_are_returned_as_arrivals_the_card_understands(built):
    db, _ = built
    noon = datetime(2026, 8, 30, 11, 30, tzinfo=IL)  # a Sunday
    arrivals = gtfs.scheduled_arrivals(gtfs.connect(db), 35962, noon, hours=2)

    assert [a.eta.strftime("%H:%M") for a in arrivals] == ["12:00", "12:30"]
    first = arrivals[0]
    assert first.is_realtime is False
    assert first.line_name == "1"
    assert first.route_type == "0"
    assert first.operator == "תבל"
    assert first.destination == "בת ים הקוממיות"


def test_a_trip_past_midnight_belongs_to_the_previous_service_day(built):
    """tram-c leaves at 25:10, which is 01:10 the next morning."""
    db, _ = built
    after_midnight = datetime(2026, 8, 31, 1, 0, tzinfo=IL)
    arrivals = gtfs.scheduled_arrivals(gtfs.connect(db), 36307, after_midnight, hours=1)

    assert len(arrivals) == 1
    assert arrivals[0].eta.strftime("%Y-%m-%d %H:%M") == "2026-08-31 01:10"


def test_nothing_runs_on_a_day_the_calendar_excludes(built):
    """Service 1 is Sunday to Thursday, so Saturday is empty."""
    db, _ = built
    saturday = datetime(2026, 9, 5, 11, 30, tzinfo=IL)
    assert gtfs.scheduled_arrivals(gtfs.connect(db), 35962, saturday, hours=3) == []


# --- search -----------------------------------------------------------------


def test_search_matches_a_stop_code_exactly(built):
    results = gtfs.search_stops(gtfs.connect(built[0]), "35962")
    assert [s.code for s in results] == [35962]


def test_search_matches_a_name_substring(built):
    results = gtfs.search_stops(gtfs.connect(built[0]), "קוממיות")
    assert [s.code for s in results] == [35962]


def test_search_matches_a_city(built):
    results = gtfs.search_stops(gtfs.connect(built[0]), "פתח תקווה")
    assert [s.code for s in results] == [36307]


def test_search_prefers_stops_whose_name_starts_with_the_query(built):
    db, _ = built
    connection = gtfs.connect(db)
    connection.close()
    writable = gtfs.sqlite3.connect(db)
    writable.execute(
        "INSERT INTO stops VALUES (5,'משהו קרית אריה','חיפה',32.8,35.0,'הרצל')"
    )
    writable.commit()
    writable.close()

    results = gtfs.search_stops(gtfs.connect(db), "קרית אריה")
    assert results[0].code == 36307  # the one that starts with it


def test_search_matches_a_street(built):
    """Stops are named for landmarks, so the road is its own way in."""
    results = gtfs.search_stops(gtfs.connect(built[0]), "אנה פרנק")
    assert [s.code for s in results] == [35962]
    assert results[0].street == "אנה פרנק"


def test_a_city_and_a_street_together_narrow_the_search(built):
    """Each word has to match something, so the pair is an AND."""
    connection = gtfs.connect(built[0])
    assert [s.code for s in gtfs.search_stops(connection, "בת ים אנה פרנק")] == [35962]
    # The same street name in the wrong city matches nothing.
    assert gtfs.search_stops(connection, "פתח תקווה אנה פרנק") == []


def test_words_match_in_any_order(built):
    connection = gtfs.connect(built[0])
    assert gtfs.search_stops(connection, "אנה פרנק בת ים") == gtfs.search_stops(
        connection, "בת ים אנה פרנק"
    )


def test_an_empty_search_returns_nothing(built):
    assert gtfs.search_stops(gtfs.connect(built[0]), "   ") == []


def test_search_respects_the_limit(built):
    results = gtfs.search_stops(gtfs.connect(built[0]), "ת", limit=1)
    assert len(results) <= 1


# --- rebuilding -------------------------------------------------------------


def test_rebuilding_replaces_the_previous_index(tmp_path: Path):
    files = write_feed(tmp_path)
    db = tmp_path / "gtfs.sqlite"

    gtfs.build_index(files, db, frozenset(), "v1")
    first = db.stat().st_ino
    gtfs.build_index(files, db, frozenset(), "v2")

    assert gtfs.stored_version(gtfs.connect(db)) == "v2"
    # A different file, not the old one rewritten: the build goes to a temp
    # path and is moved into place, so a reader never sees a half-built index.
    # (Identity rather than mtime -- this feed builds inside one clock tick.)
    assert db.stat().st_ino != first
    assert not (tmp_path / "gtfs.building").exists()
