"""factor_meta Model：PG 查询 / 更新。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_

from src.common.database import Database
from src.entities.data_entities.kline.factor_meta_entities import FactorMetaEntities


class FactorMetaModel:
    def __init__(self) -> None:
        self._db = Database()

    def search(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[FactorMetaEntities], int]:
        session = self._db.get_session()
        try:
            query = session.query(FactorMetaEntities)
            if source:
                query = query.filter(FactorMetaEntities.source == source)
            if category:
                query = query.filter(FactorMetaEntities.category == category)
            if keyword:
                like = f"%{keyword.strip()}%"
                query = query.filter(
                    or_(
                        FactorMetaEntities.factor_name.ilike(like),
                        FactorMetaEntities.display_name.ilike(like),
                    )
                )
            total = query.count()
            rows = (
                query.order_by(FactorMetaEntities.source, FactorMetaEntities.factor_name)
                .offset(offset)
                .limit(limit)
                .all()
            )
            return rows, total
        finally:
            session.close()

    def get_by_name(self, factor_name: str) -> FactorMetaEntities | None:
        session = self._db.get_session()
        try:
            return (
                session.query(FactorMetaEntities)
                .filter(FactorMetaEntities.factor_name == factor_name)
                .one_or_none()
            )
        finally:
            session.close()

    def list_formula_map(self) -> dict[str, str]:
        """factor_name → 非空 formula。"""
        session = self._db.get_session()
        try:
            rows = session.query(
                FactorMetaEntities.factor_name, FactorMetaEntities.formula
            ).all()
            return {
                str(name): str(formula)
                for name, formula in rows
                if name and formula and str(formula).strip()
            }
        finally:
            session.close()

    def update_by_name(
        self, factor_name: str, fields: dict[str, Any]
    ) -> FactorMetaEntities | None:
        session = self._db.get_session()
        try:
            row = (
                session.query(FactorMetaEntities)
                .filter(FactorMetaEntities.factor_name == factor_name)
                .one_or_none()
            )
            if row is None:
                return None
            nullable_ok = {"display_name", "formula", "category", "python_path"}
            for key, value in fields.items():
                if value is not None or key in nullable_ok:
                    setattr(row, key, value)
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
