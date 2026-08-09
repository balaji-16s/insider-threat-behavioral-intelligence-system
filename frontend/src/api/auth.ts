import { api, setToken } from './client';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserCreate {
  full_name: string;
  email: string;
  password: string;
  role?: string;
}

export interface UserOut {
  id: string;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
}

export async function login(credentials: LoginCredentials): Promise<TokenResponse> {
  const formData = new URLSearchParams();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);

  const res = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  });

  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Login failed');
  }

  const data: TokenResponse = await res.json();
  setToken(data.access_token);
  return data;
}

export async function register(user: UserCreate): Promise<UserOut> {
  return api.post<UserOut>('/auth/register', user);
}
