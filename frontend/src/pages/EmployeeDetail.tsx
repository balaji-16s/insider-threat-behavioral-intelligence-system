import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getEmployee, type Employee } from '../api/employees';
import { listActivityLogs, type ActivityLog } from '../api/activityLogs';
import { getRiskScoreHistory, type RiskScore } from '../api/riskScores';
import { listAlerts, type Alert } from '../api/alerts';
import { runUebaPipeline } from '../api/ueba';
import { useAuth } from '../context/AuthContext';
import {
  ArrowLeft, Activity, AlertTriangle, BarChart3, Building2, Monitor, Shield,
  Calendar, ChevronRight, RefreshCw, CheckCircle2,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const typeColors: Record<string, string> = {
  login: 'text-matrix-400',
  file_download: 'text-cyber-400',
  file_upload: 'text-warning-400',
  data_transfer: 'text-danger-400',
  email: 'text-blue-400',
  privilege_change: 'text-purple-400',
  remote_access: 'text-orange-400',
  usb_device: 'text-pink-400',
};

const typeBg: Record<string, string> = {
  login: 'bg-matrix-500/10',
  file_download: 'bg-cyber-500/10',
  file_upload: 'bg-amber-500/10',
  data_transfer: 'bg-red-500/10',
  email: 'bg-blue-500/10',
  privilege_change: 'bg-purple-500/10',
  remote_access: 'bg-orange-500/10',
  usb_device: 'bg-pink-500/10',
};

export default function EmployeeDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [recentLogs, setRecentLogs] = useState<ActivityLog[]>([]);
  const [riskHistory, setRiskHistory] = useState<RiskScore[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'logs' | 'alerts' | 'risk'>('logs');
  const [recalculating, setRecalculating] = useState(false);
  const [pipelineMsg, setPipelineMsg] = useState<string | null>(null);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  // The scoring pipeline is restricted to these roles server-side (a
  // security_analyst receives 403), so the control is hidden for them
  // rather than failing when clicked.
  const canRecalculate =
    user?.role === 'administrator' ||
    user?.role === 'security_manager' ||
    user?.role === 'soc_engineer';

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [emp, logs, rh, al] = await Promise.all([
        getEmployee(id),
        listActivityLogs({ employee_id: id, limit: 50 }),
        getRiskScoreHistory(id, 30),
        listAlerts({ employee_id: id, limit: 20 }),
      ]);
      setEmployee(emp);
      setRecentLogs(logs);
      setRiskHistory(rh.reverse());
      setAlerts(al);
    } catch (err) {
      console.error('Failed to load employee:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // Runs the full pipeline for this one employee: refresh their baseline,
  // re-run anomaly detection, then recalculate and persist their risk
  // score — then reloads the page data so the new score and alerts show.
  async function handleRecalculate() {
    if (!employee) return;
    setRecalculating(true);
    setPipelineMsg(null);
    setPipelineError(null);
    try {
      const result = await runUebaPipeline(30, employee.id);
      setPipelineMsg(
        `Baseline refreshed, ${result.employees_with_anomalies} anomaly scan(s), ` +
        `${result.alerts_created} new alert(s), score persisted for ` +
        `${result.risk_scores_calculated} employee(s).`
      );
      await load();
    } catch (err) {
      setPipelineError(
        err instanceof Error ? err.message : 'Recalculation failed'
      );
    } finally {
      setRecalculating(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500">Employee not found</p>
        <button onClick={() => navigate('/employees')} className="text-cyber-400 mt-2 hover:underline">
          Back to employees
        </button>
      </div>
    );
  }

  const tabs = [
    { key: 'logs', label: 'Activity Logs', icon: Activity, count: recentLogs.length },
    { key: 'alerts', label: 'Alerts', icon: AlertTriangle, count: alerts.length },
    { key: 'risk', label: 'Risk History', icon: BarChart3, count: riskHistory.length },
  ] as const;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/employees')}
            className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-surface-800 transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-cyber-500/10 flex items-center justify-center">
              <span className="text-lg font-bold text-cyber-400">
                {employee.full_name.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">{employee.full_name}</h1>
              <p className="text-sm text-gray-500">
                {employee.designation || 'Employee'} • {employee.employee_code}
              </p>
            </div>
          </div>
        </div>

        {canRecalculate && (
          <button
            onClick={handleRecalculate}
            disabled={recalculating}
            title="Refresh this employee's baseline, re-run anomaly detection, then recalculate their risk score"
            className="flex items-center gap-2 px-4 py-2.5 bg-cyber-500/20 border border-cyber-500/30
              text-cyber-400 rounded-lg font-medium hover:bg-cyber-500/30 transition-all duration-150
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {recalculating ? (
              <div className="w-4 h-4 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            {recalculating ? 'Recalculating…' : 'Recalculate Score'}
          </button>
        )}
      </div>

      {pipelineMsg && (
        <div className="p-3.5 rounded-lg bg-matrix-500/10 border border-matrix-500/20 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-matrix-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-matrix-400 font-medium">Risk score recalculated</p>
            <p className="text-xs text-gray-500 mt-0.5">{pipelineMsg}</p>
          </div>
        </div>
      )}

      {pipelineError && (
        <div className="p-3.5 rounded-lg bg-danger-500/10 border border-danger-500/20 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-danger-400 shrink-0 mt-0.5" />
          <p className="text-sm text-danger-400">{pipelineError}</p>
        </div>
      )}

      {/* Info cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <Building2 className="w-5 h-5 text-cyber-400" />
            <div>
              <p className="text-xs text-gray-500">Department</p>
              <p className="text-sm font-medium text-gray-200">{employee.department || '—'}</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <Monitor className="w-5 h-5 text-matrix-400" />
            <div>
              <p className="text-xs text-gray-500">Device</p>
              <p className="text-sm font-medium text-gray-200">
                {employee.device_info?.os as string || '—'}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-warning-400" />
            <div>
              <p className="text-xs text-gray-500">Access Privileges</p>
              <p className="text-sm font-medium text-gray-200">
                {employee.access_privileges?.length || 0} items
              </p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <Calendar className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Active Since</p>
              <p className="text-sm font-medium text-gray-200">
                {new Date(employee.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-surface-900 rounded-xl border border-surface-800">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center ${
                isActive
                  ? 'bg-cyber-500/10 text-cyber-400 border border-cyber-500/20'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${isActive ? 'bg-cyber-500/20' : 'bg-surface-800 text-gray-500'}`}>
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'logs' && (
        <div className="space-y-3">
          {recentLogs.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-8">No activity logs for this employee</p>
          ) : (
            recentLogs.slice(0, 20).map((log) => (
              <div
                key={log.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-surface-900 border border-surface-800 hover:border-surface-700 transition-all"
              >
                <div className={`p-2 rounded-lg ${typeBg[log.activity_type] || 'bg-gray-500/10'}`}>
                  <Activity className={`w-4 h-4 ${typeColors[log.activity_type] || 'text-gray-400'}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-200 capitalize">{log.activity_type.replace('_', ' ')}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {log.source && `${log.source} • `}
                    {new Date(log.occurred_at).toLocaleString()}
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-600" />
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'alerts' && (
        <div className="space-y-3">
          {alerts.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-8">No alerts for this employee</p>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-start gap-3 p-4 rounded-lg bg-surface-900 border border-surface-800 hover:border-surface-700 transition-all"
              >
                <AlertTriangle className={`w-5 h-5 mt-0.5 ${
                  alert.severity === 'critical' || alert.severity === 'high'
                    ? 'text-danger-400' : 'text-warning-400'
                }`} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-gray-200">{alert.title}</p>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                      alert.severity === 'critical' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                      alert.severity === 'high' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                    }`}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {alert.anomaly_type && `${alert.anomaly_type} • `}
                    {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'risk' && (
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Risk Score Trend</h3>
          {riskHistory.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-8">No risk score data available</p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={riskHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="calculated_at"
                    stroke="#64748b"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(d) => new Date(d).toLocaleDateString()}
                  />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                    }}
                    formatter={(value) => [`${value == null ? '—' : Number(value).toFixed(1)}`, 'Risk Score']}
                    labelFormatter={(label) => new Date(label).toLocaleString()}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    dot={{ fill: '#06b6d4', r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
