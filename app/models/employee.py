import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    department = Column(String(100))
    designation = Column(String(100))
    manager_name = Column(String(150))
    device_info = Column(JSON, default=dict)      # e.g. {"os": "Windows", "hostname": "..."}
    access_privileges = Column(JSON, default=list)  # e.g. ["vpn", "admin_panel"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)