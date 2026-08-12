import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

apiClient.interceptors.request.use(async (config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('social_ai_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthEndpoint = error.config?.url?.includes('/auth/login') || error.config?.url?.includes('/auth/register');
    if (typeof window !== 'undefined' && error.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('social_ai_token');
      localStorage.removeItem('social_ai_user');
      // Redirect to login if user is on dashboard
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const mockStorage = {
  getToken: () => (typeof window !== 'undefined' ? localStorage.getItem('social_ai_token') : null),
  setToken: (token: string) => {
    if (typeof window !== 'undefined') localStorage.setItem('social_ai_token', token);
  },
  removeToken: () => {
    if (typeof window !== 'undefined') localStorage.removeItem('social_ai_token');
  },
};
