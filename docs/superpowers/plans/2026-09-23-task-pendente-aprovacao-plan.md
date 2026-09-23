# Estado "Pendente de aprovação" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduzir o estado `pendente_aprovacao` no Kanban de tasks (entre `em_andamento` e `concluida`), opcional por task via `requer_aprovacao`, resolvendo o travamento de WIP em modo PULL quando uma task pronta espera aprovação do gerente.

**Architecture:** Onda 1 (backend) fecha as transições na origem — só `/aprovar` e `/rejeitar` (gerente/líder-only) saem de `pendente_aprovacao`, igual já fizemos com `modo_trabalho` na Entrega 4. WIP, pontuação e o job de travamento já funcionam certo sem mudança de código (confirmado lendo o código: todos comparam `coluna_kanban` por igualdade exata a valores específicos, nunca "diferente de X"). Onda 2 (frontend) conecta a 4ª coluna, o checkbox administrativo e os botões de aprovar/rejeitar.

**Tech Stack:** FastAPI + Pydantic + supabase-py (backend, testes com `unittest.mock.MagicMock`); Next.js 15 / React 19 com inline styles (frontend, sem design system file).

**Spec:** `docs/superpowers/specs/2026-09-22-task-pendente-aprovacao-design.md` — o plano argumenta a partir da spec; quem executar deve ler as duas.

## Global Constraints

- Nenhuma transição sai de `pendente_aprovacao` exceto via `POST /tasks/{id}/aprovar` ou `POST /tasks/{id}/rejeitar` — fechado na origem (`patch_task`), não só escondido no frontend.
- `pendente_aprovacao` nunca conta para WIP, nunca é contado como entrega pela pontuação, nunca é selecionado pelo job de travamento — todos os três já filtram por igualdade exata (`== "em_andamento"`, `== "concluida"`, `.in_(["planejado","em_andamento"])`), então nenhuma mudança é necessária nesses três lugares além do que já está no plano.
- Rejeição nunca penaliza travamento (o relógio já estava pausado desde a entrada em `pendente_aprovacao`) e nunca conta como reabertura (TRANS-03 continua sendo estritamente `concluida → em_andamento`).
- Migração de schema é manual (SQL colado no Supabase pelo usuário) — nunca roda sozinha, mesma convenção do projeto inteiro.
- Onda 2 só começa depois da Onda 1 100% verificada (suíte completa de backend verde).
- Frontend tem duas verificações obrigatórias e independentes: `npx tsc --noEmit` **e** `npm test` (`node --test tests/*.test.mjs`) — rodar as duas, não só o typecheck (lição da sessão anterior).
- Commits diretos em `main`, sem branch/PR, um commit por task.

---

## ONDA 1 — Backend

### Task 1: Migração de schema — coluna `requer_aprovacao` + novo valor de `coluna_kanban`

**Files:**
- Modify: `docudata-backend/supabase_schema.sql:272-289` (CREATE TABLE tasks) e final do arquivo (bloco de ALTERs)
- Test: `docudata-backend/tests/test_pendente_aprovacao_schema.py`

**Interfaces:**
- Produces: coluna `tasks.requer_aprovacao boolean NOT NULL DEFAULT false`; `coluna_kanban` aceita `'pendente_aprovacao'` como 4º valor válido. Tasks seguintes (Pydantic/backend) assumem que essas duas mudanças já existem no banco de produção depois que o usuário rodar o SQL manualmente.

- [ ] **Step 1: Escrever o teste que descreve o schema esperado**

Crie `docudata-backend/tests/test_pendente_aprovacao_schema.py` (mesmo padrão de `tests/test_modos_schema.py` — lê o arquivo `.sql` como texto e confere substrings, não conecta em banco real):

```python
"""Confirma que a migração de 'Pendente de aprovação' está presente no
schema. Ver docs/superpowers/specs/2026-09-22-task-pendente-aprovacao-design.md."""
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def _texto_schema() -> str:
    return _SCHEMA.read_text()


def test_tasks_coluna_kanban_aceita_pendente_aprovacao():
    schema = _texto_schema()
    assert "CHECK (coluna_kanban IN ('planejado','em_andamento','pendente_aprovacao','concluida'))" in schema


def test_tasks_ganha_coluna_requer_aprovacao():
    schema = _texto_schema()
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS requer_aprovacao boolean NOT NULL DEFAULT false;" in schema


def test_tasks_tem_migracao_de_constraint_coluna_kanban():
    schema = _texto_schema()
    assert "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_coluna_kanban_check;" in schema
    assert "ADD CONSTRAINT tasks_coluna_kanban_check" in schema
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_pendente_aprovacao_schema.py -v`
Expected: FAIL nos três — nada disso existe em `supabase_schema.sql` ainda.

- [ ] **Step 3: Atualizar o `CREATE TABLE tasks` (linha 272-289) para bancos novos**

Em `docudata-backend/supabase_schema.sql`, troque:

```sql
    coluna_kanban       text        NOT NULL DEFAULT 'planejado'
                            CHECK (coluna_kanban IN ('planejado','em_andamento','concluida')),
```

por:

```sql
    coluna_kanban       text        NOT NULL DEFAULT 'planejado'
                            CHECK (coluna_kanban IN ('planejado','em_andamento','pendente_aprovacao','concluida')),
    requer_aprovacao    boolean     NOT NULL DEFAULT false,
```

- [ ] **Step 4: Adicionar o bloco de ALTERs pra bancos existentes (produção)**

No final de `docudata-backend/supabase_schema.sql`, adicione (antes dos comentários de índice no rodapé, junto aos outros `ALTER TABLE tasks` já existentes — procure por `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ordem_fila int;`, que é o último da tabela `tasks` hoje, e adicione logo depois):

```sql
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS requer_aprovacao boolean NOT NULL DEFAULT false;

-- Entrega "Pendente de aprovação": coluna_kanban ganha um 4º valor válido.
-- DROP + ADD porque é um CHECK sem nome próprio — Postgres nomeou
-- automaticamente como <tabela>_<coluna>_check na criação da tabela.
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_coluna_kanban_check;
ALTER TABLE tasks ADD CONSTRAINT tasks_coluna_kanban_check
    CHECK (coluna_kanban IN ('planejado','em_andamento','pendente_aprovacao','concluida'));
```

- [ ] **Step 5: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_pendente_aprovacao_schema.py -v`
Expected: PASS nos três.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/supabase_schema.sql docudata-backend/tests/test_pendente_aprovacao_schema.py
git commit -m "feat(tasks): schema para o estado pendente_aprovacao (requer_aprovacao + constraint de coluna_kanban)"
```

**⚠️ Aviso pro usuário nesta task:** o SQL do Step 4 precisa ser rodado manualmente no SQL Editor do Supabase antes de qualquer task seguinte funcionar em produção — nenhuma das próximas tasks aciona isso sozinho.

---

### Task 2: Modelos Pydantic e RBAC

**Files:**
- Modify: `docudata-backend/models/schemas.py:456` (`_COLUNAS_VALIDAS`), `:459-477` (`TaskCreate`), `:483-514` (`TaskUpdate`), `:517-549` (`TaskResponse`)
- Modify: `docudata-backend/routers/tasks.py:33-37` (`_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL`)
- Test: `docudata-backend/tests/test_task_schemas.py`, `docudata-backend/tests/test_modos_schemas_validation.py`

**Interfaces:**
- Produces: `TaskCreate.requer_aprovacao: bool = False`, `TaskUpdate.requer_aprovacao: Optional[bool] = None`, `TaskResponse.requer_aprovacao: bool = False`, novo `RejeitarTaskRequest(BaseModel)` com `motivo: str` (obrigatório, `min_length=1`) e `autor: Optional[str] = None`. `_COLUNAS_VALIDAS = {"planejado", "em_andamento", "pendente_aprovacao", "concluida"}`. Tasks 6 e 7 (endpoints `/aprovar`/`/rejeitar`) importam `RejeitarTaskRequest`.

- [ ] **Step 1: Escrever os testes que descrevem o schema novo**

Em `docudata-backend/tests/test_task_schemas.py`, adicione:

```python
def test_task_response_aceita_requer_aprovacao():
    resp = TaskResponse(
        id="t1", project_id="p1", titulo="X", pontos=3, coluna_kanban="pendente_aprovacao",
        bloqueado=False, checklist=[], ordem=0,
        created_at="2026-09-01T00:00:00Z", updated_at="2026-09-01T00:00:00Z",
        requer_aprovacao=True,
    )
    assert resp.requer_aprovacao is True


def test_task_response_requer_aprovacao_default_false():
    resp = TaskResponse(
        id="t1", project_id="p1", titulo="X", pontos=3, coluna_kanban="planejado",
        bloqueado=False, checklist=[], ordem=0,
        created_at="2026-09-01T00:00:00Z", updated_at="2026-09-01T00:00:00Z",
    )
    assert resp.requer_aprovacao is False
```

