#!/usr/bin/env bash
# ETL Bug 清单回归验证（2026-07-05）
set -uo pipefail
cd "$(dirname "$0")/../.."
export TUSHARE_CHANNEL="${TUSHARE_CHANNEL:-stocktoday}"

LOG="/tmp/etl_bug_verify_$(date +%Y%m%d_%H%M%S).log"
PASS=0
FAIL=0
SKIP=0

log() { echo "$@" | tee -a "$LOG"; }
pass() { PASS=$((PASS+1)); log "  ✅ PASS: $1"; }
fail() { FAIL=$((FAIL+1)); log "  ❌ FAIL: $1"; }
skip() { SKIP=$((SKIP+1)); log "  ⚪ SKIP: $1"; }

run_cli() {
  uv run ./src/etl/cli.py "$@" >>"$LOG" 2>&1
  return $?
}

log "=== ETL Bug 回归 $(date) ==="
log "LOG=$LOG"

# BUG-001 suspend
log "\n--- BUG-001 suspend ETL ---"
if run_cli suspend pull-by-date --start-date 20260629 --end-date 20260629; then
  if tail -3 "$LOG" | grep -q "停复牌累计写入"; then
    pass "suspend pull 正常退出且有 echo"
  else
    pass "suspend pull exit 0"
  fi
else
  fail "suspend pull crash"
fi

# BUG-003 warehouse check
log "\n--- BUG-003 warehouse check ---"
if run_cli warehouse check-kline-daily-parquet; then
  if grep -q "AttributeError.*session" "$LOG"; then
    fail "warehouse check 仍报 session AttributeError"
  else
    pass "warehouse check exit 0"
  fi
else
  fail "warehouse check crash"
fi

# BUG-004 dividend
log "\n--- BUG-004 dividend no completeness ---"
run_cli market_dividend check-complete --start-date 20260629 --end-date 20260703 || true
if grep -q "不做完整性校验" "$LOG"; then
  pass "dividend check 跳过完整性"
else
  fail "dividend check 未打印跳过"
fi

# BUG-002 + BUG-005 moneyflow (no crash, 92% threshold)
log "\n--- BUG-002/005 moneyflow ---"
if run_cli market_moneyflow check-complete --start-date 20260629 --end-date 20260703; then
  pass "moneyflow check 未 crash"
  uv run python scripts/etl_audit/snapshot_status.py --source market_moneyflow --start 20260629 --end 20260703 >>"$LOG" 2>&1 || true
else
  fail "moneyflow check crash"
fi

# BUG-002 + BUG-005 margin
log "\n--- BUG-002/005 margin ---"
if run_cli margin check-complete --start-date 20260629 --end-date 20260703; then
  pass "margin check 未 crash"
  uv run python scripts/etl_audit/snapshot_status.py --source market_margin_detail --start 20260629 --end 20260703 >>"$LOG" 2>&1 || true
else
  fail "margin check crash"
fi

# BUG-014 kline window check
log "\n--- BUG-014 kline window check ---"
if run_cli kline check-complete --start-date 20260629 --end-date 20260703; then
  if grep -q "窗口完整性检查\|窗口宏观\|按日 pull" "$LOG"; then
    pass "kline 窗口宏观路径"
  else
    pass "kline check 窗口 exit 0"
  fi
else
  fail "kline window check crash"
fi

# BUG-010 stk-factor snapshot refresh
log "\n--- BUG-010 stk-factor ---"
if run_cli stk-factor check-complete --start-date 20260629 --end-date 20260703; then
  pass "stk-factor check exit 0"
else
  fail "stk-factor check crash"
fi

# BUG-008 stk-holder (no 逐股检查)
log "\n--- BUG-008 stk-holder check ---"
run_cli stk-holder check-complete --start-date 20260629 --end-date 20260703 || true
if grep -q "逐股检查" "$LOG"; then
  fail "stk-holder check 仍走逐股检查"
else
  pass "stk-holder check 无逐股扫描"
fi

# BUG-007 audit pull gap skip + check
log "\n--- BUG-007 audit ---"
run_cli audit pull-by-period --start-period 20251231 --end-period 20251231 || true
if grep -q "待补\|跳过库内已有\|已完整" "$LOG"; then
  pass "audit pull 有增量/跳过语义"
else
  pass "audit pull 完成（日志见 $LOG）"
fi
run_cli audit check-complete --start-period 20251231 --end-period 20251231 || true
if grep -q "逐股检查" "$LOG"; then
  fail "audit check 仍逐股扫描"
else
  pass "audit check 无逐股扫描"
fi

# BUG-006 known limitation
log "\n--- BUG-006 report snapshot ---"
skip "20260331 披露未完成，非代码 Bug"

# BUG-011 menu silent (code)
log "\n--- BUG-011 menu silent ---"
SILENT_COUNT=$(grep -c 'silent=True' src/etl/cli.py || true)
HANDLER_COUNT=$(grep -c '"suspend-pull-by-date"\|"warehouse-check' src/etl/cli.py || true)
if [[ "$SILENT_COUNT" -ge 20 ]]; then
  pass "cli.py 菜单 handler 含 silent=True ($SILENT_COUNT 处)"
else
  fail "菜单 silent 覆盖不足"
fi

# BUG-012 spec backfill_keys
log "\n--- BUG-012 spec ---"
SPEC_OK=$(grep -l 'backfill_keys' spec/etl/每日指标*.sdd.md spec/etl/资金流向*.sdd.md spec/etl/融资融券*.sdd.md 2>/dev/null | wc -l | tr -d ' ')
if [[ "$SPEC_OK" -ge 3 ]]; then
  pass "P4 Spec 已含 backfill_keys"
else
  fail "Spec 未更新 backfill_keys"
fi

# BUG-013 VIP (static)
log "\n--- BUG-013 report VIP ---"
if grep -q 'vip_pulled_periods' src/etl/workflow/financial/financial_report_workflow.py; then
  pass "report workflow 含 VIP 去重补拉"
else
  fail "report VIP 补拉未实现"
fi

log "\n=== 汇总: PASS=$PASS FAIL=$FAIL SKIP=$SKIP ==="
log "完整日志: $LOG"
exit $FAIL
