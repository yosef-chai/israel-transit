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
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from conftest import PACKAGE

gtfs = importlib.import_module(f"{PACKAGE}.gtfs")

IL = timezone(timedelta(hours=3))
# שמות העמודות במפורש, כך ש-seq החדשה נשארת NULL בשורות הבדיקה.
_DEP_COLS = "(stop_code, route_id, service_id, arrival_sec, trip_idx)"


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
        "INSERT INTO routes (route_id, short_name, long_name, agency, route_type,"
        " headsign) VALUES (?,?,?,?,?,?)",
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
        f"INSERT INTO departures {_DEP_COLS} VALUES (?,?,?,?,?)",
        [
            (35962, 34447, 1, 12 * 3600, 1),  # 12:00 on a weekday
            (35962, 34447, 1, 12 * 3600 + 600, 2),  # 12:10
            (35962, 34447, 2, 12 * 3600 + 300, 3),  # 12:05, Saturdays only
            (35962, 960, 1, 25 * 3600, 4),  # 01:00 the following morning
        ],
    )
    connection.executemany(
        "INSERT INTO trips (trip_idx, origin_sec, dest_code) VALUES (?,?,?)",
        [(1, 11 * 3600 + 40 * 60, 36307), (4, 24 * 3600 + 30 * 60, 21023)],
    )
    return connection


def _window(index, start, hours=1, code=35962):
    return gtfs.departures_at(index, code, start, start + timedelta(hours=hours))


def _clock(rows):
    return [row.when.strftime("%H:%M") for row in rows]


def test_departures_are_limited_to_services_running_that_day(index):
    rows = _window(index, datetime(2026, 8, 30, 11, 55, tzinfo=IL))

    assert _clock(rows) == ["12:00", "12:10"]  # the Saturday-only 12:05 is excluded
    assert all(row.row["agency"] == "תבל" for row in rows)


def test_the_saturday_service_appears_on_a_saturday(index):
    assert _clock(_window(index, datetime(2026, 9, 5, 11, 55, tzinfo=IL))) == ["12:05"]


def test_the_next_service_after_friday_afternoon_is_on_saturday(index):
    """מחפשים קדימה גם מעבר לחלון של הלוח: שישי אחר הצהריים -> שבת."""
    friday = datetime(2026, 9, 4, 13, 0, tzinfo=IL)

    arrival = gtfs.next_scheduled(index, 35962, friday, friday + timedelta(days=4))

    assert arrival is not None
    assert arrival.eta.strftime("%a %H:%M") == "Sat 12:05"
    assert arrival.line_name == "1"
    assert arrival.is_realtime is False


def test_the_next_service_after_saturday_is_on_sunday(index):
    saturday = datetime(2026, 9, 5, 13, 0, tzinfo=IL)

    arrival = gtfs.next_scheduled(index, 35962, saturday, saturday + timedelta(days=4))

    assert arrival is not None
    assert arrival.eta.strftime("%Y-%m-%d %H:%M") == "2026-09-06 12:00"


def test_no_next_service_for_a_stop_without_a_timetable(index):
    now = datetime(2026, 9, 4, 13, 0, tzinfo=IL)

    assert gtfs.next_scheduled(index, 1, now, now + timedelta(days=4)) is None


def test_stops_in_box_keeps_to_the_box(index):
    assert [s.code for s in gtfs.stops_in_box(index, 32.0105, 34.7495, 0.01)] == [35962]
    assert gtfs.stops_in_box(index, 32.2, 34.9, 0.01) == []


def test_a_trip_running_past_midnight_is_found_after_midnight(index):
    """A 25:00:00 departure belongs to the previous service day."""
    rows = _window(index, datetime(2026, 8, 31, 0, 45, tzinfo=IL))

    assert len(rows) == 1
    assert rows[0].row["short_name"] == "36"
    assert rows[0].when.strftime("%Y-%m-%d %H:%M") == "2026-08-31 01:00"


def test_a_trip_carries_its_origin_and_destination(index):
    rows = _window(index, datetime(2026, 8, 31, 0, 45, tzinfo=IL))

    # יצאה ב-24:30 של יום השירות הקודם, כלומר 00:30 בבוקר.
    assert rows[0].origin.strftime("%Y-%m-%d %H:%M") == "2026-08-31 00:30"
    assert rows[0].row["dest_code"] == 21023


def test_a_trip_without_a_recorded_origin_has_none(index):
    rows = _window(index, datetime(2026, 8, 30, 12, 5, tzinfo=IL))

    assert _clock(rows) == ["12:10"]
    assert rows[0].origin is None


def test_departures_outside_the_window_are_not_returned(index):
    assert _window(index, datetime(2026, 8, 30, 6, 0, tzinfo=IL)) == []


def test_an_unknown_stop_returns_nothing(index):
    noon = datetime(2026, 8, 30, 11, 55, tzinfo=IL)
    assert _window(index, noon, hours=3, code=999999) == []


def test_results_are_sorted_across_both_service_days(index):
    index.execute(
        f"INSERT INTO departures {_DEP_COLS} VALUES (35962,34447,1,?,9)", (26 * 3600,)
    )
    rows = _window(index, datetime(2026, 8, 31, 0, 30, tzinfo=IL), hours=3)
    assert [row.when for row in rows] == sorted(row.when for row in rows)


