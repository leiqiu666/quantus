"""调度 Service：命令覆盖看板。"""

from __future__ import annotations

from src.model.scheduler.schedule_job_model import ScheduleJobModel
from src.model.scheduler.schedule_run_model import ScheduleRunModel
from src.scheduler.command_registry import all_command_specs
from src.service.scheduler.schedule_run_service import ScheduleRunService


class ScheduleOverviewService:
    def __init__(self) -> None:
        self._job_model = ScheduleJobModel()
        self._run_service = ScheduleRunService()

    def get_overview(self) -> dict:
        ref_map = self._job_model.command_reference_map()
        commands: list[dict] = []
        referenced = 0
        for spec in all_command_specs():
            refs = ref_map.get(spec.command_key, [])
            is_ref = len(refs) > 0
            if is_ref:
                referenced += 1
            commands.append({
                "command_key": spec.command_key,
                "label": spec.label,
                "typer_group": spec.typer_group,
                "typer_command": spec.typer_command,
                "category": spec.category,
                "schedule_hint": spec.schedule_hint,
                "run_on_trading_day": spec.run_on_trading_day,
                "referenced_by": refs,
                "is_referenced": is_ref,
            })
        total = len(commands)
        return {
            "command_total": total,
            "command_referenced_count": referenced,
            "command_unreferenced_count": total - referenced,
            "commands": commands,
            "jobs_enabled_count": self._job_model.count_enabled_jobs(),
            "last_run_at": self._run_service.last_run_at(),
            "recent_runs": self._run_service.recent_runs(limit=10),
        }

    def list_commands(self) -> list[dict]:
        ref_map = self._job_model.command_reference_map()
        result: list[dict] = []
        for spec in all_command_specs():
            refs = ref_map.get(spec.command_key, [])
            result.append({
                "command_key": spec.command_key,
                "label": spec.label,
                "typer_group": spec.typer_group,
                "typer_command": spec.typer_command,
                "category": spec.category,
                "schedule_hint": spec.schedule_hint,
                "run_on_trading_day": spec.run_on_trading_day,
                "referenced_by": refs,
                "is_referenced": len(refs) > 0,
            })
        return result
