# ── Stage 1: build / install dependencies ─────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /install

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt


# ── Stage 2: runtime image ─────────────────────────────────────────────────────
FROM python:3.11-slim

# Non-root user for security
RUN useradd --create-home appuser

# Copy installed packages from builder
COPY --from=builder /install/deps /usr/local

WORKDIR /app

# Copy only what the MCP server needs:
#   - MCP source (routers, handlers, models, common/)
#   - requirements.txt (informational, not re-installed)
#   - data/ directory so the local uploads fallback path resolves correctly
#     (handler.py walks ../../data/uploads relative to its own file)
COPY MCP/ ./MCP/
COPY requirements.txt .
COPY .env /app/.env
RUN mkdir -p data/uploads

# Drop to non-root
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 7720

# init_db runs automatically via the @app.on_event("startup") hook in main.py
CMD ["python", "MCP/main.py"]

