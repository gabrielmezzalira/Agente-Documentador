# Modos de Trabalho e de Avaliação — Entrega 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elegibilidade temporal por operacional (entrada/saída no projeto) que corrige o bug de PULL onde quem não puxava nenhuma task nunca era avaliado, e métricas comparativas entre modo A (ATRIBUICAO/PONTOS_ATRIBUIDOS) e modo B (PULL/PONTOS_RELATIVO), dentro de um projeto e entre projetos.

**Architecture:** Duas colunas novas em `operacionais` (`data_entrada`/`data_saida`) substituem "tem task na sprint" como definição de elegível em toda a cadeia de Avaliação Semanal (pendências, contador N/M, motor de score). O motor de score (`calcular_e_travar_pontuacao`) passa a criar uma linha zerada para todo elegível sem task, não só para quem tem contribuição — sem isso a mudança de filtro em `_sequencia_pessoal` não teria efeito. Comparação de modos é uma agregação nova e isolada, lida direto dos campos já congelados no fechamento (`sprints.modo_trabalho`/`modo_avaliacao`, `pontuacao_operacional_sprint.entrega_modo`) — nenhuma mudança no motor de score em si.

**Tech Stack:** FastAPI + Supabase (supabase-py v2, mock leve nos testes — sem `.or_()`/`.lte()`, que não têm precedente nesta base), Next.js 15 / React 19 (inline styles, `recharts`).

**Spec:** `docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md`

## Global Constraints

- Golden regression (`tests/test_pontuacao_fechamento.py::test_golden_fixture_multidimensional_trava_de_regressao`) continua verde, assertions inalteradas.
- SQL sempre idempotente (`IF NOT EXISTS`), anexado ao final de `docudata-backend/supabase_schema.sql`, nunca migração automática.
- Identificadores/docstrings em português no backend; frontend sem Tailwind/design-system formal, sub-componentes sempre inline no arquivo que usa.
- Nenhuma dependência nova. Comparações de timestamp usam string ISO simples (`datetime.now(timezone.utc).isoformat()` + comparação `>`/`<=`), o mesmo padrão já usado pelo `cutoff` em `services/pontuacao.py` — não introduzir `.or_()`/`.lte()`/`.gte()` do supabase-py, sem precedente nesta base.
- RBAC: `GET /avaliacoes/{sprint_id}/elegiveis` usa `require_not_operacional` (Gerente+), mesmo nível de `routers/operacionais.py`. Endpoints de `routers/metricas.py` não têm gate de auth hoje (nenhum endpoint irmão tem) — os novos seguem o mesmo padrão do arquivo, sem introduzir inconsistência.
- Todo teste de `calcular_e_travar_pontuacao` usa o `_mock_client` já existente em `tests/test_pontuacao_fechamento.py` — extenda-o, não recrie.

---

## Onda 1 — Back-end

### Task 1: Schema — `data_entrada`/`data_saida` em `operacionais`

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (append at end of file)
- Test: `docudata-backend/tests/test_elegibilidade_schema.py`

**Interfaces:**
- Produces: colunas `operacionais.data_entrada`, `operacionais.data_saida`. Todas as tasks seguintes dependem delas existirem no schema file (testes usam mock, não banco real).

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_elegibilidade_schema.py
"""Confirma que a migração de elegibilidade temporal da Entrega 2 está
presente no schema. Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.2."""
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def test_operacionais_ganha_colunas_de_vinculo_temporal():
    schema = _SCHEMA.read_text()
    assert "ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS data_entrada timestamptz NOT NULL DEFAULT now();" in schema
    assert "ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS data_saida timestamptz;" in schema
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_elegibilidade_schema.py -v`
Expected: FAIL — colunas ainda não existem no schema.

- [ ] **Step 3: Append the migration**

Ao final de `docudata-backend/supabase_schema.sql` (depois do bloco "Modos de Trabalho e de Avaliação — Entrega 1: Base" e ANTES de qualquer seção comentada tipo "-- Migration v5", seguindo o mesmo cuidado de posicionamento que a Entrega 1 já aprendeu — ver ledger da Entrega 1, Task 1 foi reaberta por isso):

```sql
-- ═══════════════════════════════════════════════════════════════
-- Modos de Trabalho e de Avaliação — Entrega 2: Elegibilidade
-- temporal e métricas comparativas (spec
-- docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md)
-- Colunas simples (sem tabela de histórico) — 1 vínculo mais recente por
-- pessoa, sem suporte a múltiplos ciclos de entrada/saída no mesmo projeto.
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS data_entrada timestamptz NOT NULL DEFAULT now();
ALTER TABLE operacionais ADD COLUMN IF NOT EXISTS data_saida timestamptz;

-- Backfill: quem já existia recebe a mesma data de criação como entrada.
UPDATE operacionais SET data_entrada = created_at WHERE data_entrada IS NULL;
```

**IMPORTANTE:** antes de escrever este bloco, rode `grep -n "Migration v5" docudata-backend/supabase_schema.sql` e confirme se ainda existe uma seção comentada com esse marcador mais abaixo no arquivo. Se existir, o bloco acima deve ir ANTES dela (mesma regra que a Task 1 da Entrega 1 corrigiu depois de quebrar `test_migration_v5_e_somente_aditiva_e_comentada`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && pytest tests/test_elegibilidade_schema.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite once to confirm no regression (Migration v5 invariant especialmente)**

Run: `cd docudata-backend && pytest -q`
Expected: mesmas falhas pré-existentes de antes desta task (ver Entrega 1: 1 falha em `test_security.py`, não relacionada), nenhuma nova.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/supabase_schema.sql docudata-backend/tests/test_elegibilidade_schema.py
git commit -m "$(cat <<'EOF'
feat(schema): adiciona data_entrada/data_saida em operacionais (Entrega 2)

Colunas simples (sem tabela de histórico) para vínculo temporal com o
projeto — base para a elegibilidade redefinida da Entrega 2.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Schemas Pydantic

**Files:**
- Modify: `docudata-backend/models/schemas.py`

**Interfaces:**
- Consumes: nada.
- Produces: `OperacionalResponse` com `data_entrada`/`data_saida`; `ElegivelResponse` novo. Task 3 depende do primeiro; Task 8 depende do segundo.

- [ ] **Step 1: Estender `OperacionalResponse`**

Em `docudata-backend/models/schemas.py`, encontre:

```python
class OperacionalResponse(BaseModel):
    id: str
    project_id: str
    nome: str
    email: Optional[str] = None
    papel: Optional[str] = None
    ativo: bool
    github_login: Optional[str] = None
    github_email: Optional[str] = None
    created_at: datetime
```

Substitua por:

```python
class OperacionalResponse(BaseModel):
    id: str
    project_id: str
    nome: str
    email: Optional[str] = None
    papel: Optional[str] = None
    ativo: bool
    github_login: Optional[str] = None
    github_email: Optional[str] = None
    created_at: datetime
    data_entrada: datetime
    data_saida: Optional[datetime] = None
```

- [ ] **Step 2: Adicionar `ElegivelResponse`**

No mesmo arquivo, logo depois da classe `PendenciaAvaliacaoResponse` (linha ~686), adicione:

```python
class ElegivelResponse(BaseModel):
    """RF-C7 (Entrega 2): todo operacional vinculado ao projeto no momento da
    consulta, com contagem de tasks na sprint (0 é válido) e se já tem
    avaliação registrada — auditoria de quem entra no denominador da
    Avaliação Semanal."""
    operacional_id: str
    nome: str
    tasks_na_sprint: int
    avaliado: bool
```

- [ ] **Step 3: Confirmar que o módulo importa sem erro**

Run: `cd docudata-backend && python -c "import models.schemas"`
Expected: sem erro.

- [ ] **Step 4: Commit**

```bash
git add docudata-backend/models/schemas.py
git commit -m "$(cat <<'EOF'
feat(schemas): OperacionalResponse ganha data_entrada/data_saida; ElegivelResponse novo

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `routers/operacionais.py` — grava/limpa `data_saida` ao (des)ativar

**Files:**
- Modify: `docudata-backend/routers/operacionais.py`
- Test: `docudata-backend/tests/test_operacionais_vinculo_temporal.py`

**Interfaces:**
- Consumes: `OperacionalResponse` estendido (Task 2).
- Produces: nada consumido por tasks seguintes — comportamento isolado nos dois endpoints que já tocam `ativo`.

- [ ] **Step 1: Write the failing tests**

```python
# docudata-backend/tests/test_operacionais_vinculo_temporal.py
"""Testes para routers/operacionais.py — grava/limpa data_saida quando ativo
muda (Entrega 2). Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.3."""
from unittest.mock import MagicMock

from routers.operacionais import update_operacional, remover_do_projeto
from models.schemas import OperacionalUpdate


def _mock_client_update(existing_row, update_capture):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [existing_row]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                update_capture.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(existing_row, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "tasks":
            q = MagicMock()
            q.update = MagicMock(return_value=q)
            q.eq = MagicMock(return_value=q)
            q.neq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = []
            q.execute = MagicMock(return_value=resp)
            tbl.update = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


async def test_desativar_via_patch_grava_data_saida():
    capture = []
    client = _mock_client_update({"id": "op-1", "ativo": True}, capture)
    import routers.operacionais as mod
    mod.get_client = lambda: client

    await update_operacional("op-1", OperacionalUpdate(ativo=False))

    assert capture[0]["ativo"] is False
    assert capture[0]["data_saida"] is not None


async def test_reativar_via_patch_limpa_data_saida():
    capture = []
    client = _mock_client_update({"id": "op-1", "ativo": False, "data_saida": "2026-01-01T00:00:00+00:00"}, capture)
    import routers.operacionais as mod
    mod.get_client = lambda: client

    await update_operacional("op-1", OperacionalUpdate(ativo=True))

    assert capture[0]["ativo"] is True
    assert capture[0]["data_saida"] is None


async def test_remover_do_projeto_grava_data_saida():
    capture = []
    client = _mock_client_update({"id": "op-1", "ativo": True}, capture)
    import routers.operacionais as mod
    mod.get_client = lambda: client

    await remover_do_projeto("op-1")

    assert capture[0]["ativo"] is False
    assert capture[0]["data_saida"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_operacionais_vinculo_temporal.py -v`
