"""הזיכרון של התחנות שכרטיסים בלוח המחוונים שואלים עליהן.

כרטיס יכול לנקוב בכל קוד תחנה בלי שהוגדרה לה תת-רשומה, אבל לוח הזמנים של תחנה
נשמר באינדקס רק אם ביקשו ממנו לשמור אותו. בלי זה תחנה ש-SIRI לא עונה עליה --
curlbus לא מכיר כל קוד, ורכבת, רכבת קלה והרכבליות נעדרות ממנו לגמרי -- מציגה לוח
ריק לתמיד: אין זמן אמת, ואין לוח זמנים ליפול אליו.

לכן כל תחנה שנשאלה בפועל נזכרת כאן ומצטרפת לקבוצה שהאינדקס שומר לה לוחות זמנים.
הרשימה חסומה בגודל ומתיישנת, כדי שתחנה שהציצו בה פעם אחת בחיפוש לא תתפוס בה
מקום לנצח.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    MAX_REMEMBERED_STOPS,
    REMEMBERED_STOP_MAX_AGE,
    STOP_REGISTRY_SAVE_DELAY,
)

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
_STORAGE_KEY = f"{DOMAIN}.card_stops"


class StopRegistry:
    """קודי התחנות שנשאלו לאחרונה, נשמרים בין הפעלות."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store[dict[str, Any]](hass, _STORAGE_VERSION, _STORAGE_KEY)
        self._seen: dict[int, float] = {}
        self._loaded = False

    @property
    def codes(self) -> frozenset[int]:
        return frozenset(self._seen)

    async def async_load(self) -> None:
        """קורא את הרשימה השמורה. נכשל בשקט ומתחיל ריק, כדי לא להפיל את ההתקנה."""
        if self._loaded:
            return
        self._loaded = True
        try:
            stored = await self._store.async_load()
        except HomeAssistantError as err:
            _LOGGER.warning(
                "Could not read the remembered stops (%s); starting with none", err
            )
            return

        cutoff = time.time() - REMEMBERED_STOP_MAX_AGE
        for code, seen in ((stored or {}).get("stops") or {}).items():
            try:
                code_int, seen_at = int(code), float(seen)
            except (TypeError, ValueError):
                continue
            if seen_at > cutoff:
                self._seen[code_int] = seen_at
        self._prune()
        if self._seen:
            _LOGGER.debug(
                "Remembered stops: %s",
                ", ".join(str(code) for code in sorted(self._seen)),
            )

    @callback
    def async_note(self, stop_code: int) -> bool:
        """מסמן שתחנה נשאלה עכשיו. מחזיר True אם היא חדשה לרשימה."""
        is_new = stop_code not in self._seen
        self._seen[stop_code] = time.time()
        self._prune()
        self._store.async_delay_save(self._data, STOP_REGISTRY_SAVE_DELAY)
        return is_new

    def _prune(self) -> None:
        cutoff = time.time() - REMEMBERED_STOP_MAX_AGE
        self._seen = {c: seen for c, seen in self._seen.items() if seen > cutoff}
        if len(self._seen) > MAX_REMEMBERED_STOPS:
            newest = sorted(self._seen.items(), key=lambda item: item[1], reverse=True)
            self._seen = dict(newest[:MAX_REMEMBERED_STOPS])

    @callback
    def _data(self) -> dict[str, Any]:
        return {"stops": {str(code): seen for code, seen in self._seen.items()}}
