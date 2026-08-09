import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.activity_log import ActivityType


class ActivityLogCreate(BaseModel):
    employee_id: uuid.UUID
    activity_type: ActivityType
    source: str | None = None
    details: dict = {}
    occurred_at: datetime | None = None


class ActivityLogOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    activity_type: ActivityType
    source: str | None
    details: dict
    occurred_at: datetime
    ingested_at: datetime

    class Config:
        from_attributes = True


class ActivityLogBulkCreate(BaseModel):
    logs: list[ActivityLogCreate]