Expected: FAIL — `data_saida` não é gravado ainda (KeyError ou assert `is not None` falhando em `None`).

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/operacionais.py`, adicione o import de `datetime`/`timezone` no topo do arquivo:

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
```

Encontre em `update_operacional`:

```python
    updates: dict = {}
    for field in ("nome", "email", "papel", "ativo", "github_login", "github_email"):
        val = getattr(data, field, None)
        if val is not None:
            updates[field] = val

    if not updates:
```

Substitua por:

```python
    updates: dict = {}
    for field in ("nome", "email", "papel", "ativo", "github_login", "github_email"):
        val = getattr(data, field, None)
        if val is not None:
            updates[field] = val

    # Entrega 2: alternar ativo grava/limpa data_saida — colunas simples,
    # sem histórico de múltiplos ciclos (decisão de design registrada no spec).
    if "ativo" in updates:
        updates["data_saida"] = None if updates["ativo"] else datetime.now(timezone.utc).isoformat()

    if not updates:
```

Encontre em `remover_do_projeto`:

```python
    resp = client.table("operacionais").update({"ativo": False}).eq("id", operacional_id).execute()
    return resp.data[0]
```

Substitua por:

```python
    resp = client.table("operacionais").update({
        "ativo": False,
        "data_saida": datetime.now(timezone.utc).isoformat(),
    }).eq("id", operacional_id).execute()
    return resp.data[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && pytest tests/test_operacionais_vinculo_temporal.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Run full suite**

Run: `cd docudata-backend && pytest -q`
Expected: mesmas falhas pré-existentes, nenhuma nova.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/routers/operacionais.py docudata-backend/tests/test_operacionais_vinculo_temporal.py
git commit -m "$(cat <<'EOF'
feat(operacionais): grava/limpa data_saida ao (des)ativar (Entrega 2)

update_operacional (PATCH ativo) e remover_do_projeto agora gravam
data_saida = now() ao desativar, e limpam ao reativar.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `services/elegibilidade.py` — helper de vínculo temporal

**Files:**
- Create: `docudata-backend/services/elegibilidade.py`
- Test: `docudata-backend/tests/test_elegibilidade.py`

**Interfaces:**
- Consumes: colunas `operacionais.data_entrada`/`data_saida` (Task 1).
- Produces: `listar_vinculados_no_projeto(client, project_id: str, momento_iso: str) -> list[dict]` (retorna dicts com `id, nome, email, project_id, data_entrada, data_saida`). Tasks 5, 6 e 8 consomem esta função.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_elegibilidade.py
"""Testes para services/elegibilidade.py::listar_vinculados_no_projeto.
Ver docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.3."""
from unittest.mock import MagicMock

from services.elegibilidade import listar_vinculados_no_projeto


def _mock_client(operacionais):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_inclui_quem_entrou_antes_e_ainda_nao_saiu():
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert [r["id"] for r in result] == ["op-1"]


def test_exclui_quem_entrou_depois_do_momento():
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-06-15T00:00:00+00:00", "data_saida": None}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert result == []


def test_exclui_quem_ja_saiu_antes_do_momento():
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": "2026-05-01T00:00:00+00:00"}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert result == []


def test_inclui_quem_saiu_depois_do_momento():
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": "2026-07-01T00:00:00+00:00"}
    client = _mock_client([op])
    result = listar_vinculados_no_projeto(client, "p1", "2026-06-01T00:00:00+00:00")
    assert [r["id"] for r in result] == ["op-1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_elegibilidade.py -v`
Expected: FAIL — `services.elegibilidade` ainda não existe (`ModuleNotFoundError`).

- [ ] **Step 3: Implementar**

```python
# docudata-backend/services/elegibilidade.py
"""Elegibilidade temporal por vínculo com o projeto (Entrega 2) — substitui
"tem task na sprint" como definição de elegível em toda a cadeia de
Avaliação Semanal. Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.

Comparação de timestamp é string simples (ISO 8601, mesmo formato que
datetime.now(timezone.utc).isoformat() já usa em services/pontuacao.py para
o cutoff) — sem .or_()/.lte() do supabase-py, sem precedente nesta base."""


def listar_vinculados_no_projeto(client, project_id: str, momento_iso: str) -> list[dict]:
    """Operacionais vinculados ao projeto no momento informado: data_entrada
    já passou e data_saida é nula ou posterior ao momento. Filtra em Python
    (não via query composta) — mesmo padrão já usado em services/performance.py
    para agregações que não cabem numa única query simples."""
    todos = (
        client.table("operacionais")
        .select("id, nome, email, project_id, data_entrada, data_saida")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    vinculados = []
    for op in todos:
        entrada = op.get("data_entrada")
        saida = op.get("data_saida")
        if entrada and entrada > momento_iso:
            continue
        if saida and saida <= momento_iso:
            continue
        vinculados.append(op)
    return vinculados
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && pytest tests/test_elegibilidade.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/elegibilidade.py docudata-backend/tests/test_elegibilidade.py
git commit -m "$(cat <<'EOF'
feat(elegibilidade): listar_vinculados_no_projeto (Entrega 2)

Helper novo: elegibilidade por vínculo temporal (data_entrada/data_saida),
substitui "tem task na sprint" nas próximas tasks.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Redefinir elegibilidade em `routers/avaliacoes.py` e `services/avaliacoes.py`

**Files:**
- Modify: `docudata-backend/routers/avaliacoes.py`
- Modify: `docudata-backend/services/avaliacoes.py`
- Modify: `docudata-backend/routers/sprints.py:18,124` (assinatura de `contar_avaliacao_por_sprint` ganha `project_id`)
- Test: `docudata-backend/tests/test_elegibilidade_avaliacoes.py`
- Test: `docudata-backend/tests/test_avaliacao_contagem_sprint.py` (existente — precisa de ajuste de assinatura, não de comportamento novo além do já coberto por Task 4)

**Interfaces:**
- Consumes: `listar_vinculados_no_projeto` (Task 4).
- Produces: `_operacionais_elegiveis(client, sprint_id)` em `routers/avaliacoes.py` (substitui `_operacionais_com_task_na_sprint`); `contar_avaliacao_por_sprint(client, project_id, sprint_ids)` (assinatura mudou — Task 6 do plano da Entrega 1 não existe, mas o router `sprints.py` que chama esta função precisa do novo argumento).

- [ ] **Step 1: Write the failing tests**

```python
# docudata-backend/tests/test_elegibilidade_avaliacoes.py
"""Testes para a redefinição de "elegível" em routers/avaliacoes.py e
services/avaliacoes.py (Entrega 2) — vinculado ao projeto, não mais "tem
task na sprint". Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
from unittest.mock import MagicMock

from routers.avaliacoes import _operacionais_elegiveis
from services.avaliacoes import contar_avaliacao_por_sprint


def _mock_client_router(sprint, operacionais):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [sprint] if sprint else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = operacionais
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_operacionais_elegiveis_inclui_vinculado_sem_task():
    """O ponto central da correção do bug de PULL: alguém vinculado, mas SEM
    nenhuma task na sprint, precisa aparecer como elegível."""
    sprint = {"project_id": "p1"}
    op_sem_task = {
        "id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
        "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None,
    }
    client = _mock_client_router(sprint, [op_sem_task])

    result = _operacionais_elegiveis(client, "sprint-1")

    assert [r["id"] for r in result] == ["op-1"]


def test_operacionais_elegiveis_sprint_inexistente_retorna_vazio():
    client = _mock_client_router(None, [])
    assert _operacionais_elegiveis(client, "sprint-x") == []


def _mock_client_service(operacionais, tasks, avaliacoes):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = operacionais
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "avaliacoes_gerente":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = avaliacoes
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_contar_avaliacao_por_sprint_conta_vinculado_sem_task_como_elegivel():
    op_sem_task = {
        "id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
        "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None,
    }
    client = _mock_client_service([op_sem_task], tasks=[], avaliacoes=[])

    resultado = contar_avaliacao_por_sprint(client, "p1", ["sprint-1"])

    assert resultado["sprint-1"]["elegiveis"] == 1
    assert resultado["sprint-1"]["avaliados"] == 0


def test_contar_avaliacao_por_sprint_lista_vazia_retorna_vazio():
    client = _mock_client_service([], tasks=[], avaliacoes=[])
    assert contar_avaliacao_por_sprint(client, "p1", []) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_elegibilidade_avaliacoes.py -v`
Expected: FAIL — `_operacionais_elegiveis` não existe ainda; `contar_avaliacao_por_sprint` ainda não aceita `project_id` posicional do jeito que o teste chama, e ainda conta por task.

- [ ] **Step 3: Implementar em `routers/avaliacoes.py`**

Encontre:

```python
def _operacionais_com_task_na_sprint(client, sprint_id: str) -> list[dict]:
    task_rows = (
        client.table("tasks").select("operacional_id").eq("sprint_id", sprint_id).execute().data or []
    )
    operacional_ids = {t["operacional_id"] for t in task_rows if t.get("operacional_id")}
    if not operacional_ids:
        return []
    return (
        client.table("operacionais")
        .select("id, nome, email, project_id")
        .in_("id", list(operacional_ids))
        .execute()
        .data or []
    )
```

Substitua por:

```python
def _operacionais_elegiveis(client, sprint_id: str) -> list[dict]:
    """Elegível = vinculado ao projeto (Entrega 2), não mais "tem task na
    sprint" — corrige o bug de PULL onde quem não puxava nada nunca aparecia
    como pendente nem era avaliado. Ver
    docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
    sprint_resp = client.table("sprints").select("project_id").eq("id", sprint_id).execute()
    if not sprint_resp.data:
        return []
    project_id = sprint_resp.data[0]["project_id"]
    momento = datetime.now(timezone.utc).isoformat()
    return listar_vinculados_no_projeto(client, project_id, momento)
