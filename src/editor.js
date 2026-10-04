import { LitElement, css, html, nothing } from "lit";

import { DEFAULTS } from "./card.js";
import { localize } from "./localize.js";
import { sharedStyles } from "./styles.js";
import { BRAND_ICON, DOMAIN, fireEvent, modeColor } from "./util.js";

const SEARCH_DEBOUNCE_MS = 300;

/**
 * The config as the YAML should read: only what differs from the defaults.
 *
 * ha-form hands back every field it shows, defaults included, so without this
 * touching a single option wrote all fourteen of them into the dashboard.
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

  // The search box is a plain <input>, not an <ha-textfield>.
  //
  // Home Assistant registers its form elements lazily, and a custom card has no
  // supported way to force that -- the usual trick of building a built-in
  // card's editor only works while that editor still imports them. When it does
  // not, <ha-textfield> stays an unknown element: it renders as nothing at all,
  // and the stop cannot be changed because there is no box to type into. A
  // plain input cannot fail that way, and the theme tokens below give it the
  // same look.
  static styles = [
    sharedStyles,
    css`
      .box {
        display: flex;
        flex-direction: column;
        gap: 16px;
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
        width: 32px;
        height: 32px;
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

      .tool ha-icon {
        --mdc-icon-size: 20px;
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

  _onFormChange(ev) {
    ev.stopPropagation();
    this._emit({ ...this._config, ...ev.detail.value });
  }

  _emit(config) {
    this._config = compact(config);
    fireEvent(this, "config-changed", { config: this._config });
  }

  get _schema() {
    const hasRail = this._routes.some((route) => route.route_type === "2");
    const toggles = [
      "show_header",
      "show_city",
      "show_stop_code",
      "show_destination",
      "show_operator",
      "show_mode_icon",
      "show_realtime_tag",
      "show_platform",
      "show_delay",
      "show_clock",
    ];

    return [
      { name: "title", selector: { text: {} } },
      {
        name: "",
        type: "grid",
        schema: [
          {
            name: "max_arrivals",
            selector: { number: { min: 1, max: 20, step: 1, mode: "box" } },
          },
          {
            name: "max_lines",
            selector: { number: { min: 0, max: 20, step: 1, mode: "box" } },
          },
        ],
      },
      // Only meaningful once there is a chosen order to follow.
      ...(this._lines.length
        ? [
            {
              name: "order",
              selector: {
                select: {
                  mode: "dropdown",
                  options: [
                    { value: "time", label: this._t("editorOrderTime") },
                    { value: "lines", label: this._t("editorOrderLines") },
                  ],
                },
              },
            },
          ]
        : []),
      {
        name: "",
        type: "expandable",
        title: this._t("editorDisplay"),
        icon: "mdi:eye-settings-outline",
        schema: [
          {
            name: "",
            type: "grid",
            schema: toggles.map((name) => ({ name, selector: { boolean: {} } })),
          },
          { name: "show_map", selector: { boolean: {} } },
        ],
      },
      ...(hasRail ? [{ name: "rail_destination", selector: { text: {} } }] : []),
    ];
  }

  _computeLabel = (schema) => {
    const labels = {
      title: this._t("editorTitle"),
      max_arrivals: this._t("editorMaxArrivals"),
      max_lines: this._t("editorMaxLines"),
      order: this._t("editorOrder"),
      show_header: this._t("editorShowHeader"),
      show_city: this._t("editorShowCity"),
      show_stop_code: this._t("editorShowStopCode"),
      show_destination: this._t("editorShowDestination"),
      show_operator: this._t("editorShowOperator"),
      show_mode_icon: this._t("editorShowModeIcon"),
      show_realtime_tag: this._t("editorShowRealtimeTag"),
      show_platform: this._t("editorShowPlatform"),
      show_delay: this._t("editorShowDelay"),
      show_clock: this._t("editorShowClock"),
      show_map: this._t("editorShowMap"),
      rail_destination: this._t("mode_2"),
    };
    return labels[schema.name] ?? schema.name;
  };

  _computeHelper = (schema) => {
    const helpers = {
      max_lines: this._t("editorMaxLinesHelp"),
      show_map: this._t("editorShowMapHelp"),
    };
    return helpers[schema.name];
  };

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
              ${this._renderLines()}
              <ha-form
                .hass=${this.hass}
                .data=${{ ...DEFAULTS, ...this._config }}
                .schema=${this._schema}
                .computeLabel=${this._computeLabel}
                .computeHelper=${this._computeHelper}
                @value-changed=${this._onFormChange}
              ></ha-form>
            `
          : nothing}
      </div>
    `;
  }

  _renderSelected() {
    const stop = this._stop || { code: this._config.stop_code };
    return html`
      <div class="selected">
        <ha-icon icon="mdi:bus-stop"></ha-icon>
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
                <ha-icon icon="mdi:close"></ha-icon>
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
            <ha-icon icon="mdi:arrow-up"></ha-icon>
          </button>
          <button
            class="tool"
            ?disabled=${index === total - 1}
            title=${this._t("editorMoveDown")}
            aria-label=${this._t("editorMoveDown")}
            @click=${() => this._move(index, 1)}
          >
            <ha-icon icon="mdi:arrow-down"></ha-icon>
          </button>
          <button
            class="tool"
            title=${this._t("editorRemove")}
            aria-label=${this._t("editorRemove")}
            @click=${() => this._removeLine(index)}
          >
            <ha-icon icon="mdi:close"></ha-icon>
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
