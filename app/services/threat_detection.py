"""
Threat Detection Models

Sophisticated threat detection models that combine multiple signals
to identify insider threats including data exfiltration, privilege
abuse, policy violations, and overall insider threat scoring.

Scoring is *peer-relative*
--------------------------
Each signal is scored by how far an employee deviates from their peers
rather than against a fixed event count. The previous absolute thresholds
were calibrated for human-scale activity (a handful of transfers a week),
so on a dataset where every employee performs ~1,000 data transfers a
month every factor saturated at its cap simultaneously. That collapsed
every employee onto the same ~50 weighted score and produced no
discrimination (951/1002 employees "medium", zero "critical").

Relative scoring removes the dataset-specific constants entirely: a
signal's severity is its excess above the cohort median, expressed as a
fraction of the distance from the median to the 95th percentile. This is
scale-independent, so the same code behaves correctly whether the window
holds a dozen events or several million — no dataset swap or threshold
retuning needed, and no change in query cost.

When a cohort is too small to be meaningful (fewer than
``MIN_COHORT_SIZE`` employees, e.g. a single-employee lookup on a fresh
database) the engine falls back to the original absolute thresholds.
"""

from __future__ import annotations

import math
import time as _time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.activity_log import ActivityLog, ActivityType
from app.models.risk_score import RiskScore, RiskLevel
from app.models.behavioral_baseline import BehavioralBaseline
from app.services.activity_aggregates import (
    EmployeeActivity,
    load_employee_activity,
)


# ── Threat Score Weights ────────────────────────────────────────

WEIGHTS = {
    "data_exfiltration": 0.30,
    "off_hours_access": 0.15,
    "privilege_abuse": 0.20,
    "policy_violation": 0.15,
    "behavioral_deviation": 0.20,
}

# A cohort smaller than this cannot support a meaningful distribution
# (median/p95 are noise), so absolute thresholds are used instead.
MIN_COHORT_SIZE = 20

# Which raw signal feeds which factor, and the most points that factor
# can contribute. Kept separate from the scoring logic so the model
# definitions stay readable and easy to extend.
MODEL_SPECS: dict[str, list[tuple[str, str, float]]] = {
    "data_exfiltration": [
        ("data_transfer_volume", "data_transfer_count", 40.0),
        ("off_hours_transfers", "off_hours_transfers", 30.0),
        ("external_transfers", "external_transfers", 30.0),
        ("large_downloads", "huge_downloads", 25.0),
        ("usb_storage", "usb_events", 20.0),
    ],
    "off_hours_access": [
        ("off_hours_ratio", "off_hours_pct", 30.0),
        ("late_night_activity", "late_night", 30.0),
        ("weekend_access", "weekend_days", 25.0),
    ],
    "privilege_abuse": [
        ("privilege_changes", "privilege_changes", 40.0),
        ("remote_access", "off_hours_remote", 30.0),
        ("remote_access_business_hours", "remote_other", 15.0),
    ],
    "policy_violation": [
        ("usb_device_usage", "usb_events", 30.0),
        ("data_to_usb", "data_to_usb", 30.0),
    ],
    "behavioral_deviation": [
        ("daily_avg_deviation", "daily_avg_deviation_pct", 35.0),
        ("off_hours_deviation", "off_hours_deviation", 25.0),
        ("data_transfer_deviation", "data_transfer_ratio", 25.0),
    ],
}

# Absolute fallback scale: the signal value at which the factor is
# considered maximally severe. Only used when the cohort is too small to
# build a distribution (see MIN_COHORT_SIZE). These mirror the original
# published thresholds.
ABSOLUTE_SCALE: dict[str, float] = {
    "data_transfer_count": 8.0,
    "off_hours_transfers": 4.0,
    "external_transfers": 3.0,
    "huge_downloads": 4.0,
    "large_downloads": 8.0,
    "peak_daily_volume": 1000.0,
    "usb_events": 5.0,
    "off_hours_pct": 60.0,
    "late_night": 10.0,
    "weekend_days": 5.0,
    "privilege_changes": 3.33,
    "off_hours_remote": 3.75,
    "remote_other": 5.0,
    "data_to_usb": 3.0,
    "daily_avg_deviation_pct": 115.0,
    "off_hours_deviation": 50.0,
    "data_transfer_ratio": 5.0,
}

