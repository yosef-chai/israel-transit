import { LitElement, css, html, nothing } from "lit";

import { ICONS, icon } from "./icons.js";
import { reducedMotion } from "./util.js";

// The card's own dialog, on a native <dialog>, built to Home Assistant's
// adaptive dialog spec: a dialog where there is room, a bottom sheet where
// there is not. ha-dialog and ha-adaptive-dialog are not a promised API for
// custom cards and load lazily, which left this card without details whenever
// they had not been loaded yet.

// Where HA's adaptive dialog switches between the two (decided on opening).
const WIDE = "(min-width: 871px) and (min-height: 501px)";
// Matches the open animations of HA's dialog (200 ms) and sheet (300 ms), with
// a little to spare before the close goes ahead without its transitionend.
const CLOSE_FALLBACK_MS = 400;
// A pointer has to travel this far before a press becomes a drag, so a shaky
// tap on the close button is still a tap.
const DRAG_START_PX = 8;
// A flick this fast (px/ms) closes the sheet however short it was.
const FLICK_SPEED = 0.5;

/** The element that has focus, looking through every shadow root on the way. */
const deepActiveElement = () => {
  let active = document.activeElement;
  while (active?.shadowRoot?.activeElement) active = active.shadowRoot.activeElement;
  return active;
};

export class IsraelTransitDialog extends LitElement {
  static properties = {
    open: { type: Boolean },
    heading: {},
    subheading: {},
    closeLabel: { attribute: false },
    opener: { attribute: false },
    _sheet: { state: true },
    _scrolled: { state: true },
  };

  static styles = css`
    dialog {
      --it-dialog-duration: 200ms;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      width: min(580px, calc(100vw - 32px));
      max-width: none;
      max-height: calc(100vh - 80px);
      max-height: calc(100dvh - 80px);
      margin: auto;
      padding: 0;
      border: none;
      border-radius: var(--ha-border-radius-3xl, 24px);
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      box-shadow: var(--ha-box-shadow-l, 0 6px 12px -3px rgba(0, 0, 0, 0.12), 0 16px 32px -6px rgba(0, 0, 0, 0.2));
      overflow: hidden;
      opacity: 0;
      transform: scale(0.96);
      transition:
        opacity var(--it-dialog-duration) ease-out,
        transform var(--it-dialog-duration) ease-out;
    }

    dialog:not([open]) {
      display: none;
    }

    dialog.shown {
      opacity: 1;
      transform: none;
    }

    dialog::backdrop {
      background: rgba(0, 0, 0, 0.32);
      opacity: 0;
      transition: opacity var(--it-dialog-duration) ease-out;
    }

    dialog.shown::backdrop {
      opacity: 1;
    }

    dialog.sheet {
      --it-dialog-duration: 300ms;
      width: 100%;
      max-height: 90vh;
      max-height: 90dvh;
      margin: auto 0 0;
      border-end-start-radius: 0;
      border-end-end-radius: 0;
      border-start-start-radius: var(--ha-border-radius-2xl, 20px);
      border-start-end-radius: var(--ha-border-radius-2xl, 20px);
      padding-block-end: env(safe-area-inset-bottom);
      opacity: 1;
      transform: translateY(100%);
    }

    dialog.sheet.shown {
      transform: translateY(var(--it-drag, 0px));
    }

    dialog.dragging {
      transition: none;
    }

    @media (prefers-reduced-motion: reduce) {
      dialog,
      dialog::backdrop {
        transition: none;
      }
    }

    .handle {
      flex: 0 0 auto;
      display: flex;
      justify-content: center;
      padding-block: var(--ha-space-2, 8px) 0;
      touch-action: none;
      cursor: grab;
    }

    .handle::before {
      content: "";
      width: 32px;
      height: 4px;
      border-radius: var(--ha-border-radius-pill, 9999px);
      background: var(--ha-color-border-neutral-normal, rgba(127, 127, 127, 0.5));
    }

    header {
      flex: 0 0 auto;
      display: flex;
      align-items: flex-start;
      gap: var(--ha-space-1, 4px);
      min-height: 48px;
      padding: var(--ha-space-2, 8px) var(--ha-space-4, 16px) var(--ha-space-2, 8px) var(--ha-space-2, 8px);
      padding-inline: var(--ha-space-2, 8px) var(--ha-space-6, 24px);
      border-block-end: var(--ha-border-width-sm, 1px) solid transparent;
      transition: border-color var(--ha-animation-duration-fast, 150ms);
    }

    .sheet header {
      touch-action: none;
    }

    header.scrolled {
      border-block-end-color: var(--divider-color, rgba(127, 127, 127, 0.2));
    }

    .close {
      flex: 0 0 auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: none;
      color: var(--primary-text-color);
      cursor: pointer;
    }

    .close:hover {
      background: var(--ha-color-fill-neutral-quiet-hover, rgba(127, 127, 127, 0.12));
    }

    .close:focus-visible {
      outline: 2px solid var(--ha-color-focus, var(--primary-color));
      outline-offset: 2px;
    }

    .titles {
      flex: 1 1 auto;
      min-width: 0;
      padding-block: 12px var(--ha-space-1, 4px);
    }

    h2 {
      margin: 0;
      font-size: var(--ha-font-size-xl, 20px);
      font-weight: var(--ha-font-weight-medium, 500);
      line-height: var(--ha-line-height-condensed, 1.2);
      overflow-wrap: anywhere;
    }

    .subheading {
      margin-block-start: var(--ha-space-1, 4px);
      font-size: var(--ha-font-size-m, 14px);
      line-height: var(--ha-line-height-condensed, 1.2);
      color: var(--secondary-text-color);
    }

    .body {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      /* Home Assistant's own scrollbar (.ha-scrollbar). */
      scrollbar-color: var(--scrollbar-thumb-color, rgba(127, 127, 127, 0.5)) transparent;
      scrollbar-width: thin;
      padding: 0 var(--ha-space-6, 24px) var(--ha-space-6, 24px);
    }

    .sheet .body {
      padding-inline: var(--ha-space-4, 16px);
    }
  `;

