"""Turning an action's or a trigger's target into the stops it names.

A stop is a device, and its entities hang off that device, so either one picked
in the automation editor leads to the same stop code. Shared by the actions,
the triggers and the conditions so that all three read a target the same way.

The target is expanded by Home Assistant's own helper, so areas, floors,
labels -- and, from 2026.11, exclusions -- mean here what they mean everywhere
else, instead of being accepted by the schema and silently ignored.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.target import (
    TargetEntityChangeTracker,
    TargetSelection,
    async_extract_referenced_entity_ids,
)

from .const import DOMAIN


@callback
def async_resolve_stops(hass: HomeAssistant, target: Mapping[str, Any]) -> set[int]:
    """The stop codes behind everything a target names.

    Anything that is not one of this integration's stops is ignored rather than
    raised on: the caller decides whether an empty result is an error.
    """
    selected = async_extract_referenced_entity_ids(
        hass, TargetSelection(dict(target)), expand_group=False
    )
    entities = er.async_get(hass)
    device_ids = set(selected.referenced_devices)
    for entity_id in selected.referenced | selected.indirectly_referenced:
        entry = entities.async_get(entity_id)
        if entry is not None and entry.platform == DOMAIN and entry.device_id:
            device_ids.add(entry.device_id)

    devices = dr.async_get(hass)
    codes: set[int] = set()
    for device_id in device_ids:
        if (device := devices.async_get(device_id)) is None:
            continue
        codes.update(
            int(value)
            for domain, value in device.identifiers
            if domain == DOMAIN and value.isdigit()
        )
    return codes


class StopTargetTracker(TargetEntityChangeTracker):
    """מודיע מחדש על התחנות של target בכל שינוי ב-registry.

    כך טריגר על אזור או תווית מתעדכן כשתחנה נכנסת אליהם או יוצאת מהם, כמו
    הטריגרים של HA עצמו, ולא רק לפי מה שהיה ברגע שהאוטומציה עלתה.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        target: Mapping[str, Any],
        on_change: Callable[[set[int]], None],
    ) -> None:
        super().__init__(hass, TargetSelection(dict(target)), lambda ids: ids)
        self._target = dict(target)
        self._on_change = on_change

    @callback
    def _handle_entities_update(self, tracked_entities: set[str]) -> None:
        self._on_change(async_resolve_stops(self._hass, self._target))


async def async_track_stops(
    hass: HomeAssistant,
    target: Mapping[str, Any],
    on_change: Callable[[set[int]], None],
) -> CALLBACK_TYPE:
    """Call ``on_change`` with the target's stops now, and on every change."""
    return await StopTargetTracker(hass, target, on_change).async_setup()
