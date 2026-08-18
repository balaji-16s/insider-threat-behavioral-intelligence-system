import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Eye, EyeOff, UserPlus, LogIn } from 'lucide-react';

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    username: '',
    password: '',
    full_name: '',
    email: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await register({
          full_name: form.full_name,
          email: form.email,
          password: form.password,
        });
        await login({ username: form.email, password: form.password });
      } else {
        await login({ username: form.username, password: form.password });
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    try {
      const res = await fetch('/api/v1/auth/google/login');
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        setError(data?.detail || 'Google login is not configured');
        return;
      }
      window.location.href = data.auth_url;
    } catch {
      setError('Could not start Google login. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-cyber-500/5 via-transparent to-transparent" />

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-cyber-500/10 border border-cyber-500/20 mb-4">
            <Shield className="w-8 h-8 text-cyber-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">ITBIS</h1>
          <p className="text-gray-500 mt-1">Insider Threat Intelligence System</p>
        </div>

        {/* Form */}
        <div className="bg-surface-900 rounded-2xl border border-surface-800 p-8">
          <div className="flex mb-6 p-1 bg-surface-800 rounded-lg">
            <button
              onClick={() => { setIsRegister(false); setError(''); }}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                !isRegister ? 'bg-cyber-500/20 text-cyber-400' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <LogIn className="w-4 h-4 inline mr-2" />
              Sign In
            </button>
            <button
              onClick={() => { setIsRegister(true); setError(''); }}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                isRegister ? 'bg-cyber-500/20 text-cyber-400' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <UserPlus className="w-4 h-4 inline mr-2" />
              Register
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-danger-500/10 border border-danger-500/20 text-danger-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">Full Name</label>
                  <input
                    type="text"
                    required
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                    className="w-full px-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg text-gray-100 
                      placeholder-gray-500 focus:outline-none focus:border-cyber-500/50 focus:ring-1 focus:ring-cyber-500/20
                      transition-all"
                    placeholder="John Doe"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">Email</label>
                  <input
                    type="email"
                    required
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    className="w-full px-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg text-gray-100 
                      placeholder-gray-500 focus:outline-none focus:border-cyber-500/50 focus:ring-1 focus:ring-cyber-500/20
                      transition-all"
                    placeholder="you@company.com"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">
                {isRegister ? 'Email' : 'Email'}
              </label>
              {!isRegister && (
                <input
                  type="text"
                  required
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  className="w-full px-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg text-gray-100 
                    placeholder-gray-500 focus:outline-none focus:border-cyber-500/50 focus:ring-1 focus:ring-cyber-500/20
                    transition-all"
                  placeholder="you@company.com"
                />
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full px-4 py-2.5 pr-10 bg-surface-800 border border-surface-700 rounded-lg text-gray-100 
                    placeholder-gray-500 focus:outline-none focus:border-cyber-500/50 focus:ring-1 focus:ring-cyber-500/20
                    transition-all"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-cyber-500/20 border border-cyber-500/30 text-cyber-400 rounded-lg 
                font-medium hover:bg-cyber-500/30 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed
                flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
              ) : isRegister ? (
                <>
                  <UserPlus className="w-4 h-4" />
                  Create Account
                </>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  Sign In
                </>
              )}
            </button>
          </form>

          {!isRegister && (
            <>
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-surface-800" />
                </div>
                <div className="relative flex justify-center text-xs text-gray-500">
                  <span className="bg-surface-900 px-3">or</span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleGoogleLogin}
                className="w-full flex items-center justify-center gap-3 py-2.5 px-4 bg-surface-800 
                  border border-surface-700 text-gray-200 rounded-lg font-medium 
                  hover:bg-surface-700 transition-all duration-150"
              >
                <GoogleIcon className="w-5 h-5" />
                Continue with Google
              </button>
            </>
          )}
        </div>

        <p className="text-center mt-6 text-xs text-gray-600">
          Insider Threat Behavioral Intelligence System v1.0
        </p>
      </div>
    </div>
  );
}

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3l5.7-5.7C34.5 6.1 29.5 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.6-.4-3.9z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3l5.7-5.7C34.5 6.1 29.5 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C36.9 40.3 44 35 44 24c0-1.3-.1-2.6-.4-3.9z" />
    </svg>
  );
}
