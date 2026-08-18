import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
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

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/oauth/callback" element={<OAuthCallback />} />
          <Route
            path="/dashboard"
            element={<ProtectedRoute><Dashboard /></ProtectedRoute>}
          />
          <Route
            path="/employees"
            element={<ProtectedRoute><Employees /></ProtectedRoute>}
          />
          <Route
            path="/employees/new"
            element={<ProtectedRoute><AddEmployee /></ProtectedRoute>}
          />
          <Route
            path="/employees/:id"
            element={<ProtectedRoute><EmployeeDetail /></ProtectedRoute>}
          />
          <Route
            path="/activity-logs"
            element={<ProtectedRoute><ActivityLogs /></ProtectedRoute>}
          />
          <Route
            path="/alerts"
            element={<ProtectedRoute><Alerts /></ProtectedRoute>}
          />
          <Route
            path="/incidents"
            element={<ProtectedRoute><Incidents /></ProtectedRoute>}
          />
          <Route
            path="/incidents/:id"
            element={<ProtectedRoute><IncidentDetail /></ProtectedRoute>}
          />
          <Route
            path="/risk-scores"
            element={<ProtectedRoute><RiskScores /></ProtectedRoute>}
          />
          <Route
            path="/anomaly-detection"
            element={<ProtectedRoute><AnomalyDetection /></ProtectedRoute>}
          />
          <Route
            path="/behavioral-analysis"
            element={<ProtectedRoute><BehavioralAnalysis /></ProtectedRoute>}
          />
          <Route
            path="/anomaly-reports"
            element={<ProtectedRoute><AnomalyReports /></ProtectedRoute>}
          />
          <Route
            path="/ueba-intelligence"
            element={<ProtectedRoute><UebaIntelligence /></ProtectedRoute>}
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
