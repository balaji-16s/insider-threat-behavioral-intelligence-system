import { api, downloadFile } from './client';

export interface AnomalyReport {
  generated_at: string;
  report_period_days: number;
  report_period: { start: string; end: string };
  summary: {
    total_employees: number;
    total_alerts: number;
    open_alerts: number;
    critical_alerts: number;
    total_incidents: number;
    total_activity_logs: number;
  };
  alerts: {
    total: number;
    by_severity: Record<string, number>;
    by_status: Record<string, number>;
    by_anomaly_type: Record<string, number>;
    trend: string;
  };
  incidents: {
    total: number;
    by_status: Record<string, number>;
    avg_resolution_hours: number | null;
    escalation_rate: number;
  };
  activity_trends: {
    daily_trends: { date: string; count: number }[];
    by_activity_type: Record<string, number>;
    peak_day: string | null;
  };
  risk_distribution: Record<string, number>;
  high_risk_employees: {
    id: string;
    name: string;
    department: string | null;
    designation: string | null;
    risk_score: number;
    risk_level: string;
    breakdown: Record<string, unknown>;
  }[];
  threat_assessment: {
    total_assessed: number;
    top_threats: Record<string, unknown>[];
    average_threat_score: number;
  } | null;
}

export interface EmployeeReport {
  employee: {
    id: string;
    name: string;
    department: string | null;
    designation: string | null;
  };
  report_period_days: number;
  generated_at: string;
  total_alerts: number;
  total_activity_logs: number;
  alert_severity_breakdown: Record<string, number>;
  alert_type_breakdown: Record<string, number>;
  latest_risk_score: { score: number; level: string; calculated_at: string } | null;
  threat_assessment: Record<string, unknown>;
}

export async function getAnomalyReport(days = 30, includeThreats = true): Promise<AnomalyReport> {
  return api.get<AnomalyReport>(`/reports/anomaly?days=${days}&include_threats=${includeThreats}`);
}

export async function getEmployeeReport(employeeId: string, days = 30): Promise<EmployeeReport> {
  return api.get<EmployeeReport>(`/reports/employee/${employeeId}?days=${days}`);
}

export async function downloadAnomalyReport(format: 'pdf' | 'xlsx', days = 30): Promise<void> {
  const filename = `itbis_anomaly_report_${days}d.${format}`;
  return downloadFile(`/reports/anomaly/${format}?days=${days}`, filename);
}

export async function downloadEmployeeReport(
  employeeId: string,
  format: 'pdf' | 'xlsx',
  days = 30
): Promise<void> {
  const filename = `itbis_employee_report.${format}`;
  return downloadFile(`/reports/employee/${employeeId}/${format}?days=${days}`, filename);
}
