// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2024 Bruno Postle <bruno@postle.net>
import { describe, it, expect } from "vitest";
import { encodeFragment, decodeFragment } from "./fragment.js";

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function room(opts = {}) {
    const vertices = opts.vertices ?? [[0,0],[4,0],[4,4],[0,4]];
    const stylename = opts.stylename ?? "default";
    return {
        vertices,
        elevation:   opts.elevation  ?? 0,
        height:      opts.height     ?? 3,
        usage:       opts.usage      ?? "living",
        stylename,
        face_styles: opts.face_styles ?? Array(vertices.length + 2).fill(stylename),
    };
}

function approxRoom(a, b) {
    expect(a.elevation).toBeCloseTo(b.elevation, 2);
    expect(a.height).toBeCloseTo(b.height, 2);
    expect(a.usage).toBe(b.usage);
    expect(a.stylename).toBe(b.stylename);
    expect(a.vertices.length).toBe(b.vertices.length);
    for (let i = 0; i < a.vertices.length; i++) {
        expect(a.vertices[i][0]).toBeCloseTo(b.vertices[i][0], 2);
        expect(a.vertices[i][1]).toBeCloseTo(b.vertices[i][1], 2);
    }
    expect(a.face_styles).toEqual(b.face_styles);
}

// ---------------------------------------------------------------------------
// round-trip
// ---------------------------------------------------------------------------

describe("encodeFragment / decodeFragment round-trip", () => {
    it("encodes and decodes a single default room", async () => {
        const rooms = [room()];
        const frag  = await encodeFragment(rooms);
        const out   = await decodeFragment("#" + frag);
        expect(out).toHaveLength(1);
        approxRoom(out[0], rooms[0]);
    });

    it("handles two rooms with different usages", async () => {
        const rooms = [
            room({ usage: "living" }),
            room({ vertices: [[4,0],[7,0],[7,3],[4,3]], usage: "bedroom" }),
        ];
        const out = await decodeFragment("#" + await encodeFragment(rooms));
        expect(out).toHaveLength(2);
        expect(out[0].usage).toBe("living");
        expect(out[1].usage).toBe("bedroom");
    });

    it("preserves non-default elevation and height", async () => {
        const rooms = [room({ elevation: 3, height: 2.4 })];
        const out   = await decodeFragment("#" + await encodeFragment(rooms));
        expect(out[0].elevation).toBeCloseTo(3, 2);
        expect(out[0].height).toBeCloseTo(2.4, 2);
    });

    it("preserves non-default stylename", async () => {
        const rooms = [room({ stylename: "foxhouse",
                              face_styles: Array(6).fill("foxhouse") })];
        const out   = await decodeFragment("#" + await encodeFragment(rooms));
        expect(out[0].stylename).toBe("foxhouse");
    });

    it("preserves per-face styles", async () => {
        const fs = ["default","default","foxhouse","foxhouse","default","default"];
        const rooms = [room({ face_styles: fs })];
        const out   = await decodeFragment("#" + await encodeFragment(rooms));
        expect(out[0].face_styles).toEqual(fs);
    });

    it("round-trips all non-default usages", async () => {
        const usages = ["bedroom","kitchen","circulation","toilet","stair","void","outside","retail","sahn"];
        for (const u of usages) {
            const rooms = [room({ usage: u })];
            const out   = await decodeFragment("#" + await encodeFragment(rooms));
            expect(out[0].usage).toBe(u);
        }
    });

    it("round-trips coordinates rounded to 2dp", async () => {
        const rooms = [room({ vertices: [[1.123, 2.456],[5.789, 2.456],[5.789, 6.789],[1.123, 6.789]] })];
        const out   = await decodeFragment("#" + await encodeFragment(rooms));
        expect(out[0].vertices[0][0]).toBeCloseTo(1.12, 2);
        expect(out[0].vertices[0][1]).toBeCloseTo(2.46, 2);
    });

    it("handles fragment without leading #", async () => {
        const rooms = [room()];
        const frag  = await encodeFragment(rooms);
        const out   = await decodeFragment(frag);  // no "#" prefix
        expect(out).toHaveLength(1);
    });

    it("returns null for empty/absent fragment", async () => {
        expect(await decodeFragment("")).toBeNull();
        expect(await decodeFragment(null)).toBeNull();
        expect(await decodeFragment("#")).toBeNull();
    });

    it("returns null for unrecognised fragment version", async () => {
        expect(await decodeFragment("#v0:somejunk")).toBeNull();
    });

    it("returns null for corrupt base64", async () => {
        expect(await decodeFragment("#v1:!!!notbase64!!!")).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// compactness
// ---------------------------------------------------------------------------

describe("fragment length", () => {
    it("two-room building fits in 200 chars", async () => {
        const rooms = [
            room(),
            room({ vertices: [[4,0],[7,0],[7,3],[4,3]], usage: "bedroom" }),
        ];
        const frag = "#" + await encodeFragment(rooms);
        expect(frag.length).toBeLessThan(200);
    });

    it("fragment starts with #v1:", async () => {
        const frag = "#" + await encodeFragment([room()]);
        expect(frag.startsWith("#v1:")).toBe(true);
    });

    it("fragment contains only URL-safe chars after #", async () => {
        const frag = await encodeFragment([room()]);
        expect(frag).toMatch(/^v1:[A-Za-z0-9\-_]+$/);
    });
});
