# Como Executar o Polaryix

Este guia explica como conectar e executar a API (backend) e o Frontend (web).

## 📋 Pré-requisitos

- Python 3.11+
- Node.js 18+
- npm ou yarn
- Git

---

## 🔧 Backend (API FastAPI)

### 1. Acesse a pasta da API
```bash
cd apps/api
```

### 2. Crie um ambiente virtual (recomendado)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Verifique o arquivo .env
O arquivo `apps/api/.env` já está configurado com:
```env
APP_NAME=Polaryix API
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true
MAX_UPLOAD_SIZE_MB=25
MAX_ROWS_PREVIEW=1000
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 5. Inicie a API
```bash
python -m uvicorn app.main:app --reload --port 8000
```

A API estará disponível em: **http://localhost:8000**

### 6. Teste a API
Acesse a documentação automática:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🎨 Frontend (Next.js)

### 1. Acesse a pasta do frontend
```bash
cd apps/web
```

### 2. Instale as dependências
```bash
npm install
```

### 3. Verifique a variável de ambiente
O arquivo `.env.local` deve conter:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Se o arquivo não existir, crie-o com o conteúdo acima.

### 4. Inicie o frontend
```bash
npm run dev
```

O frontend estará disponível em: **http://localhost:3000**

---

## 🔗 Como a Conexão Funciona

### Arquitetura
```
┌─────────────┐         HTTP/REST          ┌─────────────┐
│   Browser   │ ──────────────────────────► │   FastAPI   │
│  (Next.js)  │ ◄────────────────────────── │   Backend   │
│  Port: 3000 │                             │  Port: 8000 │
└─────────────┘                             └─────────────┘
```

### Fluxo de Dados

1. **Frontend → Backend:**
   - O hook `useAnalysisSession.ts` faz requisições para `http://localhost:8000/api/v1/...`
   - Usa `fetch()` com headers JSON
   - Envia dados no formato JSON

2. **Backend → Frontend:**
   - Retorna JSON com os dados da sessão
   - Frontend atualiza o estado com `setSession()`

3. **CORS:**
   - Backend está configurado para aceitar requisições de `localhost:3000` e `localhost:3001`
   - Configurado em `apps/api/app/core/config/settings.py`

### Principais Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/analysis-sessions` | Cria nova sessão |
| GET | `/api/v1/analysis-sessions` | Lista todas as sessões |
| GET | `/api/v1/analysis-sessions/{id}` | Busca sessão por ID |
| POST | `/api/v1/analysis-sessions/{id}/files` | Upload de arquivo |
| GET | `/api/v1/analysis-sessions/{id}/progress` | Progresso do processamento |

---

## 🚀 Executando Ambos os Serviços

### Opção 1: Terminais Separados

**Terminal 1 (Backend):**
```bash
cd apps/api
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd apps/web
npm run dev
```

### Opção 2: Usando Make (se disponível)

```bash
# Na raiz do projeto
make dev
```

---

## ✅ Verificando se está Funcionando

### 1. Teste a API
```bash
# Em outro terminal
curl http://localhost:8000/health
```

Deve retornar algo como:
```json
{
  "status": "healthy"
}
```

### 2. Teste o Frontend
Abra o browser em: http://localhost:3000

Você deve ver:
- Header com logo Polaryix
- Botões Login/Cadastrar
- Seção hero com gradiente
- Cards de dashboards interativos

### 3. Teste a Conexão

1. Acesse http://localhost:3000/upload
2. Preencha os campos do formulário
3. Clique em "Próximo: Enviar Arquivos"
4. Faça upload de um arquivo CSV
5. Clique em "Gerar Dashboard Inteligente"

Se aparecer a tela de processamento com barra de progresso, a conexão está funcionando!

---

## 🐛 Troubleshooting

### Erro: "Cannot connect to API"

**Solução:**
1. Verifique se a API está rodando: `http://localhost:8000/docs`
2. Verifique o CORS em `settings.py`
3. Verifique a variável `NEXT_PUBLIC_API_URL` no frontend

### Erro: "Module not found" no backend

**Solução:**
```bash
cd apps/api
pip install -r requirements.txt
```

### Erro: "npm run dev" não funciona

**Solução:**
```bash
cd apps/web
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Porta já em uso

**Solução:**
```bash
# Backend - use outra porta
python -m uvicorn app.main:app --reload --port 8001

# Frontend
npm run dev -- -p 3001
```

Não esqueça de atualizar o `.env.local` e o CORS!

---

## 📊 Estrutura de Pastas

```
polaryix/
├── apps/
│   ├── api/                    # Backend FastAPI
│   │   ├── app/
│   │   │   ├── api/v1/         # Rotas da API
│   │   │   ├── domain/         # Modelos e schemas
│   │   │   ├── infrastructure/ # Storage e banco
│   │   │   └── main.py         # Entry point
│   │   ├── .env                # Configurações
│   │   └── requirements.txt    # Dependências Python
│   │
│   └── web/                    # Frontend Next.js
│       ├── src/
│       │   ├── app/            # Páginas (rotas)
│       │   ├── components/     # Componentes React
│       │   ├── hooks/          # Custom hooks
│       │   └── types/          # TypeScript types
│       ├── .env.local          # Variáveis do frontend
│       └── package.json        # Dependências Node
│
└── docs/                       # Documentação
```

---

## 🔄 Próximos Passos

1. **Autenticação:** Implementar login/cadastro real
2. **Banco de Dados:** Migrar de JSON para PostgreSQL
3. **IA:** Integrar com OpenAI/Claude para análise
4. **Deploy:** Configurar para produção (Vercel + Railway/Render)

---

## 📝 Comandos Úteis

### Backend
```bash
# Rodar com auto-reload
python -m uvicorn app.main:app --reload

# Rodar em produção
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Ver logs
tail -f logs/app.log
```

### Frontend
```bash
# Desenvolvimento
npm run dev

# Build para produção
npm run build

# Rodar produção
npm start

# Lint
npm run lint
```

---

## 🆘 Suporte

Se tiver problemas:
1. Verifique os logs do terminal
2. Consulte a documentação da API em `/docs`
3. Verifique se as portas 3000 e 8000 estão livres