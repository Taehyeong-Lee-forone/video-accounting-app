// API Configuration
// プロダクション環境では必ずHTTPSを使用
const isProduction = typeof window !== 'undefined' && window.location.hostname !== 'localhost';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 
  (isProduction
    ? 'https://video-accounting-app.onrender.com' 
    : 'http://localhost:5001');

// デバッグ用ログ
if (typeof window !== 'undefined') {
  console.log('🌐 API Configuration:', {
    API_BASE_URL,
    env: process.env.NODE_ENV,
    publicApiUrl: process.env.NEXT_PUBLIC_API_URL,
    hostname: window.location.hostname,
    isProduction
  });
}