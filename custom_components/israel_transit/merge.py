"""Building one stop's board out of real-time, the timetable and rail.co.il.

Kept free of Home Assistant so the policy can be tested on its own.

שורה חיה ושורת לוח זמנים הן אותה נסיעה כשיש להן אותו קו ואותה שעת יציאה
מתחנת המוצא: SIRI מדווח אותה ב-departed, ו-GTFS בשורה הראשונה של הנסיעה. זה
מזהה נסיעה שלא תלוי בפורמט של trip_id, ולכן ממנו נגזר עיכוב אמיתי.
"""

from __future__ import annotations

import math
from datetime import datetime

from .api import Arrival, RouteInfo, line_sort_key, normalize_train_number
from .const import (
    DEPARTED_GRACE,
    MAX_ARRIVALS,
    NEAREST_MATCH_WINDOW,
    ORIGIN_MATCH_WINDOW,
    RAIL_MATCH_WINDOW,
    ROUTE_TYPE_RAIL,
)


def merge_board(
    live: list[Arrival],
    scheduled: list[Arrival],
    rail: list[Arrival],
    routes: list[RouteInfo],
    now: datetime,
) -> list[Arrival]:
    """לוח אחד: שורות חיות, נסיעות מלוח הזמנים ש-SIRI לא מציג, והעשרה מהרכבת.

    שורות לוח זמנים מהעבר משמשות רק להתאמה (אוטובוס באיחור), ולא מוצגות.
    """
    known = {route.line_ref for route in routes} | {
        row.line_ref for row in scheduled if row.line_ref
    }
    _enrich(live, routes)
    matches = _match(live, scheduled, known)

    board: list[Arrival] = []
    used: set[int] = set()
    for index, arrival in enumerate(live):
        match = matches.get(index)
        if match is not None:
            row, exact = match
            used.add(row)
            _adopt(arrival, scheduled[row], exact, arrival.line_ref in known)
        elif arrival.cancelled and not arrival.is_realtime:
            # סימון ביטול בלי ETA ובלי נסיעה מתוכננת: אין לו זמן להציג.
            continue
        board.append(arrival)

    cutoff = now - DEPARTED_GRACE
    board.extend(
        row
        for index, row in enumerate(scheduled)
        if index not in used and row.eta >= cutoff
    )
    _apply_rail(board, rail)
    board.sort(key=lambda a: (a.eta, line_sort_key(a.line_name)))
    return _capped(board)


def _enrich(arrivals: list[Arrival], routes: list[RouteInfo]) -> None:
    """Fill in what SIRI leaves out, from the route the arrival belongs to.

    curlbus reports a line id but not its mode, so without this every live bus
    would render in the card's "unknown mode" colour instead of the bus one.
    The GTFS route_id and the curlbus line_id are the same number, which is what
    makes the join possible. ברכבת SIRI מדווח מספר רכבת במקום שם קו, ולכן השם
    נלקח מה-route כמו בשורות לוח הזמנים, והמספר נשמר בנפרד.
    """
    by_line = {route.line_ref: route for route in routes}
    for arrival in arrivals:
        route = by_line.get(arrival.line_ref or "")
        if route is None:
            continue
        if arrival.route_type is None:
            arrival.route_type = route.route_type
        if not arrival.destination:
            arrival.destination = route.destination
        if not arrival.operator:
            arrival.operator = route.agency
        if route.route_type == ROUTE_TYPE_RAIL:
            _rename_train(arrival, route.short_name or route.line_ref)


def _rename_train(arrival: Arrival, line_name: str) -> None:
    if arrival.train_number is None:
        arrival.train_number = normalize_train_number(arrival.line_name)
    arrival.line_name = line_name


def _match(
    live: list[Arrival], scheduled: list[Arrival], known: set[str]
) -> dict[int, tuple[int, bool]]:
    """שורה חיה -> (שורת לוח זמנים, האם ההתאמה מדויקת). אחד-לאחד.

    שלב 1, מדויק: אותה יציאה מהמוצא, ואותו קו. כשהקו לא מוכר בתחנה (route_id
    שהשתנה במעבר פורמט) נדרשים אותו מפעיל וגם אותה תחנת יעד, כדי שרכבת לא תוצמד
    לרכבת בכיוון ההפוך שיצאה באותה דקה. שלב 2, לשורות שנשארו: הקרובה באותו קו.
    כל ההתאמות של שלב 1 קודמות, ולכן שורה בלי departed לא גונבת מקום של שורה
    מדויקת.
    """
    window = ORIGIN_MATCH_WINDOW.total_seconds()
    nearest = NEAREST_MATCH_WINDOW.total_seconds()
    candidates: list[tuple[int, float, float, int, int]] = []
    for i, arrival in enumerate(live):
        for j, row in enumerate(scheduled):
            if (
                arrival.departed is not None
                and row.origin is not None
                and _same_trip_line(arrival, row, known)
            ):
                gap = abs(arrival.departed.timestamp() - row.origin.timestamp())
                if gap <= window:
                    eta_gap = (
                        abs(arrival.eta.timestamp() - row.eta.timestamp())
                        if arrival.is_realtime
                        else math.inf
                    )
                    candidates.append((0, gap, eta_gap, i, j))
                    continue
            if (
                arrival.is_realtime
                and arrival.line_ref is not None
                and arrival.line_ref == row.line_ref
            ):
                gap = abs(arrival.eta.timestamp() - row.eta.timestamp())
                if gap <= nearest:
                    candidates.append((1, gap, 0.0, i, j))

    matches: dict[int, tuple[int, bool]] = {}
    taken: set[int] = set()
    for phase, _gap, _eta_gap, i, j in sorted(candidates):
        if i in matches or j in taken:
            continue
        matches[i] = (j, phase == 0)
        taken.add(j)
    return matches


