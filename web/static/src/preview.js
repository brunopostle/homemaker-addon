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

const CDN_OBC    = "https://esm.sh/@thatopen/components@2.4.0?external=three";
const CDN_WEBIFC = "https://cdn.jsdelivr.net/npm/web-ifc@0.0.65/";

const FADE_OUT_MS = 500;

/**
 * Strip IFCSHAPEREPRESENTATION items for any subcontext whose
 * ContextIdentifier = 'Clearance' (door-swing / equipment-clearance volumes).
 * Must run before the buffer reaches ifcLoader.load() because web-ifc disposes
 * its IfcAPI after load, so context filtering has to happen on the raw bytes.
 */
function removeClearanceGeometry(buffer) {
    const header = String.fromCharCode(...buffer.slice(0, 10));
    if (!header.startsWith("ISO-10303")) return buffer;

    const text = new TextDecoder().decode(buffer);

    const ctxIds = new Set();
    for (const m of text.matchAll(
        /#(\d+)\s*=\s*IFCGEOMETRICREPRESENTATIONSUBCONTEXT\s*\(\s*'Clearance'/gi
    )) ctxIds.add(m[1]);
    if (!ctxIds.size) return buffer;

    const repIds = new Set();
    for (const ctxId of ctxIds)
        for (const m of text.matchAll(
            new RegExp(`#(\\d+)\\s*=\\s*IFCSHAPEREPRESENTATION\\s*\\(\\s*#${ctxId}\\s*,`, 'gi')
        )) repIds.add(m[1]);
    if (!repIds.size) return buffer;

    let modified = text;
    for (const repId of repIds)
        modified = modified.replace(
            new RegExp(
                `(#${repId}\\s*=\\s*IFCSHAPEREPRESENTATION\\s*\\([^,]+,[^,]+,[^,]+,)\\([^)]*\\)`,
                'gi'
            ),
            '$1()'
        );

    return new TextEncoder().encode(modified);
}

/**
 * Strip body geometry from all IFCSPACE entities so room volumes are not
 * rendered as solid/semi-transparent masses in the viewer.
 * Navigates: IFCSPACE → IFCPRODUCTDEFINITIONSHAPE → IFCSHAPEREPRESENTATION
 * and empties each representation's items list.
 */
