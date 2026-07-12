from pydantic import BaseModel, Field, model_validator


class EtlSseRunRequest(BaseModel):
    task_key: str = Field(description="SSE 任务键，与看板列 meta.sse_task_key 一致")
    start_date: str = Field(pattern=r"^\d{8}$", description="起始 YYYYMMDD")
    end_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description="结束 YYYYMMDD；report history init 类任务可省略",
    )
    # 仅 task_key=backtest_run 使用
    backtest_mode: str | None = Field(
        default=None, description="single | combo（backtest_run）"
    )
    factor_name: str | None = Field(default=None, description="单因子名")
    combo_id: int | None = Field(default=None, description="因子组合 ID")
    groups: int | None = Field(default=10, description="分组数，默认 10")
    rebalance: str | None = Field(
        default="monthly", description="monthly | weekly"
    )
    commission_rate: float | None = Field(
        default=None, description="佣金费率，默认 0.0003"
    )
    stamp_duty_rate: float | None = Field(
        default=None, description="印花税（卖出），默认 0.001"
    )
    slippage_rate: float | None = Field(
        default=None, description="滑点费率，默认 0"
    )
    # task_key=gtja191_compute 可选
    workers: int | None = Field(
        default=None, description="国泰191 月内并行进程数；默认自动探测"
    )

    @model_validator(mode="after")
    def validate_range(self) -> "EtlSseRunRequest":
        if self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date 不能大于 end_date")
        return self
