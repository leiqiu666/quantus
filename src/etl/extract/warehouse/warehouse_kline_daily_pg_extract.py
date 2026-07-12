"""warehouse · 日 K PG Extract：按月读 kline_daily + expected 计算。"""

from __future__ import annotations

from typing import Iterator

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.kline.kline_daily_entities import KlineDailyEntities
from src.etl.extract.local.stock.stock_trade_calendar_local_extract import TradeCalLocalExtract
from src.service.stock.stock_active_count_service import StockActiveCountService


def _month_bounds(year_month: str) -> tuple[str, str]:
    """YYYYMM → ('YYYYMM01', 'YYYYMM31')。trade_date 是 YYYYMMDD 字符串，31 上界即可。"""
    ym = (year_month or "").strip()
    if len(ym) != 6 or not ym.isdigit():
        raise ValueError(f"invalid year_month: {year_month!r}")
    return f"{ym}01", f"{ym}31"


class KlineDailyPgExtract:
    """从 PG 读 kline_daily 的 warehouse 专用 Extract。

    与 src/etl/extract/local/kline/kline_extract.py 不同：后者面向远程 ETL 的本地辅助
    （resolved 日列表、95% 完整性判定），本类面向 warehouse 批量列存导出。
    """

    def __init__(self) -> None:
        self._db = Database()
        self._trade_cal = TradeCalLocalExtract()
        self._active_count = StockActiveCountService()

    # ---------- 交易日 / 期望 ----------

    def list_open_trade_dates_by_month(
        self, year_month: str, *, exchange: str = "SSE"
    ) -> list[str]:
        start, end = _month_bounds(year_month)
        return self._trade_cal.get_open_trade_dates(
            start_date=start, end_date=end, exchange=exchange,
        )

    def compute_expected_by_dates(
        self, open_trade_dates: list[str]
    ) -> dict[str, int]:
        """expected(d) = stock_active_count.trading_count。"""
        if not open_trade_dates:
            return {}
        return self._active_count.resolve_trading_counts(open_trade_dates)

    # ---------- PG 读 ----------

    def count_by_date(self, year_month: str) -> dict[str, int]:
        start, end = _month_bounds(year_month)
        session: Session = self._db.get_session()
        try:
            rows = (
                session.query(
                    KlineDailyEntities.trade_date,
                    func.count(KlineDailyEntities.id),
                )
                .filter(
                    KlineDailyEntities.trade_date >= start,
                    KlineDailyEntities.trade_date <= end,
                )
                .group_by(KlineDailyEntities.trade_date)
                .all()
            )
            return {str(td).strip(): int(cnt) for td, cnt in rows if td}
        finally:
            session.close()

    def read_month(self, year_month: str) -> pd.DataFrame:
        """月内全 A 全字段一次性读出（单月 ~10w 行，单 DataFrame 装得下）。"""
        start, end = _month_bounds(year_month)
        cols = [
            KlineDailyEntities.ts_code,
            KlineDailyEntities.trade_date,
            KlineDailyEntities.open,
            KlineDailyEntities.high,
            KlineDailyEntities.low,
            KlineDailyEntities.close,
            KlineDailyEntities.pre_close,
            KlineDailyEntities.change,
            KlineDailyEntities.pct_chg,
            KlineDailyEntities.vol,
            KlineDailyEntities.amount,
            KlineDailyEntities.adj_factor,
            KlineDailyEntities.up_limit,
            KlineDailyEntities.down_limit,
        ]
        session: Session = self._db.get_session()
        try:
            rows = (
                session.query(*cols)
                .filter(
                    KlineDailyEntities.trade_date >= start,
                    KlineDailyEntities.trade_date <= end,
                )
                .order_by(
                    KlineDailyEntities.trade_date.asc(),
                    KlineDailyEntities.ts_code.asc(),
                )
                .all()
            )
        finally:
            session.close()

        if not rows:
            return pd.DataFrame(columns=[c.key for c in cols])
        return pd.DataFrame.from_records(rows, columns=[c.key for c in cols])

    def iter_existing_months(self) -> list[str]:
        """返回 PG 内已有数据的 YYYYMM 列表（升序），用于 Strategy 圈定月份范围。"""
        session: Session = self._db.get_session()
        try:
            rows = (
                session.query(
                    func.substr(KlineDailyEntities.trade_date, 1, 6),
                )
                .filter(KlineDailyEntities.trade_date.isnot(None))
                .distinct()
                .order_by(func.substr(KlineDailyEntities.trade_date, 1, 6).asc())
                .all()
            )
            return [str(r[0]).strip() for r in rows if r[0]]
        finally:
            session.close()

    def count_by_month_all(self) -> dict[str, int]:
        """全表按 substr(trade_date, 1, 6) 聚合，{YYYYMM: 行数}。check 路径对账用。"""
        ym = func.substr(KlineDailyEntities.trade_date, 1, 6)
        session: Session = self._db.get_session()
        try:
            rows = (
                session.query(ym, func.count(KlineDailyEntities.id))
                .filter(KlineDailyEntities.trade_date.isnot(None))
                .group_by(ym)
                .all()
            )
            return {str(m).strip(): int(cnt) for m, cnt in rows if m}
        finally:
            session.close()


__all__ = ["KlineDailyPgExtract"]
