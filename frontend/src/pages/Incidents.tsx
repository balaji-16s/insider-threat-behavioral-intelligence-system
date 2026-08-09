import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listIncidents, updateIncident, type Incident } from '../api/incidents';
import { ShieldAlert, Filter, CheckCircle, Clock, ChevronRight } from 'lucide-react';

const statusStyles: Record<string, string> = {
  open: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  investigating: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  escalated: 'bg-danger-500/10 text-danger-400 border-danger-500/20',
  closed: 'bg-matrix-500/10 text-matrix-400 border-matrix-500/20',
};

const statusIcon: Record<string, typeof ShieldAlert> = {
  open: ShieldAlert,
  investigating: Clock,
  escalated: ShieldAlert,
  closed: CheckCircle,
};

export default function Incidents() {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filterStatus) params.status = filterStatus;
      params.limit = '200';
      const data = await listIncidents(params as any);
      setIncidents(data);
    } catch (err) {
      console.error('Failed to load incidents:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filterStatus]);

  const handleStatusChange = async (incidentId: string, status: string) => {
    setActionLoading(incidentId);
    try {
      await updateIncident(incidentId, { status });
      setIncidents(incidents.map((i) => i.id === incidentId ? { ...i, status } : i));
    } catch (err) {
      console.error('Failed to update incident:', err);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Incidents</h1>
          <p className="text-gray-500 mt-1">Track and manage security incidents</p>
        </div>
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-surface-900 border border-surface-800 rounded-lg p-1">
          <Filter className="w-4 h-4 text-gray-500 ml-2" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-transparent text-sm text-gray-300 px-2 py-1.5 outline-none"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="escalated">Escalated</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        {filterStatus && (
          <button onClick={() => setFilterStatus('')} className="text-xs text-cyber-400 hover:underline">
            Clear
          </button>
        )}
      </div>

      {/* Incident list */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : incidents.length === 0 ? (
        <div className="text-center py-16 bg-surface-900 rounded-xl border border-surface-800">
          <ShieldAlert className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500">No incidents found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map((incident) => {
            const Icon = statusIcon[incident.status] || ShieldAlert;
            return (
              <div
                key={incident.id}
                onClick={() => navigate(`/incidents/${incident.id}`)}
                className="bg-surface-900 rounded-xl border border-surface-800 p-5 hover:border-surface-700 hover:border-cyber-500/30 transition-all cursor-pointer group"
              >
                <div className="flex items-start gap-4">
                  <div className={`p-2.5 rounded-lg border ${statusStyles[incident.status] || statusStyles.open}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-semibold text-gray-200">{incident.title}</h3>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border capitalize ${statusStyles[incident.status]}`}>
                        {incident.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      {incident.related_alert_ids && (
                        <span>{incident.related_alert_ids.length} related alert(s)</span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Created: {new Date(incident.created_at).toLocaleString()}
                      </span>
                      {incident.closed_at && (
                        <span className="flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" />
                          Closed: {new Date(incident.closed_at).toLocaleString()}
                        </span>
                      )}
                    </div>

                    {/* Timeline */}
                    {incident.timeline && incident.timeline.length > 0 && (
                      <details className="mt-3">
                        <summary className="text-xs text-cyber-400 cursor-pointer hover:underline">
                          View timeline ({incident.timeline.length} events)
                        </summary>
                        <div className="mt-2 space-y-1.5">
                          {incident.timeline.map((event: any, i: number) => (
                            <div key={i} className="flex items-center gap-2 text-xs text-gray-500">
                              <div className="w-1.5 h-1.5 rounded-full bg-cyber-400/50" />
                              {event.event}
                              {event.timestamp && (
                                <span className="text-gray-600">
                                  — {new Date(event.timestamp).toLocaleString()}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                  <div className="flex flex-col gap-2 items-end">
                    <button
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-cyber-400 
                        bg-cyber-500/10 border border-cyber-500/20 hover:bg-cyber-500/20 transition-all opacity-0 group-hover:opacity-100"
                      onClick={(e) => { e.stopPropagation(); navigate(`/incidents/${incident.id}`); }}
                    >
                      Open Investigation
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                    {incident.status === 'open' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStatusChange(incident.id, 'investigating'); }}
                        disabled={actionLoading === incident.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium 
                          bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-all"
                      >
                        Investigate
                      </button>
                    )}
                    {incident.status === 'investigating' && (
                      <>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleStatusChange(incident.id, 'escalated'); }}
                          disabled={actionLoading === incident.id}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium 
                            bg-danger-500/10 text-danger-400 border border-danger-500/20 hover:bg-danger-500/20 transition-all"
                        >
                          Escalate
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleStatusChange(incident.id, 'closed'); }}
                          disabled={actionLoading === incident.id}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium 
                            bg-matrix-500/10 text-matrix-400 border border-matrix-500/20 hover:bg-matrix-500/20 transition-all"
                        >
                          <CheckCircle className="w-3.5 h-3.5" />
                          Close
                        </button>
                      </>
                    )}
                    {incident.status === 'escalated' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStatusChange(incident.id, 'closed'); }}
                        disabled={actionLoading === incident.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium 
                          bg-matrix-500/10 text-matrix-400 border border-matrix-500/20 hover:bg-matrix-500/20 transition-all"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        Close
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
