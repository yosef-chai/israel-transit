"""Sensors for a stop: the next arrival and the full board, plus one per line.

The next arrival is a timestamp, which the frontend already shows as "in 5
minutes". There is no minutes-until sensor: Home Assistant's sensor docs say a
duration "should only change when the device reports a new value, not because
time passes". "Five minutes before line 18" is the arrival trigger's offset.
"""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import Arrival, localized
from .const import (
    ATTRIBUTION,
    CONF_LINES,
    DOMAIN,
    ROUTE_TYPE_ICONS,
)
from .coordinator import IsraelTransitConfigEntry, IsraelTransitCoordinator, StopData

# All entities of a stop are served from one coordinator refresh, so there is
# nothing to rate-limit here.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IsraelTransitConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up each stop's sensors against the subentry that owns them."""
    registry = er.async_get(hass)
    for subentry_id, coordinator in entry.runtime_data.items():
        entities: list[SensorEntity] = [
            NextArrivalSensor(coordinator),
            ArrivalCountSensor(coordinator),
        ]
        entities.extend(
            NextArrivalSensor(coordinator, line)
            for line in coordinator.subentry.data.get(CONF_LINES, [])
        )

        _async_prune(registry, entry, subentry_id, {e.unique_id for e in entities})
        # The entities, and the device they create, belong to the stop the
        # user added rather than to the integration as a whole.
        async_add_entities(entities, config_subentry_id=subentry_id)


@callback
def _async_prune(
    registry: er.EntityRegistry,
    entry: IsraelTransitConfigEntry,
    subentry_id: str,
    keep: set[str | None],
) -> None:
    """Drop entities this stop no longer provides.

    Untracking a line has to take its two sensors with it. Left alone they
    linger in the registry as `unavailable` forever, which looks like a fault
    rather than like a setting the user changed.
    """
    for existing in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            existing.config_subentry_id == subentry_id
            and existing.unique_id not in keep
        ):
            registry.async_remove(existing.entity_id)


class IsraelTransitEntity(CoordinatorEntity[IsraelTransitCoordinator], SensorEntity):
    """Shared identity and lookup for every entity of one stop."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self, coordinator: IsraelTransitCoordinator, line: str | None = None
    ) -> None:
        super().__init__(coordinator)
        self._line = line
        stop_code = coordinator.stop_code
        suffix = f"_line_{line}" if line else ""
        self._attr_unique_id = f"{stop_code}{suffix}_{self.entity_suffix}"
        if line:
            self._attr_translation_key = f"line_{self.entity_suffix}"
            self._attr_translation_placeholders = {"line": line}
        else:
            self._attr_translation_key = self.entity_suffix
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(stop_code))},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Israel Transit",
            name=coordinator.subentry.title,
        )

    entity_suffix: str = ""

    @property
    def _arrivals(self) -> list[Arrival]:
        # A stop whose very first read failed has no data at all. Its entities
        # exist and read unavailable, rather than the whole integration failing
        # to set up and taking every other stop's entities with it. The
        # coordinator types .data as always present, which is why the annotation
        # is here: it is None until an update succeeds.
        data: StopData | None = self.coordinator.data
        if data is None:
            return []
        rows = data.for_line(self._line) if self._line else data.upcoming()
        # נסיעה מבוטלת נשארת בלוח כדי שהכרטיס יראה אותה, אבל היא לא "ההגעה הבאה".
        return [a for a in rows if not a.cancelled]

    @property
    def _next(self) -> Arrival | None:
        return next(iter(self._arrivals), None)

    @property
    def _language(self) -> str:
        return self.hass.config.language if self.hass else "he"

    @property
    def icon(self) -> str | None:
        arrival = self._next
        if arrival and arrival.route_type in ROUTE_TYPE_ICONS:
            return ROUTE_TYPE_ICONS[arrival.route_type]
        return "mdi:bus-clock"


class NextArrivalSensor(IsraelTransitEntity):
    """When the next vehicle arrives."""

    entity_suffix = "next_arrival"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        arrival = self._next
        return arrival.eta if arrival else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        arrival = self._next
        if arrival is None:
            return {}
        return {
            "line": arrival.line_name,
            "destination": localized(arrival.destination, self._language) or None,
            "operator": localized(arrival.operator, self._language) or None,
            "is_realtime": arrival.is_realtime,
            "platform": arrival.platform,
            # 0 הוא "בזמן", None הוא "לא ידוע": עיכוב מדווח רק כשהנסיעה זוהתה.
            "delay_minutes": arrival.delay_minutes,
            "scheduled": arrival.scheduled,
            "train_number": arrival.train_number,
        }


class ArrivalCountSensor(IsraelTransitEntity):
    """How many arrivals are known, and the full list for templates."""

    entity_suffix = "arrivals"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    # The list is for templates and the card, not for history. Keeping it out of
    # the recorder is what lets it stay on the entity at all.
    _unrecorded_attributes = frozenset({"arrivals", "lines", "updated_at"})

    @property
    def native_value(self) -> int:
        return len(self._arrivals)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        data: StopData | None = self.coordinator.data
        if data is None:
            return {}
        now = dt_util.utcnow()
        arrivals = data.upcoming(now)
        return {
            "stop_code": data.stop.code,
            "stop_name": data.stop.name,
            "has_realtime": data.has_realtime,
            "updated_at": data.updated_at,
            "arrivals": [a.as_dict(self._language, now) for a in arrivals],
            "lines": sorted({a.line_name for a in arrivals}),
        }
