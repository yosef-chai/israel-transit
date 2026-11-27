import { LitElement, css, html, nothing } from "lit";

import { DEFAULTS } from "./card.js";
import { ICONS, icon } from "./icons.js";
import { languageOf, localize } from "./localize.js";
import { sharedStyles } from "./styles.js";
import { DOMAIN, fireEvent, modeColor } from "./util.js";

const SEARCH_DEBOUNCE_MS = 300;

/**
 * The config as the YAML should read: only what differs from the defaults.
 *
 * Every control holds a value, defaults included, so without this touching a
 * single option would write all fourteen of them into the dashboard.
 */
const compact = (config) =>
  Object.fromEntries(
    Object.entries(config).filter(
      ([key, value]) =>
        value !== undefined &&
        value !== null &&
        value !== "" &&
        !(Array.isArray(value) && value.length === 0) &&
        DEFAULTS[key] !== value,
    ),
  );

const TOGGLES = [
  ["show_header", "editorShowHeader"],
  ["show_city", "editorShowCity"],
  ["show_stop_code", "editorShowStopCode"],
  ["show_destination", "editorShowDestination"],
  ["show_operator", "editorShowOperator"],
  ["show_mode_icon", "editorShowModeIcon"],
  ["show_realtime_tag", "editorShowRealtimeTag"],
  ["show_platform", "editorShowPlatform"],
  ["show_delay", "editorShowDelay"],
  ["show_clock", "editorShowClock"],
];

const stopSub = (stop) => [stop.street, stop.city, stop.code].filter(Boolean).join(" · ");

