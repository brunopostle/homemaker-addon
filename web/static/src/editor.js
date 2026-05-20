// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2024 Bruno Postle <bruno@postle.net>
/**
 * editor.js — Three.js 3D space editor.
 *
 * Every room is a "cell": a quadrilateral prism with vertical walls and
 * horizontal floor/ceiling.  The default is an axis-aligned rectangle, but
 * vertex handles let the user drag any corner to create non-orthogonal plans.
 *
 * Cell data model:
 *   vertices  — [[x,z],[x,z],[x,z],[x,z]]  in Three.js XZ plane (CCW from above)
 *   elevation — Y of the floor
 *   height    — room height
 *   face_styles — [floor, ceiling, wall0..walln-1]  (n+2 entries for n-vertex room)
 *   stylename, usage — per-room defaults
 *
 * Face indices:
 *   fi=0  floor
 *   fi=1  ceiling
 *   fi=2  wall 0 (edge: vertex 0 → 1)
 *   fi=3  wall 1 (edge: vertex 1 → 2)
 *   fi=4  wall 2 (edge: vertex 2 → 3)
 *   fi=5  wall 3 (edge: vertex 3 → 0)
 *
 * Exposes:
 *   window.__hmGetGeometry()  → request body for POST /api/generate
 *   window.__hmScene          → shared THREE.Scene  (for preview.js)
 *   window.__hmRenderer       → shared THREE.WebGLRenderer
 *   window.__hmCamera         → shared THREE.PerspectiveCamera
 *
 * Fires window CustomEvent "hm:edit" whenever the room set changes.
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
    snapToFaces, snapVertexToWallPlanes, snapVertexToVertices, computeFaceDrag,
    SNAP_THRESHOLD, GRID_SNAP, MIN_DIM,
} from "./editor-utils.js";
import { getModel, setHover, peekMobile } from "./preview.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const FACE_FILL_COLOR    = 0x4488cc;
const FACE_FILL_OPACITY  = 0.18;
const FACE_EDGE_COLOR    = 0x88bbee;
const HANDLE_COLOR        = 0xffffff;
const HANDLE_STYLED_COLOR = 0x88ddff;   // face has a style ≠ room default
const HANDLE_HOVER_COLOR  = 0xffdd44;
const HANDLE_RADIUS       = 0.12;
const VERTEX_HANDLE_COLOR  = 0xff9900; // orange — polygon vertex corner handles
const VERTEX_HANDLE_RADIUS = 0.14;

// fi=0 floor, fi=1 ceiling, fi=2..5 walls
function _faceName(fi) {
    if (fi === 0) return "Floor";
    if (fi === 1) return "Ceiling";
    return `Wall ${fi - 1}`;
}
const USAGES     = ["living","bedroom","kitchen","circulation","toilet","stair","void","outside","retail","sahn"];
const DEFAULT_W = 4.0, DEFAULT_D = 4.0, DEFAULT_H = 3.0;

// Shared sphere geometries — constant across all rooms; created once.
const _HANDLE_GEO        = new THREE.SphereGeometry(HANDLE_RADIUS,        12, 8);
const _VERTEX_HANDLE_GEO = new THREE.SphereGeometry(VERTEX_HANDLE_RADIUS, 12, 8);

// ---------------------------------------------------------------------------
// Scene setup
// ---------------------------------------------------------------------------
const canvas   = document.getElementById("canvas");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(0x1a1a1a);

const scene = new THREE.Scene();
scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(10, 20, 15);
scene.add(dirLight);

scene.add(new THREE.GridHelper(40, 40, 0x333333, 0x2a2a2a));
const GRID_LIMIT = 20;  // half the grid size — keep all vertices within ±20

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
camera.position.set(12, 10, 18);
camera.lookAt(0, 1.5, 0);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.1;
controls.mouseButtons = { LEFT: null, MIDDLE: THREE.MOUSE.PAN, RIGHT: THREE.MOUSE.ROTATE };

window.__hmScene    = scene;
window.__hmRenderer = renderer;
window.__hmCamera   = camera;

for (const id of ["sel-usage", "room-usage"]) {
    const sel = document.getElementById(id);
    if (!sel) continue;
    sel.innerHTML = "";
    for (const u of USAGES) sel.add(new Option(u, u));
}

// ---------------------------------------------------------------------------
// Room data model
// ---------------------------------------------------------------------------
let _rooms    = [];
let _nextId   = 1;
let _selected = null;
let _selectedFaceIdx = null;

// ---------------------------------------------------------------------------
// Undo / Redo
// ---------------------------------------------------------------------------
const MAX_UNDO   = 50;
let _undoStack   = [];
let _redoStack   = [];

function _snapshotRooms() {
    return _rooms.map(r => ({
        vertices:    r.vertices.map(v => [...v]),
        elevation:   r.elevation,
        height:      r.height,
        stylename:   r.stylename,
        face_styles: [...(r.face_styles || [])],
        usage:       r.usage,
    }));
}

function _pushUndo() {
    _undoStack.push(_snapshotRooms());
    if (_undoStack.length > MAX_UNDO) _undoStack.shift();
    _redoStack = [];
}

function _restoreSnapshot(snapshot) {
    for (const r of [..._rooms]) _removeRoomGroup(r);
    _rooms  = [];
    _nextId = 1;
    _setSelected(null);
    for (const r of snapshot) {
        const room = {
            id: `r${_nextId++}`,
            vertices:    r.vertices.map(v => [...v]),
            elevation:   r.elevation,
            height:      r.height,
            stylename:   r.stylename,
            face_styles: [...r.face_styles],
            usage:       r.usage,
            _group: null, _handles: [], _vertexHandles: [],
        };
        _rooms.push(room);
        _makeCellGroup(room);
    }
    _emitEdit();
}

function undo() {
    if (_drag) _endDrag();
    if (_undoStack.length === 0) return;
    _redoStack.push(_snapshotRooms());
    _restoreSnapshot(_undoStack.pop());
}

function redo() {
    if (_drag) _endDrag();
    if (_redoStack.length === 0) return;
    _undoStack.push(_snapshotRooms());
    _restoreSnapshot(_redoStack.pop());
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function _polygonCentroid(vertices) {
    const n = vertices.length;
    return {
        x: vertices.reduce((s, v) => s + v[0], 0) / n,
        z: vertices.reduce((s, v) => s + v[1], 0) / n,
    };
}

/**
 * Return [cx, cz] for the next new room: flush against the right edge of the
 * existing bounding box and aligned to its minimum Z, so the new cell shares a
 * face with the existing complex rather than floating in space.
 */
