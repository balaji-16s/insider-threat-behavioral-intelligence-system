import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    CLOSED = "closed"

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN)
    related_alert_ids = Column(JSON, default=list)
    timeline = Column(JSON, default=list)
    assigned_analyst_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

