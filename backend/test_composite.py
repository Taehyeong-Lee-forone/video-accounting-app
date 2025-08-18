#!/usr/bin/env python3

# Test composite type handling
test_string = "請求書・領収書"
print(f"Test string: '{test_string}'")
print(f"Contains '・': {'・' in test_string}")
print(f"Split result: {test_string.split('・')}")
print(f"First part: {test_string.split('・')[0]}")

# Test with actual JSON
import json

json_str = '''
{
  "vendor": "Test Store",
  "document_type": "請求書・領収書",
  "total": 1000
}
'''

data = json.loads(json_str)
print(f"\nParsed JSON document_type: '{data['document_type']}'")

if data.get('document_type') and '・' in data.get('document_type', ''):
    first_type = data['document_type'].split('・')[0]
    print(f"Would normalize to: '{first_type}'")