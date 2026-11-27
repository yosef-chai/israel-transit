"""A local index of the Ministry of Transport GTFS feed.

The published feed is a 154 MB ZIP that expands to about 1 GB, which is far more
than is worth keeping. Three things make it cheap:

* The server honours HTTP range requests, so the ZIP central directory is read
  with three short reads and only the members we need are fetched; the fare
  tables are never touched.
* ``stop_times.txt`` -- 86 MB compressed, 737 MB of CSV, 14.5 million rows -- is
  streamed and filtered as it arrives, never materialised.
* Only what real-time data cannot answer is stored: one representative stop
  pattern per route, and full timetables for the modes that publish nothing to
  SIRI (light rail, rail, the cable lines) plus the stops the user configured.
  That is a few hundred thousand rows rather than 14.5 million. ``shapes.txt``
  is read the same way, keeping only the routes through those stops,
  simplified to a few metres.

The result is a SQLite file of a few tens of MB that answers every query the card
makes in well under a millisecond, works offline, and needs rebuilding only when
the Ministry publishes a new feed.

Identifiers line up across sources: a GTFS ``route_id`` is the same number
curlbus reports as ``line_id``, which is what lets a live arrival be joined to
its route and its stop pattern.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import math
import re
import sqlite3
import struct
import sys
import zlib
from array import array
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Final

import aiohttp

from .api import (
    ISRAEL_TZ,
    Arrival,
    IsraelTransitError,
    RouteInfo,
    RouteStop,
    Stop,
    line_sort_key,
)
from .const import GTFS_URL, NON_REALTIME_ROUTE_TYPES, USER_AGENT

_LOGGER = logging.getLogger(__name__)

# Members we read. The fare tables are never fetched.
MEMBERS: Final = (
    "agency.txt",
    "routes.txt",
    "trips.txt",
    "stops.txt",
    "stop_times.txt",
)

# הפורמט הישן מפרסם calendar.txt, והחדש (מסמך המפתחים v4) רק calendar_dates.txt.
# לפחות אחד מהם חובה.
CALENDAR_MEMBERS: Final = ("calendar.txt", "calendar_dates.txt")

# Read when the feed has them; a feed without them still builds.
OPTIONAL_MEMBERS: Final = (*CALENDAR_MEMBERS, "shapes.txt")

# Douglas-Peucker tolerance, in metres. Below what a card map can show.
_SHAPE_TOLERANCE_M: Final = 3.0
# Metres per microdegree of latitude.
_M_PER_MICRODEG: Final = 0.111_32

# stop_desc בפורמט הישן: "רחוב: בן יהודה 74 עיר: כפר סבא רציף:  קומה: ",
# ובחדש אותן תוויות באנגלית: "Street: … City: … Platform:  Floor:".
_CITY_RE: Final = re.compile(
    r"(?:עיר|City):\s*(.*?)\s*(?:רציף:|קומה:|Platform:|Floor:|$)"
)
_STREET_RE: Final = re.compile(
    r"(?:רחוב|Street):\s*(.*?)\s*(?:עיר:|רציף:|קומה:|City:|Platform:|Floor:|$)"
)

# שורות stop_times שנכתבות ל-SQLite בכל פעם, כדי שהבנייה לא תחזיק את כולן בזיכרון.
_BATCH_ROWS: Final = 50_000
# גג לשניות של יום שירות כשהאינדקס לא רשם אחד (GTFS מתיר זמנים מעבר ל-24:00).
_DEFAULT_MAX_SEC: Final = 48 * 3600

_ZIP64_MARK: Final = 0xFFFFFFFF

# Enough for "city street number"; past that the query is not a stop search.
_MAX_SEARCH_WORDS: Final = 4

# Bumped whenever the tables below change shape. An index built by an older
# version stays in use while its replacement is built, as long as it has every
# column the queries read; one older than that is discarded.
SCHEMA_VERSION: Final = 4
# The oldest schema the current queries can still read: one that has every
# column they select. route_shape and routes_at_stop cope with the tables an
# older index lacks; departures_at fails on one, and callers already degrade.
MIN_READABLE_SCHEMA: Final = 2

_SCHEMA: Final = """
CREATE TABLE stops (
    code INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT,
    lat REAL, lon REAL, street TEXT
);
CREATE TABLE routes (
    route_id INTEGER PRIMARY KEY, short_name TEXT, long_name TEXT,
    agency TEXT, route_type TEXT, headsign TEXT, shape_id TEXT, agency_id TEXT
);
CREATE TABLE patterns (
    route_id INTEGER NOT NULL, seq INTEGER NOT NULL,
    stop_code INTEGER NOT NULL, offset_sec INTEGER NOT NULL
);
CREATE TABLE departures (
    stop_code INTEGER NOT NULL, route_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL, arrival_sec INTEGER NOT NULL,
    trip_idx INTEGER NOT NULL
);
CREATE TABLE trips (
    trip_idx INTEGER PRIMARY KEY, origin_sec INTEGER, dest_code INTEGER
);
CREATE TABLE calendar (
    service_id INTEGER PRIMARY KEY, days INTEGER NOT NULL,
    start_date INTEGER NOT NULL, end_date INTEGER NOT NULL
);
CREATE TABLE calendar_dates (
    service_id INTEGER NOT NULL, date INTEGER NOT NULL,
    exception_type INTEGER NOT NULL
);
CREATE TABLE stop_routes (
    stop_code INTEGER NOT NULL, route_id INTEGER NOT NULL,
    PRIMARY KEY (stop_code, route_id)
) WITHOUT ROWID;
CREATE TABLE shapes (shape_id TEXT PRIMARY KEY, points BLOB);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""

_INDEXES: Final = """
CREATE INDEX idx_patterns_route ON patterns (route_id, seq);
CREATE INDEX idx_patterns_stop ON patterns (stop_code);
CREATE INDEX idx_departures_stop ON departures (stop_code, arrival_sec);
CREATE INDEX idx_calendar_window ON calendar (start_date, end_date);
CREATE INDEX idx_calendar_dates ON calendar_dates (date, exception_type);
"""


