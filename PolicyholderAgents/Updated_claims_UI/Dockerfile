FROM node:20-slim

WORKDIR /app

# Install dependencies first — separate layer so npm ci only reruns when
# package.json / package-lock.json change, not on every source edit.
COPY package.json package-lock.json ./
RUN npm ci

# Copy source — listed explicitly so node_modules is never included in the
# build context even without a .dockerignore.
COPY index.html vite.config.ts tsconfig.json components.json ./
COPY src/ ./src/
COPY vite-plugins/ ./vite-plugins/
COPY public/ ./public/
COPY attached_assets/ ./attached_assets/

EXPOSE 7133

# IMPORTANT: must run the dev server, not a static build.
# The Vite plugins (vite-plugins/*.ts) are dev-server middleware that provide
# DB-backed API routes (/api/claims, /api/fnol-submission, etc.).
# Those routes do not exist in the production build output.
# All VITE_* and AZURE_PG_* env vars must be passed in at runtime via
# docker-compose env_file or -e flags.
CMD ["npm", "run", "dev"]
