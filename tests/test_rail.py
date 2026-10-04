"""The Israel Railways client.

Trains are absent from SIRI entirely, so this is the only source of live train
data. It answers per origin/destination pair rather than per station, and it
reports delays in a side list keyed by station id, which is the fiddly part.
"""

from __future__ import annotations

import importlib
import json
from datetime import datetime

import aiohttp
import pytest
from conftest import PACKAGE

api = importlib.import_module(f"{PACKAGE}.api")

# Trimmed from a real searchTrain response.
RESPONSE = {
    "result": {
        "travels": [
            {
                "departureTime": "2026-08-31T09:00:00",
                "arrivalTime": "2026-08-31T09:32:00",
                "trains": [
                    {
                        "trainNumber": 512,
                        "orignStation": 3700,
                        "destinationStation": 680,
                        "originPlatform": 4,
                        "etaDiffTimes": [
                            {"stationId": 680, "difMin": 9},
                            {"stationId": 3700, "difMin": 3},
                        ],
                    }
                ],
            },
            {
                "departureTime": "2026-08-31T09:30:00",
                "trains": [
                    {
                        "trainNumber": 514,
                        "orignStation": 3700,
                        "destinationStation": 680,
                        "originPlatform": 4,
                        "etaDiffTimes": [],
                    }
                ],
            },
        ]
    }
}


class _Response:
    def __init__(self, payload: object, status: int = 200) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> _Response:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def raise_for_status(self) -> None:
        if self.status >= 400:
            # ClientResponseError needs a full RequestInfo to render; the base
            # class is what the client actually catches.
            raise aiohttp.ClientError(f"HTTP {self.status}")

    async def json(self, content_type: object = None) -> object:
        return json.loads(json.dumps(self._payload))


class _Session:
    def __init__(self, response: _Response) -> None:
        self._response = response
        self.body: dict[str, str] | None = None
        self.headers: dict[str, str] | None = None

    def post(self, url, json=None, headers=None, timeout=None):
        self.body = json
        self.headers = headers
        return self._response


# --- parsing ----------------------------------------------------------------


def test_the_delay_at_the_origin_is_applied_to_the_departure():
    """The delay list carries every station; only the origin's one shifts us."""
    first, second = api.parse_rail(RESPONSE)

    assert first.line_name == "512"
    assert first.delay_minutes == 3
    assert first.is_realtime is True
    assert first.eta.strftime("%H:%M") == "09:03"
    assert first.platform == "4"
    assert first.route_type == "2"
    assert api.localized(first.destination) == "ירושלים - יצחק נבון"

    assert second.delay_minutes is None
    assert second.is_realtime is False
    assert second.eta.strftime("%H:%M") == "09:30"


def test_departures_come_back_in_time_order():
    arrivals = api.parse_rail(RESPONSE)
    assert arrivals == sorted(arrivals, key=lambda a: a.eta)


def test_an_unknown_destination_falls_back_to_its_id():
    payload = {
        "result": {
            "travels": [
                {
                    "departureTime": "2026-08-31T09:00:00",
                    "trains": [{"trainNumber": 1, "destinationStation": 4242}],
                }
            ]
        }
    }
    (arrival,) = api.parse_rail(payload)
    assert api.localized(arrival.destination) == "4242"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"result": {}},
        {"result": {"travels": []}},
        {"result": {"travels": [{"trains": []}]}},
        {"result": {"travels": [{"trains": [{"trainNumber": 1}]}]}},  # no time
    ],
)
def test_an_empty_or_malformed_response_yields_nothing(payload):
    assert api.parse_rail(payload) == []


# --- the request ------------------------------------------------------------


async def test_departures_sends_the_pair_the_api_expects():
    session = _Session(_Response(RESPONSE))
    client = api.RailClient(session)

    arrivals = await client.departures(
        "3700", "680", when=datetime(2026, 8, 31, 9, 0, tzinfo=api.ISRAEL_TZ)
    )

    assert len(arrivals) == 2
    assert session.body == {
        "fromStation": "3700",
        "toStation": "680",
        "date": "2026-08-31",
        "hour": "09:00",
        "scheduleType": "ByDeparture",
        "systemType": "2",
        "languageId": "Hebrew",
    }
    assert session.headers is not None
    assert "ocp-apim-subscription-key" in session.headers


async def test_an_http_error_becomes_realtime_unavailable():
    """The card then shows the timetable instead of an empty board."""
    session = _Session(_Response(RESPONSE, status=503))
    with pytest.raises(api.RealtimeUnavailable):
        await api.RailClient(session).departures("3700", "680")


async def test_a_network_failure_becomes_realtime_unavailable():
    class Broken:
        def post(self, *args, **kwargs):
            raise aiohttp.ClientError("connection reset")

    with pytest.raises(api.RealtimeUnavailable, match="unreachable"):
        await api.RailClient(Broken()).departures("3700", "680")


# --- station matching -------------------------------------------------------


def test_a_gtfs_rail_stop_maps_to_a_station_id():
    assert api.RailClient.station_id("תל אביב מרכז") == "3700"
    assert api.RailClient.station_id("ירושלים - יצחק נבון") == "680"


def test_a_station_the_table_does_not_know_maps_to_nothing():
    """New Eastern Railway stops must not be mismatched onto an old station."""
    assert api.RailClient.station_id("חדרה מזרח") is None
