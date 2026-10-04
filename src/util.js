import { localize } from "./localize.js";

export const DOMAIN = "israel_transit";

// Namespaced on purpose. Home Assistant listens for a bare "dialog-closed" on
// the document and reads ev.detail.dialog off it, so firing that name -- which
// this card used to do, composed and with no detail -- crashed HA's quick-bar
// mixin every time a detail view was closed.
export const DIALOG_CLOSED = "israel-transit-dialog-closed";

// The integration's brand icon. Home Assistant reads the same files out of the
// integration's brand/ directory for its own UI (2026.3+); the integration also
// serves them here so the card can use the mark without chasing the rotating
// token that /api/brands requires.
export const BRAND_ICON = `/${DOMAIN}/brand/icon.png`;

// Matches the GTFS route types the backend reports.
export const MODE_ICONS = {
  0: "mdi:tram",
  2: "mdi:train",
  3: "mdi:bus",
  5: "mdi:gondola",
  8: "mdi:taxi",
  715: "mdi:bus-clock",
};

// The one place these colours are written down: styles.js turns them into the
// --it-mode-* custom properties, and the map needs them as literal values
// because Leaflet paints on a canvas that no CSS variable reaches.
export const MODE_HEX = {
  0: "#7b4fd1", // light rail
  2: "#1e6fbf", // Israel Railways
  3: "#2f7d4f", // bus
  5: "#b5651d", // cable car
  8: "#a3892c", // shared taxi
  715: "#4a6572",
};

export const UNKNOWN_HEX = "#03a9f4";

// The two things the map draws that are not a transport mode. Neither collides
// with a mode colour, so a glance at the map is enough to tell them apart.
export const VEHICLE_HEX = "#db4437";
export const MY_STOP_HEX = "#f0a202";

export const modeIcon = (routeType) => MODE_ICONS[routeType] ?? "mdi:bus";

export const modeColor = (routeType) =>
  routeType != null && MODE_ICONS[routeType]
    ? `var(--it-mode-${routeType})`
    : "var(--it-mode-unknown)";

export const modeHex = (routeType) => MODE_HEX[routeType] ?? UNKNOWN_HEX;

export const modeLabel = (hass, routeType) =>
  routeType != null && MODE_ICONS[routeType]
    ? localize(hass, `mode_${routeType}`)
    : "";

/** Whole minutes from now until an ISO timestamp; never negative. */
export const minutesUntil = (iso, now = Date.now()) => {
  const target = Date.parse(iso);
  if (Number.isNaN(target)) return null;
  return Math.max(0, Math.floor((target - now) / 60000));
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

/**
 * The dialog element to render details in.
 *
 * ha-adaptive-dialog is the current component -- a dialog on desktop, a bottom
 * sheet on small screens -- and arrived in Home Assistant 2026.3. Both it and
 * ha-dialog take an `open` property, a `header-title` attribute and fire
 * `closed`, so falling back keeps older installs working with the same markup.
 */
export const dialogTag = () =>
  customElements.get("ha-adaptive-dialog") ? "ha-adaptive-dialog" : "ha-dialog";

export const fireEvent = (node, type, detail = {}) => {
  const event = new CustomEvent(type, {
    detail,
    bubbles: true,
    composed: true,
  });
  node.dispatchEvent(event);
  return event;
};

/**
 * Make <ha-map> available, and say whether it worked.
 *
 * ha-map ships with Home Assistant but is only registered once something pulls
 * the map card's module in, so we ask for one. Building it is the side effect
 * we want; whether that particular config is one the map card likes is not.
 */
export const loadHaMap = async () => {
  if (customElements.get("ha-map")) return true;
  try {
    const helpers = await window.loadCardHelpers?.();
    await helpers?.createCardElement({ type: "map", entities: ["zone.home"] });
  } catch {
    // The import already happened; a rejected config does not undo it.
  }
  return !!customElements.get("ha-map");
};
