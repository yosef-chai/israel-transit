"""עזרי הבדיקה של HA: מהחבילה הרשמית pytest-homeassistant, ואם אינה, מהקהילתית.

הרשמית יוצאת מ-2026.11 יחד עם core. הקהילתית נשארת לגרסת המינימום, שאין לה
חבילה רשמית.
"""

from __future__ import annotations

try:
    from pytest_homeassistant.common import (
        MockConfigEntry,
        async_fire_time_changed,
        async_mock_service,
    )
    from pytest_homeassistant.typing import WebSocketGenerator
except ImportError:
    from pytest_homeassistant_custom_component.common import (
        MockConfigEntry,
        async_fire_time_changed,
        async_mock_service,
    )
    from pytest_homeassistant_custom_component.typing import WebSocketGenerator

__all__ = [
    "MockConfigEntry",
    "WebSocketGenerator",
    "async_fire_time_changed",
    "async_mock_service",
]
