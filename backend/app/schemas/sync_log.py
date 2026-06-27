from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SyncTaskLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_name: str
    source: str
    biz_date: date | None
    status: str
    start_time: datetime
    end_time: datetime | None
    total_count: int
    success_count: int
    fail_count: int
    progress_total: int
    progress_done: int
    progress_message: str | None
    error_message: str | None
    created_at: datetime
