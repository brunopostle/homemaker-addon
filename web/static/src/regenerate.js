/**
 * regenerate.js — background IFC regeneration loop.
 *
 * Watches for edits via the custom "hm:edit" event dispatched by editor.js.
 * Debounces 2 seconds after the last edit, then calls the server, with a
 * hard minimum interval of 10 seconds between requests.
 *
 * While a request is in flight (or the user is actively editing) the IFC
 * overlay is ghosted via preview.js setOpacity(). When idle and the latest
 * IFC has loaded, the overlay is solid.
 */

import { loadIfc, setOpacity } from "./preview.js";

const DEBOUNCE_MS    = 2_000;
const MIN_INTERVAL_MS = 10_000;
const GHOST_OPACITY  = 0.18;
const SOLID_OPACITY  = 1.0;

let _debounceTimer   = null;
let _lastGeneratedAt = 0;
let _inFlight        = false;
let _editActive      = false;
let _solidTimer      = null;

const statusEl = document.getElementById("status");

function setStatus(text, cls = "") {
  statusEl.textContent = text;
  statusEl.className = cls;
}

/** Called by editor.js via: window.dispatchEvent(new CustomEvent("hm:edit")) */
window.addEventListener("hm:edit", () => {
  _editActive = true;
  clearTimeout(_solidTimer);
  setOpacity(GHOST_OPACITY);

  clearTimeout(_debounceTimer);
  _debounceTimer = setTimeout(_maybeRegenerate, DEBOUNCE_MS);
});

/** Manual generate button */
document.getElementById("btn-generate")?.addEventListener("click", () => {
  clearTimeout(_debounceTimer);
  _forceRegenerate();
});

function _maybeRegenerate() {
  const elapsed = Date.now() - _lastGeneratedAt;
  const remaining = MIN_INTERVAL_MS - elapsed;
  if (remaining > 0) {
    _debounceTimer = setTimeout(_maybeRegenerate, remaining);
    return;
  }
  _forceRegenerate();
}

async function _forceRegenerate() {
  if (_inFlight) return;
  _inFlight = true;
  _editActive = false;
  setStatus("generating…", "generating");

  try {
    const geometry = window.__hmGetGeometry?.();
    if (!geometry) {
      setStatus("no geometry", "");
      return;
    }

    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(geometry),
    });

    if (!resp.ok) {
      const err = await resp.text();
      setStatus("error", "error");
      console.error("generate error:", err);
      return;
    }

    const buf = await resp.arrayBuffer();
    _lastGeneratedAt = Date.now();

    await loadIfc(buf);

    if (!_editActive) {
      // Brief delay so the model is rendered before becoming solid.
      _solidTimer = setTimeout(() => setOpacity(SOLID_OPACITY), 200);
    }
    setStatus("ready", "ready");
  } catch (err) {
    setStatus("error", "error");
    console.error("regenerate error:", err);
  } finally {
    _inFlight = false;
  }
}

// Populate style selector from server on load, then kick off first generation.
fetch("/api/styles")
  .then((r) => r.json())
  .then(({ styles }) => {
    const sel = document.getElementById("sel-style");
    const roomSel = document.getElementById("room-style");
    if (!sel || !styles?.length) return;
    sel.innerHTML = "";
    if (roomSel) roomSel.innerHTML = "";
    for (const s of styles) {
      sel.add(new Option(s, s));
      if (roomSel) roomSel.add(new Option(s, s));
    }
    // Trigger initial IFC generation now that styles are loaded.
    _forceRegenerate();
  })
  .catch(() => {
    // Server unreachable on load — still attempt a generation with seed rooms.
    _forceRegenerate();
  });
