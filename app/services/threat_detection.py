"""
Threat Detection Models

Sophisticated threat detection models that combine multiple signals
to identify insider threats including data exfiltration, privilege
abuse, policy violations, and overall insider threat scoring.
"""

from __future__ import annotations

import time as _time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.activity_log import ActivityLog, ActivityType
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.risk_score import RiskScore, RiskLevel
from app.models.behavioral_baseline import BehavioralBaseline
from app.services.behavioral_profiling import get_employee_profile


# ── Threat Score Weights ────────────────────────────────────────

WEIGHTS = {
    "data_exfiltration": 0.30,
    "off_hours_access": 0.15,
    "privilege_abuse": 0.20,
    "policy_violation": 0.15,
    "behavioral_deviation": 0.20,
}


# ── Public API ──────────────────────────────────────────────────


def assess_employee_threat(
    db: Session,
    employee_id: str,
    days: int = 30,
    logs: list[ActivityLog] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run all threat models for one employee and produce a consolidated score."""
    # Load the employee's activity once and share it across all models to
    # avoid 5x redundant queries (important when scoring 1000 employees).
    if logs is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.employee_id == employee_id,
                ActivityLog.occurred_at >= cutoff,
            )
            .all()
        )

    models = {
        "data_exfiltration": _data_exfiltration_score(db, employee_id, days, logs=logs),
        "off_hours_access": _off_hours_access_score(db, employee_id, days, logs=logs),
        "privilege_abuse": _privilege_abuse_score(db, employee_id, days, logs=logs),
        "policy_violation": _policy_violation_score(db, employee_id, days, logs=logs),
        "behavioral_deviation": _behavioral_deviation_score(
            db, employee_id, days, logs=logs, baseline=baseline
        ),
    }

    raw_score = sum(
        details["score"] * WEIGHTS[name]
        for name, details in models.items()
    )
    threat_score = min(100.0, max(0.0, raw_score))
    threat_level = _threat_level(threat_score)

    return {
        "employee_id": employee_id,
        "threat_score": round(threat_score, 1),
        "threat_level": threat_level.value,
        "model_scores": models,
        "assessed_at": datetime.utcnow().isoformat(),
        "lookback_days": days,
    }


def assess_all_employees(
    db: Session, days: int = 30, candidate_limit: int | None = None
) -> list[dict[str, Any]]:
    """Run threat assessment for employees, sorted by score descending.

    To stay fast and memory-bounded on large datasets (thousands of
    employees / millions of activity logs):

    - Stored baselines are loaded once with a single query.
    - When ``candidate_limit`` is set (e.g. for "top threats"), a cheap
      SQL aggregate pre-scores every employee and only the top candidates
      receive the full (Python) threat models.
    - Employee activity is loaded in small chunks with ``IN(...)`` queries
      instead of one giant load or one query per employee.
    """
    employees = db.query(Employee).all()
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Batch-load all stored baselines once, grouped by employee.
    baselines_by_employee: dict[str, dict[str, Any]] = {}
    for baseline in db.query(BehavioralBaseline).all():
        baselines_by_employee[str(baseline.employee_id)] = (
            baseline.baseline_data or {}
        )

    if candidate_limit is not None:
        # Cheap SQL pre-score (counts of suspicious activity per employee)
        # to pick which employees deserve the full model run.
        pre_scores = _pre_score_employees(db, cutoff)
        employees = sorted(
            employees,
            key=lambda e: pre_scores.get(str(e.id), 0),
            reverse=True,
        )[:candidate_limit]

    assessments = assess_employees_batch(
        db,
        [str(e.id) for e in employees],
        days,
        baselines_by_employee=baselines_by_employee,
        cutoff=cutoff,
    )

    results = []
    for emp in employees:
        result = assessments.get(str(emp.id))
        if result is None:
            continue
        result["employee_name"] = emp.full_name
        result["department"] = emp.department
        results.append(result)

    results.sort(key=lambda r: r["threat_score"], reverse=True)
    return results


# Short-TTL cache for the top-threats widget. Threat scores only change
# when new activity is ingested, so serving a brief stale snapshot makes
# repeated dashboard/report loads fast instead of re-scoring every time.
_TOP_THREATS_CACHE: dict[str, Any] = {"timestamp": 0.0, "assessments": []}
_TOP_THREATS_TTL_SECONDS = 60.0
_TOP_THREATS_CACHE_SIZE = 60


def get_top_threats(
    db: Session, limit: int = 20
) -> list[dict[str, Any]]:
    """Return the highest-threat employees (fast, bounded memory).

    Reads the latest persisted risk scores — the exact same numbers shown
    on the Risk Scores module — so every view stays consistent, and the
    result is cached briefly (60s). Falls back to a live whole-org
    assessment only when no risk scores have been computed yet.
    """
    now = _time.monotonic()
    if (
        now - _TOP_THREATS_CACHE["timestamp"] < _TOP_THREATS_TTL_SECONDS
        and _TOP_THREATS_CACHE["assessments"]
    ):
        return _TOP_THREATS_CACHE["assessments"][:limit]

    results = _top_risk_threats(
        db, limit=max(_TOP_THREATS_CACHE_SIZE, limit * 3)
    )
    if not results:
        # No persisted scores yet — fall back to a live assessment.
        results = assess_all_employees(
            db, candidate_limit=max(_TOP_THREATS_CACHE_SIZE, limit * 3)
        )
    _TOP_THREATS_CACHE["timestamp"] = now
    _TOP_THREATS_CACHE["assessments"] = results
    return results[:limit]


def _top_risk_threats(
    db: Session, limit: int = 150
) -> list[dict[str, Any]]:
    """Top employees by latest persisted risk score — fast SQL.

    Shapes each entry like an assessment result (``threat_score``,
    ``model_scores`` from the stored breakdown, etc.) so reports and the
    top-threats widget can consume the exact same data as the risk module.
    """
    subquery = (
        db.query(
            RiskScore.employee_id,
            RiskScore.score,
            RiskScore.risk_level,
            RiskScore.breakdown,
            RiskScore.calculated_at,
        )
        .distinct(RiskScore.employee_id)
        .order_by(RiskScore.employee_id, RiskScore.calculated_at.desc())
    ).subquery()

    rows = (
        db.query(
            Employee.id,
            Employee.employee_code,
            Employee.full_name,
            Employee.department,
            Employee.designation,
            subquery.c.score,
            subquery.c.risk_level,
            subquery.c.breakdown,
            subquery.c.calculated_at,
        )
        .join(subquery, Employee.id == subquery.c.employee_id)
        .order_by(subquery.c.score.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "employee_id": str(r.id),
            "employee_code": r.employee_code,
            "employee_name": r.full_name,
            "department": r.department,
            "designation": r.designation,
            "threat_score": round(float(r.score), 1),
            "threat_level": r.risk_level.value,
            "model_scores": (r.breakdown or {}).get("model_scores", {}),
            "assessed_at": (
                r.calculated_at.isoformat() if r.calculated_at else None
            ),
            "lookback_days": 30,
        }
        for r in rows
    ]


def assess_employees_batch(
    db: Session,
    employee_ids: list[str],
    days: int = 30,
    baselines_by_employee: dict[str, dict[str, Any]] | None = None,
    cutoff: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    """Run the full threat assessment for a set of employees efficiently.

    Employee activity is loaded in small chunks with ``IN(...)`` queries
    (memory-bounded) and baselines are looked up from an in-memory map so
    callers never hit the per-employee N+1 query pattern on large datasets.

    Returns ``{employee_id: assessment}``; employees that error out are
    skipped.
    """
    if cutoff is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
    if baselines_by_employee is None:
        baselines_by_employee = {
            str(b.employee_id): (b.baseline_data or {})
            for b in db.query(BehavioralBaseline).all()
        }

    results: dict[str, dict[str, Any]] = {}
    for chunk in _chunks(employee_ids, 20):
        logs_by_employee: dict[str, list[Any]] = defaultdict(list)
        for log in (
            db.query(
                ActivityLog.employee_id,
                ActivityLog.activity_type,
                ActivityLog.occurred_at,
                ActivityLog.details,
            )
            .filter(
                ActivityLog.employee_id.in_(chunk),
                ActivityLog.occurred_at >= cutoff,
            )
            .all()
        ):
            logs_by_employee[str(log.employee_id)].append(log)

        for emp_id in chunk:
            try:
                results[emp_id] = assess_employee_threat(
                    db,
                    emp_id,
                    days,
                    logs=logs_by_employee.get(emp_id, []),
                    baseline=baselines_by_employee.get(emp_id),
                )
            except Exception:
                continue
    return results


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    """Split a list into consecutive chunks of at most ``size`` items."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def _pre_score_employees(
    db: Session, cutoff: datetime
) -> dict[str, int]:
    """Cheap SQL heuristic: count suspicious activity per employee.

    Used only to decide which employees get the full (expensive) threat
    model run, so the dashboard/UEBA ranking stays fast on large datasets.
    """
    from sqlalchemy import or_

    hour_expr = func.extract("hour", ActivityLog.occurred_at)
    suspicious = or_(
        ActivityLog.activity_type == ActivityType.DATA_TRANSFER,
        ActivityLog.activity_type == ActivityType.USB_DEVICE,
        ActivityLog.activity_type == ActivityType.PRIVILEGE_CHANGE,
        ActivityLog.activity_type == ActivityType.REMOTE_ACCESS,
        or_(hour_expr < 7, hour_expr > 19),
    )
    rows = (
        db.query(ActivityLog.employee_id, func.count())
        .filter(ActivityLog.occurred_at >= cutoff, suspicious)
        .group_by(ActivityLog.employee_id)
        .all()
    )
    return {str(emp_id): count for emp_id, count in rows}


