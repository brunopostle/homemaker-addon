/**
 * editor-utils.js — pure geometry helpers for the quad-cell editor.
 *
 * All cells share a single data model:
 *   vertices  — [[x,z], ...]  in Three.js XZ plane (3 or more vertices)
 *   elevation — Y position of the floor
 *   height    — room height (Y extent)
 *
 * Face indices used throughout:
 *   fi=0  floor
 *   fi=1  ceiling
 *   fi=2  wall 0 (edge: vertex 0 → 1)
 *   fi=3  wall 1 (edge: vertex 1 → 2)
 *   fi=4  wall 2 (edge: vertex 2 → 3)
 *   fi=5  wall 3 (edge: vertex 3 → 0)
 */

export const SNAP_THRESHOLD = 0.15;  // metres — snap engagement distance
export const GRID_SNAP      = 0.1;   // metres — coarse grid for free dragging
export const MIN_DIM        = 0.3;   // metres — minimum room dimension

/**
 * Snap worldY to the floor or ceiling of any room except draggedRoom,
 * within SNAP_THRESHOLD.
 * Returns the snapped Y coordinate, or worldY unchanged if no snap.
 */
export function snapToFaces(worldY, rooms, draggedRoom) {
    let bestDist = SNAP_THRESHOLD;
    let snapY = worldY;
    for (const room of rooms) {
        if (room === draggedRoom) continue;
        const lo = room.elevation;
        const hi = room.elevation + room.height;
        const dlo = Math.abs(worldY - lo);
        const dhi = Math.abs(worldY - hi);
        if (dlo < bestDist) { bestDist = dlo; snapY = lo; }
        if (dhi < bestDist) { bestDist = dhi; snapY = hi; }
    }
    return snapY;
}

/**
 * Compute new elevation and height after dragging a floor (sign=-1) or
 * ceiling (sign=+1) face to worldY.
 *
 * startElevation / startHeight are captured once at drag-start — using them
 * (not the live room values) keeps the opposite face fixed across frames.
 *
 * Returns { elevation, height } or null if the new dimension < MIN_DIM.
 */
export function computeFaceDrag(startElevation, startHeight, sign, worldY) {
    if (sign > 0) {
        // Ceiling: floor stays, height changes.
        const newHeight = worldY - startElevation;
        if (newHeight < MIN_DIM) return null;
        return { elevation: startElevation, height: newHeight };
    } else {
        // Floor: ceiling stays fixed, floor moves.
        const ceiling = startElevation + startHeight;
        const newHeight = ceiling - worldY;
        if (newHeight < MIN_DIM) return null;
        return { elevation: worldY, height: newHeight };
    }
}

/**
 * Wall planes of a cell as { nx, nz, d } where nx*x + nz*z + d = 0
 * and (nx, nz) is a unit outward normal.
 */
function _wallPlanesOf(room) {
    const verts = room.vertices;
    const n = verts.length;
    const planes = [];
    for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        const [x1, z1] = verts[i];
        const [x2, z2] = verts[j];
        const dx = x2 - x1, dz = z2 - z1;
        const len = Math.sqrt(dx * dx + dz * dz);
        if (len < 0.001) continue;
        const nx = -dz / len, nz = dx / len;
        planes.push({ nx, nz, d: -(nx * x1 + nz * z1) });
    }
    return planes;
}

/**
 * Snap a vertex at (vx, vz) to the nearest corner vertex of any room except
 * draggedRoom, within SNAP_THRESHOLD.
 * Returns { x, z, snapRoom, snapWallIdx } — snapRoom is null if no snap fired.
 * snapWallIdx is the outgoing edge from the snapped vertex (for highlight).
 */
export function snapVertexToVertices(vx, vz, rooms, draggedRoom) {
    let bestDist = SNAP_THRESHOLD;
    let snapX = vx, snapZ = vz;
    let snapRoom = null, snapWallIdx = -1;
    for (const room of rooms) {
        if (room === draggedRoom) continue;
        for (let vi = 0; vi < room.vertices.length; vi++) {
            const [rx, rz] = room.vertices[vi];
            const dist = Math.sqrt((vx - rx) ** 2 + (vz - rz) ** 2);
            if (dist < bestDist) {
                bestDist = dist;
                snapX = rx;
                snapZ = rz;
                snapRoom = room;
                snapWallIdx = vi;
            }
        }
    }
    return { x: snapX, z: snapZ, snapRoom, snapWallIdx };
}

/**
 * Snap a vertex at (vx, vz) to the nearest wall plane of any room except
 * draggedRoom, within SNAP_THRESHOLD.
 * Returns { x, z, snapRoom, snapWallIdx } — snapRoom is null if no snap fired.
 */
export function snapVertexToWallPlanes(vx, vz, rooms, draggedRoom) {
    let bestDist = Infinity;
    let snapX = vx, snapZ = vz;
    let snapRoom = null, snapWallIdx = -1;
    for (const room of rooms) {
        if (room === draggedRoom) continue;
        const planes = _wallPlanesOf(room);
        for (let wi = 0; wi < planes.length; wi++) {
            const plane = planes[wi];
            const dist = plane.nx * vx + plane.nz * vz + plane.d;
            if (Math.abs(dist) < SNAP_THRESHOLD && Math.abs(dist) < bestDist) {
                bestDist = Math.abs(dist);
                snapX = vx - dist * plane.nx;
                snapZ = vz - dist * plane.nz;
                snapRoom = room;
                snapWallIdx = wi;
            }
        }
    }
    return { x: snapX, z: snapZ, snapRoom, snapWallIdx };
}
