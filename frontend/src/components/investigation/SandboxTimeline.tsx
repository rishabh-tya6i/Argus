import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Event {
  timestamp: string;
  type: string;
  description: string;
  risk_level: 'low' | 'medium' | 'high';
}

interface SandboxTimelineProps {
  events: Event[];
}

export const SandboxTimeline: React.FC<SandboxTimelineProps> = ({ events }) => {
  if (!events || events.length === 0) {
    return <div className="p-4 bg-base-100 italic rounded-lg">No timeline events captured.</div>;
  }

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-lg">Execution Timeline</h3>
      
      <div className="relative border-l-2 border-base-300 ml-4 space-y-6">
        {events.map((evt, idx) => (
          <div key={idx} className="relative pl-6">
            <span className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-base-100 ${
              evt.risk_level === 'high' ? 'bg-error' : 
              evt.risk_level === 'medium' ? 'bg-warning' : 'bg-info'
            }`}></span>
            <div className="bg-base-100 p-3 rounded-md border border-base-300 shadow-sm">
              <div className="flex justify-between items-center text-xs text-base-content/60 mb-1">
                <span className="font-mono">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                <span className="uppercase font-bold tracking-wider">{evt.type}</span>
              </div>
              <p className="text-sm">{evt.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
