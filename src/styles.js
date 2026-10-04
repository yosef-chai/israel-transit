import { css, unsafeCSS } from "lit";

import { MODE_HEX, UNKNOWN_HEX } from "./util.js";

// Everything here is built on Home Assistant's own design tokens so the card
// follows the active theme, and on logical properties so it mirrors correctly
// when Home Assistant switches the document to RTL for Hebrew.

// Derived from the same table the map paints with, so a colour can never be
// right in one place and stale in the other.
export const MODE_COLORS = unsafeCSS(
  Object.entries(MODE_HEX)
    .map(([type, hex]) => `--it-mode-${type}: ${hex};`)
    .join("\n    ") + `\n    --it-mode-unknown: var(--primary-color, ${UNKNOWN_HEX});`,
);

export const sharedStyles = css`
  :host {
    ${MODE_COLORS}
    --it-gap: 12px;
    --it-radius: 12px;
    display: block;
  }

  .badge {
    flex: 0 0 auto;
    min-width: 44px;
    padding: 4px 8px;
    border-radius: 8px;
    background: var(--it-badge-color, var(--it-mode-unknown));
    color: #fff;
    font-weight: 700;
    font-size: 1rem;
    line-height: 1.25;
    text-align: center;
    font-variant-numeric: tabular-nums;
    /* Line numbers stay left-to-right even inside an RTL layout. */
    direction: ltr;
    unicode-bidi: isolate;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    line-height: 1.3;
    white-space: nowrap;
  }

  .tag.timetable {
    color: var(--secondary-text-color);
  }


  .muted {
    color: var(--secondary-text-color);
  }

  .empty {
    padding: 24px 16px;
    text-align: center;
    color: var(--secondary-text-color);
  }

  .error {
    padding: 12px 16px;
    color: var(--error-color, #db4437);
  }
`;

export const cardStyles = css`
  ha-card {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    container-type: inline-size;
  }

  .header {
    display: flex;
    align-items: flex-start;
    gap: var(--it-gap);
    padding: 16px 16px 12px;
    cursor: pointer;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    width: 100%;
  }

  .header:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }

  .titles {
    flex: 1 1 auto;
    min-width: 0;
  }

  .stop-name {
    font-size: 1.25rem;
    font-weight: 500;
    line-height: 1.3;
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .stop-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-block-start: 2px;
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
  }

  .code {
    padding: 1px 6px;
    border-radius: 6px;
    background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.16));
    font-variant-numeric: tabular-nums;
    direction: ltr;
    unicode-bidi: isolate;
  }

  /* Over a board that is still shown: the times are real, just not fresh. */
  .stale {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    font-size: 0.75rem;
    color: var(--warning-color, #ffa600);
    --mdc-icon-size: 16px;
  }

  .rows {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    overflow-y: auto;
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--it-gap);
    padding: 10px 16px;
    border: none;
    border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    width: 100%;
    cursor: pointer;
  }

  .row:hover {
    background: var(--ha-color-surface-lower, rgba(127, 127, 127, 0.08));
  }

  .row:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }

  .row-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .destination {
    font-size: 0.9375rem;
    color: var(--primary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sub {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 2px 6px;
    margin-block-start: 2px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }

  .sep {
    color: var(--secondary-text-color);
  }

  .eta {
    flex: 0 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 52px;
    line-height: 1.1;
  }

  .eta-value {
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }

  .eta-unit {
    font-size: 0.6875rem;
    color: var(--secondary-text-color);
  }

  .eta-now .eta-value {
    font-size: 1.0625rem;
    color: var(--success-color, #43a047);
  }

  .eta-clock {
    font-size: 1.0625rem;
  }

  .at-clock {
    font-size: 0.6875rem;
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
    direction: ltr;
    unicode-bidi: isolate;
  }

  .mode {
    flex: 0 0 auto;
    --mdc-icon-size: 20px;
    color: var(--secondary-text-color);
  }

  .delay {
    font-size: 0.6875rem;
    font-weight: 500;
    color: var(--warning-color, #ffa600);
    font-variant-numeric: tabular-nums;
    /* Keep "+4" from being reordered to "4+" inside an RTL line. */
    direction: ltr;
    unicode-bidi: isolate;
  }

  /* Genuinely narrow dashboard columns: drop to the essentials. A
     full-width card on a small phone is ~327px, and should keep everything. */
  @container (max-width: 290px) {
    .header,
    .row {
      padding-inline: 12px;
    }
    .sub .operator,
    /* and the separator it would otherwise leave stranded */
    .sub .operator + .sep,
    .mode {
      display: none;
    }
    .eta {
      min-width: 44px;
    }
    .eta-value {
      font-size: 1.25rem;
    }
  }
`;
