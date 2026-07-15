"""Admin ETL SSE 任务注册表：task_key → Strategy 调用。"""

from __future__ import annotations

import queue
from typing import Callable

from src.etl.strategy.financial.financial_audit_strategy import AuditStrategy
from src.etl.strategy.financial.financial_disclosure_date_strategy import DisclosureDateStrategy
from src.etl.strategy.financial.financial_express_strategy import ExpressStrategy
from src.etl.strategy.financial.financial_fina_mainbz_strategy import FinaMainbzStrategy
from src.etl.strategy.financial.financial_forecast_strategy import ForecastStrategy
from src.etl.strategy.financial.financial_top10_floatholders_strategy import Top10FloatholdersStrategy
from src.etl.strategy.financial.financial_report_strategy import ReportStrategy
from src.etl.workflow.financial.financial_report_workflow import ReportWorkflow
from src.etl.strategy.financial.financial_shareholder_strategy import ShareholderStrategy
from src.etl.strategy.financial.financial_stock_holder_strategy import StkHoldernumberStrategy
from src.etl.strategy.index.index_basic_strategy import IndexBasicStrategy
from src.etl.strategy.index.index_classify_strategy import IndexClassifyStrategy
from src.etl.strategy.index.index_daily_strategy import IndexDailyStrategy
from src.etl.strategy.index.index_member_all_strategy import IndexMemberAllStrategy
from src.etl.strategy.index.index_weight_strategy import IndexWeightStrategy
from src.etl.strategy.kline.kline_stock_factor_strategy import StkFactorStrategy
from src.etl.strategy.kline.kline_strategy import KlineStrategy
from src.etl.strategy.market.market_block_trade_strategy import BlockTradeStrategy
from src.etl.strategy.market.market_daily_basic_strategy import DailyBasicStrategy
from src.etl.strategy.market.market_dragon_tiger_strategy import DragonTigerStrategy
from src.etl.strategy.market.market_margin_strategy import MarginStrategy
from src.etl.strategy.market.market_moneyflow_strategy import MoneyflowStrategy
from src.etl.strategy.market.market_moneyflow_hsgt_strategy import MoneyflowHsgtStrategy
from src.etl.strategy.market.market_northbound_strategy import HsgtStrategy
from src.etl.strategy.market.market_hk_hold_strategy import HkHoldStrategy
from src.etl.strategy.stock.stock_premarket_strategy import StockPremarketStrategy
from src.etl.strategy.stock.stock_share_float_strategy import StockShareFloatStrategy
from src.etl.strategy.stock.stock_suspend_strategy import SuspendStrategy
from src.service.etl.completeness_dashboard_config import all_sse_task_keys


def _run_check(
    fn: Callable[..., int],
    start: str,
    end: str,
    progress_queue: queue.Queue,
) -> None:
    saved = fn(start_date=start, end_date=end, progress_queue=progress_queue)
    progress_queue.put({"done": True, "saved": saved, "message": f"累计补拉 {saved} 条"})


def _run_force_period_pull(
    pull_fn: Callable[[str], int],
    period: str,
    progress_queue: queue.Queue,
    *,
    label: str = "报告期",
) -> None:
    progress_queue.put({"status": "running", "total": 1})
    saved = pull_fn(period)
    progress_queue.put({
        "index": 1,
        "total": 1,
        "period": period,
        "saved": saved,
    })
    progress_queue.put({
        "done": True,
        "saved": saved,
        "message": f"{label} {period} 写入 {saved} 条",
    })


def _run_check_or_force_period_pull(
    check_fn: Callable[..., int],
    pull_fn: Callable[[str], int],
    start: str,
    end: str,
    progress_queue: queue.Queue,
    *,
    label: str = "报告期",
) -> None:
    """行级补位（start==end）强制拉取该期；区间补位仍走 check_complete。"""
    if start == end:
        _run_force_period_pull(pull_fn, start, progress_queue, label=label)
        return
    _run_check(check_fn, start, end, progress_queue)


def _run_report_history(
    fn: Callable[..., None],
    start: str,
    progress_queue: queue.Queue,
) -> None:
    fn(start, progress_queue=progress_queue)


