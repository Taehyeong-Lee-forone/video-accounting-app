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

  useEffect(() => {
    // トークンがある場合のみバックグラウンドで認証チェック
    if (token) {
      checkAuth().catch(err => {
        console.error('Auth check error:', err);
      });
    }
  }, [token, checkAuth]);

  useEffect(() => {
    // 保護されたパスかチェック
    const isProtectedPath = PROTECTED_PATHS.some(path => pathname.startsWith(path));
    
    // 保護されたパスで認証されていない場合のみログインページへ
    if (isProtectedPath && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, pathname, router]);

  // ログインページで認証済みの場合はアプリへ
  useEffect(() => {
    if (pathname === '/login' && isAuthenticated) {
      router.push('/app');
    }
  }, [isAuthenticated, pathname, router]);

  // ローディング状態を削除 - 常にchildrenを表示
  return <>{children}</>;
}