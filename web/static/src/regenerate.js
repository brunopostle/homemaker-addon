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
const saveBtn      = document.getElementById("btn-save");
const loadInput    = document.getElementById("inp-load");

// ---------------------------------------------------------------------------
// Save / Load JSON
// ---------------------------------------------------------------------------
saveBtn?.addEventListener("click", () => {
  const data = window.__hmGetGeometry?.();
  if (!data) return;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
  );
  const a = document.createElement("a");
  a.href = url; a.download = "rooms.json"; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
});

document.getElementById("btn-load")?.addEventListener("click", () => loadInput?.click());

loadInput?.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    try { window.__hmLoadGeometry?.(JSON.parse(ev.target.result)); }
    catch (_) { setStatus("invalid file", "error"); }
  };
  reader.readAsText(file);
  e.target.value = "";  // allow reloading the same file
});

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

  // Autosave — persists the layout across page reloads.
  try {
    const data = window.__hmGetGeometry?.();
    if (data) localStorage.setItem("hm-rooms", JSON.stringify(data));
  } catch (_) {}
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
  setTimeout(() => URL.revokeObjectURL(url), 0);
});

function _maybeRegenerate() {
  if (_inFlight) {
    // Another request is running; retry once it finishes rather than dropping this edit.
    _debounceTimer = setTimeout(_maybeRegenerate, 1_000);
    return;
  }
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
  clearTimeout(_solidTimer);
  // Clear any pending debounce so a restore-triggered hm:edit doesn't
  // schedule a phantom regeneration ~10 s after the first real one.
  clearTimeout(_debounceTimer);
  _debounceTimer = null;
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
      let detail = "error";
      try {
        const parsed = JSON.parse(err);
        detail = parsed?.detail?.[0]?.msg ?? parsed?.detail ?? "error";
      } catch (_) {}
      setStatus(String(detail), "error");
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

function _restoreSavedLayout() {
  try {
    const saved = localStorage.getItem("hm-rooms");
    if (saved) window.__hmLoadGeometry?.(JSON.parse(saved));
  } catch (_) {}
}

// Populate style selectors from server, restore saved layout, then regenerate.
fetch("/api/styles")
  .then((r) => r.json())
  .then(({ styles }) => {
    if (styles?.length) {
      for (const id of ["sel-style", "room-style", "face-style-sel"]) {
        const sel = document.getElementById(id);
        if (!sel) continue;
        sel.innerHTML = "";
        for (const s of styles) sel.add(new Option(s, s));
      }
    }
    _restoreSavedLayout();
    _forceRegenerate();
  })
  .catch(() => {
    _restoreSavedLayout();
    _forceRegenerate();
  });
