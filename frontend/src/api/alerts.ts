import { api } from './client';

export interface Alert {
  id: string;
  employee_id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  anomaly_type: string | null;
  evidence: Record<string, unknown>;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
}

export async function listAlerts(params?: {
  status?: string;
  severity?: string;
  employee_id?: string;
  skip?: number;
  limit?: number;
}): Promise<Alert[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.severity) query.set('severity', params.severity);
  if (params?.employee_id) query.set('employee_id', params.employee_id);
  if (params?.skip) query.set('skip', String(params.skip));
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return api.get<Alert[]>(`/alerts${qs ? `?${qs}` : ''}`);
}

export async function updateAlert(id: string, data: { status?: string; assigned_to?: string }): Promise<Alert> {
  return api.patch<Alert>(`/alerts/${id}`, data);
}

export async function escalateAlert(alertId: string): Promise<unknown> {
  return api.post(`/alerts/${alertId}/escalate`);
}
