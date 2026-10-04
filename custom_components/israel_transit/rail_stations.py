"""Israel Railways station ids.

rail.co.il numbers its stations independently of Ministry of Transport stop
codes, so a GTFS rail stop is matched to a station by name. The two feeds spell
the same station differently -- GTFS says ``תל אביב מרכז`` where rail.co.il says
``תל אביב - סבידור מרכז`` -- so matching is done on normalised word sets rather
than on the raw string.

Stations opened after this table was published (the Eastern Railway line, for
example) simply do not match, and those stops fall back to the GTFS timetable
without real-time delays.
"""

from __future__ import annotations

from typing import Final

# rail.co.il station id -> Hebrew name
RAIL_STATIONS: Final[dict[str, str]] = {
    "300": "פאתי מודיעין",
    "400": "מודיעין - מרכז",
    "680": "ירושלים - יצחק נבון",
    "700": "קריית חיים",
    "1220": "מרכזית המפרץ (לב המפרץ)",
    "1240": "יקנעם - כפר יהושע",
    "1250": "מגדל העמק - כפר ברוך",
    "1260": "עפולה ר.איתן",
    "1280": "בית שאן",
    "1300": "חוצות המפרץ",
    "1400": "קריית מוצקין",
    "1500": "עכו",
    "1600": "נהריה",
    "1820": "אחיהוד",
    "1840": "כרמיאל",
    "2100": "חיפה- מרכז השמונה",
    "2200": "חיפה - בת גלים",
    "2300": "חיפה - חוף הכרמל (ש' רזיאל)",
    "2500": "עתלית",
    "2800": "בנימינה",
    "2820": "קיסריה - פרדס חנה",
    "2940": "רעננה מערב",
    "2960": "רעננה דרום",
    "3100": "חדרה - מערב",
    "3300": "נתניה",
    "3310": "נתניה - ספיר",
    "3400": "בית יהושע",
    "3500": "הרצליה",
    "3600": "תל אביב - אוניברסיטה",
    "3700": "תל אביב - סבידור מרכז",
    "4100": "בני ברק",
    "4170": "פתח תקווה  - קריית אריה",
    "4250": "פתח תקווה - סגולה",
    "4600": "תל אביב - השלום",
    "4640": "צומת חולון",
    "4660": "חולון - וולפסון",
    "4680": "בת ים - יוספטל",
    "4690": "בת ים - קוממיות",
    "4800": 'כפר חב"ד',
    "4900": "תל אביב - ההגנה",
    "5000": "לוד",
    "5010": "רמלה",
    "5150": "לוד גני אביב",
    "5200": "רחובות (א' הדר)",
    "5300": "באר יעקב",
    "5410": "יבנה מזרח",
    "5800": "אשדוד עד הלום (מ' בר כוכבא)",
    "5900": "אשקלון",
    "6150": "קרית מלאכי - יואב",
    "6300": "בית שמש",
    "6500": "ירושלים - גן החיות התנכי",
    "6700": "ירושלים - מלחה",
    "6900": "מזכרת בתיה",
    "7000": "קריית גת",
    "7300": "באר שבע- צפון/אוניברסיטה",
    "7320": "באר שבע - מרכז",
    "7500": "דימונה",
    "8550": "להבים - רהט",
    "8600": "נמל תעופה בן גוריון",
    "8700": "כפר סבא - נורדאו (א' קוסטיוק)",
    "8800": "ראש העין - צפון",
    "9000": "יבנה מערב",
    "9100": "ראשון לציון - הראשונים",
    "9200": "הוד השרון - סוקולוב",
    "9600": "שדרות",
    "9650": "נתיבות",
    "9700": "אופקים",
    "9800": "ראשון לציון-משה דיין",
}

_PUNCTUATION: Final = "()-–’'\",./|"
_MATCH_THRESHOLD: Final = 0.6


def _tokens(name: str) -> frozenset[str]:
    """Normalise a station name into comparable words.

    Collapses the spelling differences between the two feeds: ``קריית``/``קרית``
    and a definite article on words long enough to still be meaningful without it
    (``האוניברסיטה`` -> ``אוניברסיטה``).
    """
    cleaned = name or ""
    for char in _PUNCTUATION:
        cleaned = cleaned.replace(char, " ")
    words = []
    for raw in cleaned.split():
        word = raw.replace("יי", "י")
        if word.startswith("ה") and len(word) > 3:
            word = word[1:]
        words.append(word)
    return frozenset(words)


_STATION_TOKENS: Final[dict[str, frozenset[str]]] = {
    station_id: _tokens(name) for station_id, name in RAIL_STATIONS.items()
}


def rail_station_id(name: str) -> str | None:
    """Map a GTFS rail stop name to a rail.co.il station id, or None.

    Scores each station by how much of the queried name it accounts for, with a
    small penalty for words it adds, so ``באר שבע צפון`` prefers
    ``באר שבע- צפון/אוניברסיטה`` over ``באר שבע - מרכז``. Returning None for an
    unknown station is the correct answer, not a failure.
    """
    words = _tokens(name)
    if not words:
        return None
    best_id: str | None = None
    best_score = 0.0
    for station_id, station_words in _STATION_TOKENS.items():
        overlap = len(words & station_words)
        if not overlap:
            continue
        score = overlap / len(words) - 0.01 * len(station_words - words)
        if score > best_score:
            best_id, best_score = station_id, score
    return best_id if best_score >= _MATCH_THRESHOLD else None
