# Backlog UAT Phase 19 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir os 6 itens de bug/polish descobertos no UAT ao vivo da Phase 19 em produção — contraste WCAG, duplicata de operacional case-insensitive, cascade delete de operacional, delete de task pós-trava de pontuação, ícone de info faltando, e poluição visual da aba Sprints.

**Architecture:** Nenhum item requer mudança de schema ou subsistema novo — todos são correções pontuais a fluxos já existentes. Onda 1 toca 3 arquivos de `docudata-backend/routers/` (operacionais.py, metricas.py, tasks.py), cada um com testes pytest usando o padrão de mock já estabelecido no repo (`MagicMock` simulando `client.table(...)`, injetado via `monkeypatch.setattr(<router_module>, "get_client", ...)`). Onda 2 toca 3 arquivos de `docudata-frontend/app/`, sem framework de teste automatizado no repo — verificação via `npm run build` (type-check) + checagem visual manual.

**Tech Stack:** FastAPI + supabase-py (backend), Next.js/React com estilos inline + Recharts (frontend). Testes backend: pytest + pytest-asyncio + unittest.mock.

**Spec:** Sem spec file separado — design aprovado em brainstorm caminho Bounded (ver `.planning/feature-flow-state.md`, Etapa 1, decisões de produto registradas em chat).

## Global Constraints

- Sem migração de banco nesta feature — nenhum item requer `ALTER TABLE` ou novo índice (item 2 virou checagem em app-level por decisão explícita do usuário).
- Backend: seguir o padrão de teste já estabelecido no repo — `MagicMock` por tabela via `client.table(name)`, nunca banco real. Ver `tests/test_metricas_novos_endpoints.py` e `tests/test_avaliacao_semanal_confirmar.py` como referência de estilo.
- Frontend: não existe framework de teste automatizado (`docudata-frontend/package.json` só tem `dev`/`build`/`start`). Verificação de cada task de UI é `npm run build` (compila e type-checa) + descrição do que checar visualmente — não escrever testes que não existem no projeto.
- Onda 2 só começa depois de Onda 1 100% completa com testes passando.
- Preservar contratos de API existentes — nenhuma mudança deve quebrar testes já passando (rodar a suíte completa, não só os arquivos tocados, antes de considerar a Onda 1 concluída).

---

## Onda 1 — Back-end

### Task 1: Duplicata de operacional case-insensitive (Item 2)

**Files:**
- Modify: `docudata-backend/routers/operacionais.py:9-33` (função `create_operacional`)
- Test: `docudata-backend/tests/test_operacionais.py` (novo arquivo)

**Interfaces:**
- Consumes: `services.supabase_client.get_client()` (já importado no arquivo), `models.schemas.OperacionalCreate` (campos `project_id: str`, `nome: str`, `email: Optional[str]`, `papel: Optional[str]`).
- Produces: nenhuma interface nova — `create_operacional` continua retornando `OperacionalResponse` com o mesmo contrato.

- [ ] **Step 1: Escrever os testes que falham**

Criar `docudata-backend/tests/test_operacionais.py`:

```python
"""Testes para POST /operacionais (duplicata case-insensitive) e DELETE /operacionais/{id} (cascade)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_create_mock_client(project_exists=True, existing_operacionais=None, insert_ok=True):
    existing_operacionais = existing_operacionais or []
    client = MagicMock()
    calls = {"insert": []}

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
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(existing_operacionais)
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                calls["insert"].append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="new-op-id")] if insert_ok else []
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.operacionais as operacionais_router
    monkeypatch.setattr(operacionais_router, "get_client", lambda: mock_supabase)
    from main import app
    return TestClient(app)


def test_create_operacional_bloqueia_nome_duplicado_case_insensitive(monkeypatch):
    mock_sb, calls = _make_create_mock_client(
        existing_operacionais=[{"nome": "Gabriel Teste"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/operacionais", json={"project_id": "proj-1", "nome": "gabriel teste"})

    assert resp.status_code == 409
    assert "gabriel teste" in resp.json()["detail"]
    assert calls["insert"] == []


def test_create_operacional_bloqueia_nome_duplicado_com_espacos_extras(monkeypatch):
    mock_sb, calls = _make_create_mock_client(
        existing_operacionais=[{"nome": "Ana Silva"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/operacionais", json={"project_id": "proj-1", "nome": "  ANA SILVA  "})

    assert resp.status_code == 409
    assert calls["insert"] == []


def test_create_operacional_permite_nome_novo(monkeypatch):
    mock_sb, calls = _make_create_mock_client(
        existing_operacionais=[{"nome": "Ana Silva"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.post("/operacionais", json={"project_id": "proj-1", "nome": "Bruno Costa"})

    assert resp.status_code == 201
    assert len(calls["insert"]) == 1
    assert calls["insert"][0]["nome"] == "Bruno Costa"
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && python -m pytest tests/test_operacionais.py -v`
Expected: `test_create_operacional_bloqueia_nome_duplicado_case_insensitive` e `test_create_operacional_bloqueia_nome_duplicado_com_espacos_extras` FALHAM com 201 em vez de 409 (a checagem case-insensitive ainda não existe). `test_create_operacional_permite_nome_novo` já passa (comportamento não mudou para esse caso).