Em `docudata-backend/tests/test_modos_schemas_validation.py`, adicione (junto aos outros imports do topo, adicione `RejeitarTaskRequest` e `TaskCreate` à lista de `from models.schemas import (...)`):

```python
def test_task_create_aceita_coluna_pendente_aprovacao():
    t = TaskCreate(project_id="p1", titulo="X", pontos=1, coluna_kanban="pendente_aprovacao")
    assert t.coluna_kanban == "pendente_aprovacao"


def test_task_create_rejeita_coluna_invalida():
    with pytest.raises(ValidationError):
        TaskCreate(project_id="p1", titulo="X", pontos=1, coluna_kanban="arquivada")


def test_rejeitar_task_request_exige_motivo():
    with pytest.raises(ValidationError):
        RejeitarTaskRequest(motivo="")


def test_rejeitar_task_request_aceita_motivo_valido():
    r = RejeitarTaskRequest(motivo="Falta cobertura de teste")
    assert r.motivo == "Falta cobertura de teste"
    assert r.autor is None
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_task_schemas.py tests/test_modos_schemas_validation.py -v -k "requer_aprovacao or pendente_aprovacao or coluna_invalida or RejeitarTask or rejeitar_task"`
Expected: FAIL — `requer_aprovacao` não existe em `TaskResponse`, `coluna_kanban="pendente_aprovacao"` é rejeitado por `_COLUNAS_VALIDAS`, `RejeitarTaskRequest` não existe.

- [ ] **Step 3: Implementar em `models/schemas.py`**

Troque a linha 456:

```python
_COLUNAS_VALIDAS = {"planejado", "em_andamento", "concluida"}
```

por:

```python
_COLUNAS_VALIDAS = {"planejado", "em_andamento", "pendente_aprovacao", "concluida"}
```

Em `TaskCreate` (linha 459-470), adicione o campo (junto aos outros bools, após `extra`):

```python
class TaskCreate(BaseModel):
    project_id: str
    titulo: str
    pontos: int = Field(..., gt=0)
    funcionalidade_id: Optional[str] = None
    sprint_id: Optional[str] = None
    operacional_id: Optional[str] = None
    descricao: Optional[str] = None
    coluna_kanban: str = "planejado"
    checklist: Optional[list[dict]] = None  # [{texto, done}]
    ordem: int = 0
    extra: bool = False  # task concedida além do que a pessoa tinha; não consome orçamento
    requer_aprovacao: bool = False  # true: não pode ir direto pra concluida, precisa passar por pendente_aprovacao
```

Em `TaskUpdate` (linha 483-500), adicione (após `extra`):

```python
    extra: Optional[bool] = None
    requer_aprovacao: Optional[bool] = None
```

Em `TaskResponse` (linha 517-549), adicione (após `ordem_fila`):

```python
    ordem_fila: Optional[int] = None
    requer_aprovacao: bool = False
```

Logo antes de `class TaskReordenarItem` (linha 552), adicione o novo request model:

```python
class RejeitarTaskRequest(BaseModel):
    """POST /tasks/{id}/rejeitar — devolve uma task de pendente_aprovacao
    pra planejado, sem responsável. Ver spec, §4."""
    motivo: str = Field(..., min_length=1)
    autor: Optional[str] = None
```

- [ ] **Step 4: Atualizar RBAC em `routers/tasks.py`**

Troque (linha 33-37):

```python
_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL = {
    "titulo", "descricao", "pontos", "funcionalidade_id", "sprint_id",
    "operacional_id", "ordem", "extra", "bloqueado", "motivo_bloqueio",
    "bloqueado_manual", "bloqueado_por", "bloqueado_resolvido_por",
}
```

por:

