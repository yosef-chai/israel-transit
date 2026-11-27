import { localize } from "./localize.js";

export const DOMAIN = "israel_transit";

// Namespaced on purpose. Home Assistant listens for a bare "dialog-closed" on
// the document and reads ev.detail.dialog off it, so firing that name -- which
// this card used to do, composed and with no detail -- crashed HA's quick-bar
// mixin every time a detail view was closed.
export const DIALOG_CLOSED = "israel-transit-dialog-closed";

// The one place these colours are written down: styles.js turns the light ones
// into the --it-mode-* custom properties for badges (white text on them is at
// least 4.5:1), and the map, which paints on a canvas no CSS variable reaches,
// takes the pair for its theme. Every colour is at least 3:1 against the map
// background and its streets in that theme.
export const MODE_COLORS = {
  0: ["#7b4fd1", "#b39ddb"], // light rail
  2: ["#1e6fbf", "#64b5f6"], // Israel Railways
  3: ["#2f7d4f", "#66bb6a"], // bus
  5: ["#a3581a", "#ffb74d"], // cable car
  8: ["#8a7320", "#e6c84a"], // shared taxi
  715: ["#4a6572", "#90a4ae"], // flexible route
};

export const UNKNOWN_COLORS = ["#0277bd", "#4fc3f7"];

// The two things the map draws that are not a transport mode.
export const VEHICLE_COLORS = ["#c62828", "#ff6e6e"];
export const MY_STOP_COLORS = ["#9c6200", "#ffb300"];

const known = (routeType) => routeType != null && MODE_COLORS[routeType] != null;

/** A mode's colour as a CSS variable, for badges. */
export const modeColor = (routeType) =>
  known(routeType) ? `var(--it-mode-${routeType})` : "var(--it-mode-unknown)";

/** A mode's literal colour for the map, in the light or dark theme. */
export const modeMapColor = (routeType, dark) =>
  (known(routeType) ? MODE_COLORS[routeType] : UNKNOWN_COLORS)[dark ? 1 : 0];

export const modeLabel = (hass, routeType) =>
  known(routeType) ? localize(hass, `mode_${routeType}`) : "";

/** Whole minutes from now until an ISO timestamp; never negative. */
export const minutesUntil = (iso, now = Date.now()) => {
  const target = Date.parse(iso);
  if (Number.isNaN(target)) return null;
  return Math.max(0, Math.floor((target - now) / 60000));
};

/** עיכוב כטקסט: "+3" לאיחור, "−2" להקדמה, 0 לבזמן, null כשלא דווח. */
export const formatDelay = (minutes) => {
  if (minutes == null || !Number.isFinite(Number(minutes))) return null;
  const value = Math.round(Number(minutes));
  if (value === 0) return 0;
  return value > 0 ? `+${value}` : `−${-value}`;
};

/** כמה דקות שלמות עברו מאז updated_at, לפי שעון השרת; null כשאין זמן. */
export const dataAgeMinutes = (updatedAt, offset = 0, now = Date.now()) => {
  const updated = Date.parse(updatedAt);
  if (Number.isNaN(updated)) return null;
  return Math.max(0, Math.floor((now + offset - updated) / 60000));
};

/**
 * Whether the user reads times on a 12-hour clock.
 *
 * The same rule Home Assistant's own frontend applies to its profile setting:
 * "12" and "24" say so outright, and "language" or "system" mean whatever that
 * language, or the browser, writes for ten at night.
 */
const usesAmPm = (locale) => {
  if (!locale) return false; // the card's own default, before any hass arrives
  if (locale.time_format === "12") return true;
  if (locale.time_format === "24") return false;
  const language = locale.time_format === "system" ? undefined : locale.language;
  return new Date("January 1, 2023 22:00:00").toLocaleString(language).includes("10");
};

/** Wall-clock time as the user's profile asks for it, e.g. 22:06. */
export const formatClock = (iso, hass) => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const locale = hass?.locale;
  try {
    return new Intl.DateTimeFormat(locale?.language || "he-IL", {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: usesAmPm(locale) ? "h12" : "h23",
      // "server" shows Home Assistant's own time zone rather than the
      // browser's, which matters for anyone looking from abroad.
      timeZone:
        locale?.time_zone === "server" ? hass?.config?.time_zone : undefined,
    }).format(date);
  } catch {
    return date.toTimeString().slice(0, 5);
  }
};

// What a failed WebSocket call means to the person looking at the card. The
// codes are the integration's own, plus the two Home Assistant itself sends.
const ERROR_KEYS = {
  unknown_stop: "errorUnknownStop",
  index_building: "errorIndexBuilding",
  unknown_command: "errorNotLoaded",
  search_failed: "errorIndex",
  lookup_failed: "errorIndex",
  3: "errorConnection", // home-assistant-js-websocket: ERR_CONNECTION_LOST
};

/** A failed call as a sentence in the user's language. */
export const errorMessage = (hass, err) => {
  const code = err?.code ?? err?.error?.code;
  const key = ERROR_KEYS[code];
  return key ? localize(hass, key) : localize(hass, "errorGeneric");
};

export const fireEvent = (node, type, detail = {}) => {
  const event = new CustomEvent(type, {
    detail,
    bubbles: true,
    composed: true,
  });
  node.dispatchEvent(event);
  return event;
};

/** Whether the user asked the system for less motion. */
export const reducedMotion = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

/** Whether Home Assistant is showing its dark theme. */
export const isDark = (hass) => Boolean(hass?.themes?.darkMode);
