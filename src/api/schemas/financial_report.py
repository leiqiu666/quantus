from typing import Literal

from pydantic import BaseModel, Field, model_validator


class IncomeHistoryInitRequest(BaseModel):
    start_date: str = Field(
        default="19900101",
        pattern=r"^\d{8}$",
        description="财报期起点 YYYYMMDD",
    )


class IncomeHistoryInitResponse(BaseModel):
    periods: list[str]
    message: str = "ok"


class IncomeHistoryInitStreamStarted(BaseModel):
    """SSE：连接建立后立刻推送，避免客户端长时间看不到首包。"""

    status: Literal["started"] = "started"


class IncomeHistoryInitStreamRunning(BaseModel):
    """SSE：已算出总期数，尚未完成第一期入库。"""

    status: Literal["running"] = "running"
    total: int = Field(description="report_period 总期数")


class IncomeHistoryInitStreamProgress(BaseModel):
    """SSE 进度帧：每期 report_income_by_period 完成后推送。"""

    index: int = Field(description="当前期序号，从 1 起")
    total: int = Field(description="总期数")
    period: str = Field(description="报告期 YYYYMMDD")
    saved: int = Field(description="该期入库条数")


class IncomeHistoryInitStreamFinal(BaseModel):
    """SSE 结束帧：与 IncomeHistoryInitResponse.periods 一致。"""

    done: Literal[True] = True
    periods: list[str]


class IncomeHistoryInitStreamError(BaseModel):
    """SSE 错误帧：worker 线程捕获异常时推送。"""

    error: str


class ReportPeriodItem(BaseModel):
    """单期报告期及四张报表条数。"""

    report_period: str = Field(description="报告期 YYYYMMDD")
    period_stock_count: int = Field(
        default=0,
        description="该报告期在市股票数（来自 report_period_count 快照；无记录时为 0）",
    )
    report_income_count: int = Field(description="利润表该期记录数")
    report_balance_count: int = Field(description="资产负债表该期记录数")
    report_cashflow_count: int = Field(description="现金流量表该期记录数")
    report_indicator_count: int = Field(default=0, description="财务指标该期记录数")


class ReportPeriodListRequest(BaseModel):
    """报告期列表查询：按库表列 end_date（报告期）筛选，与请求字段名 start/end_period_date 区分。"""

    start_period_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description="报告期下界（含），YYYYMMDD；省略时默认为 19900101（与生成季度序列一致）",
    )
    end_period_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description="报告期上界（含），YYYYMMDD；省略时默认为当天（YYYYMMDD）",
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 起；第 1 页为最新报告期")
    count: int = Field(
        default=50,
        ge=1,
        le=500,
        description="每页返回的报告期条数（按季度末序列分页）",
    )

    @model_validator(mode="after")
    def start_not_after_end(self) -> "ReportPeriodListRequest":
        if (
            self.start_period_date is not None
            and self.end_period_date is not None
            and self.start_period_date > self.end_period_date
        ):
            raise ValueError("start_period_date 不能大于 end_period_date")
        return self
