"""调度系统 API Schema。"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ScheduleKind = Literal["daily_at", "weekdays_at", "cron"]
ScheduleHint = Literal["morning", "pre_open", "post_close", "anytime"]


class ScheduleCommandItem(BaseModel):
    command_key: str
    label: str
    typer_group: str
    typer_command: str
    category: str
    schedule_hint: ScheduleHint
    run_on_trading_day: bool
    referenced_by: list[str] = Field(default_factory=list)
    is_referenced: bool = False


class ScheduleJobItem(BaseModel):
    job_key: str
    name: str
    schedule_kind: ScheduleKind
    schedule_time: str
    cron_expr: Optional[str] = None
    run_on_trading_day: bool = False
    enabled: bool = True
    command_keys: list[str] = Field(default_factory=list)
    command_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ScheduleJobCreateRequest(BaseModel):
    job_key: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    schedule_kind: ScheduleKind = "daily_at"
    schedule_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    cron_expr: Optional[str] = None
    run_on_trading_day: bool = False
    enabled: bool = True
    command_keys: list[str] = Field(..., min_length=1)


class ScheduleJobUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    schedule_kind: Optional[ScheduleKind] = None
    schedule_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    cron_expr: Optional[str] = None
    run_on_trading_day: Optional[bool] = None
    enabled: Optional[bool] = None
    command_keys: Optional[list[str]] = None


class ScheduleRunStepItem(BaseModel):
    step_id: int
    command_key: str
    sort_order: int
    status: str
    saved_count: Optional[int] = None
    message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ScheduleRunItem(BaseModel):
    run_id: int
    job_id: Optional[int] = None
    job_key: Optional[str] = None
    triggered_by: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    steps: list[ScheduleRunStepItem] = Field(default_factory=list)


class ScheduleRunListRequest(BaseModel):
    job_key: Optional[str] = None
    page: int = Field(default=1, ge=1)
    count: int = Field(default=20, ge=1, le=500)


class ScheduleRunListResponse(BaseModel):
    items: list[ScheduleRunItem]
    total: int


class ScheduleOverviewResponse(BaseModel):
    command_total: int
    command_referenced_count: int
    command_unreferenced_count: int
    commands: list[ScheduleCommandItem]
    jobs_enabled_count: int
    last_run_at: Optional[str] = None
    recent_runs: list[ScheduleRunItem] = Field(default_factory=list)


class ScheduleRunTriggerResponse(BaseModel):
    run_id: int
