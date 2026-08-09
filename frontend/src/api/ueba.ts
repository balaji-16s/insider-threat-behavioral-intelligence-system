import { api } from './client';

export interface UebaPipelineResult {
  baselines_computed: number;
  employees_scanned: number;
  employees_with_anomalies: number;
  alerts_created: number;
  risk_scores_calculated: number;
  average_threat_score: number;
  lookback_days: number;
  ran_at: string;
  message: string;
}

export interface ThreatModelScore {
  score: number;
  level: string;
  factors: Record<string, unknown>;
}

export interface UebaOverviewItem {
  employee_id: string;
  employee_name: string;
  employee_code: string;
  department: string | null;
  designation: string | null;
  risk_score: number | null;
  risk_level: string | null;
  threat_score: number | null;
  threat_level: string | null;
  model_scores: Record<string, ThreatModelScore>;
  open_anomaly_alerts: number;
  baseline_status: string;
  assessed_at: string | null;
}

export interface UebaOverview {
  total_employees: number;
  lookback_days: number;
  generated_at: string;
  items: UebaOverviewItem[];
}

export async function runUebaPipeline(days = 30, employeeId?: string): Promise<UebaPipelineResult> {
  const query = new URLSearchParams();
  query.set('days', String(days));
  if (employeeId) query.set('employee_id', employeeId);
  return api.post<UebaPipelineResult>(`/ueba/pipeline?${query.toString()}`);
}

export async function getUebaOverview(days = 30, limit = 100): Promise<UebaOverview> {
  return api.get<UebaOverview>(`/ueba/overview?days=${days}&limit=${limit}`);
}
