import { LitElement, css, nothing, unsafeCSS } from "lit";
import { html, unsafeStatic } from "lit/static-html.js";

import { localize } from "./localize.js";
import { sharedStyles } from "./styles.js";
import {
  DIALOG_CLOSED,
  DOMAIN,
  errorMessage,
  MY_STOP_HEX,
  VEHICLE_HEX,
  dialogTag,
  formatClock,
  loadHaMap,
  modeColor,
  modeHex,
  modeIcon,
  modeLabel,
} from "./util.js";

// ha-adaptive-dialog (Home Assistant 2026.3+) is a dialog on desktop and a
// bottom sheet on small screens, which is exactly the responsive behaviour we
// want. It and ha-dialog share the same open / header-title / closed contract,
// so older installs fall back without any other change. See DialogBase._dialog
// for when the choice is made.

// How far ahead of the vehicle the map frames when the rider's own stop is not
// on this pattern, and the most it will stretch to reach that stop: past a
// dozen stops the two ends are far enough apart that neither is legible.
const AHEAD_STOPS = 6;
const MAX_AHEAD_STOPS = 12;
const MAP_ZOOM = 16;
// Leaflet is a dynamic import inside ha-map. Until it lands ha-map centres
// itself on home, so this checks often enough that the wrong view never
// settles, and long enough to cover a cold import.
const MAP_WAIT_MS = 40;
const MAP_WAIT_TRIES = 50;

// ha-map draws every path point as a fixed 3 px dot, which makes a lone point
// for the vehicle look exactly like one more stop on the line. A closed ring of
// points is drawn as a circle instead, and reads as a marker at a glance. The
// radius follows the framed span rather than being a fixed distance, so it
// keeps roughly its size on screen whether the map shows two stops or twenty.
const RING_POINTS = 16;
const RING_SHARE = 0.045;
const RING_MIN_M = 25;
const RING_MAX_M = 220;

const METRES_PER_DEGREE = 111320;

/** A usable Date from an optional ISO string. */
const _asDate = (iso, fallback) => {
  const date = iso ? new Date(iso) : null;
  return date && !Number.isNaN(date.getTime()) ? date : fallback;
};

const located = (stop) => stop.lat != null && stop.lon != null;
const coords = (stop) => [stop.lat, stop.lon];

/** Metres between two coordinates -- close enough for "which stop is it at". */
const distance = (aLat, aLon, bLat, bLon) => {
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(bLat - aLat);
  const dLon = toRad(bLon - aLon) * Math.cos(toRad((aLat + bLat) / 2));
  return 6371000 * Math.sqrt(dLat * dLat + dLon * dLon);
};

/** Which stop on the pattern the vehicle is sitting at, or -1 if unclear. */
const nearestStopIndex = (stops, lat, lon) => {
  if (lat == null || lon == null) return -1;
  let best = -1;
  let bestDistance = Infinity;
  stops.forEach((stop, index) => {
    if (!located(stop)) return;
    const metres = distance(lat, lon, stop.lat, stop.lon);
    if (metres < bestDistance) {
      bestDistance = metres;
      best = index;
    }
  });
  // Past a couple of kilometres the vehicle is nowhere near this pattern, and
  // claiming a stop would be worse than admitting we cannot tell.
  return bestDistance <= 2000 ? best : -1;
};

/** The diagonal of what the map is about to frame, in metres. */
const spanMetres = (points) => {
  if (points.length < 2) return 0;
  const lats = points.map((point) => point[0]);
  const lons = points.map((point) => point[1]);
  return distance(
    Math.min(...lats),
    Math.min(...lons),
    Math.max(...lats),
    Math.max(...lons),
  );
};

const ringRadius = (focus) =>
  Math.min(RING_MAX_M, Math.max(RING_MIN_M, spanMetres(focus) * RING_SHARE));

/** A closed ring of coordinates, which ha-map draws as a circle. */
const ringPath = (centre, metres, color, name, timestamp) => {
  const [lat, lon] = centre;
  const dLat = metres / METRES_PER_DEGREE;
  // Longitude degrees shrink towards the poles; at Israel's latitude a degree
  // of longitude is about 85% of a degree of latitude.
  const dLon = dLat / Math.max(0.2, Math.cos((lat * Math.PI) / 180));
  return {
    points: Array.from({ length: RING_POINTS + 1 }, (_, step) => {
      const angle = (step / RING_POINTS) * 2 * Math.PI;
      return {
        point: [lat + dLat * Math.sin(angle), lon + dLon * Math.cos(angle)],
        timestamp,
      };
    }),
    color,
    name,
  };
};

