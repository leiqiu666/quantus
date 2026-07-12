from datetime import datetime, timedelta

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.client.stock.stock_trade_calendar_common import TRADE_CAL_EXCHANGES
from src.etl.extract.local.stock.stock_trade_calendar_local_extract import TradeCalLocalExtract
from src.etl.workflow.stock.stock_trade_calendar_workflow import TradeCalWorkflow


def _ymd_add_days(ymd: str, days: int) -> str:
    d = datetime.strptime(ymd.strip(), "%Y%m%d").date()
    return (d + timedelta(days=days)).strftime("%Y%m%d")


def _ymd_sub_days(ymd: str, days: int) -> str:
    d = datetime.strptime(ymd.strip(), "%Y%m%d").date()
    return (d - timedelta(days=days)).strftime("%Y%m%d")


class TradeCalStrategy:
    def __init__(self) -> None:
        self.trade_cal_workflow = TradeCalWorkflow()
        self.trade_cal_local = TradeCalLocalExtract()
        self.trade_cal_start_date = settings.etl_start_date("stock_trade_calendar")

    def pull_trade_cal_history(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """
        全交易所交易日历增量入库（Tushare trade_cal，含休市日）。

        各交易所起点 = max(STOCK_TRADE_CALENDAR_START_DATE, 库内该所 max(cal_date)+1)，避免重复拉取。
        """
        if start_date is None:
            start_date = self.trade_cal_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        floor = (start_date or "").strip()
        end = (end_date or "").strip()
        if not floor or not end or floor > end:
            return 0

        total_saved = 0
        for exchange in tqdm_iter(TRADE_CAL_EXCHANGES, desc="交易日历入库", unit="所"):
            eff_start = self.trade_cal_local.resolve_incremental_start(
                exchange=exchange,
                configured_start=floor,
            )
            if not eff_start or eff_start > end:
                print(f"[信息] {exchange} 已同步至 {self.trade_cal_local.get_max_cal_date(exchange) or '无'}，跳过")
                continue

            n = self.trade_cal_workflow.pull_trade_cal_range(
                exchange=exchange,
                start_date=eff_start,
                end_date=end,
            )
            total_saved += n
            print(f"[信息] {exchange} {eff_start}~{end} 写入 {n} 条")

        return total_saved

    def ensure_trade_cal(
        self,
        *,
        start_date: str,
        end_date: str,
        exchange: str = "SSE",
    ) -> int:
        """按需补全 [start_date, end_date] 本地日历（含向前/向后缺口）。"""
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        ex = (exchange or "SSE").strip().upper()
        if not start or not end or start > end:
            return 0

        min_cal = self.trade_cal_local.get_min_cal_date(ex)
        max_cal = self.trade_cal_local.get_max_cal_date(ex)
        total = 0

        # 库内最小日期晚于请求起点 → 回填前半段（例如仅有 2025 年日历、起点为 1990）
        if min_cal is None or min_cal > start:
            head_end = _ymd_sub_days(min_cal, 1) if min_cal else end
            head_end = min(head_end, end)
            if start <= head_end:
                n = self.trade_cal_workflow.pull_trade_cal_range(
                    exchange=ex,
                    start_date=start,
                    end_date=head_end,
                )
                total += n
                if n:
                    print(f"[信息] 已回填 {ex} 交易日历 {start}~{head_end}，写入 {n} 条")
                min_cal = start
                max_cal = self.trade_cal_local.get_max_cal_date(ex)

        # 库内最大日期早于请求终点 → 向后增量
        if max_cal is None or max_cal < end:
            tail_start = _ymd_add_days(max_cal, 1) if max_cal else start
            tail_start = max(tail_start, start)
            if tail_start <= end:
                n = self.trade_cal_workflow.pull_trade_cal_range(
                    exchange=ex,
                    start_date=tail_start,
                    end_date=end,
                )
                total += n
                if n:
                    print(f"[信息] 已补全 {ex} 交易日历 {tail_start}~{end}，写入 {n} 条")

        return total
