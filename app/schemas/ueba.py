from pydantic import BaseModel


class UebaPipelineResult(BaseModel):
    baselines_computed: int
    employees_scanned: int
    employees_with_anomalies: int
    alerts_created: int
    risk_scores_calculated: int
    average_threat_score: float
    lookback_days: int
    ran_at: str
    message: str


class UebaOverviewItem(BaseModel):
    model_config = {"protected_namespaces": ()}

    employee_id: str
    employee_name: str
    employee_code: str
    department: str | None = None
    designation: str | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    threat_score: float | None = None
    threat_level: str | None = None
    model_scores: dict = {}
    open_anomaly_alerts: int = 0
    baseline_status: str = "missing"
    assessed_at: str | None = None


class UebaOverview(BaseModel):
    total_employees: int
    lookback_days: int
    generated_at: str
    items: list[UebaOverviewItem]


class UebaEmployeeOverview(UebaOverviewItem):
    generated_at: str
    lookback_days: int
