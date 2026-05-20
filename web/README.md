# homemaker-web

A standalone web application for the [homemaker-addon](https://github.com/brunopostle/homemaker-addon) library.
Draw rooms in a 3D editor, assign styles and usages, and get a live IFC building model generated in the background.

## Overview

The application has two parts running in the same browser window:

1. **3D room editor** — create and reshape rooms as quadrilateral prisms (vertical walls, horizontal floor and ceiling).  The default shape is an axis-aligned rectangle, but any corner can be dragged to create non-orthogonal plans.  Each room has a usage (bedroom, kitchen, …) and each of its faces has a style (default, foxhouse, …).  The editor uses Three.js.

2. **IFC preview overlay** — the IFC model is regenerated on the server in the background and loaded into the same Three.js scene via `@thatopen/components`.  While you are editing the overlay is ghosted; when you stop it becomes solid.

The Python server wraps the homemaker library (`molior/`, `topologist/`) with a FastAPI HTTP API.  All topology and IFC work happens server-side; `topologic_core` (a C++ extension) is the only dependency that prevents running entirely in the browser.

## Quick start

### Docker (recommended)

Build from the **repository root** — the Dockerfile needs both `web/` and the library packages (`molior/`, `topologist/`, `share/`):

```bash
docker build -f web/Dockerfile -t homemaker-web .
docker run -p 8000:8000 homemaker-web
```

Open `http://localhost:8000`.

### Local development

```bash
# From the repository root:
pip install -e .
pip install -r requirements.txt
pip install -r web/requirements.txt

cd web
uvicorn server:app --reload --port 8000
```

`server.py` automatically adds the repository root to `sys.path`, so no install step is required for the library itself during development.

### Share directory

Styles are read from the `share/` directory at the repository root.  Override with an environment variable:

```bash
SHARE_DIR=/path/to/share uvicorn server:app ...
```

## Production deployment

This section covers deploying homemaker-web as a persistent service on a Linux server behind nginx with TLS.

### Prerequisites

`topologic_core` requires the OpenMP runtime library:

```bash
# Debian/Ubuntu
apt install -y libgomp1
```

### Install

Create a dedicated virtual environment and install from the git repository:

```bash
python3 -m venv /opt/homemaker-web
cd /tmp && git clone https://github.com/brunopostle/homemaker-addon.git
/opt/homemaker-web/bin/pip install -e /tmp/homemaker-addon
/opt/homemaker-web/bin/pip install \
    fastapi "uvicorn[standard]" python-multipart \
    topologic_core ifcopenshell numpy pyaml shapely

# Keep the clone — server.py and static/ are served from it:
mv /tmp/homemaker-addon /opt/homemaker-web/src
```

The `web/server.py` and `web/static/` frontend assets are served directly from the cloned repository.

### System user

Run the service as a dedicated unprivileged user:

```bash
adduser --system --shell /bin/false --group --no-create-home homemaker-web
```

### systemd service

Create `/etc/systemd/system/homemaker-web.service`:

```ini
[Unit]
Description=homemaker-web FastAPI service
After=network.target

[Service]
Type=simple
User=homemaker-web
Group=homemaker-web
WorkingDirectory=/opt/homemaker-web/src/web
ExecStart=/opt/homemaker-web/bin/uvicorn server:app \
    --host 127.0.0.1 \
    --port 8000
Restart=on-failure
RestartSec=5
TimeoutStopSec=60
Environment=SHARE_DIR=/opt/homemaker-web/src/share
NoNewPrivileges=yes
RestrictSUIDSGID=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictNamespaces=yes
LockPersonality=yes
RestrictRealtime=yes
RestrictAddressFamilies=AF_INET AF_INET6
SystemCallArchitectures=native
SystemCallFilter=@system-service @process @files @io-event @network-io
SystemCallErrorNumber=EPERM

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now homemaker-web
# Verify:
curl http://127.0.0.1:8000/health
# → {"status":"ok","share_dir":"/opt/homemaker-web/src/share"}
```

### nginx reverse proxy

IFC generation is CPU-bound and can take several seconds, so extend the proxy timeouts.  Replace `your-domain.com` with your actual hostname:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/your-domain.com /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### TLS certificate

Obtain a certificate with [Certbot](https://certbot.eff.org/) (create the nginx config first so certbot can find the `server_name` block):

```bash
certbot --nginx -d your-domain.com --non-interactive --agree-tos -m you@example.com
```

### Updates

```bash
cd /opt/homemaker-web/src
git pull
systemctl restart homemaker-web
```

### Resource requirements

`topologic_core` is pure CPU — no GPU required.  IFC generation runs in a `ProcessPoolExecutor` (2 worker processes) so it does not block the FastAPI event loop.  Idle memory usage is around 200 MB; peak under concurrent generation is around 400 MB.

## Using the editor

| Action | How |
|---|---|
| Add a room | **+ Room** button (toolbar) |
| Move a room horizontally | **Drag** the room body — snaps to wall planes of adjacent rooms |
| Move a room vertically | **Shift+drag** the room body — snaps to floor/ceiling of adjacent rooms |
| Select a room | **Click** the room body (short click without dragging) |
| Resize height | **Drag** the floor or ceiling handle (white sphere at plan centroid) |
| Reshape plan | **Drag** an orange corner handle to move that vertex |
| Set face style | **Click** any handle (without dragging) — a "Face style" row appears in the properties panel |
| Set room usage | Properties panel → Usage dropdown |
| Set room style | Properties panel → Style dropdown (resets all faces to that style) |
| Undo | **Ctrl+Z** |
| Redo | **Ctrl+Shift+Z** or **Ctrl+Y** |
| Orbit camera | Right-drag or two-finger drag |
| Zoom | Scroll wheel |
| Top-down view | **T** key or **Top** button |
| Delete room | **Delete** / **Backspace** with room selected, or "Delete room" button |
| Save layout | **Save** button — downloads `rooms.json` |
| Load layout | **Load** button — restores from a previously saved `rooms.json` |
| Force regeneration | **Generate IFC** button |
| Download the IFC file | **Download IFC** button (enabled after first successful generation) |

The layout is also **autosaved** to `localStorage` on every edit, so the browser restores your last session automatically on reload.

### Style vs usage

**Usage** is a property of the *cell* (room).  It tells homemaker what kind of space this is: `bedroom`, `kitchen`, `living`, `circulation`, `toilet`, `stair`, `void`, `outside`.  Set it per room in the properties panel.

**Stylename** is a property of each *face* (wall, floor, ceiling).  It selects a named style definition from the `share/` directory tree.  Examples: `default`, `foxhouse`, `simple`, `party`.  A party wall — one that should render without windows — gets a different stylename from an external wall of the same room.

The toolbar **Style** dropdown sets the default stylename for newly added rooms.  The properties panel **Style** dropdown resets all faces of the selected room to one style.  To override a single face, click its handle sphere (short click, not a drag) and change the **Face style** dropdown that appears.

Face handle spheres are **white** when the face uses the room's default style, and **blue** when the face has been individually overridden.

### How style conflicts are resolved

When two rooms share or partially overlap a wall, `CellComplex.ByFaces()` may split that wall into sub-faces.  `ApplyDictionary` then walks the original face list in order and assigns the stylename of the first source face whose area contains each sub-face's interior point.  In practice: the room that appears first in the rooms list wins for the shared area.  To ensure a particular style wins on a shared wall, set it on the face of whichever room was added first, or drag the boundary so one room's wall fully overlaps the other.

## File structure

```
web/
  server.py              FastAPI application
  geometry_adapter.py    JSON rooms → topologic_core Face/Vertex objects
  requirements.txt       Python dependencies
  Dockerfile             Build from repo root: docker build -f web/Dockerfile ...
  static/
    index.html           Single-page application shell
    src/
      editor.js          Three.js quad-cell room editor
      editor-utils.js    Pure geometry helpers (snap, face drag)
      preview.js         @thatopen/components IFC loader (shared scene)
      regenerate.js      Background regeneration loop (debounce + rate-limit)
    package.json         npm metadata; Three.js loaded from CDN (no build needed)
```

## HTTP API

### `POST /api/generate`

Generate an IFC file from a set of rooms.  Returns `application/octet-stream`.

```json
{
  "name": "My Building",
  "rooms": [
    {
      "vertices": [[0, 0], [4, 0], [4, 4], [0, 4]],
      "elevation": 0.0,
      "height": 3.0,
      "face_styles": ["default", "default", "default", "party", "default", "default"],
      "stylename": "default",
      "usage": "kitchen"
    }
  ]
}
```

`vertices` is a list of `[x, z]` pairs in Three.js XZ plane (Three.js Y-up, so `x` = east, `z` = depth).  At least 3 vertices, at most 64.  `elevation` is the floor height (Three.js Y).  `height` is the room height.

`face_styles` is an array of stylenames in face-index order:

| Index | Face |
|---|---|
| 0 | Floor |
| 1 | Ceiling |
| 2 | Wall along edge vertex 0 → 1 |
| 3 | Wall along edge vertex 1 → 2 |
| 4 | Wall along edge vertex 2 → 3 |
| 5 | Wall along edge vertex 3 → 0 |

Any missing or null entry falls back to `stylename`.  The `stylename` field alone (no `face_styles`) applies one style to all faces.

Advanced: send raw `faces` (list of 4-vertex arrays in IFC Z-up coordinates) and `widgets` (list of `{position: [x,y,z], usage}`) instead of `rooms` for direct control.

### `GET /api/styles`

Returns the list of stylenames available in `share/`.  `"default"` is always first.

```json
{"styles": ["default", "blank", "fancy", "foxhouse", "simple", ...]}
```

### `POST /api/validate`

Same request format as `/api/generate`.  Builds the `CellComplex` only (no IFC generation) and returns cell and face counts.  Useful for fast geometry feedback.

```json
{"valid": true, "cells": 3, "faces": 22}
```

### `GET /health`

```json
{"status": "ok", "share_dir": "/app/share"}
```

## Regeneration loop

The IFC model regenerates automatically in the background:

- Any edit fires a 2-second debounce timer.
- The server is not called more than once every 10 seconds.
- While an edit is recent or a request is in flight, the IFC overlay is ghosted (opacity 0.18).
- When idle and the latest model has loaded, the overlay becomes solid.
- The **Generate IFC** button forces an immediate regeneration.

## Architecture notes

### Coordinate systems

Three.js uses Y-up (`Y` = elevation).  IFC and homemaker use Z-up (`Z` = elevation).  The conversion happens in `geometry_adapter.py`:

```
IFC X = Three.js vertex x   (east,  unchanged)
IFC Y = Three.js vertex z   (depth, Three.js XZ plane second component)
IFC Z = elevation           (Three.js Y elevation)
```

### IFC viewer integration

`@thatopen/components` is initialised once with a hidden 1×1 px off-screen renderer (satisfying its API).  The resulting `FragmentsGroup` is added directly to the shared Three.js scene so editor geometry and IFC fragments are rendered by a single renderer with a single camera.

### Concurrency

`topologic_core` is CPU-bound.  The server uses a `ProcessPoolExecutor` (2 workers) so generation runs in a subprocess and does not block the FastAPI event loop.

### WASM future

`topologic_core` is the only dependency preventing the entire pipeline from running in the browser.  `ifcopenshell` already has a Pyodide WASM build (`wasm-wheels`).  If a WASM build of `topologic_core` becomes available, the JSON geometry API in `server.py` / `geometry_adapter.py` is designed as a clean replacement boundary — the same interface can be called from a Pyodide worker without changing the editor.

## Tests

Python tests live in `tests/` alongside the rest of the homemaker test suite.

```bash
cd tests
python -m pytest
```

`test_geometry_adapter.py` covers the coordinate axis swap, per-face style assignment, face plane geometry, and widget centroid placement.  `test_server_validation.py` covers all Pydantic input validators (vertex bounds, height/elevation ranges, stylename sanitisation, usage whitelist, face edge lengths) without requiring topologic_core or a running server.  `tests/pytest.ini` prevents pytest from traversing up to the Blender addon `__init__.py`.

JavaScript unit tests use [Vitest](https://vitest.dev/) and run in Node — no browser required.

```bash
cd web/static
npm test
```

`editor-utils.test.js` covers the pure geometry helpers extracted from `editor.js`:

- `snapToFaces` — Y-axis snap to floor/ceiling of adjacent rooms, threshold boundary, self-exclusion
- `computeFaceDrag` — ceiling drag (floor fixed) and floor drag (ceiling fixed), minimum-dimension guard, opposite-face invariant across multiple drag frames
- `snapVertexToWallPlanes` — snaps a vertex to the infinite wall planes of adjacent rooms; handles axis-aligned, diagonal, and non-rectangular walls; picks nearest plane when multiple are within threshold
