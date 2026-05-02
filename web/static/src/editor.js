/**
 * editor.js — Three.js 3D space editor.
 *
 * Supports two room types:
 *   cuboid  — axis-aligned box (position + size)
 *   polygon — extruded 2D polygon (vertices + elevation + height)
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
const FACE_FILL_COLOR     = 0x4488cc;
const FACE_FILL_OPACITY   = 0.18;
const FACE_EDGE_COLOR     = 0x88bbee;
const HANDLE_COLOR         = 0xffffff;
const HANDLE_STYLED_COLOR  = 0x88ddff;  // face has a style different from room default
const HANDLE_HOVER_COLOR   = 0xffdd44;
const HANDLE_RADIUS        = 0.12;
const VERTEX_HANDLE_COLOR  = 0xff9900;  // orange — polygon vertex corner handles
const VERTEX_HANDLE_RADIUS = 0.14;

const FACE_NAMES = ["Floor", "Right wall", "Ceiling", "Left wall", "Back wall", "Front wall"];
const USAGES     = ["living","bedroom","kitchen","circulation","toilet","stair","void","outside"];
const DEFAULT_W = 4.0, DEFAULT_D = 4.0, DEFAULT_H = 3.0;

// Face indices for cuboid rooms: 0=floor(−y) 1=right(+x) 2=ceiling(+y) 3=left(−x) 4=back(−z) 5=front(+z)
const FACE_NORMALS = [
  new THREE.Vector3( 0,-1, 0),  // floor
  new THREE.Vector3( 1, 0, 0),  // right
  new THREE.Vector3( 0, 1, 0),  // ceiling
  new THREE.Vector3(-1, 0, 0),  // left
  new THREE.Vector3( 0, 0,-1),  // back
  new THREE.Vector3( 0, 0, 1),  // front
];
const FACE_AXIS  = [1, 0, 1, 0, 2, 2];
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

scene.add(new THREE.GridHelper(40, 40, 0x333333, 0x2a2a2a));

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
camera.position.set(12, 10, 18);
camera.lookAt(0, 1.5, 0);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.1;
controls.mouseButtons = { LEFT: null, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };

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
let _rooms           = [];
let _nextId          = 1;
let _selected        = null;
let _selectedFaceIdx = null;

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
 * Map a face handle's faceIndex (0 or 2) to the face_styles array index for polygon rooms.
 * Polygon face_styles: 0=floor, 1=ceiling, 2..n+1=walls.
 * Handle fi=0 → floor (fsi=0), fi=2 → ceiling (fsi=1).
 */
function _faceStyleIdx(room, fi) {
  if (room?.type !== "polygon") return fi;
  return fi === 2 ? 1 : 0;
}

