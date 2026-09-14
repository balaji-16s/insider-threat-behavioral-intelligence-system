import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { login as apiLogin, register as apiRegister, type LoginCredentials, type UserCreate } from '../api/auth';
import { setToken, getToken } from '../api/client';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: { email: string; role: string; employeeId: string | null } | null;
  login: (credentials: LoginCredentials) => Promise<SessionUser>;
  loginWithToken: (token: string) => SessionUser;
  register: (data: UserCreate) => Promise<void>;
  logout: () => void;
}

interface SessionUser {
  role: string;
  employeeId: string | null;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<{ email: string; role: string; employeeId: string | null } | null>(null);

  useEffect(() => {
    const token = getToken();
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser({ email: payload.sub, role: payload.role, employeeId: payload.employee_id ?? null });
        setIsAuthenticated(true);
      } catch {
        setToken(null);
      }
    }
    setIsLoading(false);
  }, []);

  // Returns the role so callers can route portal (employee) logins to
  // their own dashboard instead of the SOC dashboard.
  const login = useCallback(async (credentials: LoginCredentials) => {
    const data = await apiLogin(credentials);
    return loginWithToken(data.access_token);
  }, []);

  // Used by the Google OAuth callback: store an externally-issued JWT
  // (from /auth/google/callback) and mark the session authenticated.
  const loginWithToken = useCallback((token: string): SessionUser => {
    setToken(token);
    const payload = JSON.parse(atob(token.split('.')[1]));
    setUser({ email: payload.sub, role: payload.role, employeeId: payload.employee_id ?? null });
    setIsAuthenticated(true);
    return { role: payload.role as string, employeeId: payload.employee_id ?? null };
  }, []);

  const register = useCallback(async (data: UserCreate) => {
    await apiRegister(data);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, user, login, loginWithToken, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
