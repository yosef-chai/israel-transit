import { LitElement, css, html, nothing } from "lit";

import { ICONS, icon, modePath } from "./icons.js";
import { localize } from "./localize.js";
import {
  boundsOf,
  createProgress,
  focusPoints,
  isPoint,
  measureLine,
  nearestStopIndex,
  positionAge,
  splitLine,
  stopPoint,
  stopPositions,
  vehicleProgress,
} from "./map-geometry.js";
import { sharedStyles } from "./styles.js";
import {
  DIALOG_CLOSED,
  DOMAIN,
  MY_STOP_COLORS,
  errorMessage,
  formatClock,
  isDark,
  modeColor,
  modeLabel,
  modeMapColor,
} from "./util.js";

// A position older than this is shown as the last known one, not as live.
const STALE_POSITION_S = 120;
// How often an open route recounts the age of its vehicle's position, so the
// age keeps growing when no new answer arrives.
const AGE_TICK_MS = 15000;
// Routes asked for recently, so reopening one is instant. A wall tablet can be
// left open for weeks, hence the cap.
const ROUTE_CACHE_SIZE = 40;

const routeCache = new Map();
let cachedIndex = null;

const cacheGet = (key) => {
  const hit = routeCache.get(key);
  if (hit) {
    routeCache.delete(key);
    routeCache.set(key, hit);
  }
  return hit;
};

const cachePut = (key, value) => {
  // A rebuilt timetable can change any route; nothing cached survives it.
  if (value.index !== cachedIndex) {
    routeCache.clear();
    cachedIndex = value.index;
  }
  routeCache.set(key, value);
  while (routeCache.size > ROUTE_CACHE_SIZE) {
    routeCache.delete(routeCache.keys().next().value);
  }
};

/** The answer to route_stops, from either the current or the older backend. */
const normaliseRoute = (answer) =>
  Array.isArray(answer)
    ? { stops: answer, shape: null, index: null }
    : { stops: answer?.stops ?? [], shape: answer?.shape ?? null, index: answer?.index ?? null };

