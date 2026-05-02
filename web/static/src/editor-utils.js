/**
 * editor-utils.js — pure geometry helpers for the cuboid editor.
 *
 * No DOM or Three.js dependencies; all functions are deterministic given
 * their inputs so they can be unit-tested in Node via Vitest.
 */

// Three.js room geometry conventions:
//   position = [px, py, pz]  — corner in Three.js Y-up space
//   size     = [w,  d,  h]   — width(X), depth(Z), height(Y)
//
// SIZE_AXES maps world axis index → size array index:
//   axis 0 (X) → size[0] = w
//   axis 1 (Y) → size[2] = h
//   axis 2 (Z) → size[1] = d
export const SIZE_AXES = [0, 2, 1];

export const SNAP_THRESHOLD = 0.15;  // metres — face-snap engagement distance
export const GRID_SNAP      = 0.1;   // metres — coarse grid for free dragging
export const MIN_DIM        = 0.3;   // metres — minimum room dimension

/**
 * Snap worldCoord (along axis) to the near or far face of any room
 * in rooms except draggedRoom, within SNAP_THRESHOLD.
 * Returns the snapped coordinate, or worldCoord unchanged if no snap.
 */
export function snapToFaces(worldCoord, axis, rooms, draggedRoom) {
    for (const room of rooms) {
        if (room === draggedRoom) continue;
        const lo = room.position[axis];
        const hi = room.position[axis] + room.size[SIZE_AXES[axis]];
        if (Math.abs(worldCoord - lo) < SNAP_THRESHOLD) return lo;
        if (Math.abs(worldCoord - hi) < SNAP_THRESHOLD) return hi;
    }
    return worldCoord;
}

/**
 * Compute new position and size after dragging a face to worldCoord.
 *
 * startPos / startSize are captured once at drag start and must not be
 * mutated — using startPos[axis] (not room.position[axis]) ensures the
 * opposite face stays fixed even across multiple mousemove frames.
 *
 * Returns { position, size } or null if the resulting dimension < MIN_DIM.
 */
export function computeFaceDrag(startPos, startSize, axis, sign, worldCoord) {
    const sizeIdx = SIZE_AXES[axis];
    const newPos  = [...startPos];
    const newSize = [...startSize];

    if (sign > 0) {
        // Moving the positive face: only size changes, position stays.
        const newDim = worldCoord - startPos[axis];
        if (newDim < MIN_DIM) return null;
        newSize[sizeIdx] = newDim;
    } else {
        // Moving the negative face: position moves, far face stays fixed.
        // Use startPos[axis] — NOT room.position[axis] — so the far face
        // does not drift across successive mousemove events.
        const farFace = startPos[axis] + startSize[sizeIdx];
        const newDim  = farFace - worldCoord;
        if (newDim < MIN_DIM) return null;
        newPos[axis]     = worldCoord;
        newSize[sizeIdx] = newDim;
    }

    return { position: newPos, size: newSize };
}
