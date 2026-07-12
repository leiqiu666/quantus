"""APScheduler 引擎：加载 DB 任务并按周期触发。"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.model.scheduler.schedule_job_model import ScheduleJobModel
from src.scheduler.runner import execute_job
from src.service.scheduler.schedule_job_service import ScheduleJobService

logger = logging.getLogger(__name__)

TZ = "Asia/Shanghai"
DEFAULT_RELOAD_INTERVAL = 60


class SchedulerEngine:
    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(timezone=TZ)
        self._job_service = ScheduleJobService()
        self._job_model = ScheduleJobModel()
        self._last_config_version: datetime | None = None
        self._reload_interval = int(os.environ.get("SCHEDULER_RELOAD_INTERVAL", DEFAULT_RELOAD_INTERVAL))

    def start(self) -> None:
        self._reload_jobs()
        self._scheduler.add_job(
            self._reload_jobs,
            trigger="interval",
            seconds=self._reload_interval,
            id="schedule_config_reload",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("scheduler engine started, reload interval=%ss", self._reload_interval)

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def is_running(self) -> bool:
        return self._scheduler.running

    def _reload_jobs(self) -> None:
        version = self._job_model.max_updated_at()
        if version == self._last_config_version and self._scheduler.get_jobs():
            scheduled = [j for j in self._scheduler.get_jobs() if j.id != "schedule_config_reload"]
            if scheduled:
                return
        self._last_config_version = version

        for job in self._scheduler.get_jobs():
            if job.id != "schedule_config_reload":
                job.remove()

        for job in self._job_service.list_enabled_jobs_for_worker():
            trigger = self._build_trigger(job)
            if trigger is None:
                continue
            job_id = job["id"]
            job_key = job["job_key"]
            self._scheduler.add_job(
                self._run_job,
                trigger=trigger,
                id=f"schedule_job_{job_key}",
                kwargs={"job_id": job_id, "job_key": job_key},
                replace_existing=True,
            )
            logger.info("registered job %s (%s)", job_key, job["schedule_kind"])

    def _build_trigger(self, job: dict):
        kind = job["schedule_kind"]
        time_str = job["schedule_time"] or "00:00"
        hour, minute = (int(x) for x in time_str.split(":", 1))
        if kind == "daily_at":
            return CronTrigger(hour=hour, minute=minute, timezone=TZ)
        if kind == "weekdays_at":
            return CronTrigger(
                day_of_week="mon-fri",
                hour=hour,
                minute=minute,
                timezone=TZ,
            )
        if kind == "cron" and job.get("cron_expr"):
            return CronTrigger.from_crontab(job["cron_expr"], timezone=TZ)
        logger.warning("skip job %s: unsupported schedule_kind=%s", job["job_key"], kind)
        return None

    @staticmethod
    def _run_job(job_id: int, job_key: str) -> None:
        logger.info("trigger job %s (id=%s)", job_key, job_id)
        execute_job(job_id, triggered_by="cron")
