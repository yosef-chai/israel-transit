import { IsraelTransitCard } from "./card.js";
import { IsraelTransitDialog } from "./dialog.js";
import {
  IsraelTransitOverviewDialog,
  IsraelTransitRouteDialog,
  IsraelTransitStopDialog,
} from "./dialogs.js";
import { IsraelTransitCardEditor } from "./editor.js";
import { localize } from "./localize.js";
import { IsraelTransitMap } from "./map.js";
import { DOMAIN } from "./util.js";

const define = (tag, klass) => {
  if (!customElements.get(tag)) customElements.define(tag, klass);
};

define("israel-transit-card", IsraelTransitCard);
define("israel-transit-card-editor", IsraelTransitCardEditor);
define("israel-transit-stop-dialog", IsraelTransitStopDialog);
define("israel-transit-route-dialog", IsraelTransitRouteDialog);
define("israel-transit-overview-dialog", IsraelTransitOverviewDialog);
define("israel-transit-dialog", IsraelTransitDialog);
define("israel-transit-map", IsraelTransitMap);

// The card picker reads this. Labels follow the browser language, since the
// picker renders before any hass object reaches the card.
const lang = { locale: { language: navigator.language || "he" } };

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "israel-transit-card")) {
  window.customCards.push({
    type: "israel-transit-card",
    name: localize(lang, "name"),
    description: localize(lang, "description"),
    preview: true,
    documentationURL: "https://github.com/yosef-chai/israel-transit",
    // Home Assistant 2026.6+ offers the card in the picker for an entity it
    // fits. Only this integration's stop entities qualify; anything else
    // returns null, so the picker is not crowded for everyone else.
    getEntitySuggestion: (hass, entityId) => {
      if (hass?.entities?.[entityId]?.platform !== DOMAIN) return null;
      const stopCode = hass.states?.[entityId]?.attributes?.stop_code;
      if (!stopCode) return null;
      return { config: { type: "custom:israel-transit-card", stop_code: Number(stopCode) } };
    },
  });
}

// __CARD_VERSION__ is the integration's manifest version, set at build time
// (esbuild.config.mjs), so the banner can never fall behind the release.
console.info(
  `%c ISRAEL-TRANSIT-CARD %c v${__CARD_VERSION__} `,
  "background:#2f7d4f;color:#fff;border-radius:3px 0 0 3px;padding:2px 4px",
  "background:#1e6fbf;color:#fff;border-radius:0 3px 3px 0;padding:2px 4px",
);
