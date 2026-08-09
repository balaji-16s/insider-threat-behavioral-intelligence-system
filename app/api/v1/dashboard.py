from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.base import get_db
from app.models.employee import Employee
from app.models.activity_log import ActivityLog
from app.models.alert import Alert
from app.models.incident import Incident
from app.models.risk_score import RiskScore, RiskLevel
from app.schemas.dashboard import DashboardStats
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_employees = db.query(func.count(Employee.id)).scalar() or 0
    total_alerts = db.query(func.count(Alert.id)).scalar() or 0
    open_alerts = db.query(func.count(Alert.id)).filter(Alert.status == "open").scalar() or 0
    critical_alerts = db.query(func.count(Alert.id)).filter(Alert.severity == "critical").scalar() or 0
    total_incidents = db.query(func.count(Incident.id)).scalar() or 0
    active_incidents = db.query(func.count(Incident.id)).filter(Incident.status.in_(["open", "investigating"])).scalar() or 0
    total_activity_logs = db.query(func.count(ActivityLog.id)).scalar() or 0

    subquery = (
        db.query(
            RiskScore.employee_id,
            RiskScore.risk_level,
        )
        .distinct(RiskScore.employee_id)
        .order_by(RiskScore.employee_id, RiskScore.calculated_at.desc())
    ).subquery()

    high_risk_employees = (
        db.query(func.count())
        .select_from(subquery)
        .filter(subquery.c.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]))
    ).scalar() or 0

    return DashboardStats(
        total_employees=total_employees,
        total_alerts=total_alerts,
        open_alerts=open_alerts,
        critical_alerts=critical_alerts,
        total_incidents=total_incidents,
        active_incidents=active_incidents,
        total_activity_logs=total_activity_logs,
        high_risk_employees=high_risk_employees,
    )


@router.get("/recent-alerts")
def get_recent_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(10)
        .all()
    )


@router.get("/activity-trends")
def get_activity_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import cast, Date

    daily_counts = (
        db.query(
            cast(ActivityLog.occurred_at, Date).label("date"),
            func.count(ActivityLog.id).label("count"),
        )
        .group_by(cast(ActivityLog.occurred_at, Date))
        .order_by(cast(ActivityLog.occurred_at, Date).desc())
        .limit(30)
        .all()
    )
    return [{"date": str(row.date), "count": row.count} for row in daily_counts]
