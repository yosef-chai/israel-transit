"""Diagnostics for a configured stop.

Nothing here is personal beyond the stop the user chose, which is a public bus
stop code and is the one thing a support request needs.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import DATA_CLIENTS, DOMAIN
from .coordinator import (
    Clients,
    IsraelTransitConfigEntry,
    IsraelTransitCoordinator,
)


def _stop_diagnostics(
    hass: HomeAssistant, coordinator: IsraelTransitCoordinator
) -> dict[str, Any]:
    data = coordinator.data
    return {
        "settings": dict(coordinator.subentry.data),
        "update_interval": str(coordinator.update_interval),
        "last_update_success": coordinator.last_update_success,
        "last_exception": str(coordinator.last_exception)
        if coordinator.last_exception
        else None,
        "code": coordinator.stop_code,
        "resolved": data.stop.as_dict() if data else None,
        "has_realtime": data.has_realtime if data else None,
        "realtime_error": data.realtime_error if data else None,
        # The arrivals themselves, since a wrong time is the usual report.
        "arrivals": [a.as_dict(hass.config.language) for a in data.arrivals]
        if data
        else [],
        "routes": [r.as_dict() for r in data.routes] if data else [],
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: IsraelTransitConfigEntry
) -> dict[str, Any]:
    """Return every configured stop, and the state of the shared GTFS index."""
    clients: Clients | None = hass.data.get(DOMAIN, {}).get(DATA_CLIENTS)
    index = clients.index if clients else None

    return {
        "stops": [
            _stop_diagnostics(hass, coordinator)
            # Unset when the entry failed to load, which is when this is wanted.
            for coordinator in (getattr(entry, "runtime_data", None) or {}).values()
        ],
        "gtfs_index": {
            "available": index.available if index else False,
            "path": str(index.db_path) if index else None,
            "last_build": index.last_build if index else None,
            "last_error": index.last_error if index else None,
            # התחנות שיש להן לוח זמנים מול אלה שמבקשים אותו: פער מסביר לוח ריק.
            "indexed_stops": sorted(index.indexed_stops) if index else [],
            "card_stops": sorted(clients.stops.codes) if clients else [],
        },
    }
