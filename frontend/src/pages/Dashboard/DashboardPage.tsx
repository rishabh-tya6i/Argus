import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ShieldAlert, Globe, Activity, FileText } from 'lucide-react';
import { scansApi } from '../../api/scans';
import { sandboxApi } from '../../api/sandbox';
import { intelApi } from '../../api/intel';

export const DashboardPage = () => {
  // Fetch high-level data
  const { data: scans = [] } = useQuery({ queryKey: ['scans'], queryFn: scansApi.getScans });
  const { data: impersonationAlerts = [] } = useQuery({ queryKey: ['intel', 'impersonation'], queryFn: intelApi.getImpersonationAlerts });
  const { data: sandboxRuns = [] } = useQuery({ queryKey: ['sandboxRuns'], queryFn: sandboxApi.getRuns });

  const totalScans = scans.length;
  const phishingCount = scans.filter(s => s.prediction === 'phishing').length;

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="stat bg-base-100 border border-base-300 rounded-xl shadow-sm">
          <div className="stat-figure text-primary">
            <Globe className="w-8 h-8" />
          </div>
          <div className="stat-title">Total Scans</div>
          <div className="stat-value text-primary">{totalScans}</div>
          <div className="stat-desc">Analyzed URLs</div>
        </div>

        <div className="stat bg-base-100 border border-base-300 rounded-xl shadow-sm">
          <div className="stat-figure text-error">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <div className="stat-title">Phishing Detected</div>
          <div className="stat-value text-error">{phishingCount}</div>
          <div className="stat-desc">High risk blocks</div>
        </div>

        <div className="stat bg-base-100 border border-base-300 rounded-xl shadow-sm">
          <div className="stat-figure text-warning">
            <Activity className="w-8 h-8" />
          </div>
          <div className="stat-title">Sandbox Runs</div>
          <div className="stat-value">{sandboxRuns.length}</div>
          <div className="stat-desc">Dynamic analyses</div>
        </div>

        <div className="stat bg-base-100 border border-base-300 rounded-xl shadow-sm">
          <div className="stat-figure text-secondary">
            <FileText className="w-8 h-8" />
          </div>
          <div className="stat-title">Impersonations</div>
          <div className="stat-value">{impersonationAlerts.length}</div>
          <div className="stat-desc">Active threat intel matches</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card bg-base-100 border border-base-300 shadow-sm">
          <div className="card-body p-6">
            <h2 className="card-title text-lg mb-4">Recent Scans</h2>
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>URL</th>
                    <th>Prediction</th>
                    <th>Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {scans.slice(0, 5).map((scan) => (
                    <tr key={scan.id}>
                      <td className="max-w-[200px] truncate font-mono text-xs">{scan.url}</td>
                      <td>
                        <span className={`badge ${
                          scan.prediction === 'phishing' ? 'badge-error' : 
                          scan.prediction === 'safe' ? 'badge-success' : 'badge-warning'
                        } badge-sm uppercase font-bold`}>
                          {scan.prediction}
                        </span>
                      </td>
                      <td className="text-xs text-base-content/70">{new Date(scan.created_at).toLocaleDateString()}</td>
                      <td>
                        <Link to={`/scans/${scan.id}`} className="btn btn-ghost btn-xs">View</Link>
                      </td>
                    </tr>
                  ))}
                  {scans.length === 0 && (
                    <tr>
                      <td colSpan={4} className="text-center py-4 text-base-content/50 italic">No recent scans.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex justify-end">
              <Link to="/scans" className="btn btn-outline border-base-300 btn-sm">View All Scans</Link>
            </div>
          </div>
        </div>
        
        <div className="card bg-base-100 border border-base-300 shadow-sm">
          <div className="card-body p-6">
            <h2 className="card-title text-lg mb-4">Active Impersonation Alerts</h2>
            <div className="space-y-4">
              {impersonationAlerts.slice(0, 5).map(alert => (
                <div key={alert.id} className="flex justify-between items-center p-3 border border-base-300 rounded-lg">
                  <div>
                    <div className="text-xs font-semibold text-base-content/70 mb-1">Brand: {alert.brand}</div>
                    <div className="font-mono text-sm">{alert.suspicious_domain}</div>
                  </div>
                  <span className="badge badge-warning badge-sm">{alert.alert_type}</span>
                </div>
              ))}
              {impersonationAlerts.length === 0 && (
                <div className="p-8 text-center border border-dashed border-base-300 rounded-lg text-base-content/50">
                  <ShieldAlert className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p>No active impersonation alerts.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
