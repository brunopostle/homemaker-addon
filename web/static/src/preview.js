/**
 * preview.js — IFC overlay loader using @thatopen/components.
 *
 * Loads an IFC binary into the shared Three.js scene as fragment meshes.
 * Exposes setOpacity() so the regeneration loop can ghost the overlay
 * while the user is editing and solidify it when idle.
 *
 * The @thatopen/components library is loaded from CDN as an ES module.
 * It attaches fragment meshes directly into the Three.js scene provided
 * by editor.js via the shared `window.__hmScene` / `window.__hmRenderer`
 * / `window.__hmCamera` references set by editor.js on init.
 */

import * as THREE from "three";

const CDN_OBC = "https://cdn.jsdelivr.net/npm/@thatopen/components@2.4.0/dist/index.esm.js";
const CDN_OBCF = "https://cdn.jsdelivr.net/npm/@thatopen/components-front@2.4.0/dist/index.esm.js";

let _fragments = null;   // current loaded fragment group
let _opacity = 1.0;

/**
 * Load an IFC ArrayBuffer into the shared Three.js scene.
 * Replaces any previously loaded IFC overlay.
 */
export async function loadIfc(arrayBuffer) {
  // Lazily import @thatopen/components the first time we need it.
  const OBC = await import(CDN_OBC);

  const scene    = window.__hmScene;
  const renderer = window.__hmRenderer;
  const camera   = window.__hmCamera;

  if (!scene || !renderer || !camera) {
    console.warn("preview.js: Three.js context not ready yet");
    return;
  }

  // Remove old fragments
  if (_fragments) {
    scene.remove(_fragments);
    _fragments = null;
  }

  try {
    const components = new OBC.Components();
    const worlds = components.get(OBC.Worlds);
    const world = worlds.create();

    // Share the editor's scene/renderer/camera rather than creating new ones.
    world.scene = new OBC.SimpleScene(components);
    world.scene.three = scene;
    world.renderer = new OBC.SimpleRenderer(components, renderer.domElement);
    world.renderer.three = renderer;
    world.camera = new OBC.SimpleCamera(components);
    world.camera.three = camera;

    await components.init();

    const ifcLoader = components.get(OBC.IfcLoader);
    await ifcLoader.setup();

    const model = await ifcLoader.load(new Uint8Array(arrayBuffer));
    _fragments = model;

    // Apply current opacity immediately.
    _applyOpacity(_opacity);

    scene.add(model);
  } catch (err) {
    console.error("IFC load error:", err);
  }
}

/**
 * Set the opacity of the IFC overlay (0 = invisible, 1 = solid).
 */
export function setOpacity(value) {
  _opacity = value;
  _applyOpacity(value);
}

function _applyOpacity(value) {
  if (!_fragments) return;
  _fragments.traverse((obj) => {
    if (obj.isMesh) {
      obj.material = Array.isArray(obj.material)
        ? obj.material.map((m) => _cloneWithOpacity(m, value))
        : _cloneWithOpacity(obj.material, value);
    }
  });
}

function _cloneWithOpacity(mat, value) {
  if (!mat) return mat;
  const m = mat.clone();
  m.transparent = value < 1.0;
  m.opacity = value;
  return m;
}
