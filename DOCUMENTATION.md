# Polaryix Documentation

## Visao Geral

Polaryix e uma plataforma web para conversao de arquivos, download de midias por link e analise de datasets. O produto combina uma interface Next.js com uma API FastAPI responsavel por upload, validacao, conversao, autenticacao, planos premium, historico e armazenamento local.

O objetivo atual do sistema e oferecer:

- Conversao de arquivos entre formatos suportados.
- Download por link para YouTube e TikTok.
- Sistema de usuarios com login por e-mail/senha e Google OAuth.
- Planos premium com creditos, limites de arquivo, prioridade e qualidade superior.
- Historico de conversoes em "Meus arquivos".
- Limpeza automatica de arquivos convertidos apos janela de retencao.
- Funcionalidades adicionais de datasets, dashboards e sessoes de analise.

Arquitetura em alto nivel:

```text
Browser
  |
  v
Next.js frontend (apps/web)
  |
  v
FastAPI backend (apps/api)
  |
  +-- Auth JSON storage
  +-- Conversion queue in memory
  +-- Conversion history JSON storage
  +-- Local file storage
  +-- Dataset/dashboard storage
```

## Stack

### Frontend

- Next.js 15.
- React 19.
- TypeScript.
- CSS Modules.
- Fetch API para comunicacao com backend.
- Vercel como alvo atual de hospedagem do frontend.

### Backend

- Python 3.12.
- FastAPI.
- Uvicorn.
- Pydantic e pydantic-settings.
- Pandas, Polars, DuckDB, PyArrow, OpenPyXL e xlrd para datasets e tabulares.
- Pillow para imagens.
- FFmpeg/ffprobe para audio/video.
- yt-dlp para download por link.

### Banco de dados / Storage atual

O projeto ainda nao usa banco relacional em producao. O armazenamento atual e local e baseado em JSON/arquivos:

- Usuarios: `apps/api/storage/auth/users.json`
- Sessoes: `apps/api/storage/auth/sessions.json`
- Uso de visitantes: `apps/api/storage/usage/credits.json`
- Historico de conversoes: `apps/api/storage/history/conversions.json`
- Arquivos processados: `apps/api/storage/processed`
- Uploads/quarentena: `apps/api/storage/uploads`, `apps/api/storage/quarantine`

### Autenticacao

- Cadastro com e-mail/senha.
- Login com e-mail/senha.
- Google OAuth.
- Sessao por token Bearer salvo no localStorage do frontend.
- Nao ha JWT assinado hoje; o token de sessao e opaco e persistido em `sessions.json`.

### Sistema Premium

O premium e controlado no backend em `apps/api/app/core/premium.py` e aplicado ao usuario em `apps/api/app/core/auth_store.py`.

### Sistema de Conversao

Implementado principalmente em:

- `apps/api/app/api/v1/routes/converter.py`
- `apps/api/app/core/conversion/compatibility.py`
- `apps/api/app/core/conversion_queue.py`
- `apps/api/app/core/conversion_history.py`

### Fila

Fila em memoria com `PriorityQueue` em `apps/api/app/core/conversion_queue.py`. Jobs com maior prioridade sao processados primeiro.

### Uploads e Downloads

- Uploads de conversor sao validados e processados pela rota `/api/v1/converter/*`.
- Uploads de datasets passam por quarentena e analise.
- Downloads seguros de arquivos do usuario usam `/api/v1/me/files/{file_id}/download`.
- Downloads por link usam yt-dlp e podem ser baixados via job.

### API

Base local padrao:

```text
http://127.0.0.1:8000/api/v1
```

No frontend, `NEXT_PUBLIC_API_URL` pode apontar para uma API externa/ngrok. Se ausente, o frontend usa `/api/v1`.

## Estrutura de Pastas

```text
apps/
  api/
    app/
      api/v1/routes/        Rotas FastAPI.
      core/                 Configuracao, auth store, premium, fila, historico e seguranca.
      data_processing/      Leitura, profiling, estatisticas, dashboards e insights.
      domain/               Schemas de dominio.
      infrastructure/       Storage local, dashboards, sessoes e db placeholder.
    storage/                Dados locais, uploads, outputs, historico e sessoes.
    tests/                  Testes unitarios e integracao.
    pyproject.toml          Dependencias Python.
  web/
    public/                 Assets estaticos.
    src/app/                Rotas do Next.js.
    src/components/         Componentes reutilizaveis.
    src/lib/                Cliente API e compatibilidade de conversoes.
    package.json            Scripts e dependencias frontend.
assets/                     Assets legados/compartilhados.
docs/                       Documentos tecnicos existentes.
infra/                      Docker/nginx.
scripts/                    Scripts auxiliares PowerShell.
storage/                    Storage legado/raiz.
```

