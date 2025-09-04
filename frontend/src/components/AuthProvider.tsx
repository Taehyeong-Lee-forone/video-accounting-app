'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

// 認証が必要なパス
const PROTECTED_PATHS = ['/upload', '/settings'];

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, checkAuth, token } = useAuthStore();
  const [isHydrated, setIsHydrated] = useState(false);

  // Hydration 完了を待つ
  useEffect(() => {
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    // Hydration完了後、トークンがある場合のみバックグラウンドで認証チェック
    if (isHydrated && token) {
      checkAuth().catch(err => {
        console.error('Auth check error:', err);
      });
    }
  }, [isHydrated, token, checkAuth]);

  useEffect(() => {
    // Hydration完了後のみリダイレクト処理
    if (!isHydrated) return;
    
    // 保護されたパスかチェック
    const isProtectedPath = PROTECTED_PATHS.some(path => pathname.startsWith(path));
    
    // 保護されたパスで認証されていない場合のみログインページへ
    if (isProtectedPath && !isAuthenticated && !token) {
      router.push('/login');
    }
  }, [isHydrated, isAuthenticated, pathname, router, token]);

  // ログインページで認証済みの場合はアプリへ
  useEffect(() => {
    if (!isHydrated) return;
    
    if (pathname === '/login' && isAuthenticated) {
      router.push('/upload');
    }
  }, [isHydrated, isAuthenticated, pathname, router]);

  // ローディング状態を削除 - 常にchildrenを表示
  return <>{children}</>;
}