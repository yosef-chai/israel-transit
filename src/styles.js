import { css, unsafeCSS } from "lit";

import { MODE_COLORS, UNKNOWN_COLORS } from "./util.js";

// Built on Home Assistant's design tokens (--ha-space-*, --ha-font-*,
// --ha-border-radius-*) and its semantic and theme colours, each with a
// fallback for releases or themes that do not set it, so the card follows the
// active theme and dark mode. Logical properties keep it right in RTL.

// Badges carry white text, so they take the darker colour of each pair in
// both themes (at least 4.5:1); see util.js.
const MODE_VARS = unsafeCSS(
  Object.entries(MODE_COLORS)
    .map(([type, [light]]) => `--it-mode-${type}: ${light};`)
    .join("\n    ") + `\n    --it-mode-unknown: ${UNKNOWN_COLORS[0]};`,
);

export const sharedStyles = css`
  :host {
    ${MODE_VARS}
    display: block;
    /* Coloured text takes Home Assistant's "on" colours, which are made for
       text: 7:1 on the light card and 5.7:1 on the dark one. --warning-color
       and --success-color are fills, at 2:1 and 3.3:1 on white. */
    --it-text-warning: var(--ha-color-on-warning-normal, #c94e00);
    --it-text-success: var(--ha-color-on-success-normal, #00883c);
  }

  .icon {
    flex: 0 0 auto;
    display: block;
  }

  /* Points the same way as the text in both directions. */
  :host(:dir(rtl)) .flip {
    transform: scaleX(-1);
  }

  .badge {
    flex: 0 0 auto;
    box-sizing: border-box;
    min-width: 44px;
    height: 28px;
    padding-inline: var(--ha-space-2, 8px);
    border-radius: var(--ha-border-radius-pill, 9999px);
    background: var(--it-badge-color, var(--it-mode-unknown));
    color: #fff;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-bold, 700);
    line-height: 28px;
    text-align: center;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
    /* Line numbers stay left-to-right even inside an RTL layout. */
    direction: ltr;
    unicode-bidi: isolate;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    gap: var(--ha-space-1, 4px);
    white-space: nowrap;
  }

  .tag.timetable {
    color: var(--secondary-text-color);
  }

  .ltr {
    direction: ltr;
    unicode-bidi: isolate;
    font-variant-numeric: tabular-nums;
  }

  /* -- states: loading, empty, error, stale -- */

  .skeleton {
    display: flex;
    align-items: center;
    gap: var(--ha-space-4, 16px);
    min-height: 48px;
    padding: var(--ha-space-3, 12px) var(--ha-space-4, 16px);
    box-sizing: border-box;
    animation: fade-in 300ms ease-in;
  }

  .bone {
    border-radius: var(--ha-border-radius-sm, 4px);
    background: var(--ha-color-fill-neutral-quiet-resting, rgba(127, 127, 127, 0.14));
  }

  .bone.pill {
    width: 44px;
    height: 28px;
    border-radius: var(--ha-border-radius-pill, 9999px);
  }

  .bone.text {
    flex: 1 1 auto;
    height: 12px;
  }

  .bone.eta {
    width: 32px;
    height: 20px;
  }

  @keyframes fade-in {
    from {
      opacity: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton {
      animation: none;
    }
  }

  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--ha-space-2, 8px);
    max-width: 500px;
    margin-inline: auto;
    padding: var(--ha-space-6, 24px) var(--ha-space-4, 16px);
    text-align: center;
    color: var(--secondary-text-color);
  }

  .empty .icon {
    color: var(--secondary-text-color);
    opacity: 0.8;
  }

  .empty-title {
    margin: 0;
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
  }

  .empty-text {
    margin: 0;
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }

  /* Home Assistant's alert, narrow variant: the colour of its kind at 12%
     behind it, an icon that says the same thing as the colour. */
  .alert {
    --it-alert: var(--info-color, #039be5);
    display: flex;
    align-items: flex-start;
    gap: var(--ha-space-2, 8px);
    padding: var(--ha-space-2, 8px) var(--ha-space-3, 12px);
    border-radius: var(--ha-border-radius-sm, 4px);
    background: rgba(127, 127, 127, 0.12);
    background: color-mix(in srgb, var(--it-alert) 12%, transparent);
    color: var(--primary-text-color);
    font-size: var(--ha-font-size-s, 12px);
    line-height: var(--ha-line-height-normal, 1.6);
  }

  .alert .icon {
    color: var(--it-alert);
  }

  .alert.error {
    --it-alert: var(--error-color, #db4437);
  }

  .alert.warning {
    --it-alert: var(--warning-color, #ffa600);
  }

  .alert.warning .icon {
    color: var(--it-text-warning);
  }

  .alert.info {
    --it-alert: var(--info-color, #039be5);
  }
`;

