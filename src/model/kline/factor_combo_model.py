"""factor_combo Model。"""

from __future__ import annotations

from datetime import datetime

from src.common.database import Database
from src.entities.data_entities.kline.factor_combo_entities import FactorComboEntities


class FactorComboModel:
    def __init__(self) -> None:
        self._db = Database()

    def list_all(self) -> list[FactorComboEntities]:
        session = self._db.get_session()
        try:
            return (
                session.query(FactorComboEntities)
                .order_by(FactorComboEntities.updated_at.desc())
                .all()
            )
        finally:
            session.close()

    def get(self, combo_id: int) -> FactorComboEntities | None:
        session = self._db.get_session()
        try:
            return (
                session.query(FactorComboEntities)
                .filter(FactorComboEntities.id == combo_id)
                .one_or_none()
            )
        finally:
            session.close()

    def get_by_name(self, name: str) -> FactorComboEntities | None:
        session = self._db.get_session()
        try:
            return (
                session.query(FactorComboEntities)
                .filter(FactorComboEntities.name == name)
                .one_or_none()
            )
        finally:
            session.close()

    def create(self, name: str, items: list[dict], remark: str | None) -> FactorComboEntities:
        session = self._db.get_session()
        try:
            now = datetime.now()
            row = FactorComboEntities(
                name=name,
                items=items,
                remark=remark,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(
        self,
        combo_id: int,
        *,
        name: str | None = None,
        items: list[dict] | None = None,
        remark: str | None = None,
    ) -> FactorComboEntities | None:
        session = self._db.get_session()
        try:
            row = (
                session.query(FactorComboEntities)
                .filter(FactorComboEntities.id == combo_id)
                .one_or_none()
            )
            if row is None:
                return None
            if name is not None:
                row.name = name
            if items is not None:
                row.items = items
            if remark is not None:
                row.remark = remark
            row.updated_at = datetime.now()
            session.commit()
            session.refresh(row)
            session.expunge(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, combo_id: int) -> bool:
        session = self._db.get_session()
        try:
            row = (
                session.query(FactorComboEntities)
                .filter(FactorComboEntities.id == combo_id)
                .one_or_none()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
