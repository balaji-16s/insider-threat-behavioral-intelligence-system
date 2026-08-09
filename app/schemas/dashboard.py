from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_employees: int
    total_alerts: int
    open_alerts: int
    critical_alerts: int
    total_incidents: int
    active_incidents: int
    total_activity_logs: int
    high_risk_employees: int
