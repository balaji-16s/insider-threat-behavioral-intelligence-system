import { Fragment, useEffect, useState } from 'react';
import {
  runUebaPipeline, getUebaOverview,
  type UebaPipelineResult, type UebaOverview as UebaOverviewType, type UebaOverviewItem,
} from '../api/ueba';
import {
  Radar, Play, Users, Database, Zap, ShieldAlert, AlertTriangle, ChevronDown,
  BrainCog, Target, CheckCircle, TrendingUp,
} from 'lucide-react';

const riskColors: Record<string, string> = {
  low: 'bg-matrix-500/10 text-matrix-400 border-matrix-500/20',
  medium: 'bg-cyber-500/10 text-cyber-400 border-cyber-500/20',
  high: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  critical: 'bg-danger-500/10 text-danger-400 border-danger-500/20',
};

const riskBarColors: Record<string, string> = {
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

const MODEL_LABELS: Record<string, string> = {
  data_exfiltration: 'Data Exfiltration',
  off_hours_access: 'Off-Hours Access',
  privilege_abuse: 'Privilege Abuse',
  policy_violation: 'Policy Violation',
  behavioral_deviation: 'Behavioral Deviation',
};

export default function UebaIntelligence() {
  const [overview, setOverview] = useState<UebaOverviewType | null>(null);
  const [pipelineResult, setPipelineResult] = useState<UebaPipelineResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    loadOverview();
  }, []);

  async function loadOverview() {
    setLoading(true);
    try {
      const data = await getUebaOverview(30, 200);
      setOverview(data);
    } catch (err) {
      console.error('Failed to load UEBA overview:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunPipeline() {
    setRunning(true);
    setPipelineResult(null);
    try {
      const result = await runUebaPipeline(30);
      setPipelineResult(result);
      await loadOverview();
    } catch (err) {
      console.error('Failed to run UEBA pipeline:', err);
    } finally {
      setRunning(false);
    }
  }

  const items = overview?.items ?? [];
  const withBaseline = items.filter((i) => i.baseline_status === 'available').length;
  const withAnomalies = items.filter((i) => i.open_anomaly_alerts > 0).length;
  const highRisk = items.filter(
    (i) => i.risk_level === 'high' || i.risk_level === 'critical'
  ).length;
  const avgThreat = items.length
    ? items.reduce((sum, i) => sum + (i.threat_score ?? 0), 0) / items.length
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">UEBA Intelligence</h1>
          <p className="text-gray-500 mt-1">
            User &amp; Entity Behavior Analytics — baselines, anomalies, and insider threat in one view
          </p>
        </div>
        <button
          onClick={handleRunPipeline}
          disabled={running}
          className="flex items-center gap-2 px-5 py-2.5 bg-cyber-500/20 border border-cyber-500/30 
            text-cyber-400 rounded-lg font-medium hover:bg-cyber-500/30 transition-all duration-150 
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {running ? (
            <div className="w-4 h-4 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {running ? 'Running Pipeline...' : 'Run UEBA Pipeline'}
        </button>
      </div>

      {/* Pipeline result */}
      {pipelineResult && (
        <div className="p-4 rounded-lg bg-matrix-500/10 border border-matrix-500/20 flex items-start gap-3">
          <CheckCircle className="w-5 h-5 text-matrix-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-matrix-400 font-medium">{pipelineResult.message}</p>
            <div className="flex flex-wrap gap-x-5 gap-y-1 mt-1.5 text-xs text-gray-500">
              <span>Baselines: {pipelineResult.baselines_computed}</span>
              <span>Scanned: {pipelineResult.employees_scanned}</span>
              <span>With anomalies: {pipelineResult.employees_with_anomalies}</span>
              <span>Alerts: {pipelineResult.alerts_created}</span>
              <span>Risk scores: {pipelineResult.risk_scores_calculated}</span>
              <span>Avg threat: {pipelineResult.average_threat_score}</span>
            </div>
          </div>
        </div>
      )}

      {/* Pipeline steps */}
      <div className="bg-surface-900 rounded-xl border border-surface-800 p-5">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <BrainCog className="w-5 h-5 text-purple-400" />
          Intelligence Pipeline
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { step: '1', title: 'Behavioral Baselines', desc: 'Statistical profiles, temporal patterns, peer comparison', icon: Database, color: 'text-cyber-400 bg-cyber-500/10' },
            { step: '2', title: 'Anomaly Detection', desc: 'Z-score / IQR, rule-based, and temporal analysis engines', icon: Zap, color: 'text-warning-400 bg-warning-500/10' },
            { step: '3', title: 'Threat Assessment', desc: '5 weighted insider-threat models per employee', icon: Target, color: 'text-purple-400 bg-purple-500/10' },
            { step: '4', title: 'Risk Persistence', desc: 'Scores stored and tracked over time for analytics', icon: Radar, color: 'text-danger-400 bg-danger-500/10' },
          ].map((s) => {
            const Icon = s.icon;
            return (
              <div key={s.step} className="p-4 rounded-lg bg-surface-800/50 border border-surface-700/50">
                <div className={`inline-flex p-2 rounded-lg mb-3 ${s.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-gray-500">Step {s.step}</span>
                </div>
                <h4 className="text-sm font-medium text-gray-200 mt-0.5">{s.title}</h4>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">{s.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyber-500/10">
              <Users className="w-5 h-5 text-cyber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{overview?.total_employees ?? '—'}</p>
              <p className="text-xs text-gray-500">Employees Tracked</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-matrix-500/10">
              <Database className="w-5 h-5 text-matrix-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{withBaseline}</p>
              <p className="text-xs text-gray-500">With Baselines</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-warning-500/10">
              <AlertTriangle className="w-5 h-5 text-warning-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{withAnomalies}</p>
              <p className="text-xs text-gray-500">Open Anomaly Alerts</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-danger-500/10">
              <ShieldAlert className="w-5 h-5 text-danger-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{highRisk}</p>
              <p className="text-xs text-gray-500">High / Critical Risk</p>
            </div>
          </div>
        </div>
      </div>

      {/* Overview table */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
          <Radar className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">No UEBA data available</p>
          <p className="text-gray-600 text-sm mt-1">Run the UEBA pipeline to compute profiles and risk scores</p>
        </div>
      ) : (
        <div className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-800 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Radar className="w-5 h-5 text-cyber-400" />
              Consolidated UEBA Overview
            </h3>
            <div className="text-xs text-gray-500">
              Avg threat score: <span className="text-cyber-400 font-medium">{avgThreat.toFixed(1)}</span>
              {overview?.generated_at && (
                <span className="ml-3">Generated: {new Date(overview.generated_at).toLocaleString()}</span>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-800">
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Employee</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Score</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Threat</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Anomalies</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Baseline</th>
                  <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800">
                {items.map((item: UebaOverviewItem) => {
                  const isOpen = expanded === item.employee_id;
                  return (
                    <Fragment key={item.employee_id}>
                      <tr
                        className="hover:bg-surface-800/50 transition-colors cursor-pointer"
                        onClick={() => setExpanded(isOpen ? null : item.employee_id)}
                      >
                        <td className="px-6 py-3">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                              item.risk_level === 'critical' || item.risk_level === 'high'
                                ? 'bg-danger-500/10' : 'bg-cyber-500/10'
                            }`}>
                              <span className={`text-xs font-bold ${
                                item.risk_level === 'critical' || item.risk_level === 'high'
                                  ? 'text-danger-400' : 'text-cyber-400'
                              }`}>
                                {item.employee_name.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-200">{item.employee_name}</p>
                              <p className="text-xs text-gray-500">{item.department || '—'} • {item.employee_code}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {item.risk_score === null ? (
                            <span className="text-xs text-gray-600">Not scored</span>
                          ) : (
                            <div className="flex items-center gap-2">
                              <div className="w-20 h-1.5 bg-surface-700 rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full"
                                  style={{ width: `${item.risk_score}%`, backgroundColor: riskBarColors[item.risk_level || 'low'] }}
                                />
                              </div>
                              <span className={`text-sm font-bold ${riskText[item.risk_level || ''] || 'text-gray-300'}`}>
                                {item.risk_score.toFixed(1)}
                              </span>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {item.threat_score === null ? (
                            <span className="text-xs text-gray-600">—</span>
                          ) : (
                            <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize border ${
                              riskColors[item.threat_level || 'low'] || riskColors.low
                            }`}>
                              {item.threat_score.toFixed(0)} • {item.threat_level}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 text-sm font-medium ${
                            item.open_anomaly_alerts > 0 ? 'text-warning-400' : 'text-gray-600'
                          }`}>
                            <AlertTriangle className="w-3.5 h-3.5" />
                            {item.open_anomaly_alerts}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            item.baseline_status === 'available'
                              ? 'bg-matrix-500/10 text-matrix-400 border border-matrix-500/20'
                              : 'bg-gray-500/10 text-gray-500 border border-gray-500/20'
                          }`}>
                            {item.baseline_status}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-right">
                          <ChevronDown className={`w-4 h-4 text-gray-500 inline transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                        </td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={6} className="px-6 py-4 bg-surface-950/50">
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                              {Object.entries(item.model_scores).map(([model, data]) => (
                                <div key={model} className="p-3 rounded-lg bg-surface-800/60 border border-surface-700/50">
                                  <p className="text-xs text-gray-500 capitalize">{MODEL_LABELS[model] || model.replace(/_/g, ' ')}</p>
                                  <div className="flex items-center gap-2 mt-2">
                                    <div className="flex-1 h-1.5 bg-surface-700 rounded-full overflow-hidden">
                                      <div
                                        className="h-full rounded-full"
                                        style={{ width: `${data.score}%`, backgroundColor: riskBarColors[data.level] || '#6b7280' }}
                                      />
                                    </div>
                                    <span className={`text-sm font-bold ${
                                      data.score >= 50 ? 'text-danger-400' : data.score >= 25 ? 'text-warning-400' : 'text-matrix-400'
                                    }`}>
                                      {data.score.toFixed(0)}
                                    </span>
                                  </div>
                                  <p className="text-[10px] text-gray-600 mt-1">
                                    {Object.keys(data.factors ?? {}).length} active factor(s)
                                  </p>
                                </div>
                              ))}
                              {Object.keys(item.model_scores).length === 0 && (
                                <p className="text-xs text-gray-600 col-span-full">No threat model data available</p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-6 text-xs text-gray-500">
        <TrendingUp className="w-4 h-4 text-cyber-400" />
        <span>Click any row to expand threat model scores</span>
        <span className="text-gray-700">|</span>
        <span>Risk score is the persisted engine score; threat score is the live assessment</span>
      </div>
    </div>
  );
}
