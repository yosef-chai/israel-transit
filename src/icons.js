// Icons as inline SVG paths from @mdi/js, bundled by use. ha-icon is not a
// promised API for custom cards, renders nothing until Home Assistant has
// loaded it, and cannot be drawn inside a map marker; a path can.
import {
  mdiAccessPoint,
  mdiAlertCircleOutline,
  mdiArrowDown,
  mdiArrowUp,
  mdiBellCheckOutline,
  mdiBellRingOutline,
  mdiBus,
  mdiBusClock,
  mdiBusStop,
  mdiCalendarClock,
  mdiChevronDown,
  mdiChevronRight,
  mdiClose,
  mdiCloudAlertOutline,
  mdiCrosshairsGps,
  mdiGondola,
  mdiInformationOutline,
  mdiMagnify,
  mdiMapMarkerAccount,
  mdiMapMarkerMultipleOutline,
  mdiMapMarkerOffOutline,
  mdiMapOutline,
  mdiMenuDown,
  mdiPlus,
  mdiTaxi,
  mdiTimerSandEmpty,
  mdiTrain,
  mdiTram,
  mdiWalk,
  mdiWeatherNight,
} from "@mdi/js";
import { html } from "lit";

export const ICONS = {
  live: mdiAccessPoint,
  alert: mdiAlertCircleOutline,
  arrowDown: mdiArrowDown,
  arrowUp: mdiArrowUp,
  busStop: mdiBusStop,
  timetable: mdiCalendarClock,
  chevron: mdiChevronRight,
  expand: mdiChevronDown,
  menuDown: mdiMenuDown,
  plus: mdiPlus,
  close: mdiClose,
  offline: mdiCloudAlertOutline,
  recenter: mdiCrosshairsGps,
  info: mdiInformationOutline,
  search: mdiMagnify,
  myStop: mdiMapMarkerAccount,
  noPosition: mdiMapMarkerOffOutline,
  map: mdiMapOutline,
  empty: mdiTimerSandEmpty,
  bell: mdiBellRingOutline,
  bellSet: mdiBellCheckOutline,
  walk: mdiWalk,
  vehicles: mdiMapMarkerMultipleOutline,
  noService: mdiWeatherNight,
};

// Matches the GTFS route types the backend reports.
const MODE_PATHS = {
  0: mdiTram,
  2: mdiTrain,
  3: mdiBus,
  5: mdiGondola,
  8: mdiTaxi,
  715: mdiBusClock,
};

export const modePath = (routeType) => MODE_PATHS[routeType] ?? mdiBus;

/**
 * An icon that takes the text colour around it. Decorative by default; pass a
 * label only when the icon is the only thing saying what it means.
 */
export const icon = (path, { size = 20, label, cls = "icon" } = {}) =>
  html`<svg
    class=${cls}
    viewBox="0 0 24 24"
    width=${size}
    height=${size}
    role=${label ? "img" : "presentation"}
    aria-hidden=${label ? "false" : "true"}
    aria-label=${label ?? ""}
    focusable="false"
  ><path fill="currentColor" d=${path}></path></svg>`;

/** The same icon as markup, for a map marker built outside Lit. */
export const iconMarkup = (path, size = 18) =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true" focusable="false"><path fill="currentColor" d="${path}"/></svg>`;
