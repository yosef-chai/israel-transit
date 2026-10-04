"""Fetching selected members out of the remote archive.

The feed is 154 MB and only ~90 MB of it is wanted, so the downloader reads the
ZIP directory over byte ranges and then streams one member at a time. These
tests serve a real ZIP out of memory through a fake session, so the range
arithmetic and the local-header skip are exercised for real.
"""

from __future__ import annotations

import importlib
import io
import threading
import zipfile
from pathlib import Path

import aiohttp
import pytest
from conftest import PACKAGE

gtfs = importlib.import_module(f"{PACKAGE}.gtfs")

CONTENTS = {
    "agency.txt": b"agency_id,agency_name\n25,Tevel\n",
    "routes.txt": b"route_id,route_type\n34447,0\n",
    "stop_times.txt": b"trip_id,arrival_time\n" + b"tram-a,12:00:00\n" * 500,
    "shapes.txt": b"shape_id,lat\n" + b"1,32.0\n" * 2000,  # never fetched
}


def _archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in CONTENTS.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


class _Response:
    def __init__(self, status: int, body: bytes, headers: dict[str, str]) -> None:
        self.status = status
        self.headers = headers
        self._body = body

    async def __aenter__(self) -> _Response:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def read(self) -> bytes:
        return self._body

    @property
    def content(self) -> _Response:
        return self

    async def iter_chunked(self, size: int):
        for start in range(0, len(self._body), size):
            yield self._body[start : start + size]

    def __aiter__(self):
        return self


class _Session:
    """Serves byte ranges out of an in-memory archive, counting requests."""

    def __init__(self, archive: bytes, fail_with: int | None = None) -> None:
        self.archive = archive
        self.fail_with = fail_with
        self.requests: list[tuple[int, int]] = []

    def get(self, url: str, headers: dict[str, str], timeout: object = None):
        if self.fail_with is not None:
            return _Response(self.fail_with, b"", {})
        first, last = headers["Range"].removeprefix("bytes=").split("-")
        start, end = int(first), int(last)
        self.requests.append((start, end))
        body = self.archive[start : end + 1]
        return _Response(
            206,
            body,
            {"Content-Range": f"bytes {start}-{end}/{len(self.archive)}"},
        )


@pytest.fixture
def archive() -> bytes:
    return _archive()


async def test_the_feed_version_identifies_a_publication(archive: bytes) -> None:
    session = _Session(archive)
    version = await gtfs.GtfsDownloader(session, "http://feed").async_version()

    assert version.size == len(archive)
    assert version.token.endswith(str(len(archive)))


async def test_a_feed_that_refuses_ranges_is_an_error(archive: bytes) -> None:
    class NoRanges(_Session):
        def get(self, url, headers, timeout=None):
            return _Response(200, b"", {})  # no Content-Range

    with pytest.raises(gtfs.GtfsError, match="range requests"):
        await gtfs.GtfsDownloader(NoRanges(archive), "http://feed").async_version()


async def test_an_http_error_is_reported_not_swallowed(archive: bytes) -> None:
    session = _Session(archive, fail_with=503)
    with pytest.raises(gtfs.GtfsError, match="503"):
        await gtfs.GtfsDownloader(session, "http://feed").async_version()


async def test_the_directory_is_read_with_a_couple_of_short_requests(
    archive: bytes,
) -> None:
    session = _Session(archive)
    downloader = gtfs.GtfsDownloader(session, "http://feed")

    members = await downloader.async_members(len(archive))

    assert set(members) == set(CONTENTS)
    assert members["stop_times.txt"].file_size == len(CONTENTS["stop_times.txt"])
    # The point of the exercise: a handful of bounded reads, never the whole
    # archive. Each one is capped by the 64 KB tail window, which is why the
    # real 154 MB feed costs about a kilobyte to enumerate.
    assert len(session.requests) <= 3
    assert all(end - start + 1 <= 65536 + 22 for start, end in session.requests)


async def test_fetching_a_member_yields_exactly_its_bytes(
    archive: bytes, tmp_path: Path
) -> None:
    session = _Session(archive)
    downloader = gtfs.GtfsDownloader(session, "http://feed")
    members = await downloader.async_members(len(archive))

    target = tmp_path / "stop_times.deflate"
    written = await downloader.async_fetch_member(members["stop_times.txt"], target)

    assert written == members["stop_times.txt"].compress_size
    # The saved bytes are a raw deflate stream: inflating them must give the
    # original member back, which proves the local header was skipped correctly.
    raw = target.read_bytes()
    inflated = b"".join(gtfs.inflate([raw]))
    assert inflated == CONTENTS["stop_times.txt"]


