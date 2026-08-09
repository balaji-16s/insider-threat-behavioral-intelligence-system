import uuid
from datetime import datetime
from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    employee_code: str
    full_name: str
    department: str | None = None
    designation: str | None = None
    manager_name: str | None = None
    device_info: dict = {}
    access_privileges: list = []


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    designation: str | None = None
    manager_name: str | None = None
    device_info: dict | None = None
    access_privileges: list | None = None


class EmployeeOut(BaseModel):
    id: uuid.UUID
    employee_code: str
    full_name: str
    department: str | None
    designation: str | None
    manager_name: str | None
    device_info: dict
    access_privileges: list
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
