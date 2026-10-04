"""A miniature GTFS feed, in the exact on-disk shape the downloader produces.

Shared by the dependency-free index tests and the Home Assistant ones, so both
build a real index rather than asserting against mocks.
"""

from __future__ import annotations

import zlib
from pathlib import Path

# --- a miniature feed -------------------------------------------------------
# Two Dankal light rail routes (type 0, no real-time), one bus route (type 3,
# real-time), and a shared stop so the bus/light-rail split can be observed.

AGENCY = """agency_id,agency_name,agency_url,agency_timezone
25,תבל,http://example.com,Asia/Jerusalem
15,מטרופולין,http://example.com,Asia/Jerusalem
"""

ROUTES = """route_id,agency_id,route_short_name,route_long_name,route_desc,route_type,route_color
34447,25,1,תחנה מרכזית-פתח תקווה<->הקוממיות-בת ים-1#,79001-1-#,0,
34448,25,1,הקוממיות-בת ים<->תחנה מרכזית-פתח תקווה-2#,79001-2-#,0,
960,15,36,מסוף רדינג-תל אביב יפו<->מסוף אור יהודה-אור יהודה-1#,20036-1-0,3,
"""

TRIPS = """route_id,service_id,trip_id,trip_headsign,direction_id,shape_id,wheelchair_accessible
34447,1,tram-a,בת ים_הקוממיות,0,1,1
34447,1,tram-b,בת ים_הקוממיות,0,1,1
34448,1,tram-c,פתח תקווה_קרית אריה,1,1,1
960,1,bus-a,אור יהודה_מסוף,0,2,1
960,1,bus-b,אור יהודה_מסוף,0,2,1
"""

STOPS = """stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon,location_type,parent_station,zone_id
1,35962,הקוממיות,רחוב: אנה פרנק עיר: בת ים רציף:  קומה: ,32.010000,34.750000,0,,35962
2,36307,קרית אריה,רחוב: ז'בוטינסקי עיר: פתח תקווה רציף:  קומה: ,32.100000,34.870000,0,,36307
3,21023,ת. רכבת השלום,רחוב: גבעת התחמושת עיר: תל אביב יפו רציף:  קומה: ,32.072666,34.793390,0,,21023
4,99999,ללא עיר,no city field at all,31.000000,35.000000,0,,99999
"""

CALENDAR = """service_id,sunday,monday,tuesday,wednesday,thursday,friday,saturday,start_date,end_date
1,1,1,1,1,1,0,0,20260101,20261231
2,0,0,0,0,0,0,1,20260101,20261231
"""

# trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type
STOP_TIMES = """trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type
tram-a,12:00:00,12:00:00,1,1,0,1
tram-a,12:08:00,12:08:00,2,2,0,0
tram-a,12:22:00,12:22:00,3,3,1,0
tram-b,12:30:00,12:30:00,1,1,0,1
tram-b,12:38:00,12:38:00,2,2,0,0
tram-c,25:10:00,25:10:00,2,1,0,1
tram-c,25:20:00,25:20:00,1,2,0,0
bus-a,12:05:00,12:05:00,3,1,0,1
bus-a,12:15:00,12:15:00,1,2,0,0
bus-b,12:45:00,12:45:00,3,1,0,1
"""

MEMBERS = {
    "agency.txt": AGENCY,
    "routes.txt": ROUTES,
    "trips.txt": TRIPS,
    "stops.txt": STOPS,
    "calendar.txt": CALENDAR,
    "stop_times.txt": STOP_TIMES,
}


def write_feed(directory: Path) -> dict[str, Path]:
    """Write each member exactly as the downloader leaves it: raw deflate."""
    files = {}
    for name, text in MEMBERS.items():
        compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        payload = "﻿" + text.replace("\n", "\r\n")
        blob = compressor.compress(payload.encode("utf-8")) + compressor.flush()
        path = directory / f"{name}.deflate"
        path.write_bytes(blob)
        files[name] = path
    return files
