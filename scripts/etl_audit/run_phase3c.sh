#!/usr/bin/env bash
# ETL Phase 3C/3D batch runner — logs to /tmp/etl_phase3c.log
set -euo pipefail
cd "$(dirname "$0")/../.."
D5="${D5:-20260629}"
D1="${D1:-20260703}"
MONTH="${MONTH:-202606}"
P0="${P0:-20251231}"
P1="${P1:-20260331}"
LOG="/tmp/etl_phase3c.log"

run_pull_check() {
  local name="$1"
  local pull_cmd="$2"
  local check_cmd="$3"
  echo "========== $name PULL ==========" | tee -a "$LOG"
  eval "$pull_cmd" 2>&1 | tee -a "$LOG" || echo "[FAIL pull] $name" | tee -a "$LOG"
  echo "========== $name CHECK ==========" | tee -a "$LOG"
  eval "$check_cmd" 2>&1 | tee -a "$LOG" || echo "[FAIL check] $name" | tee -a "$LOG"
}

: > "$LOG"

run_pull_check "daily-basic" \
  "uv run ./src/etl/cli.py daily-basic pull-by-date-range --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py daily-basic check-complete --start-date $D5 --end-date $D1"

run_pull_check "dividend" \
  "uv run ./src/etl/cli.py market_dividend pull-by-date-range --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py market_dividend check-complete --start-date $D5 --end-date $D1"

run_pull_check "stk-factor" \
  "uv run ./src/etl/cli.py stk-factor pull-by-date-range --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py stk-factor check-complete --start-date $D5 --end-date $D1"

run_pull_check "moneyflow" \
  "uv run ./src/etl/cli.py market_moneyflow pull-by-date-range --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py market_moneyflow check-complete --start-date $D5 --end-date $D1"

run_pull_check "margin" \
  "uv run ./src/etl/cli.py margin pull-detail-by-date-range --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py margin check-complete --start-date $D5 --end-date $D1"

run_pull_check "hsgt" \
  "uv run ./src/etl/cli.py hsgt pull-top10-by-date-range --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py hsgt check-complete --start-date $D5 --end-date $D1"

run_pull_check "stk-holder" \
  "uv run ./src/etl/cli.py stk-holder pull-number --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py stk-holder check-complete --start-date $D5 --end-date $D1"

run_pull_check "index" \
  "uv run ./src/etl/cli.py index pull-weight-by-month-range --start-month $MONTH --end-month $MONTH" \
  "uv run ./src/etl/cli.py index check-complete --start-date ${MONTH}01 --end-date ${MONTH}31"

run_pull_check "dragon-tiger" \
  "uv run ./src/etl/cli.py dragon-tiger pull-by-date-range --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py dragon-tiger check-complete --start-date $D5 --end-date $D1"

run_pull_check "block-trade" \
  "uv run ./src/etl/cli.py block-trade pull-by-date-range --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py block-trade check-complete --start-date $D5 --end-date $D1"

run_pull_check "shareholder" \
  "uv run ./src/etl/cli.py shareholder pull-by-date --start-date $D5 --end-date $D1" \
  "uv run ./src/etl/cli.py shareholder check-complete --start-period $D5 --end-period $D1"

echo "DONE Phase 3C" | tee -a "$LOG"
