const API_BASE = '/api/v1';

/** Abort requests that hang for this long so the UI never gets stuck on a spinner. */
const REQUEST_TIMEOUT_MS = 30000;

/**
 * Long-running engine operations (UEBA pipeline, risk recalculation, ML
 * detection) process every employee and legitimately take minutes on the
 * full CERT dataset — give them a generous budget instead of the 30s default.
 */
export const LONG_REQUEST_TIMEOUT_MS = 10 * 60 * 1000;

let accessToken: string | null = localStorage.getItem('access_token');

export function setToken(token: string | null) {
  accessToken = token;
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    localStorage.removeItem('access_token');
  }
}

export function getToken(): string | null {
  return accessToken;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (err) {
    if (controller.signal.aborted) {
      throw new Error(`Request timed out: ${endpoint}`);
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }

  if (res.status === 204) return undefined as T;

  // Handle 401 Unauthorized — clear stale token and redirect to login
  if (res.status === 401) {
    setToken(null);
    window.location.href = '/login';
    throw new Error('Session expired. Please log in again.');
  }

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || `Request failed: ${res.statusText}`);
  }

  return data as T;
}

export const api = {
  get: <T>(endpoint: string, timeoutMs?: number) =>
    request<T>(endpoint, {}, timeoutMs),
  post: <T>(endpoint: string, body?: unknown, timeoutMs?: number) =>
    request<T>(endpoint, { method: 'POST', body: JSON.stringify(body) }, timeoutMs),
  put: <T>(endpoint: string, body?: unknown, timeoutMs?: number) =>
    request<T>(endpoint, { method: 'PUT', body: JSON.stringify(body) }, timeoutMs),
  patch: <T>(endpoint: string, body?: unknown, timeoutMs?: number) =>
    request<T>(endpoint, { method: 'PATCH', body: JSON.stringify(body) }, timeoutMs),
  delete: <T>(endpoint: string, timeoutMs?: number) =>
    request<T>(endpoint, { method: 'DELETE' }, timeoutMs),
};

/**
 * Download a binary file (e.g. PDF/Excel export) with the auth token attached.
 */
export async function downloadFile(
  endpoint: string,
  filename: string,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<void> {
  const headers: Record<string, string> = {};
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${endpoint}`, { headers, signal: controller.signal });
  } catch (err) {
    if (controller.signal.aborted) {
      throw new Error(`Download timed out: ${endpoint}`);
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }

  if (res.status === 401) {
    setToken(null);
    window.location.href = '/login';
    throw new Error('Session expired. Please log in again.');
  }

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `Download failed: ${res.statusText}`);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
