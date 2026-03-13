import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ExternalLink, ShieldAlert, Monitor, Globe } from 'lucide-react';
import { scansApi } from '../../api/scans';
import { RiskScoreIndicator } from '../../components/investigation/RiskScoreIndicator';
import { ExplanationReasonPanel } from '../../components/investigation/ExplanationReasonPanel';

export const ScanDetailsPage = () => {
  const { id } = useParams<{ id: string }>();

  const { data: scan, isLoading, error } = useQuery({
    queryKey: ['scan', id],
    queryFn: () => scansApi.getScanById(id!),
    enabled: !!id,
  });

  if (isLoading) return <div className="p-10 text-center"><span className="loading loading-lg text-primary"></span></div>;
  if (error || !scan) return <div className="alert alert-error">Failed to load scan details.</div>;

  const reasons = scan.explanation?.reasons || [];
  
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-4">
        <Link to="/scans" className="btn btn-circle btn-ghost btn-sm">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            Scan Details <span className="text-base-content/50 text-xl">#{scan.id}</span>
          </h1>
          <p className="text-base-content/70 text-sm">{new Date(scan.created_at).toLocaleString()} • Source: {scan.source || 'API'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card bg-base-100 border border-base-300 shadow-sm">
            <div className="card-body p-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-base-content/60 mb-2">Target URL</h2>
              <div className="flex items-center justify-between bg-base-200 p-4 rounded-lg font-mono text-sm break-all">
                {scan.url}
                <a href={scan.url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-xs ml-4">
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>
          </div>

          <RiskScoreIndicator score={scan.confidence} prediction={scan.prediction} />

          <ExplanationReasonPanel reasons={reasons} />
        </div>

        <div className="space-y-6">
          <div className="card bg-base-100 border border-base-300 shadow-sm">
            <div className="card-body p-6">
              <h3 className="card-title text-base flex items-center gap-2 mb-4">
                <Globe className="w-5 h-5" /> Client Telemetry
              </h3>
              <div className="space-y-3">
                <div>
                  <div className="text-xs text-base-content/60 font-semibold">IP Address</div>
                  <div className="font-mono text-sm">{scan.ip_address || 'N/A'}</div>
                </div>
                <div>
                  <div className="text-xs text-base-content/60 font-semibold">Client Type</div>
                  <div className="text-sm">{scan.client_type || 'N/A'}</div>
                </div>
                <div>
                  <div className="text-xs text-base-content/60 font-semibold">User Agent</div>
                  <div className="text-xs bg-base-200 p-2 rounded mt-1 break-words">{scan.user_agent || 'N/A'}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="card bg-base-100 border border-base-300 shadow-sm border-l-4 border-l-info">
            <div className="card-body p-6">
              <h3 className="card-title text-base flex items-center gap-2 mb-2">
                <Monitor className="w-5 h-5 text-info" /> Sandbox
              </h3>
              <p className="text-sm text-base-content/70 mb-4">
                Dynamic behavior analysis available for this URL.
              </p>
              <Link to={`/sandbox?query=${encodeURIComponent(scan.url)}`} className="btn btn-outline btn-info btn-sm self-start">
                View Sandbox Runs
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
