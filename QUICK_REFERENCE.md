# QUICK_REFERENCE — Cheatsheet Rápido

Status atual
- Backend: API FastAPI (docs em `http://localhost:8000/docs`) — status: pronto para rodar localmente
- Frontend: Next.js (upload) — rota principal `http://localhost:3000/upload`

URLs úteis
- API docs: `http://localhost:8000/docs`
- Frontend upload: `http://localhost:3000/upload`

Estrutura de pastas (resumida)
- `apps/api/` — backend FastAPI
- `web/` — frontend Next.js
- `apps/api/storage/processed/analysis_sessions/` — sessões processadas (JSON)
- `storage/quarantine/` — arquivos que falharam na validação

Comandos úteis

- Subir via Docker Compose (recomendado):

```powershell
docker compose up --build
```

- Rodar apenas backend local (virtualenv):

```powershell
cd apps/api
.venv\Scripts\activate
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- Rodar frontend (Next.js):

```bash
cd web
npm install
npm run dev
```

Endpoints principais (resumo)
- `POST /api/v1/analysis_sessions` — cria sessão
- `POST /api/v1/analysis_sessions/{session_id}/files` — upload de arquivo
- `GET /api/v1/analysis_sessions/{session_id}` — metadados da sessão
- `GET /api/v1/analysis_sessions/{session_id}/status` — progresso de processamento

Debug e troubleshooting rápido
- Logs do backend: ver console do Uvicorn (ou logs do container)
- Se upload falhar, checar `storage/quarantine` e o `error_message` no JSON da sessão em `storage/processed/analysis_sessions`
- Timeouts/proxy: ajustar `client_max_body_size` no Nginx e limites de upload no backend

Checklist para iniciar nova conversa (pronto para continuar)
- ✅ Backend rodando: http://localhost:8000/docs
- ✅ Frontend rodando: http://localhost:3000/upload
- ✅ Upload testado e funcionando
- ✅ Código salvo em arquivos
- ✅ Contexto documentado (`CONTEXTO_CONTINUACAO.md`)

Pronto para continuar em nova conversa! 🚀
# ⚡ QUICK REFERENCE - Polaryix

## 🎯 Status Atual
- ✅ Etapa 1-2: Upload multi-arquivo (Backend + Frontend)
- 🎬 Próxima: Etapa 3 - Processing Progress UI

## 🔗 URLs
- Backend: http://localhost:8000 (Swagger: /docs)
- Frontend: http://localhost:3000/upload

## 📂 Estrutura Chave
```
Backend:
  /apps/api/app/
    - domain/analysis_sessions/ → schemas.py (tipos)
    - api/v1/routes/ → analysis_sessions*.py (endpoints)
    - infrastructure/storage/ → analysis_sessions_storage.py (CRUD)

Frontend:
  /apps/web/src/
    - types/analysis.ts → tipos TS
    - hooks/useAnalysisSession.ts → hook API
    - components/AnalysisSessionForm.tsx → componente 3-steps
    - app/upload/page.tsx → página upload
    - .env.local → config API
```

## 🚀 Iniciar Servidores
```bash
# Terminal 1: Backend
cd d:\Python\polaryix\apps\api && python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend  
cd d:\Python\polaryix\apps\web && npm run dev
```

## 🧪 Testar Upload
1. http://localhost:3000/upload
2. Preencher form (título obrigatório)
3. Arrastar arquivo (ou clicar para selecionar)
4. Clique "Enviar Arquivos"
5. Ver sucesso com Session ID

## 📊 Endpoints API Prontos
- POST /api/v1/analysis-sessions - criar sessão
- GET /api/v1/analysis-sessions - listar
- GET /api/v1/analysis-sessions/{id} - obter
- PATCH /api/v1/analysis-sessions/{id} - atualizar
- DELETE /api/v1/analysis-sessions/{id} - deletar
- POST /api/v1/analysis-sessions/{id}/files - upload

## 💾 Dados
- Sessões JSON: `/apps/api/storage/processed/analysis_sessions/`
- Quarantine: `/apps/api/storage/quarantine/`
- Perfil: row_count, column_count, column_names, tipos semânticos

## 📖 Tipos TypeScript
- AnalysisSession
- AnalysisSessionFile
- AnalysisObjectiveCategory (enum 8 valores)
- CreateAnalysisSessionRequest
- FileUploadResponse

## 🎨 Componentes React
- AnalysisSessionForm (main, 3 steps)
- useAnalysisSession (hook)

## 🔗 Integração
- Frontend API_URL: NEXT_PUBLIC_API_URL=http://localhost:8000
- CORS: Configurado para localhost:3000
- Arquivo formdata upload funciona

## 📝 Próxima: Etapa 3
Implementar:
1. GET /api/v1/analysis-sessions/{id}/progress
2. Frontend Progress UI com % e steps
3. Real-time streaming ou polling

## 🐛 Debug
- Ver Swagger: http://localhost:8000/docs
- Ver sessão JSON: Get-Content "path\{id}.json"
- Logs backend: stdout (auto-reload ativo)
- Logs frontend: console browser

## 📞 Referência Rápida
- Teste CSV: D:\Python\polaryix\clientes.csv
- Contexto completo: D:\Python\polaryix\CONTEXTO_CONTINUACAO.md
- Clean Architecture: Domain → Storage → API
- Estado componente: 3 steps (info, upload, complete)
