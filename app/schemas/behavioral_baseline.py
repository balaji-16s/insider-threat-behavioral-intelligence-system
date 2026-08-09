import uuid
from datetime import datetime
from pydantic import BaseModel


class BehavioralBaselineOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    baseline_data: dict
    generated_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
