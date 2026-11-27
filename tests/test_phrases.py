"""המשפטים שנשלחים ל-Assist ולטלפון: מתי השירות חוזר, ומה אומרים על הלוח."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta

import pytest
from conftest import PACKAGE

api = importlib.import_module(f"{PACKAGE}.api")
phrases = importlib.import_module(f"{PACKAGE}.phrases")

IL = api.ISRAEL_TZ
# שישי, 4 בספטמבר 2026, 18:00.
FRIDAY_EVENING = datetime(2026, 9, 4, 18, 0, tzinfo=IL)


@pytest.mark.parametrize(
    ("eta", "lang", "expected"),
    [
        (datetime(2026, 9, 5, 20, 15, tzinfo=IL), "he", "במוצ״ש ב-20:15"),
        (datetime(2026, 9, 5, 20, 15, tzinfo=IL), "en", "Saturday night at 20:15"),
        (datetime(2026, 9, 4, 22, 0, tzinfo=IL), "he", "היום ב-22:00"),
        (datetime(2026, 9, 5, 10, 0, tzinfo=IL), "he", "מחר ב-10:00"),
        (datetime(2026, 9, 6, 6, 0, tzinfo=IL), "he", "ביום ראשון ב-06:00"),
        (datetime(2026, 9, 6, 6, 0, tzinfo=IL), "en-GB", "on Sunday at 06:00"),
    ],
)
def test_when_service_resumes(eta: datetime, lang: str, expected: str) -> None:
    assert phrases.when(eta, FRIDAY_EVENING, lang) == expected


def _arrival(minutes: int, **extra: object) -> object:
    return api.Arrival(
        line_name="18",
        eta=FRIDAY_EVENING + timedelta(minutes=minutes, seconds=30),
        is_realtime=True,
        destination="תל אביב",
        route_type="3",
        **extra,
    )


def test_a_row_says_line_destination_minutes_and_delay() -> None:
    row = phrases._row(_arrival(4, delay_minutes=2), "he", FRIDAY_EVENING)

    assert row == "קו 18 לכיוון תל אביב בעוד 4 דק׳ (18:04), זמן אמת, איחור של 2 דק׳"


def test_leave_hint_skips_a_vehicle_that_cannot_be_caught() -> None:
    """שש דקות הליכה: האוטובוס של עוד 3 דקות אבוד, זה של עוד 10 עוד בהישג."""
    rows = [_arrival(3), _arrival(10)]

    hint = phrases.leave_hint(rows, 6, "he", FRIDAY_EVENING)

    assert hint == "כדי להספיק את קו 18 לכיוון תל אביב כדאי לצאת בעוד 4 דק׳."
    assert phrases.leave_hint(rows, 0, "he", FRIDAY_EVENING) is None


def test_the_alert_names_the_stop_and_the_distance() -> None:
    title, message = phrases.alert_text(
        "ת. רכבת השלום", _arrival(5), 2, "he", FRIDAY_EVENING
    )

    assert title == "קו 18 בדרך"
    assert message == (
        "ת. רכבת השלום: קו 18 לכיוון תל אביב בעוד 5 דק׳ (18:05). במרחק 2 תחנות ממך."
    )