```python
_CAMPOS_BLOQUEADOS_PARA_OPERACIONAL = {
    "titulo", "descricao", "pontos", "funcionalidade_id", "sprint_id",
    "operacional_id", "ordem", "extra", "bloqueado", "motivo_bloqueio",
    "bloqueado_manual", "bloqueado_por", "bloqueado_resolvido_por",
    "requer_aprovacao",
}
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_task_schemas.py tests/test_modos_schemas_validation.py -v`
Expected: PASS em todos (novos e já existentes no arquivo).

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/routers/tasks.py docudata-backend/tests/test_task_schemas.py docudata-backend/tests/test_modos_schemas_validation.py
git commit -m "feat(tasks): modelos Pydantic e RBAC pra requer_aprovacao e pendente_aprovacao"
```

---

### Task 3: `patch_task` — gates de transição (DoD, requer_aprovacao, travamento, saída bloqueada)

**Files:**
- Modify: `docudata-backend/routers/tasks.py` (`patch_task`, bloco de WIP/DoR/DoD ~linha 655-680, bloco de travamento ~linha 717-747)
- Test: novo `docudata-backend/tests/test_pendente_aprovacao_gates.py`

**Interfaces:**
- Consumes: `_COLUNAS_VALIDAS`, `TaskUpdate.requer_aprovacao` (Task 2).
- Produces: `patch_task` rejeita (422) qualquer tentativa de tirar uma task de `pendente_aprovacao` por PATCH direto; rejeita (422) `em_andamento → concluida` quando `task.requer_aprovacao` é `true`; exige DoD (checklist completo/vazio) tanto pra `concluida` quanto pra `pendente_aprovacao`; o relógio de travamento para de contar ao entrar em `pendente_aprovacao`. Tasks 6 e 7 (`/aprovar`, `/rejeitar`) são as únicas rotas que conseguem escrever `coluna_kanban` saindo de `pendente_aprovacao`.

- [ ] **Step 1: Escrever os testes que descrevem os gates**

Crie `docudata-backend/tests/test_pendente_aprovacao_gates.py`:

```python
"""Gates de transição do estado pendente_aprovacao em patch_task. Ver
docs/superpowers/specs/2026-09-22-task-pendente-aprovacao-design.md §4-5."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                empty = MagicMock()
                empty.data = []
                q.execute = MagicMock(return_value=empty)
                return q

            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"iniciada": True, "id": "sprint-1"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
            tbl.insert = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK_BASE = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "ordem": 0, "sprint_id": "sprint-1", "operacional_id": "op-1",
    "descricao": None, "bloqueado": False, "motivo_bloqueio": None,
    "checklist": [], "extra": False, "requer_aprovacao": False,
    "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task_overrides=None, cargo="gerente"):
        import routers.tasks as tasks_router
        from main import app
        task = {**_TASK_BASE, **(task_overrides or {})}
        mock_sb = _mock_client(task)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc
    return _make


def test_patch_bloqueia_saida_generica_de_pendente_aprovacao(make_client):
    tc = make_client({"coluna_kanban": "pendente_aprovacao"})

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 422
    assert "aprovar" in resp.json()["detail"].lower()


def test_patch_bloqueia_concluida_direto_quando_requer_aprovacao(make_client):
    tc = make_client({"coluna_kanban": "em_andamento", "requer_aprovacao": True, "checklist": []})

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 422
    assert "aprovação" in resp.json()["detail"].lower()


def test_patch_permite_concluida_direto_quando_nao_requer_aprovacao(make_client):
    tc = make_client({"coluna_kanban": "em_andamento", "requer_aprovacao": False, "checklist": []})

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "concluida"})

    assert resp.status_code == 200


def test_patch_permite_ir_para_pendente_aprovacao_com_checklist_vazio(make_client):
    tc = make_client({"coluna_kanban": "em_andamento", "checklist": []})

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 200
    assert resp.json()["coluna_kanban"] == "pendente_aprovacao"


def test_patch_bloqueia_pendente_aprovacao_com_checklist_incompleto(make_client):
    tc = make_client({
        "coluna_kanban": "em_andamento",
        "checklist": [{"texto": "item", "done": False}],
    })

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 409
    assert "DoD" in resp.json()["detail"]


def test_patch_para_relogio_de_travamento_ao_entrar_em_pendente_aprovacao(make_client):
    tc = make_client({
        "coluna_kanban": "em_andamento",
        "checklist": [],
        "entrou_em_andamento_em": "2026-09-01T00:00:00+00:00",
    })

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 200
    assert resp.json()["entrou_em_andamento_em"] is None
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_pendente_aprovacao_gates.py -v`
Expected: FAIL em pelo menos os testes de bloqueio (a task hoje aceita sair de `pendente_aprovacao` livremente e não olha `requer_aprovacao`) e no teste do relógio (hoje só `concluida` limpa `entrou_em_andamento_em`).

- [ ] **Step 3: Implementar em `patch_task` — bloco de WIP/DoR/DoD**

Em `docudata-backend/routers/tasks.py`, troque:

```python
    # WIP check — rejeita antes de qualquer escrita se o limite for ultrapassado
    coluna_nova = data.coluna_kanban
    coluna_atual = task.get("coluna_kanban")
    if coluna_nova is not None and coluna_nova != coluna_atual:
        # DoR: task sem sprint não pode ir para em_andamento
        sprint_efetivo = data.sprint_id if data.sprint_id is not None else task.get("sprint_id")
        if coluna_nova == "em_andamento" and not sprint_efetivo:
            raise HTTPException(
                status_code=409,
                detail="DoR: associe a task a uma sprint antes de movê-la para Em Andamento.",
            )
        # DoD: checklist deve estar completo (ou vazio) antes de ir para Concluída.
        # MET-07 (ganchos daily/commit/retrospectiva -> sinais de saúde) é explicitamente
        # NÃO implementado nesta task — deferido, não silenciosamente descartado.
        if coluna_nova == "concluida":
            checklist_efetivo = data.checklist if data.checklist is not None else task.get("checklist", [])
            pendentes = [item for item in (checklist_efetivo or []) if not item.get("done")]
            if pendentes:
                raise HTTPException(
                    status_code=409,
                    detail=f"DoD: {len(pendentes)} item(ns) do checklist ainda não concluído(s).",
                )
        op_efetivo = data.operacional_id if data.operacional_id is not None else task.get("operacional_id")
        ok, motivo = check_wip(client, project_id, op_efetivo, coluna_nova)
        if not ok:
            raise HTTPException(status_code=409, detail=motivo)
```

por:

```python
    # WIP check — rejeita antes de qualquer escrita se o limite for ultrapassado
    coluna_nova = data.coluna_kanban
    coluna_atual = task.get("coluna_kanban")
    if coluna_nova is not None and coluna_nova != coluna_atual:
        # Pendente de aprovação só sai via /aprovar ou /rejeitar (endpoints
        # dedicados, gerente/líder-only) — fecha a saída na origem, mesmo
        # princípio já aplicado a modo_trabalho na Entrega 4.
        if coluna_atual == "pendente_aprovacao":
            raise HTTPException(
                status_code=422,
                detail="Task em Pendente de aprovação só sai via POST /tasks/{id}/aprovar ou /tasks/{id}/rejeitar.",
            )
        # DoR: task sem sprint não pode ir para em_andamento
        sprint_efetivo = data.sprint_id if data.sprint_id is not None else task.get("sprint_id")
        if coluna_nova == "em_andamento" and not sprint_efetivo:
            raise HTTPException(
                status_code=409,
                detail="DoR: associe a task a uma sprint antes de movê-la para Em Andamento.",
            )
        # requer_aprovacao=true bloqueia o caminho rápido em_andamento -> concluida
        # — a task tem que passar por pendente_aprovacao primeiro.
        if coluna_nova == "concluida" and task.get("requer_aprovacao"):
            raise HTTPException(
                status_code=422,
                detail="Esta task requer aprovação do gerente — mova para Pendente de aprovação em vez de Concluída direto.",
            )
        # DoD: checklist deve estar completo (ou vazio) antes de ir para Concluída
        # ou Pendente de aprovação — a entrada em pendente_aprovacao é quando o
        # operacional declara o trabalho pronto, mesmo gate redirecionado.
        # MET-07 (ganchos daily/commit/retrospectiva -> sinais de saúde) é explicitamente
        # NÃO implementado nesta task — deferido, não silenciosamente descartado.
        if coluna_nova in ("concluida", "pendente_aprovacao"):
            checklist_efetivo = data.checklist if data.checklist is not None else task.get("checklist", [])
            pendentes = [item for item in (checklist_efetivo or []) if not item.get("done")]
            if pendentes:
                raise HTTPException(
                    status_code=409,
                    detail=f"DoD: {len(pendentes)} item(ns) do checklist ainda não concluído(s).",
                )
        op_efetivo = data.operacional_id if data.operacional_id is not None else task.get("operacional_id")
        ok, motivo = check_wip(client, project_id, op_efetivo, coluna_nova)
        if not ok:
            raise HTTPException(status_code=409, detail=motivo)
```

- [ ] **Step 4: Implementar o carve-out no relógio de travamento**

Na mesma função, troque:

```python
        if coluna_efetiva == "concluida" or not sprint_efetivo_id:
            sprint_iniciada = False
```

por:

```python
        if coluna_efetiva in ("concluida", "pendente_aprovacao") or not sprint_efetivo_id:
            sprint_iniciada = False
```

- [ ] **Step 5: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_pendente_aprovacao_gates.py -v`
Expected: PASS em todos os seis.

- [ ] **Step 6: Rodar a suíte de regressão de patch_task**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_tasks_dod_gate.py tests/test_travamento_relogio.py tests/test_bloqueio_manual.py tests/test_task_rbac_operacional.py tests/test_tasks_pull_lock_atribuicao.py -v`
Expected: PASS em tudo — nenhum desses arquivos manda `coluna_kanban` saindo de `pendente_aprovacao` nem depende de `requer_aprovacao`, então o comportamento anterior continua intacto.

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_pendente_aprovacao_gates.py
git commit -m "feat(tasks): gates de transição pra pendente_aprovacao (DoD, requer_aprovacao, travamento, saída bloqueada)"
```

---

### Task 4: `mover_task` — aceitar `pendente_aprovacao` como destino de drag-and-drop

**Files:**
- Modify: `docudata-backend/routers/tasks.py:807-818` (`mover_task`)
- Test: novo `docudata-backend/tests/test_mover_task_pendente_aprovacao.py`

**Interfaces:**
- Consumes: `patch_task` (Task 3) — `mover_task` delega pra ele, então os gates da Task 3 já se aplicam automaticamente.
- Produces: `POST /tasks/{id}/mover?coluna_destino=pendente_aprovacao` funciona (200, sujeito aos mesmos gates de `patch_task`). Onda 2 (drag-and-drop do frontend) depende disso.

- [ ] **Step 1: Escrever o teste**

Crie `docudata-backend/tests/test_mover_task_pendente_aprovacao.py`:

```python
"""mover_task (drag-and-drop) precisa aceitar pendente_aprovacao — sua lista
de colunas válidas era separada de _COLUNAS_VALIDAS e ficou desincronizada."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                empty = MagicMock()
                empty.data = []
                q.execute = MagicMock(return_value=empty)
                return q

            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
            tbl.insert = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "em_andamento", "ordem": 0, "sprint_id": "sprint-1",
    "operacional_id": "op-1", "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": False, "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make():
        import routers.tasks as tasks_router
        from main import app
        mock_sb = _mock_client(_TASK)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc
    return _make


def test_mover_task_aceita_pendente_aprovacao_como_destino(make_client):
    tc = make_client()

    resp = tc.post("/tasks/task-1/mover?coluna_destino=pendente_aprovacao")

    assert resp.status_code == 200
    assert resp.json()["coluna_kanban"] == "pendente_aprovacao"


def test_mover_task_ainda_rejeita_coluna_invalida(make_client):
    tc = make_client()

    resp = tc.post("/tasks/task-1/mover?coluna_destino=arquivada")

    assert resp.status_code == 422
```

- [ ] **Step 2: Rodar os testes e confirmar que o primeiro falha**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_mover_task_pendente_aprovacao.py -v`
Expected: FAIL em `test_mover_task_aceita_pendente_aprovacao_como_destino` (422 hoje, `coluna_destino inválida`); PASS em `test_mover_task_ainda_rejeita_coluna_invalida` (já funciona).

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/tasks.py`, troque:

```python
    if coluna_destino not in {"planejado", "em_andamento", "concluida"}:
        raise HTTPException(status_code=422, detail="coluna_destino inválida")
```

por:

```python
    if coluna_destino not in _COLUNAS_VALIDAS:
        raise HTTPException(status_code=422, detail="coluna_destino inválida")