## Fluxo de Conversao

Fluxo de arquivo:

```text
Usuario escolhe arquivo e formatos
  |
  v
Frontend valida combinacao e arquivo quando possivel
  |
  v
POST /api/v1/converter/convert-file ou convert-batch
  |
  v
Backend normaliza formatos
  |
  v
Backend valida matriz de compatibilidade
  |
  v
Backend valida tamanho, extensao e arquivo vazio
  |
  v
Job entra na fila com prioridade do plano
  |
  v
Worker executa conversao
  |
  v
Creditos sao consumidos
  |
  v
Arquivo final e salvo em storage/processed/conversions
  |
  v
Se usuario logado, historico e registrado
  |
  v
Download e retornado ao usuario
  |
  v
Arquivo expira conforme FILE_RETENTION_HOURS
  |
  v
Limpeza automatica remove arquivo fisico e preserva historico
```

Fluxo de download por link:

```text
Usuario cola link
  |
  v
POST /api/v1/converter/link-preview para metadados
  |
  v
POST /api/v1/converter/download-link/jobs
  |
  v
Job entra na fila com prioridade do plano
  |
  v
yt-dlp baixa audio/video
  |
  v
FFmpeg/ffprobe validam ou preparam MP4 compativel
  |
  v
Creditos sao consumidos
  |
  v
Job fica ready e libera download
  |
  v
Se usuario logado, historico recebe quality_requested e quality_delivered
```

## Sistema Premium

Planos atuais:

| Plano | Preco exibido | Creditos | Tamanho maximo | Conversoes simultaneas/lote | Prioridade |
| --- | ---: | ---: | ---: | ---: | ---: |
| Free | R$ 0 | 30/dia | 100 MB | 2 | 0 |
| Basic Mensal | R$ 9.99/mes | 1000/mes | 300 MB | 30 | 50 |
| Basic Anual | R$ 4.99/mes | 1000/mes | 300 MB | 30 | 50 |
| Pro Mensal | R$ 18.99/mes | 3000/mes | 1 GB | 60 | 100 |
| Pro Anual | R$ 12.99/mes | 3000/mes | 1 GB | 60 | 100 |

Custos de download por link:

- MP3: 2 tokens.
- MP4 720p: 5 tokens.
- 4K Premium: 5 tokens.

Conversoes de arquivos comuns consomem 1 credito por arquivo.

Qualidade premium:

- A opcao 4K tenta ate 2160p.
- Se 2160p nao existir, tenta 1440p, 1080p ou a melhor disponivel abaixo.
- O backend registra `quality_requested` e `quality_delivered`.
- Usuarios free nao podem forcar 4K pelo frontend; o backend tambem bloqueia.

## Sistema de Login

### Cadastro

`POST /api/v1/auth/signup`

- Cria usuario com e-mail, senha e aceite de termos.
- Senha usa PBKDF2 com salt.
- Usuario inicia como plano free.

### Login

`POST /api/v1/auth/login`

- Valida e-mail/senha.
- Retorna token de sessao opaco.
- Frontend salva em localStorage.

### Google Login

Rotas:

- `GET /api/v1/auth/oauth/google/start`
- `POST /api/v1/auth/oauth/google/exchange`
- `GET /api/v1/auth/oauth/google/callback`

Fluxo atual:

1. Frontend redireciona para start.
2. API monta URL do Google.
3. Google retorna para `/auth/google/callback` no frontend.
4. Frontend envia `code` para `/auth/oauth/google/exchange`.
5. Backend cria ou atualiza usuario, incluindo nome e avatar.

### Sessao

- Token Bearer opaco.
- Storage em `apps/api/storage/auth/sessions.json`.
- `get_current_user` valida token e usuario.

### Cookies e Middleware

- Ha componente de consentimento de cookies no frontend.
- A autenticacao principal nao usa cookie HTTP-only ainda.
- Nao ha middleware de protecao global no Next.js; as paginas verificam sessao via API/localStorage.

## Banco de Dados / Tabelas

Nao ha tabelas relacionais hoje. Os "modelos" persistidos estao em JSON:

### users.json

Campos principais:

- `id`
- `name`
- `email`
- `password_salt`
- `password_hash`
- `auth_provider`
- `google_id`
- `avatar_url`
- `is_premium`
- `plan`
- `billing`
- `plan_started_at`
- `plan_expires_at`
- `monthly_credits`
- `credits_remaining`
- `credits_period`
- `max_file_size_mb`
- `max_concurrent_conversions`
- `priority_level`

### sessions.json

- token de sessao
- `user_id`
- `created_at`

### conversions.json

