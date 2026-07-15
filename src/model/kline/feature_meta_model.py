"""feature_meta Model：PG 查询 / upsert。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_

from src.common.database import Database
from src.entities.data_entities.kline.feature_meta_entities import FeatureMetaEntities


class FeatureMetaModel:
    def __init__(self) -> None:
        self._db = Database()

    def search(
        self,
        *,
        keyword: Optional[str] = None,
        feature_kind: Optional[str] = None,
        source_kind: Optional[str] = None,
        enabled: Optional[int] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[FeatureMetaEntities], int]:
        session = self._db.get_session()
        try:
            query = session.query(FeatureMetaEntities)
            if keyword:
                like = f"%{keyword.strip()}%"
                query = query.filter(
                    or_(
                        FeatureMetaEntities.feature_name.ilike(like),
                        FeatureMetaEntities.display_name.ilike(like),
                    )
                )
            if feature_kind:
                query = query.filter(FeatureMetaEntities.feature_kind == feature_kind)
            if source_kind:
                query = query.filter(FeatureMetaEntities.source_kind == source_kind)
            if enabled is not None:
                query = query.filter(FeatureMetaEntities.enabled == enabled)
            total = query.count()
            rows = (
                query.order_by(
                    FeatureMetaEntities.sort_order,
                    FeatureMetaEntities.feature_name,
                )
                .offset(offset)
                .limit(limit)
                .all()
            )
            return rows, total
        finally:
            session.close()

    def get_by_id(self, feature_id: int) -> FeatureMetaEntities | None:
        session = self._db.get_session()
        try:
            return (
                session.query(FeatureMetaEntities)
                .filter(FeatureMetaEntities.id == feature_id)
                .one_or_none()
            )
        finally:
            session.close()

    def upsert_by_name(self, payload: dict[str, Any], *, keep_coverage: bool = True) -> None:
        session = self._db.get_session()
        try:
            name = payload["feature_name"]
            row = (
                session.query(FeatureMetaEntities)
                .filter(FeatureMetaEntities.feature_name == name)
                .one_or_none()
            )
            if row is None:
                session.add(FeatureMetaEntities(**payload))
            else:
                for key, value in payload.items():
                    if key == "feature_name":
                        continue
                    if keep_coverage and key in ("start_date", "end_date"):
                        continue
                    setattr(row, key, value)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_by_id(self, feature_id: int, fields: dict[str, Any]) -> FeatureMetaEntities | None:
        session = self._db.get_session()
        try:
            row = (
                session.query(FeatureMetaEntities)
                .filter(FeatureMetaEntities.id == feature_id)
                .one_or_none()
            )
            if row is None:
                return None
            for key, value in fields.items():
                nullable_ok = {
                    "remark",
                    "formula",
                    "display_name",
                    "source_path",
                    "source_column",
                    "transform",
                }
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

    def create(self, payload: dict[str, Any]) -> FeatureMetaEntities:
        session = self._db.get_session()
        try:
            exists = (
                session.query(FeatureMetaEntities)
                .filter(FeatureMetaEntities.feature_name == payload["feature_name"])
                .one_or_none()
            )
            if exists is not None:
                raise ValueError(f"特征符号已存在: {payload['feature_name']}")
            row = FeatureMetaEntities(**payload)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_coverage_by_source_kind(
        self, source_kinds: list[str], start_date: str | None, end_date: str | None
    ) -> int:
        session = self._db.get_session()
        try:
            q = session.query(FeatureMetaEntities).filter(
                FeatureMetaEntities.source_kind.in_(source_kinds)
            )
            updated = 0
            for row in q.all():
                row.start_date = start_date
                row.end_date = end_date
                updated += 1
            session.commit()
            return updated
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