# code, name, city, lat, lon, street -- the stops row, in column order.
_StopRow = tuple[int, str, str | None, float | None, float | None, str | None]


class GtfsError(IsraelTransitError):
    """The feed could not be read or indexed."""


@dataclass(frozen=True, slots=True)
class ZipMember:
    """One member of the remote archive."""

    name: str
    compress_size: int
    file_size: int
    header_offset: int


@dataclass(frozen=True, slots=True)
class FeedVersion:
    """Identifies a published feed, so an unchanged one is not rebuilt."""

    etag: str | None
    last_modified: str | None
    size: int

    @property
    def token(self) -> str:
        return f"{self.etag or ''}|{self.last_modified or ''}|{self.size}"


# ---------------------------------------------------------------------------
# Reading the remote archive
# ---------------------------------------------------------------------------


def parse_central_directory(tail: bytes, directory: bytes) -> dict[str, ZipMember]:
    """Parse ZIP central directory records.

    The Ministry streams the archive, so every entry carries a ZIP64 extra field
    with the real sizes even though the archive itself is well under 4 GB. The
    base fields then read as 0xFFFFFFFF and must be taken from the extra field.
    """
    members: dict[str, ZipMember] = {}
    pos = 0
    while pos + 46 <= len(directory) and directory[pos : pos + 4] == b"PK\x01\x02":
        compress_size, file_size = struct.unpack("<II", directory[pos + 20 : pos + 28])
        name_len, extra_len, comment_len = struct.unpack(
            "<HHH", directory[pos + 28 : pos + 34]
        )
        header_offset = struct.unpack("<I", directory[pos + 42 : pos + 46])[0]
        name = directory[pos + 46 : pos + 46 + name_len].decode("utf-8", "replace")
        extra = directory[pos + 46 + name_len : pos + 46 + name_len + extra_len]

        offset = 0
        while offset + 4 <= len(extra):
            header_id, size = struct.unpack("<HH", extra[offset : offset + 4])
            if header_id == 0x0001:
                blob = extra[offset + 4 : offset + 4 + size]
                values = [
                    struct.unpack("<Q", blob[i : i + 8])[0]
                    for i in range(0, len(blob) - 7, 8)
                ]
                index = 0
                # The ZIP64 field carries only the values that overflowed, in a
                # fixed order.
                if file_size == _ZIP64_MARK and index < len(values):
                    file_size = values[index]
                    index += 1
                if compress_size == _ZIP64_MARK and index < len(values):
                    compress_size = values[index]
                    index += 1
                if header_offset == _ZIP64_MARK and index < len(values):
                    header_offset = values[index]
                    index += 1
            offset += 4 + size

        members[name] = ZipMember(name, compress_size, file_size, header_offset)
        pos += 46 + name_len + extra_len + comment_len

    if not members:
        raise GtfsError("no entries found in the GTFS archive directory")
    return members


def locate_directory(tail: bytes, total_size: int) -> tuple[int, int]:
    """Return (offset, size) of the central directory from the archive tail."""
    index = tail.rfind(b"PK\x05\x06")
    if index == -1:
        raise GtfsError("GTFS archive has no end-of-central-directory record")
    cd_size, cd_offset = struct.unpack("<II", tail[index + 12 : index + 20])
    if _ZIP64_MARK not in (cd_size, cd_offset):
        return cd_offset, cd_size
    locator = tail.rfind(b"PK\x06\x07")
    if locator == -1:
        raise GtfsError("GTFS archive claims ZIP64 but has no locator")
    return -1, struct.unpack("<Q", tail[locator + 8 : locator + 16])[0]


def iter_lines(chunks: Iterable[bytes]) -> Iterator[str]:
    """Decode a byte stream into lines without buffering the whole thing.

    These files carry a UTF-8 BOM and CRLF endings, both of which would
    otherwise end up glued to the first column name.
    """
    buffer = b""
    first = True
    for chunk in chunks:
        if first:
            buffer += chunk.removeprefix(b"\xef\xbb\xbf")
            first = False
        else:
            buffer += chunk
        start = 0
        while (newline := buffer.find(b"\n", start)) != -1:
            yield buffer[start:newline].rstrip(b"\r").decode("utf-8", "replace")
            start = newline + 1
        buffer = buffer[start:]
    if buffer:
        yield buffer.decode("utf-8", "replace")


def inflate(chunks: Iterable[bytes]) -> Iterator[bytes]:
    """Inflate a raw deflate stream; a ZIP member has no zlib wrapper."""
    decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    for chunk in chunks:
        if out := decompressor.decompress(chunk):
            yield out
    if tail := decompressor.flush():
        yield tail


