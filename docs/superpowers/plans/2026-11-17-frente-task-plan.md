# Frente da task (IA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a IA identifica a frente de cada task: `software`, `mobile`, `dados` ou `ia`. O gerente pode corrigir.

**Architecture:** `services/frente.py` faz uma chamada curta ao Gemini (`gemini-3.5-flash-lite`, saída estruturada com `Literal`). Ela roda em segundo plano (`BackgroundTasks`) depois de criar a task e quando o texto muda. Por isso não atrasa a criação, e uma falha só deixa `frente` nula. O gerente sobrescreve pelo PATCH, e aí a IA não mexe mais.

**Tech Stack:** FastAPI, LangChain `ChatGoogleGenerativeAI`, Supabase, Next.js (estilos inline, `app/components/ds`).

**Spec:** pedido do usuário em 2026-11-17: "uma chamada pra IA fazer em cada task pra identificar uma frente: software, mobile, dados ou IA". Decisões abaixo, tomadas pelo controller.

## Global Constraints

- Frentes válidas, exatamente: `software`, `mobile`, `dados`, `ia`. Rótulos na UI: "Software", "Mobile", "Dados", "IA".
- Colunas novas: `tasks.frente text NULL CHECK (frente IS NULL OR frente IN ('software','mobile','dados','ia'))` e `tasks.frente_definida_por text NULL CHECK (frente_definida_por IS NULL OR frente_definida_por IN ('ia','gerente'))`.
- Migração **"Migration v13 (2026-11-17): frente da task"**: COMENTADA no fim de `docudata-backend/supabase_schema.sql`, depois do bloco v12, com preflight e rollback no mesmo estilo dos blocos v10–v12.
- Modelo: `gemini-3.5-flash-lite`, chave via `services.gemini_key.get_gemini_api_key()`, mesmo padrão de `services/commit_extraction.py`. Não gravar tokens nem custo (o rastreio de custo de IA foi removido do produto).
- **Deploy seguro antes da migração:** `POST /tasks` NÃO grava `frente` no insert. A gravação fica só no job em segundo plano (com try/except e log) e no override do gerente. Assim, criar e editar task continua funcionando mesmo antes de a v13 rodar.
- A classificação nunca bloqueia nem atrasa a resposta de criação ou edição.
- Task com `frente_definida_por == 'gerente'` nunca é reclassificada pela IA.
- Commits em português no estilo do repo (`feat(frente): ...`), terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Comandos: `cd docudata-backend && .venv/bin/python -m pytest -q tests/<arquivo>`; frontend `cd docudata-frontend && npm test` e `npx tsc --noEmit`.

---

### Task F1: Backend da frente

**Files:**
- Create: `docudata-backend/services/frente.py`
- Modify: `docudata-backend/routers/tasks.py`:
  - `create_task`: injetar `background: BackgroundTasks`; agendar a classificação depois do insert.
  - `patch_task`: quando `_texto_mudou(...)` e a frente não for do gerente, agendar a reclassificação. O campo `frente` vindo do PATCH é o override.
  - `_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL` ganha `"frente"`.
- Modify: `docudata-backend/models/schemas.py`:
  - `TaskUpdate.frente: Optional[Literal["software","mobile","dados","ia"]] = None`.
  - `TaskResponse` ganha `frente: Optional[str] = None` e `frente_definida_por: Optional[str] = None`.
- Modify: `docudata-backend/supabase_schema.sql` (bloco v13 comentado no fim).
- Create: `docudata-backend/scripts/backfill_frente.py`.
- Test: `docudata-backend/tests/test_frente.py`.

**Interfaces:**
- `FRENTES = ("software", "mobile", "dados", "ia")`
- `async def classificar_frente(api_key: str, *, titulo: str, descricao: str | None, checklist: list[dict] | None, projeto_nome: str | None, subarea: str | None) -> str | None`. Devolve uma das `FRENTES`, ou `None` se o modelo devolver algo fora do conjunto.
- `async def atualizar_frente_da_task(task_id: str) -> None`. É a função agendada no `BackgroundTasks`, e o cliente sai de `get_client()`. Ela:
  - lê a task e o projeto (`name`, `subarea`);
  - sai sem fazer nada se `frente_definida_por == 'gerente'`;
  - chama `classificar_frente`;
  - grava `{"frente": f, "frente_definida_por": "ia"}`.

  Qualquer exceção é logada com `_LOG.warning(..., exc_info=True)` e engolida.
- O prompt (system) descreve as quatro frentes com um critério curto cada:
  - **software:** sistema web, API, backend, frontend web, infra e devops;
  - **mobile:** app iOS/Android, React Native, Flutter, publicação em loja;
  - **dados:** ETL, pipeline, modelagem, dashboard/BI, SQL, análise;
  - **ia:** LLM, agentes, machine learning, visão computacional, NLP, prompts.

  Pede a resposta só no schema `{"frente": "<uma das quatro>"}`. O user message traz projeto e subárea como pista e o texto da task (use `services.classificador_regua.texto_da_task`).

