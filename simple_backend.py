from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
from datetime import datetime
import json

app = FastAPI(title="動画会計アプリ API (Simple)")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# メモリ内データストア
videos_db = []
journals_db = []
vendors_db = []
accounts_db = [
    {"code": "1110", "name": "現金", "type": "資産"},
    {"code": "2120", "name": "未払金", "type": "負債"},
    {"code": "5130", "name": "会議費", "type": "費用"},
    {"code": "5140", "name": "消耗品費", "type": "費用"},
    {"code": "5190", "name": "雑費", "type": "費用"},
]

class VideoResponse(BaseModel):
    id: int
    filename: str
    status: str
    created_at: str
    duration_ms: Optional[int] = None

class JournalResponse(BaseModel):
    id: int
    video_id: int
    debit_account: str
    credit_account: str
    debit_amount: float
    credit_amount: float
    status: str
    memo: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "動画会計アプリ API (Simple)", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/videos/")
async def upload_video(file: UploadFile = File(...)):
    """動画アップロード"""
    # ファイル保存
    os.makedirs("uploads/videos", exist_ok=True)
    file_path = f"uploads/videos/{file.filename}"
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # DBに追加
    video = {
        "id": len(videos_db) + 1,
        "filename": file.filename,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "local_path": file_path,
        "duration_ms": 10000  # ダミー
    }
    videos_db.append(video)
    
    return VideoResponse(**video)

@app.get("/api/videos/")
async def list_videos():
    """動画一覧"""
    return [VideoResponse(**v) for v in videos_db]

@app.get("/api/videos/{video_id}")
async def get_video(video_id: int):
    """動画詳細"""
    video = next((v for v in videos_db if v["id"] == video_id), None)
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    # ダミーデータを追加
    video["receipts"] = [{
        "id": 1,
        "vendor": "スターバックス",
        "issue_date": "2024-01-15",
        "total": 1100,
        "tax": 100,
        "tax_rate": 0.10,
        "payment_method": "現金",
        "status": "unconfirmed"
    }]
    
    video["journal_entries"] = [j for j in journals_db if j.get("video_id") == video_id]
    
    return video

@app.post("/api/videos/{video_id}/analyze")
async def analyze_video(video_id: int):
    """動画分析（ダミー）"""
    video = next((v for v in videos_db if v["id"] == video_id), None)
    if not video:
        raise HTTPException(404, "動画が見つかりません")
    
    # ステータス更新
    video["status"] = "processing"
    
    # ダミー仕訳生成
    if not journals_db:
        journals_db.extend([
            {
                "id": 1,
                "video_id": video_id,
                "receipt_id": 1,
                "time_ms": 5000,
                "debit_account": "会議費",
                "credit_account": None,
                "debit_amount": 1000,
                "credit_amount": 0,
                "status": "unconfirmed",
                "memo": "スターバックス - 本体"
            },
            {
                "id": 2,
                "video_id": video_id,
                "receipt_id": 1,
                "time_ms": 5000,
                "debit_account": "仮払消費税",
                "credit_account": None,
                "debit_amount": 100,
                "credit_amount": 0,
                "status": "unconfirmed",
                "memo": "消費税 10%"
            },
            {
                "id": 3,
                "video_id": video_id,
                "receipt_id": 1,
                "time_ms": 5000,
                "debit_account": None,
                "credit_account": "現金",
                "debit_amount": 0,
                "credit_amount": 1100,
                "status": "unconfirmed",
                "memo": "現金支払"
            }
        ])
    
    video["status"] = "done"
    
    return {"message": "分析完了", "video_id": video_id}

@app.get("/api/journals/")
async def list_journals(video_id: Optional[int] = None):
    """仕訳一覧"""
    if video_id:
        return [j for j in journals_db if j.get("video_id") == video_id]
    return journals_db

@app.post("/api/journals/{journal_id}/confirm")
async def confirm_journal(journal_id: int):
    """仕訳承認"""
    journal = next((j for j in journals_db if j["id"] == journal_id), None)
    if not journal:
        raise HTTPException(404, "仕訳が見つかりません")
    
    journal["status"] = "confirmed"
    journal["confirmed_at"] = datetime.now().isoformat()
    
    return journal

@app.post("/api/journals/{journal_id}/reject")
async def reject_journal(journal_id: int):
    """仕訳差戻し"""
    journal = next((j for j in journals_db if j["id"] == journal_id), None)
    if not journal:
        raise HTTPException(404, "仕訳が見つかりません")
    
    journal["status"] = "rejected"
    
    return journal

@app.patch("/api/journals/{journal_id}")
async def update_journal(journal_id: int, data: dict):
    """仕訳更新"""
    journal = next((j for j in journals_db if j["id"] == journal_id), None)
    if not journal:
        raise HTTPException(404, "仕訳が見つかりません")
    
    journal.update(data)
    return journal

@app.get("/api/export/csv")
async def export_csv(video_id: Optional[int] = None):
    """CSVエクスポート"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # ヘッダー
    writer.writerow([
        '仕訳ID', '動画ID', 'ステータス', '借方科目', '借方金額',
        '貸方科目', '貸方金額', 'メモ'
    ])
    
    # データ
    journals = journals_db
    if video_id:
        journals = [j for j in journals if j.get("video_id") == video_id]
    
    for j in journals:
        writer.writerow([
            j.get("id", ""),
            j.get("video_id", ""),
            j.get("status", ""),
            j.get("debit_account", ""),
            j.get("debit_amount", ""),
            j.get("credit_account", ""),
            j.get("credit_amount", ""),
            j.get("memo", "")
        ])
    
    output.seek(0)
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue().encode('utf-8-sig'),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=export.csv"
        }
    )

@app.get("/api/masters/vendors")
async def list_vendors():
    """ベンダー一覧"""
    return vendors_db

@app.post("/api/masters/vendors")
async def create_vendor(data: dict):
    """ベンダー作成"""
    vendor = {
        "id": len(vendors_db) + 1,
        **data,
        "created_at": datetime.now().isoformat()
    }
    vendors_db.append(vendor)
    return vendor

@app.get("/api/masters/accounts")
async def list_accounts():
    """勘定科目一覧"""
    return accounts_db

@app.post("/api/masters/accounts")
async def create_account(data: dict):
    """勘定科目作成"""
    accounts_db.append(data)
    return data

@app.get("/api/masters/rules")
async def list_rules():
    """ルール一覧"""
    return []

@app.post("/api/masters/rules")
async def create_rule(data: dict):
    """ルール作成"""
    return data

# 動画ファイル配信用
@app.get("/uploads/videos/{filename}")
async def serve_video(filename: str):
    file_path = f"uploads/videos/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4")
    raise HTTPException(404, "ファイルが見つかりません")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)