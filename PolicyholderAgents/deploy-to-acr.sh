#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy-to-acr.sh
# Builds, tags, and pushes the three Policyholder containers to Azure Container
# Registry.
#
# Usage:
#   ./deploy-to-acr.sh <ACR_NAME> [TAG]
#
# Arguments:
#   ACR_NAME  — your ACR login server name WITHOUT the .azurecr.io suffix
#               e.g.  mycompanyacr
#   TAG       — image tag to push (default: latest)
#               pass "git" to auto-tag with the current short commit hash
#
# Examples:
#   ./deploy-to-acr.sh mycompanyacr
#   ./deploy-to-acr.sh mycompanyacr v1.2.0
#   ./deploy-to-acr.sh mycompanyacr git
#
# Prerequisites:
#   - Docker running
#   - Azure CLI installed and logged in  (az login)
#   - Contributor or AcrPush role on the target ACR
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

log()   { echo -e "${CYAN}[$(date +%H:%M:%S)]${RESET} $*"; }
ok()    { echo -e "${GREEN}[$(date +%H:%M:%S)] ✔ $*${RESET}"; }
warn()  { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠ $*${RESET}"; }
error() { echo -e "${RED}[$(date +%H:%M:%S)] ✖ $*${RESET}" >&2; exit 1; }

# ── Arguments ─────────────────────────────────────────────────────────────────
ACR_NAME="${1:-}"
TAG="${2:-latest}"

if [[ -z "$ACR_NAME" ]]; then
  error "ACR_NAME is required.\n  Usage: $0 <ACR_NAME> [TAG]"
fi

# Resolve "git" tag to the current short commit hash
if [[ "$TAG" == "git" ]]; then
  TAG=$(git -C "$(dirname "$0")" rev-parse --short HEAD 2>/dev/null) \
    || error "Could not read git commit hash. Are you inside a git repo?"
fi

# Strip .azurecr.io suffix if the user passed the full login-server URL
# so both  "myacr"  and  "myacr.azurecr.io"  work as the first argument.
ACR_NAME="${ACR_NAME%.azurecr.io}"
REGISTRY="${ACR_NAME}.azurecr.io"

echo -e "\n${BOLD}════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Deploying Policyholder containers to ACR  ${RESET}"
echo -e "${BOLD}════════════════════════════════════════════${RESET}"
echo -e "  Registry : ${CYAN}${REGISTRY}${RESET}"
echo -e "  Tag      : ${CYAN}${TAG}${RESET}"
echo

# ── Prereq checks ─────────────────────────────────────────────────────────────
command -v docker &>/dev/null || error "Docker is not installed or not in PATH."
command -v az     &>/dev/null || error "Azure CLI (az) is not installed or not in PATH."

# ── Navigate to the script directory (PolicyholderAgents/) ────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
log "Working directory: $SCRIPT_DIR"

# ── ACR login ─────────────────────────────────────────────────────────────────
log "Logging into ACR: ${REGISTRY} ..."
az acr login --name "$ACR_NAME" || error "ACR login failed. Check 'az login' and your ACR permissions."
ok "ACR login successful"
echo

# ── Image definitions ─────────────────────────────────────────────────────────
# Each entry: "service_name|build_context|dockerfile_path"
declare -a IMAGES=(
  "claims-mcp|.|MCP/Dockerfile"
  "claims-orchestrator|.|FNOLOrchestrator/Dockerfile"
  "claims-ui|Updated_claims_UI|Updated_claims_UI/Dockerfile"
)

FAILED=()
START_TOTAL=$SECONDS

for entry in "${IMAGES[@]}"; do
  IFS='|' read -r SERVICE CONTEXT DOCKERFILE <<< "$entry"

  LOCAL_TAG="${SERVICE}:${TAG}"
  REMOTE_TAG="${REGISTRY}/${SERVICE}:${TAG}"
  REMOTE_LATEST="${REGISTRY}/${SERVICE}:latest"

  echo -e "${BOLD}── ${SERVICE} ──────────────────────────────────────────${RESET}"

  # Build
  log "Building ${LOCAL_TAG} (context: ${CONTEXT}, dockerfile: ${DOCKERFILE}) ..."
  START=$SECONDS
  if docker build \
      --file "${DOCKERFILE}" \
      --tag  "${LOCAL_TAG}" \
      "${CONTEXT}"; then
    ok "Build complete ($(( SECONDS - START ))s)"
  else
    warn "Build FAILED for ${SERVICE} — skipping push"
    FAILED+=("$SERVICE")
    echo
    continue
  fi

  # Tag for ACR
  docker tag "${LOCAL_TAG}" "${REMOTE_TAG}"
  # Also tag as :latest so pulling without a tag always gets the newest build
  docker tag "${LOCAL_TAG}" "${REMOTE_LATEST}"

  # Push versioned tag
  log "Pushing ${REMOTE_TAG} ..."
  START=$SECONDS
  if docker push "${REMOTE_TAG}"; then
    ok "Pushed ${REMOTE_TAG} ($(( SECONDS - START ))s)"
  else
    warn "Push FAILED for ${REMOTE_TAG}"
    FAILED+=("$SERVICE")
    echo
    continue
  fi

  # Push :latest tag (skip if TAG is already "latest" to avoid double-push)
  if [[ "$TAG" != "latest" ]]; then
    log "Pushing ${REMOTE_LATEST} ..."
    docker push "${REMOTE_LATEST}"
    ok "Pushed ${REMOTE_LATEST}"
  fi

  echo
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo -e "${BOLD}════════════════════════════════════════════${RESET}"
if [[ ${#FAILED[@]} -eq 0 ]]; then
  ok "All images pushed successfully in $(( SECONDS - START_TOTAL ))s"
  echo
  echo -e "${BOLD}Images in ACR:${RESET}"
  for entry in "${IMAGES[@]}"; do
    IFS='|' read -r SERVICE _ _ <<< "$entry"
    echo -e "  ${GREEN}✔${RESET}  ${REGISTRY}/${SERVICE}:${TAG}"
  done
else
  warn "The following services failed: ${FAILED[*]}"
  echo -e "  Re-run the script or build/push them individually."
fi
echo -e "${BOLD}════════════════════════════════════════════${RESET}\n"
