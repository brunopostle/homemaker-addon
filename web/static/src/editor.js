/**
 * editor.js — Three.js 3D cuboid space editor.
 *
 * Each "room" is an axis-aligned box with:
 *   - a semi-transparent fill mesh
 *   - a wireframe edge overlay
 *   - 6 face-handle discs (drag to resize that face)
 *
 * Face snapping: when a handle is dragged to be coplanar with any face of
 * another room (within SNAP_THRESHOLD), it snaps precisely. Partial overlaps
 * are intentional — the server/topologic_core handles all topology inference.
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
import { snapToFaces, computeFaceDrag, SNAP_THRESHOLD, GRID_SNAP } from "./editor-utils.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const FACE_FILL_COLOR    = 0x4488cc;
const FACE_FILL_OPACITY  = 0.18;
const FACE_EDGE_COLOR    = 0x88bbee;
const HANDLE_COLOR        = 0xffffff;
const HANDLE_STYLED_COLOR = 0x88ddff;  // face has a style different from room default
const HANDLE_HOVER_COLOR  = 0xffdd44;
const HANDLE_RADIUS       = 0.12;   // metres

// Human-readable name for each face index (used in props panel label).
const FACE_NAMES = ["Floor", "Right wall", "Ceiling", "Left wall", "Back wall", "Front wall"];
const DEFAULT_W = 4.0, DEFAULT_D = 4.0, DEFAULT_H = 3.0;

// Face indices: 0=floor(−y) 1=right(+x) 2=ceiling(+y) 3=left(−x) 4=back(−z) 5=front(+z)
// Three.js is Y-up: Y = elevation, Z = depth.
const FACE_NORMALS = [
  new THREE.Vector3( 0,-1, 0),  // floor   (−Y, bottom)
  new THREE.Vector3( 1, 0, 0),  // right   (+X)
  new THREE.Vector3( 0, 1, 0),  // ceiling (+Y, top)
  new THREE.Vector3(-1, 0, 0),  // left    (−X)
  new THREE.Vector3( 0, 0,-1),  // back    (−Z)
  new THREE.Vector3( 0, 0, 1),  // front   (+Z)
];
// Which axis & sign each face handle moves on drag
const FACE_AXIS  = [1, 0, 1, 0, 2, 2];   // 0=x 1=y(elevation) 2=z(depth)
const FACE_SIGN  = [-1, 1, 1, -1, -1, 1];

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

// Grid helper
scene.add(new THREE.GridHelper(40, 40, 0x333333, 0x2a2a2a));

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
camera.position.set(12, 10, 18);
camera.lookAt(0, 1.5, 0);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.1;
controls.mouseButtons = { LEFT: null, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };

// Expose for preview.js
window.__hmScene    = scene;
window.__hmRenderer = renderer;
window.__hmCamera   = camera;

// ---------------------------------------------------------------------------
// Room data model
// ---------------------------------------------------------------------------
/**
 * @typedef {{ id:string, position:[number,number,number], size:[number,number,number],
 *             stylename:string, usage:string,
 *             _group:THREE.Group, _handles:THREE.Mesh[] }} Room
 */

let _rooms            = [];   // Room[]
let _nextId           = 1;
let _selected         = null; // Room | null
let _selectedFaceIdx  = null; // face index (0-5) of the last clicked handle, or null

// ---------------------------------------------------------------------------
// Room visual construction
// ---------------------------------------------------------------------------
function _makeRoomGroup(room) {
  const group = new THREE.Group();

  const [w, d, h] = room.size;
  const geo = new THREE.BoxGeometry(w, h, d);

  // Fill
  const fill = new THREE.Mesh(
    geo,
    new THREE.MeshLambertMaterial({
      color: FACE_FILL_COLOR,
      transparent: true,
      opacity: FACE_FILL_OPACITY,
      depthWrite: false,
    })
  );
  fill.position.set(w / 2, h / 2, d / 2);
  fill.userData.roomId = room.id;
  fill.userData.isRoomFill = true;
  group.add(fill);

  // Edges
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(geo),
    new THREE.LineBasicMaterial({ color: FACE_EDGE_COLOR })
  );
  edges.position.copy(fill.position);
  group.add(edges);

  // Face handles
  const handleGeo = new THREE.SphereGeometry(HANDLE_RADIUS, 12, 8);
  const handles = FACE_NORMALS.map((normal, fi) => {
    const hx = w / 2 + normal.x * w / 2;
    const hy = h / 2 + normal.y * h / 2;
    const hz = d / 2 + normal.z * d / 2;

    // Blue tint when this face has a style different from the room default.
    const faceStyle = room.face_styles?.[fi] ?? room.stylename;
    const baseColor = faceStyle !== room.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR;

    const mesh = new THREE.Mesh(
      handleGeo,
      new THREE.MeshBasicMaterial({ color: baseColor })
    );
    mesh.position.set(hx, hy, hz);
    mesh.userData.isHandle = true;
    mesh.userData.faceIndex = fi;
    mesh.userData.roomId = room.id;
    group.add(mesh);
    return mesh;
  });

  group.position.set(...room.position);
  room._group = group;
  room._handles = handles;
  scene.add(group);
  return group;
}

