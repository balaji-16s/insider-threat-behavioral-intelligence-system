"""
Insider Risk Scoring Engine

Runs the weighted insider-threat models for every employee and persists
the results as RiskScore records so the scores can be tracked over time.
Also produces organization-wide risk analytics (distribution, trend,
department breakdown, and top contributors).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.risk_score import RiskScore, RiskLevel
from app.services.threat_detection import assess_employees_batch

# Marker stored in the breakdown so engine-generated scores can be
# refreshed on recalculation while preserving the historical baseline.
ENGINE_TAG = "threat_detection_v1"


# ── Scoring Engine ───────────────────────────────────────────────


def calculate_risk_scores(
    db: Session,
    days: int = 30,
    employee_id: str | None = None,
) -> dict[str, Any]:
    """
    Run the insider risk scoring engine and persist the results.

    Replaces previously engine-generated scores so repeated runs stay
    clean while historical (seed/imported) scores are preserved.
    """
    if employee_id:
        employees = db.query(Employee).filter(Employee.id == employee_id).all()
    else:
        employees = db.query(Employee).all()

    # Remove previous engine-generated scores for the affected employees
    employee_ids = [emp.id for emp in employees]
    if employee_ids:
        db.query(RiskScore).filter(
            RiskScore.employee_id.in_(employee_ids),
            RiskScore.breakdown.op("->>")("engine") == ENGINE_TAG,
        ).delete(synchronize_session=False)

    # Run the full threat models in one batched pass (chunked IN(...)
    # activity loading) instead of firing a per-employee query chain,
    # which previously made whole-org recalculations slow on large datasets.
    assessments = assess_employees_batch(
        db, [str(emp.id) for emp in employees], days
    )

    created = 0
    latest: dict[str, dict[str, Any]] = {}
    calculated_at = datetime.utcnow()

    for emp in employees:
        result = assessments.get(str(emp.id))
        if result is None:
            continue

        score = round(result["threat_score"], 1)
        level = RiskLevel(result["threat_level"])

        breakdown = {
            "engine": ENGINE_TAG,
            "lookback_days": days,
            "model_scores": {
                name: {
                    "score": round(m["score"], 1),
                    "level": m["level"],
                    "factors": m["factors"],
                }
                for name, m in result["model_scores"].items()
            },
            "top_factors": _top_factors(result["model_scores"]),
        }

        db.add(
            RiskScore(
                employee_id=emp.id,
                score=score,
                risk_level=level,
                breakdown=breakdown,
                calculated_at=calculated_at,
            )
        )
        created += 1
        latest[str(emp.id)] = {"score": score, "level": level.value}

    db.commit()

    distribution: Counter[str] = Counter(
        entry["level"] for entry in latest.values()
    )
    average = (
        round(mean(entry["score"] for entry in latest.values()), 1)
        if latest
        else 0
    )

    return {
        "calculated": created,
        "days": days,
        "average_score": average,
        "distribution": {
            "low": distribution.get("low", 0),
            "medium": distribution.get("medium", 0),
            "high": distribution.get("high", 0),
            "critical": distribution.get("critical", 0),
        },
        "message": f"Risk scores calculated for {created} employees",
    }


def _top_factors(model_scores: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten the highest-scoring individual factors across all models."""
    flattened: list[dict[str, Any]] = []
    for model_name, model in model_scores.items():
        for factor_name, factor in model.get("factors", {}).items():
            if not isinstance(factor, dict):
                continue
            score = factor.get("score", 0)
            if score > 0:
                flattened.append(
                    {
                        "model": model_name,
                        "factor": factor_name,
                        "score": round(score, 1),
                    }
                )
    flattened.sort(key=lambda f: f["score"], reverse=True)
    return flattened[:5]


# ── Risk Analytics ───────────────────────────────────────────────


def get_risk_analytics(
    db: Session, days: int = 30
) -> dict[str, Any]:
    """
    Organization-wide risk analytics.

    - Latest score per employee -> distribution, average, max, min
    - Daily average score trend over the last `days` days
    - Department-level risk breakdown
    - Top 10 risk contributors
    """
    latest = _latest_scores(db)
    if not latest:
        return {
            "average_score": 0,
            "max_score": 0,
            "min_score": 0,
            "total_employees_scored": 0,
            "distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "trend": [],
            "department_breakdown": [],
            "top_contributors": [],
        }

    scores = [r["score"] for r in latest]

    distribution: Counter[str] = Counter(r["level"].value for r in latest)

    return {
        "average_score": round(mean(scores), 1),
        "max_score": round(max(scores), 1),
        "min_score": round(min(scores), 1),
        "total_employees_scored": len(latest),
        "distribution": {
            "low": distribution.get("low", 0),
            "medium": distribution.get("medium", 0),
            "high": distribution.get("high", 0),
            "critical": distribution.get("critical", 0),
        },
        "trend": _risk_trend(db, days),
        "department_breakdown": _department_breakdown(db, latest),
        "top_contributors": sorted(
            [
                {
                    "id": str(r["employee_id"]),
                    "name": r["name"],
                    "department": r["department"],
                    "designation": r["designation"],
                    "risk_score": r["score"],
                    "risk_level": r["level"].value,
                    "breakdown": r["breakdown"],
                }
                for r in latest
            ],
            key=lambda r: r["risk_score"],
            reverse=True,
        )[:10],
    }


def _latest_scores(db: Session) -> list[dict[str, Any]]:
    """Latest RiskScore per employee, joined with employee metadata."""
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
            Employee.full_name,
            Employee.department,
            Employee.designation,
            subquery.c.score,
            subquery.c.risk_level,
            subquery.c.breakdown,
        )
        .join(subquery, Employee.id == subquery.c.employee_id)
        .all()
    )

    return [
        {
            "employee_id": r.id,
            "name": r.full_name,
            "department": r.department,
            "designation": r.designation,
            "score": round(float(r.score), 1),
            "level": r.risk_level,
            "breakdown": r.breakdown,
        }
        for r in rows
    ]


def _risk_trend(db: Session, days: int) -> list[dict[str, Any]]:
    """Average risk score per day over the lookback window."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            cast(RiskScore.calculated_at, Date).label("day"),
            func.avg(RiskScore.score).label("avg_score"),
        )
        .filter(RiskScore.calculated_at >= cutoff)
        .group_by(cast(RiskScore.calculated_at, Date))
        .order_by(cast(RiskScore.calculated_at, Date))
        .all()
    )

    return [
        {"date": str(row.day), "average_score": round(float(row.avg_score), 1)}
        for row in rows
    ]


def _department_breakdown(
    db: Session, latest: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Average latest score and high-risk count per department."""
    by_dept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in latest:
        by_dept[entry["department"] or "Unassigned"].append(entry)

    breakdown = []
    for dept, entries in by_dept.items():
        scores = [e["score"] for e in entries]
        high_risk = sum(
            1
            for e in entries
            if e["level"] in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        )
        breakdown.append(
            {
                "department": dept,
                "employees": len(entries),
                "average_score": round(mean(scores), 1),
                "max_score": round(max(scores), 1),
                "high_risk_count": high_risk,
            }
        )

    breakdown.sort(key=lambda d: d["average_score"], reverse=True)
    return breakdown
