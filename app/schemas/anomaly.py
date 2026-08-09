from datetime import datetime
from pydantic import BaseModel
import uuid


class AnomalyDetectionRequest(BaseModel):
    employee_id: str | None = None
    days: int = 30


class AnomalyEvidence(BaseModel):
    class Config:
        extra = "allow"


class AnomalyItem(BaseModel):
    type: str
    description: str
    confidence: float
    severity: str
    evidence: dict


class EmployeeAnomalies(BaseModel):
    employee_id: str
    employee_name: str
    anomalies: list[AnomalyItem]


class AnomalyDetectionResult(BaseModel):
    scanned_employees: int
    employees_with_anomalies: int
    alerts_created: int
    details: list[EmployeeAnomalies]


class AnomalySummaryItem(BaseModel):
    id: str
    employee_id: str
    title: str
    anomaly_type: str
    severity: str
    created_at: str
    evidence: dict


class BehavioralProfile(BaseModel):
    id: str | None = None
    employee_id: str
    baseline_data: dict
    generated_at: str | None = None
    updated_at: str | None = None


class ThreatFactor(BaseModel):
    score: float | None = None
    count: int | None = None
    factors: dict | None = None

    class Config:
        extra = "allow"


class ThreatModelScore(BaseModel):
    score: float
    level: str
    factors: dict


class ThreatAssessmentResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    employee_id: str
    threat_score: float
    threat_level: str
    model_scores: dict[str, ThreatModelScore]
    assessed_at: str
    lookback_days: int
    employee_name: str | None = None
    department: str | None = None


class BaselineComputeResult(BaseModel):
    baselines_computed: int
    message: str


class ThreatAssessmentListResult(BaseModel):
    total: int
    average_threat_score: float
    top_threats: list[dict]


class AnomalyReport(BaseModel):
    generated_at: str
    report_period_days: int
    report_period: dict
    summary: dict
    alerts: dict
    incidents: dict
    activity_trends: dict
    risk_distribution: dict
    high_risk_employees: list[dict]
    threat_assessment: dict | None = None


class EmployeeReport(BaseModel):
    employee: dict
    report_period_days: int
    generated_at: str
    total_alerts: int
    total_activity_logs: int
    alert_severity_breakdown: dict
    alert_type_breakdown: dict
    latest_risk_score: dict | None
    threat_assessment: dict


# ── ML Anomaly Detection (Isolation Forest) ─────────────────────


class MlFactor(BaseModel):
    feature: str
    value: float
    median: float
    deviation: float


class MlEmployeeScore(BaseModel):
    employee_id: str
    employee_code: str
    employee_name: str
    department: str | None = None
    designation: str | None = None
    ml_score: float
    is_outlier: bool
    severity: str
    top_factors: list[MlFactor]
    features: dict


class MlGroundTruthCheck(BaseModel):
    total_insiders: int
    insiders_in_dataset: int
    found_in_outliers: int
    found_in_top20: int
    hit_rate_top20: float | None = None
    note: str | None = None
    detected_insiders: list[str] | None = None


class MlDetectionResult(BaseModel):
    model: str
    version: str
    contamination: float
    lookback_days: int
    scanned_employees: int
    employees_no_activity: int = 0
    outliers_detected: int
    average_ml_score: float
    top_flagged: list[MlEmployeeScore]
    ground_truth: MlGroundTruthCheck | None = None
    generated_at: str
    message: str
