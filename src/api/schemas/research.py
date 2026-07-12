"""投研分析 API schemas。"""

from pydantic import BaseModel, Field


class FactorCsResponse(BaseModel):
    trade_date: str
    factor_name: str
    rows: list[dict] = Field(default_factory=list)
    quantiles: dict = Field(default_factory=dict)


class StockKlineResponse(BaseModel):
    ts_code: str
    start: str
    end: str
    bars: list[dict] = Field(default_factory=list)
    factor: list[dict] = Field(default_factory=list)
    factor_name: str | None = None


class QuoteResponse(BaseModel):
    mode: str
    ts_code: str
    trade_date: str | None = None
    price: float | None = None
    pre_close: float | None = None
    change_pct: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    vol: float | None = None
    message: str | None = None
