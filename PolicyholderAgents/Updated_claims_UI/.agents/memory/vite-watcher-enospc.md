---
name: Vite ENOSPC file-watcher crash
description: Why the dev server crashed with ENOSPC and how it was fixed.
---

# Vite ENOSPC file-watcher crash

The `Start application` (vite) workflow crashed at startup with
`Error: ENOSPC: System limit for number of file watchers reached`, watching
paths under `.local/share/pnpm/store/...`.

**Why:** the pnpm store lives inside the workspace under `.local/`, so Vite's
chokidar watcher tried to watch the entire store and blew past the container's
inotify limit. It surfaced right after installing a new package (more store files).

**How to apply:** keep `server.watch.ignored` in `vite.config.ts` excluding
`**/.local/**` (and `**/dist/**`, `**/.git/**`). Do NOT try to raise the system
inotify limit — it's not writable in the container. If the dev server fails to
restart with ENOSPC, check this ignore list first.
