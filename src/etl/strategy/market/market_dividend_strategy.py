"""分红送股 Strategy：按 record_date / 开市日循环编排（无完整性校验）。"""

from __future__ import annotations

from datetime import datetime

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.extract.local.market.market_dividend_local_extract import DividendLocalExtract
from src.etl.extract.local.stock.stock_trade_calendar_local_extract import TradeCalLocalExtract
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.market.market_dividend_workflow import DividendWorkflow


class DividendStrategy:
    def __init__(self) -> None:
        self.dividend_workflow = DividendWorkflow()
        self.dividend_local = DividendLocalExtract()
        self.trade_cal_strategy = TradeCalStrategy()
        self.trade_cal_local = TradeCalLocalExtract()
        self.dividend_start_date = settings.etl_start_date("market_dividend")

    def pull_dividend_by_date_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        if start_date is None:
            start_date = self.dividend_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        floor = (start_date or "").strip()
        end = (end_date or "").strip()
        if not floor or not end or floor > end:
            return 0

        self.trade_cal_strategy.ensure_trade_cal(
            start_date=floor,
            end_date=end,
            exchange="SSE",
        )

        eff_start = self.dividend_local.resolve_incremental_start(configured_start=floor)
        if not eff_start or eff_start > end:
            max_rd = self.dividend_local.get_max_record_date()
            print(f"[信息] market_dividend 已同步至 {max_rd or '无'}，跳过")
            return 0

        open_dates = self.trade_cal_local.get_open_trade_dates(
            start_date=eff_start,
            end_date=end,
            exchange="SSE",
        )
        if not open_dates:
            return 0

        print(
            f"[信息] {eff_start}~{end} 共 {len(open_dates)} 个开市日待拉"
            f"（首日 {open_dates[0]}，末日 {open_dates[-1]}）"
        )

        total_saved = 0
        for td in tqdm_iter(open_dates, desc="分红送股入库", unit="日"):
            n = self.dividend_workflow.pull_dividend_by_record_date(record_date=td)
            total_saved += n

        return total_saved

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        print("[market_dividend] Spec 声明不做完整性校验，跳过快照")
        return 0

    def check_complete(self, start_date=None, end_date=None) -> int:
        print("[market_dividend] Spec 声明不做完整性校验，跳过 check-complete")
        return 0
