# PolarYix

## Documentacao de Implantacao e Configuracao da VPS

Data: 2026-06-30

Este guia adapta o fluxo usado no forum da Contabo para o projeto PolarYix.

---

## Informacoes Gerais

Projeto:

**PolarYix**

Tecnologias:

- Python 3.12 ou 3.11
- FastAPI
- Uvicorn
- Next.js
- Node.js 20+
- Nginx
- Systemd
- SMTP
- Mercado Pago
- PayPal

Sistema recomendado:

```text
Ubuntu 22.04 LTS ou Ubuntu 24.04 LTS
```

Servidor:

```text
Contabo VPS
```

---

## Estrutura Recomendada

Projeto em:

```text
/var/www/polaryix
```

Estrutura principal:

```text
polaryix/
apps/
  api/
    app/
    storage/
    .env
    requirements.txt
    venv/
  web/
    .next/
    public/
    package.json
PAYMENTS_SETUP_GUIDE.md
DEPLOY_CONTABO_POLARYIX.md
```

---

## Instalacao Base

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx git curl build-essential
```

Node.js 20:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
node -v
npm -v
```

---

## Enviar Projeto

Opcao simples, igual ao forum:

1. Enviar arquivos via WinSCP.
2. Substituir em `/var/www/polaryix`.
3. Reiniciar servicos.

Opcao com Git:

```bash
cd /var/www
git clone URL_DO_REPOSITORIO polaryix
```

---

## Backend FastAPI

Entrar na API:

```bash
cd /var/www/polaryix/apps/api
```

Criar ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Criar `.env` real:

```bash
cp .env.example .env
nano .env
```

Importante:

- Nunca coloque secrets reais em `.env.example`.
- O arquivo real deve ser `apps/api/.env`.
- `.env` deve ficar fora do Git.

---

## Variaveis Principais

Exemplo para producao usando o mesmo dominio:

```env
ENVIRONMENT=production
DEBUG=false
FRONTEND_URL=https://polaryix.com
BACKEND_PUBLIC_URL=https://polaryix.com
PUBLIC_LOGO_URL=https://polaryix.com/assets/polaryix-logo.png
ALLOWED_ORIGINS=https://polaryix.com,https://www.polaryix.com
```

Se usar subdominio para API:

```env
FRONTEND_URL=https://polaryix.com
BACKEND_PUBLIC_URL=https://api.polaryix.com
ALLOWED_ORIGINS=https://polaryix.com,https://www.polaryix.com
```

Google OAuth:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://polaryix.com/auth/google/callback
```

SMTP:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true
```

Mercado Pago:

```env
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_PUBLIC_KEY=
MERCADOPAGO_WEBHOOK_SECRET=
MERCADOPAGO_ENV=production
```

PayPal:

```env
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_WEBHOOK_ID=
PAYPAL_ENV=production
```

---

## Systemd API

Criar:

```bash
nano /etc/systemd/system/polaryix-api.service
```

Conteudo:

```ini
[Unit]
Description=PolarYix FastAPI
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/polaryix/apps/api
Environment="PATH=/var/www/polaryix/apps/api/venv/bin"
ExecStart=/var/www/polaryix/apps/api/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ativar:

```bash
systemctl daemon-reload
systemctl enable polaryix-api
systemctl start polaryix-api
```

Comandos:

```bash
systemctl restart polaryix-api
systemctl status polaryix-api
journalctl -u polaryix-api -n 100 --no-pager
```

---

## Frontend Next.js

Entrar no frontend:

```bash
cd /var/www/polaryix/apps/web
npm install
npm run build
```

Criar service:

```bash
nano /etc/systemd/system/polaryix-web.service
```

Conteudo:

```ini
[Unit]
Description=PolarYix Next.js
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/polaryix/apps/web
Environment=NODE_ENV=production
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ativar:

```bash
systemctl daemon-reload
systemctl enable polaryix-web
systemctl start polaryix-web
```

Comandos:

```bash
systemctl restart polaryix-web
systemctl status polaryix-web
journalctl -u polaryix-web -n 100 --no-pager
```

---

## Nginx

Configuracao usando um unico dominio:

```bash
nano /etc/nginx/sites-available/polaryix
```

Conteudo:

