import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ShieldAlert, Search, Activity, Flag } from 'lucide-react';
import { intelApi } from '../../api/intel';

export const ThreatIntelPage = () => {
  const [domainSearch, setDomainSearch] = useState('');
  const [searchedDomain, setSearchedDomain] = useState<string | null>(null);

  const { data: alerts = [], isLoading: loadingAlerts } = useQuery({
    queryKey: ['intel', 'impersonation'],
    queryFn: intelApi.getImpersonationAlerts
  });

  const { data: reputation, isLoading: loadingRep, refetch } = useQuery({
    queryKey: ['intel', 'domain', searchedDomain],
    queryFn: () => intelApi.getDomainReputation(searchedDomain!),
    enabled: !!searchedDomain,
    retry: false
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (domainSearch.trim()) {
      setSearchedDomain(domainSearch.trim());
      refetch();
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ShieldAlert className="w-6 h-6 text-error" /> Threat Intelligence
        </h1>
        <p className="text-base-content/70">Impersonation alerts and global domain reputation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Activity className="w-5 h-5 text-warning" /> Brand Impersonation Alerts
          </h2>
          <div className="bg-base-100 border border-base-300 rounded-xl shadow-sm overflow-hidden">
            {loadingAlerts ? (
              <div className="p-8 text-center text-primary"><span className="loading loading-spinner"></span></div>
            ) : alerts.length === 0 ? (
              <div className="p-8 text-center text-base-content/50">
                <Flag className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p>No active impersonation alerts targeting your configuration.</p>
              </div>
            ) : (
              <table className="table">
                <thead className="bg-base-200">
                  <tr>
                    <th>Target Brand</th>
                    <th>Suspicious Domain</th>
                    <th>Intelligence</th>
                    <th>Risk</th>
                    <th>Type</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((a: any) => (
                    <tr key={a.id}>
                      <td className="font-semibold">{a.brand_name}</td>
                      <td className="font-mono text-xs">{a.suspicious_domain}</td>
                      <td className="text-xs text-base-content/70">
                        {a.enrichment ? (
                          <div className="flex flex-col gap-0.5">
                            {a.enrichment.ip_address && <span>IP: {a.enrichment.ip_address}</span>}
                            {a.enrichment.registrar && <span>Registrar: {a.enrichment.registrar}</span>}
                            {a.enrichment.domain_age_days !== undefined && <span>Age: {a.enrichment.domain_age_days}d</span>}
                          </div>
                        ) : 'Pending'}
                      </td>
                      <td>
                        <span className={`badge ${a.risk_score >= 0.7 ? 'badge-error' : 'badge-warning'} font-mono`}>
                          {Math.round(a.risk_score * 100)}%
                        </span>
                      </td>
                      <td><span className="badge badge-outline badge-sm">{a.detection_type}</span></td>
                      <td><button className="btn btn-xs btn-outline">Triage</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Search className="w-5 h-5 text-info" /> Global Domain Reputation Lookup
          </h2>
          <div className="card bg-base-100 border border-base-300 shadow-sm">
            <div className="card-body">
              <form onSubmit={handleSearch} className="flex gap-2 mb-4">
                <input 
                  type="text" 
                  className="input input-bordered w-full flex-1 font-mono text-sm" 
                  placeholder="e.g. login-update-secure.com" 
                  value={domainSearch}
                  onChange={(e) => setDomainSearch(e.target.value)}
                />
                <button type="submit" className="btn btn-primary" disabled={loadingRep || !domainSearch}>
                  {loadingRep ? <span className="loading loading-spinner loading-sm"></span> : 'Scan'}
                </button>
              </form>

              {searchedDomain && (
                <div className="mt-4 border border-base-300 rounded-lg overflow-hidden">
                  <div className="bg-base-200 p-3 font-mono text-center font-bold">
                    {searchedDomain}
                  </div>
                  <div className="p-6 text-center space-y-4">
                    {loadingRep ? (
                      <span className="loading loading-spinner text-info"></span>
                    ) : reputation ? (
                      <div>
                        {/* Example displaying fetched reputation */}
                        <div className="text-4xl font-black mb-2 flex items-center justify-center gap-2 text-warning">
                           Risk: {reputation.score || 0}/100
                        </div>
                        <div className="flex flex-wrap justify-center gap-2 mt-4">
                          {(reputation.flags || []).map((f: string, i: number) => (
                            <span key={i} className="badge badge-error uppercase font-bold tracking-wider text-xs p-3">{f}</span>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-base-content/60">No adverse historical intelligence found for this domain.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