function _nextPlacementPos() {
    if (_rooms.length === 0) return [0, 0];
    let maxX = -Infinity, minZ = Infinity;
    for (const r of _rooms) {
        for (const [x, z] of r.vertices) {
            maxX = Math.max(maxX, x);
            minZ = Math.min(minZ, z);
        }
    }
    return [maxX, minZ];
}

// ---------------------------------------------------------------------------
// Cell geometry builder (used for all rooms)
// ---------------------------------------------------------------------------
function _buildCellGeometry(vertices2d, elevation, height) {
    const n = vertices2d.length;
    const contour = vertices2d.map(([x, z]) => new THREE.Vector2(x, z));
    const tris = THREE.ShapeUtils.triangulateShape(contour, []);

    const pos = [];
    for (const [x, z] of vertices2d) pos.push(x, elevation,          z);  // floor ring
    for (const [x, z] of vertices2d) pos.push(x, elevation + height, z);  // ceiling ring
    for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        const [xi, zi] = vertices2d[i], [xj, zj] = vertices2d[j];
        pos.push(
            xi, elevation,          zi,
            xj, elevation,          zj,
            xj, elevation + height, zj,
            xi, elevation + height, zi,
        );
    }

    const idx = [];
    for (const [a, b, c] of tris) { idx.push(a, b, c); idx.push(n + a, n + c, n + b); }
    for (let i = 0; i < n; i++) {
        const b = 2 * n + i * 4;
        idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    return geo;
}

// ---------------------------------------------------------------------------
// Room visual construction — unified
// ---------------------------------------------------------------------------
function _makeCellGroup(room) {
    const group = new THREE.Group();
    const { vertices, elevation, height } = room;
    const n   = vertices.length;
    const geo = _buildCellGeometry(vertices, elevation, height);

    const fill = new THREE.Mesh(
        geo,
        new THREE.MeshLambertMaterial({
            color: FACE_FILL_COLOR, transparent: true, opacity: FACE_FILL_OPACITY,
            depthWrite: false, side: THREE.DoubleSide,
        })
    );
    fill.userData.room      = room;
    fill.userData.isRoomFill = true;
    room._fillMesh = fill;
    group.add(fill);

    group.add(new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color: FACE_EDGE_COLOR })
    ));

    const centroid = _polygonCentroid(vertices);
    const midY = elevation + height / 2;

    // 6 face handles: fi=0 floor, fi=1 ceiling, fi=2..n+1 walls
    const handlePositions = [
        [centroid.x, elevation,          centroid.z],
        [centroid.x, elevation + height, centroid.z],
        ...Array.from({ length: n }, (_, i) => {
            const j = (i + 1) % n;
            return [
                (vertices[i][0] + vertices[j][0]) / 2,
                midY,
                (vertices[i][1] + vertices[j][1]) / 2,
            ];
        }),
    ];

    room._handles = handlePositions.map(([hx, hy, hz], fi) => {
        const fs    = room.face_styles?.[fi] ?? room.stylename;
        const color = fs !== room.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR;
        const mesh  = new THREE.Mesh(_HANDLE_GEO, new THREE.MeshBasicMaterial({ color }));
        mesh.position.set(hx, hy, hz);
        mesh.userData.isHandle  = true;
        mesh.userData.faceIndex = fi;
        mesh.userData.room      = room;
        group.add(mesh);
        return mesh;
    });

    // Vertex handles — orange spheres at each plan corner at mid-height
    room._vertexHandles = vertices.map(([x, z], i) => {
        const m = new THREE.Mesh(_VERTEX_HANDLE_GEO, new THREE.MeshBasicMaterial({ color: VERTEX_HANDLE_COLOR }));
        m.position.set(x, midY, z);
        m.userData.isVertexHandle = true;
        m.userData.vertexIndex    = i;
        m.userData.room           = room;
        group.add(m);
        return m;
    });

    room._group = group;
    scene.add(group);
    return group;
}

