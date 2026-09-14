import { api } from './client';

/**
 * Worker (employee) portal API.
 *
 * Every endpoint is scoped server-side to the employee linked to the
 * logged-in account, so none of these calls take an employee id.
 */

export interface WorkerEmployee {
  id: string;
  employee_code: string;
  full_name: string;
  department: string | null;
  designation: string | null;
  manager_name: string | null;
  access_privileges: string[];
}

export interface RiskComparison {
  percentile: number | null;
  peers_scored: number;
  org_average: number;
  org_max: number;
}

export interface DepartmentComparison {
  department: string | null;
  average: number | null;
  size: number;
  your_rank?: number;
}

export interface RiskHistoryPoint {
  score: number;
  level: string;
  calculated_at: string | null;
}

export interface ThreatFactor {
  score: number;
  value: number;
  metric: string;
  severity: number;
  peer_median?: number;
  peer_p95?: number;
  excess_over_peer_median?: number;
}

export interface ThreatModel {
  score: number;
  level: string;
  factors: Record<string, ThreatFactor>;
}

export interface ThreatReason {
  model: string;
  factor: string;
  metric: string | null;
  score: number;
  value: number | null;
  peer_median: number | null;
  peer_p95: number | null;
}

export interface WorkerAlert {
  id: string;
  title: string;
  description: string;
  severity: string;
  anomaly_type: string | null;
  created_at: string | null;
  evidence: Record<string, unknown>;
}

export interface ActivityTypeCount {
  type: string;
  label: string;
  count: number;
}

export interface ActivityDay {
  date: string;
  count: number;
}

export interface WorkerOverview {
  employee: WorkerEmployee;
  risk: {
    score: number | null;
    level: string | null;
    calculated_at: string | null;
    comparison: RiskComparison | null;
    department: DepartmentComparison | null;
    history: RiskHistoryPoint[];
  };
  threat: {
    score: number;
    level: string;
    model_scores: Record<string, ThreatModel>;
    reasons: ThreatReason[];
    scoring_mode: string;
    cohort_size: number;
  };
  alerts: { open_count: number; items: WorkerAlert[] };
  activity: {
    total_events: number;
    by_type: ActivityTypeCount[];
    daily: ActivityDay[];
    off_hours_events: number;
    weekend_events: number;
    unique_workstations: number;
    active_days: number;
  };
  baseline: { status: string; daily_avg: number | null };
  lookback_days: number;
  generated_at: string;
}

export interface WorkerActivityItem {
  id: string;
  activity_type: string;
  label: string;
  source: string | null;
  details: Record<string, unknown> | null;
  occurred_at: string | null;
}

export interface WorkerActivityPage {
  total: number;
  skip: number;
  limit: number;
  items: WorkerActivityItem[];
}

export async function getWorkerOverview(days = 30): Promise<WorkerOverview> {
  return api.get<WorkerOverview>(`/worker/me/overview?days=${days}`);
}

export async function getWorkerActivity(params?: {
  activity_type?: string;
  skip?: number;
  limit?: number;
}): Promise<WorkerActivityPage> {
  const query = new URLSearchParams();
  if (params?.activity_type) query.set('activity_type', params.activity_type);
  if (params?.skip) query.set('skip', String(params.skip));
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return api.get<WorkerActivityPage>(`/worker/me/activity${qs ? `?${qs}` : ''}`);
}

export async function getWorkerActivityTypes(): Promise<{ type: string; label: string }[]> {
  return api.get<{ type: string; label: string }[]>('/worker/me/activity-types');
}
