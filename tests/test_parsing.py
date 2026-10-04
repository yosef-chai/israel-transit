"""Tests for the parsing that stands between three untidy APIs and the card.

The payloads here are trimmed captures of real responses, including the ones
that misbehave: curlbus answering HTTP 500 in plain text for a stop it does not
know, and sending the literal string "None" where a timestamp belongs.
"""

from __future__ import annotations

import importlib
import json
from datetime import datetime, timedelta

import pytest
from conftest import PACKAGE

api = importlib.import_module(f"{PACKAGE}.api")
rail_stations = importlib.import_module(f"{PACKAGE}.rail_stations")


# --- captured payloads ------------------------------------------------------

CURLBUS_STOP_21023 = {
    "errors": None,
    "timestamp": "None",
    "visits": {
        "21023": [
            {
                "producer": "SIRI",
                "stop_code": "21023",
                "line_id": "960",
                "line_name": "36",
                "operator_id": "15",
                "vehicle_ref": "36760701",
                "eta": "2026-08-30 22:06:00+03:00",
                "departed": "2026-08-30 21:40:00+03:00",
                "location": {"lat": "32.073905", "lon": "34.783706"},
                "static_info": {
                    "route": {
                        "destination": {
                            "code": "2357",
                            "name": {"HE": "מסוף אור יהודה/הורדה", "EN": "Or Yehuda"},
                        },
                        "agency": {"name": {"HE": "מטרופולין", "EN": "Metropoline"}},
                    }
                },
            },
            {
                "producer": "SIRI",
                "line_id": "16352",
                "line_name": "91",
                "eta": "2026-08-30 22:20:00+03:00",
                "departed": None,
                "location": {},
                "static_info": {},
            },
        ]
    },
    "stop_info": {
        "name": {"HE": "ת. רכבת השלום", "EN": "HaShalom Rail Station", "AR": "..."},
        "address": {
            "street": "גבעת התחמושת",
            "city": "Tel Aviv Yafo",
            "city_multilingual": {"HE": "תל אביב יפו", "EN": "Tel Aviv Yafo"},
        },
        "location": {"lat": 32.072666, "lon": 34.79339},
    },
}

# Stop 40001 at night: a valid stop with nothing due. Not an error.
CURLBUS_EMPTY = {
    "errors": None,
    "timestamp": "None",
    "visits": {"40001": []},
    "stop_info": {
        "name": {"HE": "אמפיתאטרון", "EN": "Amphitheatre"},
        "address": {"city": "Caesarea"},
        "location": {"lat": 32.496682, "lon": 34.892801},
    },
}

CURLBUS_INVALID = {"errors": ["Invalid stop code 999999"], "visits": {}}


# --- localisation and time --------------------------------------------------


def test_localized_prefers_requested_language_then_falls_back():
    names = {"HE": "תל אביב", "EN": "Tel Aviv"}
    assert api.localized(names, "he") == "תל אביב"
    assert api.localized(names, "en") == "Tel Aviv"
    assert api.localized({"EN": "Only English"}, "he") == "Only English"
    assert api.localized("plain string", "en") == "plain string"
    assert api.localized(None, "he", default="-") == "-"


@pytest.mark.parametrize("junk", ["None", "null", "", None, "not a date", 12345])
def test_parse_dt_rejects_junk_without_raising(junk):
    assert api.parse_dt(junk) is None


def test_parse_dt_handles_the_space_separated_offset_curlbus_sends():
    parsed = api.parse_dt("2026-08-30 22:06:00+03:00")
    assert parsed is not None
    assert (parsed.hour, parsed.minute) == (22, 6)
    assert parsed.utcoffset() == timedelta(hours=3)


def test_parse_dt_assumes_israel_time_when_no_offset_is_given():
    parsed = api.parse_dt("2026-08-30T22:06:00")
    assert parsed is not None and parsed.utcoffset() is not None


def test_minutes_until_never_goes_negative():
    now = datetime(2026, 8, 30, 22, 0, tzinfo=api.ISRAEL_TZ)
    assert api.minutes_until(now + timedelta(minutes=7), now) == 7
    assert api.minutes_until(now + timedelta(seconds=90), now) == 1
    assert api.minutes_until(now - timedelta(minutes=5), now) == 0


# --- curlbus ----------------------------------------------------------------


