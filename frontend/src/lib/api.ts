import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('social_ai_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const mockStorage = {
  getToken: () => (typeof window !== 'undefined' ? localStorage.getItem('social_ai_token') : null),
  setToken: (token: string) => {
    if (typeof window !== 'undefined') localStorage.setItem('social_ai_token', token);
  },
  removeToken: () => {
    if (typeof window !== 'undefined') localStorage.removeItem('social_ai_token');
  },
};
