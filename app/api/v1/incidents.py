from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime

from app.db.base import get_db
from app.models.incident import Incident
from app.models.employee import Employee
from app.models.alert import Alert
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentOut,
    TimelineEventIn,
)
from app.schemas.alert import AlertOut
from app.core.deps import require_role, require_staff
from app.models.user import User

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    status: Optional[str] = Query(None),
    employee_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    query = db.query(Incident)
    if status:
        query = query.filter(Incident.status == status)
    if employee_id:
        query = query.filter(Incident.employee_id == employee_id)
    return query.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager")),
):
    employee = db.query(Employee).filter(Employee.id == incident_in.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    incident = Incident(
        employee_id=incident_in.employee_id,
        title=incident_in.title,
        related_alert_ids=incident_in.related_alert_ids,
        assigned_analyst_id=incident_in.assigned_analyst_id,
        timeline=[{"event": "Incident created", "timestamp": datetime.utcnow().isoformat()}],
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: uuid.UUID,
    incident_in: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager", "soc_engineer")),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    update_data = incident_in.model_dump(exclude_unset=True)

    # Audit: record status transitions on the incident timeline
    new_status = update_data.get("status")
    if new_status and new_status != incident.status:
        # Preserve a caller-provided timeline if given, otherwise the existing one
        timeline = list(update_data.get("timeline") or incident.timeline or [])
        timeline.append(
            {
                "event": f"Status changed from {incident.status.value} to {new_status.value}",
                "timestamp": datetime.utcnow().isoformat(),
                "by": current_user.full_name,
            }
        )
        if new_status.value == "closed" and incident.closed_at is None:
            update_data["closed_at"] = datetime.utcnow()
            timeline.append(
                {
                    "event": "Incident closed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "by": current_user.full_name,
                }
            )
        update_data["timeline"] = timeline

    for field, value in update_data.items():
        setattr(incident, field, value)
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/timeline", response_model=IncidentOut)
def add_timeline_event(
    incident_id: uuid.UUID,
    event_in: TimelineEventIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager", "soc_engineer")),
):
    """Append an investigation note/action to the incident timeline."""
    if not event_in.event or not event_in.event.strip():
        raise HTTPException(status_code=422, detail="Event description is required")

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    timeline = list(incident.timeline or [])
    timeline.append(
        {
            "event": event_in.event,
            "note": event_in.note,
            "timestamp": datetime.utcnow().isoformat(),
            "by": current_user.full_name,
        }
    )
    incident.timeline = timeline
    db.commit()
    db.refresh(incident)
    return incident


@router.get("/{incident_id}/related-alerts", response_model=list[AlertOut])
def get_related_alerts(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Resolve the alerts that triggered (or are linked to) this incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    alert_ids = [a for a in (incident.related_alert_ids or []) if a]
    if not alert_ids:
        return []

    alerts = (
        db.query(Alert)
        .filter(Alert.id.in_(alert_ids))
        .all()
    )
    return alerts
