import apiClient from './client';
import { ScanFeedback, ScanFeedbackAggregated } from '../types/api';

export const feedbackApi = {
  submitFeedback: async (data: { scan_id: number; label: string; notes?: string }): Promise<ScanFeedback> => {
    const response = await apiClient.post('/feedback', data);
    return response.data;
  },
  getFeedbackByScan: async (scanId: number | string): Promise<ScanFeedback[]> => {
    const response = await apiClient.get(`/feedback`, { params: { scan_id: scanId } });
    return response.data;
  },
  getAggregatedFeedback: async (): Promise<ScanFeedbackAggregated[]> => {
    const response = await apiClient.get('/feedback/aggregated');
    return response.data;
  }
};
