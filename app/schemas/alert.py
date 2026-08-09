import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.alert import AlertSeverity, AlertStatus


class AlertCreate(BaseModel):
    employee_id: uuid.UUID
    title: str
    description: str | None = None
    severity: AlertSeverity
    anomaly_type: str | None = None
    evidence: dict = {}
    assigned_to: uuid.UUID | None = None


class AlertUpdate(BaseModel):
    status: AlertStatus | None = None
    assigned_to: uuid.UUID | None = None


class AlertOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    title: str
    description: str | None
    severity: AlertSeverity
    status: AlertStatus
    anomaly_type: str | None
    evidence: dict
    assigned_to: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
