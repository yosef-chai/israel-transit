"""Constants for the Israel Transit integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "israel_transit"
INTEGRATION_TITLE: Final = "Israel Transit"
# Stops are subentries: "Add stop" on the integration page, one device each.
SUBENTRY_TYPE_STOP: Final = "stop"

# --- Data sources -----------------------------------------------------------
# Real-time arrivals (SIRI passthrough). Community service, be polite.
CURLBUS_BASE: Final = "https://curlbus.app"
# Ministry of Transport GTFS, mirrored by Hasadna. Fresh, CORS-enabled, complete.
STRIDE_BASE: Final = "https://open-bus-stride-api.hasadna.org.il"
# The Ministry of Transport GTFS feed: 154 MB, served with range support.
GTFS_URL: Final = "https://gtfs.mot.gov.il/gtfsfiles/israel-public-transportation.zip"
GTFS_DB_FILENAME: Final = "gtfs.sqlite"
# The Ministry republishes weekly; checking daily costs one tiny request.
GTFS_CHECK_INTERVAL_HOURS: Final = 24

# Israel Railways. Key is public, taken from rail.co.il's own main.js bundle.
RAIL_BASE: Final = "https://rail-api.rail.co.il/rjpa/api/v1"
RAIL_API_KEY: Final = "5e64d66cf03f4547bcac5de2de06b566"

# Identifies us to the services we depend on, all of which are free and
# community- or state-run. Note the deliberate spacing: the Stride API sits
# behind a filter that answers 403 to any User-Agent containing the
# unspaced string "HomeAssistant".
USER_AGENT: Final = "israel-transit/1.0 (Home Assistant integration)"

# --- Config keys ------------------------------------------------------------
CONF_STOP_CODE: Final = "stop_code"
CONF_STOP_NAME: Final = "stop_name"
CONF_LINES: Final = "lines"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_RAIL_DESTINATION: Final = "rail_destination"
CONF_QUERY: Final = "query"

# hass.data keys
DATA_CLIENTS: Final = "clients"
DATA_FRONTEND: Final = "frontend_registered"
DATA_STOP_CACHE: Final = "stop_cache"

# curlbus is a single free community service. 60s is the floor we ask of it.
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30

# Shared by every open dashboard asking about a stop nobody has configured.
# Held at the polling interval on purpose: a card refreshes twice a minute, and
# without this an unconfigured stop would be fetched upstream twice as often as
# a configured one -- for data that is no fresher either way.
STOP_CACHE_TTL: Final = float(DEFAULT_SCAN_INTERVAL)
# הזיכרון הזה מתמלא מכל קוד תחנה שמישהו שאל עליו, ולכן חייב גג.
STOP_CACHE_MAX_ENTRIES: Final = 64

# How many upcoming arrivals we keep per stop.
MAX_ARRIVALS: Final = 40

# A vehicle stays on the board this long past its time: a bus "due now" is
# often still pulling in, and dropping it at the exact minute looks like a
# glitch. Past this it has left.
DEPARTED_GRACE: Final = timedelta(seconds=60)

# A live rail.co.il train and a timetabled GTFS train are the same train when
# their timetabled departures are this close.
RAIL_MATCH_WINDOW: Final = timedelta(minutes=1)

# --- Stops the dashboard asks about -----------------------------------------
# תחנות שכרטיס שאל עליהן נכנסות לאינדקס כמו תחנות מוגדרות. הגג והתיישנות שומרים
# על הרשימה קטנה, כי כל תחנה בה מוסיפה שורות לוח זמנים לכל בנייה של האינדקס.
MAX_REMEMBERED_STOPS: Final = 40
REMEMBERED_STOP_MAX_AGE: Final = 30 * 24 * 3600.0
STOP_REGISTRY_SAVE_DELAY: Final = 30
# בנייה מחדש עולה הורדה של כ-90MB, ולוח מחוונים נטען עם כל הכרטיסים יחד --
# ההמתנה הקצרה אוספת את כולם לבנייה אחת.
NEW_STOP_INDEX_DELAY: Final = 20
# גג לניסיונות חוזרים כשהבנייה נכשלת: אחרת כל רענון של כרטיס היה מזמין עוד אחת.
TIMETABLE_REQUEST_COOLDOWN: Final = 1800.0

# --- Real-time backoff ------------------------------------------------------
# curlbus עונה 500 לצמיתות על קודי תחנה שמסד הנתונים הסטטי שלו לא מכיר. אחרי
# כמה כישלונות רצופים אין טעם לשאול אותו כל דקה, וגם לא מנומס.
REALTIME_FAILURES_BEFORE_BACKOFF: Final = 3
REALTIME_BACKOFF_BASE: Final = 60.0
REALTIME_BACKOFF_MAX: Final = 600.0
# Every watched bus stop without real-time for this long is an outage of the
# service, worth a repair issue rather than just a quieter board.
REALTIME_OUTAGE_ISSUE_AFTER: Final = 1800.0

# --- GTFS route types -------------------------------------------------------
# https://gtfs.org/schedule/reference/#routestxt
ROUTE_TYPE_TRAM: Final = "0"  # light rail: Jerusalem (Cfir), Tel Aviv (Tevel/Dankal)
ROUTE_TYPE_RAIL: Final = "2"  # Israel Railways
ROUTE_TYPE_BUS: Final = "3"
ROUTE_TYPE_CABLE_TRAM: Final = "5"  # Rakevelit (Cable Express), Carmelit
ROUTE_TYPE_SHERUT: Final = "8"  # shared taxi
ROUTE_TYPE_FLEXIBLE: Final = "715"  # demand-responsive

# Verified 2026-08-30 against the live feeds: only these report to SIRI.
# Light rail, cable tram and rail return no real-time visits at all, so their
# arrivals come from the GTFS timetable and are labelled as such in the card.
REALTIME_ROUTE_TYPES: Final = frozenset(
    {ROUTE_TYPE_BUS, ROUTE_TYPE_SHERUT, ROUTE_TYPE_FLEXIBLE}
)

# Everything SIRI does not carry, and which therefore needs a stored
# timetable: both light rail systems, Israel Railways, and the cable lines.
NON_REALTIME_ROUTE_TYPES: Final = frozenset(
    {ROUTE_TYPE_TRAM, ROUTE_TYPE_RAIL, ROUTE_TYPE_CABLE_TRAM, "6", "7"}
)

ROUTE_TYPE_ICONS: Final = {
    ROUTE_TYPE_TRAM: "mdi:tram",
    ROUTE_TYPE_RAIL: "mdi:train",
    ROUTE_TYPE_BUS: "mdi:bus",
    ROUTE_TYPE_CABLE_TRAM: "mdi:gondola",
    ROUTE_TYPE_SHERUT: "mdi:taxi",
    ROUTE_TYPE_FLEXIBLE: "mdi:bus-clock",
}

# --- Frontend ---------------------------------------------------------------
CARD_FILENAME: Final = "israel-transit-card.js"
CARD_URL: Final = f"/{DOMAIN}/{CARD_FILENAME}"
# The brand/ directory, which Home Assistant itself reads for the integration
# icon (2026.3+), served so the card's editor can show the same mark.
BRAND_URL: Final = f"/{DOMAIN}/brand"

# --- Actions ----------------------------------------------------------------
SERVICE_GET_ARRIVALS: Final = "get_arrivals"

# --- Repairs ----------------------------------------------------------------
ISSUE_INDEX_FAILED: Final = "gtfs_index_failed"
ISSUE_REALTIME_UNAVAILABLE: Final = "realtime_unavailable"

# --- Automations ------------------------------------------------------------
SERVICE_REFRESH_STOP: Final = "refresh_stop"
SERVICE_SEARCH_STOPS: Final = "search_stops"
SERVICE_REBUILD_TIMETABLE: Final = "rebuild_timetable"
CONF_LINE: Final = "line"
CONF_OFFSET: Final = "offset"
CONF_MIN_DELAY: Final = "min_delay"
CONF_MINUTES: Final = "minutes"
CONF_LIMIT: Final = "limit"
# A trigger whose moment slipped into the past -- a late ETA, a slow poll --
# still fires within this window, and never after it: a "bus is coming" that
# arrives ten minutes late is worse than none.
TRIGGER_GRACE: Final = timedelta(minutes=2)
# A live row and a timetabled one of the same line this close are one trip.
TRIGGER_MATCH_WINDOW: Final = timedelta(minutes=3)
# Nothing a trigger waits on, or remembers having fired, outlives this.
TRIGGER_MAX_AGE: Final = timedelta(hours=2)
TRIGGER_MAX_OFFSET: Final = timedelta(hours=2)

ATTRIBUTION: Final = (
    "Ministry of Transport GTFS and SIRI (via curlbus), and Israel Railways"
)
