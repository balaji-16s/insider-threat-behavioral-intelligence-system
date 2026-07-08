import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class ActivityType(str, enum.Enum):
    LOGIN = "login"
    FILE_DOWNLOAD = "file_download"
    FILE_UPLOAD = "file_upload"
    DATA_TRANSFER = "data_transfer"
    EMAIL = "email"
    PRIVILEGE_CHANGE = "privilege_change"
    REMOTE_ACCESS = "remote_access"
    USB_DEVICE = "usb_device"

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True)
    activity_type = Column(Enum(ActivityType), nullable=False)
    source = Column(String(100))
    details = Column(JSON, default=dict)
    occurred_at = Column(DateTime, nullable=False, index=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)