function _removeRoomGroup(room) {
    if (room._group) {
        scene.remove(room._group);
        room._group.traverse((obj) => {
            if (obj.isLineSegments) {
                obj.geometry?.dispose();
                obj.material?.dispose();
            } else if (obj.isMesh && !obj.userData.isHandle && !obj.userData.isVertexHandle) {
                // Per-room fill mesh — owned geometry and material.
                obj.geometry?.dispose();
                obj.material?.dispose();
            } else if (obj.isMesh) {
                // Handle meshes share _HANDLE_GEO/_VERTEX_HANDLE_GEO — only dispose the per-mesh material.
                obj.material?.dispose();
            }
        });
        room._group         = null;
        room._fillMesh      = null;
        room._handles       = [];
        room._vertexHandles = [];
    }
}

function _updateRoomGroup(room) {
    _removeRoomGroup(room);
    _makeCellGroup(room);
    // Only update fill colour — avoid the O(n·handles) full reset of _setSelected.
    if (room === _selected) {
        room._fillMesh?.material.color.setHex(0x66aaff);
    }
}

// ---------------------------------------------------------------------------
// Selection & props panel
// ---------------------------------------------------------------------------
function _setSelected(room) {
    _selectedFaceIdx = null;
    const faceRow     = document.getElementById("face-style-row");
    const faceDivider = document.getElementById("face-divider");
    if (faceRow)     faceRow.style.display     = "none";
    if (faceDivider) faceDivider.style.display = "none";

    for (const r of _rooms) {
        r._fillMesh?.material.color.setHex(FACE_FILL_COLOR);
        for (const h of r._handles) {
            const fi = h.userData.faceIndex;
            const fs = r.face_styles?.[fi] ?? r.stylename;
            h.material.color.setHex(fs !== r.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR);
        }
        for (const h of r._vertexHandles) {
            h.material.color.setHex(VERTEX_HANDLE_COLOR);
        }
    }

    _selected = room;
    const panel = document.getElementById("props-panel");
    if (!room) { panel?.classList.remove("visible"); return; }

    room._fillMesh?.material.color.setHex(0x66aaff);

    if (panel) {
        panel.classList.add("visible");
        const rsSel = document.getElementById("room-style");
        const ruSel = document.getElementById("room-usage");
        if (rsSel) rsSel.value = room.stylename;
        if (ruSel) ruSel.value = room.usage;
    }

    // Sync toolbar selectors to the selected room.
    const toolbarStyle = document.getElementById("sel-style");
    const toolbarUsage = document.getElementById("sel-usage");
    if (toolbarStyle) toolbarStyle.value = room.stylename;
    if (toolbarUsage) toolbarUsage.value = room.usage;
}

function _selectFace(handleMesh) {
    const room = handleMesh.userData.room;
    if (!room) return;
    _setSelected(room);
    _selectedFaceIdx = handleMesh.userData.faceIndex;

    const faceRow     = document.getElementById("face-style-row");
    const faceDivider = document.getElementById("face-divider");
    const faceLabel   = document.getElementById("face-style-label");
    const faceSel     = document.getElementById("face-style-sel");
    if (faceRow && faceLabel && faceSel) {
        faceLabel.textContent = _faceName(_selectedFaceIdx);
        faceSel.value = room.face_styles?.[_selectedFaceIdx] ?? room.stylename;
        faceRow.style.display = "";
        if (faceDivider) faceDivider.style.display = "";
    }
}

// ---------------------------------------------------------------------------
// Geometry serialisation
// ---------------------------------------------------------------------------
window.__hmGetGeometry = function () {
    return {
        name: "My Building",
        rooms: _rooms.map((r) => ({
            vertices:    r.vertices,
            elevation:   r.elevation,
            height:      r.height,
            face_styles: r.face_styles,
            stylename:   r.stylename,
            usage:       r.usage,
        })),
    };
};

function _emitEdit() {
    window.dispatchEvent(new CustomEvent("hm:edit"));
}

// ---------------------------------------------------------------------------
// Add / delete rooms
// ---------------------------------------------------------------------------
function addRoom(options = {}) {
    const usage     = document.getElementById("sel-usage")?.value || "living";
    const stylename = options.stylename || document.getElementById("sel-style")?.value || "default";

    let vertices;
    if (options.vertices) {
        vertices = options.vertices;
    } else {
        const [cx, cz] = _nextPlacementPos();
        const w = DEFAULT_W, d = DEFAULT_D;
        vertices = [
            [cx,     cz    ],
            [cx + w, cz    ],
            [cx + w, cz + d],
            [cx,     cz + d],
        ];
    }

    const room = {
        id:             `r${_nextId++}`,
        vertices,
        elevation:      options.elevation  ?? 0,
        height:         options.height     ?? DEFAULT_H,
        stylename,
        face_styles:    options.face_styles ?? Array(vertices.length + 2).fill(stylename),
        usage:          options.usage       || usage,
        _group:         null,
        _handles:       [],
        _vertexHandles: [],
    };
    _rooms.push(room);
    _makeCellGroup(room);
    _setSelected(room);
    _emitEdit();
    return room;
}

function deleteRoom(room) {
    _removeRoomGroup(room);
    _rooms = _rooms.filter((r) => r !== room);
    _setSelected(null);
    _emitEdit();
}

document.getElementById("btn-add-room")?.addEventListener("click", () => {
    _pushUndo();
    addRoom();
});

