import { type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard, Users, Activity, AlertTriangle, ShieldAlert,
  BarChart3, LogOut, Menu, Shield, Zap, Search, FileText, Radar, Gauge,
} from 'lucide-react';
import { useState } from 'react';

interface NavItem {
  label: string;
  path: string;
  icon: typeof LayoutDashboard;
  /** Shown only to portal (employee) accounts. */
  employeeOnly?: boolean;
}

const navItems: NavItem[] = [
  { label: 'My Dashboard', path: '/my-dashboard', icon: Gauge, employeeOnly: true },
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Employees', path: '/employees', icon: Users },
  { label: 'Activity Logs', path: '/activity-logs', icon: Activity },
  { label: 'UEBA Intelligence', path: '/ueba-intelligence', icon: Radar },
  { label: 'Anomaly Detection', path: '/anomaly-detection', icon: Zap },
  { label: 'Behavioral Analysis', path: '/behavioral-analysis', icon: Search },
  { label: 'Alerts', path: '/alerts', icon: AlertTriangle },
  { label: 'Incidents', path: '/incidents', icon: ShieldAlert },
  { label: 'Risk Scores', path: '/risk-scores', icon: BarChart3 },
  { label: 'Anomaly Reports', path: '/anomaly-reports', icon: FileText },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Portal accounts only ever get their own dashboard; security-staff
  // pages are hidden from them (and rejected server-side).
  const isEmployee = user?.role === 'employee';
  const visibleNavItems = navItems.filter((item) =>
    isEmployee ? item.employeeOnly : !item.employeeOnly
  );

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-surface-950">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-30 w-64 bg-surface-900 border-r border-surface-800 
          transform transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        <div className="flex items-center gap-3 px-6 py-5 border-b border-surface-800">
          <Shield className="w-8 h-8 text-cyber-400" />
          <div>
            <h1 className="text-sm font-bold text-white">ITBIS</h1>
            <p className="text-xs text-gray-500">
              {isEmployee ? 'Employee Portal' : 'Threat Intelligence'}
            </p>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {visibleNavItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setSidebarOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150
                  ${isActive
                    ? 'bg-cyber-500/10 text-cyber-400 border border-cyber-500/20'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-surface-800'
                  }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="px-3 py-4 border-t border-surface-800">
          <div className="flex items-center gap-3 px-3 py-2 mb-2">
            <div className="w-8 h-8 rounded-full bg-cyber-500/20 flex items-center justify-center">
              <span className="text-xs font-bold text-cyber-400">
                {user?.email?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-300 truncate">{user?.email}</p>
              <p className="text-xs text-gray-500 capitalize">{user?.role?.replace('_', ' ')}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-danger-400 hover:bg-danger-500/10 transition-all duration-150"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-16 border-b border-surface-800 flex items-center justify-between px-4 lg:px-6 bg-surface-900/50 backdrop-blur-sm">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-surface-800"
          >
            <Menu className="w-6 h-6" />
          </button>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-matrix-500/10 border border-matrix-500/20">
              <div className="w-2 h-2 rounded-full bg-matrix-400 animate-pulse" />
              <span className="text-xs text-matrix-400 font-medium">System Online</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
