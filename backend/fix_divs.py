#!/usr/bin/env python3

with open('/Users/taehyeonglee/video-accounting-app/frontend/src/components/ReceiptJournalModal.tsx', 'r') as f:
    lines = f.readlines()

# Track div depth more carefully
depth = 0
for i, line in enumerate(lines[458:1083], start=458):
    # Skip comments
    if '{/*' in line or '*/}' in line:
        continue
    
    # Count opening divs (but not in comments)
    open_count = 0
    if '<div' in line and not '//' in line[:line.find('<div') if '<div' in line else len(line)]:
        open_count = line.count('<div')
    
    # Count closing divs
    close_count = 0
    if '</div>' in line:
        close_count = line.count('</div>')
    
    if open_count > 0 or close_count > 0:
        depth += open_count - close_count
        if i < 470 or i > 1070:  # Show beginning and end
            print(f"Line {i}: depth={depth:2d} | opens={open_count} closes={close_count} | {line.rstrip()[:80]}")

print(f"\nFinal depth at line 1082: {depth}")
print("Should be 0 for balanced divs")