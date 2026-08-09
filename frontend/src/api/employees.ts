import { api } from './client';

export interface Employee {
  id: string;
  employee_code: string;
  full_name: string;
  department: string | null;
  designation: string | null;
  manager_name: string | null;
  device_info: Record<string, unknown>;
  access_privileges: string[];
  created_at: string;
  updated_at: string;
}

export interface EmployeeCreate {
  employee_code: string;
  full_name: string;
  department?: string;
  designation?: string;
  manager_name?: string;
  device_info?: Record<string, unknown>;
  access_privileges?: string[];
}

export async function listEmployees(params?: {
  department?: string;
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<Employee[]> {
  const query = new URLSearchParams();
  if (params?.department) query.set('department', params.department);
  if (params?.search) query.set('search', params.search);
  if (params?.skip) query.set('skip', String(params.skip));
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return api.get<Employee[]>(`/employees${qs ? `?${qs}` : ''}`);
}

export async function getEmployee(id: string): Promise<Employee> {
  return api.get<Employee>(`/employees/${id}`);
}

export async function createEmployee(data: EmployeeCreate): Promise<Employee> {
  return api.post<Employee>('/employees', data);
}

export async function deleteEmployee(id: string): Promise<void> {
  return api.delete<void>(`/employees/${id}`);
}

export async function getEmployeeStats(): Promise<{
  total_employees: number;
  department_distribution: Record<string, number>;
}> {
  return api.get('/employees/stats/summary');
}