function _removeRoomGroup(room) {
  if (room._group) {
    scene.remove(room._group);
    room._group = null;
    room._handles = [];
  }
}

function _updateRoomGroup(room) {
  _removeRoomGroup(room);
  _makeRoomGroup(room);
  _setSelected(room);
}

function _setSelected(room) {
  // Deselect any face.
  _selectedFaceIdx = null;
  const faceRow    = document.getElementById("face-style-row");
  const faceDivider = document.getElementById("face-divider");
  if (faceRow)    faceRow.style.display    = "none";
  if (faceDivider) faceDivider.style.display = "none";

  // Reset all fills and handle colours.
  _rooms.forEach((r) => {
    if (r._group) {
      r._group.children.forEach((c) => {
        if (c.isMesh && c.userData.isRoomFill)
          c.material.color.setHex(FACE_FILL_COLOR);
        if (c.isMesh && c.userData.isHandle) {
          const fi = c.userData.faceIndex;
          const faceStyle = r.face_styles?.[fi] ?? r.stylename;
          c.material.color.setHex(faceStyle !== r.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR);
        }
      });
    }
  });

  _selected = room;
  const panel = document.getElementById("props-panel");

  if (!room) {
    panel?.classList.remove("visible");
    return;
  }

  // Highlight selected fill
  room._group?.children.forEach((c) => {
    if (c.isMesh && c.userData.isRoomFill)
      c.material.color.setHex(0x66aaff);
  });

  // Update props panel
  if (panel) {
    panel.classList.add("visible");
    const styleSel = document.getElementById("room-style");
    const usageSel = document.getElementById("room-usage");
    if (styleSel) styleSel.value = room.stylename;
    if (usageSel) usageSel.value = room.usage;
  }
}

function _selectFace(handleMesh) {
  const room = _roomById(handleMesh.userData.roomId);
  if (!room) return;
  // Select the room (resets _selectedFaceIdx to null), then override.
  _setSelected(room);
  _selectedFaceIdx = handleMesh.userData.faceIndex;

  const faceRow     = document.getElementById("face-style-row");
  const faceDivider = document.getElementById("face-divider");
  const faceLabel   = document.getElementById("face-style-label");
  const faceSel     = document.getElementById("face-style-sel");
  if (faceRow && faceLabel && faceSel) {
    faceLabel.textContent = FACE_NAMES[_selectedFaceIdx];
    faceSel.value = room.face_styles?.[_selectedFaceIdx] ?? room.stylename;
    faceRow.style.display    = "";
    if (faceDivider) faceDivider.style.display = "";
  }
}

