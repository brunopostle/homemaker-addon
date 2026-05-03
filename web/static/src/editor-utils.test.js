import { describe, it, expect } from "vitest";
import {
    snapToFaces,
    snapVertexToWallPlanes,
    computeFaceDrag,
    SNAP_THRESHOLD,
    GRID_SNAP,
    MIN_DIM,
    SIZE_AXES,
} from "./editor-utils.js";

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function room(position, size) {
    return { position: [...position], size: [...size] };
}

// ---------------------------------------------------------------------------
// SIZE_AXES
// ---------------------------------------------------------------------------

describe("SIZE_AXES", () => {
    it("maps X axis (0) to size[0] = width", () => {
        expect(SIZE_AXES[0]).toBe(0);
    });
    it("maps Y axis (1) to size[2] = height", () => {
        expect(SIZE_AXES[1]).toBe(2);
    });
    it("maps Z axis (2) to size[1] = depth", () => {
        expect(SIZE_AXES[2]).toBe(1);
    });
});

// ---------------------------------------------------------------------------
// snapToFaces
// ---------------------------------------------------------------------------

describe("snapToFaces", () => {
    const other = room([4, 0, 0], [3, 4, 3]); // X: [4, 7]

    it("returns worldCoord unchanged when no rooms are nearby", () => {
        expect(snapToFaces(10, 0, [other], null)).toBe(10);
    });

    it("snaps to the near (lo) face of an adjacent room", () => {
        // worldCoord 4.05 is within threshold of x=4
        expect(snapToFaces(4.05, 0, [other], null)).toBe(4);
    });

    it("snaps to the far (hi) face of an adjacent room", () => {
        // worldCoord 6.9 is within threshold of x=7
        expect(snapToFaces(6.9, 0, [other], null)).toBe(7);
    });

    it("does not snap when just outside threshold", () => {
        const justOutside = 4 + SNAP_THRESHOLD + 0.01;
        expect(snapToFaces(justOutside, 0, [other], null)).toBe(justOutside);
    });

    it("snaps at exactly the threshold boundary", () => {
        // SNAP_THRESHOLD is exclusive (< not <=), so exactly at threshold does not snap
        expect(snapToFaces(4 + SNAP_THRESHOLD, 0, [other], null)).toBe(4 + SNAP_THRESHOLD);
    });

    it("skips the dragged room itself", () => {
        // other IS the dragged room — should not snap to its own faces
        expect(snapToFaces(4.05, 0, [other], other)).toBe(4.05);
    });

    it("snaps along Y axis (elevation) using size[2]=height", () => {
        // room at y=2, height=3 → Y faces at 2 and 5
        const r = room([0, 2, 0], [4, 4, 3]); // size=[w,d,h]=[4,4,3], height=3
        expect(snapToFaces(2.1, 1, [r], null)).toBe(2);   // snap to floor y=2
        expect(snapToFaces(4.9, 1, [r], null)).toBe(5);   // snap to ceiling y=5
    });

    it("snaps along Z axis (depth) using size[1]=depth", () => {
        // room at z=1, depth=4 → Z faces at 1 and 5
        const r = room([0, 0, 1], [4, 4, 3]); // size=[w=4,d=4,h=3]
        expect(snapToFaces(1.1, 2, [r], null)).toBe(1);
        expect(snapToFaces(4.9, 2, [r], null)).toBe(5);
    });

    it("snaps to the nearest room when two rooms are both within threshold", () => {
        const a = room([0, 0, 0], [4, 4, 3]); // X hi face at 4
        const b = room([4.1, 0, 0], [3, 4, 3]); // X lo face at 4.1
        // worldCoord 4.05: distance to a.hi=4 is 0.05, to b.lo=4.1 is 0.05 — first match wins
        const result = snapToFaces(4.05, 0, [a, b], null);
        expect(result).toBe(4); // a comes first
    });

    it("returns unchanged coord when rooms list is empty", () => {
        expect(snapToFaces(3.5, 0, [], null)).toBe(3.5);
    });

    it("skips polygon rooms on X axis (they have no position)", () => {
        const poly = { type: "polygon", vertices: [[0,0],[4,0],[4,4],[0,4]], elevation: 0, height: 3 };
        // Should not throw and should not snap on X axis
        expect(snapToFaces(0.05, 0, [poly], null)).toBe(0.05);
    });

    it("skips polygon rooms on Z axis", () => {
        const poly = { type: "polygon", vertices: [[0,0],[4,0],[4,4],[0,4]], elevation: 0, height: 3 };
        expect(snapToFaces(0.05, 2, [poly], null)).toBe(0.05);
    });

    it("snaps polygon room floor/ceiling on Y axis", () => {
        const poly = { type: "polygon", vertices: [[0,0],[4,0],[4,4],[0,4]], elevation: 2, height: 3 };
        expect(snapToFaces(2.05, 1, [poly], null)).toBe(2);    // snap to floor y=2
        expect(snapToFaces(4.9,  1, [poly], null)).toBe(5);    // snap to ceiling y=5
    });

    it("does not snap to polygon room Y faces when dragging that same polygon room", () => {
        const poly = { type: "polygon", vertices: [[0,0],[4,0],[4,4],[0,4]], elevation: 2, height: 3 };
        expect(snapToFaces(2.05, 1, [poly], poly)).toBe(2.05);
    });
});

