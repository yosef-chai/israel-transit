import { LitElement, css, html, nothing } from "lit";

import { ICONS, icon, iconMarkup } from "./icons.js";
import { createColorResolver, distanceM, toLngLat } from "./map-geometry.js";
import { VEHICLE_PICKED, reducedMotion } from "./util.js";

// MapLibre is served beside the card (esbuild.config.mjs copies it into a
// folder named after its version) and imported the first time a map opens, so
// a dashboard that never opens one never downloads it. Resolving against this
// module's own URL keeps it working behind a reverse proxy, under a path
// prefix and inside the Companion apps.
const VENDOR = new URL(`./vendor/${__MAPLIBRE_DIR__}/`, import.meta.url);

// Public-domain styles for the OpenStreetMap Shortbread tiles VersaTiles
// serves without a key. Gray keeps the base map quiet so the route stands out;
// the dark one follows Home Assistant's dark theme. Both carry Hebrew glyphs.
const STYLES = {
  light: "https://tiles.versatiles.org/assets/styles/gray/style.json",
  dark: "https://tiles.versatiles.org/assets/styles/gray-dark/style.json",
};
const FONT = ["noto_sans_regular"];
const FONT_BOLD = ["noto_sans_bold"];

const MAX_ZOOM = 16;
const ARROW = "it-arrow";
// How long a lost WebGL context gets to come back before the map gives up.
// iOS drops it when the Companion app goes to the background and returns it a
// moment later; Home Assistant's own map waits the same 2 s.
const CONTEXT_RESTORE_MS = 2000;
// Glide the vehicle between two sightings, unless it jumped: a bus gliding
// half a kilometre across buildings after a tab wakes up looks wrong.
const GLIDE_MS = 250;
const GLIDE_MAX_M = 500;

let loading = null;

/** MapLibre and its stylesheet together, so a map is never drawn unstyled. */
const loadMaplibre = () => {
  loading ??= Promise.all([
    import(/* @vite-ignore */ new URL("maplibre-gl.mjs", VENDOR).href),
    fetch(new URL("maplibre-gl.css", VENDOR)).then((response) => {
      if (!response.ok) throw new Error(`maplibre-gl.css: HTTP ${response.status}`);
      return response.text();
    }),
  ]).then(([maplibre, text]) => {
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(text);
    return { maplibre, sheet };
  });
  // A failed load (offline, or the card updated under an open tab) can be
  // tried again by the next map instead of failing for good.
  loading.catch(() => {
    loading = null;
  });
  return loading;
};

let webgl2 = null;
const supportsWebGL2 = () => {
  if (webgl2 === null) {
    try {
      webgl2 = Boolean(document.createElement("canvas").getContext("webgl2"));
    } catch {
      webgl2 = false;
    }
  }
  return webgl2;
};

// Theme colours can be written in forms MapLibre does not parse (color-mix(),
// oklch(), light-dark()); the browser resolves them to rgb() on a 1×1 canvas.
let probe = null;
const resolveColor = createColorResolver((value) => {
  probe ??= document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  if (!probe || !CSS.supports("color", value)) return null;
  probe.clearRect(0, 0, 1, 1);
  probe.fillStyle = "#000";
  probe.fillStyle = value;
  probe.fillRect(0, 0, 1, 1);
  const [r, g, b, a] = probe.getImageData(0, 0, 1, 1).data;
  return a === 255 ? `rgb(${r}, ${g}, ${b})` : `rgba(${r}, ${g}, ${b}, ${(a / 255).toFixed(3)})`;
});

/** A small chevron, white so that icon-color can paint it any colour (SDF). */
const arrowImage = () => {
  const size = 32;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 5;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(11, 8);
  ctx.lineTo(21, 16);
  ctx.lineTo(11, 24);
  ctx.stroke();
  return ctx.getImageData(0, 0, size, size);
};

const lineFeature = (points) => ({
  type: "Feature",
  properties: {},
  geometry: { type: "LineString", coordinates: (points || []).map(toLngLat) },
});