def _same_trip_line(arrival: Arrival, row: Arrival, known: set[str]) -> bool:
    if arrival.line_ref in known:
        return arrival.line_ref == row.line_ref
    return (
        arrival.operator_id is not None
        and arrival.operator_id == row.operator_id
        and arrival.dest_code is not None
        and arrival.dest_code == row.dest_code
    )


def _adopt(arrival: Arrival, row: Arrival, exact: bool, line_known: bool) -> None:
    """מעביר לשורה החיה את מה שלוח הזמנים יודע עליה."""
    arrival.scheduled = row.eta
    if not arrival.is_realtime:
        # סימון ביטול: הזמן היחיד שיש לו הוא זה שבלוח הזמנים.
        arrival.eta = row.eta
    elif exact:
        arrival.delay_minutes = round((arrival.eta - row.eta).total_seconds() / 60)
    if arrival.route_type is None:
        arrival.route_type = row.route_type
    if not arrival.destination:
        arrival.destination = row.destination
    if not arrival.operator:
        arrival.operator = row.operator
    if not line_known:
        # הקו לא מוכר בתחנה, ולכן שמו ושיוכו נלקחים מהנסיעה המתוכננת.
        arrival.line_ref = row.line_ref
        arrival.route_type = row.route_type
        if row.route_type == ROUTE_TYPE_RAIL:
            _rename_train(arrival, row.line_name)
        else:
            arrival.line_name = row.line_name


def _apply_rail(board: list[Arrival], rail: list[Arrival]) -> None:
    """rail.co.il מעשיר את הרכבות שכבר בלוח ברציף, ובזמן אמת כשאין כזה.

    רכבת מותאמת לפי מספר הרכבת, ואם אין לשורה מספר, לפי הזמן המתוכנן. רכבת
    שלא נמצאה לה שורה נכנסת לבד, כמו קודם.
    """
    trains = [a for a in board if a.route_type == ROUTE_TYPE_RAIL]
    claimed: set[int] = set()
    for train in rail:
        target = next(
            (
                a
                for a in trains
                if id(a) not in claimed
                and train.train_number is not None
                and a.train_number == train.train_number
            ),
            None,
        ) or next(
            (
                a
                for a in trains
                if id(a) not in claimed
                and a.train_number is None
                and train.scheduled is not None
                and abs((a.scheduled or a.eta) - train.scheduled) <= RAIL_MATCH_WINDOW
            ),
            None,
        )
        if target is None:
            board.append(train)
            continue
        claimed.add(id(target))
        target.platform = target.platform or train.platform
        target.train_number = target.train_number or train.train_number
        if target.delay_minutes is None:
            target.delay_minutes = train.delay_minutes
        if not target.is_realtime and train.is_realtime:
            target.eta = train.eta
            target.is_realtime = True


def _capped(board: list[Arrival]) -> list[Arrival]:
    """עד MAX_ARRIVALS שורות, כשכל קו שומר את ההגעה הבאה שלו שאינה מבוטלת.

    בלי זה, בתחנה עמוסה קו נדיר היה נדחק מהלוח, ואיתו החיישן שעוקב אחריו.
    """
    if len(board) <= MAX_ARRIVALS:
        return board
    keep: list[int] = []
    lines: set[str] = set()
    for index, arrival in enumerate(board):
        if not arrival.cancelled and arrival.line_name not in lines:
            lines.add(arrival.line_name)
            keep.append(index)
    keep = keep[:MAX_ARRIVALS]
    reserved = set(keep)
    for index in range(len(board)):
        if len(keep) >= MAX_ARRIVALS:
            break
        if index not in reserved:
            keep.append(index)
    return [board[index] for index in sorted(keep)]
