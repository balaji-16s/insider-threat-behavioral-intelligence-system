"""ML anomaly detection (Isolation Forest) tests."""

import random
from datetime import datetime, timedelta

from app.models.activity_log import ActivityLog, ActivityType
from app.models.employee import Employee
from app.services import ml_anomaly_detection


def _seed_population(db):
    """
    40 realistic-but-normal employees + 2 genuinely anomalous ones
    (heavy off-hours USB/data exfiltration). Normal employees must have
    realistic variance — Isolation Forest cannot split identical points.
    """
    rng = random.Random(42)
    now = datetime.utcnow()
    # the LAST two employees are the seeded insiders (codes exist!)
    anomalous = {"USR-040", "USR-041"}
    for i in range(42):
        code = f"USR-{i:03d}"
        is_bad = code in anomalous
        emp = Employee(
            employee_code=code,
            full_name=f"User {i}",
            department="Engineering",
            designation="Engineer",
        )
        db.add(emp)
        db.flush()

        for day in range(5):
            n = rng.randint(2, 6) if not is_bad else 8
            for _ in range(n):
                if is_bad:
                    hour = rng.choice([2, 3, 4])
                    atype = (
                        ActivityType.USB_DEVICE
                        if rng.random() < 0.5
                        else ActivityType.DATA_TRANSFER
                    )
                else:
                    hour = rng.randint(9, 17)
                    atype = ActivityType.LOGIN
                occurred = (
                    now.replace(hour=hour, minute=0, second=0, microsecond=0)
                    - timedelta(days=day + 1)
                )
                db.add(
                    ActivityLog(
                        employee_id=emp.id,
                        activity_type=atype,
                        source="test",
                        details={"pc": f"PC-{i}"},
                        occurred_at=occurred,
                    )
                )
    db.commit()
    return anomalous


def test_ml_engine_flags_anomalous_employees(db, monkeypatch, tmp_path):
    # point the results cache at a temp file so the real cache is untouched
    monkeypatch.setattr(ml_anomaly_detection, "RESULTS_CACHE", tmp_path / "ml.json")
    anomalous = _seed_population(db)

    result = ml_anomaly_detection.run_ml_anomaly_detection(db, days=30, contamination=0.05)

    assert result["scanned_employees"] == 42
    assert result["outliers_detected"] >= 1
    assert result["model"] == "Isolation Forest"

    # the most anomalous employee should be one of our seeded outliers
    top_code = result["top_flagged"][0]["employee_code"]
    assert top_code in anomalous

    # results were cached
    assert (tmp_path / "ml.json").exists()


def test_ml_engine_excludes_no_activity(db, monkeypatch, tmp_path):
    monkeypatch.setattr(ml_anomaly_detection, "RESULTS_CACHE", tmp_path / "ml.json")
    # one employee with NO logs in the window
    db.add(Employee(employee_code="SLEEPER", full_name="No Activity"))
    db.commit()

    result = ml_anomaly_detection.run_ml_anomaly_detection(db, days=30, contamination=0.05)
    assert result["scanned_employees"] == 0
    assert result["employees_no_activity"] == 1


def test_ml_scores_range_zero_to_hundred(db, monkeypatch, tmp_path):
    monkeypatch.setattr(ml_anomaly_detection, "RESULTS_CACHE", tmp_path / "ml.json")
    _seed_population(db)
    result = ml_anomaly_detection.run_ml_anomaly_detection(db, days=30, contamination=0.05)
    for item in result["top_flagged"]:
        assert 0.0 <= item["ml_score"] <= 100.0
