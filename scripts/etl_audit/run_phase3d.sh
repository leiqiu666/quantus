#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
P0="${P0:-20251231}"
P1="${P1:-20260331}"
LOG="/tmp/etl_phase3d.log"
: > "$LOG"

run_one() {
  local name="$1"
  local pull="$2"
  local check="$3"
  echo "========== $name ==========" | tee -a "$LOG"
  eval "$pull" 2>&1 | tee -a "$LOG" || echo "[FAIL pull] $name" | tee -a "$LOG"
  eval "$check" 2>&1 | tee -a "$LOG" || echo "[FAIL check] $name" | tee -a "$LOG"
}

run_one "forecast" \
  "uv run ./src/etl/cli.py financial_forecast pull-by-period --start-period $P0 --end-period $P1" \
  "uv run ./src/etl/cli.py financial_forecast check-complete --start-period $P0 --end-period $P1"

run_one "express" \
  "uv run ./src/etl/cli.py financial_express pull-by-period --start-period $P0 --end-period $P1" \
  "uv run ./src/etl/cli.py financial_express check-complete --start-period $P0 --end-period $P1"

run_one "audit" \
  "uv run ./src/etl/cli.py audit pull-by-period --start-period $P0 --end-period $P1" \
  "uv run ./src/etl/cli.py audit check-complete --start-period $P0 --end-period $P1"

echo "DONE Phase 3D" | tee -a "$LOG"
