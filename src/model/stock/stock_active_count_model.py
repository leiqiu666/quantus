from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.stock.stock_active_count_entities import (
    StockActiveCountEntities,
)


class StockActiveCountModel:
    def __init__(self) -> None:
        self.db = Database()
        self.db.ensure_table(StockActiveCountEntities)

    def get_by_date_key(self, date_key: str) -> dict[str, Any] | None:
        dk = (date_key or "").strip()
        if not dk:
            return None
        session: Session = self.db.get_session()
        try:
            row = (
                session.query(StockActiveCountEntities)
                .filter(StockActiveCountEntities.date_key == dk)
                .first()
            )
            if row is None:
                return None
            return {
                "date_key": row.date_key,
                "listed_count": int(row.listed_count or 0),
                "trading_count": (
                    int(row.trading_count)
                    if row.trading_count is not None
                    else None
                ),
            }
        finally:
            session.close()

    def list_by_date_keys(self, date_keys: list[str]) -> dict[str, dict[str, Any]]:
        keys = sorted({(k or "").strip() for k in date_keys if (k or "").strip()})
        if not keys:
            return {}
        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(StockActiveCountEntities)
                .filter(StockActiveCountEntities.date_key.in_(keys))
                .all()
            )
            return {
                r.date_key: {
                    "date_key": r.date_key,
                    "listed_count": int(r.listed_count or 0),
                    "trading_count": (
                        int(r.trading_count)
                        if r.trading_count is not None
                        else None
                    ),
                }
                for r in rows
            }
        finally:
            session.close()

    def list_by_range(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        session: Session = self.db.get_session()
        try:
            query = session.query(StockActiveCountEntities)
            if start_date:
                query = query.filter(StockActiveCountEntities.date_key >= start_date)
            if end_date:
                query = query.filter(StockActiveCountEntities.date_key <= end_date)
            rows = query.order_by(StockActiveCountEntities.date_key.desc()).all()
            return [
                {
                    "date_key": r.date_key,
                    "listed_count": int(r.listed_count or 0),
                    "trading_count": (
                        int(r.trading_count)
                        if r.trading_count is not None
                        else None
                    ),
                }
                for r in rows
            ]
        finally:
            session.close()