def test_the_window_reaches_back_for_a_late_trip(index):
    """אוטובוס של 12:00 שעוד לא הגיע ב-12:25 חייב להימצא כדי שיזוהה כמאחר."""
    now = datetime(2026, 8, 30, 12, 25, tzinfo=IL)
    rows = gtfs.departures_at(index, 35962, now - timedelta(hours=1), now)
    assert _clock(rows) == ["12:00", "12:10"]


def test_a_trip_just_after_midnight_on_the_next_service_day_is_found(index):
    """בפורמט הישן נסיעה של 00:30 שייכת ליום השירות של מחר."""
    index.execute(
        f"INSERT INTO departures {_DEP_COLS} VALUES (35962,34447,1,?,9)", (30 * 60,)
    )
    # 2026-08-30 is a Sunday; 23:00 Sunday looks ahead into Monday's 00:30.
    rows = _window(index, datetime(2026, 8, 30, 23, 0, tzinfo=IL), hours=2)
    assert [row.when.strftime("%Y-%m-%d %H:%M") for row in rows] == [
        "2026-08-31 00:30",
        "2026-08-31 01:00",
    ]


# --- calendar_dates (the Ministry's v4 format) ------------------------------


def test_an_exception_of_type_2_removes_a_service_on_that_day(index):
    index.execute("INSERT INTO calendar_dates VALUES (1, 20260830, 2)")
    assert _window(index, datetime(2026, 8, 30, 11, 55, tzinfo=IL)) == []


def test_an_exception_of_type_1_adds_a_service_on_that_day(index):
    # שירות 2 רץ רק בשבת; חריג מוסיף אותו ביום ראשון.
    index.execute("INSERT INTO calendar_dates VALUES (2, 20260830, 1)")
    assert _clock(_window(index, datetime(2026, 8, 30, 11, 55, tzinfo=IL))) == [
        "12:00",
        "12:05",
        "12:10",
    ]


def test_a_service_in_both_tables_is_not_returned_twice(index):
    index.execute("INSERT INTO calendar_dates VALUES (1, 20260830, 1)")
    assert _clock(_window(index, datetime(2026, 8, 30, 11, 55, tzinfo=IL))) == [
        "12:00",
        "12:10",
    ]


def test_a_feed_with_only_calendar_dates_is_read():
    """בפורמט החדש אין calendar.txt, ו-service_id הוא התאריך עצמו."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(gtfs._SCHEMA)
    connection.execute(
        "INSERT INTO routes (route_id, short_name, long_name, agency, route_type,"
        " headsign) VALUES (34446, '1', 'בת ים - פתח תקווה', 'תבל', '0', '')"
    )
    connection.execute("INSERT INTO calendar_dates VALUES (20260830, 20260830, 1)")
    # 27:30 של יום השירות שמתחיל ב-04:00: 03:30 בבוקר שלמחרת.
    connection.execute(
        f"INSERT INTO departures {_DEP_COLS} VALUES (35962, 34446, 20260830, ?, 1)",
        (27 * 3600 + 1800,),
    )
    rows = gtfs.departures_at(
        connection,
        35962,
        datetime(2026, 8, 31, 3, 0, tzinfo=IL),
        datetime(2026, 8, 31, 4, 0, tzinfo=IL),
    )
    assert [row.when.strftime("%Y-%m-%d %H:%M") for row in rows] == ["2026-08-31 03:30"]


# --- daylight saving time ---------------------------------------------------
# Israel moved to summer time on Friday 27.03.2026 at 02:00 (to 03:00), and back
# on Sunday 25.10.2026 at 02:00 (to 01:00).

JERUSALEM = gtfs.ISRAEL_TZ


def test_the_service_day_starts_at_noon_minus_twelve_hours():
    """gtfs.org: times are measured from "noon minus 12h" of the service day."""
    base = gtfs.service_day_base(date(2026, 3, 27))
    # Noon on 27.03 is summer time (UTC+3), so the zero point is 21:00 UTC on
    # 26.03 -- 23:00 local, an hour before midnight.
    assert base == datetime(2026, 3, 26, 21, 0, tzinfo=UTC)


def test_a_morning_time_on_the_spring_change_is_wall_clock_correct(index):
    index.execute("INSERT INTO calendar_dates VALUES (1, 20260327, 1)")
    index.execute(
        f"INSERT INTO departures {_DEP_COLS} VALUES (35962,34447,1,?,9)", (8 * 3600,)
    )
    start = datetime(2026, 3, 27, 7, 30, tzinfo=JERUSALEM)
    rows = gtfs.departures_at(index, 35962, start, start + timedelta(hours=1))
    assert [row.when.strftime("%H:%M %z") for row in rows] == ["08:00 +0300"]


def test_the_repeated_hour_on_the_autumn_change_resolves_by_offset(index):
    """ב-25.10 השעה 01:00-01:59 קיימת פעמיים. GTFS סופר שניות מנקודת האפס."""
    index.execute("INSERT INTO calendar_dates VALUES (1, 20261025, 1)")
    index.executemany(
        f"INSERT INTO departures {_DEP_COLS} VALUES (35962,34447,1,?,9)",
        [(30 * 60,), (90 * 60,)],
    )
    start = datetime(2026, 10, 25, 0, 0, tzinfo=JERUSALEM)
    rows = gtfs.departures_at(index, 35962, start, start + timedelta(hours=3))
    assert [row.when.utcoffset() for row in rows] == [
        timedelta(hours=3),  # 00:30 + 3h noon-anchor = 01:30, first time (fold 0)
        timedelta(hours=2),  # 01:30 = 01:30 the second time (fold 1)
    ]
    assert [row.when.strftime("%H:%M") for row in rows] == ["01:30", "01:30"]
