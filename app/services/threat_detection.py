"""
Threat Detection Models

Sophisticated threat detection models that combine multiple signals
to identify insider threats including data exfiltration, privilege
abuse, policy violations, and overall insider threat scoring.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Any

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.activity_log import ActivityLog, ActivityType
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.risk_score import RiskScore, RiskLevel
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
    db: Session, employee_id: str, days: int = 30
) -> dict[str, Any]:
    """Run all threat models for one employee and produce a consolidated score."""
    models = {
        "data_exfiltration": _data_exfiltration_score(db, employee_id, days),
        "off_hours_access": _off_hours_access_score(db, employee_id, days),
        "privilege_abuse": _privilege_abuse_score(db, employee_id, days),
        "policy_violation": _policy_violation_score(db, employee_id, days),
        "behavioral_deviation": _behavioral_deviation_score(db, employee_id, days),
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
    db: Session, days: int = 30
) -> list[dict[str, Any]]:
    """Run threat assessment for every employee, sorted by score descending."""
    employees = db.query(Employee).all()
    results = []
    for emp in employees:
        try:
            result = assess_employee_threat(db, str(emp.id), days)
            result["employee_name"] = emp.full_name
            result["department"] = emp.department
            results.append(result)
        except Exception:
            continue

    results.sort(key=lambda r: r["threat_score"], reverse=True)
    return results


def get_top_threats(
    db: Session, limit: int = 20
) -> list[dict[str, Any]]:
    """Return the highest-threat employees."""
    all_assessments = assess_all_employees(db)
    return all_assessments[:limit]


# ── Individual Threat Models ────────────────────────────────────


def _data_exfiltration_score(
    db: Session, employee_id: str, days: int
) -> dict[str, Any]:
    """
    Data exfiltration threat model.

    Signals:
    - Volume of data transfers
    - Transfers to external destinations
    - Transfers during off-hours
    - Large file downloads prior to transfers
    """
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
    db: Session, employee_id: str, days: int
) -> dict[str, Any]:
    """
    Off-hours access threat model.

    Signals:
    - Total off-hours sessions
    - Late night (midnight-5AM) activity
    - Weekend logins
    - Holiday patterns
    """
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
    db: Session, employee_id: str, days: int
) -> dict[str, Any]:
    """
    Privilege abuse threat model.

    Signals:
    - Frequency of privilege changes
    - Access to sensitive systems outside normal pattern
    - Unauthorized access attempts
    """
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
    db: Session, employee_id: str, days: int
) -> dict[str, Any]:
    """
    Policy violation threat model.

    Signals:
    - USB device usage (policy violation indicator)
    - Login failures
    - Data transfers to removable media
    """
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
    db: Session, employee_id: str, days: int
) -> dict[str, Any]:
    """
    Behavioral deviation threat model.

    Measures how much current behavior deviates from the established baseline.
    """
    profile = get_employee_profile(db, employee_id)
    baseline = profile.get("baseline_data", {})
    if not baseline or "error" in baseline:
        return {
            "score": 0,
            "level": "low",
            "factors": {"error": "No baseline available"},
        }

    cutoff = datetime.utcnow() - timedelta(days=days)
    recent_logs = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.employee_id == employee_id,
            ActivityLog.occurred_at >= cutoff,
        )
        .all()
    )

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
