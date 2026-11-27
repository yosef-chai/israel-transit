"""היציאה מהבית: זמן הליכה, השירות הבא, פולינג אדפטיבי, התראות לטלפון ו-Assist."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import llm
from homeassistant.util import dt as dt_util

from custom_components.israel_transit import llm as transit_llm
from custom_components.israel_transit.api import Arrival, RouteStop, Stop
from custom_components.israel_transit.const import (
    DOMAIN,
    EVENT_ARRIVAL_ALERT,
    IDLE_POLL_MAX,
    INTEGRATION_TITLE,
    SPARSE_POLL,
)
from custom_components.israel_transit.coordinator import StopData, poll_interval

from .common import MockConfigEntry, async_mock_service
from .conftest import STOP, stop_subentry
from .test_automation import START, advance_to, arrival_automation, at, bus

BASE = timedelta(seconds=60)


@pytest.fixture(autouse=True)
def hebrew(hass: HomeAssistant) -> None:
    """המשפטים נכתבים בשפת השרת; בבדיקות היא אנגלית כברירת מחדל."""
    hass.config.language = "he"


def _board(*arrivals: Arrival, next_service: Arrival | None = None) -> StopData:
    return StopData(stop=STOP, arrivals=list(arrivals), next_service=next_service)


# --- adaptive polling -------------------------------------------------------


@pytest.mark.parametrize(
    ("board", "expected"),
    [
        # אוטובוס בעוד 10 דקות: הקצב הרגיל.
        (_board(bus(at(10))), BASE),
        # הקרוב בעוד 40 דקות: כל חמש דקות.
        (_board(bus(at(40))), SPARSE_POLL),
        # לילה: השירות חוזר בעוד 8 שעות, ולכן רבע שעה.
        (_board(next_service=bus(at(8 * 60))), IDLE_POLL_MAX),
        # השירות חוזר בעוד 18 דקות: מתעוררים 10 דקות לפני.
        (_board(next_service=bus(at(18))), timedelta(minutes=8)),
        # בעוד 5 דקות: לא פחות מהקצב הרגיל.
        (_board(next_service=bus(at(5))), BASE),
        # לוח ריק בלי לוח זמנים ידוע לא אומר כלום.
        (_board(), BASE),
        # נסיעה מבוטלת לא נחשבת תנועה.
        (_board(bus(at(3), cancelled=True), next_service=bus(at(600))), IDLE_POLL_MAX),
    ],
)
def test_poll_interval(board: StopData, expected: timedelta) -> None:
    assert poll_interval(BASE, board, START) == expected


async def test_an_empty_board_polls_less_and_says_when_service_resumes(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    mock_curlbus: AsyncMock,
    mock_index: AsyncMock,
) -> None:
    coordinator = next(iter(loaded_entry.runtime_data.values()))
    resumes = Arrival(
        line_name="36",
        eta=dt_util.utcnow() + timedelta(hours=9),
        is_realtime=False,
        destination="אור יהודה",
        route_type="3",
    )
    mock_curlbus.arrivals.return_value = (STOP, [])
    mock_index.async_next_departure.return_value = resumes

    await coordinator.async_refresh()

    assert coordinator.data.next_service is resumes
    assert coordinator.update_interval == IDLE_POLL_MAX
    assert coordinator.data.refresh_seconds == IDLE_POLL_MAX.total_seconds()

    answer = await hass.services.async_call(
        DOMAIN,
        "get_arrivals",
        {"stop_code": 21023},
        blocking=True,
        return_response=True,
    )
    assert answer["arrivals"] == []
    assert answer["next_service"]["line_name"] == "36"
    assert "הנסיעה הבאה: קו 36" in answer["summary"]

    # השירות חזר: חזרה לקצב הרגיל.
    mock_curlbus.arrivals.return_value = (
        STOP,
        [bus(dt_util.utcnow() + timedelta(minutes=4))],
    )
    await coordinator.async_refresh()
    assert coordinator.update_interval == coordinator.base_interval
    assert coordinator.data.next_service is None


# --- walking time -----------------------------------------------------------


@pytest.fixture
async def walk_entry(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_index: AsyncMock,
    mock_curlbus: AsyncMock,
    mock_card_registration: None,
) -> MockConfigEntry:
    """תחנה עם 6 דקות הליכה וקו 36 במעקב."""
    freezer.move_to(START)
    mock_curlbus.arrivals.return_value = (STOP, [])
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=INTEGRATION_TITLE,
        unique_id=DOMAIN,
        data={},
        subentries_data=[stop_subentry(walk_minutes=6, lines=["36"])],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _publish(
    hass: HomeAssistant, entry: MockConfigEntry, mock_curlbus: AsyncMock, *rows: Arrival
) -> None:
    mock_curlbus.arrivals.return_value = (STOP, list(rows))
    await next(iter(entry.runtime_data.values())).async_refresh()
    await hass.async_block_till_done()


async def test_leave_by_is_the_first_bus_still_worth_walking_to(
    hass: HomeAssistant, walk_entry: MockConfigEntry, mock_curlbus: AsyncMock
) -> None:
    """שש דקות הליכה: האוטובוס של עוד 4 דקות אבוד, יוצאים לזה של עוד 12."""
    await _publish(hass, walk_entry, mock_curlbus, bus(at(4)), bus(at(12), vehicle="8"))
    registry = er.async_get(hass)

    stop_entity = registry.async_get_entity_id("sensor", DOMAIN, "21023_leave_by")
    line_entity = registry.async_get_entity_id(
        "sensor", DOMAIN, "21023_line_36_leave_by"
    )
    assert stop_entity and line_entity
    state = hass.states.get(stop_entity)
    assert state is not None
    assert state.state == at(6).isoformat()
    assert state.attributes["walk_minutes"] == 6
    assert hass.states.get(line_entity).state == at(6).isoformat()

    answer = await hass.services.async_call(
        DOMAIN,
        "get_arrivals",
        {"stop_code": 21023},
        blocking=True,
        return_response=True,
    )
    assert answer["walk_minutes"] == 6
    assert [row["leave_minutes"] for row in answer["arrivals"]] == [-2, 6]
    assert "כדאי לצאת בעוד 6 דק׳" in answer["summary"]


async def test_no_leave_by_sensor_without_a_walking_time(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, "21023_leave_by") is None


async def test_the_leave_trigger_fires_the_walk_and_the_heads_up_before(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    walk_entry: MockConfigEntry,
    mock_curlbus: AsyncMock,
) -> None:
    target = {
        "entity_id": [
            er.async_get(hass).async_get_entity_id(
                "sensor", DOMAIN, "21023_next_arrival"
            )
        ]
    }
    calls = await arrival_automation(
        hass, target, {"line": "36", "offset": {"minutes": 2}}, trigger="leave"
    )
    await _publish(hass, walk_entry, mock_curlbus, bus(at(20)))

    # 20 - 6 הליכה - 2 התראה מוקדמת = דקה 12.
    await advance_to(hass, freezer, at(11.9))
    assert calls == []
    await advance_to(hass, freezer, at(12))
    assert len(calls) == 1
    assert calls[0].data["minutes"] == 8


# --- "notify me when it's close" --------------------------------------------


@pytest.fixture
def notify_calls(hass: HomeAssistant) -> list[Any]:
    return async_mock_service(hass, "notify", "send_message")


@pytest.fixture
def board(
    hass: HomeAssistant, walk_entry: MockConfigEntry, mock_curlbus: AsyncMock
) -> Callable[..., Any]:
    async def _set(*rows: Arrival) -> None:
        await _publish(hass, walk_entry, mock_curlbus, *rows)

    return _set


async def _notify(hass: HomeAssistant, **data: Any) -> None:
    await hass.services.async_call(
        DOMAIN,
        "notify_arrival",
        {"stop_code": 21023, "line": "36", **data},
        blocking=True,
    )


async def test_the_alert_fires_once_when_the_bus_comes_within_the_minutes(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    board: Callable[..., Any],
    notify_calls: list[Any],
) -> None:
    events = []
    hass.bus.async_listen(EVENT_ARRIVAL_ALERT, events.append)
    await board(bus(at(10)))
    await _notify(hass, minutes=5, notify_entity_id=["notify.phone"])

    await advance_to(hass, freezer, at(4.9))
    assert notify_calls == []

    await advance_to(hass, freezer, at(6))
    assert len(notify_calls) == 1
    call = notify_calls[0]
    assert call.data["entity_id"] == ["notify.phone"]
    assert call.data["title"] == "קו 36 בדרך"
    assert call.data["message"].startswith(
        "ת. רכבת השלום: קו 36 לכיוון אור יהודה בעוד 4 דק׳"
    )
    assert len(events) == 1
    assert events[0].data["line"] == "36"

    await advance_to(hass, freezer, at(8))
    assert len(notify_calls) == 1


async def test_a_bus_already_close_when_the_alert_is_set_is_skipped(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    board: Callable[..., Any],
    notify_calls: list[Any],
) -> None:
    await board(bus(at(3)), bus(at(20), vehicle="8"))
    await _notify(hass, notify_entity_id=["notify.phone"])

    await advance_to(hass, freezer, at(4))
    assert notify_calls == []

    await advance_to(hass, freezer, at(15.5))
    assert len(notify_calls) == 1
    assert "בעוד 4 דק׳" in notify_calls[0].data["message"]


async def test_the_alert_by_stops_uses_the_live_position(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    board: Callable[..., Any],
    notify_calls: list[Any],
    mock_index: AsyncMock,
) -> None:
    """חמש תחנות בקו, התחנה שלנו האחרונה; ההתראה ל-2 תחנות לפני."""
    lats = [32.030, 32.040, 32.050, 32.060]
    mock_index.async_route_stops.return_value = [
        RouteStop(i + 1, Stop(100 + i, f"תחנה {i}", None, lat, 34.79))
        for i, lat in enumerate(lats)
    ] + [RouteStop(5, STOP)]

    def near(stop: int) -> Arrival:
        row = bus(at(15))
        row.vehicle_lat, row.vehicle_lon = lats[stop], 34.79
        return row

    await board(near(0))  # ארבע תחנות לפני
    await _notify(hass, stops=2, notify_entity_id=["notify.phone"])
    await advance_to(hass, freezer, at(1))
    assert notify_calls == []

    await board(near(2))  # שתי תחנות לפני
    await advance_to(hass, freezer, at(2))
    assert len(notify_calls) == 1
    assert "במרחק 2 תחנות ממך" in notify_calls[0].data["message"]


async def test_without_a_target_the_alert_goes_to_the_users_phone(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    board: Callable[..., Any],
    notify_calls: list[Any],
) -> None:
    user = await hass.auth.async_create_user("rider")
    phone = MockConfigEntry(domain="mobile_app", data={"user_id": user.id})
    phone.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "notify", "mobile_app", "pixel", config_entry=phone, suggested_object_id="pixel"
    )
    await board(bus(at(10)))

    await hass.services.async_call(
        DOMAIN,
        "notify_arrival",
        {"stop_code": 21023, "line": "36"},
        blocking=True,
        context=Context(user_id=user.id),
    )
    await advance_to(hass, freezer, at(6))

    assert notify_calls[0].data["entity_id"] == ["notify.pixel"]


async def test_no_phone_and_no_target_is_an_error(
    hass: HomeAssistant, board: Callable[..., Any]
) -> None:
    with pytest.raises(ServiceValidationError) as raised:
        await _notify(hass)
    assert raised.value.translation_key == "no_notify_target"


async def test_a_line_that_does_not_stop_here_is_an_error(
    hass: HomeAssistant, board: Callable[..., Any]
) -> None:
    with pytest.raises(ServiceValidationError) as raised:
        await _notify(hass, line="999", notify_entity_id=["notify.phone"])
    assert raised.value.translation_key == "unknown_line"


async def test_a_cancelled_alert_never_fires(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    board: Callable[..., Any],
    notify_calls: list[Any],
) -> None:
    await board(bus(at(10)))
    await _notify(hass, notify_entity_id=["notify.phone"])
    await hass.services.async_call(
        DOMAIN,
        "cancel_arrival_alert",
        {"stop_code": 21023, "line": "36", "notify_entity_id": ["notify.phone"]},
        blocking=True,
    )

    await advance_to(hass, freezer, at(7))
    assert notify_calls == []


# --- Assist -----------------------------------------------------------------


def _llm_context() -> llm.LLMContext:
    return llm.LLMContext(
        platform="test",
        context=None,
        language="he",
        assistant="conversation",
        device_id=None,
    )


async def test_assist_gets_a_summary_of_every_stop(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    tools = transit_llm.async_get_tools(hass, _llm_context(), llm.LLM_API_ASSIST)
    assert tools is not None
    assert transit_llm.async_get_tools(hass, _llm_context(), "other") is None
    tool = tools.tools[0]
    assert tool.name == "israel_transit__get_arrivals"

    result = await tool.async_call(
        hass, llm.ToolInput(tool_name=tool.name, tool_args={}), _llm_context()
    )
    data = getattr(result, "data", result)

    stop = data["stops"][0]
    assert stop["stop_code"] == 21023
    assert stop["summary"].startswith("ת. רכבת השלום: קו 36")
    assert stop["arrivals"][0]["line_name"] == "36"
    assert "vehicle_lat" not in stop["arrivals"][0]


async def test_assist_is_told_which_stops_exist(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    tool = transit_llm.GetArrivalsTool()

    result = await tool.async_call(
        hass,
        llm.ToolInput(tool_name=tool.name, tool_args={"stop_code": 1}),
        _llm_context(),
    )

    assert "21023" in getattr(result, "data", result)["error"]
