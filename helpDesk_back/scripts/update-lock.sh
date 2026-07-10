#!/usr/bin/env bash
# Regenerate poetry.lock to match pyproject.toml (run from repo root or helpDesk_back).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACK_DIR"
docker run --rm \
  -v "$BACK_DIR:/app" \
  -w /app \
  python:3.12-slim \
  bash -c "pip install -q poetry==2.3.0 && poetry lock"
echo "poetry.lock updated in $BACK_DIR"