# Human-readable labels for the explainability payload.
SIGNAL_LABELS: dict[str, str] = {
    "data_transfer_count": "data transfers",
    "off_hours_transfers": "off-hours transfers",
    "external_transfers": "external transfers",
    "huge_downloads": "large downloads (>50MB)",
    "large_downloads": "large downloads (>10MB)",
    "peak_daily_volume": "busiest day volume",
    "usb_events": "USB device events",
    "off_hours_pct": "off-hours activity share",
    "late_night": "late-night events",
    "weekend_days": "weekend days active",
    "privilege_changes": "privilege changes",
    "off_hours_remote": "off-hours remote access",
    "remote_other": "remote access",
    "data_to_usb": "transfers to removable media",
    "daily_avg_deviation_pct": "daily volume vs baseline",
    "off_hours_deviation": "off-hours vs baseline",
    "data_transfer_ratio": "transfer rate vs baseline",
}


# ── Public API ──────────────────────────────────────────────────


def assess_employee_threat(
    db: Session,
    employee_id: str,
    days: int = 30,
    activity: EmployeeActivity | None = None,
    baseline: dict[str, Any] | None = None,
    cohort: "Cohort | None" = None,
) -> dict[str, Any]:
    """Run all threat models for one employee and produce a consolidated score.

    Scoring is relative to the organization-wide peer cohort (cached), so
    a single-employee view reports the same number the whole-org run
    would — an employee never looks more or less risky depending on which
    page requested their score.
    """
    # Aggregate the employee's activity once and share it across all models
    # (important when scoring 1000 employees).
    if activity is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        activity = load_employee_activity(
            db, [employee_id], cutoff, sections=_ACTIVITY_SECTIONS
        ).get(str(employee_id), EmployeeActivity(employee_id=str(employee_id)))

    # Load the stored baseline when the caller has not supplied one. Without
    # it the deviation signals would be measured against zero, so a normal
    # off-hours share would read as a deviation and the single-employee
    # score would disagree with the whole-org run for the same person.
    if baseline is None:
        stored = (
            db.query(BehavioralBaseline)
            .filter(BehavioralBaseline.employee_id == employee_id)
            .first()
        )
        baseline = (stored.baseline_data or {}) if stored else {}

    if cohort is None:
        cohort = get_cohort(db, days)

    signals = _extract_signals(activity, days, baseline)
    models = _score_models(signals, cohort)
    threat_score, blended = _composite_threat_score(models)

    return {
        "employee_id": employee_id,
        "threat_score": round(threat_score, 1),
        "threat_level": _threat_level(threat_score).value,
        "model_scores": models,
        "score_components": blended,
        "scoring_mode": cohort.mode,
        "cohort_size": cohort.size,
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


def get_top_threats(db: Session, limit: int = 20) -> list[dict[str, Any]]:
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


def _top_risk_threats(db: Session, limit: int = 150) -> list[dict[str, Any]]:
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
            "top_factors": (r.breakdown or {}).get("top_factors", []),
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
    cohort: "Cohort | None" = None,
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

    # One aggregated view of activity for the whole set (a few grouped SQL
    # queries) instead of materialising every log row per chunk.
    activity = load_employee_activity(
        db, employee_ids, cutoff, sections=_ACTIVITY_SECTIONS
    )

    if cohort is None:
        cohort = get_cohort(db, days)

    results: dict[str, dict[str, Any]] = {}
    for emp_id in employee_ids:
        try:
            acts = activity.get(emp_id) or EmployeeActivity(employee_id=emp_id)
            signals = _extract_signals(
                acts, days, baselines_by_employee.get(emp_id)
            )
            models = _score_models(signals, cohort)
            score, blended = _composite_threat_score(models)
            results[emp_id] = {
                "employee_id": emp_id,
                "threat_score": round(score, 1),
                "threat_level": _threat_level(score).value,
                "model_scores": models,
                "score_components": blended,
                "scoring_mode": cohort.mode,
                "cohort_size": cohort.size,
                "assessed_at": datetime.utcnow().isoformat(),
                "lookback_days": days,
            }
        except Exception:
            continue
    return results


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    """Split a list into consecutive chunks of at most ``size`` items."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def _pre_score_employees(db: Session, cutoff: datetime) -> dict[str, int]:
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


# ── Peer cohort ─────────────────────────────────────────────────

# Sections of the activity aggregate the signal extractors read.
_ACTIVITY_SECTIONS = frozenset({"daily", "downloads", "destinations"})

# The cohort statistics are derived from every employee's behaviour, so
# building them once and reusing them for a few minutes keeps single
# employee lookups (the employee dashboard) cheap instead of triggering a
# whole-organization pass on every request. Keyed by lookback window.
_COHORT_CACHE: dict[int, tuple[float, "Cohort"]] = {}
_COHORT_TTL_SECONDS = 300.0


class Cohort:
    """Peer distribution for each behavioural signal.

    ``stats`` maps a metric key to ``(median, p95)``; ``mode`` records
    whether relative scoring could be used or absolute thresholds were
    substituted because too few employees were available.
    """

    __slots__ = ("stats", "size", "mode")

    def __init__(
        self,
        stats: dict[str, tuple[float, float]],
        size: int,
        mode: str,
    ) -> None:
        self.stats = stats
        self.size = size
        self.mode = mode

    def bounds(self, metric: str) -> tuple[float, float] | None:
        return self.stats.get(metric)


def get_cohort(db: Session, days: int = 30, force: bool = False) -> Cohort:
    """Return the organization-wide peer cohort for ``days`` (cached).

    Computed from SQL-side activity aggregates for every employee, so it
    costs a handful of grouped queries rather than materialising raw rows.
    """
    now = _time.monotonic()
    cached = _COHORT_CACHE.get(days)
    if cached and not force and now - cached[0] < _COHORT_TTL_SECONDS:
        return cached[1]

    cohort = _build_cohort(db, days)
    _COHORT_CACHE[days] = (now, cohort)
    return cohort


def invalidate_cohort_cache() -> None:
    """Drop cached cohort stats (called after ingestion / re-anchoring)."""
    _COHORT_CACHE.clear()


def _build_cohort(db: Session, days: int) -> Cohort:
    """Compute median/p95 for every signal across all employees."""
    employees = db.query(Employee).all()
    cutoff = datetime.utcnow() - timedelta(days=days)
    baselines = {
        b.employee_id: (b.baseline_data or {})
        for b in db.query(BehavioralBaseline).all()
    }

    activity = load_employee_activity(
        db, [e.id for e in employees], cutoff, sections=_ACTIVITY_SECTIONS
    )

    columns: dict[str, list[float]] = {m: [] for m in ABSOLUTE_SCALE}
    for emp in employees:
        acts = activity.get(str(emp.id))
        if acts is None:
            continue
        signals = _extract_signals(acts, days, baselines.get(emp.id))
        for metric, value in signals.items():
            columns.setdefault(metric, []).append(float(value))

    size = max((len(v) for v in columns.values()), default=0)
    stats: dict[str, tuple[float, float]] = {}
    for metric, values in columns.items():
        if not values:
            continue
        ordered = sorted(values)
        stats[metric] = (_percentile(ordered, 0.5), _percentile(ordered, 0.95))

    mode = "relative" if size >= MIN_COHORT_SIZE else "absolute"
    return Cohort(stats, size, mode)


def _percentile(ordered: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list."""
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return float(ordered[0])
    pos = q * (len(ordered) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(ordered[lo])
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo))


