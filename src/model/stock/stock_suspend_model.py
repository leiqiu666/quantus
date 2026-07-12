"""stock_suspend 聚合读模型。"""

from __future__ import annotations

from sqlalchemy import func

from src.common.database import Database
from src.entities.data_entities.stock.stock_suspend_entities import SuspendEntities


class StockSuspendModel:
    def __init__(self) -> None:
        self._db = Database()

    def count_by_trade_dates(
        self,
        trade_dates: list[str],
    ) -> dict[str, int]:
        if not trade_dates:
            return {}
        session = self._db.get_session()
        try:
            rows = (
                session.query(
                    SuspendEntities.trade_date,
                    func.count(SuspendEntities.id).label("cnt"),
                )
                .filter(SuspendEntities.trade_date.in_(trade_dates))
                .group_by(SuspendEntities.trade_date)
                .all()
            )
            return {str(r[0]): int(r[1]) for r in rows}
        finally:
            session.close()
