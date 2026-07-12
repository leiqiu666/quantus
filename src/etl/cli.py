import typer
from typing import Callable

from src.etl.strategy.market.market_daily_basic_strategy import DailyBasicStrategy
from src.etl.strategy.market.market_dividend_strategy import DividendStrategy
from src.etl.strategy.market.market_moneyflow_strategy import MoneyflowStrategy
from src.etl.strategy.market.market_moneyflow_hsgt_strategy import MoneyflowHsgtStrategy
from src.etl.strategy.market.market_margin_strategy import MarginStrategy
from src.etl.strategy.market.market_northbound_strategy import HsgtStrategy
from src.etl.strategy.market.market_hk_hold_strategy import HkHoldStrategy
from src.etl.strategy.financial.financial_stock_holder_strategy import StkHoldernumberStrategy
from src.etl.strategy.index.index_basic_strategy import IndexBasicStrategy
from src.etl.strategy.index.index_classify_strategy import IndexClassifyStrategy
from src.etl.strategy.index.index_daily_strategy import IndexDailyStrategy
from src.etl.strategy.index.index_member_all_strategy import IndexMemberAllStrategy
from src.etl.strategy.index.index_weight_strategy import IndexWeightStrategy
from src.etl.strategy.financial.financial_report_strategy import ReportStrategy
from src.etl.strategy.kline.kline_strategy import KlineStrategy
from src.etl.strategy.stock.stock_active_count_strategy import StockActiveCountStrategy
from src.etl.strategy.stock.stock_strategy import StockStrategy
from src.etl.strategy.kline.kline_stock_factor_strategy import StkFactorStrategy
from src.etl.strategy.stock.stock_premarket_strategy import StockPremarketStrategy
from src.etl.strategy.stock.stock_share_float_strategy import StockShareFloatStrategy
from src.etl.strategy.stock.stock_suspend_strategy import SuspendStrategy
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.strategy.warehouse.warehouse_kline_daily_strategy import (
    KlineDailyWarehouseStrategy,
)
from src.etl.strategy.market.market_dragon_tiger_strategy import DragonTigerStrategy
from src.etl.strategy.market.market_block_trade_strategy import BlockTradeStrategy
from src.etl.strategy.financial.financial_shareholder_strategy import ShareholderStrategy
from src.etl.strategy.financial.financial_forecast_strategy import ForecastStrategy
from src.etl.strategy.financial.financial_express_strategy import ExpressStrategy
from src.etl.strategy.financial.financial_audit_strategy import AuditStrategy
from src.etl.strategy.financial.financial_disclosure_date_strategy import DisclosureDateStrategy
from src.etl.strategy.financial.financial_top10_floatholders_strategy import Top10FloatholdersStrategy
from src.etl.strategy.financial.financial_fina_mainbz_strategy import FinaMainbzStrategy
from src.scheduler.command_registry import get_menu_handler, menu_rows

# create typer app
app = typer.Typer()


def _cli_echo(message: str, *, silent: bool = False, err: bool = False) -> None:
    if not silent:
        typer.echo(message, err=err)

# define command groups to clarify structure and purpose
report_strategy = typer.Typer()
app.add_typer(report_strategy, name="report", help="Report strategy commands")
stock_strategy = typer.Typer()
app.add_typer(stock_strategy, name="stock", help="Stock ETL commands")
kline_strategy = typer.Typer()
app.add_typer(kline_strategy, name="kline", help="K 线 ETL commands")
trade_cal_strategy = typer.Typer()
app.add_typer(trade_cal_strategy, name="trade-cal", help="交易日历 ETL commands")
suspend_strategy = typer.Typer()
app.add_typer(suspend_strategy, name="suspend", help="停复牌 ETL commands")
stock_premarket_strategy = typer.Typer()
app.add_typer(stock_premarket_strategy, name="stock_premarket", help="盘前股本 ETL commands")
stock_share_float_strategy = typer.Typer()
app.add_typer(stock_share_float_strategy, name="stock_share_float", help="限售股解禁 ETL commands")
daily_basic_strategy = typer.Typer()
app.add_typer(daily_basic_strategy, name="daily-basic", help="每日指标 ETL commands")
dividend_strategy = typer.Typer()
app.add_typer(dividend_strategy, name="market_dividend", help="分红送股 ETL commands")
moneyflow_strategy = typer.Typer()
app.add_typer(moneyflow_strategy, name="market_moneyflow", help="资金流向 ETL commands")
market_hsgt_strategy = typer.Typer()
app.add_typer(market_hsgt_strategy, name="market_hsgt", help="沪深港通资金流向 ETL commands")
market_hk_hold_strategy = typer.Typer()
app.add_typer(market_hk_hold_strategy, name="market_hk_hold", help="港股通持股 ETL commands")
margin_strategy = typer.Typer()
app.add_typer(margin_strategy, name="margin", help="融资融券 ETL commands")
hsgt_strategy = typer.Typer()
app.add_typer(hsgt_strategy, name="hsgt", help="沪深股通 ETL commands")
stk_holder_strategy = typer.Typer()
app.add_typer(stk_holder_strategy, name="stk-holder", help="股东户数 ETL commands")
index_strategy = typer.Typer()
app.add_typer(index_strategy, name="index", help="指数 ETL commands")
stk_factor_strategy = typer.Typer()
app.add_typer(stk_factor_strategy, name="stk-factor", help="技术面因子 ETL commands")
dragon_tiger_strategy = typer.Typer()
app.add_typer(dragon_tiger_strategy, name="dragon-tiger", help="龙虎榜 ETL commands")
block_trade_strategy = typer.Typer()
app.add_typer(block_trade_strategy, name="block-trade", help="大宗交易 ETL commands")
shareholder_strategy = typer.Typer()
app.add_typer(shareholder_strategy, name="shareholder", help="股东数据 ETL commands")
forecast_strategy = typer.Typer()
app.add_typer(forecast_strategy, name="financial_forecast", help="业绩预告 ETL commands")
express_strategy = typer.Typer()
app.add_typer(express_strategy, name="financial_express", help="业绩快报 ETL commands")
audit_strategy = typer.Typer()
app.add_typer(audit_strategy, name="audit", help="财务审计意见 ETL commands")
disclosure_date_strategy = typer.Typer()
app.add_typer(disclosure_date_strategy, name="financial_disclosure_date", help="财报披露计划 ETL commands")
fina_mainbz_strategy = typer.Typer()
app.add_typer(fina_mainbz_strategy, name="financial_fina_mainbz", help="主营业务构成 ETL commands")
warehouse_strategy = typer.Typer()
app.add_typer(warehouse_strategy, name="warehouse", help="数据仓库 ETL commands (PG → Parquet)")
_MENU_ROWS: list[tuple[str, str]] = menu_rows()


