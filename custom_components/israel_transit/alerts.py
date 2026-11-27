"""התראה חד-פעמית לטלפון כשקו מתקרב לתחנה: "תזכיר לי כשהוא במרחק 5 דקות".

החוזה:
* יורה פעם אחת, לרכב הראשון של הקו שנכנס לסף אחרי שההתראה נקבעה. רכב שכבר
  בתוך הסף ברגע הקביעה נשאר בחוץ: הוא כבר קרוב, והמשתמש רואה אותו בלוח.
* הסף הוא דקות עד ההגעה, או מספר תחנות כשהרכב משדר מיקום. בלי מיקום, התראה
  לפי תחנות יורה דקה לפני ההגעה, כדי שלא תחכה בשקט לאוטובוס שכבר עבר.
* בודקת כל 30 שניות דרך אותו לוח שהכרטיס קורא, כך שתחנה מוגדרת לא עולה אף
  בקשה נוספת ל-curlbus. פגה אחרי שעתיים בלי לירות, ולא שורדת הפעלה מחדש.
* קביעה חוזרת לאותו קו, תחנה ונמענים מחליפה את הקודמת ולא מוסיפה עוד אחת.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import CALLBACK_TYPE, Context, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.util.location import distance

from .api import Arrival, IsraelTransitError, RouteStop
from .const import (
    ALERT_CHECK_INTERVAL,
    ALERT_MAX_AGE,
    DOMAIN,
    EVENT_ARRIVAL_ALERT,
    NEAREST_STOP_MAX_M,
)
from .coordinator import Clients, async_find_coordinator, async_walk_minutes
from .phrases import alert_text, leave_hint
from .websocket_api import async_stop_board

_LOGGER = logging.getLogger(__name__)

type AlertKey = tuple[int, str, tuple[str, ...]]


@callback
def async_user_notify_entities(hass: HomeAssistant, user_id: str | None) -> list[str]:
    """ישויות ה-notify של אפליקציות הנייד שמחוברות למשתמש הזה.

    כל טלפון שנרשם באפליקציה הוא רשומת mobile_app עם user_id, ומאז 2026.5 יש
    לה ישות notify שנשלחת אליה ב-notify.send_message.
    """
    if not user_id:
        return []
    registry = er.async_get(hass)
    return sorted(
        entity.entity_id
        for entry in hass.config_entries.async_entries("mobile_app")
        if entry.data.get("user_id") == user_id
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.domain == "notify" and not entity.disabled
    )


def stops_away(
    route: list[RouteStop], stop_code: int, lat: float, lon: float
) -> int | None:
    """כמה תחנות בין הרכב לתחנה, או None כשאי אפשר לדעת (מחוץ למסלול, או אחריה)."""
    mine = next((i for i, rs in enumerate(route) if rs.stop.code == stop_code), None)
    if mine is None:
        return None
    measured = [
        (metres, index)
        for index, rs in enumerate(route)
        if rs.stop.lat is not None
        and rs.stop.lon is not None
        and (metres := distance(lat, lon, rs.stop.lat, rs.stop.lon)) is not None
    ]
    if not measured:
        return None
    metres, here = min(measured)
    if metres > NEAREST_STOP_MAX_M or here > mine:
        return None
    return mine - here


def _identity(arrival: Arrival) -> str:
    """מזהה יציב לנסיעה בין רענונים: הרכב, או הזמן המתוכנן, או שעת ההגעה."""
    if arrival.vehicle_ref:
        return f"v:{arrival.vehicle_ref}"
    if arrival.scheduled is not None:
        return f"s:{arrival.line_ref}:{arrival.scheduled.isoformat()}"
    return f"e:{arrival.eta.replace(second=0, microsecond=0).isoformat()}"


def alert_key(stop_code: int, line: str, targets: list[str]) -> AlertKey:
    return (stop_code, line, tuple(sorted(targets)))


@dataclass(slots=True, kw_only=True)
class Alert:
    stop_code: int
    line: str
    minutes: int
    stops: int | None
    targets: list[str]
    context: Context
    created: datetime = field(default_factory=dt_util.utcnow)
    stop_name: str = ""
    # נסיעות שכבר היו בתוך הסף כשההתראה נקבעה.
    skip: set[str] = field(default_factory=set)
    routes: dict[str, list[RouteStop]] = field(default_factory=dict)
    unsub: CALLBACK_TYPE | None = None
    checking: bool = False

    @property
    def key(self) -> AlertKey:
        return alert_key(self.stop_code, self.line, self.targets)


class ArrivalAlerts:
    """ההתראות הפעילות, בזיכרון בלבד."""

    def __init__(self, hass: HomeAssistant, clients: Clients) -> None:
        self.hass = hass
        self.clients = clients
        self._alerts: dict[AlertKey, Alert] = {}

    async def async_add(self, alert: Alert) -> None:
        """קובע התראה. זורק IsraelTransitError כשהתחנה לא ידועה בכלל."""
        key = alert.key
        stop_code, line = alert.stop_code, alert.line
        self.async_cancel(key)
        rows = await self._async_rows(alert)
        now = dt_util.utcnow()
        for row in rows:
            if await self._async_due(alert, row, now) is not None:
                alert.skip.add(_identity(row))

        async def _async_tick(_now: datetime) -> None:
            await self._async_check(key)

        alert.unsub = async_track_time_interval(
            self.hass,
            _async_tick,
            ALERT_CHECK_INTERVAL,
            name=f"{DOMAIN} alert {stop_code} {line}",
            cancel_on_shutdown=True,
        )
        self._alerts[key] = alert
        _LOGGER.debug("Alert set for line %s at stop %s", line, stop_code)

    @callback
    def async_cancel(self, key: AlertKey) -> bool:
        alert = self._alerts.pop(key, None)
        if alert is None:
            return False
        if alert.unsub is not None:
            alert.unsub()
        return True

    @callback
    def async_shutdown(self) -> None:
        for key in list(self._alerts):
            self.async_cancel(key)

    async def _async_rows(self, alert: Alert) -> list[Arrival]:
        coordinator = async_find_coordinator(self.hass, alert.stop_code)
        board = await async_stop_board(
            self.hass,
            alert.stop_code,
            coordinator.rail_destination if coordinator is not None else None,
        )
        alert.stop_name = board.stop.name
        return [a for a in board.running() if a.line_name == alert.line]

    async def _async_due(self, alert: Alert, row: Arrival, now: datetime) -> int | None:
        """None כשהרכב עוד רחוק; אחרת כמה תחנות הוא מהתחנה (0 כשלא ידוע)."""
        seconds = (row.eta - now).total_seconds()
        if seconds <= alert.minutes * 60:
            away = await self._async_stops_away(alert, row)
            return away or 0
        if alert.stops is None:
            return None
        away = await self._async_stops_away(alert, row)
        return away if away is not None and away <= alert.stops else None

    async def _async_stops_away(self, alert: Alert, row: Arrival) -> int | None:
        if (
            row.vehicle_lat is None
            or row.vehicle_lon is None
            or not row.line_ref
            or not row.line_ref.isdigit()
        ):
            return None
        if (route := alert.routes.get(row.line_ref)) is None:
            try:
                route = await self.clients.index.async_route_stops(int(row.line_ref))
            except IsraelTransitError:
                route = []
            alert.routes[row.line_ref] = route
        return stops_away(route, alert.stop_code, row.vehicle_lat, row.vehicle_lon)

    async def _async_check(self, key: AlertKey) -> None:
        alert = self._alerts.get(key)
        if alert is None or alert.checking:
            return
        now = dt_util.utcnow()
        if now - alert.created > ALERT_MAX_AGE:
            _LOGGER.debug("Alert for line %s expired", alert.line)
            self.async_cancel(key)
            return
        alert.checking = True
        try:
            rows = await self._async_rows(alert)
            for row in rows:
                if _identity(row) in alert.skip:
                    continue
                if (away := await self._async_due(alert, row, now)) is not None:
                    self.async_cancel(key)
                    await self._async_send(alert, row, away or None, now)
                    return
        except IsraelTransitError as err:
            _LOGGER.debug("Alert check for stop %s failed: %s", alert.stop_code, err)
        finally:
            alert.checking = False

    async def _async_send(
        self, alert: Alert, row: Arrival, away: int | None, now: datetime
    ) -> None:
        lang = self.hass.config.language
        title, message = alert_text(alert.stop_name, row, away, lang, now)
        walk = async_walk_minutes(self.hass, alert.stop_code)
        if hint := leave_hint([row], walk, lang, now):
            message = f"{message} {hint}"
        self.hass.bus.async_fire(
            EVENT_ARRIVAL_ALERT,
            {
                "stop_code": alert.stop_code,
                "line": row.line_name,
                "eta": row.eta.isoformat(),
                "stops_away": away,
                "title": title,
                "message": message,
                "targets": alert.targets,
            },
            context=alert.context,
        )
        try:
            await self.hass.services.async_call(
                "notify",
                "send_message",
                {"title": title, "message": message},
                target={ATTR_ENTITY_ID: alert.targets},
                blocking=True,
                context=alert.context,
            )
        except HomeAssistantError as err:
            # ההתראה כבר ירתה כאירוע, ואוטומציה עדיין יכולה לפעול עליו.
            _LOGGER.warning(
                "Could not send the arrival alert for line %s: %s", alert.line, err
            )
