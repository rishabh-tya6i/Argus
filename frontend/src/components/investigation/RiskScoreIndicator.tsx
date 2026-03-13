import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

interface RiskScoreIndicatorProps {
  score: number;
  prediction: string;
}

export const RiskScoreIndicator: React.FC<RiskScoreIndicatorProps> = ({ score, prediction }) => {
  // Map prediction to daisyUI colors
  const colorClass = 
    prediction.toLowerCase() === 'safe' ? 'text-success border-success' :
    prediction.toLowerCase() === 'phishing' ? 'text-error border-error' : 
    'text-warning border-warning';

  const Icon = 
    prediction.toLowerCase() === 'safe' ? CheckCircle2 :
    prediction.toLowerCase() === 'phishing' ? XCircle : 
    AlertTriangle;

  return (
    <div className={`p-6 bg-base-100 rounded-xl border-t-4 border shadow-sm flex items-center gap-6 ${colorClass}`}>
      <Icon className="w-16 h-16" />
      <div>
        <h2 className="text-sm text-base-content/60 font-semibold uppercase tracking-wider">Classification</h2>
        <div className="text-3xl font-bold capitalize mt-1">{prediction}</div>
      </div>
      <div className="ml-auto text-right">
        <h2 className="text-sm text-base-content/60 font-semibold uppercase tracking-wider">Model Confidence</h2>
        <div className="text-4xl font-mono font-black mt-1">{(score * 100).toFixed(1)}%</div>
      </div>
    </div>
  );
};
