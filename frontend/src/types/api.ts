import { AxiosError } from 'axios';

export interface User {
  id: number;
  email: string;
  role: 'viewer' | 'analyst' | 'engineer' | 'admin';
  tenant_id: number;
}

export interface Tenant {
  id: number;
  name: string;
  slug: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
}

export interface ApiError {
  detail: string;
}

export type QueryError = AxiosError<ApiError>;

export interface Scan {
  id: number;
  url: string;
  source: string | null;
  created_at: string;
  prediction: string;
  confidence: number;
}

export interface ScanDetail extends Scan {
  explanation: any; // Will type properly based on reason codes
  client_type: string | null;
  ip_address: string | null;
  user_agent: string | null;
}

export interface SandboxRun {
  id: number;
  scan_id: number | null;
  url: string;
  status: string;
  created_at: string;
}

export interface ThreatAlert {
  id: number;
  tenant_id: number;
  brand: string;
  suspicious_domain: string;
  alert_type: string;
  status: string;
}
