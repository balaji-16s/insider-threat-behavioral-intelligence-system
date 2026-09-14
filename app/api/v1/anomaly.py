from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from app.db.base import get_db
from app.core.deps import require_role, require_staff
from app.models.user import User
from app.models.employee import Employee

from app.schemas.anomaly import (
    AnomalyDetectionRequest,
    AnomalyDetectionResult,
    AnomalySummaryItem,
    BehavioralProfile,
    ThreatAssessmentResult,
    BaselineComputeResult,
    MlDetectionResult,
)
from app.services.ml_anomaly_detection import (
    run_ml_anomaly_detection,
    get_cached_ml_results,
)
from app.services.anomaly_detection import (
    run_anomaly_detection,
    get_anomaly_summary,
    get_anomaly_stats,
    get_cached_detection_results,
)
from app.services.behavioral_profiling import (
    compute_baseline,
    compute_all_baselines,
    get_employee_profile,
    store_baseline,
)
from app.services.threat_detection import (
    assess_employee_threat,
    assess_all_employees,
    get_top_threats,
)

router = APIRouter(prefix="/api/v1/anomaly", tags=["Anomaly Detection"])


@router.post("/ml/detect", response_model=MlDetectionResult)
def ml_detect(
    days: int = Query(30, ge=7, le=365),
    contamination: float = Query(0.05, ge=0.01, le=0.30),
    retrain: bool = Query(False, description="Force re-fitting the model before scoring"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Score all employees with the trained Isolation Forest model.

    Uses the persisted model (see scripts/train_ml_model.py) unless
    ``retrain`` is set or no model has been trained yet.
    """
    return run_ml_anomaly_detection(
        db, days=days, contamination=contamination, retrain=retrain
    )


@router.post("/ml/train", response_model=MlDetectionResult)
def ml_train(
    days: int = Query(30, ge=7, le=365),
    contamination: float = Query(0.05, ge=0.01, le=0.30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager")),
):
    """Retrain the Isolation Forest model from current data, persist it, then score."""
    return run_ml_anomaly_detection(
        db, days=days, contamination=contamination, retrain=True
    )


@router.get("/ml/results", response_model=MlDetectionResult | None)
def ml_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Return the most recent ML anomaly detection run (cached)."""
    return get_cached_ml_results()


@router.post("/detect", response_model=AnomalyDetectionResult)
def detect_anomalies(
    req: AnomalyDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Run the anomaly detection pipeline. Optionally scope to an employee."""
    result = run_anomaly_detection(db, req.employee_id, req.days)
    return AnomalyDetectionResult(**result)


@router.get("/alerts", response_model=list[AnomalySummaryItem])
def list_anomaly_alerts(
    employee_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List open anomaly alerts."""
    return get_anomaly_summary(db, employee_id)


@router.get("/alerts/stats")
def anomaly_alerts_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Real totals of open anomaly alerts (not capped like the list)."""
    return get_anomaly_stats(db)


@router.get("/detect/latest", response_model=AnomalyDetectionResult | None)
def latest_detection(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Return the most recent anomaly detection run (persisted)."""
    return get_cached_detection_results()


@router.post("/baselines/compute", response_model=BaselineComputeResult)
def compute_baselines(
    employee_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "security_manager")),
):
    """Compute or recompute behavioral baselines for all employees or a specific one."""
    if employee_id:
        data = compute_baseline(db, employee_id)
        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])
        store_baseline(db, employee_id, data)
        db.commit()
        return BaselineComputeResult(
            baselines_computed=1,
            message="Baseline computed and stored successfully",
        )
    count = compute_all_baselines(db)
    return BaselineComputeResult(
        baselines_computed=count,
        message=f"Baselines recomputed for {count} employees",
    )


@router.get("/baselines/{employee_id}", response_model=BehavioralProfile)
def get_baseline(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get the behavioral baseline/profile for an employee."""
    profile = get_employee_profile(db, employee_id)
    if "error" in profile.get("baseline_data", {}):
        raise HTTPException(status_code=404, detail=profile["baseline_data"]["error"])
    return profile


@router.post("/threat/assess")
def assess_threat(
    employee_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Assess insider threat level for an employee or all employees."""
    if employee_id:
        result = assess_employee_threat(db, employee_id, days)
        return result
    else:
        all_results = assess_all_employees(db, days)
        return all_results


@router.get("/threat/top", response_model=list[ThreatAssessmentResult])
def top_threats(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get the top threats across the organization."""
    results = get_top_threats(db, limit)
    return [ThreatAssessmentResult(**r) for r in results]


@router.get("/threat/employee/{employee_id}", response_model=ThreatAssessmentResult)
def employee_threat(
    employee_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get detailed threat assessment for a specific employee."""
    result = assess_employee_threat(db, employee_id, days)
    return ThreatAssessmentResult(**result)
