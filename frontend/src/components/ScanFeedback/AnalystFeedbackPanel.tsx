import React, { useState } from 'react';
import { MessageSquare, ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { feedbackApi } from '../../api/feedback';

interface Props {
  scanId: number;
}

export const AnalystFeedbackPanel: React.FC<Props> = ({ scanId }) => {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState('');
  
  const { data: feedbackList } = useQuery({
    queryKey: ['scanFeedback', scanId],
    queryFn: () => feedbackApi.getFeedbackByScan(scanId),
    enabled: !!scanId,
  });

  const mutation = useMutation({
    mutationFn: (label: 'safe' | 'suspicious' | 'phishing') => 
      feedbackApi.submitFeedback({ scan_id: scanId, label, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scanFeedback', scanId] });
      setNotes('');
    },
  });

  const getConsensus = () => {
    if (!feedbackList || feedbackList.length === 0) return null;
    const counts = feedbackList.reduce((acc, f) => {
      acc[f.label] = (acc[f.label] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    let maxLabel: string | null = null;
    let maxCount = 0;
    for (const [label, count] of Object.entries(counts)) {
      if (count > maxCount) {
        maxCount = count;
        maxLabel = label;
      }
    }
    return { label: maxLabel, count: maxCount, total: feedbackList.length };
  };

  const consensus = getConsensus();

  const getConsensusColor = (label: string | null) => {
    switch(label) {
      case 'safe': return 'alert-success';
      case 'phishing': return 'alert-error';
      case 'suspicious': return 'alert-warning';
      default: return 'alert-info';
    }
  };

  return (
    <div className="card bg-base-100 border border-base-300 shadow-sm overflow-hidden">
      <div className="card-body p-6">
        <h3 className="card-title text-base flex items-center gap-2 mb-4">
          <MessageSquare className="w-5 h-5 text-primary" /> Analyst Feedback
        </h3>
        
        {consensus && (
          <div className={`alert ${getConsensusColor(consensus.label)} py-3 mb-4 text-sm rounded-lg border-2 shadow-sm`}>
            <div className="flex items-center gap-3">
              {consensus.label === 'safe' && <ShieldCheck className="w-5 h-5" />}
              {consensus.label === 'phishing' && <ShieldAlert className="w-5 h-5" />}
              {consensus.label === 'suspicious' && <AlertTriangle className="w-5 h-5" />}
              <div>
                <span className="font-bold uppercase mr-1">{consensus.label}</span> 
                Consensus reached by {consensus.count} out of {consensus.total} analysts
              </div>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button 
              onClick={() => mutation.mutate('safe')}
              disabled={mutation.isPending}
              className={`btn btn-sm flex-1 ${mutation.isPending ? 'loading' : ''} btn-success text-white hover:shadow-md transition-all gap-2`}
            >
              <ShieldCheck className="w-4 h-4" /> Safe
            </button>
            <button 
              onClick={() => mutation.mutate('suspicious')}
              disabled={mutation.isPending}
              className={`btn btn-sm flex-1 ${mutation.isPending ? 'loading' : ''} btn-warning text-white hover:shadow-md transition-all gap-2`}
            >
              <AlertTriangle className="w-4 h-4" /> Suspicious
            </button>
            <button 
              onClick={() => mutation.mutate('phishing')}
              disabled={mutation.isPending}
              className={`btn btn-sm flex-1 ${mutation.isPending ? 'loading' : ''} btn-error text-white hover:shadow-md transition-all gap-2`}
            >
              <ShieldAlert className="w-4 h-4" /> Phishing
            </button>
          </div>

          <div className="form-control">
            <label className="label py-1">
              <span className="label-text-alt text-base-content/50">Add context for the ML retraining loop</span>
            </label>
            <textarea 
              className="textarea textarea-bordered textarea-sm h-16 w-full focus:textarea-primary transition-colors bg-base-200/50" 
              placeholder="E.g. Brand keyword mismatch, suspicious domain pattern recognized..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            ></textarea>
          </div>

          {feedbackList && feedbackList.length > 0 && (
            <div className="mt-6 border-t border-base-200 pt-5">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-base-content/40 mb-3 ml-1">Previous Reports</h4>
              <div className="space-y-3 max-h-48 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-base-300">
                {feedbackList.map((f) => (
                  <div key={f.id} className="text-xs bg-base-200/50 p-3 rounded-lg border border-transparent hover:border-base-300 transition-all group">
                    <div className="flex justify-between items-center mb-2">
                      <span className={`px-2 py-0.5 rounded-full font-bold uppercase text-[9px] tracking-wider 
                        ${f.label === 'safe' ? 'bg-success/20 text-success' : 
                          f.label === 'phishing' ? 'bg-error/20 text-error' : 
                          'bg-warning/20 text-warning'}`}>
                        {f.label}
                      </span>
                      <span className="text-base-content/40 text-[10px] tabular-nums">{new Date(f.created_at).toLocaleDateString()}</span>
                    </div>
                    {f.notes ? (
                      <p className="text-base-content/70 italic leading-relaxed py-1">"{f.notes}"</p>
                    ) : (
                      <p className="text-base-content/30 italic py-1">No notes provided</p>
                    )}
                    <div className="text-[9px] mt-2 flex justify-between text-base-content/30 opacity-0 group-hover:opacity-100 transition-opacity">
                      <span>AnalystRef: {f.analyst_user_id}</span>
                      <span>ID: #{f.id}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
