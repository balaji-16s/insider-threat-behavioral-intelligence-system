from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User

from app.schemas.anomaly import AnomalyReport, EmployeeReport
from app.services.report_service import (
    generate_anomaly_report,
    generate_employee_report,
)

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/anomaly", response_model=AnomalyReport)
def get_anomaly_report(
    days: int = Query(30, ge=1, le=365),
    include_threats: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a comprehensive anomaly report for the organization."""
    report = generate_anomaly_report(
        db, days=days, include_threat_assessment=include_threats
    )
    return AnomalyReport(**report)


@router.get("/employee/{employee_id}", response_model=EmployeeReport)
def get_employee_report(
    employee_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a focused anomaly report for a specific employee."""
    report = generate_employee_report(db, employee_id, days)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return EmployeeReport(**report)
