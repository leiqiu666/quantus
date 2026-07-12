"""调度任务实体"""

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ScheduleJobEntities(Base):
    __tablename__ = "schedule_job"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    job_key = Column(String(64), nullable=False, comment="任务唯一键")
    name = Column(String(128), nullable=False, comment="显示名")
    schedule_kind = Column(String(32), nullable=False, comment="daily_at / weekdays_at / cron")
    schedule_time = Column(String(5), nullable=False, comment="HH:MM 上海时区")
    cron_expr = Column(String(64), nullable=True, comment="cron 表达式")
    run_on_trading_day = Column(Boolean, nullable=False, default=False, comment="仅 SSE 开市日执行")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, comment="更新时间")

    __table_args__ = (
        Index("idx_schedule_job_job_key", "job_key", unique=True),
        Index("idx_schedule_job_enabled", "enabled"),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(ScheduleJobEntities)
