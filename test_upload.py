#!/usr/bin/env python
import requests
import json

# Create new session
session_url = "http://localhost:8000/api/v1/analysis-sessions"
session_data = {
    "title": "Análise de Vendas 2",
    "description": "Dados de vendas e clientes para análise de desempenho",
    "objective": "Identificar padrões de compra dos melhores clientes",
    "objective_category": "comercial"
}

response = requests.post(session_url, json=session_data)
session = response.json()
session_id = session["id"]
print(f"✓ Session created: {session_id}\n")

# Upload file
file_url = f"http://localhost:8000/api/v1/analysis-sessions/{session_id}/files"
file_path = "D:/Python/polaryix/clientes.csv"

with open(file_path, 'rb') as f:
    files = {'file': f}
    response = requests.post(file_url, files=files)

result = response.json()
print("✓ File upload response:")
print(json.dumps(result, indent=2, ensure_ascii=False))
