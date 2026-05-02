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

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const FACE_FILL_COLOR    = 0x4488cc;
const FACE_FILL_OPACITY  = 0.18;
const FACE_EDGE_COLOR    = 0x88bbee;
const HANDLE_COLOR       = 0xffffff;
const HANDLE_HOVER_COLOR = 0xffdd44;
const HANDLE_ACTIVE_COLOR= 0xff8800;
const HANDLE_RADIUS      = 0.12;   // metres
const SNAP_THRESHOLD     = 0.15;   // metres
const GRID_SNAP          = 0.1;    // metres — coarse grid for free dragging
const DEFAULT_W = 4.0, DEFAULT_D = 4.0, DEFAULT_H = 3.0;

// Face indices: 0=back(−y) 1=right(+x) 2=front(+y) 3=left(−x) 4=floor(−z) 5=ceiling(+z)
const FACE_NORMALS = [
  new THREE.Vector3( 0,-1, 0),
  new THREE.Vector3( 1, 0, 0),
  new THREE.Vector3( 0, 1, 0),
  new THREE.Vector3(-1, 0, 0),
  new THREE.Vector3( 0, 0,-1),
  new THREE.Vector3( 0, 0, 1),
];
// Which axis & sign each face handle moves on drag
const FACE_AXIS  = [1, 0, 1, 0, 2, 2];   // 0=x 1=y 2=z
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

let _rooms   = [];   // Room[]
let _nextId  = 1;
let _selected = null; // Room | null

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

    const mesh = new THREE.Mesh(
      handleGeo,
      new THREE.MeshBasicMaterial({ color: HANDLE_COLOR })
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
  // Reset all fills
  _rooms.forEach((r) => {
    if (r._group) {
      r._group.children.forEach((c) => {
        if (c.isMesh && c.userData.isRoomFill)
          c.material.color.setHex(FACE_FILL_COLOR);
        if (c.isMesh && c.userData.isHandle)
          c.material.color.setHex(HANDLE_COLOR);
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

// ---------------------------------------------------------------------------
// Geometry serialisation  (→ server)
// ---------------------------------------------------------------------------
window.__hmGetGeometry = function () {
  const styleSel = document.getElementById("sel-style");
  return {
    name: "My Building",
    share_dir: styleSel?.value || "default",
    rooms: _rooms.map((r) => ({
      position: r.position,
      size: r.size,
      stylename: r.stylename,
      usage: r.usage,
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
  const room = {
    id:        `r${_nextId++}`,
    position:  options.position  || [0, 0, 0],
    size:      options.size      || [DEFAULT_W, DEFAULT_D, DEFAULT_H],
    stylename: options.stylename || stylename,
    usage:     options.usage     || usage,
    _group:    null,
    _handles:  [],
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
  if (_selected) { _selected.stylename = e.target.value; _emitEdit(); }
});
document.getElementById("room-usage")?.addEventListener("change", (e) => {
  if (_selected) { _selected.usage = e.target.value; _emitEdit(); }
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
    startSize: [...room.size],
    startPos:  [...room.position],
    dragPlane: _dragPlaneHelper.clone(),
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
  const sizeAxes  = [0, 2, 1]; // Three.js BoxGeometry: x→w, z→d, y→h

  // Raw world coordinate of the dragged face
  let worldCoord = hit[axisNames[axis]];

  // Snap to grid
  worldCoord = Math.round(worldCoord / GRID_SNAP) * GRID_SNAP;

  // Snap to face planes of other rooms
  worldCoord = _snapToOtherFaces(worldCoord, axis, room);

  // Derive new position + size from the new face location
  const sizeIdx = sizeAxes[axis]; // index into [w,d,h]

  let newPos  = [...startPos];
  let newSize = [...startSize];

  if (sign > 0) {
    // Moving the +ve face: only size changes
    const minPos = newPos[axis === 0 ? 0 : axis === 1 ? 1 : 2];
    const newDim = worldCoord - room.position[axis];
    if (newDim < 0.3) return; // minimum room dimension
    newSize[sizeIdx] = newDim;
  } else {
    // Moving the −ve face: position and size both change
    const farFace = room.position[axis] + startSize[sizeIdx];
    const newDim = farFace - worldCoord;
    if (newDim < 0.3) return;
    newPos[axis === 0 ? 0 : axis === 1 ? 1 : 2] = worldCoord;
    newSize[sizeIdx] = newDim;
  }

  room.position = newPos;
  room.size     = newSize;
  _updateRoomGroup(room);
  _emitEdit();
}

function _endHandleDrag() {
  _drag = null;
  controls.enabled = true;
}

// ---------------------------------------------------------------------------
// Snap logic
// ---------------------------------------------------------------------------
function _snapToOtherFaces(worldCoord, axis, draggedRoom) {
  const axisNames = ["x", "y", "z"];
  const sizeAxes  = [0, 2, 1];

  for (const room of _rooms) {
    if (room === draggedRoom) continue;
    const [px, py, pz] = room.position;
    const [w, d, h]    = room.size;
    const origins = [px, py, pz];
    const dims    = [w, d, h];

    const lo = origins[axis];
    const hi = origins[axis] + dims[sizeAxes[axis]];

    if (Math.abs(worldCoord - lo) < SNAP_THRESHOLD) return lo;
    if (Math.abs(worldCoord - hi) < SNAP_THRESHOLD) return hi;
  }
  return worldCoord;
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
    _endHandleDrag();
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
addRoom({ position: [0, 0, 0], size: [4, 4, 3], usage: "living",  stylename: "default" });
addRoom({ position: [4, 1, 0], size: [3, 2, 3], usage: "bedroom", stylename: "default" });
