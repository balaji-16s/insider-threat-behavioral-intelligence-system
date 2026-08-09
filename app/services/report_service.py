"""
Anomaly Report Service

Generates aggregated anomaly reports combining data from behavioral
profiling, anomaly detection, and threat detection engines.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.employee import Employee
from app.models.activity_log import ActivityLog
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.incident import Incident, IncidentStatus
from app.models.risk_score import RiskScore, RiskLevel
from app.services.threat_detection import assess_all_employees, assess_employee_threat


# ── Public API ──────────────────────────────────────────────────


def generate_anomaly_report(
    db: Session,
    days: int = 30,
    include_threat_assessment: bool = True,
) -> dict[str, Any]:
    """
    Generate a comprehensive anomaly report.

    Combines data from alerts, incidents, activity trends, risk scores,
    and optionally threat assessments.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)

    report: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "report_period_days": days,
        "report_period": {
            "start": cutoff.isoformat(),
            "end": now.isoformat(),
        },
    }

    report["summary"] = _generate_summary(db, cutoff)
    report["alerts"] = _alert_analysis(db, cutoff)
    report["incidents"] = _incident_analysis(db, cutoff)
    report["activity_trends"] = _activity_trend_analysis(db, cutoff)
    report["risk_distribution"] = _risk_distribution(db)
    report["high_risk_employees"] = _high_risk_employees(db, cutoff)

    if include_threat_assessment:
        threat_assessments = assess_all_employees(db, days)
        report["threat_assessment"] = {
            "total_assessed": len(threat_assessments),
            "top_threats": threat_assessments[:10],
            "average_threat_score": round(
                sum(t["threat_score"] for t in threat_assessments)
                / max(len(threat_assessments), 1),
                1,
            ),
        }

    return report


