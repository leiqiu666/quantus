"""ETL CLI 交互菜单命令注册表（单一事实源）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from src.scheduler import command_runners as runners

ScheduleHint = Literal["morning", "pre_open", "post_close", "anytime"]
CommandRunner = Callable[[], int | None]


@dataclass(frozen=True)
class EtlCommandSpec:
    command_key: str
    label: str
    typer_group: str
    typer_command: str
    category: str
    schedule_hint: ScheduleHint
    run_on_trading_day: bool
    runner: CommandRunner


def _wrap(fn: Callable[[], int | None]) -> CommandRunner:
    return fn


ETL_COMMANDS: tuple[EtlCommandSpec, ...] = (
    EtlCommandSpec(
        "report-history-init",
        "【财报】财报三表及财务指标全量历史入库",
        "report",
        "report-history-init",
        "财报",
        "anytime",
        False,
        _wrap(runners.run_report_history_init),
    ),
    EtlCommandSpec(
        "stock-pull-list-a",
        "【基础】A 股股票列表全量入库",
        "stock",
        "pull-list-a",
        "基础",
        "morning",
        False,
        _wrap(runners.run_stock_pull_list_a),
    ),
    EtlCommandSpec(
        "trade-cal-pull-history",
        "【基础】全交易所交易日历增量入库",
        "trade-cal",
        "pull-history",
        "基础",
        "morning",
        False,
        _wrap(runners.run_trade_cal_pull_history),
    ),
    EtlCommandSpec(
        "suspend-pull-by-date",
        "【基础】A 股停复牌增量入库",
        "suspend",
        "pull-by-date",
        "基础",
        "pre_open",
        True,
        _wrap(runners.run_suspend_pull_by_date),
    ),
    EtlCommandSpec(
        "stock-refresh-active-count",
        "【基础】活跃股票数快照",
        "stock",
        "refresh-active-count",
        "基础",
        "pre_open",
        True,
        _wrap(runners.run_stock_refresh_active_count),
    ),
    EtlCommandSpec(
        "stock-backfill-delist-date",
        "【基础】(退)股 delist_date 回填",
        "stock",
        "backfill-delist-date",
        "基础",
        "anytime",
        False,
        _wrap(runners.run_stock_backfill_delist_date),
    ),
    EtlCommandSpec(
        "kline-pull-daily-by-date-range",
        "【K线】日线区间增量",
        "kline",
        "pull-daily-by-date-range",
        "K线",
        "post_close",
        True,
        _wrap(runners.run_kline_pull_daily_by_date_range),
    ),
    EtlCommandSpec(
        "kline-pull-adj-factor-by-date-range",
        "【K线】复权因子区间增量",
        "kline",
        "pull-adj-factor-by-date-range",
        "K线",
        "post_close",
        True,
        _wrap(runners.run_kline_pull_adj_factor_by_date_range),
    ),
    EtlCommandSpec(
        "kline-pull-stk-limit-by-date-range",
        "【K线】涨跌停区间增量",
        "kline",
        "pull-stk-limit-by-date-range",
        "K线",
        "post_close",
        True,
        _wrap(runners.run_kline_pull_stk_limit_by_date_range),
    ),
    EtlCommandSpec(
        "daily-basic-pull-by-date-range",
        "【估值】每日指标区间增量",
        "daily-basic",
        "pull-by-date-range",
        "市场",
        "post_close",
        True,
        _wrap(runners.run_daily_basic_pull_by_date_range),
    ),
    EtlCommandSpec(
        "dividend-pull-by-date-range",
        "【分红】分红送股区间增量",
        "market_dividend",
        "pull-by-date-range",
        "市场",
        "post_close",
        True,
        _wrap(runners.run_dividend_pull_by_date_range),
    ),
    EtlCommandSpec(
        "stk-factor-pull-by-date-range",
        "【因子】技术面因子区间增量",
        "stk-factor",
        "pull-by-date-range",
        "K线",
        "post_close",
        True,
        _wrap(runners.run_stk_factor_pull_by_date_range),
    ),
    EtlCommandSpec(
        "moneyflow-pull-by-date-range",
        "【资金流】个股资金流向区间增量",
        "market_moneyflow",
        "pull-by-date-range",
        "市场",
        "post_close",
        True,
        _wrap(runners.run_moneyflow_pull_by_date_range),
    ),
    EtlCommandSpec(
        "margin-pull-detail-by-date-range",
        "【两融】融资融券明细区间增量",
        "margin",
        "pull-detail-by-date-range",
        "市场",
        "post_close",
        True,
        _wrap(runners.run_margin_pull_detail_by_date_range),
    ),
    EtlCommandSpec(
        "hsgt-pull-top10-by-date-range",
        "【北向】沪深股通十大成交股区间增量",
        "hsgt",
        "pull-top10-by-date-range",
        "市场",
        "post_close",
        True,
        _wrap(runners.run_hsgt_pull_top10_by_date_range),
    ),
    EtlCommandSpec(
        "stk-holder-pull-number",
        "【筹码】股东户数区间增量",
        "stk-holder",
        "pull-number",
        "财务",
        "anytime",
        False,
        _wrap(runners.run_stk_holder_pull_number),
    ),
    EtlCommandSpec(
        "index-pull-weight-by-month-range",
        "【指数】指数成分和权重按月区间增量",
        "index",
        "pull-weight-by-month-range",
        "指数",
        "anytime",
        False,
        _wrap(runners.run_index_pull_weight_by_month_range),
    ),
    EtlCommandSpec(
        "dragon-tiger-pull-by-date-range",
        "【龙虎榜】龙虎榜区间增量",
        "dragon-tiger",
        "pull-by-date-range",
        "市场",
        "post_close",
        True,
        _wrap(runners.run_dragon_tiger_pull_by_date_range),
    ),
    EtlCommandSpec(
        "block-trade-pull-by-date-range",
        "【大宗】大宗交易区间增量",
        "block-trade",
        "pull-by-date-range",
        "市场",
        "post_close",
        True,
        _wrap(runners.run_block_trade_pull_by_date_range),
    ),
    EtlCommandSpec(
        "shareholder-pull-by-date",
        "【股东】前十大股东区间增量",
        "shareholder",
        "pull-by-date",
        "财务",
        "anytime",
        False,
        _wrap(runners.run_shareholder_pull_by_date),
    ),
    EtlCommandSpec(
        "floatholders-pull-by-date",
        "【股东】前十大流通股东区间增量",
        "shareholder",
        "pull-floatholders-by-date",
        "财务",
        "anytime",
        False,
        _wrap(runners.run_floatholders_pull_by_date),
    ),
    EtlCommandSpec(
        "forecast-pull-by-period",
        "【预告】业绩预告全市场增量",
        "financial_forecast",
        "pull-by-period",
        "财务",
        "anytime",
        False,
        _wrap(runners.run_forecast_pull_by_period),
    ),
    EtlCommandSpec(
        "express-pull-by-period",
        "【快报】业绩快报全市场增量",
        "financial_express",
        "pull-by-period",
        "财务",
        "anytime",
        False,
        _wrap(runners.run_express_pull_by_period),
    ),
    EtlCommandSpec(
        "audit-pull-by-period",
        "【审计】财务审计意见全市场增量",
        "audit",
        "pull-by-period",
        "财务",
        "anytime",
        False,
        _wrap(runners.run_audit_pull_by_period),
    ),
    EtlCommandSpec(
        "disclosure-date-pull-by-period",
        "【披露】财报披露计划全市场增量",
        "financial_disclosure_date",
        "pull-by-period",
        "财务",
        "anytime",
        False,
        _wrap(runners.run_disclosure_date_pull_by_period),
    ),
    EtlCommandSpec(
        "fina-mainbz-pull-by-period",
        "【主营】主营业务构成全市场增量",
        "financial_fina_mainbz",
        "pull-by-period",
        "财务",
        "anytime",
        False,
        _wrap(runners.run_fina_mainbz_pull_by_period),
    ),
    EtlCommandSpec(
        "warehouse-pull-kline-daily-by-month-range",
        "【仓库】日K PG→Parquet 按月增量",
        "warehouse",
        "pull-kline-daily-by-month-range",
        "仓库",
        "anytime",
        False,
        _wrap(runners.run_warehouse_pull_kline_daily_by_month_range),
    ),
    EtlCommandSpec(
        "warehouse-check-kline-daily-parquet",
        "【仓库】日K Parquet vs PG 月度对账",
        "warehouse",
        "check-kline-daily-parquet",
        "仓库",
        "anytime",
        False,
        _wrap(runners.run_warehouse_check_kline_daily_parquet),
    ),
)

_COMMAND_MAP: dict[str, EtlCommandSpec] = {spec.command_key: spec for spec in ETL_COMMANDS}


def all_command_specs() -> tuple[EtlCommandSpec, ...]:
    return ETL_COMMANDS


def get_command_spec(command_key: str) -> EtlCommandSpec:
    spec = _COMMAND_MAP.get(command_key)
    if spec is None:
        raise KeyError(f"unknown command_key: {command_key}")
    return spec


def validate_command_keys(command_keys: list[str]) -> None:
    unknown = [k for k in command_keys if k not in _COMMAND_MAP]
    if unknown:
        raise ValueError(f"unknown command_key: {', '.join(unknown)}")


def run_command(command_key: str, *, progress_queue=None) -> int | None:
    runner = get_command_spec(command_key).runner
    if progress_queue is None:
        return runner()
    try:
        return runner(progress_queue=progress_queue)
    except TypeError:
        return runner()


def get_menu_handler(command_key: str) -> CommandRunner:
    return get_command_spec(command_key).runner


def menu_rows() -> list[tuple[str, str]]:
    return [(spec.label, spec.command_key) for spec in ETL_COMMANDS]