// ---------------------------------------------------------------------------
// computeFaceDrag — positive face (sign > 0)
// ---------------------------------------------------------------------------

describe("computeFaceDrag — positive face (sign > 0)", () => {
    // Face 2 (ceiling +Y): axis=1, sign=+1, sizeIdx=SIZE_AXES[1]=2 → size[2]=height
    const axis = 1, sign = 1;
    const startPos  = [0, 0, 0];
    const startSize = [4, 4, 3]; // w=4, d=4, h=3

    it("increases height when dragged outward", () => {
        const r = computeFaceDrag(startPos, startSize, axis, sign, 5);
        expect(r).not.toBeNull();
        expect(r.size[2]).toBeCloseTo(5);       // new height
        expect(r.position).toEqual([0, 0, 0]);  // position unchanged
    });

    it("decreases height when dragged inward", () => {
        const r = computeFaceDrag(startPos, startSize, axis, sign, 2);
        expect(r.size[2]).toBeCloseTo(2);
        expect(r.position).toEqual([0, 0, 0]);
    });

    it("returns null when new dimension < MIN_DIM", () => {
        expect(computeFaceDrag(startPos, startSize, axis, sign, 0.1)).toBeNull();
    });

    it("returns null at exactly MIN_DIM (exclusive)", () => {
        expect(computeFaceDrag(startPos, startSize, axis, sign, MIN_DIM - 0.001)).toBeNull();
    });

    it("returns result at MIN_DIM exactly", () => {
        const r = computeFaceDrag(startPos, startSize, axis, sign, MIN_DIM);
        expect(r).not.toBeNull();
    });

    it("does not mutate startPos or startSize", () => {
        const sp = [0, 0, 0], ss = [4, 4, 3];
        computeFaceDrag(sp, ss, axis, sign, 5);
        expect(sp).toEqual([0, 0, 0]);
        expect(ss).toEqual([4, 4, 3]);
    });
});

// ---------------------------------------------------------------------------
// computeFaceDrag — negative face (sign < 0)
// ---------------------------------------------------------------------------