const dialogStyles = css`
  .list {
    display: flex;
    flex-direction: column;
  }

  .item {
    display: flex;
    align-items: center;
    gap: var(--ha-space-4, 16px);
    min-height: 56px;
    padding-block: var(--ha-space-2, 8px);
    box-sizing: border-box;
  }

  .item + .item {
    box-shadow: inset 0 1px 0 var(--divider-color, rgba(127, 127, 127, 0.2));
  }

  .item-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .item-title {
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .item-sub {
    margin-block-start: var(--ha-space-1, 4px);
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .tag {
    font-size: var(--ha-font-size-s, 12px);
  }

  israel-transit-map {
    height: 260px;
    margin-block-end: var(--ha-space-3, 12px);
  }

  /* A bottom sheet on a phone has far less room than a desktop dialog. */
  @media (max-height: 700px) {
    israel-transit-map {
      height: 200px;
    }
  }

  /* -- the status of the vehicle, under the map -- */

  .status {
    display: flex;
    align-items: center;
    gap: var(--ha-space-3, 12px);
    margin-block-end: var(--ha-space-3, 12px);
    padding: var(--ha-space-3, 12px);
    border-radius: var(--ha-border-radius-lg, 12px);
    background: var(--ha-color-fill-neutral-quiet-resting, rgba(127, 127, 127, 0.1));
  }

  .status-icon {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--it-badge-color, var(--it-mode-unknown));
    color: #fff;
  }

  .status-icon.off {
    background: var(--ha-color-fill-neutral-normal-resting, rgba(127, 127, 127, 0.3));
    color: var(--secondary-text-color);
  }

  .status-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .status-title {
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
  }

  .status-sub {
    display: flex;
    flex-wrap: wrap;
    gap: 0 var(--ha-space-2, 8px);
    margin-block-start: var(--ha-space-1, 4px);
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .status-sub .stale {
    color: var(--it-text-warning);
  }

  .approx {
    margin-block-end: var(--ha-space-3, 12px);
  }

  /* -- the stop timeline -- */

  .timeline {
    display: flex;
    flex-direction: column;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .stop {
    display: grid;
    grid-template-columns: 28px 1fr auto;
    align-items: center;
    gap: var(--ha-space-3, 12px);
    width: 100%;
    min-height: 48px;
    padding: var(--ha-space-1, 4px) 0;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    box-sizing: border-box;
  }

  .stop:disabled {
    cursor: default;
  }

  .stop:not(:disabled):hover {
    background: var(--ha-color-fill-neutral-quiet-hover, rgba(127, 127, 127, 0.08));
  }

  .stop:focus-visible {
    outline: 2px solid var(--ha-color-focus, var(--primary-color));
    outline-offset: -2px;
    border-radius: var(--ha-border-radius-md, 8px);
  }

  .track {
    position: relative;
    align-self: stretch;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  /* The line between stops, in the colour of the line. */
  .track::before {
    content: "";
    position: absolute;
    inset-block: -4px;
    width: 4px;
    border-radius: 2px;
    background: var(--it-badge-color, var(--it-mode-unknown));
  }

  li:first-child .track::before {
    inset-block-start: 50%;
  }

  li:last-child .track::before {
    inset-block-end: 50%;
  }

  .node {
    position: relative;
    box-sizing: border-box;
    width: 12px;
    height: 12px;
    border: 3px solid var(--it-badge-color, var(--it-mode-unknown));
    border-radius: 50%;
    background: var(--card-background-color, #fff);
  }

  .done .track::before,
  .done .node {
    opacity: 0.35;
  }

  .done .stop-title,
  .done .time {
    color: var(--secondary-text-color);
  }

  .here .node,
  .mine .node {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-width: 0;
    background: var(--it-badge-color, var(--it-mode-unknown));
    color: #fff;
  }

  .mine .node {
    background: var(--it-mine);
  }

  .stop-title {
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .here .stop-title,
  .mine .stop-title {
    font-weight: var(--ha-font-weight-bold, 700);
  }

  .stop-sub {
    margin-block-start: 2px;
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .stop-sub .mine-label {
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--primary-text-color);
  }

  .time {
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
  }
`;

class DialogBase extends LitElement {
  static properties = {
    open: { type: Boolean },
    opener: { attribute: false },
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
   * instance. Only the language, the time settings and the theme change what
   * a dialog shows, so those are all that ask for a render.
   */
  set hass(hass) {
    this._hass = hass;
    const look = [hass?.language, hass?.locale?.language, hass?.locale?.time_format, isDark(hass)].join("|");
    if (look !== this._look) {
      this._look = look;
      this.requestUpdate();
    }
  }

  get hass() {
    return this._hass;
  }

  _t(key, values) {
    return localize(this.hass, key, values);
  }

  _closed() {
    this.open = false;
    // Neither bubbling nor composed: the only listener is the card, on this
    // very element. Letting it escape to the document is what broke Home
    // Assistant's own handler for the name this used to borrow.
    this.dispatchEvent(new CustomEvent(DIALOG_CLOSED));
  }

  _renderDialog(heading, subheading, body) {
    return html`<israel-transit-dialog
      .heading=${heading}
      .subheading=${subheading}
      .closeLabel=${this._t("close")}
      .opener=${this.opener}
      .open=${this.open}
      @closed=${this._closed}
    >
      ${body}
    </israel-transit-dialog>`;
  }

  /** Loading, error and empty all look the same wherever they appear. */
  _renderState(items, emptyKey) {
    if (this._loading) {
      return html`<div role="progressbar" aria-label=${this._t("loading")} aria-busy="true">
        ${[0, 1, 2].map(
          () => html`<div class="skeleton" aria-hidden="true">
            <span class="bone pill"></span><span class="bone text"></span>
          </div>`,
        )}
      </div>`;
    }
    if (this._error) {
      return html`<div class="alert error" role="alert">
        ${icon(ICONS.alert, { size: 18 })}<span>${this._error}</span>
      </div>`;
    }
    if (!items.length) {
      return html`<div class="empty">
        ${icon(ICONS.empty, { size: 40 })}
        <p class="empty-title">${this._t("emptyTitle")}</p>
        <p class="empty-text">${this._t(emptyKey)}</p>
      </div>`;
    }
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
    return this._renderDialog(
      stop.name || this._t("stopDetails"),
      [stop.city, stop.code].filter(Boolean).join(" · "),
      state ??
        html`<div class="list" role="list" aria-label=${this._t("allLines")}>
          ${this._routes.map(
            (route) => html`
              <div class="item" role="listitem">
                <div class="badge" style=${`--it-badge-color:${modeColor(route.route_type)}`}>
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
                ${route.has_realtime
                  ? nothing
                  : html`<span class="tag timetable"
                      >${icon(ICONS.timetable, { size: 14 })}${this._t("scheduled")}</span
                    >`}
              </div>
            `,
          )}
        </div>`,
    );
  }
}

export class IsraelTransitRouteDialog extends DialogBase {
  static properties = {
    ...DialogBase.properties,
    arrival: { attribute: false },
    showMap: { attribute: false },
    stopCode: { attribute: false },
    clockOffset: { attribute: false },
    _route: { state: true },
    _now: { state: true },
  };

