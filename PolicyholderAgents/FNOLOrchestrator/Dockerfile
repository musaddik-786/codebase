# ── Stage 1: install dependencies ─────────────────────────────────────────────
# Build context must be PolicyholderAgents/ (parent dir) so requirements.txt
# is reachable — same convention as MCP/Dockerfile.
FROM python:3.11-slim AS builder

WORKDIR /install

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

# Non-root user for security
RUN useradd --create-home appuser

# Copy installed packages from builder stage
COPY --from=builder /install/deps /usr/local

WORKDIR /app

# server.py has no local imports — all tool calls go out over HTTP to the
# MCP container, so nothing else from the repo needs to be copied in.
COPY FNOLOrchestrator/server.py ./FNOLOrchestrator/server.py
COPY requirements.txt .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 7730

# MCP endpoint URLs default to localhost:7720 — override via env vars in
# docker-compose (MCP_URL, DOC_MCP_URL, POLICY_COVERAGE_MCP_URL, etc.)
CMD ["python", "FNOLOrchestrator/server.py"]
