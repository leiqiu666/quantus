"""schedule_run / schedule_run_step Model。"""

from __future__ import annotations

from datetime import datetime

from src.common.database import Database
from src.entities.data_entities.scheduler.schedule_run_entities import ScheduleRunEntities
from src.entities.data_entities.scheduler.schedule_run_step_entities import ScheduleRunStepEntities


class ScheduleRunModel:
    def __init__(self) -> None:
        self._db = Database()

    def create_run(
        self,
        *,
        job_id: int | None,
        triggered_by: str,
        status: str,
        started_at: datetime,
    ) -> ScheduleRunEntities:
        session = self._db.get_session()
        try:
            row = ScheduleRunEntities(
                job_id=job_id,
                triggered_by=triggered_by,
                status=status,
                started_at=started_at,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        finished_at: datetime,
        error_message: str | None = None,
    ) -> None:
        session = self._db.get_session()
        try:
            row = session.query(ScheduleRunEntities).filter(ScheduleRunEntities.id == run_id).first()
            if row is None:
                return
            row.status = status
            row.finished_at = finished_at
            row.error_message = error_message
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_run(self, run_id: int) -> ScheduleRunEntities | None:
        session = self._db.get_session()
        try:
            return session.query(ScheduleRunEntities).filter(ScheduleRunEntities.id == run_id).first()
        finally:
            session.close()

    def has_running_for_job(self, job_id: int) -> bool:
        session = self._db.get_session()
        try:
            return (
                session.query(ScheduleRunEntities)
                .filter(
                    ScheduleRunEntities.job_id == job_id,
                    ScheduleRunEntities.status == "running",
                )
                .count()
                > 0
            )
        finally:
            session.close()

    def list_runs(
        self,
        *,
        job_id: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ScheduleRunEntities], int]:
        session = self._db.get_session()
        try:
            query = session.query(ScheduleRunEntities)
            if job_id is not None:
                query = query.filter(ScheduleRunEntities.job_id == job_id)
            total = query.count()
            rows = (
                query.order_by(ScheduleRunEntities.started_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return rows, total
        finally:
            session.close()

    def recent_runs(self, limit: int = 10) -> list[ScheduleRunEntities]:
        session = self._db.get_session()
        try:
            return (
                session.query(ScheduleRunEntities)
                .order_by(ScheduleRunEntities.started_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def last_run_at(self) -> datetime | None:
        session = self._db.get_session()
        try:
            row = (
                session.query(ScheduleRunEntities)
                .order_by(ScheduleRunEntities.started_at.desc())
                .first()
            )
            return row.started_at if row else None
        finally:
            session.close()

    def create_step(
        self,
        *,
        run_id: int,
        command_key: str,
        sort_order: int,
        status: str,
        saved_count: int | None = None,
        message: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> ScheduleRunStepEntities:
        session = self._db.get_session()
        try:
            row = ScheduleRunStepEntities(
                run_id=run_id,
                command_key=command_key,
                sort_order=sort_order,
                status=status,
                saved_count=saved_count,
                message=message,
                started_at=started_at,
                finished_at=finished_at,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_step(
        self,
        step_id: int,
        *,
        status: str,
        saved_count: int | None = None,
        message: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        session = self._db.get_session()
        try:
            row = session.query(ScheduleRunStepEntities).filter(ScheduleRunStepEntities.id == step_id).first()
            if row is None:
                return
            row.status = status
            if saved_count is not None:
                row.saved_count = saved_count
            if message is not None:
                row.message = message
            if started_at is not None:
                row.started_at = started_at
            if finished_at is not None:
                row.finished_at = finished_at
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_steps_for_run(self, run_id: int) -> list[ScheduleRunStepEntities]:
        session = self._db.get_session()
        try:
            return (
                session.query(ScheduleRunStepEntities)
                .filter(ScheduleRunStepEntities.run_id == run_id)
                .order_by(ScheduleRunStepEntities.sort_order)
                .all()
            )
        finally:
            session.close()
