#!/bin/bash
set -e

# Install dependencies in case a merged task changed package.json / lockfile.
pnpm install
