#!/usr/bin/env python
import requests
import json

session_id = "0bf0db7693b14c5d86b821b5a8adde18"
file_url = f"http://localhost:8000/api/v1/analysis-sessions/{session_id}/files"
file_path = "D:/Python/polaryix/clientes.csv"

# Upload 2nd file
with open(file_path, 'rb') as f:
    files = {'file': f}
    response = requests.post(file_url, files=files)

result = response.json()
print("✓ 2nd file upload response:")
print(json.dumps(result, indent=2, ensure_ascii=False))

# Verify session now has 2 files
session_url = f"http://localhost:8000/api/v1/analysis-sessions/{session_id}"
response = requests.get(session_url)
session = response.json()

print("\n✓ Session after 2 uploads:")
print(f"  Files count: {len(session['files'])}")
for i, file in enumerate(session['files'], 1):
    print(f"  File {i}: {file['filename']} ({file['row_count']} rows, {file['column_count']} cols)")
