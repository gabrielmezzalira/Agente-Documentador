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
| `AUTH_LOGIN_RATE_LIMIT_PER_MINUTE` | Tentativas de login por IP por minuto. Inteiro positivo; padrão `5`. |
| `AUTH_SIGNUP_RATE_LIMIT_PER_HOUR` | Cadastros/claims por IP por hora. Inteiro positivo; padrão `3`. |
| `MAX_IMAGE_PIXELS` | Teto de pixels (largura × altura) antes de converter imagem. Padrão `40000000`. |
| `PDF_POPPLER_TIMEOUT_SECONDS` | Tempo máximo do Poppler ao rasterizar a 1ª página de PDF escaneado. Padrão `30`. |
| `API_DOCS_ENABLED` | `true` local, `false` em produção. Com `false`, `/docs`, `/redoc` e `/openapi.json` devolvem 404; `/health` continua público. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Cliente OAuth do Google. |
| `GOOGLE_REFRESH_TOKEN` / `GOOGLE_REFRESH_TOKEN_DEV` | Identidade Drive de Dados e Dev. |
| `GDOCS_TEMPLATE_ID*` | Templates de Dados e overrides opcionais com sufixo `_DEV`. |
| `GDRIVE_FOLDER_ID` / `GDRIVE_FOLDER_ID_DEV` | Pastas raiz de Dados e Dev. |
| `GITHUB_APP_ID` / `GITHUB_APP_SLUG` | Identidade pública do GitHub App. |
| `GITHUB_APP_PRIVATE_KEY` | Chave PEM privada do App, somente no backend. |
| `GITHUB_WEBHOOK_SECRET` | Segredo aleatório usado no HMAC dos webhooks. |
| `GITHUB_CONNECTION_STATE_SECRET` | Segredo aleatório para assinar states e tokens temporários. |

### Frontend (Vercel ou `docudata-frontend/.env.local`)

| Variável | Uso |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL pública do backend. |

Nenhuma credencial de serviço usa prefixo `NEXT_PUBLIC_`; o navegador autentica por cookie httpOnly.

### Hook legado (somente repositórios ainda não migrados para o GitHub App)

| Variável | Uso |
|---|---|
| `DOCUDATA_API_URL` | URL do backend chamada pelo workflow. |
| `DOCUDATA_PROJECT_ID` | UUID manual do projeto, mantido apenas por compatibilidade temporária. |
| `DOCUDATA_APP_SECRET` | Segredo compartilhado já usado pela aplicação. |
| `GITHUB_TOKEN` / `GITHUB_REPOSITORY` / `GITHUB_SHA` | Valores fornecidos automaticamente pelo GitHub Actions. |

Novos repositórios de Dados e Dev devem usar o GitHub App. O hook legado permanece
apenas para não interromper consumidores já configurados.

## Criar o GitHub App para Dados e Dev

1. Em **GitHub → Settings → Developer settings → GitHub Apps**, crie um App.
2. Configure o webhook como `https://SEU-BACKEND/webhooks/github` e gere um segredo aleatório para `GITHUB_WEBHOOK_SECRET`.
3. Use como **Setup URL** `https://SEU-BACKEND/integrations/github/callback` e habilite o redirecionamento após atualização da instalação.
4. Permissões do repositório: **Metadata: read-only**, **Contents: read-only** e **Commit statuses: read and write**.
5. Eventos: **Push**, **Installation**, **Installation repositories** e **Repository** (para sincronizar renomes).
6. Copie App ID e slug, gere a private key PEM e guarde tudo somente no Railway.
7. Gere `GITHUB_CONNECTION_STATE_SECRET` com `openssl rand -hex 32`.
8. Aplique manualmente a Migration v5 antes de publicar o backend com as credenciais. Em produção, crie os índices em uma janela compatível com o volume atual.

O GitHub controla quais repositórios a instalação do App pode acessar globalmente.
Depois da primeira instalação, cada projeto abre um seletor dentro da aplicação para
vincular somente os repositórios que lhe pertencem; nenhum é marcado automaticamente.
O seletor carrega os 30 repositórios com push mais recente e pesquisa os demais sob
demanda, evitando transferir toda a organização a cada abertura.
Use **Liberar mais repositórios no GitHub** apenas quando o repositório desejado ainda
não estiver autorizado. O installation token nunca é enviado ao navegador.

## Hardening operacional (Spec 09)

### Correlação de erros

Toda resposta traz `X-Request-ID` (o backend reaproveita o header recebido quando
ele é curto e alfanumérico, senão gera um). Erro não tratado devolve apenas
`{"detail": "...", "request_id": "..."}` — o diagnóstico sanitizado fica no log do Railway,
na linha `erro_nao_tratado request_id=... method=... path=... status=500 exc=... stack=...`.
O stack registra somente arquivo, linha e função: a mensagem da exceção é omitida
porque SDKs podem incluir credenciais e payloads nela. Para
investigar um erro relatado por um gerente, peça o `request_id` e busque por ele.

O backend não registra corpo de request, cookies, header de autorização, chave
Gemini, chave de aplicação, private key do GitHub App, token de instalação,
conteúdo extraído, diff nem documento gerado.

### Desligar a documentação da API em produção

Antes ou junto do deploy, defina `API_DOCS_ENABLED=false` no Railway. Confirme
depois que `/docs` responde 404 e que `/health` continua respondendo
`{"status":"ok"}`.

### Confiança no `X-Forwarded-For`

Os limites por IP usam o primeiro item de `X-Forwarded-For`. Isso só é confiável
enquanto o Railway sobrescrever/controlar esse header e o backend não estiver
acessível por um caminho que contorne o proxy — exposto direto, qualquer cliente
forja o valor e escapa do limite. Uma lista de proxies confiáveis e o
armazenamento distribuído do limiter ficam para a Spec 10.

### Migration v6 (índices)

Os índices de leitura da Spec 09 estão comentados no fim de
`docudata-backend/supabase_schema.sql`. Não são requisito funcional e **não são
aplicados por deploy**: aplique manualmente, um por vez, em janela adequada, e
prefira `CREATE INDEX CONCURRENTLY` quando a tabela já for grande.

### Auditoria automática

O workflow `.github/workflows/ci.yml` roda `pytest`, `npm run build`,
`npm audit --omit=dev --audit-level=high`, `pip-audit`, `git diff --check` e uma
varredura de segredos. Nenhum passo usa credencial real — os testes já rodam com
Gemini, GitHub, Drive, Resend e Supabase mockados.
