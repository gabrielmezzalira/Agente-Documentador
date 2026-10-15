# Modos de Trabalho — Entrega 4 (fechamento de lacunas pós-deploy) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar as 3 lacunas reais confirmadas por auditoria pós-deploy da Entrega 3: (1) `modo_avaliacao` deixa de ser escolha livre e vira derivado de `modo_trabalho`; (2) `PATCH /modos` deixa de conseguir trocar `modo_trabalho` sem migrar tasks (causa raiz do bug real observado em produção) — só `POST /migrar-modo` pode, e a UI finalmente ganha um botão pra isso; (3) gerente não consegue mais atribuir `operacional_id` manualmente (criar ou editar task) quando o projeto está em modo PULL.

**Architecture:** Onda 1 muda 3 arquivos de backend (schemas, projects router, tasks router) fechando as regras na origem — nenhum caminho de API consegue mais produzir o estado inconsistente que causou o bug. Onda 2 conecta a UI ao que já existe/foi corrigido no backend: um modal novo de migração, remoção do dropdown de `modo_avaliacao`, e uma prop nova (`modoTrabalho`) no modal de task que já recebe esse dado no componente pai.

**Tech Stack:** FastAPI + Pydantic + supabase-py (backend, mockado via `unittest.mock.MagicMock` nos testes, padrão já usado em `tests/test_project_modos.py` e `tests/test_migracao_modo.py`); Next.js 15 / React 19 com inline styles, sem design system file (frontend).

**Spec:** Sem spec file — classificado como *bounded* na skill de brainstorming (fluxos já existentes sendo estendidos). O design aprovado está registrado em `.planning/feature-flow-state.md`, seção "Design aprovado" (2026-09-21).

## Global Constraints

- Nenhuma migração retroativa de dados: projetos que já sofreram o bug (modo trocado sem migrar tasks) **não são corrigidos automaticamente** por este plano — o comportamento só muda daqui pra frente. Se o usuário quiser corrigir um projeto específico, ele mesmo aciona `POST /migrar-modo` pela UI nova.
- `/puxar` e `/devolver` (`docudata-backend/routers/tasks.py:465,513`) escrevem `operacional_id` direto na tabela via supabase — **não tocar nesses dois endpoints**, e confirmar ao final que a suíte completa (`tests/test_pull_devolver.py`, `tests/test_hardening_spec09.py`) continua verde.
- `POST /desvincular-planejado` fica fora de escopo desta entrega.
- Convenção do projeto: commit direto em `main`, sem branch/PR.
- Onda 2 só começa depois da Onda 1 100% verde (testes rodando, sem placeholder).

---

## ONDA 1 — Backend

### Task 1: `modo_avaliacao` deixa de ser aceito em `PATCH /modos` — vira sempre derivado de `modo_trabalho`

**Files:**
- Modify: `docudata-backend/models/schemas.py:79-86` (`ModosProjetoUpdate`)
- Modify: `docudata-backend/routers/projects.py:283-328` (`update_modos`)
- Test: `docudata-backend/tests/test_project_modos.py`

**Interfaces:**
- Consumes: nada de tasks anteriores (primeira task da onda).
- Produces: `update_modos` passa a ignorar qualquer `modo_avaliacao` recebido e a persistir sempre `modo_avaliacao` derivado do `modo_trabalho` final do projeto (o que ficou salvo depois do update, não o payload). Tasks seguintes (2, 3) reusam esse mesmo padrão de derivação — a função auxiliar `_derivar_modo_avaliacao(modo_trabalho: str) -> str` fica definida em `routers/projects.py`, no escopo do módulo, e é importada por `aplicar_migrar_modo` (Task 3).

- [ ] **Step 1: Escrever os testes que descrevem o comportamento novo**

Em `docudata-backend/tests/test_project_modos.py`, adicione (mantendo os fixtures `_PROJETO_BASE`, `_mock_client` e `make_client` já existentes no arquivo):

```python
def test_patch_modos_ignora_modo_avaliacao_recebido_e_deriva_de_pull(make_client):
    tc, estado = make_client(projeto={**_PROJETO_BASE, "modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_ATRIBUIDOS"})

    resp = tc.patch("/projects/proj-1/modos", json={"modo_avaliacao": "PONTOS_ATRIBUIDOS", "pull_piso_pontos": 2})

    assert resp.status_code == 200
    assert resp.json()["modo_avaliacao"] == "PONTOS_RELATIVO"


def test_patch_modos_deriva_pontos_atribuidos_quando_atribuicao(make_client):
    tc, estado = make_client(projeto={**_PROJETO_BASE, "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_RELATIVO"})

    resp = tc.patch("/projects/proj-1/modos", json={"pull_piso_pontos": 2})

    assert resp.status_code == 200
    assert resp.json()["modo_avaliacao"] == "PONTOS_ATRIBUIDOS"
```

Essas duas substituem o teste antigo que dependia de `modo_avaliacao` ser aceito livremente (procure no arquivo por qualquer teste que envie `modo_avaliacao` no payload esperando que ele seja gravado como veio — não há nenhum hoje, então não há nada pra remover; os testes acima são adição pura).

- [ ] **Step 2: Rodar os testes novos e confirmar que falham**

Run: `cd docudata-backend && python -m pytest tests/test_project_modos.py -v -k "deriva"`
Expected: FAIL — `modo_avaliacao` ainda vem do payload sem derivação (o segundo teste falha porque hoje, sem enviar `modo_avaliacao`, o campo simplesmente não muda — fica `PONTOS_RELATIVO`, não deriva pra `PONTOS_ATRIBUIDOS`).

- [ ] **Step 3: `ModosProjetoUpdate` para de aceitar `modo_avaliacao`**

Em `docudata-backend/models/schemas.py`, linha 79-86:

```python
class ModosProjetoUpdate(BaseModel):
    """PATCH /projects/{id}/modos — RF-A1..A4. Todos os campos são opcionais;
    só o que vier preenchido é alterado (mesmo padrão de ContratoUpdate).
    modo_avaliacao não é aceito aqui: é sempre derivado de modo_trabalho
    (ver _derivar_modo_avaliacao em routers/projects.py)."""
    modo_trabalho: Optional[ModoTrabalho] = None
    pull_exigir_hidratacao: Optional[bool] = None
    pull_piso_pontos: Optional[float] = Field(default=None, gt=0)
    pull_teto: Optional[float] = Field(default=None, gt=0)
```

- [ ] **Step 4: Implementar `_derivar_modo_avaliacao` e usá-la em `update_modos`**

Em `docudata-backend/routers/projects.py`, logo acima de `update_modos` (antes da linha 283), adicione:

```python
def _derivar_modo_avaliacao(modo_trabalho: str) -> str:
    """modo_avaliacao deixou de ser escolha livre do gerente (Entrega 4):
    PULL sempre avalia por PONTOS_RELATIVO, ATRIBUICAO sempre por
    PONTOS_ATRIBUIDOS. Ver .planning/feature-flow-state.md (Design
    aprovado, item 1)."""
    return "PONTOS_RELATIVO" if modo_trabalho == "PULL" else "PONTOS_ATRIBUIDOS"
```

Depois, modifique `update_modos` (linha 283-328) para derivar `modo_avaliacao` sempre que houver alguma mudança a persistir. Substitua o trecho:

```python
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        response = client.table("projects").select(_CAMPOS_PROJETO).eq("id", project_id).execute()
        return _sanitize(response.data[0])

    for campo in ("modo_trabalho", "modo_avaliacao"):
        novo = payload.get(campo)
        if novo is not None and novo != atual.get(campo):
            client.table("configuracao_historico").insert({
                "project_id": project_id,
                "campo": campo,
                "valor_anterior": atual.get(campo),
                "valor_novo": novo,
                "usuario_email": pessoa["email"],
            }).execute()
```

por:

```python
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        response = client.table("projects").select(_CAMPOS_PROJETO).eq("id", project_id).execute()
        return _sanitize(response.data[0])

    modo_trabalho_efetivo = payload.get("modo_trabalho", atual.get("modo_trabalho"))
    payload["modo_avaliacao"] = _derivar_modo_avaliacao(modo_trabalho_efetivo)

    for campo in ("modo_trabalho", "modo_avaliacao"):
        novo = payload.get(campo)
        if novo is not None and novo != atual.get(campo):
            client.table("configuracao_historico").insert({
                "project_id": project_id,
                "campo": campo,
                "valor_anterior": atual.get(campo),
                "valor_novo": novo,
                "usuario_email": pessoa["email"],
            }).execute()
```

Nota: `data.model_dump()` não tem mais `modo_avaliacao` como chave (removido do schema no Step 3), então não há colisão — `payload["modo_avaliacao"]` é sempre a versão derivada, nunca a do cliente.

- [ ] **Step 5: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && python -m pytest tests/test_project_modos.py -v`
Expected: PASS em todos, incluindo os dois novos. Preste atenção especial em `test_patch_modos_sem_mudanca_nao_grava_historico` (linha 102-109 do arquivo) — ela já espera `historico == []` ao mandar o mesmo `modo_trabalho` atual; como a derivação de `modo_avaliacao` produz o mesmo valor que já estava lá (`PONTOS_ATRIBUIDOS` pra um projeto em `ATRIBUICAO`), o histórico continua vazio e o teste deve seguir passando sem alteração.

- [ ] **Step 6: Commit**

```bash
cd docudata-backend && git add models/schemas.py routers/projects.py tests/test_project_modos.py
git commit -m "fix(modos): modo_avaliacao vira derivado de modo_trabalho, não mais escolha livre"
```

---

### Task 2: `PATCH /modos` rejeita tentativa de mudar `modo_trabalho`

**Files:**
- Modify: `docudata-backend/routers/projects.py:283-328` (`update_modos`, já tocado na Task 1)
- Test: `docudata-backend/tests/test_project_modos.py`

**Interfaces:**
- Consumes: `_derivar_modo_avaliacao` (Task 1).
- Produces: `update_modos` responde `422` com `detail` explicando que a troca de `modo_trabalho` deve passar por `POST /migrar-modo`, sempre que `data.modo_trabalho` vier preenchido e diferente do atual. Nenhuma outra rota depende disso.

- [ ] **Step 1: Escrever os testes que descrevem a rejeição**

Em `docudata-backend/tests/test_project_modos.py`, adicione:

```python
def test_patch_modos_rejeita_tentativa_de_mudar_modo_trabalho(make_client):
    historico = []
    tc, estado = make_client(historico_insert_capture=historico)

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 422
    assert "migrar-modo" in resp.json()["detail"]
    assert historico == []


def test_patch_modos_aceita_mandar_o_mesmo_modo_trabalho_atual(make_client):
    """Reenviar o valor que já está salvo não é 'trocar' — não deve ser
    rejeitado, é o caso usado por telas que sempre mandam o objeto inteiro."""
    tc, estado = make_client()

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "ATRIBUICAO", "pull_piso_pontos": 2})

    assert resp.status_code == 200
```

Agora remova os dois testes que ficaram obsoletos porque dependiam de `PATCH /modos` conseguir trocar `modo_trabalho` de verdade — eles testavam exatamente o comportamento que esta task elimina:
- `test_patch_modos_troca_modo_trabalho_e_grava_historico` (linha 78-90)
- `test_patch_modos_forca_wip_por_pessoa_1_ao_entrar_em_pull` (linha 93-99)

(Esse comportamento — trocar `modo_trabalho` de fato — já está coberto do lado de `POST /migrar-modo` em `tests/test_migracao_modo.py`, que continua intacto.)

- [ ] **Step 2: Rodar os testes novos e confirmar que falham**

Run: `cd docudata-backend && python -m pytest tests/test_project_modos.py -v -k "rejeita_tentativa_de_mudar or aceita_mandar_o_mesmo"`
Expected: FAIL no primeiro (`resp.status_code` é `200`, não `422`, porque hoje `update_modos` aceita a troca).

- [ ] **Step 3: Implementar a rejeição em `update_modos`**

No mesmo bloco editado na Task 1, logo após a linha que monta `payload` e antes do cálculo de `modo_trabalho_efetivo`, adicione a checagem:

```python
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        response = client.table("projects").select(_CAMPOS_PROJETO).eq("id", project_id).execute()
        return _sanitize(response.data[0])

    if "modo_trabalho" in payload and payload["modo_trabalho"] != atual.get("modo_trabalho"):
        raise HTTPException(
            status_code=422,
            detail="Para trocar o modo de trabalho, use POST /projects/{id}/migrar-modo — essa rota também reclassifica as tasks existentes.",
        )

    modo_trabalho_efetivo = payload.get("modo_trabalho", atual.get("modo_trabalho"))
    payload["modo_avaliacao"] = _derivar_modo_avaliacao(modo_trabalho_efetivo)
```

Note que `modo_trabalho_efetivo` continua igual a `atual.get("modo_trabalho")` daqui pra frente (já que o único jeito de chegar a esse ponto é `modo_trabalho` ausente ou igual ao atual) — a linha permanece pra clareza e porque `payload.get("modo_trabalho")` pode legitimamente ser o mesmo valor reenviado (Step 1, segundo teste novo).

- [ ] **Step 4: Rodar a suíte inteira do arquivo e confirmar que passa**

Run: `cd docudata-backend && python -m pytest tests/test_project_modos.py -v`
Expected: PASS em todos os testes restantes do arquivo (contando os dois obsoletos removidos no Step 1).

- [ ] **Step 5: Commit**

```bash
cd docudata-backend && git add routers/projects.py tests/test_project_modos.py
git commit -m "fix(modos): PATCH /modos rejeita troca de modo_trabalho — só migrar-modo pode, fecha a brecha que causou task com responsável desatualizado"
```

---

### Task 3: `POST /migrar-modo` grava `modo_avaliacao` derivado junto com `modo_trabalho`

**Files:**
- Modify: `docudata-backend/routers/projects.py:419-501` (`aplicar_migrar_modo`)
- Test: `docudata-backend/tests/test_migracao_modo.py`

**Interfaces:**
- Consumes: `_derivar_modo_avaliacao` (Task 1, mesmo módulo — sem necessidade de import, já está no escopo do arquivo).
- Produces: o primeiro `client.table("projects").update(...)` dentro de `aplicar_migrar_modo` passa a incluir `modo_avaliacao` no payload, ao lado de `modo_trabalho`. Nenhuma outra rota depende disso.

- [ ] **Step 1: Escrever o teste que descreve o comportamento novo**

Em `docudata-backend/tests/test_migracao_modo.py`, usando a fixture `make_client_completo` já existente no arquivo, adicione:

```python
def test_aplicar_migracao_para_pull_seta_modo_avaliacao_derivado(make_client_completo, monkeypatch):
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: None)
    tc, tasks_update, migracoes_insert, sprints_update, projects_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True},
        tasks=[],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    assert projects_update[0]["modo_trabalho"] == "PULL"
    assert projects_update[0]["modo_avaliacao"] == "PONTOS_RELATIVO"


