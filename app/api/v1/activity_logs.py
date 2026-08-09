from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime

from app.db.base import get_db
from app.models.activity_log import ActivityLog
from app.models.employee import Employee
from app.schemas.activity_log import ActivityLogCreate, ActivityLogOut, ActivityLogBulkCreate
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/activity-logs", tags=["Activity Logs"])


@router.get("", response_model=list[ActivityLogOut])
def list_activity_logs(
    employee_id: Optional[uuid.UUID] = Query(None),
    activity_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ActivityLog)
    if employee_id:
        query = query.filter(ActivityLog.employee_id == employee_id)
    if activity_type:
        query = query.filter(ActivityLog.activity_type == activity_type)
    if source:
        query = query.filter(ActivityLog.source == source)
    if from_date:
        query = query.filter(ActivityLog.occurred_at >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.filter(ActivityLog.occurred_at <= datetime.fromisoformat(to_date))
    return query.order_by(ActivityLog.occurred_at.desc()).offset(skip).limit(limit).all()


@router.get("/{log_id}", response_model=ActivityLogOut)
def get_activity_log(
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = db.query(ActivityLog).filter(ActivityLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Activity log not found")
    return log


@router.post("", response_model=ActivityLogOut, status_code=status.HTTP_201_CREATED)
def create_activity_log(
    log_in: ActivityLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = db.query(Employee).filter(Employee.id == log_in.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    log = ActivityLog(
        employee_id=log_in.employee_id,
        activity_type=log_in.activity_type,
        source=log_in.source,
        details=log_in.details,
        occurred_at=log_in.occurred_at or datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def bulk_create_activity_logs(
    bulk_in: ActivityLogBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = []
    for log_in in bulk_in.logs:
        log = ActivityLog(
            employee_id=log_in.employee_id,
            activity_type=log_in.activity_type,
            source=log_in.source,
            details=log_in.details,
            occurred_at=log_in.occurred_at or datetime.utcnow(),
        )
        db.add(log)
        logs.append(log)
    db.commit()
    for log in logs:
        db.refresh(log)
    return {"ingested": len(logs), "logs": logs}
