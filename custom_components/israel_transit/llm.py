"""כלי ל-Assist: "מתי הקו הבא לתל אביב?", "הרכבת שלי מאחרת?".

הפלטפורמה llm.py נטענת רק ב-Home Assistant 2026.8 ומעלה, שבהן אינטגרציה תורמת
כלים ל-Assist API. בגרסה ישנה יותר היא פשוט לא נקראת.
https://contributors.home-assistant.io/core/internals/llm-api/
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.util import dt as dt_util

from . import arrivals_response, async_service_board
from .const import CONF_LINE, CONF_STOP_CODE, DOMAIN
from .coordinator import IsraelTransitCoordinator
from .phrases import clock

# גרסאות חדשות מגדירות פרמטרים של כלים ב-probatio, ישנות ב-voluptuous; משתמשים
# במה שהעוזר של Home Assistant עצמו מייבא. ToolResult ו-ToolAnnotations חדשים.
_schema: Any = getattr(llm, "probatio", vol)
_TOOL_RESULT: Any = getattr(llm, "ToolResult", None)
_ANNOTATIONS: Any = getattr(llm, "ToolAnnotations", None)

# שורות לכל תחנה: מספיק לשאלה "מתי הבא", בלי להציף את המודל.
_ROWS = 8

PROMPT = (
    f"For questions about Israeli buses, trains, light rail or shared taxis at "
    f"the user's stops (when the next one comes, whether it is late, whether to "
    f"leave now), call {DOMAIN}__get_arrivals and answer from its summary."
)


@callback
def async_get_tools(
    hass: HomeAssistant, llm_context: llm.LLMContext, api_id: str
) -> LLMTools | None:
    """הכלי נכנס רק ל-Assist, ורק כשיש תחנה מוגדרת לשאול עליה."""
    if api_id != llm.LLM_API_ASSIST or not _stops(hass):
        return None
    return LLMTools(tools=[GetArrivalsTool()], prompt=PROMPT)


def _stops(hass: HomeAssistant) -> list[IsraelTransitCoordinator]:
    return [
        coordinator
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        for coordinator in entry.runtime_data.values()
    ]


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    """שורה בלי מה שמודל לא צריך (מזהים, קואורדינטות), כדי לחסוך בטוקנים."""
    keep = (
        "line_name",
        "destination",
        "minutes",
        "is_realtime",
        "delay_minutes",
        "cancelled",
        "platform",
        "train_number",
        "leave_minutes",
    )
    # 0 דקות ו-0 עיכוב הם מידע; רק None ו-False (לא בוטל) מיותרים.
    return {
        key: row[key]
        for key in keep
        if row.get(key) is not None and row[key] is not False
    }


def _result(payload: dict[str, Any], error: bool = False) -> Any:
    if _TOOL_RESULT is None:
        return payload
    return _TOOL_RESULT(data=payload, error=error)


class GetArrivalsTool(llm.Tool):
    """הלוח של התחנות המוגדרות, עם משפט סיכום מוכן."""

    name = f"{DOMAIN}__get_arrivals"
    title = "Public transport arrivals"
    description = (
        "Upcoming Israeli public transport arrivals (bus, train, light rail, "
        "shared taxi) at the user's configured stops: line, destination, minutes "
        "until arrival, whether the time is live or from the timetable, delay in "
        "minutes, cancellations, and when to leave home to catch it. Each stop "
        "has a ready 'summary' sentence; when nothing is due (night, Shabbat, "
        "holidays) it says when service resumes. Leave stop_code empty to get "
        "every configured stop."
    )
    integration = DOMAIN
    parameters = _schema.Schema(
        {
            _schema.Optional(
                CONF_STOP_CODE,
                description="One stop code from the user's stops; empty for all.",
            ): _schema.Coerce(int),
            _schema.Optional(
                CONF_LINE,
                description="Only this line number, for example 18 or 480.",
            ): str,
        }
    )
    if _ANNOTATIONS is not None:
        annotations = _ANNOTATIONS(
            read_only=True, destructive=False, idempotent=True, open_world=True
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> Any:
        args = tool_input.tool_args
        stops = _stops(hass)
        if (code := args.get(CONF_STOP_CODE)) is not None:
            stops = [c for c in stops if c.stop_code == code]
            if not stops:
                known = ", ".join(str(c.stop_code) for c in _stops(hass))
                return _result(
                    {"error": f"Stop {code} is not set up. The user's stops: {known}"},
                    error=True,
                )
        lines = {str(args[CONF_LINE]).strip()} if args.get(CONF_LINE) else set()
        now = dt_util.utcnow()
        results = []
        for coordinator in stops:
            try:
                data = await async_service_board(
                    hass, coordinator.stop_code, coordinator.rail_destination
                )
            except HomeAssistantError as err:
                # תחנה אחת שלא נקראה לא מסתירה את השאר.
                results.append({"stop_code": coordinator.stop_code, "error": str(err)})
                continue
            answer = arrivals_response(hass, data, lines, now, llm_context.language)
            results.append(
                {
                    "stop": data.stop.name,
                    "stop_code": data.stop.code,
                    "summary": answer["summary"],
                    "arrivals": [_compact(row) for row in answer["arrivals"][:_ROWS]],
                }
            )
        return _result({"now": clock(now), "stops": results})