// ---------------------------------------------------------------------------
// Geometry serialisation  (→ server)
// ---------------------------------------------------------------------------
window.__hmGetGeometry = function () {
  return {
    name: "My Building",
    rooms: _rooms.map((r) => ({
      position:    r.position,
      size:        r.size,
      face_styles: r.face_styles,
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
  const usage    = document.getElementById("sel-usage")?.value || "living";
  const stylename= document.getElementById("sel-style")?.value  || "default";
  const resolvedStyle = options.stylename || stylename;
  const room = {
    id:          `r${_nextId++}`,
    position:    options.position    || [0, 0, 0],
    size:        options.size        || [DEFAULT_W, DEFAULT_D, DEFAULT_H],
    stylename:   resolvedStyle,
    face_styles: options.face_styles || Array(6).fill(resolvedStyle),
    usage:       options.usage       || usage,
    _group:      null,
    _handles:    [],
  };
  _rooms.push(room);
  _makeRoomGroup(room);
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

document.getElementById("btn-add-room")?.addEventListener("click", () => addRoom());

document.getElementById("delete-room")?.addEventListener("click", () => {
  if (_selected) deleteRoom(_selected);
});

// Props panel changes
document.getElementById("room-style")?.addEventListener("change", (e) => {
  if (_selected) {
    _selected.stylename   = e.target.value;
    _selected.face_styles = Array(6).fill(e.target.value);
    _updateRoomGroup(_selected);
    _emitEdit();
  }
});
document.getElementById("room-usage")?.addEventListener("change", (e) => {
  if (_selected) { _selected.usage = e.target.value; _emitEdit(); }
});
document.getElementById("face-style-sel")?.addEventListener("change", (e) => {
  if (_selected && _selectedFaceIdx !== null) {
    const fi = _selectedFaceIdx;
    _selected.face_styles[fi] = e.target.value;
    _updateRoomGroup(_selected);
    // Restore face selection — _updateRoomGroup → _setSelected resets it.
    _selectedFaceIdx = fi;
    const faceRow     = document.getElementById("face-style-row");
    const faceDivider = document.getElementById("face-divider");
    const faceLabel   = document.getElementById("face-style-label");
    if (faceRow)     faceRow.style.display     = "";
    if (faceDivider) faceDivider.style.display = "";
    if (faceLabel)   faceLabel.textContent     = FACE_NAMES[fi];
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

function _getHandleObjects() {
  return _rooms.flatMap((r) => r._handles || []);
}

function _getFillObjects() {
  return _rooms.flatMap((r) =>
    (r._group?.children || []).filter((c) => c.isMesh && c.userData.isRoomFill)
  );
}

function _roomById(id) {
  return _rooms.find((r) => r.id === id) || null;
}

// ---------------------------------------------------------------------------
// Drag state
// ---------------------------------------------------------------------------
let _drag = null;
/*
  _drag = {
    room:      Room,
    faceIndex: number,
    axis:      0|1|2,       // world axis being moved
    sign:      1|-1,
    startFacePos: number,   // world coordinate of the face plane before drag started
    startSize:    [w,d,h],
    startPos:     [px,py,pz],
    dragPlane:    THREE.Plane,  // world plane under the pointer during drag
  }
*/

// Plane for pointer tracking
const _dragPlaneHelper = new THREE.Plane();

function _beginHandleDrag(event, handleMesh) {
  const room      = _roomById(handleMesh.userData.roomId);
  if (!room) return;
  const fi        = handleMesh.userData.faceIndex;
  const axis      = FACE_AXIS[fi];
  const sign      = FACE_SIGN[fi];

  // The face plane in world space
  const axisNames = ["x", "y", "z"];
  const axisVec   = new THREE.Vector3();
  axisVec[axisNames[axis]] = 1;

  _dragPlaneHelper.setFromNormalAndCoplanarPoint(
    axisVec,
    handleMesh.getWorldPosition(new THREE.Vector3())
  );

  _drag = {
    room,
    faceIndex: fi,
    axis,
    sign,
    startSize:  [...room.size],
    startPos:   [...room.position],
    dragPlane:  _dragPlaneHelper.clone(),
    handleMesh,           // retained so pointerup can detect a face-handle click
  };

  controls.enabled = false;
}

function _updateHandleDrag(event) {
  if (!_drag) return;
  _updatePointer(event);
  _raycaster.setFromCamera(_pointer, camera);

  const hit = new THREE.Vector3();
  if (!_raycaster.ray.intersectPlane(_drag.dragPlane, hit)) return;

  const { room, axis, sign, startPos, startSize } = _drag;
  const axisNames = ["x", "y", "z"];

  // Raw world coordinate of the dragged face.
  let worldCoord = hit[axisNames[axis]];

  // Face snap takes priority over grid so grid can't push us off a face plane.
  worldCoord = snapToFaces(worldCoord, axis, _rooms, room);
  worldCoord = Math.round(worldCoord / GRID_SNAP) * GRID_SNAP;
  worldCoord = snapToFaces(worldCoord, axis, _rooms, room);

  const result = computeFaceDrag(startPos, startSize, axis, sign, worldCoord);
  if (!result) return;

  room.position = result.position;
  room.size     = result.size;
  _updateRoomGroup(room);
  _emitEdit();
}

function _endHandleDrag() {
  _drag = null;
  controls.enabled = true;
}

// ---------------------------------------------------------------------------
// Pointer events
// ---------------------------------------------------------------------------
let _pointerDownPos = null;

canvas.addEventListener("pointerdown", (e) => {
  _pointerDownPos = { x: e.clientX, y: e.clientY };
  _updatePointer(e);
  _raycaster.setFromCamera(_pointer, camera);

  // Check handles first
  const handleHits = _raycaster.intersectObjects(_getHandleObjects());
  if (handleHits.length > 0) {
    e.stopPropagation();
    _beginHandleDrag(e, handleHits[0].object);
    return;
  }
});

canvas.addEventListener("pointermove", (e) => {
  if (_drag) {
    _updateHandleDrag(e);
    return;
  }

  // Hover highlight handles
  _updatePointer(e);
  _raycaster.setFromCamera(_pointer, camera);
  const hits = _raycaster.intersectObjects(_getHandleObjects());
  _getHandleObjects().forEach((h) => {
    if (!_drag) h.material.color.setHex(HANDLE_COLOR);
  });
  if (hits.length > 0) {
    hits[0].object.material.color.setHex(HANDLE_HOVER_COLOR);
  }
  canvas.style.cursor = hits.length > 0 ? "crosshair" : "default";
});

canvas.addEventListener("pointerup", (e) => {
  if (_drag) {
    const dx = e.clientX - (_pointerDownPos?.x ?? e.clientX);
    const dy = e.clientY - (_pointerDownPos?.y ?? e.clientY);
    const { handleMesh } = _drag;
    _endHandleDrag();
    // Short movement = click on handle → select that face for per-face style editing.
    if (Math.hypot(dx, dy) <= 4 && handleMesh) {
      _selectFace(handleMesh);
    }
    return;
  }

  // Click to select (only if pointer didn't move much)
  if (!_pointerDownPos) return;
  const dx = e.clientX - _pointerDownPos.x;
  const dy = e.clientY - _pointerDownPos.y;
  if (Math.hypot(dx, dy) > 4) return;

  _updatePointer(e);
  _raycaster.setFromCamera(_pointer, camera);
  const hits = _raycaster.intersectObjects(_getFillObjects());
  if (hits.length > 0) {
    const room = _roomById(hits[0].object.userData.roomId);
    _setSelected(room || null);
  } else {
    _setSelected(null);
  }
});

window.addEventListener("pointerup", () => {
  if (_drag) _endHandleDrag();
});

// ---------------------------------------------------------------------------
// Top view toggle
// ---------------------------------------------------------------------------
document.getElementById("btn-top-view")?.addEventListener("click", () => {
  camera.position.set(0, 30, 0.001);
  camera.lookAt(0, 0, 0);
  controls.target.set(0, 0, 0);
  controls.update();
});

// Keyboard shortcut T
window.addEventListener("keydown", (e) => {
  if (e.key === "t" || e.key === "T") {
    document.getElementById("btn-top-view")?.click();
  }
  if ((e.key === "Delete" || e.key === "Backspace") && _selected) {
    deleteRoom(_selected);
  }
});

// ---------------------------------------------------------------------------
// Resize handling
// ---------------------------------------------------------------------------
function _resize() {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  if (renderer.domElement.width !== w || renderer.domElement.height !== h) {
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
}

// ---------------------------------------------------------------------------
// Render loop
// ---------------------------------------------------------------------------
function _animate() {
  requestAnimationFrame(_animate);
  _resize();
  controls.update();
  renderer.render(scene, camera);
}
_animate();

// ---------------------------------------------------------------------------
// Seed with a default room pair so the app opens with something visible
// ---------------------------------------------------------------------------
// Two ground-floor rooms sharing the wall at x=4.
// position[1] (Three.js Y) = 0 for all rooms on the ground floor.
// The second room is narrower in depth (size[1]=3 vs 4) to demonstrate
// partial wall overlap — homemaker infers a door-sized opening there.
addRoom({ position: [0, 0, 0], size: [4, 4, 3], usage: "living",  stylename: "default" });
addRoom({ position: [4, 0, 0], size: [3, 3, 3], usage: "bedroom", stylename: "default" });
