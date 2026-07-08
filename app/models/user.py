import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class UserRole(str, enum.Enum):
    SECURITY_ANALYST = "security_analyst"
    SOC_ENGINEER = "soc_engineer"
    SECURITY_MANAGER = "security_manager"
    ADMINISTRATOR = "administrator"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.SECURITY_ANALYST)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
