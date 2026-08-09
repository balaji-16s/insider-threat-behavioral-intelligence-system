import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listEmployees, deleteEmployee, getEmployeeStats, type Employee } from '../api/employees';
import { Search, Plus, Trash2, Building2, ChevronRight, Users, ShieldAlert } from 'lucide-react';

export default function Employees() {
  const navigate = useNavigate();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [departments, setDepartments] = useState<string[]>([]);
  const [stats, setStats] = useState<{ total_employees: number } | null>(null);

  async function load() {
    setLoading(true);
    try {
      const params: { search?: string; department?: string } = {};
      if (search) params.search = search;
      if (department) params.department = department;
      const [emps, s] = await Promise.all([
        listEmployees(params),
        getEmployeeStats().catch(() => null),
      ]);
      setEmployees(emps);
      if (s?.department_distribution) {
        setDepartments(Object.keys(s.department_distribution).filter(Boolean));
      }
      if (s) setStats(s);
    } catch (err) {
      console.error('Failed to load employees:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [department]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    load();
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Delete employee "${name}"? This cannot be undone.`)) return;
    try {
      await deleteEmployee(id);
      setEmployees(employees.filter((e) => e.id !== id));
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Employees</h1>
          <p className="text-gray-500 mt-1">Monitor and manage employee profiles</p>
        </div>
        <button
          onClick={() => navigate('/employees/new')}
          className="flex items-center gap-2 px-4 py-2.5 bg-cyber-500/20 border border-cyber-500/30 text-cyber-400 
            rounded-lg font-medium hover:bg-cyber-500/30 transition-all duration-150"
        >
          <Plus className="w-4 h-4" />
          Add Employee
        </button>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-cyber-400" />
            <div>
              <p className="text-lg font-bold text-white">{stats?.total_employees || employees.length}</p>
              <p className="text-xs text-gray-500">Total Employees</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <Building2 className="w-5 h-5 text-warning-400" />
            <div>
              <p className="text-lg font-bold text-white">{departments.length || '—'}</p>
              <p className="text-xs text-gray-500">Departments</p>
            </div>
          </div>
        </div>
        <div className="bg-surface-900 rounded-xl border border-surface-800 p-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-danger-400" />
            <div>
              <p className="text-lg font-bold text-white">{employees.length}</p>
              <p className="text-xs text-gray-500">Loaded</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <form onSubmit={handleSearch} className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or employee code..."
              className="w-full pl-10 pr-4 py-2.5 bg-surface-900 border border-surface-800 rounded-lg text-gray-100 
                placeholder-gray-500 focus:outline-none focus:border-cyber-500/50 transition-all"
            />
          </div>
        </form>
        <select
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
          className="px-4 py-2.5 bg-surface-900 border border-surface-800 rounded-lg text-gray-300 
            focus:outline-none focus:border-cyber-500/50 transition-all"
        >
          <option value="">All Departments</option>
          {departments.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* Employee list */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : employees.length === 0 ? (
        <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
          <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">No employees found</p>
          <p className="text-gray-600 text-sm mt-1">Add an employee or import the CERT dataset</p>
        </div>
      ) : (
        <div className="bg-surface-900 rounded-xl border border-surface-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-800">
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Employee</th>
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Department</th>
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Designation</th>
                  <th className="text-left px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Code</th>
                  <th className="text-right px-6 py-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800">
                {employees.map((emp) => (
                  <tr
                    key={emp.id}
                    className="hover:bg-surface-800/50 transition-colors cursor-pointer group"
                    onClick={() => navigate(`/employees/${emp.id}`)}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-cyber-500/10 flex items-center justify-center">
                          <span className="text-sm font-bold text-cyber-400">
                            {emp.full_name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-200">{emp.full_name}</p>
                          {emp.manager_name && (
                            <p className="text-xs text-gray-500">Manager: {emp.manager_name}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-surface-800 text-gray-300">
                        <Building2 className="w-3 h-3" />
                        {emp.department || '—'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-400">{emp.designation || '—'}</td>
                    <td className="px-6 py-4 text-sm text-gray-500 font-mono">{emp.employee_code}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(emp.id, emp.full_name); }}
                          className="p-1.5 rounded-lg text-gray-500 hover:text-danger-400 hover:bg-danger-500/10 transition-all"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <ChevronRight className="w-4 h-4 text-gray-600" />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
