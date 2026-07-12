"""业绩预告 本地 Extract：直接读库解析增量起点。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.financial.financial_forecast_entities import ForecastEntities


class ForecastLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_end_date(self) -> str | None:
        session: Session = self._db.get_session()
        try:
            row = session.query(func.max(ForecastEntities.end_date)).scalar()
            if row is None:
                return None
            s = str(row).strip()
            return s[:8] if len(s) >= 8 else None
        finally:
            session.close()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        configured = (configured_start or "").strip()
        max_end = self.get_max_end_date()

        if not max_end:
            return configured

        if not configured:
            return max_end

        return max(configured, max_end)