def _run_interactive_menu() -> None:
    typer.echo("选择要执行的任务：")
    for idx, (label, _) in enumerate(_MENU_ROWS, start=1):
        typer.echo(f"  {idx:>2}. {label}")
    quit_idx = len(_MENU_ROWS) + 1
    typer.echo(f"  {quit_idx:>2}. 退出")

    try:
        raw = input("请输入序号（回车=退出）: ").strip()
    except EOFError:
        return

    if raw == "" or raw == str(quit_idx):
        return
    if not raw.isdigit():
        typer.echo(f"[错误] 无效输入: {raw!r}", err=True)
        raise typer.Exit(1)

    choice = int(raw)
    if not (1 <= choice <= len(_MENU_ROWS)):
        typer.echo(f"[错误] 序号超出范围: {choice}", err=True)
        raise typer.Exit(1)

    _, key = _MENU_ROWS[choice - 1]
    handler = _MENU_HANDLERS.get(key)
    if handler is None:
        typer.echo(f"[错误] 未注册菜单项: {key}", err=True)
        raise typer.Exit(1)
    handler()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    _run_interactive_menu()
    raise typer.Exit(0)


# the function register as command
@report_strategy.command("report-history-init")
def report_history_init():
    """income→balance→cashflow→indicator 四表按报告期 VIP 批量入库，跑完统一刷一次宏观快照。无 CLI 参数。"""
    ReportStrategy().report_history_init_all()


@report_strategy.command("check-report-complete")
def check_report_complete():
    """宏观→三表微观查漏补拉→宏观。无 CLI 参数。"""
    total = ReportStrategy().check_report_complete_history_all_with_snapshot()
    typer.echo(f"财报完整性检查累计发现缺期 {total} 条")


