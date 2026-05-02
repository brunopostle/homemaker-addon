/**
 * preview.js — IFC overlay using @thatopen/components.
 *
 * Loads IFC into the shared editor Three.js scene as fragment meshes.
 * @thatopen/components is initialised once with a hidden off-screen renderer
 * that satisfies its API; the resulting FragmentsGroup (a THREE.Group) is
 * then added directly to window.__hmScene so it is rendered by the editor's
 * own WebGLRenderer with no extra render pass or canvas required.
 *
 * Opacity is applied by mutating fragment materials in-place (no cloning).
 *
 * NOTE: @thatopen/components bundles all its transitive deps except three.js,
 * which it imports as a peer. The importmap in index.html maps "three" to the
 * same CDN version used by the editor, so both share one THREE namespace —
 * essential for instanceof checks and scene.add() to work correctly.
 * If CDN peer-dep resolution causes issues in production, run `npm run build`
 * (Vite will deduplicate three.js automatically).
 */

const CDN_OBC = "https://cdn.jsdelivr.net/npm/@thatopen/components@2.4.0/dist/index.esm.js";

let _components = null;   // OBC.Components — created once
let _ifcLoader  = null;   // OBC.IfcLoader  — created once
let _model      = null;   // current FragmentsGroup in the editor scene
let _opacity    = 1.0;

/**
 * Initialise @thatopen/components the first time loadIfc() is called.
 * A hidden <div> renderer satisfies the API without producing any output;
 * we never call world.renderer.update() so it never draws anything.
 */
async function _ensureInit() {
    if (_components) return;

    const OBC = await import(CDN_OBC);

    _components = new OBC.Components();
    const worlds = _components.get(OBC.Worlds);
    const world  = worlds.create();

    world.scene = new OBC.SimpleScene(_components);

    // Hidden renderer — needed by components.init() but never rendered into.
    const hiddenDiv = document.createElement("div");
    hiddenDiv.style.cssText = "position:absolute;width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none;";
    document.body.appendChild(hiddenDiv);
    world.renderer = new OBC.SimpleRenderer(_components, hiddenDiv);

    world.camera = new OBC.SimpleCamera(_components);
    // Disable the camera's orbit controls — we're not using this world's camera.
    if (world.camera.controls) world.camera.controls.enabled = false;

    await _components.init();

    _ifcLoader = _components.get(OBC.IfcLoader);
    await _ifcLoader.setup();
}

/**
 * Load an IFC ArrayBuffer into the shared Three.js scene.
 * Replaces any previously loaded IFC overlay.
 */
export async function loadIfc(arrayBuffer) {
    await _ensureInit();

    const scene = window.__hmScene;
    if (!scene) {
        console.warn("preview.js: editor scene not ready");
        return;
    }

    // Dispose and remove previous model.
    if (_model) {
        scene.remove(_model);
        _model.traverse((obj) => {
            if (!obj.isMesh) return;
            obj.geometry?.dispose();
            const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
            mats.forEach((m) => m?.dispose());
        });
        _model = null;
    }

    try {
        const model = await _ifcLoader.load(new Uint8Array(arrayBuffer));
        _model = model;
        scene.add(model);
        _applyOpacity(_opacity);
    } catch (err) {
        console.error("IFC load error:", err);
    }
}

/**
 * Set the opacity of the IFC overlay (0 = invisible, 1 = solid).
 * Mutates materials in-place — no cloning, no material leaks.
 */
export function setOpacity(value) {
    _opacity = value;
    _applyOpacity(value);
}

function _applyOpacity(value) {
    if (!_model) return;
    _model.traverse((obj) => {
        if (!obj.isMesh) return;
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        for (const m of mats) {
            if (!m) continue;
            m.transparent = value < 1.0;
            m.opacity = value;
            m.needsUpdate = true;
        }
    });
}