document.getElementById("btn-reset")?.addEventListener("click", () => {
    _pushUndo();
    for (const r of [..._rooms]) _removeRoomGroup(r);
    _rooms = []; _nextId = 1;
    _undoStack.pop(); _redoStack = []; _setSelected(null);
    addRoom({ vertices: [[0,0],[4,0],[4,4],[0,4]], elevation: 0, height: 3, usage: "living",  stylename: "default" });
    addRoom({ vertices: [[4,0],[7,0],[7,3],[4,3]], elevation: 0, height: 3, usage: "bedroom", stylename: "default" });
    try { localStorage.removeItem("hm-rooms"); } catch (_) {}
});

document.getElementById("delete-room")?.addEventListener("click", () => {
    if (_selected) { _pushUndo(); deleteRoom(_selected); }
});

// Toolbar selectors: update selected room (if any) AND serve as defaults for new rooms.
document.getElementById("sel-style")?.addEventListener("change", (e) => {
    const v = e.target.value;
    if (_selected) {
        _pushUndo();
        _selected.stylename    = v;
        _selected.face_styles  = Array(_selected.vertices.length + 2).fill(v);
        _updateRoomGroup(_selected);
        const rsSel = document.getElementById("room-style");
        if (rsSel) rsSel.value = v;
        _emitEdit();
    }
});

document.getElementById("sel-usage")?.addEventListener("change", (e) => {
    const v = e.target.value;
    if (_selected) {
        _pushUndo();
        _selected.usage = v;
        const ruSel = document.getElementById("room-usage");
        if (ruSel) ruSel.value = v;
        _emitEdit();
    }
});

document.getElementById("room-style")?.addEventListener("change", (e) => {
    if (_selected) {
        _pushUndo();
        _selected.stylename   = e.target.value;
        _selected.face_styles = Array(_selected.vertices.length + 2).fill(e.target.value);
        _updateRoomGroup(_selected);
        const tSel = document.getElementById("sel-style");
        if (tSel) tSel.value = e.target.value;
        _emitEdit();
    }
});

document.getElementById("room-usage")?.addEventListener("change", (e) => {
    if (_selected) {
        _pushUndo();
        _selected.usage = e.target.value;
        const tSel = document.getElementById("sel-usage");
        if (tSel) tSel.value = e.target.value;
        _emitEdit();
    }
});

document.getElementById("face-style-sel")?.addEventListener("change", (e) => {
    if (_selected && _selectedFaceIdx !== null) {
        _pushUndo();
        const fi = _selectedFaceIdx;
        _selected.face_styles[fi] = e.target.value;
        _updateRoomGroup(_selected);
        const faceRow     = document.getElementById("face-style-row");
        const faceDivider = document.getElementById("face-divider");
        const faceLabel   = document.getElementById("face-style-label");
        if (faceRow)     faceRow.style.display     = "";
        if (faceDivider) faceDivider.style.display = "";
        if (faceLabel)   faceLabel.textContent     = _faceName(fi);
        _emitEdit();
    }
});

// ---------------------------------------------------------------------------
// Raycasting helpers
// ---------------------------------------------------------------------------
const _raycaster = new THREE.Raycaster();
const _pointer   = new THREE.Vector2();

function _updatePointer(event) {
    const rect = canvas.getBoundingClientRect();
    _pointer.x =  ((event.clientX - rect.left) / rect.width)  * 2 - 1;
    _pointer.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;
}

function _getHandleObjects()       { return _rooms.flatMap((r) => r._handles       || []); }
function _getVertexHandleObjects() { return _rooms.flatMap((r) => r._vertexHandles || []); }
function _getFillObjects()         { return _rooms.flatMap((r) => r._fillMesh ? [r._fillMesh] : []); }

// ---------------------------------------------------------------------------
// Drag state
// ---------------------------------------------------------------------------
let _drag = null;

// fi=0 = floor (sign=-1), fi=1 = ceiling (sign=+1), fi>=2 = wall push/pull
function _beginHandleDrag(event, handleMesh) {
    const fi   = handleMesh.userData.faceIndex;
    const room = handleMesh.userData.room;
    if (!room) return;

    // Vertical drag plane facing the camera: mouse Y maps to world Y (height),
    // mouse X maps to depth along the plane. Used for both floor/ceiling and walls.
    _updatePointer(event);
    _raycaster.setFromCamera(_pointer, camera);
    const camDir = camera.getWorldDirection(new THREE.Vector3());
    const planeNorm = new THREE.Vector3(camDir.x, 0, camDir.z);
    if (planeNorm.lengthSq() < 0.01) planeNorm.set(0, 0, 1);  // top-view fallback
    else planeNorm.normalize();
    const handlePos = handleMesh.getWorldPosition(new THREE.Vector3());
    const dragPlane = new THREE.Plane().setFromNormalAndCoplanarPoint(planeNorm, handlePos);
    const startHit  = new THREE.Vector3();
    if (!_raycaster.ray.intersectPlane(dragPlane, startHit)) return;

    if (fi === 0 || fi === 1) {
        _drag = {
            mode: "face",
            room, faceIndex: fi,
            sign: fi === 0 ? -1 : 1,
            startElevation: room.elevation,
            startHeight:    room.height,
            startHitY: startHit.y,
            dragPlane,
            handleMesh,
            undoPushed: false,
        };
    } else {
        // Wall handle: push/pull the face along its outward normal.
        const wallIdx = fi - 2;
        const n  = room.vertices.length;
        const v0 = room.vertices[wallIdx];
        const v1 = room.vertices[(wallIdx + 1) % n];
        const dx = v1[0] - v0[0], dz = v1[1] - v0[1];
        const len = Math.sqrt(dx * dx + dz * dz);
        const wallNormal = len > 0.001
            ? new THREE.Vector3(-dz / len, 0, dx / len)
            : new THREE.Vector3(1, 0, 0);
        _drag = {
            mode: "wall",
            room, faceIndex: fi, wallIdx, wallNormal,
            startVertices: room.vertices.map(v => [...v]),
            startHit: startHit.clone(),
            dragPlane,
            handleMesh,
            undoPushed: false,
        };
    }
    controls.enabled = false;
}