def test_aplicar_migracao_para_atribuicao_seta_modo_avaliacao_derivado(make_client_completo, monkeypatch):
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: None)
    tc, tasks_update, migracoes_insert, sprints_update, projects_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": True},
        tasks=[],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "ATRIBUICAO"})

    assert resp.status_code == 200
    assert projects_update[0]["modo_trabalho"] == "ATRIBUICAO"
    assert projects_update[0]["modo_avaliacao"] == "PONTOS_ATRIBUIDOS"
```

- [ ] **Step 2: Rodar os testes novos e confirmar que falham**

Run: `cd docudata-backend && python -m pytest tests/test_migracao_modo.py -v -k "modo_avaliacao_derivado"`
Expected: FAIL — `projects_update[0]` hoje só tem a chave `modo_trabalho`, então `projects_update[0]["modo_avaliacao"]` lança `KeyError` (capturado pelo pytest como falha de asserção/erro).

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/projects.py`, dentro de `aplicar_migrar_modo`, localize:

```python
    proj_update = client.table("projects").update({"modo_trabalho": data.para}).eq("id", project_id).execute()
```

Substitua por:

```python
    proj_update = client.table("projects").update({
        "modo_trabalho": data.para,
        "modo_avaliacao": _derivar_modo_avaliacao(data.para),
    }).eq("id", project_id).execute()
```

- [ ] **Step 4: Rodar a suíte inteira do arquivo e confirmar que passa**

Run: `cd docudata-backend && python -m pytest tests/test_migracao_modo.py -v`
Expected: PASS em todos, incluindo os testes já existentes que checam `projects_update[0]["modo_trabalho"]` — eles não checam o conteúdo completo do dict, então a chave nova não quebra nenhuma asserção existente.

- [ ] **Step 5: Commit**

```bash
cd docudata-backend && git add routers/projects.py tests/test_migracao_modo.py
git commit -m "fix(modos): migrar-modo também grava modo_avaliacao derivado, mantendo consistente com PATCH /modos"
```

---

### Task 4: `create_task` rejeita `operacional_id` do gerente quando o projeto está em PULL

**Files:**
- Modify: `docudata-backend/routers/tasks.py:255-344` (`create_task`)
- Test: `docudata-backend/tests/test_tasks_hidratacao.py`

**Interfaces:**
- Consumes: nenhuma das tasks anteriores (arquivo diferente).
- Produces: `create_task` responde `422` quando `data.operacional_id` vem preenchido e `projeto_row.get("modo_trabalho") == "PULL"`. Task 5 replica o mesmo texto de erro em `patch_task` — mantenha a mensagem idêntica: `"Em modo Pull, tasks não podem ter responsável definido manualmente. Use a fila de puxar."`.

- [ ] **Step 1: Escrever os testes que descrevem a rejeição**

Em `docudata-backend/tests/test_tasks_hidratacao.py`, usando a fixture `make_client` já existente no arquivo (que já monta `client.table("projects").select(...)` retornando o dict passado), adicione:

```python
def test_create_task_rejeita_operacional_id_em_projeto_pull(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": False})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Nova", "pontos": 2, "operacional_id": "op-a"})

    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]
    assert ins == []


def test_create_task_aceita_operacional_id_em_projeto_atribuicao(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": False})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Nova", "pontos": 2, "operacional_id": "op-a"})

    assert resp.status_code == 422
```

Espera — o segundo teste como escrito acima vai falhar mesmo depois da implementação, porque a fixture `make_client` deste arquivo não configura a tabela `operacionais` (usada pela validação existente `op_check` em `create_task`, linha 264-273) — sem isso, `op_check.data` vem vazio e a rota já rejeitaria com 422 por "operacional_id não pertence a este projeto", mascarando o que o teste realmente quer provar. Ajuste o teste pra validar só o caminho que interessa aqui — que o modo PULL é a causa da rejeição, não a validação de pertencimento — usando `modo_trabalho: "ATRIBUICAO"` e **sem** `operacional_id` teria zero valor (não testaria nada novo). Em vez disso, escreva o positivo assim, provando que o gate de PULL não dispara fora de PULL (o 422 que sobra vem de outro motivo, o teste só precisa provar que não é por causa do modo):

```python
def test_create_task_em_atribuicao_nao_rejeita_por_causa_do_modo(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": False})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Nova", "pontos": 2, "operacional_id": "op-a"})

    # 422 aqui vem da validação de "operacional_id não pertence a este
    # projeto" (fixture não cadastra operacionais) — a prova de que o gate
    # de PULL não é o motivo é a mensagem, não o status code.
    assert "Pull" not in resp.json()["detail"]
```

Use esta versão no lugar de `test_create_task_aceita_operacional_id_em_projeto_atribuicao`.

- [ ] **Step 2: Rodar os testes novos e confirmar que falham**

Run: `cd docudata-backend && python -m pytest tests/test_tasks_hidratacao.py -v -k "rejeita_operacional_id or nao_rejeita_por_causa_do_modo"`
Expected: FAIL no primeiro (`resp.status_code` é `422` já hoje por causa da validação de pertencimento — mas `ins` não vem vazio da forma esperada e a mensagem não contém "Pull"; o teste falha na asserção `"Pull" in resp.json()["detail"]"`).

- [ ] **Step 3: Implementar em `create_task`**

Em `docudata-backend/routers/tasks.py`, logo após a checagem de `projeto_row` (linha 262) e antes do bloco `if data.operacional_id:` que valida pertencimento (linha 264), adicione:

```python
    if data.operacional_id and projeto_row.get("modo_trabalho") == "PULL":
        raise HTTPException(
            status_code=422,
            detail="Em modo Pull, tasks não podem ter responsável definido manualmente. Use a fila de puxar.",
        )

    if data.operacional_id:
        op_check = (
```

(A segunda linha `if data.operacional_id:` já existe no arquivo — só adicione o novo bloco acima dela, sem duplicar.)

- [ ] **Step 4: Rodar a suíte inteira do arquivo e confirmar que passa**

Run: `cd docudata-backend && python -m pytest tests/test_tasks_hidratacao.py -v`
Expected: PASS em todos, incluindo os dois testes já existentes no arquivo (`test_create_task_marca_rascunho_em_projeto_pull_com_hidratacao_exigida` e `test_create_task_nao_marca_rascunho_em_projeto_atribuicao`) — nenhum dos dois manda `operacional_id`, então não são afetados pelo novo gate.

- [ ] **Step 5: Commit**

```bash
cd docudata-backend && git add routers/tasks.py tests/test_tasks_hidratacao.py
git commit -m "fix(tasks): create_task rejeita atribuição manual de responsável em projeto PULL"
```

---

### Task 5: `patch_task` rejeita `operacional_id` do gerente quando o projeto está em PULL

**Files:**
- Modify: `docudata-backend/routers/tasks.py:590-620` (`patch_task`)
- Test: novo arquivo `docudata-backend/tests/test_tasks_pull_lock_atribuicao.py`

