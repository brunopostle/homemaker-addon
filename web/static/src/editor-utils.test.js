import { describe, it, expect } from "vitest";
import {
    snapToFaces,
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
