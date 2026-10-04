<div dir="rtl">

# <img src="https://raw.githubusercontent.com/yosef-chai/israel-transit/main/custom_components/israel_transit/brand/icon.png" alt="" width="40" height="40"> Israel Transit

[![HACS Custom][hacs-badge]][hacs]
[![GitHub Release][release-badge]][release]
[![Home Assistant][ha-badge]][ha]
[![Validate][validate-badge]][validate]
[![Tests][tests-badge]][tests]
[![License][license-badge]][license]

זמני הגעה של תחבורה ציבורית בישראל ל-Home Assistant, בחבילה אחת:

- **אינטגרציה** שמביאה לכל תחנה את זמני ההגעה, ויוצרת חיישנים, טריגרים, תנאים ופעולות לאוטומציות.
- **כרטיס ללוח המחוונים** שמציג את הקווים הקרובים בתחנה, עם מסלול הקו ומיקום הרכב על מפה.

אוטובוסים, מוניות שירות, רכבת קלה בירושלים ובגוש דן, רכבלית חיפה, הכרמלית ורכבת ישראל.

**[יכולות](#יכולות)** · **[התקנה](#התקנה)** · **[הגדרה](#הגדרה)** · **[הכרטיס](#הכרטיס)** · **[אוטומציות](#אוטומציות)** · **[פתרון תקלות](#פתרון-תקלות)**

## יכולות

- **זמן אמת** לאוטובוסים ולמוניות שירות, מנתוני ה-SIRI של משרד התחבורה דרך [curlbus][curlbus].
- **לוח זמנים מקומי** מקובץ ה-GTFS הרשמי של משרד התחבורה, לכל מה שאין לו זמן אמת. הוא נשמר אצלך, ולכן ממשיך לעבוד גם כשהשירות החיצוני לא זמין.
- **רכבת ישראל** עם עיכובים ורציפים, כשבוחרים תחנת יעד.
- **חיפוש תחנות** לפי שם, עיר, רחוב או קוד תחנה, בכל 35 אלף התחנות בארץ.
- **הכרטיס.** עורך חזותי, בחירה וסידור של קווים, מסך פרטי תחנה, מסלול הקו עם מיקום הרכב על מפה, עברית ואנגלית, ימין לשמאל, מצב כהה והתאמה לתצוגת Sections.
- **אוטומציות.** טריגר "קו מגיע לתחנה" (גם כמה דקות לפני או אחרי), טריגר "רכב מתעכב", שני תנאים וארבע פעולות.
- **אמין.** זמנים מסומנים בבירור כשהם מלוח הזמנים ולא בזמן אמת. כשעדכון נכשל נשארים הזמנים האחרונים. כשמשהו דורש טיפול מופיעה הודעה ב**הגדרות ← תיקונים**.

### שימושים לדוגמה

- התראה לטלפון **שש דקות לפני** שהאוטובוס לעבודה מגיע לתחנה ליד הבית.
- כרטיס על טאבלט בכניסה שמראה **מתי יוצאים** לקו הבא.
- הודעה ברמקול כשהרכבת של הבוקר **מתעכבת** ביותר מעשר דקות.
- שאלה לעוזר הקולי "**מתי מגיע קו 36?**" שמפעילה סקריפט עם `get_arrivals`.

## התקנה

דורש Home Assistant 2026.7 ומעלה.

### דרך HACS (מומלץ)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][my-hacs-badge]][my-hacs]

1. לוחצים על הכפתור. או ב-HACS פותחים **⋮ ← Custom repositories** ומוסיפים את `https://github.com/yosef-chai/israel-transit` בקטגוריה **Integration**.
2. מחפשים **Israel Transit** ולוחצים **Download**.
3. מפעילים מחדש את Home Assistant.

### התקנה ידנית

1. מורידים את **Source code (zip)** מ[הגרסה האחרונה][release].
2. מעתיקים את `custom_components/israel_transit` לתיקייה `config/custom_components/`.
3. מפעילים מחדש את Home Assistant.

## הגדרה

[![Open your Home Assistant instance and start setting up a new integration.][my-flow-badge]][my-flow]

1. לוחצים על הכפתור, או נכנסים ל**הגדרות ← מכשירים ושירותים ← הוספת שילוב ← Israel Transit**, ומאשרים.
2. בעמוד של Israel Transit לוחצים **הוספת תחנה**, מחפשים את התחנה ובוחרים אותה.

בפעם הראשונה האינטגרציה מורידה את לוח הזמנים של משרד התחבורה (כ-90MB) ובונה ממנו קובץ מקומי. זה לוקח כמה שניות במחשב רגיל וכמה דקות ב-Raspberry Pi. עד שזה מסתיים מוצג מסך התקדמות.

כל תחנה מקבלת מכשיר משלה. את ההגדרות שלה משנים ב-**⋮ ← הגדרה מחדש**:

| אפשרות | ברירת מחדל | הסבר |
| --- | --- | --- |
| קווים במעקב | — | לכל קו שנבחר נוצרים שני חיישנים משלו. בלי קווים יש רק את חיישני התחנה. |
| תדירות עדכון | ‏60 שניות | לפחות 30. ראו [שימוש הוגן](#שימוש-הוגן). |
| תחנת יעד ברכבת | — | רק בתחנות רכבת. בלעדיה אין עיכובים ורציפים. |

### ישויות

| ישות | הסבר |
| --- | --- |
| `sensor.<stop>_next_arrival` | שעת ההגעה הקרובה (timestamp). |
| `sensor.<stop>_next_arrival_in` | כמה דקות עד ההגעה הקרובה. |
| `sensor.<stop>_line_<line>` | שעת ההגעה הקרובה של קו במעקב. |
| `sensor.<stop>_line_<line>_in` | כמה דקות עד שהקו במעקב מגיע. |
| `sensor.<stop>_arrivals` | מספר ההגעות (אבחון). המאפיין `arrivals` מכיל את כל הרשימה, והוא לא נשמר בהיסטוריה. |

לחיישני ההגעה יש המאפיין `is_realtime`, שאומר אם הזמן מדיווח חי או מלוח הזמנים.

### איך הנתונים מתעדכנים

- כל תחנה מתעדכנת לפי תדירות העדכון שלה. כל התחנות חולקות בקשה אחת ל-curlbus בכל סבב.
- לוח הזמנים המקומי נבדק פעם ביום ונבנה מחדש רק כשמשרד התחבורה מפרסם קובץ חדש (בערך פעם בשבוע), או כשמוסיפים תחנה. בזמן הבנייה הקובץ הקודם ממשיך לעבוד.
- רכב שכבר עבר בתחנה יורד מהרשימה תוך דקה.
- כשאין זמן אמת, הזמנים מגיעים מלוח הזמנים ומסומנים כך. אם לאף תחנת אוטובוס לא היה זמן אמת חצי שעה, מופיעה הודעה ב**תיקונים**, והיא נעלמת כשהשירות חוזר.

### כיסוי

| סוג | זמן אמת | לוח זמנים |
| --- | :---: | :---: |
| אוטובוסים ומוניות שירות | ✓ | ✓ בתחנות שהוגדרו |
| רכבת קלה (ירושלים, גוש דן) | — | ✓ |
| רכבלית חיפה והכרמלית | — | ✓ |
| רכבת ישראל | ✓ עם תחנת יעד | ✓ |

## הכרטיס

מוסיפים את **Israel Transit** מעורך הלוח, מחפשים תחנה ובוחרים קווים. כל האפשרויות נמצאות בעורך החזותי. לחיצה על כותרת הכרטיס פותחת את פרטי התחנה, ולחיצה על שורה פותחת את מסלול הקו.

| שם | סוג | ברירת מחדל | הסבר |
| --- | --- | --- | --- |
| `type` | string | **חובה** | `custom:israel-transit-card` |
| `stop_code` | number | **חובה** | קוד התחנה של משרד התחבורה. |
| `lines` | list | כל הקווים | אילו קווים להציג. |
| `order` | `time` \| `lines` | `time` | לפי זמן ההגעה, או לפי הסדר של `lines`. |
| `title` | string | שם התחנה | כותרת הכרטיס. |
| `max_arrivals` | number | `6` | כמה שורות להציג. |
| `max_lines` | number | `0` | כמה קווים שונים להציג. `0` בלי הגבלה. |
| `rail_destination` | string | — | תחנת יעד ברכבת, לעיכובים ורציפים. |
| `show_header` | boolean | `true` | כותרת. |
| `show_city` | boolean | `true` | העיר של התחנה. |
| `show_stop_code` | boolean | `true` | קוד התחנה. |
| `show_destination` | boolean | `true` | יעד הקו. |
| `show_operator` | boolean | `true` | המפעיל. |
| `show_mode_icon` | boolean | `false` | סמל של אוטובוס, רכבת וכו'. |
| `show_realtime_tag` | boolean | `true` | התווית "לפי לוח זמנים" על זמנים שאינם בזמן אמת. |
| `show_platform` | boolean | `true` | רציף. |
| `show_delay` | boolean | `true` | עיכוב. |
| `show_clock` | boolean | `false` | שעת ההגעה לצד הדקות. |
| `show_map` | boolean | `true` | מפה במסלול הקו. |

<div dir="ltr">

```yaml
type: custom:israel-transit-card
stop_code: 21023
lines: ["480", "36"]
order: lines
```

</div>

במפה של מסלול הקו, הטבעת הכתומה היא התחנה שלך והטבעת האדומה היא הרכב. מיקום חי יש רק לאוטובוסים ולמוניות שירות.

## אוטומציות

בטריגרים ובתנאים בוחרים תחנה כיעד (target): את המכשיר שלה או אחת מהישויות שלה.

### טריגר "קו מגיע לתחנה"

מופעל כשרכב מגיע לתחנה, או זמן קבוע לפני או אחרי.

| שדה | הסבר |
| --- | --- |
| `line` | מספר הקו. ריק לכל הקווים. |
| `offset` | כמה זמן לפני או אחרי ההגעה. ריק לרגע ההגעה. |
| `offset_type` | `before` או `after`. |

<div dir="ltr">

```yaml
triggers:
  - trigger: israel_transit.arrival
    target:
      device_id: DEVICE_ID
    options:
      line: "18"
      offset:
        minutes: 6
      offset_type: before
actions:
  - action: notify.mobile_app_phone
    data:
      message: >
        קו {{ trigger.line }} ל{{ trigger.destination }} מגיע
        ב-{{ as_local(trigger.eta).strftime('%H:%M') }}
```

</div>

טוב לדעת:

- הטריגר מופעל פעם אחת לכל נסיעה. כשהזמן החי משתנה, רגע ההפעלה זז איתו.
- אם הרגע הוקדם ועבר, הטריגר עדיין מופעל עד שתי דקות אחריו. מאוחר יותר הוא לא מופעל, וב-trace של האוטומציה מופיע שהרגע הוחמץ.
- עם `after` הטריגר מופעל גם אחרי שהרכב ירד מהרשימה. נסיעה שבוטלה לפני שהגיעה לא מפעילה אותו.
- רגע שעבר בזמן ש-Home Assistant היה כבוי, או לפני שהאוטומציה נטענה, לא יופעל.

### טריגר "רכב מתעכב"

מופעל פעם אחת לכל נסיעה, כשהעיכוב מגיע ל-`min_delay` דקות. בפועל זה רלוונטי לרכבת, בתחנה שהוגדרה לה תחנת יעד.

<div dir="ltr">

```yaml
triggers:
  - trigger: israel_transit.delay
    target:
      device_id: DEVICE_ID
    options:
      min_delay: 10
```

</div>

בשני הטריגרים זמינים המשתנים `trigger.stop_code`, ‏`trigger.line`, ‏`trigger.line_ref`, ‏`trigger.destination`, ‏`trigger.operator`, ‏`trigger.eta`, ‏`trigger.minutes`, ‏`trigger.is_realtime`, ‏`trigger.vehicle_ref`, ‏`trigger.platform` ו-`trigger.delay_minutes`.

### תנאים

| תנאי | מתקיים כש |
| --- | --- |
| `israel_transit.is_arriving_within` | רכב (של `line`, או של כל קו) מגיע בתוך `minutes` דקות. |
| `israel_transit.is_realtime_available` | לתחנה יש עכשיו זמן אמת. |

אם בוחרים כמה תחנות, מספיק שאחת מהן מקיימת את התנאי. תחנה שעדיין אין לה נתונים לא מקיימת אותו.

<div dir="ltr">

```yaml
conditions:
  - condition: israel_transit.is_arriving_within
    target:
      device_id: DEVICE_ID
    options:
      line: "36"
      minutes: 10
```

</div>

### פעולות

| פעולה | הסבר |
| --- | --- |
| `israel_transit.get_arrivals` | מחזירה את זמני ההגעה לכל קוד תחנה, גם לתחנה שלא הוגדרה. |
| `israel_transit.refresh_stop` | מעדכנת תחנה מוגדרת עכשיו, בלי לחכות לסבב הבא. |
| `israel_transit.search_stops` | מחפשת תחנות ומחזירה `stops`. |
| `israel_transit.rebuild_timetable` | מורידה ובונה מחדש את לוח הזמנים המקומי. |

כל הגעה ש-`get_arrivals` מחזירה כוללת `line_name`, ‏`line_ref`, ‏`eta`, ‏`minutes`, ‏`is_realtime`, ‏`destination`, ‏`operator`, ‏`route_type`, ‏`platform` ו-`delay_minutes`, ובזמן אמת גם `vehicle_lat`, ‏`vehicle_lon` ו-`departed`.

<details>
<summary>"מתי מגיע ה-36?" ברמקול</summary>

<div dir="ltr">

```yaml
actions:
  - action: israel_transit.get_arrivals
    data:
      stop_code: 21023
      lines: ["36"]
    response_variable: board
  - action: tts.speak
    target:
      entity_id: tts.home_assistant_cloud
    data:
      media_player_entity_id: media_player.kitchen
      message: >
        {% set next = board.arrivals | first %}
        {% if next %}
          קו {{ next.line_name }} מגיע בעוד {{ next.minutes }} דקות
        {% else %}
          אין כרגע הגעות
        {% endif %}
```

</div>
</details>

<details>
<summary>התראה רק בימי עבודה, עם חיישן הדקות</summary>

<div dir="ltr">

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.home_stop_line_18_in
    below: 5
conditions:
  - condition: state
    entity_id: binary_sensor.workday_sensor
    state: "on"
actions:
  - action: notify.mobile_app_phone
    data:
      message: "קו 18 מגיע בעוד {{ states('sensor.home_stop_line_18_in') }} דקות"
```

</div>
</details>

## שימוש הוגן

curlbus הוא שירות קהילתי חינמי. כדי לא להעמיס עליו, כל התחנות חולקות בקשה אחת בכל סבב, כרטיס בלשונית מוסתרת מפסיק לשאול, והספירה לאחור מתעדכנת בדפדפן בין הסבבים. לוח הזמנים נקרא מהקובץ המקומי בלי רשת. כדאי להשאיר את תדירות העדכון על 60 שניות אם אין סיבה טובה לשנות.

## מגבלות ידועות

- **אין זמן אמת לרכבת הקלה, לרכבלית ולכרמלית**, כי הן לא מדווחות לנתוני ה-SIRI של משרד התחבורה. מוצג לוח הזמנים.
- **לוח זמנים לאוטובוסים נשמר רק לתחנות שהוגדרו.** לתחנה אחרת (למשל בכרטיס או ב-`get_arrivals`) יש רק זמן אמת.
- **זמן האמת תלוי ב-curlbus.** כשהוא לא זמין מוצג לוח הזמנים.
- **רכבת ישראל** מדווחת עיכובים לפי מסלול, ולכן צריך תחנת יעד. המפתח של rail.co.il הוא המפתח הציבורי מהאתר שלהם, והוא עלול להשתנות.
- **הורדה ראשונה** של כ-90MB, ועוד מקום זמני בדיסק בזמן הבנייה.
- **לוחות במצב YAML.** אי אפשר לרשום בהם משאב אוטומטית. מוסיפים את `/israel_transit/israel-transit-card.js` כמשאב מסוג JavaScript module (הכתובת המדויקת מופיעה בלוג).

## פתרון תקלות

### "לא ניתן להוריד את לוח הזמנים" בתיקונים

לוחצים על ההודעה ואז **שליחה**. לוח הזמנים נבנה מחדש מתוך החלון. אם זה נכשל שוב, החלון מציג את השגיאה וההודעה נשארת. בינתיים אין זמנים לרכבת הקלה ולרכבת.

### "אין זמני הגעה בזמן אמת" בתיקונים

curlbus לא ענה חצי שעה. הזמנים מוצגים מלוח הזמנים, וההודעה נעלמת לבד כשהשירות חוזר.

### אין זמני אוטובוס כש-curlbus לא זמין

לוח זמנים לאוטובוסים נשמר רק לתחנות שהוגדרו. מוסיפים את התחנה, ולוח הזמנים נבנה מחדש כדי לכלול אותה.

### זמני רכבת בלי עיכוב או רציף

לא נבחרה תחנת יעד. מוסיפים אותה ב-**⋮ ← הגדרה מחדש** של התחנה, או ב-`rail_destination` בכרטיס.

### הכרטיס לא מופיע, או מציג "אין חיבור כרגע"

אחרי התקנה או עדכון מרעננים את הדפדפן ומנקים את המטמון שלו. "אין חיבור כרגע" מעל הזמנים אומר שהעדכון האחרון נכשל, למשל בזמן הפעלה מחדש. הכרטיס מתעדכן כשהחיבור חוזר.

### לוג דיבאג ואבחון

מוסיפים את זה ל-`configuration.yaml` ומפעילים מחדש:

<div dir="ltr">

```yaml
logger:
  default: warning
  logs:
    custom_components.israel_transit: debug
```

</div>

קובץ האבחון נמצא ב**הגדרות ← מכשירים ושירותים ← Israel Transit ← ⋮ ← הורדת אבחון**. יש בו את מצב לוח הזמנים, ההגעות האחרונות והשגיאה האחרונה. כדאי לצרף אותו כש[פותחים תקלה][issues].

## הסרה

1. נכנסים ל**הגדרות ← מכשירים ושירותים ← Israel Transit** ובוחרים **⋮ ← מחיקה**. התחנות, הישויות ולוח הזמנים המקומי (`config/israel_transit/`) נמחקים.
2. מסירים את Israel Transit ב-HACS (או מוחקים את `config/custom_components/israel_transit`) ומפעילים מחדש את Home Assistant.
3. אם הכרטיס עדיין מופיע ב**הגדרות ← לוחות מחוונים ← ⋮ ← משאבים**, מוחקים אותו משם.

## פיתוח

<div dir="ltr">

```bash
npm ci && npm run build
python -m pytest
python -m pytest -c pytest-ha.ini
python -m mypy
python -m ruff check custom_components tests
```

</div>

`npm run build` בונה את הכרטיס מ-`src/` אל `custom_components/israel_transit/www/`. אפשר לראות את הכרטיס בלי Home Assistant: מריצים `python -m http.server 8777` ופותחים את `http://localhost:8777/dev/preview.html`.

## קרדיטים

הנתונים באדיבות משרד התחבורה, [curlbus][curlbus] של elad661 ורכבת ישראל.

## רישיון

[MIT][license] © Yosef Chai

</div>

[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[release]: https://github.com/yosef-chai/israel-transit/releases/latest
[release-badge]: https://img.shields.io/github/v/release/yosef-chai/israel-transit
[ha]: https://www.home-assistant.io
[ha-badge]: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fyosef-chai%2Fisrael-transit%2Fmain%2Fhacs.json&query=%24.homeassistant&prefix=%E2%89%A5%20&label=Home%20Assistant&logo=homeassistant&color=41BDF5
[validate]: https://github.com/yosef-chai/israel-transit/actions/workflows/validate.yml
[validate-badge]: https://img.shields.io/github/actions/workflow/status/yosef-chai/israel-transit/validate.yml?branch=main&label=validate
[tests]: https://github.com/yosef-chai/israel-transit/actions/workflows/tests.yml
[tests-badge]: https://img.shields.io/github/actions/workflow/status/yosef-chai/israel-transit/tests.yml?branch=main&label=tests
[license]: https://github.com/yosef-chai/israel-transit/blob/main/LICENSE
[license-badge]: https://img.shields.io/github/license/yosef-chai/israel-transit
[issues]: https://github.com/yosef-chai/israel-transit/issues
[curlbus]: https://curlbus.app
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=yosef-chai&repository=israel-transit&category=integration
[my-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[my-flow]: https://my.home-assistant.io/redirect/config_flow_start/?domain=israel_transit
[my-flow-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
