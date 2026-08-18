"""
Anomaly Detection Workflow

Implements statistical anomaly detection (Z-score, IQR, percentile),
rule-based detection, multi-factor anomaly scoring, and automated
alert generation.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev, median
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.activity_log import ActivityLog, ActivityType
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.risk_score import RiskScore, RiskLevel
from app.services.behavioral_profiling import compute_baseline
from app.services.notification_service import notify_threat_alert



# ── Result cache ────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DETECTION_CACHE = DATA_DIR / "detection_results.json"


def _cache_detection_result(result: dict[str, Any]) -> None:
    """Persist the last detection run (best-effort) so the UI can restore
    the summary/details after navigating away and back."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DETECTION_CACHE.write_text(
            json.dumps(_sanitize_for_cache(result), indent=2)
        )
    except OSError:
        pass


def _sanitize_for_cache(result: dict[str, Any]) -> dict[str, Any]:
    """Convert enum severity values to plain strings for JSON serialization."""
    for emp in result.get("details", []):
        for anomaly in emp.get("anomalies", []):
            sev = anomaly.get("severity")
            if isinstance(sev, AlertSeverity):
                anomaly["severity"] = sev.value
    return result


def get_cached_detection_results() -> dict[str, Any] | None:
    """Return the most recent anomaly detection run (None if never run)."""
    if not DETECTION_CACHE.exists():
        return None
    try:
        return json.loads(DETECTION_CACHE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def get_anomaly_stats(db: Session) -> dict[str, Any]:
    """Aggregate open anomaly alerts (real totals, not a capped list)."""
    rows = (
        db.query(Alert.severity, func.count(Alert.id))
        .filter(
            Alert.status == AlertStatus.OPEN,
            Alert.anomaly_type.isnot(None),
        )
        .group_by(Alert.severity)
        .all()
    )
    by_severity = {sev.value: count for sev, count in rows}
    return {
        "total_open": sum(by_severity.values()),
        "by_severity": by_severity,
    }


# ── Public API ──────────────────────────────────────────────────


def run_anomaly_detection(
    db: Session,
    employee_id: str | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """
    Run the full anomaly detection pipeline.

    Optionally scope to a single employee; otherwise runs for all.
    Returns a summary of what was detected.

    Activity logs are loaded in small chunks with ``IN(...)`` queries and
    shared across every detection method (statistical, rule-based,
    temporal) instead of firing one query per method per employee, which
    keeps whole-org scans fast and memory-bounded on large datasets.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    if employee_id:
        employees = (
            db.query(Employee).filter(Employee.id == employee_id).all()
        )
    else:
        employees = db.query(Employee).all()

    results: list[dict[str, Any]] = []
    alerts_created = 0

    for chunk in _chunks(employees, 20):
        chunk_ids = [e.id for e in chunk]

        # One query per chunk: all activity for these employees in the window.
        logs_by_employee: dict[str, list[Any]] = defaultdict(list)
        for log in (
            db.query(
                ActivityLog.employee_id,
                ActivityLog.activity_type,
                ActivityLog.occurred_at,
                ActivityLog.details,
            )
            .filter(
                ActivityLog.employee_id.in_(chunk_ids),
                ActivityLog.occurred_at >= cutoff,
            )
            .all()
        ):
            logs_by_employee[str(log.employee_id)].append(log)

        # One query per chunk: existing open anomaly alerts for dedup.
        existing_by_employee: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for emp_id, atype, title in (
            db.query(Alert.employee_id, Alert.anomaly_type, Alert.title)
            .filter(
                Alert.employee_id.in_(chunk_ids),
                Alert.status == AlertStatus.OPEN,
                Alert.anomaly_type.isnot(None),
            )
            .all()
        ):
            if atype:
                existing_by_employee[str(emp_id)].add((atype, title))

        for emp in chunk:
            anomalies = _detect_anomalies(
                logs_by_employee.get(str(emp.id), []), days
            )
            if anomalies:
                results.append(
                    {
                        "employee_id": str(emp.id),
                        "employee_name": emp.full_name,
                        "anomalies": anomalies,
                    }
                )
                # Generate alerts for high-confidence anomalies
                alerts_created += _generate_alerts(
                    db,
                    emp,
                    anomalies,
                    existing_by_employee.get(str(emp.id), set()),
                )

    result = {
        "scanned_employees": len(employees),
        "employees_with_anomalies": len(results),
        "alerts_created": alerts_created,
        "details": results,
        "generated_at": datetime.utcnow().isoformat(),
    }
    _cache_detection_result(result)
    return result


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    """Split a list into consecutive chunks of at most ``size`` items."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def get_anomaly_summary(
    db: Session, employee_id: str | None = None
) -> list[dict[str, Any]]:
    """Return a summary of recent open anomalies (alerts with anomaly_type)."""
    query = db.query(Alert).filter(
        Alert.status == AlertStatus.OPEN,
        Alert.anomaly_type.isnot(None),
    )
    if employee_id:
        query = query.filter(Alert.employee_id == employee_id)

    return [
        {
            "id": str(a.id),
            "employee_id": str(a.employee_id),
            "title": a.title,
            "anomaly_type": a.anomaly_type,
            "severity": a.severity.value,
            "created_at": a.created_at.isoformat(),
            "evidence": a.evidence,
        }
        for a in query.order_by(Alert.created_at.desc()).limit(100).all()
    ]


# ── Detection Pipeline ──────────────────────────────────────────


def _detect_anomalies(
    logs: list[Any], lookback_days: int
) -> list[dict[str, Any]]:
    """Run all detection methods and return a consolidated list."""
    anomalies: list[dict[str, Any]] = []

    anomalies.extend(_statistical_anomalies(logs, lookback_days))
    anomalies.extend(_rule_based_anomalies(logs, lookback_days))
    anomalies.extend(_temporal_anomalies(logs, lookback_days))

    return anomalies


def _statistical_anomalies(
    logs: list[Any], days: int
) -> list[dict[str, Any]]:
    """Z-score and IQR based anomaly detection on activity volumes."""
    if len(logs) < 10:
        return []

    found: list[dict[str, Any]] = []

    # ── Daily volume anomaly (Z-score) ──────────────────────
    daily = Counter(
        log.occurred_at.strftime("%Y-%m-%d") for log in logs
    )
    counts = list(daily.values())
    if len(counts) >= 5:
        m = mean(counts)
        s = stdev(counts) if len(counts) > 1 else 1

        for day, count in sorted(daily.items()):
            z = (count - m) / max(s, 0.01)
            if z > 2.5:
                found.append(
                    {
                        "type": "volume_anomaly",
                        "description": f"Unusually high activity on {day}: {count} events (Z={z:.2f})",
                        "confidence": min(1.0, (z - 2.5) / 3.0),
                        "severity": _z_to_severity(z),
                        "evidence": {
                            "date": day,
                            "event_count": count,
                            "z_score": round(z, 2),
                            "mean": round(m, 1),
                            "std": round(s, 1),
                        },
                    }
                )

    # ── Hourly distribution anomaly (IQR) ────────────────────
    hourly = Counter(log.occurred_at.hour for log in logs)
    hours = list(hourly.values())
    if len(hours) >= 4:
        q1 = sorted(hours)[len(hours) // 4]
        q3 = sorted(hours)[(3 * len(hours)) // 4]
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr

        for hour, count in hourly.items():
            if count > upper_bound and iqr > 0:
                found.append(
                    {
                        "type": "hourly_spike",
                        "description": f"Activity spike at hour {hour}: {count} events (threshold={upper_bound:.0f})",
                        "confidence": min(
                            1.0, (count - upper_bound) / (count + 1)
                        ),
                        "severity": AlertSeverity.MEDIUM,
                        "evidence": {
                            "hour": hour,
                            "event_count": count,
                            "iqr_upper_bound": round(upper_bound, 1),
                        },
                    }
                )

    return found


def _rule_based_anomalies(
    logs: list[Any], days: int
) -> list[dict[str, Any]]:
    """Domain rule-based anomaly detection."""
    if not logs:
        return []

    found: list[dict[str, Any]] = []

    # ── Rule: Off-hours data transfer ────────────────────────
    data_xfers = [
        log
        for log in logs
        if log.activity_type == ActivityType.DATA_TRANSFER
        and (log.occurred_at.hour < 7 or log.occurred_at.hour > 19)
    ]
    if len(data_xfers) >= 3:
        found.append(
            {
                "type": "off_hours_data_transfer",
                "description": f"{len(data_xfers)} data transfers during off-hours in the last {days} days",
                "confidence": min(1.0, len(data_xfers) / 10),
                "severity": AlertSeverity.HIGH,
                "evidence": {
                    "count": len(data_xfers),
                    "dates": [
                        d.occurred_at.isoformat() for d in data_xfers[:5]
                    ],
                },
            }
        )

    # ── Rule: USB device usage spike ─────────────────────────
    usb_events = [
        log
        for log in logs
        if log.activity_type == ActivityType.USB_DEVICE
    ]
    if len(usb_events) >= 5:
        found.append(
            {
                "type": "usb_device_spike",
                "description": f"{len(usb_events)} USB device events detected",
                "confidence": min(1.0, len(usb_events) / 15),
                "severity": AlertSeverity.MEDIUM,
                "evidence": {
                    "count": len(usb_events),
                    "devices": list(
                        set(
                            str(log.details.get("device", "unknown"))
                            for log in usb_events
                        )
                    ),
                },
            }
        )

    # ── Rule: Privilege changes ──────────────────────────────
    priv_changes = [
        log
        for log in logs
        if log.activity_type == ActivityType.PRIVILEGE_CHANGE
    ]
    if len(priv_changes) >= 2:
        found.append(
            {
                "type": "privilege_escalation",
                "description": f"{len(priv_changes)} privilege changes detected",
                "confidence": min(1.0, len(priv_changes) / 5),
                "severity": AlertSeverity.HIGH,
                "evidence": {"count": len(priv_changes)},
            }
        )

    # ── Rule: Large file downloads ───────────────────────────
    large_downloads = [
        log
        for log in logs
        if log.activity_type == ActivityType.FILE_DOWNLOAD
        and log.details.get("size_kb", 0) > 10000  # > 10 MB
    ]
    if len(large_downloads) >= 2:
        found.append(
            {
                "type": "large_file_downloads",
                "description": f"{len(large_downloads)} large file downloads (>10MB)",
                "confidence": min(1.0, len(large_downloads) / 8),
                "severity": AlertSeverity.MEDIUM,
                "evidence": {
                    "count": len(large_downloads),
                    "total_size_mb": round(
                        sum(
                            d.details.get("size_kb", 0) / 1024
                            for d in large_downloads
                        ),
                        1,
                    ),
                },
            }
        )

    return found


def _temporal_anomalies(
    logs: list[Any], days: int
) -> list[dict[str, Any]]:
    """Time-pattern based anomalies (weekends, late night, irregular)."""
    if not logs:
        return []

    found: list[dict[str, Any]] = []

    # ── Late-night activity (midnight - 5AM) ─────────────────
    late_night = [
        log for log in logs if log.occurred_at.hour < 5
    ]
    if len(late_night) >= 5:
        found.append(
            {
                "type": "late_night_activity",
                "description": f"{len(late_night)} late-night activities (midnight-5AM)",
                "confidence": min(1.0, len(late_night) / 20),
                "severity": AlertSeverity.LOW,
                "evidence": {
                    "count": len(late_night),
                    "pct": round(
                        len(late_night) / max(len(logs), 1) * 100, 1
                    ),
                },
            }
        )

    # ── Weekend activity concentration ───────────────────────
    weekend_logs = [
        log for log in logs if log.occurred_at.weekday() >= 5
    ]
    weekend_unique_days = len(
        set(log.occurred_at.strftime("%Y-%m-%d") for log in weekend_logs)
    )
    if weekend_unique_days >= 4:
        found.append(
            {
                "type": "concentrated_weekend_access",
                "description": f"Accessed systems on {weekend_unique_days} different weekend days",
                "confidence": min(1.0, weekend_unique_days / 12),
                "severity": AlertSeverity.LOW,
                "evidence": {
                    "weekend_days": weekend_unique_days,
                    "total_weekend_events": len(weekend_logs),
                },
            }
        )

    return found


# ── Alert Generation ────────────────────────────────────────────


def _generate_alerts(
    db: Session,
    employee: Employee,
    anomalies: list[dict[str, Any]],
    existing: set[tuple[str, str]] | None = None,
) -> int:
    """
    Convert anomaly detections into database alerts.

    Deduplicates by checking for existing OPEN alerts with the same
    anomaly_type + title for the same employee. This prevents the
    pipeline from creating hundreds of duplicate alerts on re-runs.

    ``existing`` may be passed in (preloaded in bulk by the caller) to
    avoid a per-employee query; when omitted it is fetched here.
    """
    count = 0

    if existing is None:
        # Fetch existing open alerts for this employee — build a set of
        # (anomaly_type, title) pairs so we can deduplicate.
        existing_rows = (
            db.query(Alert.anomaly_type, Alert.title)
            .filter(
                Alert.employee_id == employee.id,
                Alert.status == AlertStatus.OPEN,
                Alert.anomaly_type.isnot(None),
            )
            .all()
        )
        existing = {
            (row[0], row[1]) for row in existing_rows if row[0]
        }

    for anomaly in anomalies:
        anomaly_type = anomaly.get("type", "")
        title = _anomaly_title(anomaly_type, anomaly.get("description", ""))

        # Skip if we already have this exact anomaly_type + title
        if (anomaly_type, title) in existing:
            continue

        severity = anomaly.get("severity", AlertSeverity.INFORMATIONAL)
        if isinstance(severity, str):
            try:
                severity = AlertSeverity(severity)
            except ValueError:
                severity = AlertSeverity.MEDIUM

        # Only create alerts for medium+ severity
        severity_order = {
            AlertSeverity.INFORMATIONAL: 0,
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4,
        }
        if severity_order.get(severity, 0) < 2:
            continue

        alert = Alert(
            employee_id=employee.id,
            title=title,
            description=anomaly.get("description", ""),
            severity=severity,
            status=AlertStatus.OPEN,
            anomaly_type=anomaly_type,
            evidence=anomaly.get("evidence", {}),
        )
        db.add(alert)
        count += 1
        # Track so sibling anomalies of the same type don't re-enter
        existing.add((anomaly_type, title))

        if severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL):
            try:
                notify_threat_alert(
                    db=db,
                    alert_title=title,
                    severity=severity.value,
                    employee_name=employee.full_name,
                    anomaly_type=anomaly_type,
                    evidence=anomaly.get("evidence", {}),
                )
            except Exception:
                pass


    if count > 0:
        db.commit()

    return count


def _anomaly_title(atype: str, description: str) -> str:
    titles = {
        "volume_anomaly": "Abnormal Activity Volume Detected",
        "hourly_spike": "Unusual Hourly Activity Spike",
        "off_hours_data_transfer": "Off-Hours Data Transfer Detected",
        "usb_device_spike": "USB Device Usage Anomaly",
        "privilege_escalation": "Suspicious Privilege Changes",
        "large_file_downloads": "Large File Download Alert",
        "late_night_activity": "Late-Night System Access",
        "concentrated_weekend_access": "Concentrated Weekend Access",
    }
    return titles.get(atype, f"Anomaly: {atype}")


def _z_to_severity(z_score: float) -> AlertSeverity:
    if z_score > 5:
        return AlertSeverity.CRITICAL
    elif z_score > 3.5:
        return AlertSeverity.HIGH
    elif z_score > 2.5:
        return AlertSeverity.MEDIUM
    return AlertSeverity.LOW
