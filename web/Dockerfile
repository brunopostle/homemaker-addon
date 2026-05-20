FROM python:3.11-slim

# IMPORTANT: this Dockerfile must be built with the repo root as build context:
#   docker build -f web/Dockerfile -t homemaker-web .
# Running `docker build web/` will fail because COPY paths reference ../

WORKDIR /app

# Install system deps needed by topologic_core / ifcopenshell
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy homemaker-addon package first (pip-installable)
COPY molior ./molior
COPY topologist ./topologist
COPY share ./share
COPY setup.py .
COPY requirements.txt ./homemaker-requirements.txt

# Install homemaker-addon as a local package, then the web server deps
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir -r homemaker-requirements.txt

# Copy web server
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/server.py .
COPY web/geometry_adapter.py .

# Copy frontend assets (no build step needed; Three.js loaded from CDN via importmap)
COPY web/static ./static

# SHARE_DIR is auto-detected by server.py; override here if needed.
# ENV SHARE_DIR=/app/share

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