def test_parse_curlbus_reads_stop_and_arrivals():
    stop, arrivals = api.parse_curlbus(CURLBUS_STOP_21023)

    assert stop is not None
    assert stop.name == "ת. רכבת השלום"
    assert stop.city == "תל אביב יפו"
    assert stop.lat == pytest.approx(32.072666)

    assert [a.line_name for a in arrivals] == ["36", "91"]
    first = arrivals[0]
    assert first.is_realtime is True
    assert first.line_ref == "960"
    assert api.localized(first.operator) == "מטרופולין"
    assert api.localized(first.destination) == "מסוף אור יהודה/הורדה"
    assert first.vehicle_lat == pytest.approx(32.073905)
    assert first.departed is not None


def test_parse_curlbus_sorts_by_arrival_time():
    _, arrivals = api.parse_curlbus(CURLBUS_STOP_21023)
    assert arrivals == sorted(arrivals, key=lambda a: a.eta)


def test_parse_curlbus_tolerates_a_visit_with_no_static_info():
    _, arrivals = api.parse_curlbus(CURLBUS_STOP_21023)
    sparse = arrivals[1]
    assert sparse.line_name == "91"
    assert sparse.destination is None
    assert sparse.departed is None
    assert sparse.vehicle_lat is None


def test_no_arrivals_is_a_valid_answer_not_an_error():
    stop, arrivals = api.parse_curlbus(CURLBUS_EMPTY)
    assert arrivals == []
    assert stop is not None and stop.name == "אמפיתאטרון"


def test_an_unknown_stop_code_raises():
    with pytest.raises(api.InvalidStop):
        api.parse_curlbus(CURLBUS_INVALID)


# --- the curlbus failure modes seen in production ---------------------------


class _FakeResponse:
    def __init__(self, status: int, content_type: str, body: str) -> None:
        self.status = status
        self.content_type = content_type
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self, content_type=None):
        return json.loads(self._body)


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return self.response


async def _arrivals(response: _FakeResponse):
    return await api.CurlbusClient(_FakeSession(response)).arrivals(35962)


@pytest.mark.asyncio
async def test_plain_text_500_becomes_realtime_unavailable():
    """curlbus does this for stops missing from its static data, e.g. Dankal."""
    response = _FakeResponse(
        500, "text/plain", "500 Internal Server Error\n\nServer got itself in trouble"
    )
    with pytest.raises(api.RealtimeUnavailable):
        await _arrivals(response)


@pytest.mark.asyncio
async def test_a_200_that_is_not_json_becomes_realtime_unavailable():
    response = _FakeResponse(200, "text/html", "<html>maintenance</html>")
    with pytest.raises(api.RealtimeUnavailable):
        await _arrivals(response)


@pytest.mark.asyncio
async def test_a_healthy_json_response_is_parsed():
    response = _FakeResponse(200, "application/json", json.dumps(CURLBUS_EMPTY))
    stop, arrivals = await _arrivals(response)
    assert arrivals == []
    assert stop is not None


@pytest.mark.asyncio
async def test_a_stop_curlbus_keeps_refusing_stops_being_asked_about():
    """A code its static data lacks will not start working within the minute."""
    session = _FakeSession(_FakeResponse(500, "text/plain", "500 Internal Server"))
    client = api.CurlbusClient(session)

    for _ in range(api.REALTIME_FAILURES_BEFORE_BACKOFF):
        with pytest.raises(api.RealtimeUnavailable):
            await client.arrivals(35962)
    asked = session.calls

    with pytest.raises(api.RealtimeUnavailable) as err:
        await client.arrivals(35962)

    assert session.calls == asked, "the backed-off stop still reached the network"
    assert "retrying in" in str(err.value)


@pytest.mark.asyncio
async def test_another_stop_is_unaffected_by_one_stop_backing_off():
    """The backoff is per stop code, not a circuit breaker over the whole API."""
    session = _FakeSession(_FakeResponse(500, "text/plain", "500 Internal Server"))
    client = api.CurlbusClient(session)

    for _ in range(api.REALTIME_FAILURES_BEFORE_BACKOFF + 1):
        with pytest.raises(api.RealtimeUnavailable):
            await client.arrivals(35962)

    session.response = _FakeResponse(200, "application/json", json.dumps(CURLBUS_EMPTY))
    asked = session.calls
    stop, arrivals = await client.arrivals(21023)

    assert session.calls == asked + 1
    assert arrivals == []
    assert stop is not None


# --- GTFS shapes ------------------------------------------------------------


