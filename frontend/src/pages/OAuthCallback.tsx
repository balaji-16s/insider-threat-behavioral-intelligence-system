import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, AlertTriangle } from 'lucide-react';

/**
 * Landing page for the Google OAuth redirect. The backend sends the JWT in
 * the URL fragment (#access_token=...) — never in the query string, so it
 * doesn't land in server logs or browser history.
 */
export default function OAuthCallback() {
  const { loginWithToken } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    const token = params.get('access_token');
    const err = params.get('error');

    if (token) {
      try {
        loginWithToken(token);
        window.location.href = '/dashboard';
        return;
      } catch {
        setError('Could not validate the Google sign-in token.');
        return;
      }
    }

    if (err === 'invalid_state') {
      setError('Sign-in session expired. Please try again.');
    } else if (err === 'token_exchange_failed') {
      setError('Google could not verify the sign-in. Please try again.');
    } else if (err === 'no_email') {
      setError('Your Google account has no email address associated with it.');
    } else {
      setError(err ? 'Google sign-in failed. Please try again.' : 'Signing you in...');
    }
  }, [loginWithToken]);

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-cyber-500/5 via-transparent to-transparent" />

      <div className="relative w-full max-w-md">
        <div className="bg-surface-900 rounded-2xl border border-surface-800 p-8 text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-cyber-500/10 border border-cyber-500/20 mb-4">
            {error ? (
              <AlertTriangle className="w-7 h-7 text-danger-400" />
            ) : (
              <Shield className="w-7 h-7 text-cyber-400" />
            )}
          </div>

          {error ? (
            <>
              <h1 className="text-lg font-bold text-white">Google Sign-In Failed</h1>
              <p className="text-sm text-gray-500 mt-2">{error}</p>
              <Link
                to="/login"
                className="inline-block mt-6 px-5 py-2.5 bg-cyber-500/20 border border-cyber-500/30
                  text-cyber-400 rounded-lg font-medium hover:bg-cyber-500/30 transition-all duration-150"
              >
                Back to Login
              </Link>
            </>
          ) : (
            <>
              <h1 className="text-lg font-bold text-white">Completing Sign-In</h1>
              <p className="text-sm text-gray-500 mt-2">Redirecting to your dashboard...</p>
              <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin mx-auto mt-6" />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
