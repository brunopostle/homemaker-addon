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
let _lastIfcBuffer   = null;   // most recently generated IFC bytes, for download

const statusEl     = document.getElementById("status");
const downloadBtn  = document.getElementById("btn-download");

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

/** Download the most recently generated IFC file. */
downloadBtn?.addEventListener("click", () => {
  if (!_lastIfcBuffer) return;
  const url = URL.createObjectURL(new Blob([_lastIfcBuffer], { type: "application/x-step" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "building.ifc";
  a.click();
  URL.revokeObjectURL(url);
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
    _lastIfcBuffer = buf;
    if (downloadBtn) downloadBtn.disabled = false;

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

// Populate all style selectors from server on load, then kick off first generation.
fetch("/api/styles")
  .then((r) => r.json())
  .then(({ styles }) => {
    if (!styles?.length) return;
    const targets = ["sel-style", "room-style", "face-style-sel"];
    for (const id of targets) {
      const sel = document.getElementById(id);
      if (!sel) continue;
      sel.innerHTML = "";
      for (const s of styles) sel.add(new Option(s, s));
    }
    _forceRegenerate();
  })
  .catch(() => {
    _forceRegenerate();
  });
