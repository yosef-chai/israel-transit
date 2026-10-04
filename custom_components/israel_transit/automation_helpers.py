"""Turning an action's or a trigger's target into the stops it names.

A stop is a device, and its entities hang off that device, so either one picked
in the automation editor leads to the same stop code. Shared by the actions,
the triggers and the conditions so that all three read a target the same way.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


@callback
def async_resolve_stops(hass: HomeAssistant, target: Mapping[str, Any]) -> set[int]:
    """The stop codes behind the devices and entities a target names.

    Anything that is not one of this integration's stops is ignored rather than
    raised on: the caller decides whether an empty result is an error.
    """
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    device_ids: set[str] = set(cv.ensure_list(target.get(ATTR_DEVICE_ID)))
    for entity_id in cv.ensure_list(target.get(ATTR_ENTITY_ID)):
        entry = entities.async_get(entity_id)
        if entry is not None and entry.platform == DOMAIN and entry.device_id:
            device_ids.add(entry.device_id)

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
