# Spec 01 — CORS restrito + chave de aplicação compartilhada

**Prioridade:** crítica · **Depende de:** nada · **Bloqueia:** 07

## Problema

Hoje `main.py` tem `allow_origins=["*"]` com `allow_credentials=True` (combinação
inválida e sinal de que ninguém pensou nisso desde o início), e **nenhum endpoint
exige nada para ser chamado** — qualquer pessoa com a URL do Railway pode criar,
listar, apagar projetos, disparar gerações (que custam dinheiro em Gemini) e apagar
documentos.

Não vamos construir login de usuário agora (ver `AGENTS.md`). Vamos adicionar um
**segredo de aplicação único**, compartilhado entre o frontend oficial e o hook do
GitHub Actions, exigido em todo endpoint de escrita/geração. É importante ser
honesto sobre o que isso protege: como o frontend roda no navegador, esse segredo
vai parar no bundle JS e nas requisições de rede — ele **não impede** uma pessoa
determinada que inspecione o próprio app. O que ele impede é o cenário realista de
hoje: alguém (ou algum bot/scanner) encontrar a URL pública do Railway e começar a
bater nos endpoints sem contexto nenhum. Para chamadas servidor-a-servidor (o hook do
GitHub Actions, spec 07), o segredo funciona como proteção real, porque nunca passa
pelo navegador de ninguém.

## Escopo

### Backend

1. Nova env var `DOCUDATA_APP_SECRET` (string longa e aleatória, sem valor default —
   se não estiver setada, o backend deve falhar ao subir, não abrir a porta destrancada
   por engano).
2. Criar `docudata-backend/core/security.py` (crie a pasta `core/` se não existir) com
   uma dependency do FastAPI, por exemplo:
   ```python
   def require_app_key(x_docudata_key: str = Header(...)) -> None:
       ...compara com secrets.compare_digest contra os.environ["DOCUDATA_APP_SECRET"]...
       # 401 se ausente ou não bater
   ```
   Use `secrets.compare_digest`, não `==` (evita timing attack, é grátis de fazer certo).
3. Nome do header: **`X-Docudata-Key`**.
4. Aplique essa dependency em **todos os routers exceto `/health`**. Prefira aplicar
   no `include_router(..., dependencies=[Depends(require_app_key)])` em `main.py` em
   vez de decorar cada endpoint individualmente — mais fácil de auditar que nada ficou
   de fora.
5. Corrija CORS no mesmo `main.py`:
   - `allow_origins` vira uma lista lida de uma env var nova `ALLOWED_ORIGINS`
     (string separada por vírgula, ex: `https://docudata.vercel.app,http://localhost:3000`),
     nunca mais `"*"`.
   - `allow_credentials=False` (não usamos cookie de sessão; não há motivo pra `True`).
6. Resposta de erro do `require_app_key` deve ser `401` com um `detail` genérico
   (`"Chave de aplicação ausente ou inválida"`) — não ecoe o valor recebido.

### Frontend

7. Em `app/lib/api.ts`, centralize **todas** as chamadas fetch para passarem pelo
   mesmo helper (se já não passam) e adicione o header em toda requisição:
   ```ts
   const APP_KEY = process.env.NEXT_PUBLIC_DOCUDATA_APP_SECRET ?? "";
   headers: { ...existing, "X-Docudata-Key": APP_KEY }
   ```
8. Nova env var de frontend: `NEXT_PUBLIC_DOCUDATA_APP_SECRET` (mesmo valor de
   `DOCUDATA_APP_SECRET` do backend — ver `GUIDE.md` para onde configurar em cada
   ambiente).

### Não faz parte desta spec

- Rate limiting e limite de upload → spec 02.
- Qualquer UI de "login" ou tela de senha → fora de escopo, não construir.

## Critérios de aceite

- [ ] Subir o backend sem `DOCUDATA_APP_SECRET` setada falha no boot com uma mensagem
      clara (não sobe silenciosamente sem proteção).
- [ ] `GET /health` continua respondendo `200` sem header nenhum.
- [ ] Qualquer outro endpoint (ex: `GET /projects`) responde `401` sem o header
      `X-Docudata-Key`, e `401` também com o header errado.
- [ ] Com o header correto, todos os endpoints existentes continuam funcionando como
      antes (nenhuma regressão de comportamento, só a checagem nova).
- [ ] `allow_origins` não contém `"*"` em nenhum ambiente; `allow_credentials=False`.
- [ ] Frontend consegue falar com o backend normalmente em dev local depois de setar
      as duas env vars (`DOCUDATA_APP_SECRET` no backend, `NEXT_PUBLIC_DOCUDATA_APP_SECRET`
      no frontend, mesmo valor).
- [ ] `pytest` no backend passa (ajuste/estenda os testes existentes para injetar o
      header nas chamadas de `TestClient`, senão todos vão começar a falhar com 401).

## Como testar manualmente

```bash
# sem header — deve dar 401
curl -i http://localhost:8000/projects

# com header errado — 401
curl -i http://localhost:8000/projects -H "X-Docudata-Key: errado"

# com header certo — 200
curl -i http://localhost:8000/projects -H "X-Docudata-Key: $DOCUDATA_APP_SECRET"

# health não exige nada
curl -i http://localhost:8000/health
```

No frontend, abrir a lista de projetos em `http://localhost:3000` e confirmar que
carrega normalmente (prova que o header está sendo enviado).