_REPORT_SINGLE_PERIOD: dict[str, str] = {
    "report_income_history_init": "income",
    "report_balance_history_init": "balance",
    "report_cashflow_history_init": "cashflow",
    "report_indicator_history_init": "indicator",
}


def _run_report_history_or_period(
    task_key: str,
    start: str,
    end: str,
    progress_queue: queue.Queue,
) -> None:
    report_type = _REPORT_SINGLE_PERIOD.get(task_key)
    if report_type and start == end:
        progress_queue.put({"status": "running", "total": 1})
        saved = ReportWorkflow().report_by_period(report_type, start)
        ReportStrategy().refresh_report_macro_snapshot(
            start_date=start, end_date=end, scan_dimensions=False,
        )
        progress_queue.put({
            "done": True,
            "saved": saved,
            "message": f"报告期 {start} 写入 {saved} 条",
        })
        return
    fn = {
        "report_income_history_init": ReportStrategy().report_income_history_init,
        "report_balance_history_init": ReportStrategy().report_balance_history_init,
        "report_cashflow_history_init": ReportStrategy().report_cashflow_history_init,
        "report_indicator_history_init": ReportStrategy().report_indicator_history_init,
    }[task_key]
    _run_report_history(fn, start, progress_queue)


def _run_suspend_pull(start: str, end: str, progress_queue: queue.Queue) -> None:
    saved = SuspendStrategy().pull_suspend_by_date(
        start_date=start, end_date=end, progress_queue=progress_queue,
    )
    progress_queue.put({"done": True, "saved": saved, "message": f"停复牌写入 {saved} 条"})


def _run_snapshot_pull(
    fn: Callable[..., int],
    progress_queue: queue.Queue,
) -> None:
    saved = fn(progress_queue=progress_queue)
    progress_queue.put({"done": True, "saved": saved, "message": f"快照写入 {saved} 条"})


def _run_kline_window(start: str, end: str, progress_queue: queue.Queue) -> None:
    progress_queue.put({"log": f"K 线窗口完整性检查 {start}~{end}"})
    saved = KlineStrategy().check_kline_complete_history(
        start_date=start, end_date=end,
    )
    progress_queue.put({"done": True, "saved": saved, "message": f"K线窗口检查写入 {saved} 条"})


def _run_kline_dim(
    dim: str,
    start: str,
    end: str,
    progress_queue: queue.Queue,
) -> None:
    strat = KlineStrategy()
    pull_fn = {
        "daily": strat.pull_kline_daily_by_date_range,
        "adj_factor": strat.pull_kline_adj_factor_by_date_range,
        "stk_limit": strat.pull_kline_stk_limit_by_date_range,
    }[dim]
    saved = pull_fn(start, end, progress_queue=progress_queue)
    progress_queue.put({"done": True, "saved": saved, "message": f"累计写入 {saved} 条"})


