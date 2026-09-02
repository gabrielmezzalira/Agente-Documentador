---
slug: wave-4b-task-sugestoes-banner-na-aba-tas
created: 2026-09-02
status: in_progress
---

# Wave 4b — task_sugestoes + banner na aba Tasks

## Objetivo
Após ingerir um documento do tipo "review", fazer match fuzzy entre as tarefas mencionadas no review e as tasks existentes na sprint, criando sugestões na tabela `task_sugestoes`. Exibir banner na aba Tasks para o gerente aceitar/rejeitar cada sugestão.

## Tarefas

### 1. Backend: `on_review_ingested` em `services/task_events.py`
- Adicionar função `on_review_ingested(client, ingestion_id, project_id, sprint_numero, tarefas_from_review)`
- Busca todas as tasks da sprint
- Fuzzy match (difflib.SequenceMatcher, ratio ≥ 0.6 ou substring) tasks vs tarefas do review
- Cria registros em `task_sugestoes` com `acao="mover_para_concluida"` para cada match

### 2. Backend: `models/schemas.py` — `TaskSugestaoResponse`
- Campos: id, task_id, task_titulo, acao, motivo, origem_ingestion_id, aceita, criado_em

### 3. Backend: endpoints sugestoes em `routers/tasks.py`
- `GET /tasks/sugestoes?project_id=...` — lista sugestões pendentes (aceita IS NULL) com task_titulo embutido
- `PATCH /tasks/sugestoes/{sugestao_id}` — body `{"aceita": bool}`; se aceita e acao=mover_para_concluida → atualiza tasks.coluna_kanban

### 4. Backend: hook em `routers/ingest.py`
- Após extração bem-sucedida, se `result["tipo_detectado"] == "review"`:
  - Chama `on_review_ingested(client, ingestion_id, project_id, sprint_numero, tarefas)`

### 5. Frontend: `app/lib/api.ts`
- Tipo `TaskSugestaoResponse`
- `listTaskSugestoes(projectId)` → `GET /tasks/sugestoes?project_id=...`
- `resolveTaskSugestao(sugestaoId, aceita)` → `PATCH /tasks/sugestoes/{id}`

### 6. Frontend: banner em `app/components/TasksKanbanTab.tsx`
- Carrega sugestões pendentes ao montar
- Exibe banner amarelo no topo do kanban quando há sugestões `aceita === null`
- Cada linha: task_titulo + ação + botões "Aceitar" / "Ignorar"
- Após aceitar/rejeitar, atualiza lista local
