"""
一次性脚本：回填 suspend_d 历史数据（19900101 ~ 20250101）。

绕过 SuspendStrategy.resolve_incremental_start 的"只前进"语义，
直接对每个未入库的 SSE 开市日调用 SuspendWorkflow.pull_suspend_by_date。
"""

from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy import text

from src.common.database import Database
from src.common.function import tqdm_iter
from src.etl.extract.local.trade_cal.trade_cal_extract import TradeCalLocalExtract
from src.etl.strategy.trade_cal.trade_cal_strategy import TradeCalStrategy
from src.etl.workflow.suspend.suspend_workflow import SuspendWorkflow

START = "19900101"
END = "20250101"


def main() -> None:
    db = Database()
    trade_cal_strategy = TradeCalStrategy()
    trade_cal_local = TradeCalLocalExtract()
    workflow = SuspendWorkflow()

    trade_cal_strategy.ensure_trade_cal(start_date=START, end_date=END, exchange="SSE")
    open_dates = trade_cal_local.get_open_trade_dates(
        start_date=START, end_date=END, exchange="SSE",
    )
    if not open_dates:
        print("[信息] 无 SSE 开市日，跳过")
        return

    sess = db.get_session()
    try:
        rows = sess.execute(
            text(
                "SELECT DISTINCT trade_date FROM suspend_d "
                "WHERE trade_date BETWEEN :s AND :e"
            ),
            {"s": START, "e": END},
        ).fetchall()
    finally:
        sess.close()
    seen: set[str] = {str(r[0]).strip()[:8] for r in rows if r[0]}

    todo = [d for d in open_dates if d not in seen]
    print(
        f"[信息] 区间 {START}~{END} 共 {len(open_dates)} 个 SSE 开市日，"
        f"已入库 {len(seen)}，待补 {len(todo)}"
    )
    if not todo:
        print("[信息] 全部已入库，无需回填")
        return

    t0 = time.monotonic()
    total_saved = 0
    pbar = tqdm_iter(todo, desc="suspend_d 历史回填", unit="日")
    for td in pbar:
        try:
            n = workflow.pull_suspend_by_date(td)
        except Exception as e:
            print(f"[警告] {td} 失败：{e}")
            continue
        total_saved += n
        if hasattr(pbar, "set_postfix"):
            pbar.set_postfix(saved=n, total=total_saved, date=td)

    elapsed = time.monotonic() - t0
    print(
        f"[完成] 回填 {len(todo)} 日，新增/更新 {total_saved} 行，"
        f"耗时 {elapsed/60:.1f} 分钟（结束于 {datetime.now().strftime('%H:%M:%S')}）"
    )


if __name__ == "__main__":
    main()