const dialogStyles = css`
  .list {
    display: flex;
    flex-direction: column;
  }

  .item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 2px;
    border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
  }

  .item:first-child {
    border-top: none;
  }

  .item-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .item-title {
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .item-sub {
    margin-block-start: 2px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }

  .stop {
    display: grid;
    grid-template-columns: 20px 1fr auto;
    align-items: center;
    gap: 12px;
    padding-block: 8px;
  }

  .track {
    position: relative;
    align-self: stretch;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .track::before {
    content: "";
    position: absolute;
    inset-block: -8px;
    width: 2px;
    background: var(--divider-color, rgba(127, 127, 127, 0.35));
  }

  .stop:first-child .track::before {
    inset-block-start: 50%;
  }

  .stop:last-child .track::before {
    inset-block-end: 50%;
  }

  .node {
    position: relative;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    background: var(--card-background-color, #fff);
    border: 2px solid var(--divider-color, rgba(127, 127, 127, 0.6));
  }

  /* The same two colours the map paints these with, so the list and the map
     can be read as one picture. */
  .stop.mine .node {
    width: 15px;
    height: 15px;
    border-color: ${unsafeCSS(MY_STOP_HEX)};
  }

  .stop.here .node {
    width: 15px;
    height: 15px;
    background: ${unsafeCSS(VEHICLE_HEX)};
    border-color: ${unsafeCSS(VEHICLE_HEX)};
  }

  .stop.here .stop-title,
  .stop.mine .stop-title {
    font-weight: 600;
  }

  .stop-title {
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .stop-sub {
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }

  .time {
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
  }

  .note {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-block-end: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.12));
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
  }

  ha-icon {
    --mdc-icon-size: 20px;
    flex: 0 0 auto;
  }

  ha-map {
    height: 230px;
    border-radius: var(--ha-card-border-radius, 12px);
    overflow: hidden;
  }

  /* Says what each colour on the map means, which is cheaper than a marker
     the map API has no way to label. */
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin-block: 8px 12px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }

  .key {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .key i {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex: 0 0 auto;
  }

  /* A bottom sheet on a phone has far less room than a desktop dialog. */
  @media (max-height: 640px) {
    ha-map {
      height: 165px;
    }
  }
`;

class DialogBase extends LitElement {
  static properties = {
    open: { type: Boolean },
    _loading: { state: true },
    _error: { state: true },
  };

  static styles = [sharedStyles, dialogStyles];

  constructor() {
    super();
    this.open = false;
    this._loading = false;
    this._error = null;
  }

  /**
   * Home Assistant replaces this object on every state change in the whole
   * instance. Nothing rendered here follows from it beyond the language and
   * the connection, so it is a plain field: making it reactive would re-render
   * an open dialog several times a second for no visible difference.
   */
  set hass(hass) {
    this._hass = hass;
  }

  get hass() {
    return this._hass;
  }

  /**
   * The dialog element, chosen when this dialog first renders.
   *
   * Home Assistant registers ha-adaptive-dialog lazily, often after this
   * card's module has loaded, so deciding at import time picked the fallback
   * on installs that have the real thing. Each opening is a new element, so
   * this is decided per opening -- and then held, since a tag that changed
   * under an open dialog would rebuild it.
   */
  get _dialog() {
    this.__dialog ??= unsafeStatic(dialogTag());
    return this.__dialog;
  }

  _t(key) {
    return localize(this.hass, key);
  }

  _closed() {
    this.open = false;
    // Neither bubbling nor composed: the only listener is the card, on this
    // very element. Letting it escape to the document is what broke Home
    // Assistant's own handler for the name this used to borrow.
    this.dispatchEvent(new CustomEvent(DIALOG_CLOSED));
  }

  /** Loading, error and empty all look the same wherever they appear. */
  _renderState(items, emptyKey) {
    if (this._loading) return html`<div class="empty">${this._t("loading")}</div>`;
    if (this._error) return html`<div class="error">${this._error}</div>`;
    if (!items.length) return html`<div class="empty">${this._t(emptyKey)}</div>`;
    return null;
  }
}

export class IsraelTransitStopDialog extends DialogBase {
  static properties = {
    ...DialogBase.properties,
    stop: { attribute: false },
    _routes: { state: true },
  };

  constructor() {
    super();
    this._routes = [];
  }

  updated(changed) {
    if (changed.has("open") && this.open) this._load();
  }

  async _load() {
    if (!this.hass || !this.stop) return;
    this._loading = true;
    this._error = null;
    try {
      this._routes = await this.hass.callWS({
        type: `${DOMAIN}/stop_routes`,
        stop_code: this.stop.code,
      });
    } catch (err) {
      this._error = errorMessage(this.hass, err);
    } finally {
      this._loading = false;
    }
  }