# ── Individual Threat Models ────────────────────────────────────


def _data_exfiltration_score(
    db: Session,
    employee_id: str,
    days: int,
    logs: list[ActivityLog] | None = None,
) -> dict[str, Any]:
    """
    Data exfiltration threat model.

    Signals:
    - Volume of data transfers
    - Transfers to external destinations
    - Transfers during off-hours
    - Large file downloads prior to transfers
    """
    if logs is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.employee_id == employee_id,
                ActivityLog.occurred_at >= cutoff,
            )
            .all()
        )

    data_xfers = [
        l for l in logs if l.activity_type == ActivityType.DATA_TRANSFER
    ]
    file_downloads = [
        l for l in logs if l.activity_type == ActivityType.FILE_DOWNLOAD
    ]
    usb_events = [
        l for l in logs if l.activity_type == ActivityType.USB_DEVICE
    ]

    score = 0.0
    factors: dict[str, Any] = {}

    # Factor 1: Data transfer volume
    if data_xfers:
        xfer_score = min(len(data_xfers) * 5, 40)
        score += xfer_score
        factors["data_transfer_volume"] = {
            "score": xfer_score,
            "count": len(data_xfers),
        }

        # Factor 2: Off-hours transfers (double weight)
        off_hours_xfers = [
            l
            for l in data_xfers
            if l.occurred_at.hour < 7 or l.occurred_at.hour > 19
        ]
        if off_hours_xfers:
            oh_score = min(len(off_hours_xfers) * 8, 30)
            score += oh_score
            factors["off_hours_transfers"] = {
                "score": oh_score,
                "count": len(off_hours_xfers),
            }

        # Factor 3: External destination
        external = [
            l
            for l in data_xfers
            if l.details.get("destination") == "external"
        ]
        if external:
            ext_score = min(len(external) * 10, 30)
            score += ext_score
            factors["external_transfers"] = {
                "score": ext_score,
                "count": len(external),
            }

    # Factor 4: Large file downloads
    large_downloads = [
        l
        for l in file_downloads
        if l.details.get("size_kb", 0) > 50000  # > 50 MB
    ]
    if large_downloads:
        dl_score = min(len(large_downloads) * 6, 25)
        score += dl_score
        factors["large_downloads"] = {
            "score": dl_score,
            "count": len(large_downloads),
            "total_mb": round(
                sum(d.details.get("size_kb", 0) / 1024 for d in large_downloads), 1
            ),
        }

    # Factor 5: USB storage device usage
    if usb_events:
        usb_score = min(len(usb_events) * 4, 20)
        score += usb_score
        factors["usb_storage"] = {
            "score": usb_score,
            "count": len(usb_events),
        }

    score = min(score, 100)
    return {
        "score": round(score, 1),
        "level": _sub_level(score),
        "factors": factors,
    }


