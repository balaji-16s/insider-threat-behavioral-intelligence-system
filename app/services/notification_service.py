import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.request
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


def send_notification(
    db: Session,
    notification_type: NotificationType,
    subject: str,
    message: str,
    recipient: Optional[str] = None,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    metadata_info: Optional[Dict[str, Any]] = None,
) -> Notification:
    """
    Create and dispatch a notification via the requested channel (Email, Webhook, In-App).
    Persists the notification record to DB for audit and compliance.
    """
    status = NotificationStatus.SENT

    # Dispatch via Email if configured and channel is email
    if channel == NotificationChannel.EMAIL and settings.smtp_host and recipient:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.smtp_from_email
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as server:
                if settings.smtp_user and settings.smtp_password:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            logger.info(f"Email notification sent to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            status = NotificationStatus.FAILED

    # Dispatch via Webhook if configured and channel is webhook
    elif channel == NotificationChannel.WEBHOOK and settings.webhook_url:
        try:
            payload = json.dumps({
                "notification_type": notification_type.value,
                "subject": subject,
                "message": message,
                "recipient": recipient,
                "metadata": metadata_info or {},
            }).encode("utf-8")

            req = urllib.request.Request(
                settings.webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                logger.info(f"Webhook notification delivered with status {response.status}")
        except Exception as e:
            logger.error(f"Failed to deliver webhook notification: {e}")
            status = NotificationStatus.FAILED

    notification = Notification(
        notification_type=notification_type,
        channel=channel,
        recipient=recipient or "soc-team@organization.internal",
        subject=subject,
        message=message,
        status=status,
        metadata_info=metadata_info or {},
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def notify_threat_alert(
    db: Session,
    alert_title: str,
    severity: str,
    employee_name: str,
    anomaly_type: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> Notification:
    """Send notification for new threat alerts."""
    subject = f"[{severity.upper()}] Insider Threat Alert: {alert_title}"
    message = (
        f"Security Alert Triggered:\n"
        f"- Target Employee: {employee_name}\n"
        f"- Severity: {severity.upper()}\n"
        f"- Anomaly Type: {anomaly_type or 'N/A'}\n"
        f"- Description: {alert_title}\n"
    )
    channel = NotificationChannel.WEBHOOK if settings.webhook_url else NotificationChannel.IN_APP
    return send_notification(
        db=db,
        notification_type=NotificationType.THREAT_ALERT,
        subject=subject,
        message=message,
        recipient="soc-analysts@organization.internal",
        channel=channel,
        metadata_info={"employee_name": employee_name, "severity": severity, "evidence": evidence},
    )


def notify_escalation(
    db: Session,
    incident_id: str,
    incident_title: str,
    assigned_analyst: Optional[str] = None,
) -> Notification:
    """Send notification when an alert is escalated into an incident."""
    subject = f"[ESCALATED] Threat Incident #{incident_id[:8]}: {incident_title}"
    message = (
        f"An alert has been escalated to a formal investigation incident.\n"
        f"- Incident ID: {incident_id}\n"
        f"- Title: {incident_title}\n"
        f"- Assigned Analyst: {assigned_analyst or 'Unassigned'}\n"
    )
    channel = NotificationChannel.EMAIL if settings.smtp_host else NotificationChannel.IN_APP
    return send_notification(
        db=db,
        notification_type=NotificationType.INVESTIGATION_ESCALATION,
        subject=subject,
        message=message,
        recipient=assigned_analyst or "security-manager@organization.internal",
        channel=channel,
        metadata_info={"incident_id": incident_id, "title": incident_title},
    )


def get_notifications(
    db: Session,
    limit: int = 50,
    notification_type: Optional[NotificationType] = None,
) -> List[Notification]:
    """List recent notifications."""
    query = db.query(Notification)
    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()
