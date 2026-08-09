import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.risk_score import RiskLevel


class RiskScoreOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    score: float
    risk_level: RiskLevel
    breakdown: dict
    calculated_at: datetime

    class Config:
        from_attributes = True


class RiskScoreCalculateResult(BaseModel):
    calculated: int
    days: int
    average_score: float
    distribution: dict
    message: str


class RiskTrendPoint(BaseModel):
    date: str
    average_score: float


class DepartmentRisk(BaseModel):
    department: str
    employees: int
    average_score: float
    max_score: float
    high_risk_count: int


class RiskAnalytics(BaseModel):
    average_score: float
    max_score: float
    min_score: float
    total_employees_scored: int
    distribution: dict
    trend: list[RiskTrendPoint]
    department_breakdown: list[DepartmentRisk]
    top_contributors: list[dict]
