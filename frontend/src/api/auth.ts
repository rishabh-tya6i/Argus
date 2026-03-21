import apiClient from './client';
import { AuthResponse } from '../types/api';

export const authApi = {
  login: async (credentials: any): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/login', credentials);
    return response.data;
  },
  register: async (credentials: any): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/register', credentials);
    return response.data;
  },
  refresh: async (token: string): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/refresh', { refresh_token: token });
    return response.data;
  },
};
