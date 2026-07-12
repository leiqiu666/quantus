from pydantic import BaseModel, Field


class FactorComboItem(BaseModel):
    factor_name: str
    weight: float = 1.0


class FactorComboCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    items: list[FactorComboItem] = Field(min_length=2)
    remark: str | None = None


class FactorComboUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    items: list[FactorComboItem] | None = Field(default=None, min_length=2)
    remark: str | None = None


class FactorComboOut(BaseModel):
    id: int
    name: str
    items: list[FactorComboItem]
    remark: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class BacktestRunListItem(BaseModel):
    run_id: str
    backtest_mode: str
    factor_name: str | None = None
    combo_id: int | None = None
    combo_name: str | None = None
    start_date: str
    end_date: str
    rebalance: str
    groups: int
    status: str
    ic_mean: float | None = None
    rank_ic_mean: float | None = None
    sharpe: float | None = None
    annual_return: float | None = None
    mdd: float | None = None
    output_dir: str | None = None
    error_message: str | None = None
    created_at: str | None = None


class BacktestRunDetail(BacktestRunListItem):
    summary: dict = Field(default_factory=dict)
    returns: list[dict] = Field(default_factory=list)
    ic: list[dict] = Field(default_factory=list)
    nav_curves: dict[str, list[dict]] = Field(default_factory=dict)
    group_totals: list[dict] = Field(default_factory=list)
    turnover_series: list[dict] = Field(default_factory=list)
    yearly: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    cost: dict = Field(default_factory=dict)
    benchmark: str | None = None


class BacktestTableResponse(BaseModel):
    name: str
    columns: list[str]
    rows: list[dict]
    total: int
