import { useState, useEffect, type ComponentType } from 'react';
import {
  detectAnomalies,
  listAnomalyAlerts,
  runMlDetection,
  getMlResults,
  type AnomalyDetectionResult,
  type AnomalySummaryItem,
  type MlDetectionResult,
  type MlEmployeeScore,
} from '../api/anomaly';
import {
  Activity,
  AlertTriangle,
  Shield,
  Search,
  Zap,
  Play,
  ChevronDown,
  Clock,
  BarChart3,
  TrendingUp,
  Brain,
  Target,
  Gauge,
  Fingerprint,
} from 'lucide-react';

const severityColors: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  medium: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  low: 'bg-matrix-500/10 text-matrix-400 border-matrix-500/20',
  informational: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
};

const anomalyIcons: Record<string, ComponentType<{ className?: string }>> = {
  volume_anomaly: TrendingUp,
  hourly_spike: BarChart3,
  off_hours_data_transfer: Shield,
  usb_device_spike: Activity,
  privilege_escalation: Shield,
  large_file_downloads: Activity,
  late_night_activity: Clock,
  concentrated_weekend_access: Calendar,
};

function Calendar({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  );
}

export default function AnomalyDetection() {
  const [result, setResult] = useState<AnomalyDetectionResult | null>(null);
  const [anomalyAlerts, setAnomalyAlerts] = useState<AnomalySummaryItem[]>([]);
  const [mlResult, setMlResult] = useState<MlDetectionResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [mlRunning, setMlRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'alerts' | 'details' | 'ml'>('overview');
  const [expandedEmployee, setExpandedEmployee] = useState<string | null>(null);

  useEffect(() => {
    loadAnomalyAlerts();
    loadMlResults();
  }, []);

  async function loadAnomalyAlerts() {
    try {
      const alerts = await listAnomalyAlerts();
      setAnomalyAlerts(alerts);
    } catch (err) {
      console.error('Failed to load anomaly alerts:', err);
    }
  }

  async function handleScan() {
    setScanning(true);
    try {
      const res = await detectAnomalies({ days: 30 });
      setResult(res);
      await loadAnomalyAlerts();
    } catch (err) {
      console.error('Anomaly detection failed:', err);
    } finally {
      setScanning(false);
    }
  }

  async function loadMlResults() {
    try {
      const res = await getMlResults();
      if (res) setMlResult(res);
    } catch (err) {
      console.error('Failed to load ML results:', err);
    }
  }

  async function handleMlRun() {
    setMlRunning(true);
    try {
      const res = await runMlDetection(30, 0.05);
      setMlResult(res);
    } catch (err) {
      console.error('ML detection failed:', err);
    } finally {
      setMlRunning(false);
    }
  }

  const totalAnomalies = result?.details.reduce(
    (sum, emp) => sum + emp.anomalies.length, 0
  ) ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Anomaly Detection</h1>
          <p className="text-gray-500 mt-1">
            Detect behavioral anomalies using statistical analysis and rule-based engines
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center gap-2 px-5 py-2.5 bg-cyber-500/20 border border-cyber-500/30 
            text-cyber-400 rounded-lg font-medium hover:bg-cyber-500/30 transition-all duration-150 
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {scanning ? (
            <div className="w-4 h-4 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          {scanning ? 'Scanning...' : 'Run Detection'}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyber-500/10">
              <Search className="w-5 h-5 text-cyber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{result?.scanned_employees ?? '—'}</p>
              <p className="text-xs text-gray-500">Employees Scanned</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-warning-500/10">
              <AlertTriangle className="w-5 h-5 text-warning-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{result?.employees_with_anomalies ?? '—'}</p>
              <p className="text-xs text-gray-500">With Anomalies</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-danger-500/10">
              <Activity className="w-5 h-5 text-danger-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{totalAnomalies || '—'}</p>
              <p className="text-xs text-gray-500">Anomalies Found</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-matrix-500/10">
              <Zap className="w-5 h-5 text-matrix-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{result?.alerts_created ?? anomalyAlerts.length}</p>
              <p className="text-xs text-gray-500">Alerts Generated</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-surface-900 rounded-xl border border-surface-800">
        {[
          { key: 'overview' as const, label: 'Overview', icon: BarChart3 },
          { key: 'alerts' as const, label: 'Anomaly Alerts', icon: AlertTriangle },
          { key: 'details' as const, label: 'Detection Details', icon: Activity },
          { key: 'ml' as const, label: 'ML Detection', icon: Brain },
        ].map((tab) => {
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

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Detection Engine Overview</h3>
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 rounded-lg bg-surface-800/50 border border-surface-700/50">
              <div className="p-2 rounded-lg bg-cyber-500/10">
                <BarChart3 className="w-5 h-5 text-cyber-400" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-200">Statistical Anomaly Detection</h4>
                <p className="text-xs text-gray-500 mt-1">
                  Z-score and IQR-based analysis of activity volumes, hourly distributions, and 
                  daily patterns. Detects unusual spikes and outliers in employee behavior.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-4 rounded-lg bg-surface-800/50 border border-surface-700/50">
              <div className="p-2 rounded-lg bg-warning-500/10">
                <Shield className="w-5 h-5 text-warning-400" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-200">Rule-Based Detection</h4>
                <p className="text-xs text-gray-500 mt-1">
                  Domain-specific rules for off-hours data transfers, USB device spikes, 
                  privilege escalation, and large file downloads.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-4 rounded-lg bg-surface-800/50 border border-surface-700/50">
              <div className="p-2 rounded-lg bg-danger-500/10">
                <Clock className="w-5 h-5 text-danger-400" />
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-200">Temporal Pattern Analysis</h4>
                <p className="text-xs text-gray-500 mt-1">
                  Identifies late-night activity, concentrated weekend access, and 
                  irregular time-based patterns that deviate from normal work hours.
                </p>
              </div>
            </div>
          </div>
          {result && (
            <div className="mt-6 p-4 rounded-lg bg-matrix-500/10 border border-matrix-500/20">
              <div className="flex items-center gap-2 text-matrix-400">
                <Play className="w-4 h-4" />
                <span className="text-sm font-medium">
                  Last scan completed: {result.scanned_employees} employees scanned, 
                  {result.alerts_created} new alerts created
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'alerts' && (
        <div className="space-y-3">
          {anomalyAlerts.length === 0 ? (
            <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
              <CheckCircleIcon className="w-12 h-12 text-matrix-400 mx-auto mb-3" />
              <p className="text-gray-500">No anomaly alerts</p>
              <p className="text-gray-600 text-sm mt-1">Run anomaly detection to scan for threats</p>
            </div>
          ) : (
            anomalyAlerts.map((alert) => (
              <div
                key={alert.id}
                className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg border ${severityColors[alert.severity] || severityColors.informational}`}>
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-sm font-semibold text-gray-200">{alert.title}</h4>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize border ${severityColors[alert.severity]}`}>
                        {alert.severity}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span className="px-2 py-0.5 rounded bg-surface-800">{alert.anomaly_type}</span>
                      <span>{new Date(alert.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'ml' && (
        <div className="space-y-6">
          {/* ML header */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-violet-500/10 border border-violet-500/20">
                  <Brain className="w-6 h-6 text-violet-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Machine Learning Anomaly Detection</h3>
                  <p className="text-sm text-gray-500 mt-1 max-w-xl">
                    Unsupervised <span className="text-violet-400">Isolation Forest</span> model trained on
                    per-employee behavioral features (activity volume, timing, devices, baseline deviation)
                    to surface statistically unusual insider behavior.
                  </p>
                  <p className="text-xs text-gray-600 mt-2">
                    Model: Isolation Forest v1 · {mlResult?.scanned_employees ?? 0} employees scored · 
                    contamination {((mlResult?.contamination ?? 0.05) * 100).toFixed(0)}%
                    {mlResult?.employees_no_activity ? ` · ${mlResult.employees_no_activity} with no activity excluded` : ''}
                    {mlResult && ` · last run ${new Date(mlResult.generated_at).toLocaleString()}`}
                  </p>
                </div>
              </div>
              <button
                onClick={handleMlRun}
                disabled={mlRunning}
                className="flex items-center gap-2 px-5 py-2.5 bg-violet-500/20 border border-violet-500/30 
                  text-violet-400 rounded-lg font-medium hover:bg-violet-500/30 transition-all duration-150 
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {mlRunning ? (
                  <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Brain className="w-4 h-4" />
                )}
                {mlRunning ? 'Training & Scoring...' : 'Run ML Detection'}
              </button>
            </div>
          </div>

          {/* ML summary cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-violet-500/10">
                  <Target className="w-5 h-5 text-violet-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{mlResult?.outliers_detected ?? '—'}</p>
                  <p className="text-xs text-gray-500">Behavioral Outliers</p>
                </div>
              </div>
            </div>
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-warning-500/10">
                  <Gauge className="w-5 h-5 text-warning-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{mlResult?.average_ml_score ?? '—'}</p>
                  <p className="text-xs text-gray-500">Avg ML Risk Score</p>
                </div>
              </div>
            </div>
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-cyber-500/10">
                  <Fingerprint className="w-5 h-5 text-cyber-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{mlResult?.scanned_employees ?? '—'}</p>
                  <p className="text-xs text-gray-500">Employees Scored</p>
                </div>
              </div>
            </div>
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-4 hover:border-surface-700 transition-all">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-matrix-500/10">
                  <Zap className="w-5 h-5 text-matrix-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">
                    {mlResult ? `${Math.max(0, mlResult.scanned_employees - mlResult.outliers_detected)}` : '—'}
                  </p>
                  <p className="text-xs text-gray-500">Normal Behavior</p>
                </div>
              </div>
            </div>
          </div>

          {/* Ground truth panel */}
          {mlResult?.ground_truth && mlResult.ground_truth.insiders_in_dataset > 0 && (
            <div className="bg-surface-900 rounded-xl border border-matrix-500/20 p-4">
              <div className="flex items-center gap-2 text-matrix-400">
                <Target className="w-4 h-4" />
                <span className="text-sm font-medium">Ground-Truth Validation</span>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                {mlResult.ground_truth.insiders_in_dataset} known insiders in dataset ·
                {mlResult.ground_truth.found_in_outliers} flagged as outliers ·
                {mlResult.ground_truth.found_in_top20} in top-20 ·
                Hit rate (top-20): {mlResult.ground_truth.hit_rate_top20 ?? 'N/A'}
              </p>
            </div>
          )}

          {/* Top flagged table */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden">
            <div className="px-5 py-4 border-b border-surface-800 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Highest ML Risk Employees</h3>
              <span className="text-xs text-gray-500">Top {mlResult?.top_flagged.length ?? 0} of {mlResult?.scanned_employees ?? 0}</span>
            </div>
            {!mlResult ? (
              <div className="text-center py-14">
                <Brain className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500">No ML results yet</p>
                <button
                  onClick={handleMlRun}
                  className="mt-3 px-4 py-2 bg-violet-500/20 border border-violet-500/30 text-violet-400 rounded-lg text-sm hover:bg-violet-500/30 transition-all"
                >
                  Train & Run Isolation Forest
                </button>
              </div>
            ) : mlResult.top_flagged.length === 0 ? (
              <div className="text-center py-14">
                <CheckCircleIcon className="w-10 h-10 text-matrix-400 mx-auto mb-3" />
                <p className="text-gray-500">No outliers flagged</p>
              </div>
            ) : (
              <div className="divide-y divide-surface-800">
                {mlResult.top_flagged.map((emp, idx) => (
                  <MlEmployeeRow key={emp.employee_id} emp={emp} rank={idx + 1} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'details' && (
        <div className="space-y-4">
          {!result ? (
            <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
              <Search className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">No detection results</p>
              <button
                onClick={handleScan}
                className="mt-3 px-4 py-2 bg-cyber-500/20 border border-cyber-500/30 text-cyber-400 rounded-lg text-sm hover:bg-cyber-500/30 transition-all"
              >
                Run Anomaly Detection
              </button>
            </div>
          ) : result.details.length === 0 ? (
            <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
              <CheckCircleIcon className="w-12 h-12 text-matrix-400 mx-auto mb-3" />
              <p className="text-gray-500">No anomalies detected</p>
              <p className="text-gray-600 text-sm mt-1">All employees are behaving within normal patterns</p>
            </div>
          ) : (
            result.details.map((empData) => (
              <div
                key={empData.employee_id}
                className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden hover:border-surface-700 transition-all"
              >
                <button
                  onClick={() => setExpandedEmployee(
                    expandedEmployee === empData.employee_id ? null : empData.employee_id
                  )}
                  className="w-full flex items-center justify-between p-4 hover:bg-surface-800/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-danger-500/10 flex items-center justify-center">
                      <span className="text-sm font-bold text-danger-400">
                        {empData.employee_name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div className="text-left">
                      <p className="text-sm font-medium text-gray-200">{empData.employee_name}</p>
                      <p className="text-xs text-gray-500">
                        {empData.anomalies.length} anomaly pattern{empData.anomalies.length !== 1 ? 's' : ''} detected
                      </p>
                    </div>
                  </div>
                  <ChevronDown
                    className={`w-5 h-5 text-gray-500 transition-transform ${
                      expandedEmployee === empData.employee_id ? 'rotate-180' : ''
                    }`}
                  />
                </button>

                {expandedEmployee === empData.employee_id && (
                  <div className="px-4 pb-4 space-y-3">
                    {empData.anomalies.map((anomaly, idx) => {
                      const Icon = anomalyIcons[anomaly.type] || AlertTriangle;
                      return (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-surface-800/50 border border-surface-700/50"
                        >
                          <div className="flex items-start gap-3">
                            <div className={`p-1.5 rounded-lg ${severityColors[anomaly.severity] || severityColors.informational}`}>
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-gray-200">
                                  {anomaly.type.replace(/_/g, ' ')}
                                </span>
                                <span className={`px-1.5 py-0.5 rounded text-xs font-medium capitalize border ${
                                  severityColors[anomaly.severity] || severityColors.informational
                                }`}>
                                  {anomaly.severity}
                                </span>
                              </div>
                              <p className="text-xs text-gray-400 mt-1">{anomaly.description}</p>
                              <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                                <span className="flex items-center gap-1">
                                  Confidence: {(anomaly.confidence * 100).toFixed(0)}%
                                </span>
                                {!!anomaly.evidence?.count && (
                                  <span>{String(anomaly.evidence.count)} events</span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function MlEmployeeRow({ emp, rank }: { emp: MlEmployeeScore; rank: number }) {
  const scoreColor = emp.severity === 'critical' ? 'bg-red-500' : emp.severity === 'high' ? 'bg-amber-500' : emp.severity === 'medium' ? 'bg-cyan-500' : 'bg-matrix-500';

  return (
    <div className="p-4 hover:bg-surface-800/30 transition-colors">
      <div className="flex items-center gap-4 flex-wrap">
        <span className="w-7 text-center text-sm font-bold text-gray-600">{rank}</span>
        <div className="flex-1 min-w-[180px]">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-gray-200">{emp.employee_name}</p>
            <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize border ${severityColors[emp.severity] || severityColors.informational}`}>
              {emp.severity}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {emp.employee_code} · {emp.department ?? '—'}{emp.designation ? ` · ${emp.designation}` : ''}
          </p>
        </div>
        <div className="w-44">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-gray-500">ML Risk</span>
            <span className="font-semibold text-white">{emp.ml_score.toFixed(1)}</span>
          </div>
          <div className="h-1.5 rounded-full bg-surface-800 overflow-hidden">
            <div className={`h-full rounded-full ${scoreColor}`} style={{ width: `${Math.min(100, emp.ml_score)}%` }} />
          </div>
        </div>
        <div className="w-64">
          {emp.top_factors.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {emp.top_factors.slice(0, 2).map((f) => (
                <span key={f.feature} className="px-2 py-0.5 rounded bg-surface-800 border border-surface-700 text-[11px] text-gray-400">
                  {featureLabel(f.feature)}: {f.value}×
                </span>
              ))}
              {emp.top_factors.length > 2 && (
                <span className="text-[11px] text-gray-600">+{emp.top_factors.length - 2} more</span>
              )}
            </div>
          ) : (
            <span className="text-[11px] text-gray-600">within population norms</span>
          )}
        </div>
      </div>
    </div>
  );
}

function featureLabel(feature: string): string {
  const labels: Record<string, string> = {
    total_logs: 'logs',
    daily_avg: 'daily avg',
    login_count: 'logins',
    data_transfer_count: 'xfers',
    usb_count: 'USB',
    off_hours_pct: 'off-hours %',
    late_night_count: 'late-night',
    weekend_pct: 'weekend %',
    unique_pcs: 'devices',
    unique_hours: 'active hrs',
    daily_std: 'volatility',
    data_transfer_off_hours_pct: 'xfer off-hrs %',
    avg_data_per_day: 'xfer/day',
    baseline_deviation: 'deviation',
  };
  return labels[feature] ?? feature.replace(/_/g, ' ');
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
