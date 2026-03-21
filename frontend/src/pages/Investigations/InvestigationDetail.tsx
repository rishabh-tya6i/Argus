import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { casesApi, CaseStatus, CaseSeverity, CaseComment } from '../../api/cases';
import { 
  Briefcase, 
  ChevronLeft, 
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
  User as UserIcon,
  MessageSquare,
  History,
  ExternalLink,
  ShieldAlert,
  Send,
  MoreVertical,
  Activity,
  Terminal,
  Play,
  FileSearch,
  Check,
  Edit2
} from 'lucide-react';

const severityConfig = {
  critical: { color: 'text-error', bg: 'bg-error', border: 'border-error/20' },
  high: { color: 'text-warning', bg: 'bg-warning', border: 'border-warning/20' },
  medium: { color: 'text-info', bg: 'bg-info', border: 'border-info/20' },
  low: { color: 'text-success', bg: 'bg-success', border: 'border-success/20' },
};

const statusConfig = {
  open: { icon: Clock, color: 'text-error', label: 'Open', colorClass: 'badge-error' },
  in_progress: { icon: Clock, color: 'text-warning', label: 'In Progress', colorClass: 'badge-warning' },
  resolved: { icon: CheckCircle2, color: 'text-success', label: 'Resolved', colorClass: 'badge-success' },
  closed: { icon: XCircle, color: 'text-base-content/50', label: 'Closed', colorClass: 'badge-ghost' },
};

