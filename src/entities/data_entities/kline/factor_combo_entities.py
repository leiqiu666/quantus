"""因子组合配方表：多因子回测用，不物化 Parquet。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FactorComboEntities(Base):
    __tablename__ = "factor_combo"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    name = Column(String(100), nullable=False, comment="组合唯一名")
    items = Column(JSONB, nullable=False, comment="[{factor_name, weight}, ...]")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, comment="更新时间")

    __table_args__ = (
        Index("idx_factor_combo_name", "name", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(FactorComboEntities, interactive=True)
