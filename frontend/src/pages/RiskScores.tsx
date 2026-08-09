import { useEffect, useState } from 'react';
import {
  listRiskScores, getRiskDistribution, calculateRiskScores, getRiskAnalytics,
  type RiskScore, type RiskAnalytics, type RiskScoreCalculateResult,
} from '../api/riskScores';
import { listEmployees, type Employee } from '../api/employees';
import {
  BarChart3, Shield, ShieldAlert, TrendingUp, Users, RefreshCw, Target,
  Activity, Layers,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line,
} from 'recharts';

const riskColors: Record<string, string> = {
  low: '#22c55e',
  medium: '#06b6d4',
  high: '#f59e0b',
  critical: '#ef4444',
};

const riskBg: Record<string, string> = {
  low: 'bg-matrix-500/10 border-matrix-500/20 text-matrix-400',
  medium: 'bg-cyber-500/10 border-cyber-500/20 text-cyber-400',
  high: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  critical: 'bg-danger-500/10 border-danger-500/20 text-danger-400',
};

const riskText: Record<string, string> = {
  low: 'text-matrix-400',
  medium: 'text-cyber-400',
  high: 'text-amber-400',
  critical: 'text-danger-400',
};

const PIE_COLORS = ['#22c55e', '#06b6d4', '#f59e0b', '#ef4444'];

const chartTooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#e2e8f0',
};

