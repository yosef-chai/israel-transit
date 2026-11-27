import { LitElement, css, html, nothing } from "lit";

import { DEFAULTS } from "./card.js";
import { ICONS, icon } from "./icons.js";
import { localize } from "./localize.js";
import { sharedStyles } from "./styles.js";
import { BRAND_ICON, DOMAIN, fireEvent, modeColor } from "./util.js";

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
  };

  constructor() {
    super();
    this._results = [];
    this._routes = [];
    this._searching = false;
    this._searched = false;
    this._picking = false;
  }

  // Every control here is a native one: <input>, <select>, a checkbox with
  // role="switch". Home Assistant's form elements (ha-form, ha-textfield) are
  // not a promised API for custom cards and are registered lazily; when they
  // had not been, they rendered as nothing and the stop could not be changed.
  // A native control cannot fail that way, and the tokens below give it the
  // look of the built-in editors.
  static styles = [
    sharedStyles,
    css`
      .box {
        display: flex;
        flex-direction: column;
        gap: var(--ha-space-4, 16px);
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: var(--ha-space-4, 16px);
      }

      .field select,
      .field input[type="text"],
      .field input[type="number"] {
        width: 100%;
        box-sizing: border-box;
        min-height: 48px;
        padding: var(--ha-space-3, 12px) var(--ha-space-4, 16px);
        border: var(--ha-border-width-sm, 1px) solid var(--ha-color-border-neutral-normal, rgba(127, 127, 127, 0.4));
        border-radius: var(--ha-border-radius-md, 8px);
        background: var(--ha-color-surface-default, var(--card-background-color));
        color: var(--primary-text-color);
        font: inherit;
        font-size: var(--ha-font-size-l, 16px);
      }

      .field select:focus-visible,
      .field input:focus-visible {
        outline: 2px solid var(--ha-color-focus, var(--primary-color));
        outline-offset: 2px;
      }

      .switch-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--ha-space-4, 16px);
        min-height: 48px;
        cursor: pointer;
      }

      .switch-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
        font-size: var(--ha-font-size-m, 14px);
        color: var(--primary-text-color);
      }

      /* A switch built on a checkbox, in Home Assistant's proportions. */
      .switch {
        appearance: none;
        flex: 0 0 auto;
        position: relative;
        width: 36px;
        height: 20px;
        margin: 0;
        border-radius: var(--ha-border-radius-pill, 9999px);
        background: var(--ha-color-fill-neutral-loud-resting, rgba(127, 127, 127, 0.55));
        cursor: pointer;
        transition: background-color var(--ha-animation-duration-fast, 150ms);
      }

      .switch::after {
        content: "";
        position: absolute;
        inset-block-start: 2px;
        inset-inline-start: 2px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #fff;
        transition: inset-inline-start var(--ha-animation-duration-fast, 150ms);
      }

      .switch:checked {
        background: var(--primary-color);
      }

      .switch:checked::after {
        inset-inline-start: 18px;
      }

      .switch:focus-visible {
        outline: 2px solid var(--ha-color-focus, var(--primary-color));
        outline-offset: 2px;
      }

      @media (prefers-reduced-motion: reduce) {
        .switch,
        .switch::after {
          transition: none;
        }
      }

      .expandable {
        border: var(--ha-border-width-sm, 1px) solid var(--divider-color, rgba(127, 127, 127, 0.3));
        border-radius: var(--ha-border-radius-lg, 12px);
      }

      .expandable summary {
        display: flex;
        align-items: center;
        gap: var(--ha-space-2, 8px);
        min-height: 48px;
        padding-inline: var(--ha-space-3, 12px);
        list-style: none;
        cursor: pointer;
        font-size: var(--ha-font-size-m, 14px);
        font-weight: var(--ha-font-weight-medium, 500);
        color: var(--primary-text-color);
      }

      .expandable summary::-webkit-details-marker {
        display: none;
      }

      .expandable summary:focus-visible {
        outline: 2px solid var(--ha-color-focus, var(--primary-color));
        outline-offset: -2px;
        border-radius: var(--ha-border-radius-lg, 12px);
      }

      .summary-chevron {
        color: var(--secondary-text-color);
        transition: transform var(--ha-animation-duration-fast, 150ms);
      }

      :host(:dir(rtl)) .summary-chevron {
        transform: scaleX(-1);
      }

      .expandable[open] .summary-chevron {
        transform: rotate(90deg);
      }

      .switches {
        display: flex;
        flex-direction: column;
        padding: 0 var(--ha-space-4, 16px) var(--ha-space-2, 8px);
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-block-end: -4px;
      }

      .brand img {
        width: 28px;
        height: 28px;
        flex: 0 0 auto;
      }

      .brand-name {
        font-size: 0.9375rem;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      .selected {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        border-radius: 10px;
        background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.12));
      }

      .selected-body {
        flex: 1 1 auto;
        min-width: 0;
      }

      .selected-name {
        color: var(--primary-text-color);
        overflow-wrap: anywhere;
      }

      .selected-sub {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }

      /* The stop search; see the note above this stylesheet. */
      .field {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .field label {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }

      .field input {
        width: 100%;
        box-sizing: border-box;
        padding: 12px 14px;
        border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.4));
        border-radius: 10px;
        background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.1));
        color: var(--primary-text-color);
        font: inherit;
        font-size: 1rem;
      }

      .field input:focus {
        outline: none;
        border-color: var(--primary-color);
      }

      .row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .results {
        display: flex;
        flex-direction: column;
        max-height: 260px;
        overflow-y: auto;
        border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.3));
        border-radius: 10px;
      }

      .result {
        display: block;
        width: 100%;
        padding: 10px 12px;
        border: none;
        border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
        background: none;
        color: inherit;
        font: inherit;
        text-align: start;
        cursor: pointer;
      }

      .result:first-child {
        border-top: none;
      }

      .result:hover,
      .result:focus-visible {
        background: var(--ha-color-surface-lower, rgba(127, 127, 127, 0.1));
      }

      .result-name {
        color: var(--primary-text-color);
      }

      .result-sub {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }

      .hint {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }

      /* -- the ordered line list -- */

      .section {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .section-title {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      .line {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 8px;
        border-radius: 10px;
        background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.12));
      }

      .line .badge {
        min-width: 38px;
        font-size: 0.875rem;
      }

      .line-body {
        flex: 1 1 auto;
        min-width: 0;
      }

      .line-sub {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .tools {
        display: flex;
        flex: 0 0 auto;
        gap: 2px;
      }

      .tool {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        padding: 0;
        border: none;
        border-radius: 50%;
        background: none;
        color: var(--secondary-text-color);
        cursor: pointer;
      }

      .tool:hover:not(:disabled) {
        background: var(--ha-color-surface-lower, rgba(127, 127, 127, 0.14));
        color: var(--primary-text-color);
      }

      .tool:disabled {
        opacity: 0.35;
        cursor: default;
      }

      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 5px 10px;
        border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.35));
        border-radius: 16px;
        background: none;
        color: var(--primary-text-color);
        font: inherit;
        font-size: 0.8125rem;
        cursor: pointer;
      }

      .chip:hover,
      .chip:focus-visible {
        background: var(--ha-color-surface-lower, rgba(127, 127, 127, 0.12));
      }

      .chip .swatch {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--it-badge-color, var(--it-mode-unknown));
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

  _renderText(name, label, helper) {
    const id = `it-${name}`;
    return html`<div class="field">
      <label for=${id}>${label}</label>
      <input
        id=${id}
        type="text"
        .value=${this._config[name] ?? ""}
        @change=${(ev) => this._set(name, ev.target.value.trim())}
      />
      ${helper ? html`<span class="hint">${helper}</span>` : nothing}
    </div>`;
  }

  _renderNumber(name, label, min, max, helper) {
    const id = `it-${name}`;
    return html`<div class="field">
      <label for=${id}>${label}</label>
      <input
        id=${id}
        type="number"
        inputmode="numeric"
        min=${min}
        max=${max}
        step="1"
        .value=${String(this._value[name])}
        @change=${(ev) => this._setNumber(name, ev.target.value, min, max)}
      />
      ${helper ? html`<span class="hint">${helper}</span>` : nothing}
    </div>`;
  }

  _renderSwitch(name, label, helper) {
    const id = `it-${name}`;
    return html`<label class="switch-row" for=${id}>
      <span class="switch-text">
        <span>${label}</span>
        ${helper ? html`<span class="hint">${helper}</span>` : nothing}
      </span>
      <input
        id=${id}
        class="switch"
        type="checkbox"
        role="switch"
        .checked=${Boolean(this._value[name])}
        @change=${(ev) => this._set(name, ev.target.checked)}
      />
    </label>`;
  }

  _renderOptions() {
    const hasRail = this._routes.some((route) => String(route.route_type) === "2");
    const toggles = [
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
    return html`
      ${this._renderText("title", this._t("editorTitle"))}
      <div class="grid">
        ${this._renderNumber("max_arrivals", this._t("editorMaxArrivals"), 1, 20)}
        ${this._renderNumber("max_lines", this._t("editorMaxLines"), 0, 20, this._t("editorMaxLinesHelp"))}
      </div>
      ${this._lines.length
        ? html`<div class="field">
            <label for="it-order">${this._t("editorOrder")}</label>
            <select id="it-order" @change=${(ev) => this._set("order", ev.target.value)}>
              <option value="time" ?selected=${this._value.order !== "lines"}>
                ${this._t("editorOrderTime")}
              </option>
              <option value="lines" ?selected=${this._value.order === "lines"}>
                ${this._t("editorOrderLines")}
              </option>
            </select>
          </div>`
        : nothing}
      ${this._renderSwitch("show_map", this._t("editorShowMap"), this._t("editorShowMapHelp"))}
      <details class="expandable">
        <summary>
          ${icon(ICONS.chevron, { size: 20, cls: "icon summary-chevron" })}
          <span>${this._t("editorDisplay")}</span>
        </summary>
        <div class="switches">
          ${toggles.map(([name, key]) => this._renderSwitch(name, this._t(key)))}
        </div>
      </details>
      ${hasRail ? this._renderText("rail_destination", this._t("mode_2")) : nothing}
    `;
  }

  // -- rendering -------------------------------------------------------------

  render() {
    if (!this._config || !this.hass) return nothing;
    const needsPicker = !this._config.stop_code || this._picking;

    return html`
      <div class="box">
        <div class="brand">
          <img src=${BRAND_ICON} alt="" aria-hidden="true" />
          <span class="brand-name">${this._t("name")}</span>
        </div>
        ${needsPicker ? this._renderSearch() : this._renderSelected()}
        ${this._config.stop_code
          ? html`
              ${this._renderLines()} ${this._renderOptions()}
            `
          : nothing}
      </div>
    `;
  }

  _renderSelected() {
    const stop = this._stop || { code: this._config.stop_code };
    return html`
      <div class="selected">
        ${icon(ICONS.busStop, { size: 24 })}
        <div class="selected-body">
          <div class="selected-name">${stop.name || this._t("stop")}</div>
          <div class="selected-sub">
            ${[stop.street, stop.city, stop.code].filter(Boolean).join(" · ")}
          </div>
        </div>
        <button class="chip" @click=${() => (this._picking = true)}>
          ${this._t("editorChange")}
        </button>
      </div>
    `;
  }

  _renderSearch() {
    return html`
      <div class="field">
        <div class="row">
          <label for="it-search">${this._t("editorSearch")}</label>
          ${this._config.stop_code
            ? html`<button
                class="tool"
                title=${this._t("editorCancel")}
                aria-label=${this._t("editorCancel")}
                @click=${this._close}
              >
                ${icon(ICONS.close)}
              </button>`
            : nothing}
        </div>
        <input
          id="it-search"
          type="search"
          autocomplete="off"
          .value=${this._query ?? ""}
          @input=${this._onSearchInput}
        />
        <span class="hint">${this._t("editorSearchHelp")}</span>
      </div>
      ${this._searching
        ? html`<div class="hint">${this._t("editorSearching")}</div>`
        : this._results.length
          ? html`<div class="results">
              ${this._results.map(
                (stop) => html`
                  <button class="result" @click=${() => this._pick(stop)}>
                    <div class="result-name">${stop.name}</div>
                    <div class="result-sub">
                      ${[stop.street, stop.city, stop.code]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  </button>
                `,
              )}
            </div>`
          : this._searched
            ? html`<div class="hint">${this._t("editorNoResults")}</div>`
            : nothing}
    `;
  }

  _renderLines() {
    const byLine = this._routesByLine;
    const chosen = this._lines;
    const rest = [...byLine.keys()].filter((name) => !chosen.includes(name));

    return html`
      <div class="section">
        <div class="section-title">${this._t("editorLines")}</div>
        ${chosen.length
          ? chosen.map((name, index) =>
              this._renderChosenLine(name, index, chosen.length, byLine.get(name)),
            )
          : html`<div class="hint">${this._t("editorLinesHelp")}</div>`}
        ${rest.length
          ? html`<div class="chips">
              ${rest.map((name) => this._renderAddChip(name, byLine.get(name)))}
            </div>`
          : byLine.size
            ? html`<div class="hint">${this._t("editorAllShown")}</div>`
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
    return html`
      <div class="line">
        <div
          class="badge"
          style=${`--it-badge-color:${modeColor(route?.route_type)}`}
        >
          ${name}
        </div>
        <div class="line-body">
          <div class="line-sub">
            ${[route?.destination, route?.operator].filter(Boolean).join(" · ")}
          </div>
        </div>
        <div class="tools">
          <button
            class="tool"
            ?disabled=${index === 0}
            title=${this._t("editorMoveUp")}
            aria-label=${this._t("editorMoveUp")}
            @click=${() => this._move(index, -1)}
          >
            ${icon(ICONS.arrowUp)}
          </button>
          <button
            class="tool"
            ?disabled=${index === total - 1}
            title=${this._t("editorMoveDown")}
            aria-label=${this._t("editorMoveDown")}
            @click=${() => this._move(index, 1)}
          >
            ${icon(ICONS.arrowDown)}
          </button>
          <button
            class="tool"
            title=${this._t("editorRemove")}
            aria-label=${this._t("editorRemove")}
            @click=${() => this._removeLine(index)}
          >
            ${icon(ICONS.close)}
          </button>
        </div>
      </div>
    `;
  }

  _renderAddChip(name, route) {
    return html`
      <button
        class="chip"
        style=${`--it-badge-color:${modeColor(route?.route_type)}`}
        title=${`${this._t("editorAddLine")}: ${name}`}
        @click=${() => this._addLine(name)}
      >
        <span class="swatch"></span>
        <span class="line-name">${name}</span>
      </button>
    `;
  }
}
