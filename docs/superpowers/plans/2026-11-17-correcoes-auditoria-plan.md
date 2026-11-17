# Correções da auditoria (pull × normal, desempenho, análise) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir os bugs confirmados da auditoria (itens 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 18) e parar de gravar tokens/custo de IA em `commit_extraction.py`.

**Architecture:** Correções pontuais em routers/services já existentes, cada uma com teste de regressão e commit próprio. Backend antes do frontend. Duas peças novas: helper `congelar_modo_da_sprint` (snapshot do modo na sprint) e a gravação do WIP anterior em `configuracao_historico` (campo novo `wip_por_pessoa`, exige migração).

**Tech Stack:** FastAPI, Supabase (FakeClient/MagicMock nos testes), pytest; Next.js + `node --test` (testes de regex sobre o fonte) + `npx tsc --noEmit`.

**Spec:** `docs/superpowers/specs/2026-11-17-pta-nivel-gerente-design.md` (seção 4, tabela "Correções da auditoria"). Itens fora de escopo: #3, #15, #16, #17 e "remover operacional deixa tasks sem dono".

## Global Constraints

- Mensagens de commit em português, estilo do repo (`fix(tasks): ...`), terminando com a linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Comandos backend: `cd docudata-backend && .venv/bin/python -m pytest -q tests/<arquivo>`. Frontend: `cd docudata-frontend && npm test` e `npx tsc --noEmit`.
- Não reintroduzir rastreio de custo/tokens de IA (decisão do usuário, 2026-09-07).
- Migrações SQL são manuais: avisar o usuário ao alterar `supabase_schema.sql` (Task 9).
- Cada task termina com a suíte do arquivo tocado verde; a suíte inteira roda na Task 12. Se uma mudança quebrar teste existente, o conserto do teste faz parte da mesma task/commit (as tasks 2, 3, 5 listam os conhecidos).
- Em Pull o responsável nunca é definido à mão; `em_ajuste` NÃO é coluna de task (só status de funcionalidade); colunas válidas: `planejado | em_andamento | pendente_aprovacao | concluida`.

## Verificações da auditoria (feitas no código)

Todos os itens citados se confirmaram, com estas ressalvas que moldam o plano:
- **#7**: `em_ajuste` não existe como coluna de task. O plano aceita só `em_andamento` (decisão marcada na Task 3).
- **#9**: reabrir não pode apagar TODOS os `pontuacao_eventos` da sprint: `devolucao_penalidade` é inserido no meio da sprint (em `/devolver`) e nunca é recriado pelo fechamento. Apaga-se só os tipos que o fechamento gera (`entrega_concluida`, `bonus_extra`, `travamento_penalidade`, `reabertura`).
- **#10**: `sprints.iniciada` tem DEFAULT true; sprints criadas por `ensure_sprint_row` e `create_sprint(iniciada=True)` nunca passam por `iniciar_sprint_e_ancorar_tasks`. O snapshot é gravado nos três pontos.
- **#11**: o frontend (`app/avaliacoes/page.tsx`) só lê `modo_trabalho` do item devolvido pela API; corrigir o backend basta, sem mudança de frontend.
- **#14**: o WIP anterior não é gravado em lugar nenhum hoje; `configuracao_historico.campo` tem CHECK só para `modo_trabalho|modo_avaliacao`. Exige migração (Task 9). Projetos que já estão em Pull sem registro: ao sair, WIP fica como está (decisão marcada).
- O teste `test_security` passa no ambiente atual (baseline: 1223 passed).

## File Structure

- `docudata-backend/routers/tasks.py` — Tasks 1–5.
- `docudata-backend/services/sprints.py` — Tasks 5, 7 (`congelar_modo_da_sprint`, ancoragem).
- `docudata-backend/services/travamento_checker.py` — Task 5.
- `docudata-backend/routers/avaliacoes.py` — Tasks 6, 7.
- `docudata-backend/services/pontuacao.py` — Task 7.
- `docudata-backend/routers/sprints.py` — Task 7.
- `docudata-backend/routers/metricas.py` — Task 8.
- `docudata-backend/routers/projects.py`, `supabase_schema.sql` — Tasks 7, 9.
- `docudata-backend/services/commit_extraction.py` — Task 10.
- `docudata-frontend/app/components/TasksKanbanTab.tsx` — Task 11.
- Testes novos: `tests/test_auditoria_tasks.py`, `tests/test_auditoria_travamento.py`, `tests/test_auditoria_fechamento.py`, `tests/test_auditoria_modo.py`, `tests/test_auditoria_metricas.py`, `docudata-frontend/tests/auditoria-kanban.test.mjs`.

---

### Task 0: Baseline

**Files:** nenhum.

- [ ] **Step 1: Rodar a suíte**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q`
Expected: `1223 passed` (inclui `tests/test_security.py`). Se o número diferir, parar e avisar antes de seguir.

---

### Task 1: PATCH aceita `operacional_id` igual ao atual em Pull e `null` explícito (itens 1 e 18)

**Files:**
- Modify: `docudata-backend/routers/tasks.py` (`patch_task`, bloco `if data.operacional_id is not None:` ~823; laço de transições ~969; loop de updates ~1008)
- Test: `docudata-backend/tests/test_auditoria_tasks.py` (criar)

**Interfaces:**
- Consumes: `tests.test_tasks_pull_lock_atribuicao._mock_client(projeto, task)` e `_TASK_BASE`.
- Produces: `TaskUpdate.operacional_id` com semântica "campo enviado como `null` = desatribuir" (via `data.model_fields_set`) em Atribuição.

- [ ] **Step 1: Escrever os testes que falham**

```python
"""Correções da auditoria 2026-11-17: tasks (Pull x Atribuição, RBAC, puxar/devolver)."""
import pytest
from fastapi.testclient import TestClient

from tests.test_tasks_pull_lock_atribuicao import _TASK_BASE, _mock_client


@pytest.fixture
def cliente_para(monkeypatch, autenticar):
    def _make(modo, task, cargo="gerente", meu_operacional="op-9"):
        import routers.tasks as tasks_router
        from main import app
        monkeypatch.setattr(tasks_router, "get_client",
                            lambda: _mock_client({"id": "proj-1", "modo_trabalho": modo}, task))
        monkeypatch.setattr(tasks_router, "_resolver_operacional_id_da_pessoa", lambda *a: meu_operacional)
        return autenticar(TestClient(app), cargo=cargo)
    return _make


