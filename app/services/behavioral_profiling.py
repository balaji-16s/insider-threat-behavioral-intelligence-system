"""
Behavioral Profiling Engine

Computes statistical baselines, activity patterns, and peer-group
comparisons for each employee. This is the core analytics engine
for Milestone 2's behavioral analytics module.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Any

from sqlalchemy import case, cast, Date, func, or_
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.activity_log import ActivityLog
from app.models.behavioral_baseline import BehavioralBaseline
from app.services.activity_aggregates import (
    EmployeeActivity,
    load_employee_activity,
)


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


def compute_all_baselines(db: Session, days: int = 90) -> int:
    """Recompute baselines for every employee in the database.

    Uses the shared SQL aggregation layer instead of materialising every
    activity row as a Python object (millions of rows → tens of seconds),
    and aggregates peer statistics per department in a single SQL pass.
    """
    employees = db.query(Employee).all()
    cutoff = datetime.utcnow() - timedelta(days=days)

    dept_stats = _department_peer_stats(db, cutoff, employees)

    existing = {
        str(b.employee_id): b
        for b in db.query(BehavioralBaseline).all()
    }

    # One aggregated view of activity for the whole org (two grouped
    # queries) shared by every employee's baseline computation. Baselines
    # only need volume and daily counts, so the other aggregates are skipped.
    activity = load_employee_activity(
        db, [e.id for e in employees], cutoff, sections={"daily"}
    )

    count = 0
    for emp in employees:
        act = activity.get(str(emp.id))
        if act is None or not act.total_logs:
            continue
        data = _build_baseline_from_aggregates(emp, act, dept_stats)
        _store_baseline(existing, db, str(emp.id), data)
        count += 1

    db.commit()
    return count


def _hours_by_type(activity: EmployeeActivity) -> dict[str, dict[int, int]]:
    """Reshape ``(type, hour) -> count`` into ``type -> {hour: count}``."""
    by_type: dict[str, dict[int, int]] = defaultdict(dict)
    for (atype, hour), count in activity.type_hour_counts.items():
        by_type[atype][hour] = count
    return by_type


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


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    """Split a list into consecutive chunks of at most ``size`` items."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def _department_peer_stats(
    db: Session, cutoff: datetime, employees: list[Employee]
) -> dict[str, dict[str, Any]]:
    """Aggregate peer statistics per department with a single SQL pass.

    Returns ``{department: {peer_group_size, peer_daily_avg, peer_off_hours_pct}}``
    so batched baseline computation never issues per-employee peer queries.
    """
    dept_sizes: Counter[str] = Counter(
        e.department for e in employees if e.department
    )

    hour_expr = func.extract("hour", ActivityLog.occurred_at)
    off_hours_cond = or_(hour_expr < 7, hour_expr > 19)
    rows = (
        db.query(
            Employee.department,
            func.count(ActivityLog.id),
            func.count(func.distinct(cast(ActivityLog.occurred_at, Date))),
            func.coalesce(func.sum(case((off_hours_cond, 1), else_=0)), 0),
        )
        .join(ActivityLog, ActivityLog.employee_id == Employee.id)
        .filter(ActivityLog.occurred_at >= cutoff)
        .group_by(Employee.department)
        .all()
    )

    stats: dict[str, dict[str, Any]] = {}
    for dept, total, distinct_days, off_hours in rows:
        stats[dept] = {
            "peer_group_size": max(dept_sizes.get(dept, 0) - 1, 0),
            "peer_daily_avg": round(total / max(distinct_days, 1), 1),
            "peer_off_hours_pct": (
                round(off_hours / total * 100, 1) if total else 0
            ),
        }
    return stats