function _beginRoomMove(event, fillMesh) {
    const room = fillMesh.userData.room;
    if (!room) return;

    _setSelected(room);
    _updatePointer(event);
    _raycaster.setFromCamera(_pointer, camera);
    const hit = new THREE.Vector3();
    const c = _polygonCentroid(room.vertices);

    if (event.shiftKey) {
        // Vertical move — drag plane faces the camera horizontally.
        const camDir    = camera.getWorldDirection(new THREE.Vector3());
        const planeNorm = new THREE.Vector3(camDir.x, 0, camDir.z);
        if (planeNorm.lengthSq() < 0.01) return;  // camera nearly vertical (top-view) — no-op
        planeNorm.normalize();
        const centre    = new THREE.Vector3(c.x, room.elevation + room.height / 2, c.z);
        const dragPlane = new THREE.Plane().setFromNormalAndCoplanarPoint(planeNorm, centre);
        if (!_raycaster.ray.intersectPlane(dragPlane, hit)) return;
        _drag = { mode: "move", vertical: true, room, dragPlane, pointerOffset: hit.y - room.elevation, undoPushed: false };
        canvas.style.cursor = "ns-resize";
    } else {
        // Horizontal move — drag plane is the floor.
        const dragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -room.elevation);
        if (!_raycaster.ray.intersectPlane(dragPlane, hit)) return;
        _drag = {
            mode: "move", vertical: false, room, dragPlane,
            pointerOffset:  [hit.x - c.x, hit.z - c.z],
            startCentroid:  [c.x, c.z],
            startVertices:  room.vertices.map(v => [...v]),
            undoPushed: false,
        };
        canvas.style.cursor = "grabbing";
    }
    controls.enabled = false;
}

function _beginVertexDrag(event, vertexMesh) {
    const room = vertexMesh.userData.room;
    if (!room) return;
    const vertexIndex = vertexMesh.userData.vertexIndex;
    const midY = room.elevation + room.height / 2;

    _updatePointer(event);
    _raycaster.setFromCamera(_pointer, camera);
    const hit = new THREE.Vector3();
    const dragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -midY);
    if (!_raycaster.ray.intersectPlane(dragPlane, hit)) return;

    const [vx, vz] = room.vertices[vertexIndex];
    _drag = {
        mode: "vertex", room, vertexIndex, dragPlane,
        pointerOffset: [hit.x - vx, hit.z - vz],
        undoPushed: false,
    };
    controls.enabled = false;
}

function _updateRoomMove(event) {
    if (!_drag) return;
    _updatePointer(event);
    _raycaster.setFromCamera(_pointer, camera);
    const hit = new THREE.Vector3();
    if (!_raycaster.ray.intersectPlane(_drag.dragPlane, hit)) return;

    const { room, pointerOffset, vertical, startCentroid, startVertices } = _drag;

    if (vertical) {
        let newY = Math.round((hit.y - pointerOffset) / GRID_SNAP) * GRID_SNAP;
        const h  = room.height;
        const sy0 = snapToFaces(newY,     _rooms, room);
        const sy1 = snapToFaces(newY + h, _rooms, room);
        if      (sy0 !== newY)     newY = sy0;
        else if (sy1 !== newY + h) newY = sy1 - h;
        if (newY === room.elevation) return;
        if (!_drag.undoPushed) { _pushUndo(); _drag.undoPushed = true; }
        room.elevation = newY;
    } else {
        const [ox, oz] = pointerOffset;
        let newCX = Math.round((hit.x - ox) / GRID_SNAP) * GRID_SNAP;
        let newCZ = Math.round((hit.z - oz) / GRID_SNAP) * GRID_SNAP;
        const dX = newCX - startCentroid[0];
        const dZ = newCZ - startCentroid[1];

        // Apply rigid delta to all vertices.
        const tentative = startVertices.map(([x, z]) => [x + dX, z + dZ]);

        // Snap: vertex-to-vertex takes priority; fall back to wall-plane snap.
        let bestDist = Infinity, snapDX = 0, snapDZ = 0;
        let bestSnapRoom = null, bestSnapWallIdx = -1;
        for (const [vx, vz] of tentative) {
            const sv = snapVertexToVertices(vx, vz, _rooms, room);
            if (sv.snapRoom) {
                const sdx = sv.x - vx, sdz = sv.z - vz;
                const dist = Math.sqrt(sdx * sdx + sdz * sdz);
                if (dist > 0 && dist < bestDist) {
                    bestDist = dist;
                    snapDX = sdx; snapDZ = sdz;
                    bestSnapRoom = sv.snapRoom;
                    bestSnapWallIdx = sv.snapWallIdx;
                }
            }
        }
        if (!bestSnapRoom) {
            for (const [vx, vz] of tentative) {
                const snap = snapVertexToWallPlanes(vx, vz, _rooms, room);
                if (!snap.snapRoom) continue;
                const sdx = snap.x - vx, sdz = snap.z - vz;
                const dist = Math.sqrt(sdx * sdx + sdz * sdz);
                if (dist > 0 && dist < bestDist) {
                    bestDist = dist;
                    snapDX = sdx; snapDZ = sdz;
                    bestSnapRoom = snap.snapRoom;
                    bestSnapWallIdx = snap.snapWallIdx;
                }
            }
        }
        if (bestSnapRoom) _showSnapHighlight(bestSnapRoom, bestSnapWallIdx);
        else _clearSnapHighlight();

        const newVerts = tentative.map(([x, z]) => [x + snapDX, z + snapDZ]);
        if (newVerts.some(([x, z]) => Math.abs(x) > GRID_LIMIT || Math.abs(z) > GRID_LIMIT)) return;
        if (newVerts.every(([x, z], i) => x === room.vertices[i][0] && z === room.vertices[i][1])) return;
        if (!_drag.undoPushed) { _pushUndo(); _drag.undoPushed = true; }
        room.vertices = newVerts;
    }

    _updateRoomGroup(room);
    _emitEdit();
}

