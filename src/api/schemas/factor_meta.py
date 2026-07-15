"""因子元数据响应 Schema。"""

from pydantic import BaseModel, Field


class FactorMetaItem(BaseModel):
    factor_name: str = Field(description="因子名称")
    display_name: str | None = Field(default=None, description="中文名称")
    source: str = Field(description="来源：自研 / tushare / 国泰191")
    category: str | None = Field(default=None, description="分类")
    formula: str | None = Field(default=None, description="算法说明或可编辑公式")
    impl_kind: str | None = Field(
        default=None, description="formula / python / tushare"
    )
    python_path: str | None = Field(default=None, description="Python 源码相对路径")
    start_date: str | None = Field(default=None, description="Parquet 最早交易日")
    end_date: str | None = Field(default=None, description="Parquet 最晚交易日")
    month_count: int | None = Field(default=None, description="已有 Parquet 月份数")


class FactorMetaListResponse(BaseModel):
    items: list[FactorMetaItem]
    total: int


class FactorMetaUpdateRequest(BaseModel):
    display_name: str | None = None
    category: str | None = None
    formula: str | None = None


class FactorSourceResponse(BaseModel):
    factor_name: str
    python_path: str
    content: str
