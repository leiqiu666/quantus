"""ETL 菜单命令执行函数：直接调 Strategy，供 CLI 与调度系统共用。"""

from __future__ import annotations

from src.etl.strategy.financial.financial_audit_strategy import AuditStrategy
from src.etl.strategy.financial.financial_disclosure_date_strategy import DisclosureDateStrategy
from src.etl.strategy.financial.financial_express_strategy import ExpressStrategy
from src.etl.strategy.financial.financial_fina_mainbz_strategy import FinaMainbzStrategy
from src.etl.strategy.financial.financial_forecast_strategy import ForecastStrategy
from src.etl.strategy.financial.financial_top10_floatholders_strategy import Top10FloatholdersStrategy
from src.etl.strategy.financial.financial_report_strategy import ReportStrategy
from src.etl.strategy.financial.financial_shareholder_strategy import ShareholderStrategy
from src.etl.strategy.financial.financial_stock_holder_strategy import StkHoldernumberStrategy
from src.etl.strategy.index.index_weight_strategy import IndexWeightStrategy
from src.etl.strategy.kline.kline_stock_factor_strategy import StkFactorStrategy
from src.etl.strategy.kline.kline_strategy import KlineStrategy
from src.etl.strategy.market.market_block_trade_strategy import BlockTradeStrategy
from src.etl.strategy.market.market_daily_basic_strategy import DailyBasicStrategy
from src.etl.strategy.market.market_dividend_strategy import DividendStrategy
from src.etl.strategy.market.market_dragon_tiger_strategy import DragonTigerStrategy
from src.etl.strategy.market.market_margin_strategy import MarginStrategy
from src.etl.strategy.market.market_moneyflow_strategy import MoneyflowStrategy
from src.etl.strategy.market.market_northbound_strategy import HsgtStrategy
from src.etl.strategy.stock.stock_active_count_strategy import StockActiveCountStrategy
from src.etl.strategy.stock.stock_strategy import StockStrategy
from src.etl.strategy.stock.stock_suspend_strategy import SuspendStrategy
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.strategy.warehouse.warehouse_kline_daily_strategy import KlineDailyWarehouseStrategy


def run_report_history_init() -> None:
    ReportStrategy().report_history_init_all()


def run_stock_pull_list_a() -> None:
    StockStrategy().pull_stock_list_a()


def run_stock_refresh_active_count() -> int:
    return StockActiveCountStrategy().refresh_active_count()


def run_stock_backfill_delist_date() -> int:
    stats = StockStrategy().backfill_delist_date_from_kline()
    return stats.get("updated", 0)


def run_trade_cal_pull_history() -> int:
    return TradeCalStrategy().pull_trade_cal_history()


def run_suspend_pull_by_date() -> int:
    return SuspendStrategy().pull_suspend_by_date()


def run_kline_pull_daily_by_date_range() -> int:
    return KlineStrategy().pull_kline_daily_by_date_range()


def run_kline_pull_adj_factor_by_date_range() -> int:
    return KlineStrategy().pull_kline_adj_factor_by_date_range()


def run_kline_pull_stk_limit_by_date_range() -> int:
    return KlineStrategy().pull_kline_stk_limit_by_date_range()


def run_daily_basic_pull_by_date_range() -> int:
    return DailyBasicStrategy().pull_daily_basic_by_date_range()


def run_dividend_pull_by_date_range() -> int:
    return DividendStrategy().pull_dividend_by_date_range()


def run_stk_factor_pull_by_date_range() -> int:
    return StkFactorStrategy().pull_stk_factor_by_date_range()


def run_moneyflow_pull_by_date_range() -> int:
    return MoneyflowStrategy().pull_moneyflow_by_date_range()


def run_margin_pull_detail_by_date_range() -> int:
    return MarginStrategy().pull_margin_detail_by_date_range()


def run_hsgt_pull_top10_by_date_range() -> int:
    return HsgtStrategy().pull_hsgt_top10_by_date_range()


def run_stk_holder_pull_number() -> int:
    return StkHoldernumberStrategy().pull_stk_holdernumber()


def run_index_pull_weight_by_month_range() -> int:
    return IndexWeightStrategy().pull_index_weight_by_month_range()


def run_dragon_tiger_pull_by_date_range() -> int:
    total_list, total_inst = DragonTigerStrategy().pull_dragon_tiger_by_date_range()
    return total_list + total_inst


def run_block_trade_pull_by_date_range() -> int:
    return BlockTradeStrategy().pull_block_trade_by_date_range()


def run_shareholder_pull_by_date() -> int:
    return ShareholderStrategy().pull_top10_holders_by_date()


def run_floatholders_pull_by_date() -> int:
    return Top10FloatholdersStrategy().pull_top10_floatholders_by_date()


def run_forecast_pull_by_period() -> int:
    return ForecastStrategy().pull_forecast_vip_by_period()


def run_express_pull_by_period() -> int:
    return ExpressStrategy().pull_express_vip_by_period()


def run_audit_pull_by_period() -> int:
    return AuditStrategy().pull_fina_audit_by_period()


def run_disclosure_date_pull_by_period() -> int:
    return DisclosureDateStrategy().pull_disclosure_date_by_period()


def run_fina_mainbz_pull_by_period() -> int:
    return FinaMainbzStrategy().pull_fina_mainbz_by_period()


def run_warehouse_pull_kline_daily_by_month_range() -> int:
    return KlineDailyWarehouseStrategy().dump_by_month_range()


def run_warehouse_check_kline_daily_parquet() -> None:
    KlineDailyWarehouseStrategy().check_parquet_vs_pg()
