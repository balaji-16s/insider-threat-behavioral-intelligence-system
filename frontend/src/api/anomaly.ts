import { api, LONG_REQUEST_TIMEOUT_MS } from './client';

export interface AnomalyDetectionRequest {
  employee_id?: string;
  days?: number;
}

export interface AnomalyItem {
  type: string;
  description: string;
  confidence: number;
  severity: string;
  evidence: Record<string, unknown>;
}

export interface EmployeeAnomalies {
  employee_id: string;
  employee_name: string;
  anomalies: AnomalyItem[];
}

export interface AnomalyDetectionResult {
  scanned_employees: number;
  employees_with_anomalies: number;
  alerts_created: number;
  details: EmployeeAnomalies[];
  generated_at?: string | null;
}

export interface AnomalySummaryItem {
  id: string;
  employee_id: string;
  title: string;
  anomaly_type: string;
  severity: string;
  created_at: string;
  evidence: Record<string, unknown>;
}

export interface BehavioralProfile {
  id?: string;
  employee_id: string;
  baseline_data: Record<string, unknown>;
  generated_at?: string;
  updated_at?: string;
}

export interface ThreatModelScore {
  score: number;
  level: string;
  factors: Record<string, unknown>;
}

export interface ThreatAssessmentResult {
  employee_id: string;
  threat_score: number;
  threat_level: string;
  model_scores: Record<string, ThreatModelScore>;
  assessed_at: string;
  lookback_days: number;
  employee_name?: string;
  department?: string;
}

export interface BaselineComputeResult {
  baselines_computed: number;
  message: string;
}

export interface MlFactor {
  feature: string;
  value: number;
  median: number;
  deviation: number;
}

export interface MlEmployeeScore {
  employee_id: string;
  employee_code: string;
  employee_name: string;
  department?: string | null;
  designation?: string | null;
  ml_score: number;
  is_outlier: boolean;
  severity: string;
  top_factors: MlFactor[];
  features: Record<string, number>;
}

export interface MlGroundTruthCheck {
  total_insiders: number;
  insiders_in_dataset: number;
  found_in_outliers: number;
  found_in_top20: number;
  hit_rate_top20?: number | null;
  note?: string | null;
  detected_insiders?: string[] | null;
}

export interface MlDetectionResult {
  model: string;
  version: string;
  contamination: number;
  lookback_days: number;
  scanned_employees: number;
  employees_no_activity?: number;
  outliers_detected: number;
  average_ml_score: number;
  top_flagged: MlEmployeeScore[];
  ground_truth?: MlGroundTruthCheck | null;
  model_trained_at?: string | null;
  generated_at: string;
  message: string;
}

export async function detectAnomalies(req: AnomalyDetectionRequest): Promise<AnomalyDetectionResult> {
  return api.post<AnomalyDetectionResult>('/anomaly/detect', req, LONG_REQUEST_TIMEOUT_MS);
}

export async function getLatestDetection(): Promise<AnomalyDetectionResult | null> {
  return api.get<AnomalyDetectionResult | null>('/anomaly/detect/latest');
}

export async function getAnomalyStats(): Promise<{ total_open: number; by_severity: Record<string, number> }> {
  return api.get('/anomaly/alerts/stats');
}

export async function runMlDetection(days = 30, contamination = 0.05, retrain = false): Promise<MlDetectionResult> {
  return api.post<MlDetectionResult>(
    `/anomaly/ml/detect?days=${days}&contamination=${contamination}&retrain=${retrain}`,
    undefined,
    LONG_REQUEST_TIMEOUT_MS
  );
}

export async function trainMlModel(days = 30, contamination = 0.05): Promise<MlDetectionResult> {
  return api.post<MlDetectionResult>(
    `/anomaly/ml/train?days=${days}&contamination=${contamination}`,
    undefined,
    LONG_REQUEST_TIMEOUT_MS
  );
}

export async function getMlResults(): Promise<MlDetectionResult | null> {
  return api.get<MlDetectionResult | null>('/anomaly/ml/results');
}

export async function listAnomalyAlerts(employee_id?: string): Promise<AnomalySummaryItem[]> {
  const query = employee_id ? `?employee_id=${employee_id}` : '';
  return api.get<AnomalySummaryItem[]>(`/anomaly/alerts${query}`);
}

export async function computeBaselines(employee_id?: string): Promise<BaselineComputeResult> {
  const query = employee_id ? `?employee_id=${employee_id}` : '';
  return api.post<BaselineComputeResult>(`/anomaly/baselines/compute${query}`);
}

export async function getBaseline(employee_id: string): Promise<BehavioralProfile> {
  return api.get<BehavioralProfile>(`/anomaly/baselines/${employee_id}`);
}

export async function assessThreat(employee_id?: string, days = 30): Promise<ThreatAssessmentResult | ThreatAssessmentResult[]> {
  const query = new URLSearchParams();
  if (employee_id) query.set('employee_id', employee_id);
  query.set('days', String(days));
  return api.post<ThreatAssessmentResult | ThreatAssessmentResult[]>(`/anomaly/threat/assess?${query.toString()}`);
}

export async function getTopThreats(limit = 20): Promise<ThreatAssessmentResult[]> {
  return api.get<ThreatAssessmentResult[]>(`/anomaly/threat/top?limit=${limit}`);
}

export async function getEmployeeThreat(employee_id: string, days = 30): Promise<ThreatAssessmentResult> {
  return api.get<ThreatAssessmentResult>(`/anomaly/threat/employee/${employee_id}?days=${days}`);
}
