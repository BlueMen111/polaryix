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
uvicorn app.main:app --reload```

## Google Search Console

Para indexar o PolarYix no Google:

1. Acesse Google Search Console.
2. Adicione o dominio `polaryix.com`.
3. Verifique a propriedade via DNS TXT.
4. Envie o sitemap: `https://polaryix.com/sitemap.xml`.
