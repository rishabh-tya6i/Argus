import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scannerApi, SecurityScanResponse } from '../../api/scanner';
import { ShieldCheck, AlertTriangle, AlertCircle, Info, Loader2, ArrowRight } from 'lucide-react';

const SeverityIcon = ({ severity }: { severity: string }) => {
  switch (severity) {
    case 'CRITICAL': return <AlertTriangle className="text-error w-5 h-5" />;
    case 'HIGH': return <AlertCircle className="text-warning w-5 h-5" />;
    case 'MEDIUM': return <AlertCircle className="text-orange-400 w-5 h-5" />;
    case 'LOW': return <Info className="text-info w-5 h-5" />;
    default: return <Info className="w-5 h-5" />;
  }
};

export const SecurityScannerPage = () => {
  const [url, setUrl] = useState('');
  const [activeScanId, setActiveScanId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: scans, isLoading: scansLoading } = useQuery({
    queryKey: ['security_scans'],
    queryFn: () => scannerApi.getScans(),
    refetchInterval: 5000,
  });

  const { data: activeScan, isLoading: activeScanLoading } = useQuery({
    queryKey: ['security_scan', activeScanId],
    queryFn: () => activeScanId ? scannerApi.getScanById(activeScanId) : null,
    enabled: !!activeScanId,
    refetchInterval: (data: any) => data?.status === 'queued' || data?.status === 'running' ? 2000 : false,
  });

  const createScanMutation = useMutation({
    mutationFn: (targetUrl: string) => scannerApi.createScan(targetUrl),
    onSuccess: (data) => {
      setActiveScanId(data.id);
      queryClient.invalidateQueries({ queryKey: ['security_scans'] });
      setUrl('');
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url) {
       createScanMutation.mutate(url);
    }
  };

  const getScoreColor = (score: number | null) => {
    if (score === null) return 'text-base-content';
    if (score >= 80) return 'text-success';
    if (score >= 50) return 'text-warning';
    return 'text-error';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldCheck className="w-8 h-8 text-primary" />
            Website Security Scanner
          </h1>
          <p className="text-base-content/70 mt-1">Deep analysis of web application security configurations and dynamic behaviors.</p>
        </div>
      </div>

      <div className="card bg-base-100 shadow-sm border border-base-300">
        <div className="card-body">
          <form onSubmit={handleSubmit} className="flex gap-4">
            <input
              type="url"
              placeholder="https://example.com"
              className="input input-bordered flex-1"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createScanMutation.isPending}
            >
              {createScanMutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Start Scan'}
            </button>
          </form>
        </div>
      </div>

      {activeScan && (
        <div className="card bg-base-100 shadow-sm border border-base-300">
          <div className="card-body">
            <h2 className="card-title flex items-center gap-2">
              Scan Results: {activeScan.url}
              {['queued', 'running'].includes(activeScan.status) && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
              <div className="col-span-1">
                <div className="stat bg-base-200 rounded-box">
                  <div className="stat-title">Security Score</div>
                  <div className={`stat-value ${getScoreColor(activeScan.score)}`}>
                    {activeScan.score !== null ? activeScan.score : '--'}
                  </div>
                  <div className="stat-desc">Out of 100 points</div>
                </div>
                
                <div className="mt-4">
                  <h3 className="font-semibold mb-2">Status</h3>
                  <div className={`badge ${
                    activeScan.status === 'completed' ? 'badge-success' :
                    activeScan.status === 'failed' ? 'badge-error' : 'badge-primary'
                  }`}>
                    {activeScan.status.toUpperCase()}
                  </div>
                  {activeScan.summary && <p className="text-sm mt-2 text-base-content/70">{activeScan.summary}</p>}
                </div>

                {activeScan.artifacts?.length > 0 && (
                  <div className="mt-6">
                    <h3 className="font-semibold mb-2">Artifacts</h3>
                    {activeScan.artifacts.map(a => (
                      <div key={a.id} className="text-sm">
                         📸 {a.artifact_type}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              <div className="col-span-2 space-y-4">
                <h3 className="font-semibold border-b border-base-200 pb-2">Identified Issues</h3>
                {activeScan.issues?.length === 0 && activeScan.status === 'completed' ? (
                   <p className="text-success flex items-center gap-2">
                     <ShieldCheck className="w-5 h-5" /> No critical security issues found.
                   </p>
                ) : (
                  <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                    {activeScan.issues?.map(issue => (
                      <div key={issue.id} className="bg-base-200 p-4 rounded-lg flex gap-4 items-start">
                        <div className="pt-1"><SeverityIcon severity={issue.severity} /></div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`badge badge-sm ${
                              issue.severity === 'CRITICAL' ? 'badge-error' :
                              issue.severity === 'HIGH' ? 'bg-warning text-warning-content border-warning' :
                              issue.severity === 'MEDIUM' ? 'bg-orange-400 text-white border-orange-400' : 'badge-info'
                            }`}>{issue.severity}</span>
                            <span className="text-xs font-bold uppercase tracking-wider text-base-content/60">{issue.category}</span>
                          </div>
                          <p className="mt-2 font-medium">{issue.description}</p>
                          {issue.remediation && (
                            <div className="mt-3 text-sm bg-base-100 p-3 rounded border border-base-300 flex items-start gap-2">
                              <ArrowRight className="w-4 h-4 mt-0.5 opacity-50 flex-shrink-0" />
                              <span className="opacity-80 break-words">{issue.remediation}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card bg-base-100 shadow-sm border border-base-300">
        <div className="card-body">
          <h2 className="card-title mb-4">Recent Scans</h2>
          {scansLoading ? (
            <div className="flex justify-center p-8"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>URL</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Date</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {scans?.map(scan => (
                    <tr key={scan.id} className="hover">
                      <td>#{scan.id}</td>
                      <td className="max-w-[300px] truncate" title={scan.url}>{scan.url}</td>
                      <td>
                        <span className={`font-semibold ${getScoreColor(scan.score)}`}>
                          {scan.score !== null ? scan.score : '-'}
                        </span>
                      </td>
                      <td>
                        <div className={`badge badge-sm ${
                          scan.status === 'completed' ? 'badge-success' :
                          scan.status === 'failed' ? 'badge-error' : 'badge-primary'
                        }`}>
                          {scan.status}
                        </div>
                      </td>
                      <td>{new Date(scan.started_at || scan.finished_at || '').toLocaleString()}</td>
                      <td>
                        <button 
                          className="btn btn-sm btn-ghost"
                          onClick={() => setActiveScanId(scan.id)}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                  {scans?.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-4 text-base-content/50">No recent security scans</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
