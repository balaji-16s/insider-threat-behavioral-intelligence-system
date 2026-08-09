import { api } from './client';

export interface Incident {
  id: string;
  employee_id: string;
  title: string;
  status: string;
  related_alert_ids: string[];
  timeline: unknown[];
  assigned_analyst_id: string | null;
  created_at: string;
  closed_at: string | null;
}

export async function listIncidents(params?: {
  status?: string;
  employee_id?: string;
  skip?: number;
  limit?: number;
}): Promise<Incident[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.employee_id) query.set('employee_id', params.employee_id);
  if (params?.skip) query.set('skip', String(params.skip));
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return api.get<Incident[]>(`/incidents${qs ? `?${qs}` : ''}`);
}

export async function getIncident(id: string): Promise<Incident> {
  return api.get<Incident>(`/incidents/${id}`);
}

export async function updateIncident(id: string, data: { status?: string; timeline?: unknown[] }): Promise<Incident> {
  return api.patch<Incident>(`/incidents/${id}`, data);
}

export async function addTimelineEvent(
  id: string,
  data: { event: string; note?: string }
): Promise<Incident> {
  return api.post<Incident>(`/incidents/${id}/timeline`, data);
}

export async function getRelatedAlerts(id: string): Promise<unknown[]> {
  return api.get<unknown[]>(`/incidents/${id}/related-alerts`);
}
