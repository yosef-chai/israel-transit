"""Tests for reading and indexing the Ministry of Transport GTFS feed.

The awkward parts are all here: the archive writes ZIP64 extra fields even
though it is well under 4 GB, the CSV files carry a BOM and CRLF endings, and
GTFS times run past midnight so a trip that leaves at 23:55 arrives at 24:10.
"""

from __future__ import annotations

import importlib
import sqlite3
import struct
import zlib
from datetime import date, datetime, timedelta, timezone

import pytest
from conftest import PACKAGE

gtfs = importlib.import_module(f"{PACKAGE}.gtfs")

IL = timezone(timedelta(hours=3))


# --- line decoding ----------------------------------------------------------


def test_iter_lines_strips_the_bom_and_crlf():
    chunks = [b"\xef\xbb\xbfroute_id,name\r\n1,Line one\r\n"]
    assert list(gtfs.iter_lines(chunks)) == ["route_id,name", "1,Line one"]


def test_iter_lines_joins_rows_split_across_chunks():
    chunks = [b"\xef\xbb\xbfa,b\r\n1,on", b"e\r\n2,tw", b"o\r\n"]
    assert list(gtfs.iter_lines(chunks)) == ["a,b", "1,one", "2,two"]


def test_iter_lines_yields_a_final_row_without_a_newline():
    assert list(gtfs.iter_lines([b"a,b\n1,2"])) == ["a,b", "1,2"]


def test_iter_lines_only_strips_a_leading_bom():
    # A BOM sequence in the middle of the data is real content, not a marker.
    assert list(gtfs.iter_lines([b"a\n", b"\xef\xbb\xbfb\n"]))[1].startswith("﻿")


def test_inflate_round_trips_a_raw_deflate_stream():
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    payload = ("x," * 5000).encode()
    raw = compressor.compress(payload) + compressor.flush()
    assert b"".join(gtfs.inflate([raw[:100], raw[100:]])) == payload


# --- GTFS field parsing -----------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("00:00:00", 0),
        ("08:30:00", 8 * 3600 + 1800),
        ("23:59:59", 86399),
        # GTFS keeps counting past midnight rather than wrapping.
        ("24:10:00", 24 * 3600 + 600),
        ("25:30:00", 25 * 3600 + 1800),
    ],
)
def test_seconds_handles_times_past_midnight(value, expected):
    assert gtfs._seconds(value) == expected


@pytest.mark.parametrize("junk", ["", "abc", "8:30", "a:b:c", "1:2"])
def test_seconds_rejects_junk(junk):
    assert gtfs._seconds(junk) is None


def test_day_mask_puts_sunday_in_bit_zero():
    weekdays = {
        "sunday": "1",
        "monday": "1",
        "tuesday": "1",
        "wednesday": "1",
        "thursday": "1",
        "friday": "0",
        "saturday": "0",
    }
    assert gtfs._day_mask(weekdays) == 0b0011111
    assert gtfs._day_mask({"saturday": "1"}) == 0b1000000
    assert gtfs._day_mask({}) == 0


def test_service_day_bit_matches_the_mask_layout():
    # 2026-08-30 is a Sunday, 2026-09-05 a Saturday.
    assert gtfs.service_day_bit(date(2026, 8, 30)) == 0b0000001
    assert gtfs.service_day_bit(date(2026, 9, 5)) == 0b1000000


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("רחוב: בן יהודה 74 עיר: כפר סבא רציף:  קומה: ", "כפר סבא"),
        ("עיר: תל אביב יפו רציף: 3 קומה: 1", "תל אביב יפו"),
        ("עיר: ירושלים", "ירושלים"),
        ("no city here", None),
    ],
)
def test_city_is_pulled_out_of_the_stop_description(description, expected):
    assert gtfs._described(description, gtfs._CITY_RE) == expected


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("רחוב: בן יהודה 74 עיר: כפר סבא רציף:  קומה: ", "בן יהודה 74"),
        ("רחוב: ז'בוטינסקי עיר: פתח תקווה", "ז'בוטינסקי"),
        # A stop on no named road at all, which the feed does publish.
        ("עיר: תל אביב יפו רציף: 3 קומה: 1", None),
        ("no street here", None),
    ],
)
def test_street_is_pulled_out_of_the_stop_description(description, expected):
    """The street is what makes a city+street search possible."""
    assert gtfs._described(description, gtfs._STREET_RE) == expected


# --- ZIP directory parsing --------------------------------------------------


def _central_directory_entry(
    name: bytes, compress: int, uncompressed: int, offset: int, zip64: bool
) -> bytes:
    """Build one central-directory record, optionally with a ZIP64 extra field."""
    extra = b""
    if zip64:
        values = struct.pack("<QQQ", uncompressed, compress, offset)
        extra = struct.pack("<HH", 0x0001, len(values)) + values
        compress = uncompressed = offset = 0xFFFFFFFF
    return (
        b"PK\x01\x02"
        + b"\x00" * 16
        + struct.pack("<II", compress, uncompressed)
        + struct.pack("<HHH", len(name), len(extra), 0)
        + b"\x00" * 8
        + struct.pack("<I", offset)
        + name
        + extra
    )