def test_pull_aceita_operacional_id_igual_ao_atual(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("PULL", task).patch("/tasks/task-1", json={"operacional_id": "op-2", "bloqueado": False})
    assert resp.status_code == 200


def test_pull_continua_recusando_trocar_responsavel(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("PULL", task).patch("/tasks/task-1", json={"operacional_id": "op-3"})
    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]


def test_atribuicao_null_explicito_desatribui(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2")
    resp = cliente_para("ATRIBUICAO", task).patch("/tasks/task-1", json={"operacional_id": None})
    assert resp.status_code == 200
    assert resp.json()["operacional_id"] is None


def test_atribuicao_sem_o_campo_nao_desatribui(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2")
    resp = cliente_para("ATRIBUICAO", task).patch("/tasks/task-1", json={"titulo": "Novo título"})
    assert resp.json()["operacional_id"] == "op-2"


def test_pull_null_explicito_em_task_com_dono_e_422(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2")
    resp = cliente_para("PULL", task).patch("/tasks/task-1", json={"operacional_id": None})
    assert resp.status_code == 422
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_auditoria_tasks.py`
Expected: FAIL em `test_pull_aceita_operacional_id_igual_ao_atual` (422) e `test_atribuicao_null_explicito_desatribui` (operacional_id continua "op-2"); `test_pull_null_explicito...` também falha (200).

- [ ] **Step 3: Implementar**

Em `patch_task`, logo após carregar `task`/`project_id`, substituir o primeiro bloco `if data.operacional_id is not None:` (o que consulta `modo_trabalho`) por:

```python
    # Null explícito (campo presente no JSON) = "Sem operacional" em Atribuição.
    # Campo ausente continua significando "não mexer".
    desatribuir = "operacional_id" in data.model_fields_set and data.operacional_id is None
    operacional_muda = (
        data.operacional_id is not None and data.operacional_id != task.get("operacional_id")
    ) or (desatribuir and task.get("operacional_id") is not None)

    if operacional_muda:
        proj_modo = client.table("projects").select("modo_trabalho").eq("id", project_id).execute()
        if proj_modo.data and proj_modo.data[0].get("modo_trabalho") == "PULL":
            raise HTTPException(
                status_code=422,
                detail="Em modo Pull, tasks não podem ter responsável definido manualmente. Use a fila de puxar.",
            )
```

No laço `for campo in ("coluna_kanban", "operacional_id", "sprint_id"):` substituir o `continue` inicial por tratamento do null:

```python
    for campo in ("coluna_kanban", "operacional_id", "sprint_id"):
        novo_valor = getattr(data, campo, None)
        if campo == "operacional_id" and desatribuir and task.get("operacional_id") is not None:
            _registrar_task_transicao(client, task_id, task, "operacional_id", None, data.autor, data.motivo, agora)
            continue
        if novo_valor is None or str(novo_valor) == str(task.get(campo) or ""):
            continue
```

No bloco `updates` (depois do `for field in (...)` e do `if data.bloqueado is not None`), acrescentar:

```python
    if desatribuir and task.get("operacional_id") is not None:
        updates["operacional_id"] = None
```

E na condição `puxada_por` (`... and data.operacional_id is None`) trocar por `and data.operacional_id is None and not desatribuir`? Não: `desatribuir` é definido antes dela (mesmo bloco inicial), então use `and not desatribuir` para que um null explícito não vire "puxar". Mantenha a ordem: `desatribuir` deve ser calculado ANTES do bloco "Pull: arrastar..." (já está, pois fica logo após carregar a task).

- [ ] **Step 4: Rodar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_auditoria_tasks.py tests/test_tasks_pull_lock_atribuicao.py tests/test_tasks_pull_arrastar.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_auditoria_tasks.py
git commit -m "fix(tasks): Pull aceita operacional_id inalterado e Atribuição aceita null para desatribuir

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Operacional só mexe na própria task e precisa estar na equipe (item 5, backend)

**Files:**
- Modify: `docudata-backend/routers/tasks.py` (`patch_task`, logo depois de carregar `task`; `mover_task` herda via `patch_task`)
- Modify (testes existentes que autenticam como operacional): `tests/test_task_rbac_operacional.py`, `tests/test_task_conclusao_email.py` (~149), `tests/test_dependencia_cliente.py` (~111)
- Test: `docudata-backend/tests/test_auditoria_tasks.py`

**Interfaces:**
- Consumes: `_resolver_operacional_id_da_pessoa(client, project_id, email) -> str | None` (já em tasks.py); fixture `cliente_para` da Task 1.
- Produces: `_checar_operacional_pode_mexer(client, pessoa, task, data) -> None` (levanta 403).

- [ ] **Step 1: Testes que falham** (acrescentar ao arquivo)

```python
def test_operacional_nao_move_task_de_colega(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="operacional", meu_operacional="op-9").patch(
        "/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 403


def test_operacional_move_a_propria_task(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-9", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="operacional", meu_operacional="op-9").patch(
        "/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200


def test_operacional_fora_da_equipe_e_403(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-9", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="operacional", meu_operacional=None).patch(
        "/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 403


def test_operacional_puxa_da_fila_em_pull_arrastando(cliente_para):
    task = dict(_TASK_BASE, operacional_id=None, coluna_kanban="planejado", sprint_id="sp-1")
    resp = cliente_para("PULL", task, cargo="operacional", meu_operacional="op-9").patch(
        "/tasks/task-1", json={"coluna_kanban": "em_andamento"})
    assert resp.status_code == 200
    assert resp.json()["operacional_id"] == "op-9"


def test_operacional_nao_move_task_sem_dono_fora_da_fila(cliente_para):
    task = dict(_TASK_BASE, operacional_id=None, coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("PULL", task, cargo="operacional").patch("/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 403


def test_mover_endpoint_tambem_barra_task_de_colega(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="operacional", meu_operacional="op-9").post(
        "/tasks/task-1/mover", params={"coluna_destino": "planejado"})
    assert resp.status_code == 403


def test_gerente_continua_movendo_qualquer_task(cliente_para):
    task = dict(_TASK_BASE, operacional_id="op-2", coluna_kanban="em_andamento", sprint_id="sp-1")
    resp = cliente_para("ATRIBUICAO", task, cargo="gerente", meu_operacional=None).patch(
        "/tasks/task-1", json={"coluna_kanban": "concluida"})
    assert resp.status_code == 200
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_tasks.py -k "operacional or mover or gerente_continua"`
Expected: FAIL nos testes que esperam 403.

- [ ] **Step 3: Implementar**

Em `routers/tasks.py`, adicionar acima de `patch_task`:

```python
def _checar_operacional_pode_mexer(client, pessoa: dict, task: dict, data: TaskUpdate) -> None:
    """Operacional só altera task própria, ou puxa da fila em Pull (task sem
    dono em Planejado). Precisa estar vinculado ao projeto. Gerente/líder/owner
    passam direto. Vale para PATCH e para /mover (que delega ao PATCH)."""
    if pessoa["cargo"] != "operacional":
        return
    project_id = task["project_id"]
    meu_id = _resolver_operacional_id_da_pessoa(client, project_id, pessoa["email"])
    if not meu_id:
        raise HTTPException(status_code=403, detail="Você não está vinculado a este projeto.")
    dono = task.get("operacional_id")
    if dono == meu_id:
        return
    if dono is None and task.get("coluna_kanban") == "planejado":
        proj = client.table("projects").select("modo_trabalho").eq("id", project_id).execute()
        if proj.data and proj.data[0].get("modo_trabalho") == "PULL":
            return  # a regra de puxar (422 se não for para Em andamento) vem logo abaixo
    raise HTTPException(status_code=403, detail="Só quem está com a task pode alterá-la.")
```

Em `patch_task`, logo após `project_id = task["project_id"]`, chamar `_checar_operacional_pode_mexer(client, pessoa, task, data)`.

Consertar testes existentes: em cada `_client_como`/fixture que autentica como `"operacional"` e faz PATCH/mover numa task com `operacional_id="op-1"`, adicionar dentro do helper (quando `cargo == "operacional"`):

```python
monkeypatch.setattr(tasks_router, "_resolver_operacional_id_da_pessoa", lambda *a: "op-1")
```

(`tests/test_task_rbac_operacional.py::_client_como`, `tests/test_task_conclusao_email.py` e `tests/test_dependencia_cliente.py` — o id deve ser o `operacional_id` da task base de cada arquivo). `tests/test_tasks_pull_arrastar.py` já faz esse monkeypatch.

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_tasks.py tests/test_task_rbac_operacional.py tests/test_task_conclusao_email.py tests/test_dependencia_cliente.py tests/test_tasks_pull_arrastar.py`
Expected: PASS. Rodar também `-k operacional` em `tests/` inteiro e consertar qualquer outro teste que autentique como operacional e mova task (mesmo monkeypatch).

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests
git commit -m "fix(tasks): operacional só altera a própria task (ou puxa da fila em Pull) e precisa estar na equipe

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `/puxar` exige sprint; `/devolver` só em Pull e em Em andamento (itens 6 e 7)

**Files:**
- Modify: `docudata-backend/routers/tasks.py` (`puxar_task` ~533; `devolver_task` ~590)
- Modify (testes existentes): `tests/test_pull_devolver.py` (tasks dos testes `test_puxar_*` ganham `"sprint_id": "sprint-1"`), `tests/test_classificador_ciclo.py` (~275, o teste `/puxar`: garantir `sprint_id` na task)
- Test: `docudata-backend/tests/test_auditoria_tasks.py`

**Interfaces:**
- Consumes: fixture `make_client` de `tests/test_pull_devolver.py` (`make_client(task, operacional_da_pessoa, cargo=, modo_trabalho=, ...)`).
- Produces: 409 `DoR: ...` em `/puxar` sem sprint; 422 em `/devolver` fora de Pull ou fora de `em_andamento`/`planejado`.

Decisão marcada: o spec cita `em_ajuste`, que não é coluna de task. Aceita-se `em_andamento` e `planejado` com dono (o estado "preso" que já existe em produção por causa do item 5: devolver é o jeito de liberar a task de volta à fila).

- [ ] **Step 1: Testes que falham** (acrescentar)

```python
from tests.test_pull_devolver import make_client  # noqa: F401  (fixture)

_OP = {"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"}


def _task(**kw):
    base = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": False,
            "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
            "travado_automatico": False, "ordem": 0, "created_at": "2026-01-01T00:00:00+00:00"}
    base.update(kw)
    return base


def test_puxar_sem_sprint_da_409(make_client):
    resp = make_client(_task(), _OP).post("/tasks/t1/puxar")
    assert resp.status_code == 409
    assert "DoR" in resp.json()["detail"]


def test_puxar_com_sprint_funciona(make_client):
    resp = make_client(_task(sprint_id="sprint-1"), _OP).post("/tasks/t1/puxar")
    assert resp.status_code == 200


def test_devolver_task_concluida_da_422(make_client):
    resp = make_client(_task(operacional_id="op-a", coluna_kanban="concluida"), _OP).post("/tasks/t1/devolver")
    assert resp.status_code == 422


def test_devolver_em_projeto_atribuicao_da_422(make_client):
    resp = make_client(_task(operacional_id="op-a", coluna_kanban="em_andamento"), _OP,
                       modo_trabalho="ATRIBUICAO").post("/tasks/t1/devolver")
    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]


def test_devolver_planejado_com_dono_libera_para_fila(make_client):
    resp = make_client(_task(operacional_id="op-a", coluna_kanban="planejado", sprint_id="sprint-1"), _OP).post("/tasks/t1/devolver")
    assert resp.status_code == 200


def test_devolver_em_andamento_em_pull_continua_200(make_client):
    resp = make_client(_task(operacional_id="op-a", coluna_kanban="em_andamento"), _OP).post("/tasks/t1/devolver")
    assert resp.status_code == 200
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_tasks.py -k "puxar or devolver"`
Expected: FAIL em `sem_sprint` (200), `concluida` (200), `atribuicao` (200).

- [ ] **Step 3: Implementar**

Em `puxar_task`, depois do bloco que resolve `operacional_id` (antes de `check_wip`; assim o 403 de "projeto não é Pull" continua vindo antes):

```python
    if not task.get("sprint_id"):
        raise HTTPException(
            status_code=409,
            detail="DoR: associe a task a uma sprint antes de movê-la para Em Andamento.",
        )
```

Em `devolver_task`, depois do gate de `pendente_aprovacao` e antes do RBAC:

```python
    proj = client.table("projects").select("modo_trabalho").eq("id", task["project_id"]).execute()
    if not proj.data or proj.data[0].get("modo_trabalho") != "PULL":
        raise HTTPException(status_code=422, detail="Devolver à fila só existe em projetos em modo Pull.")
    if task.get("coluna_kanban") not in ("em_andamento", "planejado"):
        raise HTTPException(status_code=422, detail="Só dá para devolver uma task em Em andamento (ou parada em Planejado com dono).")
```

Consertar testes existentes: nos `test_puxar_*` de `tests/test_pull_devolver.py` (os três dicts de task) adicionar `"sprint_id": "sprint-1"`; em `tests/test_classificador_ciclo.py` (~275) idem na task usada pelo `/puxar`. Os testes de devolver existentes já usam `em_andamento` e o mock de `projects` devolve `modo_trabalho="PULL"` por padrão.

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_tasks.py tests/test_pull_devolver.py tests/test_classificador_ciclo.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests
git commit -m "fix(tasks): /puxar exige sprint e /devolver só vale em Pull e em Em andamento

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Devolver dispensa os travamentos ativos da task (item 4)

**Files:**
- Modify: `docudata-backend/routers/tasks.py` (`devolver_task`, depois do bloco do extrato e antes do `update`)
- Test: `docudata-backend/tests/test_auditoria_tasks.py`

**Interfaces:**
- Consumes: `make_client` (Task 3), `pontos_travamento_ativo` (já importado).
- Produces: `task_travamentos.dispensado = True` para a task devolvida.

- [ ] **Step 1: Teste que falha**

```python
from unittest.mock import MagicMock


def _capturar_dispensa(tc):
    capturas = []
    original = tc._mock_sb.table.side_effect

    def tabela(nome):
        tbl = original(nome)
        if nome == "task_travamentos":
            def upd(payload):
                capturas.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                return q
            tbl.update = MagicMock(side_effect=upd)
        return tbl

    tc._mock_sb.table = MagicMock(side_effect=tabela)
    return capturas


def test_devolver_task_travada_dispensa_os_travamentos(make_client):
    task = _task(operacional_id="op-a", coluna_kanban="em_andamento", travado_automatico=True, sprint_id="sprint-1")
    tc = make_client(task, _OP, task_travamentos=[{"pontos": 3, "dispensado": False}])
    capturas = _capturar_dispensa(tc)
    resp = tc.post("/tasks/t1/devolver")
    assert resp.status_code == 200
    assert capturas == [{"dispensado": True}]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_tasks.py::test_devolver_task_travada_dispensa_os_travamentos`
Expected: FAIL (`capturas == []`).

- [ ] **Step 3: Implementar**

Em `devolver_task`, imediatamente depois do `if task.get("travado_automatico"): ...` (bloco do extrato) e antes de `agora = ...`:

```python
    # A task volta para a fila: quem concluir depois não pode herdar a penalidade
    # do dono antigo (task_travamentos.operacional_id aponta para ele). O extrato
    # acima já registrou a devolução.
    try:
        (
            client.table("task_travamentos")
            .update({"dispensado": True})
            .eq("task_id", task_id)
            .eq("dispensado", False)
            .execute()
        )
    except Exception:
        _LOG.warning("Falha ao dispensar travamentos da task %s na devolução", task_id)
```

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_tasks.py tests/test_pull_devolver.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_auditoria_tasks.py
git commit -m "fix(tasks): devolver dispensa os travamentos ativos para não penalizar o dono antigo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Travamento em Pull não conta o tempo na fila (item 2)

**Files:**
- Modify: `docudata-backend/services/sprints.py` (`iniciar_sprint_e_ancorar_tasks`); `docudata-backend/routers/tasks.py` (`patch_task`, ramo `if puxada_por:` ~1014); `docudata-backend/services/travamento_checker.py`
- Modify (testes existentes): `tests/test_travamento_job_override.py` (tasks do job ganham `"operacional_id": "op-1"`)
- Test: `docudata-backend/tests/test_auditoria_travamento.py` (criar) e `tests/test_auditoria_tasks.py`

**Interfaces:**
- Consumes: `FakeClient` (`tests/fake_supabase.py`).
- Produces: nada novo público; `iniciar_sprint_e_ancorar_tasks` pula tasks sem dono em projeto Pull.

- [ ] **Step 1: Testes que falham**

`tests/test_auditoria_travamento.py`:

```python
from datetime import datetime, timedelta, timezone

from services.sprints import iniciar_sprint_e_ancorar_tasks
from tests.fake_supabase import FakeClient


def _fake(modo):
    return FakeClient({
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False}],
        "projects": [{"id": "p1", "modo_trabalho": modo, "modo_avaliacao": "PONTOS_ATRIBUIDOS"}],
        "tasks": [
            {"id": "fila", "sprint_id": "s1", "coluna_kanban": "planejado", "operacional_id": None,
             "entrou_em_andamento_em": None, "extra": False},
            {"id": "dono", "sprint_id": "s1", "coluna_kanban": "planejado", "operacional_id": "op-1",
             "entrou_em_andamento_em": None, "extra": False},
        ],
    })


def _anc(fake, task_id):
    return next(t for t in fake.tables["tasks"] if t["id"] == task_id)["entrou_em_andamento_em"]


def test_iniciar_sprint_em_pull_nao_ancora_task_da_fila():
    fake = _fake("PULL")
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    assert _anc(fake, "fila") is None
    assert _anc(fake, "dono") is not None


def test_iniciar_sprint_em_atribuicao_continua_ancorando_tudo():
    fake = _fake("ATRIBUICAO")
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    assert _anc(fake, "fila") is not None


def test_job_ignora_task_sem_dono(monkeypatch):
    import services.travamento_checker as job
    velho = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    fake = FakeClient({"tasks": [
        {"id": "fila", "pontos": 1, "operacional_id": None, "coluna_kanban": "planejado",
         "entrou_em_andamento_em": velho, "travado_automatico": False},
        {"id": "dono", "pontos": 1, "operacional_id": "op-1", "coluna_kanban": "em_andamento",
         "entrou_em_andamento_em": velho, "travado_automatico": False},
    ]})
    monkeypatch.setattr(job, "get_client", lambda: fake)
    job.check_travamento_automatico()
    marcadas = {t["id"]: t["travado_automatico"] for t in fake.tables["tasks"]}
    assert marcadas == {"fila": False, "dono": True}
    assert [r["task_id"] for r in fake.tables["task_travamentos"]] == ["dono"]
```

Acrescentar em `tests/test_auditoria_tasks.py`:

```python
def test_arrastar_para_puxar_sempre_reancora(cliente_para):
    antigo = "2026-01-01T00:00:00+00:00"
    task = dict(_TASK_BASE, operacional_id=None, coluna_kanban="planejado", sprint_id="sp-1",
                entrou_em_andamento_em=antigo)
    resp = cliente_para("PULL", task, cargo="operacional", meu_operacional="op-9").patch(
        "/tasks/task-1", json={"coluna_kanban": "em_andamento"})
    assert resp.status_code == 200
    ancora = resp.json()["entrou_em_andamento_em"]
    assert ancora and ancora != antigo
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_travamento.py tests/test_auditoria_tasks.py::test_arrastar_para_puxar_sempre_reancora`
Expected: FAIL (fila ancorada; job marca "fila"; reancora volta `None`).

- [ ] **Step 3: Implementar**

`services/sprints.py`: em `iniciar_sprint_e_ancorar_tasks`, depois do `if not ja_iniciada: marcar_foto_do_inicio(...)`, substituir a leitura/loop de `pendentes` por:

```python
    sprint_row = (client.table("sprints").select("project_id").eq("id", sprint_id).execute().data or [{}])[0]
    projeto = (
        client.table("projects").select("modo_trabalho").eq("id", sprint_row.get("project_id")).execute().data or [{}]
    )[0] if sprint_row.get("project_id") else {}
    em_pull = projeto.get("modo_trabalho") == "PULL"

    agora_iso = datetime.now(timezone.utc).isoformat()
    pendentes = (
        client.table("tasks")
        .select("id, operacional_id")
        .eq("sprint_id", sprint_id)
        .neq("coluna_kanban", "concluida")
        .is_("entrou_em_andamento_em", "null")
        .execute()
        .data or []
    )
    for t in pendentes:
        # Em Pull a task da fila (sem dono) não tem relógio: o tempo de espera
        # não é do operacional. A âncora nasce quando alguém puxa.
        if em_pull and not t.get("operacional_id"):
            continue
        client.table("tasks").update({"entrou_em_andamento_em": agora_iso}).eq("id", t["id"]).execute()
```

(apagar o `agora_iso = ...` e o `pendentes` antigos). Atualizar a docstring com uma frase sobre isso.

`routers/tasks.py` `patch_task`: o ramo `if puxada_por:` passa a reancorar sempre:

```python
    if puxada_por:
        updates.update({
            "operacional_id": puxada_por, "pull_em": agora.isoformat(), "ordem_fila": None,
            "entrou_em_andamento_em": agora.isoformat(),
            "travado_automatico": False,
        })
```

`services/travamento_checker.py`: no laço, depois do `if task.get("travado_automatico"): continue`, adicionar:

```python
        if not task.get("operacional_id"):
            # Task da fila (Pull) ou sem responsável: ninguém a quem atribuir o atraso.
            continue
```

Atualizar o docstring do módulo (uma linha). Em `tests/test_travamento_job_override.py`, as tasks de `_make_job_mock_client` usadas nos casos 1 (e demais que esperam marcação) precisam de `"operacional_id": "op-1"`.

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_travamento.py tests/test_auditoria_tasks.py tests/test_travamento_job_override.py tests/test_iniciar_sprint_ancora_tasks.py tests/test_travamento_relogio.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services docudata-backend/routers/tasks.py docudata-backend/tests
git commit -m "fix(travamento): em Pull o relógio não conta o tempo na fila nem penaliza quem puxa

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Reconfirmar sprint fechada é idempotente; reabrir apaga o extrato (itens 8 e 9)

**Files:**
- Modify: `docudata-backend/routers/avaliacoes.py` (`confirmar_avaliacao_semanal` ~286, `reabrir_avaliacao_semanal` ~340)
- Modify (testes existentes): `tests/test_avaliacao_semanal_confirmar.py` (o mock de `sprints` precisa responder ao novo `select` inicial; ver Step 3)
- Test: `docudata-backend/tests/test_auditoria_fechamento.py` (criar)

**Interfaces:**
- Consumes: `FakeClient`; `require_role("lider")` (autenticar com `cargo="lider"`).
- Produces: `confirmar` não regrava `avaliacao_completa_em`; `reabrir` apaga `pontuacao_eventos` dos tipos gerados no fechamento.

- [ ] **Step 1: Testes que falham**

```python
import pytest
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient

FECHADA_EM = "2026-11-01T10:00:00+00:00"


@pytest.fixture
def api(monkeypatch, autenticar):
    def _make(fake, cargo="lider"):
        import routers.avaliacoes as router
        from main import app
        monkeypatch.setattr(router, "get_client", lambda: fake)
        return autenticar(TestClient(app), cargo=cargo)
    return _make


def _base():
    return FakeClient({
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "iniciada": True,
                     "avaliacao_completa_em": FECHADA_EM}],
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS"}],
        "operacionais": [],
        "tasks": [],
        "pontuacao_operacional_sprint": [{"id": "l1", "sprint_id": "s1", "projeto_id": "p1",
                                           "operacional_id": "op-1", "finalizado_em": FECHADA_EM}],
        "pontuacao_eventos": [
            {"id": "e1", "sprint_id": "s1", "tipo": "entrega_concluida", "pontos": 3},
            {"id": "e2", "sprint_id": "s1", "tipo": "travamento_penalidade", "pontos": -2},
            {"id": "e3", "sprint_id": "s1", "tipo": "devolucao_penalidade", "pontos": -1},
        ],
        "eventos_pontuacao_tardios": [],
    })


def test_reconfirmar_sprint_fechada_nao_regrava_a_data(api):
    fake = _base()
    resp = api(fake, cargo="gerente").post("/avaliacoes/s1/confirmar")
    assert resp.status_code == 200
    assert resp.json()["avaliacao_completa_em"] == FECHADA_EM
    assert fake.tables["sprints"][0]["avaliacao_completa_em"] == FECHADA_EM


def test_reabrir_apaga_eventos_gerados_no_fechamento_e_preserva_devolucao(api):
    fake = _base()
    resp = api(fake).delete("/avaliacoes/s1/confirmar")
    assert resp.status_code == 200
    tipos = [e["tipo"] for e in fake.tables["pontuacao_eventos"]]
    assert tipos == ["devolucao_penalidade"]
    assert fake.tables["sprints"][0]["avaliacao_completa_em"] is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_fechamento.py`
Expected: FAIL (data regravada; eventos continuam 3).

- [ ] **Step 3: Implementar**

`confirmar_avaliacao_semanal`: no início (antes de `listar_pendencias`):

```python
    sprint_row = client.table("sprints").select("id, avaliacao_completa_em").eq("id", sprint_id).execute().data
    if not sprint_row:
        raise HTTPException(status_code=404, detail="Sprint not found")
    if sprint_row[0].get("avaliacao_completa_em"):
        # Já fechada: resposta idempotente, sem regravar a data nem recalcular.
        existentes = client.table("pontuacao_operacional_sprint").select("id").eq("sprint_id", sprint_id).execute().data or []
        return {
            "sprint_id": sprint_id,
            "avaliacao_completa_em": sprint_row[0]["avaliacao_completa_em"],
            "pontuacao_travada_count": len(existentes),
        }
```

`reabrir_avaliacao_semanal`: depois de apagar `eventos_pontuacao_tardios`:

```python
    # Extrato do fechamento é recriado ao confirmar de novo; sem apagar, duplica.
    # devolucao_penalidade nasce no meio da sprint (/devolver) e não é recriada.
    client.table("pontuacao_eventos").delete().eq("sprint_id", sprint_id).in_(
        "tipo", ["entrega_concluida", "bonus_extra", "travamento_penalidade", "reabertura"]
    ).execute()
```

Testes existentes de `tests/test_avaliacao_semanal_confirmar.py` usam MagicMock: garantir que o mock de `sprints` devolva, no `select`, uma linha sem `avaliacao_completa_em` (ex.: `{"id": "sprint-1"}`) além do `update`; ajustar o helper `_mock_client` (branch `sprints`) para `select` retornar `[{"id": "sprint-1", "avaliacao_completa_em": None}]`.

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_fechamento.py tests/test_avaliacao_semanal_confirmar.py tests/test_avaliacoes_pendencias.py tests/test_avaliacoes_rbac.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/avaliacoes.py docudata-backend/tests
git commit -m "fix(avaliacoes): reconfirmar sprint fechada é idempotente e reabrir limpa o extrato do fechamento

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Snapshot do modo da sprint no início; fechamento e histórico o usam; `hibrida` só se o modo mudou (itens 10 e 11)

**Files:**
- Modify: `docudata-backend/services/sprints.py` (novo `congelar_modo_da_sprint`; chamado em `iniciar_sprint_e_ancorar_tasks` e `ensure_sprint_row`); `docudata-backend/routers/sprints.py` (`create_sprint`); `docudata-backend/services/pontuacao.py` (~60-75); `docudata-backend/routers/avaliacoes.py` (`_montar_historico` ~100-137); `docudata-backend/routers/projects.py` (~566)
- Test: `docudata-backend/tests/test_auditoria_modo.py` (criar)

**Interfaces:**
- Consumes: `FakeClient`; `tests/test_pontuacao_fechamento.py::_mock_client(sprint=..., projeto=..., sprint_update_capture=...)` (ler o helper para o formato exato de `sprint`).
- Produces: `congelar_modo_da_sprint(client, sprint_id: str) -> str | None` (devolve o `modo_trabalho` efetivo da sprint, grava uma vez; no-op se sprint/projeto não existem).

- [ ] **Step 1: Testes que falham**

```python
from services.sprints import congelar_modo_da_sprint, iniciar_sprint_e_ancorar_tasks
from tests.fake_supabase import FakeClient


def _fake(sprint_extra=None, modo="PULL"):
    return FakeClient({
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False, **(sprint_extra or {})}],
        "projects": [{"id": "p1", "modo_trabalho": modo,
                      "modo_avaliacao": "PONTOS_RELATIVO" if modo == "PULL" else "PONTOS_ATRIBUIDOS"}],
        "tasks": [],
    })


def test_congelar_grava_o_modo_do_projeto():
    fake = _fake()
    assert congelar_modo_da_sprint(fake, "s1") == "PULL"
    s = fake.tables["sprints"][0]
    assert (s["modo_trabalho"], s["modo_avaliacao"]) == ("PULL", "PONTOS_RELATIVO")


def test_congelar_nao_sobrescreve_snapshot_existente():
    fake = _fake({"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS"}, modo="PULL")
    assert congelar_modo_da_sprint(fake, "s1") == "ATRIBUICAO"
    assert fake.tables["sprints"][0]["modo_trabalho"] == "ATRIBUICAO"


def test_iniciar_sprint_grava_snapshot():
    fake = _fake()
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    assert fake.tables["sprints"][0]["modo_trabalho"] == "PULL"


def test_historico_usa_o_modo_da_sprint_e_cai_no_do_projeto():
    from routers.avaliacoes import _montar_historico
    fake = FakeClient({
        "sprints": [
            {"id": "s1", "numero": 1, "project_id": "p1", "modo_trabalho": "ATRIBUICAO"},
            {"id": "s2", "numero": 2, "project_id": "p1", "modo_trabalho": None},
        ],
        "projects": [{"id": "p1", "name": "P", "modo_trabalho": "PULL"}],
        "operacionais": [{"id": "op-1", "nome": "Ana"}],
        "avaliacoes_gerente_edicoes": [],
        "pessoa": [{"id": "g1", "nome": "Gê"}],
    })
    base = {"operacional_id": "op-1", "gerente_id": "g1", "criado_em": "2026-01-01T00:00:00+00:00",
            **{f"resposta_{i}": 3 for i in range(1, 8)}}
    itens = _montar_historico(fake, [dict(base, id="a1", sprint_id="s1"), dict(base, id="a2", sprint_id="s2")])
    modo = {i["sprint_id"]: i["modo_trabalho"] for i in itens}
    assert modo == {"s1": "ATRIBUICAO", "s2": "PULL"}
```

Em `tests/test_pontuacao_fechamento.py` (que já tem `_mock_client`) acrescentar um teste: sprint com `modo_trabalho="PULL"`/`modo_avaliacao="PONTOS_RELATIVO"` e `projeto={"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS"}`; após `calcular_e_travar_pontuacao(client, "sprint-1")`, `sprint_update_capture[0]` deve ter `modo_trabalho == "PULL"` e `modo_avaliacao == "PONTOS_RELATIVO"` (copiar a montagem de um teste vizinho que já usa `sprint=`/`sprint_update_capture=`).

E em `tests/test_migracao_modo.py` um teste: aplicar migração com `para` igual ao modo atual (ATRIBUICAO→ATRIBUICAO) e verificar que nenhum `update` de `sprints` com `{"hibrida": True}` é capturado (usar o mesmo `make_client_completo` do teste `test_aplicar_migracao_para_atribuicao_nao_mexe_no_wip`, lendo a captura de sprints).

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_modo.py tests/test_pontuacao_fechamento.py tests/test_migracao_modo.py`
Expected: FAIL (`ImportError: congelar_modo_da_sprint`; o fechamento ainda lê o projeto; `hibrida` ainda marcado).

- [ ] **Step 3: Implementar**

`services/sprints.py`:

```python
def congelar_modo_da_sprint(client, sprint_id: str) -> Optional[str]:
    """Grava em sprints.modo_trabalho/modo_avaliacao o modo vigente do projeto
    quando a sprint começa. Só preenche o que ainda está nulo (o snapshot de
    uma sprint nunca muda depois). No-op se sprint ou projeto não existem."""
    linhas = client.table("sprints").select("project_id, modo_trabalho, modo_avaliacao").eq("id", sprint_id).execute().data
    if not linhas:
        return None
    sprint = linhas[0]
    if sprint.get("modo_trabalho") and sprint.get("modo_avaliacao"):
        return sprint["modo_trabalho"]
    projeto = client.table("projects").select("modo_trabalho, modo_avaliacao").eq("id", sprint.get("project_id")).execute().data
    if not projeto:
        return sprint.get("modo_trabalho")
    modo_trabalho = sprint.get("modo_trabalho") or projeto[0].get("modo_trabalho") or "ATRIBUICAO"
    modo_avaliacao = sprint.get("modo_avaliacao") or projeto[0].get("modo_avaliacao") or "PONTOS_ATRIBUIDOS"
    client.table("sprints").update({"modo_trabalho": modo_trabalho, "modo_avaliacao": modo_avaliacao}).eq("id", sprint_id).execute()
    return modo_trabalho
```

Em `iniciar_sprint_e_ancorar_tasks`, trocar a leitura de `sprint_row`/`projeto`/`em_pull` da Task 5 por `em_pull = congelar_modo_da_sprint(client, sprint_id) == "PULL"` (chamar logo após marcar `iniciada`, para toda chamada; é idempotente).

`ensure_sprint_row`: trocar o insert por

```python
    try:
        criada = client.table("sprints").insert({"project_id": project_id, "numero": numero}).execute()
    except Exception:
        return  # race condition (UNIQUE) — outra request criou primeiro
    try:
        if criada.data:
            congelar_modo_da_sprint(client, criada.data[0]["id"])
    except Exception:
        pass  # best-effort: o fechamento cai no modo do projeto
```

`routers/sprints.py::create_sprint`: antes do `return response.data[0]`, se `data.iniciada`, chamar `congelar_modo_da_sprint(client, response.data[0]["id"])` dentro de `try/except Exception: pass` (importar de `services.sprints`).

`services/pontuacao.py::calcular_e_travar_pontuacao`: o select da sprint passa a ser `"id, project_id, modo_trabalho, modo_avaliacao"`; depois de ler `projeto_row`:

```python
    sprint_row = sprint_resp.data[0]
    modo_trabalho = sprint_row.get("modo_trabalho") or projeto_row.get("modo_trabalho") or "ATRIBUICAO"
    modo_avaliacao = sprint_row.get("modo_avaliacao") or projeto_row.get("modo_avaliacao") or "PONTOS_ATRIBUIDOS"
```

(mantém o `update` existente, que agora só preenche o fallback; ajustar o comentário: o snapshot nasce no início da sprint).

`routers/avaliacoes.py::_montar_historico`: `sprints = _por_id(client, "sprints", "id, numero, project_id, modo_trabalho", ...)` e `"modo_trabalho": sprint.get("modo_trabalho") or projeto.get("modo_trabalho") or "ATRIBUICAO"`.

`routers/projects.py` (~566): `if sprint_ativa_id and de_modo != data.para:` antes de marcar `hibrida`.

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_modo.py tests/test_pontuacao_fechamento.py tests/test_migracao_modo.py tests/test_avaliacoes_historico_edicao.py tests/test_iniciar_sprint_ancora_tasks.py tests/test_auditoria_travamento.py`
Expected: PASS. Se algum teste existente que mocka `sprints.select` quebrar, ajustar o mock para devolver as novas colunas.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services docudata-backend/routers docudata-backend/tests
git commit -m "fix(sprints): grava o modo da sprint ao iniciar e usa o snapshot no fechamento e no histórico

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Métricas de cycle time (itens 12 e 13)

**Files:**
- Modify: `docudata-backend/routers/metricas.py` (`_cycle_time_segundos` ~48; `get_cycle_time` ~173)
- Test: `docudata-backend/tests/test_auditoria_metricas.py` (criar)

**Interfaces:**
- Consumes: `FakeClient` (`task_transicoes` ordenado por `timestamp` desc).
- Produces: `_cycle_time_segundos(client, task_id, pull_em=None)` usa `max(transição em_andamento, pull_em)`.

- [ ] **Step 1: Testes que falham**

```python
from fastapi.testclient import TestClient

from routers.metricas import _cycle_time_segundos
from tests.fake_supabase import FakeClient


def _transicoes(**ts):
    linhas = []
    for para, quando in ts.items():
        linhas.append({"task_id": "t1", "campo": "coluna_kanban", "para": para, "timestamp": quando,
                       "duracao_fase_anterior_segundos": 1})
    return FakeClient({"task_transicoes": linhas})


def test_pull_em_posterior_a_transicao_antiga_e_o_inicio():
    fake = _transicoes(em_andamento="2026-11-01T10:00:00+00:00", concluida="2026-11-03T10:00:00+00:00")
    # puxada de novo depois de devolvida: o tempo na fila não conta
    assert _cycle_time_segundos(fake, "t1", "2026-11-03T00:00:00+00:00") == 10 * 3600


def test_pull_em_anterior_a_transicao_nao_muda_nada():
    fake = _transicoes(em_andamento="2026-11-02T10:00:00+00:00", concluida="2026-11-03T10:00:00+00:00")
    assert _cycle_time_segundos(fake, "t1", "2026-11-01T00:00:00+00:00") == 24 * 3600


def test_sem_pull_em_usa_a_transicao():
    fake = _transicoes(em_andamento="2026-11-02T10:00:00+00:00", concluida="2026-11-03T10:00:00+00:00")
    assert _cycle_time_segundos(fake, "t1", None) == 24 * 3600


def test_cycle_time_de_sprint_inexistente_devolve_lista_vazia(monkeypatch):
    import routers.metricas as metricas
    from main import app
    fake = FakeClient({
        "projects": [{"id": "p1"}],
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1}],
        "tasks": [{"id": "t1", "project_id": "p1", "sprint_id": "s1", "coluna_kanban": "concluida",
                   "titulo": "X", "operacional_id": None, "pull_em": None}],
        "task_transicoes": [
            {"task_id": "t1", "campo": "coluna_kanban", "para": "em_andamento",
             "timestamp": "2026-11-02T10:00:00+00:00", "duracao_fase_anterior_segundos": 1},
            {"task_id": "t1", "campo": "coluna_kanban", "para": "concluida",
             "timestamp": "2026-11-03T10:00:00+00:00", "duracao_fase_anterior_segundos": 1},
        ],
    })
    monkeypatch.setattr(metricas, "get_client", lambda: fake)
    tc = TestClient(app)
    # a rota é pública/autenticada conforme o router; usar autenticar se o teste devolver 401
    resp = tc.get("/metricas/p1/cycle-time", params={"sprint_numero": 99})
    assert resp.status_code in (200, 401)
    if resp.status_code == 200:
        assert resp.json() == []
```

Obs. para o executor: se a rota exigir sessão, usar a fixture `autenticar` (como nos outros testes) e exigir `status_code == 200` no teste final; o formato de retorno de `get_cycle_time` é lista (conferir no fim da função) — ajustar o `== []` se o retorno for um dict com lista.

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_metricas.py`
Expected: FAIL em `pull_em_posterior...` (retorna 2 dias) e `sprint_inexistente` (devolve a task).

- [ ] **Step 3: Implementar**

`_cycle_time_segundos`, trocar o cálculo de `ts_inicio`:

```python
    em_andamento = _ultima_transicao_para(client, task_id, "em_andamento")
    ts_fim = _parse_ts(concluida.get("timestamp"))
    ts_transicao = _parse_ts(em_andamento.get("timestamp")) if em_andamento else None
    ts_pull = _parse_ts(pull_em)
    # Puxar (de novo) depois da transição antiga reinicia o trabalho: o tempo na
    # fila não é cycle time. /puxar não grava transição, por isso o pull_em manda.
    if ts_pull and (ts_transicao is None or ts_pull > ts_transicao):
        ts_inicio = ts_pull
    else:
        ts_inicio = ts_transicao
```

Atualizar o docstring (uma frase). Em `get_cycle_time`, no bloco de `sprint_numero`:

```python
        if not sprint_resp.data:
            return []
        tasks_query = tasks_query.eq("sprint_id", sprint_resp.data[0]["id"])
```

(conferir que o retorno normal da função também é uma lista; se for outro formato, devolver o equivalente vazio).

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_metricas.py tests/test_metricas_novos_endpoints.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/metricas.py docudata-backend/tests/test_auditoria_metricas.py
git commit -m "fix(metricas): cycle time usa pull_em quando é posterior e sprint inexistente devolve vazio

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Sair de Pull restaura o WIP por pessoa anterior (item 14)

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (CHECK de `configuracao_historico.campo`); `docudata-backend/routers/projects.py` (`aplicar_migrar_modo` ~525; `get_modos_historico`; `update_modos` ~372)
- Test: `docudata-backend/tests/test_auditoria_modo.py`

**Interfaces:**
- Consumes: `FakeClient`; `require_not_operacional` (autenticar como gerente).
- Produces: linhas `configuracao_historico` com `campo="wip_por_pessoa"`, `valor_anterior` = WIP anterior como texto (`""` quando era nulo), gravadas ao entrar em Pull (por `aplicar_migrar_modo` e por `update_modos`); ao sair de Pull o `por_pessoa` volta ao valor da linha mais recente. Sem linha (projeto já estava em Pull): WIP fica como está (decisão marcada).

- [ ] **Step 1: Testes que falham** (acrescentar em `tests/test_auditoria_modo.py`)

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def projetos_api(monkeypatch, autenticar):
    def _make(fake):
        import routers.projects as projects_router
        from main import app
        monkeypatch.setattr(projects_router, "get_client", lambda: fake)
        return autenticar(TestClient(app), cargo="gerente")
    return _make


def _projeto(modo, wip):
    return FakeClient({
        "projects": [{"id": "p1", "name": "P", "modo_trabalho": modo, "modo_avaliacao": "PONTOS_ATRIBUIDOS",
                      "wip_config": wip}],
        "tasks": [], "sprints": [], "ingestions": [], "operacionais": [], "pessoa": [],
        "configuracao_historico": [], "migracoes_modo": [],
    })


def test_ida_e_volta_restaura_o_wip_por_pessoa(projetos_api):
    fake = _projeto("ATRIBUICAO", {"por_pessoa": 3, "por_coluna_em_andamento": 5})
    tc = projetos_api(fake)
    assert tc.post("/projects/p1/migrar-modo", json={"para": "PULL"}).status_code == 200
    assert fake.tables["projects"][0]["wip_config"]["por_pessoa"] == 1
    assert tc.post("/projects/p1/migrar-modo", json={"para": "ATRIBUICAO"}).status_code == 200
    assert fake.tables["projects"][0]["wip_config"] == {"por_pessoa": 3, "por_coluna_em_andamento": 5}


def test_ida_e_volta_com_wip_nulo_volta_a_nulo(projetos_api):
    fake = _projeto("ATRIBUICAO", {"por_pessoa": None, "por_coluna_em_andamento": None})
    tc = projetos_api(fake)
    tc.post("/projects/p1/migrar-modo", json={"para": "PULL"})
    tc.post("/projects/p1/migrar-modo", json={"para": "ATRIBUICAO"})
    assert fake.tables["projects"][0]["wip_config"]["por_pessoa"] is None


def test_sair_de_pull_sem_registro_nao_mexe_no_wip(projetos_api):
    fake = _projeto("PULL", {"por_pessoa": 1, "por_coluna_em_andamento": None})
    projetos_api(fake).post("/projects/p1/migrar-modo", json={"para": "ATRIBUICAO"})
    assert fake.tables["projects"][0]["wip_config"]["por_pessoa"] == 1


def test_historico_de_modos_nao_expoe_o_registro_de_wip(projetos_api):
    fake = _projeto("ATRIBUICAO", {"por_pessoa": 3, "por_coluna_em_andamento": None})
    tc = projetos_api(fake)
    tc.post("/projects/p1/migrar-modo", json={"para": "PULL"})
    campos = {l["campo"] for l in tc.get("/projects/p1/modos-historico").json()}
    assert "wip_por_pessoa" not in campos
```

Obs.: `FakeClient.update(...)` devolve a linha mesclada; `aplicar_migrar_modo` lê `proj_update.data[0]["wip_config"]`. Se `get_current_sprint_id` ou `_avisar_mudanca_para_pull` reclamarem do fake, adicionar as tabelas faltantes ao dict (o e-mail é best-effort).

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_modo.py -k "wip or historico_de_modos"`
Expected: FAIL (`por_pessoa` continua 1 depois da volta).

- [ ] **Step 3: Implementar**

`supabase_schema.sql`, depois do `CREATE TABLE configuracao_historico`, acrescentar (migração manual, aditiva):

```sql
-- 2026-11-17: guarda o WIP por pessoa de antes de entrar em Pull, para restaurar ao sair.
ALTER TABLE configuracao_historico DROP CONSTRAINT IF EXISTS configuracao_historico_campo_check;
ALTER TABLE configuracao_historico
    ADD CONSTRAINT configuracao_historico_campo_check
    CHECK (campo IN ('modo_trabalho','modo_avaliacao','wip_por_pessoa'));
```

`routers/projects.py`: adicionar helpers

```python
def _guardar_wip_anterior(client, project_id: str, wip_atual: dict, email: str) -> None:
    anterior = wip_atual.get("por_pessoa")
    client.table("configuracao_historico").insert({
        "project_id": project_id,
        "campo": "wip_por_pessoa",
        "valor_anterior": "" if anterior is None else str(anterior),
        "valor_novo": "1",
        "usuario_email": email,
    }).execute()


def _restaurar_wip_anterior(client, project_id: str, wip_atual: dict) -> dict:
    """Volta o por_pessoa ao valor guardado na última entrada em Pull. Sem
    registro (projeto que já estava em Pull), mantém o que está."""
    linhas = (
        client.table("configuracao_historico").select("valor_anterior")
        .eq("project_id", project_id).eq("campo", "wip_por_pessoa")
        .order("criado_em", desc=True).limit(1).execute().data or []
    )
    if not linhas:
        return wip_atual
    bruto = linhas[0].get("valor_anterior")
    return {**wip_atual, "por_pessoa": int(bruto) if bruto not in (None, "") else None}
```

Em `aplicar_migrar_modo`, o bloco "RF-A5" passa a:

```python
    wip_atual = (proj_update.data[0].get("wip_config") if proj_update.data else None) or {}
    if data.para == "PULL":
        if de_modo != "PULL":
            _guardar_wip_anterior(client, project_id, wip_atual, pessoa["email"])
        client.table("projects").update({"wip_config": {**wip_atual, "por_pessoa": 1}}).eq("id", project_id).execute()
    elif de_modo == "PULL":
        novo_wip = _restaurar_wip_anterior(client, project_id, wip_atual)
        if novo_wip != wip_atual:
            client.table("projects").update({"wip_config": novo_wip}).eq("id", project_id).execute()
```

Em `update_modos` (ramo `if payload.get("modo_trabalho") == "PULL":`), chamar `_guardar_wip_anterior` apenas se `atual.get("modo_trabalho") != "PULL"` (hoje esse endpoint recusa troca de modo, então o ramo só roda em Pull→Pull; a guarda evita registro duplicado). `get_modos_historico`: acrescentar `.in_("campo", ["modo_trabalho", "modo_avaliacao"])` na query (o `ConfiguracaoHistoricoResponse` tem `Literal` só desses dois).

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_auditoria_modo.py tests/test_migracao_modo.py tests/test_project_modos.py tests/test_modos_schema.py`
Expected: PASS. `tests/test_schema_migrations_comentadas.py` pode exigir formato de migração; se falhar, seguir o padrão que ele cobra.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/projects.py docudata-backend/supabase_schema.sql docudata-backend/tests
git commit -m "fix(projects): sair de Pull restaura o WIP por pessoa anterior (guardado em configuracao_historico)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Avisar o usuário no resumo final: rodar a migração do `ALTER TABLE configuracao_historico` no Supabase ANTES do deploy (sem ela o insert de `wip_por_pessoa` falha na migração de modo).

---

### Task 10: Parar de gravar tokens e custo no commit (extração)

**Files:**
- Modify: `docudata-backend/services/commit_extraction.py` (~21-22, ~122-125, ~154-156)
- Test: `docudata-backend/tests/test_github_integration.py` (teste `test_extracao_persiste_origem_sem_diff`, ~745)

**Interfaces:**
- Consumes: —
- Produces: registro de `ingestions` de commit sem `input_tokens`/`output_tokens`/`cost_usd`.

- [ ] **Step 1: Teste que falha** (no final de `test_extracao_persiste_origem_sem_diff`, depois do último `assert`)

```python
    assert "cost_usd" not in row
    assert "input_tokens" not in row
    assert "output_tokens" not in row
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest -q tests/test_github_integration.py::test_extracao_persiste_origem_sem_diff`
Expected: FAIL (`cost_usd` presente).

- [ ] **Step 3: Implementar**

Em `commit_extraction.py`: apagar as constantes `_COST_PER_INPUT_TOKEN`/`_COST_PER_OUTPUT_TOKEN`; apagar as quatro linhas `uso = ...`/`tokens_entrada`/`tokens_saida`/`custo`; remover as chaves `"input_tokens"`, `"output_tokens"`, `"cost_usd"` do dict `registro`. Manter `include_raw=True` e `raw_msg` só se algo mais usar; se `raw_msg` ficar sem uso, remover a atribuição `raw_msg = resultado["raw"]` (e deixar `include_raw=True`, pois muda o formato de `resultado`, que os testes simulam).

- [ ] **Step 4: Rodar**

Run: `.venv/bin/python -m pytest -q tests/test_github_integration.py tests/test_commit_qualidade_pipeline.py tests/test_commit_tracker_hook.py tests/test_remocao_orcamento.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/commit_extraction.py docudata-backend/tests/test_github_integration.py
git commit -m "fix(commits): para de gravar tokens e custo de IA na ingestão de commit

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Frontend do Kanban (itens 1, 5 e 18)

**Files:**
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx` (`TaskModal.handleSubmit` ~212-230; `TaskCard` ~1019-1036; `handleDrop` ~1223; uso do `TaskCard` ~1535)
- Test: `docudata-frontend/tests/auditoria-kanban.test.mjs` (criar)

**Interfaces:**
- Consumes: `modoTrabalho`, `ehOperacional`, `meuOperacional` (já existem em `TasksKanbanTab`); `patchTaskKanban` (aceita `operacional_id?: string | null`).
- Produces: `TaskCard` com prop `arrastavel: boolean`; helper local `podeArrastar(t)`.

- [ ] **Step 1: Teste que falha** (`tests/auditoria-kanban.test.mjs`, mesmo estilo dos testes de regex existentes)

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const KANBAN = readFileSync(new URL("../app/components/TasksKanbanTab.tsx", import.meta.url), "utf-8");

test("edição só envia operacional_id quando mudou, e nunca em Pull", () => {
  assert.match(KANBAN, /const operacionalMudou = modoTrabalho !== "PULL" && operacionalId !== \(task\?\.operacional_id \?\? ""\);/);
  assert.match(KANBAN, /\.\.\.\(operacionalMudou \? \{ operacional_id: operacionalId \|\| null \} : \{\}\)/);
});

test("criação continua mandando operacional_id só quando escolhido", () => {
  assert.match(KANBAN, /operacional_id: operacionalId \|\| undefined,\n\s+funcionalidade_id: funcId \|\| undefined,\n\s+extra,/);
});

test("card de outra pessoa não é arrastável para operacional", () => {
  assert.match(KANBAN, /draggable=\{arrastavel\}/);
  assert.match(KANBAN, /function podeArrastar\(t: TaskKanbanResponse\)/);
  assert.match(KANBAN, /arrastavel=\{podeArrastar\(t\)\}/);
});

test("handleDrop também recusa mover task de colega", () => {
  assert.match(KANBAN, /if \(!podeArrastar\(task\)\) return;/);
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-frontend && node --test tests/auditoria-kanban.test.mjs`
Expected: FAIL (4 testes).

- [ ] **Step 3: Implementar**

`TaskModal.handleSubmit`: antes do `try`, calcular `const operacionalMudou = modoTrabalho !== "PULL" && operacionalId !== (task?.operacional_id ?? "");`. No ramo `patchTaskKanban`, trocar a linha `operacional_id: operacionalId || undefined,` por `...(operacionalMudou ? { operacional_id: operacionalId || null } : {}),`. No ramo `createTaskKanban` manter a linha como está (já fica sem efeito em Pull, pois o campo não existe na UI de Pull e `operacionalId` começa `""`).

`TaskCard`: adicionar `arrastavel` às props (`arrastavel: boolean;`) e trocar `draggable` por `draggable={arrastavel}`.

`TasksKanbanTab`, depois de `jaPediu`:

```tsx
  // Operacional só arrasta a própria task, ou puxa da fila em Pull (task sem dono em Planejado).
  function podeArrastar(t: TaskKanbanResponse): boolean {
    if (!ehOperacional) return true;
    if (!meuOperacional) return false;
    if (t.operacional_id === meuOperacional.id) return true;
    return modoTrabalho === "PULL" && !t.operacional_id && t.coluna_kanban === "planejado";
  }
```

Em `handleDrop`, logo depois de `if (!task || task.coluna_kanban === coluna) return;` acrescentar `if (!podeArrastar(task)) return;`. No uso do card: `arrastavel={podeArrastar(t)}`.

- [ ] **Step 4: Rodar**

Run: `cd docudata-frontend && npm test && npx tsc --noEmit`
Expected: todos passam, sem erro de tipo. (Os regex dos passos 1 dependem do texto exato; se o Prettier/estilo do arquivo divergir, ajustar o teste ao texto realmente escrito, mantendo a intenção.)

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/components/TasksKanbanTab.tsx docudata-frontend/tests/auditoria-kanban.test.mjs
git commit -m "fix(kanban): não reenvia responsável em Pull, envia null em Sem operacional e trava arrastar task de colega

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Verificação final

**Files:** nenhum.

- [ ] **Step 1:** `cd docudata-backend && .venv/bin/python -m pytest -q` — Expected: tudo verde (1223 + testes novos).
- [ ] **Step 2:** `cd docudata-frontend && npm test && npx tsc --noEmit` — Expected: verde.
- [ ] **Step 3:** `git status` limpo (exceto arquivos já modificados antes do trabalho) e `git log --oneline -12` com um commit por task.
- [ ] **Step 4:** Avisar o usuário da migração manual da Task 9 (CHECK de `configuracao_historico`), e dos itens de decisão: `em_ajuste` (Task 3), WIP sem registro ao sair de Pull (Task 9), `devolucao_penalidade` preservado ao reabrir (Task 6).

---

## Self-review

**Spec coverage:** #1 (T1 back, T11 front), #2 (T5), #4 (T4), #5 (T2 back, T11 front), #6 e #7 (T3), #8 e #9 (T6), #10 (T7), #11 (T7; frontend já lê o campo da API), #12 e #13 (T8), #14 (T9), #18 (T1 back, T11 front), `commit_extraction` (T10). Itens fora de escopo não aparecem.

**Placeholders:** nenhum "TBD"; os pontos que dependem de formato de mock existente (T6 mock de `sprints`, T7 teste de `pontuacao_fechamento`/`migracao_modo`, T8 formato de retorno/autenticação do cycle-time) trazem instrução explícita do que conferir. Os testes deste plano não foram executados na hora de escrever; os comandos "Expected: FAIL" são a previsão.

**Consistência de tipos:** `congelar_modo_da_sprint(client, sprint_id) -> Optional[str]` usado igual em T5 (via T7), T7; `_checar_operacional_pode_mexer(client, pessoa, task, data)` só em T2; `_guardar_wip_anterior`/`_restaurar_wip_anterior` só em T9; fixture `cliente_para(modo, task, cargo, meu_operacional)` definida em T1 e reutilizada em T2 e T5; `make_client` importado de `tests/test_pull_devolver.py` em T3 e T4. Ordem T5 → T7: T5 escreve inicialmente a leitura de projeto dentro de `iniciar_sprint_e_ancorar_tasks`, e T7 a substitui por `congelar_modo_da_sprint` (dito em T7).
