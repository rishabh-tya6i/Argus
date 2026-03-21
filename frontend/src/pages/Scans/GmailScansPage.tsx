import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Mail, RefreshCw, ShieldAlert, CheckCircle, ExternalLink, User } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

interface EmailScan {
  id: number;
  email_id: str;
  subject: string;
  sender: string;
  scan_id: number;
  detection_result: string;
  risk_score: number;
  created_at: string;
}

export const GmailScansPage = () => {
  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);

  const { data: emailScans = [], isLoading } = useQuery<EmailScan[]>({
    queryKey: ['gmail-scans'],
    queryFn: async () => {
      const resp = await axios.get(`${API_BASE_URL}/gmail/scans`);
      return resp.data;
    }
  });

  const syncMutation = useMutation({
    mutationFn: async () => {
      setIsSyncing(true);
      const resp = await axios.post(`${API_BASE_URL}/gmail/sync`, { user_id: 1 }); // Mock user_id
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmail-scans'] });
      setIsSyncing(false);
    },
    onError: () => {
      setIsSyncing(false);
      alert('Failed to sync Gmail. Ensure backend is running.');
    }
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Mail className="w-6 h-6 text-primary" /> Gmail Integration
          </h1>
          <p className="text-base-content/70">Automatic link extraction and phishing detection from your inbox.</p>
        </div>
        <button 
          className={`btn btn-primary gap-2 ${isSyncing ? 'loading' : ''}`}
          onClick={() => syncMutation.mutate()}
          disabled={isSyncing}
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
          Sync Inbox
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {isLoading ? (
          <div className="flex justify-center p-20"><span className="loading loading-lg text-primary"></span></div>
        ) : emailScans.length === 0 ? (
          <div className="bg-base-100 p-20 text-center border-2 border-dashed border-base-300 rounded-2xl">
            <Mail className="w-12 h-12 mx-auto mb-4 text-base-content/20" />
            <h3 className="text-lg font-semibold">No scanned emails yet</h3>
            <p className="text-base-content/60 max-w-xs mx-auto mb-6">Click Sync Inbox to start fetching and analyzing links from your recent emails.</p>
          </div>
        ) : (
          emailScans.map((scan) => (
            <div key={scan.id} className={`card bg-base-100 border-l-4 ${
              scan.detection_result === 'phishing' ? 'border-l-error' : 
              scan.detection_result === 'safe' ? 'border-l-success' : 'border-l-warning'
            } shadow-sm border border-base-200 hover:shadow-md transition-all`}>
              <div className="card-body p-4 flex-row items-center gap-4">
                <div className={`p-3 rounded-full ${
                  scan.detection_result === 'phishing' ? 'bg-error/10 text-error' : 
                  scan.detection_result === 'safe' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                }`}>
                  {scan.detection_result === 'phishing' ? <ShieldAlert className="w-6 h-6" /> : <CheckCircle className="w-6 h-6" />}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold truncate text-lg">{scan.subject}</span>
                    <span className={`badge badge-sm uppercase font-bold ${
                       scan.detection_result === 'phishing' ? 'badge-error' : 
                       scan.detection_result === 'safe' ? 'badge-success' : 'badge-warning'
                    }`}>{scan.detection_result}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-base-content/60">
                    <span className="flex items-center gap-1"><User className="w-3 h-3" /> {scan.sender}</span>
                    <span>{new Date(scan.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                <div className="text-right px-4 border-l border-base-200">
                  <div className="text-xs text-base-content/50 uppercase font-bold mb-1">Risk Score</div>
                  <div className={`text-xl font-black ${
                    scan.risk_score > 0.8 ? 'text-error' : 
                    scan.risk_score < 0.3 ? 'text-success' : 'text-warning'
                  }`}>
                    {(scan.risk_score * 100).toFixed(1)}%
                  </div>
                </div>

                <a href={`/scans/${scan.scan_id}`} className="btn btn-ghost btn-circle">
                  <ExternalLink className="w-5 h-5" />
                </a>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
