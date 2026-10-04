import { LitElement, html, nothing } from "lit";

import { localize } from "./localize.js";
import { cardStyles, sharedStyles } from "./styles.js";
import {
  DOMAIN,
  errorMessage,
  formatClock,
  minutesUntil,
  modeColor,
  modeIcon,
} from "./util.js";

// The backend answers every stop from a shared 60 s cache (or straight from a
// configured stop's coordinator), so several open dashboards still add up to one
// upstream request. Minutes are recounted locally in between so the countdown
// stays honest without asking again.
const REFRESH_MS = 30000;
const TICK_MS = 10000;
// A vehicle stays on the board this long past its time, the same grace the
// backend gives: "now" is often still pulling in. After that it has left.
const DEPARTED_MS = 60000;

// Every visible part of a row can be switched off, and everything is on by
// default except the two that add clutter more often than they add information.
export const DEFAULTS = {
  max_arrivals: 6,
  max_lines: 0, // 0 = however many the stop has
  order: "time", // "time" | "lines"
  show_header: true,
  show_city: true,
  show_stop_code: true,
  show_destination: true,
  show_operator: true,
  show_mode_icon: false,
  show_realtime_tag: true,
  show_platform: true,
  show_delay: true,
  show_clock: false,
  show_map: true,
};

export class IsraelTransitCard extends LitElement {
  static properties = {
    _config: { state: true },
    _data: { state: true },
    _error: { state: true },
    _tick: { state: true },
    _stopDialog: { state: true },
    _routeDialog: { state: true },
  };

  static styles = [sharedStyles, cardStyles];

  constructor() {
    super();
    this._data = null;
    this._error = null;
    this._tick = 0;
    this._stopDialog = false;
    this._routeDialog = null;
  }

