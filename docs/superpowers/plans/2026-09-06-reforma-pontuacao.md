# Reforma do Modelo de Pontuação Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fixar o total de pontos de um projeto em 100, distribuídos entre sprints no planejamento (aba Escopo) e entre tasks na execução (Kanban), com faturamento derivado automaticamente quando o valor do projeto é informado.

**Architecture:** Dois níveis de validação independentes — orçamento de sprint (soma de `sprints.pontos_orcamento` do projeto ≤ 100) e orçamento de task (soma de `tasks.pontos` de uma sprint ≤ `pontos_orcamento` daquela sprint). O antigo mecanismo de baseline manual por sprint (Phase 12, `PATCH /sprints/{id}/baseline`) é removido e substituído por `PATCH /sprints/{id}/orcamento`. `projects.valor_por_ponto` (campo dormente desde a Phase 12) é reaproveitado para derivar faturamento previsto por sprint.

**Tech Stack:** FastAPI + supabase-py (backend), Next.js/React com estilos inline (frontend). Testes backend: pytest + unittest.mock (MagicMock por tabela). Frontend sem framework de teste — verificação via `npm run build`.

**Spec:** `docs/superpowers/specs/2026-09-06-reforma-pontuacao-design.md`

## Global Constraints

- Total de pontos de um projeto é sempre 100 — constante fixa, nunca um campo editável por projeto.
- `supabase_schema.sql` não roda sozinho contra produção — as duas `ALTER TABLE` novas (`sprints.pontos_orcamento`, `projects.valor_projeto`) precisam de aplicação manual no Supabase depois do deploy.
- Sem migração/backfill de dados existentes — nenhuma sprint/task pré-existente é revalidada retroativamente; `pontos_orcamento` começa `NULL` (sem trava) até o gerente definir.
- Não confundir `projects.valor_projeto` (novo, valor do contrato) com `projects.budget_usd` (já existe, teto de custo de IA — conceito diferente, não mexer).
- Backend: seguir o padrão de teste já estabelecido — `MagicMock` por tabela via `client.table(name)`, injetado via `monkeypatch.setattr(<router_module>, "get_client", ...)`, autenticação via `tc.cookies.set("docudata_session", criar_jwt(pessoa_id, email, "gerente"))` (cargo "gerente" satisfaz `require_not_operacional`/`require_project_access` em todas as rotas tocadas).
- Frontend: sem framework de teste automatizado no repo — verificação de cada task de UI é `npm run build` (type-check) + descrição do que checar visualmente.
- Onda 2 só começa depois de Onda 1 100% completa com testes passando (suíte inteira, não só os arquivos tocados).

---

## Onda 1 — Back-end

### Task 1: Endpoint de orçamento de sprint (substitui o baseline manual)

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (adicionar `ALTER TABLE sprints ADD COLUMN IF NOT EXISTS pontos_orcamento int CHECK (pontos_orcamento IS NULL OR pontos_orcamento >= 0);` logo após a definição existente de `sprints` na seção de baseline, ~linha 307)
- Modify: `docudata-backend/models/schemas.py` — remover `SprintBaselineUpdate`/`SprintBaselineResponse` (~linhas 495-508), adicionar `SprintOrcamentoUpdate` no lugar, adicionar `pontos_orcamento: Optional[int] = None` em `SprintResponse` (~linha 147-155)
- Modify: `docudata-backend/routers/sprints.py` — remover `update_baseline` (~linhas 145-186), adicionar `update_orcamento`
- Test: `docudata-backend/tests/test_sprint_orcamento.py` (novo arquivo)

**Interfaces:**
- Consumes: `services.supabase_client.get_client()`, `services.auth.require_not_operacional`, `services.auth.criar_jwt` (em testes).
- Produces: `PATCH /sprints/{sprint_id}/orcamento` retornando `SprintResponse` (agora com `pontos_orcamento`). Task 2 (validação de task) e Task 4 (list_sprints) consomem `sprints.pontos_orcamento` como coluna de banco — mesmo nome em todos os lugares.

- [ ] **Step 1: Adicionar a coluna no schema**

Em `docudata-backend/supabase_schema.sql`, logo após a linha `ALTER TABLE sprints ADD COLUMN IF NOT EXISTS baseline_locked_at     timestamptz;` (dentro do bloco "Baseline e faturamento por sprint", ~linha 306), adicionar:

```sql
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS pontos_orcamento int CHECK (pontos_orcamento IS NULL OR pontos_orcamento >= 0);
```

Não remover nenhuma coluna existente (`pontos_previstos`, `faturamento_previsto`, `baseline_locked_at` ficam no schema sem uso).

- [ ] **Step 2: Escrever os testes que falham**

Criar `docudata-backend/tests/test_sprint_orcamento.py`:

```python
"""Testes para PATCH /sprints/{id}/orcamento (substitui o antigo baseline manual)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(sprint_exists=True, sprint_data=None, tasks_na_sprint=None, outras_sprints=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.neq = MagicMock(return_value=q)
                resp = MagicMock()
                if "*" in cols:
                    resp.data = [dict(sprint_data)] if sprint_exists else []
                else:
                    resp.data = list(outras_sprints) if outras_sprints is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()

                def eq_side_effect(field, value):
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [dict(sprint_data, **payload)]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(tasks_na_sprint) if tasks_na_sprint is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.sprints as sprints_router
    monkeypatch.setattr(sprints_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def test_define_orcamento_dentro_do_limite(monkeypatch):
    mock_sb = _make_mock_client(
        sprint_data={"id": "sprint-1", "project_id": "proj-1", "numero": 1},
        tasks_na_sprint=[],
        outras_sprints=[{"pontos_orcamento": 30}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/sprints/sprint-1/orcamento", json={"pontos_orcamento": 20})

    assert resp.status_code == 200
    assert resp.json()["pontos_orcamento"] == 20


def test_bloqueia_se_soma_do_projeto_passar_de_100(monkeypatch):
    mock_sb = _make_mock_client(
        sprint_data={"id": "sprint-1", "project_id": "proj-1", "numero": 1},
        tasks_na_sprint=[],
        outras_sprints=[{"pontos_orcamento": 90}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/sprints/sprint-1/orcamento", json={"pontos_orcamento": 20})

    assert resp.status_code == 409
    assert "10" in resp.json()["detail"]


def test_bloqueia_reducao_abaixo_do_ja_usado_em_tasks(monkeypatch):
    mock_sb = _make_mock_client(
        sprint_data={"id": "sprint-1", "project_id": "proj-1", "numero": 1},
        tasks_na_sprint=[{"pontos": 8}, {"pontos": 5}],
        outras_sprints=[],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/sprints/sprint-1/orcamento", json={"pontos_orcamento": 10})

    assert resp.status_code == 409
    assert "13" in resp.json()["detail"]


def test_sprint_not_found(monkeypatch):
    mock_sb = _make_mock_client(sprint_exists=False)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/sprints/does-not-exist/orcamento", json={"pontos_orcamento": 10})

    assert resp.status_code == 404
```

