import React from 'react';

interface NetworkRequest {
  url: string;
  method: string;
  status: number;
  type: string;
  is_suspicious: boolean;
}

interface NetworkVisualizationProps {
  requests: NetworkRequest[];
}

export const NetworkVisualization: React.FC<NetworkVisualizationProps> = ({ requests }) => {
  if (!requests || requests.length === 0) {
    return <div className="p-4 bg-base-100 italic rounded-lg">No network activity captured.</div>;
  }

  return (
    <div className="bg-base-100 border border-base-300 rounded-lg overflow-x-auto">
      <table className="table w-full">
        <thead>
          <tr className="bg-base-200">
            <th>Method</th>
            <th>Type</th>
            <th>URL</th>
            <th>Status</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {requests.map((req, idx) => (
            <tr key={idx} className={req.is_suspicious ? 'bg-error/10' : ''}>
              <td><span className="badge badge-outline">{req.method}</span></td>
              <td className="text-xs uppercase">{req.type}</td>
              <td className="font-mono text-xs max-w-xs truncate" title={req.url}>{req.url}</td>
              <td>
                <span className={`badge ${req.status >= 400 ? 'badge-error' : 'badge-ghost'}`}>
                  {req.status}
                </span>
              </td>
              <td>
                {req.is_suspicious && <span className="badge badge-error badge-sm">Suspicious</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