def _off_hours_access_score(
    db: Session,
    employee_id: str,
    days: int,
    logs: list[ActivityLog] | None = None,
) -> dict[str, Any]:
    """
    Off-hours access threat model.

    Signals:
    - Total off-hours sessions
    - Late night (midnight-5AM) activity
    - Weekend logins
    - Holiday patterns
    """
    if logs is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.employee_id == employee_id,
                ActivityLog.occurred_at >= cutoff,
            )
            .all()
        )

    score = 0.0
    factors: dict[str, Any] = {}

    off_hours = [
        l for l in logs if l.occurred_at.hour < 7 or l.occurred_at.hour > 19
    ]
    late_night = [l for l in logs if l.occurred_at.hour < 5]
    weekend = [l for l in logs if l.occurred_at.weekday() >= 5]

    if off_hours:
        oh_pct = len(off_hours) / max(len(logs), 1) * 100
        oh_score = min(oh_pct * 0.5, 30)
        score += oh_score
        factors["off_hours_ratio"] = {
            "score": round(oh_score, 1),
            "pct": round(oh_pct, 1),
        }

    if late_night:
        ln_score = min(len(late_night) * 3, 30)
        score += ln_score
        factors["late_night_activity"] = {
            "score": ln_score,
            "count": len(late_night),
        }

    if weekend:
        unique_weekend_days = len(
            set(l.occurred_at.strftime("%Y-%m-%d") for l in weekend)
        )
        we_score = min(unique_weekend_days * 5, 25)
        score += we_score
        factors["weekend_access"] = {
            "score": we_score,
            "unique_days": unique_weekend_days,
        }

    score = min(score, 100)
    return {
        "score": round(score, 1),
        "level": _sub_level(score),
        "factors": factors,
    }