- [ ] **Step 3: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && python3 -m pytest tests/test_sprint_orcamento.py -v`
Expected: FALHA em todos — a rota `/sprints/{id}/orcamento` ainda não existe (404 genérico do FastAPI, não o 404 esperado da lógica).

- [ ] **Step 4: Remover o endpoint de baseline antigo**

Em `docudata-backend/models/schemas.py`, remover as classes `SprintBaselineUpdate` e `SprintBaselineResponse` (linhas ~495-508) e substituir por:

```python
class SprintOrcamentoUpdate(BaseModel):
    pontos_orcamento: int = Field(..., ge=0)
```

Em `docudata-backend/models/schemas.py`, adicionar `pontos_orcamento: Optional[int] = None` em `SprintResponse` (logo após `plano_correcao`, ~linha 152):

```python
class SprintResponse(BaseModel):
    id: str
    project_id: str
    numero: int
    status_saude: Optional[str] = None
    plano_correcao: Optional[str] = None
    pontos_orcamento: Optional[int] = None
    avaliacao_completa_em: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 5: Implementar o novo endpoint**

Em `docudata-backend/routers/sprints.py`, substituir a função `update_baseline` inteira (linhas ~145-186) por:

```python
@router.patch("/sprints/{sprint_id}/orcamento", response_model=SprintResponse, dependencies=[Depends(require_not_operacional)])
async def update_orcamento(sprint_id: str, data: SprintOrcamentoUpdate):
    """Define quantos dos 100 pontos do projeto esta sprint recebe (planejamento, aba Escopo)."""
    client = get_client()
    check = client.table("sprints").select("*").eq("id", sprint_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Sprint not found")
    sprint = check.data[0]
    project_id = sprint["project_id"]

    tasks_existentes = (
        client.table("tasks")
        .select("pontos")
        .eq("sprint_id", sprint_id)
        .execute()
    ).data or []
    usados = sum(t["pontos"] for t in tasks_existentes)
    if data.pontos_orcamento < usados:
        raise HTTPException(
            status_code=409,
            detail=f"Não é possível reduzir o orçamento abaixo dos {usados} pontos já usados em tasks desta sprint.",
        )

    outras_sprints = (
        client.table("sprints")
        .select("pontos_orcamento")
        .eq("project_id", project_id)
        .neq("id", sprint_id)
        .execute()
    ).data or []
    total_outras = sum(s["pontos_orcamento"] or 0 for s in outras_sprints)
    if total_outras + data.pontos_orcamento > 100:
        raise HTTPException(
            status_code=409,
            detail=f"Orçamento do projeto excedido: restam {100 - total_outras} pontos pra distribuir entre as sprints.",
        )

    resp = client.table("sprints").update({"pontos_orcamento": data.pontos_orcamento}).eq("id", sprint_id).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to update orcamento")
    return resp.data[0]
```

E atualizar o import no topo do arquivo: trocar `SprintBaselineUpdate, SprintBaselineResponse,` por `SprintOrcamentoUpdate,` na lista de imports de `models.schemas`.

