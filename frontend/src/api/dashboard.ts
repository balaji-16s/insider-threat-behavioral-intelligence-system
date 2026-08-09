import { api } from './client';

export interface DashboardStats {
  total_employees: number;
  total_alerts: number;
  open_alerts: number;
  critical_alerts: number;
  total_incidents: number;
  active_incidents: number;
  total_activity_logs: number;
  high_risk_employees: number;
}

export interface ActivityTrend {
  date: string;
  count: number;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return api.get<DashboardStats>('/dashboard/stats');
}

export async function getActivityTrends(): Promise<ActivityTrend[]> {
  return api.get<ActivityTrend[]>('/dashboard/activity-trends');
}

export async function getRecentAlerts(): Promise<unknown[]> {
  return api.get('/dashboard/recent-alerts');
}
