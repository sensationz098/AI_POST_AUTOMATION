import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export const DEFAULT_API_TIMEOUT_MS = 15000;
export const PUBLISHING_TIMEOUT_MS = 300000; // 300s window matching server-side max Meta video processing window

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: DEFAULT_API_TIMEOUT_MS,
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
      const isPublicPage = ['/login', '/register', '/privacy-policy', '/data-deletion', '/terms'].some((path) =>
        window.location.pathname.startsWith(path)
      );
      if (!isPublicPage) {
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