function AnalyticsCard({ title, value, icon: Icon, color, sub }: {
  title: string; value: number | string; icon: typeof Users; color: string; sub?: string;
}) {
  return (
    <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
      <div className="flex items-center gap-3">
        <div className={`p-2.5 rounded-lg bg-opacity-10 ${color}`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-xs text-gray-500">{title}</p>
          {sub && <p className="text-[10px] text-gray-600">{sub}</p>}
        </div>
      </div>
    </div>
  );
}

export default function RiskScores() {
  const [scores, setScores] = useState<RiskScore[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [distribution, setDistribution] = useState<Record<string, number>>({});
  const [analytics, setAnalytics] = useState<RiskAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterLevel, setFilterLevel] = useState('');
  const [activeTab, setActiveTab] = useState<'scores' | 'analytics'>('scores');
  const [recalculating, setRecalculating] = useState(false);
  const [calcResult, setCalcResult] = useState<RiskScoreCalculateResult | null>(null);

  async function load() {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filterLevel) params.risk_level = filterLevel;
      params.limit = '500';

      const [s, e, d] = await Promise.all([
        listRiskScores(params as any),
        listEmployees({ limit: 500 }),
        getRiskDistribution(),
      ]);
      setScores(s);
      setEmployees(e);
      setDistribution(d);
    } catch (err) {
      console.error('Failed to load risk scores:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadAnalytics() {
    try {
      const a = await getRiskAnalytics(30);
      setAnalytics(a);
    } catch (err) {
      console.error('Failed to load risk analytics:', err);
    }
  }

  useEffect(() => { load(); }, [filterLevel]);
  useEffect(() => { if (activeTab === 'analytics') loadAnalytics(); }, [activeTab]);

  async function handleRecalculate() {
    setRecalculating(true);
    setCalcResult(null);
    try {
      const result = await calculateRiskScores(30);
      setCalcResult(result);
      await load();
      await loadAnalytics();
    } catch (err) {
      console.error('Failed to recalculate risk scores:', err);
    } finally {
      setRecalculating(false);
    }
  }

  const getEmployeeName = (id: string) => {
    const emp = employees.find((e) => e.id === id);
    return emp?.full_name || id.slice(0, 8) + '...';
  };

  const pieData = Object.entries(distribution).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  }));

  // Bar chart data sorted by score descending
  const barData = scores
    .slice()
    .sort((a, b) => b.score - a.score)
    .slice(0, 20)
    .map((s) => ({
      name: getEmployeeName(s.employee_id),
      score: s.score,
      level: s.risk_level,
    }));

  const analyticsPie = analytics
    ? Object.entries(analytics.distribution).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
      }))
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Risk Scores</h1>
          <p className="text-gray-500 mt-1">Insider risk scoring engine — assessment and threat prioritization</p>
        </div>
        <button
          onClick={handleRecalculate}
          disabled={recalculating}
          className="flex items-center gap-2 px-4 py-2.5 bg-cyber-500/20 border border-cyber-500/30 
            text-cyber-400 rounded-lg font-medium hover:bg-cyber-500/30 transition-all duration-150 
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {recalculating ? (
            <div className="w-4 h-4 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          {recalculating ? 'Calculating...' : 'Recalculate Scores'}
        </button>
      </div>

      {calcResult && (
        <div className="p-4 rounded-lg bg-matrix-500/10 border border-matrix-500/20 flex items-center gap-3">
          <Target className="w-5 h-5 text-matrix-400" />
          <div>
            <p className="text-sm text-matrix-400 font-medium">{calcResult.message}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Avg score {calcResult.average_score} • Low {calcResult.distribution.low} / Medium {calcResult.distribution.medium} /
              High {calcResult.distribution.high} / Critical {calcResult.distribution.critical}
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-surface-900 rounded-xl border border-surface-800">
        {([
          { key: 'scores' as const, label: 'Risk Scores', icon: BarChart3 },
          { key: 'analytics' as const, label: 'Risk Analytics', icon: TrendingUp },
        ]).map((tab) => {
          const isActive = activeTab === tab.key;
          const Icon = tab.icon;
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
            </button>
          );
        })}
      </div>

      {activeTab === 'analytics' ? (
        !analytics ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <AnalyticsCard title="Average Risk Score" value={analytics.average_score} icon={BarChart3} color="text-cyber-400" sub="across all employees" />
              <AnalyticsCard title="Highest Score" value={analytics.max_score} icon={ShieldAlert} color="text-danger-400" sub="most at-risk employee" />
              <AnalyticsCard title="Lowest Score" value={analytics.min_score} icon={Shield} color="text-matrix-400" sub="least at-risk employee" />
              <AnalyticsCard title="Employees Scored" value={analytics.total_employees_scored} icon={Users} color="text-warning-400" sub="latest assessment each" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Trend */}
              <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-cyber-400" />
                  Risk Score Trend (30 Days)
                </h3>
                {analytics.trend.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-16">No trend data — run the scoring engine</p>
                ) : (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={analytics.trend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} tickFormatter={(d) => d?.slice(5) || ''} />
                        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} domain={[0, 100]} />
                        <Tooltip
                          contentStyle={chartTooltipStyle}
                          formatter={(value) => [`${value == null ? '—' : Number(value).toFixed(1)}`, 'Avg Score']}
                        />
                        <Line type="monotone" dataKey="average_score" stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4', r: 3 }} activeDot={{ r: 5 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Department breakdown */}
              <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-warning-400" />
                  Department Risk Breakdown
                </h3>
                {analytics.department_breakdown.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-16">No department data</p>
                ) : (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.department_breakdown} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis type="number" domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis
                          type="category" dataKey="department" stroke="#64748b" tick={{ fontSize: 10 }} width={90}
                          tickFormatter={(name: string) => name.length > 10 ? name.slice(0, 10) + '…' : name}
                        />
                        <Tooltip
                          contentStyle={chartTooltipStyle}
                          formatter={(value, _name, item) => {
                            const payload = (item as any)?.payload ?? {};
                            return [
                              `${value == null ? '—' : Number(value)} avg (${payload.high_risk_count} high-risk of ${payload.employees})`,
                              'Risk Score',
                            ];
                          }}
                        />
                        <Bar dataKey="average_score" radius={[0, 4, 4, 0]}>
                          {analytics.department_breakdown.map((entry, index) => (
                            <Cell
                              key={index}
                              fill={entry.average_score >= 60 ? '#ef4444' : entry.average_score >= 30 ? '#f59e0b' : '#06b6d4'}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </div>

            {/* Distribution + top contributors */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-matrix-400" />
                  Risk Distribution
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={analyticsPie} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                        paddingAngle={3} dataKey="value"
                      >
                        {analyticsPie.map((_, index) => (
                          <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={chartTooltipStyle} />
                      <Legend formatter={(value: string) => <span className="text-gray-400 text-sm">{value}</span>} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Target className="w-5 h-5 text-danger-400" />
                  Top Risk Contributors
                </h3>
                {analytics.top_contributors.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-16">No contributors</p>
                ) : (
                  <div className="space-y-2">
                    {analytics.top_contributors.map((contrib, idx) => (
                      <div key={contrib.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-surface-800/50 hover:bg-surface-800 transition-all">
                        <span className="text-xs font-bold text-gray-500 w-6 text-center">#{idx + 1}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-200 truncate">{contrib.name}</p>
                          <p className="text-xs text-gray-500 truncate">{contrib.department || '—'} • {contrib.designation || '—'}</p>
                        </div>
                        <div className="w-24 h-2 bg-surface-700 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{ width: `${contrib.risk_score}%`, backgroundColor: riskColors[contrib.risk_level] || '#6b7280' }}
                          />
                        </div>
                        <span className={`text-sm font-bold w-14 text-right ${riskText[contrib.risk_level] || 'text-gray-400'}`}>
                          {contrib.risk_score.toFixed(1)}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium border capitalize ${
                          riskBg[contrib.risk_level] || 'bg-gray-500/10 border-gray-500/20 text-gray-400'
                        }`}>
                          {contrib.risk_level}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      ) : (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {Object.entries(distribution).map(([level, count]) => (
              <div key={level} className={`rounded-xl border p-4 ${riskBg[level] || 'bg-gray-500/10 border-gray-500/20 text-gray-400'}`}>
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium uppercase tracking-wider opacity-80">{level}</p>
                  {level === 'critical' || level === 'high' ? (
                    <ShieldAlert className="w-4 h-4" />
                  ) : (
                    <Shield className="w-4 h-4" />
                  )}
                </div>
                <p className="text-2xl font-bold mt-2">{count}</p>
                <p className="text-xs opacity-60 mt-1">employees</p>
              </div>
            ))}
          </div>

          {/* Filter */}
          <div className="flex items-center gap-3">
            <select
              value={filterLevel}
              onChange={(e) => setFilterLevel(e.target.value)}
              className="px-4 py-2 bg-surface-900 border border-surface-800 rounded-lg text-sm text-gray-300
                focus:outline-none focus:border-cyber-500/50 transition-all"
            >
              <option value="">All Risk Levels</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {loading ? (
            <div className="flex justify-center py-16">
              <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Distribution pie chart */}
              <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Risk Distribution</h3>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {pieData.map((_, index) => (
                          <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={chartTooltipStyle} />
                      <Legend formatter={(value: string) => <span className="text-gray-400 text-sm">{value}</span>} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Top risk scores bar chart */}
              <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Top Risk Scores</h3>
                {barData.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-16">No risk score data — run "Recalculate Scores"</p>
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis type="number" domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} />
                        <YAxis
                          type="category"
                          dataKey="name"
                          stroke="#64748b"
                          tick={{ fontSize: 10 }}
                          width={100}
                          tickFormatter={(name) => name.length > 12 ? name.slice(0, 12) + '...' : name}
                        />
                        <Tooltip
                          contentStyle={chartTooltipStyle}
                          formatter={(value, _name, item) => {
                            const payload = (item as any)?.payload ?? {};
                            return [
                              `${value == null ? '—' : Number(value).toFixed(1)} (${payload.level})`,
                              'Risk Score',
                            ];
                          }}
                        />
                        <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                          {barData.map((entry, index) => (
                            <Cell key={index} fill={riskColors[entry.level] || '#6b7280'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Score list */}
              <div className="lg:col-span-2 bg-surface-900 rounded-xl border border-surface-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-cyber-400" />
                  All Risk Scores
                </h3>
                {scores.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-8">No risk scores available</p>
                ) : (
                  <div className="space-y-2">
                    {scores
                      .slice()
                      .sort((a, b) => b.score - a.score)
                      .map((score) => (
                        <div
                          key={score.id}
                          className="flex items-center gap-4 p-3 rounded-lg bg-surface-800/50 border border-surface-700/50 hover:border-surface-600 transition-all"
                        >
                          <div className="flex-1">
                            <p className="text-sm font-medium text-gray-200">{getEmployeeName(score.employee_id)}</p>
                            <p className="text-xs text-gray-500">{new Date(score.calculated_at).toLocaleString()}</p>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="w-32 h-2 bg-surface-700 rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{
                                  width: `${score.score}%`,
                                  backgroundColor: riskColors[score.risk_level] || '#6b7280',
                                }}
                              />
                            </div>
                            <span className={`text-sm font-bold w-16 text-right ${riskText[score.risk_level] || 'text-gray-400'}`}>
                              {score.score.toFixed(1)}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-xs font-medium border capitalize ${
                              riskBg[score.risk_level] || 'bg-gray-500/10 border-gray-500/20 text-gray-400'
                            }`}>
                              {score.risk_level}
                            </span>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
