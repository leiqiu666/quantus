"""调度任务命令绑定实体"""

from sqlalchemy import Column, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ScheduleJobCommandEntities(Base):
    __tablename__ = "schedule_job_command"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    job_id = Column(Integer, nullable=False, comment="schedule_job.id")
    command_key = Column(String(64), nullable=False, comment="ETL 命令键")
    sort_order = Column(Integer, nullable=False, default=0, comment="串行顺序")

    __table_args__ = (
        Index("idx_schedule_job_command_job_id", "job_id"),
        Index(
            "idx_schedule_job_command_unique",
            "job_id",
            "command_key",
            unique=True,
        ),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(ScheduleJobCommandEntities)
