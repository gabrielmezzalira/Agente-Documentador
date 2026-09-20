# Modos de Trabalho e de Avaliação — Entrega 1 (Base) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the schema, backend, and UI for Entrega 1 (Base) of the Modos de Trabalho e de Avaliação feature — project-level config for `modo_trabalho`/`modo_avaliacao`, an immutable config-change history, a per-sprint "N/M" avaliação semanal counter, and an auditable points ledger (`pontuacao_eventos`) — **without changing any existing scoring behavior** for projects left in the default `ATRIBUICAO` + `PONTOS_ATRIBUIDOS` configuration.

**Architecture:** Two waves. Onda 1 (backend) adds the schema, extends `services/pontuacao.py`'s existing fechamento function to freeze the sprint's modo and write ledger rows, adds a new `services/avaliacoes.py` helper for the N/M counter, and exposes three new endpoints on `routers/projects.py` plus one on `routers/pontuacao.py`. A golden regression test with fixed data is written and confirmed green **before** touching `services/pontuacao.py`, and confirmed green **again after**, to prove zero behavior change (SDD risk #1). Onda 2 (UI) wires all of this into the existing inline-styled Next.js pages, following established patterns exactly (no new libraries, no design system file — this codebase has neither).

**Tech Stack:** FastAPI + Pydantic + supabase-py (backend), Next.js 15 / React 19 with inline `style={{}}` objects (frontend). Backend tests: pytest + `unittest.mock.MagicMock` + `fastapi.testclient.TestClient`. Frontend tests: `node --test` reading raw source files and asserting on literal substrings (no component-testing framework is installed).

**Spec:** `docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md` (§3 "Entrega 1 — Base", §4 schema, §10 test plan). Read it alongside this plan — this plan implements exactly its Entrega 1 scope and no more.

## Global Constraints

- Entrega 1 **must not change any computed score** for a project left at the defaults (`modo_trabalho='ATRIBUICAO'`, `modo_avaliacao='PONTOS_ATRIBUIDOS'`). Every existing test in `tests/test_pontuacao_fechamento.py` must stay green, unmodified in its assertions.
- All SQL migrations are appended to `docudata-backend/supabase_schema.sql`, are idempotent (`IF NOT EXISTS`), and are **never** run automatically — this project's migrations are always manual (Supabase SQL Editor), per existing convention at the top of that file.
- No new npm/pip dependency is introduced. No Tailwind, no CSS framework, no drag-and-drop library — this codebase uses plain inline `style={{}}` objects and native HTML5 drag-and-drop exclusively.
- RBAC follows the existing hierarchy in `services/auth.py` (`operacional < gerente < lider < owner`). New config-writing endpoints use `require_not_operacional` (Gerente and up), matching the existing `/projects/{id}/subarea` endpoint. The points ledger (`GET /operacionais/{id}/extrato`) is Gerente/Líder/Owner only — never Operacional.
- Follow existing naming/docstring conventions: Portuguese identifiers and docstrings throughout `services/`, `routers/`, `models/schemas.py`; English is not used in this codebase's Python or component code.
- Frontend: new types/functions go in `app/lib/api.ts` (single file — that's the existing convention); new page-level sub-components are defined **inline** inside the file that uses them (e.g. `OperacionaisSection` inside `page.tsx`, `BlocoACard` inside `PainelTab.tsx`) — never split into a new file, matching this codebase's existing pattern.
- Every backend task follows TDD: write the failing test(s) first, run to confirm failure, implement, run to confirm pass, commit.

---

## Task 1: Schema — Entrega 1 tables and columns

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (append at end of file)
- Test: `docudata-backend/tests/test_modos_schema.py`

**Interfaces:**
- Produces: columns `projects.modo_trabalho`, `projects.modo_avaliacao`, `projects.pull_exigir_hidratacao`, `projects.pull_piso_pontos`, `projects.pull_teto`; table `configuracao_historico`; columns `sprints.modo_trabalho`, `sprints.modo_avaliacao`, `sprints.hibrida`; table `pontuacao_eventos`. All later tasks depend on these existing in the schema file (not necessarily in a live database during tests — tests mock the Supabase client).

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_modos_schema.py
"""Confirma que a migração da Entrega 1 (Modos de Trabalho e de Avaliação)
está presente no schema. Ver docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md §4."""
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def _texto_schema() -> str:
    return _SCHEMA.read_text()


def test_projects_ganha_colunas_de_modo():
    schema = _texto_schema()
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS modo_trabalho text NOT NULL DEFAULT 'ATRIBUICAO'" in schema
    assert "CHECK (modo_trabalho IN ('ATRIBUICAO','PULL'))" in schema
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS modo_avaliacao text NOT NULL DEFAULT 'PONTOS_ATRIBUIDOS'" in schema
    assert "CHECK (modo_avaliacao IN ('PONTOS_ATRIBUIDOS','PONTOS_RELATIVO'))" in schema
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_exigir_hidratacao boolean NOT NULL DEFAULT true;" in schema
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_piso_pontos numeric(6,2) NOT NULL DEFAULT 1;" in schema
    assert "ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_teto numeric(4,2) NOT NULL DEFAULT 1.5;" in schema


def test_configuracao_historico_existe():
    schema = _texto_schema()
    assert "CREATE TABLE IF NOT EXISTS configuracao_historico (" in schema
    assert "campo           text NOT NULL CHECK (campo IN ('modo_trabalho','modo_avaliacao'))" in schema


def test_sprints_ganha_colunas_de_modo_e_hibrida():
    schema = _texto_schema()
    assert "ALTER TABLE sprints ADD COLUMN IF NOT EXISTS modo_trabalho text;" in schema
    assert "ALTER TABLE sprints ADD COLUMN IF NOT EXISTS modo_avaliacao text;" in schema
    assert "ALTER TABLE sprints ADD COLUMN IF NOT EXISTS hibrida boolean NOT NULL DEFAULT false;" in schema


def test_pontuacao_eventos_existe():
    schema = _texto_schema()
    assert "CREATE TABLE IF NOT EXISTS pontuacao_eventos (" in schema
    assert "'entrega_concluida','travamento_penalidade','devolucao_penalidade','bonus_extra','reabertura'" in schema
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && python -m pytest tests/test_modos_schema.py -v`
Expected: FAIL — none of the strings exist in `supabase_schema.sql` yet.

- [ ] **Step 3: Append the migration to `supabase_schema.sql`**

Append this block at the very end of `docudata-backend/supabase_schema.sql` (after the last existing line, which is the `idx_pontuacao_operacional_sprint_fim` comment block):

```sql

-- ═══════════════════════════════════════════════════════════════
-- Modos de Trabalho e de Avaliação — Entrega 1: Base (spec
-- docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md)
-- Só schema desta entrega: config de modo por projeto, histórico de
-- mudança de modo, congelamento de modo por sprint, e o extrato de
-- pontos (ledger). Nenhuma coluna de fila/pull/elegibilidade (Entrega 2).
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE projects ADD COLUMN IF NOT EXISTS modo_trabalho text NOT NULL DEFAULT 'ATRIBUICAO'
    CHECK (modo_trabalho IN ('ATRIBUICAO','PULL'));
ALTER TABLE projects ADD COLUMN IF NOT EXISTS modo_avaliacao text NOT NULL DEFAULT 'PONTOS_ATRIBUIDOS'
    CHECK (modo_avaliacao IN ('PONTOS_ATRIBUIDOS','PONTOS_RELATIVO'));
ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_exigir_hidratacao boolean NOT NULL DEFAULT true;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_piso_pontos numeric(6,2) NOT NULL DEFAULT 1;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS pull_teto numeric(4,2) NOT NULL DEFAULT 1.5;

CREATE TABLE IF NOT EXISTS configuracao_historico (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    campo           text NOT NULL CHECK (campo IN ('modo_trabalho','modo_avaliacao')),
    valor_anterior  text,
    valor_novo      text NOT NULL,
    usuario_email   text NOT NULL,
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_configuracao_historico_project ON configuracao_historico(project_id, criado_em DESC);

ALTER TABLE sprints ADD COLUMN IF NOT EXISTS modo_trabalho text;
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS modo_avaliacao text;
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS hibrida boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS pontuacao_eventos (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id  uuid NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    sprint_id       uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    projeto_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id         uuid REFERENCES tasks(id) ON DELETE SET NULL,
    tipo            text NOT NULL CHECK (tipo IN
        ('entrega_concluida','travamento_penalidade','devolucao_penalidade','bonus_extra','reabertura')),
    pontos          int NOT NULL DEFAULT 0,
    descricao       text,
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pontuacao_eventos_operacional ON pontuacao_eventos(operacional_id, sprint_id);
CREATE INDEX IF NOT EXISTS idx_pontuacao_eventos_sprint ON pontuacao_eventos(sprint_id);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && python -m pytest tests/test_modos_schema.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/supabase_schema.sql docudata-backend/tests/test_modos_schema.py
git commit -m "$(cat <<'EOF'
feat(schema): adiciona colunas e tabelas da Entrega 1 de Modos de Trabalho

projects ganha modo_trabalho/modo_avaliacao/pull_*; nova tabela
configuracao_historico (RF-A6); sprints ganha modo_trabalho/modo_avaliacao/
hibrida (congelamento no fechamento); nova tabela pontuacao_eventos (extrato
de pontos auditável, extra do usuário). Migração manual — não roda sozinha.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Pydantic schemas for the new endpoints and response fields

**Files:**
- Modify: `docudata-backend/models/schemas.py`
- Test: `docudata-backend/tests/test_modos_schemas_validation.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `ModoTrabalho`, `ModoAvaliacao` type aliases; `ModosProjetoUpdate`, `ConfiguracaoHistoricoResponse`, `WipConfigUpdate`, `WipConfigResponse`, `PontuacaoEventoResponse` classes; extended `ProjectResponse` (adds `modo_trabalho`, `modo_avaliacao`, `pull_exigir_hidratacao`, `pull_piso_pontos`, `pull_teto`, `wip_config`); extended `SprintResponse` (adds `modo_trabalho`, `modo_avaliacao`, `hibrida`); extended `SprintStatusResponse` (adds `avaliados_count`, `elegiveis_avaliacao_count`). Tasks 3–8 all import from this file.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_modos_schemas_validation.py
"""Validação dos schemas Pydantic novos da Entrega 1 (Modos de Trabalho)."""
import pytest
from pydantic import ValidationError

from models.schemas import (
    ModosProjetoUpdate,
    ProjectResponse,
    SprintStatusResponse,
    WipConfigUpdate,
    PontuacaoEventoResponse,
)


def test_project_response_tem_defaults_de_modo():
    resp = ProjectResponse(
        id="p1", name="Projeto", client="CITi", created_at="2026-09-01T00:00:00Z",
    )
    assert resp.modo_trabalho == "ATRIBUICAO"
    assert resp.modo_avaliacao == "PONTOS_ATRIBUIDOS"
    assert resp.pull_exigir_hidratacao is True
    assert resp.pull_piso_pontos == 1
    assert resp.pull_teto == 1.5
    assert resp.wip_config is None


def test_modos_projeto_update_rejeita_modo_trabalho_invalido():
    with pytest.raises(ValidationError):
        ModosProjetoUpdate(modo_trabalho="PARALELO")


def test_modos_projeto_update_rejeita_piso_nao_positivo():
    with pytest.raises(ValidationError):
        ModosProjetoUpdate(pull_piso_pontos=0)


def test_wip_config_update_rejeita_por_pessoa_menor_que_1():
    with pytest.raises(ValidationError):
        WipConfigUpdate(por_pessoa=0)


def test_sprint_status_response_tem_contadores_de_avaliacao_default_zero():
    resp = SprintStatusResponse(
        id="s1", project_id="p1", numero=1,
        created_at="2026-09-01T00:00:00Z", updated_at="2026-09-01T00:00:00Z",
    )
    assert resp.avaliados_count == 0
    assert resp.elegiveis_avaliacao_count == 0


def test_pontuacao_evento_response_aceita_tipo_valido():
    ev = PontuacaoEventoResponse(
        id="e1", operacional_id="op-1", sprint_id="s1", projeto_id="p1",
        tipo="entrega_concluida", pontos=5, criado_em="2026-09-01T00:00:00Z",
    )
    assert ev.pontos == 5


def test_pontuacao_evento_response_rejeita_tipo_invalido():
    with pytest.raises(ValidationError):
        PontuacaoEventoResponse(
            id="e1", operacional_id="op-1", sprint_id="s1", projeto_id="p1",
            tipo="tipo_inventado", pontos=5, criado_em="2026-09-01T00:00:00Z",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && python -m pytest tests/test_modos_schemas_validation.py -v`
Expected: FAIL with `ImportError: cannot import name 'ModosProjetoUpdate'`

- [ ] **Step 3: Implement the schema additions**

In `docudata-backend/models/schemas.py`, add this block immediately **before** `class ProjectCreate(BaseModel):` (currently line 33):

```python
ModoTrabalho = Literal["ATRIBUICAO", "PULL"]
ModoAvaliacao = Literal["PONTOS_ATRIBUIDOS", "PONTOS_RELATIVO"]


class WipConfigResponse(BaseModel):
    por_pessoa: Optional[int] = None
    por_coluna_em_andamento: Optional[int] = None


```

Then in `class ProjectResponse(BaseModel):`, add these fields at the end of the class (after the existing `arquetipo: str = "padrao"` line):

```python
    modo_trabalho: ModoTrabalho = "ATRIBUICAO"
    modo_avaliacao: ModoAvaliacao = "PONTOS_ATRIBUIDOS"
    pull_exigir_hidratacao: bool = True
    pull_piso_pontos: float = 1
    pull_teto: float = 1.5
    wip_config: Optional[WipConfigResponse] = None
```

Then, still before `class ProjectSubareaUpdate(BaseModel):`, add:

```python
class ModosProjetoUpdate(BaseModel):
    """PATCH /projects/{id}/modos — RF-A1..A4. Todos os campos são opcionais;
    só o que vier preenchido é alterado (mesmo padrão de ContratoUpdate)."""
    modo_trabalho: Optional[ModoTrabalho] = None
    modo_avaliacao: Optional[ModoAvaliacao] = None
    pull_exigir_hidratacao: Optional[bool] = None
    pull_piso_pontos: Optional[float] = Field(default=None, gt=0)
    pull_teto: Optional[float] = Field(default=None, gt=0)


class ConfiguracaoHistoricoResponse(BaseModel):
    id: str
    project_id: str
    campo: Literal["modo_trabalho", "modo_avaliacao"]
    valor_anterior: Optional[str] = None
    valor_novo: str
    usuario_email: str
    criado_em: datetime


class WipConfigUpdate(BaseModel):
    """PATCH /projects/{id}/wip-config. Em projeto PULL, por_pessoa é
    ignorado e forçado a 1 no servidor (RF-A5) — nunca confiar no valor que o
    cliente mandou nesse modo."""
    por_pessoa: Optional[int] = Field(default=None, ge=1)
    por_coluna_em_andamento: Optional[int] = Field(default=None, ge=1)


class PontuacaoEventoResponse(BaseModel):
    id: str
    operacional_id: str
    sprint_id: str
    projeto_id: str
    task_id: Optional[str] = None
    tipo: Literal[
        "entrega_concluida", "travamento_penalidade", "devolucao_penalidade",
        "bonus_extra", "reabertura",
    ]
    pontos: int
    descricao: Optional[str] = None
    criado_em: datetime
```

Finally, in `class SprintResponse(BaseModel):`, add at the end (after `updated_at: datetime`):

```python
    modo_trabalho: Optional[str] = None
    modo_avaliacao: Optional[str] = None
    hibrida: bool = False
```

And in `class SprintStatusResponse(SprintResponse):`, add at the end (after `faturamento_previsto: Optional[float] = None`):

```python
    avaliados_count: int = 0
    elegiveis_avaliacao_count: int = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && python -m pytest tests/test_modos_schemas_validation.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Run the full existing schema-related suite to confirm no regression**

Run: `cd docudata-backend && python -m pytest tests/test_schemas_and_client.py -v`
Expected: PASS (same pass/fail count as before this change — this file is known to have 4 pre-existing unrelated failures per project memory; do not attempt to fix those)

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/tests/test_modos_schemas_validation.py
git commit -m "$(cat <<'EOF'
feat(schemas): adiciona modelos Pydantic da Entrega 1 de Modos de Trabalho

ModosProjetoUpdate, ConfiguracaoHistoricoResponse, WipConfigUpdate/Response,
PontuacaoEventoResponse; ProjectResponse/SprintResponse/SprintStatusResponse
ganham os campos novos com defaults que preservam o comportamento atual.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Motor de score — golden regression test + congela modo da sprint

**Files:**
- Modify: `docudata-backend/services/pontuacao.py`
- Modify: `docudata-backend/tests/test_pontuacao_fechamento.py`

**Interfaces:**
- Consumes: nothing new (this task only touches `calcular_e_travar_pontuacao`, already defined in this file).
- Produces: `calcular_e_travar_pontuacao` now writes `entrega_modo` on every row it inserts, and freezes `sprints.modo_trabalho`/`sprints.modo_avaliacao` at fechamento time. Task 4 (ledger events) builds on the same function, in the same file, immediately after this task.

This task is the highest-risk one in the plan (SDD risk §11: "regressão silenciosa no cálculo"). Follow the steps in order — the golden test in Step 1 is written and confirmed passing **against the current, unmodified code** before any implementation change.

- [ ] **Step 1: Write the golden regression test against the CURRENT code (before any implementation change)**

Add this test function to `docudata-backend/tests/test_pontuacao_fechamento.py`, anywhere after the existing `_AVALIACAO_OP1` constant near the top of the file:

```python
def test_golden_fixture_multidimensional_trava_de_regressao(monkeypatch):
    """Sprint de referência com dado fixo cobrindo as 5 dimensões numa
    passada só (entrega, qualidade, autonomia, gerente, bônus). Serve de
    trava de regressão para a spec de Modos de Trabalho e de Avaliação
    (docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md):
    depois que services/pontuacao.py ganhar os campos da Entrega 1, este
    teste tem que continuar passando com os MESMOS valores — prova que
    projeto em ATRIBUICAO + PONTOS_ATRIBUIDOS não muda de comportamento
    (SDD original, risco §11). Escrito e confirmado passando ANTES de
    qualquer mudança em calcular_e_travar_pontuacao."""
    insert_capture = []
    aval = {
        "operacional_id": "op-1",
        "resposta_1": 4, "resposta_2": 4, "resposta_3": 3, "resposta_4": 4,
        "resposta_5": 4, "resposta_6": 5, "resposta_7": 4,
    }
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            {
                "id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida",
                "bloqueado_resolvido_por": "operacional", "bloqueado_resolvido_em": "2026-09-01T00:00:00Z",
            },
            {"id": "task-2", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"},
            {"id": "task-3", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "concluida", "extra": True},
        ],
        task_transicoes=[
            {"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"},
            {"task_id": "task-3", "operacional_id": "op-1", "timestamp": "2026-09-03T00:00:00Z"},
        ],
        task_reaberturas=[{"operacional_id": "op-1"}],
        task_travamentos=[{"task_id": "task-1", "operacional_id": "op-1", "pontos": 5, "dispensado": False, "timestamp": "2026-09-01T12:00:00Z"}],
        avaliacoes=[aval],
        commit_qualidade=[{"operacional_id": "op-1", "nota": 8}, {"operacional_id": "op-1", "nota": 6}],
        insert_capture=insert_capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert len(resultado) == 1
    linha = resultado[0]
    assert linha["operacional_id"] == "op-1"
    assert linha["sprint_id"] == "sprint-1"
    assert linha["projeto_id"] == "proj-1"
    assert linha["gerente_media"] == 3.83
    assert linha["gerente_pergunta6"] == 5
    assert linha["gerente_pergunta3"] == 3
    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 8
    assert linha["entrega_pontos_penalizados"] == 5
    assert linha["bonus_pontos_extra"] == 2
    assert linha["qualidade_reaberturas"] == 1
    assert linha["qualidade_tasks_concluidas"] == 2
    assert linha["autonomia_bloqueios_resolvidos_proprio"] == 1
    assert linha["autonomia_bloqueios_totais"] == 1
    assert linha["qualidade_commit_media"] == 7.0
    assert linha["arquetipo"] is None
```

- [ ] **Step 2: Run this one test to confirm it PASSES against the unmodified code**

Run: `cd docudata-backend && python -m pytest tests/test_pontuacao_fechamento.py::test_golden_fixture_multidimensional_trava_de_regressao -v`
Expected: PASS. This locks in the baseline — do not proceed until it passes.

- [ ] **Step 3: Extend the shared mock helper, then write failing tests for the new behavior**

Replace the entire `_mock_client` function in `docudata-backend/tests/test_pontuacao_fechamento.py` (currently lines 14–214, from `def _mock_client(` through the `return client` that ends it) with this version — it adds two new optional parameters (`projeto`, `sprint_update_capture`) and extends the `sprints`/adds a `projects` branch; every other branch is unchanged:

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
):
    pontuacao_existente = pontuacao_existente or []
    cutoff_existente = cutoff_existente or []
    tasks = tasks or []
    task_transicoes = task_transicoes or []
    task_reaberturas = task_reaberturas or []
    task_travamentos = task_travamentos or []
    eventos_tardios = eventos_tardios or []
    avaliacoes = avaliacoes or []
    commit_qualidade = commit_qualidade or []
    insert_capture = insert_capture if insert_capture is not None else []
    projeto = projeto or {"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS"}
    sprint_update_capture = sprint_update_capture if sprint_update_capture is not None else []

    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()

        if name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                # Duas queries diferentes passam por aqui: a checagem de
                # idempotência (.eq("sprint_id", ...)) e a busca de cutoff
                # (.eq("projeto_id", ...).order(...).limit(...)) — distingue
                # pela presença de .order() na chain.
                q = MagicMock()
                state = {"order_called": False}

                def eq_effect(*a, **kw):
                    return q

                def order_effect(*a, **kw):
                    state["order_called"] = True
                    return q

                def limit_effect(*a, **kw):
                    return q

                def execute_effect():
                    resp = MagicMock()
                    resp.data = cutoff_existente if state["order_called"] else pontuacao_existente
                    return resp

                q.eq = MagicMock(side_effect=eq_effect)
                q.order = MagicMock(side_effect=order_effect)
                q.limit = MagicMock(side_effect=limit_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q

            def insert_side_effect(payload):
                insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(row, id=f"pont-{i}") for i, row in enumerate(payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)

        elif name == "sprints":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [sprint] if sprint else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                sprint_update_capture.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(sprint or {}, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)

        elif name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [projeto]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = tasks
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "task_transicoes":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = task_transicoes
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "task_reaberturas":
            def select_side_effect(cols):
                q = MagicMock()
                state = {"gt_timestamp": None}

                def in_effect(*a, **kw):
                    return q

                def gt_effect(field, value):
                    state["gt_timestamp"] = value
                    return q

                def execute_effect():
                    resp = MagicMock()
                    data = task_reaberturas
                    if state["gt_timestamp"] is not None:
                        data = [r for r in data if r.get("timestamp", "") > state["gt_timestamp"]]
                    resp.data = data
                    return resp

                q.in_ = MagicMock(side_effect=in_effect)
                q.gt = MagicMock(side_effect=gt_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "task_travamentos":
            def select_side_effect(cols):
                q = MagicMock()
                state = {"gt_timestamp": None, "dispensado": None, "task_ids": None}

                def in_effect(field, valores):
                    if field == "task_id":
                        state["task_ids"] = set(valores)
                    return q

                def eq_effect(field, value):
                    if field == "dispensado":
                        state["dispensado"] = value
                    return q

                def gt_effect(field, value):
                    state["gt_timestamp"] = value
                    return q

                def execute_effect():
                    resp = MagicMock()
                    data = task_travamentos
                    if state["task_ids"] is not None:
                        data = [r for r in data if r.get("task_id", "task-1") in state["task_ids"]]
                    if state["dispensado"] is not None:
                        data = [r for r in data if r.get("dispensado", False) == state["dispensado"]]
                    if state["gt_timestamp"] is not None:
                        data = [r for r in data if r.get("timestamp", "") > state["gt_timestamp"]]
                    resp.data = data
                    return resp

                q.in_ = MagicMock(side_effect=in_effect)
                q.eq = MagicMock(side_effect=eq_effect)
                q.gt = MagicMock(side_effect=gt_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "eventos_pontuacao_tardios":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = eventos_tardios
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        elif name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = avaliacoes
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        if name == "commit_qualidade":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.gt = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = commit_qualidade
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)

        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client
```

Then add these two new test functions after the golden test from Step 1:

```python
def test_congela_modo_trabalho_e_avaliacao_da_sprint_no_fechamento():
    sprint_update_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        projeto={"modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO"},
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        sprint_update_capture=sprint_update_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    assert sprint_update_capture == [{"modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO"}]


def test_entrega_modo_default_pontos_atribuidos_quando_projeto_nao_configurado():
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
    )

    linha = calcular_e_travar_pontuacao(client, "sprint-1")[0]

    assert linha["entrega_modo"] == "PONTOS_ATRIBUIDOS"
```

- [ ] **Step 4: Run to verify the two new tests fail, and the golden test + full suite still pass**

Run: `cd docudata-backend && python -m pytest tests/test_pontuacao_fechamento.py -v`
Expected: the two new tests FAIL (`KeyError: 'entrega_modo'` and empty `sprint_update_capture`); every other test (including the golden one) PASSES — the mock extension alone must not break anything.

- [ ] **Step 5: Implement the freeze + `entrega_modo` field in `services/pontuacao.py`**

In `docudata-backend/services/pontuacao.py`, find:

```python
    sprint_resp = client.table("sprints").select("id, project_id").eq("id", sprint_id).execute()
    if not sprint_resp.data:
        return []
    project_id = sprint_resp.data[0]["project_id"]
```

Replace it with:

```python
    sprint_resp = client.table("sprints").select("id, project_id").eq("id", sprint_id).execute()
    if not sprint_resp.data:
        return []
    project_id = sprint_resp.data[0]["project_id"]

    projeto_resp = client.table("projects").select("modo_trabalho, modo_avaliacao").eq("id", project_id).execute()
    projeto_row = projeto_resp.data[0] if projeto_resp.data else {}
    modo_trabalho = projeto_row.get("modo_trabalho") or "ATRIBUICAO"
    modo_avaliacao = projeto_row.get("modo_avaliacao") or "PONTOS_ATRIBUIDOS"

    # Congela o modo vigente na sprint no momento do fechamento (RF-E1) — os
    # dois períodos do experimento (ATRIBUICAO x PULL) precisam ficar
    # comparáveis mesmo que o projeto troque de modo depois.
    client.table("sprints").update({
        "modo_trabalho": modo_trabalho,
        "modo_avaliacao": modo_avaliacao,
    }).eq("id", sprint_id).execute()
```

Then find, inside the `linhas.append({...})` block:

```python
            "gerente_pergunta3": gerente_pergunta3,
            "entrega_pontos_concluidos": pontos_concluidos.get(operacional_id, 0),
```

Replace it with:

```python
            "gerente_pergunta3": gerente_pergunta3,
            "entrega_modo": modo_avaliacao,
            "entrega_pontos_concluidos": pontos_concluidos.get(operacional_id, 0),
```

- [ ] **Step 6: Run to verify all tests pass, including the golden regression test**

Run: `cd docudata-backend && python -m pytest tests/test_pontuacao_fechamento.py -v`
Expected: PASS, all tests including `test_golden_fixture_multidimensional_trava_de_regressao` with the exact same values as Step 2.

Run: `cd docudata-backend && python -m pytest tests/ -v -x --ignore=tests/test_schemas_and_client.py`
Expected: PASS (full suite, excluding the file with pre-existing unrelated failures documented in project memory).

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "$(cat <<'EOF'
feat(pontuacao): congela modo_trabalho/modo_avaliacao da sprint no fechamento

calcular_e_travar_pontuacao passa a consultar projects.modo_trabalho/
modo_avaliacao e gravar entrega_modo em cada linha + congelar os dois campos
em sprints (RF-E1). Golden regression test escrito e confirmado passando
ANTES da mudança, e confirmado passando de novo depois, com os mesmos
valores — zero mudança de comportamento para projetos em ATRIBUICAO +
PONTOS_ATRIBUIDOS (SDD original, risco §11).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Motor de score — extrato de pontos (ledger)

**Files:**
- Modify: `docudata-backend/services/pontuacao.py`
- Modify: `docudata-backend/tests/test_pontuacao_fechamento.py`

**Interfaces:**
- Consumes: `_mock_client` as extended by Task 3 (with `projeto`, `sprint_update_capture` params already in place).
- Produces: `calcular_e_travar_pontuacao` now also writes rows to `pontuacao_eventos` on every fechamento (`entrega_concluida`, `bonus_extra`, `travamento_penalidade`, `reabertura`). New private helpers `_eventos_travamento` and `_eventos_reabertura`. Task 8 (`GET /operacionais/{id}/extrato`) reads these rows back.

- [ ] **Step 1: Extend the mock again and write failing tests**

In `docudata-backend/tests/test_pontuacao_fechamento.py`, add a new parameter `eventos_insert_capture=None` to `_mock_client`'s signature (alongside `sprint_update_capture=None`), initialize it the same way (`eventos_insert_capture = eventos_insert_capture if eventos_insert_capture is not None else []`), and add a new `elif` branch right after the `elif name == "projects":` branch:

```python
        elif name == "pontuacao_eventos":
            def insert_side_effect(payload):
                eventos_insert_capture.extend(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(row, id=f"evt-{i}") for i, row in enumerate(payload)]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
```

Then add these test functions to the same file:

```python
def test_extrato_registra_entrega_concluida_e_bonus_extra():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[
            {"id": "task-1", "operacional_id": "op-1", "pontos": 5, "coluna_kanban": "concluida"},
            {"id": "task-2", "operacional_id": "op-1", "pontos": 2, "coluna_kanban": "concluida", "extra": True},
        ],
        task_transicoes=[
            {"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"},
            {"task_id": "task-2", "operacional_id": "op-1", "timestamp": "2026-09-03T00:00:00Z"},
        ],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    tipos = {(e["tipo"], e["task_id"], e["pontos"]) for e in eventos_insert_capture}
    assert ("entrega_concluida", "task-1", 5) in tipos
    assert ("bonus_extra", "task-2", 2) in tipos
    for evento in eventos_insert_capture:
        assert evento["sprint_id"] == "sprint-1"
        assert evento["projeto_id"] == "proj-1"
        assert evento["operacional_id"] == "op-1"


def test_extrato_registra_travamento_como_penalidade_negativa():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 8, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_travamentos=[{"task_id": "task-1", "operacional_id": "op-1", "pontos": 8, "dispensado": False, "timestamp": "2026-09-01T00:00:00Z"}],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    penalidades = [e for e in eventos_insert_capture if e["tipo"] == "travamento_penalidade"]
    assert len(penalidades) == 1
    assert penalidades[0]["pontos"] == -8
    assert penalidades[0]["task_id"] == "task-1"


def test_extrato_travamento_dispensado_nao_gera_evento():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 8, "coluna_kanban": "concluida"}],
        task_transicoes=[{"task_id": "task-1", "operacional_id": "op-1", "timestamp": "2026-09-02T00:00:00Z"}],
        task_travamentos=[{"task_id": "task-1", "operacional_id": "op-1", "pontos": 8, "dispensado": True, "timestamp": "2026-09-01T00:00:00Z"}],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    assert not any(e["tipo"] == "travamento_penalidade" for e in eventos_insert_capture)


def test_extrato_registra_reabertura_sem_pontos():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        task_reaberturas=[{"operacional_id": "op-1"}],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    reaberturas = [e for e in eventos_insert_capture if e["tipo"] == "reabertura"]
    assert len(reaberturas) == 1
    assert reaberturas[0]["pontos"] == 0


def test_extrato_nao_insere_nada_quando_nao_ha_eventos():
    eventos_insert_capture = []
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 3, "coluna_kanban": "em_andamento"}],
        eventos_insert_capture=eventos_insert_capture,
    )

    calcular_e_travar_pontuacao(client, "sprint-1")

    assert eventos_insert_capture == []
```

- [ ] **Step 2: Run to verify these tests fail**

Run: `cd docudata-backend && python -m pytest tests/test_pontuacao_fechamento.py -k extrato -v`
Expected: FAIL — `_mock_client() got an unexpected keyword argument 'eventos_insert_capture'` (fix the mock signature per Step 1 exactly as written first if this happens), then once the mock compiles, FAIL with `eventos_insert_capture == []` (nothing implemented yet).

- [ ] **Step 3: Implement the ledger in `services/pontuacao.py`**

Add these two new private functions right after `_somar_travamentos` (which ends with `return total`) and before `_calcular_qualidade_commit`:

```python
def _eventos_travamento(client, task_ids: list[str], cutoff: str | None = None) -> list[dict]:
    """Linhas cruas de travamento não dispensado, com task_id — usadas só
    pelo extrato de pontos (pontuacao_eventos). Consulta separada de
    _somar_travamentos para não alterar uma função já coberta pelo teste de
    regressão do motor de score."""
    if not task_ids:
        return []
    query = (
        client.table("task_travamentos")
        .select("task_id, operacional_id, pontos, timestamp")
        .in_("task_id", task_ids)
        .eq("dispensado", False)
    )
    if cutoff is not None:
        query = query.gt("timestamp", cutoff)
    return query.execute().data or []


def _eventos_reabertura(client, task_ids: list[str], cutoff: str | None = None) -> list[dict]:
    """Espelha _contar_reaberturas preservando task_id, para o extrato de
    pontos."""
    if not task_ids:
        return []
    query = (
        client.table("task_reaberturas")
        .select("task_id, operacional_id, timestamp")
        .in_("task_id", task_ids)
    )
    if cutoff is not None:
        query = query.gt("timestamp", cutoff)
    return query.execute().data or []
```

Now find the main loop in `calcular_e_travar_pontuacao`:

```python
    for task in tasks:
        pontos = task.get("pontos") or 0
        concluida = task.get("coluna_kanban") == "concluida"

        # Task extra (pedida pelo operacional depois de fechar tudo que tinha)
        # não entra em Entrega: ela não consumiu orçamento da sprint e entrar no
        # denominador puniria quem pediu mais trabalho. Vira bônus, só se
        # concluída dentro da sprint.
        if task.get("extra"):
            if concluida:
                operacional_id = quem_completou.get(task["id"]) or task.get("operacional_id")
                if operacional_id:
                    bonus_extra[operacional_id] = bonus_extra.get(operacional_id, 0) + pontos
                    tasks_concluidas[operacional_id] = tasks_concluidas.get(operacional_id, 0) + 1
        elif concluida:
            operacional_id = quem_completou.get(task["id"]) or task.get("operacional_id")
            if operacional_id:
                pontos_concluidos[operacional_id] = pontos_concluidos.get(operacional_id, 0) + pontos
                pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos
                tasks_concluidas[operacional_id] = tasks_concluidas.get(operacional_id, 0) + 1
        else:
            operacional_id = task.get("operacional_id")
            if operacional_id:
                pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos
```

Replace it with (adds `eventos = []` before the loop and two `.append` calls inside it — every other line is unchanged):

```python
    eventos: list[dict] = []

    for task in tasks:
        pontos = task.get("pontos") or 0
        concluida = task.get("coluna_kanban") == "concluida"

        # Task extra (pedida pelo operacional depois de fechar tudo que tinha)
        # não entra em Entrega: ela não consumiu orçamento da sprint e entrar no
        # denominador puniria quem pediu mais trabalho. Vira bônus, só se
        # concluída dentro da sprint.
        if task.get("extra"):
            if concluida:
                operacional_id = quem_completou.get(task["id"]) or task.get("operacional_id")
                if operacional_id:
                    bonus_extra[operacional_id] = bonus_extra.get(operacional_id, 0) + pontos
                    tasks_concluidas[operacional_id] = tasks_concluidas.get(operacional_id, 0) + 1
                    eventos.append({
                        "operacional_id": operacional_id, "task_id": task["id"],
                        "tipo": "bonus_extra", "pontos": pontos,
                        "descricao": "Task extra concluída",
                    })
        elif concluida:
            operacional_id = quem_completou.get(task["id"]) or task.get("operacional_id")
            if operacional_id:
                pontos_concluidos[operacional_id] = pontos_concluidos.get(operacional_id, 0) + pontos
                pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos
                tasks_concluidas[operacional_id] = tasks_concluidas.get(operacional_id, 0) + 1
                eventos.append({
                    "operacional_id": operacional_id, "task_id": task["id"],
                    "tipo": "entrega_concluida", "pontos": pontos,
                    "descricao": "Task concluída",
                })
        else:
            operacional_id = task.get("operacional_id")
            if operacional_id:
                pontos_alocados[operacional_id] = pontos_alocados.get(operacional_id, 0) + pontos
```

Now find:

```python
    reaberturas = _contar_reaberturas(client, [t["id"] for t in tasks], cutoff)
    qualidade_commit = _calcular_qualidade_commit(client, project_id, cutoff)
    # A penalidade de atraso só faz sentido em task que foi entregue depois do
    # alerta: se ela nunca foi concluída, os pontos dela já não estão nos
    # concluídos, e descontar de novo puniria as OUTRAS entregas da pessoa.
    pontos_penalizados = _somar_travamentos(client, task_ids_concluidas, cutoff)
```

Replace it with (adds two loops right after, building the remaining ledger events):

```python
    reaberturas = _contar_reaberturas(client, [t["id"] for t in tasks], cutoff)
    qualidade_commit = _calcular_qualidade_commit(client, project_id, cutoff)
    # A penalidade de atraso só faz sentido em task que foi entregue depois do
    # alerta: se ela nunca foi concluída, os pontos dela já não estão nos
    # concluídos, e descontar de novo puniria as OUTRAS entregas da pessoa.
    pontos_penalizados = _somar_travamentos(client, task_ids_concluidas, cutoff)

    for row in _eventos_travamento(client, task_ids_concluidas, cutoff):
        op = row.get("operacional_id")
        if op:
            eventos.append({
                "operacional_id": op, "task_id": row.get("task_id"),
                "tipo": "travamento_penalidade", "pontos": -(row.get("pontos") or 0),
                "descricao": "Travamento automático não dispensado",
            })

    for row in _eventos_reabertura(client, [t["id"] for t in tasks], cutoff):
        op = row.get("operacional_id")
        if op:
            eventos.append({
                "operacional_id": op, "task_id": row.get("task_id"),
                "tipo": "reabertura", "pontos": 0,
                "descricao": "Reabertura registrada",
            })
```

Finally, find the end of the function:

```python
    resp = client.table("pontuacao_operacional_sprint").insert(linhas).execute()
    return resp.data or []
```

Replace it with:

```python
    resp = client.table("pontuacao_operacional_sprint").insert(linhas).execute()

    if eventos:
        client.table("pontuacao_eventos").insert([
            {
                "operacional_id": e["operacional_id"],
                "sprint_id": sprint_id,
                "projeto_id": project_id,
                "task_id": e.get("task_id"),
                "tipo": e["tipo"],
                "pontos": e["pontos"],
                "descricao": e.get("descricao"),
            }
            for e in eventos
        ]).execute()

    return resp.data or []
```

- [ ] **Step 4: Run to verify all tests pass**

Run: `cd docudata-backend && python -m pytest tests/test_pontuacao_fechamento.py -v`
Expected: PASS, every test in the file, including the golden regression test from Task 3 (still with the exact same values).

- [ ] **Step 5: Run the full backend suite**

Run: `cd docudata-backend && python -m pytest tests/ -v --ignore=tests/test_schemas_and_client.py`
Expected: PASS, no regressions anywhere else.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "$(cat <<'EOF'
feat(pontuacao): grava extrato auditável de pontos no fechamento (pontuacao_eventos)

calcular_e_travar_pontuacao agora escreve uma linha por fato de pontuação —
entrega concluída, bônus extra, travamento não dispensado, reabertura — no
mesmo fechamento que já grava os agregados. Extra do usuário: log claro de
todo ponto ganho ou descontado por operacional.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `services/avaliacoes.py` — contador de avaliação semanal por sprint

**Files:**
- Create: `docudata-backend/services/avaliacoes.py`
- Test: `docudata-backend/tests/test_avaliacao_contagem_sprint.py`

**Interfaces:**
- Produces: `contar_avaliacao_por_sprint(client, sprint_ids: list[str]) -> dict[str, dict]` — for each sprint id, `{"elegiveis": int, "avaliados": int}`. Task 6 (`routers/sprints.py`) consumes this directly.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_avaliacao_contagem_sprint.py
"""Testes para services/avaliacoes.py::contar_avaliacao_por_sprint.

Extra do usuário (não faz parte do SDD original): contador "N/M" de
avaliação semanal por sprint. Reusa a MESMA derivação de hoje (operacional
com task na sprint) usada por routers/avaliacoes.py — não a elegibilidade
temporal nova da Entrega 2. Ver spec §3 "Entrega 1"."""
from unittest.mock import MagicMock

from services.avaliacoes import contar_avaliacao_por_sprint


def _mock_client(tasks=None, avaliacoes=None):
    tasks = tasks or []
    avaliacoes = avaliacoes or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = tasks
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = avaliacoes
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def test_conta_elegiveis_e_avaliados_por_sprint():
    client = _mock_client(
        tasks=[
            {"sprint_id": "sprint-1", "operacional_id": "op-1"},
            {"sprint_id": "sprint-1", "operacional_id": "op-2"},
            {"sprint_id": "sprint-2", "operacional_id": "op-3"},
        ],
        avaliacoes=[
            {"sprint_id": "sprint-1", "operacional_id": "op-1"},
        ],
    )

    resultado = contar_avaliacao_por_sprint(client, ["sprint-1", "sprint-2"])

    assert resultado["sprint-1"] == {"elegiveis": 2, "avaliados": 1}
    assert resultado["sprint-2"] == {"elegiveis": 1, "avaliados": 0}


def test_sprint_sem_task_fica_zero_a_zero():
    client = _mock_client(tasks=[], avaliacoes=[])

    resultado = contar_avaliacao_por_sprint(client, ["sprint-1"])

    assert resultado["sprint-1"] == {"elegiveis": 0, "avaliados": 0}


def test_lista_vazia_de_sprints_retorna_dict_vazio():
    client = _mock_client()
    assert contar_avaliacao_por_sprint(client, []) == {}


def test_avaliacao_orfa_nao_conta_se_pessoa_nao_tem_mais_task():
    """Se alguém foi avaliado mas não tem mais task na sprint (dado
    inconsistente/legado), não pode fazer avaliados > elegíveis."""
    client = _mock_client(
        tasks=[{"sprint_id": "sprint-1", "operacional_id": "op-1"}],
        avaliacoes=[
            {"sprint_id": "sprint-1", "operacional_id": "op-1"},
            {"sprint_id": "sprint-1", "operacional_id": "op-orfao"},
        ],
    )

    resultado = contar_avaliacao_por_sprint(client, ["sprint-1"])

    assert resultado["sprint-1"] == {"elegiveis": 1, "avaliados": 1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && python -m pytest tests/test_avaliacao_contagem_sprint.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.avaliacoes'`

- [ ] **Step 3: Implement**

```python
# docudata-backend/services/avaliacoes.py
"""Contagem de elegibilidade e avaliação semanal por sprint (Entrega 1 —
extra do usuário: contador "N/M" no card da sprint).

Reusa a MESMA derivação de hoje (operacional com task na sprint) usada por
routers/avaliacoes.py::_operacionais_com_task_na_sprint — não a elegibilidade
temporal nova da Entrega 2 (entrada/saída no projeto). Trocar a derivação
aqui mudaria quem "conta como pendente" em projetos ATRIBUICAO hoje, o que
violaria a promessa de zero mudança de comportamento desta entrega. Ver
docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md §3."""


def contar_avaliacao_por_sprint(client, sprint_ids: list[str]) -> dict[str, dict]:
    """Para cada sprint_id, quantos operacionais têm task nela (elegíveis) e
    quantos desses já têm avaliacoes_gerente registrada (avaliados). Uma
    consulta batelada — evita N chamadas quando o chamador lista várias
    sprints de uma vez (GET /projects/{id}/sprints)."""
    if not sprint_ids:
        return {}

    tasks_resp = (
        client.table("tasks").select("sprint_id, operacional_id").in_("sprint_id", sprint_ids).execute()
    )
    elegiveis_por_sprint: dict[str, set[str]] = {sid: set() for sid in sprint_ids}
    for row in (tasks_resp.data or []):
        sid = row.get("sprint_id")
        op = row.get("operacional_id")
        if sid in elegiveis_por_sprint and op:
            elegiveis_por_sprint[sid].add(op)

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
            "elegiveis": len(elegiveis_por_sprint[sid]),
            # Só conta quem ainda é elegível — evita avaliados > elegiveis se
            # um dado antigo ficou órfão (avaliação de alguém que não tem
            # mais task na sprint).
            "avaliados": len(avaliados_por_sprint[sid] & elegiveis_por_sprint[sid]),
        }
        for sid in sprint_ids
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && python -m pytest tests/test_avaliacao_contagem_sprint.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/avaliacoes.py docudata-backend/tests/test_avaliacao_contagem_sprint.py
git commit -m "$(cat <<'EOF'
feat(avaliacoes): contador batelado de elegiveis/avaliados por sprint

services/avaliacoes.py::contar_avaliacao_por_sprint — base do contador
"N/M" de avaliação semanal no card da sprint (extra do usuário). Reusa a
derivação atual por task, não a elegibilidade temporal da Entrega 2.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `routers/sprints.py` — expõe avaliados_count/elegiveis_avaliacao_count

**Files:**
- Modify: `docudata-backend/routers/sprints.py`
- Create: `docudata-backend/tests/test_sprints_avaliacao_contador.py`

**Interfaces:**
- Consumes: `contar_avaliacao_por_sprint` from Task 5.
- Produces: `GET /projects/{project_id}/sprints` response items gain `avaliados_count`/`elegiveis_avaliacao_count`. Task 11 (frontend) consumes these two fields.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_sprints_avaliacao_contador.py
"""Testes para avaliados_count/elegiveis_avaliacao_count em
GET /projects/{id}/sprints (Entrega 1, extra do usuário: contador "N/M" de
avaliação semanal)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_mock_client(sprints_data=None, tasks_data=None, avaliacoes_data=None):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [{"id": "proj-1", "valor_por_ponto": None}]
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
        elif name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(tasks_data) if tasks_data is not None else []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name in ("ingestions", "generated_docs"):
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = []
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "avaliacoes_gerente":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = list(avaliacoes_data) if avaliacoes_data is not None else []
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


_SPRINT_ROW = {
    "id": "sprint-1", "project_id": "proj-1", "numero": 1,
    "created_at": "2026-09-06T00:00:00+00:00", "updated_at": "2026-09-06T00:00:00+00:00",
}


def test_contador_avaliacao_reflete_elegiveis_e_avaliados(monkeypatch):
    mock_sb = _make_mock_client(
        sprints_data=[_SPRINT_ROW],
        tasks_data=[
            {"sprint_id": "sprint-1", "pontos": 5, "operacional_id": "op-1"},
            {"sprint_id": "sprint-1", "pontos": 3, "operacional_id": "op-2"},
        ],
        avaliacoes_data=[{"sprint_id": "sprint-1", "operacional_id": "op-1"}],
    )
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    data = resp.json()[0]
    assert data["elegiveis_avaliacao_count"] == 2
    assert data["avaliados_count"] == 1


def test_contador_zero_a_zero_sem_ninguem_com_task(monkeypatch):
    mock_sb = _make_mock_client(sprints_data=[_SPRINT_ROW], tasks_data=[], avaliacoes_data=[])
    tc = _patch_and_client(monkeypatch, mock_sb)

    resp = tc.get("/projects/proj-1/sprints")

    assert resp.status_code == 200
    data = resp.json()[0]
    assert data["elegiveis_avaliacao_count"] == 0
    assert data["avaliados_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && python -m pytest tests/test_sprints_avaliacao_contador.py -v`
Expected: FAIL — `KeyError: 'elegiveis_avaliacao_count'` (field not returned yet).

- [ ] **Step 3: Implement**

In `docudata-backend/routers/sprints.py`, add this import alongside the existing ones near the top of the file (after `from services.sprints import iniciar_sprint_e_ancorar_tasks`):

```python
from services.avaliacoes import contar_avaliacao_por_sprint
```

Then, inside `list_sprints`, find:

```python
    docs_resp = (
        client.table("generated_docs")
        .select("sprint_number")
        .eq("project_id", project_id)
        .execute()
    )
```

Replace it with (adds the new batched call right after, using the sprint ids already fetched into `sprints`):

```python
    docs_resp = (
        client.table("generated_docs")
        .select("sprint_number")
        .eq("project_id", project_id)
        .execute()
    )

    contagem_avaliacao = contar_avaliacao_por_sprint(client, [s["id"] for s in sprints])
```

Then, inside the `enriched.append({...})` block, find:

```python
            "pendencias": pendencias,
            "pontos_usados": pontos_usados_por_sprint.get(sprint["id"], 0),
```

Replace it with:

```python
            "pendencias": pendencias,
            "avaliados_count": contagem_avaliacao.get(sprint["id"], {}).get("avaliados", 0),
            "elegiveis_avaliacao_count": contagem_avaliacao.get(sprint["id"], {}).get("elegiveis", 0),
            "pontos_usados": pontos_usados_por_sprint.get(sprint["id"], 0),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && python -m pytest tests/test_sprints_avaliacao_contador.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full sprints test suite to confirm no regression**

Run: `cd docudata-backend && python -m pytest tests/test_sprints_orcamento_derivado.py tests/test_iniciar_sprint_ancora_tasks.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/routers/sprints.py docudata-backend/tests/test_sprints_avaliacao_contador.py
git commit -m "$(cat <<'EOF'
feat(sprints): expõe avaliados_count/elegiveis_avaliacao_count na listagem

GET /projects/{id}/sprints ganha o contador "N/M" de avaliação semanal por
sprint, base do chip novo no SprintCard (extra do usuário).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `routers/projects.py` — PATCH /modos, GET /modos-historico, PATCH /wip-config

**Files:**
- Modify: `docudata-backend/routers/projects.py`
- Create: `docudata-backend/tests/test_project_modos.py`

**Interfaces:**
- Consumes: `ModosProjetoUpdate`, `ConfiguracaoHistoricoResponse`, `WipConfigUpdate` from Task 2.
- Produces: `PATCH /projects/{id}/modos`, `GET /projects/{id}/modos-historico`, `PATCH /projects/{id}/wip-config`. Task 12 and Task 13 (frontend) call these three endpoints.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_project_modos.py
"""Testes para PATCH /projects/{id}/modos, GET /projects/{id}/modos-historico
e PATCH /projects/{id}/wip-config (Entrega 1 de Modos de Trabalho e de
Avaliação)."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


_PROJETO_BASE = {
    "id": "proj-1", "name": "Projeto Teste", "client": "CITi", "subarea": "dados",
    "description": None, "squad": None, "valor_projeto": None, "valor_por_ponto": None,
    "is_delivered": False, "created_at": "2026-09-01T00:00:00+00:00",
    "data_inicio": None, "data_fim_contratada": None, "tolerancia_desvio_pontos": None,
    "periodo_garantia_dias": None, "gerente_email": None, "arquetipo": "padrao",
    "github_token": None, "github_repo": None,
    "modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS",
    "pull_exigir_hidratacao": True, "pull_piso_pontos": 1, "pull_teto": 1.5,
    "wip_config": None,
}


def _mock_client(projeto, historico_insert_capture=None):
    estado = dict(projeto) if projeto is not None else None
    historico_insert_capture = historico_insert_capture if historico_insert_capture is not None else []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(estado)] if estado is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                if estado is not None:
                    estado.update(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(estado)] if estado is not None else []
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "configuracao_historico":
            def insert_side_effect(payload):
                historico_insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(payload, id=f"hist-{len(historico_insert_capture)}", criado_em="2026-09-20T00:00:00Z")]
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.insert = MagicMock(side_effect=insert_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client, estado


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto=_PROJETO_BASE, historico_insert_capture=None, cargo="gerente"):
        import routers.projects as projects_router
        from main import app
        mock_sb, estado = _mock_client(projeto, historico_insert_capture)
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc, estado
    return _make


def test_patch_modos_troca_modo_trabalho_e_grava_historico(make_client):
    historico = []
    tc, estado = make_client(historico_insert_capture=historico)

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 200
    assert resp.json()["modo_trabalho"] == "PULL"
    assert historico == [{
        "project_id": "proj-1", "campo": "modo_trabalho",
        "valor_anterior": "ATRIBUICAO", "valor_novo": "PULL",
        "usuario_email": "pessoa@citi.org.br",
    }]


def test_patch_modos_forca_wip_por_pessoa_1_ao_entrar_em_pull(make_client):
    tc, estado = make_client(projeto={**_PROJETO_BASE, "wip_config": {"por_coluna_em_andamento": 8}})

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 200
    assert resp.json()["wip_config"] == {"por_coluna_em_andamento": 8, "por_pessoa": 1}


def test_patch_modos_sem_mudanca_nao_grava_historico(make_client):
    historico = []
    tc, estado = make_client(historico_insert_capture=historico)

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "ATRIBUICAO"})

    assert resp.status_code == 200
    assert historico == []


def test_patch_modos_bloqueia_operacional(make_client):
    tc, estado = make_client(cargo="operacional")

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 403


def test_patch_modos_projeto_inexistente_404(make_client):
    tc, estado = make_client(projeto=None)

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PULL"})

    assert resp.status_code == 404


def test_patch_modos_rejeita_valor_fora_do_enum(make_client):
    tc, estado = make_client()

    resp = tc.patch("/projects/proj-1/modos", json={"modo_trabalho": "PARALELO"})

    assert resp.status_code == 422


def test_patch_modos_rejeita_piso_nao_positivo(make_client):
    tc, estado = make_client()

    resp = tc.patch("/projects/proj-1/modos", json={"pull_piso_pontos": 0})

    assert resp.status_code == 422


def test_get_modos_historico_lista_registros(make_client, monkeypatch):
    tc, estado = make_client()
    import routers.projects as projects_router

    registros = [{"id": "h1", "project_id": "proj-1", "campo": "modo_trabalho",
                  "valor_anterior": "ATRIBUICAO", "valor_novo": "PULL",
                  "usuario_email": "g@citi.com", "criado_em": "2026-09-20T00:00:00Z"}]

    mock_sb = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "configuracao_historico":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = registros
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    mock_sb.table = MagicMock(side_effect=table_side_effect)
    monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)

    resp = tc.get("/projects/proj-1/modos-historico")

    assert resp.status_code == 200
    assert resp.json() == registros


def test_patch_wip_config_forca_por_pessoa_1_em_pull(make_client):
    tc, estado = make_client(projeto={**_PROJETO_BASE, "modo_trabalho": "PULL", "wip_config": None})

    resp = tc.patch("/projects/proj-1/wip-config", json={"por_pessoa": 3})

    assert resp.status_code == 200
    assert resp.json()["wip_config"] == {"por_pessoa": 1}


def test_patch_wip_config_edita_livre_em_atribuicao(make_client):
    tc, estado = make_client()

    resp = tc.patch("/projects/proj-1/wip-config", json={"por_pessoa": 3, "por_coluna_em_andamento": 10})

    assert resp.status_code == 200
    assert resp.json()["wip_config"] == {"por_pessoa": 3, "por_coluna_em_andamento": 10}


def test_patch_wip_config_bloqueia_operacional(make_client):
    tc, estado = make_client(cargo="operacional")

    resp = tc.patch("/projects/proj-1/wip-config", json={"por_pessoa": 2})

    assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && python -m pytest tests/test_project_modos.py -v`
Expected: FAIL with 404/405 for all routes (endpoints don't exist yet).

- [ ] **Step 3: Implement**

In `docudata-backend/routers/projects.py`, extend the import block at the top:

```python
from models.schemas import (
    ProjectCreate,
    ProjectResponse,
    TechTimelineResponse,
    ContratoUpdate,
    GerenteEmailUpdate,
    ProjectSubareaUpdate,
    ModosProjetoUpdate,
    ConfiguracaoHistoricoResponse,
    WipConfigUpdate,
)
```

Extend `_CAMPOS_PROJETO`:

```python
_CAMPOS_PROJETO = (
    "id, name, client, subarea, description, squad, valor_projeto, valor_por_ponto, "
    "is_delivered, created_at, data_inicio, data_fim_contratada, "
    "tolerancia_desvio_pontos, periodo_garantia_dias, gerente_email, arquetipo, "
    "github_token, github_repo, "
    "modo_trabalho, modo_avaliacao, pull_exigir_hidratacao, pull_piso_pontos, pull_teto, wip_config"
)
```

Add these three endpoints at the end of the file:

```python
@router.patch("/{project_id}/modos", response_model=ProjectResponse)
async def update_modos(
    project_id: str,
    data: ModosProjetoUpdate,
    pessoa: dict = Depends(require_not_operacional),
):
    """RF-A1..A4/A6: troca modo de trabalho e/ou modo de avaliação do
    projeto, com parâmetros de PULL. Toda mudança de modo_trabalho ou
    modo_avaliacao grava um registro imutável em configuracao_historico."""
    client = get_client()
    atual_resp = client.table("projects").select(
        "modo_trabalho, modo_avaliacao"
    ).eq("id", project_id).execute()
    if not atual_resp.data:
        raise HTTPException(status_code=404, detail="Project not found")
    atual = atual_resp.data[0]

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

    response = client.table("projects").update(payload).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update project modos")

    # RF-A5: entrar em PULL força WIP por pessoa = 1, mesmo que o gerente não
    # tenha mexido no campo agora — sem isso um projeto migrado ficaria em
    # modo pull com WIP de atribuição, incoerente com a regra do modo.
    if payload.get("modo_trabalho") == "PULL":
        wip_atual = response.data[0].get("wip_config") or {}
        novo_wip = {**wip_atual, "por_pessoa": 1}
        response = client.table("projects").update({"wip_config": novo_wip}).eq("id", project_id).execute()

    return _sanitize(response.data[0])


@router.get("/{project_id}/modos-historico", response_model=list[ConfiguracaoHistoricoResponse])
async def get_modos_historico(project_id: str, _pessoa: dict = Depends(require_not_operacional)):
    client = get_client()
    resp = (
        client.table("configuracao_historico")
        .select("*")
        .eq("project_id", project_id)
        .order("criado_em", desc=True)
        .execute()
    )
    return resp.data or []


@router.patch("/{project_id}/wip-config", response_model=ProjectResponse)
async def update_wip_config(
    project_id: str,
    data: WipConfigUpdate,
    _pessoa: dict = Depends(require_not_operacional),
):
    """Atualiza projects.wip_config. Em projeto PULL, por_pessoa é sempre
    forçado a 1 no servidor (RF-A5) — o valor que o cliente mandar para esse
    campo é ignorado nesse modo, nunca confiado."""
    client = get_client()
    check = client.table("projects").select("modo_trabalho, wip_config").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")
    projeto = check.data[0]

    wip_atual = projeto.get("wip_config") or {}
    novo_wip = dict(wip_atual)
    if data.por_coluna_em_andamento is not None:
        novo_wip["por_coluna_em_andamento"] = data.por_coluna_em_andamento
    if data.por_pessoa is not None:
        novo_wip["por_pessoa"] = data.por_pessoa
    if projeto.get("modo_trabalho") == "PULL":
        novo_wip["por_pessoa"] = 1

    response = client.table("projects").update({"wip_config": novo_wip}).eq("id", project_id).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update wip_config")
    return _sanitize(response.data[0])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && python -m pytest tests/test_project_modos.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Run the full projects test suite to confirm no regression**

Run: `cd docudata-backend && python -m pytest tests/test_project_subarea.py tests/test_contrato_arquetipo.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/routers/projects.py docudata-backend/tests/test_project_modos.py
git commit -m "$(cat <<'EOF'
feat(projects): PATCH /modos, GET /modos-historico, PATCH /wip-config

RF-A1..A6: troca de modo de trabalho/avaliação com histórico imutável de
mudanças, e configuração de WIP por pessoa/coluna forçando por_pessoa=1
sempre que o projeto está em modo PULL (RF-A5).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `routers/pontuacao.py` — GET /operacionais/{id}/extrato

**Files:**
- Modify: `docudata-backend/services/pontuacao.py`
- Modify: `docudata-backend/routers/pontuacao.py`
- Create: `docudata-backend/tests/test_extrato_pontos.py`

**Interfaces:**
- Consumes: `pontuacao_eventos` rows written by Task 4; `PontuacaoEventoResponse` from Task 2.
- Produces: `GET /operacionais/{id}/extrato?sprint_id=` (Gerente/Líder/Owner only). Task 13 (frontend `PainelTab`) consumes this endpoint.

- [ ] **Step 1: Write the failing test**

```python
# docudata-backend/tests/test_extrato_pontos.py
"""Testes para GET /operacionais/{id}/extrato (extra do usuário: log claro
de todo ponto ganho ou descontado, Gerente/Líder apenas)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _mock_client(eventos=None):
    eventos = eventos or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pontuacao_eventos":
            def select_side_effect(cols):
                q = MagicMock()
                state = {"sprint_id": None}

                def eq_effect(field, value):
                    if field == "sprint_id":
                        state["sprint_id"] = value
                    return q

                def order_effect(*a, **kw):
                    return q

                def execute_effect():
                    resp = MagicMock()
                    data = eventos
                    if state["sprint_id"] is not None:
                        data = [e for e in data if e.get("sprint_id") == state["sprint_id"]]
                    resp.data = data
                    return resp

                q.eq = MagicMock(side_effect=eq_effect)
                q.order = MagicMock(side_effect=order_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_and_client(monkeypatch, mock_supabase, autenticar, cargo="gerente"):
    import routers.pontuacao as pontuacao_router
    from main import app
    monkeypatch.setattr(pontuacao_router, "get_client", lambda: mock_supabase)
    return autenticar(TestClient(app), cargo=cargo)


_EVENTOS = [
    {"id": "ev-1", "operacional_id": "op-1", "sprint_id": "sprint-1", "projeto_id": "proj-1",
     "task_id": "task-1", "tipo": "entrega_concluida", "pontos": 5, "descricao": "Task concluída",
     "criado_em": "2026-09-10T00:00:00Z"},
    {"id": "ev-2", "operacional_id": "op-1", "sprint_id": "sprint-2", "projeto_id": "proj-1",
     "task_id": "task-2", "tipo": "travamento_penalidade", "pontos": -3, "descricao": "Travamento não dispensado",
     "criado_em": "2026-09-17T00:00:00Z"},
]


def test_extrato_lista_todos_os_eventos_do_operacional(monkeypatch, autenticar):
    tc = _patch_and_client(monkeypatch, _mock_client(_EVENTOS), autenticar)

    resp = tc.get("/operacionais/op-1/extrato")

    assert resp.status_code == 200
    tipos = {e["tipo"] for e in resp.json()}
    assert tipos == {"entrega_concluida", "travamento_penalidade"}


def test_extrato_filtra_por_sprint(monkeypatch, autenticar):
    tc = _patch_and_client(monkeypatch, _mock_client(_EVENTOS), autenticar)

    resp = tc.get("/operacionais/op-1/extrato?sprint_id=sprint-2")

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["tipo"] == "travamento_penalidade"


def test_extrato_bloqueia_operacional(monkeypatch, autenticar):
    tc = _patch_and_client(monkeypatch, _mock_client(_EVENTOS), autenticar, cargo="operacional")

    resp = tc.get("/operacionais/op-1/extrato")

    assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && python -m pytest tests/test_extrato_pontos.py -v`
Expected: FAIL with 404 (route doesn't exist).

- [ ] **Step 3: Implement**

In `docudata-backend/services/pontuacao.py`, add this function at the end of the file:

```python
def listar_extrato_pontos(client, operacional_id: str, sprint_id: str | None = None) -> list[dict]:
    """Extrato auditável de todo ponto ganho/descontado (extra do usuário —
    não faz parte do SDD original). RBAC (Gerente/Líder apenas) é do router,
    não desta função."""
    query = (
        client.table("pontuacao_eventos")
        .select("*")
        .eq("operacional_id", operacional_id)
    )
    if sprint_id:
        query = query.eq("sprint_id", sprint_id)
    resp = query.order("criado_em", desc=True).execute()
    return resp.data or []
```

In `docudata-backend/routers/pontuacao.py`, find the module docstring and imports at the very top of the file:

```python
"""Router do Motor de Score: SPI do operacional, evolução e baseline.

Acesso: o ranking e o score final continuam exclusivos do Líder
(routers/performance.py). SPI travado e Evolução por operacional foram abertos
ao Gerente em 2026-09-07 (decisão do Líder) para sustentar a conversa de
feedback — Operacional segue sem acesso a nenhum payload de score."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    BaselineEvolucaoCreate,
    BaselineEvolucaoResponse,
    SpiEvolucaoOperacionalResponse,
    SpiOperacionalResponse,
)
from services.auth import require_not_operacional, require_role
from services.pontuacao import calcular_spi_operacional, listar_spi_evolucao_do_projeto
from services.supabase_client import get_client
```

Replace it with:

```python
"""Router do Motor de Score: SPI do operacional, evolução e baseline.

Acesso: o ranking e o score final continuam exclusivos do Líder
(routers/performance.py). SPI travado e Evolução por operacional foram abertos
ao Gerente em 2026-09-07 (decisão do Líder) para sustentar a conversa de
feedback — Operacional segue sem acesso a nenhum payload de score.

O extrato de pontos (GET /operacionais/{id}/extrato) é extra do usuário —
não faz parte do SDD de Modos de Trabalho e de Avaliação — e segue a mesma
regra de acesso: Gerente e Líder, nunca Operacional."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import (
    BaselineEvolucaoCreate,
    BaselineEvolucaoResponse,
    PontuacaoEventoResponse,
    SpiEvolucaoOperacionalResponse,
    SpiOperacionalResponse,
)
from services.auth import require_not_operacional, require_role
from services.pontuacao import calcular_spi_operacional, listar_extrato_pontos, listar_spi_evolucao_do_projeto
from services.supabase_client import get_client
```

Then add this endpoint at the end of the file:

```python
@router.get(
    "/operacionais/{operacional_id}/extrato",
    response_model=list[PontuacaoEventoResponse],
    dependencies=[Depends(require_not_operacional)],
)
async def get_extrato_pontos(operacional_id: str, sprint_id: Optional[str] = None):
    """Extrato de todo ponto ganho ou descontado do operacional (extra do
    usuário). Gerente e Líder apenas."""
    client = get_client()
    return listar_extrato_pontos(client, operacional_id, sprint_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-backend && python -m pytest tests/test_extrato_pontos.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full backend suite (Onda 1 exit gate)**

Run: `cd docudata-backend && python -m pytest tests/ -v --ignore=tests/test_schemas_and_client.py`
Expected: PASS — every test in the suite, no regressions. This is the gate: do not start Task 9 (frontend) until this is fully green.

Run: `cd docudata-backend && python -m pytest tests/test_schemas_and_client.py -v`
Expected: same pass/fail counts as before this plan started (4 pre-existing unrelated failures, per project memory `project_manual_migrations.md`/session history — confirm the failure count did not increase).

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/routers/pontuacao.py docudata-backend/tests/test_extrato_pontos.py
git commit -m "$(cat <<'EOF'
feat(pontuacao): GET /operacionais/{id}/extrato — extrato de pontos auditável

Expõe pontuacao_eventos (Task 4) via endpoint, restrito a Gerente/Líder.
Fecha a Onda 1 (backend) da Entrega 1 de Modos de Trabalho e de Avaliação.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `app/lib/api.ts` — tipos e funções novas

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`
- Create: `docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs`

**Interfaces:**
- Consumes: nothing (this is the frontend's data layer, matching the backend endpoints from Tasks 6, 7, 8).
- Produces: extended `Project` and `SprintWithStatus` interfaces; new `ConfiguracaoHistoricoEntry`, `ModosProjetoInput`, `PontuacaoEvento` types; new `updateProjectModos`, `getModosHistorico`, `updateWipConfig`, `getExtratoPontos` functions. Tasks 10, 11, 12 import from this file.

- [ ] **Step 1: Write the failing test**

```js
// docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf8");

test("api.ts expõe os endpoints de modos, wip-config e extrato de pontos", () => {
  assert.ok(API.includes("export async function updateProjectModos("));
  assert.ok(API.includes("`${API}/projects/${projectId}/modos`"));
  assert.ok(API.includes("export async function getModosHistorico("));
  assert.ok(API.includes("`${API}/projects/${projectId}/modos-historico`"));
  assert.ok(API.includes("export async function updateWipConfig("));
  assert.ok(API.includes("`${API}/projects/${projectId}/wip-config`"));
  assert.ok(API.includes("export async function getExtratoPontos("));
  assert.ok(API.includes("`${API}/operacionais/${operacionalId}/extrato${qs}`"));
});

test("Project e SprintWithStatus ganham os campos novos", () => {
  assert.ok(API.includes('modo_trabalho: "ATRIBUICAO" | "PULL";'));
  assert.ok(API.includes('modo_avaliacao: "PONTOS_ATRIBUIDOS" | "PONTOS_RELATIVO";'));
  assert.ok(API.includes("avaliados_count: number;"));
  assert.ok(API.includes("elegiveis_avaliacao_count: number;"));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && npm test -- --test-name-pattern="modos"` (or `node --test tests/modos-trabalho-avaliacao.test.mjs`)
Expected: FAIL — none of these strings exist in `api.ts` yet.

- [ ] **Step 3: Implement**

In `docudata-frontend/app/lib/api.ts`, extend the `Project` interface (currently ending with `gerente_email?: string | null;` then `}`):

```ts
export interface Project {
  id: string;
  name: string;
  client: string;
  subarea: Subarea;
  description?: string;
  valor_projeto?: number | null;
  valor_por_ponto?: number | null;
  is_delivered: boolean;
  created_at: string;
  last_ingestion_at?: string | null;
  data_inicio?: string | null;
  data_fim_contratada?: string | null;
  tolerancia_desvio_pontos?: number | null;
  periodo_garantia_dias?: number | null;
  arquetipo?: "padrao" | "consultoria_discovery";
  gerente_email?: string | null;
  modo_trabalho: "ATRIBUICAO" | "PULL";
  modo_avaliacao: "PONTOS_ATRIBUIDOS" | "PONTOS_RELATIVO";
  pull_exigir_hidratacao: boolean;
  pull_piso_pontos: number;
  pull_teto: number;
  wip_config?: { por_pessoa?: number | null; por_coluna_em_andamento?: number | null } | null;
}
```

Extend the `SprintWithStatus` interface (currently ending with `avaliacao_completa_em?: string | null;` then `}`):

```ts
/** Retorno do GET /projects/{id}/sprints — Sprint + agregados de mínimo obrigatório. */
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
  avaliados_count: number;
  elegiveis_avaliacao_count: number;
}
```

Add this block anywhere after `updateProjectSubarea` (e.g. right after its closing `}`):

```ts
export interface ConfiguracaoHistoricoEntry {
  id: string;
  project_id: string;
  campo: "modo_trabalho" | "modo_avaliacao";
  valor_anterior: string | null;
  valor_novo: string;
  usuario_email: string;
  criado_em: string;
}

export interface ModosProjetoInput {
  modo_trabalho?: "ATRIBUICAO" | "PULL";
  modo_avaliacao?: "PONTOS_ATRIBUIDOS" | "PONTOS_RELATIVO";
  pull_exigir_hidratacao?: boolean;
  pull_piso_pontos?: number;
  pull_teto?: number;
}

export async function updateProjectModos(projectId: string, data: ModosProjetoInput): Promise<Project> {
  const res = await apiFetch(`${API}/projects/${projectId}/modos`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao atualizar modos do projeto");
  }
  return res.json();
}

export async function getModosHistorico(projectId: string): Promise<ConfiguracaoHistoricoEntry[]> {
  const res = await apiFetch(`${API}/projects/${projectId}/modos-historico`);
  if (!res.ok) throw new Error("Erro ao buscar histórico de configuração");
  return res.json();
}

export async function updateWipConfig(
  projectId: string,
  data: { por_pessoa?: number; por_coluna_em_andamento?: number }
): Promise<Project> {
  const res = await apiFetch(`${API}/projects/${projectId}/wip-config`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao atualizar limite de WIP");
  }
  return res.json();
}

export interface PontuacaoEvento {
  id: string;
  operacional_id: string;
  sprint_id: string;
  projeto_id: string;
  task_id: string | null;
  tipo: "entrega_concluida" | "travamento_penalidade" | "devolucao_penalidade" | "bonus_extra" | "reabertura";
  pontos: number;
  descricao: string | null;
  criado_em: string;
}

export async function getExtratoPontos(operacionalId: string, sprintId?: string): Promise<PontuacaoEvento[]> {
  const qs = sprintId ? `?sprint_id=${sprintId}` : "";
  const res = await apiFetch(`${API}/operacionais/${operacionalId}/extrato${qs}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao buscar extrato de pontos");
  }
  return res.json();
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao.test.mjs`
Expected: PASS (2 tests)

- [ ] **Step 5: Run TypeScript build to catch type errors**

Run: `cd docudata-frontend && npm run build`
Expected: builds cleanly (type-check only, per existing project convention — no visual check).

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/lib/api.ts docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs
git commit -m "$(cat <<'EOF'
feat(api): tipos e funções fetch para modos, wip-config e extrato de pontos

Project e SprintWithStatus ganham os campos novos da Entrega 1;
updateProjectModos, getModosHistorico, updateWipConfig, getExtratoPontos.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: `SprintCard.tsx` — chip "N/M" de Avaliação Semanal

**Files:**
- Modify: `docudata-frontend/app/components/SprintCard.tsx`

**Interfaces:**
- Consumes: `sprint.avaliados_count`, `sprint.elegiveis_avaliacao_count` from Task 9's `SprintWithStatus`; `onOpenAvaliacaoSemanal` (existing prop).
- Produces: nothing consumed by later tasks — this is a leaf UI change.

- [ ] **Step 1: Write the failing test**

Append to `docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs` (created in Task 9):

```js
const SPRINT_CARD = readFileSync(new URL("../app/components/SprintCard.tsx", import.meta.url), "utf8");

test("SprintCard mostra o contador N/M de avaliação semanal", () => {
  assert.ok(SPRINT_CARD.includes("const avaliacaoPendente ="));
  assert.ok(SPRINT_CARD.includes("sprint.elegiveis_avaliacao_count > 0"));
  assert.ok(SPRINT_CARD.includes("{sprint.avaliados_count}/{sprint.elegiveis_avaliacao_count} Avaliação"));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao.test.mjs`
Expected: FAIL on the new test (strings not present in `SprintCard.tsx` yet).

- [ ] **Step 3: Implement**

In `docudata-frontend/app/components/SprintCard.tsx`, find:

```tsx
  const temRetro = docs.some((d) => d.doc_type === "retrospectiva");
```

Replace it with:

```tsx
  const temRetro = docs.some((d) => d.doc_type === "retrospectiva");
  const avaliacaoPendente =
    sprint.elegiveis_avaliacao_count > 0 && sprint.avaliados_count < sprint.elegiveis_avaliacao_count;
```

Then find the chips block:

```tsx
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
```

Replace it with (adds a new chip between Retrospectiva and Dailys, only rendered when there is someone to evaluate):

```tsx
        <button
          type="button"
          style={statusChip(temRetro)}
          onClick={() => onOpenRetroModal(sprint.numero)}
          title="Adicionar Retrospectiva"
        >
          {temRetro ? "1/1" : "0/1"} Retrospectiva
          <span style={{ marginLeft: 4, fontWeight: 800 }}>+</span>
        </button>
        {sprint.elegiveis_avaliacao_count > 0 && (
          <button
            type="button"
            style={statusChip(!avaliacaoPendente)}
            onClick={() => onOpenAvaliacaoSemanal?.(sprint)}
            title="Avaliação Semanal"
          >
            {sprint.avaliados_count}/{sprint.elegiveis_avaliacao_count} Avaliação
          </button>
        )}
        <button
          type="button"
          style={dailyChip(sprint.dailys_count)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao.test.mjs`
Expected: PASS

- [ ] **Step 5: Run full frontend test suite and build**

Run: `cd docudata-frontend && npm test && npm run build`
Expected: all pass, clean build.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/components/SprintCard.tsx docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs
git commit -m "$(cat <<'EOF'
feat(sprint-card): chip N/M de Avaliação Semanal (extra do usuário)

Mostra quantos operacionais elegíveis já foram avaliados na sprint, no
mesmo estilo dos chips de Planning/Review/Retrospectiva já existentes.
Escondido quando ninguém tem task na sprint ainda.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: `page.tsx` — seção "Modos de Trabalho e de Avaliação" na aba Configurações

**Files:**
- Modify: `docudata-frontend/app/[subarea]/projects/[id]/page.tsx`

**Interfaces:**
- Consumes: `updateProjectModos`, `getModosHistorico`, `updateWipConfig`, `type ConfiguracaoHistoricoEntry` from Task 9; `Project` (extended by Task 9).
- Produces: a new inline component `ModosTrabalhoSection`, rendered in the Configurações tab. Nothing later depends on this.

- [ ] **Step 1: Write the failing test**

Append to `docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs`:

```js
const PROJECT_PAGE = readFileSync(new URL("../app/[subarea]/projects/[id]/page.tsx", import.meta.url), "utf8");

test("Configurações mostram os selects de modo com campos condicionais e WIP forçado", () => {
  assert.ok(PROJECT_PAGE.includes("function ModosTrabalhoSection("));
  assert.ok(PROJECT_PAGE.includes('id="project-modo-trabalho"'));
  assert.ok(PROJECT_PAGE.includes('id="project-modo-avaliacao"'));
  assert.ok(PROJECT_PAGE.includes("updateProjectModos(projectId,"));
  assert.ok(PROJECT_PAGE.includes('modoTrabalho === "PULL"'));
  assert.ok(PROJECT_PAGE.includes('modoAvaliacao === "PONTOS_RELATIVO"'));
  assert.ok(PROJECT_PAGE.includes("updateWipConfig(projectId,"));
  assert.ok(PROJECT_PAGE.includes("getModosHistorico(projectId)"));
  assert.ok(PROJECT_PAGE.includes("<ModosTrabalhoSection"));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao.test.mjs`
Expected: FAIL on the new test.

- [ ] **Step 3: Add the imports**

In `docudata-frontend/app/[subarea]/projects/[id]/page.tsx`, find the closing of the big import block from `"../../../lib/api"`:

```tsx
  type GitHubRepositoryCandidate,
  type ProjectRepository,
} from "../../../lib/api";
```

Replace it with:

```tsx
  type GitHubRepositoryCandidate,
  type ProjectRepository,
  updateProjectModos,
  getModosHistorico,
  updateWipConfig,
  type ConfiguracaoHistoricoEntry,
} from "../../../lib/api";
```

- [ ] **Step 4: Add the `ModosTrabalhoSection` component**

In `docudata-frontend/app/[subarea]/projects/[id]/page.tsx`, find the end of `OperacionaisSection` and the start of the page's default export:

```tsx
          <p style={{ fontSize: 11, color: "#9696a0", marginTop: 8 }}>
            E-mail e GitHub username não são obrigatórios, mas sem eles a pessoa não é
            reconhecida entre projetos e os commits dela não contam na nota de qualidade.
            O email do commit é o que o Git usa localmente — se for diferente do e-mail
            de login, preencha o campo "Email do GitHub" para o commit ser reconhecido.
          </p>
        </div>
      )}
    </section>
  );
}

export default function ProjectDashboard() {
```

Replace it with (adds the new component between the two, everything else unchanged):

```tsx
          <p style={{ fontSize: 11, color: "#9696a0", marginTop: 8 }}>
            E-mail e GitHub username não são obrigatórios, mas sem eles a pessoa não é
            reconhecida entre projetos e os commits dela não contam na nota de qualidade.
            O email do commit é o que o Git usa localmente — se for diferente do e-mail
            de login, preencha o campo "Email do GitHub" para o commit ser reconhecido.
          </p>
        </div>
      )}
    </section>
  );
}

type ModoTrabalho = "ATRIBUICAO" | "PULL";
type ModoAvaliacao = "PONTOS_ATRIBUIDOS" | "PONTOS_RELATIVO";

function ModosTrabalhoSection({
  projectId,
  project,
  onProjectUpdated,
}: {
  projectId: string;
  project: Project;
  onProjectUpdated: (updated: Project) => void;
}) {
  const [modoTrabalhoDestino, setModoTrabalhoDestino] = useState<ModoTrabalho | null>(null);
  const [modoAvaliacaoDestino, setModoAvaliacaoDestino] = useState<ModoAvaliacao | null>(null);
  const [hidratacaoDestino, setHidratacaoDestino] = useState<boolean | null>(null);
  const [pisoDestino, setPisoDestino] = useState<string | null>(null);
  const [tetoDestino, setTetoDestino] = useState<string | null>(null);
  const [savingModos, setSavingModos] = useState(false);
  const [modosMsg, setModosMsg] = useState<{ ok: boolean; text: string } | null>(null);

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

  const modoTrabalho = modoTrabalhoDestino ?? project.modo_trabalho;
  const modoAvaliacao = modoAvaliacaoDestino ?? project.modo_avaliacao;
  const hidratacao = hidratacaoDestino ?? project.pull_exigir_hidratacao;
  const piso = pisoDestino ?? String(project.pull_piso_pontos);
  const teto = tetoDestino ?? String(project.pull_teto);

  const modosMudou =
    modoTrabalho !== project.modo_trabalho ||
    modoAvaliacao !== project.modo_avaliacao ||
    hidratacao !== project.pull_exigir_hidratacao ||
    piso !== String(project.pull_piso_pontos) ||
    teto !== String(project.pull_teto);

  async function handleSalvarModos() {
    setSavingModos(true);
    setModosMsg(null);
    try {
      const updated = await updateProjectModos(projectId, {
        modo_trabalho: modoTrabalho,
        modo_avaliacao: modoAvaliacao,
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
        qual fórmula calcula a dimensão Entrega da pontuação. Pode ser trocado a qualquer
        momento, inclusive no meio de uma sprint em andamento.
      </p>

      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginBottom: 16 }}>
        <div>
          <label htmlFor="project-modo-trabalho" style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 4 }}>
            Modo de trabalho
          </label>
          <select
            id="project-modo-trabalho"
            value={modoTrabalho}
            onChange={(e) => { setModoTrabalhoDestino(e.target.value as ModoTrabalho); setModosMsg(null); }}
            disabled={savingModos}
            style={{ ...inputStyle, width: 180, minHeight: 38, background: "#fff", cursor: "pointer" }}
          >
            <option value="ATRIBUICAO">Atribuição</option>
            <option value="PULL">Puxada (pull)</option>
          </select>
        </div>

        <div>
          <label htmlFor="project-modo-avaliacao" style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 4 }}>
            Modo de avaliação da Entrega
          </label>
          <select
            id="project-modo-avaliacao"
            value={modoAvaliacao}
            onChange={(e) => { setModoAvaliacaoDestino(e.target.value as ModoAvaliacao); setModosMsg(null); }}
            disabled={savingModos}
            style={{ ...inputStyle, width: 200, minHeight: 38, background: "#fff", cursor: "pointer" }}
          >
            <option value="PONTOS_ATRIBUIDOS">Pontos atribuídos</option>
            <option value="PONTOS_RELATIVO">Pontos relativo ao squad</option>
          </select>
        </div>
      </div>

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
          disabled={savingModos || !modosMudou}
          style={{ ...btnSecondary, opacity: savingModos || !modosMudou ? 0.5 : 1, cursor: savingModos || !modosMudou ? "not-allowed" : "pointer" }}
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
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <input
              type="number"
              min={1}
              value={wipPorPessoaInput}
              onChange={(e) => { setWipPorPessoaInput(e.target.value); setWipMsg(null); }}
              disabled={savingWip}
              placeholder="Sem limite"
              style={{ ...inputStyle, width: 100 }}
            />
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

export default function ProjectDashboard() {
```

- [ ] **Step 5: Render the new section in the Configurações tab**

In the same file, find:

```tsx
          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Status do projeto</h2>
            <button onClick={handleToggleDelivered} style={project.is_delivered ? btnDeliveredActive : btnDelivered}>
              {project.is_delivered ? "✓ Marcado como entregue (desfazer)" : "Marcar como entregue"}
            </button>
          </section>

          <OperacionaisSection
```

Replace it with:

```tsx
          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Status do projeto</h2>
            <button onClick={handleToggleDelivered} style={project.is_delivered ? btnDeliveredActive : btnDelivered}>
              {project.is_delivered ? "✓ Marcado como entregue (desfazer)" : "Marcar como entregue"}
            </button>
          </section>

          <ModosTrabalhoSection
            projectId={id}
            project={project}
            onProjectUpdated={(updated) => setProject(updated)}
          />

          <OperacionaisSection
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao.test.mjs`
Expected: PASS

- [ ] **Step 7: Run full frontend suite and build**

Run: `cd docudata-frontend && npm test && npm run build`
Expected: all pass, clean build (type-check only).

- [ ] **Step 8: Commit**

```bash
git add "docudata-frontend/app/[subarea]/projects/[id]/page.tsx" docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs
git commit -m "$(cat <<'EOF'
feat(config): seção Modos de Trabalho e de Avaliação na aba Configurações

Dois selects (modo de trabalho, modo de avaliação) com campos condicionais
(hidratação, piso, teto) só quando relevantes; WIP por pessoa fixo em 1 e
somente leitura quando o projeto está em PULL (RF-A5); histórico de
mudanças de modo (RF-A6) listado abaixo.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: `PainelTab.tsx` — seção "Extrato de pontos"

**Files:**
- Modify: `docudata-frontend/app/components/PainelTab.tsx`
- Modify: `docudata-frontend/app/[subarea]/projects/[id]/page.tsx` (pass `operacionais` prop through)

**Interfaces:**
- Consumes: `getExtratoPontos`, `type PontuacaoEvento` from Task 9; `operacionais` state (already exists in `page.tsx`, currently not passed to `PainelTab`).
- Produces: nothing consumed by later tasks — final UI piece of Entrega 1.

- [ ] **Step 1: Write the failing test**

Append to `docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs`:

```js
const PAINEL = readFileSync(new URL("../app/components/PainelTab.tsx", import.meta.url), "utf8");

test("Painel recebe operacionais e mostra o extrato de pontos", () => {
  assert.ok(PAINEL.includes("function ExtratoPontosCard("));
  assert.ok(PAINEL.includes("getExtratoPontos("));
  assert.ok(PAINEL.includes("operacionais: OperacionalResponse[];"));
  assert.ok(PAINEL.includes("<ExtratoPontosCard"));
  assert.ok(PROJECT_PAGE.includes("<PainelTab"));
  assert.ok(PROJECT_PAGE.match(/<PainelTab[\s\S]*?operacionais=\{operacionais\}/));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao.test.mjs`
Expected: FAIL on the new test.

- [ ] **Step 3: Extend `PainelTab`'s imports and Props**

In `docudata-frontend/app/components/PainelTab.tsx`, find:

```tsx
import {
  getPainel,
  listFuncionalidades,
  getSprintFuncionalidades,
  createSprintFuncionalidades,
  updateSprintFuncionalidade,
  updateFuncionalidade,
  updateContrato,
  listTasksKanban,
  type BlocoD,
  type FuncionalidadeResponse,
  type PainelData,
  type Project,
  type SprintFuncionalidade,
  type SprintWithStatus,
} from "../lib/api";

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
  project: Project;
  onProjectUpdated?: (updated: Project) => void;
}
```

Replace it with:

```tsx
import {
  getPainel,
  listFuncionalidades,
  getSprintFuncionalidades,
  createSprintFuncionalidades,
  updateSprintFuncionalidade,
  updateFuncionalidade,
  updateContrato,
  listTasksKanban,
  getExtratoPontos,
  type BlocoD,
  type FuncionalidadeResponse,
  type OperacionalResponse,
  type PainelData,
  type PontuacaoEvento,
  type Project,
  type SprintFuncionalidade,
  type SprintWithStatus,
} from "../lib/api";

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
  project: Project;
  operacionais: OperacionalResponse[];
  onProjectUpdated?: (updated: Project) => void;
}
```

- [ ] **Step 4: Add the `ExtratoPontosCard` component**

In the same file, find `function BlocoDCard({` and its matching closing `}` right before `export default function PainelTab`. Add the new component right after `BlocoDCard`'s closing brace and before `export default function PainelTab({ projectId, sprints, project, onProjectUpdated }: Props) {`:

```tsx
function ExtratoPontosCard({
  operacionais,
  sprints,
}: {
  operacionais: OperacionalResponse[];
  sprints: SprintWithStatus[];
}) {
  const [operacionalId, setOperacionalId] = useState("");
  const [sprintId, setSprintId] = useState("");
  const [eventos, setEventos] = useState<PontuacaoEvento[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!operacionalId) {
      setEventos([]);
      return;
    }
    setLoading(true);
    setErro(null);
    getExtratoPontos(operacionalId, sprintId || undefined)
      .then(setEventos)
      .catch((err) => setErro(err instanceof Error ? err.message : "Erro ao buscar extrato"))
      .finally(() => setLoading(false));
  }, [operacionalId, sprintId]);

  const rotuloTipo: Record<PontuacaoEvento["tipo"], string> = {
    entrega_concluida: "Entrega concluída",
    travamento_penalidade: "Travamento (penalidade)",
    devolucao_penalidade: "Devolução após travamento (penalidade)",
    bonus_extra: "Bônus de task extra",
    reabertura: "Reabertura",
  };

  return (
    <div style={cardStyle}>
      <span style={cardTitleStyle}>Extrato de pontos</span>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
        <select
          value={operacionalId}
          onChange={(e) => setOperacionalId(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #e4e4ea", borderRadius: 7, fontSize: 13 }}
        >
          <option value="">Selecione um operacional...</option>
          {operacionais.map((op) => (
            <option key={op.id} value={op.id}>{op.nome}</option>
          ))}
        </select>
        <select
          value={sprintId}
          onChange={(e) => setSprintId(e.target.value)}
          style={{ padding: "6px 10px", border: "1px solid #e4e4ea", borderRadius: 7, fontSize: 13 }}
        >
          <option value="">Todas as sprints</option>
          {sprints.map((s) => (
            <option key={s.id} value={s.id}>Sprint {s.numero}</option>
          ))}
        </select>
      </div>

      {!operacionalId ? (
        <p style={{ fontSize: 12, color: "#9696a0" }}>Selecione um operacional para ver o extrato.</p>
      ) : loading ? (
        <p style={{ fontSize: 12, color: "#9696a0" }}>Carregando...</p>
      ) : erro ? (
        <p style={{ fontSize: 12, color: "#dc2626" }}>{erro}</p>
      ) : eventos.length === 0 ? (
        <p style={{ fontSize: 12, color: "#9696a0" }}>Nenhum evento de pontuação registrado ainda.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 280, overflowY: "auto" }}>
          {eventos.map((ev) => (
            <div key={ev.id} style={{ display: "flex", justifyContent: "space-between", gap: 10, fontSize: 12, borderBottom: "1px solid #f0f0f4", padding: "6px 0" }}>
              <span style={{ color: "#374151" }}>
                {rotuloTipo[ev.tipo]}
                {ev.descricao ? ` — ${ev.descricao}` : ""}
              </span>
              <span style={{ fontWeight: 700, color: ev.pontos > 0 ? "#16a34a" : ev.pontos < 0 ? "#dc2626" : "#9696a0", whiteSpace: "nowrap" }}>
                {ev.pontos > 0 ? `+${ev.pontos}` : ev.pontos}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

Then update the `export default function PainelTab` signature to destructure the new prop:

```tsx
export default function PainelTab({ projectId, sprints, project, operacionais, onProjectUpdated }: Props) {
```

- [ ] **Step 5: Render `ExtratoPontosCard` at the end of the returned JSX**

At the end of the file, find:

```tsx
                    <KanbanCard f={f} allSprints={allSprintsByFuncional[f.id_funcional] ?? []} taskCounts={taskCountsByFuncId.get(f.id)} />
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

Replace it with (adds `<ExtratoPontosCard>` as a new sibling right before the outermost closing `</div>`):

```tsx
                    <KanbanCard f={f} allSprints={allSprintsByFuncional[f.id_funcional] ?? []} taskCounts={taskCountsByFuncId.get(f.id)} />
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      <ExtratoPontosCard operacionais={operacionais} sprints={sprints} />
    </div>
  );
}
```

- [ ] **Step 6: Pass `operacionais` through from `page.tsx`**

In `docudata-frontend/app/[subarea]/projects/[id]/page.tsx`, find:

```tsx
        <PainelTab
          projectId={id}
          sprints={sprints}
          project={project}
          onProjectUpdated={(updated) => setProject(updated)}
        />
      )}
```

Replace it with:

```tsx
        <PainelTab
          projectId={id}
          sprints={sprints}
          project={project}
          operacionais={operacionais}
          onProjectUpdated={(updated) => setProject(updated)}
        />
      )}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao.test.mjs`
Expected: PASS (all tests in the file)

- [ ] **Step 8: Run full frontend suite and build (Onda 2 exit gate)**

Run: `cd docudata-frontend && npm test`
Expected: PASS, every test file in `tests/`.

Run: `cd docudata-frontend && npm run build`
Expected: clean build, no type errors.

- [ ] **Step 9: Commit**

```bash
git add docudata-frontend/app/components/PainelTab.tsx "docudata-frontend/app/[subarea]/projects/[id]/page.tsx" docudata-frontend/tests/modos-trabalho-avaliacao.test.mjs
git commit -m "$(cat <<'EOF'
feat(painel): seção Extrato de pontos — log auditável por operacional

ExtratoPontosCard no Painel: seletor de operacional + sprint, lista de
todo ponto ganho ou descontado (extra do usuário). Fecha a Onda 2 (UI) da
Entrega 1 de Modos de Trabalho e de Avaliação.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Final verification (both waves complete)

After Task 12, run the complete verification sweep before declaring Entrega 1 done:

```bash
cd docudata-backend && python -m pytest tests/ -v --ignore=tests/test_schemas_and_client.py
cd docudata-backend && python -m pytest tests/test_schemas_and_client.py -v   # confirm same pre-existing failure count as baseline
cd docudata-frontend && npm test
cd docudata-frontend && npm run build
```

All four must pass (the second only needs to match, not improve on, its known pre-existing failure count). Update `.planning/feature-flow-state.md` to `status: "concluido"` for this Entrega-1 cycle, and note in it that Entrega 2 (Experimento: fila, pull, hidratação, migração, fórmula relativa) and Entrega 3 (Evidência: métricas, CSV) remain as separate future feature-flow-lean cycles, per spec §3.
