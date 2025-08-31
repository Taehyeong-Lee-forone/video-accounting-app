import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';
import { API_BASE_URL } from '@/config/api';

interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_superuser: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        try {
          // FormDataとして送信（OAuth2仕様）
          const formData = new URLSearchParams();
          formData.append('username', username);
          formData.append('password', password);

          const response = await axios.post(
            `${API_BASE_URL}/api/auth/login`,
            formData,
            {
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
              },
            }
          );

          const { access_token, refresh_token } = response.data;

          // ユーザー情報取得
          const userResponse = await axios.get(`${API_BASE_URL}/api/auth/me`, {
            headers: {
              Authorization: `Bearer ${access_token}`,
            },
          });

          set({
            token: access_token,
            refreshToken: refresh_token,
            user: userResponse.data,
            isAuthenticated: true,
          });

          // Axiosのデフォルトヘッダーに設定
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        } catch (error: any) {
          console.error('Login failed:', error);
          throw new Error(
            error.response?.data?.detail || 'ログインに失敗しました'
          );
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
        });
        delete axios.defaults.headers.common['Authorization'];
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        try {
          const response = await axios.post(
            `${API_BASE_URL}/api/auth/refresh`,
            { refresh_token: refreshToken }
          );

          const { access_token } = response.data;
          
          set({ token: access_token });
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        } catch (error) {
          console.error('Token refresh failed:', error);
          get().logout();
          throw error;
        }
      },

      checkAuth: async () => {
        const { token } = get();
        if (!token) {
          get().logout();
          return;
        }

        try {
          const response = await axios.get(`${API_BASE_URL}/api/auth/me`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          set({
            user: response.data,
            isAuthenticated: true,
          });
          
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        } catch (error) {
          console.error('Auth check failed:', error);
          // トークンが無効な場合はリフレッシュを試みる
          try {
            await get().refreshAccessToken();
            await get().checkAuth();
          } catch (refreshError) {
            get().logout();
          }
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    }
  )
);