import { IsraelTransitCard } from "./card.js";
import { IsraelTransitCardEditor } from "./editor.js";
import { IsraelTransitRouteDialog, IsraelTransitStopDialog } from "./dialogs.js";
import { localize } from "./localize.js";

const define = (tag, klass) => {
  if (!customElements.get(tag)) customElements.define(tag, klass);
};

define("israel-transit-card", IsraelTransitCard);
define("israel-transit-card-editor", IsraelTransitCardEditor);
define("israel-transit-stop-dialog", IsraelTransitStopDialog);
define("israel-transit-route-dialog", IsraelTransitRouteDialog);

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
  });
}

// __CARD_VERSION__ is the integration's manifest version, set at build time
// (esbuild.config.mjs), so the banner can never fall behind the release.
console.info(
  `%c ISRAEL-TRANSIT-CARD %c v${__CARD_VERSION__} `,
  "background:#2f7d4f;color:#fff;border-radius:3px 0 0 3px;padding:2px 4px",
  "background:#1e6fbf;color:#fff;border-radius:0 3px 3px 0;padding:2px 4px",
);
