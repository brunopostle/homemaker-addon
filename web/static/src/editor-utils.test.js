import { describe, it, expect } from "vitest";
import {
    snapToFaces,
    snapVertexToWallPlanes,
    computeFaceDrag,
    SNAP_THRESHOLD,
    GRID_SNAP,
    MIN_DIM,
} from "./editor-utils.js";

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

/** Build a minimal quad room (rectangle) for testing. */
function rect(px, pz, w, d, elevation = 0, height = 3) {
    return {
        vertices:  [[px, pz], [px + w, pz], [px + w, pz + d], [px, pz + d]],
        elevation,
        height,
    };
}

// ---------------------------------------------------------------------------
// snapToFaces  (Y-axis only — floor and ceiling snap)
// ---------------------------------------------------------------------------

describe("snapToFaces", () => {
    const other = rect(0, 0, 4, 4, 2, 3);  // elevation=2, height=3 → floor=2, ceiling=5

    it("returns worldY unchanged when no rooms are nearby", () => {
        expect(snapToFaces(0, [other], null)).toBe(0);
    });

    it("snaps to the floor of an adjacent room", () => {
        expect(snapToFaces(2.05, [other], null)).toBe(2);
    });

    it("snaps to the ceiling of an adjacent room", () => {
        expect(snapToFaces(4.9, [other], null)).toBe(5);
    });

    it("does not snap when just outside threshold", () => {
        const justOutside = 2 + SNAP_THRESHOLD + 0.01;
        expect(snapToFaces(justOutside, [other], null)).toBe(justOutside);
    });

    it("does not snap when clearly outside threshold", () => {
        const outside = 2 + SNAP_THRESHOLD * 2;
        expect(snapToFaces(outside, [other], null)).toBe(outside);
    });

    it("skips the dragged room itself", () => {
        expect(snapToFaces(2.05, [other], other)).toBe(2.05);
    });

    it("returns unchanged when rooms list is empty", () => {
        expect(snapToFaces(3.5, [], null)).toBe(3.5);
    });

    it("snaps to nearest face when two are within threshold", () => {
        const a = rect(0, 0, 4, 4, 0, 3);    // floor at y=0   (dist 0.08)
        const b = rect(0, 0, 4, 4, 0.05, 3); // floor at y=0.05 (dist 0.03)
        // y=0.08 is within threshold of both; b's floor is closer
        const result = snapToFaces(0.08, [a, b], null);
        expect(result).toBe(0.05);
    });
});

// ---------------------------------------------------------------------------
// computeFaceDrag — ceiling (sign > 0)
// ---------------------------------------------------------------------------

describe("computeFaceDrag — ceiling (sign > 0)", () => {
    it("increases height when ceiling dragged up", () => {
        const r = computeFaceDrag(0, 3, 1, 5);
        expect(r).not.toBeNull();
        expect(r.elevation).toBe(0);
        expect(r.height).toBeCloseTo(5);
    });

    it("decreases height when ceiling dragged down", () => {
        const r = computeFaceDrag(0, 3, 1, 2);
        expect(r.elevation).toBe(0);
        expect(r.height).toBeCloseTo(2);
    });

    it("returns null when new height < MIN_DIM", () => {
        expect(computeFaceDrag(0, 3, 1, 0.1)).toBeNull();
    });

    it("returns null at just below MIN_DIM (exclusive)", () => {
        expect(computeFaceDrag(0, 3, 1, MIN_DIM - 0.001)).toBeNull();
    });

    it("returns result at exactly MIN_DIM", () => {
        const r = computeFaceDrag(0, 3, 1, MIN_DIM);
        expect(r).not.toBeNull();
        expect(r.height).toBeCloseTo(MIN_DIM);
    });

    it("works correctly when floor is not at y=0", () => {
        const r = computeFaceDrag(2, 3, 1, 7);   // floor=2, ceiling dragged to y=7
        expect(r.elevation).toBe(2);
        expect(r.height).toBeCloseTo(5);
    });
});

// ---------------------------------------------------------------------------
// computeFaceDrag — floor (sign < 0)
// ---------------------------------------------------------------------------

describe("computeFaceDrag — floor (sign < 0)", () => {
    it("moves floor down, ceiling stays fixed", () => {
        const r = computeFaceDrag(0, 3, -1, -1);
        expect(r).not.toBeNull();
        expect(r.elevation).toBeCloseTo(-1);
        expect(r.height).toBeCloseTo(4);    // ceiling still at y=3
    });

    it("ceiling stays fixed across multiple simulated drag frames", () => {
        const ceiling = 0 + 3;  // startElevation + startHeight
        const r1 = computeFaceDrag(0, 3, -1, -0.5);
        expect(r1.elevation + r1.height).toBeCloseTo(ceiling);

        const r2 = computeFaceDrag(0, 3, -1, -1.0);
        expect(r2.elevation + r2.height).toBeCloseTo(ceiling);
    });

    it("returns null when floor dragged too close to ceiling (dim < MIN_DIM)", () => {
        // ceiling=3, drag floor to 2.9 → height=0.1 < MIN_DIM
        expect(computeFaceDrag(0, 3, -1, 2.9)).toBeNull();
    });

    it("returns result when floor is dragged to a valid position", () => {
        // ceiling = 3, drag floor down to y=0.5 → height=2.5 ≥ MIN_DIM
        const r = computeFaceDrag(0, 3, -1, 0.5);
        expect(r).not.toBeNull();
        expect(r.height).toBeCloseTo(2.5);
    });

    it("works with non-zero start elevation", () => {
        // Floor starts at y=2, ceiling at y=5 (height=3). Drag floor to y=1.
        const r = computeFaceDrag(2, 3, -1, 1);
        expect(r.elevation).toBeCloseTo(1);
        expect(r.height).toBeCloseTo(4);    // ceiling still at y=5
        expect(r.elevation + r.height).toBeCloseTo(5);
    });
});