const collection = (features) => ({ type: "FeatureCollection", features });

/**
 * The route map of a line: the route, its stops, the rider's stop and the
 * vehicle, on a MapLibre vector map of its own.
 *
 * The dialog decides what to draw (`view`); this element only draws it and
 * reports when it cannot.
 */
export class IsraelTransitMap extends LitElement {
  static properties = {
    view: { attribute: false },
    strings: { attribute: false },
    _status: { state: true },
    _moved: { state: true },
  };

  static styles = css`
    :host {
      position: relative;
      display: block;
      overflow: hidden;
      border-radius: var(--ha-border-radius-lg, 12px);
      background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.12));
      /* A drag on the map moves the map, never the sheet around it. */
      touch-action: none;
    }

    #map {
      position: absolute;
      inset: 0;
    }

    .status {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: var(--ha-space-2, 8px);
      padding: var(--ha-space-4, 16px);
      text-align: center;
      font-size: var(--ha-font-size-m, 14px);
      color: var(--secondary-text-color);
    }

    .status button {
      min-height: 36px;
      padding-inline: var(--ha-space-4, 16px);
      border: var(--ha-border-width-sm, 1px) solid var(--divider-color);
      border-radius: var(--ha-border-radius-pill, 9999px);
      background: var(--card-background-color);
      color: var(--primary-text-color);
      font: inherit;
      cursor: pointer;
    }

    .recenter {
      position: absolute;
      inset-block-end: var(--ha-space-3, 12px);
      inset-inline-end: var(--ha-space-3, 12px);
      display: inline-flex;
      align-items: center;
      gap: var(--ha-space-2, 8px);
      min-height: 40px;
      padding-inline: var(--ha-space-3, 12px) var(--ha-space-4, 16px);
      border: none;
      border-radius: var(--ha-border-radius-pill, 9999px);
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      box-shadow: var(--ha-box-shadow-m, 0 3px 6px -1px rgba(0, 0, 0, 0.1), 0 8px 16px -2px rgba(0, 0, 0, 0.15));
      font: inherit;
      font-size: var(--ha-font-size-s, 12px);
      font-weight: var(--ha-font-weight-medium, 500);
      cursor: pointer;
    }

    button:focus-visible {
      outline: 2px solid var(--ha-color-focus, var(--primary-color));
      outline-offset: 2px;
    }

    /* -- markers: MapLibre moves these with transform, so nothing on the
       marker element itself may transition, only what is inside it. -- */

    .vehicle {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 34px;
      height: 34px;
    }

    .vehicle .dot {
      position: relative;
      z-index: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      border: 3px solid var(--it-casing);
      border-radius: 50%;
      box-sizing: border-box;
      background: var(--it-color);
      color: #fff;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
    }

    .vehicle .line {
      position: absolute;
      z-index: 2;
      inset-block-start: -10px;
      inset-inline-start: 22px;
      padding: 1px 6px;
      border-radius: var(--ha-border-radius-pill, 9999px);
      background: var(--it-casing);
      color: var(--it-text);
      font-size: 11px;
      font-weight: 700;
      line-height: 16px;
      white-space: nowrap;
      direction: ltr;
      unicode-bidi: isolate;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    }

    .vehicle .pulse {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background: var(--it-color);
      opacity: 0.35;
      animation: pulse 2s ease-out infinite;
    }

    .vehicle[role="button"] {
      cursor: pointer;
    }

    .vehicle:focus-visible .dot {
      outline: 2px solid var(--ha-color-focus, var(--primary-color));
      outline-offset: 2px;
    }

    .vehicle.stale .dot {
      background: var(--it-stale);
      border-style: dashed;
    }

    .vehicle.stale .pulse {
      display: none;
    }

    @keyframes pulse {
      from {
        transform: scale(1);
        opacity: 0.4;
      }
      to {
        transform: scale(2.2);
        opacity: 0;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .vehicle .pulse {
        animation: none;
        display: none;
      }
    }

    /* MapLibre's own controls, in the card's colours rather than its white. */
    .maplibregl-ctrl-group,
    .maplibregl-ctrl-attrib {
      background: var(--card-background-color, #fff) !important;
      color: var(--primary-text-color);
    }

    .maplibregl-ctrl-group {
      border-radius: var(--ha-border-radius-md, 8px) !important;
      box-shadow: var(--ha-box-shadow-s, 0 1px 2px 0 rgba(0, 0, 0, 0.08), 0 1px 3px 0 rgba(0, 0, 0, 0.12)) !important;
    }

    .maplibregl-ctrl-group button + button {
      border-top-color: var(--divider-color, rgba(127, 127, 127, 0.2)) !important;
    }

    .maplibregl-ctrl-attrib a {
      color: var(--secondary-text-color);
    }

    :host([dark]) .maplibregl-ctrl-icon,
    :host([dark]) .maplibregl-ctrl-attrib-button {
      filter: invert(1);
    }

    .mine {
      display: flex;
      color: var(--it-mine);
      filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.45));
    }
  `;