def generate_employee_report(
    db: Session, employee_id: str, days: int = 30
) -> dict[str, Any]:
    """Generate a focused report for a single employee."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)

    employee = (
        db.query(Employee).filter(Employee.id == employee_id).first()
    )
    if not employee:
        return {"error": "Employee not found"}

    alerts = (
        db.query(Alert)
        .filter(
            Alert.employee_id == employee_id,
            Alert.created_at >= cutoff,
        )
        .all()
    )

    recent_logs = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.employee_id == employee_id,
            ActivityLog.occurred_at >= cutoff,
        )
        .count()
    )

    risk_scores = (
        db.query(RiskScore)
        .filter(
            RiskScore.employee_id == employee_id,
            RiskScore.calculated_at >= cutoff,
        )
        .order_by(RiskScore.calculated_at.desc())
        .all()
    )

    latest_risk = risk_scores[0] if risk_scores else None

    # Count alerts by severity
    severity_counts: Counter[str] = Counter()
    for a in alerts:
        severity_counts[a.severity.value] += 1

    alert_types: Counter[str] = Counter()
    for a in alerts:
        if a.anomaly_type:
            alert_types[a.anomaly_type] += 1

    threat = assess_employee_threat(db, employee_id, days)

    return {
        "employee": {
            "id": str(employee.id),
            "name": employee.full_name,
            "department": employee.department,
            "designation": employee.designation,
        },
        "report_period_days": days,
        "generated_at": now.isoformat(),
        "total_alerts": len(alerts),
        "total_activity_logs": recent_logs,
        "alert_severity_breakdown": dict(severity_counts),
        "alert_type_breakdown": dict(alert_types),
        "latest_risk_score": {
            "score": latest_risk.score if latest_risk else None,
            "level": latest_risk.risk_level.value if latest_risk else None,
            "calculated_at": latest_risk.calculated_at.isoformat() if latest_risk else None,
        }
        if latest_risk
        else None,
        "threat_assessment": threat,
    }


# ── Internal Report Components ──────────────────────────────────


def _generate_summary(
    db: Session, cutoff: datetime
) -> dict[str, Any]:
    """Top-level summary statistics for the report."""
    total_employees = db.query(func.count(Employee.id)).scalar() or 0
    total_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.created_at >= cutoff)
        .scalar()
        or 0
    )
    open_alerts = (
        db.query(func.count(Alert.id))
        .filter(
            Alert.created_at >= cutoff,
            Alert.status == AlertStatus.OPEN,
        )
        .scalar()
        or 0
    )
    critical_alerts = (
        db.query(func.count(Alert.id))
        .filter(
            Alert.created_at >= cutoff,
            Alert.severity == AlertSeverity.CRITICAL,
        )
        .scalar()
        or 0
    )
    total_incidents = (
        db.query(func.count(Incident.id))
        .filter(Incident.created_at >= cutoff)
        .scalar()
        or 0
    )
    total_activity = (
        db.query(func.count(ActivityLog.id))
        .filter(ActivityLog.occurred_at >= cutoff)
        .scalar()
        or 0
    )

    return {
        "total_employees": total_employees,
        "total_alerts": total_alerts,
        "open_alerts": open_alerts,
        "critical_alerts": critical_alerts,
        "total_incidents": total_incidents,
        "total_activity_logs": total_activity,
    }


def _alert_analysis(
    db: Session, cutoff: datetime
) -> dict[str, Any]:
    """Deep analysis of alert data."""
    alerts = (
        db.query(Alert).filter(Alert.created_at >= cutoff).all()
    )

    severity_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()

    for a in alerts:
        severity_counts[a.severity.value] += 1
        status_counts[a.status.value] += 1
        if a.anomaly_type:
            type_counts[a.anomaly_type] += 1

    return {
        "total": len(alerts),
        "by_severity": dict(severity_counts),
        "by_status": dict(status_counts),
        "by_anomaly_type": dict(type_counts.most_common(10)),
        "trend": "increasing"
        if len(alerts) > 10
        else "stable",
    }


def _incident_analysis(
    db: Session, cutoff: datetime
) -> dict[str, Any]:
    """Analysis of incident data over the report period."""
    incidents = (
        db.query(Incident)
        .filter(Incident.created_at >= cutoff)
        .all()
    )

    status_counts: Counter[str] = Counter()
    for inc in incidents:
        status_counts[inc.status.value] += 1

    avg_resolution_hours = None
    closed = [
        inc
        for inc in incidents
        if inc.status == IncidentStatus.CLOSED
        and inc.closed_at is not None
    ]
    if closed:
        hours = [
            (inc.closed_at - inc.created_at).total_seconds() / 3600
            for inc in closed
        ]
        avg_resolution_hours = round(mean(hours), 1) if hours else None

    return {
        "total": len(incidents),
        "by_status": dict(status_counts),
        "avg_resolution_hours": avg_resolution_hours,
        "escalation_rate": round(
            status_counts.get("escalated", 0)
            / max(len(incidents), 1)
            * 100,
            1,
        ),
    }


def _activity_trend_analysis(
    db: Session, cutoff: datetime
) -> dict[str, Any]:
    """Activity type trends for the report period."""
    from sqlalchemy import cast, Date

    daily = (
        db.query(
            cast(ActivityLog.occurred_at, Date).label("date"),
            func.count(ActivityLog.id).label("count"),
        )
        .filter(ActivityLog.occurred_at >= cutoff)
        .group_by(cast(ActivityLog.occurred_at, Date))
        .order_by(cast(ActivityLog.occurred_at, Date))
        .all()
    )

    # Activity type breakdown
    type_counts = (
        db.query(
            ActivityLog.activity_type,
            func.count(ActivityLog.id),
        )
        .filter(ActivityLog.occurred_at >= cutoff)
        .group_by(ActivityLog.activity_type)
        .all()
    )

    return {
        "daily_trends": [
            {"date": str(row.date), "count": row.count}
            for row in daily
        ],
        "by_activity_type": {
            str(tp): count for tp, count in type_counts
        },
        "peak_day": max(daily, key=lambda r: r.count).date.isoformat()
        if daily
        else None,
    }


def _risk_distribution(db: Session) -> dict[str, Any]:
    """Current risk score distribution across all employees."""
    subquery = (
        db.query(
            RiskScore.employee_id,
            RiskScore.risk_level,
        )
        .distinct(RiskScore.employee_id)
        .order_by(
            RiskScore.employee_id, RiskScore.calculated_at.desc()
        )
    ).subquery()

    distribution = (
        db.query(subquery.c.risk_level, func.count())
        .group_by(subquery.c.risk_level)
        .all()
    )

    return {str(level): count for level, count in distribution} or {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }


def _high_risk_employees(
    db: Session, cutoff: datetime
) -> list[dict[str, Any]]:
    """List employees with high or critical risk scores."""
    subquery = (
        db.query(
            RiskScore.employee_id,
            RiskScore.score,
            RiskScore.risk_level,
            RiskScore.breakdown,
            RiskScore.calculated_at,
        )
        .distinct(RiskScore.employee_id)
        .order_by(
            RiskScore.employee_id, RiskScore.calculated_at.desc()
        )
    ).subquery()

    results = (
        db.query(
            Employee.id,
            Employee.full_name,
            Employee.department,
            Employee.designation,
            subquery.c.score,
            subquery.c.risk_level,
            subquery.c.breakdown,
        )
        .join(subquery, Employee.id == subquery.c.employee_id)
        .filter(
            subquery.c.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
        )
        .order_by(subquery.c.score.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "id": str(r.id),
            "name": r.full_name,
            "department": r.department,
            "designation": r.designation,
            "risk_score": round(r.score, 1),
            "risk_level": r.risk_level.value,
            "breakdown": r.breakdown,
        }
        for r in results
    ]
