import apiClient from './client';
import { Scan, ScanDetail } from '../types/api';

export const scansApi = {
  getScans: async (): Promise<Scan[]> => {
    const response = await apiClient.get('/scans');
    return response.data;
  },
  getScanById: async (id: number | string): Promise<ScanDetail> => {
    const response = await apiClient.get(`/scans/${id}`);
    return response.data;
  },
};