export class IsraelTransitCardEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _stop: { state: true },
    _routes: { state: true },
    _results: { state: true },
    _searching: { state: true },
    _searched: { state: true },
    _picking: { state: true },
    _nearby: { state: true },
  };

  constructor() {
    super();
    this._results = [];
    this._routes = [];
    this._searching = false;
    this._searched = false;
    this._picking = false;
  }

  // A custom editor, because finding a stop is a WebSocket search that a
  // getConfigForm() schema cannot hold. Home Assistant's own form elements
  // (ha-form, ha-input) are not a promised API for custom cards and are
  // registered lazily, so the controls are native ones drawn the way the
  // frontend draws its form today: a filled 56px field with a floating label
  // and a bottom line, ha-form's checkboxes, an outlined expansion panel, and
  // ha-form's 24px between fields. Every value is a theme token with a
  // fallback for releases that do not set it.
  static styles = [
    sharedStyles,
    css`
      :host {
        --it-field-bg: var(--ha-color-form-background, rgba(127, 127, 127, 0.08));
        --it-field-bg-hover: var(--ha-color-form-background-hover, rgba(127, 127, 127, 0.14));
        --it-line: var(--ha-color-border-neutral-loud, rgba(127, 127, 127, 0.6));
        --it-outline: var(--outline-color, var(--divider-color, rgba(127, 127, 127, 0.3)));
        --it-hover: var(--ha-color-fill-neutral-quiet-hover, rgba(127, 127, 127, 0.08));
        --it-duration: var(--ha-animation-duration-fast, 150ms);
        /* The semantic secondary text colour: on the dark form background
           it stays above 4.5:1, where --secondary-text-color is 4.35:1. */
        --it-secondary: var(--ha-color-text-secondary, var(--secondary-text-color));
      }

      .box {
        display: flex;
        flex-direction: column;
        gap: var(--ha-space-6, 24px);
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: var(--ha-space-6, 24px) var(--ha-space-2, 8px);
      }

      /* -- the filled text field (ha-input, appearance "material") -- */

      .field {
        display: flex;
        flex-direction: column;
        min-width: 0;
      }

      .control {
        position: relative;
        display: flex;
        align-items: center;
        gap: var(--ha-space-2, 8px);
        box-sizing: border-box;
        width: 100%;
        min-height: 56px;
        margin: 0;
        padding: 0 var(--ha-space-4, 16px);
        border: none;
        border-radius: var(--ha-border-radius-sm, 4px) var(--ha-border-radius-sm, 4px) 0 0;
        background: var(--it-field-bg);
        color: var(--primary-text-color);
        font: inherit;
        text-align: start;
        transition: background-color var(--it-duration) ease-in-out;
      }

      .control:hover {
        background: var(--it-field-bg-hover);
      }

      .control::after {
        content: "";
        position: absolute;
        inset-inline: 0;
        bottom: 0;
        height: 1px;
        background: var(--it-line);
        pointer-events: none;
        transition:
          height var(--it-duration) ease-in-out,
          background-color var(--it-duration) ease-in-out;
      }

      .control:focus-within::after {
        height: 2px;
        background: var(--primary-color);
      }

      .control > label {
        position: absolute;
        top: 20px;
        inset-inline: var(--ha-space-4, 16px);
        overflow: hidden;
        color: var(--it-secondary);
        font-size: var(--ha-font-size-m, 14px);
        line-height: var(--ha-line-height-condensed, 1.2);
        white-space: nowrap;
        text-overflow: ellipsis;
        pointer-events: none;
        transition: all var(--it-duration) ease-in-out;
      }

      .control.start > label {
        inset-inline-start: 48px;
      }

      .control:focus-within > label {
        color: var(--primary-color);
      }

      /* Raised once there is a value, as ha-input does; a select and a
         number always have one. */
      .control:focus-within > label,
      .control.raised > label,
      .control:has(input:not(:placeholder-shown)) > label {
        top: var(--ha-space-2, 8px);
        font-size: var(--ha-font-size-s, 12px);
      }

      .control input,
      .control select {
        flex: 1 1 auto;
        align-self: stretch;
        min-width: 0;
        margin: 0;
        padding: var(--ha-space-5, 20px) 0 var(--ha-space-1, 4px);
        border: none;
        outline: none;
        background: none;
        color: inherit;
        font: inherit;
        font-size: var(--ha-font-size-l, 16px);
      }

      .control select {
        appearance: none;
        padding-inline-end: 32px;
        cursor: pointer;
      }

      .control option {
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
      }

      .control input::-webkit-search-cancel-button {
        display: none;
      }

      .control .end {
        position: absolute;
        inset-inline-end: var(--ha-space-3, 12px);
        color: var(--it-secondary);
        pointer-events: none;
      }

      .control > .icon {
        color: var(--it-secondary);
      }

      .hint {
        display: flex;
        align-items: center;
        min-height: var(--ha-space-5, 20px);
        margin-inline-start: var(--ha-space-4, 16px);
        color: var(--it-secondary);
        font-size: var(--ha-font-size-s, 12px);
      }

      .hint.alone {
        margin-inline-start: 0;
      }

      /* -- the stop, picked (ha-picker-field) and being searched for -- */

      button.control {
        cursor: pointer;
      }

      button.control:focus-visible {
        outline: none;
      }

      .two-line {
        display: flex;
        flex: 1 1 auto;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
        padding-block: var(--ha-space-2, 8px);
      }

      .primary {
        overflow-wrap: anywhere;
        color: var(--primary-text-color);
        font-size: var(--ha-font-size-m, 14px);
        line-height: var(--ha-line-height-condensed, 1.2);
      }

      .secondary {
        overflow: hidden;
        color: var(--it-secondary);
        font-size: var(--ha-font-size-s, 12px);
        line-height: var(--ha-line-height-condensed, 1.2);
        white-space: nowrap;
        text-overflow: ellipsis;
      }

      .icon-button {
        display: inline-flex;
        flex: 0 0 auto;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        margin: 0;
        padding: 0;
        border: none;
        border-radius: var(--ha-border-radius-circle, 50%);
        background: none;
        color: var(--it-secondary);
        cursor: pointer;
      }

      .icon-button:hover:not(:disabled) {
        background: var(--it-hover);
        color: var(--primary-text-color);
      }

      .icon-button:focus-visible,
      .chip:focus-visible,
      .check input:focus-visible {
        outline: 2px solid var(--ha-color-focus, var(--primary-color));
        outline-offset: 2px;
      }

      .icon-button:disabled {
        opacity: 0.3;
        cursor: default;
      }

      .control .icon-button {
        margin-inline-end: calc(-1 * var(--ha-space-2, 8px));
      }

      .results {
        display: flex;
        flex-direction: column;
        max-height: 280px;
        margin-block-start: var(--ha-space-2, 8px);
        overflow-y: auto;
        overscroll-behavior: contain;
        scrollbar-color: var(--scrollbar-thumb-color, rgba(127, 127, 127, 0.5)) transparent;
        scrollbar-width: thin;
        border: 1px solid var(--it-outline);
        border-radius: var(--ha-border-radius-md, 8px);
      }

      .result {
        display: flex;
        flex: 0 0 auto;
        flex-direction: column;
        justify-content: center;
        gap: 2px;
        box-sizing: border-box;
        width: 100%;
        min-height: 56px;
        padding: var(--ha-space-2, 8px) var(--ha-space-4, 16px);
        border: none;
        background: none;
        color: inherit;
        font: inherit;
        text-align: start;
        cursor: pointer;
      }

      .result + .result {
        border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
      }

      .result:hover {
        background: var(--it-hover);
      }

      .result:focus-visible {
        outline: 2px solid var(--ha-color-focus, var(--primary-color));
        outline-offset: -2px;
      }

      .status {
        padding: var(--ha-space-2, 8px) var(--ha-space-4, 16px) 0;
        color: var(--it-secondary);
        font-size: var(--ha-font-size-s, 12px);
      }

      /* -- checkboxes (ha-form-boolean) -- */

      .check {
        display: flex;
        align-items: center;
        gap: var(--ha-space-2, 8px);
        min-height: 56px;
        cursor: pointer;
      }

      .check input {
        flex: 0 0 auto;
        width: 18px;
        height: 18px;
        margin: 11px;
        accent-color: var(--primary-color);
        cursor: pointer;
      }

      .check-text {
        display: flex;
        flex-direction: column;
        color: var(--primary-text-color);
        font-size: var(--ha-font-size-m, 14px);
      }

      .check-text .hint {
        min-height: 0;
        margin: 0;
      }

      .checks {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        column-gap: var(--ha-space-2, 8px);
      }

      /* -- the expansion panel (ha-expansion-panel, outlined) -- */

      .panel {
        border: 1px solid var(--it-outline);
        border-radius: var(--ha-border-radius-md, 8px);
      }

      .panel summary {
        display: flex;
        align-items: center;
        min-height: 48px;
        padding-inline: var(--ha-space-3, 12px) var(--ha-space-2, 8px);
        border-radius: var(--ha-border-radius-md, 8px);
        color: var(--primary-text-color);
        font-weight: var(--ha-font-weight-medium, 500);
        list-style: none;
        cursor: pointer;
      }

      .panel summary::-webkit-details-marker {
        display: none;
      }

      .panel summary:focus-visible {
        outline: none;
        background: var(--ha-color-fill-neutral-normal-active, var(--it-hover));
      }

      .panel summary > span {
        flex: 1 1 auto;
      }

      .panel summary .icon {
        color: var(--it-secondary);
        transition: transform var(--it-duration) cubic-bezier(0.4, 0, 0.2, 1);
      }

      .panel[open] summary .icon {
        transform: rotate(180deg);
      }

      .panel[open] summary {
        border-end-start-radius: 0;
        border-end-end-radius: 0;
      }

      .panel-content {
        padding: 0 var(--ha-space-3, 12px) var(--ha-space-2, 8px);
      }

      @media (prefers-reduced-motion: reduce) {
        .control,
        .control::after,
        .control > label,
        .panel summary .icon {
          transition: none;
        }
      }

      /* -- the ordered line list -- */

      .section {
        display: flex;
        flex-direction: column;
        gap: var(--ha-space-2, 8px);
      }

      .section-title {
        margin: 0;
        color: var(--primary-text-color);
        font-size: var(--ha-font-size-m, 14px);
        font-weight: var(--ha-font-weight-medium, 500);
      }

      .lines {
        display: flex;
        flex-direction: column;
        margin: 0;
        padding: 0;
        list-style: none;
      }

      .line {
        display: flex;
        align-items: center;
        gap: var(--ha-space-3, 12px);
        min-height: 48px;
      }

      .line .badge {
        min-width: 40px;
      }

      .line-body {
        flex: 1 1 auto;
        min-width: 0;
      }

      .tools {
        display: flex;
        flex: 0 0 auto;
      }

      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: var(--ha-space-2, 8px);
      }

      /* ha-assist-chip: 32px high, a pill, outlined. */
      .chip {
        display: inline-flex;
        align-items: center;
        gap: var(--ha-space-1, 4px);
        box-sizing: border-box;
        height: 32px;
        padding-inline: var(--ha-space-2, 8px) var(--ha-space-4, 16px);
        border: 1px solid var(--ha-color-border-neutral-quiet, var(--it-outline));
        border-radius: var(--ha-border-radius-pill, 9999px);
        background: none;
        color: var(--primary-text-color);
        font: inherit;
        font-size: var(--ha-font-size-m, 14px);
        font-weight: var(--ha-font-weight-medium, 500);
        cursor: pointer;
      }

      .chip:hover {
        background: var(--it-hover);
      }

      .chip .icon {
        color: var(--it-badge-color, var(--it-mode-unknown));
      }

      .line-name {
        font-variant-numeric: tabular-nums;
        direction: ltr;
        unicode-bidi: isolate;
      }
    `,
  ];

  connectedCallback() {
    super.connectedCallback();
    if (this._config?.stop_code && !this._stop) this._loadStop();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this._searchTimer);
  }

  updated(changed) {
    // setConfig can arrive before hass does, and then had nothing to ask with.
    if (changed.has("hass") && !changed.get("hass") && !this._stop) {
      this._loadStop();
    }
    // התחנות הקרובות לבית, פעם אחת, ברגע שבוחר התחנה מוצג.
    if (this.hass && this._nearby === undefined && (!this._config?.stop_code || this._picking)) {
      this._loadNearby();
    }
  }

  async _loadNearby() {
    this._nearby = null;
    try {
      this._nearby = await this.hass.callWS({ type: `${DOMAIN}/nearby_stops`, limit: 8 });
    } catch {
      this._nearby = [];
    }
  }

  setConfig(config) {
    this._config = { ...config };
    // Numbers here, strings from hand-written YAML: comparing them raw would
    // reload the stop on every keystroke elsewhere in the editor.
    if (config.stop_code && Number(this._stop?.code) !== Number(config.stop_code)) {
      this._loadStop();
    }
  }

  _t(key) {
    return localize(this.hass, key);
  }

  async _loadStop() {
    if (!this.hass || !this._config?.stop_code) return;
    const asked = Number(this._config.stop_code);
    try {
      const [data, routes] = await Promise.all([
        this.hass.callWS({ type: `${DOMAIN}/stop`, stop_code: asked }),
        this.hass.callWS({ type: `${DOMAIN}/stop_routes`, stop_code: asked }),
      ]);
      // The user can pick a different stop while this is still in flight.
      if (asked !== Number(this._config?.stop_code)) return;
      this._stop = data.stop;
      this._routes = routes;
    } catch {
      if (asked !== Number(this._config?.stop_code)) return;
      // A stop we cannot load is still a stop the user typed: keep the code and
      // let the card itself report the problem.
      this._stop = { code: asked, name: "" };
      this._routes = [];
    }
  }

  // -- choosing a stop -------------------------------------------------------

  _onSearchInput(ev) {
    // Plain field, not reactive state: searching re-renders on its own, and
    // this only has to survive that render so the box keeps what was typed.
    this._query = ev.target.value ?? "";
    clearTimeout(this._searchTimer);
    if (this._query.trim().length < 2) {
      this._results = [];
      this._searched = false;
      return;
    }
    const query = this._query.trim();
    this._searchTimer = setTimeout(() => this._search(query), SEARCH_DEBOUNCE_MS);
  }

  async _search(query) {
    if (!this.hass) return;
    // Answers can come back out of order; only the latest search may land, or
    // a slow one for "כפר" would replace the results for "כפר סבא".
    const asked = (this._searchSeq = (this._searchSeq || 0) + 1);
    this._searching = true;
    let results = [];
    try {
      results = await this.hass.callWS({
        type: `${DOMAIN}/search_stops`,
        query,
        limit: 30,
      });
    } catch {
      results = [];
    }
    if (asked !== this._searchSeq) return;
    this._results = results;
    this._searching = false;
    this._searched = true;
  }

  _pick(stop) {
    this._stop = stop;
    this._close();
    // A new stop invalidates the previous line filter.
    this._emit({ ...this._config, stop_code: stop.code, lines: [] });
    this._loadRoutes(stop.code);
  }

  async _startPicking() {
    this._picking = true;
    await this.updateComplete;
    this.shadowRoot.querySelector("#it-search")?.focus();
  }

  /** Leave the stop picker, forgetting what was typed into it. */
  _close() {
    this._results = [];
    this._searched = false;
    this._picking = false;
    this._query = "";
  }

  async _loadRoutes(code) {
    try {
      this._routes = await this.hass.callWS({
        type: `${DOMAIN}/stop_routes`,
        stop_code: Number(code),
      });
    } catch {
      this._routes = [];
    }
  }

  // -- choosing and ordering lines -------------------------------------------

  /** One entry per line number at the stop; a line has a route per direction. */
  get _routesByLine() {
    const byLine = new Map();
    for (const route of this._routes) {
      const name = String(route.line_name);
      if (!byLine.has(name)) byLine.set(name, route);
    }
    return byLine;
  }

  get _lines() {
    return (this._config?.lines || []).map(String);
  }

  _setLines(lines) {
    this._emit({ ...this._config, lines });
  }

  _move(index, delta) {
    const lines = [...this._lines];
    const target = index + delta;
    if (target < 0 || target >= lines.length) return;
    [lines[index], lines[target]] = [lines[target], lines[index]];
    // Arranging the list is a statement about the order it should appear in.
    // Leaving the card sorted by time here would make the arrows look broken.
    this._emit({ ...this._config, lines, order: "lines" });
  }

  _removeLine(index) {
    this._setLines(this._lines.filter((_, position) => position !== index));
  }

  _addLine(name) {
    this._setLines([...this._lines, name]);
  }

  // -- the rest of the options ----------------------------------------------

  _emit(config) {
    this._config = compact(config);
    fireEvent(this, "config-changed", { config: this._config });
  }

  _set(name, value) {
    this._emit({ ...this._config, [name]: value });
  }

  /** A whole number within limits, or the default when the box is cleared. */
  _setNumber(name, raw, min, max) {
    const value = Number.parseInt(raw, 10);
    this._set(name, Number.isNaN(value) ? DEFAULTS[name] : Math.min(max, Math.max(min, value)));
  }

  get _value() {
    return { ...DEFAULTS, ...this._config };
  }

  _hint(text, id) {
    return text ? html`<span class="hint" id=${id}>${text}</span>` : nothing;
  }

  _renderText(name, label, helper) {
    const id = `it-${name}`;
    return html`<div class="field">
      <div class="control">
        <label for=${id}>${label}</label>
        <input
          id=${id}
          type="text"
          placeholder=" "
          aria-describedby=${helper ? `${id}-hint` : nothing}
          .value=${this._config[name] ?? ""}
          @change=${(ev) => this._set(name, ev.target.value.trim())}
        />
      </div>
      ${this._hint(helper, `${id}-hint`)}
    </div>`;
  }

  _renderNumber(name, label, min, max, helper) {
    const id = `it-${name}`;
    return html`<div class="field">
      <div class="control raised">
        <label for=${id}>${label}</label>
        <input
          id=${id}
          type="number"
          inputmode="numeric"
          min=${min}
          max=${max}
          step="1"
          aria-describedby=${helper ? `${id}-hint` : nothing}
          .value=${String(this._value[name] ?? "")}
          @change=${(ev) => this._setNumber(name, ev.target.value, min, max)}
        />
      </div>
      ${this._hint(helper, `${id}-hint`)}
    </div>`;
  }

  _renderSelect(name, label, options) {
    const id = `it-${name}`;
    return html`<div class="field">
      <div class="control raised">
        <label for=${id}>${label}</label>
        <select id=${id} @change=${(ev) => this._set(name, ev.target.value)}>
          ${options.map(
            ([value, text]) =>
              html`<option value=${value} ?selected=${this._value[name] === value}>
                ${text}
              </option>`,
          )}
        </select>
        ${icon(ICONS.menuDown, { size: 24, cls: "icon end" })}
      </div>
    </div>`;
  }

  _renderCheck(name, label, helper) {
    const id = `it-${name}`;
    return html`<label class="check" for=${id}>
      <input
        id=${id}
        type="checkbox"
        aria-describedby=${helper ? `${id}-hint` : nothing}
        .checked=${Boolean(this._value[name])}
        @change=${(ev) => this._set(name, ev.target.checked)}
      />
      <span class="check-text">
        <span>${label}</span>
        ${this._hint(helper, `${id}-hint`)}
      </span>
    </label>`;
  }

  _renderOptions() {
    const hasRail = this._routes.some((route) => String(route.route_type) === "2");
    return html`
      ${this._renderText("title", this._t("editorTitle"))}
      <div class="grid">
        ${this._renderNumber("max_arrivals", this._t("editorMaxArrivals"), 1, 20)}
        ${this._renderNumber("max_lines", this._t("editorMaxLines"), 0, 20, this._t("editorMaxLinesHelp"))}
      </div>
      ${this._lines.length
        ? this._renderSelect("order", this._t("editorOrder"), [
            ["time", this._t("editorOrderTime")],
            ["lines", this._t("editorOrderLines")],
          ])
        : nothing}
      ${hasRail ? this._renderText("rail_destination", this._t("mode_2")) : nothing}
      <div class="grid">
        ${this._renderNumber("walk_minutes", this._t("editorWalk"), 0, 60, this._t("editorWalkHelp"))}
        ${this._renderNumber("alert_minutes", this._t("editorAlertMinutes"), 0, 60)}
      </div>
      ${this._renderNotify()}
      ${this._renderCheck("show_map", this._t("editorShowMap"), this._t("editorShowMapHelp"))}
      <details class="panel">
        <summary>
          <span>${this._t("editorDisplay")}</span>
          ${icon(ICONS.expand, { size: 24, cls: "icon" })}
        </summary>
        <div class="panel-content checks">
          ${TOGGLES.map(([name, key]) => this._renderCheck(name, this._t(key)))}
        </div>
      </details>
    `;
  }

  /** לאן נשלחת ההתראה מפרטי הקו. בלי בחירה: הטלפונים של מי שלוחץ. */
  _renderNotify() {
    const targets = Object.keys(this.hass.states || {})
      .filter((id) => id.startsWith("notify."))
      .map((id) => [id, this.hass.states[id].attributes?.friendly_name || id]);
    if (!targets.length) return nothing;
    return this._renderSelect("notify_entity", this._t("editorNotify"), [
      ["", this._t("editorNotifyMine")],
      ...targets,
    ]);
  }

  // -- rendering -------------------------------------------------------------

  render() {
    if (!this._config || !this.hass) return nothing;
    const needsPicker = !this._config.stop_code || this._picking;

    return html`
      <div class="box">
        ${needsPicker ? this._renderSearch() : this._renderSelected()}
        ${this._config.stop_code
          ? html`${this._renderLines()} ${this._renderOptions()}`
          : nothing}
      </div>
    `;
  }

  /** The chosen stop, drawn like Home Assistant's picker field. */
  _renderSelected() {
    const stop = this._stop || { code: this._config.stop_code };
    const name = stop.name || this._t("stop");
    return html`<div class="field">
      <button
        class="control picker"
        aria-label=${`${this._t("editorStop")}: ${name}. ${this._t("editorChange")}`}
        @click=${this._startPicking}
      >
        ${icon(ICONS.busStop, { size: 24 })}
        <span class="two-line">
          <span class="primary">${name}</span>
          <span class="secondary">${stopSub(stop)}</span>
        </span>
        ${icon(ICONS.menuDown, { size: 24 })}
      </button>
    </div>`;
  }

  _renderSearch() {
    return html`
      <div class="field">
        <div class="control start">
          ${icon(ICONS.search, { size: 24 })}
          <label for="it-search">${this._t("editorSearch")}</label>
          <input
            id="it-search"
            type="search"
            autocomplete="off"
            placeholder=" "
            aria-describedby="it-search-hint"
            .value=${this._query ?? ""}
            @input=${this._onSearchInput}
            @keydown=${(ev) => ev.key === "Escape" && this._config.stop_code && this._close()}
          />
          ${this._config.stop_code
            ? html`<button
                class="icon-button"
                title=${this._t("editorCancel")}
                aria-label=${this._t("editorCancel")}
                @click=${this._close}
              >
                ${icon(ICONS.close)}
              </button>`
            : nothing}
        </div>
        ${this._hint(this._t("editorSearchHelp"), "it-search-hint")}
        <div role="status" aria-live="polite">
          ${this._searching
            ? html`<div class="status">${this._t("editorSearching")}</div>`
            : this._searched && !this._results.length
              ? html`<div class="status">${this._t("editorNoResults")}</div>`
              : nothing}
        </div>
        ${!this._searching && this._results.length
          ? this._renderResults(this._results)
          : !(this._query ?? "").trim() && this._nearby?.length
            ? html`<div class="status">${this._t("editorNearby")}</div>
                ${this._renderResults(this._nearby)}`
            : nothing}
      </div>
    `;
  }

  _renderResults(stops) {
    return html`<div class="results">
      ${stops.map(
        (stop) => html`
          <button class="result" @click=${() => this._pick(stop)}>
            <span class="primary">${stop.name}</span>
            <span class="secondary"
              >${[stopSub(stop), stop.distance != null ? this._distance(stop.distance) : ""]
                .filter(Boolean)
                .join(" · ")}</span
            >
          </button>
        `,
      )}
    </div>`;
  }

  /** "350 מ׳" או "1.2 ק״מ", כמו בהוספת תחנה באינטגרציה. */
  _distance(metres) {
    const he = languageOf(this.hass) === "he";
    return metres < 1000
      ? `${Math.round(metres / 10) * 10} ${he ? "מ׳" : "m"}`
      : `${(metres / 1000).toFixed(1)} ${he ? "ק״מ" : "km"}`;
  }

  _renderLines() {
    const byLine = this._routesByLine;
    const chosen = this._lines;
    const rest = [...byLine.keys()].filter((name) => !chosen.includes(name));

    return html`
      <div class="section" role="group" aria-labelledby="it-lines-title">
        <h3 class="section-title" id="it-lines-title">${this._t("editorLines")}</h3>
        ${chosen.length
          ? html`<ul class="lines">
              ${chosen.map((name, index) =>
                this._renderChosenLine(name, index, chosen.length, byLine.get(name)),
              )}
            </ul>`
          : html`<span class="hint alone">${this._t("editorLinesHelp")}</span>`}
        ${rest.length
          ? html`<div class="chips">
              ${rest.map((name) => this._renderAddChip(name, byLine.get(name)))}
            </div>`
          : byLine.size
            ? html`<span class="hint alone">${this._t("editorAllShown")}</span>`
            : nothing}
      </div>
    `;
  }

  /**
   * One chosen line, with the controls that order it.
   *
   * Arrows rather than dragging: they work with a keyboard, with a screen
   * reader and with a thumb, and they need no sortable library that a custom
   * card cannot rely on being loaded.
   */
  _renderChosenLine(name, index, total, route) {
    const sub = [route?.destination, route?.operator].filter(Boolean).join(" · ");
    return html`
      <li class="line">
        <div class="badge" style=${`--it-badge-color:${modeColor(route?.route_type)}`}>
          ${name}
        </div>
        <div class="line-body">
          <div class="secondary">${sub}</div>
        </div>
        <div class="tools">
          <button
            class="icon-button"
            ?disabled=${index === 0}
            title=${this._t("editorMoveUp")}
            aria-label=${`${this._t("editorMoveUp")}: ${name}`}
            @click=${() => this._move(index, -1)}
          >
            ${icon(ICONS.arrowUp)}
          </button>
          <button
            class="icon-button"
            ?disabled=${index === total - 1}
            title=${this._t("editorMoveDown")}
            aria-label=${`${this._t("editorMoveDown")}: ${name}`}
            @click=${() => this._move(index, 1)}
          >
            ${icon(ICONS.arrowDown)}
          </button>
          <button
            class="icon-button"
            title=${this._t("editorRemove")}
            aria-label=${`${this._t("editorRemove")}: ${name}`}
            @click=${() => this._removeLine(index)}
          >
            ${icon(ICONS.close)}
          </button>
        </div>
      </li>
    `;
  }

  _renderAddChip(name, route) {
    return html`
      <button
        class="chip"
        style=${`--it-badge-color:${modeColor(route?.route_type)}`}
        aria-label=${`${this._t("editorAddLine")}: ${name}`}
        title=${`${this._t("editorAddLine")}: ${name}`}
        @click=${() => this._addLine(name)}
      >
        ${icon(ICONS.plus, { size: 18 })}
        <span class="line-name">${name}</span>
      </button>
    `;
  }
}
