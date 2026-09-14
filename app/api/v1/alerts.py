from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.db.base import get_db
from app.models.alert import Alert
from app.models.employee import Employee
from app.models.incident import Incident
from app.schemas.alert import AlertCreate, AlertUpdate, AlertOut
from app.schemas.incident import IncidentOut
from app.core.deps import require_role, require_staff
from app.models.user import User
from app.services.notification_service import notify_escalation

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    employee_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if employee_id:
        query = query.filter(Alert.employee_id == employee_id)
    return query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert_in: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager", "soc_engineer")),
):
    employee = db.query(Employee).filter(Employee.id == alert_in.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    alert = Alert(**alert_in.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert(
    alert_id: uuid.UUID,
    alert_in: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    for field, value in alert_in.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/{alert_id}/escalate", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def escalate_alert_to_incident(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager", "soc_engineer")),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "acknowledged"
    incident = Incident(
        employee_id=alert.employee_id,
        title=f"Escalated: {alert.title}",
        related_alert_ids=[str(alert.id)],
        assigned_analyst_id=alert.assigned_to,
        timeline=[{"event": "Alert escalated to incident", "alert_id": str(alert.id)}],
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    try:
        notify_escalation(
            db=db,
            incident_id=str(incident.id),
            incident_title=incident.title,
            assigned_analyst=str(incident.assigned_analyst_id) if incident.assigned_analyst_id else None,
        )
    except Exception:
        pass

    return incident
