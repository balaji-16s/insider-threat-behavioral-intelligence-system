"""Risk scoring engine tests."""

from datetime import datetime, timedelta

from app.models.activity_log import ActivityLog, ActivityType
from app.models.employee import Employee
from app.models.risk_score import RiskScore
from app.services.risk_scoring import calculate_risk_scores, get_risk_analytics


def _seed(db, code="RS-001", transfers=0):
    emp = Employee(employee_code=code, full_name="Risk User", department="Finance")
    db.add(emp)
    db.commit()
    db.refresh(emp)
    now = datetime.utcnow()
    for _ in range(transfers):
        db.add(
            ActivityLog(
                employee_id=emp.id,
                activity_type=ActivityType.DATA_TRANSFER,
                source="http",
                details={"pc": "PC-1"},
                occurred_at=now - timedelta(hours=1),
            )
        )
    db.commit()
    return emp


def test_calculate_persists_scores(db):
    _seed(db, "RS-001", transfers=3)
    result = calculate_risk_scores(db, days=30)
    assert result["calculated"] == 1
    assert result["average_score"] > 0

    scores = db.query(RiskScore).all()
    assert len(scores) == 1
    assert scores[0].score > 0
    assert "engine" in scores[0].breakdown


def test_recalculate_replaces_engine_scores(db):
    """Re-running the engine replaces the previous engine score (no duplicates)."""
    emp = _seed(db, "RS-002", transfers=2)
    calculate_risk_scores(db, days=30)
    calculate_risk_scores(db, days=30)
    ids = [r.id for r in db.query(RiskScore).all()]
    assert len(ids) == 1  # replaced, not duplicated


def test_risk_analytics_returns_distribution(db):
    _seed(db, "RS-003", transfers=5)
    calculate_risk_scores(db, days=30)
    analytics = get_risk_analytics(db, days=30)
    assert analytics["total_employees_scored"] == 1
    assert "distribution" in analytics
    assert "trend" in analytics
    assert "top_contributors" in analytics
    assert analytics["top_contributors"][0]["risk_score"] > 0