// ---------------------------------------------------------------------------
// snapVertexToWallPlanes
// ---------------------------------------------------------------------------

describe("snapVertexToWallPlanes", () => {
    // Rectangle at X:[2,6], Z:[3,7]
    const box = rect(2, 3, 4, 4);

    it("returns vertex unchanged when no rooms are nearby", () => {
        const [sx, sz] = snapVertexToWallPlanes(0, 0, [box], null);
        expect(sx).toBeCloseTo(0);
        expect(sz).toBeCloseTo(0);
    });

    it("snaps to the left wall plane (X = px)", () => {
        const [sx, sz] = snapVertexToWallPlanes(2.05, 5, [box], null);
        expect(sx).toBeCloseTo(2);
        expect(sz).toBeCloseTo(5);
    });

    it("snaps to the right wall plane (X = px+w)", () => {
        const [sx, sz] = snapVertexToWallPlanes(5.9, 5, [box], null);
        expect(sx).toBeCloseTo(6);
        expect(sz).toBeCloseTo(5);
    });

    it("snaps to the front wall plane (Z = pz)", () => {
        const [sx, sz] = snapVertexToWallPlanes(4, 3.1, [box], null);
        expect(sx).toBeCloseTo(4);
        expect(sz).toBeCloseTo(3);
    });

    it("snaps to the back wall plane (Z = pz+d)", () => {
        const [sx, sz] = snapVertexToWallPlanes(4, 6.9, [box], null);
        expect(sx).toBeCloseTo(4);
        expect(sz).toBeCloseTo(7);
    });

    it("does not snap when outside threshold", () => {
        const justOutside = 2 - SNAP_THRESHOLD - 0.01;
        const [sx, sz] = snapVertexToWallPlanes(justOutside, 5, [box], null);
        expect(sx).toBeCloseTo(justOutside);
        expect(sz).toBeCloseTo(5);
    });

    it("skips the dragged room itself", () => {
        const [sx] = snapVertexToWallPlanes(2.05, 5, [box], box);
        expect(sx).toBeCloseTo(2.05);
    });

    it("snaps to an axis-aligned wall of a non-rectangular quad room", () => {
        // L-shape approximated as a quad with one axis-aligned edge at Z=0
        const poly = { vertices: [[0,0],[4,0],[4,4],[0,4]], elevation: 0, height: 3 };
        const [sx, sz] = snapVertexToWallPlanes(2, 0.08, [poly], null);
        expect(sx).toBeCloseTo(2);
        expect(sz).toBeCloseTo(0);
    });

    it("snaps to a diagonal wall plane (infinite line)", () => {
        // quad with edge from [0,0] to [4,4]: plane normal = (-1/√2, 1/√2), d=0
        // point [2.05, 1.95]: dist = (-2.05+1.95)/√2 ≈ -0.071 → within threshold
        // snapped point should lie on the line x=z
        const poly = { vertices: [[0,0],[4,4],[0,4]], elevation: 0, height: 3 };
        const [sx, sz] = snapVertexToWallPlanes(2.05, 1.95, [poly], null);
        expect(sx).toBeCloseTo(sz, 4);
    });

    it("picks the nearest plane when two are within threshold", () => {
        const a = rect(0, 0, 4, 4);    // left wall at X=0 (dist 0.05 from x=0.05)
        const b = rect(4.08, 0, 4, 4); // left wall at X=4.08 (dist ~4 from x=0.05)
        const [sx] = snapVertexToWallPlanes(0.05, 2, [a, b], null);
        expect(sx).toBeCloseTo(0);
    });

    it("returns unchanged when rooms list is empty", () => {
        expect(snapVertexToWallPlanes(3, 4, [], null)).toEqual([3, 4]);
    });

    it("snaps to a wall plane far from the physical face (infinite plane behaviour)", () => {
        // Wall at X=10; vertex at (9.95, 100) — far in Z but still on the plane
        const far = rect(10, 0, 4, 4);
        const [sx, sz] = snapVertexToWallPlanes(9.95, 100, [far], null);
        expect(sx).toBeCloseTo(10);
        expect(sz).toBeCloseTo(100);
    });
});