  constructor() {
    super();
    this.open = false;
    this.heading = "";
    this.subheading = "";
    this.closeLabel = "Close";
    this._sheet = false;
    this._scrolled = false;
  }

  get _dialog() {
    return this.renderRoot.querySelector("dialog");
  }

  updated(changed) {
    if (changed.has("open")) {
      if (this.open) this._show();
      else if (changed.get("open")) this.close();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this._closeTimer);
    this._dialog?.close();
  }

  _show() {
    const dialog = this._dialog;
    if (!dialog || dialog.open) return;
    // Taken now, before showModal moves focus into the dialog.
    this._returnTo = this.opener ?? deepActiveElement();
    this._sheet = !window.matchMedia(WIDE).matches;
    this._closing = false;
    dialog.showModal();
    // One frame in the closed position, so the opening can transition.
    requestAnimationFrame(() => dialog.classList.add("shown"));
  }

  /** Close with the same animation that opened it. */
  close() {
    const dialog = this._dialog;
    if (!dialog?.open || this._closing) return;
    this._closing = true;
    dialog.classList.remove("shown", "dragging");
    dialog.style.removeProperty("--it-drag");
    if (reducedMotion()) {
      dialog.close();
      return;
    }
    const done = () => {
      clearTimeout(this._closeTimer);
      dialog.removeEventListener("transitionend", onEnd);
      if (dialog.open) dialog.close();
    };
    const onEnd = (event) => {
      if (event.target === dialog) done();
    };
    dialog.addEventListener("transitionend", onEnd);
    this._closeTimer = setTimeout(done, CLOSE_FALLBACK_MS);
  }

  // Escape fires cancel; taking it over keeps the closing animation. A browser
  // only honours that once without a user gesture in between, after which it
  // closes outright -- _onClose tidies up either way.
  _onCancel(event) {
    event.preventDefault();
    this.close();
  }

