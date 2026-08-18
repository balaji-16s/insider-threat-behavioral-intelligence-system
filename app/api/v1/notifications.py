from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.notification import NotificationType
from app.schemas.notification import NotificationOut, NotificationCreate
from app.services.notification_service import (
    get_notifications,
    send_notification,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationOut])
def list_notifications_endpoint(
    limit: int = Query(50, ge=1, le=200),
    notification_type: Optional[NotificationType] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List system notifications (threat alerts, escalations, compliance updates)."""
    return get_notifications(db, limit=limit, notification_type=notification_type)


@router.post("/send", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def send_notification_endpoint(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually dispatch a security event or compliance notification."""
    return send_notification(
        db=db,
        notification_type=payload.notification_type,
        subject=payload.subject,
        message=payload.message,
        recipient=payload.recipient,
        channel=payload.channel,
        metadata_info=payload.metadata_info,
    )
