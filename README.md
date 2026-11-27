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

- **זמן אמת** לאוטובוסים, למוניות שירות ולרכבת ישראל, מנתוני ה-SIRI של משרד התחבורה דרך [curlbus][curlbus]. כש-curlbus לא עונה לתחנה, זמן ההגעה מוערך ממיקום האוטובוס בנתוני [open-bus][open-bus] של הסדנא לידע ציבורי, ומסומן "משוער".
- **לוח זמנים מקומי** מקובץ ה-GTFS הרשמי של משרד התחבורה. כל נסיעה חיה מזוהה מולו, וכך רואים איחור או הקדמה גם באוטובוס. נסיעה שעוד לא משדרת מוצגת לפי לוח הזמנים, ונסיעה שבוטלה מוצגת מחוקה. הקובץ נשמר אצלך, ולכן ממשיך לעבוד גם כשהשירות החיצוני לא זמין.
- **רכבת ישראל** עם מספר רכבת, ועם רציף כשבוחרים תחנת יעד.
- **חיפוש תחנות** לפי שם, עיר, רחוב או קוד תחנה, בכל 35 אלף התחנות בארץ, ורשימה של התחנות הקרובות לבית כבר בפתיחה.
- **זמן הליכה לתחנה.** מגדירים כמה דקות הולכים מהבית, ומקבלים חיישן "לצאת עד", טריגר "הזמן לצאת לתחנה" ובכרטיס "לצאת בעוד 3 דק׳".
- **התראה לטלפון בלחיצה.** בפרטי הקו: "תזכירו לי כשהוא 5 דקות מכאן" או "2 תחנות מכאן", לאפליקציית Home Assistant בטלפון.
- **לילה, שבת וחג.** במקום "אין הגעות", הכרטיס והחיישנים אומרים מתי השירות חוזר: "הנסיעה הבאה: קו 36, במוצ״ש ב-20:15".
- **פולינג חסכוני.** כשאין נסיעות בשעות הקרובות התחנה נשאלת פעם ברבע שעה, וחוזרת לקצב הרגיל עשר דקות לפני הנסיעה הבאה.
- **Assist.** עוזר קולי עם מודל שפה עונה על "מתי הקו הבא לתל אביב?" או "הרכבת שלי מאחרת?" בלי סקריפט.
- **הכרטיס.** עורך חזותי, בחירה וסידור של קווים, מסך פרטי תחנה, מסלול הקו עם מיקום הרכב על מפה, מפה של כל הרכבים שבדרך לתחנה, עברית ואנגלית, ימין לשמאל, מצב כהה והתאמה לתצוגת Sections.
- **אוטומציות.** טריגרים "קו מגיע לתחנה" (גם כמה דקות לפני או אחרי), "הזמן לצאת לתחנה" ו"רכב מתעכב", שני תנאים ושש פעולות.
- **אמין.** זמנים מסומנים בבירור כשהם מלוח הזמנים ולא בזמן אמת. כשעדכון נכשל נשארים הזמנים האחרונים. כשמשהו דורש טיפול מופיעה הודעה ב**הגדרות ← תיקונים**.

### שימושים לדוגמה

- התראה לטלפון **כשצריך לצאת מהבית** כדי להספיק את האוטובוס לעבודה.
- נורה בכניסה שמהבהבת, או רמקול שאומר "קו 402 בדרך, כדאי לצאת בעוד 2 דקות".
- כרטיס על טאבלט בכניסה שמראה **מתי יוצאים** לקו הבא, ומפה של כל האוטובוסים שבדרך.
- הודעה ברמקול כשהרכבת של הבוקר **מתעכבת** ביותר מעשר דקות.
- שאלה לעוזר הקולי: "**מתי מגיע קו 36?**".

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
2. בעמוד של Israel Transit לוחצים **הוספת תחנה**, ובוחרים אחת מהתחנות הקרובות לבית או מחפשים תחנה אחרת. הרשימה מופיעה כשמיקום הבית מוגדר ב**הגדרות ← מערכת ← כללי**.

