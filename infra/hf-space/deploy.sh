#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# Deploy the backend to a Hugging Face Space.
#
# First run:
#   export HF_USERNAME=<your-hf-username>
#   bash infra/hf-space/deploy.sh --init
#
# Subsequent runs:
#   bash infra/hf-space/deploy.sh
#
# The Space repo lives at a sibling directory so its .git doesn't nest inside
# the monorepo.
# ----------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SPACE_DIR="${REPO_ROOT}/../aria-hf-space"

: "${HF_USERNAME:?HF_USERNAME env var must be set to your Hugging Face username}"
SPACE_URL="https://huggingface.co/spaces/${HF_USERNAME}/aria-api"

if [[ "${1:-}" == "--init" ]]; then
  if [[ -d "${SPACE_DIR}" ]]; then
    echo "Space directory already exists at ${SPACE_DIR}. Remove it or drop --init."
    exit 1
  fi
  echo "Cloning ${SPACE_URL} → ${SPACE_DIR}"
  git clone "${SPACE_URL}" "${SPACE_DIR}"
fi

if [[ ! -d "${SPACE_DIR}" ]]; then
  echo "Space directory missing. Run once with --init after creating the Space on Hugging Face."
  exit 1
fi

echo "Syncing backend/ → ${SPACE_DIR}"
cd "${SPACE_DIR}"

# Keep the .git, wipe everything else, repopulate from backend/
find . -mindepth 1 -not -path "./.git*" -delete
cp -r "${REPO_ROOT}/backend/." .

git add -A
if git diff --cached --quiet; then
  echo "No changes to deploy."
  exit 0
fi

git commit -m "deploy: sync backend/ from monorepo ($(date -u +%FT%TZ))"
git push
echo ""
echo "Pushed. Hugging Face will now build the Docker image (first build ~5–10 min)."
echo "Watch logs at: ${SPACE_URL}"
echo "Health check:  ${SPACE_URL/spaces/$HF_USERNAME-aria-api.hf.space}/health"