```

(`_COLUNAS_VALIDAS` já vem importado de `models.schemas` no topo do arquivo — confira o import existente antes de assumir que precisa adicionar um novo; se `_COLUNAS_VALIDAS` não estiver no `from models.schemas import (...)` do topo do arquivo, adicione à lista.)

- [ ] **Step 4: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_mover_task_pendente_aprovacao.py -v`
Expected: PASS nos dois.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_mover_task_pendente_aprovacao.py
git commit -m "fix(tasks): mover_task aceita pendente_aprovacao — lista de colunas válidas estava desincronizada de _COLUNAS_VALIDAS"
```

---

### Task 5: Emails — templates e avisos (entrada em aprovação, rejeição)

**Files:**
- Modify: `docudata-backend/services/email_service.py` (novos templates, após `email_modo_pull_ativado`)
- Modify: `docudata-backend/routers/tasks.py` (import de email, novas funções `_avisar_gerente_pendente_aprovacao`/`_avisar_operacional_rejeicao`, wiring no bloco de pós-transição de `patch_task`)
- Test: `docudata-backend/tests/test_aviso_pendente_aprovacao_email.py`

**Interfaces:**
- Produces: `email_task_pendente_aprovacao(projeto_nome, operacional_nome, task_titulo) -> tuple[str, str]`, `email_task_rejeitada(projeto_nome, task_titulo, motivo) -> tuple[str, str]` em `services/email_service.py`. `_avisar_gerente_pendente_aprovacao(client, task)` e `_avisar_operacional_rejeicao(client, task, motivo)` em `routers/tasks.py` (best-effort, mesmo padrão de `_avisar_gerente_task_concluida`). Task 7 (`/rejeitar`) chama `_avisar_operacional_rejeicao`.

- [ ] **Step 1: Escrever os testes de template**

Crie `docudata-backend/tests/test_aviso_pendente_aprovacao_email.py`:

```python
"""Entrega Pendente de aprovação: aviso por email ao entrar em aprovação
(gerente/líder) e ao rejeitar (operacional). Mesmo padrão best-effort de
_avisar_gerente_task_concluida. Ver spec §7."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.email_service import email_task_pendente_aprovacao, email_task_rejeitada


def test_email_task_pendente_aprovacao_conteudo():
    subject, html = email_task_pendente_aprovacao("Projeto X", "Davi", "Fazer algo")
    assert "Fazer algo" in subject
    assert "Davi" in html
    assert "Projeto X" in html


def test_email_task_rejeitada_conteudo():
    subject, html = email_task_rejeitada("Projeto X", "Fazer algo", "Faltou o teste unitário")
    assert "Fazer algo" in subject
    assert "Faltou o teste unitário" in html
    assert "Projeto X" in html


def _mock_client(task):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                empty = MagicMock()
                empty.data = []
                q.execute = MagicMock(return_value=empty)
                return q

            def insert_side_effect(payload):
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"nome": "Davi", "email": "davi@citi.com"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"name": "Projeto X"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "pessoa":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"email": "ger@citi.com"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_TASK = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "em_andamento", "ordem": 0, "sprint_id": "sprint-1",
    "operacional_id": "op-1", "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": False, "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(cargo="gerente"):
        import routers.tasks as tasks_router
        from main import app
        mock_sb = _mock_client(_TASK)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        envios = []
        monkeypatch.setattr(
            tasks_router, "send_email",
            lambda to, subject, html: envios.append((to, subject, html)),
        )
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, envios
    return _make


def test_entrar_em_pendente_aprovacao_avisa_gerente(make_client):
    tc, envios = make_client()

    resp = tc.patch("/tasks/task-1", json={"coluna_kanban": "pendente_aprovacao"})

    assert resp.status_code == 200
    assert len(envios) == 1
    to, subject, html = envios[0]
    assert to == "ger@citi.com"
    assert "Fazer algo" in subject
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_aviso_pendente_aprovacao_email.py -v`
Expected: FAIL — `email_task_pendente_aprovacao`/`email_task_rejeitada` ainda não existem (ImportError), e `envios` continua vazio no teste de integração.

- [ ] **Step 3: Adicionar os templates em `services/email_service.py`**

Logo depois de `email_modo_pull_ativado` (antes de `email_esqueci_senha`), adicione:

```python
def email_task_pendente_aprovacao(projeto_nome: str, operacional_nome: str, task_titulo: str) -> tuple[str, str]:
    """Retorna (subject, html) pro aviso de que uma task está esperando
    aprovação do gerente (Entrega Pendente de aprovação)."""
    subject = f"[DocuData] Task aguardando aprovação: {task_titulo}"
    corpo = f"""
    <p><strong>{operacional_nome}</strong> marcou a task <strong>{task_titulo}</strong> como pronta no projeto <strong>{projeto_nome}</strong> — ela está esperando sua aprovação.</p>
    <p>Acesse o DocuData e aprove ou rejeite na coluna "Pendente de aprovação".</p>
    """
    return subject, _base_template("Task aguardando aprovação", corpo, badge="Aprovação pendente")


def email_task_rejeitada(projeto_nome: str, task_titulo: str, motivo: str) -> tuple[str, str]:
    """Retorna (subject, html) pro aviso de que uma task foi rejeitada e
    voltou para a fila (Entrega Pendente de aprovação)."""
    subject = f"[DocuData] Task rejeitada: {task_titulo}"
    corpo = f"""
    <p>Sua task <strong>{task_titulo}</strong> no projeto <strong>{projeto_nome}</strong> foi rejeitada e voltou para a fila.</p>
    <p style="background:#fef2f2;border-radius:8px;padding:10px 14px;"><strong>Motivo:</strong><br>{motivo}</p>
    """
    return subject, _base_template("Task rejeitada", corpo, badge="Rejeitada")
```

- [ ] **Step 4: Adicionar as funções de aviso e o import em `routers/tasks.py`**

Troque o import existente:

```python
from services.email_service import email_task_atribuida, email_task_concluida, send_email
```

por:

```python
from services.email_service import (
    email_task_atribuida,
    email_task_concluida,
    email_task_pendente_aprovacao,
    email_task_rejeitada,
    send_email,
)
```

Logo depois de `_avisar_gerente_task_concluida` (mesmo arquivo), adicione:

```python
def _avisar_gerente_pendente_aprovacao(client, task: dict) -> None:
    """Best-effort: avisa gerente/líder que uma task está esperando
    aprovação. A transição vale mesmo que o e-mail falhe."""
    try:
        proj = client.table("projects").select("name").eq("id", task["project_id"]).execute().data
        projeto_nome = proj[0]["name"] if proj else "projeto"

        operacional_nome = "Alguém"
        op_id = task.get("operacional_id")
        if op_id:
            op = client.table("operacionais").select("nome").eq("id", op_id).execute().data
            if op:
                operacional_nome = op[0]["nome"]

        gerentes = (
            client.table("pessoa").select("email").in_("cargo", ["gerente", "lider"]).execute().data or []
        )
        if not gerentes:
            return

        subject, html = email_task_pendente_aprovacao(projeto_nome, operacional_nome, task["titulo"])
        for g in gerentes:
            send_email(g["email"], subject, html)
    except Exception as exc:
        _LOG.warning("notificacao_pendente_aprovacao_falhou exc=%s", type(exc).__name__)


def _avisar_operacional_rejeicao(client, task: dict, motivo: str) -> None:
    """Best-effort: avisa o operacional que estava na task que ela foi
    rejeitada. A rejeição vale mesmo que o e-mail falhe."""
    try:
        operacional_id = task.get("operacional_id")
        if not operacional_id:
            return
        op = client.table("operacionais").select("nome, email").eq("id", operacional_id).execute().data
        if not op or not op[0].get("email"):
            return
        proj = client.table("projects").select("name").eq("id", task["project_id"]).execute().data
        projeto_nome = proj[0]["name"] if proj else "projeto"

        subject, html = email_task_rejeitada(projeto_nome, task["titulo"], motivo)
        send_email(op[0]["email"], subject, html)
    except Exception as exc:
        _LOG.warning("notificacao_rejeicao_falhou exc=%s", type(exc).__name__)
```

- [ ] **Step 5: Conectar o aviso ao entrar em `pendente_aprovacao` dentro de `patch_task`**

No bloco de pós-transição de `patch_task` (perto do final da função), troque:

```python
    if coluna_nova is not None and coluna_nova != coluna_atual:
        on_task_transition(client, task, "coluna_kanban", coluna_atual, coluna_nova)
        if coluna_nova == "concluida":
            sprint_id_atual = task.get("sprint_id")
            if sprint_id_atual:
                try:
                    auto_update_sprint_health(client, sprint_id_atual)
                except Exception:
                    pass  # best-effort
            if pessoa["cargo"] == "operacional":
                _avisar_gerente_task_concluida(client, result.data[0])
```

por:

```python
    if coluna_nova is not None and coluna_nova != coluna_atual:
        on_task_transition(client, task, "coluna_kanban", coluna_atual, coluna_nova)
        if coluna_nova == "concluida":
            sprint_id_atual = task.get("sprint_id")
            if sprint_id_atual:
                try:
                    auto_update_sprint_health(client, sprint_id_atual)
                except Exception:
                    pass  # best-effort
            if pessoa["cargo"] == "operacional":
                _avisar_gerente_task_concluida(client, result.data[0])
        elif coluna_nova == "pendente_aprovacao":
            _avisar_gerente_pendente_aprovacao(client, result.data[0])
```

- [ ] **Step 6: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_aviso_pendente_aprovacao_email.py -v`
Expected: PASS em todos.

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/services/email_service.py docudata-backend/routers/tasks.py docudata-backend/tests/test_aviso_pendente_aprovacao_email.py
git commit -m "feat(tasks): notifica gerente/líder ao entrar em pendente_aprovacao (reusa o fluxo de email já existente)"
```

---

### Task 6: `POST /tasks/{id}/aprovar`

**Files:**
- Modify: `docudata-backend/routers/tasks.py` (novo endpoint, perto de `devolver_task`)
- Test: novo `docudata-backend/tests/test_aprovar_task.py`

**Interfaces:**
- Consumes: `_registrar_task_transicao` (já existe no arquivo), `on_task_transition`, `auto_update_sprint_health` (já importados), `require_not_operacional` (já importado).
- Produces: `POST /tasks/{id}/aprovar?autor=<opcional>` (RBAC gerente/líder) — 404 se task não existe, 409 se não está em `pendente_aprovacao`, senão move pra `concluida`, grava a transição (essencial pra `_resolver_quem_completou` em `services/pontuacao.py` atribuir os pontos certo), dispara `on_task_transition`/`auto_update_sprint_health`. Nenhuma outra task depende deste endpoint.

- [ ] **Step 1: Escrever os testes**

Crie `docudata-backend/tests/test_aprovar_task.py`:

```python
"""POST /tasks/{id}/aprovar — só gerente/líder, só sai de pendente_aprovacao
pra concluida. Ver spec §4, §6, §8."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task):
    tasks_update = []
    transicoes_insert = []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                tasks_update.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                empty = MagicMock()
                empty.data = []
                q.execute = MagicMock(return_value=empty)
                return q

            def insert_side_effect(payload):
                transicoes_insert.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, tasks_update, transicoes_insert


