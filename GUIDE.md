# Guia de configuração

## Mapa de variáveis de ambiente

### Backend (Railway ou `docudata-backend/.env`)

| Variável | Uso |
|---|---|
| `DOCUDATA_APP_SECRET` | Segredo compartilhado apenas por hooks e automações servidor-a-servidor. |
| `DOCUDATA_SECRETS_KEY` | Chave Fernet que criptografa a chave Gemini global. |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | Acesso servidor ao Supabase. |
| `ALLOWED_ORIGINS` | Origens permitidas e URL usada no retorno do GitHub. |
| `FRONTEND_URL` | Origem principal do frontend para CORS com cookies. |
| `JWT_SECRET` | Assinatura das sessões de usuário. |
| `RESEND_API_KEY` / `RESEND_FROM` | Envio dos lembretes por email. |
| `MAX_UPLOAD_MB` / `RATE_LIMIT_PER_MINUTE` | Limites de upload e chamadas pagas. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Cliente OAuth do Google. |
| `GOOGLE_REFRESH_TOKEN` / `GOOGLE_REFRESH_TOKEN_DEV` | Identidade Drive de Dados e Dev. |
| `GDOCS_TEMPLATE_ID*` | Templates de Dados e overrides opcionais com sufixo `_DEV`. |
| `GDRIVE_FOLDER_ID` / `GDRIVE_FOLDER_ID_DEV` | Pastas raiz de Dados e Dev. |
| `GITHUB_INTEGRATION_ENABLED` | `false` por padrão; liga a integração somente após a migration. |
| `GITHUB_INTEGRATION_SUBAREAS` | Lista permitida; no piloto deve permanecer `dev`. |
| `GITHUB_APP_ID` / `GITHUB_APP_SLUG` | Identidade pública do GitHub App. |
| `GITHUB_APP_PRIVATE_KEY` | Chave PEM privada do App, somente no backend. |
| `GITHUB_WEBHOOK_SECRET` | Segredo aleatório usado no HMAC dos webhooks. |
| `GITHUB_CONNECTION_STATE_SECRET` | Segredo aleatório para assinar states e tokens temporários. |

### Frontend (Vercel ou `docudata-frontend/.env.local`)

| Variável | Uso |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL pública do backend. |

Nenhuma credencial de serviço usa prefixo `NEXT_PUBLIC_`; o navegador autentica por cookie httpOnly.

### Hook legado (somente repositórios ainda não migrados durante o piloto)

| Variável | Uso |
|---|---|
| `DOCUDATA_API_URL` | URL do backend chamada pelo workflow. |
| `DOCUDATA_PROJECT_ID` | UUID manual do projeto, mantido apenas por compatibilidade temporária. |
| `DOCUDATA_APP_SECRET` | Segredo compartilhado já usado pela aplicação. |
| `GITHUB_TOKEN` / `GITHUB_REPOSITORY` / `GITHUB_SHA` | Valores fornecidos automaticamente pelo GitHub Actions. |

Novos repositórios Dev devem usar o GitHub App. O hook legado não será removido até
os consumidores atuais serem levantados e o piloto ser aprovado.

## Criar o GitHub App para o piloto Dev

1. Em **GitHub → Settings → Developer settings → GitHub Apps**, crie um App.
2. Configure o webhook como `https://SEU-BACKEND/webhooks/github` e gere um segredo aleatório para `GITHUB_WEBHOOK_SECRET`.
3. Use como **Setup URL** `https://SEU-BACKEND/integrations/github/callback` e habilite o redirecionamento após atualização da instalação.
4. Permissões do repositório: **Metadata: read-only**, **Contents: read-only** e **Commit statuses: read and write**.
5. Eventos: **Push**, **Installation**, **Installation repositories** e **Repository** (para sincronizar renomes).
6. Copie App ID e slug, gere a private key PEM e guarde tudo somente no Railway.
7. Gere `GITHUB_CONNECTION_STATE_SECRET` com `openssl rand -hex 32`.
8. Publique primeiro com a flag `false`, aplique manualmente a Migration v5 e só então altere para `true`, mantendo `GITHUB_INTEGRATION_SUBAREAS=dev`. Em produção, crie os índices em uma janela compatível com o volume atual.

O GitHub permite selecionar um ou mais repositórios durante a instalação. A aplicação
lista somente os repositórios autorizados e nunca envia o installation token ao navegador.
