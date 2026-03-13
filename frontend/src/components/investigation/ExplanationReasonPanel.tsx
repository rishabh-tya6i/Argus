import React from 'react';
import { ShieldAlert, ShieldCheck, HelpCircle, Eye } from 'lucide-react';

interface Reason {
  code: string;
  message: string;
  weight: number;
}

interface ExplanationReasonPanelProps {
  reasons: Reason[];
}

export const ExplanationReasonPanel: React.FC<ExplanationReasonPanelProps> = ({ reasons }) => {
  if (!reasons || reasons.length === 0) {
    return (
      <div className="p-4 bg-base-100 rounded-lg border border-base-300">
        <p className="text-sm text-base-content/70">No explanation reasons provided by the model.</p>
      </div>
    );
  }

  const visualImpersonations = reasons.filter(r => r.code === 'BRAND_IMPERSONATION_DETECTED');
  const otherReasons = reasons.filter(r => r.code !== 'BRAND_IMPERSONATION_DETECTED');

  return (
    <div className="space-y-6">
      
      {visualImpersonations.length > 0 && (
         <div className="space-y-3">
             <h3 className="font-semibold text-lg flex items-center gap-2 text-warning">
               <Eye className="w-5 h-5" /> Visual Impersonation Analysis
             </h3>
             <div className="grid gap-3">
               {visualImpersonations.map((reason, idx) => (
                 <div key={`vi-${idx}`} className="p-4 bg-warning/10 rounded-lg border border-warning/50 flex items-start gap-4 shadow-sm">
                   <div className="mt-1">
                     <ShieldAlert className="w-6 h-6 text-warning" />
                   </div>
                   <div className="flex-1">
                     <div className="flex items-center justify-between">
                       <span className="font-mono text-sm font-bold text-warning-content">{reason.code}</span>
                       <span className={`text-sm font-bold text-warning-content`}>
                         Weight: +{reason.weight.toFixed(2)}
                       </span>
                     </div>
                     <p className="text-sm font-medium mt-1">{reason.message}</p>
                   </div>
                 </div>
               ))}
             </div>
         </div>
      )}

      {otherReasons.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-lg flex items-center gap-2">
            <HelpCircle className="w-5 h-5" /> Explanation Reasons
          </h3>
          <div className="grid gap-3">
            {otherReasons.map((reason, idx) => (
              <div key={`or-${idx}`} className="p-4 bg-base-100 rounded-lg border border-base-300 flex items-start gap-4">
                <div className="mt-1">
                  {reason.weight > 0 ? (
                    <ShieldAlert className="w-5 h-5 text-error" />
                  ) : (
                    <ShieldCheck className="w-5 h-5 text-success" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold">{reason.code}</span>
                    <span className={`text-sm font-bold ${reason.weight > 0 ? 'text-error' : 'text-success'}`}>
                      Weight: {reason.weight > 0 ? '+' : ''}{reason.weight.toFixed(2)}
                    </span>
                  </div>
                  <p className="text-sm text-base-content/80 mt-1">{reason.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
    </div>
  );
};
