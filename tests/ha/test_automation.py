"""The automation triggers and conditions, driven through real automations.

Time is frozen and moved by hand. The mocked feed answers with absolute ETAs,
the way the real one does, so a board read later is the same board read later
-- and the stop's own polling keeps running underneath, as it would.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components import automation
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import condition as condition_helper
from homeassistant.helpers.trigger import TriggerConfig
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.israel_transit import trigger as trigger_module
from custom_components.israel_transit.api import Arrival, IsraelTransitError
from custom_components.israel_transit.const import DOMAIN
from custom_components.israel_transit.trigger import ArrivalTrigger

from .conftest import STOP, stop_device

START = datetime(2026, 10, 4, 9, 0, tzinfo=dt_util.UTC)


def bus(
    eta: datetime,
    *,
    line: str = "36",
    vehicle: str | None = "7",
    realtime: bool = True,
    delay: int | None = None,
) -> Arrival:
    return Arrival(
        line_name=line,
        eta=eta,
        is_realtime=realtime,
        destination="אור יהודה",
        operator="מטרופולין",
        line_ref="960",
        route_type="3",
        vehicle_ref=vehicle,
        delay_minutes=delay,
    )


def at(minutes: float) -> datetime:
    return START + timedelta(minutes=minutes)


@pytest.fixture
async def entry(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
    config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """One loaded stop with nothing due, so each test sets its own board."""
    freezer.move_to(START)
    mock_curlbus.arrivals.return_value = (STOP, [])
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def stop_target(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, Any]:
    device = stop_device(hass, "21023")
    assert device is not None
    return {"device_id": [device.id]}


@pytest.fixture
def board(
    hass: HomeAssistant, entry: MockConfigEntry, mock_curlbus: AsyncMock
) -> Callable[..., Any]:
    """Publish a new board and let the stop refresh with it."""

    async def _publish(*arrivals: Arrival, error: str | None = None) -> None:
        if error:
            mock_curlbus.arrivals.side_effect = IsraelTransitError(error)
        else:
            mock_curlbus.arrivals.side_effect = None
            mock_curlbus.arrivals.return_value = (STOP, list(arrivals))
        coordinator = next(iter(entry.runtime_data.values()))
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    return _publish


async def advance_to(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, when: datetime
) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass, when)
    await hass.async_block_till_done()


async def arrival_automation(
    hass: HomeAssistant,
    target: dict[str, Any],
    options: dict[str, Any],
    trigger: str = "arrival",
) -> list[ServiceCall]:
    calls = async_mock_service(hass, "test", "automation")
    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "bus",
                "triggers": [
                    {
                        "trigger": f"{DOMAIN}.{trigger}",
                        "target": target,
                        "options": options,
                    }
                ],
                "actions": [
                    {
                        "action": "test.automation",
                        "data": {
                            "line": "{{ trigger.line }}",
                            "stop_code": "{{ trigger.stop_code }}",
                            "eta": "{{ trigger.eta.isoformat() }}",
                            "is_realtime": "{{ trigger.is_realtime }}",
                            "delay": "{{ trigger.delay_minutes }}",
                        },
                    }
                ],
            }
        },
    )
    await hass.async_block_till_done()
    return calls


# --- the arrival trigger ----------------------------------------------------


async def test_fires_once_the_set_time_before_the_arrival(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(
        hass,
        stop_target,
        {"line": "36", "offset": {"minutes": 2}, "offset_type": "before"},
    )
    await board(bus(at(10)))

    await advance_to(hass, freezer, at(7.9))
    assert calls == []

    await advance_to(hass, freezer, at(8))
    assert len(calls) == 1
    # Templates render native types, so line "36" arrives as the number 36.
    assert str(calls[0].data["line"]) == "36"
    assert calls[0].data["stop_code"] == 21023
    assert calls[0].data["eta"] == at(10).isoformat()

    # Later boards still carry the same bus; it has had its turn.
    await advance_to(hass, freezer, at(9))
    await board(bus(at(10)))
    await advance_to(hass, freezer, at(12))
    assert len(calls) == 1


async def test_a_zero_offset_fires_at_the_arrival_itself(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(hass, stop_target, {})
    await board(bus(at(10)))

    await advance_to(hass, freezer, at(9.9))
    assert calls == []
    await advance_to(hass, freezer, at(10))
    assert len(calls) == 1


async def test_an_offset_after_fires_once_the_bus_has_left_the_board(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(
        hass, stop_target, {"offset": {"minutes": 3}, "offset_type": "after"}
    )
    await board(bus(at(5)))

    await advance_to(hass, freezer, at(5.5))
    await board()  # it arrived, and the feed no longer lists it
    assert calls == []

    await advance_to(hass, freezer, at(8))
    assert len(calls) == 1
    assert calls[0].data["eta"] == at(5).isoformat()


async def test_the_moment_follows_a_live_time_that_slips(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(hass, stop_target, {})
    await board(bus(at(10)))

    await advance_to(hass, freezer, at(5))
    await board(bus(at(15)))  # the same vehicle, running late

    await advance_to(hass, freezer, at(10))
    assert calls == []
    await advance_to(hass, freezer, at(15))
    assert len(calls) == 1
    assert calls[0].data["eta"] == at(15).isoformat()


async def test_a_moment_pulled_just_into_the_past_fires_straight_away(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(
        hass, stop_target, {"offset": {"minutes": 2}, "offset_type": "before"}
    )
    await board(bus(at(10)))

    await advance_to(hass, freezer, at(6))
    await board(bus(at(7)))  # due at 5 now: a minute late, inside the grace

    assert len(calls) == 1


async def test_a_moment_that_slipped_far_into_the_past_is_dropped_not_fired_late(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    validated = await ArrivalTrigger.async_validate_config(
        hass,
        {
            "target": stop_target,
            "options": {"offset": {"minutes": 5}, "offset_type": "before"},
        },
    )
    run_action, did_not_trigger = Mock(), Mock()
    detach = await ArrivalTrigger(
        hass,
        TriggerConfig(
            key=f"{DOMAIN}.arrival",
            target=validated["target"],
            options=validated["options"],
        ),
    ).async_attach_runner(run_action, did_not_trigger)

    await board(bus(at(20)))  # due at 15
    await advance_to(hass, freezer, at(10))
    await board(bus(at(12)))  # due at 7 now: three minutes ago

    run_action.assert_not_called()
    did_not_trigger.assert_called_once()
    assert did_not_trigger.call_args.args[0].reason == "missed"
    detach()


async def test_a_timetable_row_turning_live_is_still_one_trip(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
    mock_index: AsyncMock,
) -> None:
    calls = await arrival_automation(
        hass, stop_target, {"offset": {"minutes": 2}, "offset_type": "before"}
    )
    mock_index.async_departures.return_value = [
        bus(at(10), vehicle=None, realtime=False)
    ]
    await board(error="curlbus HTTP 500")

    await advance_to(hass, freezer, at(3))
    await board(bus(at(11)))  # real-time is back, and this is that bus

    await advance_to(hass, freezer, at(9))
    assert len(calls) == 1
    assert calls[0].data["is_realtime"] is True

    # Real-time drops again and the timetable row returns; it has fired.
    await board(error="curlbus HTTP 500")
    await advance_to(hass, freezer, at(12))
    assert len(calls) == 1


async def test_vehicles_of_a_frequent_line_each_fire_their_own_moment(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
    mock_index: AsyncMock,
) -> None:
    """Timetable rows two minutes apart carry no vehicle to tell them by.

    Each still has to be its own trip: neither may swallow the other, and the
    one that fired must not stop the next from firing.
    """
    calls = await arrival_automation(hass, stop_target, {})
    mock_index.async_departures.return_value = [
        bus(at(5), vehicle=None, realtime=False),
        bus(at(7), vehicle=None, realtime=False),
    ]
    await board(error="curlbus HTTP 500")

    await advance_to(hass, freezer, at(5))
    assert [call.data["eta"] for call in calls] == [at(5).isoformat()]
    await advance_to(hass, freezer, at(6))
    await advance_to(hass, freezer, at(7))
    assert [call.data["eta"] for call in calls] == [
        at(5).isoformat(),
        at(7).isoformat(),
    ]


async def test_a_bus_that_vanished_before_arriving_does_not_fire(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(hass, stop_target, {})
    await board(bus(at(10)))

    await advance_to(hass, freezer, at(3))
    await board()  # cancelled, or lost: it never reached the stop

    await advance_to(hass, freezer, at(11))
    assert calls == []


async def test_a_moment_from_before_the_automation_existed_does_not_fire(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    await board(bus(at(0.5)))
    await advance_to(hass, freezer, at(1))

    calls = await arrival_automation(hass, stop_target, {})
    await advance_to(hass, freezer, at(3))

    assert calls == []


async def test_turning_the_automation_off_cancels_what_it_was_waiting_for(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    """No timer may outlive the automation that set it."""
    timers: list[dict[str, bool]] = []
    real = trigger_module.async_track_point_in_utc_time

    def spy(hass: HomeAssistant, action: Any, when: datetime) -> Callable[[], None]:
        record = {"cancelled": False}
        timers.append(record)
        unsub = real(hass, action, when)

        def cancel() -> None:
            record["cancelled"] = True
            unsub()

        return cancel

    with patch.object(trigger_module, "async_track_point_in_utc_time", spy):
        calls = await arrival_automation(hass, stop_target, {})
        await board(bus(at(10)))
        assert timers

        await hass.services.async_call(
            automation.DOMAIN,
            "turn_off",
            {"entity_id": "automation.bus"},
            blocking=True,
        )
        await advance_to(hass, freezer, at(11))

    assert calls == []
    assert all(record["cancelled"] for record in timers)


async def test_reloading_the_integration_does_not_lose_a_waiting_trip(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry: MockConfigEntry,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(hass, stop_target, {})
    await board(bus(at(10)))

    await advance_to(hass, freezer, at(2))
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    await advance_to(hass, freezer, at(10))
    assert len(calls) == 1


async def test_other_lines_do_not_fire_a_line_trigger(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(hass, stop_target, {"line": "36"})
    await board(bus(at(2), line="91", vehicle="8"), bus(at(4)))

    await advance_to(hass, freezer, at(2))
    assert calls == []
    await advance_to(hass, freezer, at(4))
    assert [str(call.data["line"]) for call in calls] == ["36"]


async def test_a_target_that_is_not_a_stop_is_refused(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    validated = await ArrivalTrigger.async_validate_config(
        hass, {"target": {"device_id": ["not-a-device"]}, "options": {}}
    )
    trigger = ArrivalTrigger(
        hass,
        TriggerConfig(
            key=f"{DOMAIN}.arrival",
            target=validated["target"],
            options=validated["options"],
        ),
    )
    with pytest.raises(HomeAssistantError) as err:
        await trigger.async_attach_runner(Mock())
    assert err.value.translation_key == "invalid_target"


# --- the delay trigger ------------------------------------------------------


async def test_a_delay_fires_once_when_it_reaches_the_threshold(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    calls = await arrival_automation(
        hass, stop_target, {"min_delay": 5}, trigger="delay"
    )
    await board(bus(at(20), delay=4))
    assert calls == []

    await board(bus(at(22), delay=6))
    assert len(calls) == 1
    assert calls[0].data["delay"] == 6

    await board(bus(at(23), delay=7))
    assert len(calls) == 1


# --- conditions -------------------------------------------------------------


async def check(
    hass: HomeAssistant,
    condition: str,
    target: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> bool | None:
    config = await condition_helper.async_validate_condition_config(
        hass,
        {
            "condition": f"{DOMAIN}.{condition}",
            "target": target,
            "options": options or {},
        },
    )
    checker = await condition_helper.async_from_config(hass, config)
    return checker(hass)


async def test_is_arriving_within(
    hass: HomeAssistant, stop_target: dict[str, Any], board: Callable[..., Any]
) -> None:
    await board(bus(at(4)))

    assert await check(hass, "is_arriving_within", stop_target, {"minutes": 5})
    assert not await check(hass, "is_arriving_within", stop_target, {"minutes": 3})
    assert not await check(
        hass, "is_arriving_within", stop_target, {"line": "91", "minutes": 10}
    )
    assert await check(
        hass, "is_arriving_within", stop_target, {"line": "36", "minutes": 10}
    )


async def test_is_realtime_available(
    hass: HomeAssistant, stop_target: dict[str, Any], board: Callable[..., Any]
) -> None:
    await board(bus(at(4)))
    assert await check(hass, "is_realtime_available", stop_target)

    await board(error="curlbus HTTP 500")
    assert not await check(hass, "is_realtime_available", stop_target)


async def test_conditions_are_false_without_a_board(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    stop_target: dict[str, Any],
    board: Callable[..., Any],
) -> None:
    await board(bus(at(4)))
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not await check(hass, "is_arriving_within", stop_target, {"minutes": 60})
    assert not await check(hass, "is_realtime_available", stop_target)
