"""API 进程内调度引擎生命周期（与 tdx_quant_service 同级）。"""

from __future__ import annotations

import logging

from src.common.setting import settings
from src.scheduler.engine import SchedulerEngine
from src.service.scheduler.schedule_run_service import ScheduleRunService

logger = logging.getLogger(__name__)

_engine: SchedulerEngine | None = None


def is_enabled() -> bool:
    return settings.scheduler_enabled


def is_running() -> bool:
    return _engine is not None and _engine.is_running()


def startup() -> None:
    global _engine
    # API / Worker 启动时清理上次进程残留的 running，避免「已有运行中实例」误拦
    abandoned = ScheduleRunService().abandon_orphan_runs()
    if abandoned:
        logger.warning("abandoned %s orphan schedule_run(s) left as running", abandoned)
    if not settings.scheduler_enabled:
        logger.info("scheduler disabled (SCHEDULER_ENABLED=false)")
        return
    if _engine is not None:
        return
    _engine = SchedulerEngine()
    _engine.start()
    logger.info("scheduler started inside API process")


def shutdown() -> None:
    global _engine
    if _engine is None:
        return
    _engine.shutdown()
    _engine = None
