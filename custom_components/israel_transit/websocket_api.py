"""WebSocket commands for the dashboard card.

The card needs more than entity state can reasonably carry: a search over ~30k
stops for its visual editor, every line serving a stop, and a line's full stop
sequence. Serving those over the WebSocket API keeps them out of the state
machine and the recorder, and inherits Home Assistant's own authentication.
"""

from __future__ import annotations

import logging
from time import monotonic
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .api import IsraelTransitError, parse_dt
from .const import (
    DATA_CLIENTS,
    DATA_STOP_CACHE,
    DOMAIN,
    STOP_CACHE_MAX_ENTRIES,
    STOP_CACHE_TTL,
)
from .coordinator import (
    Clients,
    StopData,
    async_fetch_stop,
    async_find_coordinator,
)

_LOGGER = logging.getLogger(__name__)

# קוד תחנה ויעד ברכבת -> (מתי נשלף, הלוח עצמו).
type _StopCache = dict[tuple[int, str | None], tuple[float, StopData]]


def _clients(hass: HomeAssistant) -> Clients:
    clients: Clients = hass.data[DOMAIN][DATA_CLIENTS]
    return clients


async def _async_stop_data(
    hass: HomeAssistant, stop_code: int, rail_destination: str | None
) -> StopData:
    """One upstream request per stop per interval, however many cards ask.

    Every open dashboard polls this command, and curlbus is a single free
    community service, so an already-polled stop is answered from its
    coordinator and anything else from a short-lived cache.
    """
    coordinator = async_find_coordinator(hass, stop_code)
    # A stop whose first read failed has no board yet, and a configured stop
    # polled for another train destination -- or for none -- has the wrong
    # rail rows. Either way the card gets a board of its own, never that one.
    if (
        coordinator is not None
        and coordinator.data is not None
        and coordinator.rail_destination == (rail_destination or None)
    ):
        return coordinator.data

    cache: _StopCache = hass.data[DOMAIN].setdefault(DATA_STOP_CACHE, {})
    # היעד ברכבת משנה את הלוח עצמו, ולכן הוא חלק מהמפתח ולא רק פרמטר לשליפה.
    key = (stop_code, rail_destination or None)
    now = monotonic()
    cached = cache.get(key)
    if cached is not None and now - cached[0] < STOP_CACHE_TTL:
        return cached[1]

    data = await async_fetch_stop(
        _clients(hass), stop_code, rail_destination=rail_destination
    )
    cache[key] = (now, data)
    _prune_cache(cache, now)
    return data


def _prune_cache(cache: _StopCache, now: float) -> None:
    """מנקה את המטמון מרשומות שפגו. בלי זה כל קוד תחנה שנשאל נשאר בזיכרון."""
    for key in [k for k, (at, _) in cache.items() if now - at >= STOP_CACHE_TTL]:
        del cache[key]
    if len(cache) > STOP_CACHE_MAX_ENTRIES:
        newest = sorted(cache.items(), key=lambda item: item[1][0], reverse=True)
        cache.clear()
        cache.update(newest[:STOP_CACHE_MAX_ENTRIES])


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register every command this integration serves to the frontend."""
    websocket_api.async_register_command(hass, ws_search_stops)
    websocket_api.async_register_command(hass, ws_stop)
    websocket_api.async_register_command(hass, ws_stop_routes)
    websocket_api.async_register_command(hass, ws_route_stops)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/search_stops",
        vol.Required("query"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Optional("limit", default=25): vol.All(int, vol.Range(min=1, max=100)),
    }
)
@websocket_api.async_response
async def ws_search_stops(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Search stops by name, city or code, for the card's visual editor."""
    try:
        stops = await _clients(hass).index.async_search(msg["query"], msg["limit"])
    except IsraelTransitError as err:
        connection.send_error(msg["id"], "search_failed", str(err))
        return
    connection.send_result(msg["id"], [stop.as_dict() for stop in stops])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/stop",
        vol.Required("stop_code"): vol.Coerce(int),
        vol.Optional("rail_destination"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_stop(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """The arrival board for any stop, configured as an entry or not."""
    # כרטיס שמבקש תחנה הוא הסימן היחיד שהיא בשימוש, ולכן גם מה שמכניס אותה
    # לאינדקס לוחות הזמנים.
    clients = _clients(hass)
    clients.async_note_stop(msg["stop_code"])
    try:
        data = await _async_stop_data(
            hass, msg["stop_code"], msg.get("rail_destination")
        )
    except IsraelTransitError as err:
        connection.send_error(msg["id"], "unknown_stop", str(err))
        return
    if data.realtime_error and not data.arrivals:
        clients.async_request_timetable(msg["stop_code"])
    connection.send_result(msg["id"], data.as_dict(hass.config.language))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/stop_routes",
        vol.Required("stop_code"): vol.Coerce(int),
    }
)
@websocket_api.async_response
async def ws_stop_routes(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Every line serving a stop -- the stop detail view."""
    try:
        routes = await _clients(hass).index.async_routes_at_stop(msg["stop_code"])
    except IsraelTransitError as err:
        connection.send_error(msg["id"], "lookup_failed", str(err))
        return
    connection.send_result(msg["id"], [route.as_dict() for route in routes])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/route_stops",
        vol.Required("line_ref"): vol.Coerce(int),
        vol.Optional("departed"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_route_stops(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """A line's ordered stop sequence -- the vehicle detail view.

    Stop times are stored as offsets from the start of a run, so passing the
    tracked vehicle's departure time turns them into times for that vehicle
    rather than for whichever sample trip was indexed.
    """
    try:
        stops = await _clients(hass).index.async_route_stops(msg["line_ref"])
    except IsraelTransitError as err:
        connection.send_error(msg["id"], "lookup_failed", str(err))
        return
    departed = parse_dt(msg.get("departed"))
    connection.send_result(msg["id"], [stop.as_dict(departed) for stop in stops])