  /**
   * Home Assistant assigns this on every state change in the whole instance,
   * which on a busy system is several times a second. Nothing the card renders
   * follows from it beyond the language and the connection, so it is held as a
   * plain field: as a reactive property it would re-render every card on screen
   * every time any unrelated entity changed.
   */
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (hass?.connection !== this._connection) this._watch(hass?.connection);
    if (first) this._refresh();
  }

  get hass() {
    return this._hass;
  }

  static getConfigElement() {
    return document.createElement("israel-transit-card-editor");
  }

  static getStubConfig(hass) {
    // Prefer a stop the user has already set up, so the preview shows real data.
    const configured = Object.values(hass?.states || {}).find(
      (state) => state.attributes?.stop_code,
    );
    // Just the stop: setConfig fills the rest in, and a stub that spelled out
    // every default would drop thirteen lines of noise into the user's YAML.
    return {
      stop_code: configured?.attributes.stop_code ?? null,
      max_arrivals: DEFAULTS.max_arrivals,
    };
  }

  setConfig(config) {
    // No stop yet is a card still being set up, not a broken one: the card
    // picker adds it exactly like that, and it renders as "no stop selected".
    if (!config || typeof config !== "object") {
      throw new Error(localize(this.hass, "errorNoStop"));
    }
    this._config = { ...DEFAULTS, ...config };
    this._data = null;
    this._error = null;
    this._refresh();
  }

  getCardSize() {
    return (this._config?.max_arrivals ?? DEFAULTS.max_arrivals) + 2;
  }

  getGridOptions() {
    const rows = Math.min(this._config?.max_arrivals ?? DEFAULTS.max_arrivals, 8);
    const header = this._config?.show_header === false ? 1 : 2;
    return { rows: rows + header, columns: 12, min_rows: 3, min_columns: 6 };
  }

  connectedCallback() {
    super.connectedCallback();
    this._startTimers();
    this._onVisibility = () => {
      if (document.visibilityState === "visible") {
        this._startTimers();
        this._refresh();
      } else {
        this._stopTimers();
      }
    };
    document.addEventListener("visibilitychange", this._onVisibility);
    this._connection?.addEventListener("ready", this._onReconnect);
    this._refresh();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._stopTimers();
    document.removeEventListener("visibilitychange", this._onVisibility);
    this._connection?.removeEventListener("ready", this._onReconnect);
  }

  // Home Assistant restarting, or the network dropping, leaves the board
  // frozen at the last answer. Asking again the moment the socket is back
  // beats waiting out the rest of the polling interval.
  _onReconnect = () => this._refresh();

  _watch(connection) {
    this._connection?.removeEventListener("ready", this._onReconnect);
    this._connection = connection;
    if (this.isConnected) connection?.addEventListener("ready", this._onReconnect);
  }

  _startTimers() {
    this._stopTimers();
    // A hidden dashboard should not be polling a free community service.
    if (document.visibilityState === "hidden") return;
    this._refreshTimer = setInterval(() => this._refresh(), REFRESH_MS);
    this._tickTimer = setInterval(() => {
      this._tick = Date.now();
    }, TICK_MS);
  }

  _stopTimers() {
    clearInterval(this._refreshTimer);
    clearInterval(this._tickTimer);
    this._refreshTimer = undefined;
    this._tickTimer = undefined;
  }

  async _refresh() {
    if (!this.hass || !this._config?.stop_code) return;
    const asked = Number(this._config.stop_code);
    try {
      const data = await this.hass.callWS({
        type: `${DOMAIN}/stop`,
        stop_code: asked,
        rail_destination: this._config.rail_destination || null,
      });
      // Changing the stop in the editor calls setConfig while the previous
      // stop's request is still in flight. Without this the slower answer wins
      // and the card goes on showing the stop the user just replaced, which
      // looks exactly like the change having been ignored.
      if (asked !== Number(this._config?.stop_code)) return;
      this._data = data;
      this._error = null;
      this._followVehicle();
    } catch (err) {
      if (asked !== Number(this._config?.stop_code)) return;
      // The last good board stays up: one failed poll -- a restart, a dropped
      // connection -- says nothing about the buses already on it.
      this._error = errorMessage(this.hass, err);
    }
  }

  /**
   * Keep an open line detail view pointed at the current sighting.
   *
   * The dialog holds one arrival, and every refresh replaces the whole list, so
   * without this the map would freeze at wherever the vehicle was when it was
   * opened -- which is the opposite of what a live position is for.
   */
  _followVehicle() {
    const open = this._routeDialog;
    if (!open) return;
    const arrivals = this._data?.arrivals || [];
    const next = open.vehicle_ref
      ? arrivals.find((a) => a.vehicle_ref === open.vehicle_ref)
      : arrivals.find((a) => a.line_ref === open.line_ref);
    if (next) this._routeDialog = next;
  }

  _t(key) {
    return localize(this.hass, key);
  }

  /** Arrivals after the configured line filter, ordering and limits. */
  get _arrivals() {
    const config = this._config;
    // Read on every tick, so a vehicle that has left drops off between polls
    // instead of lingering as "now" until the next answer.
    const cutoff = Date.now() - DEPARTED_MS;
    const all = (this._data?.arrivals || []).filter(
      (arrival) => !(Date.parse(arrival.eta) < cutoff),
    );
    const chosen = (config.lines || []).map(String);
    let rows = chosen.length
      ? all.filter((arrival) => chosen.includes(String(arrival.line_name)))
      : all;

    // Sorting is stable and the backend sorts by time, so lines stay in the
    // order the user arranged them and each line stays in time order within it.
    if (config.order === "lines" && chosen.length) {
      rows = [...rows].sort(
        (a, b) =>
          chosen.indexOf(String(a.line_name)) - chosen.indexOf(String(b.line_name)),
      );
    }

    const maxLines = Number(config.max_lines) || 0;
    if (maxLines > 0) {
      const kept = new Set();
      rows = rows.filter((arrival) => {
        const line = String(arrival.line_name);
        if (kept.has(line)) return true;
        if (kept.size >= maxLines) return false;
        kept.add(line);
        return true;
      });
    }

    return rows.slice(0, config.max_arrivals ?? DEFAULTS.max_arrivals);
  }

  render() {
    if (!this._config) return nothing;
    if (!this._config.stop_code) {
      return html`<ha-card
        ><div class="empty">${this._t("editorNoStop")}</div></ha-card
      >`;
    }

    const stop = this._data?.stop;
    // _tick is read so departed rows drop off, and countdowns move, on time.
    void this._tick;
    const arrivals = this._data ? this._arrivals : [];

    return html`
      <ha-card>
        ${this._config.show_header === false ? nothing : this._renderHeader(stop)}
        ${this._error && this._data
          ? html`<div class="stale" role="status">
              <ha-icon icon="mdi:cloud-alert-outline"></ha-icon>
              <span>${this._t("staleData")}</span>
            </div>`
          : nothing}
        <div class="rows">
          ${!this._data
            ? this._error
              ? html`<div class="error" role="alert">${this._error}</div>`
              : html`<div class="empty">${this._t("loading")}</div>`
            : arrivals.length === 0
              ? html`<div class="empty">${this._emptyMessage()}</div>`
              : arrivals.map((arrival) => this._renderRow(arrival))}
        </div>
        ${this._renderDialogs(stop)}
      </ha-card>
    `;
  }

  /**
   * Nothing to show can mean three different things, and saying which one is
   * the difference between a card that looks broken and one that is honest.
   */
  _emptyMessage() {
    if (this._config.lines?.length) return this._t("noArrivals");
    // Neither feed publishes anything for this stop -- the Tel Aviv light rail
    // platforms are the known case. Not a temporary outage.
    if (this._data.realtime_error && !this._data.routes?.length) {
      return this._t("noData");
    }
    if (this._data.realtime_error) return this._t("noRealtime");
    return this._t("noArrivals");
  }

  _renderHeader(stop) {
    const title = this._config.title || stop?.name || this._t("loading");
    const city = this._config.show_city !== false && stop?.city;
    const code = this._config.show_stop_code !== false && stop?.code;

    return html`
      <button
        class="header"
        part="header"
        @click=${() => (this._stopDialog = true)}
        aria-label=${this._t("stopDetails")}
      >
        <div class="titles">
          <div class="stop-name">${title}</div>
          ${city || code
            ? html`<div class="stop-meta">
                ${city ? html`<span>${stop.city}</span>` : nothing}
                ${code ? html`<span class="code">${stop.code}</span>` : nothing}
              </div>`
            : nothing}
        </div>
        <ha-icon class="muted" icon="mdi:information-outline"></ha-icon>
      </button>
    `;
  }

  _renderRow(arrival) {
    const config = this._config;
    const minutes = minutesUntil(arrival.eta);
    // Past an hour a countdown stops meaning anything; show the clock instead.
    const asClock = minutes === null || minutes > 59;
    const clock = formatClock(arrival.eta, this.hass);

    return html`
      <button class="row" @click=${() => (this._routeDialog = arrival)}>
        ${config.show_mode_icon
          ? html`<ha-icon
              class="mode"
              .icon=${modeIcon(arrival.route_type)}
            ></ha-icon>`
          : nothing}
        <div
          class="badge"
          style=${`--it-badge-color:${modeColor(arrival.route_type)}`}
        >
          ${arrival.line_name}
        </div>
        <div class="row-body">
          ${config.show_destination !== false
            ? html`<div class="destination">
                ${arrival.destination || arrival.line_name}
              </div>`
            : nothing}
          ${this._renderSub(arrival)}
        </div>
        <div class="eta ${minutes === 0 ? "eta-now" : ""}">
          ${asClock
            ? html`<span class="eta-value eta-clock">${clock}</span>`
            : minutes === 0
              ? html`<span class="eta-value">${this._t("now")}</span>`
              : html`<span class="eta-value">${minutes}</span>
                  <span class="eta-unit">${this._t("minutes")}</span>`}
          ${config.show_clock && !asClock
            ? html`<span class="at-clock">${clock}</span>`
            : nothing}
          ${config.show_delay !== false && arrival.delay_minutes
            ? html`<span class="delay">+${arrival.delay_minutes}</span>`
            : nothing}
        </div>
      </button>
    `;
  }

  /** The second line of a row: operator, timetable tag, platform. */
  _renderSub(arrival) {
    const config = this._config;
    const parts = [
      config.show_operator !== false && arrival.operator
        ? html`<span class="operator">${arrival.operator}</span>`
        : nothing,
      // Only the timetabled rows carry a tag. A live arrival is the normal
      // case, so labelling every one of them said nothing while crowding out
      // the operator and the platform.
      config.show_realtime_tag !== false && !arrival.is_realtime
        ? html`<span class="tag timetable"
            ><ha-icon
              icon="mdi:calendar-clock"
              style="--mdc-icon-size:13px"
            ></ha-icon
            >${this._t("scheduled")}</span
          >`
        : nothing,
      config.show_platform !== false && arrival.platform
        ? html`<span>${this._t("platform")} ${arrival.platform}</span>`
        : nothing,
    ].filter((part) => part !== nothing);

    if (!parts.length) return nothing;
    // Separators go between what is actually there. Baking one into each part
    // left a stray dot on every row whose later parts were switched off.
    return html`<div class="sub">
      ${parts.map((part, index) =>
        index ? html`<span class="sep">·</span>${part}` : part,
      )}
    </div>`;
  }

  _renderDialogs(stop) {
    return html`
      ${this._stopDialog
        ? html`<israel-transit-stop-dialog
            .hass=${this.hass}
            .stop=${stop}
            .open=${true}
            @israel-transit-dialog-closed=${() => (this._stopDialog = false)}
          ></israel-transit-stop-dialog>`
        : nothing}
      ${this._routeDialog
        ? html`<israel-transit-route-dialog
            .hass=${this.hass}
            .arrival=${this._routeDialog}
            .stopCode=${stop?.code ?? this._config.stop_code}
            .showMap=${this._config.show_map !== false}
            .open=${true}
            @israel-transit-dialog-closed=${() => (this._routeDialog = null)}
          ></israel-transit-route-dialog>`
        : nothing}
    `;
  }
}
