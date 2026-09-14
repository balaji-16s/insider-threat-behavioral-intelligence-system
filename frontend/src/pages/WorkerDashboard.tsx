import { useEffect, useState, type ReactNode } from 'react';
import {
  Activity, AlertTriangle, BarChart3, Fingerprint, Gauge, Info,
  ShieldAlert, TrendingUp, User, MonitorSmartphone, Clock, CalendarDays,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, Cell,
} from 'recharts';
import {
  getWorkerOverview, getWorkerActivity,
  type WorkerOverview, type WorkerActivityPage,
} from '../api/worker';

const riskColors: Record<string, string> = {
  low: '#22c55e',
  medium: '#06b6d4',
  high: '#f59e0b',
  critical: '#ef4444',
};

const riskText: Record<string, string> = {
  low: 'text-matrix-400',
  medium: 'text-cyber-400',
  high: 'text-amber-400',
  critical: 'text-danger-400',
};

const severityBg: Record<string, string> = {
  informational: 'bg-gray-500/10 border-gray-500/20 text-gray-400',
  low: 'bg-matrix-500/10 border-matrix-500/20 text-matrix-400',
  medium: 'bg-cyber-500/10 border-cyber-500/20 text-cyber-400',
  high: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  critical: 'bg-danger-500/10 border-danger-500/20 text-danger-400',
};

const chartTooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#e2e8f0',
};

