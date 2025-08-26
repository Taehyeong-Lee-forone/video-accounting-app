"""
ヘルスチェックAPI
"""
from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET /api/health"""
        try:
            # データベース接続確認
            db_url = os.environ.get("DATABASE_URL", "")
            supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
            
            status = {
                "status": "healthy",
                "environment": "production" if db_url else "development",
                "services": {
                    "database": bool(db_url),
                    "supabase": bool(supabase_url),
                    "vision_api": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
                },
                "timestamp": str(os.environ.get("VERCEL_GIT_COMMIT_SHA", "local"))
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error = {"error": str(e), "status": "unhealthy"}
            self.wfile.write(json.dumps(error).encode())
    
    def do_OPTIONS(self):
        """CORS対応"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()