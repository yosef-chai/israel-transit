"""A local index of the Ministry of Transport GTFS feed.

The published feed is a 154 MB ZIP that expands to about 1 GB, which is far more
than is worth keeping. Three things make it cheap:

* The server honours HTTP range requests, so the ZIP central directory is read
  with three short reads and only the members we need are fetched. ``shapes.txt``
  alone is 57 MB of compressed data we never touch.
* ``stop_times.txt`` -- 86 MB compressed, 737 MB of CSV, 14.5 million rows -- is
  streamed and filtered as it arrives, never materialised.
* Only what real-time data cannot answer is stored: one representative stop
  pattern per route, and full timetables for the modes that publish nothing to
  SIRI (light rail, rail, the cable lines) plus the stops the user configured.
  That is a few hundred thousand rows rather than 14.5 million.

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
import re
import sqlite3
import struct
import zlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import aiohttp

from .api import (
    Arrival,
    IsraelTransitError,
    RouteInfo,
    RouteStop,
    Stop,
    line_sort_key,
)
from .const import GTFS_URL, NON_REALTIME_ROUTE_TYPES, USER_AGENT

_LOGGER = logging.getLogger(__name__)

# Members we read. shapes.txt (57 MB) and the fare tables are never fetched.
MEMBERS: Final = (
    "agency.txt",
    "routes.txt",
    "trips.txt",
    "stops.txt",
    "calendar.txt",
    "stop_times.txt",
)

# stop_desc looks like "רחוב: בן יהודה 74 עיר: כפר סבא רציף:  קומה: "
_CITY_RE: Final = re.compile(r"עיר:\s*(.*?)\s*(?:רציף:|קומה:|$)")
_STREET_RE: Final = re.compile(r"רחוב:\s*(.*?)\s*(?:עיר:|רציף:|קומה:|$)")

_ZIP64_MARK: Final = 0xFFFFFFFF

# Enough for "city street number"; past that the query is not a stop search.
_MAX_SEARCH_WORDS: Final = 4

# Bumped whenever the tables below change shape. An index built by an older
# version is discarded rather than queried, since a missing column is a crash
# and a rebuild is only a few seconds.
SCHEMA_VERSION: Final = 2

_SCHEMA: Final = """
CREATE TABLE stops (
    code INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT,
    lat REAL, lon REAL, street TEXT
);
CREATE TABLE routes (
    route_id INTEGER PRIMARY KEY, short_name TEXT, long_name TEXT,
    agency TEXT, route_type TEXT, headsign TEXT
);
CREATE TABLE patterns (
    route_id INTEGER NOT NULL, seq INTEGER NOT NULL,
    stop_code INTEGER NOT NULL, offset_sec INTEGER NOT NULL
);
CREATE TABLE departures (
    stop_code INTEGER NOT NULL, route_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL, arrival_sec INTEGER NOT NULL
);
CREATE TABLE calendar (
    service_id INTEGER PRIMARY KEY, days INTEGER NOT NULL,
    start_date INTEGER NOT NULL, end_date INTEGER NOT NULL
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
"""

_INDEXES: Final = """
CREATE INDEX idx_patterns_route ON patterns (route_id, seq);
CREATE INDEX idx_patterns_stop ON patterns (stop_code);
CREATE INDEX idx_departures_stop ON departures (stop_code, arrival_sec);
CREATE INDEX idx_calendar_window ON calendar (start_date, end_date);
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
        # Opening and writing are blocking calls, and this streams ~90 MB, so
        # every one of them is handed to a worker thread. The chunk is a whole
        # megabyte, which keeps the number of hops to about ninety.
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

    # route key (the GTFS string) -> (route_id, short, long, agency, type)
    routes: dict[str, tuple[int, str, str, str, str]] = {}
    for row in _member_rows(files["routes.txt"]):
        if not (row.get("route_id") or "").isdigit():
            continue
        routes[row["route_id"]] = (
            int(row["route_id"]),
            row.get("route_short_name", ""),
            row.get("route_long_name", ""),
            agencies.get(row.get("agency_id", ""), ""),
            row.get("route_type", ""),
        )
    stats["routes"] = len(routes)

    # One trip per route gives its stop pattern; every trip of a mode without
    # real-time gives its timetable.
    pattern_trips: dict[str, str] = {}  # trip_id -> route key
    timetable_trips: dict[str, tuple[str, int]] = {}  # trip_id -> (route key, service)
    headsigns: dict[str, str] = {}
    seen_routes: set[str] = set()
    for row in _member_rows(files["trips.txt"]):
        route_key = row.get("route_id", "")
        route = routes.get(route_key)
        if route is None:
            continue
        trip_id = row["trip_id"]
        if route_key not in seen_routes:
            seen_routes.add(route_key)
            pattern_trips[trip_id] = route_key
            headsigns[route_key] = row.get("trip_headsign", "")
        if route[4] in NON_REALTIME_ROUTE_TYPES:
            timetable_trips[trip_id] = (route_key, _int(row.get("service_id")))
    stats["pattern_trips"] = len(pattern_trips)
    stats["timetable_trips"] = len(timetable_trips)

    stops: dict[str, _StopRow] = {}
    stop_id_by_code: dict[int, str] = {}
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
        stop_id_by_code[code] = row["stop_id"]
    stats["stops"] = len(stops)

    wanted_stop_ids = {
        stop_id
        for code in extra_stop_codes
        if (stop_id := stop_id_by_code.get(code)) is not None
    }

    patterns: list[tuple[int, int, int, int]] = []
    departures: list[tuple[int, int, int, int]] = []
    # Rows at a configured stop belong to trips we know nothing about yet; their
    # routes are resolved with a second cheap pass over trips.txt afterwards.
    pending: list[tuple[str, int, int]] = []
    trip_start: dict[str, int] = {}
    scanned = 0

    lines = _member_lines(files["stop_times.txt"])
    next(lines, None)  # header
    for line in lines:
        scanned += 1
        trip_id = line[: line.find(",")]
        pattern_route = pattern_trips.get(trip_id)
        timetable = timetable_trips.get(trip_id)
        if pattern_route is None and timetable is None and not wanted_stop_ids:
            continue

        # trip_id,arrival_time,departure_time,stop_id,stop_sequence,...
        fields = line.split(",", 5)
        if len(fields) < 5:
            continue
        stop_id = fields[3]
        interesting_stop = stop_id in wanted_stop_ids
        if pattern_route is None and timetable is None and not interesting_stop:
            continue
        stop = stops.get(stop_id)
        if stop is None:
            continue
        arrival = _seconds(fields[1])
        if arrival is None:
            continue

        if pattern_route is not None:
            base = trip_start.setdefault(trip_id, arrival)
            patterns.append(
                (routes[pattern_route][0], _int(fields[4]), stop[0], arrival - base)
            )
        if timetable is not None:
            departures.append((stop[0], routes[timetable[0]][0], timetable[1], arrival))
        elif interesting_stop:
            pending.append((trip_id, stop[0], arrival))

    stats["stop_times_scanned"] = scanned

    if pending:
        wanted_trips = {trip_id for trip_id, _, _ in pending}
        resolved: dict[str, tuple[int, int]] = {}
        for row in _member_rows(files["trips.txt"]):
            trip_id = row.get("trip_id", "")
            if trip_id not in wanted_trips:
                continue
            if route := routes.get(row.get("route_id", "")):
                resolved[trip_id] = (route[0], _int(row.get("service_id")))
        for trip_id, stop_code, arrival in pending:
            if (entry := resolved.get(trip_id)) is not None:
                departures.append((stop_code, entry[0], entry[1], arrival))

    stats["patterns"] = len(patterns)
    stats["departures"] = len(departures)

    calendar_rows = [
        (
            _int(row["service_id"]),
            _day_mask(row),
            _int(row.get("start_date")),
            _int(row.get("end_date")),
        )
        for row in _member_rows(files["calendar.txt"])
        if (row.get("service_id") or "").isdigit()
    ]
    stats["calendar"] = len(calendar_rows)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = staged_path(db_path)
    tmp_path.unlink(missing_ok=True)
    connection = sqlite3.connect(tmp_path)
    try:
        connection.executescript("PRAGMA journal_mode=OFF;PRAGMA synchronous=OFF;")
        connection.executescript(_SCHEMA)
        connection.executemany(
            "INSERT OR REPLACE INTO stops VALUES (?,?,?,?,?,?)", list(stops.values())
        )
        connection.executemany(
            "INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?,?)",
            [
                (rid, short, long_name, agency, rtype, headsigns.get(key, ""))
                for key, (rid, short, long_name, agency, rtype) in routes.items()
            ],
        )
        connection.executemany("INSERT INTO patterns VALUES (?,?,?,?)", patterns)
        connection.executemany("INSERT INTO departures VALUES (?,?,?,?)", departures)
        connection.executemany(
            "INSERT OR REPLACE INTO calendar VALUES (?,?,?,?)", calendar_rows
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


def schema_is_current(connection: sqlite3.Connection) -> bool:
    """Whether this index was built by the current schema."""
    row = connection.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
    return bool(row) and row["value"] == str(SCHEMA_VERSION)


def service_day_bit(day: date) -> int:
    """The calendar bit for a weekday; GTFS weeks start on Sunday."""
    return 1 << ((day.weekday() + 1) % 7)


_DEPARTURES_SQL: Final = """
SELECT d.route_id, d.arrival_sec, r.short_name, r.long_name,
       r.agency, r.route_type, r.headsign
  FROM departures d
  JOIN routes r ON r.route_id = d.route_id
 WHERE d.stop_code = ?
   AND d.arrival_sec BETWEEN ? AND ?
   AND d.service_id IN (
       SELECT service_id FROM calendar
        WHERE (days & ?) != 0 AND start_date <= ? AND end_date >= ?)
 ORDER BY d.arrival_sec
 LIMIT 100
"""


def departures_at(
    connection: sqlite3.Connection, stop_code: int, now: datetime, hours: int = 3
) -> list[tuple[sqlite3.Row, datetime]]:
    """Timetabled departures in the next few hours, with absolute times.

    A trip that started yesterday and runs past midnight is stored with a time
    beyond 24:00, so yesterday's service day is queried as well.

    The active services stay inside the statement as a subquery: the feed has
    ~44k calendar rows and thousands are live on any given day, so lifting them
    into a Python list only to send them back as bind parameters is slower than
    letting SQLite join them.
    """
    results: list[tuple[sqlite3.Row, datetime]] = []
    for day_offset in (0, -1):
        day = (now + timedelta(days=day_offset)).date()
        midnight = datetime.combine(day, datetime.min.time(), tzinfo=now.tzinfo)
        start = int((now - midnight).total_seconds())
        stamp = int(day.strftime("%Y%m%d"))
        rows = connection.execute(
            _DEPARTURES_SQL,
            (
                stop_code,
                start,
                start + hours * 3600,
                service_day_bit(day),
                stamp,
                stamp,
            ),
        ).fetchall()
        results.extend(
            (row, midnight + timedelta(seconds=row["arrival_sec"])) for row in rows
        )
    results.sort(key=lambda item: item[1])
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
    rows = connection.execute(
        "SELECT DISTINCT r.route_id, r.short_name, r.long_name, r.agency, "
        "r.route_type, r.headsign FROM patterns p "
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


def scheduled_arrivals(
    connection: sqlite3.Connection, code: int, now: datetime, hours: int = 3
) -> list[Arrival]:
    """Timetabled arrivals as the card and the entities consume them."""
    arrivals = []
    for row, when in departures_at(connection, code, now, hours):
        route = route_of(row)
        arrivals.append(
            Arrival(
                line_name=route.short_name or route.line_ref,
                eta=when,
                is_realtime=False,
                destination=route.destination,
                operator=route.agency,
                line_ref=route.line_ref,
                route_type=route.route_type,
            )
        )
    return arrivals
