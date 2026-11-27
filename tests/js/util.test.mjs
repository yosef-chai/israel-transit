// node --test tests/js
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  dataAgeMinutes,
  errorMessage,
  formatDelay,
  leaveMinutes,
  minutesUntil,
  whenPhrase,
} from "../../src/util.js";

test("מתי השירות חוזר, בשעון ישראל", () => {
  // שעון ישראל במפורש: ב-CI אזור הזמן של המכונה הוא UTC.
  const hass = {
    language: "he",
    locale: { language: "he", time_format: "24", time_zone: "server" },
    config: { time_zone: "Asia/Jerusalem" },
  };
  // שישי, 4 בספטמבר 2026, 18:00 בישראל.
  const friday = Date.parse("2026-09-04T15:00:00Z");
  assert.equal(whenPhrase(hass, "2026-09-05T17:15:00Z", friday), "במוצ״ש ב-20:15");
  assert.equal(whenPhrase(hass, "2026-09-04T19:00:00Z", friday), "היום ב-22:00");
  assert.equal(whenPhrase(hass, "2026-09-05T07:00:00Z", friday), "מחר ב-10:00");
  assert.equal(whenPhrase(hass, "2026-09-06T03:00:00Z", friday), "ביום ראשון ב-06:00");
  assert.equal(whenPhrase(hass, "junk", friday), "");
});

test("דקות עד היציאה: הליכה של 6 דקות", () => {
  const now = Date.parse("2026-11-27T10:00:00Z");
  assert.equal(leaveMinutes("2026-11-27T10:10:30Z", 6, now), 4);
  assert.equal(leaveMinutes("2026-11-27T10:04:00Z", 6, now), -2);
  assert.equal(leaveMinutes("2026-11-27T10:10:00Z", 0, now), null);
});

test("עיכוב: איחור עם +, הקדמה עם מינוס אמיתי, 0 נשאר 0, חוסר נשאר null", () => {
  assert.equal(formatDelay(3), "+3");
  assert.equal(formatDelay(-2), "−2");
  assert.equal(formatDelay(0), 0);
  assert.equal(formatDelay(null), null);
  assert.equal(formatDelay(undefined), null);
  assert.equal(formatDelay("x"), null);
});

test("גיל הנתונים לא שלילי גם כשהשעון של המכשיר מקדים", () => {
  const updated = "2026-11-27T10:00:00Z";
  const at = Date.parse(updated);
  assert.equal(dataAgeMinutes(updated, 0, at + 3 * 60000 + 59000), 3);
  assert.equal(dataAgeMinutes(updated, 0, at - 120000), 0);
  // המכשיר מאחר בדקה: offset מתקן לפי שעון השרת
  assert.equal(dataAgeMinutes(updated, 60000, at + 60000), 2);
  assert.equal(dataAgeMinutes(undefined, 0, at), null);
});

test("דקות עד ההגעה מעוגלות למטה", () => {
  const now = Date.parse("2026-11-27T10:00:00Z");
  assert.equal(minutesUntil("2026-11-27T10:01:59Z", now), 1);
  assert.equal(minutesUntil("2026-11-27T09:59:00Z", now), 0);
  assert.equal(minutesUntil("garbage", now), null);
});

test("לוח זמנים בבנייה הוא הודעה משלו, לא תחנה לא מוכרת", () => {
  const hass = { language: "he" };
  assert.notEqual(
    errorMessage(hass, { code: "index_building" }),
    errorMessage(hass, { code: "unknown_stop" }),
  );
});
