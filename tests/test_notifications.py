import pytest
from app.models.notification import Notification, NotificationType, NotificationChannel, NotificationStatus
from app.services.notification_service import (
    send_notification,
    notify_threat_alert,
    notify_escalation,
    get_notifications,
)


def test_send_notification_creates_db_record(db):
    notif = send_notification(
        db=db,
        notification_type=NotificationType.THREAT_ALERT,
        subject="Test High Threat Alert",
        message="Employee EMP001 triggered exfiltration anomaly",
        recipient="analyst@corp.local",
        channel=NotificationChannel.IN_APP,
    )
    assert notif.id is not None
    assert notif.notification_type == NotificationType.THREAT_ALERT
    assert notif.status == NotificationStatus.SENT
    assert notif.subject == "Test High Threat Alert"

    # Verify queryable in db
    fetched = get_notifications(db, limit=10)
    assert len(fetched) >= 1
    assert fetched[0].subject == "Test High Threat Alert"


def test_notify_threat_alert_helper(db):
    notif = notify_threat_alert(
        db=db,
        alert_title="Off-Hours Data Transfer Detected",
        severity="high",
        employee_name="John Doe",
        anomaly_type="off_hours_data_transfer",
    )
    assert "John Doe" in notif.message
    assert notif.notification_type == NotificationType.THREAT_ALERT


def test_notify_escalation_helper(db):
    notif = notify_escalation(
        db=db,
        incident_id="inc-12345-abc",
        incident_title="Escalated: Data Leakage",
        assigned_analyst="analyst_jane",
    )
    assert "inc-12345-abc" in notif.message
    assert notif.notification_type == NotificationType.INVESTIGATION_ESCALATION


def test_notifications_api_endpoint(client, auth_headers):
    headers = auth_headers()
    response = client.get("/api/v1/notifications", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_send_custom_notification_api(client, auth_headers):
    headers = auth_headers()
    payload = {
        "notification_type": "compliance_alert",
        "channel": "in_app",
        "recipient": "compliance@corp.local",
        "subject": "Quarterly Compliance Audit",
        "message": "Audit completed with 0 policy violations.",
    }
    response = client.post("/api/v1/notifications/send", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["subject"] == "Quarterly Compliance Audit"
    assert data["notification_type"] == "compliance_alert"
