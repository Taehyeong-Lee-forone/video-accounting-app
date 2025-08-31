'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

// 認証が必要なパス
const PROTECTED_PATHS = ['/app', '/settings'];

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, checkAuth, token } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 初期認証チェック
    const initAuth = async () => {
      try {
        await checkAuth();
      } finally {
        setIsLoading(false);
      }
    };
    initAuth();
  }, []);

  useEffect(() => {
    // ローディング中はスキップ
    if (isLoading) return;

    // 保護されたパスかチェック
    const isProtectedPath = PROTECTED_PATHS.some(path => pathname.startsWith(path));
    
    // 保護されたパスで認証されていない場合のみログインページへ
    if (isProtectedPath && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, pathname, router, isLoading]);

  // ログインページで認証済みの場合はアプリへ
  useEffect(() => {
    if (pathname === '/login' && isAuthenticated && !isLoading) {
      router.push('/app');
    }
  }, [isAuthenticated, pathname, router, isLoading]);

  // ローディング中は何も表示しない
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  return <>{children}</>;
}