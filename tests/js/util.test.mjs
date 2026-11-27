// node --test tests/js
import assert from "node:assert/strict";
import { test } from "node:test";

import { dataAgeMinutes, errorMessage, formatDelay, minutesUntil } from "../../src/util.js";

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
