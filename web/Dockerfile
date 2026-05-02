FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by topologic_core / ifcopenshell
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy homemaker-addon package first (pip-installable)
COPY ../molior ./molior
COPY ../topologist ./topologist
COPY ../share ./share
COPY ../setup.py .
COPY ../requirements.txt ./homemaker-requirements.txt

# Install homemaker-addon as a local package, then the web server deps
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir -r homemaker-requirements.txt

# Copy web server
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/server.py .
COPY web/geometry_adapter.py .

# Copy built frontend assets
COPY web/static ./static

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
