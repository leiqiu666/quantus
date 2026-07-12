"""调度 Service：任务 CRUD。"""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from src.model.scheduler.schedule_job_model import ScheduleJobModel
from src.scheduler.command_registry import validate_command_keys

_SCHEDULE_KINDS = frozenset({"daily_at", "weekdays_at", "cron"})
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


class ScheduleJobService:
    def __init__(self) -> None:
        self._model = ScheduleJobModel()

    def list_jobs(self) -> list[dict]:
        jobs = self._model.list_jobs()
        result: list[dict] = []
        for job in jobs:
            cmds = self._model.list_commands_for_job(job.id)
            result.append(self._job_to_dict(job, [c.command_key for c in cmds]))
        return result

    def get_job(self, job_key: str) -> dict | None:
        job = self._model.get_by_job_key(job_key)
        if job is None:
            return None
        cmds = self._model.list_commands_for_job(job.id)
        return self._job_to_dict(job, [c.command_key for c in cmds])

    def get_job_by_id(self, job_id: int) -> dict | None:
        job = self._model.get_by_id(job_id)
        if job is None:
            return None
        cmds = self._model.list_commands_for_job(job.id)
        return self._job_to_dict(job, [c.command_key for c in cmds])

    def create_job(self, payload: dict) -> dict:
        self._validate_payload(payload, require_key=True)
        now = datetime.now()
        try:
            job = self._model.create_job(
                job_key=payload["job_key"],
                name=payload["name"],
                schedule_kind=payload["schedule_kind"],
                schedule_time=payload["schedule_time"],
                cron_expr=payload.get("cron_expr"),
                run_on_trading_day=bool(payload.get("run_on_trading_day", False)),
                enabled=bool(payload.get("enabled", True)),
                now=now,
            )
        except IntegrityError as exc:
            raise ValueError(f"job_key 已存在: {payload['job_key']}") from exc
        self._model.replace_commands(job.id, payload["command_keys"])
        return self._job_to_dict(job, payload["command_keys"])

    def update_job(self, job_key: str, payload: dict) -> dict | None:
        job = self._model.get_by_job_key(job_key)
        if job is None:
            return None
        if "command_keys" in payload:
            validate_command_keys(payload["command_keys"])
        fields: dict = {"updated_at": datetime.now()}
        for key in ("name", "schedule_kind", "schedule_time", "cron_expr", "run_on_trading_day", "enabled"):
            if key in payload:
                fields[key] = payload[key]
        if "schedule_kind" in fields or "schedule_time" in fields:
            self._validate_schedule(
                fields.get("schedule_kind", job.schedule_kind),
                fields.get("schedule_time", job.schedule_time),
                fields.get("cron_expr", job.cron_expr),
            )
        job = self._model.update_job(job, **fields)
        if "command_keys" in payload:
            self._model.replace_commands(job.id, payload["command_keys"])
            command_keys = payload["command_keys"]
        else:
            cmds = self._model.list_commands_for_job(job.id)
            command_keys = [c.command_key for c in cmds]
        return self._job_to_dict(job, command_keys)

    def delete_job(self, job_key: str) -> bool:
        job = self._model.get_by_job_key(job_key)
        if job is None:
            return False
        self._model.delete_job(job.id)
        return True

    def list_enabled_jobs_for_worker(self) -> list[dict]:
        jobs = self._model.list_enabled_jobs()
        result: list[dict] = []
        for job in jobs:
            cmds = self._model.list_commands_for_job(job.id)
            result.append({
                "id": job.id,
                "job_key": job.job_key,
                "schedule_kind": job.schedule_kind,
                "schedule_time": job.schedule_time,
                "cron_expr": job.cron_expr,
                "run_on_trading_day": job.run_on_trading_day,
                "updated_at": job.updated_at,
            })
        return result

    def max_updated_at(self) -> datetime | None:
        return self._model.max_updated_at()

    def _validate_payload(self, payload: dict, *, require_key: bool) -> None:
        if require_key and not payload.get("job_key"):
            raise ValueError("job_key 不能为空")
        if not payload.get("name"):
            raise ValueError("name 不能为空")
        if not payload.get("command_keys"):
            raise ValueError("command_keys 不能为空")
        validate_command_keys(payload["command_keys"])
        self._validate_schedule(
            payload["schedule_kind"],
            payload["schedule_time"],
            payload.get("cron_expr"),
        )

    def _validate_schedule(
        self,
        schedule_kind: str,
        schedule_time: str,
        cron_expr: str | None,
    ) -> None:
        if schedule_kind not in _SCHEDULE_KINDS:
            raise ValueError(f"无效 schedule_kind: {schedule_kind}")
        if schedule_kind in ("daily_at", "weekdays_at"):
            if not _TIME_RE.match(schedule_time or ""):
                raise ValueError("schedule_time 须为 HH:MM")
        if schedule_kind == "cron" and not cron_expr:
            raise ValueError("cron 模式须提供 cron_expr")

    def _job_to_dict(self, job, command_keys: list[str]) -> dict:
        return {
            "job_key": job.job_key,
            "name": job.name,
            "schedule_kind": job.schedule_kind,
            "schedule_time": job.schedule_time,
            "cron_expr": job.cron_expr,
            "run_on_trading_day": job.run_on_trading_day,
            "enabled": job.enabled,
            "command_keys": command_keys,
            "command_count": len(command_keys),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }
