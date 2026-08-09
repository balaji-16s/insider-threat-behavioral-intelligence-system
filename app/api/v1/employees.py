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
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut
from app.core.deps import get_current_user, require_role
from app.models.user import User

router = APIRouter(prefix="/api/v1/employees", tags=["Employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    query = db.query(ActivityLog).filter(ActivityLog.employee_id == employee_id)
    if activity_type:
        query = query.filter(ActivityLog.activity_type == activity_type)
    return query.order_by(ActivityLog.occurred_at.desc()).offset(skip).limit(limit).all()


@router.get("/{employee_id}/risk-scores", response_model=list)
def get_employee_risk_scores(
    employee_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(RiskScore)
        .filter(RiskScore.employee_id == employee_id)
        .order_by(RiskScore.calculated_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{employee_id}/alerts", response_model=list)
def get_employee_alerts(
    employee_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Alert)
        .filter(Alert.employee_id == employee_id)
        .order_by(Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/stats/summary")
def get_employee_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
