import apiClient from './client';
import { User, Tenant } from '../types/api';

export const tenantApi = {
  getTenant: async (): Promise<Tenant> => {
    const response = await apiClient.get('/tenant');
    return response.data;
  },
  getUsers: async (): Promise<User[]> => {
    const response = await apiClient.get('/users');
    return response.data;
  },
  getApiKeys: async (): Promise<any[]> => {
    const response = await apiClient.get('/api-keys');
    return response.data;
  }
};
