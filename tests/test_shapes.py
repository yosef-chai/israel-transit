"""The street path of a route: read from shapes.txt, cleaned, simplified, stored.

Built from the miniature feed, so the trips pass, the shapes pass and the
SQLite round trip are exercised together.
"""

from __future__ import annotations

import importlib
import math
import sqlite3
import struct
from array import array
from pathlib import Path
from unittest.mock import patch

import pytest
from conftest import PACKAGE
from gtfs_fixture import TRIPS, write_feed

gtfs = importlib.import_module(f"{PACKAGE}.gtfs")

# 21023 is on the first tram route and on the bus; 36307 is on both tram routes.
BUS_STOP = 21023
TRAM_STOP = 36307


def _build(tmp_path: Path, stops: set[int], **members: str | None):
    files = write_feed(
        tmp_path, {f"{name}.txt": text for name, text in members.items()}
    )
    db = tmp_path / "gtfs.sqlite"
    stats = gtfs.build_index(files, db, frozenset(stops), "v1")
    return gtfs.connect(db), stats


def test_a_route_through_an_indexed_stop_gets_its_shape(tmp_path: Path) -> None:
    connection, stats = _build(tmp_path, {BUS_STOP})
    try:
        assert gtfs.route_shape(connection, 34447) == [
            [32.01, 34.75],
            [32.1, 34.87],
            [32.072666, 34.79339],
        ]
        # The other tram direction does not pass this stop, so it is not kept.
        assert gtfs.route_shape(connection, 34448) is None
        assert stats["shapes"] == 2
    finally:
        connection.close()


def test_the_opposite_direction_has_its_own_shape(tmp_path: Path) -> None:
    connection, _ = _build(tmp_path, {TRAM_STOP})
    try:
        forward = gtfs.route_shape(connection, 34447)
        backward = gtfs.route_shape(connection, 34448)
        assert forward is not None and backward == forward[::-1]
    finally:
        connection.close()


def test_points_are_sorted_and_zero_points_dropped(tmp_path: Path) -> None:
    """Shape 2 is listed out of order and carries a (0, 0) point."""
    connection, _ = _build(tmp_path, {BUS_STOP})
    try:
        assert gtfs.route_shape(connection, 960) == [
            [32.072666, 34.79339],
            [32.01, 34.75],
        ]
    finally:
        connection.close()


def test_no_indexed_stop_means_no_shapes(tmp_path: Path) -> None:
    connection, stats = _build(tmp_path, set())
    try:
        assert stats["shapes"] == 0
        assert gtfs.route_shape(connection, 34447) is None
    finally:
        connection.close()


def test_a_feed_without_shapes_still_builds(tmp_path: Path) -> None:
    connection, stats = _build(tmp_path, {BUS_STOP}, shapes=None)
    try:
        assert stats["shapes"] == 0
        assert gtfs.route_shape(connection, 34447) is None
        assert gtfs.get_stop(connection, BUS_STOP) is not None
    finally:
        connection.close()


def test_a_pattern_trip_without_a_shape_takes_the_common_one(tmp_path: Path) -> None:
    trips = TRIPS.replace(
        "960,1,bus-a,אור יהודה_מסוף,0,2,1", "960,1,bus-a,אור יהודה_מסוף,0,,1"
    )
    trips += "960,1,bus-c,אור יהודה_מסוף,0,2,1\n960,1,bus-d,אור יהודה_מסוף,0,1,1\n"
    assert trips != TRIPS
    connection, _ = _build(tmp_path, {BUS_STOP}, trips=trips)
    try:
        assert gtfs.route_shape(connection, 960) == [
            [32.072666, 34.79339],
            [32.01, 34.75],
        ]
    finally:
        connection.close()


def test_a_shared_shape_is_stored_and_simplified_once(tmp_path: Path) -> None:
    trips = TRIPS.replace("פתח תקווה_קרית אריה,1,3,1", "פתח תקווה_קרית אריה,1,1,1")
    assert trips != TRIPS
    real = gtfs.encode_shape
    with patch.object(gtfs, "encode_shape", side_effect=real) as encode:
        connection, stats = _build(tmp_path, {TRAM_STOP}, trips=trips)
    try:
        assert encode.call_count == 1
        assert stats["shapes"] == 1
        assert gtfs.route_shape(connection, 34447) == gtfs.route_shape(
            connection, 34448
        )
    finally:
        connection.close()


def test_the_blob_is_little_endian_microdegrees(tmp_path: Path) -> None:
    connection, _ = _build(tmp_path, {BUS_STOP})
    try:
        blob = connection.execute(
            "SELECT points FROM shapes WHERE shape_id = '2'"
        ).fetchone()["points"]
    finally:
        connection.close()
    assert struct.unpack("<4i", blob) == (
        32_072_666,
        34_793_390,
        32_010_000,
        34_750_000,
    )
    assert gtfs.decode_shape(blob) == [[32.072666, 34.79339], [32.01, 34.75]]


def test_a_schema_2_index_answers_without_a_shape(tmp_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE routes (route_id INTEGER PRIMARY KEY)")
    assert gtfs.route_shape(connection, 34447) is None


def test_shapes_read_past_a_bom() -> None:
    raw = b"\xef\xbb\xbfshape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\r\n"
    raw += b"7,32.0,34.8,1\r\n8,31.0,35.0,1\r\n"
    shapes = gtfs.read_shapes(gtfs.iter_lines([raw]), {"7"})
    assert list(shapes) == ["7"]
    seqs, lats, lons = shapes["7"]
    assert (list(seqs), list(lats), list(lons)) == ([1], [32_000_000], [34_800_000])


# --- simplification ---------------------------------------------------------


def test_a_straight_line_collapses_to_its_ends() -> None:
    lats = [32_000_000 + i * 100 for i in range(50)]
    lons = [34_800_000 + i * 100 for i in range(50)]
    assert gtfs.simplify(lats, lons, 3.0) == [0, 49]


def test_a_long_shape_does_not_recurse() -> None:
    """A spiral splits one point at a time: deep enough to break recursion."""
    count = 5000
    lats = [round(32e6 + i * 20 * math.sin(i / 50)) for i in range(count)]
    lons = [round(34.8e6 + i * 20 * math.cos(i / 50)) for i in range(count)]
    kept = gtfs.simplify(lats, lons, 3.0)
    assert kept[0] == 0 and kept[-1] == count - 1
    assert 2 < len(kept) < count


def test_a_closed_loop_keeps_its_corners() -> None:
    """Start and end coincide, so the chord has no length to divide by."""
    lats = [32_000_000, 32_000_000, 32_010_000, 32_010_000, 32_000_000]
    lons = [34_800_000, 34_810_000, 34_810_000, 34_800_000, 34_800_000]
    assert gtfs.simplify(lats, lons, 3.0) == [0, 1, 2, 3, 4]


@pytest.mark.parametrize(
    ("lat", "lon"), [(0, 0), (40_000_000, 34_800_000), (32_000_000, 20_000_000)]
)
def test_points_outside_israel_are_dropped(lat: int, lon: int) -> None:
    seqs = array("i", [1, 2])
    lats = array("i", [32_000_000, lat])
    lons = array("i", [34_800_000, lon])
    assert gtfs.encode_shape(seqs, lats, lons) is None
