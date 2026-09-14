from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.db.base import get_db
from app.models.risk_score import RiskScore
from app.models.employee import Employee
from app.schemas.risk_score import (
    RiskScoreOut,
    RiskScoreCalculateResult,
    RiskAnalytics,
)
from app.services.risk_scoring import (
    calculate_risk_scores,
    get_risk_analytics,
)
from app.core.deps import require_role, require_staff
from app.models.user import User

router = APIRouter(prefix="/api/v1/risk-scores", tags=["Risk Scores"])


@router.get("", response_model=list[RiskScoreOut])
def list_risk_scores(
    employee_id: Optional[uuid.UUID] = Query(None),
    risk_level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    subquery = (
        db.query(
            RiskScore.employee_id,
            RiskScore.id,
            RiskScore.score,
            RiskScore.risk_level,
            RiskScore.breakdown,
            RiskScore.calculated_at,
        )
        .distinct(RiskScore.employee_id)
        .order_by(RiskScore.employee_id, RiskScore.calculated_at.desc())
    ).subquery()

    query = db.query(subquery)
    if employee_id:
        query = query.filter(subquery.c.employee_id == employee_id)
    if risk_level:
        query = query.filter(subquery.c.risk_level == risk_level)
    return query.limit(limit).all()


@router.get("/history/{employee_id}", response_model=list[RiskScoreOut])
def get_risk_score_history(
    employee_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
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


@router.get("/distribution")
def get_risk_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    from sqlalchemy import func

    subquery = (
        db.query(
            RiskScore.employee_id,
            RiskScore.risk_level,
        )
        .distinct(RiskScore.employee_id)
        .order_by(RiskScore.employee_id, RiskScore.calculated_at.desc())
    ).subquery()

    distribution = (
        db.query(subquery.c.risk_level, func.count())
        .group_by(subquery.c.risk_level)
        .all()
    )
    return {level: count for level, count in distribution}


@router.post("/calculate", response_model=RiskScoreCalculateResult)
def recalculate_risk_scores(
    days: int = Query(30, ge=1, le=365),
    employee_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager", "soc_engineer")),
):
    """
    Run the insider risk scoring engine and persist fresh scores.

    Recomputes the weighted threat models for every employee (or a single
    one) and stores the results as new RiskScore records.
    """
    result = calculate_risk_scores(
        db, days=days, employee_id=str(employee_id) if employee_id else None
    )
    return RiskScoreCalculateResult(**result)


@router.get("/analytics", response_model=RiskAnalytics)
def risk_analytics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Organization-wide risk analytics: distribution, trend, and department breakdown."""
    return get_risk_analytics(db, days=days)