_TASK_PENDENTE = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "pendente_aprovacao", "ordem": 0, "sprint_id": "sprint-1",
    "operacional_id": "op-1", "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": True, "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task=None, cargo="gerente"):
        import routers.tasks as tasks_router
        from main import app
        mock_sb, tasks_update, transicoes_insert = _mock_client(task or _TASK_PENDENTE)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, tasks_update, transicoes_insert
    return _make


def test_aprovar_move_para_concluida(make_client):
    tc, tasks_update, transicoes_insert = make_client()

    resp = tc.post("/tasks/task-1/aprovar")

    assert resp.status_code == 200
    assert resp.json()["coluna_kanban"] == "concluida"
    assert tasks_update[-1]["coluna_kanban"] == "concluida"


def test_aprovar_grava_transicao_para_concluida(make_client):
    tc, tasks_update, transicoes_insert = make_client()

    tc.post("/tasks/task-1/aprovar")

    assert len(transicoes_insert) == 1
    assert transicoes_insert[0]["campo"] == "coluna_kanban"
    assert transicoes_insert[0]["para"] == "concluida"


def test_aprovar_rejeita_task_que_nao_esta_pendente(make_client):
    task = {**_TASK_PENDENTE, "coluna_kanban": "em_andamento"}
    tc, tasks_update, _ = make_client(task=task)

    resp = tc.post("/tasks/task-1/aprovar")

    assert resp.status_code == 409
    assert tasks_update == []


def test_aprovar_bloqueia_operacional(make_client):
    tc, tasks_update, _ = make_client(cargo="operacional")

    resp = tc.post("/tasks/task-1/aprovar")

    assert resp.status_code == 403
    assert tasks_update == []
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_aprovar_task.py -v`
Expected: FAIL — rota `/tasks/{id}/aprovar` não existe (404 genérico do FastAPI ao invés dos status codes esperados).

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/tasks.py`, adicione o endpoint logo depois de `devolver_task` (antes de `@router.get("/{task_id}", response_model=TaskResponse)`):

```python
@router.post("/{task_id}/aprovar", response_model=TaskResponse)
async def aprovar_task(
    task_id: str,
    autor: Optional[str] = None,
    pessoa: dict = Depends(require_not_operacional),
):
    """Só gerente/líder — aprova uma task em Pendente de aprovação, movendo
    pra Concluída. Único jeito de sair de pendente_aprovacao pra concluida
    (patch_task bloqueia a saída genérica — ver o gate em patch_task)."""
    client = get_client()
    resp = client.table("tasks").select("*").eq("id", task_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = resp.data[0]
    if task.get("coluna_kanban") != "pendente_aprovacao":
        raise HTTPException(status_code=409, detail="Task não está em Pendente de aprovação.")

    agora = datetime.now(timezone.utc)
    _registrar_task_transicao(client, task_id, task, "coluna_kanban", "concluida", autor, None, agora)

    result = client.table("tasks").update({
        "coluna_kanban": "concluida",
        "updated_at": agora.isoformat(),
    }).eq("id", task_id).execute()

    on_task_transition(client, task, "coluna_kanban", "pendente_aprovacao", "concluida")
    sprint_id_atual = task.get("sprint_id")
    if sprint_id_atual:
        try:
            auto_update_sprint_health(client, sprint_id_atual)
        except Exception:
            pass  # best-effort

    return result.data[0]
```

- [ ] **Step 4: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_aprovar_task.py -v`
Expected: PASS nos quatro.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_aprovar_task.py
git commit -m "feat(tasks): POST /tasks/{id}/aprovar — único caminho de pendente_aprovacao pra concluida"
```

---

### Task 7: `POST /tasks/{id}/rejeitar`

**Files:**
- Modify: `docudata-backend/routers/tasks.py` (novo endpoint, logo após `aprovar_task`)
- Test: novo `docudata-backend/tests/test_rejeitar_task.py`

**Interfaces:**
- Consumes: `RejeitarTaskRequest` (Task 2), `_avisar_operacional_rejeicao` (Task 5), `_registrar_task_transicao`/`on_task_transition` (já existentes).
- Produces: `POST /tasks/{id}/rejeitar` com body `{"motivo": str, "autor"?: str}` (RBAC gerente/líder) — 404/409 iguais ao `/aprovar`, 422 se `motivo` vazio (validação Pydantic). Limpa `operacional_id`, move pra `planejado`, recalcula `ordem_fila` (mesmo padrão de `devolver_task`), **sem** penalidade de travamento, dispara email pro operacional.

- [ ] **Step 1: Escrever os testes**

Crie `docudata-backend/tests/test_rejeitar_task.py`:

```python
"""POST /tasks/{id}/rejeitar — só gerente/líder, limpa responsável e volta
pra planejado sem penalidade. Ver spec §4."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task, fila_existente=None):
    fila_existente = fila_existente or []
    tasks_update = []
    transicoes_insert = []
    envios = []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()

                def eq_effect(field, value):
                    if field == "coluna_kanban" and value == "planejado":
                        resp_fila = MagicMock()
                        resp_fila.data = fila_existente
                        q2 = MagicMock()
                        q2.execute = MagicMock(return_value=resp_fila)
                        return q2
                    return q

                q.eq = MagicMock(side_effect=eq_effect)
                resp = MagicMock()
                resp.data = [dict(task)]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                tasks_update.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(task, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.limit = MagicMock(return_value=q)
                empty = MagicMock()
                empty.data = []
                q.execute = MagicMock(return_value=empty)
                return q

            def insert_side_effect(payload):
                transicoes_insert.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id="transicao-1")]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"nome": "Davi", "email": "davi@citi.com"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"name": "Projeto X"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        else:
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, tasks_update, transicoes_insert, envios


_TASK_PENDENTE = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "pendente_aprovacao", "ordem": 0, "sprint_id": "sprint-1",
    "operacional_id": "op-1", "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "requer_aprovacao": True, "travado_automatico": False,
    "entrou_em_andamento_em": None, "pull_em": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task=None, cargo="gerente", fila_existente=None):
        import routers.tasks as tasks_router
        from main import app
        mock_sb, tasks_update, transicoes_insert, envios = _mock_client(task or _TASK_PENDENTE, fila_existente)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        monkeypatch.setattr(
            tasks_router, "send_email",
            lambda to, subject, html: envios.append((to, subject, html)),
        )
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, tasks_update, transicoes_insert, envios
    return _make


def test_rejeitar_limpa_responsavel_e_volta_pra_planejado(make_client):
    tc, tasks_update, _, _ = make_client()

    resp = tc.post("/tasks/task-1/rejeitar", json={"motivo": "Faltou cobrir o edge case"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["coluna_kanban"] == "planejado"
    assert body["operacional_id"] is None
    assert tasks_update[-1]["travado_automatico"] is False


def test_rejeitar_exige_motivo(make_client):
    tc, tasks_update, _, _ = make_client()

    resp = tc.post("/tasks/task-1/rejeitar", json={"motivo": ""})

    assert resp.status_code == 422
    assert tasks_update == []


def test_rejeitar_avisa_operacional_por_email(make_client):
    tc, _, _, envios = make_client()

    tc.post("/tasks/task-1/rejeitar", json={"motivo": "Faltou cobrir o edge case"})

    assert len(envios) == 1
    to, subject, html = envios[0]
    assert to == "davi@citi.com"
    assert "Faltou cobrir o edge case" in html


def test_rejeitar_rejeita_task_que_nao_esta_pendente(make_client):
    task = {**_TASK_PENDENTE, "coluna_kanban": "em_andamento"}
    tc, tasks_update, _, _ = make_client(task=task)

    resp = tc.post("/tasks/task-1/rejeitar", json={"motivo": "x"})

    assert resp.status_code == 409
    assert tasks_update == []


def test_rejeitar_bloqueia_operacional(make_client):
    tc, tasks_update, _, _ = make_client(cargo="operacional")

    resp = tc.post("/tasks/task-1/rejeitar", json={"motivo": "x"})

    assert resp.status_code == 403
    assert tasks_update == []
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_rejeitar_task.py -v`
Expected: FAIL — rota não existe ainda.

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/tasks.py`, adicione logo depois de `aprovar_task`:

```python
@router.post("/{task_id}/rejeitar", response_model=TaskResponse)
async def rejeitar_task(
    task_id: str,
    data: RejeitarTaskRequest,
    pessoa: dict = Depends(require_not_operacional),
):
    """Só gerente/líder — rejeita uma task em Pendente de aprovação: limpa o
    responsável e volta pra planejado (fila), sem penalidade de travamento
    (o relógio já estava pausado desde a entrada em pendente_aprovacao)."""
    client = get_client()
    resp = client.table("tasks").select("*").eq("id", task_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = resp.data[0]
    if task.get("coluna_kanban") != "pendente_aprovacao":
        raise HTTPException(status_code=409, detail="Task não está em Pendente de aprovação.")

    agora = datetime.now(timezone.utc)
    _registrar_task_transicao(client, task_id, task, "coluna_kanban", "planejado", data.autor, data.motivo, agora)

    fila = client.table("tasks").select("ordem_fila").eq("project_id", task["project_id"]).eq("coluna_kanban", "planejado").execute().data or []
    max_ordem = max((t.get("ordem_fila") or 0) for t in fila) if fila else 0

    result = client.table("tasks").update({
        "operacional_id": None,
        "coluna_kanban": "planejado",
        "pull_em": None,
        "entrou_em_andamento_em": None,
        "travado_automatico": False,
        "ordem_fila": max_ordem + 1,
        "updated_at": agora.isoformat(),
    }).eq("id", task_id).execute()

    on_task_transition(client, task, "coluna_kanban", "pendente_aprovacao", "planejado")
    _avisar_operacional_rejeicao(client, task, data.motivo)

    return result.data[0]
```

Adicione `RejeitarTaskRequest` ao import de `models.schemas` no topo do arquivo (junto aos outros: `TaskCreate`, `TaskUpdate`, `TaskResponse`, etc.).

- [ ] **Step 4: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_rejeitar_task.py -v`
Expected: PASS nos cinco.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_rejeitar_task.py
git commit -m "feat(tasks): POST /tasks/{id}/rejeitar — devolve pra fila sem penalidade, avisa o operacional"
```

---

### Task 8: CFD — 4ª faixa `pendente_aprovacao`

**Files:**
- Modify: `docudata-backend/routers/metricas.py:184-223` (`get_cfd`)
- Test: `docudata-backend/tests/test_metricas_comparacao.py` (ou novo arquivo, verifique se já existe teste de `get_cfd`; se não existir, crie `docudata-backend/tests/test_cfd_pendente_aprovacao.py`)

**Interfaces:**
- Produces: `GET /metricas/{project_id}/cfd` inclui a chave `pendente_aprovacao` em cada ponto retornado. Onda 2 (Task 13, `MetricasTab.tsx`) consome esse campo novo.

- [ ] **Step 1: Escrever o teste**

Crie `docudata-backend/tests/test_cfd_pendente_aprovacao.py`:

```python
"""GET /metricas/{id}/cfd soma a faixa pendente_aprovacao — senão essas
tasks somem silenciosamente do gráfico. Ver spec §10."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client():
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "proj-1"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "sprint-1", "numero": 1}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [
                {"coluna_kanban": "planejado"},
                {"coluna_kanban": "em_andamento"},
                {"coluna_kanban": "pendente_aprovacao"},
                {"coluna_kanban": "pendente_aprovacao"},
                {"coluna_kanban": "concluida"},
            ]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


@pytest.fixture
def make_client(monkeypatch):
    import routers.metricas as metricas_router
    from main import app
    mock_sb = _mock_client()
    monkeypatch.setattr(metricas_router, "get_client", lambda: mock_sb)
    return TestClient(app)


def test_cfd_soma_pendente_aprovacao(make_client):
    resp = make_client.get("/metricas/proj-1/cfd")

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["pendente_aprovacao"] == 2
    assert body[0]["planejado"] == 1
    assert body[0]["em_andamento"] == 1
    assert body[0]["concluida"] == 1
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_cfd_pendente_aprovacao.py -v`
Expected: FAIL com `KeyError: 'pendente_aprovacao'` — a chave não existe na resposta hoje.

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/metricas.py`, dentro de `get_cfd`, troque:

```python
        planejado = sum(1 for t in tasks if t["coluna_kanban"] == "planejado")
        em_andamento = sum(1 for t in tasks if t["coluna_kanban"] == "em_andamento")
        concluida = sum(1 for t in tasks if t["coluna_kanban"] == "concluida")
        if tasks:
            result.append({
                "sprint_numero": s["numero"],
                "planejado": planejado,
                "em_andamento": em_andamento,
                "concluida": concluida,
            })
```

por:

```python
        planejado = sum(1 for t in tasks if t["coluna_kanban"] == "planejado")
        em_andamento = sum(1 for t in tasks if t["coluna_kanban"] == "em_andamento")
        pendente_aprovacao = sum(1 for t in tasks if t["coluna_kanban"] == "pendente_aprovacao")
        concluida = sum(1 for t in tasks if t["coluna_kanban"] == "concluida")
        if tasks:
            result.append({
                "sprint_numero": s["numero"],
                "planejado": planejado,
                "em_andamento": em_andamento,
                "pendente_aprovacao": pendente_aprovacao,
                "concluida": concluida,
            })
```

- [ ] **Step 4: Rodar o teste de novo e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_cfd_pendente_aprovacao.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/metricas.py docudata-backend/tests/test_cfd_pendente_aprovacao.py
git commit -m "feat(metricas): CFD soma a faixa pendente_aprovacao"
```

---

### Task 9: Verificação final da Onda 1

**Files:** nenhum arquivo novo — só verificação.

- [ ] **Step 1: Rodar a suíte completa do backend**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q`
Expected: PASS em tudo (todos os arquivos de `tests/`, não só os tocados nesta onda).

- [ ] **Step 2: Confirmar com o usuário antes de avançar pra Onda 2**

Reporte quantos testes novos foram adicionados e o resultado da suíte completa. Lembre explicitamente o usuário de rodar o SQL da Task 1 em produção antes de testar qualquer coisa desta feature ao vivo — nenhuma task seguinte depende disso pra passar nos testes automatizados (que usam mocks), mas a feature real não funciona sem a migração aplicada. Só prossiga pra Onda 2 depois de confirmação explícita.

---

## ONDA 2 — Frontend

### Task 10: `api.ts` — tipos e funções novas

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts:1635-1668` (`TaskKanbanResponse`), `:1699-1721` (`createTaskKanban`), `:1723-1755` (`patchTaskKanban`), `:1854-1859` (`CfdPoint`)

**Interfaces:**
- Produces: `TaskKanbanResponse.coluna_kanban` aceita `"pendente_aprovacao"`; `TaskKanbanResponse.requer_aprovacao: boolean`; `createTaskKanban`/`patchTaskKanban` aceitam `requer_aprovacao?: boolean` no payload; `aprovarTask(id: string): Promise<TaskKanbanResponse>`; `rejeitarTask(id: string, motivo: string): Promise<TaskKanbanResponse>`; `CfdPoint.pendente_aprovacao: number`. Tasks 11-13 consomem essas funções/tipos.

- [ ] **Step 1: Atualizar `TaskKanbanResponse`**

Em `docudata-frontend/app/lib/api.ts`, troque:

```typescript
  coluna_kanban: "planejado" | "em_andamento" | "concluida";
```

por:

```typescript
  coluna_kanban: "planejado" | "em_andamento" | "pendente_aprovacao" | "concluida";
```

E adicione, logo após `ordem_fila?: number | null;` (ainda dentro de `TaskKanbanResponse`):

```typescript
  ordem_fila?: number | null;
  requer_aprovacao: boolean;
```

- [ ] **Step 2: Atualizar `createTaskKanban` e `patchTaskKanban`**

Em `createTaskKanban`, adicione ao objeto de parâmetros (após `checklist?`):

```typescript
  checklist?: { texto: string; done: boolean }[];
  requer_aprovacao?: boolean;
```

Em `patchTaskKanban`, adicione ao objeto `data` (após `extra?`):

```typescript
    extra?: boolean;
    requer_aprovacao?: boolean;
```

- [ ] **Step 3: Adicionar `aprovarTask` e `rejeitarTask`**

Logo depois de `overrideTravamentoTask` (mesma seção de ações de task), adicione:

```typescript
export async function aprovarTask(id: string, autor?: string): Promise<TaskKanbanResponse> {
  const q = new URLSearchParams();
  if (autor) q.set("autor", autor);
  const res = await apiFetch(`${API}/tasks/${id}/aprovar?${q}`, { method: "POST" });
  if (res.status === 409) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error((err as { detail?: string }).detail ?? "Task não está em Pendente de aprovação"), { status: 409 });
  }
  if (!res.ok) throw new Error("Erro ao aprovar task");
  return res.json();
}

export async function rejeitarTask(id: string, motivo: string, autor?: string): Promise<TaskKanbanResponse> {
  const res = await apiFetch(`${API}/tasks/${id}/rejeitar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ motivo, autor }),
  });
  if (res.status === 409) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error((err as { detail?: string }).detail ?? "Task não está em Pendente de aprovação"), { status: 409 });
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao rejeitar task");
  }
  return res.json();
}
```

- [ ] **Step 4: Atualizar `CfdPoint`**

Troque:

```typescript
export interface CfdPoint {
  sprint_numero: number;
  planejado: number;
  em_andamento: number;
  concluida: number;
}
```

por:

```typescript
export interface CfdPoint {
  sprint_numero: number;
  planejado: number;
  em_andamento: number;
  pendente_aprovacao: number;
  concluida: number;
}
```

- [ ] **Step 5: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: sem erros novos neste arquivo. Erros em `TasksKanbanTab.tsx`/`MetricasTab.tsx` sobre `coluna_kanban`/`CfdPoint` incompletos são esperados até as Tasks 11-13 — se aparecerem, confirme que são exatamente esses e não algo inesperado.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/lib/api.ts
git commit -m "feat(api): tipos e funções pra pendente_aprovacao (aprovarTask, rejeitarTask, requer_aprovacao)"
```

---

### Task 11: Kanban — 4ª coluna e checkbox "Requer aprovação"

**Files:**
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx:40-46` (`Coluna`, `COLUNAS`), `:119-209` (`TaskModal` — estado e `handleSubmit`), `:327-336` (bloco "Task extra")

**Interfaces:**
- Consumes: `aprovarTask`/`rejeitarTask`/`requer_aprovacao` (Task 10).
- Produces: o board renderiza 4 colunas; `TaskModal` tem um novo estado `requerAprovacao` enviado em criar/editar. Task 12 consome o mesmo `TaskModal` pra adicionar os botões Aprovar/Rejeitar.

- [ ] **Step 1: Adicionar a 4ª coluna**

Troque:

```typescript
type Coluna = "planejado" | "em_andamento" | "concluida";

const COLUNAS: { id: Coluna; label: string; color: string; bg: string }[] = [
  { id: "planejado", label: "Planejado", color: "#374151", bg: "#f1f5f9" },
  { id: "em_andamento", label: "Em andamento", color: "#a16207", bg: "#fef9c3" },
  { id: "concluida", label: "Concluída", color: "#166534", bg: "#dcfce7" },
];
```

por:

```typescript
type Coluna = "planejado" | "em_andamento" | "pendente_aprovacao" | "concluida";

const COLUNAS: { id: Coluna; label: string; color: string; bg: string }[] = [
  { id: "planejado", label: "Planejado", color: "#374151", bg: "#f1f5f9" },
  { id: "em_andamento", label: "Em andamento", color: "#a16207", bg: "#fef9c3" },
  { id: "pendente_aprovacao", label: "Pendente de aprovação", color: "#7c3aed", bg: "#ede9fe" },
  { id: "concluida", label: "Concluída", color: "#166534", bg: "#dcfce7" },
];
```

- [ ] **Step 2: Adicionar o estado `requerAprovacao` em `TaskModal`**

Logo após `const [extra, setExtra] = useState(task?.extra ?? false);`, adicione:

```typescript
  const [requerAprovacao, setRequerAprovacao] = useState(task?.requer_aprovacao ?? false);
```

- [ ] **Step 3: Enviar o campo em `handleSubmit`**

Em `createTaskKanban({...})`, adicione `extra,` seguido de `requer_aprovacao: requerAprovacao,`. Em `patchTaskKanban(task!.id, {...})`, adicione `extra,` seguido de `requer_aprovacao: requerAprovacao,` (mesma posição, logo após o `extra` existente nos dois `try`/payload).

- [ ] **Step 4: Adicionar o checkbox no formulário**

Logo depois do bloco "Task extra" (linhas 327-336), adicione:

```typescript
          <div style={{ background: requerAprovacao ? "#f5f3ff" : "#f8fafc", border: `1px solid ${requerAprovacao ? "#ddd6fe" : "#e8e8ed"}`, borderRadius: 8, padding: "10px 12px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
              <input type="checkbox" checked={requerAprovacao} onChange={(e) => setRequerAprovacao(e.target.checked)} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>Requer aprovação do gerente</span>
            </label>
            <p style={{ fontSize: 11, color: "#64748b", margin: "6px 0 0" }}>
              A task não pode ir direto de Em andamento pra Concluída — precisa passar por
              Pendente de aprovação primeiro.
            </p>
          </div>
```

(`TaskModal` só é renderizado pra quem não é operacional — ver `ehOperacional ? <TaskViewModal/> : <TaskModal/>` no componente principal — então não precisa de checagem de cargo adicional aqui.)

- [ ] **Step 5: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: sem novos erros relacionados a este arquivo pra `Coluna`/`requer_aprovacao`. Erros sobre `CfdPoint` em `MetricasTab.tsx` continuam esperados até a Task 13.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/components/TasksKanbanTab.tsx
git commit -m "feat(tasks): Kanban ganha a coluna Pendente de aprovação e o checkbox requer_aprovacao"
```

---

### Task 12: Botões Aprovar/Rejeitar

**Files:**
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx` (`TaskModal`, dentro do bloco `{mode === "edit" && (...)}`)

**Interfaces:**
- Consumes: `aprovarTask`, `rejeitarTask` (Task 10).
- Produces: nenhuma outra task consome isso — é o fim da cadeia de UI desta feature.

- [ ] **Step 1: Adicionar handlers de aprovar/rejeitar em `TaskModal`**

Logo depois de `handleOverrideTravamento`, adicione:

```typescript
  const [rejeitando, setRejeitando] = useState(false);
  const [motivoRejeicao, setMotivoRejeicao] = useState("");
  const [aprovando, setAprovando] = useState(false);

  async function handleAprovar() {
    if (!task) return;
    setAprovando(true);
    setErr("");
    try {
      const updated = await aprovarTask(task.id);
      onSaved(updated);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao aprovar");
    } finally {
      setAprovando(false);
    }
  }

  async function handleRejeitar() {
    if (!task || !motivoRejeicao.trim()) { setErr("Informe o motivo da rejeição."); return; }
    setAprovando(true);
    setErr("");
    try {
      const updated = await rejeitarTask(task.id, motivoRejeicao.trim());
      onSaved(updated);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao rejeitar");
    } finally {
      setAprovando(false);
    }
  }
```

- [ ] **Step 2: Adicionar o bloco de UI, dentro de `{mode === "edit" && (...)}`, logo antes do bloco "Histórico"**

```typescript
              {task?.coluna_kanban === "pendente_aprovacao" && (
                <div style={{ background: "#f5f3ff", border: "1px solid #ddd6fe", borderRadius: 8, padding: 12 }}>
                  <p style={{ fontSize: 12, color: "#5b21b6", margin: "0 0 10px", fontWeight: 600 }}>
                    Esta task está esperando aprovação.
                  </p>
                  {!rejeitando ? (
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        type="button"
                        onClick={handleAprovar}
                        disabled={aprovando}
                        style={{ ...btnPrimary, opacity: aprovando ? 0.6 : 1 }}
                      >
                        {aprovando ? "Aprovando..." : "Aprovar"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setRejeitando(true)}
                        disabled={aprovando}
                        style={btnGhost}
                      >
                        Rejeitar
                      </button>
                    </div>
                  ) : (
                    <div>
                      <label style={labelSt}>Motivo da rejeição *</label>
                      <textarea
                        value={motivoRejeicao}
                        onChange={(e) => setMotivoRejeicao(e.target.value)}
                        rows={2}
                        placeholder="Por que esta task está voltando pra fila?"
                        style={{ ...inputSt, resize: "vertical", marginBottom: 8 }}
                      />
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          type="button"
                          onClick={handleRejeitar}
                          disabled={aprovando}
                          style={{ ...btnPrimary, background: "#dc2626", opacity: aprovando ? 0.6 : 1 }}
                        >
                          {aprovando ? "Rejeitando..." : "Confirmar rejeição"}
                        </button>
                        <button type="button" onClick={() => setRejeitando(false)} disabled={aprovando} style={btnGhost}>
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

```

- [ ] **Step 3: Importar `aprovarTask`/`rejeitarTask`**

No bloco de imports do topo do arquivo (junto a `patchTaskKanban`, `moverTaskKanban`, etc.), adicione `aprovarTask` e `rejeitarTask`.

- [ ] **Step 4: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: sem erros novos.

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/components/TasksKanbanTab.tsx
git commit -m "feat(tasks): botões Aprovar/Rejeitar no modal de task em Pendente de aprovação"
```

---

### Task 13: `MetricasTab.tsx` — CFD ganha a 4ª área

**Files:**
- Modify: `docudata-frontend/app/components/MetricasTab.tsx:278-297` (bloco CFD)

**Interfaces:**
- Consumes: `CfdPoint.pendente_aprovacao` (Task 10).
- Produces: nenhuma outra task consome isso.

- [ ] **Step 1: Atualizar o gráfico**

Troque:

```typescript
              <Tooltip labelFormatter={(l) => `Sprint ${l}`} formatter={(v, n) => [v, n === "concluida" ? "Concluída" : n === "em_andamento" ? "Em andamento" : "Planejado"]} />
              <Legend formatter={(v) => v === "concluida" ? "Concluída" : v === "em_andamento" ? "Em andamento" : "Planejado"} />
              <Area type="monotone" dataKey="concluida" stackId="1" stroke="#166534" fill="#dcfce7" />
              <Area type="monotone" dataKey="em_andamento" stackId="1" stroke="#92400e" fill="#fef9c3" />
              <Area type="monotone" dataKey="planejado" stackId="1" stroke="#374151" fill="#f1f5f9" />
```

por:

```typescript
              <Tooltip labelFormatter={(l) => `Sprint ${l}`} formatter={(v, n) => [v, _cfdLabel(String(n))]} />
              <Legend formatter={(v) => _cfdLabel(v)} />
              <Area type="monotone" dataKey="concluida" stackId="1" stroke="#166534" fill="#dcfce7" />
              <Area type="monotone" dataKey="pendente_aprovacao" stackId="1" stroke="#5b21b6" fill="#ede9fe" />
              <Area type="monotone" dataKey="em_andamento" stackId="1" stroke="#92400e" fill="#fef9c3" />
              <Area type="monotone" dataKey="planejado" stackId="1" stroke="#374151" fill="#f1f5f9" />
```

Adicione a função auxiliar logo acima de `export default function MetricasTab` (mesmo nível de `spiColor`):

```typescript
function _cfdLabel(v: string): string {
  if (v === "concluida") return "Concluída";
  if (v === "pendente_aprovacao") return "Pendente de aprovação";
  if (v === "em_andamento") return "Em andamento";
  return "Planejado";
}
```

- [ ] **Step 2: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: limpo — este era o último arquivo com erro pendente de `CfdPoint`.

- [ ] **Step 3: Commit**

```bash
git add docudata-frontend/app/components/MetricasTab.tsx
git commit -m "feat(metricas): CFD mostra a faixa Pendente de aprovação"
```

---

### Task 14: Testes de frontend

**Files:**
- Modify: `docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs` (ou novo arquivo `docudata-frontend/tests/pendente-aprovacao.test.mjs`)

**Interfaces:**
- Consumes: nada de outras tasks — só lê os arquivos-fonte já editados.

- [ ] **Step 1: Escrever o teste estrutural**

Crie `docudata-frontend/tests/pendente-aprovacao.test.mjs` (mesmo padrão de `readFileSync` + asserções de string usado em `modos-trabalho-avaliacao.test.mjs`):

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const KANBAN = readFileSync(new URL("../app/components/TasksKanbanTab.tsx", import.meta.url), "utf-8");
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");
const METRICAS = readFileSync(new URL("../app/components/MetricasTab.tsx", import.meta.url), "utf-8");

test("Kanban tem a coluna pendente_aprovacao e o checkbox requer_aprovacao", () => {
  assert.match(KANBAN, /pendente_aprovacao/);
  assert.match(KANBAN, /Requer aprovação do gerente/);
  assert.match(KANBAN, /handleAprovar/);
  assert.match(KANBAN, /handleRejeitar/);
});

test("api.ts expõe aprovarTask e rejeitarTask", () => {
  assert.match(API, /export async function aprovarTask/);
  assert.match(API, /export async function rejeitarTask/);
  assert.match(API, /pendente_aprovacao/);
});

test("MetricasTab CFD inclui pendente_aprovacao", () => {
  assert.match(METRICAS, /pendente_aprovacao/);
});
```

- [ ] **Step 2: Rodar `npm test` e confirmar que passa**

Run: `cd docudata-frontend && npm test`
Expected: PASS em todos os testes (novos e os já existentes — nenhum arquivo anterior foi quebrado pelas Tasks 10-13).

- [ ] **Step 3: Rodar o typecheck de novo, por garantia**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: limpo.

- [ ] **Step 4: Commit**

```bash
git add docudata-frontend/tests/pendente-aprovacao.test.mjs
git commit -m "test(tasks): cobertura estrutural de Pendente de aprovação no frontend"
```

---

### Task 15: Verificação final completa

**Files:** nenhum arquivo novo — só verificação.

- [ ] **Step 1: Suíte completa do backend, de novo**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q`
Expected: PASS — confirma que nada na Onda 2 (só frontend) quebrou o backend.

- [ ] **Step 2: Typecheck e testes do frontend, juntos**

Run: `cd docudata-frontend && npx tsc --noEmit && npm test`
Expected: os dois limpos/verdes.

- [ ] **Step 3: Checklist manual (reportar ao usuário, não pode ser verificado automaticamente sem ambiente real)**

Peça pro usuário, depois de rodar o SQL da Task 1 em produção:
1. Criar uma task com "Requer aprovação do gerente" marcado, mover pra "Em andamento", tentar arrastar direto pra "Concluída" — deve ser rejeitado (o board volta a task pra coluna anterior ou mostra erro).
2. Mover a mesma task pra "Pendente de aprovação" — deve funcionar, e o gerente deve receber um email.
3. Abrir a task, clicar "Aprovar" — deve ir pra "Concluída".
4. Repetir com outra task e clicar "Rejeitar" com um motivo — deve voltar pra "Planejado" sem responsável, e o operacional deve receber um email com o motivo.
5. Em modo PULL, confirmar que mover uma task pra "Pendente de aprovação" libera o WIP da pessoa pra puxar a próxima.
6. Conferir o gráfico CFD em Métricas — a faixa "Pendente de aprovação" deve aparecer.

- [ ] **Step 4: Relatar ao usuário**

Resuma o que foi verificado automaticamente (testes + typecheck) e liste o checklist manual do Step 3 como pendente de confirmação dele.

---

## Self-Review

**Cobertura da spec:** §3 (modelo de dados) → Tasks 1-2. §4 (transições/RBAC) → Tasks 3-4, 6-7. §5 (WIP/travamento) → Task 3 (travamento) + confirmado sem mudança de código pra WIP/job diário (constraint global). §6 (pontuação) → confirmado sem mudança de código, coberto pelo teste de transição em Task 6 (`test_aprovar_grava_transicao_para_concluida`, essencial pra `_resolver_quem_completou`). §7 (email) → Task 5. §8 (endpoints) → Tasks 2-7. §9 (migração) → Task 1. §10 (métricas) → Task 8 (backend) + Task 13 (frontend). §11 (frontend) → Tasks 10-12. §12 (fora de escopo) → nenhuma task cobre de propósito. §13 (testes) → distribuído em cada task.

**Consistência de tipos:** `requer_aprovacao` (bool) idêntico em `TaskCreate`/`TaskUpdate`/`TaskResponse` (Python) e `TaskKanbanResponse`/payloads de `createTaskKanban`/`patchTaskKanban` (TypeScript). `RejeitarTaskRequest.motivo` (obrigatório) casa com `rejeitarTask(id, motivo)` (motivo obrigatório, sem `?`). `aprovarTask`/`rejeitarTask` retornam `TaskKanbanResponse`, igual toda outra função de ação de task em `api.ts`.

**Placeholders:** nenhum "TBD"/"adicionar validação apropriada" — todo código é literal.