  render() {
    const stop = this.stop || {};
    const state = this._renderState(this._routes, "noLines");

    return html`
      <${this._dialog}
        header-title=${stop.name || this._t("stopDetails")}
        header-subtitle=${[stop.city, stop.code].filter(Boolean).join(" · ")}
        width="medium"
        .open=${this.open}
        @closed=${this._closed}
      >
        ${
          state ??
          html`<div class="list">
            ${this._routes.map(
              (route) => html`
                <div class="item">
                  <div
                    class="badge"
                    style=${`--it-badge-color:${modeColor(route.route_type)}`}
                  >
                    ${route.line_name}
                  </div>
                  <div class="item-body">
                    <div class="item-title">${route.destination}</div>
                    <div class="item-sub">
                      ${[route.operator, modeLabel(this.hass, route.route_type)]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  </div>
                  ${
                    route.has_realtime
                      ? nothing
                      : html`<span class="tag timetable"
                          >${this._t("scheduled")}</span
                        >`
                  }
                </div>
              `,
            )}
          </div>`
        }
      </${this._dialog}>
    `;
  }
}

export class IsraelTransitRouteDialog extends DialogBase {
  static properties = {
    ...DialogBase.properties,
    arrival: { attribute: false },
    showMap: { attribute: false },
    stopCode: { attribute: false },
    _stops: { state: true },
    _mapReady: { state: true },
  };

  constructor() {
    super();
    this._stops = [];
    this.showMap = true;
    this._mapReady = false;
    this._paths = [];
    this._focus = [];
  }

  willUpdate(changed) {
    // The card hands over a fresh arrival on every poll, so this recomputes
    // whenever the vehicle moves -- and only then. Framing is decided first,
    // because it is what sets the size of the markers drawn into it.
    if (
      changed.has("arrival") ||
      changed.has("_stops") ||
      changed.has("stopCode")
    ) {
      this._focus = this._computeFocus();
      this._paths = this._computePaths();
    }
  }

  updated(changed) {
    if (changed.has("open") && this.open) this._load();
    this._fitMap();
  }

  async _load() {
    this._stops = [];
    this._error = null;
    if (!this.hass || !this.arrival?.line_ref) {
      this._error = this._t("noRouteStops");
      return;
    }
    this._loading = true;
    if (this.showMap) {
      loadHaMap().then((ready) => {
        this._mapReady = ready;
      });
    }
    try {
      this._stops = await this.hass.callWS({
        type: `${DOMAIN}/route_stops`,
        line_ref: this.arrival.line_ref,
        // Stop times are stored as offsets from the start of a run, so handing
        // over this vehicle's departure turns them into its own times.
        departed: this.arrival.departed || null,
      });
    } catch (err) {
      this._error = errorMessage(this.hass, err);
    } finally {
      this._loading = false;
    }
  }

  // -- the map -------------------------------------------------------------

  get _located() {
    return this._stops.filter(located);
  }

  get _vehiclePoint() {
    const { vehicle_lat: lat, vehicle_lon: lon } = this.arrival || {};
    return lat != null && lon != null ? [lat, lon] : null;
  }

  /** Where the vehicle is on this pattern, and where the rider is waiting. */
  get _hereIndex() {
    const { vehicle_lat: lat, vehicle_lon: lon } = this.arrival || {};
    return nearestStopIndex(this._stops, lat, lon);
  }

  get _mineIndex() {
    if (this.stopCode == null) return -1;
    const code = Number(this.stopCode);
    return this._stops.findIndex((stop) => Number(stop.code) === code);
  }

  /**
   * What the map should frame.
   *
   * The stretch a rider actually cares about is from where the vehicle is now
   * through to their own stop. Fitting the whole route instead would put both
   * of those inside a couple of pixels on any intercity line.
   */
  _computeFocus() {
    const vehicle = this._vehiclePoint;
    const all = this._located.map(coords);
    if (!vehicle) return all;

    const here = this._hereIndex;
    // Nowhere near this pattern: showing both is more honest than guessing.
    if (here < 0) return [vehicle, ...all];

    const mine = this._mineIndex;
    const last =
      mine > here ? Math.min(mine, here + MAX_AHEAD_STOPS) : here + AHEAD_STOPS;
    const stretch = this._stops.slice(here, last + 1).filter(located).map(coords);
    return [vehicle, ...(stretch.length ? stretch : all)];
  }

