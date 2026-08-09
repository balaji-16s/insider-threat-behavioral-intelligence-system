import { useEffect, useState } from 'react';
import { listActivityLogs, type ActivityLog } from '../api/activityLogs';
import { listEmployees, type Employee } from '../api/employees';
import { Filter, Activity, Calendar, ChevronDown } from 'lucide-react';

const activityTypes = [
  'login', 'file_download', 'file_upload', 'data_transfer',
  'email', 'privilege_change', 'remote_access', 'usb_device',
];

const typeColors: Record<string, string> = {
  login: 'text-matrix-400 bg-matrix-500/10 border-matrix-500/20',
  file_download: 'text-cyber-400 bg-cyber-500/10 border-cyber-500/20',
  file_upload: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  data_transfer: 'text-danger-400 bg-danger-500/10 border-danger-500/20',
  email: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  privilege_change: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  remote_access: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  usb_device: 'text-pink-400 bg-pink-500/10 border-pink-500/20',
};

export default function ActivityLogs() {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('');
  const [filterEmployee, setFilterEmployee] = useState('');
  const [searchSource, setSearchSource] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filterType) params.activity_type = filterType;
      if (filterEmployee) params.employee_id = filterEmployee;
      if (searchSource) params.source = searchSource;
      params.limit = '200';

      const [logsData, emps] = await Promise.all([
        listActivityLogs(params as any),
        listEmployees({ limit: 500 }),
      ]);
      setLogs(logsData);
      setEmployees(emps);
    } catch (err) {
      console.error('Failed to load logs:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [filterType, filterEmployee]);

  const getEmployeeName = (id: string) => {
    const emp = employees.find((e) => e.id === id);
    return emp?.full_name || id.slice(0, 8) + '...';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Activity Logs</h1>
          <p className="text-gray-500 mt-1">Monitor employee activity and behavioral data</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-all ${
            showFilters
              ? 'bg-cyber-500/10 border-cyber-500/30 text-cyber-400'
              : 'bg-surface-900 border-surface-800 text-gray-400 hover:text-gray-200'
          }`}
        >
          <Filter className="w-4 h-4" />
          Filters
          <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Activity Type</label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-gray-300 text-sm
                  focus:outline-none focus:border-cyber-500/50 transition-all"
              >
                <option value="">All Types</option>
                {activityTypes.map((t) => (
                  <option key={t} value={t}>{t.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Employee</label>
              <select
                value={filterEmployee}
                onChange={(e) => setFilterEmployee(e.target.value)}
                className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-gray-300 text-sm
                  focus:outline-none focus:border-cyber-500/50 transition-all"
              >
                <option value="">All Employees</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.full_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Source</label>
              <input
                type="text"
                value={searchSource}
                onChange={(e) => setSearchSource(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && load()}
                placeholder="Search source..."
                className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-gray-300 text-sm
                  placeholder-gray-600 focus:outline-none focus:border-cyber-500/50 transition-all"
              />
            </div>
          </div>
          {(filterType || filterEmployee || searchSource) && (
            <button
              onClick={() => { setFilterType(''); setFilterEmployee(''); setSearchSource(''); }}
              className="mt-3 text-xs text-cyber-400 hover:underline"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Activity count */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Activity className="w-4 h-4" />
        {loading ? 'Loading...' : `${logs.length} log entries`}
      </div>

      {/* Log list */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
          <Activity className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">No activity logs found</p>
          <p className="text-gray-600 text-sm mt-1">Ingest the CERT dataset or create activity logs via API</p>
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <div
              key={log.id}
              className="flex items-start gap-4 p-4 bg-surface-900 rounded-xl border border-surface-800 hover:border-surface-700 transition-all group"
            >
              <div className={`p-2.5 rounded-lg border ${typeColors[log.activity_type] || 'text-gray-400 bg-gray-500/10 border-gray-500/20'}`}>
                <Activity className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-gray-200 capitalize">
                    {log.activity_type.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-gray-600">•</span>
                  <span className="text-sm text-cyber-400">{getEmployeeName(log.employee_id)}</span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  {log.source && (
                    <span className="px-2 py-0.5 rounded bg-surface-800">{log.source}</span>
                  )}
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(log.occurred_at).toLocaleString()}
                  </span>
                </div>
                {Object.keys(log.details).length > 0 && (
                  <details className="mt-2">
                    <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-400">View details</summary>
                    <pre className="mt-1 text-xs text-gray-500 bg-surface-800 p-2 rounded-lg overflow-x-auto">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