function _updateHandleDrag(event) {
    if (!_drag) return;
    _updatePointer(event);
    _raycaster.setFromCamera(_pointer, camera);
    const hit = new THREE.Vector3();
    if (!_raycaster.ray.intersectPlane(_drag.dragPlane, hit)) return;

    const { room, sign, startElevation, startHeight, startHitY } = _drag;
    // startFaceY is the Y of the dragged face at rest; map mouse delta to world Y delta.
    const startFaceY = sign > 0 ? startElevation + startHeight : startElevation;
    let worldY = startFaceY + (hit.y - startHitY);
    worldY = snapToFaces(worldY, _rooms, room);
    worldY = Math.round(worldY / GRID_SNAP) * GRID_SNAP;
    worldY = snapToFaces(worldY, _rooms, room);

    const result = computeFaceDrag(startElevation, startHeight, sign, worldY);
    if (!result) return;

    if (!_drag.undoPushed) { _pushUndo(); _drag.undoPushed = true; }
    room.elevation = result.elevation;
    room.height    = result.height;
    _updateRoomGroup(room);
    _emitEdit();
}

function _updateWallHandleDrag(event) {
    if (!_drag) return;
    _updatePointer(event);
    _raycaster.setFromCamera(_pointer, camera);
    const hit = new THREE.Vector3();
    if (!_raycaster.ray.intersectPlane(_drag.dragPlane, hit)) return;

    const { room, wallIdx, wallNormal, startVertices, startHit } = _drag;
    // Project mouse displacement onto the wall's outward normal, then grid-snap.
    let displacement = hit.clone().sub(startHit).dot(wallNormal);
    displacement = Math.round(displacement / GRID_SNAP) * GRID_SNAP;

    const n  = room.vertices.length;
    const i1 = (wallIdx + 1) % n;

    // Tentative new positions for the two wall vertices.
    const nv0 = [startVertices[wallIdx][0] + displacement * wallNormal.x,
                 startVertices[wallIdx][1] + displacement * wallNormal.z];
    const nv1 = [startVertices[i1][0]      + displacement * wallNormal.x,
                 startVertices[i1][1]      + displacement * wallNormal.z];

    // Wall-plane snap: project snap delta onto wallNormal so we only pull in
    // the push direction (avoids sideways drift for diagonal walls).
    let snapAdjust = 0, bestSnapDist = Infinity;
    let snapR = null, snapWI = -1;
    for (const [vx, vz] of [nv0, nv1]) {
        const s = snapVertexToWallPlanes(vx, vz, _rooms, room);
        if (!s.snapRoom) continue;
        const adj  = (s.x - vx) * wallNormal.x + (s.z - vz) * wallNormal.z;
        const dist = Math.sqrt((s.x - vx) ** 2 + (s.z - vz) ** 2);
        if (dist < bestSnapDist) {
            bestSnapDist = dist;
            snapAdjust = adj;
            snapR = s.snapRoom;
            snapWI = s.snapWallIdx;
        }
    }
    // Also snap the dragged wall plane to pass through scene vertices.
    const startD = wallNormal.x * startVertices[wallIdx][0] + wallNormal.z * startVertices[wallIdx][1];
    for (const other of _rooms) {
        if (other === room) continue;
        for (let vi = 0; vi < other.vertices.length; vi++) {
            const [vx, vz] = other.vertices[vi];
            const proj = wallNormal.x * vx + wallNormal.z * vz;
            const dist = Math.abs(proj - startD - displacement);
            if (dist < SNAP_THRESHOLD && dist < bestSnapDist) {
                bestSnapDist = dist;
                snapAdjust = proj - startD - displacement;
                snapR = other;
                snapWI = vi;
            }
        }
    }
    displacement += snapAdjust;
    if (snapR) _showSnapHighlight(snapR, snapWI);
    else _clearSnapHighlight();

    const newVerts = startVertices.map(v => [...v]);
    newVerts[wallIdx] = [
        startVertices[wallIdx][0] + displacement * wallNormal.x,
        startVertices[wallIdx][1] + displacement * wallNormal.z,
    ];
    newVerts[i1] = [
        startVertices[i1][0] + displacement * wallNormal.x,
        startVertices[i1][1] + displacement * wallNormal.z,
    ];
    if ([newVerts[wallIdx], newVerts[i1]].some(([x, z]) => Math.abs(x) > GRID_LIMIT || Math.abs(z) > GRID_LIMIT)) return;

    if (!_drag.undoPushed) { _pushUndo(); _drag.undoPushed = true; }
    room.vertices = newVerts;
    _updateRoomGroup(room);
    _emitEdit();
}

