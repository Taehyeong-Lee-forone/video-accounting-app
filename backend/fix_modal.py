#!/usr/bin/env python3

# Check div structure
with open('/Users/taehyeonglee/video-accounting-app/frontend/src/components/ReceiptJournalModal.tsx', 'r') as f:
    lines = f.readlines()

# Find the return statement
for i, line in enumerate(lines[455:465], start=455):
    print(f"Line {i}: {line.rstrip()}")

print("\n\nNow checking closing divs around line 1075-1085:")
for i, line in enumerate(lines[1075:1085], start=1075):
    print(f"Line {i}: {line.rstrip()}")