"""תמונת ה-SIRI של הסדנא: פענוח, הגנה מקבצים מנופחים, והלקוח שמוריד אותה.

הביקורים כאן הם העתק מקוצץ של תמונה אמיתית מ-27.11.2026 08:23Z, ועוד מקרים
שבורים שנבנו לפי מה שנמדד בה (קואורדינטה 0, מרחק 0 באמצע נסיעה, רכב כפול).
"""

from __future__ import annotations

import asyncio
import importlib
import json
from datetime import datetime

import pytest
from conftest import PACKAGE

brotli = pytest.importorskip("brotli")
open_bus = importlib.import_module(f"{PACKAGE}.open_bus")
api = importlib.import_module(f"{PACKAGE}.api")

NOW = datetime.fromisoformat("2026-11-27T10:23:00+02:00").timestamp()


def visit(
    line="3266",
    origin="2026-11-27T09:00:00+02:00",
    recorded="2026-11-27T10:22:04+02:00",
    order="58",
    dist="21950",
    lat="32.02993",
    lon="34.797913",
    vehicle="18340504",
    journey="25317845",
):
    journey_doc = {
        "LineRef": line,
        "FramedVehicleJourneyRef": {
            "DataFrameRef": "2026-11-27",
            "DatedVehicleJourneyRef": journey,
        },
        "OperatorRef": "3",
        "OriginAimedDepartureTime": origin,
        "VehicleLocation": {"Longitude": lon, "Latitude": lat},
        "VehicleRef": vehicle,
        "MonitoredCall": {
            "StopPointRef": "35780",
            "Order": order,
            "DistanceFromStop": dist,
        },
    }
    return {"RecordedAtTime": recorded, "MonitoredVehicleJourney": journey_doc}


def snapshot_doc(visits, status="true", taken="2026-11-27T10:23:00+02:00"):
    delivery = {"ResponseTimestamp": taken, "Status": status}
    if visits is not None:
        delivery["StopMonitoringDelivery"] = [
            {"Status": "true", "MonitoredStopVisit": visits}
        ]
    return {"Siri": {"ServiceDelivery": delivery}}


def packed(doc) -> bytes:
    return brotli.compress(json.dumps(doc).encode())


def parse(visits, **kwargs):
    return open_bus.parse_open_bus(packed(snapshot_doc(visits, **kwargs)), NOW)


# --- פענוח ---------------------------------------------------------------------


def test_a_real_visit_becomes_a_vehicle_on_its_line():
    snap = parse([visit()])
    [bus] = snap.by_line["3266"]
    assert (bus.order, bus.dist, bus.vehicle_ref, bus.journey_ref) == (
        58,
        21950,
        "18340504",
        25317845,
    )
    assert bus.origin == int(
        datetime.fromisoformat("2026-11-27T09:00:00+02:00").timestamp()
    )
    assert (snap.seen, snap.dropped) == (1, 0)


def test_broken_visits_are_dropped_and_counted():
    snap = parse(
        [
            visit(line=""),
            visit(origin="junk"),
            visit(recorded="2026-11-27T10:22:04"),  # בלי אזור זמן
            visit(recorded="2026-11-27T10:28:00+02:00"),  # 5 דק' בעתיד
            visit(recorded="2026-11-27T10:10:00+02:00"),  # 13 דק' ישן
            {"RecordedAtTime": "2026-11-27T10:22:04+02:00"},
            "not a visit",
        ]
    )
    assert (snap.seen, snap.dropped, snap.by_line) == (7, 7, {})


def test_a_zero_distance_mid_trip_is_no_position_but_at_the_origin_is_real():
    snap = parse(
        [
            visit(order="40", dist="0", vehicle="a"),
            visit(order="1", dist="0", vehicle="b"),
        ]
    )
    dists = {bus.vehicle_ref: bus.dist for bus in snap.by_line["3266"]}
    assert dists == {"a": None, "b": 0}


