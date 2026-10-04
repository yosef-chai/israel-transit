"""The GTFS index as Home Assistant drives it: loading, querying, refreshing.

Unlike the rest of the Home Assistant tests these use a real index built from
the miniature feed, so the executor plumbing and the SQL are exercised together.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from gtfs_fixture import write_feed
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.israel_transit import gtfs
from custom_components.israel_transit.const import (
    DOMAIN,
    GTFS_DB_FILENAME,
    ISSUE_INDEX_FAILED,
)
from custom_components.israel_transit.gtfs import (
    MEMBERS,
    GtfsError,
    ZipMember,
    build_index,
    stored_stop_codes,
)
from custom_components.israel_transit.index import GtfsIndex

IL = timezone(timedelta(hours=3))


@pytest.fixture
async def built_index(hass: HomeAssistant, tmp_path: Path):
    """A GtfsIndex backed by a real, freshly built database.

    Closed afterwards: on Windows an open sqlite connection stops the next
    test from replacing the file, and under coverage nothing else closes it.
    """
    index = GtfsIndex(hass)
    db_path = Path(hass.config.path(DOMAIN)) / GTFS_DB_FILENAME
    db_path.parent.mkdir(parents=True, exist_ok=True)
    build_index(write_feed(tmp_path), db_path, frozenset({21023}), "v1")
    yield index
    await index.async_close()


async def test_an_existing_index_is_opened(built_index: GtfsIndex) -> None:
    assert await built_index.async_load() is True
    assert built_index.available is True


async def test_an_index_from_an_older_schema_is_refused(
    built_index: GtfsIndex,
) -> None:
    """Otherwise the first query crashes on a column that is not there."""
    writable = sqlite3.connect(built_index.db_path)
    writable.execute("UPDATE meta SET value='0' WHERE key='schema'")
    writable.commit()
    writable.close()

    assert await built_index.async_load() is False
    assert built_index.available is False


async def test_a_missing_index_is_not_an_error(hass: HomeAssistant) -> None:
    """First run, before anything has been downloaded."""
    index = GtfsIndex(hass)
    index.db_path.unlink(missing_ok=True)

    assert await index.async_load() is False
    assert index.available is False


async def test_queries_before_the_index_exists_are_refused(
    hass: HomeAssistant,
) -> None:
    """The coordinator catches this and falls back to real-time alone."""
    index = GtfsIndex(hass)
    with pytest.raises(GtfsError, match="not built"):
        await index.async_stop(21023)


async def test_the_index_answers_every_query_the_card_makes(
    built_index: GtfsIndex,
) -> None:
    await built_index.async_load()

    stop = await built_index.async_stop(35962)
    assert stop is not None and stop.name == "הקוממיות" and stop.city == "בת ים"

    assert [s.code for s in await built_index.async_search("קוממיות")] == [35962]

    routes = await built_index.async_routes_at_stop(35962)
    assert {r.route_id for r in routes} == {34447, 34448, 960}

    pattern = await built_index.async_route_stops(34447)
    assert [p.stop.code for p in pattern] == [35962, 36307, 21023]
    assert [p.offset_seconds for p in pattern] == [0, 480, 1320]

    noon = datetime(2026, 8, 30, 11, 30, tzinfo=IL)  # a Sunday
    departures = await built_index.async_departures(35962, noon, hours=2)
    assert [d.eta.strftime("%H:%M") for d in departures] == ["12:00", "12:30"]
    assert all(d.is_realtime is False for d in departures)


async def test_closing_releases_the_database(built_index: GtfsIndex) -> None:
    await built_index.async_load()
    await built_index.async_close()

    assert built_index.available is False
    with pytest.raises(GtfsError):
        await built_index.async_stop(35962)


async def test_an_unchanged_feed_is_not_rebuilt(built_index: GtfsIndex) -> None:
    """The whole point of storing the feed version with the index."""
    await built_index.async_load()
    with patch.object(
        built_index, "_downloader", **{"async_version": AsyncMock()}
    ) as downloader:
        downloader.async_version.return_value.token = "v1"
        rebuilt = await built_index.async_refresh(frozenset())

    assert rebuilt is False


async def test_a_failed_build_raises_a_repair_issue(
    hass: HomeAssistant, issue_registry: ir.IssueRegistry
) -> None:
    """Losing the index silently removes light rail and rail from the card."""
    index = GtfsIndex(hass)
    with patch.object(
        index,
        "_downloader",
        **{"async_version": AsyncMock(side_effect=GtfsError("feed unreachable"))},
    ):
        assert await index.async_refresh(frozenset()) is False

    assert index.last_error == "feed unreachable"
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_INDEX_FAILED) is not None


@pytest.mark.parametrize(
    "error",
    [
        OSError(28, "No space left on device"),
        sqlite3.OperationalError("database or disk is full"),
        KeyError("trip_id"),
    ],
)
async def test_any_failure_mid_build_is_reported_and_fixable(
    hass: HomeAssistant, issue_registry: ir.IssueRegistry, error: Exception
) -> None:
    """Not only feed errors: a full disk or a malformed row fails a build too.

    Left uncaught they ended the background task with nothing recorded -- no
    error for diagnostics, no issue, and a config flow waiting on a build that
    had already died.
    """
    index = GtfsIndex(hass)
    index.db_path.unlink(missing_ok=True)
    with (
        patch.object(index, "_downloader", **{"async_version": AsyncMock()}),
        patch.object(index, "_async_build", side_effect=error),
    ):
        assert await index.async_refresh(frozenset()) is False

    assert index.last_error
    assert index.building is False
    issue = issue_registry.async_get_issue(DOMAIN, ISSUE_INDEX_FAILED)
    assert issue is not None
    assert issue.is_fixable is True
    assert issue.translation_placeholders == {"error": index.last_error}


async def test_the_repair_issue_clears_once_a_build_succeeds(
    hass: HomeAssistant, tmp_path: Path, issue_registry: ir.IssueRegistry
) -> None:
    index = GtfsIndex(hass)
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_INDEX_FAILED,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_INDEX_FAILED,
    )

    files = write_feed(tmp_path)

    async def fake_build(version, stop_codes):
        build_index(files, index.db_path, stop_codes, version.token)
        await index.async_load()

    with (
        patch.object(index, "_downloader", **{"async_version": AsyncMock()}),
        patch.object(index, "_async_build", side_effect=fake_build),
    ):
        index._downloader.async_version.return_value.token = "v2"
        assert await index.async_refresh(frozenset()) is True

    assert issue_registry.async_get_issue(DOMAIN, ISSUE_INDEX_FAILED) is None
    await index.async_close()


async def test_a_second_refresh_queues_behind_the_first(
    hass: HomeAssistant,
) -> None:
    """A stop added mid-rebuild must not wait a day for its timetable.

    Refreshes used to return early while another was running, which threw away
    the very ask that carried the newly configured stop. They serialise now:
    the one behind re-checks afterwards and usually finds nothing to do.
    """
    index = GtfsIndex(hass)
    order: list[str] = []
    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_refresh(stop_codes: frozenset[int], force: bool) -> bool:
        order.append(f"start {sorted(stop_codes)}")
        started.set()
        await release.wait()
        order.append(f"done {sorted(stop_codes)}")
        return True

    with patch.object(index, "_async_refresh", side_effect=fake_refresh):
        first = index.async_schedule_refresh(frozenset({21023}))
        await started.wait()
        second = index.async_schedule_refresh(frozenset({20092}))
        # What a config flow waits on is the latest ask, and the lock makes
        # waiting for it wait for everything before it.
        assert index.build_task is second
        release.set()
        assert await first is True
        assert await second is True

    assert order == [
        "start [21023]",
        "done [21023]",
        "start [20092]",
        "done [20092]",
    ]
    assert index.build_task is None


async def test_a_full_refresh_downloads_the_members_and_builds_the_index(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    """The whole path: directory, per-member download, executor build, reload."""
    index = GtfsIndex(hass)
    index.db_path.unlink(missing_ok=True)
    feed = write_feed(tmp_path)

    members = {
        name: ZipMember(name, feed[name].stat().st_size, 0, 0) for name in MEMBERS
    }
    fetched: list[str] = []

    async def fake_fetch(member: ZipMember, target: Path) -> int:
        fetched.append(member.name)
        target.write_bytes(feed[member.name].read_bytes())
        return member.compress_size

    with patch.object(
        index,
        "_downloader",
        **{
            "async_version": AsyncMock(),
            "async_members": AsyncMock(return_value=members),
            "async_fetch_member": AsyncMock(side_effect=fake_fetch),
        },
    ):
        index._downloader.async_version.return_value.token = "v9"
        index._downloader.async_version.return_value.size = 1234
        assert await index.async_refresh(frozenset({21023})) is True

    assert sorted(fetched) == sorted(MEMBERS)
    assert index.available is True
    assert index.last_build is not None
    assert index.last_build["stops"] == 4
    assert index.last_error is None

    # And it is genuinely queryable afterwards.
    stop = await index.async_stop(35962)
    assert stop is not None and stop.name == "הקוממיות"
    await index.async_close()


async def test_a_feed_missing_a_member_is_refused(
    hass: HomeAssistant, issue_registry: ir.IssueRegistry
) -> None:
    """A truncated publication must not produce a half-built index."""
    index = GtfsIndex(hass)
    index.db_path.unlink(missing_ok=True)

    with patch.object(
        index,
        "_downloader",
        **{
            "async_version": AsyncMock(),
            "async_members": AsyncMock(return_value={"agency.txt": None}),
        },
    ):
        assert await index.async_refresh(frozenset()) is False

    assert index.last_error is not None
    assert "stop_times.txt" in index.last_error
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_INDEX_FAILED) is not None


@pytest.fixture
async def built_for(hass: HomeAssistant, tmp_path: Path):
    """Build an index for a given set of stops, and close it afterwards.

    Closing matters on Windows, where an open sqlite connection stops the next
    test from unlinking the file.
    """
    opened: list[GtfsIndex] = []

    async def _build(codes: frozenset[int]) -> tuple[GtfsIndex, dict[str, Path]]:
        index = GtfsIndex(hass)
        for previous in opened:
            await previous.async_close()
        index.db_path.unlink(missing_ok=True)
        files = write_feed(tmp_path)
        build_index(files, index.db_path, codes, "v1")
        await index.async_load()
        opened.append(index)
        return index, files

    yield _build

    for index in opened:
        await index.async_close()


async def test_an_unchanged_feed_and_the_same_stops_do_not_rebuild(built_for) -> None:
    index, _ = await built_for(frozenset({21023}))

    with patch.object(index, "_downloader", **{"async_version": AsyncMock()}):
        index._downloader.async_version.return_value.token = "v1"
        assert await index.async_refresh(frozenset({21023})) is False


async def test_a_newly_configured_stop_rebuilds_an_otherwise_current_index(
    built_for,
) -> None:
    """The feed never changes when a stop is added, so nothing else notices.

    Regression: bus timetables are only stored for the stops the build is told
    about, and adding one used to leave the index exactly as it was -- so the
    documented fallback for a stop curlbus cannot answer never appeared.
    """
    index, files = await built_for(frozenset({21023}))

    async def fake_build(version, stop_codes):
        # The real _async_build closes the reader first, because the finished
        # index replaces the file it is holding open.
        await index.async_close()
        build_index(files, index.db_path, stop_codes, version.token)
        await index.async_load()

    with (
        patch.object(index, "_downloader", **{"async_version": AsyncMock()}),
        patch.object(index, "_async_build", side_effect=fake_build),
    ):
        index._downloader.async_version.return_value.token = "v1"  # unchanged
        assert await index.async_refresh(frozenset({21023, 35962})) is True

    assert stored_stop_codes(index._connection) == frozenset({21023, 35962})


async def test_dropping_a_stop_does_not_force_a_rebuild(built_for) -> None:
    """The extra timetable is harmless; re-downloading 90 MB to remove it is not."""
    index, _ = await built_for(frozenset({21023, 35962}))

    with patch.object(index, "_downloader", **{"async_version": AsyncMock()}):
        index._downloader.async_version.return_value.token = "v1"
        assert await index.async_refresh(frozenset({21023})) is False


async def test_an_index_from_before_this_was_recorded_rebuilds_once(built_for) -> None:
    """Existing installs have no record of what they indexed; assume nothing."""
    index, files = await built_for(frozenset({21023}))
    await index.async_close()
    writable = sqlite3.connect(index.db_path)
    writable.execute("DELETE FROM meta WHERE key='stops'")
    writable.commit()
    writable.close()
    await index.async_load()

    async def fake_build(version, stop_codes):
        # The real _async_build closes the reader first, because the finished
        # index replaces the file it is holding open.
        await index.async_close()
        build_index(files, index.db_path, stop_codes, version.token)
        await index.async_load()

    with (
        patch.object(index, "_downloader", **{"async_version": AsyncMock()}),
        patch.object(index, "_async_build", side_effect=fake_build),
    ):
        index._downloader.async_version.return_value.token = "v1"
        assert await index.async_refresh(frozenset({21023})) is True


# --- the index answers all the way through a rebuild ------------------------


async def test_the_index_keeps_answering_while_a_rebuild_runs(
    hass: HomeAssistant, tmp_path: Path, built_index: GtfsIndex
) -> None:
    """A build used to close the reader before it started.

    Regression: every card and every stop lost its timetable for the several
    minutes a build takes, which is most of what adding a stop cost -- and
    a read caught by the close crashed with sqlite3.InterfaceError, which
    reached the frontend as an unhandled WebSocket error.
    """
    assert await built_index.async_load() is True
    feed = write_feed(tmp_path)
    members = {
        name: ZipMember(name, feed[name].stat().st_size, 0, 0) for name in MEMBERS
    }
    staging = asyncio.Event()
    release = asyncio.Event()

    async def fake_fetch(member: ZipMember, target: Path) -> int:
        target.write_bytes(feed[member.name].read_bytes())
        return member.compress_size

    real_stage = gtfs.stage_index

    def blocking_stage(*args: object, **kwargs: object) -> dict[str, int]:
        hass.loop.call_soon_threadsafe(staging.set)
        asyncio.run_coroutine_threadsafe(release.wait(), hass.loop).result(10)
        return real_stage(*args, **kwargs)  # type: ignore[arg-type]

    with (
        patch.object(
            built_index,
            "_downloader",
            **{
                "async_version": AsyncMock(),
                "async_members": AsyncMock(return_value=members),
                "async_fetch_member": AsyncMock(side_effect=fake_fetch),
            },
        ),
        patch("custom_components.israel_transit.index.stage_index", blocking_stage),
    ):
        built_index._downloader.async_version.return_value.token = "v2"
        built_index._downloader.async_version.return_value.size = 1234
        task = built_index.async_schedule_refresh(frozenset({21023}))

        await staging.wait()
        assert built_index.building is True
        # The whole point: still open, still answering, mid-build.
        assert built_index.available is True
        assert (await built_index.async_stop(21023)) is not None
        release.set()
        assert await task is True

    assert built_index.available is True
    assert (await built_index.async_stop(21023)) is not None


async def test_a_read_caught_by_the_swap_is_an_index_error_not_a_crash(
    built_index: GtfsIndex,
) -> None:
    """The swap closes the reader, and a read already on its way finds it shut.

    sqlite3 raises InterfaceError there, which is not an IsraelTransitError and
    so escaped every caller's handling.
    """
    assert await built_index.async_load() is True

    def close_then_query(connection: sqlite3.Connection, code: int) -> object:
        connection.close()
        return gtfs.get_stop(connection, code)

    with pytest.raises(GtfsError):
        await built_index._query(close_then_query, 21023)
