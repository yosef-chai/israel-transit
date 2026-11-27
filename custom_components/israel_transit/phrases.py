"""משפטים קצרים בעברית ובאנגלית: סיכום הלוח ל-Assist, ההתראה לטלפון, והשירות הבא.

אין להם מקום ב-strings.json, שמקבל רק את הקטגוריות ש-hassfest מכיר, ולכן הם כאן.
השפה היא שפת השרת (hass.config.language): עברית לכל מה שמתחיל ב-he, אחרת אנגלית.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Final

from .api import ISRAEL_TZ, Arrival, localized, minutes_until
from .const import LEAVE_GRACE, ROUTE_TYPE_RAIL

if TYPE_CHECKING:
    from .coordinator import StopData

# כמה שורות נכנסות לסיכום: מספיק לשאלה "מתי הבא", בלי להציף מודל שפה.
SUMMARY_ROWS: Final = 5
# שירות בשבת מהשעה הזו נקרא "מוצ״ש": אין תחבורה ציבורית לפני צאת השבת.
_MOTZASH_HOUR: Final = 17
# לפי datetime.weekday(): שני הוא 0.
_DAYS_HE: Final = ("שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון")
_DAYS_EN: Final = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

_TEXT: Final = {
    "he": {
        "line": "קו {line}",
        "train": "הרכבת",
        "towards": "{who} לכיוון {dest}",
        "in": "בעוד {n} דק׳ ({clock})",
        "now": "בעוד פחות מדקה",
        "at": "ב-{clock}",
        "live": "זמן אמת",
        "scheduled": "לפי לוח הזמנים",
        "late": "איחור של {n} דק׳",
        "early": "הקדמה של {n} דק׳",
        "on_time": "בזמן",
        "cancelled": "בוטל",
        "none": "אין הגעות קרובות.",
        "next": "הנסיעה הבאה: {who}, {when}.",
        "no_realtime": "זמן אמת לא זמין כרגע, הזמנים לפי לוח הזמנים.",
        "leave_in": "כדי להספיק את {who} כדאי לצאת בעוד {n} דק׳.",
        "leave_now": "כדי להספיק את {who} כדאי לצאת עכשיו.",
        "today": "היום ב-{clock}",
        "tomorrow": "מחר ב-{clock}",
        "motzash": "במוצ״ש ב-{clock}",
        "weekday": "ביום {day} ב-{clock}",
        "alert_title": "{who} בדרך",
        "alert_minutes": "{stop}: {who} בעוד {n} דק׳ ({clock}).",
        "alert_now": "{stop}: {who} בעוד פחות מדקה.",
        "alert_stops": "במרחק {n} תחנות ממך.",
        "alert_stop": "במרחק תחנה אחת ממך.",
    },
    "en": {
        "line": "Line {line}",
        "train": "The train",
        "towards": "{who} to {dest}",
        "in": "in {n} min ({clock})",
        "now": "in under a minute",
        "at": "at {clock}",
        "live": "live",
        "scheduled": "timetable",
        "late": "{n} min late",
        "early": "{n} min early",
        "on_time": "on time",
        "cancelled": "cancelled",
        "none": "No upcoming arrivals.",
        "next": "Next service: {who}, {when}.",
        "no_realtime": (
            "Real-time is unavailable right now; times are from the timetable."
        ),
        "leave_in": "To catch {who}, leave in {n} min.",
        "leave_now": "To catch {who}, leave now.",
        "today": "today at {clock}",
        "tomorrow": "tomorrow at {clock}",
        "motzash": "Saturday night at {clock}",
        "weekday": "on {day} at {clock}",
        "alert_title": "{who} is on the way",
        "alert_minutes": "{stop}: {who} in {n} min ({clock}).",
        "alert_now": "{stop}: {who} in under a minute.",
        "alert_stops": "It is {n} stops away.",
        "alert_stop": "It is one stop away.",
    },
}


def language(lang: str | None) -> str:
    return "he" if (lang or "he").lower().startswith(("he", "iw")) else "en"


def _t(lang: str, key: str, **values: object) -> str:
    return _TEXT[lang][key].format(**values)


def clock(when: datetime) -> str:
    return when.astimezone(ISRAEL_TZ).strftime("%H:%M")


def who(arrival: Arrival, lang: str) -> str:
    """'קו 18 לכיוון תל אביב', או 'רכבת לכיוון חיפה'."""
    lang = language(lang)
    name = (
        _t(lang, "train")
        if arrival.route_type == ROUTE_TYPE_RAIL
        else _t(lang, "line", line=arrival.line_name)
    )
    dest = localized(arrival.destination, lang)
    return _t(lang, "towards", who=name, dest=dest) if dest else name


def when(eta: datetime, now: datetime, lang: str) -> str:
    """'היום ב-20:15', 'מחר ב-06:00', 'במוצ״ש ב-20:15', 'ביום ראשון ב-06:00'."""
    lang = language(lang)
    local = eta.astimezone(ISRAEL_TZ)
    today = now.astimezone(ISRAEL_TZ).date()
    at = clock(local)
    if local.weekday() == 5 and local.hour >= _MOTZASH_HOUR:
        return _t(lang, "motzash", clock=at)
    if local.date() == today:
        return _t(lang, "today", clock=at)
    if local.date() == today + timedelta(days=1):
        return _t(lang, "tomorrow", clock=at)
    days = _DAYS_HE if lang == "he" else _DAYS_EN
    return _t(lang, "weekday", day=days[local.weekday()], clock=at)


def _row(arrival: Arrival, lang: str, now: datetime) -> str:
    if arrival.cancelled:
        return (
            f"{who(arrival, lang)} {_t(lang, 'at', clock=clock(arrival.eta))}: "
            + _t(lang, "cancelled")
        )
    minutes = minutes_until(arrival.eta, now)
    timing = (
        _t(lang, "now")
        if minutes == 0
        else _t(lang, "at", clock=clock(arrival.eta))
        if minutes > 59
        else _t(lang, "in", n=minutes, clock=clock(arrival.eta))
    )
    notes = [_t(lang, "live" if arrival.is_realtime else "scheduled")]
    if (delay := arrival.delay_minutes) is not None:
        notes.append(
            _t(lang, "on_time")
            if delay == 0
            else _t(lang, "late" if delay > 0 else "early", n=abs(delay))
        )
    return f"{who(arrival, lang)} {timing}, {', '.join(notes)}"


def leave_hint(
    arrivals: list[Arrival], walk_minutes: int, lang: str, now: datetime
) -> str | None:
    """מתי לצאת כדי להספיק את הנסיעה הראשונה שעוד אפשר להגיע אליה."""
    if walk_minutes <= 0:
        return None
    lang = language(lang)
    walk = timedelta(minutes=walk_minutes)
    for arrival in arrivals:
        if arrival.cancelled or arrival.eta - walk < now - LEAVE_GRACE:
            continue
        minutes = minutes_until(arrival.eta - walk, now)
        if minutes == 0:
            return _t(lang, "leave_now", who=who(arrival, lang))
        return _t(lang, "leave_in", who=who(arrival, lang), n=minutes)
    return None


def board_summary(
    data: StopData,
    arrivals: list[Arrival],
    lang: str,
    now: datetime,
    walk_minutes: int = 0,
) -> str:
    """הלוח כמשפט אחד: מה מגיע ומתי, מה מאחר, ומה קורה כשאין כלום.

    ``arrivals`` הן השורות לסיכום, אחרי סינון הקווים של הקורא.
    """
    lang = language(lang)
    stop_name = data.stop.name
    if arrivals:
        rows = "; ".join(_row(a, lang, now) for a in arrivals[:SUMMARY_ROWS])
        parts = [f"{stop_name}: {rows}."]
        if hint := leave_hint(arrivals, walk_minutes, lang, now):
            parts.append(hint)
    else:
        parts = [f"{stop_name}: {_t(lang, 'none')}"]
    # השירות הבא נשלף רק כשאין שום נסיעה פעילה, גם אם יש בלוח נסיעות שבוטלו.
    following = data.next_service
    if following is not None and all(a.cancelled for a in arrivals):
        parts.append(
            _t(
                lang,
                "next",
                who=who(following, lang),
                when=when(following.eta, now, lang),
            )
        )
    if data.realtime_error:
        parts.append(_t(lang, "no_realtime"))
    return " ".join(parts)


def alert_text(
    stop_name: str,
    arrival: Arrival,
    stops_away: int | None,
    lang: str,
    now: datetime,
) -> tuple[str, str]:
    """כותרת וגוף להתראה שרכב מתקרב. מתי לצאת מוסיף הקורא (leave_hint)."""
    lang = language(lang)
    name = who(arrival, lang)
    minutes = minutes_until(arrival.eta, now)
    parts = [
        _t(lang, "alert_now", who=name, stop=stop_name)
        if minutes == 0
        else _t(
            lang,
            "alert_minutes",
            who=name,
            stop=stop_name,
            n=minutes,
            clock=clock(arrival.eta),
        )
    ]
    if stops_away == 1:
        parts.append(_t(lang, "alert_stop"))
    elif stops_away:
        parts.append(_t(lang, "alert_stops", n=stops_away))
    line = (
        _t(lang, "train")
        if arrival.route_type == ROUTE_TYPE_RAIL
        else _t(lang, "line", line=arrival.line_name)
    )
    return _t(lang, "alert_title", who=line), " ".join(parts)
