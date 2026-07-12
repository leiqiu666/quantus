"""因子元数据响应 Schema。"""

from pydantic import BaseModel, Field


class FactorMetaItem(BaseModel):
    factor_name: str = Field(description="因子名称")
    display_name: str | None = Field(default=None, description="中文名称")
    source: str = Field(description="来源：自研 / tushare")
    category: str | None = Field(default=None, description="分类")
    formula: str | None = Field(default=None, description="算法说明")
    start_date: str | None = Field(default=None, description="Parquet 最早交易日")
    end_date: str | None = Field(default=None, description="Parquet 最晚交易日")
    month_count: int | None = Field(default=None, description="已有 Parquet 月份数")