def _privilege_abuse_score(
    db: Session,
    employee_id: str,
    days: int,
    logs: list[ActivityLog] | None = None,
) -> dict[str, Any]:
    """
    Privilege abuse threat model.

    Signals:
    - Frequency of privilege changes
    - Access to sensitive systems outside normal pattern
    - Unauthorized access attempts
    """
    if logs is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.employee_id == employee_id,
                ActivityLog.occurred_at >= cutoff,
            )
            .all()
        )

    score = 0.0
    factors: dict[str, Any] = {}

    priv_changes = [
        l for l in logs if l.activity_type == ActivityType.PRIVILEGE_CHANGE
    ]
    remote_access = [
        l for l in logs if l.activity_type == ActivityType.REMOTE_ACCESS
    ]

    if priv_changes:
        pc_score = min(len(priv_changes) * 12, 40)
        score += pc_score
        factors["privilege_changes"] = {
            "score": pc_score,
            "count": len(priv_changes),
        }

    if remote_access:
        # Check for off-hours remote access which is more suspicious
        off_hours_remote = [
            l
            for l in remote_access
            if l.occurred_at.hour < 7 or l.occurred_at.hour > 19
        ]
        ra_score = min(len(off_hours_remote) * 8, 30)
        if len(off_hours_remote) < len(remote_access):
            ra_score += min((len(remote_access) - len(off_hours_remote)) * 3, 15)
        score += ra_score
        factors["remote_access"] = {
            "score": round(ra_score, 1),
            "total": len(remote_access),
            "off_hours": len(off_hours_remote),
        }

    score = min(score, 100)
    return {
        "score": round(score, 1),
        "level": _sub_level(score),
        "factors": factors,
    }


def _policy_violation_score(
    db: Session,
    employee_id: str,
    days: int,
    logs: list[ActivityLog] | None = None,
) -> dict[str, Any]:
    """
    Policy violation threat model.

    Signals:
    - USB device usage (policy violation indicator)
    - Login failures
    - Data transfers to removable media
    """
    if logs is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.employee_id == employee_id,
                ActivityLog.occurred_at >= cutoff,
            )
            .all()
        )

    score = 0.0
    factors: dict[str, Any] = {}

    usb_devices = [
        l for l in logs if l.activity_type == ActivityType.USB_DEVICE
    ]
    login_events = [
        l for l in logs if l.activity_type == ActivityType.LOGIN
    ]
    data_to_usb = [
        l
        for l in logs
        if l.activity_type == ActivityType.DATA_TRANSFER
        and l.details.get("destination") == "usb"
    ]

    if usb_devices:
        usb_score = min(len(usb_devices) * 6, 30)
        score += usb_score
        factors["usb_device_usage"] = {
            "score": usb_score,
            "count": len(usb_devices),
        }

    if data_to_usb:
        dt_score = min(len(data_to_usb) * 10, 30)
        score += dt_score
        factors["data_to_usb"] = {
            "score": dt_score,
            "count": len(data_to_usb),
        }

    score = min(score, 100)
    return {
        "score": round(score, 1),
        "level": _sub_level(score),
        "factors": factors,
    }


