"""
Anomaly Detection Workflow

Implements statistical anomaly detection (Z-score, IQR, percentile),
rule-based detection, multi-factor anomaly scoring, and automated
alert generation.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median, stdev
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.activity_log import ActivityType
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.services.activity_aggregates import (
    EmployeeActivity,
    load_employee_activity,
)
from app.services.notification_service import notify_threat_alert
from app.services.threat_detection import Cohort, get_cohort



# ── Result cache ────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DETECTION_CACHE = DATA_DIR / "detection_results.json"

# A day is a volume anomaly only when it clears both bars:
#
#   1. It is busier than the 95th percentile of *every* employee's busiest
#      day, so it stands out against peers and not merely against the
#      employee's own (often very spiky) history.
#   2. It is at least this multiple of that employee's own typical day, so a
#      routine fluctuation on a quiet account is not reported.
#
# A robust z-score is still computed and recorded as evidence, but it is not
# a gate: when an employee's volume is steady the MAD is tiny, the z inflates
# without limit, and it flagged a busy day for ~91% of the organization.
VOLUME_MIN_MULTIPLE = 2.0


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

    # Aggregate activity in SQL once instead of materialising every log row
    # for the window, requesting only the aggregates the rules consume.
    activity = load_employee_activity(
        db,
        [e.id for e in employees],
        cutoff,
        sections={"daily", "downloads", "devices", "off_hours_dates"},
    )

    # Peer distribution, so rule thresholds adapt to the dataset's actual
    # scale. Fixed thresholds are calibrated for human-scale activity and
    # fire for every employee on a large dataset, drowning the real signal.
    cohort = get_cohort(db, days)

    results: list[dict[str, Any]] = []
    alerts_created = 0

    for chunk in _chunks(employees, 500):
        chunk_ids = [e.id for e in chunk]

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
            acts = activity.get(str(emp.id))
            anomalies = _detect_anomalies(acts, days, cohort) if acts else []
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
    # Only a whole-org run is a meaningful "latest detection" for the UI — a
    # single-employee scoped run must not overwrite the shared cache with a
    # one-row result.
    if employee_id is None:
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


def _peer_threshold(
    cohort: Cohort | None, metric: str, absolute_floor: float
) -> tuple[float, dict[str, Any]]:
    """Threshold for a rule: the peer 95th percentile, floored absolutely.

    A rule fires only when the employee is genuinely unusual *relative to
    their peers*, so the same rule stays meaningful whether the window
    holds a handful of events or several million. The absolute floor keeps
    unmistakable behaviour (e.g. any off-hours exfiltration at all) from
    being normalised away in a very active dataset.

    Returns ``(threshold, evidence)``; the evidence is attached to the
    alert so an analyst can see what the rule compared against.
    """
    if cohort is not None and cohort.mode == "relative":
        bounds = cohort.bounds(metric)
        if bounds:
            med, p95 = bounds
            if p95 <= med:
                # Every employee looks the same on this signal, so it
                # cannot distinguish anyone. Never fire rather than raise
                # a pointless alert against the whole organization.
                return float("inf"), {
                    "peer_median": round(med, 2),
                    "peer_p95": round(p95, 2),
                    "note": "signal does not vary across peers; rule disabled",
                }
            threshold = max(absolute_floor, p95)
            return threshold, {
                "peer_median": round(med, 2),
                "peer_p95": round(p95, 2),
                "absolute_floor": absolute_floor,
                "threshold": round(threshold, 2),
            }
    return absolute_floor, {
        "absolute_floor": absolute_floor,
        "threshold": absolute_floor,
    }


def _volume_severity(count: float, med: float) -> AlertSeverity:
    """Severity from how much busier the day is than a normal day.

    Keyed on magnitude rather than the raw robust z-score: when an
    employee's volume is steady the MAD is small, robust z inflates, and a
    z-based band labelled hundreds of routine swings as critical.
    """
    if med <= 0:
        return AlertSeverity.MEDIUM
    ratio = count / med
    if ratio >= 3:
        return AlertSeverity.CRITICAL
    if ratio >= 2:
        return AlertSeverity.HIGH
    return AlertSeverity.MEDIUM


def _confidence(value: float, threshold: float) -> float:
    """Confidence ramps from 0.5 at the threshold to 1.0 at twice it."""
    if threshold <= 0:
        return 1.0
    return round(min(1.0, (value / threshold) / 2.0), 3)


def _detect_anomalies(
    activity: EmployeeActivity,
    lookback_days: int,
    cohort: Cohort | None = None,
) -> list[dict[str, Any]]:
    """Run all detection methods and return a consolidated list."""
    anomalies: list[dict[str, Any]] = []

    anomalies.extend(_statistical_anomalies(activity, lookback_days, cohort))
    anomalies.extend(_rule_based_anomalies(activity, lookback_days, cohort))
    anomalies.extend(_temporal_anomalies(activity, lookback_days, cohort))

    return anomalies


def _statistical_anomalies(
    activity: EmployeeActivity,
    days: int,
    cohort: Cohort | None = None,
) -> list[dict[str, Any]]:
    """Robust z-score and IQR based anomaly detection on activity volumes.

    ``cohort`` provides the peer distribution used to decide whether a
    unusually busy day is also unusual by peer standards.
    """
    if activity.total_logs < 10:
        return []

    found: list[dict[str, Any]] = []

    # ── Daily volume anomaly (robust z-score) ───────────────
    daily = activity.daily_counts
    counts = list(daily.values())
    if len(counts) >= 5:
        med = median(counts)
        mad = median([abs(c - med) for c in counts])
        if mad > 0:
            scale = mad
        elif len(counts) > 1:
            scale = stdev(counts)
        else:
            scale = 0.0

        # A day must also be a busy day by peer standards. Without this, an
        # employee whose own volume is spiky gets flagged repeatedly: the
        # test only asks whether the day is unusual for *them*, and in this
        # dataset that is true for almost everybody.
        peak_threshold, peak_ctx = _peer_threshold(
            cohort, "peak_daily_volume", 1000
        )

        if scale > 0:
            for day, count in sorted(daily.items()):
                # 0.6745 rescales MAD onto the same footing as a std dev.
                z = 0.6745 * (count - med) / scale
                if (
                    count >= med * VOLUME_MIN_MULTIPLE
                    and count >= peak_threshold
                ):
                    day_key = day.strftime("%Y-%m-%d")
                    found.append(
                        {
                            "type": "volume_anomaly",
                            "description": f"Unusually high activity on {day_key}: {count} events (robust Z={z:.2f})",
                            "confidence": min(
                                1.0, count / max(peak_threshold, 1.0) / 2.0
                            ),
                            "severity": _volume_severity(count, med),
                            "evidence": {
                                "date": day_key,
                                "event_count": count,
                                "z_score": round(z, 2),
                                "median": round(med, 1),
                                "med_multiple": round(count / med, 2) if med else None,
                                "mad": round(mad, 1),
                                "peer_peak_threshold": peak_ctx.get("threshold"),
                            },
                        }
                    )

    # ── Hourly distribution anomaly (IQR) ────────────────────
    hourly = activity.hourly_counts
    hours = list(hourly.values())
    if len(hours) >= 4:
        q1 = sorted(hours)[len(hours) // 4]
        q3 = sorted(hours)[(3 * len(hours)) // 4]
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr

        for hour in sorted(hourly):
            count = hourly[hour]
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
    activity: EmployeeActivity,
    days: int,
    cohort: Cohort | None = None,
) -> list[dict[str, Any]]:
    """Domain rule-based anomaly detection.

    Thresholds are peer-relative (see ``_peer_threshold``) so a rule fires
    only for employees that genuinely stand out among their colleagues.
    """
    if not activity.total_logs:
        return []

    found: list[dict[str, Any]] = []

    # ── Rule: Off-hours data transfer ────────────────────────
    off_hours_xfers = activity.off_hours_of(ActivityType.DATA_TRANSFER)
    threshold, ctx = _peer_threshold(cohort, "off_hours_transfers", 3)
    if off_hours_xfers >= threshold:
        found.append(
            {
                "type": "off_hours_data_transfer",
                "description": f"{off_hours_xfers} data transfers during off-hours in the last {days} days (peer threshold {threshold:.0f})",
                "confidence": _confidence(off_hours_xfers, threshold),
                "severity": AlertSeverity.HIGH,
                "evidence": {
                    "count": off_hours_xfers,
                    **ctx,
                    "dates": [
                        d.isoformat()
                        for d in activity.off_hours_transfer_dates
                    ],
                },
            }
        )

    # ── Rule: USB device usage spike ─────────────────────────
    usb_events = activity.count_of(ActivityType.USB_DEVICE)
    threshold, ctx = _peer_threshold(cohort, "usb_events", 5)
    if usb_events >= threshold:
        found.append(
            {
                "type": "usb_device_spike",
                "description": f"{usb_events} USB device events detected (peer threshold {threshold:.0f})",
                "confidence": _confidence(usb_events, threshold),
                "severity": AlertSeverity.MEDIUM,
                "evidence": {
                    "count": usb_events,
                    **ctx,
                    "devices": sorted(activity.usb_devices),
                },
            }
        )

    # ── Rule: Privilege changes ──────────────────────────────
    priv_changes = activity.count_of(ActivityType.PRIVILEGE_CHANGE)
    threshold, ctx = _peer_threshold(cohort, "privilege_changes", 2)
    if priv_changes >= threshold:
        found.append(
            {
                "type": "privilege_escalation",
                "description": f"{priv_changes} privilege changes detected (peer threshold {threshold:.0f})",
                "confidence": _confidence(priv_changes, threshold),
                "severity": AlertSeverity.HIGH,
                "evidence": {"count": priv_changes, **ctx},
            }
        )

    # ── Rule: Large file downloads ───────────────────────────
    large_downloads = activity.large_download_count
    threshold, ctx = _peer_threshold(cohort, "large_downloads", 2)
    if large_downloads >= threshold:
        found.append(
            {
                "type": "large_file_downloads",
                "description": f"{large_downloads} large file downloads (>10MB, peer threshold {threshold:.0f})",
                "confidence": _confidence(large_downloads, threshold),
                "severity": AlertSeverity.MEDIUM,
                "evidence": {
                    "count": large_downloads,
                    **ctx,
                    "total_size_mb": round(activity.large_download_kb / 1024, 1),
                },
            }
        )

    return found


def _temporal_anomalies(
    activity: EmployeeActivity,
    days: int,
    cohort: Cohort | None = None,
) -> list[dict[str, Any]]:
    """Time-pattern based anomalies (weekends, late night, irregular).

    Thresholds are peer-relative, so a signal that every employee exhibits
    (for example working most weekend days) simply stops firing instead of
    raising an alert against the whole organization.
    """
    if not activity.total_logs:
        return []

    found: list[dict[str, Any]] = []

    # ── Late-night activity (midnight - 5AM) ─────────────────
    late_night = activity.late_night
    threshold, ctx = _peer_threshold(cohort, "late_night", 5)
    if late_night >= threshold:
        found.append(
            {
                "type": "late_night_activity",
                "description": f"{late_night} late-night activities (midnight-5AM, peer threshold {threshold:.0f})",
                "confidence": _confidence(late_night, threshold),
                "severity": AlertSeverity.LOW,
                "evidence": {
                    "count": late_night,
                    **ctx,
                    "pct": round(
                        late_night / max(activity.total_logs, 1) * 100, 1
                    ),
                },
            }
        )

    # ── Weekend activity concentration ───────────────────────
    weekend_unique_days = activity.weekend_days
    threshold, ctx = _peer_threshold(cohort, "weekend_days", 4)
    if weekend_unique_days >= threshold:
        found.append(
            {
                "type": "concentrated_weekend_access",
                "description": f"Accessed systems on {weekend_unique_days} different weekend days (peer threshold {threshold:.0f})",
                "confidence": _confidence(weekend_unique_days, threshold),
                "severity": AlertSeverity.LOW,
                "evidence": {
                    "weekend_days": weekend_unique_days,
                    **ctx,
                    "total_weekend_events": activity.weekend_events,
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
