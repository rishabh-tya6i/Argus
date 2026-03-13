import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Filter, Search } from 'lucide-react';
import { scansApi } from '../../api/scans';

export const ScansPage = () => {
  const { data: scans = [], isLoading } = useQuery({ 
    queryKey: ['scans'], 
    queryFn: scansApi.getScans 
  });
  
  const [filterQuery, setFilterQuery] = useState('');
  const [filterClass, setFilterClass] = useState('ALL');

  const filteredScans = scans.filter(s => {
    const matchesSearch = s.url.includes(filterQuery) || s.source?.includes(filterQuery);
    const matchesClass = filterClass === 'ALL' || s.prediction.toUpperCase() === filterClass;
    return matchesSearch && matchesClass;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold">Investigation / Scans</h1>
          <p className="text-base-content/70">View and filter URL scanning history.</p>
        </div>
      </div>

      <div className="bg-base-100 p-4 border border-base-300 rounded-xl shadow-sm flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="w-5 h-5 absolute left-3 top-3 text-base-content/50" />
          <input 
            type="text" 
            placeholder="Search by URL or Source..." 
            className="input input-bordered w-full pl-10"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-base-content/70" />
          <select 
            className="select select-bordered"
            value={filterClass}
            onChange={(e) => setFilterClass(e.target.value)}
          >
            <option value="ALL">All Classifications</option>
            <option value="PHISHING">Phishing</option>
            <option value="SUSPICIOUS">Suspicious</option>
            <option value="SAFE">Safe</option>
          </select>
        </div>
      </div>

      <div className="bg-base-100 border border-base-300 rounded-xl shadow-sm overflow-x-auto">
        <table className="table">
          <thead>
            <tr className="bg-base-200/50">
              <th>ID</th>
              <th>Date</th>
              <th>URL</th>
              <th>Confidence</th>
              <th>Verdict</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={7} className="text-center py-10">
                  <span className="loading loading-spinner text-primary"></span>
                </td>
              </tr>
            ) : filteredScans.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-10 text-base-content/50">
                  No scans found matching your filters.
                </td>
              </tr>
            ) : (
              filteredScans.map((scan) => (
                <tr key={scan.id} className="hover">
                  <td className="font-mono text-xs">{scan.id}</td>
                  <td className="text-xs whitespace-nowrap">{new Date(scan.created_at).toLocaleString()}</td>
                  <td className="max-w-[300px] truncate font-mono text-sm" title={scan.url}>{scan.url}</td>
                  <td>{(scan.confidence * 100).toFixed(1)}%</td>
                  <td>
                    <span className={`badge ${
                      scan.prediction === 'phishing' ? 'badge-error' : 
                      scan.prediction === 'safe' ? 'badge-success' : 'badge-warning'
                    } badge-sm uppercase font-bold`}>
                      {scan.prediction}
                    </span>
                  </td>
                  <td className="text-xs uppercase">{scan.source || 'API'}</td>
                  <td>
                    <Link to={`/scans/${scan.id}`} className="btn btn-ghost btn-xs font-semibold">Investigate</Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
