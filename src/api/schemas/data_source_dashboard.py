from pydantic import BaseModel, Field, model_validator


class ColumnMetric(BaseModel):
    count: int = Field(description="实到条数")
    period_stock_count: int = Field(default=0, description="分母")
    ratio: float | None = Field(default=None, description="count/period_stock_count")
    is_complete: bool = Field(default=False)
    has_snapshot: bool = Field(default=True)
    threshold: float = Field(default=0.95)


class DashboardColumnMeta(BaseModel):
    key: str
    label: str
    threshold: float = 0.95
    sse_task_key: str = ""


class DashboardRow(BaseModel):
    date_key: str
    period_stock_count: int | None = None
    columns: dict[str, ColumnMetric]
    row_complete: bool = False


class DashboardMeta(BaseModel):
    group_id: str
    title: str
    date_key_type: str
    date_label: str
    columns: list[DashboardColumnMeta]
    default_start: str = Field(description="分组 ETL 默认起点（YYYYMMDD 或 YYYYMM）")
    default_end: str = Field(description="默认终点（通常为今天或本月）")


class DashboardRequest(BaseModel):
    group_id: str = Field(description="看板分组 ID")
    start: str | None = Field(default=None, description="区间起点（YYYYMMDD 或 YYYYMM）")
    end: str | None = Field(default=None, description="区间终点")
    page: int = Field(default=1, ge=1)
    count: int = Field(default=50, ge=1, le=500)

    @model_validator(mode="after")
    def validate_range(self) -> "DashboardRequest":
        if self.start and self.end and self.start > self.end:
            raise ValueError("start 不能大于 end")
        return self


class DashboardResponse(BaseModel):
    items: list[DashboardRow]
    total: int
    meta: DashboardMeta
