import { api } from './client';

export interface ActivityLog {
  id: string;
  employee_id: string;
  activity_type: string;
  source: string | null;
  details: Record<string, unknown>;
  occurred_at: string;
  ingested_at: string;
}

export async function listActivityLogs(params?: {
  employee_id?: string;
  activity_type?: string;
  source?: string;
  from_date?: string;
  to_date?: string;
  skip?: number;
  limit?: number;
}): Promise<ActivityLog[]> {
  const query = new URLSearchParams();
  if (params?.employee_id) query.set('employee_id', params.employee_id);
  if (params?.activity_type) query.set('activity_type', params.activity_type);
  if (params?.source) query.set('source', params.source);
  if (params?.from_date) query.set('from_date', params.from_date);
  if (params?.to_date) query.set('to_date', params.to_date);
  if (params?.skip) query.set('skip', String(params.skip));
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return api.get<ActivityLog[]>(`/activity-logs${qs ? `?${qs}` : ''}`);
}