# ── Signal extraction ───────────────────────────────────────────


def _extract_signals(
    activity: EmployeeActivity,
    days: int,
    baseline: dict[str, Any] | None,
) -> dict[str, float]:
    """Reduce one employee's activity to the raw per-factor signal values.

    These are *raw* measurements (counts, percentages, ratios); the
    cohort turns them into severities in ``_score_models``.
    """
    total = activity.total_logs
    window = max(days, 1)
    xfers = activity.count_of(ActivityType.DATA_TRANSFER)
    off_hours_xfers = activity.off_hours_of(ActivityType.DATA_TRANSFER)
    remote = activity.count_of(ActivityType.REMOTE_ACCESS)
    off_hours_remote = activity.off_hours_of(ActivityType.REMOTE_ACCESS)

    base = baseline or {}

    # Deviation of recent daily volume from the stored baseline.
    baseline_daily = base.get("daily_avg") or 0
    daily_deviation = 0.0
    if total and baseline_daily > 0:
        recent_daily = total / window
        daily_deviation = (
            abs(recent_daily - baseline_daily) / max(baseline_daily, 0.1) * 100
        )

    # How much the off-hours share exceeds the baseline share.
    baseline_off_pct = base.get("off_hours_pct") or 0
    off_hours_deviation = 0.0
    if total:
        recent_off_pct = activity.off_hours / total * 100
        off_hours_deviation = max(0.0, recent_off_pct - baseline_off_pct)

    # Transfer rate relative to the baseline rate (1.0 == unchanged).
    baseline_xfers = (base.get("activity_distribution") or {}).get(
        "data_transfer", 0
    ) or 0
    transfer_ratio = 0.0
    if total and baseline_xfers > 0:
        recent_rate = xfers / window
        baseline_rate = baseline_xfers / 30
        if baseline_rate > 0:
            transfer_ratio = recent_rate / baseline_rate

    return {
        "data_transfer_count": float(xfers),
        "off_hours_transfers": float(off_hours_xfers),
        "external_transfers": float(
            activity.transfer_destinations.get("external", 0)
        ),
        "huge_downloads": float(activity.huge_download_count),
        "large_downloads": float(activity.large_download_count),
        "peak_daily_volume": (
            float(max(activity.daily_counts.values()))
            if activity.daily_counts
            else 0.0
        ),
        "usb_events": float(activity.count_of(ActivityType.USB_DEVICE)),
        "off_hours_pct": (
            activity.off_hours / total * 100 if total else 0.0
        ),
        "late_night": float(activity.late_night),
        "weekend_days": float(activity.weekend_days),
        "privilege_changes": float(
            activity.count_of(ActivityType.PRIVILEGE_CHANGE)
        ),
        "off_hours_remote": float(off_hours_remote),
        "remote_other": float(max(0, remote - off_hours_remote)),
        "data_to_usb": float(activity.transfer_destinations.get("usb", 0)),
        "daily_avg_deviation_pct": daily_deviation,
        "off_hours_deviation": off_hours_deviation,
        "data_transfer_ratio": transfer_ratio,
    }


