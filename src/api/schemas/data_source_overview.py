from pydantic import BaseModel, Field


class OverviewWorstColumn(BaseModel):
    key: str
    label: str
    ratio: float


class OverviewGroupItem(BaseModel):
    group_id: str
    title: str
    date_label: str
    date_key_type: str
    column_count: int
    window_row_count: int
    rows_complete: int
    complete_rate: float
    gap_cell_count: int
    status: str
    worst_column: OverviewWorstColumn | None = None
    latest_gap_date_key: str | None = None
    detail_path: str = ""


class OverviewGapItem(BaseModel):
    group_id: str
    group_title: str
    date_key: str
    date_key_type: str
    column_key: str
    column_label: str
    ratio: float | None = None
    threshold: float = 0.95
    sse_task_key: str = ""


class OverviewActiveStock(BaseModel):
    date_key: str
    listed_count: int
    trading_count: int


class OverviewKeyPathItem(BaseModel):
    name: str
    latest_date: str | None = None
    reference_date: str | None = None
    lag_days: int | None = None
    status: str


class OverviewSchedulerRunItem(BaseModel):
    run_id: int
    job_key: str | None = None
    triggered_by: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None


class OverviewSchedulerSummary(BaseModel):
    jobs_enabled_count: int
    last_run_at: str | None = None
    today_run_count: int
    today_success_count: int
    recent_runs: list[OverviewSchedulerRunItem] = Field(default_factory=list)


class OverviewResponse(BaseModel):
    as_of: str
    latest_trade_date: str | None = None
    is_trading_day: bool
    window: int
    source_total: int
    group_total: int
    groups_healthy: int
    gap_cell_count: int
    active_stock: OverviewActiveStock | None = None
    groups: list[OverviewGroupItem]
    gaps: list[OverviewGapItem]
    key_paths: list[OverviewKeyPathItem] = Field(default_factory=list)
    scheduler: OverviewSchedulerSummary