function _updateVertexDrag(event) {
    if (!_drag) return;
    _updatePointer(event);
    _raycaster.setFromCamera(_pointer, camera);
    const hit = new THREE.Vector3();
    if (!_raycaster.ray.intersectPlane(_drag.dragPlane, hit)) return;

    const { room, vertexIndex, pointerOffset } = _drag;
    const [ox, oz] = pointerOffset;
    let newX = Math.round((hit.x - ox) / GRID_SNAP) * GRID_SNAP;
    let newZ = Math.round((hit.z - oz) / GRID_SNAP) * GRID_SNAP;
    // Vertex-to-vertex snap takes priority over plane snap.
    let snap = snapVertexToVertices(newX, newZ, _rooms, room);
    if (!snap.snapRoom) snap = snapVertexToWallPlanes(newX, newZ, _rooms, room);
    newX = snap.x; newZ = snap.z;
    if (snap.snapRoom) _showSnapHighlight(snap.snapRoom, snap.snapWallIdx);
    else _clearSnapHighlight();

    if (Math.abs(newX) > GRID_LIMIT || Math.abs(newZ) > GRID_LIMIT) return;
    if (newX === room.vertices[vertexIndex][0] && newZ === room.vertices[vertexIndex][1]) return;
    if (!_drag.undoPushed) { _pushUndo(); _drag.undoPushed = true; }
    room.vertices[vertexIndex][0] = newX;
    room.vertices[vertexIndex][1] = newZ;
    _updateRoomGroup(room);
    _emitEdit();
}

// ---------------------------------------------------------------------------
// Snap highlight — bright LineLoop quad drawn over the wall being snapped to
// ---------------------------------------------------------------------------
let _snapHighlight = null;  // { mesh, snapRoom, wallIdx }

function _showSnapHighlight(snapRoom, wallIdx) {
    if (_snapHighlight?.snapRoom === snapRoom && _snapHighlight?.wallIdx === wallIdx) return;
    _clearSnapHighlight();
    const n  = snapRoom.vertices.length;
    const v0 = snapRoom.vertices[wallIdx];
    const v1 = snapRoom.vertices[(wallIdx + 1) % n];
    const lo = snapRoom.elevation;
    const hi = snapRoom.elevation + snapRoom.height;
    const pts = new Float32Array([
        v0[0], lo, v0[1],
        v1[0], lo, v1[1],
        v1[0], hi, v1[1],
        v0[0], hi, v0[1],
    ]);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pts, 3));
    const mesh = new THREE.LineLoop(geo, new THREE.LineBasicMaterial({ color: 0xffdd00 }));
    scene.add(mesh);
    _snapHighlight = { mesh, snapRoom, wallIdx };
}

function _clearSnapHighlight() {
    if (_snapHighlight) {
        scene.remove(_snapHighlight.mesh);
        _snapHighlight.mesh.geometry.dispose();
        _snapHighlight.mesh.material.dispose();
        _snapHighlight = null;
    }
}

function _endDrag() {
    _clearSnapHighlight();
    _drag = null;
    controls.enabled = true;
    canvas.style.cursor = "default";
}

// ---------------------------------------------------------------------------
// Pointer events
// ---------------------------------------------------------------------------
let _pointerDownPos = null;

canvas.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;   // middle/right reserved for camera (OrbitControls)
    if (_drag) _endDrag();
    _pointerDownPos = { x: e.clientX, y: e.clientY };
    _updatePointer(e);
    _raycaster.setFromCamera(_pointer, camera);

    // Vertex handles first (orange corners).
    const vtxHits = _raycaster.intersectObjects(_getVertexHandleObjects());
    if (vtxHits.length > 0) {
        _beginVertexDrag(e, vtxHits[0].object);
        return;
    }

    // Face handles.
    const handleHits = _raycaster.intersectObjects(_getHandleObjects());
    if (handleHits.length > 0) {
        _beginHandleDrag(e, handleHits[0].object);
        return;
    }

    // Room fill.
    const fillHits = _raycaster.intersectObjects(_getFillObjects());
    if (fillHits.length > 0) {
        _beginRoomMove(e, fillHits[0].object);
    }
});

canvas.addEventListener("pointermove", (e) => {
    if (_drag) {
        if      (_drag.mode === "vertex") _updateVertexDrag(e);
        else if (_drag.mode === "move")   _updateRoomMove(e);
        else if (_drag.mode === "wall")   _updateWallHandleDrag(e);
        else                              _updateHandleDrag(e);
        return;
    }

    _updatePointer(e);
    _raycaster.setFromCamera(_pointer, camera);
    const handleObjs = _getHandleObjects();
    const vertexObjs = _getVertexHandleObjects();

    // Reset colours.
    handleObjs.forEach((h) => {
        const r  = h.userData.room;
        const fi = h.userData.faceIndex;
        const fs = r?.face_styles?.[fi] ?? r?.stylename;
        h.material.color.setHex(fs !== r?.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR);
    });
    vertexObjs.forEach((h) => h.material.color.setHex(VERTEX_HANDLE_COLOR));

    const hits = _raycaster.intersectObjects([...handleObjs, ...vertexObjs]);
    if (hits.length > 0) {
        hits[0].object.material.color.setHex(HANDLE_HOVER_COLOR);
        canvas.style.cursor = "crosshair";
    } else {
        const fillHits = _raycaster.intersectObjects(_getFillObjects());
        canvas.style.cursor = fillHits.length > 0 ? "grab" : "default";
    }

    // IFC overlay hover: make model transparent while mouse is over it (desktop only).
    if (e.pointerType !== "touch") {
        const model = getModel();
        if (model) {
            const modelHits = _raycaster.intersectObject(model, true);
            setHover(modelHits.length > 0);
        }
    } else {
        setHover(false);
    }
});