export const InvestigationDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [commentText, setCommentText] = useState('');
  const caseId = parseInt(id || '0');

  const { data: caseItem, isLoading } = useQuery({
    queryKey: ['cases', id],
    queryFn: () => casesApi.getCase(caseId),
    enabled: !!id
  });

  const { data: comments = [] } = useQuery({
    queryKey: ['cases', id, 'comments'],
    queryFn: () => casesApi.getComments(caseId),
    enabled: !!id
  });

  const statusMutation = useMutation({
    mutationFn: (status: CaseStatus) => casesApi.updateStatus(caseId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', id] });
    }
  });

  const assignMutation = useMutation({
    mutationFn: (userId: number | null) => casesApi.assignCase(caseId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', id] });
    }
  });

  const commentMutation = useMutation({
    mutationFn: (comment: string) => casesApi.addComment(caseId, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', id, 'comments'] });
      setCommentText('');
    }
  });

  if (isLoading) return <div className="flex justify-center p-20"><span className="loading loading-spinner loading-lg text-primary"></span></div>;
  if (!caseItem) return <div className="p-20 text-center">Case not found.</div>;

  return (
    <div className="space-y-6 max-w-[1200px] mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center gap-4 mb-2">
        <button 
          onClick={() => navigate('/investigations')}
          className="btn btn-ghost btn-sm group p-0 hover:bg-transparent"
        >
          <div className="w-8 h-8 rounded-full bg-base-100 border border-base-300 flex items-center justify-center group-hover:bg-primary group-hover:text-primary-content transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </div>
          <span className="font-bold text-base-content/60 group-hover:text-primary transition-colors">Back to Cases</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Main Content Area */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-base-100 p-8 rounded-3xl border border-base-300 shadow-sm relative overflow-hidden">
             {/* Header Section */}
             <div className="relative z-10">
                <div className="flex flex-wrap items-center gap-3 mb-4">
                   <div className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest bg-base-200 border border-base-300`}>
                     Case ID: #{caseItem.id}
                   </div>
                   <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${statusConfig[caseItem.status].colorClass} text-white`}>
                     {React.createElement(statusConfig[caseItem.status].icon, { className: "w-3.5 h-3.5" })}
                     {statusConfig[caseItem.status].label}
                   </div>
                </div>

                <h1 className="text-4xl font-black tracking-tight leading-tight mb-4">{caseItem.title}</h1>
                <p className="text-lg text-base-content/70 italic bg-base-200/50 p-4 rounded-xl border border-base-300">
                  {caseItem.description || 'No description provided.'}
                </p>
             </div>

             <div className="absolute top-0 right-0 p-8 opacity-5">
                <Briefcase className="w-48 h-48" />
             </div>
          </div>

          {/* Linked Alerts Section */}
          <div className="bg-base-100 p-8 rounded-3xl border border-base-300 shadow-sm">
             <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-black flex items-center gap-2">
                  <ShieldAlert className="w-6 h-6 text-error" />
                  Linked Alerts 
                  <span className="badge badge-error ml-2 font-bold">{caseItem.alerts?.length || 0}</span>
                </h3>
             </div>
             
             <div className="space-y-3">
                {caseItem.alerts && caseItem.alerts.length > 0 ? (
                  caseItem.alerts.map((alert) => (
                    <div 
                      key={alert.id}
                      className="group bg-base-100 border border-base-300 p-4 rounded-2xl flex items-center justify-between hover:border-primary/50 hover:shadow-md transition-all"
                    >
                      <div className="flex items-center gap-4">
                         <div className="w-10 h-10 rounded-full bg-base-200 flex items-center justify-center border border-base-300">
                            <ShieldAlert className="w-5 h-5 text-error" />
                         </div>
                         <div>
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-black text-base-content/40 uppercase">Alert-#{alert.id}</span>
                                <span className="badge badge-outline badge-xs opacity-50 font-bold uppercase">{alert.severity}</span>
                            </div>
                            <h4 className="font-bold">{alert.alert_type.replace(/_/g, ' ')}</h4>
                            <div className="text-xs text-base-content/50 truncate max-w-md font-mono mt-1 opacity-70 group-hover:opacity-100 transition-opacity">
                                URL: {alert.url}
                            </div>
                         </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                         <div className="flex flex-wrap gap-2">
                            {alert.scan_id && (
                                <button 
                                  onClick={(e) => { e.stopPropagation(); navigate(`/scans/${alert.scan_id}`); }}
                                  className="btn btn-ghost btn-xs bg-base-200 hover:bg-primary hover:text-primary-content gap-1" 
                                  title="Open Scan Details"
                                >
                                    <FileSearch className="w-3 h-3" /> Scan
                                </button>
                            )}
                            {alert.sandbox_run_id && (
                                <button 
                                  onClick={(e) => { e.stopPropagation(); navigate(`/sandbox/${alert.sandbox_run_id}`); }}
                                  className="btn btn-ghost btn-xs bg-base-200 hover:bg-primary hover:text-primary-content gap-1" 
                                  title="Open Sandbox Run"
                                >
                                    <Play className="w-3 h-3" /> Sandbox
                                </button>
                            )}
                         </div>
                         <ExternalLink className="w-4 h-4 text-base-content/20" />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-10 text-center border-2 border-dashed border-base-200 rounded-2xl opacity-40">
                    No alerts linked to this case.
                  </div>
                )}
             </div>
          </div>

          {/* Activity / Comments Thread */}
          <div className="bg-base-100 rounded-3xl border border-base-300 shadow-sm overflow-hidden">
             <div className="p-8 pb-4 border-b border-base-200 bg-base-100/50 backdrop-blur-xl sticky top-0 z-10">
                <h3 className="text-xl font-black flex items-center gap-2">
                  <MessageSquare className="w-6 h-6 text-primary" />
                  Activity History
                  <span className="badge badge-primary ml-2 font-bold">{comments.length}</span>
                </h3>
             </div>

             <div className="p-8 space-y-8 min-h-[300px]">
                {comments.length > 0 ? (
                  comments.map((comment, i) => (
                    <div key={comment.id} className="relative group">
                      {/* Vertical line for thread */}
                      {i < comments.length - 1 && (
                        <div className="absolute left-6 top-10 bottom-0 w-0.5 bg-base-200 -z-0"></div>
                      )}
                      
                      <div className="flex gap-6 items-start relative z-10">
                         <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center border-4 border-base-100 shadow-sm shrink-0">
                            {comment.user?.email.charAt(0).toUpperCase() || <UserIcon className="w-6 h-6" />}
                         </div>
                         <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                               <div className="flex items-center gap-2">
                                  <span className="font-black text-primary">{comment.user?.email.split('@')[0]}</span>
                                  <span className="text-[10px] text-base-content/30">•</span>
                                  <span className="text-xs text-base-content/40 font-medium">{new Date(comment.created_at).toLocaleString()}</span>
                               </div>
                               <button className="btn btn-ghost btn-xs opacity-0 group-hover:opacity-100 transition-opacity">
                                  <MoreVertical className="w-3 h-3 text-base-content/30" />
                               </button>
                            </div>
                            <div className="p-4 bg-base-200 border border-base-300 rounded-2xl text-base-content/70 leading-relaxed font-medium">
                               {comment.comment}
                            </div>
                         </div>
                      </div>
                    </div>
                  ))
                ) : (
                   <div className="p-10 text-center opacity-30 italic">No activity yet.</div>
                )}
             </div>

             {/* Comment Input Box */}
             <div className="p-8 bg-base-200/50 border-t border-base-300">
                <div className="relative group">
                   <textarea 
                     className="textarea textarea-bordered w-full pr-12 bg-base-100 border-base-300 focus:border-primary transition-all rounded-2xl shadow-sm text-base font-medium min-h-[100px]"
                     placeholder="Add a comment or update the investigation status..."
                     value={commentText}
                     onChange={(e) => setCommentText(e.target.value)}
                   />
                   <button 
                     className="absolute bottom-4 right-4 btn btn-primary btn-sm btn-circle shadow-lg shadow-primary/20 hover:scale-110 active:scale-95 transition-all"
                     disabled={!commentText.trim() || commentMutation.isPending}
                     onClick={() => commentMutation.mutate(commentText)}
                   >
                     {commentMutation.isPending ? <span className="loading loading-spinner loading-xs"></span> : <Send className="w-4 h-4" />}
                   </button>
                </div>
                <div className="mt-4 flex gap-2">
                   <span className="text-[10px] font-black uppercase text-base-content/30 tracking-widest pt-1">Quick actions:</span>
                   <div className="flex flex-wrap gap-2">
                      <button className="btn btn-xs bg-base-300 border-none hover:bg-primary/10 hover:text-primary rounded-full px-4" onClick={() => setCommentText("Working on this case currently.")}>Working on it</button>
                      <button className="btn btn-xs bg-base-300 border-none hover:bg-primary/10 hover:text-primary rounded-full px-4" onClick={() => setCommentText("False positive. No threat detected.")}>False Positive</button>
                      <button className="btn btn-xs bg-base-300 border-none hover:bg-primary/10 hover:text-primary rounded-full px-4" onClick={() => setCommentText("Verified threat. Initiating takedown.")}>Verified threat</button>
                   </div>
                </div>
             </div>
          </div>
        </div>

        {/* Sidebar Info Area */}
        <div className="space-y-6 lg:sticky lg:top-4">
           {/* Detailed Status Card */}
           <div className="bg-base-100 p-8 rounded-3xl border border-base-300 shadow-sm">
             <h3 className="text-xl font-black mb-6 flex items-center gap-2">
                <Activity className="w-6 h-6 text-primary" />
                Management
             </h3>
             
             <div className="space-y-6">
                {/* Status Selector */}
                <div>
                   <label className="text-[10px] font-black uppercase tracking-widest text-base-content/30 mb-2 block">Status</label>
                   <select 
                     className={`select select-sm select-bordered w-full bg-base-100 border-base-300 font-bold ${statusConfig[caseItem.status].colorClass} text-white`}
                     value={caseItem.status}
                     onChange={(e) => statusMutation.mutate(e.target.value as CaseStatus)}
                   >
                      <option value="open">Open Case</option>
                      <option value="in_progress">In Progress</option>
                      <option value="resolved">Mark Resolved</option>
                      <option value="closed">Close Case</option>
                   </select>
                </div>

                {/* Severity Badge (not a selector for now to keep it simple) */}
                <div>
                   <label className="text-[10px] font-black uppercase tracking-widest text-base-content/30 mb-2 block">Severity</label>
                   <div className={`flex items-center gap-2 px-4 py-2 rounded-xl bg-base-200 border border-base-300`}>
                      <div className={`w-3 h-3 rounded-full ${severityConfig[caseItem.severity].bg} animate-pulse`}></div>
                      <span className="font-black text-sm uppercase tracking-widest">{caseItem.severity}</span>
                      <button className="btn btn-ghost btn-xs ml-auto opacity-30 hover:opacity-100">
                         <Edit2 className="w-3 h-3" />
                      </button>
                   </div>
                </div>

                {/* Assigned To */}
                <div>
                   <label className="text-[10px] font-black uppercase tracking-widest text-base-content/30 mb-2 block">Assigned To</label>
                   <div className="flex items-center gap-3 p-4 rounded-2xl bg-base-200 border border-base-300">
                      <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center border border-primary/20 shrink-0">
                         <UserIcon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                         <h4 className="font-bold truncate text-sm">{caseItem.assigned_to?.email.split('@')[0] || 'Unassigned'}</h4>
                         <p className="text-[10px] text-base-content/40 truncate">Security Analyst</p>
                      </div>
                      <button className="btn btn-ghost btn-xs opacity-50 hover:bg-primary/10 hover:text-primary">Change</button>
                   </div>
                </div>
             </div>
           </div>

           {/* Quick Actions Panel */}
           <div className="bg-base-100 p-8 rounded-3xl border border-base-300 shadow-sm relative overflow-hidden group">
              <h3 className="text-xl font-black mb-6 flex items-center gap-2 relative z-10">
                <ShieldAlert className="w-6 h-6 text-primary" />
                Tools & Scopes
              </h3>
              
              <div className="grid grid-cols-1 gap-3 relative z-10">
                 <button className="btn btn-sm bg-base-100 hover:bg-primary hover:text-primary-content border-base-300 flex justify-between group-hover:shadow-md transition-all">
                    <span className="flex items-center gap-2 font-bold"><Terminal className="w-4 h-4" /> Open DevTools Panel</span>
                    <ExternalLink className="w-3 h-3 opacity-30" />
                 </button>
                 <button className="btn btn-sm bg-base-100 hover:bg-primary hover:text-primary-content border-base-300 flex justify-between">
                    <span className="flex items-center gap-2 font-bold"><Play className="w-4 h-4" /> Start Sandbox Run</span>
                    <ExternalLink className="w-3 h-3 opacity-30" />
                 </button>
                 <button className="btn btn-sm bg-base-100 hover:bg-primary hover:text-primary-content border-base-300 flex justify-between">
                    <span className="flex items-center gap-2 font-bold"><FileSearch className="w-4 h-4" /> View Scan Details</span>
                    <ExternalLink className="w-3 h-3 opacity-30" />
                 </button>
              </div>

              <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:scale-110 transition-transform">
                <ShieldAlert className="w-32 h-32" />
              </div>
           </div>

           {/* Metrics / Timeline Summary */}
           <div className="bg-gradient-to-br from-primary to-primary-focus p-8 rounded-3xl text-primary-content shadow-xl shadow-primary/20">
              <h3 className="text-xl font-black mb-4 flex items-center gap-2">
                <History className="w-6 h-6" />
                Timeline
              </h3>
              <div className="space-y-4">
                 <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                       <Check className="w-4 h-4 text-primary-content bg-white/20 rounded-full p-0.5" />
                       <div className="w-0.5 h-full bg-white/10 my-1"></div>
                    </div>
                    <div>
                        <p className="text-[10px] font-black uppercase tracking-widest opacity-60">Created</p>
                        <p className="text-sm font-bold">{new Date(caseItem.created_at).toLocaleDateString()}</p>
                    </div>
                 </div>
                 <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                       <Activity className="w-4 h-4 text-primary-content bg-white/20 rounded-full p-0.5" />
                       <div className="w-0.5 h-6 bg-white/10 my-1"></div>
                    </div>
                    <div>
                        <p className="text-[10px] font-black uppercase tracking-widest opacity-60">Last Update</p>
                        <p className="text-sm font-bold">{new Date(caseItem.updated_at).toLocaleDateString()} {new Date(caseItem.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                    </div>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
};