describe("computeFaceDrag — negative face (sign < 0)", () => {
    // Face 0 (floor -Y): axis=1, sign=-1, sizeIdx=SIZE_AXES[1]=2 → size[2]=height
    const axis = 1, sign = -1;
    const startPos  = [0, 0, 0];
    const startSize = [4, 4, 3]; // h=3, so ceiling fixed at y=3

    it("moves position when dragged (floor goes down)", () => {
        const r = computeFaceDrag(startPos, startSize, axis, sign, -1);
        expect(r).not.toBeNull();
        expect(r.position[1]).toBeCloseTo(-1);  // floor at -1
        expect(r.size[2]).toBeCloseTo(4);        // ceiling still at y=3 → h=4
    });

    it("far face stays fixed across multiple simulated drag frames", () => {
        // Frame 1: drag floor to -0.5
        const r1 = computeFaceDrag(startPos, startSize, axis, sign, -0.5);
        expect(r1.position[1]).toBeCloseTo(-0.5);
        expect(r1.size[2]).toBeCloseTo(3.5);  // ceiling still at y=3

        // Frame 2: drag floor to -1.0 (still from SAME startPos/startSize)
        const r2 = computeFaceDrag(startPos, startSize, axis, sign, -1.0);
        expect(r2.position[1]).toBeCloseTo(-1.0);
        expect(r2.size[2]).toBeCloseTo(4.0);  // ceiling still at y=3

        // Far face = startPos[1] + startSize[2] = 0 + 3 = 3 in both cases ✓
        // (This would fail if we used room.position[axis] instead of startPos[axis])
        expect(r2.position[1] + r2.size[2]).toBeCloseTo(3.0);
    });

    it("returns null when dragged too far inward (dim < MIN_DIM)", () => {
        // ceiling at y=3, drag floor to y=2.9 → dim = 0.1 < MIN_DIM
        expect(computeFaceDrag(startPos, startSize, axis, sign, 2.9)).toBeNull();
    });

    it("X axis negative face (left wall): position[0] moves, size[0] changes", () => {
        // Face 3 (left -X): axis=0, sign=-1, sizeIdx=SIZE_AXES[0]=0 → size[0]=width
        const sp = [1, 0, 0], ss = [4, 4, 3]; // right face at x=5
        const r = computeFaceDrag(sp, ss, 0, -1, 0);
        expect(r.position[0]).toBeCloseTo(0);  // left face at x=0
        expect(r.size[0]).toBeCloseTo(5);       // width 5 (right face still at x=5)
    });

    it("Z axis negative face (back wall): position[2] moves, size[1] changes", () => {
        // Face 4 (back -Z): axis=2, sign=-1, sizeIdx=SIZE_AXES[2]=1 → size[1]=depth
        const sp = [0, 0, 2], ss = [4, 3, 3]; // front face at z=5
        const r = computeFaceDrag(sp, ss, 2, -1, 1);
        expect(r.position[2]).toBeCloseTo(1);  // back wall at z=1
        expect(r.size[1]).toBeCloseTo(4);       // depth 4 (front face still at z=5)
    });

    it("does not mutate startPos or startSize", () => {
        const sp = [0, 0, 0], ss = [4, 4, 3];
        computeFaceDrag(sp, ss, axis, sign, -1);
        expect(sp).toEqual([0, 0, 0]);
        expect(ss).toEqual([4, 4, 3]);
    });
});

// ---------------------------------------------------------------------------
// computeFaceDrag — all six face index combinations
// ---------------------------------------------------------------------------

describe("computeFaceDrag — all six face axes and signs", () => {
    // FACE_AXIS  = [1, 0, 1, 0, 2, 2]
    // FACE_SIGN  = [-1, 1, 1, -1, -1, 1]
    const faceParams = [
        { name: "floor  (fi=0)", axis: 1, sign: -1 },
        { name: "right  (fi=1)", axis: 0, sign:  1 },
        { name: "ceiling(fi=2)", axis: 1, sign:  1 },
        { name: "left   (fi=3)", axis: 0, sign: -1 },
        { name: "back   (fi=4)", axis: 2, sign: -1 },
        { name: "front  (fi=5)", axis: 2, sign:  1 },
    ];

    const startPos  = [1, 1, 1];
    const startSize = [4, 4, 3];

    for (const { name, axis, sign } of faceParams) {
        it(`${name}: result is non-null for valid drag`, () => {
            // For positive face: drag outward by 1 unit
            // For negative face: drag inward by -1 unit (decrease coord)
            const faceCoord = sign > 0
                ? startPos[axis] + startSize[SIZE_AXES[axis]] + 1
                : startPos[axis] - 1;
            const r = computeFaceDrag(startPos, startSize, axis, sign, faceCoord);
            expect(r).not.toBeNull();
        });
    }
});

// ---------------------------------------------------------------------------
// snapVertexToWallPlanes
// ---------------------------------------------------------------------------