def _build_baseline_from_aggregates(
    employee: Employee,
    activity: EmployeeActivity,
    dept_stats: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a full baseline for one employee from SQL aggregates.

    Produces exactly the same keys/values as the per-row implementation,
    but from pre-aggregated counts so no activity rows are materialised.
    """
    total = activity.total_logs
    daily = activity.daily_counts

    hour_summary = {}
    for atype, hours in _hours_by_type(activity).items():
        type_total = sum(hours.values())
        hour_summary[atype] = {
            "mean_hour": round(
                sum(hour * count for hour, count in hours.items())
                / max(type_total, 1),
                1,
            ),
            # max over sorted hours makes ties deterministic (lowest wins)
            "peak_hour": max(sorted(hours), key=hours.__getitem__),
        }

    counts = list(daily.values())
    burst_threshold = (
        mean(counts) + 2 * (stdev(counts) if len(counts) > 1 else 0)
        if counts
        else 0
    )
    burst_days = sum(1 for c in counts if c > burst_threshold)

    data: dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_logs": total,
        "daily_avg": round(total / 30, 2) if total else 0,
        "activity_distribution": dict(activity.type_counts),
        "activity_hourly_patterns": hour_summary,
        "weekend_activity": activity.weekend_events,
        "total_off_hours": activity.off_hours,
        "late_night_activity": activity.late_night,
        "off_hours_pct": round(activity.off_hours / max(total, 1) * 100, 1),
        "burst_days": burst_days,
        "avg_events_per_day": round(mean(counts), 1) if counts else 0,
    }
    data.update(_statistical_baselines_from_counts(activity.hourly_counts))
    data.update(
        _peer_comparison_from_stats(
            employee,
            Counter(
                {d.strftime("%Y-%m-%d"): c for d, c in daily.items()}
            ),
            activity.off_hours,
            total,
            dept_stats,
        )
    )
    return data


def _statistical_baselines_from_counts(
    hourly_counts: Counter[int],
) -> dict[str, Any]:
    """Z-score markers derived from per-hour activity counts."""
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
        "anomaly_hours": sorted(
            int(h)
            for h, c in hourly_counts.items()
            if (c - m) / max(s, 0.01) > 2.0
        ),
    }


def _peer_comparison_from_stats(
    employee: Employee,
    emp_daily: Counter[str],
    emp_off_hours: int,
    total_logs: int,
    dept_stats: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Peer comparison using precomputed per-department stats (no queries)."""
    dept = employee.department
    stats = (dept_stats or {}).get(dept) if dept else None
    if not stats:
        return {"peer_group": None}

    emp_avg = round(mean(emp_daily.values()), 1) if emp_daily else 0
    emp_off_hours_pct = round(
        emp_off_hours / max(total_logs, 1) * 100, 1
    )

    return {
        "peer_group": dept,
        "peer_group_size": stats["peer_group_size"],
        "your_daily_avg": emp_avg,
        "peer_daily_avg": stats["peer_daily_avg"],
        "your_off_hours_pct": emp_off_hours_pct,
        "peer_off_hours_pct": stats["peer_off_hours_pct"],
        "activity_vs_peer": round(emp_avg - stats["peer_daily_avg"], 1),
    }


def _store_baseline(
    existing: dict[str, BehavioralBaseline],
    db: Session,
    employee_id: str,
    data: dict[str, Any],
) -> None:
    """Upsert a baseline using the preloaded ``existing`` map (no query)."""
    baseline = existing.get(employee_id)
    if baseline:
        baseline.baseline_data = data
        baseline.updated_at = datetime.utcnow()
    else:
        baseline = BehavioralBaseline(
            employee_id=employee_id,
            baseline_data=data,
            generated_at=datetime.utcnow(),
        )
        db.add(baseline)
        existing[employee_id] = baseline


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
                # sorted() makes ties deterministic (lowest peak hour wins)
                "peak_hour": max(sorted(set(hours)), key=hours.count),
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
        "anomaly_hours": sorted(
            int(h)
            for h, c in hourly_counts.items()
            if (c - m) / max(s, 0.01) > 2.0
        ),
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