SSE_TASK_REGISTRY: dict[str, Callable[..., None]] = {
    "report_income_history_init": lambda start, end, q: _run_report_history_or_period(
        "report_income_history_init", start, end, q,
    ),
    "report_balance_history_init": lambda start, end, q: _run_report_history_or_period(
        "report_balance_history_init", start, end, q,
    ),
    "report_cashflow_history_init": lambda start, end, q: _run_report_history_or_period(
        "report_cashflow_history_init", start, end, q,
    ),
    "report_indicator_history_init": lambda start, end, q: _run_report_history_or_period(
        "report_indicator_history_init", start, end, q,
    ),
    "financial_forecast_check": lambda start, end, q: _run_check_or_force_period_pull(
        ForecastStrategy().check_complete,
        ForecastStrategy().forecast_workflow.pull_forecast_by_period,
        start,
        end,
        q,
        label="业绩预告",
    ),
    "financial_express_check": lambda start, end, q: _run_check_or_force_period_pull(
        ExpressStrategy().check_complete,
        ExpressStrategy().express_workflow.pull_express_by_period,
        start,
        end,
        q,
        label="业绩快报",
    ),
    "financial_audit_check": lambda start, end, q: _run_check_or_force_period_pull(
        AuditStrategy().check_complete,
        AuditStrategy().pull_fina_audit_gaps_for_period,
        start,
        end,
        q,
        label="审计意见",
    ),
    "financial_disclosure_date_check": lambda start, end, q: _run_check_or_force_period_pull(
        DisclosureDateStrategy().check_complete,
        DisclosureDateStrategy().workflow.pull_disclosure_date_by_period,
        start,
        end,
        q,
        label="披露计划",
    ),
    "financial_fina_mainbz_check": lambda start, end, q: _run_check_or_force_period_pull(
        FinaMainbzStrategy().check_complete,
        lambda period: FinaMainbzStrategy().workflow.pull_fina_mainbz_period(period=period),
        start,
        end,
        q,
        label="主营构成",
    ),
    "financial_top10_floatholders_check": lambda start, end, q: _run_check(
        Top10FloatholdersStrategy().check_complete, start, end, q,
    ),
    "financial_stock_holder_check": lambda start, end, q: _run_check(
        StkHoldernumberStrategy().check_complete, start, end, q,
    ),
    "financial_shareholder_check": lambda start, end, q: _run_check(
        ShareholderStrategy().check_complete, start, end, q,
    ),
    "kline_daily_check": lambda start, end, q: _run_kline_dim("daily", start, end, q),
    "kline_adj_factor_check": lambda start, end, q: _run_kline_dim("adj_factor", start, end, q),
    "kline_stk_limit_check": lambda start, end, q: _run_kline_dim("stk_limit", start, end, q),
    "kline_stock_factor_check": lambda start, end, q: _run_check(
        StkFactorStrategy().check_complete, start, end, q,
    ),
    "kline_window_check": lambda start, end, q: _run_kline_window(start, end, q),
    "market_daily_basic_check": lambda start, end, q: _run_check(
        DailyBasicStrategy().check_complete, start, end, q,
    ),
    "market_moneyflow_check": lambda start, end, q: _run_check(
        MoneyflowStrategy().check_complete, start, end, q,
    ),
    "market_margin_check": lambda start, end, q: _run_check(
        MarginStrategy().check_complete, start, end, q,
    ),
    "market_northbound_check": lambda start, end, q: _run_check(
        HsgtStrategy().check_complete, start, end, q,
    ),
    "market_hsgt_check": lambda start, end, q: _run_check(
        MoneyflowHsgtStrategy().check_complete, start, end, q,
    ),
    "market_hk_hold_check": lambda start, end, q: _run_check(
        HkHoldStrategy().check_complete, start, end, q,
    ),
    "market_block_trade_check": lambda start, end, q: _run_check(
        BlockTradeStrategy().check_complete, start, end, q,
    ),
    "dragon_tiger_check": lambda start, end, q: _run_check(
        DragonTigerStrategy().check_complete, start, end, q,
    ),
    "index_weight_check": lambda start, end, q: _run_check(
        IndexWeightStrategy().check_complete, start, end, q,
    ),
    "index_daily_check": lambda start, end, q: _run_check(
        IndexDailyStrategy().check_complete, start, end, q,
    ),
    "index_basic_pull": lambda start, end, q: _run_snapshot_pull(
        IndexBasicStrategy().pull_snapshot, q,
    ),
    "index_classify_pull": lambda start, end, q: _run_snapshot_pull(
        IndexClassifyStrategy().pull_snapshot, q,
    ),
    "index_member_all_pull": lambda start, end, q: _run_snapshot_pull(
        IndexMemberAllStrategy().pull_snapshot, q,
    ),
    "stock_suspend_pull": lambda start, end, q: _run_suspend_pull(start, end, q),
    "stock_premarket_check": lambda start, end, q: _run_check(
        StockPremarketStrategy().check_complete, start, end, q,
    ),
    "stock_share_float_check": lambda start, end, q: _run_check(
        StockShareFloatStrategy().check_complete, start, end, q,
    ),
    "gtja191_compute": lambda start, end, q, **kwargs: _run_gtja191_compute(
        start, end, q, **kwargs
    ),
    "factor_compute": lambda start, end, q, **kwargs: _run_factor_compute(
        start, end, q, **kwargs
    ),
    "backtest_run": lambda start, end, q, **kwargs: _run_backtest(start, end, q, **kwargs),
}