  constructor() {
    super();
    this.view = null;
    this.strings = {};
    this._status = "loading";
    this._moved = false;
  }

  connectedCallback() {
    super.connectedCallback();
    if (this.hasUpdated) this._start();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._stop();
  }

  firstUpdated() {
    this._start();
  }

  updated(changed) {
    if (changed.has("view")) {
      this.toggleAttribute("dark", Boolean(this.view?.dark));
      this._apply(changed.get("view"));
    }
  }

  /** Pan to a point, as when the rider picks a stop from the list. */
  focusOn(point) {
    if (!this._map || !point) return;
    this._moved = true;
    this._map.easeTo({
      center: toLngLat(point),
      zoom: Math.max(this._map.getZoom(), 15),
      duration: reducedMotion() ? 0 : 350,
    });
  }

  // -- lifecycle -----------------------------------------------------------

  async _start() {
    if (this._map || this._starting) return;
    if (!supportsWebGL2()) {
      this._status = "unsupported";
      return;
    }
    this._status = "loading";
    const generation = (this._generation = (this._generation ?? 0) + 1);
    this._starting = true;
    let loaded;
    try {
      loaded = await loadMaplibre();
    } catch {
      this._starting = false;
      if (generation === this._generation) this._status = "vendor";
      return;
    }
    this._starting = false;
    // Closed while MapLibre was on its way.
    if (generation !== this._generation || !this.isConnected) return;
    const { maplibre, sheet } = loaded;
    this._maplibre = maplibre;
    if (!this.shadowRoot.adoptedStyleSheets.includes(sheet)) {
      this.shadowRoot.adoptedStyleSheets = [...this.shadowRoot.adoptedStyleSheets, sheet];
    }
    const container = this.renderRoot.querySelector("#map");
    const rtl = getComputedStyle(this).direction === "rtl";
    this._dark = Boolean(this.view?.dark);
    this._styleLoaded = false;

    let map;
    try {
      map = new maplibre.Map({
        container,
        style: STYLES[this._dark ? "dark" : "light"],
        // Later setStyle calls (the theme turning dark) reuse this, so the
        // route travels to the new style instead of vanishing with the old.
        transformStyle: (_previous, next) => this._withRoute(next),
        bounds: this.view?.bounds ?? undefined,
        fitBoundsOptions: this._fitOptions(),
        maxZoom: 19,
        attributionControl: { compact: true },
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
        renderWorldCopies: false,
        locale: this.strings.maplibre,
        fadeDuration: reducedMotion() ? 0 : 300,
      });
    } catch {
      this._status = "failed";
      return;
    }
    this._map = map;
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();
    map.addControl(
      new maplibre.NavigationControl({ showCompass: false }),
      rtl ? "top-left" : "top-right",
    );

    // The compact credits open on load and cover a third of a small map; once
    // it has drawn they fold away, one tap away on the (i) button.
    map.once("idle", () => {
      container
        .querySelector(".maplibregl-ctrl-attrib.maplibregl-compact-show")
        ?.classList.remove("maplibregl-compact-show");
    });
    map.on("styleimagemissing", (event) => {
      if (event.id === ARROW && !map.hasImage(ARROW)) {
        map.addImage(ARROW, arrowImage(), { sdf: true, pixelRatio: 2 });
      }
    });
    map.on("style.load", () => {
      this._styleLoaded = true;
      this._status = "ready";
      // Updates that arrived while a new style was loading were held back.
      this._syncSources();
    });
    map.on("error", (event) => {
      // A single tile failing is normal (a timeout, a 404 at the edge of the
      // map); MapLibre tries again. Only a style that never arrived leaves
      // nothing to look at.
      if (event.tile || event.sourceId || this._styleLoaded) return;
      this._status = "unavailable";
    });
    // Anything the rider does to the view is theirs to keep: the next update
    // must not snap it back. Programmatic moves carry no originalEvent.
    const mark = (event) => {
      if (event.originalEvent) this._moved = true;
    };
    map.on("dragstart", mark);
    map.on("zoomstart", mark);

    map.on("webglcontextlost", () => {
      clearTimeout(this._contextTimer);
      this._contextTimer = setTimeout(() => (this._status = "failed"), CONTEXT_RESTORE_MS);
    });
    map.on("webglcontextrestored", () => {
      clearTimeout(this._contextTimer);
      if (this._status === "failed") this._status = "ready";
    });

    // A dialog opens with an animation, so the container may still be
    // growing; the map keeps up with it, and fits only once it has a size.
    this._resize = new ResizeObserver(() => {
      map.resize();
      if (!this._fitted && container.clientWidth && container.clientHeight) this._fit(false);
    });
    this._resize.observe(container);

    this._updateMarkers();
  }

