"""Report export (PDF/Excel) tests."""

from datetime import datetime, timedelta

from app.models.activity_log import ActivityLog, ActivityType
from app.models.employee import Employee
from app.services.report_export import (
    anomaly_report_pdf_bytes,
    anomaly_report_xlsx_bytes,
    employee_report_pdf_bytes,
    employee_report_xlsx_bytes,
)


def _seed(db):
    emp = Employee(employee_code="EXP-001", full_name="Export User", department="IT")
    db.add(emp)
    db.commit()
    db.refresh(emp)
    db.add(
        ActivityLog(
            employee_id=emp.id,
            activity_type=ActivityType.LOGIN,
            source="test",
            details={"pc": "PC-1"},
            occurred_at=datetime.utcnow() - timedelta(hours=2),
        )
    )
    db.commit()
    return emp


def test_anomaly_report_pdf(db):
    _seed(db)
    pdf = anomaly_report_pdf_bytes(db, days=30)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_anomaly_report_xlsx(db):
    _seed(db)
    xlsx = anomaly_report_xlsx_bytes(db, days=30)
    assert xlsx[:2] == b"PK"  # zip container
    assert len(xlsx) > 1000


def test_employee_report_pdf(db):
    emp = _seed(db)
    pdf = employee_report_pdf_bytes(db, str(emp.id), days=30)
    assert pdf[:4] == b"%PDF"


def test_employee_report_xlsx(db):
    emp = _seed(db)
    xlsx = employee_report_xlsx_bytes(db, str(emp.id), days=30)
    assert xlsx[:2] == b"PK"


def test_employee_report_missing_raises(db):
    import uuid

    try:
        employee_report_pdf_bytes(db, str(uuid.uuid4()), days=30)
        raise AssertionError("expected ValueError for missing employee")
    except ValueError:
        pass
