import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { casesApi, CaseSeverity } from '../../api/cases';
import { X, AlertTriangle, Briefcase, Info } from 'lucide-react';

interface CreateCaseModalProps {
  onClose: () => void;
  alertIds: number[];
}

export const CreateCaseModal = ({ onClose, alertIds }: CreateCaseModalProps) => {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<CaseSeverity>('medium');
  const [useExisting, setUseExisting] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);

  const { data: existingCases = [] } = useQuery({
    queryKey: ['cases', { status: 'open' }],
    queryFn: () => casesApi.getCases({ status: 'open' }),
    enabled: useExisting
  });

  const createMutation = useMutation({
    mutationFn: () => casesApi.createCase({ title, description, severity, alert_ids: alertIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      onClose();
    }
  });

  const linkMutation = useMutation({
    mutationFn: () => casesApi.linkAlerts(selectedCaseId!, alertIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', selectedCaseId?.toString()] });
      onClose();
    }
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-base-300/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-base-100 w-full max-w-lg rounded-3xl shadow-2xl border border-base-300 overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="p-6 border-b border-base-300 flex justify-between items-center bg-base-100/50">
          <h3 className="text-xl font-black flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-primary" />
            {useExisting ? 'Add to Existing Case' : 'Create New Investigation'}
          </h3>
          <button onClick={onClose} className="btn btn-ghost btn-sm btn-circle"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-8 space-y-6">
          <div className="flex gap-2 p-1 bg-base-200 rounded-xl mb-4">
             <button 
               onClick={() => setUseExisting(false)}
               className={`flex-1 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${!useExisting ? 'bg-base-100 shadow-sm text-primary' : 'text-base-content/40 hover:text-base-content/60'}`}
             >
                New Case
             </button>
             <button 
               onClick={() => setUseExisting(true)}
               className={`flex-1 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${useExisting ? 'bg-base-100 shadow-sm text-primary' : 'text-base-content/40 hover:text-base-content/60'}`}
             >
                Existing Case
             </button>
          </div>

          <div className="bg-primary/5 p-4 rounded-2xl border border-primary/10 flex items-start gap-3">
             <Info className="w-5 h-5 text-primary shrink-0 mt-0.5" />
             <p className="text-xs font-medium text-primary/80">
                You are about to link <strong>{alertIds.length} alert(s)</strong> to a case. This will help track the investigation and resolution process.
             </p>
          </div>

          {!useExisting ? (
            <div className="space-y-4">
              <div className="form-control">
                <label className="label pt-0"><span className="label-text font-bold text-xs uppercase tracking-widest text-base-content/40">Case Title</span></label>
                <input 
                  type="text" 
                  className="input input-sm input-bordered focus:border-primary transition-all font-medium" 
                  placeholder="e.g. Unusual login pattern investigation"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="form-control">
                <label className="label"><span className="label-text font-bold text-xs uppercase tracking-widest text-base-content/40">Severity</span></label>
                <div className="flex gap-2">
                   {(['critical', 'high', 'medium', 'low'] as const).map((sev) => (
                     <button
                        key={sev}
                        type="button"
                        onClick={() => setSeverity(sev)}
                        className={`btn btn-xs flex-1 border border-base-300 font-bold uppercase tracking-tighter ${severity === sev ? (
                          sev === 'critical' ? 'bg-error text-white' : 
                          sev === 'high' ? 'bg-warning text-white' :
                          sev === 'medium' ? 'bg-info text-white' : 'bg-success text-white'
                        ) : 'bg-base-200'}`}
                     >
                        {sev}
                     </button>
                   ))}
                </div>
              </div>

              <div className="form-control">
                <label className="label"><span className="label-text font-bold text-xs uppercase tracking-widest text-base-content/40">Internal Notes (Optional)</span></label>
                <textarea 
                  className="textarea textarea-sm textarea-bordered focus:border-primary transition-all font-medium min-h-[100px]" 
                  placeholder="Provide context for the investigation..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            </div>
          ) : (
            <div className="form-control">
               <label className="label pt-0"><span className="label-text font-bold text-xs uppercase tracking-widest text-base-content/40">Select Case</span></label>
               <select 
                 className="select select-sm select-bordered w-full font-medium"
                 value={selectedCaseId || ''}
                 onChange={(e) => setSelectedCaseId(parseInt(e.target.value))}
               >
                  <option value="" disabled>Choose an open case...</option>
                  {existingCases.map(c => (
                    <option key={c.id} value={c.id}>Case #{c.id}: {c.title}</option>
                  ))}
               </select>
               {existingCases.length === 0 && (
                 <p className="text-[10px] text-error mt-2 font-bold uppercase tracking-widest">No open cases found to link with.</p>
               )}
            </div>
          )}
        </div>

        <div className="p-6 bg-base-200/50 border-t border-base-300 flex justify-end gap-3">
          <button onClick={onClose} className="btn btn-ghost btn-sm font-bold uppercase tracking-widest">Cancel</button>
          {!useExisting ? (
            <button 
                onClick={() => createMutation.mutate()} 
                className="btn btn-primary btn-sm font-bold uppercase tracking-widest px-6 shadow-lg shadow-primary/20"
                disabled={!title || createMutation.isPending}
            >
              {createMutation.isPending ? <span className="loading loading-spinner loading-xs"></span> : 'Create Case'}
            </button>
          ) : (
            <button 
                onClick={() => linkMutation.mutate()} 
                className="btn btn-primary btn-sm font-bold uppercase tracking-widest px-6 shadow-lg shadow-primary/20"
                disabled={!selectedCaseId || linkMutation.isPending}
            >
              {linkMutation.isPending ? <span className="loading loading-spinner loading-xs"></span> : 'Add to Case'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
