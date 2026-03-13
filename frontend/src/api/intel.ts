import apiClient from './client';
import { ThreatAlert } from '../types/api';

export const intelApi = {
  getImpersonationAlerts: async (): Promise<ThreatAlert[]> => {
    try {
      const response = await apiClient.get('/intel/impersonation-alerts');
      return response.data;
    } catch {
      return [];
    }
  },
  getDomainReputation: async (domain: string): Promise<any> => {
    const response = await apiClient.get(`/intel/domain/${domain}`);
    return response.data;
  }
};