def _run_report_update_period_count(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    n = ReportStrategy().refresh_report_macro_snapshot(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"report_period_count 快照刷新 {n} 条", silent=silent)


@report_strategy.command("update-period-count")
def report_update_period_count(
    start_date: str | None = typer.Option(
        None, "--start-date", help="起始报告期 YYYYMMDD，默认 REPORT_PERIOD_COUNT_START_DATE"
    ),
    end_date: str | None = typer.Option(None, "--end-date", help="结束报告期 YYYYMMDD，默认今日"),
) -> None:
    """刷新 report_period_count 完整性快照（含 income/balance/cashflow/indicator 四列）。"""
    _run_report_update_period_count(start_date=start_date, end_date=end_date)


@stock_strategy.command("pull-list-a")
def stock_pull_list_a():
    """Tushare stock_basic 全量拉取并按 ts_code upsert 到 stock_list；无参数，返回值不打印。"""
    stock_strat = StockStrategy()
    stock_strat.pull_stock_list_a()


def _run_stock_refresh_active_count(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    n = StockActiveCountStrategy().refresh_active_count(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"活跃股票数快照落库 {n} 条", silent=silent)


@stock_strategy.command("refresh-active-count")
def stock_refresh_active_count(
    start_date: str | None = typer.Option(
        None, "--start-date", help="起始日 YYYYMMDD，默认 STOCK_ACTIVE_COUNT_START_DATE"
    ),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """刷新 stock_active_count：listed_count（未退市）与 trading_count（应交易）。"""
    _run_stock_refresh_active_count(start_date=start_date, end_date=end_date)


@stock_strategy.command("backfill-delist-date")
def stock_backfill_delist_date(
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不写库"),
    report_path: str = typer.Option(
        "docs/analysis/delist-date-backfill-from-kline.md",
        "--report-path",
        help="Markdown 报告路径",
    ),
) -> None:
    """名称含 (退)/（退）的股票：用 kline_daily 最后 trade_date 回填 stock_list.delist_date。"""
    stats = StockStrategy().backfill_delist_date_from_kline(
        dry_run=dry_run,
        report_path=report_path,
    )
    typer.echo(
        f"合计 {stats['total']} 只，更新 {stats['updated']}，"
        f"无日K {stats['skipped_no_kline']}，未变 {stats['skipped_unchanged']}；"
        f"报告 {stats['report_path']}"
    )


@kline_strategy.command("pull-adj-factor-by-date")
def kline_pull_adj_factor_by_date(
    trade_date: str = typer.Option(..., "--trade-date", help="交易日 YYYYMMDD"),
) -> None:
    """按单个交易日拉取全市场复权因子（tushare），结束后刷新宏观快照。"""
    total = KlineStrategy().pull_kline_adj_factor_by_date_with_finalize(trade_date)
    typer.echo(f"{trade_date} 复权因子写入 {total} 条")


def _run_pull_kline_adj_factor_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = KlineStrategy().pull_kline_adj_factor_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"复权因子 by date 区间累计写入 {total} 条", silent=silent)


@kline_strategy.command("pull-adj-factor-by-date-range")
def kline_pull_adj_factor_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 KLINE_DAILY_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按交易日区间增量拉取全市场复权因子（仅 95% 未达标开市日）。"""
    _run_pull_kline_adj_factor_by_date_range(start_date=start_date, end_date=end_date)


@kline_strategy.command("pull-daily-by-date")
def kline_pull_daily_by_date(
    trade_date: str = typer.Option(..., "--trade-date", help="交易日 YYYYMMDD"),
) -> None:
    """按单个交易日拉取全市场日线（tushare 优先，tdx_quant 降级），结束后刷新宏观快照。"""
    total = KlineStrategy().pull_kline_daily_by_date_with_finalize(trade_date)
    typer.echo(f"{trade_date} 日线写入 {total} 条")


def _run_pull_kline_daily_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = KlineStrategy().pull_kline_daily_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"按 date 区间累计写入 {total} 条", silent=silent)


@kline_strategy.command("pull-daily-by-date-range")
def kline_pull_daily_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 KLINE_DAILY_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按交易日区间增量拉取全市场日线（仅开市日）。"""
    _run_pull_kline_daily_by_date_range(start_date=start_date, end_date=end_date)


def _run_kline_update_daily_period_count(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    n = KlineStrategy().refresh_kline_macro_snapshot(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"kline_daily_period_count 快照刷新 {n} 条", silent=silent)


@kline_strategy.command("update-daily-period-count")
def kline_update_daily_period_count(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 KLINE_DAILY_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """刷新 kline_daily_period_count 完整性快照（含日线/复权/涨跌停四列）。"""
    _run_kline_update_daily_period_count(start_date=start_date, end_date=end_date)


@kline_strategy.command("update-adj-factor-period-count", hidden=True)
def kline_update_adj_factor_period_count(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 KLINE_DAILY_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """[别名] 同 update-daily-period-count。"""
    _run_kline_update_daily_period_count(start_date=start_date, end_date=end_date)


@kline_strategy.command("update-stk-limit-period-count", hidden=True)
def kline_update_stk_limit_period_count(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 KLINE_DAILY_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """[别名] 同 update-daily-period-count。"""
    _run_kline_update_daily_period_count(start_date=start_date, end_date=end_date)


def _run_kline_check_complete(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    missing = KlineStrategy().check_kline_complete_history(
        start_date=start_date,
        end_date=end_date,
    )
    if not silent:
        _cli_echo(f"K线完整性检查累计发现缺日 {missing} 条", silent=silent)


@kline_strategy.command("check-complete")
def check_kline_complete(
    start_date: str | None = typer.Option(
        None, "--start-date", help="起始日 YYYYMMDD；指定时走窗口宏观补拉，否则全历史微观扫描"
    ),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """K 线完整性：默认全 A 股微观扫描；传 --start-date/--end-date 时按窗口 pull 补拉。"""
    _run_kline_check_complete(start_date=start_date, end_date=end_date)


@kline_strategy.command("check-daily-complete", hidden=True)
def check_kline_daily_complete() -> None:
    """[别名] 仅检查日线维度，见 check-complete。"""
    KlineStrategy().check_kline_daily_complete_history()


@kline_strategy.command("check-adj-factor-complete", hidden=True)
def check_kline_adj_factor_complete() -> None:
    """[别名] 仅检查复权因子维度，见 check-complete。"""
    KlineStrategy().check_kline_adj_factor_complete_history()


@kline_strategy.command("pull-stk-limit-by-date")
def kline_pull_stk_limit_by_date(
    trade_date: str = typer.Option(..., "--trade-date", help="交易日 YYYYMMDD"),
) -> None:
    """按单个交易日拉取全市场涨跌停价（tushare stk_limit），结束后刷新宏观快照。"""
    total = KlineStrategy().pull_kline_stk_limit_by_date_with_finalize(trade_date)
    typer.echo(f"{trade_date} 涨跌停写入 {total} 条")


def _run_pull_kline_stk_limit_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = KlineStrategy().pull_kline_stk_limit_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"涨跌停 by date 区间累计写入 {total} 条", silent=silent)


@kline_strategy.command("pull-stk-limit-by-date-range")
def kline_pull_stk_limit_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 KLINE_DAILY_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按交易日区间增量拉取全市场涨跌停价（仅 95% 未达标开市日）。"""
    _run_pull_kline_stk_limit_by_date_range(start_date=start_date, end_date=end_date)


@kline_strategy.command("check-stk-limit-complete", hidden=True)
def check_kline_stk_limit_complete() -> None:
    """[别名] 仅检查涨跌停维度，见 check-complete。"""
    KlineStrategy().check_kline_stk_limit_complete_history()


@trade_cal_strategy.command("pull-history")
def trade_cal_pull_history(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 TRADE_CAL_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """7 所交易日历 Tushare 增量入库 trade_cal（含休市日）。交互菜单不传日期且无 typer.echo。"""
    total = TradeCalStrategy().pull_trade_cal_history(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"交易日历累计写入 {total} 条")


def _run_suspend_pull_by_date(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = SuspendStrategy().pull_suspend_by_date(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"停复牌累计写入 {total} 条", silent=silent)


@suspend_strategy.command("pull-by-date")
def suspend_pull_by_date(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 SUSPEND_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare suspend_d 并 upsert 到 suspend_d（含 S 停牌 / R 复牌）。"""
    _run_suspend_pull_by_date(start_date=start_date, end_date=end_date)


def _run_stock_premarket_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = StockPremarketStrategy().pull_premarket_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"盘前股本累计写入 {total} 条", silent=silent)


@stock_premarket_strategy.command("pull-by-date-range")
def stock_premarket_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 STOCK_PREMARKET_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare stk_premarket 并 upsert。"""
    _run_stock_premarket_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_stock_share_float_pull_by_date(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = StockShareFloatStrategy().pull_share_float_by_date(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"限售股解禁累计写入 {total} 条", silent=silent)


@stock_share_float_strategy.command("pull-by-date")
def stock_share_float_pull_by_date(
    start_date: str | None = typer.Option(None, "--start-date", help="解禁日起点 YYYYMMDD，默认 STOCK_SHARE_FLOAT_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="解禁日终点 YYYYMMDD，默认今日"),
) -> None:
    """按解禁日逐日拉取 Tushare share_float 全市场并 upsert。"""
    _run_stock_share_float_pull_by_date(start_date=start_date, end_date=end_date)


def _run_daily_basic_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = DailyBasicStrategy().pull_daily_basic_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"每日指标累计写入 {total} 条", silent=silent)


@daily_basic_strategy.command("pull-by-date-range")
def daily_basic_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 DAILY_BASIC_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare daily_basic 并 upsert（PE/PB/PS/市值/换手率等）。"""
    _run_daily_basic_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_dividend_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = DividendStrategy().pull_dividend_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"分红送股累计写入 {total} 条", silent=silent)


@dividend_strategy.command("pull-by-date-range")
def dividend_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 DIVIDEND_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare dividend 并 upsert（现金分红/送转/除权除息日）。"""
    _run_dividend_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_stk_holder_pull_number(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = StkHoldernumberStrategy().pull_stk_holdernumber(
        start_date=start_date, end_date=end_date,
    )
    _cli_echo(f"股东户数累计写入 {total} 条", silent=silent)


@stk_holder_strategy.command("pull-number")
def stk_holder_pull_number(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 STK_HOLDERNUMBER_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按公告日逐日拉取 Tushare stk_holdernumber 全市场并 upsert。"""
    _run_stk_holder_pull_number(start_date=start_date, end_date=end_date)


def _run_index_pull_weight_by_month_range(
    start_month: str | None = None,
    end_month: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = IndexWeightStrategy().pull_index_weight_by_month_range(
        start_month=start_month, end_month=end_month,
    )
    _cli_echo(f"指数权重累计写入 {total} 条", silent=silent)


@index_strategy.command("pull-weight-by-month-range")
def index_pull_weight_by_month_range(
    start_month: str | None = typer.Option(None, "--start-month", help="起始月 YYYYMM，默认 INDEX_WEIGHT_START_MONTH"),
    end_month: str | None = typer.Option(None, "--end-month", help="结束月 YYYYMM，默认当月"),
) -> None:
    """按月 × 指数拉取 Tushare index_weight 并 upsert（沪深300/中证500/中证1000/创业板指）。"""
    _run_index_pull_weight_by_month_range(start_month=start_month, end_month=end_month)


def _run_index_pull_basic_snapshot(*, silent: bool = False) -> None:
    total = IndexBasicStrategy().pull_snapshot()
    _cli_echo(f"指数基本信息累计写入 {total} 条", silent=silent)


@index_strategy.command("pull-basic-snapshot")
def index_pull_basic_snapshot() -> None:
    """全量拉取 Tushare index_basic 并 upsert。"""
    _run_index_pull_basic_snapshot()


def _run_index_pull_classify_snapshot(*, silent: bool = False) -> None:
    total = IndexClassifyStrategy().pull_snapshot()
    _cli_echo(f"申万行业分类累计写入 {total} 条", silent=silent)


@index_strategy.command("pull-classify-snapshot")
def index_pull_classify_snapshot() -> None:
    """全量拉取 Tushare index_classify（L1/L2/L3 × SW2021）并 upsert。"""
    _run_index_pull_classify_snapshot()


def _run_index_pull_member_all_snapshot(*, silent: bool = False) -> None:
    total = IndexMemberAllStrategy().pull_snapshot()
    _cli_echo(f"申万行业成分累计写入 {total} 条", silent=silent)


@index_strategy.command("pull-member-all-snapshot")
def index_pull_member_all_snapshot() -> None:
    """全量拉取 Tushare index_member_all（is_new=Y）并 upsert。"""
    _run_index_pull_member_all_snapshot()


def _run_index_pull_daily_by_code_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    ts_code: str | None = None,
    silent: bool = False,
) -> None:
    total = IndexDailyStrategy().pull_index_daily_by_code_range(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
    )
    _cli_echo(f"指数日线累计写入 {total} 条", silent=silent)


@index_strategy.command("pull-daily-by-code-range")
def index_pull_daily_by_code_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 INDEX_DAILY_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
    ts_code: str | None = typer.Option(None, "--ts-code", help="指定指数代码，默认遍历预设指数列表"),
) -> None:
    """按指数代码区间拉取 Tushare index_daily 并 upsert。"""
    _run_index_pull_daily_by_code_range(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
    )


def _run_hsgt_pull_top10_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = HsgtStrategy().pull_hsgt_top10_by_date_range(
        start_date=start_date, end_date=end_date,
    )
    _cli_echo(f"沪深股通十大成交累计写入 {total} 条", silent=silent)


@hsgt_strategy.command("pull-top10-by-date-range")
def hsgt_pull_top10_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 HSGT_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare hsgt_top10 并 upsert。"""
    _run_hsgt_pull_top10_by_date_range(start_date=start_date, end_date=end_date)


def _run_margin_pull_detail_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = MarginStrategy().pull_margin_detail_by_date_range(
        start_date=start_date, end_date=end_date,
    )
    _cli_echo(f"融资融券明细累计写入 {total} 条", silent=silent)


@margin_strategy.command("pull-detail-by-date-range")
def margin_pull_detail_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 MARGIN_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare margin_detail 并 upsert。"""
    _run_margin_pull_detail_by_date_range(start_date=start_date, end_date=end_date)


def _run_moneyflow_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = MoneyflowStrategy().pull_moneyflow_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"资金流向累计写入 {total} 条", silent=silent)


@moneyflow_strategy.command("pull-by-date-range")
def moneyflow_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 MONEYFLOW_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare moneyflow 并 upsert（大/中/小单买卖）。"""
    _run_moneyflow_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_market_hsgt_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = MoneyflowHsgtStrategy().pull_moneyflow_hsgt_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"沪深港通资金流向累计写入 {total} 条", silent=silent)


@market_hsgt_strategy.command("pull-by-date-range")
def market_hsgt_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 HSGT_FLOW_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare moneyflow_hsgt 并 upsert。"""
    _run_market_hsgt_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_market_hk_hold_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = HkHoldStrategy().pull_hk_hold_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"港股通持股累计写入 {total} 条", silent=silent)


@market_hk_hold_strategy.command("pull-by-date-range")
def market_hk_hold_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 HK_HOLD_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare hk_hold 并 upsert。"""
    _run_market_hk_hold_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_stk_factor_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = StkFactorStrategy().pull_stk_factor_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"技术面因子累计写入 {total} 条", silent=silent)


@stk_factor_strategy.command("pull-by-date-range")
def stk_factor_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 STK_FACTOR_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日拉取 Tushare stk_factor_pro 并 upsert（MACD/KDJ/RSI/BOLL/CCI，后复权）。"""
    _run_stk_factor_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_dragon_tiger_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total_list, total_inst = DragonTigerStrategy().pull_dragon_tiger_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"龙虎榜 list 写入 {total_list} 条，inst 写入 {total_inst} 条", silent=silent)


@dragon_tiger_strategy.command("pull-by-date-range")
def dragon_tiger_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 DRAGON_TIGER_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare top_list + top_inst 并 upsert。"""
    _run_dragon_tiger_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_block_trade_pull_by_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = BlockTradeStrategy().pull_block_trade_by_date_range(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"大宗交易累计写入 {total} 条", silent=silent)


@block_trade_strategy.command("pull-by-date-range")
def block_trade_pull_by_date_range(
    start_date: str | None = typer.Option(None, "--start-date", help="起始日 YYYYMMDD，默认 BLOCK_TRADE_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="结束日 YYYYMMDD，默认今日"),
) -> None:
    """按 SSE 开市日逐日拉取 Tushare block_trade 并 upsert（支持分页）。"""
    _run_block_trade_pull_by_date_range(start_date=start_date, end_date=end_date)


def _run_shareholder_pull_by_date(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = ShareholderStrategy().pull_top10_holders_by_date(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"前十大股东累计写入 {total} 条", silent=silent)


@shareholder_strategy.command("pull-by-date")
def shareholder_pull_by_date(
    start_date: str | None = typer.Option(None, "--start-date", help="公告日起点 YYYYMMDD，默认 SHAREHOLDER_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="公告日终点 YYYYMMDD，默认今日"),
) -> None:
    """按公告日逐日拉取 Tushare top10_holders 全市场并 upsert。"""
    _run_shareholder_pull_by_date(start_date=start_date, end_date=end_date)


def _run_floatholders_pull_by_date(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = Top10FloatholdersStrategy().pull_top10_floatholders_by_date(
        start_date=start_date,
        end_date=end_date,
    )
    _cli_echo(f"前十大流通股东累计写入 {total} 条", silent=silent)


@shareholder_strategy.command("pull-floatholders-by-date")
def floatholders_pull_by_date(
    start_date: str | None = typer.Option(None, "--start-date", help="公告日起点 YYYYMMDD，默认 TOP10_FLOATHOLDERS_START_DATE"),
    end_date: str | None = typer.Option(None, "--end-date", help="公告日终点 YYYYMMDD，默认今日"),
) -> None:
    """按公告日逐日拉取 Tushare top10_floatholders 全市场并 upsert。"""
    _run_floatholders_pull_by_date(start_date=start_date, end_date=end_date)


def _run_forecast_pull_by_period(
    start_period: str | None = None,
    end_period: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = ForecastStrategy().pull_forecast_vip_by_period(
        start_period=start_period,
        end_period=end_period,
    )
    _cli_echo(f"业绩预告累计写入 {total} 条", silent=silent)


@forecast_strategy.command("pull-by-period")
def forecast_pull_by_period(
    start_period: str | None = typer.Option(None, "--start-period", help="报告期起点 YYYYMMDD，默认 FORECAST_START_PERIOD"),
    end_period: str | None = typer.Option(None, "--end-period", help="报告期终点 YYYYMMDD，默认最新"),
) -> None:
    """按报告期全市场拉取 Tushare forecast_vip 并 upsert。"""
    _run_forecast_pull_by_period(start_period=start_period, end_period=end_period)


def _run_express_pull_by_period(
    start_period: str | None = None,
    end_period: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = ExpressStrategy().pull_express_vip_by_period(
        start_period=start_period,
        end_period=end_period,
    )
    _cli_echo(f"业绩快报累计写入 {total} 条", silent=silent)


@express_strategy.command("pull-by-period")
def express_pull_by_period(
    start_period: str | None = typer.Option(None, "--start-period", help="报告期起点 YYYYMMDD，默认 EXPRESS_START_PERIOD"),
    end_period: str | None = typer.Option(None, "--end-period", help="报告期终点 YYYYMMDD，默认最新"),
) -> None:
    """按报告期全市场拉取 Tushare express_vip 并 upsert。"""
    _run_express_pull_by_period(start_period=start_period, end_period=end_period)


def _run_audit_pull_by_period(
    start_period: str | None = None,
    end_period: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = AuditStrategy().pull_fina_audit_by_period(
        start_period=start_period,
        end_period=end_period,
    )
    _cli_echo(f"财务审计意见累计写入 {total} 条", silent=silent)


@audit_strategy.command("pull-by-period")
def audit_pull_by_period(
    start_period: str | None = typer.Option(None, "--start-period", help="报告期起点 YYYYMMDD，默认 AUDIT_START_PERIOD"),
    end_period: str | None = typer.Option(None, "--end-period", help="报告期终点 YYYYMMDD，默认最新"),
) -> None:
    """按报告期×全A股拉取 Tushare fina_audit（仅年报）并 upsert。"""
    _run_audit_pull_by_period(start_period=start_period, end_period=end_period)


def _run_disclosure_date_pull_by_period(
    start_period: str | None = None,
    end_period: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = DisclosureDateStrategy().pull_disclosure_date_by_period(
        start_period=start_period,
        end_period=end_period,
    )
    _cli_echo(f"财报披露计划累计写入 {total} 条", silent=silent)


@disclosure_date_strategy.command("pull-by-period")
def disclosure_date_pull_by_period(
    start_period: str | None = typer.Option(None, "--start-period", help="报告期起点 YYYYMMDD，默认 DISCLOSURE_DATE_START_DATE"),
    end_period: str | None = typer.Option(None, "--end-period", help="报告期终点 YYYYMMDD，默认最新"),
) -> None:
    """按报告期全市场拉取 Tushare disclosure_date 并 upsert。"""
    _run_disclosure_date_pull_by_period(start_period=start_period, end_period=end_period)


def _run_fina_mainbz_pull_by_period(
    start_period: str | None = None,
    end_period: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = FinaMainbzStrategy().pull_fina_mainbz_by_period(
        start_period=start_period,
        end_period=end_period,
    )
    _cli_echo(f"主营业务构成累计写入 {total} 条", silent=silent)


@fina_mainbz_strategy.command("pull-by-period")
def fina_mainbz_pull_by_period(
    start_period: str | None = typer.Option(None, "--start-period", help="报告期起点 YYYYMMDD，默认 FINA_MAINBZ_START_DATE"),
    end_period: str | None = typer.Option(None, "--end-period", help="报告期终点 YYYYMMDD，默认最新"),
) -> None:
    """按报告期×全A股拉取 Tushare fina_mainbz 并 upsert。"""
    _run_fina_mainbz_pull_by_period(start_period=start_period, end_period=end_period)


# ── 完整性保障命令（P4）──────────────────────────────────────

def _run_completeness_update(strategy_factory, label: str, start=None, end=None) -> None:
    n = strategy_factory().refresh_completeness_snapshot(start_date=start, end_date=end)
    _cli_echo(f"[{label}] 快照刷新 {n} 条")


def _run_completeness_check(strategy_factory, label: str, start=None, end=None) -> None:
    n = strategy_factory().check_complete(start_date=start, end_date=end)
    _cli_echo(f"[{label}] 完整性检查完成，累计补拉 {n} 条")


@daily_basic_strategy.command("update-period-count")
def daily_basic_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 daily_basic 完整性快照。"""
    _run_completeness_update(DailyBasicStrategy, "market_daily_basic", start_date, end_date)


@daily_basic_strategy.command("check-complete")
def daily_basic_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 daily_basic 完整性并补拉缺失日。"""
    _run_completeness_check(DailyBasicStrategy, "market_daily_basic", start_date, end_date)


@stock_premarket_strategy.command("update-period-count")
def stock_premarket_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 stock_premarket 完整性快照。"""
    _run_completeness_update(StockPremarketStrategy, "stock_premarket", start_date, end_date)


@stock_premarket_strategy.command("check-complete")
def stock_premarket_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 stock_premarket 完整性并补拉缺失日。"""
    _run_completeness_check(StockPremarketStrategy, "stock_premarket", start_date, end_date)


@stock_share_float_strategy.command("update-period-count")
def stock_share_float_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 stock_share_float 完整性快照。"""
    _run_completeness_update(StockShareFloatStrategy, "stock_share_float", start_date, end_date)


@stock_share_float_strategy.command("check-complete")
def stock_share_float_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 stock_share_float 完整性并缺日补拉。"""
    _run_completeness_check(StockShareFloatStrategy, "stock_share_float", start_date, end_date)


@dividend_strategy.command("update-period-count")
def dividend_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 dividend 完整性快照。"""
    _run_completeness_update(DividendStrategy, "market_dividend", start_date, end_date)


@dividend_strategy.command("check-complete")
def dividend_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 dividend 完整性并补拉缺失日。"""
    _run_completeness_check(DividendStrategy, "market_dividend", start_date, end_date)


@moneyflow_strategy.command("update-period-count")
def moneyflow_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 moneyflow 完整性快照。"""
    _run_completeness_update(MoneyflowStrategy, "market_moneyflow", start_date, end_date)


@moneyflow_strategy.command("check-complete")
def moneyflow_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 moneyflow 完整性并补拉缺失日。"""
    _run_completeness_check(MoneyflowStrategy, "market_moneyflow", start_date, end_date)


@margin_strategy.command("update-period-count")
def margin_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 margin_detail 完整性快照。"""
    _run_completeness_update(MarginStrategy, "market_margin_detail", start_date, end_date)


@margin_strategy.command("check-complete")
def margin_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 margin_detail 完整性并补拉缺失日。"""
    _run_completeness_check(MarginStrategy, "market_margin_detail", start_date, end_date)


@hsgt_strategy.command("update-period-count")
def hsgt_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 hsgt_top10 完整性快照。"""
    _run_completeness_update(HsgtStrategy, "market_northbound_top10", start_date, end_date)


@hsgt_strategy.command("check-complete")
def hsgt_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 hsgt_top10 完整性并补拉缺失日。"""
    _run_completeness_check(HsgtStrategy, "market_northbound_top10", start_date, end_date)


@market_hsgt_strategy.command("update-period-count")
def market_hsgt_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 moneyflow_hsgt 完整性快照。"""
    _run_completeness_update(MoneyflowHsgtStrategy, "market_moneyflow_hsgt", start_date, end_date)


@market_hsgt_strategy.command("check-complete")
def market_hsgt_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 moneyflow_hsgt 完整性并补拉缺失日。"""
    _run_completeness_check(MoneyflowHsgtStrategy, "market_moneyflow_hsgt", start_date, end_date)


@market_hk_hold_strategy.command("update-period-count")
def market_hk_hold_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 hk_hold 完整性快照。"""
    _run_completeness_update(HkHoldStrategy, "market_hk_hold", start_date, end_date)


@market_hk_hold_strategy.command("check-complete")
def market_hk_hold_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 hk_hold 完整性并补拉缺失日。"""
    _run_completeness_check(HkHoldStrategy, "market_hk_hold", start_date, end_date)


@dragon_tiger_strategy.command("update-period-count")
def dragon_tiger_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 dragon_tiger 完整性快照。"""
    _run_completeness_update(DragonTigerStrategy, "dragon_tiger", start_date, end_date)


@dragon_tiger_strategy.command("check-complete")
def dragon_tiger_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 dragon_tiger 完整性并补拉缺失日。"""
    _run_completeness_check(DragonTigerStrategy, "dragon_tiger", start_date, end_date)


@block_trade_strategy.command("update-period-count")
def block_trade_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 block_trade 完整性快照。"""
    _run_completeness_update(BlockTradeStrategy, "market_block_trade", start_date, end_date)


@block_trade_strategy.command("check-complete")
def block_trade_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 block_trade 完整性并补拉缺失日。"""
    _run_completeness_check(BlockTradeStrategy, "market_block_trade", start_date, end_date)


@forecast_strategy.command("update-period-count")
def forecast_update_period_count(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """刷新 forecast 完整性快照。"""
    _run_completeness_update(ForecastStrategy, "financial_forecast", start_date, end_date)


@forecast_strategy.command("check-complete")
def forecast_check_complete(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """检查 forecast 完整性并补拉缺失期。"""
    _run_completeness_check(ForecastStrategy, "financial_forecast", start_date, end_date)


@express_strategy.command("update-period-count")
def express_update_period_count(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """刷新 express 完整性快照。"""
    _run_completeness_update(ExpressStrategy, "financial_express", start_date, end_date)


@express_strategy.command("check-complete")
def express_check_complete(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """检查 express 完整性并补拉缺失期。"""
    _run_completeness_check(ExpressStrategy, "financial_express", start_date, end_date)


@stk_holder_strategy.command("update-period-count")
def stk_holder_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 stk_holdernumber 完整性快照。"""
    _run_completeness_update(StkHoldernumberStrategy, "financial_stock_holder", start_date, end_date)


@stk_holder_strategy.command("check-complete")
def stk_holder_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 stk_holdernumber 完整性并逐股补拉。"""
    _run_completeness_check(StkHoldernumberStrategy, "financial_stock_holder", start_date, end_date)


@stk_factor_strategy.command("update-period-count")
def stk_factor_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 stk_factor 完整性快照。"""
    _run_completeness_update(StkFactorStrategy, "kline_stock_factor", start_date, end_date)


@stk_factor_strategy.command("check-complete")
def stk_factor_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 stk_factor 完整性并缺日补拉。"""
    _run_completeness_check(StkFactorStrategy, "kline_stock_factor", start_date, end_date)


@shareholder_strategy.command("update-period-count")
def shareholder_update_period_count(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """刷新 top10_holders 完整性快照。"""
    _run_completeness_update(ShareholderStrategy, "financial_shareholder_top10", start_date, end_date)


@shareholder_strategy.command("check-complete")
def shareholder_check_complete(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """检查 top10_holders 完整性并缺日补拉。"""
    _run_completeness_check(ShareholderStrategy, "financial_shareholder_top10", start_date, end_date)


@shareholder_strategy.command("update-floatholders-period-count")
def floatholders_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 top10_floatholders 完整性快照。"""
    _run_completeness_update(Top10FloatholdersStrategy, "financial_top10_floatholders", start_date, end_date)


@shareholder_strategy.command("check-floatholders-complete")
def floatholders_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 top10_floatholders 完整性并缺日补拉。"""
    _run_completeness_check(Top10FloatholdersStrategy, "financial_top10_floatholders", start_date, end_date)


@audit_strategy.command("update-period-count")
def audit_update_period_count(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """刷新 fina_audit 完整性快照。"""
    _run_completeness_update(AuditStrategy, "financial_audit", start_date, end_date)


@audit_strategy.command("check-complete")
def audit_check_complete(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """检查 fina_audit 完整性并逐股补拉。"""
    _run_completeness_check(AuditStrategy, "financial_audit", start_date, end_date)


@disclosure_date_strategy.command("update-period-count")
def disclosure_date_update_period_count(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """刷新 disclosure_date 完整性快照。"""
    _run_completeness_update(DisclosureDateStrategy, "financial_disclosure_date", start_date, end_date)


@disclosure_date_strategy.command("check-complete")
def disclosure_date_check_complete(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """检查 disclosure_date 完整性并补拉缺失期。"""
    _run_completeness_check(DisclosureDateStrategy, "financial_disclosure_date", start_date, end_date)


@fina_mainbz_strategy.command("update-period-count")
def fina_mainbz_update_period_count(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """刷新 fina_mainbz 完整性快照。"""
    _run_completeness_update(FinaMainbzStrategy, "financial_fina_mainbz", start_date, end_date)


@fina_mainbz_strategy.command("check-complete")
def fina_mainbz_check_complete(
    start_date: str | None = typer.Option(None, "--start-period"),
    end_date: str | None = typer.Option(None, "--end-period"),
) -> None:
    """检查 fina_mainbz 完整性并逐股补拉。"""
    _run_completeness_check(FinaMainbzStrategy, "financial_fina_mainbz", start_date, end_date)


@index_strategy.command("update-period-count")
def index_update_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 index_weight 完整性快照。"""
    _run_completeness_update(IndexWeightStrategy, "index_weight", start_date, end_date)


@index_strategy.command("check-complete")
def index_check_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 index_weight 完整性并逐指数补拉。"""
    _run_completeness_check(IndexWeightStrategy, "index_weight", start_date, end_date)


@index_strategy.command("update-daily-period-count")
def index_update_daily_period_count(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """刷新 index_daily 完整性快照。"""
    _run_completeness_update(IndexDailyStrategy, "index_daily", start_date, end_date)


@index_strategy.command("check-daily-complete")
def index_check_daily_complete(
    start_date: str | None = typer.Option(None, "--start-date"),
    end_date: str | None = typer.Option(None, "--end-date"),
) -> None:
    """检查 index_daily 完整性并逐指数补拉。"""
    _run_completeness_check(IndexDailyStrategy, "index_daily", start_date, end_date)



def _run_warehouse_pull_kline_daily_by_month_range(
    start_month: str | None = None,
    end_month: str | None = None,
    *,
    silent: bool = False,
) -> None:
    total = KlineDailyWarehouseStrategy().dump_by_month_range(
        start_month=start_month,
        end_month=end_month,
    )
    _cli_echo(f"日K Parquet 累计写入 {total} 行", silent=silent)


@warehouse_strategy.command("pull-kline-daily-by-month-range")
def warehouse_pull_kline_daily_by_month_range(
    start_month: str | None = typer.Option(None, "--start-month", help="起始月 YYYYMM，默认 KLINE_DAILY_START_DATE 所在月"),
    end_month: str | None = typer.Option(None, "--end-month", help="结束月 YYYYMM，默认当月"),
) -> None:
    """按月把 PG kline_daily 导出为 Parquet 分区（99% 完整性守门 + 当月强制重写，幂等覆盖）。"""
    _run_warehouse_pull_kline_daily_by_month_range(
        start_month=start_month, end_month=end_month,
    )


def _run_warehouse_check_kline_daily_parquet(*, silent: bool = False) -> None:
    KlineDailyWarehouseStrategy().check_parquet_vs_pg()


@warehouse_strategy.command("check-kline-daily-parquet")
def warehouse_check_kline_daily_parquet() -> None:
    """PG vs Parquet 月度行数对账：找出 diff / pg-only / pq-only 月份（含 99% 预期跳过标识）。无 CLI 参数。"""
    _run_warehouse_check_kline_daily_parquet()


def _menu_handler(key: str) -> Callable[[], None]:
    runner = get_menu_handler(key)

    def _invoke() -> None:
        runner()

    return _invoke


_MENU_HANDLERS: dict[str, Callable[[], None]] = {
    key: _menu_handler(key) for _, key in _MENU_ROWS
}

# start the app
if __name__ == "__main__":
    app()
