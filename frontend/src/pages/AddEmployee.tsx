import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createEmployee } from '../api/employees';
import { ArrowLeft, Save, ShieldAlert } from 'lucide-react';

const DEPARTMENTS = [
  'Engineering', 'Product', 'Sales', 'Marketing', 'Finance', 'HR',
  'Legal', 'IT Security', 'Operations', 'Executive', 'R&D', 'General',
];

const PRIVILEGE_OPTIONS = [
  'vpn_access', 'admin_panel', 'source_code', 'financial_reports',
  'employee_data', 'client_data', 'cloud_console', 'file_server',
];

export default function AddEmployee() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    employee_code: '',
    full_name: '',
    department: '',
    designation: '',
    manager_name: '',
  });
  const [privileges, setPrivileges] = useState<string[]>([]);
  const [deviceOs, setDeviceOs] = useState('Windows 11');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await createEmployee({
        employee_code: form.employee_code.trim(),
        full_name: form.full_name.trim(),
        department: form.department || undefined,
        designation: form.designation.trim() || undefined,
        manager_name: form.manager_name.trim() || undefined,
        access_privileges: privileges,
        device_info: { os: deviceOs, source: 'manual' },
      });
      navigate('/employees');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create employee');
      setLoading(false);
    }
  };

  const togglePrivilege = (priv: string) => {
    setPrivileges((prev) =>
      prev.includes(priv) ? prev.filter((p) => p !== priv) : [...prev, priv]
    );
  };

  const inputCls =
    'w-full px-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg text-gray-100 ' +
    'placeholder-gray-500 focus:outline-none focus:border-cyber-500/50 focus:ring-1 focus:ring-cyber-500/20 transition-all';

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/employees')}
          className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-surface-800 transition-all"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Add Employee</h1>
          <p className="text-gray-500 mt-1">Create a new monitored employee profile</p>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/20 text-danger-400 text-sm flex items-center gap-2">
          <ShieldAlert className="w-4 h-4" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-surface-900 rounded-xl border border-surface-800 p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Employee Code *</label>
            <input
              type="text"
              required
              value={form.employee_code}
              onChange={(e) => setForm({ ...form, employee_code: e.target.value })}
              className={inputCls}
              placeholder="EMP1001"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Full Name *</label>
            <input
              type="text"
              required
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className={inputCls}
              placeholder="Jane Doe"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Department</label>
            <select
              value={form.department}
              onChange={(e) => setForm({ ...form, department: e.target.value })}
              className={inputCls}
            >
              <option value="">Select department...</option>
              {DEPARTMENTS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Designation</label>
            <input
              type="text"
              value={form.designation}
              onChange={(e) => setForm({ ...form, designation: e.target.value })}
              className={inputCls}
              placeholder="Security Analyst"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Manager</label>
            <input
              type="text"
              value={form.manager_name}
              onChange={(e) => setForm({ ...form, manager_name: e.target.value })}
              className={inputCls}
              placeholder="Reporting manager"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">Device OS</label>
            <select value={deviceOs} onChange={(e) => setDeviceOs(e.target.value)} className={inputCls}>
              <option>Windows 11</option>
              <option>macOS 14</option>
              <option>Ubuntu 22.04</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Access Privileges</label>
          <div className="flex flex-wrap gap-2">
            {PRIVILEGE_OPTIONS.map((priv) => {
              const active = privileges.includes(priv);
              return (
                <button
                  key={priv}
                  type="button"
                  onClick={() => togglePrivilege(priv)}
                  className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                    active
                      ? 'bg-cyber-500/20 border-cyber-500/30 text-cyber-400'
                      : 'bg-surface-800 border-surface-700 text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {priv.replace(/_/g, ' ')}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2 border-t border-surface-800">
          <button
            type="button"
            onClick={() => navigate('/employees')}
            className="px-4 py-2.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-surface-800 transition-all"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-cyber-500/20 border border-cyber-500/30 text-cyber-400
              rounded-lg font-medium hover:bg-cyber-500/30 transition-all duration-150 disabled:opacity-50"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {loading ? 'Creating...' : 'Create Employee'}
          </button>
        </div>
      </form>
    </div>
  );
}
