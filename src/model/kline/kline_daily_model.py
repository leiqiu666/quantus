"""kline_daily 表查询。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.kline.kline_daily_entities import KlineDailyEntities


class KlineDailyModel:
    def __init__(self) -> None:
        self.db = Database()

    def get_max_trade_date(self) -> str | None:
        session: Session = self.db.get_session()
        try:
            row = session.query(func.max(KlineDailyEntities.trade_date)).scalar()
            if row is None:
                return None
            s = str(row).strip()
            return s[:8] if len(s) >= 8 else None
        finally:
            session.close()

    def get_trade_date_list(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        按 trade_date 分组统计 kline_daily 条数。

        Returns:
            列表按 trade_date 倒序，元素含 trade_date、kline_daily_count。
        """
        clauses = [
            KlineDailyEntities.trade_date.isnot(None),
            KlineDailyEntities.trade_date != "",
        ]
        if start_date is not None:
            clauses.append(KlineDailyEntities.trade_date >= start_date)
        if end_date is not None:
            clauses.append(KlineDailyEntities.trade_date <= end_date)
        rows = self.db.select_grouped(
            KlineDailyEntities,
            KlineDailyEntities.trade_date,
            func.count(KlineDailyEntities.id),
            group_by=(KlineDailyEntities.trade_date,),
            order_by=(KlineDailyEntities.trade_date.desc(),),
            where_clauses=tuple(clauses),
        )
        return [
            {"trade_date": trade_date, "kline_daily_count": int(cnt)}
            for trade_date, cnt in rows
        ]

    def get_trade_dates_with_adj_factor_by_ts_code(
        self,
        ts_code: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """返回单股在区间内已入库且 adj_factor 非空的 trade_date 列表（升序、去重）。"""
        code = (ts_code or "").strip()
        if not code:
            return []

        clauses = [
            KlineDailyEntities.ts_code == code,
            KlineDailyEntities.trade_date.isnot(None),
            KlineDailyEntities.trade_date != "",
            KlineDailyEntities.adj_factor.isnot(None),
        ]
        if start_date is not None:
            clauses.append(KlineDailyEntities.trade_date >= start_date)
        if end_date is not None:
            clauses.append(KlineDailyEntities.trade_date <= end_date)

        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(KlineDailyEntities.trade_date)
                .filter(*clauses)
                .distinct()
                .order_by(KlineDailyEntities.trade_date.asc())
                .all()
            )
            return [str(r[0]).strip()[:8] for r in rows if r[0]]
        finally:
            session.close()

    def get_trade_date_adj_factor_count_list(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按 trade_date 分组统计 adj_factor 非空的 kline_daily 条数。"""
        clauses = [
            KlineDailyEntities.trade_date.isnot(None),
            KlineDailyEntities.trade_date != "",
            KlineDailyEntities.adj_factor.isnot(None),
        ]
        if start_date is not None:
            clauses.append(KlineDailyEntities.trade_date >= start_date)
        if end_date is not None:
            clauses.append(KlineDailyEntities.trade_date <= end_date)
        rows = self.db.select_grouped(
            KlineDailyEntities,
            KlineDailyEntities.trade_date,
            func.count(KlineDailyEntities.id),
            group_by=(KlineDailyEntities.trade_date,),
            order_by=(KlineDailyEntities.trade_date.desc(),),
            where_clauses=tuple(clauses),
        )
        return [
            {"trade_date": trade_date, "kline_adj_factor_count": int(cnt)}
            for trade_date, cnt in rows
        ]

    def get_trade_dates_with_stk_limit_by_ts_code(
        self,
        ts_code: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """返回单股在区间内 up_limit、down_limit 均已入库的 trade_date 列表（升序、去重）。"""
        code = (ts_code or "").strip()
        if not code:
            return []

        clauses = [
            KlineDailyEntities.ts_code == code,
            KlineDailyEntities.trade_date.isnot(None),
            KlineDailyEntities.trade_date != "",
            KlineDailyEntities.up_limit.isnot(None),
            KlineDailyEntities.down_limit.isnot(None),
        ]
        if start_date is not None:
            clauses.append(KlineDailyEntities.trade_date >= start_date)
        if end_date is not None:
            clauses.append(KlineDailyEntities.trade_date <= end_date)

        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(KlineDailyEntities.trade_date)
                .filter(*clauses)
                .distinct()
                .order_by(KlineDailyEntities.trade_date.asc())
                .all()
            )
            return [str(r[0]).strip()[:8] for r in rows if r[0]]
        finally:
            session.close()

    def get_trade_date_stk_limit_count_list(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按 trade_date 分组统计 up_limit、down_limit 均已入库的 kline_daily 条数。"""
        clauses = [
            KlineDailyEntities.trade_date.isnot(None),
            KlineDailyEntities.trade_date != "",
            KlineDailyEntities.up_limit.isnot(None),
            KlineDailyEntities.down_limit.isnot(None),
        ]
        if start_date is not None:
            clauses.append(KlineDailyEntities.trade_date >= start_date)
        if end_date is not None:
            clauses.append(KlineDailyEntities.trade_date <= end_date)
        rows = self.db.select_grouped(
            KlineDailyEntities,
            KlineDailyEntities.trade_date,
            func.count(KlineDailyEntities.id),
            group_by=(KlineDailyEntities.trade_date,),
            order_by=(KlineDailyEntities.trade_date.desc(),),
            where_clauses=tuple(clauses),
        )
        return [
            {"trade_date": trade_date, "kline_stk_limit_count": int(cnt)}
            for trade_date, cnt in rows
        ]

    def get_trade_dates_by_ts_code(
        self,
        ts_code: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """返回单股在区间内已入库的 trade_date 列表（升序、去重）。"""
        code = (ts_code or "").strip()
        if not code:
            return []

        clauses = [
            KlineDailyEntities.ts_code == code,
            KlineDailyEntities.trade_date.isnot(None),
            KlineDailyEntities.trade_date != "",
        ]
        if start_date is not None:
            clauses.append(KlineDailyEntities.trade_date >= start_date)
        if end_date is not None:
            clauses.append(KlineDailyEntities.trade_date <= end_date)

        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(KlineDailyEntities.trade_date)
                .filter(*clauses)
                .distinct()
                .order_by(KlineDailyEntities.trade_date.asc())
                .all()
            )
            return [str(r[0]).strip()[:8] for r in rows if r[0]]
        finally:
            session.close()

    def list_resolved_trade_dates_grouped(
        self,
        *,
        dimension: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        全市场一次性按维度返回 {ts_code: [trade_date, ...]}（升序、去重）。

        dimension:
          - "daily"      → 仅按主键非空判定
          - "adj_factor" → 仅返回 adj_factor 非空行
          - "stk_limit"  → 仅返回 up_limit、down_limit 均非空行

        替代逐股的 get_trade_dates_*_by_ts_code，将 N 次查询合并成 1 次。
        """
        clauses = [
            KlineDailyEntities.ts_code.isnot(None),
            KlineDailyEntities.trade_date.isnot(None),
            KlineDailyEntities.trade_date != "",
        ]
        if dimension == "adj_factor":
            clauses.append(KlineDailyEntities.adj_factor.isnot(None))
        elif dimension == "stk_limit":
            clauses.append(KlineDailyEntities.up_limit.isnot(None))
            clauses.append(KlineDailyEntities.down_limit.isnot(None))
        elif dimension != "daily":
            raise ValueError(f"未知 K 线维度: {dimension}")
        if start_date is not None:
            clauses.append(KlineDailyEntities.trade_date >= start_date)
        if end_date is not None:
            clauses.append(KlineDailyEntities.trade_date <= end_date)

        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(
                    KlineDailyEntities.ts_code,
                    KlineDailyEntities.trade_date,
                )
                .filter(*clauses)
                .distinct()
                .all()
            )
        finally:
            session.close()

        bucket: Dict[str, set[str]] = {}
        for ts_code, trade_date in rows:
            if not ts_code or not trade_date:
                continue
            code = str(ts_code).strip()
            td = str(trade_date).strip()[:8]
            if not code or not td:
                continue
            bucket.setdefault(code, set()).add(td)
        return {code: sorted(dates) for code, dates in bucket.items()}

    def list_by_trade_date(self, trade_date: str) -> List[Dict[str, Any]]:
        """返回指定交易日全市场日线（dict 列表，供 Load filter 比对）。"""
        rows = self.db.get_all(
            KlineDailyEntities, trade_date=str(trade_date).strip()
        )
        columns = KlineDailyEntities.__table__.columns
        return [
            {col.name: getattr(row, col.name) for col in columns}
            for row in rows
        ]
