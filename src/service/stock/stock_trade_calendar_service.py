"""个股交易日历服务。

组合 trade_cal 开市日、stock_list 上市存续期、suspend_d 全天停牌，
给出指定区间内单股「应该有 K 线」的交易日列表。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.stock.stock_list_entities import StockListEntities
from src.service.suspend.suspend_service import SuspendService
from src.service.stock.stock_trade_cal_service import TradeCalService


def _norm_ymd(value: object) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    digits = "".join(c for c in raw if c.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


class StockTradeCalendarService:
    """个股交易日历查询（只读，组合多张基础表）。"""

    def __init__(self) -> None:
        self.db = Database()
        self.trade_cal = TradeCalService()
        self.suspend = SuspendService()

    def get_stock_active_window(
        self, ts_code: str
    ) -> tuple[str, str]:
        """返回 (list_date, delist_date)；任一缺失返回空串。delist_date 为空表示在市。"""
        code = (ts_code or "").strip()
        if not code:
            return ("", "")
        session: Session = self.db.get_session()
        try:
            row = (
                session.query(
                    StockListEntities.list_date,
                    StockListEntities.delist_date,
                )
                .filter(StockListEntities.ts_code == code)
                .first()
            )
        finally:
            session.close()
        if row is None:
            return ("", "")
        return (_norm_ymd(row[0]), _norm_ymd(row[1]))

    def compute_stock_trade_calendar(
        self,
        ts_code: str,
        *,
        start_date: str,
        end_date: str,
        exchange: str = "SSE",
    ) -> list[str]:
        """
        计算单股 [start_date, end_date] 内「应该有 K 线」的交易日（升序）。

        公式：交易所开市日 ∩ [list_date, delist_date) − 全天停牌日。
        - list_date 缺失或晚于 start，使用 list_date 作为下界
        - delist_date 不为空，则 trade_date >= delist_date 视为已退市排除
        - 全天停牌：suspend_d 中 suspend_type='S' AND suspend_timing=''

        日期区间由调用方决定；不做开/闭翻转判断（trade_cal 已是闭区间语义）。
        """
        code = (ts_code or "").strip()
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        if not code or not start or not end or start > end:
            return []

        list_date, delist_date = self.get_stock_active_window(code)

        effective_start = max(start, list_date) if list_date else start
        if delist_date:
            # 退市前一日为最后可交易日；trade_date < delist_date 才有效
            effective_end = min(end, _ymd_sub_days(delist_date, 1))
        else:
            effective_end = end
        if not effective_start or not effective_end or effective_start > effective_end:
            return []

        open_dates = self.trade_cal.get_open_trade_dates(
            start_date=effective_start,
            end_date=effective_end,
            exchange=exchange,
        )
        if not open_dates:
            return []

        suspend_set = set(
            self.suspend.get_full_day_suspend_dates(
                code,
                start_date=effective_start,
                end_date=effective_end,
            )
        )
        if not suspend_set:
            return open_dates
        return [td for td in open_dates if td not in suspend_set]


def _ymd_sub_days(ymd: str, days: int) -> str:
    from datetime import datetime, timedelta

    d = datetime.strptime(ymd.strip(), "%Y%m%d").date()
    return (d - timedelta(days=days)).strftime("%Y%m%d")