async def test_only_the_wanted_members_are_downloaded(
    archive: bytes, tmp_path: Path
) -> None:
    """shapes.txt is 57 MB in the real feed and must never be touched."""
    session = _Session(archive)
    downloader = gtfs.GtfsDownloader(session, "http://feed")
    members = await downloader.async_members(len(archive))
    session.requests.clear()

    wanted = ("agency.txt", "routes.txt")
    for name in wanted:
        await downloader.async_fetch_member(members[name], tmp_path / name)

    # Exactly the two members, plus a 30-byte local-header probe for each.
    fetched = sum(end - start + 1 for start, end in session.requests)
    assert fetched == sum(members[n].compress_size for n in wanted) + 2 * 30

    # And nothing read overlaps the bytes belonging to shapes.txt.
    shapes = members["shapes.txt"]
    body_start = shapes.header_offset + 30 + len("shapes.txt")
    body_end = body_start + shapes.compress_size
    assert not any(
        start < body_end and end >= body_start for start, end in session.requests
    )


async def test_a_member_that_errors_midway_is_reported(
    archive: bytes, tmp_path: Path
) -> None:
    session = _Session(archive)
    downloader = gtfs.GtfsDownloader(session, "http://feed")
    members = await downloader.async_members(len(archive))
    session.fail_with = 500

    with pytest.raises(gtfs.GtfsError, match="500"):
        await downloader.async_fetch_member(members["agency.txt"], tmp_path / "a")


async def test_a_network_failure_becomes_a_gtfs_error(tmp_path: Path) -> None:
    class Broken:
        def get(self, url, headers, timeout=None):
            raise aiohttp.ClientError("connection reset")

    with pytest.raises(gtfs.GtfsError, match="unreachable"):
        await gtfs.GtfsDownloader(Broken(), "http://feed").async_version()


class _TimesOut:
    """A request that never answers within its ClientTimeout.

    aiohttp raises plain TimeoutError for that, which is not a ClientError;
    on a slow link it is the most likely failure of the 86 MB member.
    """

    def get(self, url, headers, timeout=None):
        return self

    async def __aenter__(self):
        raise TimeoutError

    async def __aexit__(self, *exc: object) -> bool:
        return False


async def test_a_timed_out_version_check_becomes_a_gtfs_error() -> None:
    with pytest.raises(gtfs.GtfsError, match="unreachable"):
        await gtfs.GtfsDownloader(_TimesOut(), "http://feed").async_version()


async def test_a_timed_out_member_becomes_a_gtfs_error(
    archive: bytes, tmp_path: Path
) -> None:
    members = await gtfs.GtfsDownloader(_Session(archive), "http://feed").async_members(
        len(archive)
    )
    with pytest.raises(gtfs.GtfsError):
        await gtfs.GtfsDownloader(_TimesOut(), "http://feed").async_fetch_member(
            members["agency.txt"], tmp_path / "a"
        )


async def test_the_download_never_writes_on_the_event_loop(
    archive: bytes, tmp_path: Path
) -> None:
    """Home Assistant's loop protection catches this, and rightly.

    A member is up to 86 MB; opening the file and writing every chunk of it on
    the event loop stalls everything else in Home Assistant for the duration.
    """
    session = _Session(archive)
    downloader = gtfs.GtfsDownloader(session)
    members = await downloader.async_members(len(archive))

    loop_thread = threading.current_thread()
    used: list[threading.Thread] = []
    real_open = Path.open

    def spy(self: Path, *args: object, **kwargs: object) -> object:
        used.append(threading.current_thread())
        return real_open(self, *args, **kwargs)

    Path.open = spy  # type: ignore[method-assign]
    try:
        await downloader.async_fetch_member(
            members["stop_times.txt"], tmp_path / "stop_times.deflate"
        )
    finally:
        Path.open = real_open  # type: ignore[method-assign]

    assert used, "the member was never written"
    assert all(thread is not loop_thread for thread in used)
