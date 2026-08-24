import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export const DEFAULT_API_TIMEOUT_MS = 15000;
export const PUBLISHING_TIMEOUT_MS = 300000; // 300s window matching server-side max Meta video processing window
export const MEDIA_UPLOAD_TIMEOUT_MS = 600000; // 600s (10 min) window for large media file uploads (up to 500MB)

// In-memory access token storage (NEVER written to localStorage, sessionStorage, or JS cookies)
let memoryAccessToken: string | null = null;

export const getMemoryToken = (): string | null => memoryAccessToken;

export const setMemoryToken = (token: string | null) => {
  memoryAccessToken = token;
};

// Callbacks for AuthContext integration
type TokenRefreshedCallback = (token: string, data: any) => void;
type LogoutCallback = () => void;

let onTokenRefreshedCallback: TokenRefreshedCallback | null = null;
let onLogoutCallback: LogoutCallback | null = null;

export const setAuthCallbacks = (
  onRefreshed: TokenRefreshedCallback,
  onLogout: LogoutCallback
) => {
  onTokenRefreshedCallback = onRefreshed;
  onLogoutCallback = onLogout;
};

export const apiClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // Always send HttpOnly cookies to API backend
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  },
  timeout: DEFAULT_API_TIMEOUT_MS,
});

function getCsrfTokenFromCookie(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp('(?:^|; )csrf_token=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

// Request Interceptor: Attach in-memory access token & anti-CSRF headers
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  config.withCredentials = true;
  if (config.headers) {
    config.headers['X-Requested-With'] = 'XMLHttpRequest';
    const csrfToken = getCsrfTokenFromCookie();
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
    if (memoryAccessToken) {
      config.headers.Authorization = `Bearer ${memoryAccessToken}`;
    }
  }
  return config;
});

// Response Interceptor: Simultaneous 401 handling with queue & single refresh promise
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (!originalRequest) {
      return Promise.reject(error);
    }

    const url = originalRequest.url || '';
    const isAuthEndpoint =
      url.includes('/auth/login') ||
      url.includes('/auth/register') ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/logout');

    // Handle 401 Unauthorized for non-auth endpoints
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      if (isRefreshing) {
        // Queue parallel requests while refresh is in flight
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt silent refresh using HttpOnly refresh cookie
        const res = await apiClient.post('/auth/refresh', null, {
          _retry: true,
        } as any);

        const newAccessToken = res.data?.access_token;
        if (newAccessToken) {
          setMemoryToken(newAccessToken);

          if (onTokenRefreshedCallback) {
            onTokenRefreshedCallback(newAccessToken, res.data);
          }

          processQueue(null, newAccessToken);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          }
          return apiClient(originalRequest);
        } else {
          throw new Error('Refresh endpoint did not return an access token');
        }
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        setMemoryToken(null);

        if (onLogoutCallback) {
          onLogoutCallback();
        }

        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