```nginx
server {
    listen 80;
    server_name polaryix.com www.polaryix.com;

    client_max_body_size 1024M;

    location /api/v1/ {
        proxy_pass http://127.0.0.1:8000/api/v1/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Ativar:

```bash
ln -s /etc/nginx/sites-available/polaryix /etc/nginx/sites-enabled/polaryix
nginx -t
systemctl reload nginx
```

---

## SSL

Instalar Certbot:

```bash
apt install -y certbot python3-certbot-nginx
```

Gerar SSL:

```bash
certbot --nginx -d polaryix.com -d www.polaryix.com
```

Testar renovacao:

```bash
certbot renew --dry-run
```

---

## Google OAuth

No Google Cloud Console:

1. Criar projeto.
2. Configurar OAuth consent screen.
3. Criar OAuth Client ID do tipo Web application.
4. Authorized JavaScript origins:

```text
https://polaryix.com
```

5. Authorized redirect URIs:

```text
https://polaryix.com/auth/google/callback
```

6. Copiar Client ID e Client Secret para `apps/api/.env`.

Depois:

```bash
systemctl restart polaryix-api
```

---

## SMTP Google

Para Gmail pessoal ou Google Workspace:

1. Ativar verificacao em duas etapas.
2. Criar senha de app para o e-mail remetente.
3. Configurar no `apps/api/.env`.

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seu-email@dominio.com
SMTP_PASSWORD=SENHA_DE_APP
SMTP_FROM_EMAIL=seu-email@dominio.com
SMTP_USE_TLS=true
```

Recomendado para producao:

- Usar `no-reply@polaryix.com`.
- Configurar SPF, DKIM e DMARC.
- Testar verificacao de e-mail e recuperacao de senha.

---

## Mercado Pago e PIX

Webhook:

```text
https://polaryix.com/api/v1/webhooks/mercadopago
```

No `.env`:

```env
MERCADOPAGO_ENV=production
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_PUBLIC_KEY=
MERCADOPAGO_WEBHOOK_SECRET=
```

Testar:

1. Checkout normal.
2. PIX QR Code.
3. Webhook aprovado.
4. Premium/creditos liberados apenas com `approved`.

---

## PayPal

Webhook:

```text
https://polaryix.com/api/v1/webhooks/paypal
```

No `.env`:

```env
PAYPAL_ENV=production
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_WEBHOOK_ID=
```

Testar pagamento real de baixo valor antes de lancar.

---

## Atualizacao do Projeto

Fluxo com WinSCP:

1. Enviar arquivos novos.
2. Substituir arquivos em `/var/www/polaryix`.
3. Reinstalar dependencias se mudaram.
4. Rodar build do frontend.
5. Reiniciar servicos.

Comandos:

```bash
cd /var/www/polaryix/apps/api
source venv/bin/activate
pip install -r requirements.txt

cd /var/www/polaryix/apps/web
npm install
npm run build

systemctl restart polaryix-api
systemctl restart polaryix-web
```

---

## Logs

API:

```bash
journalctl -u polaryix-api -n 100 --no-pager
```

Web:

```bash
journalctl -u polaryix-web -n 100 --no-pager
```

Nginx:

```bash
tail -n 100 /var/log/nginx/error.log
tail -n 100 /var/log/nginx/access.log
```

---

## Backup

Enquanto o projeto usa storage JSON/local:

```bash
mkdir -p /var/backups/polaryix
tar -czf /var/backups/polaryix/storage-$(date +%F-%H%M).tar.gz /var/www/polaryix/apps/api/storage
```

Antes de atualizacoes importantes:

```bash
tar -czf /var/backups/polaryix/pre-update-$(date +%F-%H%M).tar.gz /var/www/polaryix
```

---

## Checklist Antes de Produzir

- [ ] `.env` real criado em `apps/api/.env`.
- [ ] Nenhum secret dentro de `.env.example`.
- [ ] `ENVIRONMENT=production`.
- [ ] `DEBUG=false`.
- [ ] HTTPS ativo.
- [ ] Nginx proxy para `/api/v1`.
- [ ] Google OAuth testado.
- [ ] SMTP testado.
- [ ] Verificacao de e-mail testada.
- [ ] Recuperacao de senha testada.
- [ ] Mercado Pago sandbox testado.
- [ ] PayPal sandbox testado.
- [ ] PIX QR Code testado.
- [ ] Webhooks publicos funcionando.
- [ ] Pagamento real de baixo valor testado.
- [ ] Premium/creditos liberam apenas apos `approved`.
- [ ] Backup do storage configurado.
