"""数据源优先级配置实体"""

from sqlalchemy import Boolean, Column, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DataSourceConfigEntities(Base):
    __tablename__ = "data_source_config"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    data_key = Column(String(64), nullable=False, comment="数据类型键，如 kline_daily")
    source = Column(String(32), nullable=False, comment="数据源标识，如 tushare、tdx_quant")
    priority = Column(Integer, nullable=False, default=1, comment="优先级，数值越小越优先")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")

    __table_args__ = (
        Index(
            "idx_data_source_config_unique",
            "data_key",
            "source",
            unique=True,
        ),
        Index("idx_data_source_config_data_key", "data_key"),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(DataSourceConfigEntities)