**Interfaces:**
- Consumes: mesma mensagem de erro definida na Task 4 (`"Em modo Pull, tasks não podem ter responsável definido manualmente. Use a fila de puxar."`) — mantenha o texto idêntico nos dois pontos.
- Produces: `patch_task` responde `422` quando `data.operacional_id is not None` e o projeto da task está em PULL. `/puxar` e `/devolver` não usam `patch_task` (escrevem direto na tabela via `client.table("tasks").update(...)`), então continuam funcionando sem qualquer mudança de código.

- [ ] **Step 1: Escrever o teste (arquivo novo)**

Crie `docudata-backend/tests/test_tasks_pull_lock_atribuicao.py`:

```python
"""Entrega 4 (fechamento de lacunas): gerente não pode mais atribuir
operacional_id manualmente — nem criando (test_tasks_hidratacao.py) nem
editando task — quando o projeto está em modo PULL. Ver
.planning/feature-flow-state.md, Design aprovado, item 3."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(projeto, task):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
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
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "op-2"}]
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


_TASK_BASE = {
    "id": "task-1", "project_id": "proj-1", "titulo": "Fazer algo", "pontos": 2,
    "coluna_kanban": "planejado", "ordem": 0, "sprint_id": None,
    "operacional_id": None, "descricao": None, "bloqueado": False,
    "motivo_bloqueio": None, "checklist": [], "extra": False,
    "created_at": "2026-01-01T00:00:00+00:00",
}


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto, task=None):
        import routers.tasks as tasks_router
        from main import app
        mock_sb = _mock_client(projeto, task or _TASK_BASE)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc
    return _make


def test_patch_task_rejeita_operacional_id_em_projeto_pull(make_client):
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "PULL"})

    resp = tc.patch("/tasks/task-1", json={"operacional_id": "op-2"})

    assert resp.status_code == 422
    assert "Pull" in resp.json()["detail"]


def test_patch_task_aceita_operacional_id_em_projeto_atribuicao(make_client):
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO"})

    resp = tc.patch("/tasks/task-1", json={"operacional_id": "op-2"})

    assert resp.status_code == 200


def test_patch_task_sem_operacional_id_nao_consulta_modo_do_projeto(make_client):
    """PATCH que não mexe em operacional_id não deve nem olhar modo_trabalho
    — evita uma query extra desnecessária em toda edição de task."""
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "PULL"})

    resp = tc.patch("/tasks/task-1", json={"pontos": 5})

    assert resp.status_code == 200
```

- [ ] **Step 2: Rodar os testes novos e confirmar que falham**

Run: `cd docudata-backend && python -m pytest tests/test_tasks_pull_lock_atribuicao.py -v`
Expected: FAIL em `test_patch_task_rejeita_operacional_id_em_projeto_pull` (hoje retorna `200`, não `422`). Os outros dois já devem passar mesmo antes da mudança (comportamento pré-existente) — confirme que passam também, pra isolar exatamente o que falta implementar.

- [ ] **Step 3: Implementar em `patch_task`**

Em `docudata-backend/routers/tasks.py`, dentro de `patch_task`, logo após buscar `task` e `project_id` (linha 606-607) e antes do bloco existente de validação de `data.operacional_id` (linha 609-618), adicione:

```python
    if data.operacional_id is not None:
        proj_modo = client.table("projects").select("modo_trabalho").eq("id", project_id).execute()
        if proj_modo.data and proj_modo.data[0].get("modo_trabalho") == "PULL":
            raise HTTPException(
                status_code=422,
                detail="Em modo Pull, tasks não podem ter responsável definido manualmente. Use a fila de puxar.",
            )

    if data.operacional_id is not None:
        op_check = (
```

(A segunda linha `if data.operacional_id is not None:` já existe — só adicione o bloco novo acima, sem duplicar o corpo existente.)

- [ ] **Step 4: Rodar a suíte do arquivo novo e confirmar que passa**

Run: `cd docudata-backend && python -m pytest tests/test_tasks_pull_lock_atribuicao.py -v`
Expected: PASS em todos os três.

- [ ] **Step 5: Rodar as suítes de regressão que exercitam `patch_task`, `/puxar` e `/devolver`**

Run: `cd docudata-backend && python -m pytest tests/test_task_rbac_operacional.py tests/test_pull_devolver.py tests/test_hardening_spec09.py tests/test_bloqueio_manual.py tests/test_task_conclusao_email.py tests/test_task_confirmacao_sugestao.py tests/test_task_reabertura.py tests/test_task_transicao_operacional_snapshot.py tests/test_tasks_dod_gate.py tests/test_travamento_relogio.py -v`
Expected: PASS em tudo. Esses arquivos cobrem `patch_task` a partir de ângulos diferentes (RBAC, puxar/devolver, bloqueio, conclusão, reabertura, DoD, travamento) — nenhum deles envia `operacional_id` num projeto PULL como parte do que já testam, então o novo gate não deveria mudar nenhum resultado. Se algo quebrar aqui, é sinal de que o novo bloco está disparando fora do caso pretendido — pare e investigue antes de continuar.

- [ ] **Step 6: Commit**

```bash
cd docudata-backend && git add routers/tasks.py tests/test_tasks_pull_lock_atribuicao.py
git commit -m "fix(tasks): patch_task rejeita atribuição manual de responsável em projeto PULL"
```

---

### Task 6: Verificação final da Onda 1 — suíte completa do backend

**Files:** nenhum arquivo novo — só verificação.

**Interfaces:** N/A.

- [ ] **Step 1: Rodar a suíte inteira do backend**

Run: `cd docudata-backend && python -m pytest -v`
Expected: PASS em todos os arquivos de `tests/` (não só os tocados nesta onda). Preste atenção em qualquer teste fora dos arquivos já mencionados que dependa de `modo_avaliacao` vir aceito em `PATCH /modos`, ou de `PATCH /modos` conseguir trocar `modo_trabalho` — se aparecer algum, ele estava testando exatamente o comportamento eliminado por esta entrega e precisa ser ajustado seguindo o mesmo padrão das Tasks 1 e 2 (não pule, não marque como skip).

- [ ] **Step 2: Confirmar ao usuário antes de avançar pra Onda 2**

Reporte: quantos testes novos foram adicionados, quantos obsoletos foram removidos/ajustados (Task 2), e o resultado da suíte completa. Só prossiga pra Onda 2 depois de confirmação explícita — nenhum código de frontend deste plano deve ser escrito antes disso (regra do feature-flow-lean: Onda 2 nunca começa antes da Onda 1 verificada).

---

## ONDA 2 — Frontend

### Task 7: `api.ts` — funções para preview e aplicação de migração de modo

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts:442-461` (`ModosProjetoInput`, `updateProjectModos`)

**Interfaces:**
- Consumes: `GET /projects/{id}/migrar-modo/preview?para=X` e `POST /projects/{id}/migrar-modo` (Onda 1, já testados no backend).
- Produces: `previewMigrarModo(projectId: string, para: "ATRIBUICAO" | "PULL"): Promise<MigracaoPreview>` e `aplicarMigrarModo(projectId: string, para: "ATRIBUICAO" | "PULL"): Promise<{ de_modo: string; para_modo: string; contagem: MigracaoPreview }>`. Task 9 importa e usa essas duas funções e o tipo `MigracaoPreview`.

- [ ] **Step 1: Remover `modo_avaliacao` de `ModosProjetoInput`**

Em `docudata-frontend/app/lib/api.ts`, linha 442-448, troque:

```typescript
export interface ModosProjetoInput {
  modo_trabalho?: "ATRIBUICAO" | "PULL";
  modo_avaliacao?: "PONTOS_ATRIBUIDOS" | "PONTOS_RELATIVO";
  pull_exigir_hidratacao?: boolean;
  pull_piso_pontos?: number;
  pull_teto?: number;
}
```

por:

```typescript
export interface ModosProjetoInput {
  pull_exigir_hidratacao?: boolean;
  pull_piso_pontos?: number;
  pull_teto?: number;
}
```

(`modo_trabalho` também sai daqui — o backend agora rejeita esse campo em `PATCH /modos`, Onda 1 Task 2; a troca de modo de trabalho passa a usar só `aplicarMigrarModo`, definida no Step 2 abaixo.)

- [ ] **Step 2: Adicionar as duas funções novas, logo após `updateProjectModos` (linha 461)**

```typescript
export interface MigracaoPreview {
  entrando_na_fila: number;
  vira_rascunho: number;
  mantem_responsavel: number;
  sem_alteracao: number;
}

