"""
Behavioral Profiling Engine

Computes statistical baselines, activity patterns, and peer-group
comparisons for each employee. This is the core analytics engine
for Milestone 2's behavioral analytics module.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev, median
from typing import Any

from sqlalchemy import case, cast, Date, func, or_
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.activity_log import ActivityLog, ActivityType
from app.models.behavioral_baseline import BehavioralBaseline


# ── Public API ──────────────────────────────────────────────────


def compute_baseline(db: Session, employee_id: str) -> dict[str, Any]:
    """Compute a full behavioral baseline for a single employee."""
    logs = _get_recent_logs(db, employee_id, days=90)
    total = len(logs)

    if total == 0:
        return {"error": "no activity data available", "total_logs": 0}

    baseline: dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_logs": total,
        "daily_avg": round(total / 30, 2) if total > 0 else 0,
    }

    baseline.update(_activity_type_profile(logs))
    baseline.update(_temporal_profile(logs))
    baseline.update(_statistical_baselines(logs))
    baseline.update(_peer_comparison(db, employee_id, logs))

    return baseline


def compute_all_baselines(db: Session) -> int:
    """Recompute baselines for every employee in the database."""
    employees = db.query(Employee).all()
    count = 0
    for emp in employees:
        data = compute_baseline(db, str(emp.id))
        if "error" in data:
            continue
        store_baseline(db, str(emp.id), data)
        count += 1

    db.commit()
    return count


def store_baseline(
    db: Session, employee_id: str, data: dict[str, Any]
) -> BehavioralBaseline:
    """Persist (or update) the stored behavioral baseline for an employee."""
    existing = (
        db.query(BehavioralBaseline)
        .filter(BehavioralBaseline.employee_id == employee_id)
        .first()
    )
    if existing:
        existing.baseline_data = data
        existing.updated_at = datetime.utcnow()
        return existing

    baseline = BehavioralBaseline(
        employee_id=employee_id,
        baseline_data=data,
        generated_at=datetime.utcnow(),
    )
    db.add(baseline)
    db.flush()
    return baseline


def get_employee_profile(
    db: Session, employee_id: str
) -> dict[str, Any]:
    """Return the latest stored baseline for an employee."""
    baseline = (
        db.query(BehavioralBaseline)
        .filter(BehavioralBaseline.employee_id == employee_id)
        .first()
    )
    if not baseline:
        return compute_baseline(db, employee_id)
    return {
        "id": str(baseline.id),
        "employee_id": str(baseline.employee_id),
        "baseline_data": baseline.baseline_data,
        "generated_at": baseline.generated_at.isoformat(),
        "updated_at": baseline.updated_at.isoformat(),
    }


# ── Internal helpers ────────────────────────────────────────────


def _get_recent_logs(db: Session, employee_id: str, days: int = 90):
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(ActivityLog)
        .filter(
            ActivityLog.employee_id == employee_id,
            ActivityLog.occurred_at >= cutoff,
        )
        .order_by(ActivityLog.occurred_at)
        .all()
    )


def _activity_type_profile(logs: list[ActivityLog]) -> dict[str, Any]:
    """Build a profile of activity type frequencies."""
    counter: Counter[str] = Counter()
    hour_distribution: dict[str, list[int]] = defaultdict(list)
    day_distribution: dict[str, list[int]] = defaultdict(list)

    for log in logs:
        atype = log.activity_type.value if hasattr(log.activity_type, "value") else str(log.activity_type)
        counter[atype] += 1
        hour_distribution[atype].append(log.occurred_at.hour)
        day_distribution[atype].append(log.occurred_at.weekday())

    # Convert hourly patterns to a compact summary
    hour_summary = {}
    for atype, hours in hour_distribution.items():
        if hours:
            hour_summary[atype] = {
                "mean_hour": round(mean(hours), 1),
                "peak_hour": max(set(hours), key=hours.count),
            }

    return {
        "activity_distribution": dict(counter),
        "activity_hourly_patterns": hour_summary,
        "weekend_activity": sum(
            1 for log in logs if log.occurred_at.weekday() >= 5
        ),
    }


def _temporal_profile(logs: list[ActivityLog]) -> dict[str, Any]:
    """Analyze when the employee is active (off-hours, weekends, bursts)."""
    off_hours = sum(
        1 for log in logs if log.occurred_at.hour < 7 or log.occurred_at.hour > 19
    )
    late_night = sum(
        1 for log in logs if log.occurred_at.hour < 5
    )

    # Burst detection: count time windows where activity > 2 standard deviations above mean
    daily_counts: Counter[str] = Counter()
    for log in logs:
        day_key = log.occurred_at.strftime("%Y-%m-%d")
        daily_counts[day_key] += 1

    counts = list(daily_counts.values())
    burst_threshold = mean(counts) + 2 * (stdev(counts) if len(counts) > 1 else 0)
    burst_days = sum(1 for c in counts if c > burst_threshold)

    return {
        "total_off_hours": off_hours,
        "late_night_activity": late_night,
        "off_hours_pct": round(off_hours / max(len(logs), 1) * 100, 1),
        "burst_days": burst_days,
        "avg_events_per_day": round(mean(counts), 1) if counts else 0,
    }


def _statistical_baselines(logs: list[ActivityLog]) -> dict[str, Any]:
    """Compute Z-score thresholds and deviation markers."""
    hourly_counts: Counter[int] = Counter()
    for log in logs:
        hourly_counts[log.occurred_at.hour] += 1

    values = list(hourly_counts.values())
    if len(values) < 2:
        return {
            "hourly_activity_mean": 0,
            "hourly_activity_std": 0,
            "z_score_threshold": 2.0,
        }

    m = mean(values)
    s = stdev(values)

    return {
        "hourly_activity_mean": round(m, 2),
        "hourly_activity_std": round(s, 2),
        "z_score_threshold": 2.0,
        "anomaly_hours": [
            int(h)
            for h, c in hourly_counts.items()
            if (c - m) / max(s, 0.01) > 2.0
        ],
    }


def _peer_comparison(
    db: Session, employee_id: str, employee_logs: list[ActivityLog]
) -> dict[str, Any]:
    """
    Compare this employee's profile to their department peers.

    Peer statistics are computed with SQL aggregation (single query)
    instead of loading every peer's logs into memory, which makes
    whole-org baseline computation feasible at 1000+ employees.
    """
    employee = (
        db.query(Employee).filter(Employee.id == employee_id).first()
    )
    if not employee or not employee.department:
        return {"peer_group": None}

    peers = (
        db.query(Employee.id)
        .filter(
            Employee.department == employee.department,
            Employee.id != employee.id,
        )
        .all()
    )
    peer_ids = [p.id for p in peers]
    if not peer_ids:
        return {"peer_group": None}

    cutoff = datetime.utcnow() - timedelta(days=90)
    hour_expr = func.extract("hour", ActivityLog.occurred_at)
    off_hours_cond = or_(hour_expr < 7, hour_expr > 19)

    total_logs, distinct_days, off_hours = (
        db.query(
            func.count(ActivityLog.id),
            func.count(func.distinct(cast(ActivityLog.occurred_at, Date))),
            func.coalesce(
                func.sum(case((off_hours_cond, 1), else_=0)), 0
            ),
        )
        .filter(
            ActivityLog.employee_id.in_(peer_ids),
            ActivityLog.occurred_at >= cutoff,
        )
        .one()
    )

    if not total_logs:
        return {"peer_group": None}

    peer_avg = round(total_logs / max(distinct_days, 1), 1)
    peer_off_hours_pct = round(off_hours / total_logs * 100, 1)

    emp_daily = Counter(
        log.occurred_at.strftime("%Y-%m-%d") for log in employee_logs
    )
    emp_avg = round(mean(emp_daily.values()), 1) if emp_daily else 0

    emp_off_hours = sum(
        1
        for log in employee_logs
        if log.occurred_at.hour < 7 or log.occurred_at.hour > 19
    )
    emp_off_hours_pct = round(
        emp_off_hours / max(len(employee_logs), 1) * 100, 1
    )

    return {
        "peer_group": employee.department,
        "peer_group_size": len(peer_ids),
        "your_daily_avg": emp_avg,
        "peer_daily_avg": peer_avg,
        "your_off_hours_pct": emp_off_hours_pct,
        "peer_off_hours_pct": peer_off_hours_pct,
        "activity_vs_peer": round(emp_avg - peer_avg, 1),
    }
