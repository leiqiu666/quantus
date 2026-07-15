"""特征目录 Schema。"""

from pydantic import BaseModel, Field


class FeatureMetaItem(BaseModel):
    id: int
    feature_name: str
    display_name: str | None = None
    feature_kind: str
    source_kind: str
    source_path: str | None = None
    source_column: str | None = None
    transform: str | None = None
    frequency: str
    domain: str
    dtype: str
    formula: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    enabled: int
    sort_order: int
    remark: str | None = None


class FeatureMetaListResponse(BaseModel):
    items: list[FeatureMetaItem]
    total: int


class FeatureMetaCreateRequest(BaseModel):
    feature_name: str = Field(min_length=1, max_length=64, description="公式符号，唯一")
    display_name: str | None = None
    feature_kind: str = Field(default="source", description="source / derived")
    source_kind: str = Field(default="kline_daily")
    source_path: str | None = None
    source_column: str | None = None
    transform: str | None = None
    frequency: str = Field(default="daily")
    domain: str = Field(default="stock")
    dtype: str = Field(default="float64")
    formula: str | None = None
    enabled: int = Field(default=1, ge=0, le=1)
    sort_order: int = Field(default=0)
    remark: str | None = None


class FeatureMetaUpdateRequest(BaseModel):
    display_name: str | None = None
    feature_kind: str | None = None
    source_kind: str | None = None
    source_path: str | None = None
    source_column: str | None = None
    transform: str | None = None
    frequency: str | None = None
    domain: str | None = None
    dtype: str | None = None
    formula: str | None = None
    enabled: int | None = Field(default=None, ge=0, le=1)
    sort_order: int | None = None
    remark: str | None = None


class FeatureSeedResponse(BaseModel):
    upserted: int


class FeatureCoverageResponse(BaseModel):
    updated: int
    kline_start: str | None = None
    kline_end: str | None = None
    index_start: str | None = None
    index_end: str | None = None
