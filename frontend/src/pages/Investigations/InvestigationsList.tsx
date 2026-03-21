import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { casesApi, CaseStatus, CaseSeverity } from '../../api/cases';
import { 
  Briefcase, 
  Plus, 
  Search, 
  Filter, 
  ChevronRight, 
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
  User as UserIcon,
  Shield
} from 'lucide-react';

const severityConfig = {
  critical: { color: 'text-error', bg: 'bg-error/10', border: 'border-error/20' },
  high: { color: 'text-warning', bg: 'bg-warning/10', border: 'border-warning/20' },
  medium: { color: 'text-info', bg: 'bg-info/10', border: 'border-info/20' },
  low: { color: 'text-success', bg: 'bg-success/10', border: 'border-success/20' },
};

const statusConfig = {
  open: { icon: Clock, color: 'text-error', label: 'Open' },
  in_progress: { icon: Clock, color: 'text-warning', label: 'In Progress' },
  resolved: { icon: CheckCircle2, color: 'text-success', label: 'Resolved' },
  closed: { icon: XCircle, color: 'text-base-content/50', label: 'Closed' },
};

export const InvestigationsList = () => {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<{ status?: CaseStatus; severity?: CaseSeverity }>({});
  const [searchTerm, setSearchTerm] = useState('');

  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['cases', filters],
    queryFn: () => casesApi.getCases(filters),
  });

  const filteredCases = cases.filter(c => 
    c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex justify-between items-center bg-base-100 p-8 rounded-2xl border border-base-300 shadow-sm overflow-hidden relative">
        <div className="absolute top-0 right-0 p-8 opacity-5">
            <Briefcase className="w-32 h-32" />
        </div>
        <div className="relative z-10">
          <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
            <Briefcase className="w-8 h-8 text-primary" />
            Investigations
          </h1>
          <p className="text-base-content/60 mt-1 font-medium">Manage and resolve security incidents and case workflows.</p>
        </div>
        {/* <button className="btn btn-primary gap-2 shadow-lg shadow-primary/20">
          <Plus className="w-5 h-5" />
          New Case
        </button> */}
      </div>

      {/* Filters & Search */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex gap-2">
          <div className="join border border-base-300 shadow-sm overflow-hidden">
            <button 
                onClick={() => setFilters({})}
                className={`join-item btn btn-sm ${!filters.status && !filters.severity ? 'btn-active' : 'bg-base-100'}`}
            >
                All
            </button>
            <button 
                onClick={() => setFilters({ ...filters, status: 'open' })}
                className={`join-item btn btn-sm ${filters.status === 'open' ? 'btn-active' : 'bg-base-100'}`}
            >
                Open
            </button>
            <button 
                onClick={() => setFilters({ ...filters, status: 'in_progress' })}
                className={`join-item btn btn-sm ${filters.status === 'in_progress' ? 'btn-active' : 'bg-base-100'}`}
            >
                In Progress
            </button>
          </div>

          <select 
            className="select select-sm select-bordered bg-base-100 border-base-300 shadow-sm"
            value={filters.severity || ''}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value as CaseSeverity || undefined })}
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div className="relative w-full max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40" />
          <input 
            type="text" 
            placeholder="Search cases..." 
            className="input input-sm input-bordered w-full pl-10 bg-base-100 border-base-300 shadow-sm"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* List */}
      <div className="grid grid-cols-1 gap-1">
        {isLoading ? (
          <div className="flex justify-center p-20">
            <span className="loading loading-spinner loading-lg text-primary"></span>
          </div>
        ) : filteredCases.length > 0 ? (
          filteredCases.map((c) => (
            <div 
              key={c.id} 
              onClick={() => navigate(`/investigations/${c.id}`)}
              className="group bg-base-100 border border-base-300 hover:border-primary/50 p-4 flex items-center justify-between hover:shadow-md transition-all cursor-pointer first:rounded-t-xl last:rounded-b-xl border-t-0 first:border-t"
            >
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className={`w-2 h-10 rounded-full ${severityConfig[c.severity].bg} ${severityConfig[c.severity].color} flex items-center justify-center shrink-0`}>
                  <div className={`w-1 h-6 rounded-full bg-current opacity-50`}></div>
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] font-black uppercase tracking-widest text-base-content/30">Case-#{c.id}</span>
                    <span className="text-base-content/20">•</span>
                    <span className={`text-[10px] font-bold uppercase tracking-widest ${severityConfig[c.severity].color}`}>
                        {c.severity}
                    </span>
                  </div>
                  <h3 className="font-bold text-lg truncate group-hover:text-primary transition-colors">{c.title}</h3>
                  <p className="text-sm text-base-content/50 truncate max-w-2xl">{c.description || 'No description provided.'}</p>
                </div>
              </div>

              <div className="flex items-center gap-8 shrink-0 ml-4">
                <div className="flex flex-col items-end gap-1">
                   {c.assigned_to ? (
                     <div className="flex items-center gap-2 text-xs font-medium text-base-content/70">
                        <span className="truncate max-w-[100px]">{c.assigned_to.email.split('@')[0]}</span>
                        <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
                            <UserIcon className="w-3 h-3" />
                        </div>
                     </div>
                   ) : (
                     <span className="text-xs font-medium text-base-content/20 italic">Unassigned</span>
                   )}
                   <span className="text-[10px] text-base-content/30 tabular-nums">
                     Updated {new Date(c.updated_at).toLocaleDateString()}
                   </span>
                </div>

                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg bg-base-200/50 border border-base-300 min-w-[120px] justify-center`}>
                   {React.createElement(statusConfig[c.status].icon, { className: `w-3.5 h-3.5 ${statusConfig[c.status].color}` })}
                   <span className="text-xs font-bold uppercase tracking-wider">{statusConfig[c.status].label}</span>
                </div>

                <ChevronRight className="w-5 h-5 text-base-content/20 group-hover:text-primary transition-colors" />
              </div>
            </div>
          ))
        ) : (
          <div className="bg-base-100 p-20 text-center rounded-2xl border-2 border-dashed border-base-300">
            <div className="bg-base-200/50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
               <Shield className="w-8 h-8 text-base-content/20" />
            </div>
            <h3 className="text-xl font-bold opacity-50">No cases found</h3>
            <p className="opacity-40 max-w-xs mx-auto">Try adjusting your filters or create a new case from an existing alert.</p>
          </div>
        )}
      </div>
    </div>
  );
};
