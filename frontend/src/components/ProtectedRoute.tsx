import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from './Layout';
import { type ReactNode } from 'react';

/**
 * Route guard.
 *
 * `staffOnly` marks the analyst/SOC pages. Worker portal accounts are
 * redirected to their own dashboard instead — the backend rejects them
 * with 403 regardless, this just avoids showing them a broken page.
 */
export default function ProtectedRoute({
  children,
  staffOnly = false,
}: {
  children: ReactNode;
  staffOnly?: boolean;
}) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-surface-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500 text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (staffOnly && user?.role === 'employee') {
    return <Navigate to="/my-dashboard" replace />;
  }

  return <Layout>{children}</Layout>;
}
