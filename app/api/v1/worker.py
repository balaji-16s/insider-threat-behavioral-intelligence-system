"""
Worker (Employee) Portal API

Self-service endpoints for ``UserRole.EMPLOYEE`` accounts: a worker can
see exactly what the platform has recorded about *them* — their activity,
their detected threats, and their risk level and score — and nothing
about anyone else.

Authorization model
-------------------
Every endpoint derives the employee from the authenticated token
(``current_user.employee_id`` via ``require_linked_employee``). No
endpoint accepts an employee id from the caller, so an employee account
cannot read another employee's data by editing a URL. These routes are
intentionally separate from the analyst-facing ``/employees/{id}/…``
endpoints, which remain role-restricted to security staff.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import require_linked_employee
from app.db.base import get_db
from app.models.activity_log import ActivityLog, ActivityType
from app.models.alert import Alert, AlertStatus
from app.models.behavioral_baseline import BehavioralBaseline
from app.models.employee import Employee
from app.models.risk_score import RiskScore
from app.models.user import User
from app.services.activity_aggregates import load_employee_activity
from app.services.threat_detection import assess_employee_threat, get_cohort

router = APIRouter(prefix="/api/v1/worker", tags=["Worker Portal"])

# Friendly labels for the eight monitored activity types, so the portal
# can render plain English instead of raw enum values.
ACTIVITY_LABELS: dict[str, str] = {
    "login": "Logins",
    "file_download": "File downloads",
    "file_upload": "File uploads",
    "data_transfer": "Data transfers",
    "email": "Emails",
    "privilege_change": "Privilege changes",
    "remote_access": "Remote access",
    "usb_device": "USB device events",
}


def _linked_employee(db: Session, user: User) -> Employee:
    """Load the employee record backing this portal account."""
    employee = (
        db.query(Employee).filter(Employee.id == user.employee_id).first()
    )
    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Your account is linked to an employee record that no "
            "longer exists. Ask an administrator to re-link it.",
        )
    return employee


def _latest_risk(db: Session, employee_id: Any) -> RiskScore | None:
    return (
        db.query(RiskScore)
        .filter(RiskScore.employee_id == employee_id)
        .order_by(RiskScore.calculated_at.desc())
        .first()
    )


def _risk_percentile(db: Session, score: float) -> dict[str, Any]:
    """Where this score sits among every employee's latest score.

    Computed in SQL over one row per employee, so it stays cheap on the
    full CERT dataset.
    """
    latest = (
        db.query(RiskScore.employee_id, func.max(RiskScore.score))
        .group_by(RiskScore.employee_id)
        .all()
    )
    if not latest:
        return {"percentile": None, "peers_scored": 0}
    scores = [float(s or 0) for _, s in latest]
    below = sum(1 for s in scores if s < score)
    return {
        "percentile": round(below / len(scores) * 100),
        "peers_scored": len(scores),
        "org_average": round(sum(scores) / len(scores), 1),
        "org_max": round(max(scores), 1),
    }


def _department_comparison(
    db: Session, employee: Employee, score: float
) -> dict[str, Any]:
    """Average latest score for the employee's own department."""
    rows = (
        db.query(
            Employee.id,
            func.max(RiskScore.score),
        )
        .join(RiskScore, RiskScore.employee_id == Employee.id)
        .filter(Employee.department == employee.department)
        .group_by(Employee.id)
        .all()
    )
    if not rows:
        return {"department": employee.department, "average": None, "size": 0}
    scores = [float(s or 0) for _, s in rows]
    return {
        "department": employee.department,
        "average": round(sum(scores) / len(scores), 1),
        "size": len(scores),
        "your_rank": sum(1 for s in scores if s > score) + 1,
    }