```

Adicione o import no topo do arquivo (junto aos existentes de `services`):

```python
from services.avaliacoes import None  # NÃO adicionar esta linha — ver abaixo
```

(Ignore a linha acima — é só para deixar claro que NÃO existe import cruzado aqui. O import correto é:)

```python
from services.elegibilidade import listar_vinculados_no_projeto
```

Adicione essa linha junto aos outros imports de `services` no topo de `routers/avaliacoes.py` (depois de `from services.auth import get_current_pessoa, require_role`).

Atualize a única chamada existente, em `listar_pendencias`:

```python
    operacionais = _operacionais_com_task_na_sprint(client, sprint_id)
```

vira:

```python
    operacionais = _operacionais_elegiveis(client, sprint_id)
```

- [ ] **Step 4: Implementar em `services/avaliacoes.py`**

Substitua o arquivo inteiro:

```python
# docudata-backend/services/avaliacoes.py
"""Contagem de elegibilidade e avaliação semanal por sprint (Entrega 1 —
extra do usuário: contador "N/M" no card da sprint).

Entrega 2: elegibilidade passa a ser vínculo temporal com o projeto
(services.elegibilidade.listar_vinculados_no_projeto), não mais "tem task na
sprint" — corrige o bug de PULL onde quem não puxava nada nunca contava.
Ver docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4.

Nuance aceita: este contador usa "vinculado agora" (momento da consulta),
não o momento exato do fechamento de cada sprint individualmente — é um
contador de exibição (chip N/M), não a fonte de verdade. A fonte de
verdade real (o que efetivamente vira linha em pontuacao_operacional_sprint)
usa o momento exato do fechamento, em services/pontuacao.py."""
from datetime import datetime, timezone

from services.elegibilidade import listar_vinculados_no_projeto


def contar_avaliacao_por_sprint(client, project_id: str, sprint_ids: list[str]) -> dict[str, dict]:
    """Para cada sprint_id, quantos operacionais estão vinculados ao projeto
    (elegíveis) e quantos desses já têm avaliacoes_gerente registrada
    (avaliados). Uma consulta batelada — evita N chamadas quando o chamador
    lista várias sprints de uma vez (GET /projects/{id}/sprints)."""
    if not sprint_ids:
        return {}

    momento = datetime.now(timezone.utc).isoformat()
    vinculados = listar_vinculados_no_projeto(client, project_id, momento)
    elegiveis_ids = {op["id"] for op in vinculados}

    aval_resp = (
        client.table("avaliacoes_gerente").select("sprint_id, operacional_id").in_("sprint_id", sprint_ids).execute()
    )
    avaliados_por_sprint: dict[str, set[str]] = {sid: set() for sid in sprint_ids}
    for row in (aval_resp.data or []):
        sid = row.get("sprint_id")
        op = row.get("operacional_id")
        if sid in avaliados_por_sprint and op:
            avaliados_por_sprint[sid].add(op)

    return {
        sid: {
            "elegiveis": len(elegiveis_ids),
            # Só conta quem ainda é elegível — evita avaliados > elegiveis se
            # um dado antigo ficou órfão (avaliação de alguém que saiu do
            # projeto depois de ter sido avaliado).
            "avaliados": len(avaliados_por_sprint[sid] & elegiveis_ids),
        }
        for sid in sprint_ids
    }
```

- [ ] **Step 5: Atualizar o chamador em `routers/sprints.py`**

Em `docudata-backend/routers/sprints.py`, encontre:

```python
    contagem_avaliacao = contar_avaliacao_por_sprint(client, [s["id"] for s in sprints])
```

Substitua por:

```python
    contagem_avaliacao = contar_avaliacao_por_sprint(client, project_id, [s["id"] for s in sprints])
```

(`project_id` já está em escopo nessa função — é o parâmetro da rota `GET /projects/{project_id}/sprints`.)

- [ ] **Step 6: Atualizar o teste existente `test_avaliacao_contagem_sprint.py`**

Leia `docudata-backend/tests/test_avaliacao_contagem_sprint.py` inteiro primeiro. Ele hoje monta um mock só com `tasks`/`avaliacoes_gerente` (sem `operacionais`) e chama `contar_avaliacao_por_sprint(client, ["sprint-1", "sprint-2"])` (2 argumentos). Ajuste:
- Toda chamada da função ganha `project_id` como segundo argumento posicional (use `"p1"` como valor, ou o que já fizer sentido no teste).
- O mock precisa de um branch `"operacionais"` retornando os operacionais que antes apareciam via `tasks` (mesmos `id`s, com `data_entrada` no passado e `data_saida` nulo, pra não afetar o resultado esperado).
- As asserções de contagem (`elegiveis`/`avaliados`) devem continuar batendo com os mesmos números do teste original — se um teste specifico dependia de "task sem operacional_id não conta" ou similar, adapte a fixture de `operacionais` pra refletir só quem estava vinculado, não quem tinha task.

Este é trabalho de adaptação de teste existente, não teste novo — não pule, mas não crie asserções novas além de manter o comportamento equivalente pro caso ATRIBUICAO padrão (todo mundo com task também está vinculado).

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd docudata-backend && pytest tests/test_elegibilidade_avaliacoes.py tests/test_avaliacao_contagem_sprint.py -v`
Expected: PASS em tudo.

- [ ] **Step 8: Run full suite**

Run: `cd docudata-backend && pytest -q`
Expected: mesmas falhas pré-existentes, nenhuma nova. Preste atenção especial em qualquer teste de `routers/sprints.py` que chame `GET /projects/{id}/sprints` via mock — a assinatura nova de `contar_avaliacao_por_sprint` pode quebrar outros testes que não estão listados aqui; se algum quebrar, ajuste o mock dele do mesmo jeito do Step 6.

- [ ] **Step 9: Commit**

```bash
git add docudata-backend/routers/avaliacoes.py docudata-backend/services/avaliacoes.py docudata-backend/routers/sprints.py docudata-backend/tests/test_elegibilidade_avaliacoes.py docudata-backend/tests/test_avaliacao_contagem_sprint.py
git commit -m "$(cat <<'EOF'
feat(avaliacoes): elegibilidade = vinculado ao projeto, não mais "tem task" (Entrega 2)

routers/avaliacoes.py::_operacionais_elegiveis e
services/avaliacoes.py::contar_avaliacao_por_sprint agora usam
services.elegibilidade — corrige o bug de PULL onde quem não puxava
nenhuma task nunca aparecia como pendente nem era avaliado.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `services/pontuacao.py` — linha zerada pra vinculado sem task (golden regression)

**Files:**
- Modify: `docudata-backend/services/pontuacao.py`
- Modify: `docudata-backend/tests/test_pontuacao_fechamento.py` (`_mock_client` ganha parâmetro `operacionais`)
- Test: `docudata-backend/tests/test_pontuacao_fechamento.py` (novo teste)

**Interfaces:**
- Consumes: `listar_vinculados_no_projeto` (Task 4).
- Produces: `calcular_e_travar_pontuacao` passa a incluir, no conjunto de `operacional_ids` que ganham linha em `pontuacao_operacional_sprint`, todo vinculado sem contribuição nenhuma (com todos os contadores em 0). Task 7 (`_sequencia_pessoal`) depende deste efeito para fazer sentido.

**Este é o ponto mais delicado do plano — leia com atenção antes de mexer.** `calcular_e_travar_pontuacao` hoje SÓ cria linha pra quem aparece em `tasks` (via `pontos_alocados`/`pontos_concluidos`/etc. ou `avaliacoes_gerente`). `if not tasks: return []` no topo da função também impede QUALQUER linha de ser criada se a sprint não tiver nenhuma task. Este task muda os dois pontos: passa a incluir todo vinculado (mesmo sem task nenhuma) no conjunto que ganha linha, e só retorna `[]` cedo se não houver NEM tasks NEM vinculados.

- [ ] **Step 1: Write the failing test**

Primeiro, leia `docudata-backend/tests/test_pontuacao_fechamento.py` inteiro (função `_mock_client`, linhas 12-90 aproximadamente, e o teste golden em `test_golden_fixture_multidimensional_trava_de_regressao`, linha 268) — você vai estender o mock, não recriar.

Adicione o parâmetro `operacionais=None` à assinatura de `_mock_client` (junto aos outros parâmetros opcionais) e um branch novo `elif name == "operacionais":` no `table_side_effect`, no mesmo estilo do branch `elif name == "tasks":` já existente (select simples, sem filtro de fato aplicado pelo mock — o mock só devolve a lista fixa):

```python
def _mock_client(
    pontuacao_existente=None,
    cutoff_existente=None,
    sprint=None,
    tasks=None,
    task_transicoes=None,
    task_reaberturas=None,
    task_travamentos=None,
    eventos_tardios=None,
    avaliacoes=None,
    commit_qualidade=None,
    insert_capture=None,
    projeto=None,
    sprint_update_capture=None,
    eventos_insert_capture=None,
    eventos_insert_raises=False,
    operacionais=None,
):
    ...
    operacionais = operacionais or []
    ...
