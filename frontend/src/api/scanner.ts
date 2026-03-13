import apiClient from './client';

export interface SecurityScanIssue {
  id: number;
  run_id: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  description: string;
  remediation: string | null;
}

export interface SecurityScanArtifact {
  id: number;
  run_id: number;
  artifact_type: string;
  storage_path: string;
  created_at: string;
}

export interface SecurityScanResponse {
  id: number;
  tenant_id: number;
  url: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  started_at: string | null;
  finished_at: string | null;
  score: number | null;
  summary: string | null;
  issues: SecurityScanIssue[];
  artifacts: SecurityScanArtifact[];
}

export const scannerApi = {
  createScan: async (url: string): Promise<SecurityScanResponse> => {
    const response = await apiClient.post('/security-scans', { url });
    return response.data;
  },
  getScans: async (): Promise<SecurityScanResponse[]> => {
    const response = await apiClient.get('/security-scans');
    return response.data;
  },
  getScanById: async (id: number | string): Promise<SecurityScanResponse> => {
    const response = await apiClient.get(`/security-scans/${id}`);
    return response.data;
  }
};
