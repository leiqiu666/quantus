"""schedule_job / schedule_job_command Model。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func

from src.common.database import Database
from src.entities.data_entities.scheduler.schedule_job_command_entities import (
    ScheduleJobCommandEntities,
)
from src.entities.data_entities.scheduler.schedule_job_entities import ScheduleJobEntities


class ScheduleJobModel:
    def __init__(self) -> None:
        self._db = Database()

    def list_jobs(self) -> list[ScheduleJobEntities]:
        session = self._db.get_session()
        try:
            return (
                session.query(ScheduleJobEntities)
                .order_by(ScheduleJobEntities.job_key)
                .all()
            )
        finally:
            session.close()

    def list_enabled_jobs(self) -> list[ScheduleJobEntities]:
        session = self._db.get_session()
        try:
            return (
                session.query(ScheduleJobEntities)
                .filter(ScheduleJobEntities.enabled.is_(True))
                .order_by(ScheduleJobEntities.job_key)
                .all()
            )
        finally:
            session.close()

    def get_by_job_key(self, job_key: str) -> ScheduleJobEntities | None:
        session = self._db.get_session()
        try:
            return (
                session.query(ScheduleJobEntities)
                .filter(ScheduleJobEntities.job_key == job_key)
                .first()
            )
        finally:
            session.close()

    def get_by_id(self, job_id: int) -> ScheduleJobEntities | None:
        session = self._db.get_session()
        try:
            return session.query(ScheduleJobEntities).filter(ScheduleJobEntities.id == job_id).first()
        finally:
            session.close()

    def max_updated_at(self) -> datetime | None:
        session = self._db.get_session()
        try:
            return session.query(func.max(ScheduleJobEntities.updated_at)).scalar()
        finally:
            session.close()

    def create_job(
        self,
        *,
        job_key: str,
        name: str,
        schedule_kind: str,
        schedule_time: str,
        cron_expr: str | None,
        run_on_trading_day: bool,
        enabled: bool,
        now: datetime,
    ) -> ScheduleJobEntities:
        session = self._db.get_session()
        try:
            row = ScheduleJobEntities(
                job_key=job_key,
                name=name,
                schedule_kind=schedule_kind,
                schedule_time=schedule_time,
                cron_expr=cron_expr,
                run_on_trading_day=run_on_trading_day,
                enabled=enabled,
                created_at=now,
                updated_at=now,
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

    def update_job(self, job: ScheduleJobEntities, **fields) -> ScheduleJobEntities:
        session = self._db.get_session()
        try:
            merged = session.merge(job)
            for key, value in fields.items():
                setattr(merged, key, value)
            session.commit()
            session.refresh(merged)
            return merged
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_job(self, job_id: int) -> None:
        session = self._db.get_session()
        try:
            session.query(ScheduleJobCommandEntities).filter(
                ScheduleJobCommandEntities.job_id == job_id,
            ).delete(synchronize_session=False)
            session.query(ScheduleJobEntities).filter(ScheduleJobEntities.id == job_id).delete(
                synchronize_session=False,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_commands_for_job(self, job_id: int) -> list[ScheduleJobCommandEntities]:
        session = self._db.get_session()
        try:
            return (
                session.query(ScheduleJobCommandEntities)
                .filter(ScheduleJobCommandEntities.job_id == job_id)
                .order_by(ScheduleJobCommandEntities.sort_order)
                .all()
            )
        finally:
            session.close()

    def list_all_commands(self) -> list[ScheduleJobCommandEntities]:
        session = self._db.get_session()
        try:
            return session.query(ScheduleJobCommandEntities).all()
        finally:
            session.close()

    def replace_commands(self, job_id: int, command_keys: list[str]) -> None:
        session = self._db.get_session()
        try:
            session.query(ScheduleJobCommandEntities).filter(
                ScheduleJobCommandEntities.job_id == job_id,
            ).delete(synchronize_session=False)
            for idx, command_key in enumerate(command_keys):
                session.add(
                    ScheduleJobCommandEntities(
                        job_id=job_id,
                        command_key=command_key,
                        sort_order=idx,
                    ),
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def command_reference_map(self) -> dict[str, list[str]]:
        session = self._db.get_session()
        try:
            rows = (
                session.query(ScheduleJobCommandEntities, ScheduleJobEntities)
                .join(
                    ScheduleJobEntities,
                    ScheduleJobEntities.id == ScheduleJobCommandEntities.job_id,
                )
                .all()
            )
            result: dict[str, list[str]] = {}
            for cmd, job in rows:
                result.setdefault(cmd.command_key, [])
                if job.job_key not in result[cmd.command_key]:
                    result[cmd.command_key].append(job.job_key)
            return result
        finally:
            session.close()

    def count_enabled_jobs(self) -> int:
        session = self._db.get_session()
        try:
            return (
                session.query(ScheduleJobEntities)
                .filter(ScheduleJobEntities.enabled.is_(True))
                .count()
            )
        finally:
            session.close()
