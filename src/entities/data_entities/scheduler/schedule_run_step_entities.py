"""调度执行步骤实体"""

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ScheduleRunStepEntities(Base):
    __tablename__ = "schedule_run_step"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    run_id = Column(Integer, nullable=False, comment="schedule_run.id")
    command_key = Column(String(64), nullable=False, comment="ETL 命令键")
    sort_order = Column(Integer, nullable=False, default=0, comment="串行顺序")
    status = Column(String(16), nullable=False, comment="pending / running / success / failed / cancelled")
    saved_count = Column(Integer, nullable=True, comment="写入条数")
    message = Column(Text, nullable=True, comment="摘要")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")

    __table_args__ = (
        Index("idx_schedule_run_step_run_id", "run_id"),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(ScheduleRunStepEntities)
