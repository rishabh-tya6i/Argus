import api from './client';

export interface SecurityAlert {
  id: number;
  tenant_id: number;
  alert_type: 'PHISHING_DETECTED' | 'DOMAIN_IMPERSONATION' | 'SANDBOX_HIGH_RISK' | 'THREAT_FEED_MATCH' | 'CRITICAL_SECURITY_ISSUE';
  severity: 'critical' | 'high' | 'medium' | 'low';
  url?: string;
  domain?: string;
  scan_id?: number;
  sandbox_run_id?: number;
  security_scan_run_id?: number;
  created_at: string;
  status: 'open' | 'acknowledged' | 'resolved';
}

export interface NotificationChannel {
  id: number;
  tenant_id: number;
  type: 'slack' | 'webhook' | 'email';
  config: any;
  is_active: boolean;
  created_at: string;
}

export const alertsApi = {
  getAlerts: async (params?: { status?: string; severity?: string; alert_type?: string }) => {
    const { data } = await api.get<SecurityAlert[]>('/alerts/', { params });
    return data;
  },
  getAlert: async (id: number) => {
    const { data } = await api.get<SecurityAlert>(`/alerts/${id}`);
    return data;
  },
  updateAlertStatus: async (id: number, status: 'open' | 'acknowledged' | 'resolved') => {
    const { data } = await api.patch<SecurityAlert>(`/alerts/${id}/status`, { status });
    return data;
  },
  getNotificationChannels: async () => {
    const { data } = await api.get<NotificationChannel[]>('/notification-channels/');
    return data;
  },
  createNotificationChannel: async (payload: { type: string; config: any }) => {
    const { data } = await api.post<NotificationChannel>('/notification-channels/', payload);
    return data;
  },
  deleteNotificationChannel: async (id: number) => {
    await api.delete(`/notification-channels/${id}`);
  },
};
