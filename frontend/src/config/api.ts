// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? 'https://video-accounting-app.onrender.com' 
    : 'http://localhost:5001')