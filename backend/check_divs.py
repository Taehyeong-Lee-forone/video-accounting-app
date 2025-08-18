#!/usr/bin/env python3

with open('/Users/taehyeonglee/video-accounting-app/frontend/src/components/ReceiptJournalModal.tsx', 'r') as f:
    lines = f.readlines()

# Track div depth
depth = 0
in_jsx = False
for i, line in enumerate(lines[457:1083], start=457):
    # Skip comments
    if '{/*' in line:
        continue
    
    # Count opening divs
    open_count = line.count('<div')
    # Count closing divs
    close_count = line.count('</div>')
    
    if open_count > 0 or close_count > 0:
        depth += open_count - close_count
        print(f"Line {i}: depth={depth} | {line.rstrip()}")

print(f"\nFinal depth: {depth}")
print("Should be 0 if all divs are balanced")