export const cardStyles = css`
  /* The sections view gives the card a fixed height when it is resized;
     filling it lets the list scroll inside rather than spill out. In the
     masonry view the height stays the content's. */
  :host {
    height: 100%;
  }

  ha-card {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    container-type: inline-size;
  }

  .header {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: var(--ha-space-3, 12px);
    width: 100%;
    min-height: 48px;
    padding: var(--ha-space-4, 16px) var(--ha-space-4, 16px) var(--ha-space-2, 8px);
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    box-sizing: border-box;
  }

  .header:focus-visible,
  .row:focus-visible {
    outline: 2px solid var(--ha-color-focus, var(--primary-color));
    outline-offset: -2px;
    border-radius: var(--ha-card-border-radius, 12px);
  }

  .titles {
    flex: 1 1 auto;
    min-width: 0;
  }

  .stop-name {
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .stop-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--ha-space-2, 8px);
    margin-block-start: var(--ha-space-1, 4px);
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .code {
    padding: 0 var(--ha-space-2, 8px);
    border-radius: var(--ha-border-radius-pill, 9999px);
    background: var(--ha-color-fill-neutral-quiet-resting, rgba(127, 127, 127, 0.14));
    line-height: 20px;
  }

  .header .info {
    color: var(--secondary-text-color);
  }

  .notice {
    flex: 0 0 auto;
    padding: 0 var(--ha-space-4, 16px) var(--ha-space-2, 8px);
  }

  .rows {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    /* Lets the list shrink to the height the grid gives the card, and
       scroll inside it, instead of being clipped. */
    min-height: 0;
    overflow-y: auto;
    /* Home Assistant's own scrollbar (.ha-scrollbar). */
    scrollbar-color: var(--scrollbar-thumb-color, rgba(127, 127, 127, 0.5)) transparent;
    scrollbar-width: thin;
    padding-block-end: var(--ha-space-2, 8px);
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--ha-space-3, 12px);
    width: 100%;
    min-height: 56px;
    padding: var(--ha-space-2, 8px) var(--ha-space-4, 16px);
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    box-sizing: border-box;
    transition: background-color var(--ha-animation-duration-fast, 150ms);
  }

  .row + .row {
    box-shadow: inset 0 1px 0 var(--divider-color, rgba(127, 127, 127, 0.2));
  }

  .row:hover {
    background: var(--ha-color-fill-neutral-quiet-hover, rgba(127, 127, 127, 0.08));
  }

  .row:active {
    background: var(--ha-color-fill-neutral-quiet-active, rgba(127, 127, 127, 0.14));
  }

  .mode {
    color: var(--secondary-text-color);
  }

  .row-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .destination {
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sub {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0 var(--ha-space-1, 4px);
    margin-block-start: var(--ha-space-1, 4px);
    font-size: var(--ha-font-size-s, 12px);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--secondary-text-color);
  }

  .eta {
    flex: 0 0 auto;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    min-width: 48px;
    text-align: end;
  }

  .eta-main {
    display: flex;
    align-items: baseline;
    gap: var(--ha-space-1, 4px);
  }

  .eta-value {
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }

  .eta-unit {
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .eta-now .eta-value {
    font-size: var(--ha-font-size-l, 16px);
    color: var(--it-text-success);
  }

  .eta-clock {
    font-size: var(--ha-font-size-l, 16px);
  }

  .eta-extra {
    display: flex;
    align-items: center;
    gap: var(--ha-space-1, 4px);
    margin-block-start: 2px;
    font-size: var(--ha-font-size-xs, 10px);
    color: var(--secondary-text-color);
  }

  .live {
    color: var(--it-text-success);
  }

  .delay {
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--it-text-warning);
  }

  .delay.early,
  .delay.on-time {
    color: var(--it-text-success);
  }

  /* נסיעה שבוטלה נשארת בלוח, מחוקה, כדי שלא יחכו לה. */
  .row.cancelled .destination,
  .row.cancelled .eta-main {
    text-decoration: line-through;
    color: var(--secondary-text-color);
  }

  .cancelled-tag {
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--ha-color-on-danger-normal, #b30532);
  }

  .chevron {
    color: var(--secondary-text-color);
    margin-inline-start: calc(-1 * var(--ha-space-1, 4px));
  }

  /* Times that stopped updating: still the last real answer, so they stay,
     in the secondary text colour until a fresh one arrives. Not faded with
     opacity: that took them below a readable contrast. */
  .rows.stale .eta-value,
  .rows.stale .live,
  .rows.stale .delay {
    color: var(--secondary-text-color);
  }

  /* Genuinely narrow dashboard columns: drop to the essentials. A
     full-width card on a small phone is ~327px, and should keep everything. */
  @container (max-width: 290px) {
    .header,
    .row {
      padding-inline: var(--ha-space-3, 12px);
    }
    .row {
      gap: var(--ha-space-2, 8px);
    }
    .sub .operator,
    .sub .operator + .sep,
    .mode,
    .chevron {
      display: none;
    }
    .eta-value {
      font-size: var(--ha-font-size-l, 16px);
    }
    .stop-name {
      font-size: var(--ha-font-size-l, 16px);
    }
  }

  /* Six columns of a phone-width section: the line, where it goes, when. */
  @container (max-width: 220px) {
    .header,
    .row {
      padding-inline: var(--ha-space-2, 8px);
    }
    .sub {
      display: none;
    }
    /* One line for the name and one for the code, so the header keeps the
       height the grid was sized for. */
    .stop-name {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .stop-meta span:not(.code) {
      display: none;
    }
    .badge {
      min-width: 36px;
      padding-inline: var(--ha-space-1, 4px);
    }
    .eta {
      min-width: 0;
    }
  }
`;