def _behavioral_deviation_score(
    db: Session,
    employee_id: str,
    days: int,
    logs: list[ActivityLog] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Behavioral deviation threat model.

    Measures how much current behavior deviates from the established baseline.
    """
    if baseline is None:
        profile = get_employee_profile(db, employee_id)
        baseline = profile.get("baseline_data", {})
    if not baseline or "error" in baseline:
        return {
            "score": 0,
            "level": "low",
            "factors": {"error": "No baseline available"},
        }

    if logs is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_logs = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.employee_id == employee_id,
                ActivityLog.occurred_at >= cutoff,
            )
            .all()
        )
    else:
        recent_logs = logs

    score = 0.0
    factors: dict[str, Any] = {}

    # Compare recent daily average to baseline
    baseline_daily_avg = baseline.get("daily_avg", 0)
    if recent_logs and baseline_daily_avg > 0:
        recent_daily = len(recent_logs) / max(days, 1)
        deviation_pct = (
            abs(recent_daily - baseline_daily_avg)
            / max(baseline_daily_avg, 0.1)
            * 100
        )
        if deviation_pct > 50:
            dev_score = min(deviation_pct * 0.3, 35)
            score += dev_score
            factors["daily_avg_deviation"] = {
                "score": round(dev_score, 1),
                "baseline_avg": baseline_daily_avg,
                "recent_avg": round(recent_daily, 1),
                "deviation_pct": round(deviation_pct, 1),
            }

    # Compare off-hours activity to baseline
    baseline_off_hours = baseline.get("off_hours_pct", 0)
    if recent_logs and baseline_off_hours > 0:
        recent_off = sum(
            1
            for l in recent_logs
            if l.occurred_at.hour < 7 or l.occurred_at.hour > 19
        )
        recent_off_pct = recent_off / max(len(recent_logs), 1) * 100
        if recent_off_pct > baseline_off_hours * 1.5:
            oh_score = min(
                (recent_off_pct - baseline_off_hours) * 0.5, 25
            )
            score += oh_score
            factors["off_hours_deviation"] = {
                "score": round(oh_score, 1),
                "baseline_pct": baseline_off_hours,
                "recent_pct": round(recent_off_pct, 1),
            }

    # Compare data transfer frequency
    baseline_xfers = baseline.get("activity_distribution", {}).get(
        "data_transfer", 0
    )
    if recent_logs and baseline_xfers > 0:
        recent_xfers = len(
            [
                l
                for l in recent_logs
                if l.activity_type == ActivityType.DATA_TRANSFER
            ]
        )
        recent_xfer_rate = recent_xfers / max(days, 1)
        baseline_xfer_rate = baseline_xfers / 30
        if (
            recent_xfer_rate > baseline_xfer_rate * 2
            and recent_xfers >= 2
        ):
            xfer_score = min(
                (recent_xfer_rate / max(baseline_xfer_rate, 0.01)) * 5,
                25,
            )
            score += xfer_score
            factors["data_transfer_deviation"] = {
                "score": round(xfer_score, 1),
                "baseline_rate": round(baseline_xfer_rate, 2),
                "recent_rate": round(recent_xfer_rate, 2),
            }

    score = min(score, 100)
    return {
        "score": round(score, 1),
        "level": _sub_level(score),
        "factors": factors,
    }


# ── Helpers ──────────────────────────────────────────────────────


def _sub_level(score: float) -> str:
    if score >= 70:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 25:
        return "medium"
    return "low"


def _threat_level(score: float):
    if score >= 80:
        return RiskLevel.CRITICAL
    elif score >= 60:
        return RiskLevel.HIGH
    elif score >= 30:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
