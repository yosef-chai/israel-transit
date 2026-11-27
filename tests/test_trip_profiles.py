"""פרופיל הזמנים לכל נסיעה שעוברת בתחנה מבוקשת, כפי שנבנה מ-stop_times."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import gtfs_fixture
from conftest import PACKAGE
from gtfs_fixture import write_feed

gtfs = importlib.import_module(f"{PACKAGE}.gtfs")

IL = timezone(timedelta(hours=3))

# נסיעת אוטובוס עם trip_id בפורמט הישן, דרך שלוש תחנות, עם מרחקים.
JOURNEY = "25317845_041226"
TRIPS = gtfs_fixture.TRIPS + f"960,1,{JOURNEY},אור יהודה_מסוף,0,2,1\n"
HEADER = (
    "trip_id,arrival_time,departure_time,stop_id,stop_sequence,"
    "pickup_type,drop_off_type,shape_dist_traveled\n"
)


def _stop_times(rows: str, with_dist: bool = True) -> str:
    """ה-stop_times של ה-fixture, ועוד הנסיעה; עמודת המרחק ריקה בשורות הישנות."""
    base = gtfs_fixture.STOP_TIMES.split("\n", 1)[1]
    if not with_dist:
        return gtfs_fixture.STOP_TIMES + "".join(
            line.rsplit(",", 1)[0] + "\n" for line in rows.strip().split("\n")
        )
    old = "".join(f"{line},\n" for line in base.strip().split("\n"))
    return HEADER + old + rows


TRIP_ROWS = (
    f"{JOURNEY},12:00:00,12:00:00,3,1,0,1,0\n"
    f"{JOURNEY},12:06:00,12:08:00,2,2,0,0,1500.4\n"
    f"{JOURNEY},12:15:00,12:15:00,1,3,0,0,3000\n"
)


def _build(tmp_path: Path, stop_times: str, codes=frozenset({35962})):
    files = write_feed(tmp_path, {"trips.txt": TRIPS, "stop_times.txt": stop_times})
    db = tmp_path / "gtfs.sqlite"
    stats = gtfs.build_index(files, db, codes, "v1")
    return gtfs.connect(db), stats


def _journey_idx(connection) -> int:
    return connection.execute(
        "SELECT trip_idx FROM trips WHERE journey_ref = 25317845"
    ).fetchone()["trip_idx"]


def test_a_trip_through_a_wanted_stop_gets_its_profile(tmp_path: Path):
    connection, stats = _build(tmp_path, _stop_times(TRIP_ROWS))
    idx = _journey_idx(connection)
    profile = gtfs.trip_profiles(connection, [idx])[idx]

    assert list(profile.seqs) == [1, 2, 3]
    assert list(profile.dists) == [0, 1500, 3000]
    assert list(profile.arrs) == [12 * 3600, 12 * 3600 + 360, 12 * 3600 + 900]
    # עצירה 2 יוצאת שתי דקות אחרי שהגיעה.
    assert list(profile.deps) == [12 * 3600, 12 * 3600 + 480, 12 * 3600 + 900]
    assert profile.dists_valid
    assert stats["profiles"] >= 1


def test_the_profile_ends_at_the_last_wanted_stop(tmp_path: Path):
    # 21023 היא העצירה הראשונה בנסיעה: הפרופיל נגמר בה.
    connection, _ = _build(tmp_path, _stop_times(TRIP_ROWS), frozenset({21023}))
    idx = _journey_idx(connection)
    assert list(gtfs.trip_profiles(connection, [idx])[idx].seqs) == [1]


def test_without_shape_distances_the_profile_has_none(tmp_path: Path):
    connection, _ = _build(tmp_path, _stop_times(TRIP_ROWS, with_dist=False))
    idx = _journey_idx(connection)
    profile = gtfs.trip_profiles(connection, [idx])[idx]
    assert list(profile.dists) == [-1, -1, -1]
    assert not profile.dists_valid


def test_a_trip_out_of_order_gets_no_profile(tmp_path: Path):
    shuffled = TRIP_ROWS.replace(",2,0,0,1500.4", ",9,0,0,1500.4")
    connection, stats = _build(tmp_path, _stop_times(shuffled))
    idx = _journey_idx(connection)
    assert gtfs.trip_profiles(connection, [idx]) == {}
    assert stats["origin_violations"] >= 1


def test_the_timetable_row_carries_its_trip_and_place_in_it(tmp_path: Path):
    connection, _ = _build(tmp_path, _stop_times(TRIP_ROWS))
    start = datetime(2026, 9, 1, 12, 10, tzinfo=IL)  # יום שלישי
    rows = gtfs.departures_at(connection, 35962, start, start + timedelta(minutes=10))
    [row] = [r for r in rows if r.journey_ref == 25317845]
    assert (row.seq, row.trip_idx) == (3, _journey_idx(connection))
    arrival = gtfs.scheduled_arrivals(
        connection, 35962, start, start + timedelta(minutes=10)
    )
    [bus] = [a for a in arrival if a.journey_ref == 25317845]
    assert (bus.stop_seq, bus.trip_idx) == (3, row.trip_idx)


def test_an_index_without_the_table_has_no_profiles(tmp_path: Path):
    connection, _ = _build(tmp_path, _stop_times(TRIP_ROWS))
    raw = gtfs.sqlite3.connect(tmp_path / "gtfs.sqlite")
    raw.execute("DROP TABLE trip_profiles")
    raw.commit()
    raw.close()
    assert gtfs.trip_profiles(gtfs.connect(tmp_path / "gtfs.sqlite"), [1, 2]) == {}
    assert gtfs.trip_profiles(connection, []) == {}
