#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
  docker compose down --remove-orphans
}
trap cleanup EXIT

echo "setup poetry env"
poetry config virtualenvs.in-project true --local
if ! poetry env info --path >/dev/null 2>&1; then
  if command -v python3.15 >/dev/null 2>&1; then
    poetry env use "$(command -v python3.15)"
  elif command -v python3.14 >/dev/null 2>&1; then
    poetry env use "$(command -v python3.14)"
  elif command -v python3.12 >/dev/null 2>&1; then
    poetry env use "$(command -v python3.12)"
  elif command -v python3.11 >/dev/null 2>&1; then
    poetry env use "$(command -v python3.11)"
  else
    poetry env use "$(command -v python3)"
  fi
fi

echo "install project dependencies"
poetry install --with dev --sync

echo "set test env"
export APP_CODE="${APP_CODE:-test}"
export STACK="${STACK:-test}"
export MONGO_DB="${MONGO_DB:-servicetest}"
export MONGO_USER="${MONGO_USER:-servicetest}"
export MONGO_PASS="${MONGO_PASS:-servicetest}"
export MONGO_URL="${MONGO_URL:-localhost:10002}"
export MONGO_REPLICA="${MONGO_REPLICA:-}"
export MODELS_FOLDER="${MODELS_FOLDER:-tests/models}"

echo "reset compose stack"
docker compose down -v --remove-orphans || true

echo "make compose"
docker compose up -d --force-recreate

echo "check code"
poetry run black ozonenv/**/*.py
# poetry run flake8 ozonenv/**/*.py

echo "run test"
rm -rf tests/models
time poetry run pytest --cov --cov-report=html -vv -x -s "$@"

echo "make project: Done."