def test_central_directory_reads_zip64_sizes_from_the_extra_field():
    """The feed marks sizes 0xFFFFFFFF and puts the truth in the extra field."""
    directory = _central_directory_entry(
        b"stop_times.txt", 90_000_000, 773_000_000, 1234, zip64=True
    ) + _central_directory_entry(b"agency.txt", 500, 1400, 99, zip64=False)

    members = gtfs.parse_central_directory(b"", directory)

    assert set(members) == {"stop_times.txt", "agency.txt"}
    big = members["stop_times.txt"]
    assert (big.compress_size, big.file_size, big.header_offset) == (
        90_000_000,
        773_000_000,
        1234,
    )
    small = members["agency.txt"]
    assert (small.compress_size, small.file_size, small.header_offset) == (
        500,
        1400,
        99,
    )


def test_an_empty_directory_is_an_error():
    with pytest.raises(gtfs.GtfsError):
        gtfs.parse_central_directory(b"", b"")


def test_locate_directory_reads_a_plain_end_record():
    eocd = (
        b"PK\x05\x06" + b"\x00" * 8 + struct.pack("<II", 783, 161_503_514) + b"\x00\x00"
    )
    assert gtfs.locate_directory(b"padding" + eocd, 161_504_319) == (161_503_514, 783)


def test_locate_directory_falls_back_to_the_zip64_locator():
    locator = b"PK\x06\x07" + b"\x00" * 4 + struct.pack("<Q", 4242) + b"\x00" * 4
    eocd = (
        b"PK\x05\x06"
        + b"\x00" * 8
        + struct.pack("<II", 0xFFFFFFFF, 0xFFFFFFFF)
        + b"\x00\x00"
    )
    offset, value = gtfs.locate_directory(locator + eocd, 5000)
    assert offset == -1 and value == 4242


def test_a_missing_end_record_is_an_error():
    with pytest.raises(gtfs.GtfsError):
        gtfs.locate_directory(b"not a zip at all", 16)


# --- querying the index -----------------------------------------------------


@pytest.fixture
def index() -> sqlite3.Connection:
    """A tiny index: one stop, two routes, a weekday and a Saturday service."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(gtfs._SCHEMA)
    connection.execute(
        "INSERT INTO stops VALUES (35962,'הקוממיות','בת ים',32.01,34.75,'אנה פרנק')"
    )
    connection.executemany(
        "INSERT INTO routes VALUES (?,?,?,?,?,?)",
        [
            (34447, "1", "א<->ב-1#", "תבל", "0", "בת ים_הקוממיות"),
            (960, "36", "ג<->ד-1#", "מטרופולין", "3", ""),
        ],
    )
    connection.executemany(
        "INSERT INTO calendar VALUES (?,?,?,?)",
        [
            (1, 0b0011111, 20260101, 20261231),  # Sunday-Thursday
            (2, 0b1000000, 20260101, 20261231),  # Saturday only
        ],
    )
    connection.executemany(
        "INSERT INTO departures VALUES (?,?,?,?)",
        [
            (35962, 34447, 1, 12 * 3600),  # 12:00 on a weekday
            (35962, 34447, 1, 12 * 3600 + 600),  # 12:10
            (35962, 34447, 2, 12 * 3600 + 300),  # 12:05, Saturdays only
            (35962, 960, 1, 25 * 3600),  # 01:00 the following morning
        ],
    )
    return connection


def test_departures_are_limited_to_services_running_that_day(index):
    sunday_noon = datetime(2026, 8, 30, 11, 55, tzinfo=IL)
    rows = gtfs.departures_at(index, 35962, sunday_noon, hours=1)

    times = [when.strftime("%H:%M") for _, when in rows]
    assert times == ["12:00", "12:10"]  # the Saturday-only 12:05 is excluded
    assert all(row["agency"] == "תבל" for row, _ in rows)


def test_the_saturday_service_appears_on_a_saturday(index):
    saturday_noon = datetime(2026, 9, 5, 11, 55, tzinfo=IL)
    rows = gtfs.departures_at(index, 35962, saturday_noon, hours=1)
    assert [when.strftime("%H:%M") for _, when in rows] == ["12:05"]


def test_a_trip_running_past_midnight_is_found_after_midnight(index):
    """A 25:00:00 departure belongs to the previous service day."""
    after_midnight = datetime(2026, 8, 31, 0, 45, tzinfo=IL)
    rows = gtfs.departures_at(index, 35962, after_midnight, hours=1)

    assert len(rows) == 1
    row, when = rows[0]
    assert row["short_name"] == "36"
    assert when.strftime("%Y-%m-%d %H:%M") == "2026-08-31 01:00"


def test_departures_outside_the_window_are_not_returned(index):
    early = datetime(2026, 8, 30, 6, 0, tzinfo=IL)
    assert gtfs.departures_at(index, 35962, early, hours=1) == []


def test_an_unknown_stop_returns_nothing(index):
    noon = datetime(2026, 8, 30, 11, 55, tzinfo=IL)
    assert gtfs.departures_at(index, 999999, noon, hours=3) == []


def test_results_are_sorted_across_both_service_days(index):
    index.execute("INSERT INTO departures VALUES (35962,34447,1,?)", (26 * 3600,))
    after_midnight = datetime(2026, 8, 31, 0, 30, tzinfo=IL)
    rows = gtfs.departures_at(index, 35962, after_midnight, hours=3)
    assert [when for _, when in rows] == sorted(when for _, when in rows)
