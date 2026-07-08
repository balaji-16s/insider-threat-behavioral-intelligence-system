import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=False)
    breakdown = Column(JSON, default=dict)
    calculated_at = Column(DateTime, default=datetime.utcnow, index=True)

