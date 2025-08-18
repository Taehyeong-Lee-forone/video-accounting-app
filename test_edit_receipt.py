#!/usr/bin/env python3
"""
Receipt editing functionality test script
Tests the receipt information direct editing feature with history tracking
"""

import requests
import time
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:8000/api"

def test_receipt_edit():
    print("📝 Testing Receipt Edit Functionality")
    print("=" * 50)
    
    # 1. Get list of videos
    print("\n1. Getting video list...")
    response = requests.get(f"{BASE_URL}/videos/")
    videos = response.json()
    
    if not videos:
        print("❌ No videos found. Please upload a video first.")
        return
    
    # Get the most recent video with receipts
    video_id = None
    receipt_id = None
    
    for video in videos:
        video_detail = requests.get(f"{BASE_URL}/videos/{video['id']}").json()
        if video_detail.get('receipts'):
            video_id = video['id']
            receipt_id = video_detail['receipts'][0]['id']
            print(f"✅ Found video ID: {video_id} with receipt ID: {receipt_id}")
            break
    
    if not video_id or not receipt_id:
        print("❌ No videos with receipts found.")
        return
    
    # 2. Get current receipt data
    print("\n2. Getting current receipt data...")
    video_detail = requests.get(f"{BASE_URL}/videos/{video_id}").json()
    receipt = next(r for r in video_detail['receipts'] if r['id'] == receipt_id)
    
    print(f"Current vendor: {receipt.get('vendor', 'N/A')}")
    print(f"Current total: {receipt.get('total', 0)}")
    print(f"Current tax: {receipt.get('tax', 0)}")
    
    # 3. Test editing receipt
    print("\n3. Testing receipt edit...")
    edit_data = {
        "vendor": "Test Store Updated",
        "total": 1500,
        "tax": 150,
        "memo": f"Edited at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }
    
    response = requests.patch(
        f"{BASE_URL}/videos/{video_id}/receipts/{receipt_id}",
        json=edit_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Receipt updated successfully: {result.get('message')}")
        
        if 'history' in result:
            print(f"   History entries: {len(result['history'])}")
            for h in result['history'][:3]:  # Show first 3 history entries
                print(f"   - {h['field_name']}: {h['old_value']} → {h['new_value']}")
    else:
        print(f"❌ Failed to update receipt: {response.status_code}")
        print(f"   Error: {response.text}")
    
    # 4. Get history
    print("\n4. Getting receipt history...")
    response = requests.get(f"{BASE_URL}/videos/{video_id}/receipts/{receipt_id}/history")
    
    if response.status_code == 200:
        history = response.json()
        print(f"✅ Retrieved {len(history)} history entries")
        
        for i, h in enumerate(history[:5], 1):  # Show first 5 entries
            print(f"\n   Entry {i}:")
            print(f"   Field: {h['field_name']}")
            print(f"   Old: {h.get('old_value', '(empty)')}")
            print(f"   New: {h.get('new_value', '(empty)')}")
            print(f"   Changed by: {h.get('changed_by', 'unknown')}")
            print(f"   Time: {h.get('changed_at', 'unknown')}")
    else:
        print(f"❌ Failed to get history: {response.status_code}")
    
    # 5. Test another edit
    print("\n5. Testing another edit...")
    edit_data2 = {
        "vendor": "Final Test Store",
        "issue_date": "2024-12-25T00:00:00"
    }
    
    response = requests.patch(
        f"{BASE_URL}/videos/{video_id}/receipts/{receipt_id}",
        json=edit_data2
    )
    
    if response.status_code == 200:
        print("✅ Second edit successful")
    else:
        print(f"❌ Second edit failed: {response.status_code}")
    
    # 6. Verify changes in video detail
    print("\n6. Verifying changes in video detail...")
    video_detail = requests.get(f"{BASE_URL}/videos/{video_id}").json()
    receipt = next(r for r in video_detail['receipts'] if r['id'] == receipt_id)
    
    print(f"Final vendor: {receipt.get('vendor', 'N/A')}")
    print(f"Final total: {receipt.get('total', 0)}")
    print(f"Final tax: {receipt.get('tax', 0)}")
    print(f"History entries in receipt: {len(receipt.get('history', []))}")
    
    print("\n" + "=" * 50)
    print("✅ Receipt editing functionality test completed!")

if __name__ == "__main__":
    test_receipt_edit()