function StatCard({ title, value, sub, icon: Icon, tone }: {
  title: string; value: ReactNode; sub?: string;
  icon: typeof User; tone: string;
}) {
  return (
    <div className="bg-surface-900 rounded-xl border border-surface-800 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-white mt-2">{value}</p>
          {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
        </div>
        <div className={`p-2.5 rounded-lg bg-opacity-10 ${tone}`}>
          <Icon className={`w-5 h-5 ${tone}`} />
        </div>
      </div>
    </div>
  );
}

export default function WorkerDashboard() {
  const [overview, setOverview] = useState<WorkerOverview | null>(null);
  const [activity, setActivity] = useState<WorkerActivityPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      getWorkerOverview(days),
      getWorkerActivity({ limit: 25 }),
    ])
      .then(([ov, act]) => {
        if (cancelled) return;
        setOverview(ov);
        setActivity(act);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [days]);

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-danger-500/10 border border-danger-500/20 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-danger-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-danger-400 font-medium">Could not load your dashboard</p>
          <p className="text-xs text-gray-500 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!overview) return null;

  const { employee, risk, threat, alerts, activity: summary, baseline } = overview;
  const level = risk.level || 'low';
  const threatLevel = threat.level || 'low';

  const modelData = Object.entries(threat.model_scores).map(([name, model]) => ({
    name: name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    score: model.score,
    level: model.level,
  }));

  const typeData = summary.by_type.map((t) => ({ name: t.label, count: t.count }));
  const dailyData = summary.daily.map((d) => ({ date: d.date.slice(5), count: d.count }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-cyber-500/15 border border-cyber-500/25 flex items-center justify-center">
            <Fingerprint className="w-7 h-7 text-cyber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">{employee.full_name}</h1>
            <p className="text-gray-500 mt-0.5">
              {employee.employee_code} • {employee.designation || 'Employee'}
              {employee.department ? ` • ${employee.department}` : ''}
            </p>
          </div>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-4 py-2 bg-surface-900 border border-surface-800 rounded-lg text-sm text-gray-300
            focus:outline-none focus:border-cyber-500/50 transition-all"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      <div className="p-3 rounded-lg bg-surface-900/60 border border-surface-800 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-cyber-400 shrink-0 mt-0.5" />
        <p className="text-xs text-gray-500">
          This is everything the platform has recorded about you over the last {overview.lookback_days} days.
          Scores are calculated relative to your peers, so a low score means your behaviour is typical of
          the organization ({threat.cohort_size} employees compared).
        </p>
      </div>

      {/* Key numbers */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="My Risk Score"
          value={risk.score == null ? '—' : risk.score.toFixed(1)}
          sub={risk.calculated_at ? `updated ${new Date(risk.calculated_at).toLocaleDateString()}` : 'not yet scored'}
          icon={Gauge}
          tone={riskText[level] || 'text-gray-400'}
        />
        <StatCard
          title="Risk Level"
          value={<span className="capitalize">{level}</span>}
          sub={risk.comparison?.percentile != null ? `higher than ${risk.comparison.percentile}% of peers` : undefined}
          icon={ShieldAlert}
          tone={riskText[level] || 'text-gray-400'}
        />
        <StatCard
          title="My Threat Score"
          value={threat.score.toFixed(1)}
          sub={`${threatLevel} severity`}
          icon={Activity}
          tone={riskText[threatLevel] || 'text-gray-400'}
        />
        <StatCard
          title="Open Alerts"
          value={alerts.open_count}
          sub={alerts.open_count === 0 ? 'nothing flagged' : 'review below'}
          icon={AlertTriangle}
          tone={alerts.open_count > 0 ? 'text-amber-400' : 'text-matrix-400'}
        />
      </div>

      {/* Where I stand */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-cyber-400" />
            How I Compare
          </h3>
          {risk.comparison && risk.score != null ? (
            <div className="space-y-5">
              <div>
                <div className="flex justify-between text-xs text-gray-500 mb-1.5">
                  <span>Your score</span>
                  <span>Organization max {risk.comparison.org_max}</span>
                </div>
                <div className="h-3 bg-surface-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${risk.score}%`, backgroundColor: riskColors[level] || '#6b7280' }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1.5">
                  Organization average is {risk.comparison.org_average} across {risk.comparison.peers_scored} scored employees.
                </p>
              </div>
              {risk.department?.average != null && (
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-1.5">
                    <span>{risk.department.department || 'Department'} average</span>
                    <span>
                      {risk.department.your_rank
                        ? `rank ${risk.department.your_rank} of ${risk.department.size}`
                        : `${risk.department.size} employees`}
                    </span>
                  </div>
                  <div className="h-3 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-cyber-500/60 transition-all duration-500"
                      style={{ width: `${risk.department.average}%` }}
                    />
                  </div>
                </div>
              )}
              <div className="grid grid-cols-3 gap-3 pt-1">
                <div className="p-3 rounded-lg bg-surface-800/50">
                  <p className="text-xs text-gray-500">Peers beaten</p>
                  <p className="text-lg font-bold text-white">{risk.comparison.percentile}%</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-800/50">
                  <p className="text-xs text-gray-500">Baseline</p>
                  <p className="text-lg font-bold text-white capitalize">{baseline.status}</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-800/50">
                  <p className="text-xs text-gray-500">Scoring</p>
                  <p className="text-lg font-bold text-white capitalize">{threat.scoring_mode}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm py-8 text-center">
              No risk score yet — an administrator needs to run the detection pipeline.
            </p>
          )}
        </div>

        {/* Threat models */}
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-warning-400" />
            Threat Breakdown
          </h3>
          {modelData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">No threats detected</p>
          ) : (
            <div className="space-y-3">
              {modelData.map((m) => (
                <div key={m.name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-400">{m.name}</span>
                    <span className={`font-semibold ${riskText[m.level] || 'text-gray-400'}`}>
                      {m.score.toFixed(1)}
                    </span>
                  </div>
                  <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${m.score}%`, backgroundColor: riskColors[m.level] || '#6b7280' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Why */}
      {threat.reasons.length > 0 && (
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-danger-400" />
            What Triggered My Score
          </h3>
          <p className="text-xs text-gray-500 mb-4">
            Each signal is compared against your peers. "Peer median" is a typical colleague's value;
            "peer p95" is the top 5%.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-gray-500 border-b border-surface-800">
                  <th className="pb-2 pr-4">Signal</th>
                  <th className="pb-2 pr-4">Model</th>
                  <th className="pb-2 pr-4 text-right">Your value</th>
                  <th className="pb-2 pr-4 text-right">Peer median</th>
                  <th className="pb-2 pr-4 text-right">Peer p95</th>
                  <th className="pb-2 text-right">Points</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60">
                {threat.reasons.map((r, idx) => (
                  <tr key={`${r.model}-${r.factor}-${idx}`} className="text-gray-300">
                    <td className="py-2.5 pr-4">{r.metric || r.factor}</td>
                    <td className="py-2.5 pr-4 text-gray-500">{r.model}</td>
                    <td className="py-2.5 pr-4 text-right font-medium text-white">{r.value ?? '—'}</td>
                    <td className="py-2.5 pr-4 text-right text-gray-500">{r.peer_median ?? '—'}</td>
                    <td className="py-2.5 pr-4 text-right text-gray-500">{r.peer_p95 ?? '—'}</td>
                    <td className="py-2.5 text-right font-semibold text-amber-400">{r.score.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* What I've done */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <MonitorSmartphone className="w-5 h-5 text-cyber-400" />
            My Activity by Type
          </h3>
          {typeData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">No activity recorded</p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={typeData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis
                    type="category" dataKey="name" stroke="#64748b" tick={{ fontSize: 10 }} width={110}
                    tickFormatter={(n: string) => (n.length > 15 ? n.slice(0, 15) + '…' : n)}
                  />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {typeData.map((_, i) => (
                      <Cell key={i} fill={['#06b6d4', '#22c55e', '#f59e0b', '#8b5cf6', '#ef4444', '#14b8a6', '#eab308', '#ec4899'][i % 8]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <CalendarDays className="w-5 h-5 text-matrix-400" />
            My Daily Activity
          </h3>
          {dailyData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">No activity recorded</p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dailyData}>
                  <defs>
                    <linearGradient id="workerDaily" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Area type="monotone" dataKey="count" stroke="#06b6d4" strokeWidth={2} fill="url(#workerDaily)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-surface-800">
            <div>
              <p className="text-xs text-gray-500">Events</p>
              <p className="text-sm font-bold text-white">{summary.total_events.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Active days</p>
              <p className="text-sm font-bold text-white">{summary.active_days}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Off-hours</p>
              <p className="text-sm font-bold text-white">{summary.off_hours_events.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Workstations</p>
              <p className="text-sm font-bold text-white">{summary.unique_workstations}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Alerts */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          Threats Flagged Against Me
          <span className="text-sm font-normal text-gray-500">({alerts.open_count} open)</span>
        </h3>
        {alerts.items.length === 0 ? (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-matrix-500/5 border border-matrix-500/20">
            <Activity className="w-5 h-5 text-matrix-400" />
            <p className="text-sm text-matrix-400">No open alerts. Your behaviour is within normal ranges.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {alerts.items.map((a) => (
              <div key={a.id} className="p-3.5 rounded-lg bg-surface-800/50 border border-surface-700/50">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-200">{a.title}</p>
                    <p className="text-xs text-gray-500 mt-1">{a.description}</p>
                    {a.created_at && (
                      <p className="text-xs text-gray-600 mt-1.5">
                        {new Date(a.created_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium border capitalize shrink-0 ${
                    severityBg[a.severity] || 'bg-gray-500/10 border-gray-500/20 text-gray-400'
                  }`}>
                    {a.severity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent activity */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-cyber-400" />
          My Recent Activity
          <span className="text-sm font-normal text-gray-500">
            ({activity?.total.toLocaleString()} total records)
          </span>
        </h3>
        {!activity || activity.items.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">No activity recorded</p>
        ) : (
          <div className="space-y-1.5">
            {activity.items.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-3 p-2.5 rounded-lg bg-surface-800/40 hover:bg-surface-800 transition-all"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-cyber-400 shrink-0" />
                <span className="text-sm text-gray-300 w-36 shrink-0">{item.label}</span>
                <span className="text-xs text-gray-500 flex-1 truncate">
                  {item.source || '—'}
                </span>
                <span className="text-xs text-gray-600 shrink-0">
                  {item.occurred_at ? new Date(item.occurred_at).toLocaleString() : '—'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