export async function previewMigrarModo(
  projectId: string,
  para: "ATRIBUICAO" | "PULL"
): Promise<MigracaoPreview> {
  const res = await apiFetch(`${API}/projects/${projectId}/migrar-modo/preview?para=${para}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao calcular preview da migração");
  }
  return res.json();
}

export async function aplicarMigrarModo(
  projectId: string,
  para: "ATRIBUICAO" | "PULL"
): Promise<{ de_modo: string; para_modo: string; contagem: MigracaoPreview }> {
  const res = await apiFetch(`${API}/projects/${projectId}/migrar-modo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ para }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao aplicar migração de modo");
  }
  return res.json();
}
```

- [ ] **Step 3: Verificar que o projeto compila (typecheck)**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: nenhum erro novo relacionado a `api.ts`. Erros preexistentes não relacionados (se houver) não são responsabilidade desta task — se aparecer algum erro em `page.tsx` sobre `modo_trabalho`/`modo_avaliacao` não existirem mais em `ModosProjetoInput`, isso é esperado e será corrigido na Task 8.

- [ ] **Step 4: Commit**

```bash
cd docudata-frontend && git add app/lib/api.ts
git commit -m "feat(api): adiciona previewMigrarModo e aplicarMigrarModo, remove campos obsoletos de ModosProjetoInput"
```

---

### Task 8: Tela de Configurações — modal de migração + remoção do dropdown de `modo_avaliacao`

**Files:**
- Modify: `docudata-frontend/app/[subarea]/projects/[id]/page.tsx:356-604` (`ModosTrabalhoSection` e tipos `ModoTrabalho`/`ModoAvaliacao` acima dela)

**Interfaces:**
- Consumes: `previewMigrarModo`, `aplicarMigrarModo`, `MigracaoPreview` (Task 7); `updateProjectModos`, `getModosHistorico` (já existentes, sem mudança de assinatura relevante — `updateProjectModos` simplesmente não recebe mais `modo_trabalho`/`modo_avaliacao` no `data`).
- Produces: nenhuma interface nova consumida por outra task — esta é a última peça da seção de Configurações.

- [ ] **Step 1: Importar as funções novas**

No topo de `docudata-frontend/app/[subarea]/projects/[id]/page.tsx`, no bloco de import existente que já traz `updateProjectModos` e `getModosHistorico` (linhas 8-59), adicione `previewMigrarModo`, `aplicarMigrarModo` e o tipo `MigracaoPreview` à lista.

- [ ] **Step 2: Reescrever `ModosTrabalhoSection` (linhas 356-606)**

Substitua o bloco inteiro (do `type ModoTrabalho = ...` na linha 356 até o `}` que fecha a função na linha 606) por:

```typescript
type ModoTrabalho = "ATRIBUICAO" | "PULL";

function derivarModoAvaliacaoLabel(modoTrabalho: ModoTrabalho): string {
  return modoTrabalho === "PULL" ? "Pontos relativo ao squad" : "Pontos atribuídos";
}