def _route(long_name: str, route_type: str = "0") -> api.RouteInfo:
    return api.RouteInfo(
        route_id=1,
        line_ref="10747",
        short_name="1",
        long_name=long_name,
        agency="כפיר",
        route_type=route_type,
    )


@pytest.mark.parametrize(
    ("long_name", "expected"),
    [
        # Jerusalem light rail: place, city, then a direction code.
        ("נווה יעקב - צפון-ירושלים<->הדסה עין כרם-ירושלים-20", "הדסה עין כרם"),
        # Dankal: same shape, different city.
        ("קרית אריה-פתח תקווה<->הקוממיות-בת ים-10", "הקוממיות"),
        # Israel Railways: no direction code, city repeated as the place.
        ("נתב''ג-נמל תעופה בן גוריון<->נהריה-נהריה", "נהריה"),
        ("מודיעין מרכז-מודיעין מכבים רעות<->נהריה-נהריה", "נהריה"),
        # Nothing to split: keep it whole rather than mangling it.
        ("קו מעגלי", "קו מעגלי"),
    ],
)
def test_route_destination_drops_the_city_and_direction_code(long_name, expected):
    assert _route(long_name).destination == expected


def test_light_rail_is_flagged_as_having_no_realtime():
    assert _route("א-עיר<->ב-עיר-10").as_dict()["has_realtime"] is False


def test_bus_routes_are_flagged_as_having_realtime():
    route = api.RouteInfo(
        route_id=2,
        line_ref="960",
        short_name="36",
        long_name="א<->ב-10",
        agency="מטרופולין",
        route_type="3",
    )
    assert route.as_dict()["has_realtime"] is True


def test_lines_sort_numerically_not_lexically():
    lines = ["480", "5", "41", "5א", "לילה"]
    assert sorted(lines, key=api.line_sort_key) == ["5", "5א", "41", "480", "לילה"]


# --- Israel Railways --------------------------------------------------------


def test_parse_rail_applies_the_reported_delay_to_the_departure():
    payload = {
        "result": {
            "travels": [
                {
                    "departureTime": "2026-08-31T09:00:00",
                    "trains": [
                        {
                            "trainNumber": 123,
                            "orignStation": 3700,
                            "destinationStation": 680,
                            "originPlatform": 4,
                            "etaDiffTimes": [{"stationId": 3700, "difMin": 3}],
                        }
                    ],
                }
            ]
        }
    }
    (arrival,) = api.parse_rail(payload)
    assert arrival.delay_minutes == 3
    assert arrival.is_realtime is True
    assert arrival.platform == "4"
    assert arrival.eta.hour == 9 and arrival.eta.minute == 3
    assert api.localized(arrival.destination) == "ירושלים - יצחק נבון"


def test_parse_rail_without_a_delay_is_marked_as_timetable_only():
    payload = {
        "result": {
            "travels": [
                {
                    "departureTime": "2026-08-31T09:00:00",
                    "trains": [{"trainNumber": 5, "orignStation": 3700}],
                }
            ]
        }
    }
    (arrival,) = api.parse_rail(payload)
    assert arrival.is_realtime is False
    assert arrival.delay_minutes is None


def test_parse_rail_on_an_empty_result():
    assert api.parse_rail({}) == []
    assert api.parse_rail({"result": {"travels": []}}) == []


# --- rail station name matching --------------------------------------------


@pytest.mark.parametrize(
    ("gtfs_name", "expected"),
    [
        ("השלום", "4600"),
        ("תל אביב מרכז", "3700"),  # rail.co.il calls it Tel Aviv - Savidor Center
        ("תל אביב האוניברסיטה - אקספו", "3600"),
        ("קרית אריה", "4170"),  # spelled קריית on the rail side
        ("באר שבע צפון", "7300"),  # must beat באר שבע - מרכז
        ("דימונה", "7500"),
        ("לוד", "5000"),  # must not be captured by לוד גני אביב
        ("ירושלים - יצחק נבון", "680"),
    ],
)
def test_rail_station_matching(gtfs_name, expected):
    assert rail_stations.rail_station_id(gtfs_name) == expected


@pytest.mark.parametrize(
    "unknown",
    ["חדרה מזרח", "שומרון-טייבה", "טירה-כוכב יאיר", "", "כזה לא קיים"],
)
def test_stations_missing_from_the_table_return_none(unknown):
    """New Eastern Railway stops must not be mismatched onto an old station."""
    assert rail_stations.rail_station_id(unknown) is None
