import { api } from './client';

export interface RiskScore {
  employee_id: string;
  id: string;
  score: number;
  risk_level: string;
  breakdown: Record<string, unknown>;
  calculated_at: string;
}

export async function listRiskScores(params?: {
  employee_id?: string;
  risk_level?: string;
  limit?: number;
}): Promise<RiskScore[]> {
  const query = new URLSearchParams();
  if (params?.employee_id) query.set('employee_id', params.employee_id);
  if (params?.risk_level) query.set('risk_level', params.risk_level);
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return api.get<RiskScore[]>(`/risk-scores${qs ? `?${qs}` : ''}`);
}

export async function getRiskDistribution(): Promise<Record<string, number>> {
  return api.get<Record<string, number>>('/risk-scores/distribution');
}

export async function getRiskScoreHistory(employeeId: string, limit = 100): Promise<RiskScore[]> {
  return api.get<RiskScore[]>(`/risk-scores/history/${employeeId}?limit=${limit}`);
}

export interface RiskTrendPoint {
  date: string;
  average_score: number;
}

export interface DepartmentRisk {
  department: string;
  employees: number;
  average_score: number;
  max_score: number;
  high_risk_count: number;
}

export interface RiskAnalytics {
  average_score: number;
  max_score: number;
  min_score: number;
  total_employees_scored: number;
  distribution: Record<string, number>;
  trend: RiskTrendPoint[];
  department_breakdown: DepartmentRisk[];
  top_contributors: {
    id: string;
    name: string;
    department: string | null;
    designation: string | null;
    risk_score: number;
    risk_level: string;
    breakdown: Record<string, unknown>;
  }[];
}

export interface RiskScoreCalculateResult {
  calculated: number;
  days: number;
  average_score: number;
  distribution: Record<string, number>;
  message: string;
}

export async function calculateRiskScores(days = 30): Promise<RiskScoreCalculateResult> {
  return api.post<RiskScoreCalculateResult>(`/risk-scores/calculate?days=${days}`);
}

export async function getRiskAnalytics(days = 30): Promise<RiskAnalytics> {
  return api.get<RiskAnalytics>(`/risk-scores/analytics?days=${days}`);
}