  _onClose() {
    clearTimeout(this._closeTimer);
    this._closing = false;
    const dialog = this._dialog;
    dialog?.classList.remove("shown", "dragging");
    dialog?.style.removeProperty("--it-drag");
    this.open = false;
    const target = this._returnTo;
    this._returnTo = undefined;
    if (target?.isConnected) target.focus?.({ preventScroll: true });
    this.dispatchEvent(new CustomEvent("closed"));
  }

  // Home Assistant has single-key shortcuts on the document ("c", "e", "/").
  // Typing inside the dialog must not reach them; nothing else is stopped, so
  // Tab, arrows on the map and Escape all still work.
  _onKeydown(event) {
    event.stopPropagation();
  }

  // A click on the backdrop closes; a drag that started on the map and ended
  // outside the dialog must not. Both halves have to land on the backdrop.
  _onPointerDown(event) {
    this._downOnBackdrop = event.target === this._dialog;
  }

  _onClick(event) {
    if (this._downOnBackdrop && event.target === this._dialog) this.close();
    this._downOnBackdrop = false;
  }

  _onScroll(event) {
    this._scrolled = event.target.scrollTop > 0;
  }

  // -- dragging the sheet down ----------------------------------------------

  _onDragStart(event) {
    if (!this._sheet || event.button > 0) return;
    if (event.target.closest?.("button, a, input, select, textarea")) return;
    this._drag = { id: event.pointerId, y: event.clientY, t: event.timeStamp, active: false };
  }

  _onDragMove(event) {
    const drag = this._drag;
    if (!drag || event.pointerId !== drag.id) return;
    const dy = event.clientY - drag.y;
    if (!drag.active) {
      if (Math.abs(dy) < DRAG_START_PX) return;
      drag.active = true;
      try {
        event.currentTarget.setPointerCapture?.(event.pointerId);
      } catch {
        // The pointer is already gone (lifted, or cancelled by the system).
      }
      this._dialog.classList.add("dragging");
    }
    drag.dy = Math.max(0, dy);
    drag.last = event.timeStamp;
    this._dialog.style.setProperty("--it-drag", `${drag.dy}px`);
  }

  _onDragEnd(event) {
    const drag = this._drag;
    this._drag = undefined;
    if (!drag?.active || event.pointerId !== drag.id) return;
    const dialog = this._dialog;
    dialog.classList.remove("dragging");
    const elapsed = Math.max(1, (drag.last ?? event.timeStamp) - drag.t);
    const fast = drag.dy / elapsed > FLICK_SPEED;
    if (fast || drag.dy > dialog.offsetHeight / 2) {
      this.close();
    } else {
      dialog.style.removeProperty("--it-drag");
    }
  }

  render() {
    const drag = {
      down: (e) => this._onDragStart(e),
      move: (e) => this._onDragMove(e),
      up: (e) => this._onDragEnd(e),
    };
    return html`
      <dialog
        class=${this._sheet ? "sheet" : ""}
        aria-labelledby="title"
        @cancel=${this._onCancel}
        @close=${this._onClose}
        @keydown=${this._onKeydown}
        @pointerdown=${this._onPointerDown}
        @click=${this._onClick}
      >
        ${this._sheet
          ? html`<div
              class="handle"
              aria-hidden="true"
              @pointerdown=${drag.down}
              @pointermove=${drag.move}
              @pointerup=${drag.up}
              @pointercancel=${drag.up}
            ></div>`
          : nothing}
        <header
          class=${this._scrolled ? "scrolled" : ""}
          @pointerdown=${drag.down}
          @pointermove=${drag.move}
          @pointerup=${drag.up}
          @pointercancel=${drag.up}
        >
          <button
            class="close"
            aria-label=${this.closeLabel}
            title=${this.closeLabel}
            @click=${() => this.close()}
          >
            ${icon(ICONS.close, { size: 24 })}
          </button>
          <div class="titles">
            <h2 id="title">${this.heading}</h2>
            ${this.subheading ? html`<div class="subheading">${this.subheading}</div>` : nothing}
          </div>
          <slot name="actions"></slot>
        </header>
        <div class="body" @scroll=${this._onScroll}>
          ${this.open ? html`<slot></slot>` : nothing}
        </div>
      </dialog>
    `;
  }
}
