import api from './client';
import { User } from '../types/api';
import { SecurityAlert } from './alerts';

export type CaseSeverity = 'critical' | 'high' | 'medium' | 'low';
export type CaseStatus = 'open' | 'in_progress' | 'resolved' | 'closed';

export interface InvestigationCase {
  id: number;
  tenant_id: number;
  title: string;
  description: string | null;
  severity: CaseSeverity;
  status: CaseStatus;
  assigned_to_user_id: number | null;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
  assigned_to?: User;
  created_by?: User;
  alerts?: SecurityAlert[];
}

export interface CaseComment {
  id: number;
  case_id: number;
  user_id: number;
  comment: string;
  created_at: string;
  user?: User;
}

export const casesApi = {
  createCase: async (payload: { title: string; description?: string; severity: CaseSeverity; alert_ids?: number[] }) => {
    const { data } = await api.post<InvestigationCase>('/cases', payload);
    return data;
  },
  getCases: async (params?: { status?: string; severity?: string; assigned_to?: number }) => {
    const { data } = await api.get<InvestigationCase[]>('/cases', { params });
    return data;
  },
  getCase: async (id: number) => {
    const { data } = await api.get<InvestigationCase>(`/cases/${id}`);
    return data;
  },
  updateCase: async (id: number, payload: Partial<{ title: string; description: string; severity: CaseSeverity; status: CaseStatus; assigned_to_user_id: number | null }>) => {
    const { data } = await api.patch<InvestigationCase>(`/cases/${id}`, payload);
    return data;
  },
  assignCase: async (id: number, userId: number | null) => {
    const { data } = await api.post<InvestigationCase>(`/cases/${id}/assign`, { user_id: userId });
    return data;
  },
  updateStatus: async (id: number, status: CaseStatus) => {
    const { data } = await api.post<InvestigationCase>(`/cases/${id}/status`, { status });
    return data;
  },
  addComment: async (id: number, comment: string) => {
    const { data } = await api.post<CaseComment>(`/cases/${id}/comments`, { comment });
    return data;
  },
  getComments: async (id: number) => {
    const { data } = await api.get<CaseComment[]>(`/cases/${id}/comments`);
    return data;
  },
  linkAlerts: async (id: number, alertIds: number[]) => {
    await api.post(`/cases/${id}/alerts`, { alert_ids: alertIds });
  },
};