  /**
   * The route as a line of stops, then the rider's stop and the vehicle as
   * rings on top of it.
   *
   * ha-map paints on a canvas, so these carry literal colours rather than the
   * theme variables the rest of the card uses. Order is paint order: the
   * vehicle goes last so it is never hidden under the line.
   */
  _computePaths() {
    if (!this.showMap) return [];
    const arrival = this.arrival || {};
    const now = new Date();
    const radius = ringRadius(this._focus);
    const paths = [];

    const points = this._located.map((stop) => ({
      point: coords(stop),
      timestamp: _asDate(stop.arrival_time, now),
    }));
    if (points.length > 1) {
      paths.push({
        points,
        color: modeHex(arrival.route_type),
        name: `${arrival.line_name ?? ""} ${this._t("routeLine")}`.trim(),
      });
    }

    const mine = this._stops[this._mineIndex];
    if (mine && located(mine)) {
      paths.push(
        ringPath(coords(mine), radius, MY_STOP_HEX, this._t("myStop"), now),
      );
    }

    const vehicle = this._vehiclePoint;
    if (vehicle) {
      paths.push(
        ringPath(vehicle, radius, VEHICLE_HEX, this._t("vehicleMap"), now),
      );
    }
    return paths;
  }

  /**
   * ha-map's own auto-fit only looks at entities and layers, and this map has
   * neither, so the framing is ours to set. Leaflet arrives by dynamic import,
   * which is why this waits for it rather than assuming it is there.
   */
  _fitMap() {
    const key = this._focus.length ? JSON.stringify(this._focus) : "";
    if (!key || key === this._fitted) return;
    const map = this.renderRoot.querySelector("ha-map");
    if (!map) return;
    if (!map.leafletMap) {
      // One wait at a time: every render calls this, and each starting its
      // own chain of retries piled dozens of timers onto one dialog.
      if (!this._fitTimer && (this._fitTries ?? 0) < MAP_WAIT_TRIES) {
        this._fitTries = (this._fitTries ?? 0) + 1;
        this._fitTimer = setTimeout(() => {
          this._fitTimer = undefined;
          this._fitMap();
        }, MAP_WAIT_MS);
      }
      return;
    }
    this._fitTries = 0;
    map.fitBounds(this._focus, { zoom: MAP_ZOOM });
    this._fitted = key;
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this._fitTimer);
    this._fitTimer = undefined;
  }

  _renderMap() {
    if (!this.showMap || !this._mapReady || !this._paths.length) return nothing;
    return html`
      <ha-map .hass=${this.hass} .paths=${this._paths} .zoom=${MAP_ZOOM}></ha-map>
      <div class="legend">
        ${this._paths.map(
          (path) => html`<span class="key"
            ><i style=${`background:${path.color}`}></i>${path.name}</span
          >`,
        )}
      </div>
    `;
  }

  /** Minutes into the run, for when no vehicle departure time is known. */
  _relative(seconds) {
    if (seconds == null) return "";
    const minutes = Math.round(seconds / 60);
    return minutes ? `+${minutes} ${this._t("minutes")}` : "";
  }

  render() {
    const arrival = this.arrival || {};
    const here = this._hereIndex;
    const mine = this._mineIndex;
    const state = this._renderState(this._stops, "noRouteStops");
    const title = [modeLabel(this.hass, arrival.route_type), arrival.line_name]
      .filter(Boolean)
      .join(" ");

    return html`
      <${this._dialog}
        header-title=${`${title} · ${arrival.destination || ""}`}
        header-subtitle=${[arrival.operator, this._t("routeStops")]
          .filter(Boolean)
          .join(" · ")}
        width="medium"
        .open=${this.open}
        @closed=${this._closed}
      >
        ${this._renderMap()}
        ${
          here >= 0 || arrival.departed
            ? html`<div class="note">
                <ha-icon .icon=${modeIcon(arrival.route_type)}></ha-icon>
                <span>
                  ${here >= 0
                    ? `${this._t("vehicleHere")}: ${this._stops[here].name}`
                    : ""}
                  ${arrival.departed
                    ? `${here >= 0 ? " · " : ""}${this._t("departedAt")}${formatClock(arrival.departed, this.hass)}`
                    : ""}
                </span>
              </div>`
            : // Only worth saying when a position was expected: a timetabled row
              // has no vehicle to locate in the first place.
              this.showMap && arrival.is_realtime && !this._vehiclePoint
              ? html`<div class="note">
                  <ha-icon icon="mdi:map-marker-off-outline"></ha-icon>
                  <span>${this._t("noVehicleLocation")}</span>
                </div>`
              : nothing
        }
        ${
          state ??
          html`<div class="list">
            ${this._stops.map(
              (stop, index) => html`
                <div
                  class="stop ${index === here ? "here" : ""} ${index === mine
                    ? "mine"
                    : ""}"
                >
                  <div class="track"><div class="node"></div></div>
                  <div>
                    <div class="stop-title">${stop.name}</div>
                    <div class="stop-sub">
                      ${[
                        stop.city,
                        stop.code,
                        index === mine ? this._t("myStop") : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  </div>
                  <div class="time">
                    ${stop.arrival_time
                      ? formatClock(stop.arrival_time, this.hass)
                      : this._relative(stop.offset_seconds)}
                  </div>
                </div>
              `,
            )}
          </div>`
        }
      </${this._dialog}>
    `;
  }
}
