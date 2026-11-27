"""WebSocket commands for the dashboard card.

The card needs more than entity state can reasonably carry: a search over ~30k
stops for its visual editor, every line serving a stop, and a line's full stop
sequence. Serving those over the WebSocket API keeps them out of the state
machine and the recorder, and inherits Home Assistant's own authentication.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from time import monotonic
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .api import IsraelTransitError, parse_dt
from .const import (
    DATA_CLIENTS,
    DATA_STOP_CACHE,
    DATA_STOP_IN_FLIGHT,
    DOMAIN,
    NEARBY_STOPS,
    STOP_CACHE_MAX_ENTRIES,
    STOP_CACHE_TTL,
)
from .coordinator import (
    Clients,
    StopData,
    async_fetch_stop,
    async_find_coordinator,
    async_walk_minutes,
    poll_interval,
)

_LOGGER = logging.getLogger(__name__)

# קוד תחנה ויעד ברכבת -> (עד מתי בתוקף, הלוח עצמו).
type _StopCache = dict[tuple[int, str | None], tuple[float, StopData]]


def _clients(hass: HomeAssistant) -> Clients:
    clients: Clients = hass.data[DOMAIN][DATA_CLIENTS]
    return clients


async def async_stop_board(
    hass: HomeAssistant, stop_code: int, rail_destination: str | None
) -> StopData:
    """One upstream request per stop per interval, however many cards ask.

    Every open dashboard polls this command, and curlbus is a single free
    community service, so an already-polled stop is answered from its
    coordinator and anything else from a short-lived cache. Shared by the
    get_arrivals action, for the same reason.

    לוח של coordinator שהרענון האחרון שלו נכשל עדיין מוגש: updated_at מסגיר
    את גילו, ושליפה טרייה מכל כרטיס הייתה מציפה את curlbus דווקא כשהוא נופל.
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
    if cached is not None and now < cached[0]:
        return cached[1]

    # כמה כרטיסים של אותה תחנה נטענים יחד עם הדשבורד: כולם מחכים לשליפה אחת.
    in_flight: dict[tuple[int, str | None], asyncio.Future[StopData]] = hass.data[
        DOMAIN
    ].setdefault(DATA_STOP_IN_FLIGHT, {})
    if (pending := in_flight.get(key)) is not None:
        return await asyncio.shield(pending)
    task = hass.async_create_task(
        async_fetch_stop(_clients(hass), stop_code, rail_destination=rail_destination),
        f"{DOMAIN}-stop-{stop_code}",
        eager_start=False,
    )
    in_flight[key] = task
    try:
        data = await asyncio.shield(task)
    finally:
        in_flight.pop(key, None)
    # אותו קצב כמו תחנה מוגדרת: בלילה ובשבת לוח ריק נשמר עד רבע שעה.
    ttl = poll_interval(timedelta(seconds=STOP_CACHE_TTL), data, dt_util.utcnow())
    data.refresh_seconds = int(ttl.total_seconds())
    cache[key] = (now + ttl.total_seconds(), data)
    _prune_cache(cache, now)
    return data


def _prune_cache(cache: _StopCache, now: float) -> None:
    """מנקה את המטמון מרשומות שפגו. בלי זה כל קוד תחנה שנשאל נשאר בזיכרון."""
    for key in [k for k, (until, _) in cache.items() if now >= until]:
        del cache[key]
    if len(cache) > STOP_CACHE_MAX_ENTRIES:
        newest = sorted(cache.items(), key=lambda item: item[1][0], reverse=True)
        cache.clear()
        cache.update(newest[:STOP_CACHE_MAX_ENTRIES])


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register every command this integration serves to the frontend."""
    websocket_api.async_register_command(hass, ws_search_stops)
    websocket_api.async_register_command(hass, ws_nearby_stops)
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
        vol.Required("type"): f"{DOMAIN}/nearby_stops",
        vol.Optional("limit", default=NEARBY_STOPS): vol.All(
            int, vol.Range(min=1, max=25)
        ),
    }
)
@websocket_api.async_response
async def ws_nearby_stops(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """התחנות הקרובות למיקום הבית, לעורך הכרטיס, עם המרחק במטרים."""
    try:
        found = await _clients(hass).index.async_nearest_stops(
            hass.config.latitude, hass.config.longitude, msg["limit"]
        )
    except IsraelTransitError as err:
        connection.send_error(msg["id"], "search_failed", str(err))
        return
    connection.send_result(
        msg["id"],
        [{**stop.as_dict(), "distance": round(metres)} for stop, metres in found],
    )


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
        data = await async_stop_board(
            hass, msg["stop_code"], msg.get("rail_destination")
        )
    except IsraelTransitError as err:
        # בלי אינדקס, בזמן הבנייה הראשונה, אי אפשר לדעת אם הקוד שגוי. "תחנה לא
        # נמצאה" היה שולח את המשתמש לבדוק קוד נכון.
        code = (
            "index_building"
            if not clients.index.available and clients.rebuilding
            else "unknown_stop"
        )
        connection.send_error(msg["id"], code, str(err))
        return
    if data.realtime_error and not data.arrivals:
        clients.async_request_timetable(msg["stop_code"])
    connection.send_result(
        msg["id"],
        {
            **data.as_dict(hass.config.language),
            # שעון השרת, כדי שהכרטיס יחשב גיל של מיקום רכב בלי לסמוך על שעון הדפדפן.
            "server_time": dt_util.utcnow().isoformat(),
            "walk_minutes": async_walk_minutes(hass, msg["stop_code"]),
        },
    )


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
    """A line's ordered stop sequence and street path -- the vehicle detail view.

    Stop times are stored as offsets from the start of a run, so passing the
    tracked vehicle's departure time turns them into times for that vehicle
    rather than for whichever sample trip was indexed. ``index`` is when the
    index was built, which lets the card cache the path until it changes.
    """
    index = _clients(hass).index
    try:
        stops = await index.async_route_stops(msg["line_ref"])
        shape = await index.async_route_shape(msg["line_ref"])
    except IsraelTransitError as err:
        connection.send_error(msg["id"], "lookup_failed", str(err))
        return
    departed = parse_dt(msg.get("departed"))
    connection.send_result(
        msg["id"],
        {
            "stops": [stop.as_dict(departed) for stop in stops],
            # חמש ספרות אחרי הנקודה הן כמטר, ומקצרות את ההודעה בחצי.
            "shape": (
                [[round(lat, 5), round(lon, 5)] for lat, lon in shape]
                if shape
                else None
            ),
            "index": index.built,
        },
    )
