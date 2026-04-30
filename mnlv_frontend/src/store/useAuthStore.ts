import { create } from 'zustand';
import axios from 'axios';

interface User {
  id: number;
  username: string;
  email: string;
}

interface ProviderStatus {
  spotify: boolean;
  deezer: boolean;
  apple_music: boolean;
  tidal: boolean;
  soundcloud: boolean;
  amazon_music: boolean;
  youtube_music: boolean;
  boomplay: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isInitialized: boolean;
  providerStatus: ProviderStatus;
  
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => void;
  fetchProfile: () => Promise<void>;
  fetchProviderStatus: () => Promise<void>;
  initialize: () => Promise<void>;
}

const initialProviderStatus: ProviderStatus = { 
  spotify: false, 
  deezer: false, 
  apple_music: false,
  tidal: false,
  soundcloud: false,
  amazon_music: false,
  youtube_music: false,
  boomplay: false
};

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem('mnlv_access_token'),
  refreshToken: localStorage.getItem('mnlv_refresh_token'),
  isAuthenticated: false,
  isInitialized: false,
  providerStatus: initialProviderStatus,

  login: async (accessToken, refreshToken) => {
    localStorage.setItem('mnlv_access_token', accessToken);
    localStorage.setItem('mnlv_refresh_token', refreshToken);
    set({ accessToken, refreshToken, isAuthenticated: true });
    await get().fetchProfile();
    await get().fetchProviderStatus();
  },

  logout: () => {
    localStorage.removeItem('mnlv_access_token');
    localStorage.removeItem('mnlv_refresh_token');
    set({ 
      user: null, 
      accessToken: null, 
      refreshToken: null, 
      isAuthenticated: false, 
      providerStatus: initialProviderStatus 
    });
  },

  fetchProfile: async () => {
    const { accessToken } = get();
    if (!accessToken) return;

    try {
      const response = await axios.get('/api/auth/profile/');
      set({ user: response.data, isAuthenticated: true });
    } catch (error) {
      get().logout();
    }
  },

  fetchProviderStatus: async () => {
    const { accessToken } = get();
    if (!accessToken) return;

    try {
      const response = await axios.get('/api/auth/providers/status/');
      set({ providerStatus: response.data });
    } catch (error) {}
  },

  initialize: async () => {
    const token = localStorage.getItem('mnlv_access_token');
    if (token) {
      await get().fetchProfile();
      await get().fetchProviderStatus();
    }
    set({ isInitialized: true });
  }
}));

// Axios interceptor for JWT
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('mnlv_access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<{ access: string; refresh?: string }> | null = null;

// Refresh token interceptor
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/api/auth/refresh/')) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('mnlv_refresh_token');
      
      if (refreshToken) {
        try {
          if (!refreshPromise) {
            refreshPromise = axios
              .post('/api/auth/refresh/', { refresh: refreshToken })
              .then((r) => r.data)
              .finally(() => {
                refreshPromise = null;
              });
          }

          const { access, refresh } = await refreshPromise;
          
          localStorage.setItem('mnlv_access_token', access);
          if (refresh) {
            localStorage.setItem('mnlv_refresh_token', refresh);
          }
          
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return axios(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('mnlv_access_token');
          localStorage.removeItem('mnlv_refresh_token');
          useAuthStore.getState().logout();
          window.location.href = '/';
          return Promise.reject(refreshError);
        }
      }
    }
    
    if (error.response?.status === 401 && originalRequest.url?.includes('/api/auth/refresh/')) {
      localStorage.removeItem('mnlv_access_token');
      localStorage.removeItem('mnlv_refresh_token');
      useAuthStore.getState().logout();
      window.location.href = '/';
    }

    return Promise.reject(error);
  }
);
