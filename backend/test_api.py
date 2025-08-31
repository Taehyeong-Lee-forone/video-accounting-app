#!/usr/bin/env python3
import os
import requests
import json

# APIベースURLを環境変数から取得
API_URL = os.getenv("API_URL", "http://localhost:8000")

response = requests.get(f"{API_URL}/api/videos/19")
data = response.json()

if 'receipts' in data and len(data['receipts']) > 0:
    receipt = data['receipts'][0]
    print("Receipt ID:", receipt.get('id'))
    print("Best Frame ID:", receipt.get('best_frame_id'))
    print("Best Frame Object:", receipt.get('best_frame'))
    
    if receipt.get('best_frame'):
        print("  - Frame ID:", receipt['best_frame'].get('id'))
        print("  - Time MS:", receipt['best_frame'].get('time_ms'))
    else:
        print("  ! best_frame object is missing!")
else:
    print("No receipts found")