def test_a_zero_distance_without_order_is_no_position():
    [bus] = parse([visit(order="", dist="0")]).by_line["3266"]
    assert (bus.order, bus.dist) == (None, None)


@pytest.mark.parametrize(("lat", "lon"), [("0", "0"), ("40.7", "-74.0"), ("x", "34.8")])
def test_a_position_outside_israel_is_dropped_but_the_vehicle_kept(lat, lon):
    [bus] = parse([visit(lat=lat, lon=lon)]).by_line["3266"]
    assert (bus.lat, bus.lon) == (None, None)


def test_the_same_vehicle_twice_keeps_the_newer_report():
    snap = parse(
        [
            visit(recorded="2026-11-27T10:21:00+02:00", dist="100"),
            visit(recorded="2026-11-27T10:22:30+02:00", dist="900"),
        ]
    )
    assert [bus.dist for bus in snap.by_line["3266"]] == [900]


def test_relief_buses_on_the_same_departure_are_both_kept():
    snap = parse([visit(vehicle="a"), visit(vehicle="b")])
    assert sorted(bus.vehicle_ref for bus in snap.by_line["3266"]) == ["a", "b"]


def test_a_single_visit_object_is_read_like_a_list():
    doc = snapshot_doc([visit()])
    doc["Siri"]["ServiceDelivery"]["StopMonitoringDelivery"][0][
        "MonitoredStopVisit"
    ] = visit()
    assert len(open_bus.parse_open_bus(packed(doc), NOW).by_line["3266"]) == 1


def test_an_empty_night_snapshot_is_valid():
    assert parse(None).by_line == {}
    assert parse([]).by_line == {}


def test_a_failed_request_is_unavailable():
    with pytest.raises(api.RealtimeUnavailable):
        parse([visit()], status="false")


def test_a_snapshot_without_a_timestamp_is_unavailable():
    with pytest.raises(api.RealtimeUnavailable):
        parse([visit()], taken="2026-11-27T10:23:00")


@pytest.mark.parametrize(
    "raw",
    [
        b"not brotli at all",
        packed(snapshot_doc([visit()]))[:-20],
        brotli.compress(b"{nope"),
    ],
)
def test_broken_truncated_or_unreadable_files_are_unavailable(raw):
    with pytest.raises(api.RealtimeUnavailable):
        open_bus.parse_open_bus(raw, NOW)


def test_a_decompression_bomb_stops_at_the_limit():
    bomb = brotli.compress(b"\0" * (8 * 1024 * 1024))
    assert len(bomb) < 1024
    with pytest.raises(api.RealtimeUnavailable, match="larger"):
        open_bus.decompress(bomb, limit=1024 * 1024)
    # מה שבתוך התקרה נפרס במלואו, גם כשהוא גדול מחתיכה אחת.
    assert len(open_bus.decompress(bomb, limit=16 * 1024 * 1024)) == 8 * 1024 * 1024


@pytest.mark.parametrize(
    "payload",
    [
        {
            "last_snapshot_id": "../../etc/passwd",
            "last_datetime_utc": "2026-11-27 08:23:00",
        },
        {"last_snapshot_id": "", "last_datetime_utc": "2026-11-27 08:23:00"},
        {"last_snapshot_id": "2026/11/27/08/23", "last_datetime_utc": "junk"},
        ["not", "an", "object"],
    ],
)
def test_a_bad_status_is_rejected_before_any_url_is_built(payload):
    with pytest.raises(api.RealtimeUnavailable):
        open_bus.parse_status(payload)


def test_the_status_time_is_utc():
    snapshot_id, written = open_bus.parse_status(
        {
            "last_snapshot_id": "2026/11/27/08/23",
            "last_datetime_utc": "2026-11-27 08:23:11",
        }
    )
    assert snapshot_id == "2026/11/27/08/23"
    assert written == datetime.fromisoformat("2026-11-27T08:23:11+00:00").timestamp()