  _stop() {
    this._generation = (this._generation ?? 0) + 1;
    this._starting = false;
    this._vehicleMarkers?.forEach((marker) => cancelAnimationFrame(marker.glide));
    clearTimeout(this._contextTimer);
    this._resize?.disconnect();
    this._resize = undefined;
    this._vehicleMarkers = undefined;
    this._mineMarker = undefined;
    try {
      this._map?.remove();
    } catch {
      // A map whose context is already gone can throw on the way out.
    }
    this._map = undefined;
    this._fitted = false;
  }

  _retry() {
    this._stop();
    this._start();
  }

  // -- what to draw --------------------------------------------------------

  /** Colours for the current theme, resolved for MapLibre. */
  get _colors() {
    const view = this.view || {};
    const dark = Boolean(view.dark);
    return {
      route: resolveColor(view.color, dark ? "#66bb6a" : "#2f7d4f"),
      casing: dark ? "#1c1c1c" : "#ffffff",
      halo: dark ? "rgba(28, 28, 28, 0.9)" : "rgba(255, 255, 255, 0.92)",
      text: dark ? "#e1e1e1" : "#212121",
      stopFill: dark ? "#2a2a2a" : "#ffffff",
      mine: resolveColor(view.mineColor, dark ? "#ffb300" : "#9c6200"),
    };
  }

  _sources() {
    const view = this.view || {};
    const stops = (view.stops || []).map((stop) => ({
      type: "Feature",
      properties: { name: stop.name ?? "", done: Boolean(stop.done) },
      geometry: { type: "Point", coordinates: toLngLat(stop.point) },
    }));
    const mine = view.mine
      ? [
          {
            type: "Feature",
            properties: { name: view.mine.name ?? "" },
            geometry: { type: "Point", coordinates: toLngLat(view.mine.point) },
          },
        ]
      : [];
    return {
      "it-line": lineFeature(view.line),
      "it-done": lineFeature(view.done),
      "it-ahead": lineFeature(view.ahead ?? view.line),
      "it-stops": collection(stops),
      "it-mine": collection(mine),
    };
  }

