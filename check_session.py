#!/usr/bin/env python
import requests
import json

session_id = "0bf0db7693b14c5d86b821b5a8adde18"
session_url = f"http://localhost:8000/api/v1/analysis-sessions/{session_id}"
response = requests.get(session_url)
session = response.json()

print("GET Session Response:")
print(json.dumps(session, indent=2, ensure_ascii=False))
