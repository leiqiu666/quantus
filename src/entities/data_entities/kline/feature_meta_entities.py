"""特征目录表：公式可用符号、血缘与覆盖区间（不物化特征值）。"""

from sqlalchemy import Column, Integer, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FeatureMetaEntities(Base):
    __tablename__ = "feature_meta"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    feature_name = Column(String(64), nullable=False, comment="公式符号（唯一）")
    display_name = Column(String(200), comment="中文名称")
    feature_kind = Column(String(32), nullable=False, comment="source / derived")
    source_kind = Column(String(64), nullable=False, comment="kline_daily / index_daily / derived")
    source_path = Column(String(200), comment="物理路径或表提示")
    source_column = Column(String(64), comment="源列名")
    transform = Column(Text, comment="变换说明")
    frequency = Column(String(16), nullable=False, default="daily", comment="频率")
    domain = Column(String(32), nullable=False, default="stock", comment="stock / index")
    dtype = Column(String(32), nullable=False, default="float64", comment="数据类型")
    formula = Column(Text, comment="派生特征公式")
    start_date = Column(String(8), comment="覆盖起始 YYYYMMDD")
    end_date = Column(String(8), comment="覆盖截止 YYYYMMDD")
    enabled = Column(Integer, nullable=False, default=1, comment="1 启用 / 0 禁用")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序")
    remark = Column(Text, comment="备注")

    __table_args__ = (
        Index("idx_feature_meta_name", "feature_name", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(FeatureMetaEntities, interactive=True)
