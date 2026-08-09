import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getIncident, updateIncident, addTimelineEvent, getRelatedAlerts,
  type Incident,
} from '../api/incidents';
import { getEmployee, type Employee } from '../api/employees';
import {
  ArrowLeft, ShieldAlert, CheckCircle, Clock, AlertTriangle, User,
  MessageSquarePlus, Send, Building2, ChevronRight, Scale,
} from 'lucide-react';

const statusStyles: Record<string, string> = {
  open: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  investigating: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  escalated: 'bg-danger-500/10 text-danger-400 border-danger-500/20',
  closed: 'bg-matrix-500/10 text-matrix-400 border-matrix-500/20',
};

const severityStyles: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  medium: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  low: 'bg-matrix-500/10 text-matrix-400 border-matrix-500/20',
  informational: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
};

interface RelatedAlert {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  anomaly_type: string | null;
  evidence: Record<string, unknown>;
  created_at: string;
}

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [relatedAlerts, setRelatedAlerts] = useState<RelatedAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [note, setNote] = useState('');
  const [noteLoading, setNoteLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    const incidentId = id;
    async function load() {
      try {
        const inc = await getIncident(incidentId);
        setIncident(inc);
        const [alerts, emp] = await Promise.all([
          getRelatedAlerts(incidentId).catch(() => []),
          getEmployee(inc.employee_id).catch(() => null),
        ]);
        setRelatedAlerts(alerts as RelatedAlert[]);
        setEmployee(emp);
      } catch (err) {
        console.error('Failed to load incident:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function handleStatusChange(status: string) {
    if (!incident) return;
    setActionLoading(true);
    try {
      const updated = await updateIncident(incident.id, { status });
      setIncident(updated);
    } catch (err) {
      console.error('Failed to update incident:', err);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!incident || !note.trim()) return;
    setNoteLoading(true);
    try {
      const updated = await addTimelineEvent(incident.id, {
        event: note.trim(),
        note: note.trim(),
      });
      setIncident(updated);
      setNote('');
    } catch (err) {
      console.error('Failed to add timeline note:', err);
    } finally {
      setNoteLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-8 h-8 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500">Incident not found</p>
        <button onClick={() => navigate('/incidents')} className="text-cyber-400 mt-2 hover:underline">
          Back to incidents
        </button>
      </div>
    );
  }

  const isClosed = incident.status === 'closed';
  const timeline = (incident.timeline as any[]) ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/incidents')}
          className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-surface-800 transition-all"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-white">{incident.title}</h1>
            <span className={`px-2.5 py-1 rounded text-xs font-medium border capitalize ${statusStyles[incident.status] || statusStyles.open}`}>
              {incident.status}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Created {new Date(incident.created_at).toLocaleString()}
            {incident.closed_at && ` • Closed ${new Date(incident.closed_at).toLocaleString()}`}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: employee + actions */}
        <div className="space-y-6">
          {/* Employee context */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-5">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
              <User className="w-4 h-4 text-cyber-400" />
              Employee Context
            </h3>
            {employee ? (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-cyber-500/10 flex items-center justify-center">
                  <span className="text-sm font-bold text-cyber-400">
                    {employee.full_name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-200">{employee.full_name}</p>
                  <p className="text-xs text-gray-500">
                    {employee.department || '—'} • {employee.designation || '—'}
                  </p>
                  <p className="text-xs text-gray-600 font-mono mt-0.5">{employee.employee_code}</p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-gray-500">Employee details unavailable</p>
            )}
            {employee && (
              <button
                onClick={() => navigate(`/employees/${employee.id}`)}
                className="mt-4 w-full flex items-center justify-between px-3 py-2 rounded-lg bg-surface-800/50 border border-surface-700/50 
                  text-xs text-cyber-400 hover:border-cyber-500/30 transition-all"
              >
                <span className="flex items-center gap-2">
                  <Building2 className="w-3.5 h-3.5" />
                  View full employee profile
                </span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Investigation actions */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-5">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
              <Scale className="w-4 h-4 text-warning-400" />
              Investigation Actions
            </h3>
            {isClosed ? (
              <div className="p-3 rounded-lg bg-matrix-500/10 border border-matrix-500/20 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-matrix-400" />
                <span className="text-sm text-matrix-400 font-medium">Incident closed</span>
              </div>
            ) : (
              <div className="space-y-2">
                {incident.status === 'open' && (
                  <button
                    onClick={() => handleStatusChange('investigating')}
                    disabled={actionLoading}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium 
                      bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-all disabled:opacity-50"
                  >
                    <Clock className="w-4 h-4" />
                    Start Investigation
                  </button>
                )}
                {incident.status === 'investigating' && (
                  <>
                    <button
                      onClick={() => handleStatusChange('escalated')}
                      disabled={actionLoading}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium 
                        bg-danger-500/10 text-danger-400 border border-danger-500/20 hover:bg-danger-500/20 transition-all disabled:opacity-50"
                    >
                      <ShieldAlert className="w-4 h-4" />
                      Escalate Incident
                    </button>
                    <button
                      onClick={() => handleStatusChange('closed')}
                      disabled={actionLoading}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium 
                        bg-matrix-500/10 text-matrix-400 border border-matrix-500/20 hover:bg-matrix-500/20 transition-all disabled:opacity-50"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Close Investigation
                    </button>
                  </>
                )}
                {incident.status === 'escalated' && (
                  <button
                    onClick={() => handleStatusChange('closed')}
                    disabled={actionLoading}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium 
                      bg-matrix-500/10 text-matrix-400 border border-matrix-500/20 hover:bg-matrix-500/20 transition-all disabled:opacity-50"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Close Investigation
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Related alerts */}
          <div className="bg-surface-900 rounded-xl border border-surface-800 p-5">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-danger-400" />
              Related Alerts ({relatedAlerts.length})
            </h3>
            {relatedAlerts.length === 0 ? (
              <p className="text-xs text-gray-500">No linked alerts</p>
            ) : (
              <div className="space-y-2">
                {relatedAlerts.map((alert) => (
                  <div key={alert.id} className="p-3 rounded-lg bg-surface-800/50 border border-surface-700/50">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className={`w-4 h-4 mt-0.5 shrink-0 ${
                        alert.severity === 'critical' || alert.severity === 'high'
                          ? 'text-danger-400' : 'text-warning-400'
                      }`} />
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-gray-200">{alert.title}</p>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border capitalize ${
                            severityStyles[alert.severity] || severityStyles.informational
                          }`}>
                            {alert.severity}
                          </span>
                          {alert.anomaly_type && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-surface-800 text-gray-400">
                              {alert.anomaly_type}
                            </span>
                          )}
                          <span className="text-[10px] text-gray-600">
                            {new Date(alert.created_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column: timeline */}
        <div className="lg:col-span-2 bg-surface-900 rounded-xl border border-surface-800 p-5">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyber-400" />
            Investigation Timeline ({timeline.length} events)
          </h3>

          {/* Add note */}
          {!isClosed && (
            <form onSubmit={handleAddNote} className="mb-6">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <MessageSquarePlus className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="text"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Add an investigation note or finding..."
                    className="w-full pl-10 pr-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg text-gray-200 text-sm
                      placeholder-gray-600 focus:outline-none focus:border-cyber-500/50 transition-all"
                  />
                </div>
                <button
                  type="submit"
                  disabled={noteLoading || !note.trim()}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium 
                    bg-cyber-500/20 border border-cyber-500/30 text-cyber-400 hover:bg-cyber-500/30 
                    transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {noteLoading ? (
                    <div className="w-4 h-4 border-2 border-cyber-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  Add Note
                </button>
              </div>
            </form>
          )}

          {/* Timeline entries */}
          {timeline.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-12">No timeline events yet</p>
          ) : (
            <div className="relative space-y-4 pl-5 before:content-[''] before:absolute before:left-[7px] before:top-2 before:bottom-2 before:w-px before:bg-surface-700">
              {[...timeline].reverse().map((event, i) => (
                <div key={i} className="relative">
                  <div className="absolute -left-5 top-1.5 w-[15px] h-[15px] rounded-full bg-surface-900 border-2 border-cyber-500/50" />
                  <div className="p-3 rounded-lg bg-surface-800/50 border border-surface-700/50 hover:border-surface-600 transition-all">
                    <p className="text-sm text-gray-200">{event.event}</p>
                    {event.note && event.note !== event.event && (
                      <p className="text-xs text-gray-500 mt-1 italic">"{event.note}"</p>
                    )}
                    <div className="flex items-center gap-3 mt-1.5 text-[11px] text-gray-600">
                      {event.timestamp && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(event.timestamp).toLocaleString()}
                        </span>
                      )}
                      {event.by && (
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3" />
                          {event.by}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