- [ ] **Step 3: Implementar a checagem case-insensitive**

Em `docudata-backend/routers/operacionais.py`, modificar `create_operacional` (linhas 9-33):

```python
@router.post("", response_model=OperacionalResponse, status_code=201)
async def create_operacional(data: OperacionalCreate):
    client = get_client()
    check = client.table("projects").select("id").eq("id", data.project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    nome_normalizado = data.nome.strip().lower()
    existentes = (
        client.table("operacionais")
        .select("nome")
        .eq("project_id", data.project_id)
        .execute()
        .data or []
    )
    if any(e["nome"].strip().lower() == nome_normalizado for e in existentes):
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um operacional com o nome '{data.nome}' neste projeto",
        )

    payload = {
        "project_id": data.project_id,
        "nome": data.nome,
    }
    if data.email is not None:
        payload["email"] = data.email
    if data.papel is not None:
        payload["papel"] = data.papel

    try:
        resp = client.table("operacionais").insert(payload).execute()
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409,
                detail=f"Já existe um operacional com o nome '{data.nome}' neste projeto",
            )
        raise HTTPException(status_code=500, detail=f"Failed to create operacional: {exc}")

    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create operacional")
    return resp.data[0]
```

(O `try/except` de unique constraint do banco continua como fallback de defesa em profundidade — cobre a corrida rara entre a checagem e o insert. Não removê-lo.)

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && python -m pytest tests/test_operacionais.py -v`
Expected: PASS nos 3 testes.

- [ ] **Step 5: Commit**

```bash
cd docudata-backend
git add routers/operacionais.py tests/test_operacionais.py
git commit -m "fix(operacionais): bloquear nome duplicado case-insensitive na criação"
```

---

### Task 2: Cascade delete de operacional (Item 5, parte back-end)

**Files:**
- Modify: `docudata-backend/routers/operacionais.py:87-108` (função `delete_operacional`)
- Test: `docudata-backend/tests/test_operacionais.py` (adicionar ao arquivo do Task 1)

**Interfaces:**
- Consumes: mesmo `get_client()` do Task 1.
- Produces: `DELETE /operacionais/{operacional_id}` deixa de retornar 409 quando há tasks vinculadas — sempre desvincula e apaga (ou 404 se não existe).

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao final de `docudata-backend/tests/test_operacionais.py`:

```python
def _make_delete_mock_client(operacional_exists=True):
    client = MagicMock()
    calls = {"tasks_update": [], "operacionais_delete": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "op-1"}] if operacional_exists else []
                q.execute = MagicMock(return_value=resp)
                return q

            def delete_side_effect():
                q = MagicMock()

                def eq_side_effect(field, value):
                    calls["operacionais_delete"].append((field, value))
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [{"id": value}]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.delete = MagicMock(side_effect=delete_side_effect)
        elif name == "tasks":
            def update_side_effect(payload):
                q = MagicMock()

                def eq_side_effect(field, value):
                    calls["tasks_update"].append((payload, field, value))
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = []
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.update = MagicMock(side_effect=update_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def test_delete_operacional_desvincula_tasks_e_apaga(monkeypatch):
    mock_sb, calls = _make_delete_mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/operacionais/op-1")

    assert resp.status_code == 204
    assert calls["tasks_update"] == [({"operacional_id": None}, "operacional_id", "op-1")]
    assert calls["operacionais_delete"] == [("id", "op-1")]


def test_delete_operacional_not_found(monkeypatch):
    mock_sb, calls = _make_delete_mock_client(operacional_exists=False)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/operacionais/does-not-exist")

    assert resp.status_code == 404
    assert calls["tasks_update"] == []
    assert calls["operacionais_delete"] == []
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && python -m pytest tests/test_operacionais.py -v`
Expected: `test_delete_operacional_desvincula_tasks_e_apaga` FALHA (código atual bloqueia com 409 quando há tasks — mas o mock não simula tasks vinculadas, então checar: o comportamento atual chama `client.table("tasks").select(...)` para checar `has_tasks`, que nesse mock não está configurado e vai levantar erro de atributo ou retornar MagicMock não-vazio incorretamente). Se o teste falhar por erro de mock em vez de assertion, ainda conta como falha esperada — o objetivo é confirmar que o código atual não bate com o comportamento novo.

- [ ] **Step 3: Implementar o cascade delete**

Em `docudata-backend/routers/operacionais.py`, substituir `delete_operacional` (linhas 87-108):

```python
@router.delete("/{operacional_id}", status_code=204)
async def delete_operacional(operacional_id: str):
    client = get_client()
    check = client.table("operacionais").select("id").eq("id", operacional_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Operacional not found")

    client.table("tasks").update({"operacional_id": None}).eq("operacional_id", operacional_id).execute()
    client.table("operacionais").delete().eq("id", operacional_id).execute()
```

(Remove a checagem de `has_tasks` e o bloqueio 409 — tasks vinculadas são desvinculadas em vez de bloquear a exclusão. `pontuacao_operacional_sprint` e demais tabelas com `ON DELETE CASCADE` em `operacional_id` — já confirmadas no `supabase_schema.sql` — são limpas automaticamente pelo banco quando a linha de `operacionais` é apagada; nenhuma chamada extra necessária para isso.)

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && python -m pytest tests/test_operacionais.py -v`
Expected: PASS nos 5 testes do arquivo (3 do Task 1 + 2 deste task).

- [ ] **Step 5: Commit**

```bash
cd docudata-backend
git add routers/operacionais.py tests/test_operacionais.py
git commit -m "fix(operacionais): permitir exclusão com cascade em vez de bloquear com tasks vinculadas"
```

---

### Task 3: Excluir operacionais inativos do ranking de Métricas (Item 5, bug de listagem)

**Files:**
- Modify: `docudata-backend/routers/metricas.py` (função `get_performance_operacional`, ~linha 218-260)
- Test: `docudata-backend/tests/test_metricas_novos_endpoints.py` (adicionar teste)

**Interfaces:**
- Consumes: mesmo `get_client()` já usado no arquivo.
- Produces: `GET /metricas/{project_id}/performance-operacional` deixa de incluir operacionais com `ativo=False` na resposta.

- [ ] **Step 1: Escrever o teste que falha**

Adicionar a `docudata-backend/tests/test_metricas_novos_endpoints.py`, na seção `performance-operacional`:

```python
def test_performance_operacional_exclui_operacionais_inativos(monkeypatch):
    operacionais = [
        {"id": "op-1", "nome": "Ana", "ativo": True},
        {"id": "op-2", "nome": "Bruno (desativado)", "ativo": False},
    ]
    tasks = [
        {"operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida"},
        {"operacional_id": "op-2", "pontos": 3, "coluna_kanban": "concluida"},
    ]
    mock_sb = _make_mock_client(operacionais_data=operacionais, tasks_data=tasks)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/metricas/test-project-id/performance-operacional")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["operacional_id"] == "op-1"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `cd docudata-backend && python -m pytest tests/test_metricas_novos_endpoints.py -v -k inativos`
Expected: FALHA — `len(data) == 2` hoje (operacional inativo aparece).

- [ ] **Step 3: Implementar o filtro**

Em `docudata-backend/routers/metricas.py`, dentro de `get_performance_operacional`, trocar:

```python
    operacionais = (
        client.table("operacionais")
        .select("id, nome")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
```

por:

```python
    operacionais_raw = (
        client.table("operacionais")
        .select("id, nome, ativo")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    operacionais = [o for o in operacionais_raw if o.get("ativo", True)]
```

(O filtro `.get("ativo", True)` — em vez de indexação direta — mantém compatibilidade com fixtures/linhas antigas que não tragam o campo `ativo`, tratando-as como ativas por padrão.)

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && python -m pytest tests/test_metricas_novos_endpoints.py -v`
Expected: PASS em todos os testes do arquivo, incluindo os 3 já existentes de `performance-operacional` (que não usam o campo `ativo` nas fixtures e continuam passando pelo default `True`).

- [ ] **Step 5: Commit**

```bash
cd docudata-backend
git add routers/metricas.py tests/test_metricas_novos_endpoints.py
git commit -m "fix(metricas): excluir operacionais inativos do ranking de performance-operacional"
```

---

### Task 4: Bloquear delete de task quando pontuação da sprint já está travada (Item 6)

**Files:**
- Modify: `docudata-backend/routers/tasks.py:489-496` (função `delete_task`)
- Test: `docudata-backend/tests/test_task_delete_pontuacao_travada.py` (novo arquivo)

**Interfaces:**
- Consumes: `get_client()` já importado em `routers/tasks.py`. Campo `sprints.avaliacao_completa_em` (já existente, setado por `routers/avaliacoes.py::confirmar_avaliacao_semanal`).
- Produces: `DELETE /tasks/{task_id}` retorna 409 quando a task pertence a uma sprint com `avaliacao_completa_em` preenchido.

- [ ] **Step 1: Escrever os testes que falham**

Criar `docudata-backend/tests/test_task_delete_pontuacao_travada.py`:

```python
"""Testes para DELETE /tasks/{id} bloqueando exclusão quando a pontuação da sprint já está travada."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(task_data=None, sprint_data=None, task_exists=True):
    client = MagicMock()
    calls = {"tasks_delete": []}

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task_data)] if task_exists else []
                q.execute = MagicMock(return_value=resp)
                return q

            def delete_side_effect():
                q = MagicMock()

                def eq_side_effect(field, value):
                    calls["tasks_delete"].append((field, value))
                    exec_q = MagicMock()
                    resp = MagicMock()
                    resp.data = [{"id": value}]
                    exec_q.execute = MagicMock(return_value=resp)
                    return exec_q

                q.eq = MagicMock(side_effect=eq_side_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.delete = MagicMock(side_effect=delete_side_effect)
        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(sprint_data)] if sprint_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, calls


def _patch_and_client(monkeypatch, mock_supabase):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.tasks as tasks_router
    monkeypatch.setattr(tasks_router, "get_client", lambda: mock_supabase)
    from main import app
    return TestClient(app)


def test_delete_task_bloqueado_quando_pontuacao_ja_travada(monkeypatch):
    mock_sb, calls = _make_mock_client(
        task_data={"id": "task-1", "sprint_id": "sprint-1"},
        sprint_data={"avaliacao_completa_em": "2026-09-01T00:00:00+00:00"},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/tasks/task-1")

    assert resp.status_code == 409
    assert "travad" in resp.json()["detail"].lower()
    assert calls["tasks_delete"] == []


def test_delete_task_permitido_quando_sprint_sem_avaliacao_confirmada(monkeypatch):
    mock_sb, calls = _make_mock_client(
        task_data={"id": "task-1", "sprint_id": "sprint-1"},
        sprint_data={"avaliacao_completa_em": None},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/tasks/task-1")

    assert resp.status_code == 204
    assert calls["tasks_delete"] == [("id", "task-1")]


def test_delete_task_permitido_quando_task_sem_sprint(monkeypatch):
    mock_sb, calls = _make_mock_client(
        task_data={"id": "task-1", "sprint_id": None},
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/tasks/task-1")

    assert resp.status_code == 204
    assert calls["tasks_delete"] == [("id", "task-1")]


def test_delete_task_not_found(monkeypatch):
    mock_sb, calls = _make_mock_client(task_exists=False)
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.delete("/tasks/does-not-exist")

    assert resp.status_code == 404
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && python -m pytest tests/test_task_delete_pontuacao_travada.py -v`
Expected: `test_delete_task_bloqueado_quando_pontuacao_ja_travada` FALHA com 204 em vez de 409 (comportamento atual não checa a sprint).

- [ ] **Step 3: Implementar o bloqueio**

Em `docudata-backend/routers/tasks.py`, substituir `delete_task` (linhas 489-496):

```python
@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str):
    client = get_client()
    check = client.table("tasks").select("id, sprint_id").eq("id", task_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Task not found")

    sprint_id = check.data[0].get("sprint_id")
    if sprint_id:
        sprint = client.table("sprints").select("avaliacao_completa_em").eq("id", sprint_id).execute()
        if sprint.data and sprint.data[0].get("avaliacao_completa_em"):
            raise HTTPException(
                status_code=409,
                detail="A pontuação desta sprint já foi travada (Avaliação Semanal confirmada); exclusão de task bloqueada.",
            )

    client.table("tasks").delete().eq("id", task_id).execute()
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && python -m pytest tests/test_task_delete_pontuacao_travada.py -v`
Expected: PASS nos 4 testes.

- [ ] **Step 5: Rodar a suíte completa do backend**

Run: `cd docudata-backend && python -m pytest -v`
Expected: todos os testes passam, incluindo os já existentes que tocam `delete_task`, `create_operacional`, `delete_operacional` e `performance-operacional` (nenhuma regressão).

- [ ] **Step 6: Commit**

```bash
cd docudata-backend
git add routers/tasks.py tests/test_task_delete_pontuacao_travada.py
git commit -m "fix(tasks): bloquear exclusão de task quando pontuação da sprint já está travada"
```

---

## Onda 2 — UI (só inicia após Onda 1 verificada)

### Task 5: Contraste WCAG AA nos gráficos de Métricas (Item 1)

**Files:**
- Modify: `docudata-frontend/app/components/MetricasTab.tsx:190,210,301`

**Interfaces:**
- Consumes: nada novo.
- Produces: nada novo — só troca de valor de cor.

- [ ] **Step 1: Trocar o fill das 3 barras "previstos/total"**

Em `docudata-frontend/app/components/MetricasTab.tsx`, trocar `fill="#e2e8f0"` por `fill="#64748b"` nas 3 ocorrências:

Linha 190:
```tsx
              <Bar dataKey="pontos_previstos" fill="#64748b" radius={[4, 4, 0, 0]} />
```

Linha 210:
```tsx
              <Bar dataKey="tasks_total" fill="#64748b" radius={[4, 4, 0, 0]} />
```

Linha 301:
```tsx
              <Bar dataKey="pontos_atribuidos" fill="#64748b" radius={[4, 4, 0, 0]} />
```

(A legenda de cada gráfico — `<Legend formatter={...}>` — herda a cor do swatch a partir do `fill` do `<Bar>` correspondente automaticamente; não precisa de mudança separada.)

- [ ] **Step 2: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros de type-check.

- [ ] **Step 3: Checagem visual manual**

Abrir a aba Métricas de um projeto com dados (`npm run dev`, navegar até `/projects/{id}` → aba Métricas). Confirmar que as barras "Previstos" (gráfico SPI), "Total" (Throughput) e "Atribuídos" (SPI por operacional) agora aparecem em cinza mais escuro, legíveis contra o fundo branco, e a legenda de cada gráfico também mudou de cor.

- [ ] **Step 4: Commit**

```bash
cd docudata-frontend
git add app/components/MetricasTab.tsx
git commit -m "fix(metricas): aumentar contraste das barras previstos/total para WCAG AA"
```

---

### Task 6: Ícone de info faltando no card "Métricas de Fluxo" (Item 3)

**Files:**
- Modify: `docudata-frontend/app/components/PainelTab.tsx:286`

**Interfaces:**
- Consumes: componente local `InfoTooltip({ text }: { text: string })` (já definido no mesmo arquivo, linha 417).
- Produces: nada novo.

- [ ] **Step 1: Adicionar o InfoTooltip ao título do card**

Em `docudata-frontend/app/components/PainelTab.tsx`, trocar (linha 286):

```tsx
      <span style={cardTitleStyle}>Métricas de Fluxo</span>
```

por:

```tsx
      <span style={cardTitleStyle}>
        Métricas de Fluxo
        <InfoTooltip text="WIP (Work in Progress) = funcionalidades em andamento agora. Throughput = quantas foram concluídas por semana. Cycle-time = tempo médio de uma funcionalidade do início ao fim. Métricas calculadas a partir do histórico de status das funcionalidades." />
      </span>
```

- [ ] **Step 2: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros.

- [ ] **Step 3: Checagem visual manual**

Abrir a aba Painel de um projeto. Confirmar que o card "Métricas de Fluxo" agora tem o ícone "i" ao lado do título, igual aos cards "Itens em Atenção" e "Tempo por Fase", e que passar o mouse/tocar mostra o texto correto.

- [ ] **Step 4: Commit**

```bash
cd docudata-frontend
git add app/components/PainelTab.tsx
git commit -m "fix(painel): adicionar InfoTooltip faltando no card Métricas de Fluxo"
```

---

### Task 7: Reduzir poluição visual da aba Sprints (Item 4)

**Files:**
- Modify: `docudata-frontend/app/components/SprintCard.tsx`

**Interfaces:**
- Consumes: estados/handlers já existentes no componente (`baselineOpen`, `setBaselineOpen`, `baselineInput`, `setBaselineInput`, `setBaselineErr`, `handleSaveBaseline`, `pendingGen`, `setPendingGen`, `cargo`, `onOpenAvaliacaoSemanal`, `onUploadLivre`, `onAddManualDoc`) — nenhum novo estado.
- Produces: nada novo — só reorganização visual.

- [ ] **Step 1: Adicionar o estilo de botão primário**

Em `docudata-frontend/app/components/SprintCard.tsx`, logo após a definição de `btnActionActive` (linha ~127-132), adicionar:

```tsx
const btnPrimary: React.CSSProperties = {
  background: "#0f172a",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  padding: "11px 18px",
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
};
```

- [ ] **Step 2: Tirar o Baseline do grupo de chips e criar uma linha própria**

Substituir o bloco `statusRow` inteiro (linhas 406-460) por:

```tsx
      <div style={statusRow}>
        <button
          type="button"
          style={statusChip(sprint.tem_planning)}
          onClick={() => onOpenPlanning(sprint)}
          title="Adicionar Planning"
        >
          {sprint.tem_planning ? "1/1" : "0/1"} Planning
          <span style={{ marginLeft: 4, fontWeight: 800 }}>+</span>
        </button>
        <button
          type="button"
          style={statusChip(sprint.tem_review)}
          onClick={() => onOpenSprintDoc("review", sprint.numero)}
          title="Adicionar Review"
        >
          {sprint.tem_review ? "1/1" : "0/1"} Review
          <span style={{ marginLeft: 4, fontWeight: 800 }}>+</span>
        </button>
        <button
          type="button"
          style={statusChip(temRetro)}
          onClick={() => onOpenRetroModal(sprint.numero)}
          title="Adicionar Retrospectiva"
        >
          {temRetro ? "1/1" : "0/1"} Retrospectiva
          <span style={{ marginLeft: 4, fontWeight: 800 }}>+</span>
        </button>
        <button
          type="button"
          style={dailyChip(sprint.dailys_count)}
          onClick={() => onOpenSprintDoc("daily", sprint.numero)}
          title="Adicionar Daily"
        >
          Dailys
          <span style={{ marginLeft: 4, fontWeight: 800 }}>+</span>
        </button>
      </div>

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

Ajustar também `statusRow` (definição de estilo, linhas 68-75) — trocar `marginBottom: 18` por `marginBottom: 10`, já que a nova linha do Baseline assume o `marginBottom: 18` antes do form/actionRow:

```tsx
const statusRow: React.CSSProperties = {
  display: "flex",
  gap: 10,
  alignItems: "center",
  flexWrap: "wrap",
  marginTop: 18,
  marginBottom: 10,
};
```

- [ ] **Step 3: Promover a ação mais relevante do momento a botão primário**

Substituir o bloco `actionRow` inteiro (linhas 485-503) por:

```tsx
      <div style={actionRow}>
        {cargo !== "operacional" && (
          <button
            style={sprint.avaliacao_completa_em ? btnAction : btnPrimary}
            onClick={() => onOpenAvaliacaoSemanal?.(sprint)}
          >
            {sprint.avaliacao_completa_em ? "✓ Avaliação Semanal" : "Avaliação Semanal"}
          </button>
        )}
        <button
          style={
            pendingGen === "repasse_semanal"
              ? btnActionActive
              : sprint.avaliacao_completa_em
              ? btnPrimary
              : btnAction
          }
          onClick={() => setPendingGen(pendingGen === "repasse_semanal" ? null : "repasse_semanal")}
        >
          Gerar Repasse Semanal
        </button>
        <button style={btnSubtle} onClick={() => onUploadLivre(sprint.numero)}>
          Upload livre
        </button>
        <button style={btnSubtle} onClick={() => onAddManualDoc(sprint.numero)}>
          + Documento manual
        </button>
      </div>
```

(Regra: se a Avaliação Semanal ainda não foi confirmada, ela é a ação primária — é o que falta pra fechar a sprint. Se já foi confirmada, "Gerar Repasse Semanal" vira a primária. "Upload livre" e "+ Documento manual" são ações secundárias/menos frequentes, rebaixadas para `btnSubtle`.)

- [ ] **Step 4: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros de type-check.

- [ ] **Step 5: Checagem visual manual**

Abrir a aba Sprints de um projeto com pelo menos uma sprint. Confirmar: (a) linha de chips agora tem só 4 itens (Planning/Review/Retrospectiva/Dailys), (b) Baseline aparece como link de texto abaixo, não como chip colorido, (c) o contador de ingestões/docs continua visível na mesma linha do Baseline, (d) o botão de ação mais relevante (Avaliação Semanal pendente, ou Repasse Semanal se já avaliada) aparece em destaque escuro, (e) Upload livre e + Documento manual aparecem como links discretos, não como botões cheios.

- [ ] **Step 6: Commit**

```bash
cd docudata-frontend
git add app/components/SprintCard.tsx
git commit -m "refactor(sprints): reduzir poluição visual — separar baseline do checklist e hierarquizar ações"
```

---

### Task 8: Atualizar mensagem de confirmação de exclusão de operacional em Configurações (Item 5, parte front-end)

**Files:**
- Modify: `docudata-frontend/app/projects/[id]/page.tsx:114` (função `handleDelete` dentro de `OperacionaisSection`)

**Interfaces:**
- Consumes: `deleteOperacional` (já importado de `../lib/api`), `operacionais`, `onUpdated` — nenhuma mudança de assinatura.
- Produces: nada novo — o botão "×" já existente passa a funcionar de ponta a ponta agora que o Task 2 (back-end) não bloqueia mais com 409.

- [ ] **Step 1: Atualizar o texto de confirmação**

Em `docudata-frontend/app/projects/[id]/page.tsx`, trocar (linha 114):

```tsx
    if (!confirm(`Excluir "${op.nome}"? Tasks vinculadas perdem o operacional.`)) return;
```

por:

```tsx
    if (!confirm(`Excluir "${op.nome}"? As tasks vinculadas ficam sem operacional atribuído, e toda a pontuação/ranking desse operacional será apagada. Esta ação não pode ser desfeita.`)) return;
```

- [ ] **Step 2: Verificar que o build passa**

Run: `cd docudata-frontend && npm run build`
Expected: build sem erros.

- [ ] **Step 3: Checagem manual de ponta a ponta**

Com a Onda 1 já em produção (ou rodando o backend local com as mudanças do Task 2): na aba Configurações de um projeto, criar um operacional de teste, vincular uma task a ele, clicar em "×" para excluir, confirmar. Verificar: a operação sucede (sem erro 409), o operacional some da lista de Configurações, a task antes vinculada aparece sem operacional atribuído, e o operacional não aparece mais na aba Métricas (SPI por operacional).

- [ ] **Step 4: Commit**

```bash
cd docudata-frontend
git add app/projects/\[id\]/page.tsx
git commit -m "fix(configuracoes): atualizar mensagem de confirmação de exclusão de operacional"
```

---

## Self-Review

**Cobertura dos 6 itens do backlog:**
1. Contraste WCAG → Task 5. ✅
2. Duplicata case-insensitive → Task 1. ✅
3. Ícone de info faltando → Task 6. ✅
4. Aba Sprints poluída → Task 7. ✅
5. Cascade delete + bug de listagem → Tasks 2, 3 e 8. ✅
6. Delete de task pós-trava → Task 4. ✅

**Consistência de tipos/nomes:** `get_client()`, `HTTPException`, `OperacionalCreate`/`OperacionalResponse` usados de forma consistente com o código existente em todas as tasks de back-end. Nomes de campos (`operacional_id`, `ativo`, `avaliacao_completa_em`, `sprint_id`) conferidos contra `supabase_schema.sql` e o código-fonte atual antes de escrever o plano.

**Placeholders:** nenhum — todo código de teste e implementação está completo e executável, sem "TBD" ou "implementar depois".
