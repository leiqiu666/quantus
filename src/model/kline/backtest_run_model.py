"""backtest_run Model。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.common.database import Database
from src.entities.data_entities.kline.backtest_run_entities import BacktestRunEntities


class BacktestRunModel:
    def __init__(self) -> None:
        self._db = Database()

    def save_success(self, payload: dict[str, Any]) -> BacktestRunEntities:
        session = self._db.get_session()
        try:
            row = BacktestRunEntities(
                run_id=payload["run_id"],
                backtest_mode=payload["backtest_mode"],
                factor_name=payload.get("factor_name"),
                combo_id=payload.get("combo_id"),
                combo_name=payload.get("combo_name"),
                start_date=payload["start_date"],
                end_date=payload["end_date"],
                rebalance=payload.get("rebalance") or "monthly",
                groups=int(payload.get("groups") or 10),
                status="success",
                summary_json=payload.get("summary"),
                output_dir=payload.get("output_dir"),
                error_message=None,
                created_at=datetime.now(),
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

    def save_failed(self, payload: dict[str, Any], error_message: str) -> BacktestRunEntities:
        session = self._db.get_session()
        try:
            row = BacktestRunEntities(
                run_id=payload["run_id"],
                backtest_mode=payload["backtest_mode"],
                factor_name=payload.get("factor_name"),
                combo_id=payload.get("combo_id"),
                combo_name=payload.get("combo_name"),
                start_date=payload["start_date"],
                end_date=payload["end_date"],
                rebalance=payload.get("rebalance") or "monthly",
                groups=int(payload.get("groups") or 10),
                status="failed",
                error_message=(error_message or "")[:2000],
                created_at=datetime.now(),
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

    def list_recent(self, limit: int = 50) -> list[BacktestRunEntities]:
        session = self._db.get_session()
        try:
            return (
                session.query(BacktestRunEntities)
                .order_by(BacktestRunEntities.created_at.desc())
                .limit(max(1, min(int(limit), 200)))
                .all()
            )
        finally:
            session.close()

    def get_by_run_id(self, run_id: str) -> BacktestRunEntities | None:
        session = self._db.get_session()
        try:
            return (
                session.query(BacktestRunEntities)
                .filter(BacktestRunEntities.run_id == run_id)
                .one_or_none()
            )
        finally:
            session.close()