- [ ] **Step 1: testes que falham** em `tests/test_frente.py`. Use o `FakeClient` de `tests/fake_supabase.py` e o padrão de autenticação dos testes de `routers/tasks.py` (ex.: `tests/test_nivel_gerente.py`). O teste não pode chamar o Gemini de verdade: faça monkeypatch de `services.frente.classificar_frente`, ou da fábrica do LLM.
  1. `classificar_frente` devolve `None` quando o LLM (mockado) devolve um valor fora de `FRENTES`, e o valor quando ele é válido.
  2. `atualizar_frente_da_task` grava `frente` e `frente_definida_por='ia'`.
  3. `atualizar_frente_da_task` não chama o classificador quando `frente_definida_por=='gerente'`.
  4. `atualizar_frente_da_task` engole exceção do classificador: a task fica igual e nada é levantado.
  5. `POST /tasks` agenda `atualizar_frente_da_task` com o id criado. Com o `TestClient`, as background tasks rodam ao fim da request, então basta mockar `atualizar_frente_da_task` e afirmar que foi chamada com o id. O payload do insert não tem `frente`.
  6. PATCH que muda o título agenda a reclassificação. PATCH que só move de coluna não agenda. PATCH de texto em task com `frente_definida_por=='gerente'` não agenda.
  7. PATCH do gerente com `{"frente": "mobile"}` grava `frente='mobile'` e `frente_definida_por='gerente'`.
  8. PATCH do operacional com `frente` dá 403.
  9. PATCH com `frente` inválida dá 422.
- [ ] **Step 2:** rodar e ver falhar.
- [ ] **Step 3:** implementar.
  - **Agendamento:** em `create_task`, depois de montar a resposta: `background.add_task(atualizar_frente_da_task, criada["id"])`. Em `patch_task`, faça o mesmo quando o texto mudou, o PATCH não trouxe `frente` e a task não tem `frente_definida_por == 'gerente'`.
  - **Override:** em `patch_task`, se `"frente" in data.model_fields_set` e `data.frente` não for nulo, `updates["frente"] = data.frente` e `updates["frente_definida_por"] = "gerente"`.
  - **Assinatura do PATCH:** `mover_task` chama `patch_task` direto. Dê ao parâmetro novo de `patch_task` o default `background: BackgroundTasks = None` e trate `None` (sem agendamento), para não quebrar o `mover_task`.
- [ ] **Step 4: backfill.** `scripts/backfill_frente.py` percorre as tasks com `frente` nula, em páginas (use `ler_tudo` se existir no repo, como em `classificador_aprendizado.py`), e chama `atualizar_frente_da_task` para cada uma, com pausa de 0,5 s.
  - `--aplicar` grava. Sem a flag, só lista quantas seriam classificadas.
  - Carrega o `.env` como os outros scripts de `scripts/`.
- [ ] **Step 5:** bloco v13 comentado no `supabase_schema.sql`. Se `tests/test_pta_nivel_migracoes.py` ou `tests/test_schema_migrations_comentadas.py` verificam que os blocos são só comentários, garanta que o v13 passe neles. Acrescente um teste para o v13 seguindo o padrão do v12.
- [ ] **Step 6:** rodar `tests/test_frente.py` e a suíte completa, que deve ficar verde (último número: 1325 passed).
- [ ] **Step 7:** commit `feat(frente): IA identifica a frente da task (software, mobile, dados, IA) e o gerente pode corrigir`.

### Task F2: Frontend da frente

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`:
  - o tipo da task kanban ganha `frente?: "software" | "mobile" | "dados" | "ia" | null` e `frente_definida_por?: "ia" | "gerente" | null`;
  - a função de PATCH aceita `frente`;
  - exportar `FRENTES = [{ value: "software", label: "Software" }, { value: "mobile", label: "Mobile" }, { value: "dados", label: "Dados" }, { value: "ia", label: "IA" }] as const`, num lugar puro que os testes `.mjs` consigam importar, seguindo o padrão já usado pelos testes de `docudata-frontend/tests/`.
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx`:
  - **Card (`TaskCard`):** um `Chip` com o rótulo da frente quando ela existir, ao lado dos outros chips. Use o mesmo tom neutro dos chips informativos que já existem; não crie cor nova.
  - **`TaskModal`, task existente e cargo diferente de operacional:** um `select` "Frente" com as quatro opções. O valor atual vem selecionado; sem frente, mostra "Identificando…" desabilitado como placeholder. Trocar o valor manda `PATCH { frente }`. Abaixo vai um texto pequeno: "definida pela IA" ou "definida pelo gerente", conforme `frente_definida_por`.
  - **Operacional:** vê só o chip.
- Test: `docudata-frontend/tests/frente.test.mjs`, que valida `FRENTES` (valores e rótulos exatos) seguindo o padrão dos testes existentes.

- [ ] **Step 1:** teste que falha.
- [ ] **Step 2:** implementar.
- [ ] **Step 3:** `npm test` e `npx tsc --noEmit` verdes.
- [ ] **Step 4:** commit `feat(frente): chip da frente no card e correção pelo gerente no modal`.