- `id`
- `user_id`
- `original_filename`
- `original_format`
- `target_format`
- `input_path`
- `output_path`
- `download_url`
- `file_size`
- `status`
- `error_message`
- `quality_requested`
- `quality_delivered`
- `is_premium_job`
- `priority_level`
- `created_at`
- `started_at`
- `finished_at`
- `expires_at`
- `deleted_at`

### credits.json

Controle de uso de visitantes e chaves anonimas.

### Dataset/dashboard JSON

Arquivos em `storage/processed/datasets`, `storage/processed/dashboards`, `storage/processed/analysis_sessions` e `storage/processed/public`.

## API

Todas as rotas abaixo estao sob `/api/v1`.

### Health

- `GET /health`
  - Autenticacao: nao.
  - Retorna status da API.

### Auth

- `POST /auth/signup`
  - Body JSON: `name`, `email`, `password`, `terms_accepted`.
  - Autenticacao: nao.
  - Retorna: `{ token, user }`.

- `POST /auth/login`
  - Body JSON: `email`, `password`.
  - Autenticacao: nao.
  - Retorna: `{ token, user }`.

- `GET /auth/me`
  - Header: `Authorization: Bearer <token>`.
  - Retorna usuario atual.

- `POST /auth/logout`
  - Header Bearer opcional.
  - Remove sessao atual.

- `GET /auth/plans`
  - Lista planos premium.

- `POST /auth/premium/activate`
  - Header Bearer obrigatorio.
  - Body JSON: `plan` (`basic` ou `pro`), `billing` (`monthly` ou `annual`).
  - Retorna usuario atualizado.

- `GET /auth/oauth/google/start`
  - Redireciona para Google OAuth.

- `POST /auth/oauth/google/exchange`
  - Body JSON: `code`, `redirect_uri`.
  - Troca codigo do Google por sessao Polaryix.

- `GET /auth/oauth/google/callback`
  - Callback legado do backend.

### Converter

- `GET /converter/usage`
  - Headers: `x-polaryix-client-id` e/ou Bearer.
  - Query: `is_premium`, `premium_plan`.
  - Retorna creditos usados/restantes.

- `POST /converter/convert-file`
  - FormData: `file`, `from_format`, `to_format`, `is_premium`, `premium_plan`.
  - Autenticacao: opcional.
  - Retorna arquivo convertido.

- `POST /converter/convert-batch`
  - FormData: `files[]`, `from_format`, `to_format`, `is_premium`, `premium_plan`.
  - Autenticacao: opcional.
  - Retorna ZIP.

- `POST /converter/download-link/jobs`
  - FormData: `url`, `media_type`, `download_format`, `is_premium`, `premium_plan`.
  - Cria job assicrono.

- `GET /converter/download-link/jobs/{job_id}`
  - Retorna status, progresso, mensagem, download_url e qualidade entregue quando disponivel.

- `GET /converter/download-link/jobs/{job_id}/file`
  - Baixa arquivo final do job.

- `POST /converter/download-link`
  - Rota sincrona legada para baixar por link.

- `POST /converter/link-preview`
  - FormData: `url`.
  - Retorna titulo, thumbnail, duracao, uploader e URL publica.

### Meus Arquivos

- `GET /me/files`
  - Header Bearer obrigatorio.
  - Query: `limit`.
  - Retorna arquivos do usuario logado.

- `GET /me/files/{file_id}`
  - Header Bearer obrigatorio.
  - Retorna status de um arquivo do usuario.

- `GET /me/files/{file_id}/download`
  - Header Bearer obrigatorio.
  - Baixa arquivo se pertencer ao usuario e nao estiver expirado.

### Admin

- `POST /admin/cleanup-files`
  - Header: `x-admin-token` quando `ADMIN_CLEANUP_TOKEN` estiver configurado.
  - Executa limpeza manual.

### Datasets

- `POST /datasets/upload`
  - Upload de dataset.

- `GET /datasets`
  - Lista datasets analisados.

- `GET /datasets/{dataset_id}`
  - Retorna dataset analisado.

### Dashboards

- `POST /dashboards`
  - Cria dashboard.

- `GET /dashboards`
  - Lista dashboards.

- `GET /dashboards/{dashboard_id}`
  - Retorna dashboard enriquecido.

- `GET /dashboards/public/{slug}`
  - Retorna dashboard publico.

### Analysis Sessions

- `POST /analysis-sessions`
  - Cria sessao de analise multi-arquivo.

- `GET /analysis-sessions`
  - Lista sessoes.

- `GET /analysis-sessions/{session_id}`
  - Retorna sessao.

- `PATCH /analysis-sessions/{session_id}`
  - Atualiza sessao.

- `DELETE /analysis-sessions/{session_id}`
  - Remove sessao.

