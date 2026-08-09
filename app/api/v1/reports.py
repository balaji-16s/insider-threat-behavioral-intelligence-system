from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User

from app.schemas.anomaly import AnomalyReport, EmployeeReport
from app.services.report_service import (
    generate_anomaly_report,
    generate_employee_report,
)
from app.services.report_export import (
    anomaly_filename,
    anomaly_report_pdf_bytes,
    anomaly_report_xlsx_bytes,
    employee_filename,
    employee_report_pdf_bytes,
    employee_report_xlsx_bytes,
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


# ── Export endpoints (PDF / Excel) ──────────────────────────────


@router.get("/anomaly/pdf")
def export_anomaly_pdf(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the organization anomaly report as a PDF."""
    pdf = anomaly_report_pdf_bytes(db, days)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{anomaly_filename("pdf", days)}"'},
    )


@router.get("/anomaly/xlsx")
def export_anomaly_xlsx(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the organization anomaly report as an Excel workbook."""
    xlsx = anomaly_report_xlsx_bytes(db, days)
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{anomaly_filename("xlsx", days)}"'},
    )


@router.get("/employee/{employee_id}/pdf")
def export_employee_pdf(
    employee_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a single-employee report as a PDF."""
    try:
        pdf = employee_report_pdf_bytes(db, employee_id, days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{employee_filename("pdf")}"'},
    )


@router.get("/employee/{employee_id}/xlsx")
def export_employee_xlsx(
    employee_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a single-employee report as an Excel workbook."""
    try:
        xlsx = employee_report_xlsx_bytes(db, employee_id, days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{employee_filename("xlsx")}"'},
    )