canvas.addEventListener("pointerup", (e) => {
    if (_drag) {
        const dx = e.clientX - (_pointerDownPos?.x ?? e.clientX);
        const dy = e.clientY - (_pointerDownPos?.y ?? e.clientY);
        const isClick = Math.hypot(dx, dy) <= 4;
        const { mode, handleMesh, room } = _drag;
        _endDrag();
        if (mode === "vertex") {
            // no click action for vertex handles
        } else if ((mode === "face" || mode === "wall") && isClick && handleMesh) {
            _selectFace(handleMesh);
        } else if (mode === "move" && isClick) {
            _setSelected(room);
        }
        // Mobile tap on a cell: peek through the model to expose handles.
        if (e.pointerType === "touch" && isClick) peekMobile(3000);
        return;
    }

    if (!_pointerDownPos) return;
    const dx = e.clientX - _pointerDownPos.x;
    const dy = e.clientY - _pointerDownPos.y;
    if (Math.hypot(dx, dy) > 4) return;

    _updatePointer(e);
    _raycaster.setFromCamera(_pointer, camera);
    const fillHits = _raycaster.intersectObjects(_getFillObjects());
    if (fillHits.length > 0) _setSelected(fillHits[0].object.userData.room);
    else _setSelected(null);

    // Mobile tap on IFC model: peek transparent for 3 s so cell handles are visible.
    if (e.pointerType === "touch") {
        const model = getModel();
        if (model && _raycaster.intersectObject(model, true).length > 0) {
            peekMobile(3000);
        } else {
            setHover(false);
        }
    }
});

window.addEventListener("pointerup", () => { if (_drag) _endDrag(); });

// ---------------------------------------------------------------------------
// Top view / keyboard
// ---------------------------------------------------------------------------
document.getElementById("btn-top-view")?.addEventListener("click", () => {
    camera.position.set(0, 30, 0.001);
    camera.lookAt(0, 0, 0);
    controls.target.set(0, 0, 0);
    controls.update();
});

window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && _drag) {
        const moved = _drag.undoPushed;
        _endDrag();
        if (moved) undo();   // revert any movement that already happened
        return;
    }
    if (e.key === "t" || e.key === "T") document.getElementById("btn-top-view")?.click();
    if ((e.key === "Delete" || e.key === "Backspace") && _selected && !e.ctrlKey && !e.metaKey) {
        _pushUndo();
        deleteRoom(_selected);
    }
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === "z") { e.preventDefault(); undo(); }
    if ((e.ctrlKey || e.metaKey) && (e.shiftKey  && e.key === "z" || e.key === "y")) { e.preventDefault(); redo(); }
});

// ---------------------------------------------------------------------------
// Resize / render loop
// ---------------------------------------------------------------------------
let _lastCssW = 0, _lastCssH = 0;

function _resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (w === _lastCssW && h === _lastCssH) return;
    _lastCssW = w; _lastCssH = h;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
}

function _animate() {
    requestAnimationFrame(_animate);
    _resize();
    controls.update();
    renderer.render(scene, camera);
}
_animate();

// ---------------------------------------------------------------------------
// Load geometry  (called by regenerate.js to restore saved state)
// ---------------------------------------------------------------------------
window.__hmLoadGeometry = function (data) {
    if (!Array.isArray(data?.rooms)) return;
    for (const r of [..._rooms]) _removeRoomGroup(r);
    _rooms  = [];
    _nextId = 1;
    _undoStack = [];
    _redoStack = [];
    _setSelected(null);

    for (const r of data.rooms) {
        if (!r.vertices || r.vertices.length < 3 || r.vertices[0]?.length !== 2) continue;
        const stylename = r.stylename || "default";
        const room = {
            id: `r${_nextId++}`,
            vertices:    r.vertices.map(v => [...v]),
            elevation:   r.elevation ?? 0,
            height:      r.height    ?? DEFAULT_H,
            stylename,
            face_styles: r.face_styles || Array(r.vertices.length + 2).fill(stylename),
            usage:       r.usage || "living",
            _group: null, _handles: [], _vertexHandles: [],
        };
        _rooms.push(room);
        _makeCellGroup(room);
    }

    if (_rooms.length > 0) _setSelected(_rooms[0]);
    _emitEdit();
};

// Seed rooms — shown when no saved layout exists.
addRoom({ vertices: [[0,0],[4,0],[4,4],[0,4]], elevation: 0, height: 3, usage: "living",  stylename: "default" });
addRoom({ vertices: [[4,0],[7,0],[7,3],[4,3]], elevation: 0, height: 3, usage: "bedroom", stylename: "default" });
