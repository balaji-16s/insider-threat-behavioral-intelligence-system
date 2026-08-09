import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.incident import IncidentStatus


class IncidentCreate(BaseModel):
    employee_id: uuid.UUID
    title: str
    related_alert_ids: list = []
    assigned_analyst_id: uuid.UUID | None = None


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    timeline: list | None = None
    assigned_analyst_id: uuid.UUID | None = None


class TimelineEventIn(BaseModel):
    event: str
    note: str | None = None


class IncidentOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    title: str
    status: IncidentStatus
    related_alert_ids: list
    timeline: list
    assigned_analyst_id: uuid.UUID | None
    created_at: datetime
    closed_at: datetime | None

    class Config:
        from_attributes = True
