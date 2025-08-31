'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

const PUBLIC_PATHS = ['/login'];

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    // 初期認証チェック
    checkAuth();
  }, []);

  useEffect(() => {
    // パブリックパスの場合はスキップ
    if (PUBLIC_PATHS.includes(pathname)) {
      return;
    }

    // 認証されていない場合はログインページへ
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, pathname, router]);

  // ログインページで認証済みの場合はホームへ
  useEffect(() => {
    if (pathname === '/login' && isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, pathname, router]);

  return <>{children}</>;
}