# ── Model scoring ───────────────────────────────────────────────


def _score_models(
    signals: dict[str, float], cohort: Cohort
) -> dict[str, dict[str, Any]]:
    """Score every threat model from raw signals against the peer cohort."""
    models: dict[str, dict[str, Any]] = {}

    for model_name, spec in MODEL_SPECS.items():
        score = 0.0
        factors: dict[str, Any] = {}

        for factor_name, metric, max_points in spec:
            value = float(signals.get(metric, 0.0))
            severity = _severity(value, metric, cohort)
            points = severity * max_points
            if points <= 0:
                continue

            score += points
            factor: dict[str, Any] = {
                "score": round(points, 1),
                "value": round(value, 2),
                "metric": SIGNAL_LABELS.get(metric, metric),
                "severity": round(severity, 3),
            }
            bounds = cohort.bounds(metric)
            if cohort.mode == "relative" and bounds:
                median, p95 = bounds
                factor["peer_median"] = round(median, 2)
                factor["peer_p95"] = round(p95, 2)
                factor["excess_over_peer_median"] = round(
                    max(0.0, value - median), 2
                )
            factors[factor_name] = factor

        score = min(score, 100.0)
        models[model_name] = {
            "score": round(score, 1),
            "level": _sub_level(score),
            "factors": factors,
        }

    return models


def _severity(value: float, metric: str, cohort: Cohort) -> float:
    """Map a raw signal value onto a 0-1 severity.

    Relative mode: how far the value exceeds the cohort median, as a
    fraction of the median→p95 distance. A median employee scores 0 (they
    are, by definition, unremarkable) and the top 5% saturate.

    Absolute mode: the original fixed-scale behaviour, used only when the
    cohort is too small to have a meaningful distribution.
    """
    if cohort.mode == "relative":
        bounds = cohort.bounds(metric)
        if bounds:
            median, p95 = bounds
            if p95 > median:
                return _clamp((value - median) / (p95 - median))
            # Degenerate spread: everything identical, so only a clear
            # excess over the median is treated as notable.
            return 1.0 if value > median else 0.0

    scale = ABSOLUTE_SCALE.get(metric)
    if not scale:
        return 0.0
    return _clamp(value / scale)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


# How much weight the single most severe model carries in the composite.
# A plain weighted average across all five models dilutes a single
# extreme dimension: an employee exfiltrating at 100 would average down to
# ~30 and be labelled "low" next to spotless peers. Blending in the peak
# model keeps the composite sensitive to one dominant behaviour while
# still rewarding employees who are elevated across several dimensions.
PEAK_WEIGHT = 0.5


def _composite_threat_score(
    models: dict[str, dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    """Combine the model scores into one 0-100 insider threat score.

    ``composite = (1 - PEAK_WEIGHT) * weighted_average + PEAK_WEIGHT * peak``
    where ``peak`` is the highest single model score. Both inputs are
    already peer-relative, so the composite is too.
    """
    if not models:
        return 0.0, {"weighted_score": 0.0, "peak_model": None, "peak_score": 0.0}

    weighted = sum(
        details["score"] * WEIGHTS[name]
        for name, details in models.items()
        if name in WEIGHTS
    )
    peak_name, peak = max(
        ((name, details["score"]) for name, details in models.items()),
        key=lambda pair: pair[1],
    )
    composite = _clamp(
        (1.0 - PEAK_WEIGHT) * weighted + PEAK_WEIGHT * peak, 0.0, 100.0
    )
    return composite, {
        "weighted_score": round(weighted, 1),
        "peak_model": peak_name,
        "peak_score": round(peak, 1),
        "peak_weight": PEAK_WEIGHT,
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
