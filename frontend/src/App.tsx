import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import OAuthCallback from './pages/OAuthCallback';
import Dashboard from './pages/Dashboard';
import Employees from './pages/Employees';
import AddEmployee from './pages/AddEmployee';
import EmployeeDetail from './pages/EmployeeDetail';
import ActivityLogs from './pages/ActivityLogs';
import Alerts from './pages/Alerts';
import Incidents from './pages/Incidents';
import RiskScores from './pages/RiskScores';
import AnomalyDetection from './pages/AnomalyDetection';
import BehavioralAnalysis from './pages/BehavioralAnalysis';
import AnomalyReports from './pages/AnomalyReports';
import UebaIntelligence from './pages/UebaIntelligence';
import IncidentDetail from './pages/IncidentDetail';
import WorkerDashboard from './pages/WorkerDashboard';

/** Send each role to the dashboard it is actually allowed to see. */
function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user?.role === 'employee' ? '/my-dashboard' : '/dashboard'} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/oauth/callback" element={<OAuthCallback />} />

          {/* Worker (employee) portal */}
          <Route
            path="/my-dashboard"
            element={<ProtectedRoute><WorkerDashboard /></ProtectedRoute>}
          />

          <Route
            path="/dashboard"
            element={<ProtectedRoute staffOnly><Dashboard /></ProtectedRoute>}
          />
          <Route
            path="/employees"
            element={<ProtectedRoute staffOnly><Employees /></ProtectedRoute>}
          />
          <Route
            path="/employees/new"
            element={<ProtectedRoute staffOnly><AddEmployee /></ProtectedRoute>}
          />
          <Route
            path="/employees/:id"
            element={<ProtectedRoute staffOnly><EmployeeDetail /></ProtectedRoute>}
          />
          <Route
            path="/activity-logs"
            element={<ProtectedRoute staffOnly><ActivityLogs /></ProtectedRoute>}
          />
          <Route
            path="/alerts"
            element={<ProtectedRoute staffOnly><Alerts /></ProtectedRoute>}
          />
          <Route
            path="/incidents"
            element={<ProtectedRoute staffOnly><Incidents /></ProtectedRoute>}
          />
          <Route
            path="/incidents/:id"
            element={<ProtectedRoute staffOnly><IncidentDetail /></ProtectedRoute>}
          />
          <Route
            path="/risk-scores"
            element={<ProtectedRoute staffOnly><RiskScores /></ProtectedRoute>}
          />
          <Route
            path="/anomaly-detection"
            element={<ProtectedRoute staffOnly><AnomalyDetection /></ProtectedRoute>}
          />
          <Route
            path="/behavioral-analysis"
            element={<ProtectedRoute staffOnly><BehavioralAnalysis /></ProtectedRoute>}
          />
          <Route
            path="/anomaly-reports"
            element={<ProtectedRoute staffOnly><AnomalyReports /></ProtectedRoute>}
          />
          <Route
            path="/ueba-intelligence"
            element={<ProtectedRoute staffOnly><UebaIntelligence /></ProtectedRoute>}
          />
          <Route path="/" element={<HomeRedirect />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
