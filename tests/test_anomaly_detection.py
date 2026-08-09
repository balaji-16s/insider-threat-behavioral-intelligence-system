"""Anomaly detection & threat assessment service tests."""

from datetime import datetime, timedelta
from uuid import uuid4

from app.models.activity_log import ActivityLog, ActivityType
from app.models.alert import Alert, AlertStatus
from app.models.employee import Employee
from app.services.anomaly_detection import run_anomaly_detection
from app.services.threat_detection import assess_employee_threat


def _make_employee(db, code="EMP001", name="Test Employee"):
    emp = Employee(
        employee_code=code,
        full_name=name,
        department="Engineering",
        designation="Engineer",
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def _log(db, emp, atype, hours_ago=1, **details):
    db.add(
        ActivityLog(
            employee_id=emp.id,
            activity_type=atype,
            source="test",
            details=details or {"pc": "PC-1"},
            occurred_at=datetime.utcnow() - timedelta(hours=hours_ago),
        )
    )


def test_off_hours_data_transfer_rule_fires(db):
    """>=3 off-hours data transfers should produce a HIGH anomaly + alert."""
    emp = _make_employee(db, "EMP-HI")
    # fix the clock to a guaranteed off-hours time (23:00 UTC)
    now = datetime.utcnow().replace(hour=23, minute=5, second=0, microsecond=0)
    for _ in range(4):
        db.add(
            ActivityLog(
                employee_id=emp.id,
                activity_type=ActivityType.DATA_TRANSFER,
                source="http",
                details={"pc": "PC-9", "url": "http://x.com"},
                occurred_at=now - timedelta(hours=2),  # 21:00 = still off-hours
            )
        )
    db.commit()

    result = run_anomaly_detection(db, employee_id=str(emp.id), days=30)
    # anomaly list should include the off-hours transfer rule
    types = {
        a["type"]
        for emp_item in result["details"]
        for a in emp_item["anomalies"]
    }
    assert "off_hours_data_transfer" in types
    assert result["alerts_created"] >= 1

    alerts = (
        db.query(Alert)
        .filter(Alert.employee_id == emp.id, Alert.status == AlertStatus.OPEN)
        .all()
    )
    assert any(a.anomaly_type == "off_hours_data_transfer" for a in alerts)


def test_quiet_employee_no_anomalies(db):
    """A user with weekday business-hours logins should have NO anomalies.
    Uses explicit weekday dates so the test is not clock/calendar dependent."""
    emp = _make_employee(db, "EMP-QUIET")
    dates = []
    d = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while len(dates) < 10:
        if d.weekday() < 5:  # Mon-Fri only
            dates.append(d)
        d -= timedelta(days=1)
    for dt in dates:
        db.add(
            ActivityLog(
                employee_id=emp.id,
                activity_type=ActivityType.LOGIN,
                source="test",
                details={"pc": "PC-1", "method": "mfa"},
                occurred_at=dt,
            )
        )
    db.commit()

    result = run_anomaly_detection(db, employee_id=str(emp.id), days=30)
    assert result["employees_with_anomalies"] == 0
    assert result["alerts_created"] == 0


def test_threat_assessment_scoring(db):
    emp = _make_employee(db, "EMP-THREAT")
    now = datetime.utcnow()
    # heavy off-hours exfiltration profile
    for i in range(6):
        db.add(
            ActivityLog(
                employee_id=emp.id,
                activity_type=ActivityType.DATA_TRANSFER,
                source="http",
                details={"pc": "PC-1", "destination": "external"},
                occurred_at=now - timedelta(hours=3 + i),
            )
        )
    db.commit()

    result = assess_employee_threat(db, str(emp.id), days=30)
    assert result["threat_score"] > 0
    assert "data_exfiltration" in result["model_scores"]
    assert result["model_scores"]["data_exfiltration"]["score"] > 0


def test_no_data_returns_zero_threat(db):
    emp = _make_employee(db, "EMP-NODATA")
    result = assess_employee_threat(db, str(emp.id), days=30)
    assert result["threat_score"] == 0