function removeSpaceGeometry(buffer) {
    const header = String.fromCharCode(...buffer.slice(0, 10));
    if (!header.startsWith("ISO-10303")) return buffer;

    const text = new TextDecoder().decode(buffer);

    // Match IFCSPACE and capture its Representation attribute (7th positional arg).
    // Attr types 1-7: 'GUID', #ref/$, str/$, str/$, str/$, #ref/$, #ref/$
    const OPT = `(?:'[^']*'|#\\d+|\\$|\\.[A-Z_]+\\.)`;
    const shapeIds = new Set();
    for (const m of text.matchAll(
        new RegExp(
            `#\\d+\\s*=\\s*IFCSPACE\\s*\\(\\s*'[^']*'\\s*,\\s*${OPT}\\s*,\\s*${OPT}\\s*,\\s*${OPT}\\s*,\\s*${OPT}\\s*,\\s*${OPT}\\s*,\\s*(#\\d+|\\$)`,
            'gi'
        )
    )) {
        const ref = m[1].match(/^#(\d+)$/);
        if (ref) shapeIds.add(ref[1]);
    }
    if (!shapeIds.size) return buffer;

    // IFCPRODUCTDEFINITIONSHAPE(Name, Description, Representations-list)
    const repIds = new Set();
    for (const id of shapeIds) {
        for (const m of text.matchAll(
            new RegExp(
                `#${id}\\s*=\\s*IFCPRODUCTDEFINITIONSHAPE\\s*\\(\\s*${OPT}\\s*,\\s*${OPT}\\s*,\\s*\\(([^)]*)\\)`,
                'gi'
            )
        )) {
            for (const r of m[1].matchAll(/#(\d+)/g)) repIds.add(r[1]);
        }
    }
    if (!repIds.size) return buffer;

    let modified = text;
    for (const id of repIds)
        modified = modified.replace(
            new RegExp(
                `(#${id}\\s*=\\s*IFCSHAPEREPRESENTATION\\s*\\([^,]+,[^,]+,[^,]+,)\\([^)]*\\)`,
                'gi'
            ),
            '$1()'
        );

    return new TextEncoder().encode(modified);
}

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

    // web-ifc's Emscripten glue reads document.currentScript.src at module-evaluation
    // time to auto-detect the wasm base URL.  In ES module context
    // document.currentScript is always null, which throws.  Shadow it with an own
    // property on the document object for the entire init sequence (import + setup),
    // then delete the own property to restore the prototype accessor.
    Object.defineProperty(document, 'currentScript', {
        get: () => ({ src: CDN_WEBIFC + 'web-ifc.js' }),
        configurable: true,
    });

    let OBC;
    try {
        OBC = await import(CDN_OBC);
    } finally {
        delete document.currentScript;
    }

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
    _ifcLoader.settings.wasm = { path: CDN_WEBIFC, absolute: true };

    // web-ifc may load lazily during setup(); keep the stub active.
    Object.defineProperty(document, 'currentScript', {
        get: () => ({ src: CDN_WEBIFC + 'web-ifc.js' }),
        configurable: true,
    });
    try {
        await _ifcLoader.setup();
    } finally {
        delete document.currentScript;
    }
}

/**
 * Load an IFC ArrayBuffer into the shared Three.js scene.
 * The old model stays visible during parsing, then fades out as the new
 * model fades in — no blank gap between models.
 */
export async function loadIfc(arrayBuffer) {
    await _ensureInit();

    const scene = window.__hmScene;
    if (!scene) {
        console.warn("preview.js: editor scene not ready");
        return;
    }

    // Strip Clearance and IfcSpace geometry before parsing so those volumes
    // are never rendered — must happen before ifcLoader.load() because web-ifc
    // disposes its IfcAPI after loading and can't be filtered post-load.
    const filtered = removeSpaceGeometry(
        removeClearanceGeometry(new Uint8Array(arrayBuffer))
    );

    // Parse while the old model stays visible (avoids a blank gap).
    let newModel;
    try {
        newModel = await _ifcLoader.load(filtered);
    } catch (err) {
        console.error("IFC load error:", err);
        return;
    }

    // geometry_adapter.py uses IFC Y = Three.js Z (toward camera / south).
    // @thatopen applies the standard IFC Z-up→Y-up transform: Three.js Z = -IFC Y,
    // so the model ends up mirrored on Z relative to the editor.  Undo that here.
    // The scale flip inverts face normals, so force DoubleSide on all materials.
    newModel.scale.set(1, 1, -1);
    newModel.traverse((obj) => {
        if (!obj.isMesh) return;
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        for (const m of mats) {
            if (m) m.side = 2; // THREE.DoubleSide = 2
        }
    });

    // Swap: new model in at current opacity, old model fades out.
    const oldModel = _model;
    _model = newModel;
    scene.add(newModel);
    _applyOpacityToModel(newModel, _opacity);

    if (oldModel) {
        _fadeOutAndDispose(oldModel, scene);
    }
}

/**
 * Fade a model's opacity to zero over FADE_OUT_MS, then remove and dispose it.
 */
function _fadeOutAndDispose(model, scene) {
    const startOpacity = _opacity;
    const t0 = performance.now();
    (function tick() {
        const t = Math.min((performance.now() - t0) / FADE_OUT_MS, 1);
        // Ease-out: feels faster at start, slower at end.
        _applyOpacityToModel(model, startOpacity * (1 - t * t));
        if (t < 1) {
            requestAnimationFrame(tick);
        } else {
            scene.remove(model);
            model.traverse((obj) => {
                // Dispose geometry only — @thatopen shares material instances between loads
                if (obj.isMesh) obj.geometry?.dispose();
            });
        }
    })();
}

/**
 * Set the opacity of the current IFC overlay (0 = invisible, 1 = solid).
 */
export function setOpacity(value) {
    _opacity = value;
    _applyOpacityToModel(_model, value);
}

function _applyOpacityToModel(model, value) {
    if (!model) return;
    model.traverse((obj) => {
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
