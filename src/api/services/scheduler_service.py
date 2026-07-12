"""API 进程内调度引擎生命周期（与 tdx_quant_service 同级）。"""

from __future__ import annotations

import logging

from src.common.setting import settings
from src.scheduler.engine import SchedulerEngine

logger = logging.getLogger(__name__)

_engine: SchedulerEngine | None = None


def is_enabled() -> bool:
    return settings.scheduler_enabled


def is_running() -> bool:
    return _engine is not None and _engine.is_running()


def startup() -> None:
    global _engine
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