בפעם הראשונה האינטגרציה מורידה את לוח הזמנים של משרד התחבורה (כ-170MB, ובפורמט החדש שמשרד התחבורה עובר אליו כ-300MB) ובונה ממנו קובץ מקומי. זה לוקח כמה שניות במחשב רגיל וכמה דקות ב-Raspberry Pi. עד שזה מסתיים מוצג מסך התקדמות.

כל תחנה מקבלת מכשיר משלה. את ההגדרות שלה משנים ב-**⋮ ← הגדרה מחדש**:

| אפשרות | ברירת מחדל | הסבר |
| --- | --- | --- |
| קווים במעקב | - | לכל קו שנבחר נוצר חיישן משלו. בלי קווים יש רק את חיישני התחנה. |
| תדירות עדכון | ‏60 שניות | לפחות 30. ראו [שימוש הוגן](#שימוש-הוגן). |
| זמן הליכה לתחנה | ‏0 | דקות מהבית לתחנה. מוסיף את חיישני "לצאת עד" ומפעיל את הטריגר [הזמן לצאת לתחנה](#טריגר-הזמן-לצאת-לתחנה). ‏0 מכבה. |
| תחנת יעד ברכבת | - | רק בתחנות רכבת. בלעדיה אין רציפים. |

### ישויות

| ישות | הסבר |
| --- | --- |
| `sensor.<stop>_next_arrival` | שעת ההגעה הקרובה (timestamp). |
| `sensor.<stop>_line_<line>` | שעת ההגעה הקרובה של קו במעקב. |
| `sensor.<stop>_arrivals` | מספר ההגעות (אבחון), בלי נסיעות שבוטלו. המאפיין `arrivals` מכיל את כל הרשימה, והוא לא נשמר בהיסטוריה. |
| `sensor.<stop>_leave_by` | מתי לצאת מהבית (timestamp) כדי להספיק את הנסיעה הבאה שעוד אפשר להגיע אליה. רק כשהוגדר זמן הליכה. |
| `sensor.<stop>_line_<line>_leave_by` | אותו דבר, לקו במעקב. |

לחיישני ההגעה יש המאפיינים `is_realtime` (זמן חי או מלוח הזמנים), `scheduled` (השעה המתוכננת, כשהנסיעה זוהתה), `delay_minutes` (‏0 הוא בזמן, ריק הוא לא ידוע), `platform` ו-`train_number`. לחיישן `arrivals` יש גם `updated_at`, מתי התקבל העדכון האחרון. כשאין שום נסיעה בשעות הקרובות, לחיישן ההגעה של התחנה ולחיישן `arrivals` יש `next_service`: מתי השירות חוזר לפי לוח הזמנים.

חיישן "לצאת עד" הוא חותמת זמן, ולכן עובד עם טריגר הזמן הרגיל של Home Assistant, כולל היסט:

<div dir="ltr">

```yaml
triggers:
  - trigger: time
    at:
      entity_id: sensor.home_stop_leave_by
      offset: "-00:02:00"
```

</div>

> **שינוי שובר ב-1.6.0:** חיישני הדקות (`_next_arrival_in` ו-`_line_<line>_in`) הוסרו, ונמחקים אוטומטית בעדכון. לפי [כללי Home Assistant][ha-sensor-rules] חיישן משך משתנה רק כשמגיע ערך חדש, לא כי הזמן עובר, וחיישן כזה רשם שינוי בהיסטוריה כל דקה. במקומם:
> - לאוטומציה "X דקות לפני": הטריגר [`israel_transit.arrival`](#טריגר-קו-מגיע-לתחנה) עם `offset`.
> - לתבנית: `{{ ((as_timestamp(states('sensor.home_stop_next_arrival')) - now().timestamp()) / 60) | round(0, 'floor') }}`.
> - לתנאי: [`israel_transit.is_arriving_within`](#תנאים).

### איך הנתונים מתעדכנים

- כל תחנה מתעדכנת לפי תדירות העדכון שלה, בבקשה אחת ל-curlbus בכל סבב. החיישנים, האוטומציות והכרטיסים של התחנה חולקים את התשובה.
- התדירות מתאימה את עצמה: כשהנסיעה הקרובה רחוקה מחצי שעה, עדכון כל חמש דקות. כשאין שום נסיעה בשעות הקרובות (לילה, שבת, חג), עדכון פעם ברבע שעה, וחזרה לקצב הרגיל עשר דקות לפני הנסיעה הבאה בלוח הזמנים. ההחלטה נשענת על לוח הזמנים של התחנה עצמה ולא על שעות קבועות, ולכן מתאימה גם לחגים ולקווים שפועלים בשבת.
- לוח הזמנים המקומי נבדק פעם ביום ונבנה מחדש רק כשמשרד התחבורה מפרסם קובץ חדש (בערך פעם בשבוע), או כשמוסיפים תחנה. בזמן הבנייה הקובץ הקודם ממשיך לעבוד.
- רכב שכבר עבר בתחנה יורד מהרשימה תוך דקה.
- כל נסיעה חיה מזוהה מול לוח הזמנים לפי הקו ושעת היציאה שלה מתחנת המוצא. כשהיא זוהתה, העיכוב הוא ההפרש בין הזמן החי לשעה המתוכננת. נסיעה שלא משדרת עדיין נשארת בלוח לפי לוח הזמנים, ונסיעה שהמפעיל ביטל מסומנת כמבוטלת.
- כש-curlbus נכשל לתחנה (למשל שגיאה קבועה בתחנות מסוימות), האינטגרציה מורידה את תמונת המצב של כל הרכבים בארץ מ-open-bus של הסדנא לידע ציבורי. התמונה מתעדכנת בערך פעם בדקה ושוקלת כ-170KB, והיא יורדת לכל היותר פעם בדקה ורק כל עוד יש תחנה שצריכה אותה. כש-curlbus עובד, לא נשלחת לסדנא אף בקשה. מהמיקום של הרכב לאורך המסלול ומלוח הזמנים מחושב כמה הוא מאחר, וזמן ההגעה הוא השעה המתוכננת ועוד האיחור הזה. בכרטיס השורה מסומנת "משוער", ובמעבר עכבר רואים לפני כמה זמן דיווח האוטובוס. רכב שכבר עבר את התחנה יורד מהרשימה. ברכבת ישראל זה לא חל, כי לה יש מקור משלה.
- כשאין זמן אמת, הזמנים מגיעים מלוח הזמנים ומסומנים כך, והכרטיס מציין זאת. אין על זה הודעה ב**תיקונים**, כי אין מה לתקן: זה נרשם בלוג פעם אחת כשזמן האמת נעלם ופעם אחת כשהוא חוזר.
- הכרטיס מציג כמה זמן עבר מהעדכון האחרון כשעברו יותר משתי דקות, או יותר מהקצב שהתחנה מתעדכנת בו כרגע.
- אם לוח הזמנים עומד להיגמר בתוך שלושה ימים, כי משרד התחבורה לא פרסם קובץ חדש, מופיעה הודעה ב**תיקונים**. בנייה שנכשלה מנסה שוב אחרי רבע שעה, שעה, שש שעות ויום.

### כיסוי

| סוג | זמן אמת | לוח זמנים |
| --- | :---: | :---: |
| אוטובוסים ומוניות שירות | ✓ | ✓ בתחנות שהוגדרו |
| רכבת קלה (ירושלים, גוש דן) | - | ✓ |
| רכבלית חיפה והכרמלית | - | ✓ |
| רכבת ישראל | ✓ (רציף עם תחנת יעד) | ✓ |

## הכרטיס

מוסיפים את **Israel Transit** מעורך הלוח, מחפשים תחנה (או בוחרים מהקרובות לבית) ובוחרים קווים. כל האפשרויות נמצאות בעורך החזותי. לחיצה על כותרת הכרטיס פותחת את פרטי התחנה, ולחיצה על שורה פותחת את מסלול הקו.

- **מפה של כל מה שבדרך.** הכפתור בכותרת פותח מפה עם כל הרכבים שבדרך לתחנה ומשדרים מיקום, ומתחתיה רשימה לפי זמן ההגעה. לחיצה על רכב פותחת את הקו שלו.
- **מתי לצאת.** עם זמן הליכה, בכל שורה מופיע "לצאת בעוד 3 דק׳", "לצאת עכשיו" או "כבר לא תספיקו". זמן ההליכה נלקח מהגדרות התחנה באינטגרציה, או מ-`walk_minutes` בכרטיס.
- **התראה לטלפון.** בפרטי הקו יש "5 דק׳ לפני", וכשהרכב משדר מיקום גם "2 תחנות לפני". ההתראה נשלחת לטלפונים של מי שלחץ, באפליקציית Home Assistant, או לנמען שנבחר ב-`notify_entity`. לחיצה נוספת מבטלת.
- **לילה ושבת.** כשאין כלום בשעות הקרובות, הכרטיס כותב "אין שירות מתוכנן כרגע" ומתי הנסיעה הבאה.

| שם | סוג | ברירת מחדל | הסבר |
| --- | --- | --- | --- |
| `type` | string | **חובה** | `custom:israel-transit-card` |
| `stop_code` | number | **חובה** | קוד התחנה של משרד התחבורה. |
| `lines` | list | כל הקווים | אילו קווים להציג. |
| `order` | `time` \| `lines` | `time` | לפי זמן ההגעה, או לפי הסדר של `lines`. |
| `title` | string | שם התחנה | כותרת הכרטיס. |
| `max_arrivals` | number | `6` | כמה שורות להציג. |
| `max_lines` | number | `0` | כמה קווים שונים להציג. `0` בלי הגבלה. |
| `rail_destination` | string | - | תחנת יעד ברכבת, לעיכובים ורציפים. |
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
| `show_map` | boolean | `true` | מפה במסלול הקו, וכפתור מפת הרכבים בכותרת. |
| `walk_minutes` | number | מהגדרות התחנה | דקות הליכה לתחנה, ל"לצאת בעוד". |
| `alert_minutes` | number | `5` | כמה דקות לפני מתריע כפתור ההתראה. |
| `notify_entity` | string | הטלפונים שלך | ישות `notify` לשלוח אליה את ההתראה, למשל טלפון משותף. |

<div dir="ltr">

```yaml
type: custom:israel-transit-card
stop_code: 21023
lines: ["480", "36"]
order: lines
```

</div>

במפה של מסלול הקו, הקו מצויר לאורך הרחובות שהוא עובר בהם, והחלק שהרכב כבר עבר מופיע בהיר יותר. הסיכה היא התחנה שלך, והעיגול עם מספר הקו הוא הרכב. מיקום שלא התעדכן יותר משתי דקות מופיע באפור, עם הזמן שעבר. מיקום חי יש רק לאוטובוסים ולמוניות שירות. כשאין במשרד התחבורה מסלול לקו, הוא מצויר בקו מקווקו ישר בין התחנות.

המפה משתמשת באריחים של [VersaTiles][versatiles] מנתוני OpenStreetMap, ונטענת רק כשפותחים מסלול. אם הרשת חוסמת את `tiles.versatiles.org`, רשימת התחנות ממשיכה לעבוד גם בלי המפה.

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
  - action: notify.send_message
    target:
      entity_id: notify.my_phone
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

### טריגר "הזמן לצאת לתחנה"

מופעל כשצריך לצאת מהבית כדי להספיק רכב: שעת ההגעה פחות זמן ההליכה של התחנה, ועוד `offset` לפני כן אם נבחר. עוקב אחרי הזמן החי, ומופעל פעם אחת לכל נסיעה, כמו "קו מגיע לתחנה". בתחנה בלי זמן הליכה הוא מופעל ברגע ההגעה.

| שדה | הסבר |
| --- | --- |
| `line` | מספר הקו. ריק לכל הקווים. |
| `offset` | כמה זמן לפני רגע היציאה להזכיר. ריק לרגע היציאה עצמו. |

<div dir="ltr">

```yaml
triggers:
  - trigger: israel_transit.leave
    target:
      device_id: DEVICE_ID
    options:
      line: "402"
      offset:
        minutes: 2
actions:
  - action: light.turn_on
    target:
      entity_id: light.entrance
    data:
      flash: short
  - action: tts.speak
    target:
      entity_id: tts.home_assistant_cloud
    data:
      media_player_entity_id: media_player.hallway
      message: >
        קו {{ trigger.line }} בדרך, כדאי לצאת בעוד {{ trigger.leave_minutes }} דקות
```

</div>

### טריגר "רכב מתעכב"

מופעל פעם אחת לכל נסיעה, כשהעיכוב מגיע ל-`min_delay` דקות. עובד לכל נסיעה חיה שזוהתה בלוח הזמנים: אוטובוס, מונית שירות או רכבת.

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

בכל הטריגרים זמינים המשתנים `trigger.stop_code`, ‏`trigger.line`, ‏`trigger.line_ref`, ‏`trigger.destination`, ‏`trigger.operator`, ‏`trigger.eta`, ‏`trigger.minutes`, ‏`trigger.is_realtime`, ‏`trigger.vehicle_ref`, ‏`trigger.platform`, ‏`trigger.delay_minutes`, ‏`trigger.scheduled`, ‏`trigger.train_number`, ‏`trigger.walk_minutes`, ‏`trigger.leave_at` ו-`trigger.leave_minutes`. ‏`trigger.minutes` הוא מספר הדקות מרגע ההפעלה עד ההגעה, ו-`trigger.leave_minutes` עד שצריך לצאת מהבית, כך שטריגר שהופעל באיחור מראה כמה זמן באמת נשאר.

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
| `israel_transit.notify_arrival` | התראה אחת לטלפון כשהרכב הבא של `line` נמצא `minutes` דקות או `stops` תחנות מהתחנה. |
| `israel_transit.cancel_arrival_alert` | מבטלת התראה שנקבעה לאותה תחנה, קו ונמענים. |

כל הגעה ש-`get_arrivals` מחזירה כוללת `line_name`, ‏`line_ref`, ‏`eta`, ‏`minutes`, ‏`is_realtime`, ‏`destination`, ‏`operator`, ‏`route_type`, ‏`platform`, ‏`delay_minutes`, ‏`scheduled`, ‏`cancelled`, ‏`train_number` ו-`leave_minutes` (דקות עד שצריך לצאת, שלילי כשכבר מאוחר מדי), ובזמן אמת גם `vehicle_lat`, ‏`vehicle_lon` ו-`departed`. נסיעות שבוטלו מופיעות עם `cancelled: true`, ואפשר לסנן אותן בתבנית. בתשובה יש גם `summary`, משפט מוכן להקראה על כל הלוח, `walk_minutes`, ו-`next_service` כשאין נסיעות בשעות הקרובות.

`notify_arrival` יורה פעם אחת, לרכב הראשון של הקו שמגיע לסף אחרי שההתראה נקבעה. רכב שכבר קרוב יותר ברגע הקביעה לא נספר. `stops` צריך מיקום חי של הרכב. בלעדיו קובעות הדקות, שברירת המחדל שלהן 5, או 1 כשנבחר `stops`. בלי `notify_entity_id` ההתראה נשלחת לטלפונים של המשתמש שקבע אותה, דרך `notify.send_message`. היא תקפה עד שעתיים, ולא שורדת הפעלה מחדש. בכל התראה נשלח גם האירוע `israel_transit_arrival_alert` עם `stop_code`, ‏`line`, ‏`eta`, ‏`stops_away`, ‏`title` ו-`message`, כך שאפשר להפעיל ממנו גם רמקול או נורה.

<div dir="ltr">

```yaml
action: israel_transit.notify_arrival
data:
  stop_code: 21023
  line: "36"
  minutes: 5
  notify_entity_id: notify.pixel_8
```

</div>

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
      message: "{{ board.summary }}"
```

</div>

`summary` כבר כולל את הקו, היעד, הדקות, העיכוב, ומתי השירות חוזר בלילה ובשבת. לניסוח משלכם, השדות של כל הגעה נמצאים ב-`board.arrivals`.

</details>

<details>
<summary>התראה חמש דקות לפני, רק בימי עבודה</summary>

<div dir="ltr">

```yaml
triggers:
  - trigger: israel_transit.arrival
    target:
      device_id: DEVICE_ID
    options:
      line: "18"
      offset:
        minutes: 5
      offset_type: before
conditions:
  - condition: state
    entity_id: binary_sensor.workday_sensor
    state: "on"
actions:
  - action: notify.send_message
    target:
      entity_id: notify.my_phone
    data:
      message: "קו 18 מגיע בעוד {{ trigger.minutes }} דקות"
```

</div>
</details>

### Assist ועוזר קולי

לעוזר עם מודל שפה (OpenAI, Google, Anthropic, Ollama וכו') שמוגדר עם **Assist** ב"שליטה ב-Home Assistant", האינטגרציה מוסיפה כלי משלה, `israel_transit__get_arrivals`, מ-Home Assistant 2026.8. אין צורך בסקריפט או בחשיפת ישויות: שואלים "מתי הקו הבא לתל אביב?", "הרכבת שלי מאחרת?" או "מתי צריך לצאת?", והמודל מקבל את הלוח של התחנות המוגדרות עם משפט סיכום, עיכובים, ביטולים ומתי השירות חוזר בלילה ובשבת.

בלי מודל שפה, אפשר לחשוף ל-Assist סקריפט שמפעיל את `get_arrivals` ומחזיר את `summary`, כמו בדוגמת הרמקול למעלה.

## שימוש הוגן

curlbus הוא שירות קהילתי חינמי. כדי לא להעמיס עליו, כל תחנה נשאלת פעם אחת בכל סבב, תחנה בלי נסיעות בשעות הקרובות נשאלת לכל היותר פעם ברבע שעה, כרטיס בלשונית מוסתרת מפסיק לשאול, והספירה לאחור מתעדכנת בדפדפן בין הסבבים. לוח הזמנים נקרא מהקובץ המקומי בלי רשת. כדאי להשאיר את תדירות העדכון על 60 שניות אם אין סיבה טובה לשנות.

curlbus חוסם זמנית בית ששולח יותר מחמש בקשות בתוך עשר שניות. לכן האינטגרציה שולחת עד ארבע בקשות בכל עשר שניות, ומחכה לתור כשתחנות רבות מתעדכנות יחד. כשבכל זאת מגיעה חסימה, היא מחכה את הזמן ש-curlbus מבקש ומנסה שוב פעם אחת. עם יותר מכ-12 תחנות, חלק מהתחנות יציגו בחלק מהסבבים את לוח הזמנים במקום זמן אמת.

## מגבלות ידועות

- **אין זמן אמת לרכבת הקלה בירושלים, לרכבלית ולכרמלית**, כי הן לא מדווחות לנתוני ה-SIRI של משרד התחבורה. מוצג לוח הזמנים.
- **לוח זמנים לאוטובוסים נשמר רק לתחנות שהוגדרו.** לתחנה אחרת (למשל בכרטיס או ב-`get_arrivals`) יש רק זמן אמת.
- **זמן האמת תלוי ב-curlbus.** כשהוא לא זמין, אוטובוסים מקבלים זמן משוער מ-open-bus. כששניהם לא זמינים, מוצג לוח הזמנים.
- **זמן משוער** מניח שאוטובוס מאחר ימשיך לנסוע לאט באותו יחס, עד תקרה. בנסיעה ארוכה בפקק הוא עדיין עלול להיות אופטימי בכמה דקות. אוטובוס שממתין במוצא נחשב בזמן עד שהוא יוצא.
- **עיכוב** מחושב רק לנסיעה שזוהתה בלוח הזמנים. נסיעה חיה שלא זוהתה (למשל תגבור שלא בלוח) מוצגת בזמן אמת בלי עיכוב.
- **רציף ברכבת ישראל** מגיע מ-rail.co.il ודורש תחנת יעד. המפתח של rail.co.il הוא המפתח הציבורי מהאתר שלהם, והוא עלול להשתנות.
- **הורדה** של כ-170MB בכל עדכון של לוח הזמנים (כ-270MB בפורמט החדש), ועוד מקום זמני בדיסק בזמן הבנייה, בתיקייה `israel_transit/.download` שבתוך תיקיית ההגדרות.
- **השירות הבא** ("במוצ״ש ב-20:15") ידוע רק לתחנות שלוח הזמנים שלהן שמור: תחנות שהוגדרו, ותחנות שכרטיס שואל עליהן.
- **התראות לטלפון** נשמרות בזיכרון בלבד: הפעלה מחדש של Home Assistant מוחקת אותן. בכרטיס, סימון "התראה נקבעה" פג דקה אחרי שהרכב אמור להגיע, גם אם ההתראה ירתה קודם.
- **לוחות במצב YAML.** אי אפשר לרשום בהם משאב אוטומטית. מוסיפים את `/israel_transit/israel-transit-card.js` כמשאב מסוג JavaScript module (הכתובת המדויקת מופיעה בלוג).

## פתרון תקלות

### "לא ניתן להוריד את לוח הזמנים" בתיקונים

לוחצים על ההודעה ואז **שליחה**. לוח הזמנים נבנה מחדש מתוך החלון. אם זה נכשל שוב, החלון מציג את השגיאה וההודעה נשארת. בינתיים אין זמנים לרכבת הקלה ולרכבת.

### "לוח הזמנים של התחבורה הציבורית עומד להיגמר" בתיקונים

לוח הזמנים המקומי מכסה פחות משלושה ימים קדימה, כי משרד התחבורה לא פרסם קובץ חדש או שההורדה נכשלה. לוחצים על ההודעה ואז **שליחה** כדי לנסות לבנות מחדש. ההודעה נעלמת כשיש לוח שמכסה לפחות שלושה ימים.

### "אין כרגע זמן אמת" בכרטיס

גם curlbus וגם open-bus לא ענו. הזמנים מוצגים מלוח הזמנים, והכרטיס חוזר לזמן אמת לבד כשאחד מהם חוזר. ב**אבחון** של האינטגרציה מופיעים גיל התמונה של open-bus והשגיאה האחרונה שלה.

### אין זמני אוטובוס כש-curlbus לא זמין

לוח זמנים לאוטובוסים נשמר רק לתחנות שהוגדרו. מוסיפים את התחנה, ולוח הזמנים נבנה מחדש כדי לכלול אותה.

### זמני רכבת בלי עיכוב או רציף

לא נבחרה תחנת יעד. מוסיפים אותה ב-**⋮ ← הגדרה מחדש** של התחנה, או ב-`rail_destination` בכרטיס.

### הכרטיס לא מופיע, או מציג "אין חיבור כרגע"

אחרי התקנה או עדכון מרעננים את הדפדפן ומנקים את המטמון שלו. "אין חיבור כרגע" מעל הזמנים אומר שהעדכון האחרון נכשל, למשל בזמן הפעלה מחדש. "עודכן לפני N דק׳" אומר ש-Home Assistant עונה, אבל לא הצליח לקבל זמנים חדשים מאז. בשני המקרים הכרטיס מתעדכן לבד כשזה מסתדר.

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
node --test "tests/js/*.test.mjs"
```

</div>

`npm run build` בונה את הכרטיס מ-`src/` אל `custom_components/israel_transit/www/`. אפשר לראות את הכרטיס בלי Home Assistant: מריצים `python -m http.server 8777` ופותחים את `http://localhost:8777/dev/preview.html`.

## קרדיטים

הנתונים באדיבות משרד התחבורה, [curlbus][curlbus] של elad661, [open-bus][open-bus] של הסדנא לידע ציבורי (MIT) ורכבת ישראל. המפה: [MapLibre GL JS][maplibre] (BSD-3), אריחים של [VersaTiles][versatiles] ונתונים של © [OpenStreetMap][osm]. האייקונים מ-[Material Design Icons][mdi] (Apache 2.0).

## רישיון

[MIT][license] © Yosef Chai

</div>

[hacs]: https://hacs.xyz
[maplibre]: https://maplibre.org
[versatiles]: https://versatiles.org
[osm]: https://www.openstreetmap.org/copyright
[mdi]: https://pictogrammers.com/library/mdi/
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
[open-bus]: https://github.com/hasadna/open-bus-siri-requester
[ha-sensor-rules]: https://contributors.home-assistant.io/core/entities/sensor/
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=yosef-chai&repository=israel-transit&category=integration
[my-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[my-flow]: https://my.home-assistant.io/redirect/config_flow_start/?domain=israel_transit
[my-flow-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
