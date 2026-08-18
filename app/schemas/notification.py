import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.models.notification import NotificationType, NotificationChannel, NotificationStatus

class NotificationBase(BaseModel):
    notification_type: NotificationType
    channel: NotificationChannel = NotificationChannel.IN_APP
    recipient: Optional[str] = None
    subject: str
    message: str
    metadata_info: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationOut(NotificationBase):
    id: uuid.UUID
    status: NotificationStatus
    created_at: datetime

    class Config:
        from_attributes = True
