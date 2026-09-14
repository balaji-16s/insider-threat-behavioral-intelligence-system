from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import uuid

from app.db.base import get_db
from app.models.employee import Employee
from app.models.activity_log import ActivityLog
from app.models.risk_score import RiskScore
from app.models.alert import Alert
from pydantic import BaseModel, EmailStr

from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut
from app.schemas.risk_score import RiskScoreOut
from app.schemas.alert import AlertOut
from app.core.deps import require_role, require_staff
from app.core.security import hash_password
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/v1/employees", tags=["Employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    query = db.query(Employee)
    if department:
        query = query.filter(Employee.department == department)
    if search:
        query = query.filter(
            Employee.full_name.ilike(f"%{search}%")
            | Employee.employee_code.ilike(f"%{search}%")
        )
    return query.offset(skip).limit(limit).all()


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_in: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager")),
):
    existing = db.query(Employee).filter(Employee.employee_code == employee_in.employee_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee code already exists")
    employee = Employee(**employee_in.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: uuid.UUID,
    employee_in: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager")),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    for field, value in employee_in.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator")),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(employee)
    db.commit()


@router.get("/{employee_id}/activity-logs")
def get_employee_activity_logs(
    employee_id: uuid.UUID,
    activity_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    query = db.query(ActivityLog).filter(ActivityLog.employee_id == employee_id)
    if activity_type:
        query = query.filter(ActivityLog.activity_type == activity_type)
    return query.order_by(ActivityLog.occurred_at.desc()).offset(skip).limit(limit).all()


@router.get("/{employee_id}/risk-scores", response_model=list[RiskScoreOut])
def get_employee_risk_scores(
    employee_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return (
        db.query(RiskScore)
        .filter(RiskScore.employee_id == employee_id)
        .order_by(RiskScore.calculated_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{employee_id}/alerts", response_model=list[AlertOut])
def get_employee_alerts(
    employee_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return (
        db.query(Alert)
        .filter(Alert.employee_id == employee_id)
        .order_by(Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


class LinkWorkerAccountRequest(BaseModel):
    """Link (or create) the portal login for an employee."""

    email: EmailStr
    full_name: Optional[str] = None
    # Required only when create_if_missing is set and no account exists yet.
    password: Optional[str] = None
    create_if_missing: bool = False


@router.get("/{employee_id}/account")
def get_employee_account(
    employee_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager")),
):
    """The portal login currently linked to this employee, if any."""
    user = db.query(User).filter(User.employee_id == employee_id).first()
    if not user:
        return {"linked": False, "account": None}
    return {
        "linked": True,
        "account": {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
        },
    }


@router.post("/{employee_id}/link-account")
def link_worker_account(
    employee_id: uuid.UUID,
    payload: LinkWorkerAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager")),
):
    """Give an employee a portal login, so they can see their own risk.

    Links an existing account by email, or creates one with the
    ``employee`` role when ``create_if_missing`` is set. Refuses to move
    an account that is already attached to a different employee, which
    would otherwise silently re-point someone's access.
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if user is None:
        if not payload.create_if_missing:
            raise HTTPException(
                status_code=404,
                detail="No account with that email. Set create_if_missing "
                "and provide a password to create the portal login.",
            )
        if not payload.password or len(payload.password) < 8:
            raise HTTPException(
                status_code=400,
                detail="A password of at least 8 characters is required to "
                "create a portal login.",
            )
        user = User(
            full_name=payload.full_name or employee.full_name,
            email=email,
            hashed_password=hash_password(payload.password),
            role=UserRole.EMPLOYEE,
        )
        db.add(user)
    elif user.employee_id is not None and str(user.employee_id) != str(employee_id):
        raise HTTPException(
            status_code=409,
            detail="That account is already linked to a different employee. "
            "Unlink it first.",
        )

    user.employee_id = employee.id
    db.commit()
    db.refresh(user)

    return {
        "linked": True,
        "account": {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
        },
        "employee": {
            "id": str(employee.id),
            "full_name": employee.full_name,
            "employee_code": employee.employee_code,
        },
    }


@router.delete("/{employee_id}/link-account", status_code=status.HTTP_204_NO_CONTENT)
def unlink_worker_account(
    employee_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator")),
):
    """Remove the portal login link without deleting the account."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    user = db.query(User).filter(User.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account linked")
    user.employee_id = None
    db.commit()


@router.get("/stats/summary")
def get_employee_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    total = db.query(func.count(Employee.id)).scalar()
    dept_distribution = (
        db.query(Employee.department, func.count(Employee.id))
        .group_by(Employee.department)
        .all()
    )
    return {
        "total_employees": total,
        "department_distribution": {dept: count for dept, count in dept_distribution if dept},
    }
