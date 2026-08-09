from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.base import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User

from app.schemas.ueba import (
    UebaPipelineResult,
    UebaOverview,
    UebaEmployeeOverview,
)
from app.services.ueba import (
    run_ueba_pipeline,
    get_ueba_overview,
    get_employee_ueba,
)

router = APIRouter(prefix="/api/v1/ueba", tags=["UEBA Intelligence"])


@router.post("/pipeline", response_model=UebaPipelineResult)
def run_pipeline(
    days: int = Query(30, ge=1, le=365),
    employee_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager", "soc_engineer")),
):
    """
    Run the complete UEBA intelligence pipeline:

    baselines → anomaly detection → threat assessment → risk persistence
    """
    result = run_ueba_pipeline(db, days=days, employee_id=employee_id)
    return UebaPipelineResult(**result)


@router.get("/overview", response_model=UebaOverview)
def ueba_overview(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consolidated UEBA view for every employee."""
    return get_ueba_overview(db, days=days, limit=limit)


@router.get("/overview/{employee_id}", response_model=UebaEmployeeOverview)
def employee_ueba(
    employee_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consolidated UEBA view for a single employee."""
    try:
        return get_employee_ueba(db, employee_id, days=days)
    except ValueError:
        raise HTTPException(status_code=404, detail="Employee not found")
