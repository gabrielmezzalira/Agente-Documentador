# Spec 07 — Rollout do commit tracker pra Dev + proteger o webhook

**Prioridade:** média · **Depende de:** 01, 04 · **Bloqueia:** nada

## Problema

`hooks/docudata_agent.py` + `hooks/docudata.yml` já implementam o que "dev" precisa
(ingestão automática de commits via GitHub Actions) — só que hoje batem em
`POST /ingest/commit` sem nenhum header de autenticação, o que depois da spec 01 vai
começar a devolver `401` pra esse script. Esta spec conserta isso e documenta a
instalação pros squads de dev.

## Escopo

### 1. Atualizar `hooks/docudata_agent.py`

- Novo env var esperada: `DOCUDATA_APP_SECRET` (vem de um GitHub Secret do repositório
  do projeto, igual `DOCUDATA_PROJECT_ID` já é hoje).
- No `http_json(...)` usado para chamar `POST /ingest/commit`, adicionar o header
  `X-Docudata-Key: <DOCUDATA_APP_SECRET>` (mesmo header definido na spec 01).
- A chamada a `GET /projects/{project_id}/current-sprint` também precisa do mesmo
  header, já que a spec 01 protege todos os routers.
- Não mude nada na lógica de detecção de sprint, diff, ou no commit status do GitHub
  — só a autenticação contra o DocuData.

### 2. Atualizar `hooks/docudata.yml`

Adicionar `DOCUDATA_APP_SECRET: ${{ secrets.DOCUDATA_APP_SECRET }}` ao bloco `env:`
do step "Registrar commit no DocuData", junto dos secrets que já existem.

### 3. Atualizar o comentário de instalação no topo dos dois arquivos

Hoje o comentário de `docudata.yml` lista os secrets a configurar
(`DOCUDATA_API_URL`, `DOCUDATA_PROJECT_ID`). Adicionar `DOCUDATA_APP_SECRET` a essa
lista, com a instrução de que o valor é o mesmo configurado no backend (pegar com
quem administra o Railway).

### 4. Documentação de instalação para squads de Dev

No mesmo arquivo (ou em um novo `hooks/README.md`, se ficar mais organizado),
adicionar uma seção curta "Instalando em um projeto de Dev": os passos são
idênticos aos de Dados, a única diferença é que o `DOCUDATA_PROJECT_ID` usado deve
ser o de um projeto criado com `subarea: "dev"` (ver spec 06 — criado a partir de
`/dev/projects/new`). Não existe nenhuma flag ou env var separada pra "modo dev" no
hook — a subárea já está implícita no `project_id`.

### Não faz parte desta spec

- Nenhuma mudança de lógica em `commit_ingest.py` (o backend já é agnóstico de
  subárea nesse endpoint, porque a chave Gemini certa já é resolvida via
  `project["subarea"]` desde a spec 04).

## Critérios de aceite

- [ ] Rodar `docudata_agent.py` localmente (simulando as env vars do GitHub Actions)
      contra o backend com a spec 01 aplicada resulta em `201` no `/ingest/commit`,
      não `401`.
- [ ] Sem `DOCUDATA_APP_SECRET` setada, o script ainda roda sem crashar (o header vai
      vazio ou ausente) mas recebe `401` do backend e loga isso de forma clara — hoje
      o script já trata `post_status != 201` como "falha ao registrar, continuando"
      sem quebrar o commit; mantenha esse comportamento (o objetivo do hook é nunca
      travar o `git push` do desenvolvedor).
- [ ] `docudata.yml` tem o novo secret referenciado corretamente.
- [ ] Documentação de instalação pra Dev existe e está clara o suficiente pra alguém
      que nunca viu o projeto seguir sozinho.

## Como testar manualmente

```bash
export DOCUDATA_API_URL="http://localhost:8000"
export DOCUDATA_PROJECT_ID="<uuid de um projeto subarea=dev criado na spec 06>"
export DOCUDATA_APP_SECRET="<mesmo valor do backend>"
export GITHUB_TOKEN=""   # vazio é ok localmente, só pula a escrita de commit status
export GITHUB_REPOSITORY=""
export GITHUB_SHA=""

# dentro de um repo git qualquer com pelo menos 1 commit:
python3 hooks/docudata_agent.py
# esperado: log final "[docudata] Commit <hash> registrado na Sprint N"
```