- `POST /analysis-sessions/{session_id}/files`
  - Adiciona arquivo a sessao.

- `GET /analysis-sessions/{session_id}/progress`
  - Retorna progresso.

## Sistema de Filas

Arquivo: `apps/api/app/core/conversion_queue.py`.

Funcionamento:

- Usa `queue.PriorityQueue`.
- Cada job possui `priority_level` e contador incremental.
- A prioridade e invertida internamente para que valores maiores sejam processados primeiro.
- Dentro da mesma prioridade, a ordem de chegada e preservada.
- Workers em threads daemon sao iniciados no startup da API.
- Quantidade de workers: `CONVERSION_WORKERS`.

Prioridades:

- Free: 0.
- Basic: 50.
- Pro: 100.

Status de jobs:

- Conversoes de arquivo ainda retornam de forma sincrona para preservar o contrato atual, mas entram na fila antes de processar.
- Downloads por link usam status `queued`, `running`, `ready` e `error`.
- Historico usa `queued`, `processing`, `completed`, `failed`, `expired` e `deleted`.

## Historico de Conversoes

Arquivo: `apps/api/app/core/conversion_history.py`.

O historico registra conversoes de usuarios logados. Visitantes podem converter e baixar, mas nao possuem area "Meus arquivos".

Regras:

- Usuario so lista seus proprios arquivos.
- Download por ID valida propriedade do usuario.
- Paths internos nao sao expostos na resposta publica.
- Arquivos expirados aparecem como expirados e nao oferecem download.

## Sistema de Limpeza Automatica

Implementado em:

- `apps/api/app/core/conversion_history.py`
- `apps/api/app/main.py`
- `apps/api/app/api/v1/routes/admin.py`

Funcionamento:

- A API inicia uma task de background no startup.
- A cada `CLEANUP_INTERVAL_HOURS`, executa `cleanup_expired_files`.
- Arquivos fisicos de `input_path` e `output_path` expirados sao removidos se estiverem dentro de `settings.storage_path`.
- Historico nao e apagado.
- Registros recebem `status = expired`, `deleted_at` e `download_url = null`.
- Cleanup manual pode ser chamado por `/api/v1/admin/cleanup-files`.

## Variaveis de Ambiente

### API

Definidas em `apps/api/app/core/config/settings.py` e documentadas em `apps/api/.env.example`.

```text
FRONTEND_URL
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
CONVERSION_WORKERS
FILE_RETENTION_HOURS
CLEANUP_INTERVAL_HOURS
MAX_FREE_FILE_SIZE_MB
MAX_BASIC_FILE_SIZE_MB
MAX_PRO_FILE_SIZE_MB
ADMIN_CLEANUP_TOKEN
```

Tambem existem defaults no backend:

```text
APP_NAME
APP_VERSION
ENVIRONMENT
DEBUG
MAX_UPLOAD_SIZE_MB
MAX_ROWS_PREVIEW
FREE_DAILY_CREDITS
BASIC_MONTHLY_CREDITS
PRO_MONTHLY_CREDITS
ALLOWED_ORIGINS
ALLOWED_ORIGIN_REGEX
STORAGE_PATH
UPLOAD_PATH
QUARANTINE_PATH
PROCESSED_PATH
```

### Frontend

```text
NEXT_PUBLIC_API_URL
```

Uso:

- Sem valor: frontend chama `/api/v1`.
- Com valor: frontend usa essa URL como origem da API e acrescenta `/api/v1`.
- Nao incluir `/api/v1` duplicado no valor.

## Comandos Uteis

API:

```powershell
cd D:\Python\polaryix\apps\api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd D:\Python\polaryix\apps\web
npm run dev
```

Build limpo:

```powershell
cd D:\Python\polaryix\apps\web
npm run build:clean
```

Testes backend:

```powershell
cd D:\Python\polaryix
python -m unittest apps.api.tests.unit.test_premium_history apps.api.tests.unit.test_converter_compatibility
```

## TODO

- Migrar JSON storage para banco persistente real, como PostgreSQL ou Supabase.
- Implementar pagamento real para Premium.
- Trocar sessao opaca em localStorage por cookies HTTP-only ou JWT assinado com refresh seguro.
- Persistir fila em Redis/RQ/Celery para producao multi-instancia.
- Criar painel administrativo real para cleanup, usuarios e planos.
- Adicionar logs estruturados de conversao e downloads.
- Adicionar rate limiting persistente por usuario/IP.
- Melhorar cobertura de testes de API com TestClient.
- Adicionar CI para build frontend e testes backend.
- Formalizar migracoes Alembic quando banco relacional for adotado.
- Criar politicas completas de privacidade, termos e retencao.
- Substituir ativacao manual de Premium por gateway de pagamento.
