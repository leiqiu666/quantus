"""Admin 量化数据源看板：group / 列 / SSE 任务配置（单一事实源）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DateKeyType = Literal["trade_date", "report_period", "ann_date", "month"]


@dataclass(frozen=True)
class DashboardColumn:
    key: str
    label: str
    threshold: float = 0.95
    sse_task_key: str = ""
    source_name: str | None = None
    count_field: str | None = None


@dataclass(frozen=True)
class DashboardGroup:
    group_id: str
    title: str
    date_key_type: DateKeyType
    date_label: str
    columns: tuple[DashboardColumn, ...]
    start_default_env: str | None = None


DASHBOARD_GROUPS: dict[str, DashboardGroup] = {
    "financial_report_period": DashboardGroup(
        group_id="financial_report_period",
        title="财务类 / 报告期",
        date_key_type="report_period",
        date_label="报告期",
        start_default_env="financial_report",
        columns=(
            DashboardColumn("report_income", "利润表", count_field="report_income_count", sse_task_key="report_income_history_init"),
            DashboardColumn("report_balance", "资产负债表", count_field="report_balance_count", sse_task_key="report_balance_history_init"),
            DashboardColumn("report_cashflow", "现金流量表", count_field="report_cashflow_count", sse_task_key="report_cashflow_history_init"),
            DashboardColumn("report_indicator", "财务指标", count_field="report_indicator_count", sse_task_key="report_indicator_history_init"),
            DashboardColumn("financial_forecast", "业绩预告", source_name="financial_forecast", sse_task_key="financial_forecast_check"),
            DashboardColumn("financial_express", "业绩快报", source_name="financial_express", sse_task_key="financial_express_check"),
            DashboardColumn("financial_audit", "审计意见", source_name="financial_audit", sse_task_key="financial_audit_check"),
            DashboardColumn("financial_disclosure_date", "披露计划", source_name="financial_disclosure_date", sse_task_key="financial_disclosure_date_check"),
            DashboardColumn("financial_fina_mainbz", "主营构成", source_name="financial_fina_mainbz", sse_task_key="financial_fina_mainbz_check"),
        ),
    ),
    "financial_ann_date": DashboardGroup(
        group_id="financial_ann_date",
        title="财务类 / 公告日",
        date_key_type="ann_date",
        date_label="公告日",
        start_default_env="financial_stock_holder",
        columns=(
            DashboardColumn("financial_stock_holder", "股东户数", source_name="financial_stock_holder", sse_task_key="financial_stock_holder_check"),
            DashboardColumn("financial_shareholder_top10", "前十大股东", source_name="financial_shareholder_top10", sse_task_key="financial_shareholder_check"),
            DashboardColumn("financial_top10_floatholders", "前十大流通股东", source_name="financial_top10_floatholders", sse_task_key="financial_top10_floatholders_check"),
        ),
    ),
    "kline_trade_date": DashboardGroup(
        group_id="kline_trade_date",
        title="K线类 / 交易日",
        date_key_type="trade_date",
        date_label="交易日",
        start_default_env="kline_daily",
        columns=(
            DashboardColumn("kline_daily", "日K", count_field="kline_daily_count", sse_task_key="kline_daily_check"),
            DashboardColumn("kline_adj_factor", "复权因子", count_field="kline_adj_factor_count", sse_task_key="kline_adj_factor_check"),
            DashboardColumn("kline_stk_limit", "涨跌停", count_field="kline_stk_limit_count", sse_task_key="kline_stk_limit_check"),
            DashboardColumn("kline_stock_factor", "技术因子", source_name="kline_stock_factor", sse_task_key="kline_stock_factor_check"),
        ),
    ),
    "market_trade_date": DashboardGroup(
        group_id="market_trade_date",
        title="市场类 / 交易日",
        date_key_type="trade_date",
        date_label="交易日",
        start_default_env="market_daily_basic",
        columns=(
            DashboardColumn("market_daily_basic", "每日指标", source_name="market_daily_basic", sse_task_key="market_daily_basic_check"),
            DashboardColumn("market_moneyflow", "资金流向", source_name="market_moneyflow", threshold=0.92, sse_task_key="market_moneyflow_check"),
            DashboardColumn("market_margin_detail", "融资融券", source_name="market_margin_detail", sse_task_key="market_margin_check"),
            DashboardColumn("market_northbound_top10", "北向十大", source_name="market_northbound_top10", sse_task_key="market_northbound_check"),
            DashboardColumn("market_moneyflow_hsgt", "沪深港通资金", source_name="market_moneyflow_hsgt", sse_task_key="market_hsgt_check"),
            DashboardColumn("market_hk_hold", "港股通持股", source_name="market_hk_hold", sse_task_key="market_hk_hold_check"),
            DashboardColumn("market_block_trade", "大宗交易", source_name="market_block_trade", sse_task_key="market_block_trade_check"),
            DashboardColumn("dragon_tiger", "龙虎榜", source_name="dragon_tiger", sse_task_key="dragon_tiger_check"),
        ),
    ),
    "index_month": DashboardGroup(
        group_id="index_month",
        title="指数类 / 月",
        date_key_type="month",
        date_label="月份",
        start_default_env="index_weight",
        columns=(
            DashboardColumn("index_weight", "指数权重", source_name="index_weight", sse_task_key="index_weight_check"),
            DashboardColumn("index_basic", "指数基本信息", sse_task_key="index_basic_pull"),
            DashboardColumn("index_classify", "申万分类", sse_task_key="index_classify_pull"),
            DashboardColumn("index_member_all", "申万成分", sse_task_key="index_member_all_pull"),
        ),
    ),
    "index_trade_date": DashboardGroup(
        group_id="index_trade_date",
        title="指数类 / 交易日",
        date_key_type="trade_date",
        date_label="交易日",
        start_default_env="index_daily",
        columns=(
            DashboardColumn("index_daily", "指数日线", source_name="index_daily", sse_task_key="index_daily_check"),
        ),
    ),
    "stock_basic_trade_date": DashboardGroup(
        group_id="stock_basic_trade_date",
        title="基础类 / 交易日",
        date_key_type="trade_date",
        date_label="交易日",
        start_default_env="stock_suspend",
        columns=(
            DashboardColumn("stock_suspend", "停复牌", count_field="stock_suspend_count", threshold=0.0, sse_task_key="stock_suspend_pull"),
            DashboardColumn("stock_premarket", "盘前股本", source_name="stock_premarket", sse_task_key="stock_premarket_check"),
            DashboardColumn("stock_share_float", "限售解禁", source_name="stock_share_float", sse_task_key="stock_share_float_check"),
        ),
    ),
}


def get_dashboard_group(group_id: str) -> DashboardGroup:
    group = DASHBOARD_GROUPS.get(group_id)
    if group is None:
        raise KeyError(f"unknown dashboard group: {group_id}")
    return group


def all_sse_task_keys() -> set[str]:
    keys: set[str] = set()
    for group in DASHBOARD_GROUPS.values():
        for col in group.columns:
            if col.sse_task_key:
                keys.add(col.sse_task_key)
    return keys


GROUP_DETAIL_PATHS: dict[str, str] = {
    "financial_report_period": "/data-source/financial/period",
    "financial_ann_date": "/data-source/financial/ann-date",
    "kline_trade_date": "/data-source/kline/trade-date",
    "market_trade_date": "/data-source/market/trade-date",
    "index_month": "/data-source/index/month",
    "index_trade_date": "/data-source/index/trade-date",
    "stock_basic_trade_date": "/data-source/stock/trade-date",
}
