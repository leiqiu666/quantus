"""股票列表 API 契约（与 stock_list 表字段一致）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StockListItem(BaseModel):
    """与 StockListEntities / stock_list 表列一致。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="主键")
    ts_code: str | None = Field(default=None, description="股票代码")
    symbol: str | None = Field(default=None, description="股票简称")
    name: str | None = Field(default=None, description="股票名称")
    fullname: str | None = Field(default=None, description="全称")
    enname: str | None = Field(default=None, description="英文名称")
    cnspell: str | None = Field(default=None, description="拼音简称")
    market: str | None = Field(
        default=None,
        description="市场类型(主板/中小板/创业板/科创板/港股通/北交所等)",
    )
    exchange: str | None = Field(default=None, description="交易所代码")
    curr_type: str | None = Field(default=None, description="交易货币")
    list_status: str | None = Field(default=None, description="上市状态")
    list_date: str | None = Field(default=None, description="上市日期")
    delist_date: str | None = Field(default=None, description="退市日期")
    is_hs: str | None = Field(default=None, description="是否沪深港通标的(1是/0否)")
    is_ggt: str | None = Field(default=None, description="是否港股通标的(1是/0否)")
    shenwan_1: str | None = Field(default=None, description="申万一级行业代码")
    shenwan_2: str | None = Field(default=None, description="申万二级行业名称")
    shenwan_3: str | None = Field(default=None, description="申万三级行业代码")
    zhengjian_1: str | None = Field(default=None, description="证监会一级行业代码")
    zhengjian_2: str | None = Field(default=None, description="证监会二级行业名称")
    concept: str | None = Field(default=None, description="概念代码")
    area: str | None = Field(default=None, description="地区")
    city: str | None = Field(default=None, description="城市")
    country: str | None = Field(default=None, description="国家")
    kline_day_ddl: datetime | None = Field(default=None, description="日线数据更新截止日期")
    kline_min_ddl: datetime | None = Field(default=None, description="分钟线数据更新截止日期")
    report_income_ddl: datetime | None = Field(
        default=None, description="财报（利润表相关）更新截止日期"
    )
    report_cashflow_ddl: datetime | None = Field(
        default=None, description="现金流量表更新截止日期"
    )
    report_profit_ddl: datetime | None = Field(default=None, description="利润表更新截止日期")
    report_balance_ddl: datetime | None = Field(
        default=None, description="资产负债表更新截止日期"
    )
