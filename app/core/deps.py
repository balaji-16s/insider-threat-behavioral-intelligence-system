from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.core.security import decode_access_token
from app.services.auth_service import get_user_by_email
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_exception
    user = get_user_by_email(db, payload["sub"])
    if user is None:
        raise credentials_exception
    return user

def require_role(*allowed_roles):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return role_checker

# Roles allowed to read organization-wide security data. Portal
# ("employee") accounts are deliberately excluded, and the check is an
# allow-list so any role added later is denied by default rather than
# silently gaining access to every employee's telemetry.
STAFF_ROLES = (
    UserRole.ADMINISTRATOR,
    UserRole.SECURITY_MANAGER,
    UserRole.SOC_ENGINEER,
    UserRole.SECURITY_ANALYST,
)

def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Authorise security staff; reject employee portal accounts."""
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security staff access required",
        )
    return current_user

def require_linked_employee(current_user: User = Depends(get_current_user)) -> User:
    """Authorise a portal account and guarantee it maps to an employee.

    Worker endpoints derive the employee from the *token*, never from a
    request parameter, so an employee account cannot request another
    employee's data by changing a URL.
    """
    if current_user.employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not linked to an employee record. "
            "Ask an administrator to link it.",
        )
    return current_user
