import { useState, useEffect } from 'react';
import {
  getBaseline,
  computeBaselines,
  type BehavioralProfile,
  type BaselineComputeResult,
} from '../api/anomaly';
import { listEmployees, type Employee } from '../api/employees';
import {
  Users,
  Activity,
  Clock,
  TrendingUp,
  BarChart3,
  RefreshCw,
  Building2,
  Search,
  Database,
} from 'lucide-react';

export default function BehavioralAnalysis() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployee, setSelectedEmployee] = useState<string>('');
  const [profile, setProfile] = useState<BehavioralProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [computeResult, setComputeResult] = useState<BaselineComputeResult | null>(null);

  useEffect(() => {
    listEmployees({ limit: 500 }).then(setEmployees).catch(console.error);
  }, []);

  async function loadProfile(employeeId: string) {
    if (!employeeId) return;
    setLoading(true);
    try {
      const p = await getBaseline(employeeId);
      setProfile(p);
    } catch (err) {
      console.error('Failed to load profile:', err);
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (selectedEmployee) loadProfile(selectedEmployee);
  }, [selectedEmployee]);

  async function handleComputeBaselines() {
    setComputing(true);
    try {
      const result = await computeBaselines(selectedEmployee || undefined);
      setComputeResult(result);
      if (selectedEmployee) {
        await loadProfile(selectedEmployee);
      }
    } catch (err) {
      console.error('Failed to compute baselines:', err);
    } finally {
      setComputing(false);
    }
  }

  const baseline = profile?.baseline_data ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Behavioral Analysis</h1>
          <p className="text-gray-500 mt-1">Employee behavioral profiling and peer comparison analysis</p>
        </div>
        <button
          onClick={handleComputeBaselines}
          disabled={computing}
          className="flex items-center gap-2 px-4 py-2.5 bg-cyber-500/20 border border-cyber-500/30 
            text-cyber-400 rounded-lg font-medium hover:bg-cyber-500/30 transition-all duration-150 
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {computing ? (
            <div className="w-4 h-4 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          {computing ? 'Computing...' : (selectedEmployee ? 'Compute Baseline' : 'Compute All')}
        </button>
      </div>

      {computeResult && (
        <div className="p-4 rounded-lg bg-matrix-500/10 border border-matrix-500/20 flex items-center gap-3">
          <Database className="w-5 h-5 text-matrix-400" />
          <div>
            <p className="text-sm text-matrix-400 font-medium">
              {computeResult.message}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {computeResult.baselines_computed} baseline(s) computed
            </p>
          </div>
        </div>
      )}

      {/* Employee selector */}
      <div className="flex gap-3">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <select
              value={selectedEmployee}
              onChange={(e) => setSelectedEmployee(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-surface-900 border border-surface-800 rounded-lg text-gray-300
                focus:outline-none focus:border-cyber-500/50 transition-all appearance-none cursor-pointer"
            >
              <option value="">Select an employee to analyze...</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.full_name} — {emp.department || 'No Dept'} — {emp.employee_code}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : !selectedEmployee ? (
        <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
          <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">Select an employee to view their behavioral profile</p>
          <p className="text-gray-600 text-sm mt-1">Or click "Compute All" to generate baselines for everyone</p>
        </div>
      ) : !profile ? (
        <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
          <p className="text-gray-500">No behavioral profile found for this employee</p>
          <p className="text-gray-600 text-sm mt-1">Click "Compute Baseline" to generate one</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Activity Distribution */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyber-400" />
              Activity Distribution
            </h3>
            {baseline.activity_distribution ? (
              <div className="space-y-3">
                {Object.entries(baseline.activity_distribution as Record<string, number>)
                  .sort(([, a], [, b]) => b - a)
                  .map(([type, count]) => {
                    const total = Object.values(baseline.activity_distribution as Record<string, number>).reduce((a: number, b: number) => a + b, 0);
                    const pct = total > 0 ? (count / total * 100) : 0;
                    return (
                      <div key={type}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-300 capitalize">{type.replace(/_/g, ' ')}</span>
                          <span className="text-gray-500">{count} ({pct.toFixed(1)}%)</span>
                        </div>
                        <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-cyber-400 transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No activity distribution data</p>
            )}
          </div>

          {/* Temporal Profile */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-warning-400" />
              Temporal Profile
            </h3>
            {baseline.total_logs ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Daily Average</p>
                    <p className="text-lg font-bold text-white">{baseline.daily_avg as string}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Total Logs</p>
                    <p className="text-lg font-bold text-white">{baseline.total_logs as string}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Off-Hours Activity</p>
                    <p className="text-lg font-bold text-danger-400">{baseline.total_off_hours as string}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Off-Hours %</p>
                    <p className="text-lg font-bold text-warning-400">{baseline.off_hours_pct as string}%</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Late Night Events</p>
                    <p className="text-lg font-bold text-gray-200">{baseline.late_night_activity as string}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Weekend Activity</p>
                    <p className="text-lg font-bold text-gray-200">{baseline.weekend_activity as string}</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No temporal profile data</p>
            )}
          </div>

          {/* Peer Comparison */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-matrix-400" />
              Peer Comparison
            </h3>
            {baseline.peer_group ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-3">
                  <Building2 className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-400">Peer Group: {baseline.peer_group as string}</span>
                  <span className="text-xs text-gray-600">({baseline.peer_group_size as string} peers)</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-surface-800/50 border border-surface-700/50">
                    <p className="text-xs text-gray-500">Your Daily Avg</p>
                    <p className="text-lg font-bold text-cyber-400">{baseline.your_daily_avg as string}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50 border border-surface-700/50">
                    <p className="text-xs text-gray-500">Peer Daily Avg</p>
                    <p className="text-lg font-bold text-gray-200">{baseline.peer_daily_avg as string}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50 border border-surface-700/50">
                    <p className="text-xs text-gray-500">Your Off-Hours %</p>
                    <p className={`text-lg font-bold ${(baseline.your_off_hours_pct as number) > (baseline.peer_off_hours_pct as number) ? 'text-danger-400' : 'text-matrix-400'}`}>
                      {baseline.your_off_hours_pct as string}%
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50 border border-surface-700/50">
                    <p className="text-xs text-gray-500">Peer Off-Hours %</p>
                    <p className="text-lg font-bold text-gray-200">{baseline.peer_off_hours_pct as string}%</p>
                  </div>
                </div>
                <div className={`p-3 rounded-lg ${
                  (baseline.activity_vs_peer as number) > 0 ? 'bg-warning-500/10 border border-warning-500/20' : 'bg-matrix-500/10 border border-matrix-500/20'
                }`}>
                  <div className="flex items-center gap-2">
                    <TrendingUp className={`w-4 h-4 ${(baseline.activity_vs_peer as number) > 0 ? 'text-warning-400' : 'text-matrix-400'}`} />
                    <span className={`text-sm ${(baseline.activity_vs_peer as number) > 0 ? 'text-warning-400' : 'text-matrix-400'}`}>
                      {(baseline.activity_vs_peer as number) > 0 ? '+' : ''}{baseline.activity_vs_peer as string} vs peer average
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">
                {baseline.peer_group === null
                  ? 'Employee has no department or peers for comparison'
                  : 'No peer comparison data available'}
              </p>
            )}
          </div>

          {/* Statistical Baselines */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-purple-400" />
              Statistical Baselines
            </h3>
            {baseline.hourly_activity_mean !== undefined ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Hourly Mean</p>
                    <p className="text-lg font-bold text-gray-200">{baseline.hourly_activity_mean as string}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Hourly Std Dev</p>
                    <p className="text-lg font-bold text-gray-200">{baseline.hourly_activity_std as string}</p>
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-surface-800/50 border border-surface-700/50">
                  <p className="text-xs text-gray-500 mb-2">Z-Score Threshold</p>
                  <p className="text-2xl font-bold text-cyber-400">{baseline.z_score_threshold as string}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Values exceeding this threshold are flagged as anomalies
                  </p>
                </div>
                {(() => {
                  const anomalyHours = baseline.anomaly_hours as number[] | undefined;
                  return anomalyHours && anomalyHours.length > 0 ? (
                    <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/20">
                      <p className="text-sm text-danger-400 font-medium">Anomaly Hours Detected</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Hours: {anomalyHours.map(h => `${h}:00`).join(', ')}
                      </p>
                    </div>
                  ) : null;
                })()}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No statistical baseline data</p>
            )}
          </div>
        </div>
      )}

      {/* Profile metadata */}
      {profile?.generated_at && (
        <div className="text-xs text-gray-600 text-center">
          Profile generated: {new Date(profile.generated_at).toLocaleString()}
          {profile.updated_at && ` • Updated: ${new Date(profile.updated_at).toLocaleString()}`}
        </div>
      )}
    </div>
  );
}