class GtfsDownloader:
    """Fetches just the members we need, over Home Assistant's HTTP session."""

    def __init__(self, session: aiohttp.ClientSession, url: str = GTFS_URL) -> None:
        self._session = session
        self._url = url

    async def _range(self, start: int, end: int) -> bytes:
        headers = {"Range": f"bytes={start}-{end}", "User-Agent": USER_AGENT}
        try:
            async with self._session.get(
                self._url, headers=headers, timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status not in (200, 206):
                    raise GtfsError(f"GTFS feed returned HTTP {response.status}")
                return await response.read()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise GtfsError(f"GTFS feed unreachable: {err}") from err

    async def async_version(self) -> FeedVersion:
        """Identify the published feed without downloading it."""
        headers = {"Range": "bytes=0-0", "User-Agent": USER_AGENT}
        try:
            async with self._session.get(
                self._url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status not in (200, 206):
                    raise GtfsError(f"GTFS feed returned HTTP {response.status}")
                content_range = response.headers.get("Content-Range", "")
                if "/" not in content_range:
                    raise GtfsError("GTFS feed does not support range requests")
                return FeedVersion(
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                    size=int(content_range.rsplit("/", 1)[-1]),
                )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise GtfsError(f"GTFS feed unreachable: {err}") from err

    async def async_members(self, total_size: int) -> dict[str, ZipMember]:
        """Read the archive directory with three short range requests."""
        tail_length = min(total_size, 65536 + 22)
        tail = await self._range(total_size - tail_length, total_size - 1)
        cd_offset, cd_size = locate_directory(tail, total_size)
        if cd_offset == -1:  # ZIP64: cd_size holds the EOCD64 record offset
            eocd = await self._range(cd_size, cd_size + 55)
            cd_size, cd_offset = struct.unpack("<QQ", eocd[40:56])
        directory = await self._range(cd_offset, cd_offset + cd_size - 1)
        return parse_central_directory(tail, directory)

    async def async_fetch_member(self, member: ZipMember, target: Path) -> int:
        """Stream one member's compressed bytes to disk without holding them."""
        head = await self._range(member.header_offset, member.header_offset + 29)
        name_len, extra_len = struct.unpack("<HH", head[26:30])
        start = member.header_offset + 30 + name_len + extra_len
        headers = {
            "Range": f"bytes={start}-{start + member.compress_size - 1}",
            "User-Agent": USER_AGENT,
        }
        # Opening and writing are blocking calls, and this streams ~150 MB, so
        # every one of them is handed to a worker thread. The chunk is a whole
        # megabyte, which keeps the number of hops to about a hundred and fifty.
        loop = asyncio.get_running_loop()
        written = 0
        try:
            async with self._session.get(
                self._url, headers=headers, timeout=aiohttp.ClientTimeout(total=1800)
            ) as response:
                if response.status not in (200, 206):
                    raise GtfsError(f"GTFS member returned HTTP {response.status}")
                handle = await loop.run_in_executor(None, target.open, "wb")
                try:
                    async for chunk in response.content.iter_chunked(1 << 20):
                        await loop.run_in_executor(None, handle.write, chunk)
                        written += len(chunk)
                finally:
                    await loop.run_in_executor(None, handle.close)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise GtfsError(f"GTFS member download failed: {err}") from err
        return written


# ---------------------------------------------------------------------------
# Building the index -- everything below blocks and runs in an executor
# ---------------------------------------------------------------------------


def _member_lines(path: Path) -> Iterator[str]:
    with path.open("rb") as handle:
        yield from iter_lines(inflate(iter(lambda: handle.read(1 << 20), b"")))


def _member_rows(path: Path) -> Iterator[dict[str, str]]:
    return csv.DictReader(_member_lines(path))


def _seconds(value: str) -> int | None:
    """GTFS times run past midnight: 25:10:00 is 01:10 the following day."""
    parts = value.split(":")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None


def _day_mask(row: dict[str, str]) -> int:
    """Weekday flags as a bitmask; bit 0 is Sunday, as the GTFS columns are."""
    days = (
        "sunday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
    )
    return sum(1 << i for i, day in enumerate(days) if row.get(day) == "1")


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _described(description: str, field: re.Pattern[str]) -> str | None:
    """One labelled field out of stop_desc, or None when it is blank."""
    found = field.search(description)
    return (found.group(1) or None) if found else None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _in_israel(lat: int, lon: int) -> bool:
    """Microdegrees inside a box around Israel; (0, 0) and stray points fall out."""
    return 29_000_000 <= lat <= 34_000_000 and 34_000_000 <= lon <= 36_000_000


def read_shapes(
    lines: Iterator[str], wanted: set[str]
) -> dict[str, tuple[array[int], array[int], array[int]]]:
    """The points of the wanted shapes: (seq, lat, lon) arrays, in file order.

    shapes.txt is the largest member after stop_times, so a row is tested by
    its shape_id before paying for any number conversion.
    """
    rows = csv.reader(lines)
    header = next(rows, None)
    if header is None:
        return {}
    try:
        i_id, i_lat, i_lon, i_seq = (
            header.index(name)
            for name in (
                "shape_id",
                "shape_pt_lat",
                "shape_pt_lon",
                "shape_pt_sequence",
            )
        )
    except ValueError as err:
        raise GtfsError(f"shapes.txt lacks a column: {err}") from err
    width = max(i_id, i_lat, i_lon, i_seq)
    shapes: dict[str, tuple[array[int], array[int], array[int]]] = {}
    for row in rows:
        if len(row) <= width or (shape_id := row[i_id]) not in wanted:
            continue
        try:
            seq = int(row[i_seq])
            lat = round(float(row[i_lat]) * 1e6)
            lon = round(float(row[i_lon]) * 1e6)
        except ValueError:
            continue
        if shape_id not in shapes:
            shapes[shape_id] = (array("i"), array("i"), array("i"))
        seqs, lats, lons = shapes[shape_id]
        seqs.append(seq)
        lats.append(lat)
        lons.append(lon)
    return shapes


def simplify(lats: list[int], lons: list[int], tolerance: float) -> list[int]:
    """Douglas-Peucker over microdegrees; returns the indexes of the kept points.

    Iterative, with an explicit stack: a shape runs to thousands of points and
    recursion would hit Python's limit. Distances are squared, in metres, on a
    local flat projection, which is plenty at the scale of a bus route.
    """
    count = len(lats)
    if count < 3:
        return list(range(count))
    scale_x = _M_PER_MICRODEG * math.cos(math.radians(lats[0] / 1e6))
    xs = [lon * scale_x for lon in lons]
    ys = [lat * _M_PER_MICRODEG for lat in lats]
    limit = tolerance * tolerance
    keep = bytearray(count)
    keep[0] = keep[-1] = 1
    stack = [(0, count - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        ax, ay = xs[start], ys[start]
        dx, dy = xs[end] - ax, ys[end] - ay
        length = dx * dx + dy * dy
        worst, worst_at = -1.0, start
        for i in range(start + 1, end):
            px, py = xs[i] - ax, ys[i] - ay
            if length:
                # Distance to the segment, not to the infinite line.
                t = max(0.0, min(1.0, (px * dx + py * dy) / length))
                px, py = px - t * dx, py - t * dy
            # A closed loop has a zero-length chord; measure from its start.
            distance = px * px + py * py
            if distance > worst:
                worst, worst_at = distance, i
        if worst > limit:
            keep[worst_at] = 1
            stack.append((start, worst_at))
            stack.append((worst_at, end))
    return [i for i in range(count) if keep[i]]


def encode_shape(seqs: array[int], lats: array[int], lons: array[int]) -> bytes | None:
    """Sort, clean and simplify one shape into interleaved little-endian int32.

    The file order of shapes.txt is not guaranteed, so the points are put in
    sequence order first. None when fewer than two points survive.
    """
    order = sorted(range(len(seqs)), key=seqs.__getitem__)
    points = [(lats[i], lons[i]) for i in order if _in_israel(lats[i], lons[i])]
    if len(points) < 2:
        return None
    kept_lats = [lat for lat, _ in points]
    kept_lons = [lon for _, lon in points]
    out = array("i")
    for i in simplify(kept_lats, kept_lons, _SHAPE_TOLERANCE_M):
        out.append(kept_lats[i])
        out.append(kept_lons[i])
    if sys.byteorder == "big":
        out.byteswap()
    return out.tobytes()


def decode_shape(blob: bytes) -> list[list[float]]:
    """Interleaved little-endian microdegrees back into [[lat, lon], ...]."""
    values = array("i")
    values.frombytes(blob)
    if sys.byteorder == "big":
        values.byteswap()
    return [
        [values[i] / 1e6, values[i + 1] / 1e6] for i in range(0, len(values) - 1, 2)
    ]


def staged_path(db_path: Path) -> Path:
    """Where an index is written before it takes the place of the live one."""
    return db_path.with_suffix(".building")


def build_index(
    files: dict[str, Path],
    db_path: Path,
    extra_stop_codes: frozenset[int],
    version_token: str,
) -> dict[str, int]:
    """Build an index at ``db_path``, replacing whatever was there."""
    stats = stage_index(files, db_path, extra_stop_codes, version_token)
    activate_index(db_path)
    return stats


def activate_index(db_path: Path) -> None:
    """Put a staged index in place of the live one.

    Any reader has to be closed first: on Windows the replace fails outright
    while a connection is open, and on POSIX it succeeds but leaves that
    connection serving a file with no name for as long as it lives.
    """
    db_path.unlink(missing_ok=True)
    staged_path(db_path).replace(db_path)


def stage_index(
    files: dict[str, Path],
    db_path: Path,
    extra_stop_codes: frozenset[int],
    version_token: str,
) -> dict[str, int]:
    """Build the SQLite index from downloaded members, without installing it.

    A single pass over ``stop_times.txt`` produces both the per-route stop
    patterns and the timetables, testing each raw line against small sets before
    paying for any CSV parsing.

    It writes beside ``db_path`` rather than to it and stops there, so the index
    already in place stays open and answering for the several minutes this
    takes. Only :func:`activate_index` needs the reader out of the way.
    """
    stats: dict[str, int] = {}

    agencies = {
        row["agency_id"]: row["agency_name"]
        for row in _member_rows(files["agency.txt"])
    }

    # route key (the GTFS string) -> (route_id, short, long, agency, type, agency_id)
    routes: dict[str, tuple[int, str, str, str, str, str]] = {}
    for row in _member_rows(files["routes.txt"]):
        if not (row.get("route_id") or "").isdigit():
            continue
        routes[row["route_id"]] = (
            int(row["route_id"]),
            row.get("route_short_name", ""),
            row.get("route_long_name", ""),
            agencies.get(row.get("agency_id", ""), ""),
            row.get("route_type", ""),
            row.get("agency_id", ""),
        )
    stats["routes"] = len(routes)

    # One trip per route gives its stop pattern; every trip of a mode without
    # real-time gives its timetable.
    pattern_trips: dict[str, str] = {}  # trip_id -> route key
    timetable_trips: dict[str, tuple[str, int]] = {}  # trip_id -> (route key, service)
    headsigns: dict[str, str] = {}
    route_shapes: dict[str, str] = {}  # route key -> shape_id
    # Routes whose pattern trip has no shape_id fall back to their most common.
    shape_votes: dict[str, Counter[str]] = {}
    seen_routes: set[str] = set()
    for row in _member_rows(files["trips.txt"]):
        route_key = row.get("route_id", "")
        route = routes.get(route_key)
        if route is None:
            continue
        trip_id = row["trip_id"]
        shape_id = row.get("shape_id") or ""
        if route_key not in seen_routes:
            seen_routes.add(route_key)
            pattern_trips[trip_id] = route_key
            headsigns[route_key] = row.get("trip_headsign", "")
            if shape_id:
                route_shapes[route_key] = shape_id
            else:
                shape_votes[route_key] = Counter()
        elif shape_id and route_key in shape_votes:
            shape_votes[route_key][shape_id] += 1
        if route[4] in NON_REALTIME_ROUTE_TYPES:
            timetable_trips[trip_id] = (route_key, _int(row.get("service_id")))
    for route_key, votes in shape_votes.items():
        if votes:
            route_shapes[route_key] = votes.most_common(1)[0][0]
    stats["pattern_trips"] = len(pattern_trips)
    stats["timetable_trips"] = len(timetable_trips)

    stops: dict[str, _StopRow] = {}
    # מסוף או תחנה מרכזית הם stop_id לכל רציף, כולם עם אותו קוד: כולם נכנסים.
    wanted_stop_ids: set[str] = set()
    for row in _member_rows(files["stops.txt"]):
        code_text = row.get("stop_code") or ""
        if not code_text.isdigit():
            continue
        code = int(code_text)
        description = row.get("stop_desc") or ""
        stops[row["stop_id"]] = (
            code,
            row.get("stop_name", ""),
            _described(description, _CITY_RE),
            _float(row.get("stop_lat")),
            _float(row.get("stop_lon")),
            _described(description, _STREET_RE),
        )
        if code in extra_stop_codes:
            wanted_stop_ids.add(row["stop_id"])
    stats["stops"] = len(stops)

    calendar_rows = (
        [
            (
                _int(row["service_id"]),
                _day_mask(row),
                _int(row.get("start_date")),
                _int(row.get("end_date")),
            )
            for row in _member_rows(files["calendar.txt"])
            if (row.get("service_id") or "").isdigit()
        ]
        if "calendar.txt" in files
        else []
    )
    exception_rows = (
        [
            (
                _int(row["service_id"]),
                _int(row.get("date")),
                _int(row.get("exception_type")),
            )
            for row in _member_rows(files["calendar_dates.txt"])
            if (row.get("service_id") or "").isdigit()
        ]
        if "calendar_dates.txt" in files
        else []
    )
    if not calendar_rows and not exception_rows:
        raise GtfsError("GTFS feed has no service calendar")
    stats["calendar"] = len(calendar_rows)
    stats["calendar_dates"] = len(exception_rows)
    # עד איזה יום יש בו שירות. חריג מסוג 2 מבטל ולכן לא מאריך את הכיסוי.
    coverage_end = max(
        [end for _, _, _, end in calendar_rows]
        + [day for _, day, kind in exception_rows if kind == 1],
        default=0,
    )

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = staged_path(db_path)
    tmp_path.unlink(missing_ok=True)
    connection = sqlite3.connect(tmp_path)
    try:
        connection.executescript("PRAGMA journal_mode=OFF;PRAGMA synchronous=OFF;")
        connection.executescript(_SCHEMA)

        scan = _scan_stop_times(
            connection,
            files["stop_times.txt"],
            _Feed(
                routes,
                pattern_trips,
                timetable_trips,
                stops,
                wanted_stop_ids,
                extra_stop_codes,
            ),
        )
        if scan.pending:
            _resolve_pending(connection, files["trips.txt"], routes, scan)
        stats["stop_times_scanned"] = scan.scanned
        stats["patterns"] = scan.patterns
        stats["departures"] = scan.departures
        stats["origin_violations"] = scan.violations
        if scan.violations:
            _LOGGER.warning(
                "%s GTFS trips are not stored in stop order; their rows will "
                "not be matched to live arrivals by trip",
                f"{scan.violations:,}",
            )

        # Shapes only for the routes through the indexed stops: the card draws a
        # route from a stop's board, and every route would cost tens of MB.
        wanted_shapes = {
            shape_id
            for key, shape_id in route_shapes.items()
            if routes[key][0] in scan.serving
        }
        shape_rows: list[tuple[str, bytes]] = []
        if wanted_shapes and "shapes.txt" in files:
            # Each shape_id once, however many routes share it.
            for shape_id, (seqs, lats, lons) in read_shapes(
                _member_lines(files["shapes.txt"]), wanted_shapes
            ).items():
                if (blob := encode_shape(seqs, lats, lons)) is not None:
                    shape_rows.append((shape_id, blob))
        stats["shapes"] = len(shape_rows)

        connection.executemany(
            "INSERT OR REPLACE INTO stops VALUES (?,?,?,?,?,?)", list(stops.values())
        )
        connection.executemany(
            "INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    rid,
                    short,
                    long_name,
                    agency,
                    rtype,
                    headsigns.get(key, ""),
                    route_shapes.get(key),
                    agency_id,
                )
                for key, (
                    rid,
                    short,
                    long_name,
                    agency,
                    rtype,
                    agency_id,
                ) in routes.items()
            ],
        )
        connection.executemany("INSERT INTO shapes VALUES (?,?)", shape_rows)
        connection.executemany(
            "INSERT OR REPLACE INTO calendar VALUES (?,?,?,?)", calendar_rows
        )
        connection.executemany(
            "INSERT INTO calendar_dates VALUES (?,?,?)", exception_rows
        )
        # הקווים בכל תחנה, מחושבים פעם אחת כאן ולא בכל polling.
        connection.execute(
            "INSERT OR IGNORE INTO stop_routes "
            "SELECT stop_code, route_id FROM patterns "
            "UNION SELECT stop_code, route_id FROM departures"
        )
        connection.executescript(_INDEXES)
        connection.executemany(
            "INSERT OR REPLACE INTO meta VALUES (?,?)",
            [
                ("version", version_token),
                ("schema", str(SCHEMA_VERSION)),
                ("built", datetime.now().isoformat(timespec="seconds")),
                # Which stops got a bus timetable. A feed that has not changed
                # still needs rebuilding once a stop is added, and the version
                # token alone cannot say that.
                ("stops", ",".join(str(code) for code in sorted(extra_stop_codes))),
                ("coverage_end", str(coverage_end)),
                ("max_sec", str(scan.max_sec)),
            ],
        )
        connection.commit()
        # Give the query planner statistics, then compact the file.
        connection.execute("ANALYZE")
        connection.execute("VACUUM")
    finally:
        connection.close()

    stats["db_bytes"] = tmp_path.stat().st_size
    return stats


@dataclass(slots=True)
class _Feed:
    """מה שנקרא מהקבצים הקטנים, ומשמש את סריקת stop_times."""

    routes: dict[str, tuple[int, str, str, str, str, str]]
    pattern_trips: dict[str, str]
    timetable_trips: dict[str, tuple[str, int]]
    stops: dict[str, _StopRow]
    wanted_stop_ids: set[str]
    extra_stop_codes: frozenset[int]


@dataclass(slots=True)
class _Block:
    """רצף שורות stop_times של נסיעה אחת, כפי שהן מגיעות בזרם."""

    trip_id: str
    idx: int
    pattern_route: str | None
    timetable: tuple[str, int] | None
    origin: int | None = None
    dest: int | None = None
    base: int | None = None
    last_seq: int | None = None
    valid: bool = True
    kept: bool = False


@dataclass(slots=True)
class _Scan:
    """מה שסריקת stop_times מחזירה, אחרי שהשורות עצמן כבר נכתבו ל-SQLite."""

    scanned: int = 0
    patterns: int = 0
    departures: int = 0
    violations: int = 0
    max_sec: int = 0
    serving: set[int] = field(default_factory=set)
    # שורות בתחנה מוגדרת של נסיעה שה-route שלה עוד לא ידוע:
    # (trip_id, stop_code, arrival_sec, trip_idx).
    pending: list[tuple[str, int, int, int]] = field(default_factory=list)


class _Writer:
    """צובר שורות וכותב אותן במנות, כדי שהבנייה לא תחזיק את כולן בזיכרון."""

    def __init__(self, connection: sqlite3.Connection, sql: str) -> None:
        self._connection = connection
        self._sql = sql
        self._rows: list[tuple[Any, ...]] = []

    def add(self, row: tuple[Any, ...]) -> None:
        self._rows.append(row)
        if len(self._rows) >= _BATCH_ROWS:
            self.flush()

    def flush(self) -> None:
        if self._rows:
            self._connection.executemany(self._sql, self._rows)
            self._rows.clear()


def _scan_stop_times(connection: sqlite3.Connection, path: Path, feed: _Feed) -> _Scan:
    """מעבר יחיד על stop_times: דפוסי קווים, לוחות זמנים, ומוצא ויעד לכל נסיעה.

    המוצא והיעד נלקחים מהשורה הראשונה והאחרונה של רצף הנסיעה, ולכן תקפים רק
    אם הקובץ ממוין לפי נסיעה ו-stop_sequence עולה בתוכה. רצף שלא מתחיל ב-0 או ב-1,
    או שה-sequence בו לא עולה, נשמר בלי מוצא ויעד ונספר כהפרה.
    """
    lines = _member_lines(path)
    columns = next(csv.reader([next(lines, "")]), [])
    try:
        i_trip, i_arr, i_dep, i_stop, i_seq = (
            columns.index(name)
            for name in (
                "trip_id",
                "arrival_time",
                "departure_time",
                "stop_id",
                "stop_sequence",
            )
        )
    except ValueError as err:
        raise GtfsError(f"stop_times.txt lacks a column: {err}") from err
    width = max(i_trip, i_arr, i_dep, i_stop, i_seq)
    routes, stops, wanted_stop_ids = feed.routes, feed.stops, feed.wanted_stop_ids
    extra_stop_codes = feed.extra_stop_codes

    scan = _Scan()
    patterns = _Writer(connection, "INSERT INTO patterns VALUES (?,?,?,?)")
    departures = _Writer(connection, "INSERT INTO departures VALUES (?,?,?,?,?)")
    trips = _Writer(connection, "INSERT INTO trips VALUES (?,?,?)")

    def close(block: _Block) -> None:
        if not block.kept:
            return
        if not block.valid:
            scan.violations += 1
            trips.add((block.idx, None, None))
        else:
            trips.add((block.idx, block.origin, block.dest))

    block: _Block | None = None
    for line in lines:
        scan.scanned += 1
        trip_id = (
            line[: line.find(",")]
            if i_trip == 0
            else line.split(",", i_trip + 1)[i_trip]
        )
        if block is None or trip_id != block.trip_id:
            if block is not None:
                close(block)
            block = _Block(
                trip_id,
                block.idx + 1 if block is not None else 0,
                feed.pattern_trips.get(trip_id),
                feed.timetable_trips.get(trip_id),
            )
        if (
            block.pattern_route is None
            and block.timetable is None
            and not wanted_stop_ids
        ):
            continue

        fields = line.split(",", width + 1)
        if len(fields) <= width:
            continue
        seq = _int(fields[i_seq], -1)
        if block.last_seq is None:
            block.valid = 0 <= seq <= 1
            departure = _seconds(fields[i_dep])
            block.origin = (
                departure if departure is not None else _seconds(fields[i_arr])
            )
        elif seq <= block.last_seq:
            block.valid = False
        block.last_seq = seq
        stop_id = fields[i_stop]
        stop = stops.get(stop_id)
        # היעד הוא תחנת השורה האחרונה ברצף, גם אם היא לא נשמרת לשום טבלה.
        block.dest = stop[0] if stop is not None else None
        if stop is None:
            continue
        arrival = _seconds(fields[i_arr])
        if arrival is None:
            continue
        code = stop[0]

        if block.pattern_route is not None:
            if block.base is None:
                block.base = arrival
            route_id = routes[block.pattern_route][0]
            patterns.add((route_id, seq, code, arrival - block.base))
            scan.patterns += 1
            if code in extra_stop_codes:
                scan.serving.add(route_id)
        if block.timetable is not None:
            route_id = routes[block.timetable[0]][0]
            departures.add((code, route_id, block.timetable[1], arrival, block.idx))
            scan.departures += 1
            block.kept = True
            scan.max_sec = max(scan.max_sec, arrival)
            if code in extra_stop_codes:
                scan.serving.add(route_id)
        elif stop_id in wanted_stop_ids:
            scan.pending.append((trip_id, code, arrival, block.idx))
            block.kept = True
            scan.max_sec = max(scan.max_sec, arrival)

    if block is not None:
        close(block)
    for writer in (patterns, departures, trips):
        writer.flush()
    return scan


def _resolve_pending(
    connection: sqlite3.Connection,
    trips_path: Path,
    routes: dict[str, tuple[int, str, str, str, str, str]],
    scan: _Scan,
) -> None:
    """משלים route ושירות לשורות של תחנות מוגדרות, במעבר זול שני על trips.txt."""
    wanted_trips = {trip_id for trip_id, _, _, _ in scan.pending}
    resolved: dict[str, tuple[int, int]] = {}
    for row in _member_rows(trips_path):
        trip_id = row.get("trip_id", "")
        if trip_id not in wanted_trips:
            continue
        if route := routes.get(row.get("route_id", "")):
            resolved[trip_id] = (route[0], _int(row.get("service_id")))
    departures = _Writer(connection, "INSERT INTO departures VALUES (?,?,?,?,?)")
    for trip_id, code, arrival, trip_idx in scan.pending:
        if (entry := resolved.get(trip_id)) is not None:
            departures.add((code, entry[0], entry[1], arrival, trip_idx))
            scan.departures += 1
            scan.serving.add(entry[0])
    departures.flush()
    scan.pending.clear()


# ---------------------------------------------------------------------------
# Querying the index
# ---------------------------------------------------------------------------


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the index read-only for Home Assistant's executor threads."""
    connection = sqlite3.connect(
        f"file:{db_path}?mode=ro", uri=True, check_same_thread=False
    )
    connection.row_factory = sqlite3.Row
    return connection


def stored_version(connection: sqlite3.Connection) -> str | None:
    row = connection.execute("SELECT value FROM meta WHERE key='version'").fetchone()
    return row["value"] if row else None


def stored_stop_codes(connection: sqlite3.Connection) -> frozenset[int]:
    """The stops this index holds bus timetables for.

    An index built before this was recorded answers with the empty set, which
    is the truth as far as anything can tell: rebuilding is the only way to
    find out, and it is what the caller wants anyway.
    """
    row = connection.execute("SELECT value FROM meta WHERE key='stops'").fetchone()
    if not row or not row["value"]:
        return frozenset()
    return frozenset(
        int(part) for part in row["value"].split(",") if part.strip().isdigit()
    )


def stored_schema(connection: sqlite3.Connection) -> int | None:
    """The schema this index was built by, or None when it does not say."""
    row = connection.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
    return _int(row["value"], -1) if row else None


def schema_is_readable(schema: int | None) -> bool:
    """Whether the current queries can run on an index of this schema."""
    return schema is not None and MIN_READABLE_SCHEMA <= schema <= SCHEMA_VERSION


def stored_built(connection: sqlite3.Connection) -> str | None:
    """When this index was built, as written to meta."""
    row = connection.execute("SELECT value FROM meta WHERE key='built'").fetchone()
    return row["value"] if row else None


def _stored_int(connection: sqlite3.Connection, key: str) -> int | None:
    row = connection.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    value = _int(row["value"], -1) if row else -1
    return value if value >= 0 else None


def stored_coverage_end(connection: sqlite3.Connection) -> date | None:
    """היום האחרון שיש בו שירות באינדקס, או None באינדקס שלא רשם אותו."""
    stamp = _stored_int(connection, "coverage_end")
    if not stamp:
        return None
    try:
        return datetime.strptime(str(stamp), "%Y%m%d").date()
    except ValueError:
        return None


def stored_max_sec(connection: sqlite3.Connection) -> int | None:
    """השנייה המאוחרת ביותר של יום שירות שנשמרה בלוח הזמנים."""
    return _stored_int(connection, "max_sec")


def has_table(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        is not None
    )


def service_day_bit(day: date) -> int:
    """The calendar bit for a weekday; GTFS weeks start on Sunday."""
    return 1 << ((day.weekday() + 1) % 7)


def service_day_base(day: date) -> datetime:
    """נקודת האפס של יום שירות, ב-UTC.

    לפי תקן GTFS זמנים נמדדים מ-"noon minus 12h" של יום השירות. בדרך כלל זו
    חצות, אבל לא בימים שבהם השעון זז.
    """
    noon = datetime.combine(day, time(12), tzinfo=ISRAEL_TZ)
    return noon.astimezone(UTC) - timedelta(hours=12)


# שירות פעיל ביום מסוים: calendar פחות חריגים מסוג 2, ובנוסף חריגים מסוג 1.
_DEPARTURES_SQL: Final = """
SELECT d.route_id, d.arrival_sec, r.short_name, r.long_name,
       r.agency, r.route_type, r.headsign, r.agency_id,
       t.origin_sec, t.dest_code
  FROM departures d
  JOIN routes r ON r.route_id = d.route_id
  LEFT JOIN trips t ON t.trip_idx = d.trip_idx
 WHERE d.stop_code = :stop
   AND d.arrival_sec BETWEEN :low AND :high
   AND d.service_id IN (
       SELECT service_id FROM calendar
        WHERE (days & :bit) != 0 AND start_date <= :day AND end_date >= :day
          AND service_id NOT IN (
              SELECT service_id FROM calendar_dates
               WHERE date = :day AND exception_type = 2)
       UNION
       SELECT service_id FROM calendar_dates
        WHERE date = :day AND exception_type = 1)
 ORDER BY d.arrival_sec
"""


@dataclass(frozen=True, slots=True)
class ScheduledRow:
    """שורת לוח זמנים עם הזמנים המוחלטים שלה."""

    row: sqlite3.Row
    when: datetime
    origin: datetime | None


def departures_at(
    connection: sqlite3.Connection,
    stop_code: int,
    start: datetime,
    end: datetime,
    max_sec: int | None = None,
) -> list[ScheduledRow]:
    """Timetabled departures between ``start`` and ``end``, with absolute times.

    נבדקים אתמול, היום ומחר: נסיעה שהתחילה אתמול נשמרת עם זמן מעבר ל-24:00,
    ובפורמט הישן נסיעה של 00:30 שייכת ליום השירות של מחר. גבולות החלון
    מחושבים לכל יום מנקודת האפס שלו, כך שימים של 23 ו-25 שעות לא מאבדים שעה.
    יום שהחלון לא נוגע בו לא נשאל בכלל.

    The active services stay inside the statement as a subquery: the feed has
    ~44k calendar rows and thousands are live on any given day, so lifting them
    into a Python list only to send them back as bind parameters is slower than
    letting SQLite join them.
    """
    limit = _DEFAULT_MAX_SEC if max_sec is None else max_sec
    first = start.astimezone(ISRAEL_TZ).date() - timedelta(days=1)
    days = (end.astimezone(ISRAEL_TZ).date() - first).days + 1
    results: list[ScheduledRow] = []
    for day_offset in range(days):
        day = first + timedelta(days=day_offset)
        base = service_day_base(day)
        low = math.floor((start - base).total_seconds())
        high = math.ceil((end - base).total_seconds())
        if high < 0 or low > limit:
            continue
        stamp = int(day.strftime("%Y%m%d"))
        rows = connection.execute(
            _DEPARTURES_SQL,
            {
                "stop": stop_code,
                "low": low,
                "high": high,
                "bit": service_day_bit(day),
                "day": stamp,
            },
        ).fetchall()
        for row in rows:
            origin = row["origin_sec"]
            results.append(
                ScheduledRow(
                    row,
                    (base + timedelta(seconds=row["arrival_sec"])).astimezone(
                        ISRAEL_TZ
                    ),
                    (base + timedelta(seconds=origin)).astimezone(ISRAEL_TZ)
                    if origin is not None
                    else None,
                )
            )
    results.sort(key=lambda item: item.when)
    return results


# ---------------------------------------------------------------------------
# Queries. These take a connection and block, so callers run them off the loop.
# ---------------------------------------------------------------------------


def headsign_of(row: sqlite3.Row) -> str:
    """What the vehicle shows on the front.

    ``trip_headsign`` is written for riders and is preferred. Falling back to
    ``route_long_name`` means unpicking ``origin-city<->destination-city-direction``,
    whose far half carries a city and a direction code nobody sees on a vehicle.
    """
    if sign := (row["headsign"] or "").strip():
        return sign.replace("_", " ")
    long_name = row["long_name"] or ""
    if "<->" not in long_name:
        return long_name
    tail = long_name.split("<->", 1)[1].strip()
    parts = [part.strip() for part in tail.split("-") if part.strip()]
    if parts and parts[-1].rstrip("#").isdigit():
        parts.pop()
    if len(parts) > 1:
        parts.pop()
    return "-".join(parts) or tail


def route_of(row: sqlite3.Row) -> RouteInfo:
    """Build a route from a joined query row."""
    return RouteInfo(
        route_id=row["route_id"],
        line_ref=str(row["route_id"]),
        short_name=row["short_name"] or "",
        long_name=row["long_name"] or "",
        agency=row["agency"] or "",
        route_type=row["route_type"] or "",
        headsign=headsign_of(row),
    )


def _stop_of(row: sqlite3.Row) -> Stop:
    return Stop(
        row["code"], row["name"], row["city"], row["lat"], row["lon"], row["street"]
    )


def get_stop(connection: sqlite3.Connection, code: int) -> Stop | None:
    row = connection.execute(
        "SELECT code, name, city, lat, lon, street FROM stops WHERE code = ?", (code,)
    ).fetchone()
    return _stop_of(row) if row else None


def search_stops(
    connection: sqlite3.Connection, query: str, limit: int = 25
) -> list[Stop]:
    """Search by code, or by name / city / street, best matches first.

    Every word has to match something, in any order, which is what makes
    "כפר סבא ויצמן" -- a city and a street -- narrow down to the handful of
    stops on that road rather than to everything in the city. Israeli stops
    are usually named for a landmark rather than for the road they stand on,
    so the street from ``stop_desc`` is searched alongside the name.
    """
    needle = (query or "").strip()
    if not needle:
        return []
    if needle.isdigit() and (exact := get_stop(connection, int(needle))) is not None:
        return [exact]

    words = needle.split()[:_MAX_SEARCH_WORDS]
    params: list[Any] = []
    for word in words:
        params += [f"%{word}%"] * 3
    # The longest word is the most specific one, and the one worth ranking on:
    # in "בת ים הקוממיות" it is the stop, in "בת ים" it is the city.
    key = max(words, key=len)
    params += [f"{key}%", f"%{key}%", limit]

    rows = connection.execute(
        "SELECT code, name, city, lat, lon, street FROM stops WHERE "
        + " AND ".join(["(name LIKE ? OR city LIKE ? OR street LIKE ?)"] * len(words))
        # A stop whose own name opens with the query is what was meant; a match
        # only on the city or the street is the weakest of the three.
        + " ORDER BY CASE WHEN name LIKE ? THEN 0 WHEN name LIKE ? THEN 1"
        " ELSE 2 END, name, code LIMIT ?",
        params,
    ).fetchall()
    return [_stop_of(row) for row in rows]


def routes_at_stop(connection: sqlite3.Connection, code: int) -> list[RouteInfo]:
    """כל הקווים בתחנה. אינדקס מסכמה ישנה, בלי stop_routes, נשען על הדפוסים."""
    source = "stop_routes" if has_table(connection, "stop_routes") else "patterns"
    rows = connection.execute(
        "SELECT DISTINCT r.route_id, r.short_name, r.long_name, r.agency, "
        f"r.route_type, r.headsign FROM {source} p "
        "JOIN routes r ON r.route_id = p.route_id WHERE p.stop_code = ?",
        (code,),
    ).fetchall()
    return sorted(
        (route_of(row) for row in rows),
        key=lambda route: line_sort_key(route.short_name),
    )


def route_stops(connection: sqlite3.Connection, route_id: int) -> list[RouteStop]:
    rows = connection.execute(
        "SELECT p.seq, p.offset_sec, s.code, s.name, s.city, s.lat, s.lon, s.street "
        "FROM patterns p JOIN stops s ON s.code = p.stop_code "
        "WHERE p.route_id = ? ORDER BY p.seq",
        (route_id,),
    ).fetchall()
    return [
        RouteStop(
            sequence=row["seq"],
            stop=_stop_of(row),
            offset_seconds=row["offset_sec"],
        )
        for row in rows
    ]


def route_shape(
    connection: sqlite3.Connection, route_id: int
) -> list[list[float]] | None:
    """The street path of a route as [[lat, lon], ...], or None without one.

    An index from schema 2 has no shapes table, and keeps answering until the
    rebuild replaces it.
    """
    if not connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='shapes'"
    ).fetchone():
        return None
    row = connection.execute(
        "SELECT s.points FROM routes r JOIN shapes s ON s.shape_id = r.shape_id "
        "WHERE r.route_id = ?",
        (route_id,),
    ).fetchone()
    return decode_shape(row["points"]) if row else None


def scheduled_arrivals(
    connection: sqlite3.Connection,
    code: int,
    start: datetime,
    end: datetime,
    max_sec: int | None = None,
) -> list[Arrival]:
    """Timetabled arrivals as the card and the entities consume them."""
    arrivals = []
    for item in departures_at(connection, code, start, end, max_sec):
        row = item.row
        route = route_of(row)
        arrivals.append(
            Arrival(
                line_name=route.short_name or route.line_ref,
                eta=item.when,
                is_realtime=False,
                destination=route.destination,
                operator=route.agency,
                line_ref=route.line_ref,
                route_type=route.route_type,
                scheduled=item.when,
                origin=item.origin,
                operator_id=row["agency_id"] or None,
                dest_code=row["dest_code"],
            )
        )
    return arrivals