  /**
   * The route's layers. Lines go under the base map's labels, so street names
   * stay readable over them; stops and their names go on top of everything.
   */
  _layers() {
    const c = this._colors;
    const dashed = Boolean(this.view?.dashed);
    const width = (low, high) => ["interpolate", ["linear"], ["zoom"], 10, low, 16, high];
    const under = [
      {
        id: "it-casing",
        type: "line",
        source: "it-line",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": c.casing, "line-width": width(6, 11) },
      },
      {
        id: "it-done",
        type: "line",
        source: "it-done",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": c.route, "line-width": width(3, 6), "line-opacity": 0.35 },
      },
      {
        id: "it-ahead",
        type: "line",
        source: "it-ahead",
        layout: { "line-cap": dashed ? "butt" : "round", "line-join": "round" },
        paint: {
          "line-color": c.route,
          "line-width": width(3, 6),
          // Without the real street path the line is a guess between stops,
          // and should look like one.
          ...(dashed ? { "line-dasharray": [2, 1.5] } : {}),
        },
      },
      {
        id: "it-arrows",
        type: "symbol",
        source: "it-ahead",
        minzoom: 13,
        layout: {
          "symbol-placement": "line",
          "symbol-spacing": 90,
          "icon-image": ARROW,
          "icon-size": ["interpolate", ["linear"], ["zoom"], 13, 0.45, 17, 0.7],
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
          "icon-rotation-alignment": "map",
        },
        paint: { "icon-color": c.casing, "icon-opacity": 0.95 },
      },
    ];
    const over = [
      {
        id: "it-stops",
        type: "circle",
        source: "it-stops",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 2.5, 16, 5.5],
          "circle-color": c.stopFill,
          "circle-stroke-color": c.route,
          "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10, 1.5, 16, 2.5],
          "circle-opacity": ["case", ["get", "done"], 0.55, 1],
          "circle-stroke-opacity": ["case", ["get", "done"], 0.45, 1],
        },
      },
      {
        id: "it-stop-labels",
        type: "symbol",
        source: "it-stops",
        minzoom: 15,
        layout: {
          "text-field": ["get", "name"],
          "text-font": FONT,
          "text-size": 12,
          "text-offset": [0, 1],
          "text-anchor": "top",
          "text-max-width": 9,
          "symbol-sort-key": 2,
        },
        paint: {
          "text-color": c.text,
          "text-halo-color": c.halo,
          "text-halo-width": 1.6,
          "text-opacity": ["case", ["get", "done"], 0.6, 1],
        },
      },
      {
        // The rider's stop is named at every zoom and never gives way to
        // anything else, however crowded the street is.
        id: "it-mine-label",
        type: "symbol",
        source: "it-mine",
        layout: {
          "text-field": ["get", "name"],
          "text-font": FONT_BOLD,
          "text-size": 13,
          "text-offset": [0, 0.9],
          "text-anchor": "top",
          "text-max-width": 9,
          "text-allow-overlap": true,
          "text-ignore-placement": true,
          "symbol-sort-key": 0,
        },
        paint: {
          "text-color": c.text,
          "text-halo-color": c.halo,
          "text-halo-width": 2,
        },
      },
    ];
    return { under, over };
  }

  /** A base style with the route spliced in; also used on a theme change. */
  _withRoute(style) {
    const sources = Object.fromEntries(
      Object.entries(this._sources()).map(([id, data]) => [id, { type: "geojson", data }]),
    );
    const { under, over } = this._layers();
    const layers = [...(style.layers || [])];
    const firstLabel = layers.findIndex((layer) => layer.type === "symbol");
    const at = firstLabel < 0 ? layers.length : firstLabel;
    layers.splice(at, 0, ...under);
    layers.push(...over);
    return { ...style, sources: { ...style.sources, ...sources }, layers };
  }

  _apply(previous) {
    const map = this._map;
    if (!map) return;
    const view = this.view || {};
    const dark = Boolean(view.dark);
    if (dark !== this._dark) {
      this._dark = dark;
      // transformStyle carries the route over to the new base map.
      this._styleLoaded = false;
      map.setStyle(STYLES[dark ? "dark" : "light"]);
    } else if (this._styleLoaded) {
      this._syncSources();
      if (previous?.color !== view.color || previous?.dashed !== view.dashed) {
        this._repaint();
      }
    }
    this._updateMarkers();
    if (view.fitKey !== previous?.fitKey) {
      // A different vehicle or line is a different question; the old view
      // belongs to the old one.
      if (view.subject !== previous?.subject) this._moved = false;
      if (!this._moved) this._fit(Boolean(this._fitted));
    }
  }

  _syncSources() {
    const map = this._map;
    if (!map) return;
    for (const [id, data] of Object.entries(this._sources())) {
      map.getSource(id)?.setData(data);
    }
  }

  _repaint() {
    const map = this._map;
    const { under, over } = this._layers();
    for (const layer of [...under, ...over]) {
      if (!map.getLayer(layer.id)) continue;
      for (const [name, value] of Object.entries(layer.paint || {})) {
        map.setPaintProperty(layer.id, name, value);
      }
    }
    if (map.getLayer("it-ahead")) {
      const dashed = Boolean(this.view?.dashed);
      map.setPaintProperty("it-ahead", "line-dasharray", dashed ? [2, 1.5] : undefined);
      map.setLayoutProperty("it-ahead", "line-cap", dashed ? "butt" : "round");
    }
  }

  _fitOptions() {
    return { padding: 48, maxZoom: MAX_ZOOM };
  }

  _fit(animate) {
    const map = this._map;
    const bounds = this.view?.bounds;
    if (!map || !bounds) return;
    const container = map.getContainer();
    if (!container.clientWidth || !container.clientHeight) return;
    const single = bounds[0][0] === bounds[1][0] && bounds[0][1] === bounds[1][1];
    const options = {
      ...this._fitOptions(),
      duration: animate && !reducedMotion() ? 350 : 0,
    };
    if (single) {
      map.jumpTo({ center: bounds[0], zoom: MAX_ZOOM - 1 });
    } else {
      // Small containers can be smaller than the padding; MapLibre then
      // refuses to fit, and a fit with no padding still beats none.
      const fits = container.clientWidth > 120 && container.clientHeight > 120;
      map.fitBounds(bounds, fits ? options : { ...options, padding: 8 });
    }
    this._fitted = true;
  }

  recenter() {
    this._moved = false;
    this._fit(true);
  }

  // -- markers -------------------------------------------------------------

  _updateMarkers() {
    const map = this._map;
    const maplibre = this._maplibre;
    if (!map || !maplibre) return;
    const view = this.view || {};
    const c = this._colors;
    const vars = {
      "--it-color": c.route,
      "--it-casing": c.casing,
      "--it-text": c.text,
      "--it-mine": c.mine,
      "--it-stale": view.dark ? "#757575" : "#9e9e9e",
    };

    // The rider's stop: a pin, so it reads as "here" without its colour.
    if (view.mine) {
      if (!this._mineMarker) {
        const element = document.createElement("div");
        element.className = "mine";
        element.innerHTML = iconMarkup(ICONS.myStop, 30);
        this._mineMarker = new maplibre.Marker({ element, anchor: "bottom" })
          .setLngLat(toLngLat(view.mine.point))
          .addTo(map);
      }
      const element = this._mineMarker.getElement();
      Object.entries(vars).forEach(([name, value]) => element.style.setProperty(name, value));
      element.setAttribute("role", "img");
      element.setAttribute("aria-label", view.mine.label ?? view.mine.name ?? "");
      this._mineMarker.setLngLat(toLngLat(view.mine.point));
    } else {
      this._mineMarker?.remove();
      this._mineMarker = undefined;
    }

    // רכב אחד בפרטי הקו, כמה רכבים במבט על התחנה. כל אחד נשמר לפי המזהה שלו,
    // כדי שיגלוש למיקום החדש ולא ייווצר מחדש בכל רענון.
    const vehicles = view.vehicles ?? (view.vehicle ? [view.vehicle] : []);
    this._vehicleMarkers ??= new Map();
    const seen = new Set();
    vehicles.forEach((vehicle, index) => {
      const id = vehicle.id ?? String(index);
      seen.add(id);
      let marker = this._vehicleMarkers.get(id);
      if (!marker) {
        const element = document.createElement("div");
        element.className = "vehicle";
        element.innerHTML =
          `<span class="pulse"></span><span class="dot"></span><span class="line"></span>`;
        if (view.vehicles) {
          element.tabIndex = 0;
          const pick = () =>
            this.dispatchEvent(new CustomEvent(VEHICLE_PICKED, { detail: { id } }));
          element.addEventListener("click", pick);
          element.addEventListener("keydown", (ev) => ev.key === "Enter" && pick());
        }
        marker = new maplibre.Marker({ element }).setLngLat(toLngLat(vehicle.point)).addTo(map);
        this._vehicleMarkers.set(id, marker);
      }
      const element = marker.getElement();
      Object.entries(vars).forEach(([name, value]) => element.style.setProperty(name, value));
      if (vehicle.color) {
        element.style.setProperty("--it-color", resolveColor(vehicle.color, c.route));
      }
      element.classList.toggle("stale", Boolean(vehicle.stale));
      element.querySelector(".dot").innerHTML = iconMarkup(vehicle.icon, 16);
      element.querySelector(".line").textContent = vehicle.lineName ?? "";
      element.setAttribute("role", view.vehicles ? "button" : "img");
      element.setAttribute("aria-label", vehicle.label ?? "");
      this._glideTo(marker, vehicle.point);
    });
    for (const [id, marker] of this._vehicleMarkers) {
      if (seen.has(id)) continue;
      cancelAnimationFrame(marker.glide);
      marker.remove();
      this._vehicleMarkers.delete(id);
    }
  }

  _glideTo(marker, point) {
    cancelAnimationFrame(marker.glide);
    const { lng, lat } = marker.getLngLat();
    const from = [lat, lng];
    if (from[0] === point[0] && from[1] === point[1]) return;
    if (reducedMotion() || distanceM(from, point) > GLIDE_MAX_M) {
      marker.setLngLat(toLngLat(point));
      return;
    }
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / GLIDE_MS);
      const eased = 1 - (1 - t) ** 3;
      marker.setLngLat([
        from[1] + (point[1] - from[1]) * eased,
        from[0] + (point[0] - from[0]) * eased,
      ]);
      if (t < 1) marker.glide = requestAnimationFrame(step);
    };
    marker.glide = requestAnimationFrame(step);
  }

  // -- rendering -----------------------------------------------------------

  render() {
    const s = this.strings;
    const message = {
      unsupported: s.unsupported,
      unavailable: s.unavailable,
      failed: s.failed,
      vendor: s.vendor,
    }[this._status];
    return html`
      <div id="map" ?hidden=${Boolean(message)}></div>
      ${message
        ? html`<div class="status" role="status">
            ${icon(ICONS.noPosition, { size: 28 })}
            <span>${message}</span>
            ${this._status === "unsupported"
              ? nothing
              : html`<button @click=${this._status === "vendor" ? () => location.reload() : this._retry}>
                  ${this._status === "vendor" ? s.reload : s.retry}
                </button>`}
          </div>`
        : nothing}
      ${this._moved && !message && this.view?.bounds
        ? html`<button class="recenter" @click=${this.recenter}>
            ${icon(ICONS.recenter, { size: 18 })}<span>${s.recenter}</span>
          </button>`
        : nothing}
    `;
  }
}
