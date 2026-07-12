"""factor_meta Model：PG 查询。"""

from __future__ import annotations

from typing import Optional

from src.common.database import Database
from src.entities.data_entities.kline.factor_meta_entities import FactorMetaEntities


class FactorMetaModel:
    def __init__(self) -> None:
        self._db = Database()

    def search(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[FactorMetaEntities]:
        session = self._db.get_session()
        try:
            query = session.query(FactorMetaEntities)
            if source:
                query = query.filter(FactorMetaEntities.source == source)
            if category:
                query = query.filter(FactorMetaEntities.category == category)
            query = query.order_by(FactorMetaEntities.source, FactorMetaEntities.factor_name)
            return query.all()
        finally:
            session.close()
