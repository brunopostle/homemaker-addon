/**
 * fragment.js — encode/decode building layout as a #v1:BASE64URL URL fragment.
 *
 * Format:  #v1:<base64url of deflate-raw compressed compact JSON>
 *
 * Compact JSON schema:
 *   { v:1, s?:[non-default-styles], r:[...rooms] }
 *
 * Each room (object, defaults omitted):
 *   p  — flat vertex array [x1,z1, x2,z2, ...]  (required, coords rounded to 2dp)
 *   e  — elevation  (omit if 0)
 *   h  — height     (omit if 3)
 *   u  — usage char (omit if "l")  l b k c t s v o
 *   s  — style index (omit if 0)   0="default", n=compact.s[n-1]
 *   f  — face-style indices, trailing room-style entries trimmed (omit if all match)
 */

const DEFAULT_H = 3.0;

const USAGE_TO_CHAR = {
    living: "l", bedroom: "b", kitchen: "k", circulation: "c",
    toilet: "t", stair: "s", void: "v", outside: "o",
    retail: "r", sahn: "a",
};
const CHAR_TO_USAGE = Object.fromEntries(
    Object.entries(USAGE_TO_CHAR).map(([k, v]) => [v, k])
);

const r2 = n => Math.round(n * 100) / 100;

// ---------------------------------------------------------------------------
// Compact JSON  ↔  rooms[]
// ---------------------------------------------------------------------------

function _toCompact(rooms) {
    // Build style palette: unique non-"default" styles in encounter order.
    const palette = [];
    const styleIdx = name => {
        if (!name || name === "default") return 0;
        let i = palette.indexOf(name);
        if (i === -1) { i = palette.length; palette.push(name); }
        return i + 1;
    };
    // Pre-scan so palette order is stable regardless of field iteration order.
    for (const r of rooms) {
        styleIdx(r.stylename);
        for (const fs of (r.face_styles || [])) if (fs) styleIdx(fs);
    }

    const compact = { v: 1, r: [] };
    if (palette.length) compact.s = palette;

    for (const r of rooms) {
        const si = styleIdx(r.stylename);
        const entry = { p: r.vertices.flatMap(([x, z]) => [r2(x), r2(z)]) };

        if (r.elevation !== 0)                       entry.e = r2(r.elevation);
        if (Math.abs(r.height - DEFAULT_H) > 0.005) entry.h = r2(r.height);
        const uc = USAGE_TO_CHAR[r.usage || "living"];
        if (uc && uc !== "l")                        entry.u = uc;
        if (si !== 0)                                entry.s = si;

        // Face styles: omit if all match room style; trim trailing matches.
        if (r.face_styles) {
            const mapped = r.face_styles.map(fs => styleIdx(fs || r.stylename));
            if (!mapped.every(i => i === si)) {
                let end = mapped.length;
                while (end > 0 && mapped[end - 1] === si) end--;
                entry.f = mapped.slice(0, end);
            }
        }

        compact.r.push(entry);
    }
    return compact;
}

function _fromCompact(compact) {
    const palette = compact.s || [];
    const styleFromIdx = i => (i && palette[i - 1]) ? palette[i - 1] : "default";

    return (compact.r || []).map(entry => {
        const flat = entry.p || [];
        const vertices = [];
        for (let i = 0; i < flat.length - 1; i += 2) vertices.push([flat[i], flat[i + 1]]);
        if (vertices.length < 3) return null;

        const stylename = styleFromIdx(entry.s);
        const n = vertices.length;

        let face_styles = Array(n + 2).fill(stylename);
        if (entry.f) {
            for (let i = 0; i < entry.f.length && i < face_styles.length; i++) {
                face_styles[i] = styleFromIdx(entry.f[i]);
            }
        }

        return {
            vertices,
            elevation:   entry.e ?? 0,
            height:      entry.h ?? DEFAULT_H,
            usage:       CHAR_TO_USAGE[entry.u || "l"] || "living",
            stylename,
            face_styles,
        };
    }).filter(Boolean);
}

// ---------------------------------------------------------------------------
// Compression / Base64URL
// ---------------------------------------------------------------------------

async function _deflate(str) {
    const bytes = new TextEncoder().encode(str);
    const cs = new CompressionStream("deflate-raw");
    const writer = cs.writable.getWriter();
    writer.write(bytes);
    writer.close();
    const chunks = [];
    const reader = cs.readable.getReader();
    for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
    }
    const out = new Uint8Array(chunks.reduce((n, c) => n + c.length, 0));
    let off = 0;
    for (const c of chunks) { out.set(c, off); off += c.length; }
    return out;
}

async function _inflate(bytes) {
    const ds = new DecompressionStream("deflate-raw");
    const writer = ds.writable.getWriter();
    writer.write(bytes);
    writer.close();
    const chunks = [];
    const reader = ds.readable.getReader();
    for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
    }
    const out = new Uint8Array(chunks.reduce((n, c) => n + c.length, 0));
    let off = 0;
    for (const c of chunks) { out.set(c, off); off += c.length; }
    return new TextDecoder().decode(out);
}

function _toBase64Url(bytes) {
    let bin = "";
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function _fromBase64Url(str) {
    const bin = atob(str.replace(/-/g, "+").replace(/_/g, "/"));
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Encode a rooms array → "#v1:…" fragment string. */
export async function encodeFragment(rooms) {
    const json = JSON.stringify(_toCompact(rooms));
    const compressed = await _deflate(json);
    return "v1:" + _toBase64Url(compressed);
}

/**
 * Decode a fragment string (with or without leading "#") → rooms array,
 * or null if the fragment is absent, unrecognised, or corrupt.
 */
export async function decodeFragment(fragment) {
    const s = fragment?.startsWith("#") ? fragment.slice(1) : fragment;
    if (!s?.startsWith("v1:")) return null;
    try {
        const bytes = _fromBase64Url(s.slice(3));
        const json  = await _inflate(bytes);
        return _fromCompact(JSON.parse(json));
    } catch (_) {
        return null;
    }
}