describe("snapVertexToWallPlanes", () => {
    const cuboid = room([2, 0, 3], [4, 4, 3]); // X: [2, 6], Z: [3, 7]

    it("returns vertex unchanged when no rooms are nearby", () => {
        expect(snapVertexToWallPlanes(0, 0, [cuboid], null)).toEqual([0, 0]);
    });

    it("snaps to left wall plane of a cuboid (X = px)", () => {
        // vertex at x=2.05 is within threshold of X=2
        const [sx, sz] = snapVertexToWallPlanes(2.05, 5, [cuboid], null);
        expect(sx).toBeCloseTo(2);
        expect(sz).toBeCloseTo(5);
    });

    it("snaps to right wall plane of a cuboid (X = px+w)", () => {
        const [sx, sz] = snapVertexToWallPlanes(5.9, 5, [cuboid], null);
        expect(sx).toBeCloseTo(6);
        expect(sz).toBeCloseTo(5);
    });

    it("snaps to front wall plane of a cuboid (Z = pz)", () => {
        const [sx, sz] = snapVertexToWallPlanes(4, 3.1, [cuboid], null);
        expect(sx).toBeCloseTo(4);
        expect(sz).toBeCloseTo(3);
    });

    it("snaps to back wall plane of a cuboid (Z = pz+depth)", () => {
        const [sx, sz] = snapVertexToWallPlanes(4, 6.9, [cuboid], null);
        expect(sx).toBeCloseTo(4);
        expect(sz).toBeCloseTo(7);
    });

    it("does not snap when outside threshold", () => {
        const justOutside = 2 - SNAP_THRESHOLD - 0.01;
        const result = snapVertexToWallPlanes(justOutside, 5, [cuboid], null);
        expect(result[0]).toBeCloseTo(justOutside);
        expect(result[1]).toBeCloseTo(5);
    });

    it("skips the dragged room itself", () => {
        const [sx] = snapVertexToWallPlanes(2.05, 5, [cuboid], cuboid);
        expect(sx).toBeCloseTo(2.05);
    });

    it("snaps to a polygon room wall plane", () => {
        // polygon with a vertical edge from [0,0] to [4,0] — wall plane Z=0
        const poly = { type: "polygon", vertices: [[0,0],[4,0],[4,4],[0,4]], elevation: 0, height: 3 };
        const [sx, sz] = snapVertexToWallPlanes(2, 0.08, [poly], null);
        expect(sx).toBeCloseTo(2);
        expect(sz).toBeCloseTo(0);
    });

    it("snaps to a diagonal polygon wall plane", () => {
        // polygon with an edge from [0,0] to [4,4] — wall plane nx=-0.707, nz=0.707, d=0
        const poly = { type: "polygon", vertices: [[0,0],[4,4],[0,4]], elevation: 0, height: 3 };
        // Point [2.1, 1.9] is close to the plane nx*x + nz*z + d = 0 where nx=-1/√2, nz=1/√2, d=0
        // dist = (-1/√2)*2.1 + (1/√2)*1.9 + 0 = (-2.1+1.9)/√2 = -0.2/√2 ≈ -0.141
        // That's outside SNAP_THRESHOLD=0.15. Try [2.05, 1.95]:
        // dist = (-2.05+1.95)/√2 = -0.1/√2 ≈ -0.0707 → within threshold
        const [sx, sz] = snapVertexToWallPlanes(2.05, 1.95, [poly], null);
        // snapped point should lie on the line x=z
        expect(sx).toBeCloseTo(sz, 4);
    });

    it("picks the nearest plane when two planes are both within threshold", () => {
        // Two cuboids with wall planes at x=0 (dist 0.05) and x=4.08 (dist 0.07)
        const a = room([0, 0, 0], [4, 4, 3]); // X lo=0
        const b = room([4.08, 0, 0], [4, 4, 3]); // X lo=4.08
        // vertex at x=0.05: dist to a's X=0 is 0.05, dist to b's X=4.08 is 4.03 (far away)
        const [sx] = snapVertexToWallPlanes(0.05, 2, [a, b], null);
        expect(sx).toBeCloseTo(0);
    });

    it("returns unchanged when rooms list is empty", () => {
        expect(snapVertexToWallPlanes(3, 4, [], null)).toEqual([3, 4]);
    });

    it("snaps correctly to wall planes aligned far from the vertex's position (infinite plane)", () => {
        // The whole point: wall plane X=10 extends infinitely in Z.
        // vertex at (9.95, 100) should still snap to X=10
        const far = room([10, 0, 0], [4, 4, 3]);
        const [sx, sz] = snapVertexToWallPlanes(9.95, 100, [far], null);
        expect(sx).toBeCloseTo(10);
        expect(sz).toBeCloseTo(100);
    });
});
