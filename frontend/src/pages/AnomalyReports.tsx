import { useState, useEffect } from 'react';
import {
  getAnomalyReport,
  getEmployeeReport,
  downloadAnomalyReport,
  downloadEmployeeReport,
  type AnomalyReport,
  type EmployeeReport,
} from '../api/reports';
import {
  getTopThreats,
  getEmployeeThreat,
  type ThreatAssessmentResult,
} from '../api/anomaly';
import { listEmployees, type Employee } from '../api/employees';
import {
  FileText,
  Users,
  Shield,
  TrendingUp,
  BarChart3,
  Search,
  Target,
  CheckCircle,
  FileDown,
  FileSpreadsheet,
} from 'lucide-react';

const riskColors: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  medium: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  low: 'bg-matrix-500/10 text-matrix-400 border-matrix-500/20',
};

const riskBarColors: Record<string, string> = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#06b6d4',
  low: '#22c55e',
};

export default function AnomalyReports() {
  const [report, setReport] = useState<AnomalyReport | null>(null);
  const [topThreats, setTopThreats] = useState<ThreatAssessmentResult[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [employeeReport, setEmployeeReport] = useState<EmployeeReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'org' | 'top_threats' | 'employee'>('org');

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [r, t, e] = await Promise.all([
          getAnomalyReport(30, true),
          getTopThreats(20),
          listEmployees({ limit: 500 }),
        ]);
        setReport(r);
        setTopThreats(t);
        setEmployees(e);
      } catch (err) {
        console.error('Failed to load report data:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function loadEmployeeReport(employeeId: string) {
    if (!employeeId) return;
    try {
      const [rep] = await Promise.all([
        getEmployeeReport(employeeId, 30),
        getEmployeeThreat(employeeId, 30),
      ]);
      setEmployeeReport(rep);
    } catch (err) {
      console.error('Failed to load employee report:', err);
    }
  }

  useEffect(() => {
    if (selectedEmployee) loadEmployeeReport(selectedEmployee);
  }, [selectedEmployee]);

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const tabs = [
    { key: 'org' as const, label: 'Organization Report', icon: BarChart3 },
    { key: 'top_threats' as const, label: 'Top Threats', icon: Target },
    { key: 'employee' as const, label: 'Employee Report', icon: Users },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Anomaly Reports</h1>
          <p className="text-gray-500 mt-1">Comprehensive threat intelligence reports and employee risk analysis</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-surface-900 rounded-xl border border-surface-800">
        {tabs.map((tab) => {
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

      {activeTab === 'org' && report && (
        <div className="space-y-6">
          {/* Report header */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <FileText className="w-6 h-6 text-cyber-400" />
                <div>
                  <h3 className="text-lg font-semibold text-white">Anomaly Report</h3>
                  <p className="text-xs text-gray-500">
                    Generated: {new Date(report.generated_at).toLocaleString()} 
                    {' '}&bull; Period: {report.report_period_days} days
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => downloadAnomalyReport('pdf', report.report_period_days)}
                  className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-danger-500/10 border border-danger-500/30
                    text-danger-400 text-sm font-medium hover:bg-danger-500/20 transition-all"
                >
                  <FileDown className="w-4 h-4" /> PDF
                </button>
                <button
                  onClick={() => downloadAnomalyReport('xlsx', report.report_period_days)}
                  className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-matrix-500/10 border border-matrix-500/30
                    text-matrix-400 text-sm font-medium hover:bg-matrix-500/20 transition-all"
                >
                  <FileSpreadsheet className="w-4 h-4" /> Excel
                </button>
              </div>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                <p className="text-2xl font-bold text-white">{report.summary.total_employees}</p>
                <p className="text-xs text-gray-500">Employees</p>
              </div>
              <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                <p className="text-2xl font-bold text-warning-400">{report.summary.total_alerts}</p>
                <p className="text-xs text-gray-500">Total Alerts</p>
              </div>
              <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                <p className="text-2xl font-bold text-danger-400">{report.summary.critical_alerts}</p>
                <p className="text-xs text-gray-500">Critical</p>
              </div>
              <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                <p className="text-2xl font-bold text-cyber-400">{report.summary.open_alerts}</p>
                <p className="text-xs text-gray-500">Open Alerts</p>
              </div>
              <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                <p className="text-2xl font-bold text-white">{report.summary.total_incidents}</p>
                <p className="text-xs text-gray-500">Incidents</p>
              </div>
              <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                <p className="text-2xl font-bold text-white">{report.summary.total_activity_logs.toLocaleString()}</p>
                <p className="text-xs text-gray-500">Activities</p>
              </div>
            </div>
          </div>

          {/* Alerts breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Alert Severity Breakdown</h3>
              <div className="space-y-3">
                {Object.entries(report.alerts.by_severity).map(([severity, count]) => {
                  const total = Object.values(report.alerts.by_severity).reduce((a, b) => a + b, 0);
                  const pct = total > 0 ? (count / total * 100) : 0;
                  return (
                    <div key={severity}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-300 capitalize">{severity}</span>
                        <span className="text-gray-500">{count} ({(pct).toFixed(1)}%)</span>
                      </div>
                      <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: riskBarColors[severity] || '#6b7280',
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Anomaly Type Distribution</h3>
              {Object.keys(report.alerts.by_anomaly_type).length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-8">No anomaly types recorded</p>
              ) : (
                <div className="space-y-3">
                  {Object.entries(report.alerts.by_anomaly_type).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between p-2 rounded-lg bg-surface-800/50">
                      <span className="text-sm text-gray-300 capitalize">{type.replace(/_/g, ' ')}</span>
                      <span className="text-sm font-medium text-gray-200">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Incidents */}
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Incident Status Breakdown</h3>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(report.incidents.by_status).map(([status, count]) => (
                  <div key={status} className="p-3 rounded-lg bg-surface-800/50 text-center">
                    <p className="text-xl font-bold text-white">{count}</p>
                    <p className="text-xs text-gray-500 capitalize">{status}</p>
                  </div>
                ))}
              </div>
              {report.incidents.avg_resolution_hours && (
                <div className="mt-3 p-3 rounded-lg bg-cyber-500/10 border border-cyber-500/20">
                  <p className="text-xs text-gray-500">Avg Resolution Time</p>
                  <p className="text-lg font-bold text-cyber-400">{report.incidents.avg_resolution_hours}h</p>
                </div>
              )}
            </div>

            {/* Risk Distribution */}
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Risk Score Distribution</h3>
              <div className="space-y-3">
                {Object.entries(report.risk_distribution).map(([level, count]) => {
                  const total = Object.values(report.risk_distribution).reduce((a, b) => a + b, 0);
                  const pct = total > 0 ? (count / total * 100) : 0;
                  return (
                    <div key={level}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-300 capitalize">{level}</span>
                        <span className="text-gray-500">{count} employees</span>
                      </div>
                      <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: riskBarColors[level] || '#6b7280',
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* High Risk Employees */}
          {report.high_risk_employees.length > 0 && (
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-danger-400" />
                High Risk Employees
              </h3>
              <div className="space-y-2">
                {report.high_risk_employees.map((emp) => (
                  <div
                    key={emp.id}
                    className="flex items-center gap-4 p-3 rounded-lg bg-surface-800/50 border border-surface-700/50"
                  >
                    <div className="w-8 h-8 rounded-full bg-danger-500/10 flex items-center justify-center">
                      <span className="text-xs font-bold text-danger-400">{emp.name.charAt(0)}</span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-200">{emp.name}</p>
                      <p className="text-xs text-gray-500">{emp.department} • {emp.designation}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-2 bg-surface-700 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${emp.risk_score}%`,
                            backgroundColor: riskBarColors[emp.risk_level] || '#6b7280',
                          }}
                        />
                      </div>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize border ${
                        riskColors[emp.risk_level] || riskColors.low
                      }`}>
                        {emp.risk_level}
                      </span>
                      <span className="text-sm font-bold text-gray-200 w-12 text-right">
                        {emp.risk_score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Threat Assessment Summary */}
          {report.threat_assessment && (
            <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-cyber-400" />
                Threat Assessment Summary
              </h3>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                  <p className="text-2xl font-bold text-white">{report.threat_assessment.total_assessed}</p>
                  <p className="text-xs text-gray-500">Employees Assessed</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                  <p className="text-2xl font-bold text-cyber-400">{report.threat_assessment.average_threat_score}</p>
                  <p className="text-xs text-gray-500">Avg Threat Score</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-800/50 text-center">
                  <p className="text-2xl font-bold text-danger-400">{report.threat_assessment.top_threats.length}</p>
                  <p className="text-xs text-gray-500">Top Threats Listed</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'top_threats' && (
        <div className="space-y-3">
          {topThreats.length === 0 ? (
            <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
              <CheckCircle className="w-12 h-12 text-matrix-400 mx-auto mb-3" />
              <p className="text-gray-500">No top threats identified</p>
            </div>
          ) : (
            topThreats.map((threat, idx) => (
              <div
                key={threat.employee_id}
                className="bg-surface-900 rounded-xl border border-surface-800 p-5 hover:border-surface-700 transition-all"
              >
                <div className="flex items-start gap-4">
                  <div className={`flex items-center justify-center w-8 h-8 rounded-lg text-sm font-bold ${
                    idx < 3 ? 'bg-danger-500/10 text-danger-400 border border-danger-500/20' : 'bg-surface-800 text-gray-400'
                  }`}>
                    #{idx + 1}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-danger-500/10 flex items-center justify-center">
                        <span className="text-sm font-bold text-danger-400">
                          {threat.employee_name?.charAt(0) || '?'}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-200">{threat.employee_name || 'Unknown'}</p>
                        <p className="text-xs text-gray-500">{threat.department || 'No department'}</p>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${threat.threat_score}%`,
                                backgroundColor: riskBarColors[threat.threat_level] || '#6b7280',
                              }}
                            />
                          </div>
                          <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize border ${
                            riskColors[threat.threat_level] || riskColors.low
                          }`}>
                            {threat.threat_level}
                          </span>
                          <span className="text-sm font-bold text-gray-200 w-12 text-right">
                            {threat.threat_score}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-5 gap-2">
                      {Object.entries(threat.model_scores).map(([model, data]) => (
                        <div key={model} className="p-2 rounded-lg bg-surface-800/50 text-center">
                          <p className="text-xs text-gray-500 capitalize truncate">{model.replace(/_/g, ' ')}</p>
                          <p className={`text-sm font-bold mt-1 ${
                            data.score >= 50 ? 'text-danger-400' : data.score >= 25 ? 'text-warning-400' : 'text-matrix-400'
                          }`}>
                            {data.score.toFixed(0)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'employee' && (
        <div className="space-y-6">
          {/* Employee selector */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <select
              value={selectedEmployee}
              onChange={(e) => setSelectedEmployee(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-surface-900 border border-surface-800 rounded-lg text-gray-300
                focus:outline-none focus:border-cyber-500/50 transition-all appearance-none cursor-pointer"
            >
              <option value="">Select an employee for detailed report...</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.full_name} — {emp.department || 'No Dept'}
                </option>
              ))}
            </select>
          </div>

          {!selectedEmployee ? (
            <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
              <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">Select an employee to view their detailed report</p>
            </div>
          ) : !employeeReport ? (
            <div className="flex justify-center py-16">
              <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Employee Info */}
              <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">Employee Report</h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => downloadEmployeeReport(selectedEmployee, 'pdf', 30)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-danger-500/10 border border-danger-500/30
                        text-danger-400 text-xs font-medium hover:bg-danger-500/20 transition-all"
                    >
                      <FileDown className="w-3.5 h-3.5" /> PDF
                    </button>
                    <button
                      onClick={() => downloadEmployeeReport(selectedEmployee, 'xlsx', 30)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-matrix-500/10 border border-matrix-500/30
                        text-matrix-400 text-xs font-medium hover:bg-matrix-500/20 transition-all"
                    >
                      <FileSpreadsheet className="w-3.5 h-3.5" /> Excel
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-12 h-12 rounded-full bg-cyber-500/10 flex items-center justify-center">
                    <span className="text-lg font-bold text-cyber-400">
                      {employeeReport.employee.name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-white">{employeeReport.employee.name}</p>
                    <p className="text-sm text-gray-500">
                      {employeeReport.employee.department} • {employeeReport.employee.designation}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Total Alerts</p>
                    <p className="text-xl font-bold text-warning-400">{employeeReport.total_alerts}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800/50">
                    <p className="text-xs text-gray-500">Activity Logs</p>
                    <p className="text-xl font-bold text-white">{employeeReport.total_activity_logs}</p>
                  </div>
                </div>

                {employeeReport.latest_risk_score && (
                  <div className="mt-4 p-4 rounded-lg bg-surface-800/50 border border-surface-700/50">
                    <p className="text-xs text-gray-500 mb-1">Latest Risk Score</p>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${employeeReport.latest_risk_score.score}%`,
                            backgroundColor: riskBarColors[employeeReport.latest_risk_score.level] || '#6b7280',
                          }}
                        />
                      </div>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize border ${
                        riskColors[employeeReport.latest_risk_score.level] || riskColors.low
                      }`}>
                        {employeeReport.latest_risk_score.level}
                      </span>
                      <span className="text-sm font-bold text-gray-200">
                        {employeeReport.latest_risk_score.score.toFixed(0)}
                      </span>
                    </div>
                  </div>
                )}

                {/* Alert Severity Breakdown */}
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-300 mb-3">Alert Severity Breakdown</h4>
                  <div className="space-y-2">
                    {Object.entries(employeeReport.alert_severity_breakdown).map(([severity, count]) => (
                      <div key={severity} className="flex justify-between items-center p-2 rounded-lg bg-surface-800/30">
                        <span className="text-sm capitalize text-gray-400">{severity}</span>
                        <span className="text-sm font-medium text-gray-200">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Threat Assessment */}
              <div className="bg-surface-900 rounded-xl border border-surface-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Threat Assessment</h3>
                {employeeReport.threat_assessment?.threat_score !== undefined && (
                  <>
                    <div className="flex items-center gap-4 mb-6">
                      <div className={`text-3xl font-bold ${
                        (employeeReport.threat_assessment.threat_score as number) >= 60
                          ? 'text-danger-400'
                          : (employeeReport.threat_assessment.threat_score as number) >= 30
                          ? 'text-warning-400'
                          : 'text-matrix-400'
                      }`}>
                        {(employeeReport.threat_assessment.threat_score as number).toFixed(0)}
                      </div>
                      <div>
                        <p className={`px-2 py-0.5 rounded text-sm font-medium capitalize border ${
                          riskColors[(employeeReport.threat_assessment.threat_level as string)] || riskColors.low
                        }`}>
                          {employeeReport.threat_assessment.threat_level as string}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Threat Level</p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {Object.entries(employeeReport.threat_assessment.model_scores as Record<string, any> || {}).map(([model, data]) => (
                        <div key={model}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-gray-300 capitalize">{model.replace(/_/g, ' ')}</span>
                            <span className={`text-sm font-medium ${
                              data.score >= 50 ? 'text-danger-400' : data.score >= 25 ? 'text-warning-400' : 'text-gray-400'
                            }`}>
                              {data.score.toFixed(1)}
                            </span>
                          </div>
                          <div className="h-1.5 bg-surface-700 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${data.score}%`,
                                backgroundColor: riskBarColors[data.level] || '#6b7280',
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