function MigrarModoModal({
  projectId,
  para,
  onClose,
  onMigrado,
}: {
  projectId: string;
  para: ModoTrabalho;
  onClose: () => void;
  onMigrado: () => void;
}) {
  const [preview, setPreview] = useState<MigracaoPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(true);
  const [confirmando, setConfirmando] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelado = false;
    setLoadingPreview(true);
    previewMigrarModo(projectId, para)
      .then((p) => { if (!cancelado) setPreview(p); })
      .catch((e) => { if (!cancelado) setErr(e instanceof Error ? e.message : "Erro ao calcular preview"); })
      .finally(() => { if (!cancelado) setLoadingPreview(false); });
    return () => { cancelado = true; };
  }, [projectId, para]);

  async function handleConfirmar() {
    setConfirmando(true);
    setErr("");
    try {
      await aplicarMigrarModo(projectId, para);
      onMigrado();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao aplicar migração");
      setConfirmando(false);
    }
  }

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{
        background: "#fff", borderRadius: 16, padding: "28px 32px",
        width: "100%", maxWidth: 460, boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
      }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#0f172a", margin: "0 0 12px" }}>
          Migrar para {para === "PULL" ? "Puxada (pull)" : "Atribuição"}
        </h3>
        <p style={{ fontSize: 13, color: "#6a6a7a", margin: "0 0 16px", lineHeight: 1.5 }}>
          O modo de avaliação da Entrega também muda junto, para{" "}
          <strong>{derivarModoAvaliacaoLabel(para)}</strong>.
        </p>

        {loadingPreview ? (
          <p style={{ fontSize: 13, color: "#9696a0" }}>Calculando impacto...</p>
        ) : preview ? (
          <ul style={{ fontSize: 13, color: "#374151", lineHeight: 1.8, margin: "0 0 20px", paddingLeft: 20 }}>
            <li>{preview.entrando_na_fila} task(s) entrando na fila de puxar</li>
            <li>{preview.vira_rascunho} task(s) virando rascunho (faltam dados)</li>
            <li>{preview.mantem_responsavel} task(s) mantêm o responsável atual</li>
            <li>{preview.sem_alteracao} task(s) sem alteração</li>
          </ul>
        ) : null}

        {err && <p style={{ fontSize: 12, color: "#dc2626", marginBottom: 12 }}>{err}</p>}

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button type="button" onClick={onClose} disabled={confirmando} style={btnSecondary}>
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleConfirmar}
            disabled={loadingPreview || confirmando || !preview}
            style={{ ...btnPrimary, opacity: confirmando ? 0.6 : 1 }}
          >
            {confirmando ? "Migrando..." : "Confirmar migração"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ModosTrabalhoSection({
  projectId,
  project,
  onProjectUpdated,
}: {
  projectId: string;
  project: Project;
  onProjectUpdated: (updated: Project) => void;
}) {
  const [hidratacaoDestino, setHidratacaoDestino] = useState<boolean | null>(null);
  const [pisoDestino, setPisoDestino] = useState<string | null>(null);
  const [tetoDestino, setTetoDestino] = useState<string | null>(null);
  const [savingModos, setSavingModos] = useState(false);
  const [modosMsg, setModosMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [migrandoPara, setMigrandoPara] = useState<ModoTrabalho | null>(null);

  const [wipPorPessoaInput, setWipPorPessoaInput] = useState(String(project.wip_config?.por_pessoa ?? ""));
  const [savingWip, setSavingWip] = useState(false);
  const [wipMsg, setWipMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [historico, setHistorico] = useState<ConfiguracaoHistoricoEntry[]>([]);
  const [loadingHistorico, setLoadingHistorico] = useState(true);

  useEffect(() => {
    getModosHistorico(projectId)
      .then(setHistorico)
      .catch(() => setHistorico([]))
      .finally(() => setLoadingHistorico(false));
  }, [projectId]);

  const modoTrabalho = project.modo_trabalho;
  const modoAvaliacao = project.modo_avaliacao;
  const hidratacao = hidratacaoDestino ?? project.pull_exigir_hidratacao;
  const piso = pisoDestino ?? String(project.pull_piso_pontos);
  const teto = tetoDestino ?? String(project.pull_teto);

  const configMudou =
    hidratacao !== project.pull_exigir_hidratacao ||
    piso !== String(project.pull_piso_pontos) ||
    teto !== String(project.pull_teto);

  async function handleSalvarModos() {
    setSavingModos(true);
    setModosMsg(null);
    try {
      const updated = await updateProjectModos(projectId, {
        pull_exigir_hidratacao: hidratacao,
        pull_piso_pontos: Number(piso),
        pull_teto: Number(teto),
      });
      onProjectUpdated(updated);
      setModosMsg({ ok: true, text: "Configuração salva." });
      getModosHistorico(projectId).then(setHistorico).catch(() => {});
    } catch (err) {
      setModosMsg({ ok: false, text: err instanceof Error ? err.message : "Erro ao salvar." });
    } finally {
      setSavingModos(false);
    }
  }

  async function handleSalvarWip() {
    setSavingWip(true);
    setWipMsg(null);
    try {
      const valor = Number(wipPorPessoaInput);
      const updated = await updateWipConfig(projectId, {
        por_pessoa: Number.isFinite(valor) && valor > 0 ? valor : undefined,
      });
      onProjectUpdated(updated);
      setWipMsg({ ok: true, text: "Limite de WIP salvo." });
    } catch (err) {
      setWipMsg({ ok: false, text: err instanceof Error ? err.message : "Erro ao salvar." });
    } finally {
      setSavingWip(false);
    }
  }

  return (
    <section style={sectionStyle}>
      <h2 style={sectionTitle}>Modos de Trabalho e de Avaliação</h2>
      <p style={{ fontSize: 13, color: "#6a6a7a", marginTop: 0, marginBottom: 16, lineHeight: 1.5 }}>
        Define como as tasks chegam ao operacional (atribuição direta ou fila de puxada) e
        qual fórmula calcula a dimensão Entrega da pontuação. Trocar o modo de trabalho migra
        as tasks existentes — veja o impacto antes de confirmar.
      </p>

      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginBottom: 16 }}>
        <div>
          <label htmlFor="project-modo-trabalho" style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 4 }}>
            Modo de trabalho
          </label>
          <select
            id="project-modo-trabalho"
            value={modoTrabalho}
            onChange={(e) => setMigrandoPara(e.target.value as ModoTrabalho)}
            disabled={savingModos}
            style={{ ...inputStyle, width: 180, minHeight: 38, background: "#fff", cursor: "pointer" }}
          >
            <option value="ATRIBUICAO">Atribuição</option>
            <option value="PULL">Puxada (pull)</option>
          </select>
        </div>

        <div>
          <span style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 4 }}>
            Modo de avaliação da Entrega
          </span>
          <div style={{ ...inputStyle, width: 200, minHeight: 38, display: "flex", alignItems: "center", background: "#f7f7fa", color: "#374151" }}>
            {derivarModoAvaliacaoLabel(modoTrabalho)}
          </div>
        </div>
      </div>

      {migrandoPara && migrandoPara !== modoTrabalho && (
        <MigrarModoModal
          projectId={projectId}
          para={migrandoPara}
          onClose={() => setMigrandoPara(null)}
          onMigrado={() => {
            setMigrandoPara(null);
            const modoAvaliacaoNovo = migrandoPara === "PULL" ? "PONTOS_RELATIVO" : "PONTOS_ATRIBUIDOS";
            onProjectUpdated({ ...project, modo_trabalho: migrandoPara, modo_avaliacao: modoAvaliacaoNovo });
            getModosHistorico(projectId).then(setHistorico).catch(() => {});
          }}
        />
      )}

      {modoTrabalho === "PULL" && (
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "center", marginBottom: 16, padding: "12px 14px", background: "#f7f7fa", borderRadius: 10 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#374151" }}>
            <input
              type="checkbox"
              checked={hidratacao}
              onChange={(e) => { setHidratacaoDestino(e.target.checked); setModosMsg(null); }}
              disabled={savingModos}
            />
            Exigir hidratação para entrar na fila
          </label>
        </div>
      )}

      {modoAvaliacao === "PONTOS_RELATIVO" && (
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginBottom: 16 }}>
          <div>
            <label htmlFor="project-pull-piso" style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 4 }}>
              Piso mínimo (pontos)
            </label>
            <input
              id="project-pull-piso"
              type="number"
              min={0}
              step="0.5"
              value={piso}
              onChange={(e) => { setPisoDestino(e.target.value); setModosMsg(null); }}
              disabled={savingModos}
              style={{ ...inputStyle, width: 110 }}
            />
          </div>
          <div>
            <label htmlFor="project-pull-teto" style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 4 }}>
              Teto do bônus (múltiplo da média)
            </label>
            <input
              id="project-pull-teto"
              type="number"
              min={1}
              step="0.1"
              value={teto}
              onChange={(e) => { setTetoDestino(e.target.value); setModosMsg(null); }}
              disabled={savingModos}
              style={{ ...inputStyle, width: 110 }}
            />
          </div>
          <p style={{ fontSize: 11, color: "#94a3b8", margin: 0, maxWidth: 320, alignSelf: "center" }}>
            Padrão 1 e 1,5. Com denominador em pontos, o piso 1 tende a ficar baixo — recalibre depois da primeira sprint real.
          </p>
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button
          type="button"
          onClick={handleSalvarModos}
          disabled={savingModos || !configMudou}
          style={{ ...btnSecondary, opacity: savingModos || !configMudou ? 0.5 : 1, cursor: savingModos || !configMudou ? "not-allowed" : "pointer" }}
        >
          {savingModos ? "Salvando..." : "Salvar"}
        </button>
        {modosMsg && (
          <span style={{ fontSize: 12, color: modosMsg.ok ? "#15803d" : "#b91c1c" }}>{modosMsg.text}</span>
        )}
      </div>

      <div style={{ marginTop: 24, paddingTop: 20, borderTop: "1px solid #f0f0f4" }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", margin: "0 0 6px" }}>Limite de WIP por pessoa</h3>
        {modoTrabalho === "PULL" ? (
          <p style={{ fontSize: 12, color: "#6a6a7a", margin: 0 }}>
            Fixo em <strong>1</strong> — o modo pull opera com uma task em andamento por pessoa. O limite de WIP da coluna inteira continua editável na aba Tasks.
          </p>
        ) : (
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10 }}>
            <div>
              <label htmlFor="project-wip-por-pessoa" style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 4 }}>
                Limite de WIP por pessoa
              </label>
              <input
                id="project-wip-por-pessoa"
                type="number"
                min={1}
                value={wipPorPessoaInput}
                onChange={(e) => { setWipPorPessoaInput(e.target.value); setWipMsg(null); }}
                disabled={savingWip}
                placeholder="Sem limite"
                style={{ ...inputStyle, width: 100 }}
              />
            </div>
            <button
              type="button"
              onClick={handleSalvarWip}
              disabled={savingWip}
              style={{ ...btnSecondary, opacity: savingWip ? 0.5 : 1 }}
            >
              {savingWip ? "Salvando..." : "Salvar"}
            </button>
            {wipMsg && <span style={{ fontSize: 12, color: wipMsg.ok ? "#15803d" : "#b91c1c" }}>{wipMsg.text}</span>}
          </div>
        )}
      </div>

      <div style={{ marginTop: 24, paddingTop: 20, borderTop: "1px solid #f0f0f4" }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", margin: "0 0 10px" }}>Histórico de configuração</h3>
        {loadingHistorico ? (
          <p style={{ fontSize: 12, color: "#9696a0" }}>Carregando...</p>
        ) : historico.length === 0 ? (
          <p style={{ fontSize: 12, color: "#9696a0" }}>Nenhuma troca de modo registrada ainda.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {historico.map((h) => (
              <div key={h.id} style={{ fontSize: 12, color: "#374151" }}>
                <strong>{new Date(h.criado_em).toLocaleString("pt-BR")}</strong> — {h.usuario_email} mudou{" "}
                {h.campo === "modo_trabalho" ? "modo de trabalho" : "modo de avaliação"} de{" "}
                <em>{h.valor_anterior ?? "—"}</em> para <em>{h.valor_novo}</em>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
```

Pontos de atenção ao aplicar (não são passos separados, são parte desta substituição):
- O `<select>` de modo de trabalho não usa mais estado local "destino" com botão "Salvar" — a mudança abre direto o `MigrarModoModal` via `onChange`. Se o usuário cancelar, `migrandoPara` volta a `null` e o `<select>` re-renderiza com `value={modoTrabalho}` (o valor real do projeto, não o que foi selecionado), revertendo visualmente sem nenhuma chamada de API.
- `configMudou` substitui o antigo `modosMudou` — agora só considera os três campos que ainda passam por `handleSalvarModos` (hidratação, piso, teto), já que modo de trabalho tem seu próprio fluxo e modo de avaliação não é mais editável.
- `onMigrado` deriva `modo_avaliacao` inline (`migrandoPara === "PULL" ? "PONTOS_RELATIVO" : "PONTOS_ATRIBUIDOS"`) só para atualizar o estado local otimisticamente — mesma regra que o backend aplica em `_derivar_modo_avaliacao` (Task 1), então não há divergência possível.

- [ ] **Step 2: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: sem erros novos no arquivo. Se aparecer erro de tipo em `onProjectUpdated({ ...project, modo_trabalho: migrandoPara, ... })` por causa do tipo de `Project.modo_trabalho`/`modo_avaliacao`, confirme que os literais usados (`"ATRIBUICAO"`, `"PULL"`, `"PONTOS_RELATIVO"`, `"PONTOS_ATRIBUIDOS"`) batem exatamente com a definição em `api.ts:172-173`.

- [ ] **Step 3: Verificação manual no navegador**

Suba o backend (`cd docudata-backend && uvicorn main:app --reload`) e o frontend (`cd docudata-frontend && npm run dev`), abra um projeto de teste em modo ATRIBUICAO com pelo menos uma task em "planejado" com responsável atribuído, vá em Configurações:
1. Confirme que o dropdown "Modo de avaliação da Entrega" sumiu e virou texto "Pontos atribuídos".
2. Troque "Modo de trabalho" para "Puxada (pull)" — confirme que o modal abre, mostra a contagem calculada (compare manualmente com as tasks do projeto de teste), e que "Cancelar" fecha sem mudar nada (recarregue a página pra confirmar que `modo_trabalho` continua `ATRIBUICAO` no banco).
3. Repita e confirme desta vez — confirme que a task que tinha responsável em "planejado" perdeu o `operacional_id` (vira fila) e que a tela agora mostra "Pontos relativo ao squad".
4. Confirme que o histórico de configuração ganhou uma entrada nova.

Reporte o resultado dessa verificação manual explicitamente antes de prosseguir — não é opcional dado o histórico de "completo" com lacunas na Entrega 3.

- [ ] **Step 4: Commit**

```bash
cd docudata-frontend && git add "app/[subarea]/projects/[id]/page.tsx"
git commit -m "feat(config): conecta botão de migração de modo à UI, remove escolha livre de modo_avaliacao"
```

---

### Task 9: `TaskModal` esconde atribuição manual de responsável em projeto PULL

**Files:**
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx:105-121` (`TaskModalProps`, `TaskModal`)
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx:305-313` (campo "Operacional" dentro do form)
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx:1303-1335` (as duas invocações de `<TaskModal>`)

**Interfaces:**
- Consumes: nenhuma das tasks anteriores desta onda (arquivo independente de `page.tsx`).
- Produces: nada consumido por outra task deste plano — é a última peça.

- [ ] **Step 1: Adicionar `modoTrabalho` à interface e à assinatura de `TaskModal`**

Em `docudata-frontend/app/components/TasksKanbanTab.tsx`, linha 105-121, troque:

```typescript
interface TaskModalProps {
  mode: "create" | "edit";
  task?: TaskKanbanResponse;
  projectId: string;
  sprints: SprintWithStatus[];
  operacionais: OperacionalResponse[];
  funcionalidades: FuncionalidadeResponse[];
  defaultSprintId?: string;
  onClose: () => void;
  onSaved: (t: TaskKanbanResponse) => void;
  onDeleted?: (id: string) => void;
}

function TaskModal({
  mode, task, projectId, sprints, operacionais, funcionalidades,
  defaultSprintId, onClose, onSaved, onDeleted,
}: TaskModalProps) {
```

por:

```typescript
interface TaskModalProps {
  mode: "create" | "edit";
  task?: TaskKanbanResponse;
  projectId: string;
  sprints: SprintWithStatus[];
  operacionais: OperacionalResponse[];
  funcionalidades: FuncionalidadeResponse[];
  defaultSprintId?: string;
  modoTrabalho: "ATRIBUICAO" | "PULL";
  onClose: () => void;
  onSaved: (t: TaskKanbanResponse) => void;
  onDeleted?: (id: string) => void;
}

function TaskModal({
  mode, task, projectId, sprints, operacionais, funcionalidades,
  defaultSprintId, modoTrabalho, onClose, onSaved, onDeleted,
}: TaskModalProps) {
```

- [ ] **Step 2: Esconder o select "Operacional" quando `modoTrabalho === "PULL"`**

Na mesma função, linha 305-313, troque:

```typescript
          <div>
            <label style={labelSt}>Operacional</label>
            <select value={operacionalId} onChange={(e) => setOperacionalId(e.target.value)} style={inputSt}>
              <option value="">Sem operacional</option>
              {operacionais.filter((o) => o.ativo).map((o) => (
                <option key={o.id} value={o.id}>{o.nome}{o.papel ? ` — ${o.papel}` : ""}</option>
              ))}
            </select>
          </div>
```

por:

```typescript
          {modoTrabalho === "PULL" ? (
            <div>
              <label style={labelSt}>Operacional</label>
              <p style={{ fontSize: 12, color: "#6a6a7a", margin: "4px 0 0", padding: "8px 10px", background: "#f7f7fa", borderRadius: 8 }}>
                {mode === "create" || !task?.operacional_id
                  ? "Atribuição via fila de puxar — não é definida manualmente em modo Pull."
                  : `Responsável atual: ${operacionais.find((o) => o.id === task.operacional_id)?.nome ?? "—"} (somente leitura em modo Pull).`}
              </p>
            </div>
          ) : (
            <div>
              <label style={labelSt}>Operacional</label>
              <select value={operacionalId} onChange={(e) => setOperacionalId(e.target.value)} style={inputSt}>
                <option value="">Sem operacional</option>
                {operacionais.filter((o) => o.ativo).map((o) => (
                  <option key={o.id} value={o.id}>{o.nome}{o.papel ? ` — ${o.papel}` : ""}</option>
                ))}
              </select>
            </div>
          )}
```

Note que `operacionalId` (o estado local, linha 126) continua existindo e é lido em `handleSubmit` (linhas 177 e 188) — em modo PULL ele nunca é alterado pelo usuário (não há select pra isso), então mantém o valor inicial (`task?.operacional_id ?? ""`), preservando o responsável já existente numa task que veio de antes da trava (ex: bloqueada ou em andamento) em vez de apagá-lo silenciosamente. Isso é consistente com a Task 5 do backend: `patch_task` só rejeita quando `operacional_id` vier **diferente** do que já está — como o modal nem manda um valor novo em PULL, o PATCH nunca inclui uma mudança nesse campo.

- [ ] **Step 3: Passar `modoTrabalho` nas duas invocações de `<TaskModal>`**

Linha 1303-1313, troque:

```typescript
      {createModal !== null && (
        <TaskModal
          mode="create"
          projectId={projectId}
          sprints={sprints}
          operacionais={operacionais}
          funcionalidades={funcionalidades}
          defaultSprintId={createModal.defaultSprintId}
          onClose={() => setCreateModal(null)}
          onSaved={(t) => { upsertTask(t); setCreateModal(null); }}
        />
      )}
```

por:

```typescript
      {createModal !== null && (
        <TaskModal
          mode="create"
          projectId={projectId}
          sprints={sprints}
          operacionais={operacionais}
          funcionalidades={funcionalidades}
          defaultSprintId={createModal.defaultSprintId}
          modoTrabalho={modoTrabalho}
          onClose={() => setCreateModal(null)}
          onSaved={(t) => { upsertTask(t); setCreateModal(null); }}
        />
      )}
```

E na invocação de edição, logo abaixo (linha 1327-1335 aproximadamente), adicione `modoTrabalho={modoTrabalho}` junto às outras props de `<TaskModal mode="edit" ...>` do mesmo jeito.

`modoTrabalho` já é uma prop de `TasksKanbanTab` (linha 851: `export default function TasksKanbanTab({ projectId, sprints, operacionais, funcionalidades, modoTrabalho }: Props)`), então já está disponível no escopo — não precisa buscar de lugar nenhum novo.

- [ ] **Step 4: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: sem erros novos. Se `modoTrabalho` aparecer como obrigatório faltando em alguma outra invocação de `TaskModal` que não foi coberta (busque `<TaskModal` no arquivo pra confirmar que são exatamente essas duas), adicione lá também.

- [ ] **Step 5: Verificação manual no navegador**

Com backend e frontend rodando (Task 8, Step 3):
1. Num projeto em modo PULL, abra "Nova task" — confirme que o texto "Atribuição via fila de puxar..." aparece no lugar do select.
2. Edite uma task já existente que tenha responsável (ex: uma bloqueada ou em andamento) — confirme que aparece "Responsável atual: <nome> (somente leitura em modo Pull)" e que salvar a task (mudando outro campo, ex: pontos) não apaga o responsável.
3. Num projeto em modo ATRIBUICAO, confirme que o select "Operacional" continua aparecendo normalmente, criar e editar task com responsável continua funcionando.

- [ ] **Step 6: Commit**

```bash
cd docudata-frontend && git add app/components/TasksKanbanTab.tsx
git commit -m "feat(tasks): esconde atribuição manual de responsável no modal de task em projeto PULL"
```

---

### Task 10: Verificação final da Onda 2 e da entrega completa

**Files:** nenhum arquivo novo — só verificação.

**Interfaces:** N/A.

- [ ] **Step 1: Typecheck completo do frontend**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: sem erros.

- [ ] **Step 2: Suíte completa do backend, de novo**

Run: `cd docudata-backend && python -m pytest -v`
Expected: PASS — confirma que nenhum ajuste feito durante a Onda 2 (não deveria haver nenhum, já que Onda 2 é só frontend) quebrou nada.

- [ ] **Step 3: Checklist de verificação end-to-end (repetir o roteiro manual, agora de ponta a ponta)**

Usando um projeto de teste real (não apenas os passos isolados das Tasks 8 e 9):
1. Projeto em ATRIBUICAO com uma task em "planejado" com responsável atribuído.
2. Migrar pra PULL pela UI nova (preview → confirmar).
3. Confirmar que a task perdeu o responsável e entrou na fila (não mais "atribuída do jeito antigo" — o bug original que motivou esta entrega).
4. Confirmar que "Modo de avaliação da Entrega" mostra "Pontos relativo ao squad" sem intervenção manual.
5. Tentar criar uma task nova nesse projeto (agora em PULL) tentando forçar um responsável via DevTools/API direta (`POST /tasks` com `operacional_id`) — confirmar 422.
6. Editar uma task existente tentando mudar o responsável via `PATCH /tasks/{id}` direto — confirmar 422.
7. Confirmar que `/puxar` e `/devolver` continuam funcionando normalmente nesse mesmo projeto (um operacional puxa uma task da fila, depois devolve).
8. Migrar de volta pra ATRIBUICAO — confirmar que "Modo de avaliação" volta pra "Pontos atribuídos" e que o select "Operacional" volta a aparecer no modal de task.

- [ ] **Step 4: Relatar ao usuário**

Resuma o que foi verificado (testes automatizados + checklist manual), aponte explicitamente que dados de projetos que já sofreram o bug antes desta entrega não foram tocados retroativamente (comportamento intencional, confirmado no brainstorm), e pergunte se quer que algum projeto real específico seja migrado agora usando a UI nova.

---

## Self-Review (preenchido durante a escrita do plano)

**Cobertura das 3 lacunas do design aprovado:**
1. `modo_avaliacao` derivado — Tasks 1, 3 (backend) e 8 (frontend). ✓
2. `PATCH /modos` não migra tasks / botão de migração ausente — Tasks 2 (backend) e 7, 8 (frontend). ✓
3. Trava de atribuição manual em PULL — Tasks 4, 5 (backend) e 9 (frontend). ✓
4. Testes de backend nunca pulados — Tasks 1, 2, 3, 4, 5 todas incluem teste antes da implementação; Task 6 roda a suíte completa. ✓
5. Regra de que dados antigos não são tocados retroativamente — documentada em Global Constraints e reforçada no Step 4 da Task 10. ✓
6. `/puxar`/`/devolver` não regridem — checado explicitamente no Step 5 da Task 5 e no Step 3 da Task 10. ✓

**Consistência de tipos:** `MigracaoPreview` definido uma vez em `api.ts` (Task 7) e reusado sem redefinição em `page.tsx` (Task 8, via import). Mensagem de erro `"Em modo Pull, tasks não podem ter responsável definido manualmente. Use a fila de puxar."` idêntica nas Tasks 4 e 5 (checada por substring `"Pull"` nos testes, não pela frase inteira, pra não engessar redação futura).

**Placeholders:** nenhum "TBD"/"adicionar validação apropriada" — todo código é literal, pronto pra colar.
