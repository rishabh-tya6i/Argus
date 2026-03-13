import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Box, Play, AlertCircle } from 'lucide-react';
import { sandboxApi } from '../../api/sandbox';
import { SandboxTimeline } from '../../components/investigation/SandboxTimeline';
import { NetworkVisualization } from '../../components/investigation/NetworkVisualization';

export const SandboxPage = () => {
  const [activeTab, setActiveTab] = useState<'runs' | 'analysis'>('runs');
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['sandboxRuns'],
    queryFn: sandboxApi.getRuns
  });

  const { data: runDetails, isLoading: runningDetails } = useQuery({
    queryKey: ['sandboxRun', selectedRunId],
    queryFn: () => sandboxApi.getRunById(selectedRunId!),
    enabled: !!selectedRunId,
  });

  const handleSelectRun = (id: number) => {
    setSelectedRunId(id);
    setActiveTab('analysis');
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Box className="w-6 h-6 text-info" /> Sandbox Environments
          </h1>
          <p className="text-base-content/70">Isolated browser execution and dynamic analysis results.</p>
        </div>
        <button className="btn btn-primary gap-2">
          <Play className="w-4 h-4" /> New Sandbox Run
        </button>
      </div>

      <div className="tabs tabs-boxed bg-base-200 p-1 w-fit">
        <button className={`tab ${activeTab === 'runs' ? 'tab-active' : ''}`} onClick={() => setActiveTab('runs')}>Recent Runs</button>
        <button 
          className={`tab ${activeTab === 'analysis' ? 'tab-active' : ''} ${!selectedRunId ? 'opacity-50 cursor-not-allowed' : ''}`} 
          onClick={() => selectedRunId && setActiveTab('analysis')}
          disabled={!selectedRunId}
        >
          Analysis Details
        </button>
      </div>

      {activeTab === 'runs' && (
        <div className="bg-base-100 border border-base-300 rounded-xl shadow-sm overflow-hidden">
          <table className="table w-full">
            <thead className="bg-base-200/50">
              <tr>
                <th>ID</th>
                <th>Target URL</th>
                <th>Status</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={5} className="text-center py-8"><span className="loading loading-spinner"></span></td></tr>
              ) : runs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-base-content/50">
                    <Box className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    No sandbox runs tracked yet. Connect the Sandbox worker pool to begin.
                  </td>
                </tr>
              ) : (
                runs.map(run => (
                  <tr key={run.id} className="hover cursor-pointer" onClick={() => handleSelectRun(run.id)}>
                    <td className="font-mono text-xs">{run.id}</td>
                    <td className="font-mono text-xs truncate max-w-xs">{run.url}</td>
                    <td><span className={`badge ${run.status === 'completed' ? 'badge-success' : 'badge-warning'} badge-sm uppercase`}>{run.status}</span></td>
                    <td className="text-xs">{new Date(run.created_at).toLocaleString()}</td>
                    <td><button className="btn btn-ghost btn-xs">View Report</button></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'analysis' && selectedRunId && (
        <div className="space-y-6">
          {runningDetails ? (
            <div className="flex justify-center p-12"><span className="loading loading-lg text-info"></span></div>
          ) : runDetails ? (
             <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
               <div className="space-y-6">
                 <div className="card bg-base-100 border border-base-300 shadow-sm">
                   <div className="card-body">
                     <h2 className="card-title border-b border-base-300 pb-2">Target</h2>
                     <div className="font-mono text-sm bg-base-200 p-3 rounded">{runDetails.url}</div>
                   </div>
                 </div>
                 {/* MOCK DATA INJECTION IF BACKEND RETURNS EMPTY ARRAY FOR NOW */}
                 <SandboxTimeline events={runDetails.timeline_events || []} />
               </div>
               <div className="space-y-6">
                 <div className="card bg-base-100 border border-base-300 shadow-sm">
                    <div className="card-body">
                      <h2 className="card-title">Final Screenshot</h2>
                      <div className="aspect-video bg-base-200 rounded-lg border border-base-300 flex items-center justify-center text-base-content/40 mt-2 object-cover overflow-hidden">
                        {runDetails.screenshot_url ? (
                          <img src={runDetails.screenshot_url} alt="Sandbox payload" className="w-full h-full object-cover" />
                        ) : (
                          <span>Screenshot Capture Unavailable</span>
                        )}
                      </div>
                    </div>
                 </div>
                 <h3 className="font-semibold text-lg mt-6">Network Activity</h3>
                 <NetworkVisualization requests={runDetails.network_activity || []} />
               </div>
             </div>
          ) : (
            <div className="alert alert-warning shadow-lg">
              <AlertCircle className="w-6 h-6" />
              <div>
                <h3 className="font-bold">Missing Report</h3>
                <div className="text-xs">The sandbox cluster may not have finished writing the bundle.</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
