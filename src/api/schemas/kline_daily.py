from pydantic import BaseModel, Field, model_validator


class KlineDailyDateItem(BaseModel):
    """单个交易日及日 K 采集条数。"""

    trade_date: str = Field(description="开市日 YYYYMMDD")
    period_stock_count: int = Field(
        default=0,
        description="该日应交易股票数（stock_active_count.trading_count）",
    )
    kline_daily_count: int = Field(description="kline_daily 该日记录数")
    kline_adj_factor_count: int = Field(description="kline_daily.adj_factor 非空该日记录数")
    kline_stk_limit_count: int = Field(
        description="kline_daily.up_limit、down_limit 均已入库该日记录数"
    )


class KlineDailyDateListRequest(BaseModel):
    """日 K 交易日列表查询：按 trade_date 筛选。"""

    start_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description="交易日下界（含），YYYYMMDD；省略时默认为 KLINE_DAILY_START_DATE 或 19900101",
    )
    end_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description="交易日上界（含），YYYYMMDD；省略时默认为当天（YYYYMMDD）",
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 起；第 1 页为最新开市日")
    count: int = Field(
        default=50,
        ge=1,
        le=500,
        description="每页返回的开市日条数（按 SSE 开市日序列分页）",
    )

    @model_validator(mode="after")
    def start_not_after_end(self) -> "KlineDailyDateListRequest":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date 不能大于 end_date")
        return self


class KlineDailyDateListResponse(BaseModel):
    """日 K 交易日列表分页响应。"""

    items: list[KlineDailyDateItem] = Field(description="当前页数据（仅含库中有日 K 的开市日）")
    total: int = Field(
        description="区间内 SSE 开市日总数（用于前端 ProTable 分页，与 items 条数可能不同）"
    )
