import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class NotificationType(str, enum.Enum):
    THREAT_ALERT = "threat_alert"
    INVESTIGATION_ESCALATION = "investigation_escalation"
    COMPLIANCE_ALERT = "compliance_alert"
    SECURITY_EVENT = "security_event"

class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"

class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"
    QUEUED = "queued"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_type = Column(Enum(NotificationType), nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP)
    recipient = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=False)
    message = Column(String(2000), nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.SENT)
    metadata_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
