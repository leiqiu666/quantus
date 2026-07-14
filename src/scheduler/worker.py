"""Scheduler Worker 入口（可选：独立进程部署时使用；默认随 API 启动）。"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time

from src.scheduler.engine import SchedulerEngine
from src.service.scheduler.schedule_run_service import ScheduleRunService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    if os.environ.get("SCHEDULER_EMBEDDED_IN_API", "").lower() in ("1", "true", "yes"):
        logger.error(
            "调度已随 quantus-api 启动，无需单独运行 quantus-scheduler；"
            "若需独立进程请 unset SCHEDULER_EMBEDDED_IN_API 并设 SCHEDULER_ENABLED=false"
        )
        sys.exit(1)
    engine = SchedulerEngine()
    abandoned = ScheduleRunService().abandon_orphan_runs()
    if abandoned:
        logger.warning("abandoned %s orphan schedule_run(s) left as running", abandoned)
    engine.start()
    logger.info("quantus-scheduler running; Ctrl+C to stop")

    def _shutdown(signum, _frame) -> None:
        logger.info("received signal %s, shutting down", signum)
        engine.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        engine.shutdown()


if __name__ == "__main__":
    main()
