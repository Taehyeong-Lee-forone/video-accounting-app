import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';

interface AuthContextType {
  isAuthenticated: boolean;
  token: string | null;
  login: (accessToken: string, refreshToken: string) => void;
  logout: () => void;
  checkAuth: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    // 初期化時にローカルストレージから認証情報を復元
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      setToken(storedToken);
      setIsAuthenticated(true);
      // axiosのデフォルトヘッダーに設定
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
    }
  }, []);

  const login = (accessToken: string, refreshToken: string) => {
    // トークンを保存
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    
    // 状態を更新
    setToken(accessToken);
    setIsAuthenticated(true);
    
    // axiosのデフォルトヘッダーに設定
    axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
  };

  const logout = () => {
    // トークンを削除
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    
    // 状態をリセット
    setToken(null);
    setIsAuthenticated(false);
    
    // axiosのヘッダーから削除
    delete axios.defaults.headers.common['Authorization'];
  };

  const checkAuth = () => {
    const storedToken = localStorage.getItem('access_token');
    return !!storedToken;
  };

  // axiosインターセプターを設定（401エラー時の自動ログアウト）
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // トークンが無効な場合は自動ログアウト
          logout();
          // ログインページにリダイレクト（オプション）
          // window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};