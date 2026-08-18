"""
UEBA Intelligence Workflow

Orchestrates the full User and Entity Behavior Analytics pipeline:

    baselines → anomaly detection → threat assessment → risk persistence

and exposes a consolidated, per-employee UEBA overview so analysts can
see behavior, anomalies, and risk in a single view.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.employee import Employee
from app.models.risk_score import RiskScore
from app.models.alert import Alert, AlertStatus
from app.models.behavioral_baseline import BehavioralBaseline
from app.services.behavioral_profiling import (
    compute_all_baselines,
    store_baseline,
    compute_baseline,
)
from app.services.anomaly_detection import run_anomaly_detection
from app.services.risk_scoring import calculate_risk_scores
from app.services.threat_detection import (
    assess_employee_threat,
    assess_employees_batch,
)


# ── Pipeline ─────────────────────────────────────────────────────


def run_ueba_pipeline(
    db: Session,
    days: int = 30,
    employee_id: str | None = None,
) -> dict[str, Any]:
    """
    Run the complete UEBA intelligence pipeline in order:

    1. Compute (or refresh) behavioral baselines
    2. Run anomaly detection (creates alerts for anomalies)
    3. Assess insider threat scores
    4. Persist risk scores
    """
    if employee_id:
        baseline_data = compute_baseline(db, employee_id)
        baselines_computed = 1 if "error" not in baseline_data else 0
        if baselines_computed:
            store_baseline(db, employee_id, baseline_data)
            db.commit()
    else:
        baselines_computed = compute_all_baselines(db)

    detection = run_anomaly_detection(db, employee_id=employee_id, days=days)
    scoring = calculate_risk_scores(db, days=days, employee_id=employee_id)

    return {
        "baselines_computed": baselines_computed,
        "employees_scanned": detection["scanned_employees"],
        "employees_with_anomalies": detection["employees_with_anomalies"],
        "alerts_created": detection["alerts_created"],
        "risk_scores_calculated": scoring["calculated"],
        "average_threat_score": scoring["average_score"],
        "lookback_days": days,
        "ran_at": datetime.utcnow().isoformat(),
        "message": (
            "UEBA pipeline completed: baselines refreshed, anomalies scanned, "
            f"risk scores recalculated for {scoring['calculated']} employees"
        ),
    }


# ── Overview ─────────────────────────────────────────────────────


def get_ueba_overview(
    db: Session,
    days: int = 30,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Consolidated per-employee UEBA view combining the latest risk score,
    threat assessment, open anomaly alerts, and baseline status.

    Only the top ``limit`` employees by latest risk score receive a threat
    assessment (the rows actually displayed), which keeps this endpoint
    fast and memory-bounded on large datasets instead of running the
    per-employee N+1 assessment pattern over every employee.
    """
    employees = db.query(Employee).all()

    # Latest risk score per employee
    latest_scores = _latest_score_map(db)

    # Open anomaly alert counts per employee
    alert_counts = _open_anomaly_counts(db)

    # Baselines present per employee
    baseline_ids = {
        b.employee_id
        for b in db.query(BehavioralBaseline.employee_id).all()
    }

    # The overview is sorted by risk score and sliced to ``limit``, so only
    # the rows that will actually be shown need a threat assessment.
    employees.sort(
        key=lambda e: (
            latest_scores.get(e.id)["score"]
            if latest_scores.get(e.id)
            else -1.0
        ),
        reverse=True,
    )
    shown = employees[:limit]

    assessments = assess_employees_batch(
        db, [str(e.id) for e in shown], days
    )

    items = []
    for emp in shown:
        threat = assessments.get(str(emp.id))
        latest = latest_scores.get(emp.id)

        items.append(
            {
                "employee_id": str(emp.id),
                "employee_name": emp.full_name,
                "employee_code": emp.employee_code,
                "department": emp.department,
                "designation": emp.designation,
                "risk_score": latest["score"] if latest else None,
                "risk_level": latest["level"] if latest else None,
                "threat_score": threat["threat_score"] if threat else None,
                "threat_level": threat["threat_level"] if threat else None,
                "model_scores": threat["model_scores"] if threat else {},
                "open_anomaly_alerts": alert_counts.get(emp.id, 0),
                "baseline_status": (
                    "available" if emp.id in baseline_ids else "missing"
                ),
                "assessed_at": (
                    latest["calculated_at"] if latest else None
                ),
            }
        )

    return {
        "total_employees": len(employees),
        "lookback_days": days,
        "generated_at": datetime.utcnow().isoformat(),
        "items": items,
    }


def get_employee_ueba(
    db: Session, employee_id: str, days: int = 30
) -> dict[str, Any]:
    """UEBA overview entry for a single employee."""
    employee = (
        db.query(Employee).filter(Employee.id == employee_id).first()
    )
    if not employee:
        raise ValueError("Employee not found")

    latest = _latest_score_map(db).get(employee.id)
    threat = _safe_threat(db, employee_id, days)
    baseline_present = (
        db.query(func.count(BehavioralBaseline.id))
        .filter(BehavioralBaseline.employee_id == employee.id)
        .scalar()
        or 0
    )
    alert_count = _open_anomaly_counts(db).get(employee.id, 0)

    item = {
        "employee_id": str(employee.id),
        "employee_name": employee.full_name,
        "employee_code": employee.employee_code,
        "department": employee.department,
        "designation": employee.designation,
        "risk_score": latest["score"] if latest else None,
        "risk_level": latest["level"] if latest else None,
        "threat_score": threat["threat_score"] if threat else None,
        "threat_level": threat["threat_level"] if threat else None,
        "model_scores": threat["model_scores"] if threat else {},
        "open_anomaly_alerts": alert_count,
        "baseline_status": (
            "available" if baseline_present else "missing"
        ),
        "assessed_at": latest["calculated_at"] if latest else None,
        "generated_at": datetime.utcnow().isoformat(),
        "lookback_days": days,
    }
    return item


def _safe_threat(
    db: Session, employee_id: str, days: int
) -> dict[str, Any] | None:
    try:
        return assess_employee_threat(db, employee_id, days)
    except Exception:
        return None


def _latest_score_map(
    db: Session,
) -> dict[Any, dict[str, Any]]:
    subquery = (
        db.query(
            RiskScore.employee_id,
            RiskScore.score,
            RiskScore.risk_level,
            RiskScore.calculated_at,
        )
        .distinct(RiskScore.employee_id)
        .order_by(RiskScore.employee_id, RiskScore.calculated_at.desc())
    ).subquery()

    rows = (
        db.query(
            subquery.c.employee_id,
            subquery.c.score,
            subquery.c.risk_level,
            subquery.c.calculated_at,
        )
        .all()
    )

    return {
        r.employee_id: {
            "score": round(float(r.score), 1),
            "level": r.risk_level.value,
            "calculated_at": r.calculated_at.isoformat(),
        }
        for r in rows
    }


def _open_anomaly_counts(db: Session) -> dict[Any, int]:
    rows = (
        db.query(Alert.employee_id, func.count(Alert.id))
        .filter(
            Alert.status == AlertStatus.OPEN,
            Alert.anomaly_type.isnot(None),
        )
        .group_by(Alert.employee_id)
        .all()
    )
    return {employee_id: count for employee_id, count in rows}
