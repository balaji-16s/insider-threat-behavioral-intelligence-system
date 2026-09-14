import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.SECURITY_ANALYST
    # Required when creating a UserRole.EMPLOYEE account, so the portal
    # knows whose behaviour the login is allowed to display.
    employee_id: Optional[uuid.UUID] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: UserRole
    employee_id: Optional[uuid.UUID] = None
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
