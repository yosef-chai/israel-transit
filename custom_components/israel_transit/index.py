"""Home Assistant side of the GTFS index: refreshing it, and querying it.

Everything expensive -- the download, the parse, the SQLite writes and the
reads -- happens off the event loop. The download is async over Home
Assistant's own session; the blocking work runs in the executor. The SQL itself
lives in :mod:`.gtfs`, which has no Home Assistant dependency and is therefore
testable on its own.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sqlite3
import tempfile
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ISRAEL_TZ, Arrival, RouteInfo, RouteStop, Stop
from .const import DOMAIN, GTFS_DB_FILENAME, ISSUE_INDEX_FAILED
from .gtfs import (
    MEMBERS,
    FeedVersion,
    GtfsDownloader,
    GtfsError,
    activate_index,
    connect,
    get_stop,
    route_stops,
    routes_at_stop,
    scheduled_arrivals,
    schema_is_current,
    search_stops,
    stage_index,
    stored_stop_codes,
    stored_version,
)

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")

# קבוצת תחנות, או פונקציה שמחזירה אותה ברגע שהרענון באמת רץ.
type StopCodes = frozenset[int] | Callable[[], frozenset[int]]


class GtfsIndex:
    """The local copy of the Ministry feed, and the queries the card makes."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._downloader = GtfsDownloader(async_get_clientsession(hass))
        self._db_path = Path(hass.config.path(DOMAIN)) / GTFS_DB_FILENAME
        self._connection: sqlite3.Connection | None = None
        self._building = False
        self._lock = asyncio.Lock()
        # חיבור SQLite אחד משותף לכל ה-executor threads, ושתי שאילתות
        # במקביל עליו מחזירות שורות שבורות.
        self._db_lock = threading.Lock()
        self._task: asyncio.Task[bool] | None = None
        # נקרא פעם אחת בפתיחה, כדי שבדיקה אם תחנה כבר באינדקס לא תיגע ב-SQLite.
        self._indexed_stops: frozenset[int] = frozenset()
        self.last_build: dict[str, int] | None = None
        self.last_error: str | None = None

    @property
    def available(self) -> bool:
        return self._connection is not None

    @property
    def indexed_stops(self) -> frozenset[int]:
        """התחנות שלאינדקס הפתוח יש עבורן לוח זמנים של אוטובוסים."""
        return self._indexed_stops

    @property
    def building(self) -> bool:
        """Whether a rebuild is in flight, which closes the index for a while."""
        return self._building

    @property
    def build_task(self) -> asyncio.Task[bool] | None:
        """The refresh in flight, which a config flow can show progress for."""
        return None if self._task is None or self._task.done() else self._task

    @property
    def db_path(self) -> Path:
        return self._db_path

    # -- lifecycle ----------------------------------------------------------

    async def async_load(self) -> bool:
        """Open an existing index, if there is one and it is still readable."""
        if not self._db_path.exists():
            return False
        try:
            self._connection = await self._hass.async_add_executor_job(
                connect, self._db_path
            )
            current = await self._hass.async_add_executor_job(
                self._locked, schema_is_current, self._connection
            )
        except sqlite3.Error as err:
            _LOGGER.warning("Existing GTFS index is unusable (%s); rebuilding", err)
            # החיבור עשוי להיות פתוח והבדיקה שאחריו היא שנפלה, ולכן נסגר כאן
            # ולא רק נזנח.
            await self.async_close()
            return False
        if not current:
            # An upgrade changed the tables. Querying it would mean crashing on
            # a missing column, and rebuilding costs a few seconds.
            _LOGGER.info("GTFS index predates this version; rebuilding")
            await self.async_close()
            return False
        self._indexed_stops = await self._hass.async_add_executor_job(
            self._locked, stored_stop_codes, self._connection
        )
        return True

    async def async_close(self) -> None:
        self._indexed_stops = frozenset()
        if self._connection is not None:
            connection, self._connection = self._connection, None
            await self._hass.async_add_executor_job(self._locked, connection.close)

    def _locked(self, func: Callable[..., _T], *args: Any) -> _T:
        """מריץ פעולה על החיבור כשהוא לא בשימוש. חוסם, ולכן רק מתוך ה-executor."""
        with self._db_lock:
            return func(*args)

    @callback
    def async_schedule_refresh(
        self, stop_codes: StopCodes, force: bool = False
    ) -> asyncio.Task[bool]:
        """Refresh in the background, and hand back the task to wait on.

        Every refresh goes through here so that anything needing the index --
        a config flow above all -- can find the one in flight instead of
        concluding there is none and giving up.
        """
        self._task = self._hass.async_create_background_task(
            self.async_refresh(stop_codes, force), f"{DOMAIN}-gtfs-refresh"
        )
        return self._task

    async def async_refresh(self, stop_codes: StopCodes, force: bool = False) -> bool:
        """Rebuild the index if the feed changed, or if a stop was added.

        Bus timetables are only stored for the stops asked for -- indexing all
        of them would cost hundreds of megabytes for data SIRI already gives --
        so a stop added since the last build has none, and no amount of waiting
        for a new feed will give it any. Both are reasons to rebuild.

        Returns True when a rebuild happened. Concurrent calls queue rather
        than being dropped: a stop added while a rebuild runs would otherwise
        wait a whole day for its timetable. The one behind pays a single HEAD
        request to find the feed unchanged and its stop already indexed.

        ``stop_codes`` מתקבל גם כפונקציה, ואז הוא נקרא רק כשתורו של הרענון מגיע:
        שלוש תחנות שנוספו בזו אחר זו נכנסות לבנייה אחת במקום לשלוש, וכל בנייה
        עולה הורדה של 115MB וסריקה של 21 מיליון שורות.
        """
        async with self._lock:
            wanted = stop_codes() if callable(stop_codes) else stop_codes
            return await self._async_refresh(wanted, force)

    async def _async_refresh(self, stop_codes: frozenset[int], force: bool) -> bool:
        self._building = True
        try:
            version = await self._downloader.async_version()
            if not force and self._connection is not None:
                current, indexed = await self._hass.async_add_executor_job(
                    self._locked, self._stored_state
                )
                missing = stop_codes - indexed
                if current == version.token and not missing:
                    _LOGGER.debug("GTFS feed unchanged (%s)", version.token)
                    return False
                if missing:
                    _LOGGER.info(
                        "Rebuilding the GTFS index for %s newly configured stop(s): %s",
                        len(missing),
                        ", ".join(str(code) for code in sorted(missing)),
                    )
            await self._async_build(version, stop_codes)
            self.last_error = None
            ir.async_delete_issue(self._hass, DOMAIN, ISSUE_INDEX_FAILED)
            return True
        # מעבר ל-GtfsError: דיסק מלא, SQLite שבור או שורה בלי עמודה חובה. כולן
        # אותו כישלון מבחינת המשתמש, ובלי זה הן היו נבלעות במשימת הרקע.
        except (GtfsError, OSError, sqlite3.Error, KeyError, ValueError) as err:
            self.last_error = str(err) or type(err).__name__
            _LOGGER.error("GTFS index refresh failed: %s", self.last_error)
            if not self.available:
                # Without an index there is no timetable at all, so light rail,
                # the cable lines and rail have nothing to show. Worth telling
                # the user about rather than silently degrading.
                ir.async_create_issue(
                    self._hass,
                    DOMAIN,
                    ISSUE_INDEX_FAILED,
                    # repairs.py מריץ את הבנייה מתוך הדיאלוג עצמו.
                    is_fixable=True,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key=ISSUE_INDEX_FAILED,
                    translation_placeholders={"error": self.last_error},
                )
            return False
        finally:
            self._building = False

    def _stored_state(self) -> tuple[str | None, frozenset[int]]:
        """The feed token and the stops of the index currently open."""
        assert self._connection is not None
        return (
            stored_version(self._connection),
            stored_stop_codes(self._connection),
        )

    async def _async_build(
        self, version: FeedVersion, stop_codes: frozenset[int]
    ) -> None:
        members = await self._downloader.async_members(version.size)
        missing = [name for name in MEMBERS if name not in members]
        if missing:
            raise GtfsError(f"GTFS feed is missing {', '.join(missing)}")

        workdir = Path(
            await self._hass.async_add_executor_job(
                tempfile.mkdtemp, None, f"{DOMAIN}-"
            )
        )
        try:
            files: dict[str, Path] = {}
            downloaded = 0
            for name in MEMBERS:
                target = workdir / f"{name}.deflate"
                downloaded += await self._downloader.async_fetch_member(
                    members[name], target
                )
                files[name] = target
            _LOGGER.debug("Downloaded %.1f MB of GTFS members", downloaded / 1048576)

            # The index already in place stays open and answering all the
            # way through this: it is a separate file until the swap below.
            # Closing it here instead -- which is what this used to do -- left
            # every card and every stop without a timetable for the several
            # minutes a build takes, which is most of what adding a stop cost.
            stats = await self._hass.async_add_executor_job(
                stage_index, files, self._db_path, stop_codes, version.token
            )
            await self.async_close()
            await self._hass.async_add_executor_job(activate_index, self._db_path)
            self.last_build = stats
            _LOGGER.info(
                "Built GTFS index: %s stops, %s routes, %s pattern rows, "
                "%s timetabled departures from %s scanned rows (%.1f MB)",
                f"{stats['stops']:,}",
                f"{stats['routes']:,}",
                f"{stats['patterns']:,}",
                f"{stats['departures']:,}",
                f"{stats['stop_times_scanned']:,}",
                stats["db_bytes"] / 1048576,
            )
        finally:
            await self._hass.async_add_executor_job(shutil.rmtree, workdir, True)
            if self._connection is None:
                await self.async_load()

    # -- queries ------------------------------------------------------------

    async def _query(self, func: Callable[..., _T], *args: Any) -> _T:
        connection = self._connection
        if connection is None:
            raise GtfsError("the GTFS index is not built yet")
        try:
            return await self._hass.async_add_executor_job(
                self._locked, func, connection, *args
            )
        except sqlite3.Error as err:
            # A finished build swaps the file, so a read already on its way to
            # the executor can find this connection closed underneath it. That
            # is a gap of a moment in a local cache, and every caller already
            # copes with the index being unavailable. Crashing a WebSocket
            # command over it is not the right answer.
            raise GtfsError(f"the GTFS index was replaced mid-read: {err}") from err

    async def async_stop(self, code: int) -> Stop | None:
        return await self._query(get_stop, int(code))

    async def async_search(self, query: str, limit: int = 25) -> list[Stop]:
        return await self._query(search_stops, query, limit)

    async def async_routes_at_stop(self, code: int) -> list[RouteInfo]:
        return await self._query(routes_at_stop, int(code))

    async def async_route_stops(self, route_id: int) -> list[RouteStop]:
        return await self._query(route_stops, int(route_id))

    async def async_departures(
        self, code: int, now: datetime | None = None, hours: int = 3
    ) -> list[Arrival]:
        moment = (now or datetime.now(ISRAEL_TZ)).astimezone(ISRAEL_TZ)
        return await self._query(scheduled_arrivals, int(code), moment, hours)
