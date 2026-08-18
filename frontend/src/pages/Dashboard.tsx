import { useEffect, useState } from 'react';
import { getDashboardStats, getActivityTrends, type DashboardStats, type ActivityTrend } from '../api/dashboard';
import { listAlerts, type Alert } from '../api/alerts';
import { getRiskAnalytics, type RiskAnalytics } from '../api/riskScores';
import { getTopThreats, type ThreatAssessmentResult } from '../api/anomaly';
import { useNavigate } from 'react-router-dom';
import {
  Users, AlertTriangle, Activity, ShieldAlert, BarChart3, TrendingUp, TrendingDown,
  Target, ChevronRight,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';

const severityBg: Record<string, string> = {
  critical: 'bg-red-500/10 border-red-500/20 text-red-400',
  high: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  medium: 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400',
  low: 'bg-green-500/10 border-green-500/20 text-green-400',
  informational: 'bg-gray-500/10 border-gray-500/20 text-gray-400',
};

function StatCard({
  title, value, icon: Icon, color, trend, trendUp,
}: {
  title: string; value: number | string; icon: typeof Users; color: string;
  trend?: string; trendUp?: boolean;
}) {
  return (
    <div className="bg-surface-900 rounded-xl border border-surface-800 p-5 hover:border-surface-700 transition-all duration-200 group">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2.5 rounded-lg ${color} bg-opacity-10`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs font-medium ${trendUp ? 'text-matrix-400' : 'text-danger-400'}`}>
            {trendUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {trend}
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{title}</p>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trends, setTrends] = useState<ActivityTrend[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [riskAnalytics, setRiskAnalytics] = useState<RiskAnalytics | null>(null);
  const [topThreats, setTopThreats] = useState<ThreatAssessmentResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, t, a, r, threats] = await Promise.all([
          getDashboardStats(),
          getActivityTrends(),
          listAlerts({ limit: 10 }),
          getRiskAnalytics(30).catch(() => null),
          getTopThreats(5).catch(() => []),
        ]);
        setStats(s);
        setTrends(t.reverse());
        setRecentAlerts(a);
        setRiskAnalytics(r);
        setTopThreats(threats);
      } catch (err) {
        console.error('Failed to load dashboard:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const [viewMode, setViewMode] = useState<'all' | 'soc' | 'manager' | 'admin'>('all');

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-16">
        <AlertTriangle className="w-12 h-12 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-500">Unable to load dashboard data. Make sure the backend is running and database has data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Security Dashboard</h1>
          <p className="text-gray-500 mt-1">Real-time overview of insider threat intelligence</p>
        </div>
        <div className="flex items-center gap-1 bg-surface-900 border border-surface-800 p-1 rounded-xl">
          {[
            { id: 'all', label: 'All Views' },
            { id: 'soc', label: 'SOC Engineer' },
            { id: 'manager', label: 'Security Manager' },
            { id: 'admin', label: 'Admin Oversight' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setViewMode(tab.id as any)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                viewMode === tab.id
                  ? 'bg-cyber-500/20 text-cyber-400 border border-cyber-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-surface-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>


      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {(viewMode === 'all' || viewMode === 'admin') && (
          <StatCard title="Total Employees" value={stats.total_employees} icon={Users} color="text-cyber-400" />
        )}
        {(viewMode === 'all' || viewMode === 'soc') && (
          <StatCard title="Total Alerts" value={stats.total_alerts} icon={AlertTriangle} color="text-warning-400" />
        )}
        {(viewMode === 'all' || viewMode === 'soc') && (
          <StatCard title="Critical Alerts" value={stats.critical_alerts} icon={ShieldAlert} color="text-danger-400" />
        )}
        {(viewMode === 'all' || viewMode === 'manager') && (
          <StatCard title="High Risk Employees" value={stats.high_risk_employees} icon={BarChart3} color="text-danger-400" />
        )}
        {(viewMode === 'all' || viewMode === 'soc') && (
          <StatCard title="Open Alerts" value={stats.open_alerts} icon={AlertTriangle} color="text-warning-400" />
        )}
        {(viewMode === 'all' || viewMode === 'soc') && (
          <StatCard title="Active Incidents" value={stats.active_incidents} icon={ShieldAlert} color="text-danger-400" />
        )}
        {(viewMode === 'all' || viewMode === 'admin') && (
          <StatCard title="Total Activity Logs" value={stats.total_activity_logs.toLocaleString()} icon={Activity} color="text-matrix-400" />
        )}
        {(viewMode === 'all' || viewMode === 'manager' || viewMode === 'admin') && (
          <StatCard title="Total Incidents" value={stats.total_incidents} icon={ShieldAlert} color="text-cyber-400" />
        )}
      </div>


      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity Trends */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Activity Trends (Last 30 Days)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} tickFormatter={(d) => d?.slice(5) || ''} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#e2e8f0',
                  }}
                />
                <Line type="monotone" dataKey="count" stroke="#06b6d4" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk Distribution */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Risk Distribution</h3>
          <div className="h-64 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={[
                    { name: 'Low', value: stats.total_employees - stats.high_risk_employees },
                    { name: 'High/Critical', value: stats.high_risk_employees },
                  ]}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  <Cell fill="#22c55e" />
                  <Cell fill="#ef4444" />
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#e2e8f0',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute flex flex-col items-center gap-1">
              <span className="text-2xl font-bold text-white">{stats.total_employees}</span>
              <span className="text-xs text-gray-500">Total</span>
            </div>
          </div>
          <div className="flex justify-center gap-6 mt-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-matrix-400" />
              <span className="text-sm text-gray-400">Normal</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-danger-400" />
              <span className="text-sm text-gray-400">High Risk</span>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Trend + Top Threats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Score Trend */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Org Risk Score Trend</h3>
            {riskAnalytics && (
              <span className="text-xs text-gray-500">Avg: {riskAnalytics.average_score} • Max: {riskAnalytics.max_score}</span>
            )}
          </div>
          {!riskAnalytics || riskAnalytics.trend.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-16">No risk trend data — run the scoring engine on the Risk Scores page</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={riskAnalytics.trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} tickFormatter={(d) => d?.slice(5) || ''} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                    }}
                    formatter={(value) => [`${value == null ? '—' : Number(value).toFixed(1)}`, 'Avg Score']}
                  />
                  <Line type="monotone" dataKey="average_score" stroke="#f59e0b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Top Threats */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Target className="w-5 h-5 text-danger-400" />
              Top Insider Threats
            </h3>
            <button
              onClick={() => navigate('/ueba-intelligence')}
              className="flex items-center gap-1 text-xs text-cyber-400 hover:underline"
            >
              View UEBA <ChevronRight className="w-3 h-3" />
            </button>
          </div>
          {topThreats.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-16">No threat assessments available</p>
          ) : (
            <div className="space-y-2">
              {topThreats.map((threat, idx) => (
                <div key={threat.employee_id} className="flex items-center gap-3 p-2.5 rounded-lg bg-surface-800/50 hover:bg-surface-800 transition-all">
                  <span className="text-xs font-bold text-gray-500 w-5 text-center">{idx + 1}</span>
                  <div className="w-8 h-8 rounded-full bg-danger-500/10 flex items-center justify-center">
                    <span className="text-xs font-bold text-danger-400">{threat.employee_name?.charAt(0) || '?'}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-200 truncate">{threat.employee_name || 'Unknown'}</p>
                    <p className="text-xs text-gray-500 truncate">{threat.department || '—'}</p>
                  </div>
                  <div className="w-20 h-1.5 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${threat.threat_score}%`, backgroundColor: threat.threat_score >= 60 ? '#ef4444' : '#f59e0b' }}
                    />
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize border ${
                    threat.threat_score >= 60
                      ? 'bg-red-500/10 text-red-400 border-red-500/20'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  }`}>
                    {threat.threat_score.toFixed(0)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Alerts</h3>
        {recentAlerts.length === 0 ? (
          <p className="text-gray-500 text-sm py-4 text-center">No recent alerts</p>
        ) : (
          <div className="space-y-3">
            {recentAlerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-surface-800/50 border border-surface-700/50 hover:border-surface-600 transition-all"
              >
                <div className={`p-2 rounded-lg ${severityBg[alert.severity] || severityBg.informational}`}>
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-200 truncate">{alert.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {alert.anomaly_type && `${alert.anomaly_type} • `}
                    {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                  severityBg[alert.severity] || severityBg.informational
                }`}>
                  {alert.severity}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