function _buildPolygonGeometry(vertices2d, elevation, height) {
  const n = vertices2d.length;
  const contour = vertices2d.map(([x, z]) => new THREE.Vector2(x, z));
  const tris = THREE.ShapeUtils.triangulateShape(contour, []);

  const pos = [];
  // Floor ring (y = elevation): indices 0..n-1
  for (const [x, z] of vertices2d) pos.push(x, elevation, z);
  // Ceiling ring (y = elevation + height): indices n..2n-1
  for (const [x, z] of vertices2d) pos.push(x, elevation + height, z);
  // Wall quads: 4 verts each, starting at 2n (separate to get correct normals)
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    const [xi, zi] = vertices2d[i];
    const [xj, zj] = vertices2d[j];
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
// Room visual construction — cuboid
// ---------------------------------------------------------------------------
function _makeRoomGroup(room) {
  const group = new THREE.Group();
  const [w, d, h] = room.size;
  const geo = new THREE.BoxGeometry(w, h, d);

  const fill = new THREE.Mesh(
    geo,
    new THREE.MeshLambertMaterial({
      color: FACE_FILL_COLOR, transparent: true, opacity: FACE_FILL_OPACITY, depthWrite: false,
    })
  );
  fill.position.set(w / 2, h / 2, d / 2);
  fill.userData.roomId = room.id;
  fill.userData.isRoomFill = true;
  group.add(fill);

  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(geo),
    new THREE.LineBasicMaterial({ color: FACE_EDGE_COLOR })
  );
  edges.position.copy(fill.position);
  group.add(edges);

  const handleGeo = new THREE.SphereGeometry(HANDLE_RADIUS, 12, 8);
  const handles = FACE_NORMALS.map((normal, fi) => {
    const hx = w / 2 + normal.x * w / 2;
    const hy = h / 2 + normal.y * h / 2;
    const hz = d / 2 + normal.z * d / 2;
    const faceStyle = room.face_styles?.[fi] ?? room.stylename;
    const baseColor = faceStyle !== room.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR;
    const mesh = new THREE.Mesh(handleGeo, new THREE.MeshBasicMaterial({ color: baseColor }));
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
  room._vertexHandles = [];
  scene.add(group);
  return group;
}

// ---------------------------------------------------------------------------
// Room visual construction — polygon
// ---------------------------------------------------------------------------
function _makePolygonRoomGroup(room) {
  const group = new THREE.Group();
  const { vertices, elevation, height } = room;
  const geo = _buildPolygonGeometry(vertices, elevation, height);

  const fill = new THREE.Mesh(
    geo,
    new THREE.MeshLambertMaterial({
      color: FACE_FILL_COLOR, transparent: true, opacity: FACE_FILL_OPACITY,
      depthWrite: false, side: THREE.DoubleSide,
    })
  );
  fill.userData.roomId = room.id;
  fill.userData.isRoomFill = true;
  group.add(fill);

  group.add(new THREE.LineSegments(
    new THREE.EdgesGeometry(geo),
    new THREE.LineBasicMaterial({ color: FACE_EDGE_COLOR })
  ));

  const centroid = _polygonCentroid(vertices);
  const handleGeo = new THREE.SphereGeometry(HANDLE_RADIUS, 12, 8);

  // Floor handle (fi=0)
  const fsi0 = _faceStyleIdx(room, 0);
  const fs0 = room.face_styles?.[fsi0] ?? room.stylename;
  const floorH = new THREE.Mesh(handleGeo, new THREE.MeshBasicMaterial({
    color: fs0 !== room.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR,
  }));
  floorH.position.set(centroid.x, elevation, centroid.z);
  floorH.userData.isHandle = true;
  floorH.userData.faceIndex = 0;
  floorH.userData.roomId = room.id;
  group.add(floorH);

  // Ceiling handle (fi=2 to reuse FACE_AXIS/FACE_SIGN)
  const fsi2 = _faceStyleIdx(room, 2);
  const fs2 = room.face_styles?.[fsi2] ?? room.stylename;
  const ceilH = new THREE.Mesh(handleGeo, new THREE.MeshBasicMaterial({
    color: fs2 !== room.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR,
  }));
  ceilH.position.set(centroid.x, elevation + height, centroid.z);
  ceilH.userData.isHandle = true;
  ceilH.userData.faceIndex = 2;
  ceilH.userData.roomId = room.id;
  group.add(ceilH);

  room._handles = [floorH, ceilH];

  // Vertex handles — orange spheres at each plan corner, mid-height
  const vtxGeo = new THREE.SphereGeometry(VERTEX_HANDLE_RADIUS, 12, 8);
  const midY = elevation + height / 2;
  room._vertexHandles = vertices.map(([x, z], i) => {
    const m = new THREE.Mesh(vtxGeo, new THREE.MeshBasicMaterial({ color: VERTEX_HANDLE_COLOR }));
    m.position.set(x, midY, z);
    m.userData.isVertexHandle = true;
    m.userData.vertexIndex = i;
    m.userData.roomId = room.id;
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
    room._group = null;
    room._handles = [];
    room._vertexHandles = [];
  }
}

function _updateRoomGroup(room) {
  _removeRoomGroup(room);
  if (room.type === "polygon") _makePolygonRoomGroup(room);
  else _makeRoomGroup(room);
  _setSelected(room);
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

  _rooms.forEach((r) => {
    if (!r._group) return;
    r._group.children.forEach((c) => {
      if (!c.isMesh) return;
      if (c.userData.isRoomFill)
        c.material.color.setHex(FACE_FILL_COLOR);
      if (c.userData.isHandle) {
        const fi  = c.userData.faceIndex;
        const fsi = _faceStyleIdx(r, fi);
        const fs  = r.face_styles?.[fsi] ?? r.stylename;
        c.material.color.setHex(fs !== r.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR);
      }
      if (c.userData.isVertexHandle)
        c.material.color.setHex(VERTEX_HANDLE_COLOR);
    });
  });

  _selected = room;
  const panel = document.getElementById("props-panel");
  if (!room) { panel?.classList.remove("visible"); return; }

  room._group?.children.forEach((c) => {
    if (c.isMesh && c.userData.isRoomFill) c.material.color.setHex(0x66aaff);
  });

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
  _setSelected(room);
  _selectedFaceIdx = handleMesh.userData.faceIndex;

  const faceRow     = document.getElementById("face-style-row");
  const faceDivider = document.getElementById("face-divider");
  const faceLabel   = document.getElementById("face-style-label");
  const faceSel     = document.getElementById("face-style-sel");
  if (faceRow && faceLabel && faceSel) {
    faceLabel.textContent = FACE_NAMES[_selectedFaceIdx];
    const fsi = _faceStyleIdx(room, _selectedFaceIdx);
    faceSel.value = room.face_styles?.[fsi] ?? room.stylename;
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
    rooms: _rooms.map((r) => {
      if (r.type === "polygon") {
        return {
          type:        "polygon",
          vertices:    r.vertices,
          elevation:   r.elevation,
          height:      r.height,
          face_styles: r.face_styles,
          stylename:   r.stylename,
          usage:       r.usage,
        };
      }
      return {
        position:    r.position,
        size:        r.size,
        face_styles: r.face_styles,
        stylename:   r.stylename,
        usage:       r.usage,
      };
    }),
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
  const room = {
    id:            `r${_nextId++}`,
    position:      options.position    || [0, 0, 0],
    size:          options.size        || [DEFAULT_W, DEFAULT_D, DEFAULT_H],
    stylename,
    face_styles:   options.face_styles || Array(6).fill(stylename),
    usage:         options.usage       || usage,
    _group:        null,
    _handles:      [],
    _vertexHandles: [],
  };
  _rooms.push(room);
  _makeRoomGroup(room);
  _setSelected(room);
  _emitEdit();
  return room;
}

function addPolygonRoom(options = {}) {
  const usage     = document.getElementById("sel-usage")?.value || "living";
  const stylename = options.stylename || document.getElementById("sel-style")?.value || "default";
  const n  = options.sides    ?? 6;
  const r  = options.radius   ?? 2.5;
  const cx = options.cx       ?? 0;
  const cz = options.cz       ?? 0;
  const vertices = [];
  for (let i = 0; i < n; i++) {
    const angle = (i / n) * 2 * Math.PI;
    vertices.push([
      Math.round((cx + r * Math.cos(angle)) * 1000) / 1000,
      Math.round((cz + r * Math.sin(angle)) * 1000) / 1000,
    ]);
  }
  const room = {
    id:            `r${_nextId++}`,
    type:          "polygon",
    vertices,
    elevation:     options.elevation  ?? 0,
    height:        options.height     ?? DEFAULT_H,
    stylename,
    face_styles:   options.face_styles ?? Array(n + 2).fill(stylename),
    usage:         options.usage       || usage,
    _group:        null,
    _handles:      [],
    _vertexHandles: [],
  };
  _rooms.push(room);
  _makePolygonRoomGroup(room);
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
document.getElementById("btn-add-polygon")?.addEventListener("click", () => addPolygonRoom());

document.getElementById("delete-room")?.addEventListener("click", () => {
  if (_selected) deleteRoom(_selected);
});

document.getElementById("room-style")?.addEventListener("change", (e) => {
  if (_selected) {
    _selected.stylename = e.target.value;
    const faceCount = _selected.type === "polygon"
      ? (_selected.vertices?.length ?? 0) + 2
      : 6;
    _selected.face_styles = Array(faceCount).fill(e.target.value);
    _updateRoomGroup(_selected);
    _emitEdit();
  }
});
document.getElementById("room-usage")?.addEventListener("change", (e) => {
  if (_selected) { _selected.usage = e.target.value; _emitEdit(); }
});
document.getElementById("face-style-sel")?.addEventListener("change", (e) => {
  if (_selected && _selectedFaceIdx !== null) {
    const fi  = _selectedFaceIdx;
    const fsi = _faceStyleIdx(_selected, fi);
    _selected.face_styles[fsi] = e.target.value;
    _updateRoomGroup(_selected);
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

function _getVertexHandleObjects() {
  return _rooms.flatMap((r) => r._vertexHandles || []);
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

const _dragPlaneHelper = new THREE.Plane();

function _beginHandleDrag(event, handleMesh) {
  const room = _roomById(handleMesh.userData.roomId);
  if (!room) return;
  const fi   = handleMesh.userData.faceIndex;
  const axis = FACE_AXIS[fi];
  const sign = FACE_SIGN[fi];

  const axisVec = new THREE.Vector3();
  ["x", "y", "z"].forEach((k, i) => { if (i === axis) axisVec[k] = 1; });

  _dragPlaneHelper.setFromNormalAndCoplanarPoint(
    axisVec,
    handleMesh.getWorldPosition(new THREE.Vector3())
  );

  // Polygon rooms use synthetic startPos/startSize so computeFaceDrag works for
  // floor (fi=0) and ceiling (fi=2) — only the Y component is ever read.
  const startPos  = room.type === "polygon" ? [0, room.elevation, 0]     : [...room.position];
  const startSize = room.type === "polygon" ? [0, 0, room.height]        : [...room.size];

  _drag = {
    mode: "face", room, faceIndex: fi, axis, sign,
    startSize, startPos, dragPlane: _dragPlaneHelper.clone(), handleMesh,
  };
  controls.enabled = false;
}

function _beginRoomMove(event, fillMesh) {
  const room = _roomById(fillMesh.userData.roomId);
  if (!room) return;

  _updatePointer(event);
  _raycaster.setFromCamera(_pointer, camera);
  const hit = new THREE.Vector3();

  const isPolygon  = room.type === "polygon";
  const floorY     = isPolygon ? room.elevation : room.position[1];
  const heightVal  = isPolygon ? room.height    : room.size[2];
  let centreX, centreZ;
  if (isPolygon) {
    const c = _polygonCentroid(room.vertices);
    centreX = c.x; centreZ = c.z;
  } else {
    centreX = room.position[0] + room.size[0] / 2;
    centreZ = room.position[2] + room.size[1] / 2;
  }

  if (event.shiftKey) {
    const camDir    = camera.getWorldDirection(new THREE.Vector3());
    const planeNorm = new THREE.Vector3(camDir.x, 0, camDir.z).normalize();
    const centre    = new THREE.Vector3(centreX, floorY + heightVal / 2, centreZ);
    const dragPlane = new THREE.Plane().setFromNormalAndCoplanarPoint(planeNorm, centre);
    if (!_raycaster.ray.intersectPlane(dragPlane, hit)) return;
    _drag = { mode: "move", vertical: true, room, dragPlane, pointerOffset: hit.y - floorY };
    canvas.style.cursor = "ns-resize";
  } else {
    const dragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -floorY);
    if (!_raycaster.ray.intersectPlane(dragPlane, hit)) return;
    if (isPolygon) {
      const c = _polygonCentroid(room.vertices);
      _drag = {
        mode: "move", vertical: false, room, dragPlane,
        pointerOffset:  [hit.x - c.x, hit.z - c.z],
        startCentroid:  [c.x, c.z],
        startVertices:  room.vertices.map(v => [...v]),
      };
    } else {
      _drag = {
        mode: "move", vertical: false, room, dragPlane,
        pointerOffset: [hit.x - room.position[0], hit.z - room.position[2]],
      };
    }
    canvas.style.cursor = "grabbing";
  }

  controls.enabled = false;
}

function _beginVertexDrag(event, vertexMesh) {
  const room = _roomById(vertexMesh.userData.roomId);
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
  };
  controls.enabled = false;
}

function _updateRoomMove(event) {
  if (!_drag) return;
  _updatePointer(event);
  _raycaster.setFromCamera(_pointer, camera);
  const hit = new THREE.Vector3();
  if (!_raycaster.ray.intersectPlane(_drag.dragPlane, hit)) return;

  const { room, pointerOffset, vertical } = _drag;
  const isPolygon = room.type === "polygon";

  if (vertical) {
    let newY = Math.round((hit.y - pointerOffset) / GRID_SNAP) * GRID_SNAP;
    if (isPolygon) {
      const h  = room.height;
      const sy0 = snapToFaces(newY,     1, _rooms, room);
      const sy1 = snapToFaces(newY + h, 1, _rooms, room);
      if      (sy0 !== newY)     newY = sy0;
      else if (sy1 !== newY + h) newY = sy1 - h;
      if (newY === room.elevation) return;
      room.elevation = newY;
    } else {
      const h  = room.size[2];
      const sy0 = snapToFaces(newY,     1, _rooms, room);
      const sy1 = snapToFaces(newY + h, 1, _rooms, room);
      if      (sy0 !== newY)     newY = sy0;
      else if (sy1 !== newY + h) newY = sy1 - h;
      if (newY === room.position[1]) return;
      room.position[1] = newY;
    }
  } else {
    const [ox, oz] = pointerOffset;
    if (isPolygon) {
      const { startCentroid, startVertices } = _drag;
      let newCX = Math.round((hit.x - ox) / GRID_SNAP) * GRID_SNAP;
      let newCZ = Math.round((hit.z - oz) / GRID_SNAP) * GRID_SNAP;
      const dX = newCX - startCentroid[0];
      const dZ = newCZ - startCentroid[1];
      room.vertices = startVertices.map(([x, z]) => [
        Math.round((x + dX) * 1000) / 1000,
        Math.round((z + dZ) * 1000) / 1000,
      ]);
    } else {
      let newX = Math.round((hit.x - ox) / GRID_SNAP) * GRID_SNAP;
      let newZ = Math.round((hit.z - oz) / GRID_SNAP) * GRID_SNAP;
      const w = room.size[0], d = room.size[1];
      const sx0 = snapToFaces(newX,     0, _rooms, room);
      const sx1 = snapToFaces(newX + w, 0, _rooms, room);
      if      (sx0 !== newX)     newX = sx0;
      else if (sx1 !== newX + w) newX = sx1 - w;
      const sz0 = snapToFaces(newZ,     2, _rooms, room);
      const sz1 = snapToFaces(newZ + d, 2, _rooms, room);
      if      (sz0 !== newZ)     newZ = sz0;
      else if (sz1 !== newZ + d) newZ = sz1 - d;
      if (newX === room.position[0] && newZ === room.position[2]) return;
      room.position[0] = newX;
      room.position[2] = newZ;
    }
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

  const { room, axis, sign, startPos, startSize } = _drag;
  const axisNames = ["x", "y", "z"];
  let worldCoord = hit[axisNames[axis]];
  worldCoord = snapToFaces(worldCoord, axis, _rooms, room);
  worldCoord = Math.round(worldCoord / GRID_SNAP) * GRID_SNAP;
  worldCoord = snapToFaces(worldCoord, axis, _rooms, room);

  const result = computeFaceDrag(startPos, startSize, axis, sign, worldCoord);
  if (!result) return;

  if (room.type === "polygon") {
    room.elevation = result.position[1];
    room.height    = result.size[2];
  } else {
    room.position = result.position;
    room.size     = result.size;
  }
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
  const newX = Math.round((hit.x - ox) / GRID_SNAP) * GRID_SNAP;
  const newZ = Math.round((hit.z - oz) / GRID_SNAP) * GRID_SNAP;
  if (newX === room.vertices[vertexIndex][0] && newZ === room.vertices[vertexIndex][1]) return;
  room.vertices[vertexIndex][0] = newX;
  room.vertices[vertexIndex][1] = newZ;
  _updateRoomGroup(room);
  _emitEdit();
}

function _endDrag() {
  _drag = null;
  controls.enabled = true;
  canvas.style.cursor = "default";
}

// ---------------------------------------------------------------------------
// Pointer events
// ---------------------------------------------------------------------------
let _pointerDownPos = null;

canvas.addEventListener("pointerdown", (e) => {
  _pointerDownPos = { x: e.clientX, y: e.clientY };
  _updatePointer(e);
  _raycaster.setFromCamera(_pointer, camera);

  // Vertex handles first (polygon corners)
  const vtxHits = _raycaster.intersectObjects(_getVertexHandleObjects());
  if (vtxHits.length > 0) {
    e.stopPropagation();
    _beginVertexDrag(e, vtxHits[0].object);
    return;
  }

  // Face handles
  const handleHits = _raycaster.intersectObjects(_getHandleObjects());
  if (handleHits.length > 0) {
    e.stopPropagation();
    _beginHandleDrag(e, handleHits[0].object);
    return;
  }

  // Fill mesh
  const fillHits = _raycaster.intersectObjects(_getFillObjects());
  if (fillHits.length > 0) {
    e.stopPropagation();
    _beginRoomMove(e, fillHits[0].object);
  }
});

canvas.addEventListener("pointermove", (e) => {
  if (_drag) {
    if (_drag.mode === "vertex") _updateVertexDrag(e);
    else if (_drag.mode === "move") _updateRoomMove(e);
    else _updateHandleDrag(e);
    return;
  }

  _updatePointer(e);
  _raycaster.setFromCamera(_pointer, camera);
  const handleObjs = _getHandleObjects();
  const vertexObjs = _getVertexHandleObjects();

  // Reset colours
  handleObjs.forEach((h) => {
    const r  = _roomById(h.userData.roomId);
    const fi = h.userData.faceIndex;
    const fsi = _faceStyleIdx(r, fi);
    const fs = r?.face_styles?.[fsi] ?? r?.stylename;
    h.material.color.setHex(fs !== r?.stylename ? HANDLE_STYLED_COLOR : HANDLE_COLOR);
  });
  vertexObjs.forEach(h => h.material.color.setHex(VERTEX_HANDLE_COLOR));

  const hits = _raycaster.intersectObjects([...handleObjs, ...vertexObjs]);
  if (hits.length > 0) {
    hits[0].object.material.color.setHex(HANDLE_HOVER_COLOR);
    canvas.style.cursor = "crosshair";
  } else {
    const fillHits = _raycaster.intersectObjects(_getFillObjects());
    canvas.style.cursor = fillHits.length > 0 ? "grab" : "default";
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
      // Vertex handle drag — no click action
    } else if (mode === "face" && isClick && handleMesh) {
      _selectFace(handleMesh);
    } else if (mode === "move" && isClick) {
      _setSelected(room);
    }
    return;
  }

  if (!_pointerDownPos) return;
  const dx = e.clientX - _pointerDownPos.x;
  const dy = e.clientY - _pointerDownPos.y;
  if (Math.hypot(dx, dy) > 4) return;

  _updatePointer(e);
  _raycaster.setFromCamera(_pointer, camera);
  if (_raycaster.intersectObjects(_getFillObjects()).length === 0) _setSelected(null);
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
  if (e.key === "t" || e.key === "T") document.getElementById("btn-top-view")?.click();
  if ((e.key === "Delete" || e.key === "Backspace") && _selected) deleteRoom(_selected);
});

// ---------------------------------------------------------------------------
// Resize / render loop
// ---------------------------------------------------------------------------
function _resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (renderer.domElement.width !== w || renderer.domElement.height !== h) {
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
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
  _rooms = [];
  _nextId = 1;
  _setSelected(null);

  for (const r of data.rooms) {
    const stylename = r.stylename || "default";
    if (r.type === "polygon" || r.vertices) {
      const n = r.vertices.length;
      const room = {
        id:            `r${_nextId++}`,
        type:          "polygon",
        vertices:      r.vertices.map(v => [...v]),
        elevation:     r.elevation ?? 0,
        height:        r.height    ?? DEFAULT_H,
        stylename,
        face_styles:   r.face_styles || Array(n + 2).fill(stylename),
        usage:         r.usage || "living",
        _group:        null,
        _handles:      [],
        _vertexHandles: [],
      };
      _rooms.push(room);
      _makePolygonRoomGroup(room);
    } else {
      const room = {
        id:            `r${_nextId++}`,
        position:      (r.position || [0, 0, 0]).slice(0, 3),
        size:          (r.size || [DEFAULT_W, DEFAULT_D, DEFAULT_H]).slice(0, 3),
        stylename,
        face_styles:   r.face_styles || Array(6).fill(stylename),
        usage:         r.usage || "living",
        _group:        null,
        _handles:      [],
        _vertexHandles: [],
      };
      _rooms.push(room);
      _makeRoomGroup(room);
    }
  }
  if (_rooms.length > 0) _setSelected(_rooms[0]);
  _emitEdit();
};

// Seed rooms (overridden by regenerate.js if localStorage has a saved layout)
addRoom({ position: [0, 0, 0], size: [4, 4, 3], usage: "living",  stylename: "default" });
addRoom({ position: [4, 0, 0], size: [3, 3, 3], usage: "bedroom", stylename: "default" });
