from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.kline.kline_daily_period_count_entities import (
    KlineDailyPeriodCountEntities,
)


class KlineDailyPeriodCountModel:
    def __init__(self) -> None:
        self.db = Database()

    def get_counts_by_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        按交易日区间查询 trade_date -> period_stock_count 映射。

        Args:
            start_date: 交易日下界（含），YYYYMMDD；不传则不限制。
            end_date: 交易日上界（含），YYYYMMDD；不传则不限制。
        """
        session: Session = self.db.get_session()
        try:
            query = session.query(KlineDailyPeriodCountEntities)
            if start_date is not None:
                query = query.filter(
                    KlineDailyPeriodCountEntities.trade_date >= start_date
                )
            if end_date is not None:
                query = query.filter(
                    KlineDailyPeriodCountEntities.trade_date <= end_date
                )
            rows = query.all()
            return {r.trade_date: int(r.period_stock_count) for r in rows}
        finally:
            session.close()

    def list_by_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        按交易日区间查询 kline_daily_period_count 快照，按 trade_date 倒序。

        Returns:
            每项含 trade_date、period_stock_count、kline_daily_count、
            kline_adj_factor_count、kline_stk_limit_count。
        """
        session: Session = self.db.get_session()
        try:
            query = session.query(KlineDailyPeriodCountEntities)
            if start_date is not None:
                query = query.filter(
                    KlineDailyPeriodCountEntities.trade_date >= start_date
                )
            if end_date is not None:
                query = query.filter(
                    KlineDailyPeriodCountEntities.trade_date <= end_date
                )
            rows = query.order_by(
                KlineDailyPeriodCountEntities.trade_date.desc()
            ).all()
            return [
                {
                    "trade_date": r.trade_date,
                    "period_stock_count": int(r.period_stock_count or 0),
                    "kline_daily_count": int(r.kline_daily_count or 0),
                    "kline_adj_factor_count": int(r.kline_adj_factor_count or 0),
                    "kline_stk_limit_count": int(r.kline_stk_limit_count or 0),
                }
                for r in rows
            ]
        finally:
            session.close()

    def list_all(self) -> List[Dict[str, Any]]:
        """查询 kline_daily_period_count 全表记录，按 trade_date 倒序。"""
        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(KlineDailyPeriodCountEntities)
                .order_by(KlineDailyPeriodCountEntities.trade_date.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "trade_date": r.trade_date,
                    "period_stock_count": r.period_stock_count,
                    "kline_daily_count": r.kline_daily_count,
                    "kline_adj_factor_count": r.kline_adj_factor_count,
                    "kline_stk_limit_count": r.kline_stk_limit_count,
                }
                for r in rows
            ]
        finally:
            session.close()
