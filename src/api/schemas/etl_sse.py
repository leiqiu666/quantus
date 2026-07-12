from pydantic import BaseModel, Field, model_validator


class EtlSseRunRequest(BaseModel):
    task_key: str = Field(description="SSE 任务键，与看板列 meta.sse_task_key 一致")
    start_date: str = Field(pattern=r"^\d{8}$", description="起始 YYYYMMDD")
    end_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description="结束 YYYYMMDD；report history init 类任务可省略",
    )

    @model_validator(mode="after")
    def validate_range(self) -> "EtlSseRunRequest":
        if self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date 不能大于 end_date")
        return self
