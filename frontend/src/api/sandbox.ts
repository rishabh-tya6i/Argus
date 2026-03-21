import apiClient from './client';
import { SandboxRun } from '../types/api';

// Mocks underlying these paths if the backend lacks them today
export const sandboxApi = {
  getRuns: async (): Promise<SandboxRun[]> => {
    try {
      const response = await apiClient.get('/sandbox/runs');
      return response.data;
    } catch (err: any) {
      if (err.response?.status === 404) return []; // Graceful empty fallback
      throw err;
    }
  },
  getRunById: async (id: number | string): Promise<any> => {
    const response = await apiClient.get(`/sandbox/runs/${id}`);
    return response.data;
  },
  getRunEvents: async (id: number | string): Promise<any[]> => {
    const response = await apiClient.get(`/sandbox/runs/${id}/events`);
    return response.data;
  },
  createRun: async (url: string): Promise<SandboxRun> => {
    const response = await apiClient.post('/sandbox/run', { url });
    return response.data;
  }
};