```

E dentro de `table_side_effect`, depois do branch `elif name == "avaliacoes_gerente":` (é o último antes do `return tbl`), adicione:

```python
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
```

Agora adicione o teste novo, ao final do arquivo:

```python
def test_vinculado_sem_task_ganha_linha_zerada():
    """O ponto central da correção do bug de PULL: alguém vinculado ao
    projeto, mas sem nenhuma contribuição na sprint (sem task, sem
    avaliação), ainda assim ganha uma linha em pontuacao_operacional_sprint
    com todos os contadores zerados — pra contar no denominador em vez de
    sumir. Ver
    docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
    vinculado_ativo = {
        "id": "op-ocioso", "nome": "Bruno", "email": None, "project_id": "proj-1",
        "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None,
    }
    task_de_outra_pessoa = {
        "id": "task-1", "operacional_id": "op-com-task", "pontos": 5,
        "coluna_kanban": "concluida", "extra": False,
        "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None,
    }
    insert_capture = []
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=[task_de_outra_pessoa],
        operacionais=[vinculado_ativo],
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linhas_por_operacional = {r["operacional_id"]: r for r in resultado}
    assert "op-ocioso" in linhas_por_operacional
    linha = linhas_por_operacional["op-ocioso"]
    assert linha["entrega_pontos_alocados"] == 0
    assert linha["entrega_pontos_concluidos"] == 0
    assert linha["bonus_pontos_extra"] == 0
    # A pessoa com task continua presente normalmente.
    assert "op-com-task" in linhas_por_operacional


def test_sprint_sem_nenhuma_task_ainda_cria_linhas_zeradas_pra_vinculados():
    """Antes desta Entrega 2, uma sprint com zero tasks retornava [] direto
    (early return). Agora, se houver vinculados, eles ainda ganham linha
    zerada — só retorna [] se não houver NEM task NEM vinculado."""
    vinculado = {
        "id": "op-1", "nome": "Ana", "email": None, "project_id": "proj-1",
        "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None,
    }
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=[],
        operacionais=[vinculado],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert len(resultado) == 1
    assert resultado[0]["operacional_id"] == "op-1"
    assert resultado[0]["entrega_pontos_alocados"] == 0


def test_sprint_sem_task_e_sem_vinculado_continua_retornando_vazio():
    client = _mock_client(sprint={"id": "sprint-1", "project_id": "proj-1"}, tasks=[], operacionais=[])
    assert calcular_e_travar_pontuacao(client, "sprint-1") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_pontuacao_fechamento.py -k "vinculado_sem_task or sem_nenhuma_task or sem_task_e_sem_vinculado" -v`
Expected: FAIL — `services/pontuacao.py` ainda não consulta `operacionais`, e ainda retorna `[]` cedo quando `tasks` está vazio.

- [ ] **Step 3: Implementar**

No topo de `docudata-backend/services/pontuacao.py`, adicione o import:

```python
from services.elegibilidade import listar_vinculados_no_projeto
```

Encontre:

```python
    tasks = (
        client.table("tasks")
        .select("id, operacional_id, pontos, coluna_kanban, extra, bloqueado_resolvido_por, bloqueado_resolvido_em")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    if not tasks:
        return []
```

Substitua por:

```python
    tasks = (
        client.table("tasks")
        .select("id, operacional_id, pontos, coluna_kanban, extra, bloqueado_resolvido_por, bloqueado_resolvido_em")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )

    # Entrega 2: todo vinculado ao projeto no momento do fechamento ganha
    # linha, mesmo sem nenhuma task — corrige o bug de PULL onde quem não
    # puxava nada nunca contava no denominador. `agora` é definido mais
    # abaixo pro resto da função; aqui usamos o mesmo timestamp calculado
    # já nesse ponto pra manter consistência com o congelamento de modo.
    momento_fechamento = datetime.now(timezone.utc).isoformat()
    vinculados = listar_vinculados_no_projeto(client, project_id, momento_fechamento)
    vinculados_ids = {op["id"] for op in vinculados}

    if not tasks and not vinculados_ids:
        return []
```

Mais abaixo, encontre o bloco que monta `operacional_ids` e a checagem seguinte:

```python
    operacional_ids = (
        set(pontos_alocados)
        | set(pontos_concluidos)
        | set(reaberturas)
        | set(bloqueios_totais)
        | set(pontos_penalizados)
        | set(bonus_extra)
        | set(avaliacao_por_operacional)
    )
    if not operacional_ids:
        return []

    agora = datetime.now(timezone.utc).isoformat()
```

Substitua por:

```python
    operacional_ids = (
        set(pontos_alocados)
        | set(pontos_concluidos)
        | set(reaberturas)
        | set(bloqueios_totais)
        | set(pontos_penalizados)
        | set(bonus_extra)
        | set(avaliacao_por_operacional)
        | vinculados_ids
    )
    if not operacional_ids:
        return []

    agora = momento_fechamento
```

(Reaproveita o `momento_fechamento` já calculado em vez de gerar um `datetime.now()` novo alguns microssegundos depois — mantém `sprint_fim`/`finalizado_em` consistentes com o momento usado pra decidir quem estava vinculado.)

**Note bem:** `vinculados_ids` inclui gente que JÁ estava em `operacional_ids` via task (redundante, mas `set` já deduplica — sem problema). Todo `operacional_id` que só veio de `vinculados_ids` vai cair nos `.get(operacional_id, 0)` de cada dict (`pontos_alocados.get(...)` etc.) mais abaixo no loop de montagem de `linhas`, que já usam `.get(..., 0)` — ou seja, a linha monta automaticamente com tudo zerado pra quem só está em `vinculados_ids`. Não precisa mexer no loop `for operacional_id in operacional_ids:` — ele já está pronto pra isso.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd docudata-backend && pytest tests/test_pontuacao_fechamento.py -v`
Expected: PASS em TODOS os testes do arquivo, incluindo `test_golden_fixture_multidimensional_trava_de_regressao` — se o golden fixture quebrar, leia a fixture (ela não passa `operacionais=` hoje, então `operacionais` fica `[]` por padrão, `vinculados_ids` fica vazio, e o comportamento deve ser idêntico ao de antes; se quebrar mesmo assim, é sinal de um bug na implementação do Step 3, não do teste — não ajuste a asserção do golden test).

- [ ] **Step 5: Run full suite**

Run: `cd docudata-backend && pytest -q`
Expected: mesmas falhas pré-existentes, nenhuma nova.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "$(cat <<'EOF'
feat(pontuacao): cria linha zerada pra vinculado sem task no fechamento (Entrega 2)

calcular_e_travar_pontuacao passa a incluir todo elegível (vinculado ao
projeto no momento do fechamento), não só quem tem contribuição via task —
sem isso a remoção do filtro de _sequencia_pessoal (próxima task) não teria
efeito nenhum. Golden regression confirmada verde.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `services/performance.py` — remove filtro que esconde quem tem 0 alocado

**Files:**
- Modify: `docudata-backend/services/performance.py`
- Test: `docudata-backend/tests/test_performance_sequencia.py` (criar se não existir; verifique primeiro com `ls docudata-backend/tests/ | grep performance`)

**Interfaces:**
- Consumes: linhas zeradas produzidas pela Task 6.
- Produces: `_sequencia_pessoal` passa a incluir linhas com `entrega_pontos_alocados == 0`. Nenhuma task seguinte depende diretamente disso.

- [ ] **Step 1: Verificar se já existe um arquivo de teste pra `_sequencia_pessoal`**

Run: `ls docudata-backend/tests/ | grep -i performance`

Se existir um arquivo cobrindo `_sequencia_pessoal`, adicione o teste novo nele. Se não existir nenhum, crie `docudata-backend/tests/test_performance_sequencia.py`.

- [ ] **Step 2: Write the failing test**

```python
# docudata-backend/tests/test_performance_sequencia.py (ou o arquivo existente)
"""services/performance.py::_sequencia_pessoal deve incluir linhas com 0
pontos alocados (Entrega 2 — vinculado que não puxou nada em PULL). Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §2.4."""
from unittest.mock import MagicMock

from services.performance import _sequencia_pessoal


def test_sequencia_pessoal_inclui_linha_com_zero_pontos_alocados():
    linha_zerada = {
        "operacional_id": "op-1", "entrega_pontos_alocados": 0,
        "entrega_pontos_concluidos": 0, "projeto_id": "p1", "sprint_fim": "2026-06-01T00:00:00+00:00",
    }
    client = MagicMock()
    q = MagicMock()
    q.in_ = MagicMock(return_value=q)
    q.order = MagicMock(return_value=q)
    resp = MagicMock()
    resp.data = [linha_zerada]
    q.execute = MagicMock(return_value=resp)
    client.table = MagicMock(return_value=MagicMock(select=MagicMock(return_value=q)))

    resultado = _sequencia_pessoal(client, ["op-1"])

    assert len(resultado) == 1
    assert resultado[0]["operacional_id"] == "op-1"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_performance_sequencia.py -v`
Expected: FAIL — a linha some porque o `.gt("entrega_pontos_alocados", 0)` no mock também precisa ser removido do lado do teste (o mock não filtra de verdade, então o teste falha por outro motivo: `q.gt` não está definido no mock acima, então a chain quebra com `AttributeError` antes mesmo de rodar o filtro real — confirma que o código de produção ainda chama `.gt(...)`).

- [ ] **Step 4: Implementar**

Em `docudata-backend/services/performance.py`, encontre:

```python
def _sequencia_pessoal(client, operacional_ids: list[str]) -> list[dict]:
    if not operacional_ids:
        return []
    return (
        client.table("pontuacao_operacional_sprint")
        .select("*")
        .in_("operacional_id", operacional_ids)
        .gt("entrega_pontos_alocados", 0)
        .order("sprint_fim", desc=True)
        .execute()
        .data or []
    )
```

Substitua por:

```python
def _sequencia_pessoal(client, operacional_ids: list[str]) -> list[dict]:
    """Entrega 2: NÃO filtra mais por entrega_pontos_alocados > 0 — antes
    disso, quem estava vinculado mas não tinha alocado nada (ex.: PULL, não
    puxou nenhuma task) sumia da própria sequência em vez de aparecer com 0.
    A Task 6 (services/pontuacao.py) garante que toda linha zerada
    relevante já existe em pontuacao_operacional_sprint."""
    if not operacional_ids:
        return []
    return (
        client.table("pontuacao_operacional_sprint")
        .select("*")
        .in_("operacional_id", operacional_ids)
        .order("sprint_fim", desc=True)
        .execute()
        .data or []
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd docudata-backend && pytest tests/test_performance_sequencia.py -v`
Expected: PASS

- [ ] **Step 6: Run full suite**

Run: `cd docudata-backend && pytest -q`
Expected: mesmas falhas pré-existentes, nenhuma nova. Preste atenção especial a qualquer teste que dependa do comportamento anterior (linha com 0 alocado sendo excluída) — se algum quebrar, é um teste que assumia o bug antigo; ajuste a fixture dele pra não ter esse tipo de linha se o objetivo do teste for outro, ou remova a asserção que dependia do bug se for exatamente esse o comportamento sendo testado.

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/services/performance.py docudata-backend/tests/test_performance_sequencia.py
git commit -m "$(cat <<'EOF'
fix(performance): _sequencia_pessoal não esconde mais quem tem 0 pontos alocados (Entrega 2)

Removido o filtro .gt("entrega_pontos_alocados", 0) — em PULL, quem não
puxava nenhuma task sumia da própria sequência em vez de aparecer com 0.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: RF-C7 — endpoint de elegíveis auditável

**Files:**
- Modify: `docudata-backend/routers/avaliacoes.py`
- Test: `docudata-backend/tests/test_endpoint_elegiveis.py`

**Interfaces:**
- Consumes: `_operacionais_elegiveis` (Task 5), `ElegivelResponse` (Task 2).
- Produces: `GET /avaliacoes/{sprint_id}/elegiveis`. Task 11 (frontend) consome este endpoint.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_endpoint_elegiveis.py
"""Testes para GET /avaliacoes/{sprint_id}/elegiveis (RF-C7, Entrega 2)."""
from unittest.mock import MagicMock

from routers.avaliacoes import listar_elegiveis


def _mock_client(sprint, operacionais, tasks, avaliacoes):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [sprint] if sprint else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = operacionais
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "avaliacoes_gerente":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = avaliacoes
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


async def test_lista_vinculado_sem_task_com_zero_e_nao_avaliado():
    sprint = {"id": "sprint-1", "project_id": "p1"}
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None}
    client = _mock_client(sprint, [op], tasks=[], avaliacoes=[])
    import routers.avaliacoes as mod
    mod.get_client = lambda: client

    resultado = await listar_elegiveis("sprint-1")

    assert resultado == [{"operacional_id": "op-1", "nome": "Ana", "tasks_na_sprint": 0, "avaliado": False}]


async def test_conta_tasks_e_avaliacao_corretamente():
    sprint = {"id": "sprint-1", "project_id": "p1"}
    op = {"id": "op-1", "nome": "Ana", "email": None, "project_id": "p1",
          "data_entrada": "2020-01-01T00:00:00+00:00", "data_saida": None}
    client = _mock_client(
        sprint, [op],
        tasks=[{"operacional_id": "op-1"}, {"operacional_id": "op-1"}],
        avaliacoes=[{"operacional_id": "op-1"}],
    )
    import routers.avaliacoes as mod
    mod.get_client = lambda: client

    resultado = await listar_elegiveis("sprint-1")

    assert resultado[0]["tasks_na_sprint"] == 2
    assert resultado[0]["avaliado"] is True


async def test_sprint_inexistente_retorna_404():
    from fastapi import HTTPException
    client = _mock_client(None, [], [], [])
    import routers.avaliacoes as mod
    mod.get_client = lambda: client

    try:
        await listar_elegiveis("sprint-x")
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_endpoint_elegiveis.py -v`
Expected: FAIL — `listar_elegiveis` ainda não existe.

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/avaliacoes.py`, adicione os imports necessários (`ElegivelResponse` em `models.schemas`, `require_not_operacional` em `services.auth`):

```python
from models.schemas import (
    AvaliacaoGerenteCreate,
    AvaliacaoGerenteResponse,
    ConfirmarAvaliacaoResponse,
    ElegivelResponse,
    PendenciaAvaliacaoResponse,
)
from services.auth import get_current_pessoa, require_not_operacional, require_role
```

Adicione o endpoint, logo depois de `listar_pendencias`:

```python
@router.get("/{sprint_id}/elegiveis", response_model=list[ElegivelResponse], dependencies=[Depends(require_not_operacional)])
async def listar_elegiveis(sprint_id: str):
    """RF-C7 (Entrega 2): todo operacional vinculado ao projeto no momento da
    consulta, com contagem de tasks na sprint (0 é válido) e se já tem
    avaliação registrada — audita quem entra no denominador da Avaliação
    Semanal mesmo sem ter puxado nenhuma task."""
    client = get_client()
    sprint_resp = client.table("sprints").select("project_id").eq("id", sprint_id).execute()
    if not sprint_resp.data:
        raise HTTPException(status_code=404, detail="Sprint not found")

    operacionais = _operacionais_elegiveis(client, sprint_id)

    task_rows = client.table("tasks").select("operacional_id").eq("sprint_id", sprint_id).execute().data or []
    tasks_por_operacional: dict[str, int] = {}
    for t in task_rows:
        op = t.get("operacional_id")
        if op:
            tasks_por_operacional[op] = tasks_por_operacional.get(op, 0) + 1

    aval_rows = client.table("avaliacoes_gerente").select("operacional_id").eq("sprint_id", sprint_id).execute().data or []
    avaliados_ids = {a["operacional_id"] for a in aval_rows}

    return [
        {
            "operacional_id": op["id"],
            "nome": op["nome"],
            "tasks_na_sprint": tasks_por_operacional.get(op["id"], 0),
            "avaliado": op["id"] in avaliados_ids,
        }
        for op in operacionais
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && pytest tests/test_endpoint_elegiveis.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Run full suite**

Run: `cd docudata-backend && pytest -q`
Expected: mesmas falhas pré-existentes, nenhuma nova.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/routers/avaliacoes.py docudata-backend/tests/test_endpoint_elegiveis.py
git commit -m "$(cat <<'EOF'
feat(avaliacoes): GET /avaliacoes/{sprint_id}/elegiveis — RF-C7 (Entrega 2)

Lista todo operacional vinculado ao projeto com contagem de tasks (0 é
válido) e se já foi avaliado — auditoria de quem entra no denominador.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: `services/metricas_comparacao.py` — agregação por modo

**Files:**
- Create: `docudata-backend/services/metricas_comparacao.py`
- Test: `docudata-backend/tests/test_metricas_comparacao.py`

**Interfaces:**
- Consumes: `sprints.modo_trabalho`/`modo_avaliacao` (congelados desde a Entrega 1), `sprints.pontos_orcamento`, `tasks.pontos`/`coluna_kanban`, `pontuacao_operacional_sprint.entrega_pontos_alocados`/`entrega_pontos_concluidos`.
- Produces: `comparar_modos_do_projeto(client, project_id) -> list[dict]`, `comparar_modos_entre_projetos(client, project_ids) -> list[dict]`. Task 10 consome ambas.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_metricas_comparacao.py
"""Testes para services/metricas_comparacao.py (Entrega 2). Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §3."""
from unittest.mock import MagicMock

from services.metricas_comparacao import comparar_modos_do_projeto, comparar_modos_entre_projetos


def _mock_client(sprints, tasks, pontuacoes):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "sprints":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = sprints
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "pontuacao_operacional_sprint":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = pontuacoes
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_agrupa_sprints_por_modo_congelado_dentro_do_projeto():
    sprints = [
        {"id": "s1", "project_id": "p1", "numero": 1, "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS", "pontos_orcamento": 10},
        {"id": "s2", "project_id": "p1", "numero": 2, "modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO", "pontos_orcamento": 10},
    ]
    tasks = [
        {"sprint_id": "s1", "pontos": 10, "coluna_kanban": "concluida"},
        {"sprint_id": "s2", "pontos": 5, "coluna_kanban": "concluida"},
    ]
    pontuacoes = [
        {"sprint_id": "s1", "entrega_pontos_alocados": 10, "entrega_pontos_concluidos": 10},
        {"sprint_id": "s2", "entrega_pontos_alocados": 8, "entrega_pontos_concluidos": 5},
    ]
    client = _mock_client(sprints, tasks, pontuacoes)

    resultado = comparar_modos_do_projeto(client, "p1")

    grupos = {(r["modo_trabalho"], r["modo_avaliacao"]): r for r in resultado}
    assert ("ATRIBUICAO", "PONTOS_ATRIBUIDOS") in grupos
    assert ("PULL", "PONTOS_RELATIVO") in grupos
    assert grupos[("ATRIBUICAO", "PONTOS_ATRIBUIDOS")]["sprints_count"] == 1
    assert grupos[("PULL", "PONTOS_RELATIVO")]["pontos_realizados_total"] == 5


def test_ignora_sprint_ainda_nao_fechada_sem_modo_congelado():
    sprints = [
        {"id": "s1", "project_id": "p1", "numero": 1, "modo_trabalho": None, "modo_avaliacao": None, "pontos_orcamento": 10},
    ]
    client = _mock_client(sprints, tasks=[], pontuacoes=[])

    resultado = comparar_modos_do_projeto(client, "p1")

    assert resultado == []


def test_comparar_modos_entre_projetos_junta_sprints_de_varios_projetos():
    sprints = [
        {"id": "s1", "project_id": "p1", "numero": 1, "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS", "pontos_orcamento": 10},
        {"id": "s2", "project_id": "p2", "numero": 1, "modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO", "pontos_orcamento": 10},
    ]
    client = _mock_client(sprints, tasks=[], pontuacoes=[])

    resultado = comparar_modos_entre_projetos(client, ["p1", "p2"])

    grupos = {(r["modo_trabalho"], r["modo_avaliacao"]) for r in resultado}
    assert grupos == {("ATRIBUICAO", "PONTOS_ATRIBUIDOS"), ("PULL", "PONTOS_RELATIVO")}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_metricas_comparacao.py -v`
Expected: FAIL — `services.metricas_comparacao` ainda não existe.

- [ ] **Step 3: Implementar**

```python
# docudata-backend/services/metricas_comparacao.py
"""Agregação de métricas por modo de trabalho/avaliação (Entrega 2). Usa
SEMPRE o modo congelado por sprint (sprints.modo_trabalho/modo_avaliacao),
nunca o modo ATUAL do projeto — um projeto pode já ter trocado de modo, e o
valor atual não representaria o histórico de sprints antigas. Ver
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md §3."""


def _agrupar_sprints_por_modo(sprints: list[dict]) -> dict[tuple[str, str], list[dict]]:
    grupos: dict[tuple[str, str], list[dict]] = {}
    for s in sprints:
        modo_trabalho = s.get("modo_trabalho")
        modo_avaliacao = s.get("modo_avaliacao")
        if not modo_trabalho or not modo_avaliacao:
            continue  # sprint ainda não fechada, sem modo congelado
        grupos.setdefault((modo_trabalho, modo_avaliacao), []).append(s)
    return grupos


def _metricas_do_grupo(client, sprints_do_grupo: list[dict]) -> dict:
    sprint_ids = [s["id"] for s in sprints_do_grupo]

    tasks = (
        client.table("tasks")
        .select("sprint_id, pontos, coluna_kanban")
        .in_("sprint_id", sprint_ids)
        .execute()
        .data or []
    )
    pontos_realizados_total = sum(t["pontos"] for t in tasks if t.get("coluna_kanban") == "concluida")
    pontos_previstos_total = sum(s.get("pontos_orcamento") or 0 for s in sprints_do_grupo) or None
    spi_medio = (
        round(pontos_realizados_total / pontos_previstos_total, 3)
        if pontos_previstos_total else None
    )

    pont_rows = (
        client.table("pontuacao_operacional_sprint")
        .select("entrega_pontos_concluidos, entrega_pontos_alocados")
        .in_("sprint_id", sprint_ids)
        .execute()
        .data or []
    )
    alocados_total = sum(r.get("entrega_pontos_alocados") or 0 for r in pont_rows)
    concluidos_travados_total = sum(r.get("entrega_pontos_concluidos") or 0 for r in pont_rows)
    entrega_media = round(concluidos_travados_total / alocados_total, 3) if alocados_total else None

    return {
        "sprints_count": len(sprints_do_grupo),
        "pontos_previstos_total": pontos_previstos_total,
        "pontos_realizados_total": pontos_realizados_total,
        "spi_medio": spi_medio,
        "entrega_media": entrega_media,
    }


def _comparar(client, sprints: list[dict]) -> list[dict]:
    grupos = _agrupar_sprints_por_modo(sprints)
    resultado = []
    for (modo_trabalho, modo_avaliacao), sprints_do_grupo in grupos.items():
        resultado.append({
            "modo_trabalho": modo_trabalho,
            "modo_avaliacao": modo_avaliacao,
            **_metricas_do_grupo(client, sprints_do_grupo),
        })
    return resultado


def comparar_modos_do_projeto(client, project_id: str) -> list[dict]:
    sprints = (
        client.table("sprints")
        .select("id, project_id, numero, modo_trabalho, modo_avaliacao, pontos_orcamento")
        .eq("project_id", project_id)
        .execute()
        .data or []
    )
    return _comparar(client, sprints)


def comparar_modos_entre_projetos(client, project_ids: list[str]) -> list[dict]:
    """Mesma agregação de comparar_modos_do_projeto, mas junta as sprints de
    TODOS os projetos informados num único grupo por modo — cada projeto
    pode contribuir sprints pra mais de um grupo se já trocou de modo."""
    sprints = (
        client.table("sprints")
        .select("id, project_id, numero, modo_trabalho, modo_avaliacao, pontos_orcamento")
        .in_("project_id", project_ids)
        .execute()
        .data or []
    )
    return _comparar(client, sprints)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && pytest tests/test_metricas_comparacao.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/metricas_comparacao.py docudata-backend/tests/test_metricas_comparacao.py
git commit -m "$(cat <<'EOF'
feat(metricas): agregação por modo dentro do projeto e entre projetos (Entrega 2)

services/metricas_comparacao.py — agrupa sprints fechadas pelo modo
congelado (nunca o modo atual do projeto), calcula SPI médio e entrega
média por grupo.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Endpoints de comparação de modos

**Files:**
- Modify: `docudata-backend/routers/metricas.py`
- Test: `docudata-backend/tests/test_endpoint_comparacao_modos.py`

**Interfaces:**
- Consumes: `comparar_modos_do_projeto`, `comparar_modos_entre_projetos` (Task 9).
- Produces: `GET /metricas/{project_id}/comparacao-modos`, `GET /metricas/comparacao-modos?projeto_ids=...`. Task 12 (frontend) consome ambos.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_endpoint_comparacao_modos.py
"""Testes para os endpoints de comparação de modos (Entrega 2)."""
from unittest.mock import MagicMock

from routers.metricas import get_comparacao_modos, get_comparacao_modos_entre_projetos


async def test_get_comparacao_modos_404_se_projeto_nao_existe():
    from fastapi import HTTPException
    client = MagicMock()
    q = MagicMock()
    q.eq = MagicMock(return_value=q)
    resp = MagicMock()
    resp.data = []
    q.execute = MagicMock(return_value=resp)
    client.table = MagicMock(return_value=MagicMock(select=MagicMock(return_value=q)))
    import routers.metricas as mod
    mod.get_client = lambda: client

    try:
        await get_comparacao_modos("proj-x")
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404


async def test_get_comparacao_modos_entre_projetos_exige_ao_menos_2_ids():
    from fastapi import HTTPException
    try:
        await get_comparacao_modos_entre_projetos(projeto_ids="proj-1")
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_endpoint_comparacao_modos.py -v`
Expected: FAIL — endpoints ainda não existem.

- [ ] **Step 3: Implementar**

Em `docudata-backend/routers/metricas.py`, adicione o import no topo:

```python
from services.metricas_comparacao import comparar_modos_do_projeto, comparar_modos_entre_projetos
```

Adicione os dois endpoints, ao final do arquivo:

```python
@router.get("/{project_id}/comparacao-modos")
async def get_comparacao_modos(project_id: str):
    """Entrega 2 — compara métricas entre os modos que este projeto já usou
    (sprints agrupadas pelo modo congelado no fechamento de cada uma)."""
    client = get_client()
    proj = client.table("projects").select("id").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return comparar_modos_do_projeto(client, project_id)


@router.get("/comparacao-modos")
async def get_comparacao_modos_entre_projetos(
    projeto_ids: str = Query(..., description="IDs de projeto separados por vírgula, mínimo 2"),
):
    """Entrega 2 — compara métricas entre os modos usados por 2+ projetos
    escolhidos, agrupando pelo modo congelado de cada sprint deles."""
    ids = [p.strip() for p in projeto_ids.split(",") if p.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=422, detail="Informe ao menos 2 projeto_ids")
    client = get_client()
    return comparar_modos_entre_projetos(client, ids)
```

(A rota `/comparacao-modos` sem parâmetro de path não colide com `/{project_id}/comparacao-modos` — a primeira tem 1 segmento depois do prefixo `/metricas`, a segunda tem 2. Ordem de declaração não importa aqui.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && pytest tests/test_endpoint_comparacao_modos.py -v`
Expected: PASS (2/2)

- [ ] **Step 5: Run full suite (fim da Onda 1)**

Run: `cd docudata-backend && pytest -q`
Expected: mesmas falhas pré-existentes de antes da Entrega 2 (1 falha em `test_security.py`, não relacionada), nenhuma nova. Confirme especificamente que `test_golden_fixture_multidimensional_trava_de_regressao` está verde.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/routers/metricas.py docudata-backend/tests/test_endpoint_comparacao_modos.py
git commit -m "$(cat <<'EOF'
feat(metricas): GET .../comparacao-modos dentro e entre projetos (Entrega 2)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

**FIM DA ONDA 1.** Não inicie a Onda 2 antes de confirmar que a suite completa do backend está verde (Step 5 acima) e que o golden regression continua intacto.

---

## Onda 2 — Front-end

### Task 11: `app/lib/api.ts` — tipos e funções novas

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`

**Interfaces:**
- Consumes: `GET /avaliacoes/{sprint_id}/elegiveis`, `GET /metricas/{project_id}/comparacao-modos`, `GET /metricas/comparacao-modos` (Tasks 8, 10).
- Produces: `getElegiveis`, `getComparacaoModos`, `getComparacaoModosEntreProjetos`, tipos `ElegivelPonto`, `ComparacaoModoPonto`. Tasks 12, 13, 14 consomem.

- [ ] **Step 1: Write the failing test**

Crie (ou estenda, se o arquivo da Entrega 1 ainda existir) `docudata-frontend/tests/modos-trabalho-avaliacao-entrega2.test.mjs`:

```js
import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf8");

test("api.ts tem os tipos e funções de elegibilidade e comparação de modos", () => {
  assert.ok(API.includes("export interface ElegivelPonto"));
  assert.ok(API.includes("export async function getElegiveis("));
  assert.ok(API.includes("export interface ComparacaoModoPonto"));
  assert.ok(API.includes("export async function getComparacaoModos("));
  assert.ok(API.includes("export async function getComparacaoModosEntreProjetos("));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega2.test.mjs`
Expected: FAIL

- [ ] **Step 3: Implementar**

Ao final de `docudata-frontend/app/lib/api.ts` (depois das funções de métricas existentes, `getMetricasCycleTimeStats` etc.), adicione:

```ts
// ---------------------------------------------------------------------------
// Elegibilidade e comparação de modos (Entrega 2)
// ---------------------------------------------------------------------------

export interface ElegivelPonto {
  operacional_id: string;
  nome: string;
  tasks_na_sprint: number;
  avaliado: boolean;
}

export async function getElegiveis(sprintId: string): Promise<ElegivelPonto[]> {
  const res = await apiFetch(`${API}/avaliacoes/${sprintId}/elegiveis`);
  if (!res.ok) throw new Error("Erro ao buscar elegíveis da sprint");
  return res.json();
}

export interface ComparacaoModoPonto {
  modo_trabalho: string;
  modo_avaliacao: string;
  sprints_count: number;
  pontos_previstos_total: number | null;
  pontos_realizados_total: number;
  spi_medio: number | null;
  entrega_media: number | null;
}

export async function getComparacaoModos(projectId: string): Promise<ComparacaoModoPonto[]> {
  const res = await apiFetch(`${API}/metricas/${projectId}/comparacao-modos`);
  if (!res.ok) throw new Error("Erro ao buscar comparação de modos");
  return res.json();
}

export async function getComparacaoModosEntreProjetos(projetoIds: string[]): Promise<ComparacaoModoPonto[]> {
  const res = await apiFetch(`${API}/metricas/comparacao-modos?projeto_ids=${projetoIds.join(",")}`);
  if (!res.ok) throw new Error("Erro ao buscar comparação entre projetos");
  return res.json();
}
```

Confirme que a constante `API` (base URL) já existe no arquivo — se o nome real for diferente (ex.: `API_URL`), use o nome que já existe no arquivo em vez de `API`, seguindo exatamente o padrão das funções vizinhas (`getMetricasSpi` etc.) já copiadas acima.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega2.test.mjs`
Expected: PASS

- [ ] **Step 5: Run full frontend suite and build**

Run: `cd docudata-frontend && npm test && npm run build`
Expected: tudo passa, build limpo.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/lib/api.ts docudata-frontend/tests/modos-trabalho-avaliacao-entrega2.test.mjs
git commit -m "$(cat <<'EOF'
feat(api): tipos e funções pra elegibilidade e comparação de modos (Entrega 2)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: `PainelTab.tsx` — seção "Elegibilidade da sprint" (RF-C7)

**Files:**
- Modify: `docudata-frontend/app/components/PainelTab.tsx`

**Interfaces:**
- Consumes: `getElegiveis`, `type ElegivelPonto` (Task 11); `sprints: SprintWithStatus[]` (já é prop existente de `PainelTab`).
- Produces: nada consumido por tasks seguintes.

- [ ] **Step 1: Write the failing test**

Adicione ao mesmo arquivo de teste da Task 11:

```js
const PAINEL = readFileSync(new URL("../app/components/PainelTab.tsx", import.meta.url), "utf8");

test("PainelTab mostra a seção de elegibilidade da sprint", () => {
  assert.ok(PAINEL.includes("function ElegibilidadeCard("));
  assert.ok(PAINEL.includes("getElegiveis("));
  assert.ok(PAINEL.includes("<ElegibilidadeCard"));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega2.test.mjs`
Expected: FAIL na nova asserção.

- [ ] **Step 3: Implementar**

Primeiro leia `docudata-frontend/app/components/PainelTab.tsx` inteiro e localize `ExtratoPontosCard` (adicionado na Entrega 1) — este componente novo (`ElegibilidadeCard`) segue exatamente o mesmo formato: um `<select>` de sprint (reaproveite `Props.sprints`, já disponível), busca via `useEffect`, estados de loading/erro/vazio, tabela `<table>` com `thSt`/`tdSt` (já existem no arquivo desde a Task 12 da Entrega 1 — não redeclare, reaproveite os mesmos consts).

Adicione o import de `getElegiveis`/`ElegivelPonto` ao bloco de imports de `../lib/api` já existente no topo do arquivo.

Adicione o componente, logo depois de `ExtratoPontosCard`:

```tsx
function ElegibilidadeCard({ sprints }: { sprints: SprintWithStatus[] }) {
  const [sprintId, setSprintId] = useState<string>(sprints[0]?.id ?? "");
  const [elegiveis, setElegiveis] = useState<ElegivelPonto[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!sprintId) return;
    setLoading(true);
    setErro(null);
    getElegiveis(sprintId)
      .then(setElegiveis)
      .catch((err) => setErro(err instanceof Error ? err.message : "Erro ao carregar"))
      .finally(() => setLoading(false));
  }, [sprintId]);

  return (
    <div style={cardStyle}>
      <p style={cardTitleStyle}>Elegibilidade da sprint</p>
      <select
        value={sprintId}
        onChange={(e) => setSprintId(e.target.value)}
        style={{ ...inputSmStyle, marginBottom: 12 }}
      >
        {sprints.map((s) => (
          <option key={s.id} value={s.id}>Sprint {s.numero}</option>
        ))}
      </select>

      {loading ? (
        <p style={{ fontSize: 12, color: "#9696a0" }}>Carregando...</p>
      ) : erro ? (
        <p style={{ fontSize: 12, color: "#dc2626" }}>{erro}</p>
      ) : elegiveis.length === 0 ? (
        <p style={{ fontSize: 12, color: "#9696a0" }}>Ninguém vinculado a este projeto nesta consulta.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
            <thead>
              <tr>
                <th style={thSt} scope="col">Nome</th>
                <th style={thSt} scope="col">Tasks na sprint</th>
                <th style={thSt} scope="col">Avaliado</th>
              </tr>
            </thead>
            <tbody>
              {elegiveis.map((e) => (
                <tr key={e.operacional_id}>
                  <td style={tdSt}>{e.nome}</td>
                  <td style={tdSt}>{e.tasks_na_sprint}</td>
                  <td style={{ ...tdSt, color: e.avaliado ? "#16a34a" : "#dc2626" }}>
                    {e.avaliado ? "Sim" : "Não"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

Renderize `<ElegibilidadeCard sprints={sprints} />` no corpo de `PainelTab`, logo depois de `<ExtratoPontosCard ... />`.

Confirme os nomes exatos de `cardStyle`, `cardTitleStyle`, `inputSmStyle`, `thSt`, `tdSt` no arquivo real antes de usar — se algum tiver nome ligeiramente diferente do que está acima, use o nome real (os das Tasks 11/12 da Entrega 1 são a referência).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega2.test.mjs`
Expected: PASS

- [ ] **Step 5: Run full frontend suite and build**

Run: `cd docudata-frontend && npm test && npm run build`
Expected: tudo passa, build limpo.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/components/PainelTab.tsx docudata-frontend/tests/modos-trabalho-avaliacao-entrega2.test.mjs
git commit -m "$(cat <<'EOF'
feat(painel): seção Elegibilidade da sprint (RF-C7, Entrega 2)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: `MetricasTab.tsx` — seção "Comparação de modos" (dentro do projeto)

**Files:**
- Modify: `docudata-frontend/app/components/MetricasTab.tsx`

**Interfaces:**
- Consumes: `getComparacaoModos`, `type ComparacaoModoPonto` (Task 11).
- Produces: nada consumido por tasks seguintes.

- [ ] **Step 1: Write the failing test**

```js
const METRICAS = readFileSync(new URL("../app/components/MetricasTab.tsx", import.meta.url), "utf8");

test("MetricasTab mostra a comparação de modos dentro do projeto", () => {
  assert.ok(METRICAS.includes("getComparacaoModos("));
  assert.ok(METRICAS.includes("Comparação de modos"));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega2.test.mjs`
Expected: FAIL

- [ ] **Step 3: Implementar**

Adicione `getComparacaoModos`, `type ComparacaoModoPonto` ao bloco de imports de `../lib/api` no topo de `MetricasTab.tsx`.

Dentro do componente `MetricasTab`, adicione o `useState`/`useEffect` novo junto aos existentes (`spi`, `throughput`, etc. — siga o mesmo padrão de carregamento):

```tsx
  const [comparacaoModos, setComparacaoModos] = useState<ComparacaoModoPonto[]>([]);

  useEffect(() => {
    getComparacaoModos(projectId).then(setComparacaoModos).catch(() => setComparacaoModos([]));
  }, [projectId]);
```

(Localize onde os outros `useEffect` de carregamento estão, no topo do componente, e siga exatamente o mesmo padrão — os detalhes exatos de nome de variável de erro/loading das seções vizinhas devem ser espelhados; leia o arquivo antes de escrever para confirmar o padrão exato usado nas seções já existentes.)

Adicione a seção nova, depois da última seção existente (`Entrega e evolução por pessoa`), reaproveitando o `BarChart` agrupado exatamente como em "SPI por sprint":

```tsx
      {/* Comparação de modos (Entrega 2) */}
      {comparacaoModos.length >= 2 && (
        <div style={section}>
          <p style={title}>Comparação de modos</p>
          <p style={subtitle}>
            Sprints fechadas agrupadas pelo modo vigente no momento do fechamento de cada uma.
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={comparacaoModos.map((c) => ({
                modo: `${c.modo_trabalho}/${c.modo_avaliacao}`,
                spi_medio: c.spi_medio,
                entrega_media: c.entrega_media,
              }))}
              margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="modo" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend formatter={(v) => v === "spi_medio" ? "SPI médio" : "Entrega média"} />
              <Bar dataKey="spi_medio" fill="#64748b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="entrega_media" fill="#166534" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
```

(A condição `comparacaoModos.length >= 2` esconde a seção quando o projeto só usou um modo até agora — comparação de 1 grupo só não agrega nada visualmente. Ajuste pra `length >= 1` se preferir mostrar mesmo com um único modo, mas o padrão pedido no spec é comparativo, então manter `>= 2` é a leitura mais fiel.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega2.test.mjs`
Expected: PASS

- [ ] **Step 5: Run full frontend suite and build**

Run: `cd docudata-frontend && npm test && npm run build`
Expected: tudo passa, build limpo.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/components/MetricasTab.tsx docudata-frontend/tests/modos-trabalho-avaliacao-entrega2.test.mjs
git commit -m "$(cat <<'EOF'
feat(metricas): seção Comparação de modos dentro do projeto (Entrega 2)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: Nova página — comparação de modos entre projetos

**Files:**
- Create: `docudata-frontend/app/comparacao-modos/page.tsx`

**Interfaces:**
- Consumes: `getComparacaoModosEntreProjetos`, `type ComparacaoModoPonto` (Task 11); `listProjects(subarea: Subarea)` e `type Project` (já existem em `api.ts`, `Subarea = "dados" | "dev"`); `useAuth` de `../components/AuthGuard`.
- Produces: nada consumido por tasks seguintes — última peça de UI do plano.

**Confirmado por exploração (não é preciso reconfirmar ao implementar):** `app/pessoas/page.tsx` e `app/performance/page.tsx` são páginas top-level (fora de `app/[subarea]/`, que é usado só para as rotas de projeto). `listProjects` exige `subarea` como argumento — não existe uma listagem cross-subarea pronta, então esta página busca as duas subáreas (`"dados"` e `"dev"`) em paralelo e junta o resultado.

- [ ] **Step 1: Write the failing test**

```js
const PAGE_ENTRE_PROJETOS = readFileSync(
  new URL("../app/comparacao-modos/page.tsx", import.meta.url),
  "utf8"
);

test("página de comparação entre projetos existe e usa a função certa", () => {
  assert.ok(PAGE_ENTRE_PROJETOS.includes("getComparacaoModosEntreProjetos("));
  assert.ok(PAGE_ENTRE_PROJETOS.includes("export default function"));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega2.test.mjs`
Expected: FAIL — arquivo ainda não existe.

- [ ] **Step 3: Implementar**

```tsx
// docudata-frontend/app/comparacao-modos/page.tsx
"use client";

import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  listProjects,
  getComparacaoModosEntreProjetos,
  type Project,
  type ComparacaoModoPonto,
} from "../lib/api";

const section: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 12,
  padding: "20px 24px",
  marginBottom: 20,
};

export default function ComparacaoModosPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selecionados, setSelecionados] = useState<string[]>([]);
  const [resultado, setResultado] = useState<ComparacaoModoPonto[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listProjects("dados"), listProjects("dev")])
      .then(([dados, dev]) => setProjects([...dados, ...dev]))
      .catch(() => setProjects([]));
  }, []);

  function toggleProjeto(id: string) {
    setSelecionados((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  }

  function buscar() {
    if (selecionados.length < 2) {
      setErro("Selecione ao menos 2 projetos.");
      return;
    }
    setLoading(true);
    setErro(null);
    getComparacaoModosEntreProjetos(selecionados)
      .then(setResultado)
      .catch((err) => setErro(err instanceof Error ? err.message : "Erro ao comparar"))
      .finally(() => setLoading(false));
  }

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", marginBottom: 20 }}>
        Comparação de modos entre projetos
      </h1>

      <div style={section}>
        <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Escolha 2 ou mais projetos</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
          {projects.map((p) => (
            <label key={p.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
              <input
                type="checkbox"
                checked={selecionados.includes(p.id)}
                onChange={() => toggleProjeto(p.id)}
              />
              {p.name}
            </label>
          ))}
        </div>
        <button
          type="button"
          onClick={buscar}
          disabled={loading || selecionados.length < 2}
          style={{
            background: "#22c55e",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "8px 16px",
            fontSize: 13,
            cursor: loading || selecionados.length < 2 ? "not-allowed" : "pointer",
            opacity: loading || selecionados.length < 2 ? 0.5 : 1,
          }}
        >
          {loading ? "Comparando..." : "Comparar"}
        </button>
        {erro && <p style={{ fontSize: 12, color: "#dc2626", marginTop: 8 }}>{erro}</p>}
      </div>

      {resultado.length > 0 && (
        <div style={section}>
          <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Resultado</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={resultado.map((r) => ({
                modo: `${r.modo_trabalho}/${r.modo_avaliacao}`,
                spi_medio: r.spi_medio,
                entrega_media: r.entrega_media,
              }))}
              margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="modo" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend formatter={(v) => v === "spi_medio" ? "SPI médio" : "Entrega média"} />
              <Bar dataKey="spi_medio" fill="#64748b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="entrega_media" fill="#166534" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega2.test.mjs`
Expected: PASS

- [ ] **Step 5: Run full frontend suite and build**

Run: `cd docudata-frontend && npm test && npm run build`
Expected: tudo passa, build limpo. Este é o último passo de código do plano — depois deste build limpo, a Entrega 2 está funcionalmente completa.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/comparacao-modos/page.tsx docudata-frontend/tests/modos-trabalho-avaliacao-entrega2.test.mjs
git commit -m "$(cat <<'EOF'
feat(comparacao-modos): página de comparação entre projetos (Entrega 2)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Verificação final (depois da Task 14)

Rodar a suíte completa de backend e frontend + build antes de declarar a Entrega 2 concluída:

```bash
cd docudata-backend && pytest -q
cd ../docudata-frontend && npm test && npm run build
```

Esperado: mesmas falhas pré-existentes de sempre (1 em `test_security.py`), nenhuma nova; golden regression verde; build limpo. Depois disso, seguir pro checklist de Etapa 12 do feature-flow-lean (mesmo formato usado na Entrega 1 — ver `docs/superpowers/plans/2026-09-20-modos-trabalho-avaliacao-entrega1-VERIFICACAO.md` como modelo).

**Lembrete de deploy:** a migração da Task 1 (`operacionais.data_entrada`/`data_saida`) precisa rodar manualmente no Supabase antes do próximo deploy, no mesmo lote da migração pendente da Entrega 1 se ela ainda não tiver rodado (ver memória `project_manual_migrations.md`).