  constructor() {
    super();
    this.showMap = true;
    this.clockOffset = 0;
    this._route = { stops: [], shape: null, index: null };
    this._now = Date.now();
    this._progress = createProgress();
    this._request = 0;
  }

  connectedCallback() {
    super.connectedCallback();
    this._ageTimer = setInterval(() => (this._now = Date.now()), AGE_TICK_MS);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearInterval(this._ageTimer);
    this._progress.reset();
    // Anything still on its way belongs to a dialog that is gone.
    this._request += 1;
  }

  willUpdate(changed) {
    // The card hands over a fresh arrival on every poll. The route is asked
    // for again only when it is a different run: the line, or the departure
    // its stop times are counted from.
    if (changed.has("arrival") || changed.has("open")) {
      const key = this._routeKey;
      if (this.open && key !== this._loadedKey) this._load(key);
    }
    if (changed.has("arrival")) this._now = Date.now();
  }

  get _routeKey() {
    const arrival = this.arrival || {};
    return arrival.line_ref ? `${arrival.line_ref}|${arrival.departed ?? ""}` : "";
  }

  async _load(key) {
    this._loadedKey = key;
    this._error = null;
    const arrival = this.arrival || {};
    if (!this.hass || !arrival.line_ref) {
      this._route = { stops: [], shape: null, index: null };
      this._error = this._t("noRouteStops");
      return;
    }
    const cached = cacheGet(key);
    if (cached) {
      this._route = cached;
      return;
    }
    // Only the latest request may land: closing one line and opening another
    // must not show the first one's route on the second one's map.
    const request = ++this._request;
    this._loading = !this._route.stops.length;
    try {
      const answer = normaliseRoute(
        await this.hass.callWS({
          type: `${DOMAIN}/route_stops`,
          line_ref: arrival.line_ref,
          // Stop times are stored as offsets from the start of a run, so
          // handing over this vehicle's departure turns them into its own.
          departed: arrival.departed || null,
        }),
      );
      if (request !== this._request) return;
      cachePut(key, answer);
      this._route = answer;
    } catch (err) {
      if (request !== this._request) return;
      this._error = errorMessage(this.hass, err);
    } finally {
      if (request === this._request) this._loading = false;
    }
  }

  // -- what the map and the list show ----------------------------------------

  get _vehiclePoint() {
    const { vehicle_lat: lat, vehicle_lon: lon } = this.arrival || {};
    const point = lat != null && lon != null ? [Number(lat), Number(lon)] : null;
    return isPoint(point) ? point : null;
  }