def _run_gtja191_compute(
    start: str, end: str, progress_queue: queue.Queue, **kwargs
) -> None:
    from src.research.factor.gtja.strategy import Gtja191Strategy
    from src.research.factor.meta_service import FactorMetaService

    workers = kwargs.get("workers")
    Gtja191Strategy().compute_by_date_range(
        start_date=start,
        end_date=end,
        force=False,
        workers=int(workers) if workers is not None else None,
        progress_queue=progress_queue,
    )
    try:
        FactorMetaService().update_meta()
    except Exception as e:
        progress_queue.put({"log": f"update-meta 失败: {e}"})


def _run_factor_compute(
    start: str, end: str, progress_queue: queue.Queue, **kwargs
) -> None:
    import re

    from src.etl.strategy.kline.kline_factor_compute_strategy import FactorComputeStrategy
    from src.model.kline.factor_meta_model import FactorMetaModel
    from src.research.factor.gtja.strategy import Gtja191Strategy
    from src.research.factor.meta_service import FactorMetaService

    name = (kwargs.get("factor_name") or "").strip()
    if not name:
        progress_queue.put({"done": True, "saved": 0, "message": "缺少 factor_name"})
        return
    force = bool(kwargs.get("force"))
    sm, em = start[:6], end[:6]

    row = FactorMetaModel().get_by_name(name)
    impl = (getattr(row, "impl_kind", None) if row else None) or ""
    source = (row.source if row else "") or ""
    if not impl:
        if source == "国泰191" or name.startswith("gtja_alpha"):
            impl = "formula"
        elif source == "自研":
            impl = "python"
        elif source == "tushare":
            impl = "tushare"

    if impl == "tushare":
        msg = "tushare 因子请使用 Research CLI：tushare-factor pull-by-date-range"
        progress_queue.put({"done": True, "saved": 0, "message": msg})
        return

    if impl == "formula" or name.startswith("gtja_alpha"):
        m = re.fullmatch(r"gtja_alpha(\d+)", name)
        if not m:
            progress_queue.put({
                "done": True,
                "saved": 0,
                "message": f"无法解析国泰因子编号: {name}",
            })
            return
        alpha = int(m.group(1))
        Gtja191Strategy().compute(
            start_month=sm,
            end_month=em,
            alpha=alpha,
            force=force,
            progress_queue=progress_queue,
        )
    else:
        FactorComputeStrategy().compute_factor(
            name,
            start_month=sm,
            end_month=em,
            force=force,
            progress_queue=progress_queue,
        )

    try:
        FactorMetaService().update_meta()
    except Exception as e:
        progress_queue.put({"log": f"update-meta 失败: {e}"})


def _run_backtest(start: str, end: str, progress_queue: queue.Queue, **kwargs) -> None:
    from src.research.backtest.runner import BacktestRunner

    BacktestRunner().run(
        start_date=start,
        end_date=end,
        backtest_mode=kwargs.get("backtest_mode") or "single",
        factor_name=kwargs.get("factor_name"),
        combo_id=kwargs.get("combo_id"),
        groups=int(kwargs.get("groups") or 10),
        rebalance=kwargs.get("rebalance") or "monthly",
        commission_rate=kwargs.get("commission_rate"),
        stamp_duty_rate=kwargs.get("stamp_duty_rate"),
        slippage_rate=kwargs.get("slippage_rate"),
        progress_queue=progress_queue,
    )


def get_sse_task_runner(task_key: str) -> Callable[..., None]:
    runner = SSE_TASK_REGISTRY.get(task_key)
    if runner is None:
        raise KeyError(f"unknown SSE task_key: {task_key}")
    return runner


def validate_sse_task_key(task_key: str) -> None:
    if task_key not in all_sse_task_keys() and task_key not in SSE_TASK_REGISTRY:
        raise KeyError(f"unknown SSE task_key: {task_key}")