def _activity_summary(
    db: Session, employee: Employee, days: int
) -> dict[str, Any]:
    """What this worker has actually done over the lookback window.

    Built from SQL-side aggregates rather than loading raw rows, so it
    stays fast even on a multi-million row activity table.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    activity = load_employee_activity(
        db, [employee.id], cutoff, sections={"daily"}
    ).get(str(employee.id))

    if activity is None:
        return {
            "total_events": 0,
            "by_type": [],
            "daily": [],
            "off_hours_events": 0,
            "weekend_events": 0,
            "unique_workstations": 0,
        }

    by_type = [
        {
            "type": key,
            "label": ACTIVITY_LABELS.get(key, key.replace("_", " ").title()),
            "count": count,
        }
        for key, count in activity.type_counts.most_common()
    ]

    daily = [
        {"date": day.isoformat(), "count": count}
        for day, count in sorted(activity.daily_counts.items())
    ]

    return {
        "total_events": activity.total_logs,
        "by_type": by_type,
        "daily": daily,
        "off_hours_events": activity.off_hours,
        "weekend_events": activity.weekend_events,
        "unique_workstations": activity.unique_pcs,
        "active_days": len(activity.daily_counts),
    }


def _open_alerts(db: Session, employee_id: Any, limit: int = 25) -> dict[str, Any]:
    """Threats currently raised against this worker."""
    rows = (
        db.query(Alert)
        .filter(
            Alert.employee_id == employee_id,
            Alert.status == AlertStatus.OPEN,
        )
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "open_count": len(rows),
        "items": [
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "severity": a.severity.value,
                "anomaly_type": a.anomaly_type,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "evidence": a.evidence,
            }
            for a in rows
        ],
    }


def _explain_models(model_scores: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the per-model factors into an ordered 'why' list."""
    reasons: list[dict[str, Any]] = []
    for model_name, model in (model_scores or {}).items():
        for factor_name, factor in (model.get("factors") or {}).items():
            if not isinstance(factor, dict):
                continue
            reasons.append(
                {
                    "model": model_name.replace("_", " ").title(),
                    "factor": factor_name.replace("_", " "),
                    "metric": factor.get("metric"),
                    "score": factor.get("score", 0),
                    "value": factor.get("value"),
                    "peer_median": factor.get("peer_median"),
                    "peer_p95": factor.get("peer_p95"),
                }
            )
    reasons.sort(key=lambda r: r["score"], reverse=True)
    return reasons[:8]


@router.get("/me/overview")
def worker_overview(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_linked_employee),
) -> dict[str, Any]:
    """Complete self-service view for the logged-in worker.

    Answers the three questions the portal is built around: what have I
    done, what threats were detected, and what is my risk level/score.
    """
    employee = _linked_employee(db, current_user)

    latest = _latest_risk(db, employee.id)
    score = round(float(latest.score), 1) if latest else None
    level = latest.risk_level.value if latest else None

    threat = assess_employee_threat(db, str(employee.id), days)
    cohort = get_cohort(db, days)

    history = (
        db.query(RiskScore)
        .filter(RiskScore.employee_id == employee.id)
        .order_by(RiskScore.calculated_at.desc())
        .limit(30)
        .all()
    )

    baseline = (
        db.query(BehavioralBaseline)
        .filter(BehavioralBaseline.employee_id == employee.id)
        .first()
    )

    return {
        "employee": {
            "id": str(employee.id),
            "employee_code": employee.employee_code,
            "full_name": employee.full_name,
            "department": employee.department,
            "designation": employee.designation,
            "manager_name": employee.manager_name,
            "access_privileges": employee.access_privileges or [],
        },
        "risk": {
            "score": score,
            "level": level,
            "calculated_at": (
                latest.calculated_at.isoformat()
                if latest and latest.calculated_at
                else None
            ),
            "comparison": _risk_percentile(db, score) if score is not None else None,
            "department": (
                _department_comparison(db, employee, score)
                if score is not None
                else None
            ),
            "history": [
                {
                    "score": round(float(r.score), 1),
                    "level": r.risk_level.value,
                    "calculated_at": (
                        r.calculated_at.isoformat() if r.calculated_at else None
                    ),
                }
                for r in history
            ],
        },
        "threat": {
            "score": threat["threat_score"],
            "level": threat["threat_level"],
            "model_scores": threat["model_scores"],
            "reasons": _explain_models(threat["model_scores"]),
            "scoring_mode": threat.get("scoring_mode"),
            "cohort_size": cohort.size,
        },
        "alerts": _open_alerts(db, employee.id),
        "activity": _activity_summary(db, employee, days),
        "baseline": {
            "status": "available" if baseline else "missing",
            "daily_avg": (baseline.baseline_data or {}).get("daily_avg")
            if baseline
            else None,
        },
        "lookback_days": days,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/me/activity")
def worker_activity(
    activity_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_linked_employee),
) -> dict[str, Any]:
    """Paginated list of this worker's own recorded activity."""
    query = db.query(ActivityLog).filter(
        ActivityLog.employee_id == current_user.employee_id
    )
    if activity_type:
        query = query.filter(ActivityLog.activity_type == activity_type)

    total = query.count()
    rows = (
        query.order_by(ActivityLog.occurred_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": str(log.id),
                "activity_type": (
                    log.activity_type.value
                    if hasattr(log.activity_type, "value")
                    else str(log.activity_type)
                ),
                "label": ACTIVITY_LABELS.get(
                    log.activity_type.value
                    if hasattr(log.activity_type, "value")
                    else str(log.activity_type),
                    "Activity",
                ),
                "source": log.source,
                "details": log.details,
                "occurred_at": (
                    log.occurred_at.isoformat() if log.occurred_at else None
                ),
            }
            for log in rows
        ],
    }


@router.get("/me/activity-types")
def worker_activity_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_linked_employee),
) -> list[dict[str, str]]:
    """The monitored activity types, for the portal's filter control."""
    return [
        {"type": atype.value, "label": ACTIVITY_LABELS.get(atype.value, atype.value)}
        for atype in ActivityType
    ]