  /** Everything the map and the timeline need, worked out once per render. */
  _picture() {
    const arrival = this.arrival || {};
    const stops = this._route.stops || [];
    const dark = isDark(this.hass);
    const vehicle = this._vehiclePoint;
    const here = nearestStopIndex(stops, vehicle);
    const mineCode = this.stopCode == null ? null : Number(this.stopCode);
    const mine = mineCode == null ? -1 : stops.findIndex((stop) => Number(stop.code) === mineCode);

    const shape = (this._route.shape || []).filter(isPoint);
    const dashed = shape.length < 2;
    const line = measureLine(dashed ? stops.map(stopPoint).filter(isPoint) : shape);
    const positions = stopPositions(line, stops);

    // Where the vehicle is along the line, never moving backwards within one
    // run of one vehicle.
    const measured = vehicleProgress(line, positions, here, vehicle);
    const subject = `${arrival.line_ref}|${arrival.vehicle_ref ?? ""}`;
    const along = this._progress.update(subject, here, measured);
    const { done, ahead } =
      along != null && measured != null ? splitLine(line, along) : { done: [], ahead: line.points };
    const passed = (index) =>
      along != null && positions[index] != null ? positions[index] < along - 30 : index < here;

    const age = vehicle ? positionAge(arrival.vehicle_seen, this.clockOffset ?? 0, this._now) : null;
    const stale = age != null && age > STALE_POSITION_S;
    const name = (index) => stops[index]?.name ?? "";

    const view = {
      dark,
      dashed,
      color: modeMapColor(arrival.route_type, dark),
      mineColor: MY_STOP_COLORS[dark ? 1 : 0],
      line: line.points,
      done,
      ahead,
      stops: stops
        .map((stop, index) => ({ point: stopPoint(stop), name: stop.name, done: passed(index) }))
        .filter((stop, index) => isPoint(stop.point) && index !== mine),
      mine:
        mine >= 0 && isPoint(stopPoint(stops[mine]))
          ? { point: stopPoint(stops[mine]), name: name(mine), label: `${this._t("myStop")}: ${name(mine)}` }
          : null,
      vehicle: vehicle
        ? {
            point: vehicle,
            icon: modePath(arrival.route_type),
            lineName: arrival.line_name,
            stale,
            label: this._t(stale ? "vehicleStale" : "vehicleOf", { line: arrival.line_name ?? "" }),
          }
        : null,
      bounds: boundsOf(focusPoints({ stops, vehicle, hereIndex: here, mineIndex: mine })),
      // Framed again when the vehicle reaches another stop, not on every
      // sighting: between stops it moves on the map without the map moving.
      fitKey: `${subject}|${here}|${mine}|${stops.length}|${shape.length}`,
      subject,
    };
    return { view, here, mine, passed, age, stale, dashed, vehicle };
  }

  _strings() {
    const t = (key) => this._t(key);
    return {
      unavailable: t("mapUnavailable"),
      unsupported: t("mapUnsupported"),
      failed: t("mapFailed"),
      vendor: t("mapVendor"),
      retry: t("retry"),
      reload: t("reload"),
      recenter: t("recenter"),
      maplibre: {
        "NavigationControl.ZoomIn": t("zoomIn"),
        "NavigationControl.ZoomOut": t("zoomOut"),
        "AttributionControl.ToggleAttribution": t("attribution"),
        "Map.Title": t("mapLabel"),
      },
    };
  }

  /** Minutes into the run, for when no vehicle departure time is known. */
  _relative(seconds) {
    if (seconds == null) return "";
    const minutes = Math.round(seconds / 60);
    return minutes ? `+${minutes} ${this._t("minutes")}` : "";
  }

  _focusStop(stop) {
    this.renderRoot.querySelector("israel-transit-map")?.focusOn(stopPoint(stop));
  }