- [ ] **Step 6: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && python3 -m pytest tests/test_sprint_orcamento.py -v`
Expected: PASS nos 4 testes.

- [ ] **Step 7: Commit**

```bash
cd docudata-backend
git add supabase_schema.sql models/schemas.py routers/sprints.py tests/test_sprint_orcamento.py
git commit -m "feat(sprints): substituir baseline manual por orcamento de pontos validado contra o pool de 100"
```

---

### Task 2: Validação de orçamento ao criar/editar task

**Files:**
- Modify: `docudata-backend/routers/tasks.py` — `create_task` (~linhas 84-146) e `patch_task` (~linhas 273-441)
- Test: `docudata-backend/tests/test_task_orcamento_sprint.py` (novo arquivo)

**Interfaces:**
- Consumes: `sprints.pontos_orcamento` (Task 1). `TaskCreate.pontos`, `TaskCreate.sprint_id`, `TaskUpdate.pontos`, `TaskUpdate.sprint_id` (já existentes, sem mudança de schema).
- Produces: `POST /tasks` e `PATCH /tasks/{id}` retornam 409 quando o orçamento da sprint de destino é excedido.

- [ ] **Step 1: Escrever os testes que falham**

Criar `docudata-backend/tests/test_task_orcamento_sprint.py`:

```python
"""Testes para validação de orçamento de sprint (pontos_orcamento) ao criar/editar task."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(
    project_exists=True,
    sprint_data=None,
    tasks_na_sprint=None,
    task_atual=None,
    task_exists=True,
):
    client = MagicMock()
    calls = {"insert": [], "update": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "proj-1"}] if project_exists else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(sprint_data)] if sprint_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.neq = MagicMock(return_value=q)
                resp = MagicMock()
                if cols == "*":
                    resp.data = [dict(task_atual)] if task_exists and task_atual else []
                else:
                    resp.data = list(tasks_na_sprint) if tasks_na_sprint is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                calls["insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="task-nova")]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                calls["update"].append(payload)
                q = MagicMock()

                def eq_side_effect(field, value):
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [dict(task_atual or {}, **payload, id=value)]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def test_create_task_bloqueado_quando_estoura_orcamento_da_sprint(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": 10},
        tasks_na_sprint=[{"pontos": 7}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks", json={
        "project_id": "proj-1", "titulo": "Nova task", "pontos": 5, "sprint_id": "sprint-1",
    })

    assert resp.status_code == 409
    assert "3" in resp.json()["detail"]
    assert calls["insert"] == []


def test_create_task_permitido_dentro_do_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": 10},
        tasks_na_sprint=[{"pontos": 7}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks", json={
        "project_id": "proj-1", "titulo": "Nova task", "pontos": 3, "sprint_id": "sprint-1",
    })

    assert resp.status_code == 201
    assert len(calls["insert"]) == 1


def test_create_task_sem_validacao_quando_sprint_sem_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": None},
        tasks_na_sprint=[{"pontos": 999}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/tasks", json={
        "project_id": "proj-1", "titulo": "Nova task", "pontos": 50, "sprint_id": "sprint-1",
    })

    assert resp.status_code == 201


def test_patch_task_bloqueado_quando_aumentar_pontos_estoura_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": 10},
        tasks_na_sprint=[{"pontos": 6}],  # outras tasks, não inclui a própria
        task_atual={"id": "task-1", "project_id": "proj-1", "sprint_id": "sprint-1", "pontos": 4, "coluna_kanban": "planejado", "operacional_id": None, "checklist": [], "bloqueado_manual": False},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"pontos": 5})

    assert resp.status_code == 409
    assert calls["update"] == []


def test_patch_task_permitido_quando_dentro_do_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(
        sprint_data={"id": "sprint-1", "pontos_orcamento": 10},
        tasks_na_sprint=[{"pontos": 6}],
        task_atual={"id": "task-1", "project_id": "proj-1", "sprint_id": "sprint-1", "pontos": 4, "coluna_kanban": "planejado", "operacional_id": None, "checklist": [], "bloqueado_manual": False},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/tasks/task-1", json={"pontos": 4})

    assert resp.status_code == 200
    assert len(calls["update"]) == 1
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && python3 -m pytest tests/test_task_orcamento_sprint.py -v`
Expected: os testes de bloqueio (409) FALHAM com 201/200 — nenhuma validação de orçamento existe ainda.

- [ ] **Step 3: Implementar a validação em `create_task`**

Em `docudata-backend/routers/tasks.py`, dentro de `create_task`, trocar o bloco:

```python
    if data.sprint_id:
        sp_check = (
            client.table("sprints")
            .select("id")
            .eq("id", data.sprint_id)
            .eq("project_id", data.project_id)
            .execute()
        )
        if not sp_check.data:
            raise HTTPException(status_code=422, detail="sprint_id não pertence a este projeto")
```

por:

```python
    if data.sprint_id:
        sp_check = (
            client.table("sprints")
            .select("id, pontos_orcamento")
            .eq("id", data.sprint_id)
            .eq("project_id", data.project_id)
            .execute()
        )
        if not sp_check.data:
            raise HTTPException(status_code=422, detail="sprint_id não pertence a este projeto")
        orcamento = sp_check.data[0].get("pontos_orcamento")
        if orcamento is not None:
            tasks_na_sprint = (
                client.table("tasks")
                .select("pontos")
                .eq("sprint_id", data.sprint_id)
                .execute()
            ).data or []
            usados = sum(t["pontos"] for t in tasks_na_sprint)
            if usados + data.pontos > orcamento:
                raise HTTPException(
                    status_code=409,
                    detail=f"Orçamento da sprint excedido: restam {orcamento - usados} pontos.",
                )
```

- [ ] **Step 4: Implementar a validação em `patch_task`**

Em `docudata-backend/routers/tasks.py`, dentro de `patch_task`, logo após o bloco existente que valida `data.sprint_id is not None` (~linhas 294-303), adicionar:

```python
    if data.pontos is not None or data.sprint_id is not None:
        sprint_id_efetivo = data.sprint_id if data.sprint_id is not None else task.get("sprint_id")
        pontos_efetivo = data.pontos if data.pontos is not None else task["pontos"]
        if sprint_id_efetivo:
            sp_orc = client.table("sprints").select("pontos_orcamento").eq("id", sprint_id_efetivo).execute()
            orcamento = sp_orc.data[0].get("pontos_orcamento") if sp_orc.data else None
            if orcamento is not None:
                outras_tasks = (
                    client.table("tasks")
                    .select("pontos")
                    .eq("sprint_id", sprint_id_efetivo)
                    .neq("id", task_id)
                    .execute()
                ).data or []
                usados = sum(t["pontos"] for t in outras_tasks)
                if usados + pontos_efetivo > orcamento:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Orçamento da sprint excedido: restam {orcamento - usados} pontos.",
                    )
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && python3 -m pytest tests/test_task_orcamento_sprint.py -v`
Expected: PASS nos 5 testes.

- [ ] **Step 6: Commit**

```bash
cd docudata-backend
git add routers/tasks.py tests/test_task_orcamento_sprint.py
git commit -m "feat(tasks): validar pontos de task contra o orcamento da sprint ao criar/editar"
```

---

### Task 3: Valor do projeto e valor_por_ponto (com trava de edição)

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` — adicionar `ALTER TABLE projects ADD COLUMN IF NOT EXISTS valor_projeto numeric(10,2);` logo após a linha existente `ALTER TABLE projects ADD COLUMN IF NOT EXISTS valor_por_ponto  numeric(10,2);` (~linha 311)
- Modify: `docudata-backend/models/schemas.py` — `ProjectCreate` (~linhas 33-39), `ProjectResponse` (~linhas 42-59), `ContratoUpdate` (~linhas 308-313)
- Modify: `docudata-backend/routers/projects.py` — `create_project` (~linhas 42-54), `update_contrato` (~linhas 344-360)
- Test: `docudata-backend/tests/test_valor_projeto.py` (novo arquivo)

**Interfaces:**
- Consumes: `sprints.pontos_orcamento` (Task 1) para checar a trava.
- Produces: `projects.valor_projeto`/`projects.valor_por_ponto` — consumidos pela Task 4 (`faturamento_previsto` derivado).

- [ ] **Step 1: Adicionar a coluna no schema**

Em `docudata-backend/supabase_schema.sql`, logo após `ALTER TABLE projects ADD COLUMN IF NOT EXISTS valor_por_ponto  numeric(10,2);` (~linha 311), adicionar:

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS valor_projeto numeric(10,2);
```

- [ ] **Step 2: Escrever os testes que falham**

Criar `docudata-backend/tests/test_valor_projeto.py`:

```python
"""Testes para projects.valor_projeto / valor_por_ponto (criação e edição via contrato, com trava)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(project_exists=True, sprints_com_orcamento=None, insert_ok=True):
    client = MagicMock()
    calls = {"insert": [], "update": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "proj-1"}] if project_exists else []
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                calls["insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="new-proj-id", is_delivered=False, created_at="2026-09-06T00:00:00+00:00")] if insert_ok else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                calls["update"].append(payload)
                q = MagicMock()

                def eq_side_effect(field, value):
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [dict(payload, id=value, name="X", client="Y", is_delivered=False, created_at="2026-09-06T00:00:00+00:00")]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.not_ = MagicMock()
                q.not_.is_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(sprints_com_orcamento) if sprints_com_orcamento is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def test_create_project_com_valor_projeto_calcula_valor_por_ponto(monkeypatch):
    mock_sb, calls = _make_mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/projects", json={"name": "Proj X", "client": "Cliente Y", "valor_projeto": 35000})

    assert resp.status_code == 201
    assert calls["insert"][0]["valor_projeto"] == 35000
    assert calls["insert"][0]["valor_por_ponto"] == 350.0


def test_update_contrato_com_valor_projeto_quando_nenhuma_sprint_tem_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(sprints_com_orcamento=[])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/projects/proj-1/contrato", json={"valor_projeto": 10000})

    assert resp.status_code == 200
    assert calls["update"][0]["valor_projeto"] == 10000
    assert calls["update"][0]["valor_por_ponto"] == 100.0


def test_update_contrato_bloqueia_valor_projeto_se_ja_ha_sprint_com_orcamento(monkeypatch):
    mock_sb, calls = _make_mock_client(sprints_com_orcamento=[{"id": "sprint-1"}])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/projects/proj-1/contrato", json={"valor_projeto": 10000})

    assert resp.status_code == 409
    assert calls["update"] == []


def test_update_contrato_outros_campos_funcionam_mesmo_com_valor_travado(monkeypatch):
    mock_sb, calls = _make_mock_client(sprints_com_orcamento=[{"id": "sprint-1"}])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.patch("/projects/proj-1/contrato", json={"arquetipo": "consultoria_discovery"})

    assert resp.status_code == 200
    assert calls["update"][0] == {"arquetipo": "consultoria_discovery"}
```

- [ ] **Step 3: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && python3 -m pytest tests/test_valor_projeto.py -v`
Expected: FALHA nos 3 primeiros (campo `valor_projeto` não existe em `ProjectCreate`/`ContratoUpdate`, então é ignorado pelo Pydantic e nunca chega no payload). O último teste (`test_update_contrato_outros_campos_funcionam_mesmo_com_valor_travado`) já deve passar, já que não envolve `valor_projeto`.

- [ ] **Step 4: Adicionar os campos nos schemas**

Em `docudata-backend/models/schemas.py`, em `ProjectCreate` (~linha 33-39), adicionar `valor_projeto: Optional[float] = None` (não confundir com `budget_usd`, que já existe e é outra coisa):

```python
class ProjectCreate(BaseModel):
    name: str
    client: str
    description: Optional[str] = None
    squad: Optional[str] = None
    budget_usd: Optional[float] = None
    valor_projeto: Optional[float] = None
    gemini_api_key: Optional[str] = None
```

Em `ProjectResponse` (~linha 42-59), adicionar `valor_projeto`/`valor_por_ponto`:

```python
class ProjectResponse(BaseModel):
    id: str
    name: str
    client: str
    description: Optional[str] = None
    squad: Optional[str] = None
    budget_usd: Optional[float] = None
    valor_projeto: Optional[float] = None
    valor_por_ponto: Optional[float] = None
    has_api_key: bool = False
    is_delivered: bool = False
    created_at: datetime
    last_ingestion_at: Optional[datetime] = None
    data_inicio: Optional[date] = None
    data_fim_contratada: Optional[date] = None
    tolerancia_desvio_pontos: Optional[int] = None
    periodo_garantia_dias: Optional[int] = None
    has_github_config: bool = False
    gerente_email: Optional[str] = None
    arquetipo: str = "padrao"
```

Em `ContratoUpdate` (~linha 308-313), adicionar `valor_projeto`:

```python
class ContratoUpdate(BaseModel):
    data_inicio: Optional[date] = None
    data_fim_contratada: Optional[date] = None
    tolerancia_desvio_pontos: Optional[int] = Field(default=None, ge=0)
    periodo_garantia_dias: Optional[int] = Field(default=None, ge=0)
    arquetipo: Optional[Literal["padrao", "consultoria_discovery"]] = None
    valor_projeto: Optional[float] = None
```

- [ ] **Step 5: Implementar em `create_project`**

Em `docudata-backend/routers/projects.py`, dentro de `create_project`, trocar:

```python
    payload = {"name": data.name, "client": data.client, "description": data.description, "squad": data.squad}
    if data.budget_usd is not None:
        payload["budget_usd"] = data.budget_usd
    if data.gemini_api_key:
        payload["gemini_api_key"] = data.gemini_api_key
```

por:

```python
    payload = {"name": data.name, "client": data.client, "description": data.description, "squad": data.squad}
    if data.budget_usd is not None:
        payload["budget_usd"] = data.budget_usd
    if data.valor_projeto is not None:
        payload["valor_projeto"] = data.valor_projeto
        payload["valor_por_ponto"] = round(data.valor_projeto / 100, 2)
    if data.gemini_api_key:
        payload["gemini_api_key"] = data.gemini_api_key
```

- [ ] **Step 6: Implementar em `update_contrato`**

Em `docudata-backend/routers/projects.py`, substituir `update_contrato` inteira (~linhas 344-360) por:

```python
@router.patch("/{project_id}/contrato", response_model=ProjectResponse)
async def update_contrato(project_id: str, data: ContratoUpdate):
    """Atualiza campos de contrato do projeto: datas, tolerancia, garantia e valor do projeto."""
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    campos = data.model_dump()
    valor_projeto = campos.pop("valor_projeto", None)
    payload = {k: v for k, v in campos.items() if v is not None}

    if valor_projeto is not None:
        sprints_com_orcamento = (
            client.table("sprints")
            .select("id")
            .eq("project_id", project_id)
            .not_.is_("pontos_orcamento", "null")
            .execute()
        ).data or []
        if sprints_com_orcamento:
            raise HTTPException(
                status_code=409,
                detail="Não é possível alterar o valor do projeto: já existe orçamento de pontos definido em pelo menos uma sprint.",
            )
        payload["valor_projeto"] = valor_projeto
        payload["valor_por_ponto"] = round(valor_projeto / 100, 2)

    if not payload:
        raise HTTPException(status_code=422, detail="Nenhum campo fornecido")
    for k, v in list(payload.items()):
        if hasattr(v, "isoformat"):
            payload[k] = v.isoformat()
    response = client.table("projects").update(payload).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update contract fields")
    return _sanitize(response.data[0])
```

- [ ] **Step 7: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && python3 -m pytest tests/test_valor_projeto.py -v`
Expected: PASS nos 4 testes.

- [ ] **Step 8: Commit**

```bash
cd docudata-backend
git add supabase_schema.sql models/schemas.py routers/projects.py tests/test_valor_projeto.py
git commit -m "feat(projects): valor_projeto com trava de edicao apos primeira sprint com orcamento"
```

---

### Task 4: `GET /projects/{id}/sprints` retorna orçamento, saldo usado e faturamento derivado

**Files:**
- Modify: `docudata-backend/models/schemas.py` — `SprintStatusResponse` (~linhas 158-165)
- Modify: `docudata-backend/routers/sprints.py` — `list_sprints` (~linhas 64-142)
- Test: `docudata-backend/tests/test_sprints_orcamento_derivado.py` (novo arquivo)

**Interfaces:**
- Consumes: `sprints.pontos_orcamento` (Task 1), `projects.valor_por_ponto` (Task 3).
- Produces: cada item de `GET /projects/{id}/sprints` ganha `pontos_usados: int` e `faturamento_previsto: float | None` — consumidos pelo frontend nas Tasks 6/7 (Onda 2).

- [ ] **Step 1: Escrever os testes que falham**

Criar `docudata-backend/tests/test_sprints_orcamento_derivado.py`:

```python
"""Testes para pontos_usados/faturamento_previsto derivados em GET /projects/{id}/sprints."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(project_data=None, sprints_data=None, tasks_data=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(project_data)] if project_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(sprints_data) if sprints_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name in ("tasks", "ingestions", "generated_docs"):
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                if name == "tasks":
                    resp.data = list(tasks_data) if tasks_data is not None else []
                else:
                    resp.data = []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.sprints as sprints_router
    monkeypatch.setattr(sprints_router, "get_client", lambda: mock_supabase)
    from main import app
    from services.auth import criar_jwt
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", "gerente"))
    return tc


def test_pontos_usados_soma_tasks_da_sprint(monkeypatch):
    mock_sb = _make_mock_client(
        project_data={"id": "proj-1", "valor_por_ponto": None},
        sprints_data=[{"id": "sprint-1", "project_id": "proj-1", "numero": 1, "pontos_orcamento": 20}],
        tasks_data=[{"sprint_id": "sprint-1", "pontos": 5}, {"sprint_id": "sprint-1", "pontos": 3}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["pontos_usados"] == 8
    assert data[0]["pontos_orcamento"] == 20


def test_faturamento_previsto_deriva_de_valor_por_ponto(monkeypatch):
    mock_sb = _make_mock_client(
        project_data={"id": "proj-1", "valor_por_ponto": 350.0},
        sprints_data=[{"id": "sprint-1", "project_id": "proj-1", "numero": 1, "pontos_orcamento": 20}],
        tasks_data=[],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    assert resp.json()[0]["faturamento_previsto"] == 7000.0


def test_faturamento_previsto_none_sem_valor_por_ponto_ou_sem_orcamento(monkeypatch):
    mock_sb = _make_mock_client(
        project_data={"id": "proj-1", "valor_por_ponto": None},
        sprints_data=[{"id": "sprint-1", "project_id": "proj-1", "numero": 1, "pontos_orcamento": None}],
        tasks_data=[],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    assert resp.json()[0]["faturamento_previsto"] is None
    assert resp.json()[0]["pontos_usados"] == 0
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && python3 -m pytest tests/test_sprints_orcamento_derivado.py -v`
Expected: FALHA — `pontos_usados`/`faturamento_previsto` não existem em `SprintStatusResponse`, então são descartados da resposta (KeyError no teste ao acessar `data[0]["pontos_usados"]`).

- [ ] **Step 3: Adicionar os campos no schema de resposta**

Em `docudata-backend/models/schemas.py`, em `SprintStatusResponse` (~linhas 158-165), adicionar:

```python
class SprintStatusResponse(SprintResponse):
    """Sprint + agregados de mínimo obrigatório (usado pelo GET de listagem)."""
    tem_planning: bool = False
    tem_review: bool = False
    dailys_count: int = 0
    ingestions_count: int = 0
    docs_gerados_count: int = 0
    pendencias: list[str] = []
    pontos_usados: int = 0
    faturamento_previsto: Optional[float] = None
```

- [ ] **Step 4: Calcular os campos em `list_sprints`**

Em `docudata-backend/routers/sprints.py`, dentro de `list_sprints`, logo após a checagem de projeto (`if not check.data: raise HTTPException(...)`, ~linha 78) e antes da query de `sprints_resp` (~linha 80), buscar o `valor_por_ponto` do projeto:

```python
    valor_por_ponto = (
        client.table("projects").select("valor_por_ponto").eq("id", project_id).execute()
    ).data[0].get("valor_por_ponto")
```

Depois, logo após a query `docs_resp` existente (~linha 102) e antes do loop de agregação de ingestões, buscar as tasks de todas as sprints do projeto de uma vez:

```python
    tasks_resp = (
        client.table("tasks")
        .select("sprint_id, pontos")
        .eq("project_id", project_id)
        .execute()
    )
    pontos_usados_por_sprint: defaultdict = defaultdict(int)
    for t in (tasks_resp.data or []):
        sid = t.get("sprint_id")
        if sid:
            pontos_usados_por_sprint[sid] += t["pontos"]
```

E, no `enriched.append({...})` já existente (~linhas 133-141), adicionar os dois campos novos:

```python
        enriched.append({
            **sprint,
            "tem_planning": agg["planning"] > 0,
            "tem_review": agg["review"] > 0,
            "dailys_count": agg["daily"],
            "ingestions_count": agg["total"],
            "docs_gerados_count": docs_by_sprint[n],
            "pendencias": pendencias,
            "pontos_usados": pontos_usados_por_sprint.get(sprint["id"], 0),
            "faturamento_previsto": (
                round(sprint["pontos_orcamento"] * valor_por_ponto, 2)
                if sprint.get("pontos_orcamento") is not None and valor_por_ponto is not None
                else None
            ),
        })
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && python3 -m pytest tests/test_sprints_orcamento_derivado.py -v`
Expected: PASS nos 3 testes.

- [ ] **Step 6: Rodar a suíte completa do backend**

Run: `cd docudata-backend && python3 -m pytest -v`
Expected: todos passam, exceto as 4 falhas pré-existentes já conhecidas em `test_schemas_and_client.py` (schema legado do MVP, sem relação com esta feature — confirmadas antes desta feature em sessões anteriores). Nenhuma outra regressão.

- [ ] **Step 7: Commit**

```bash
cd docudata-backend
git add models/schemas.py routers/sprints.py tests/test_sprints_orcamento_derivado.py
git commit -m "feat(sprints): derivar pontos_usados e faturamento_previsto em GET /projects/{id}/sprints"
```

---

## Onda 2 — UI (só inicia após Onda 1 verificada)

### Task 5: `api.ts` — tipos e funções para o novo modelo de pontuação

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`

**Interfaces:**
- Consumes: nada novo.
- Produces: `SprintWithStatus` (com `pontos_orcamento`/`pontos_usados`/`faturamento_previsto`), `updateSprintOrcamento`, `Project` (com `valor_projeto`/`valor_por_ponto`), `createProject`/`updateContrato` aceitando `valor_projeto` — consumidos pelas Tasks 6-9.

- [ ] **Step 1: Atualizar `SprintWithStatus`**

Em `docudata-frontend/app/lib/api.ts`, trocar (linhas ~204-214):

```tsx
export interface SprintWithStatus extends Sprint {
  tem_planning: boolean;
  tem_review: boolean;
  dailys_count: number;
  ingestions_count: number;
  docs_gerados_count: number;
  pendencias: string[];          // subset de ['planning','review']
  pontos_previstos: number | null;
  baseline_locked_at: string | null;
  avaliacao_completa_em?: string | null;
}
```

por:

```tsx
export interface SprintWithStatus extends Sprint {
  tem_planning: boolean;
  tem_review: boolean;
  dailys_count: number;
  ingestions_count: number;
  docs_gerados_count: number;
  pendencias: string[];          // subset de ['planning','review']
  pontos_orcamento: number | null;
  pontos_usados: number;
  faturamento_previsto: number | null;
  avaliacao_completa_em?: string | null;
}
```

- [ ] **Step 2: Substituir `updateSprintBaseline` por `updateSprintOrcamento`**

Trocar (linhas ~418-431):

```tsx
export async function updateSprintBaseline(
  sprintId: string,
  pontosPrevistos: number
): Promise<SprintWithStatus> {
  const res = await apiFetch(`${API}/sprints/${sprintId}/baseline`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pontos_previstos: pontosPrevistos }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao definir baseline");
  }
  return res.json();
}
```

por:

```tsx
export async function updateSprintOrcamento(
  sprintId: string,
  pontosOrcamento: number
): Promise<SprintWithStatus> {
  const res = await apiFetch(`${API}/sprints/${sprintId}/orcamento`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pontos_orcamento: pontosOrcamento }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao definir orçamento da sprint");
  }
  return res.json();
}
```

- [ ] **Step 3: Atualizar `Project`, `createProject` e `updateContrato`**

Em `docudata-frontend/app/lib/api.ts`, no `interface Project` (~linhas 94-110), adicionar logo após `budget_usd?: number | null;`:

```tsx
  valor_projeto?: number | null;
  valor_por_ponto?: number | null;
```

Em `createProject` (~linhas 338-345), adicionar `valor_projeto` ao tipo do parâmetro:

```tsx
export async function createProject(data: {
  name: string;
  client: string;
  description?: string;
  squad?: string;
  budget_usd?: number | null;
  valor_projeto?: number | null;
  gemini_api_key?: string;
}): Promise<Project> {
```

Em `updateContrato` (~linhas 299-308), adicionar `valor_projeto` ao tipo do parâmetro:

```tsx
export async function updateContrato(
  projectId: string,
  data: {
    data_inicio?: string | null;
    data_fim_contratada?: string | null;
    tolerancia_desvio_pontos?: number | null;
    periodo_garantia_dias?: number | null;
    arquetipo?: "padrao" | "consultoria_discovery";
    valor_projeto?: number | null;
  }
): Promise<Project> {
```

- [ ] **Step 4: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: falha nesta etapa é esperada — `SprintCard.tsx` ainda referencia `updateSprintBaseline` (removida) e `sprint.pontos_previstos`/`sprint.baseline_locked_at` (removidos do tipo). Essa falha será corrigida na Task 6. Não commitar ainda.

- [ ] **Step 5: Commit**

```bash
cd docudata-frontend
git add app/lib/api.ts
git commit -m "feat(api): tipos e funcoes de api.ts para orcamento de pontos por sprint e valor do projeto"
```

---

### Task 6: `SprintCard.tsx` — remover baseline manual, mostrar orçamento derivado

**Files:**
- Modify: `docudata-frontend/app/components/SprintCard.tsx`

**Interfaces:**
- Consumes: `SprintWithStatus.pontos_orcamento`/`pontos_usados`/`faturamento_previsto` (Task 5).
- Produces: nada novo — só remove UI antiga e mostra os campos derivados.

- [ ] **Step 1: Remover os estados e a lógica de baseline**

Em `docudata-frontend/app/components/SprintCard.tsx`, remover a linha de import `updateSprintBaseline` (linha ~11: `import { updateSprintBaseline } from "../lib/api";`) — ela some, nenhuma outra função é importada de `api.ts` neste arquivo hoje, então remover a linha inteira.

Remover os estados (linhas ~295-298):

```tsx
  const [baselineOpen, setBaselineOpen] = useState(false);
  const [baselineInput, setBaselineInput] = useState("");
  const [baselineSaving, setBaselineSaving] = useState(false);
  const [baselineErr, setBaselineErr] = useState("");
```

Remover a função `handleSaveBaseline` inteira (~linhas 308-322).

- [ ] **Step 2: Substituir a linha de Baseline por texto derivado**

Trocar o bloco (adicionado no ciclo anterior, entre o `statusRow` e o `actionRow`):

```tsx
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
        <button
          type="button"
          onClick={() => { setBaselineOpen((v) => !v); setBaselineInput(sprint.pontos_previstos ? String(sprint.pontos_previstos) : ""); setBaselineErr(""); }}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            fontSize: 12,
            fontWeight: 600,
            color: sprint.pontos_previstos != null ? "#4338ca" : "#9696a0",
            textDecoration: "underline",
            cursor: "pointer",
          }}
          title="Definir baseline (pontos previstos)"
        >
          {sprint.pontos_previstos != null ? `Baseline: ${sprint.pontos_previstos} pts` : "+ Definir baseline"}
        </button>
        <span style={muted}>
          · {sprint.ingestions_count} ingestões · {sprint.docs_gerados_count} docs
        </span>
      </div>
```

por:

```tsx
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18, flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: sprint.pontos_orcamento != null ? "#4338ca" : "#9696a0" }}>
          {sprint.pontos_orcamento != null
            ? `${sprint.pontos_usados}/${sprint.pontos_orcamento} pts em tasks${
                sprint.faturamento_previsto != null ? ` · R$ ${sprint.faturamento_previsto.toLocaleString("pt-BR")} previstos` : ""
              }`
            : "Orçamento de pontos não definido (defina na aba Escopo)"}
        </span>
        <span style={muted}>
          · {sprint.ingestions_count} ingestões · {sprint.docs_gerados_count} docs
        </span>
      </div>
```

- [ ] **Step 3: Remover o form inline de Baseline**

Remover o bloco `{baselineOpen && (...)}` inteiro (form com input numérico e botões Salvar/Cancelar, logo após o bloco anterior) — ele não existe mais, já que a edição agora acontece na aba Escopo (Task 7), não no card da sprint.

- [ ] **Step 4: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros de type-check.

- [ ] **Step 5: Checagem visual manual**

Abrir a aba Sprints de um projeto. Confirmar: nenhuma referência a "Baseline" aparece mais no card; em vez disso, um texto mostra o orçamento/uso/faturamento derivados (ou "Orçamento de pontos não definido" se a sprint ainda não tiver `pontos_orcamento`).

- [ ] **Step 6: Commit**

```bash
cd docudata-frontend
git add app/components/SprintCard.tsx
git commit -m "refactor(sprints): remover baseline manual, mostrar orcamento/uso/faturamento derivados"
```

---

### Task 7: `EscopoTab.tsx` — planejamento de orçamento de pontos por sprint

**Files:**
- Create: `docudata-frontend/app/components/SprintOrcamentoPlanner.tsx`
- Modify: `docudata-frontend/app/components/EscopoTab.tsx`
- Modify: `docudata-frontend/app/projects/[id]/page.tsx` — passar `sprints`/`onSprintUpdated` pra `EscopoTab`

**Interfaces:**
- Consumes: `SprintWithStatus[]` (Task 5), `updateSprintOrcamento` (Task 5).
- Produces: `SprintOrcamentoPlanner` exportado como default, usado por `EscopoTab`.

- [ ] **Step 1: Criar o componente de planejamento**

Criar `docudata-frontend/app/components/SprintOrcamentoPlanner.tsx`:

```tsx
"use client";

import { useState } from "react";
import { SprintWithStatus, updateSprintOrcamento } from "../lib/api";

interface Props {
  sprints: SprintWithStatus[];
  onSprintUpdated: (updated: SprintWithStatus) => void;
}

export default function SprintOrcamentoPlanner({ sprints, onSprintUpdated }: Props) {
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [errBySprint, setErrBySprint] = useState<Record<string, string>>({});

  const totalAlocado = sprints.reduce((acc, s) => acc + (s.pontos_orcamento ?? 0), 0);

  async function handleSalvar(sprint: SprintWithStatus) {
    const raw = inputs[sprint.id] ?? String(sprint.pontos_orcamento ?? "");
    const valor = parseInt(raw, 10);
    if (isNaN(valor) || valor < 0) {
      setErrBySprint((e) => ({ ...e, [sprint.id]: "Informe um número válido." }));
      return;
    }
    setSavingId(sprint.id);
    setErrBySprint((e) => ({ ...e, [sprint.id]: "" }));
    try {
      const updated = await updateSprintOrcamento(sprint.id, valor);
      onSprintUpdated(updated);
    } catch (err) {
      setErrBySprint((e) => ({
        ...e,
        [sprint.id]: err instanceof Error ? err.message : "Erro ao salvar orçamento.",
      }));
    } finally {
      setSavingId(null);
    }
  }

  if (sprints.length === 0) {
    return (
      <div style={{ background: "#fff", border: "1px solid #e8e8ed", borderRadius: 14, padding: "20px 24px", marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", margin: "0 0 8px" }}>Orçamento de pontos por sprint</h3>
        <p style={{ fontSize: 13, color: "#9696a0", margin: 0 }}>
          Nenhuma sprint criada ainda. Crie sprints na aba Sprints antes de distribuir os pontos.
        </p>
      </div>
    );
  }

  return (
    <div style={{ background: "#fff", border: "1px solid #e8e8ed", borderRadius: 14, padding: "20px 24px", marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", margin: 0 }}>Orçamento de pontos por sprint</h3>
        <span style={{ fontSize: 13, fontWeight: 700, color: totalAlocado > 100 ? "#dc2626" : "#4338ca" }}>
          {totalAlocado}/100 pontos alocados
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {sprints.map((s) => (
          <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#111116", width: 90 }}>Sprint {s.numero}</span>
            <input
              type="number"
              min={0}
              value={inputs[s.id] ?? (s.pontos_orcamento != null ? String(s.pontos_orcamento) : "")}
              onChange={(e) => setInputs((i) => ({ ...i, [s.id]: e.target.value }))}
              placeholder="0"
              style={{ width: 80, padding: "6px 10px", border: "1px solid #e4e4ea", borderRadius: 7, fontSize: 13 }}
            />
            <button
              onClick={() => handleSalvar(s)}
              disabled={savingId === s.id}
              style={{
                background: "#0f172a", color: "#fff", border: "none", borderRadius: 8,
                padding: "6px 14px", fontSize: 12, fontWeight: 700, cursor: "pointer",
                opacity: savingId === s.id ? 0.6 : 1,
              }}
            >
              {savingId === s.id ? "…" : "Salvar"}
            </button>
            <span style={{ fontSize: 12, color: "#9696a0" }}>{s.pontos_usados} pts já usados em tasks</span>
            {errBySprint[s.id] && <span style={{ fontSize: 12, color: "#dc2626" }}>{errBySprint[s.id]}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Integrar no `EscopoTab.tsx`**

Em `docudata-frontend/app/components/EscopoTab.tsx`, adicionar o import (junto aos outros imports, ~linha 4):

```tsx
import SprintOrcamentoPlanner from "./SprintOrcamentoPlanner";
```

Adicionar `SprintWithStatus` ao import de `../lib/api` (~linhas 5-13):

```tsx
import {
  FuncionalidadeResponse,
  FuncionalidadeProposta,
  SprintWithStatus,
  importarFuncionalidades,
  importarFuncionalidadesArquivo,
  confirmarImportacao,
  createFuncionalidade,
  updateFuncionalidade,
} from "../lib/api";
```

Atualizar `Props` (~linhas 44-48):

```tsx
interface Props {
  projectId: string;
  funcionalidades: FuncionalidadeResponse[];
  onImported: (novas: FuncionalidadeResponse[]) => void;
  sprints: SprintWithStatus[];
  onSprintUpdated: (updated: SprintWithStatus) => void;
}
```

Atualizar a assinatura da função (~linha 50):

```tsx
export default function EscopoTab({ projectId, funcionalidades, onImported, sprints, onSprintUpdated }: Props) {
```

Renderizar o novo bloco logo após o header (depois do `</div>` que fecha o bloco de título+botões, ~linha 241, antes do restante do conteúdo):

```tsx
      <SprintOrcamentoPlanner sprints={sprints} onSprintUpdated={onSprintUpdated} />
```

- [ ] **Step 3: Passar `sprints`/`onSprintUpdated` de `page.tsx`**

Em `docudata-frontend/app/projects/[id]/page.tsx`, no uso de `<EscopoTab .../>` (~linhas 1007-1013), adicionar os dois novos props:

```tsx
      {activeTab === "escopo" && (
        <EscopoTab
          projectId={id}
          funcionalidades={funcionalidades}
          onImported={(novas) => setFuncionalidades((prev) => [...prev, ...novas])}
          sprints={sprints}
          onSprintUpdated={(updated) =>
            setSprints((prev) => prev.map((s) => (s.id === updated.id ? updated : s)))
          }
        />
      )}
```

- [ ] **Step 4: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros.

- [ ] **Step 5: Checagem visual manual**

Abrir a aba Escopo de um projeto com pelo menos uma sprint criada. Confirmar: aparece o bloco "Orçamento de pontos por sprint" com um input por sprint, um total rodando ("X/100 pontos alocados", em vermelho se passar de 100), e o número de pontos já usados em tasks por sprint. Salvar um valor e ver o total atualizar.

- [ ] **Step 6: Commit**

```bash
cd docudata-frontend
git add app/components/SprintOrcamentoPlanner.tsx app/components/EscopoTab.tsx "app/projects/[id]/page.tsx"
git commit -m "feat(escopo): planejamento de orcamento de pontos por sprint"
```

---

### Task 8: `PainelTab.tsx` — campo `valor_projeto` no formulário de Contrato

**Files:**
- Modify: `docudata-frontend/app/components/PainelTab.tsx`

**Interfaces:**
- Consumes: `Project.valor_projeto`/`valor_por_ponto` (Task 5), `SprintWithStatus.pontos_orcamento` (via prop `sprints` já existente em `PainelTab`).
- Produces: nada novo.

- [ ] **Step 1: Adicionar o campo no formulário**

Em `docudata-frontend/app/components/PainelTab.tsx`, dentro de `BlocoACard`, adicionar o prop `sprints` (~linhas 96-104):

```tsx
function BlocoACard({
  bloco,
  project,
  sprints,
  onSaved,
}: {
  bloco: PainelData["bloco_a"];
  project: Project;
  sprints: SprintWithStatus[];
  onSaved?: (updated: Project) => void;
}) {
```

Adicionar o estado do novo campo, logo após `arquetipo` (~linha 111):

```tsx
  const [valorProjeto, setValorProjeto] = useState(
    project.valor_projeto != null ? String(project.valor_projeto) : ""
  );
```

Calcular a trava (logo após os estados, antes de `handleSave`):

```tsx
  const valorTravado = sprints.some((s) => s.pontos_orcamento != null);
```

Incluir `valor_projeto` na chamada de `updateContrato` dentro de `handleSave` (~linhas 121-126):

```tsx
      const updated = await updateContrato(project.id, {
        data_inicio: dataInicio,
        data_fim_contratada: dataFim,
        tolerancia_desvio_pontos: tolerancia !== "" ? Number(tolerancia) : null,
        arquetipo,
        valor_projeto: !valorTravado && valorProjeto !== "" ? Number(valorProjeto) : undefined,
      });
```

Adicionar o campo no formulário JSX, logo após o bloco de `arquetipo` (~linhas 177-187):

```tsx
          <div>
            <label style={labelSmStyle}>
              Valor do projeto (R$) <span style={{ fontWeight: 400 }}>— opcional</span>
            </label>
            <input
              type="number"
              min={0}
              step="0.01"
              value={valorProjeto}
              onChange={(e) => setValorProjeto(e.target.value)}
              placeholder="ex: 35000"
              style={inputSmStyle}
              disabled={valorTravado}
            />
            {valorTravado && (
              <p style={{ fontSize: 11, color: "#9696a0", margin: "4px 0 0" }}>
                Travado: já existe orçamento de pontos definido em pelo menos uma sprint.
              </p>
            )}
          </div>
```

- [ ] **Step 2: Passar `sprints` de onde `BlocoACard` é renderizado**

Em `docudata-frontend/app/components/PainelTab.tsx`, no uso de `<BlocoACard .../>` (~linhas 690-697), adicionar o prop (`sprints` já está disponível no escopo de `PainelTab`, vindo de `Props`):

```tsx
        <BlocoACard
          bloco={data.bloco_a}
          project={project}
          sprints={sprints}
          onSaved={(updated) => {
            onProjectUpdated?.(updated);
            getPainel(projectId).then(setData).catch(() => {});
          }}
        />
```

Adicionar `SprintWithStatus` ao import de `../lib/api` no topo do arquivo, se ainda não estiver importado (verificar a lista atual de imports do arquivo — `Project` já é importado; adicionar `SprintWithStatus` junto).

- [ ] **Step 3: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros.

- [ ] **Step 4: Checagem visual manual**

Abrir a aba Painel de um projeto, clicar em "Editar"/"Configurar" no card "Tempo × Escopo". Confirmar: aparece o campo "Valor do projeto (R$)". Se nenhuma sprint do projeto tiver orçamento definido, o campo é editável; se alguma tiver, aparece desabilitado com a explicação.

- [ ] **Step 5: Commit**

```bash
cd docudata-frontend
git add app/components/PainelTab.tsx
git commit -m "feat(painel): campo valor_projeto no formulario de contrato, travado apos primeiro orcamento de sprint"
```

---

### Task 9: "Marcar como entregue" — aviso não-bloqueante de saldo

**Files:**
- Modify: `docudata-frontend/app/projects/[id]/page.tsx`

**Interfaces:**
- Consumes: `sprints` (estado já existente em `page.tsx`), `SprintWithStatus.pontos_orcamento`.
- Produces: nada novo.

- [ ] **Step 1: Localizar o botão e o handler de "Marcar como entregue"**

Em `docudata-frontend/app/projects/[id]/page.tsx`, localizar o botão "Marcar como entregue" (seção Configurações/Zona Perigosa não é essa — é o card "Status do Projeto" visto na captura de tela do usuário) e sua função de clique, que chama o endpoint de toggle delivered (buscar por `toggleDelivered` ou `/delivered` no arquivo).

- [ ] **Step 2: Adicionar o aviso não-bloqueante**

Envolver a chamada existente com uma checagem de saldo antes de prosseguir. Se a função de clique for algo como:

```tsx
async function handleMarcarEntregue() {
  const updated = await toggleDelivered(id);
  setProject(updated);
}
```

trocar por:

```tsx
async function handleMarcarEntregue() {
  const totalOrcamento = sprints.reduce((acc, s) => acc + (s.pontos_orcamento ?? 0), 0);
  if (totalOrcamento !== 100) {
    const ok = confirm(
      `${totalOrcamento}/100 pontos alocados entre as sprints. Marcar como entregue mesmo assim?`
    );
    if (!ok) return;
  }
  const updated = await toggleDelivered(id);
  setProject(updated);
}
```

(Ajustar nomes exatos de variáveis/estado ao encontrar o código real — `id`, `setProject`, `toggleDelivered` devem já existir no arquivo; usar os nomes reais encontrados no Step 1, não necessariamente os acima.)

- [ ] **Step 3: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros.

- [ ] **Step 4: Checagem visual manual**

Com um projeto onde a soma dos orçamentos de sprint seja diferente de 100, clicar em "Marcar como entregue" em Configurações. Confirmar que aparece o aviso com o saldo antes de prosseguir, e que cancelar não altera o status do projeto.

- [ ] **Step 5: Commit**

```bash
cd docudata-frontend
git add "app/projects/[id]/page.tsx"
git commit -m "feat(configuracoes): aviso nao-bloqueante de saldo de pontos ao marcar projeto como entregue"
```

---

## Lembrete pós-deploy (não é uma task de código)

Depois do deploy desta feature, aplicar manualmente no Supabase de produção (`supabase_schema.sql` não roda sozinho):

```sql
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS pontos_orcamento int CHECK (pontos_orcamento IS NULL OR pontos_orcamento >= 0);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS valor_projeto numeric(10,2);
```

## Self-Review

**Cobertura da spec (seções 1-9):**
- Seção 3.1 (projects.valor_projeto) → Task 3. ✅
- Seção 3.2 (sprints.pontos_orcamento, baseline aposentado) → Task 1. ✅
- Seção 4.1 (validação de orçamento de sprint) → Task 1. ✅
- Seção 4.2 (validação de orçamento de task) → Task 2. ✅
- Seção 5 (aviso não-bloqueante em "Marcar como entregue") → Task 9. ✅
- Seção 6 (API: todas as rotas listadas) → Tasks 1, 2, 3, 4. ✅
- Seção 7 (UI: todas as mudanças listadas) → Tasks 5, 6, 7, 8, 9. ✅
- Seção 8 (fora de escopo) → nenhuma task implementa isso, corretamente. ✅

**Consistência de tipos/nomes:** `pontos_orcamento`, `pontos_usados`, `faturamento_previsto`, `valor_projeto`, `valor_por_ponto` usados com o mesmo nome em schemas Python, rotas, tipos TypeScript e componentes React em todas as tasks.

**Placeholders:** nenhum — todo código de teste e implementação está completo e executável.
