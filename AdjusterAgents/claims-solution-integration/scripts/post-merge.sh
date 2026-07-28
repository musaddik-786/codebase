#!/bin/bash
set -e

# Root package.json has a preinstall hook that deletes package-lock.json.
# The user's package-lock.json must stay in place, so back it up and restore it.
if [ -f package-lock.json ]; then
  cp package-lock.json /tmp/package-lock.json.bak
fi

pnpm install

if [ -f /tmp/package-lock.json.bak ]; then
  cp /tmp/package-lock.json.bak package-lock.json
  rm -f /tmp/package-lock.json.bak
fi