  render() {
    const arrival = this.arrival || {};
    const stops = this._route.stops || [];
    const picture = this._picture();
    const title = [modeLabel(this.hass, arrival.route_type), arrival.line_name]
      .filter(Boolean)
      .join(" ");
    const state = this._renderState(stops, "noRouteStops");
    const showMap = this.showMap && stops.length > 0;

    return this._renderDialog(
      `${title}${arrival.destination ? ` · ${arrival.destination}` : ""}`,
      [arrival.operator, this._t("routeStops")].filter(Boolean).join(" · "),
      html`
        <div style=${`--it-badge-color:${modeColor(arrival.route_type)};--it-mine:${MY_STOP_COLORS[0]}`}>
          ${showMap
            ? html`<israel-transit-map
                .view=${picture.view}
                .strings=${this._strings()}
              ></israel-transit-map>`
            : nothing}
          ${stops.length ? this._renderStatus(arrival, stops, picture) : nothing}
          ${showMap && picture.dashed && stops.length > 1
            ? html`<div class="alert info approx" role="note">
                ${icon(ICONS.map, { size: 18 })}<span>${this._t("approximateRoute")}</span>
              </div>`
            : nothing}
          ${state ?? this._renderTimeline(stops, picture, showMap)}
        </div>
      `,
    );
  }

  /** Where the vehicle is, and what that means for the rider. */
  _renderStatus(arrival, stops, { here, mine, age, stale, vehicle }) {
    let headline;
    if (vehicle && here >= 0) {
      headline = here === mine ? this._t("atYourStop") : this._t("nearStop", { stop: stops[here].name });
    } else if (vehicle) {
      headline = this._t("awayFromRoute");
    } else if (arrival.is_realtime) {
      headline = this._t("noVehicleLocation");
    } else {
      headline = this._t("scheduled");
    }

    const details = [];
    if (vehicle && here >= 0 && mine > here) {
      const left = mine - here;
      details.push(left === 1 ? this._t("stopsToGoOne") : this._t("stopsToGo", { n: left }));
    }
    if (arrival.eta) {
      details.push(this._t("arrivesAt", { time: formatClock(arrival.eta, this.hass) }));
    }
    if (!vehicle && arrival.departed) {
      details.push(`${this._t("departedAt")}${formatClock(arrival.departed, this.hass)}`);
    }

    return html`<div class="status" role="status">
      <div class="status-icon ${vehicle ? "" : "off"}">
        ${icon(vehicle ? modePath(arrival.route_type) : ICONS.noPosition, { size: 22 })}
      </div>
      <div class="status-body">
        <div class="status-title">${headline}</div>
        ${details.length || stale
          ? html`<div class="status-sub">
              ${details.map((text) => html`<span>${text}</span>`)}
              ${stale
                ? html`<span class="stale"
                    >${age < 60
                      ? this._t("positionAgeSeconds")
                      : this._t("positionAge", { n: Math.floor(age / 60) })}</span
                  >`
                : nothing}
            </div>`
          : nothing}
      </div>
    </div>`;
  }

  _renderTimeline(stops, { here, mine, passed }, showMap) {
    return html`<ol class="timeline" aria-label=${this._t("routeStops")}>
      ${stops.map((stop, index) => {
        const isHere = index === here;
        const isMine = index === mine;
        const located = isPoint(stopPoint(stop));
        const classes = [passed(index) && !isHere ? "done" : "", isHere ? "here" : "", isMine ? "mine" : ""].join(" ");
        return html`<li class=${classes}>
          <button
            class="stop"
            ?disabled=${!showMap || !located}
            title=${showMap && located ? this._t("showOnMap") : ""}
            @click=${() => this._focusStop(stop)}
          >
            <div class="track">
              <div class="node">
                ${isHere
                  ? icon(modePath(this.arrival?.route_type), { size: 16, label: this._t("vehicleHere") })
                  : isMine
                    ? icon(ICONS.myStop, { size: 16 })
                    : nothing}
              </div>
            </div>
            <div>
              <div class="stop-title">${stop.name}</div>
              <div class="stop-sub">
                ${isMine ? html`<span class="mine-label">${this._t("myStop")}</span> · ` : nothing}${[
                  stop.city,
                  stop.code,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
            </div>
            ${stop.arrival_time
              ? html`<div class="time ltr">${formatClock(stop.arrival_time, this.hass)}</div>`
              : html`<div class="time">${this._relative(stop.offset_seconds)}</div>`}
          </button>
        </li>`;
      })}
    </ol>`;
  }
}