# --- הלקוח ---------------------------------------------------------------------


class _Content:
    def __init__(self, body: bytes) -> None:
        self._body = body

    async def iter_chunked(self, size):
        for start in range(0, len(self._body), size):
            yield self._body[start : start + size]


class _Response:
    def __init__(self, status: int, body: bytes = b"", headers=None) -> None:
        self.status = status
        self.headers = headers or {}
        self.content = _Content(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _Server:
    """שרת מזויף: status אחד שאפשר להחליף, וקבצי .br לפי שם."""

    def __init__(self) -> None:
        self.status = {
            "last_snapshot_id": "2026/11/27/08/23",
            "last_datetime_utc": "2026-11-27 08:23:01",
        }
        self.files: dict[str, _Response] = {
            "2026/11/27/08/23.br": _Response(200, packed(snapshot_doc([visit()])))
        }
        self.requests: list[str] = []
        self.status_response: _Response | None = None

    def get(self, url, **kwargs):
        path = url.split(".hasadna.org.il/", 1)[1]
        self.requests.append(path)
        if path == "daemon_status.json":
            return self.status_response or _Response(
                200, json.dumps(self.status).encode()
            )
        return self.files.get(path, _Response(404))

    def downloads(self):
        return [path for path in self.requests if path.endswith(".br")]


class _Clocks:
    def __init__(self, monkeypatch) -> None:
        self.mono = 1000.0
        self.wall = NOW + 10
        monkeypatch.setattr(open_bus, "monotonic", lambda: self.mono)
        monkeypatch.setattr(open_bus.time, "time", lambda: self.wall)
        monkeypatch.setattr(open_bus.random, "uniform", lambda a, b: 0.0)

    def advance(self, seconds: float) -> None:
        self.mono += seconds
        self.wall += seconds


async def _run_sync(func, *args):
    return func(*args)


def _client(server):
    return open_bus.OpenBusClient(server, _run_sync)


@pytest.mark.asyncio
async def test_a_snapshot_is_downloaded_once_and_reused(monkeypatch):
    clocks = _Clocks(monkeypatch)
    server = _Server()
    client = _client(server)

    first = await client.async_snapshot()
    clocks.advance(30)
    assert await client.async_snapshot() is first
    assert server.requests == ["daemon_status.json", "2026/11/27/08/23.br"]


@pytest.mark.asyncio
async def test_concurrent_stops_share_one_download(monkeypatch):
    _Clocks(monkeypatch)
    server = _Server()
    client = _client(server)
    results = await asyncio.gather(*(client.async_snapshot() for _ in range(5)))
    assert len({id(r) for r in results}) == 1
    assert server.downloads() == ["2026/11/27/08/23.br"]


@pytest.mark.asyncio
async def test_after_a_new_snapshot_the_status_waits_50s_then_15s(monkeypatch):
    clocks = _Clocks(monkeypatch)
    server = _Server()
    client = _client(server)
    await client.async_snapshot()
    clocks.advance(49)
    await client.async_snapshot()
    assert server.requests.count("daemon_status.json") == 1
    clocks.advance(2)
    await client.async_snapshot()  # אותו id: לא מורידים, ובודקים שוב בעוד 15 שנ'
    assert server.requests.count("daemon_status.json") == 2
    clocks.advance(14)
    await client.async_snapshot()
    assert server.requests.count("daemon_status.json") == 2
    clocks.advance(2)
    await client.async_snapshot()
    assert server.requests.count("daemon_status.json") == 3
    assert len(server.downloads()) == 1


@pytest.mark.asyncio
async def test_a_frozen_daemon_is_not_trusted_past_240s(monkeypatch):
    clocks = _Clocks(monkeypatch)
    server = _Server()
    client = _client(server)
    await client.async_snapshot()
    clocks.advance(250)
    with pytest.raises(api.RealtimeUnavailable):
        await client.async_snapshot()
    assert client.snapshot is None, "an expired snapshot is released"
    assert len(server.downloads()) == 1


@pytest.mark.asyncio
async def test_a_stale_status_backs_off_instead_of_polling(monkeypatch):
    clocks = _Clocks(monkeypatch)
    server = _Server()
    server.status["last_datetime_utc"] = "2026-11-27 07:00:00"
    client = _client(server)
    with pytest.raises(api.RealtimeUnavailable):
        await client.async_snapshot()
    asked = len(server.requests)
    clocks.advance(30)
    with pytest.raises(api.RealtimeUnavailable):
        await client.async_snapshot()
    assert len(server.requests) == asked, "backing off still reached the network"
    assert server.downloads() == []


@pytest.mark.asyncio
async def test_a_404_on_a_fresh_file_does_not_remember_its_id(monkeypatch):
    clocks = _Clocks(monkeypatch)
    server = _Server()
    held = server.files.pop("2026/11/27/08/23.br")
    client = _client(server)
    with pytest.raises(api.RealtimeUnavailable):
        await client.async_snapshot()
    server.files["2026/11/27/08/23.br"] = held
    clocks.advance(61)  # אחרי מדרגת ה-backoff הראשונה
    assert (await client.async_snapshot()).by_line
    assert len(server.downloads()) == 2


@pytest.mark.asyncio
async def test_backoff_steps_grow_only_on_real_failures(monkeypatch):
    clocks = _Clocks(monkeypatch)
    server = _Server()
    server.status_response = _Response(500)
    client = _client(server)
    with pytest.raises(api.RealtimeUnavailable):
        await client.async_snapshot()
    # שבע תחנות בזמן ה-backoff: אף אחת לא מקדמת את המדרגה.
    for _ in range(7):
        with pytest.raises(api.RealtimeUnavailable):
            await client.async_snapshot()
    assert client._failures == 1
    clocks.advance(61)
    with pytest.raises(api.RealtimeUnavailable):
        await client.async_snapshot()
    assert client._failures == 2
    assert client._blocked_until == pytest.approx(clocks.mono + 120)
    # הצלחה מאפסת.
    server.status_response = None
    clocks.advance(121)
    await client.async_snapshot()
    assert client._failures == 0


@pytest.mark.asyncio
async def test_a_held_snapshot_is_served_during_backoff_until_it_expires(monkeypatch):
    clocks = _Clocks(monkeypatch)
    server = _Server()
    client = _client(server)
    first = await client.async_snapshot()
    server.status_response = _Response(500)
    clocks.advance(51)
    assert await client.async_snapshot() is first
    clocks.advance(200)
    with pytest.raises(api.RealtimeUnavailable):
        await client.async_snapshot()


@pytest.mark.asyncio
async def test_retry_after_is_honoured(monkeypatch):
    clocks = _Clocks(monkeypatch)
    server = _Server()
    server.status_response = _Response(429, headers={"Retry-After": "45"})
    client = _client(server)
    with pytest.raises(api.RealtimeUnavailable):
        await client.async_snapshot()
    # הגדול מבין Retry-After ומדרגת ה-backoff.
    assert client._blocked_until >= clocks.mono + 45


@pytest.mark.asyncio
async def test_a_cancelled_request_does_not_count_as_a_failure(monkeypatch):
    _Clocks(monkeypatch)

    class _Hangs(_Server):
        def get(self, url, **kwargs):
            raise asyncio.CancelledError

    client = _client(_Hangs())
    with pytest.raises(asyncio.CancelledError):
        await client.async_snapshot()
    assert client._failures == 0


@pytest.mark.asyncio
async def test_an_oversized_body_is_cut_off(monkeypatch):
    _Clocks(monkeypatch)
    monkeypatch.setattr(open_bus, "OPEN_BUS_MAX_BODY_BYTES", 100)
    server = _Server()
    with pytest.raises(api.RealtimeUnavailable, match="larger"):
        await _client(server).async_snapshot()
