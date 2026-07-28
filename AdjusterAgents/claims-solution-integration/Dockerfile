# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────────────────────
# Hexaware Agentic Claims Solution — deployment image
#
# IMPORTANT: The /api/* endpoints are implemented as Vite server plugins
# (configureServer only). A static `vite build` would drop every /api/* route,
# so production runs the SAME Vite server that dev uses. This image therefore
# starts `vite` rather than serving a static bundle.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-slim

# Enable corepack and pin the exact pnpm version used to author the lockfile
# (pnpm-lock.yaml is lockfileVersion 9.0).
RUN corepack enable && corepack prepare pnpm@10.26.1 --activate

WORKDIR /app

# Copy the whole project first. The root package.json has a `preinstall` hook
# that requires pnpm and removes npm/yarn lockfiles, and the pnpm workspace
# references lib/ and scripts/, so a reliable install needs the full tree.
COPY . .

# Install dependencies exactly as locked.
RUN pnpm install --frozen-lockfile

# The Vite server binds 0.0.0.0 and reads PORT (see vite.config.ts).
ENV PORT=5000
EXPOSE 5000

# Required at runtime (provide via `-e` / compose / your platform's secrets):
#   AZURE_DATABASE_URL  — Azure PostgreSQL connection string (all /api/* data)
# Optional:
#   AZURE_STORAGE_SAS   — SAS token or storage connection string for direct
#                         blob viewing in the Document Hub
CMD ["pnpm", "exec", "vite", "--config", "vite.config.ts"]
