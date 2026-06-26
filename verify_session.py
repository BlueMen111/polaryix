#!/usr/bin/env python
import requests
import json

session_id = "27e9a93189914c88b59c23bb72d8b12f"
url = f"http://localhost:8000/api/v1/analysis-sessions/{session_id}"

response = requests.get(url)
session = response.json()

print("✓ Sessão recuperada do backend:")
print(json.dumps(session, indent=2, ensure_ascii=False))

# Verify session has files_count
print(f"\n✓ Files count: {session['files_count']}")
print(f"✓ Status: {session['status']}")
print(f"✓ Created at: {session['created_at']}")
print(f"✓ Updated at: {session['updated_at']}")
