# Polaryix

Polaryix é uma plataforma SaaS para análise segura de datasets.

## Fase atual

- Backend FastAPI
- Health check
- Upload inicial de datasets
- Validação básica de segurança para arquivos

## Rodar API localmente

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload