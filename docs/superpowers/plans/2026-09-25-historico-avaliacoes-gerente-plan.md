# Histórico e correção de avaliações do gerente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tela `/avaliacoes` onde gerente/líder/owner veem e corrigem (com motivo auditado) as notas da avaliação semanal, e toda criação/edição de avaliação passa a refletir no snapshot do ranking.

**Architecture:** Backend ganha um helper `sincronizar_snapshot_gerente` em `services/pontuacao.py` (reusa a fórmula de `calcular_e_travar_pontuacao`), três rotas novas em `routers/avaliacoes.py` e uma tabela de log `avaliacoes_gerente_edicoes`. O `POST /avaliacoes` existente também passa a sincronizar. Frontend ganha uma página standalone no padrão de `app/performance/page.tsx`, com os textos das perguntas extraídos para um módulo compartilhado.

**Tech Stack:** FastAPI + supabase-py (sync) + pytest / Next.js 15 + React 19, inline styles, testes `node --test` por regex no fonte.

**Spec:** `docs/superpowers/specs/2026-09-25-historico-avaliacoes-gerente-design.md`

## Global Constraints

- Onda 1 (Tasks 1–3, backend) completa e com `pytest` verde antes da Onda 2 (Tasks 4–6).
- Router `/avaliacoes` já é montado com `require_not_operacional` (`main.py:197`) — operacional recebe 403 em tudo.
- Edição: qualquer não-operacional, sem prazo; motivo obrigatório (não vazio após trim); respostas 0–5.
- Média do gerente = média de `resposta_1,2,3,4,5,7` com 2 casas (resposta_6 fora). Na tela: `média × 20` (escala 0–100 do ranking).
- Migração é manual (`supabase_schema.sql` não roda sozinho) — avisar o usuário no fim.
- Rodar testes backend de `docudata-backend/`: `python -m pytest ...`. Frontend de `docudata-frontend/`: `npx tsc --noEmit -p .` e `npm test`.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

---

## Onda 1 — Backend

### Task 1: Helper de snapshot do gerente + fake de Supabase para testes

**Files:**
- Create: `docudata-backend/tests/fake_supabase.py`
- Modify: `docudata-backend/services/pontuacao.py` (adicionar helpers após `log = ...`; refatorar bloco `if aval:` em `calcular_e_travar_pontuacao`, ~linha 228-240)
- Test: `docudata-backend/tests/test_snapshot_gerente.py`

**Interfaces:**
- Produces: `campos_gerente(aval: dict) -> dict` com chaves `gerente_media`, `gerente_pergunta6`, `gerente_pergunta3`; `sincronizar_snapshot_gerente(client, aval: dict) -> None`; `tests.fake_supabase.FakeClient(tables: dict[str, list[dict]])` com `.tables` (dict mutável).

- [ ] **Step 1: Criar o fake de Supabase**

`docudata-backend/tests/fake_supabase.py`:

```python
"""Supabase em memória para testes de rota — cobre só o subconjunto da API
usado pelos routers (select/eq/in_/order/limit/insert/update)."""


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, tables, name, op, payload=None):
        self._tables = tables
        self._name = name
        self._op = op
        self._payload = payload
        self._filtros = []
        self._ordem = None
        self._limite = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, col, val):
        self._filtros.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        conjunto = set(vals)
        self._filtros.append(lambda r: r.get(col) in conjunto)
        return self

    def order(self, col, desc=False):
        self._ordem = (col, desc)
        return self

    def limit(self, n):
        self._limite = n
        return self

    def execute(self):
        linhas = self._tables.setdefault(self._name, [])
        if self._op == "insert":
            itens = self._payload if isinstance(self._payload, list) else [self._payload]
            saida = []
            for item in itens:
                row = dict(item)
                row.setdefault("id", f"{self._name}-{len(linhas) + 1}")
                linhas.append(row)
                saida.append(dict(row))
            return _Resp(saida)
        casadas = [r for r in linhas if all(f(r) for f in self._filtros)]
        if self._op == "update":
            for r in casadas:
                r.update(self._payload)
            return _Resp([dict(r) for r in casadas])
        if self._ordem:
            col, desc = self._ordem
            casadas = sorted(casadas, key=lambda r: str(r.get(col) or ""), reverse=desc)
        if self._limite is not None:
            casadas = casadas[: self._limite]
        return _Resp([dict(r) for r in casadas])


class _Table:
    def __init__(self, tables, name):
        self._tables = tables
        self._name = name

    def select(self, *_args, **_kwargs):
        return _Query(self._tables, self._name, "select")

    def insert(self, payload):
        return _Query(self._tables, self._name, "insert", payload)

    def update(self, payload):
        return _Query(self._tables, self._name, "update", payload)


class FakeClient:
    def __init__(self, tables=None):
        self.tables = {k: [dict(r) for r in v] for k, v in (tables or {}).items()}

    def table(self, name):
        return _Table(self.tables, name)
```

- [ ] **Step 2: Escrever os testes que falham**

`docudata-backend/tests/test_snapshot_gerente.py`:

```python
from services.pontuacao import campos_gerente, sincronizar_snapshot_gerente
from tests.fake_supabase import FakeClient

_AVAL = {
    "sprint_id": "sp-1", "operacional_id": "op-1",
    "resposta_1": 4, "resposta_2": 4, "resposta_3": 5, "resposta_4": 5,
    "resposta_5": 5, "resposta_6": 0, "resposta_7": 5,
}


def test_campos_gerente_ignora_resposta_6():
    assert campos_gerente(_AVAL) == {
        "gerente_media": 4.67,
        "gerente_pergunta6": 0,
        "gerente_pergunta3": 5,
    }


def test_sincroniza_linha_existente():
    fake = FakeClient({"pontuacao_operacional_sprint": [
        {"id": "p1", "sprint_id": "sp-1", "operacional_id": "op-1", "gerente_media": 5.0, "gerente_pergunta3": 5, "gerente_pergunta6": None},
        {"id": "p2", "sprint_id": "sp-1", "operacional_id": "op-2", "gerente_media": 3.0, "gerente_pergunta3": 3, "gerente_pergunta6": None},
    ]})

    sincronizar_snapshot_gerente(fake, _AVAL)

    linhas = {r["id"]: r for r in fake.tables["pontuacao_operacional_sprint"]}
    assert linhas["p1"]["gerente_media"] == 4.67
    assert linhas["p1"]["gerente_pergunta6"] == 0
    assert linhas["p2"]["gerente_media"] == 3.0  # outro operacional intacto


def test_sprint_aberta_sem_linha_e_no_op():
    fake = FakeClient({"pontuacao_operacional_sprint": []})

    sincronizar_snapshot_gerente(fake, _AVAL)

    assert fake.tables["pontuacao_operacional_sprint"] == []
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `cd docudata-backend && python -m pytest tests/test_snapshot_gerente.py -v`
Expected: FAIL — `ImportError: cannot import name 'campos_gerente'`.

- [ ] **Step 4: Implementar em `services/pontuacao.py`**

Logo após `log = logging.getLogger("pontuacao")`:

```python
def campos_gerente(aval: dict) -> dict:
    """Campos de gerente do snapshot a partir de uma linha de avaliacoes_gerente.

    A resposta 6 fica FORA da média de propósito. Historicamente era a fonte
    exclusiva da dimensão Evolução (removida em 2026-09-23) — o campo continua
    existindo por compat com dado antigo, mas não alimenta mais nenhuma
    dimensão de score."""
    notas = [aval["resposta_1"], aval["resposta_2"], aval["resposta_3"], aval["resposta_4"], aval["resposta_5"], aval["resposta_7"]]
    return {
        "gerente_media": round(sum(notas) / len(notas), 2),
        "gerente_pergunta6": aval.get("resposta_6"),
        "gerente_pergunta3": aval["resposta_3"],
    }


def sincronizar_snapshot_gerente(client, aval: dict) -> None:
    """Reflete uma avaliação criada/editada DEPOIS do fechamento no snapshot
    congelado — sem isso a nota nova nunca chegava ao ranking. Só mexe nos
    campos de gerente (Entrega/Autonomia e correções manuais ficam como estão).
    Sprint ainda aberta não tem linha: o update não casa nada e é no-op."""
    (
        client.table("pontuacao_operacional_sprint")
        .update(campos_gerente(aval))
        .eq("sprint_id", aval["sprint_id"])
        .eq("operacional_id", aval["operacional_id"])
        .execute()
    )
```

Em `calcular_e_travar_pontuacao`, substituir o bloco:

```python
        if aval:
            # A resposta 6 fica FORA desta média de propósito. Historicamente
            # era a fonte exclusiva da dimensão Evolução (removida em
            # 2026-09-23) — o campo continua existindo por compat com dado
            # antigo, mas não alimenta mais nenhuma dimensão de score.
            notas = [aval["resposta_1"], aval["resposta_2"], aval["resposta_3"], aval["resposta_4"], aval["resposta_5"], aval["resposta_7"]]
            gerente_media = round(sum(notas) / len(notas), 2)
            gerente_pergunta6 = aval["resposta_6"]
            gerente_pergunta3 = aval["resposta_3"]
```

por:

```python
        if aval:
            gerente = campos_gerente(aval)
            gerente_media = gerente["gerente_media"]
            gerente_pergunta6 = gerente["gerente_pergunta6"]
            gerente_pergunta3 = gerente["gerente_pergunta3"]
```

- [ ] **Step 5: Rodar os testes novos e os de pontuação existentes**

Run: `cd docudata-backend && python -m pytest -q`
Expected: PASS, 0 falhas.

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/tests/fake_supabase.py docudata-backend/tests/test_snapshot_gerente.py docudata-backend/services/pontuacao.py
git commit -m "feat(pontuacao): sincronizar_snapshot_gerente reflete avaliação pós-fechamento no ranking"
```

---

### Task 2: Edição auditada — migração, schemas, `PATCH /avaliacoes/{id}`, `GET /avaliacoes/{id}/edicoes`, `GET /avaliacoes/historico`

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (append no fim)
- Modify: `docudata-backend/models/schemas.py` (após `AvaliacaoGerenteResponse`, ~linha 697)
- Modify: `docudata-backend/routers/avaliacoes.py`
- Test: `docudata-backend/tests/test_avaliacoes_historico_edicao.py`

**Interfaces:**
- Consumes: `sincronizar_snapshot_gerente(client, aval)` (Task 1), `FakeClient` (Task 1).
- Produces (JSON consumido pela Onda 2):
  - `GET /avaliacoes/historico?project_id=&sprint_id=` → `AvaliacaoHistoricoItem[]`: `id, operacional_id, operacional_nome, sprint_id, sprint_numero, projeto_id, projeto_nome, modo_trabalho, avaliador_nome, resposta_1..5, resposta_6 (nullable), resposta_7, criado_em, total_edicoes, ultima_edicao_em (nullable), ultima_edicao_por (nullable)`.
  - `PATCH /avaliacoes/{id}` body `{resposta_1..5, resposta_7, motivo}` → `AvaliacaoHistoricoItem`. Erros: 404, 422 (validação / "Nenhuma nota alterada.").
  - `GET /avaliacoes/{id}/edicoes` → `AvaliacaoEdicaoItem[]`: `id, editor_nome, antes, depois, motivo, criado_em` (desc por data). `antes`/`depois` têm as 7 chaves `resposta_N`.

- [ ] **Step 1: Migração em `supabase_schema.sql`** (append)

```sql
-- Histórico e correção de avaliações do gerente (2026-09-25). Toda edição
-- feita pela tela /avaliacoes grava antes/depois e motivo — a tela é aberta
-- a qualquer gerente/líder, então o log é o que dá rastreabilidade.
CREATE TABLE IF NOT EXISTS avaliacoes_gerente_edicoes (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    avaliacao_id  uuid        NOT NULL REFERENCES avaliacoes_gerente(id) ON DELETE CASCADE,
    editor_id     uuid        NOT NULL REFERENCES pessoa(id),
    antes         jsonb       NOT NULL,
    depois        jsonb       NOT NULL,
    motivo        text        NOT NULL CHECK (length(trim(motivo)) > 0),
    criado_em     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_aval_edicoes_avaliacao ON avaliacoes_gerente_edicoes(avaliacao_id);

-- Correção retroativa (2026-09-25): o snapshot de gerente era congelado no
-- fechamento e avaliação criada/editada depois disso nunca chegava ao
-- ranking. Ressincroniza todo snapshot com a avaliação atual. Idempotente.
UPDATE pontuacao_operacional_sprint p
SET gerente_media = ROUND((a.resposta_1 + a.resposta_2 + a.resposta_3 + a.resposta_4 + a.resposta_5 + a.resposta_7)::numeric / 6, 2),
    gerente_pergunta3 = a.resposta_3,
    gerente_pergunta6 = a.resposta_6
FROM avaliacoes_gerente a
WHERE a.sprint_id = p.sprint_id
  AND a.operacional_id = p.operacional_id;
```

- [ ] **Step 2: Schemas em `models/schemas.py`** (após `AvaliacaoGerenteResponse`)

```python
class AvaliacaoGerenteEdicao(BaseModel):
    resposta_1: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_2: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_3: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_4: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_5: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_7: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_obrigatorio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe o motivo da edição")
        return v


class AvaliacaoHistoricoItem(BaseModel):
    id: str
    operacional_id: str
    operacional_nome: str
    sprint_id: str
    sprint_numero: Optional[int] = None
    projeto_id: Optional[str] = None
    projeto_nome: str
    modo_trabalho: str
    avaliador_nome: str
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: Optional[int] = None
    resposta_7: int
    criado_em: datetime
    total_edicoes: int
    ultima_edicao_em: Optional[datetime] = None
    ultima_edicao_por: Optional[str] = None


class AvaliacaoEdicaoItem(BaseModel):
    id: str
    editor_nome: str
    antes: dict
    depois: dict
    motivo: str
    criado_em: datetime
```

- [ ] **Step 3: Escrever os testes que falham**

`docudata-backend/tests/test_avaliacoes_historico_edicao.py`:

```python
"""Tela /avaliacoes: histórico, edição auditada e sincronização do snapshot."""
from fastapi.testclient import TestClient

from services.auth import criar_jwt
from tests.fake_supabase import FakeClient


def _seed(com_snapshot=True):
    return {
        "projects": [
            {"id": "proj-1", "name": "PMO", "modo_trabalho": "ATRIBUICAO"},
            {"id": "proj-2", "name": "Visus", "modo_trabalho": "PULL"},
        ],
        "sprints": [
            {"id": "sp-1", "numero": 1, "project_id": "proj-1"},
            {"id": "sp-2", "numero": 2, "project_id": "proj-1"},
            {"id": "sp-9", "numero": 1, "project_id": "proj-2"},
        ],
        "operacionais": [
            {"id": "op-1", "nome": "Victor Lemos"},
            {"id": "op-2", "nome": "Antonio"},
        ],
        "pessoa": [
            {"id": "pessoa-theo", "nome": "Theo"},
            {"id": "pessoa-ger-1", "nome": "Gabriel"},
        ],
        "avaliacoes_gerente": [
            {"id": "aval-1", "operacional_id": "op-1", "gerente_id": "pessoa-theo", "sprint_id": "sp-1",
             "resposta_1": 5, "resposta_2": 5, "resposta_3": 5, "resposta_4": 5, "resposta_5": 5,
             "resposta_6": None, "resposta_7": 5,
             "criado_em": "2026-09-20T12:00:00+00:00", "editavel_ate": "2026-09-22T12:00:00+00:00"},
            {"id": "aval-2", "operacional_id": "op-2", "gerente_id": "pessoa-theo", "sprint_id": "sp-9",
             "resposta_1": 3, "resposta_2": 3, "resposta_3": 3, "resposta_4": 3, "resposta_5": 3,
             "resposta_6": None, "resposta_7": 3,
             "criado_em": "2026-09-20T12:00:00+00:00", "editavel_ate": "2026-09-22T12:00:00+00:00"},
        ],
        "pontuacao_operacional_sprint": (
            [{"id": "pont-1", "sprint_id": "sp-1", "operacional_id": "op-1",
              "gerente_media": 5.0, "gerente_pergunta3": 5, "gerente_pergunta6": None}]
            if com_snapshot else []
        ),
        "avaliacoes_gerente_edicoes": [],
    }


def _tc(monkeypatch, fake, cargo="gerente"):
    import routers.avaliacoes as avaliacoes_router
    monkeypatch.setattr(avaliacoes_router, "get_client", lambda: fake)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-ger-1", "ger@citi.com", cargo))
    return tc


_EDICAO = {
    "resposta_1": 4, "resposta_2": 4, "resposta_3": 5, "resposta_4": 5, "resposta_5": 5, "resposta_7": 5,
    "motivo": "Theo tinha dado 4 em P1 e P2",
}


def test_patch_grava_log_atualiza_e_sincroniza_snapshot(monkeypatch):
    fake = FakeClient(_seed())
    tc = _tc(monkeypatch, fake)

    resp = tc.patch("/avaliacoes/aval-1", json=_EDICAO)

    assert resp.status_code == 200
    body = resp.json()
    assert body["resposta_1"] == 4
    assert body["avaliador_nome"] == "Theo"
    assert body["total_edicoes"] == 1
    assert body["ultima_edicao_por"] == "Gabriel"

    aval = next(a for a in fake.tables["avaliacoes_gerente"] if a["id"] == "aval-1")
    assert aval["resposta_2"] == 4
    assert aval["gerente_id"] == "pessoa-theo"  # avaliador original preservado

    [log] = fake.tables["avaliacoes_gerente_edicoes"]
    assert log["avaliacao_id"] == "aval-1"
    assert log["editor_id"] == "pessoa-ger-1"
    assert log["antes"]["resposta_1"] == 5
    assert log["depois"]["resposta_1"] == 4
    assert log["motivo"] == "Theo tinha dado 4 em P1 e P2"

    [snap] = fake.tables["pontuacao_operacional_sprint"]
    assert snap["gerente_media"] == 4.67


def test_patch_sprint_aberta_nao_cria_snapshot(monkeypatch):
    fake = FakeClient(_seed(com_snapshot=False))
    tc = _tc(monkeypatch, fake)

    resp = tc.patch("/avaliacoes/aval-1", json=_EDICAO)

    assert resp.status_code == 200
    assert fake.tables["pontuacao_operacional_sprint"] == []


def test_patch_motivo_em_branco_422(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))
    resp = tc.patch("/avaliacoes/aval-1", json={**_EDICAO, "motivo": "   "})
    assert resp.status_code == 422


def test_patch_nota_fora_da_escala_422(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))
    resp = tc.patch("/avaliacoes/aval-1", json={**_EDICAO, "resposta_1": 6})
    assert resp.status_code == 422


def test_patch_sem_mudanca_422_e_nao_loga(monkeypatch):
    fake = FakeClient(_seed())
    tc = _tc(monkeypatch, fake)
    sem_mudanca = {**_EDICAO, "resposta_1": 5, "resposta_2": 5}

    resp = tc.patch("/avaliacoes/aval-1", json=sem_mudanca)

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Nenhuma nota alterada."
    assert fake.tables["avaliacoes_gerente_edicoes"] == []


def test_patch_inexistente_404(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))
    resp = tc.patch("/avaliacoes/nao-existe", json=_EDICAO)
    assert resp.status_code == 404


def test_patch_operacional_403(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()), cargo="operacional")
    resp = tc.patch("/avaliacoes/aval-1", json=_EDICAO)
    assert resp.status_code == 403


def test_edicoes_lista_mais_recente_primeiro(monkeypatch):
    fake = FakeClient(_seed())
    tc = _tc(monkeypatch, fake)
    tc.patch("/avaliacoes/aval-1", json=_EDICAO)
    fake.tables["avaliacoes_gerente_edicoes"][0]["criado_em"] = "2026-09-25T10:00:00+00:00"
    tc.patch("/avaliacoes/aval-1", json={**_EDICAO, "resposta_4": 3, "motivo": "segunda correção"})
    fake.tables["avaliacoes_gerente_edicoes"][1]["criado_em"] = "2026-09-25T11:00:00+00:00"

    resp = tc.get("/avaliacoes/aval-1/edicoes")

    assert resp.status_code == 200
    itens = resp.json()
    assert [i["motivo"] for i in itens] == ["segunda correção", "Theo tinha dado 4 em P1 e P2"]
    assert itens[0]["editor_nome"] == "Gabriel"


def test_historico_sem_filtro_traz_tudo_com_nomes(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))

    resp = tc.get("/avaliacoes/historico")

    assert resp.status_code == 200
    itens = resp.json()
    assert [i["id"] for i in itens] == ["aval-1", "aval-2"]  # ordenado por projeto_nome: PMO, Visus
    assert itens[0]["projeto_nome"] == "PMO"
    assert itens[0]["sprint_numero"] == 1
    assert itens[0]["operacional_nome"] == "Victor Lemos"
    assert itens[1]["modo_trabalho"] == "PULL"
    assert itens[0]["total_edicoes"] == 0
    assert itens[0]["ultima_edicao_em"] is None


def test_historico_filtra_por_projeto_e_sprint(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()))

    por_projeto = tc.get("/avaliacoes/historico", params={"project_id": "proj-2"}).json()
    por_sprint = tc.get("/avaliacoes/historico", params={"sprint_id": "sp-1"}).json()
    projeto_sem_sprint = tc.get("/avaliacoes/historico", params={"project_id": "proj-x"}).json()

    assert [i["id"] for i in por_projeto] == ["aval-2"]
    assert [i["id"] for i in por_sprint] == ["aval-1"]
    assert projeto_sem_sprint == []


def test_historico_operacional_403(monkeypatch):
    tc = _tc(monkeypatch, FakeClient(_seed()), cargo="operacional")
    assert tc.get("/avaliacoes/historico").status_code == 403
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `cd docudata-backend && python -m pytest tests/test_avaliacoes_historico_edicao.py -v`
Expected: FAIL — PATCH 405 / historico 404 (rotas não existem).

- [ ] **Step 5: Implementar em `routers/avaliacoes.py`**

Imports — trocar o bloco de schemas e o de pontuacao por:

```python
from models.schemas import (
    AvaliacaoEdicaoItem,
    AvaliacaoGerenteCreate,
    AvaliacaoGerenteEdicao,
    AvaliacaoGerenteResponse,
    AvaliacaoHistoricoItem,
    ConfirmarAvaliacaoResponse,
    ElegivelResponse,
    PendenciaAvaliacaoResponse,
)
from services.auth import get_current_pessoa, require_not_operacional, require_role
from services.elegibilidade import listar_vinculados_no_projeto
from services.pontuacao import calcular_e_travar_pontuacao, sincronizar_snapshot_gerente
```

Após `_EDITAVEL_HORAS = 48`:

```python
_CAMPOS_RESPOSTA = ("resposta_1", "resposta_2", "resposta_3", "resposta_4", "resposta_5", "resposta_6", "resposta_7")


def _por_id(client, tabela: str, colunas: str, ids) -> dict[str, dict]:
    ids = list({i for i in ids if i})
    if not ids:
        return {}
    rows = client.table(tabela).select(colunas).in_("id", ids).execute().data or []
    return {r["id"]: r for r in rows}


def _montar_historico(client, avaliacoes: list[dict]) -> list[dict]:
    """Enriquece avaliações com nomes (projeto, sprint, operacional, avaliador)
    e resumo de edições, em lote — uma query por tabela, não por linha."""
    if not avaliacoes:
        return []
    sprints = _por_id(client, "sprints", "id, numero, project_id", [a["sprint_id"] for a in avaliacoes])
    projetos = _por_id(client, "projects", "id, name, modo_trabalho", [s["project_id"] for s in sprints.values()])
    operacionais = _por_id(client, "operacionais", "id, nome", [a["operacional_id"] for a in avaliacoes])
    edicoes = (
        client.table("avaliacoes_gerente_edicoes")
        .select("avaliacao_id, editor_id, criado_em")
        .in_("avaliacao_id", [a["id"] for a in avaliacoes])
        .execute()
        .data or []
    )
    pessoas = _por_id(
        client, "pessoa", "id, nome",
        [a["gerente_id"] for a in avaliacoes] + [e["editor_id"] for e in edicoes],
    )

    total: dict[str, int] = {}
    ultima: dict[str, dict] = {}
    for e in edicoes:
        aid = e["avaliacao_id"]
        total[aid] = total.get(aid, 0) + 1
        if aid not in ultima or str(e["criado_em"]) > str(ultima[aid]["criado_em"]):
            ultima[aid] = e

    itens = []
    for a in avaliacoes:
        sprint = sprints.get(a["sprint_id"], {})
        projeto = projetos.get(sprint.get("project_id"), {})
        ult = ultima.get(a["id"])
        itens.append({
            "id": a["id"],
            "operacional_id": a["operacional_id"],
            "operacional_nome": operacionais.get(a["operacional_id"], {}).get("nome", "—"),
            "sprint_id": a["sprint_id"],
            "sprint_numero": sprint.get("numero"),
            "projeto_id": sprint.get("project_id"),
            "projeto_nome": projeto.get("name", "—"),
            "modo_trabalho": projeto.get("modo_trabalho") or "ATRIBUICAO",
            "avaliador_nome": pessoas.get(a["gerente_id"], {}).get("nome", "—"),
            **{c: a.get(c) for c in _CAMPOS_RESPOSTA},
            "criado_em": a["criado_em"],
            "total_edicoes": total.get(a["id"], 0),
            "ultima_edicao_em": ult["criado_em"] if ult else None,
            "ultima_edicao_por": pessoas.get(ult["editor_id"], {}).get("nome", "—") if ult else None,
        })
    itens.sort(key=lambda i: (i["projeto_nome"], -(i["sprint_numero"] or 0), i["operacional_nome"]))
    return itens


@router.get("/historico", response_model=list[AvaliacaoHistoricoItem])
async def historico_avaliacoes(project_id: Optional[str] = None, sprint_id: Optional[str] = None):
    """Todas as avaliações (gerente/líder/owner veem tudo — decisão da spec
    2026-09-25), filtráveis por projeto ou sprint."""
    client = get_client()
    q = client.table("avaliacoes_gerente").select("*")
    if sprint_id:
        q = q.eq("sprint_id", sprint_id)
    elif project_id:
        sprint_ids = [
            s["id"] for s in client.table("sprints").select("id").eq("project_id", project_id).execute().data or []
        ]
        if not sprint_ids:
            return []
        q = q.in_("sprint_id", sprint_ids)
    return _montar_historico(client, q.execute().data or [])


@router.patch("/{avaliacao_id}", response_model=AvaliacaoHistoricoItem)
async def editar_avaliacao(
    avaliacao_id: str,
    data: AvaliacaoGerenteEdicao,
    pessoa: dict = Depends(get_current_pessoa),
):
    """Correção de nota dada errado, sem prazo (a janela de 48h vale só pro
    questionário). Mantém o avaliador original e grava o log com motivo."""
    client = get_client()
    encontrada = client.table("avaliacoes_gerente").select("*").eq("id", avaliacao_id).execute().data
    if not encontrada:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    atual = encontrada[0]

    novas = {
        "resposta_1": data.resposta_1,
        "resposta_2": data.resposta_2,
        "resposta_3": data.resposta_3,
        "resposta_4": data.resposta_4,
        "resposta_5": data.resposta_5,
        "resposta_7": data.resposta_7,
    }
    if all(atual.get(k) == v for k, v in novas.items()):
        raise HTTPException(status_code=422, detail="Nenhuma nota alterada.")

    antes = {c: atual.get(c) for c in _CAMPOS_RESPOSTA}
    atualizada = client.table("avaliacoes_gerente").update(novas).eq("id", avaliacao_id).execute().data
    if not atualizada:
        raise HTTPException(status_code=500, detail="Falha ao salvar avaliação")
    atualizada = atualizada[0]

    client.table("avaliacoes_gerente_edicoes").insert({
        "avaliacao_id": avaliacao_id,
        "editor_id": pessoa["id"],
        "antes": antes,
        "depois": {**antes, **novas},
        "motivo": data.motivo,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }).execute()

    sincronizar_snapshot_gerente(client, atualizada)
    return _montar_historico(client, [atualizada])[0]


@router.get("/{avaliacao_id}/edicoes", response_model=list[AvaliacaoEdicaoItem])
async def listar_edicoes(avaliacao_id: str):
    client = get_client()
    rows = (
        client.table("avaliacoes_gerente_edicoes")
        .select("*")
        .eq("avaliacao_id", avaliacao_id)
        .order("criado_em", desc=True)
        .execute()
        .data or []
    )
    pessoas = _por_id(client, "pessoa", "id, nome", [r["editor_id"] for r in rows])
    return [
        {
            "id": r["id"],
            "editor_nome": pessoas.get(r["editor_id"], {}).get("nome", "—"),
            "antes": r["antes"],
            "depois": r["depois"],
            "motivo": r["motivo"],
            "criado_em": r["criado_em"],
        }
        for r in rows
    ]
```

Coloque as três rotas logo após `_buscar_ultima_avaliacao_outro_projeto` (antes de `listar_pendencias`). Não há colisão: `/historico` tem 1 segmento e as rotas `/{sprint_id}/pendencias|elegiveis|confirmar` têm sufixo literal diferente de `/edicoes`.

- [ ] **Step 6: Rodar os testes**

Run: `cd docudata-backend && python -m pytest tests/test_avaliacoes_historico_edicao.py tests/test_avaliacoes_rbac.py tests/test_avaliacoes_submit.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/supabase_schema.sql docudata-backend/models/schemas.py docudata-backend/routers/avaliacoes.py docudata-backend/tests/test_avaliacoes_historico_edicao.py
git commit -m "feat(avaliacoes): histórico, edição auditada com motivo e log de edições"
```

---

### Task 3: `POST /avaliacoes` sincroniza o snapshot

**Files:**
- Modify: `docudata-backend/routers/avaliacoes.py` (`criar_ou_atualizar_avaliacao`, antes do `return resp.data[0]`)
- Test: `docudata-backend/tests/test_avaliacoes_historico_edicao.py` (append)

**Interfaces:**
- Consumes: `sincronizar_snapshot_gerente` (Task 1), `_seed`/`_tc` (Task 2).

- [ ] **Step 1: Teste que falha** (append em `test_avaliacoes_historico_edicao.py`)

```python
def test_post_apos_fechamento_sincroniza_snapshot(monkeypatch):
    seed = _seed()
    seed["avaliacoes_gerente"] = []  # avaliação ainda não existia quando a sprint fechou
    seed["pontuacao_operacional_sprint"][0].update(gerente_media=None, gerente_pergunta3=None)
    fake = FakeClient(seed)
    tc = _tc(monkeypatch, fake)

    resp = tc.post("/avaliacoes", json={
        "operacional_id": "op-1", "sprint_id": "sp-1",
        "resposta_1": 4, "resposta_2": 4, "resposta_3": 5, "resposta_4": 5,
        "resposta_5": 5, "resposta_7": 5,
    })

    assert resp.status_code == 201
    [snap] = fake.tables["pontuacao_operacional_sprint"]
    assert snap["gerente_media"] == 4.67
    assert snap["gerente_pergunta3"] == 5
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && python -m pytest tests/test_avaliacoes_historico_edicao.py::test_post_apos_fechamento_sincroniza_snapshot -v`
Expected: FAIL — `assert None == 4.67`.

- [ ] **Step 3: Implementar** — em `criar_ou_atualizar_avaliacao`, trocar:

```python
    if not resp.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar avaliação")
    return resp.data[0]
```

por:

```python
    if not resp.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar avaliação")
    # Avaliação feita/editada depois do fechamento (permitido na janela de 48h)
    # precisa chegar ao snapshot do ranking — antes ficava com a nota antiga.
    sincronizar_snapshot_gerente(client, resp.data[0])
    return resp.data[0]
```

- [ ] **Step 4: Rodar a suíte inteira do backend**

Run: `cd docudata-backend && python -m pytest -q`
Expected: PASS, 0 falhas (os testes antigos de POST usam MagicMock, que aceita o update extra).

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/avaliacoes.py docudata-backend/tests/test_avaliacoes_historico_edicao.py
git commit -m "fix(avaliacoes): avaliação feita após o fechamento passa a refletir no ranking"
```

**Checkpoint Onda 1:** suíte backend verde → confirmar com o usuário antes da Onda 2.

---

## Onda 2 — UI

### Task 4: Perguntas compartilhadas + cliente de API

**Files:**
- Create: `docudata-frontend/app/lib/perguntasAvaliacao.ts`
- Modify: `docudata-frontend/app/components/AvaliacaoSemanalModal.tsx:11-22` (remover função local, importar)
- Modify: `docudata-frontend/app/lib/api.ts` (após `confirmarAvaliacaoSemanal`, ~linha 745)
- Modify: `docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs:14-21`
- Test: `docudata-frontend/tests/historico-avaliacoes.test.mjs`

**Interfaces:**
- Produces: `perguntas(modo: ModoTrabalho): string[]`, `CAMPOS_RESPOSTA`, `type CampoResposta`, `type ModoTrabalho`, `mediaGerente100(r: Record<CampoResposta, number>): number`; em `api.ts`: `AvaliacaoHistoricoItem`, `AvaliacaoEdicaoItem`, `getHistoricoAvaliacoes(filtros?)`, `editarAvaliacao(id, body)`, `getEdicoesAvaliacao(id)`.

- [ ] **Step 1: Teste que falha** — `docudata-frontend/tests/historico-avaliacoes.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf-8");

test("perguntas da avaliação vivem num módulo compartilhado", () => {
  const lib = read("../app/lib/perguntasAvaliacao.ts");
  assert.match(lib, /export function perguntas/);
  assert.match(lib, /Puxou e entregou num ritmo consistente\?/);
  assert.match(lib, /export const CAMPOS_RESPOSTA/);
  assert.match(lib, /export function mediaGerente100/);
  const modal = read("../app/components/AvaliacaoSemanalModal.tsx");
  assert.match(modal, /from "\.\.\/lib\/perguntasAvaliacao"/);
  assert.doesNotMatch(modal, /function perguntas\(/);
});

test("api.ts expõe histórico, edição e log de avaliações", () => {
  const api = read("../app/lib/api.ts");
  assert.match(api, /export async function getHistoricoAvaliacoes/);
  assert.match(api, /export async function editarAvaliacao/);
  assert.match(api, /export async function getEdicoesAvaliacao/);
  assert.match(api, /\/avaliacoes\/historico/);
  assert.match(api, /method: "PATCH"/);
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-frontend && node --test tests/historico-avaliacoes.test.mjs`
Expected: FAIL — ENOENT `perguntasAvaliacao.ts`.

- [ ] **Step 3: Criar `app/lib/perguntasAvaliacao.ts`**

```ts
export type ModoTrabalho = "ATRIBUICAO" | "PULL";

// Ordem das perguntas do questionário. resposta_6 (Evolução) saiu em
// 2026-09-23 — por isso a 6ª pergunta grava em resposta_7.
export const CAMPOS_RESPOSTA = [
  "resposta_1",
  "resposta_2",
  "resposta_3",
  "resposta_4",
  "resposta_5",
  "resposta_7",
] as const;

export type CampoResposta = (typeof CAMPOS_RESPOSTA)[number];

export function perguntas(modoTrabalho: ModoTrabalho): string[] {
  return [
    modoTrabalho === "PULL"
      ? "Puxou e entregou num ritmo consistente?"
      : "Entregou o que se comprometeu dentro do combinado nesta sprint?",
    "A qualidade da entrega precisou de pouca ou nenhuma correção?",
    "A pessoa destravou sozinha antes de te escalar?",
    "A comunicação da entrega foi clara a ponto de você não precisar perguntar?",
    "Ajudou, desbloqueou ou ensinou outro membro nesta sprint?",
    "Trouxe algo além do que foi pedido?",
  ];
}

// Mesma escala da dimensão Gerente no ranking: média 0-5 (2 casas) × 20.
export function mediaGerente100(r: Record<CampoResposta, number>): number {
  const soma = CAMPOS_RESPOSTA.reduce((acc, c) => acc + r[c], 0);
  const media = Math.round((soma / CAMPOS_RESPOSTA.length) * 100) / 100;
  return Math.round(media * 20 * 100) / 100;
}
```

- [ ] **Step 4: Modal importa do módulo** — em `AvaliacaoSemanalModal.tsx`, apagar a função `perguntas` (linhas 11-22) e adicionar após o import de `../lib/api`:

```ts
import { perguntas } from "../lib/perguntasAvaliacao";
```

O parâmetro `modoTrabalho: "ATRIBUICAO" | "PULL"` das Props continua igual.

- [ ] **Step 5: Atualizar teste antigo** — em `tests/modos-trabalho-avaliacao-entrega3.test.mjs`, substituir o teste "pergunta 1 da Avaliação Semanal muda de texto conforme o modo de trabalho" por:

```js
test("pergunta 1 da Avaliação Semanal muda de texto conforme o modo de trabalho", () => {
  const modal = readFileSync(
    new URL("../app/components/AvaliacaoSemanalModal.tsx", import.meta.url),
    "utf-8"
  );
  const lib = readFileSync(new URL("../app/lib/perguntasAvaliacao.ts", import.meta.url), "utf-8");
  assert.match(modal, /modoTrabalho/);
  assert.match(lib, /Puxou e entregou num ritmo consistente\?/);
});
```

- [ ] **Step 6: API em `app/lib/api.ts`** (após `confirmarAvaliacaoSemanal`)

```ts
export interface AvaliacaoHistoricoItem {
  id: string;
  operacional_id: string;
  operacional_nome: string;
  sprint_id: string;
  sprint_numero: number | null;
  projeto_id: string | null;
  projeto_nome: string;
  modo_trabalho: "ATRIBUICAO" | "PULL";
  avaliador_nome: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number | null;
  resposta_7: number;
  criado_em: string;
  total_edicoes: number;
  ultima_edicao_em: string | null;
  ultima_edicao_por: string | null;
}

export interface AvaliacaoEdicaoItem {
  id: string;
  editor_nome: string;
  antes: Record<string, number | null>;
  depois: Record<string, number | null>;
  motivo: string;
  criado_em: string;
}

export async function getHistoricoAvaliacoes(
  filtros: { project_id?: string; sprint_id?: string } = {}
): Promise<AvaliacaoHistoricoItem[]> {
  const q = new URLSearchParams();
  if (filtros.project_id) q.set("project_id", filtros.project_id);
  if (filtros.sprint_id) q.set("sprint_id", filtros.sprint_id);
  const res = await apiFetch(`${API}/avaliacoes/historico?${q}`);
  if (!res.ok) throw new Error("Erro ao carregar avaliações");
  return res.json();
}

export async function editarAvaliacao(
  id: string,
  body: {
    resposta_1: number;
    resposta_2: number;
    resposta_3: number;
    resposta_4: number;
    resposta_5: number;
    resposta_7: number;
    motivo: string;
  }
): Promise<AvaliacaoHistoricoItem> {
  const res = await apiFetch(`${API}/avaliacoes/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: unknown }).detail;
    throw new Error(typeof detail === "string" ? detail : "Erro ao salvar a edição");
  }
  return res.json();
}

export async function getEdicoesAvaliacao(id: string): Promise<AvaliacaoEdicaoItem[]> {
  const res = await apiFetch(`${API}/avaliacoes/${id}/edicoes`);
  if (!res.ok) throw new Error("Erro ao carregar histórico de edições");
  return res.json();
}
```

- [ ] **Step 7: Verificar**

Run: `cd docudata-frontend && npx tsc --noEmit -p . && npm test`
Expected: tsc sem erros; todos os testes PASS.

- [ ] **Step 8: Commit**

```bash
git add docudata-frontend/app/lib/perguntasAvaliacao.ts docudata-frontend/app/components/AvaliacaoSemanalModal.tsx docudata-frontend/app/lib/api.ts docudata-frontend/tests/historico-avaliacoes.test.mjs docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs
git commit -m "feat(avaliacoes): perguntas compartilhadas e cliente de histórico/edição"
```

---

### Task 5: Página `/avaliacoes` + link no nav

**Files:**
- Create: `docudata-frontend/app/avaliacoes/page.tsx`
- Modify: `docudata-frontend/app/page.tsx:37` (nav global)
- Test: `docudata-frontend/tests/historico-avaliacoes.test.mjs` (append)

**Interfaces:**
- Consumes: tudo que a Task 4 produz; `useAuth` de `../components/AuthGuard`.

- [ ] **Step 1: Testes que falham** (append)

```js
test("página /avaliacoes: guarda de cargo, filtros, edição com motivo e histórico", () => {
  assert.ok(existsSync(new URL("../app/avaliacoes/page.tsx", import.meta.url)));
  const page = read("../app/avaliacoes/page.tsx");
  assert.match(page, /cargo === "operacional"/);
  assert.match(page, /getHistoricoAvaliacoes/);
  assert.match(page, /editarAvaliacao/);
  assert.match(page, /getEdicoesAvaliacao/);
  assert.match(page, /Motivo da correção/);
  assert.match(page, /mediaGerente100/);
  assert.match(page, /Nenhuma avaliação/);
});

test("nav global linka /avaliacoes para gerente/líder/owner", () => {
  const home = read("../app/page.tsx");
  assert.match(home, /podeConfigurar && <Link href="\/avaliacoes"/);
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-frontend && node --test tests/historico-avaliacoes.test.mjs`
Expected: FAIL nos dois testes novos.

- [ ] **Step 3: Criar `app/avaliacoes/page.tsx`**

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "../components/AuthGuard";
import {
  editarAvaliacao,
  getEdicoesAvaliacao,
  getHistoricoAvaliacoes,
  type AvaliacaoEdicaoItem,
  type AvaliacaoHistoricoItem,
} from "../lib/api";
import { CAMPOS_RESPOSTA, mediaGerente100, perguntas, type CampoResposta } from "../lib/perguntasAvaliacao";

type Notas = Record<CampoResposta, number>;

function notasDe(a: AvaliacaoHistoricoItem): Notas {
  return {
    resposta_1: a.resposta_1,
    resposta_2: a.resposta_2,
    resposta_3: a.resposta_3,
    resposta_4: a.resposta_4,
    resposta_5: a.resposta_5,
    resposta_7: a.resposta_7,
  };
}

function formatData(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function AvaliacoesPage() {
  const auth = useAuth();
  const [itens, setItens] = useState<AvaliacaoHistoricoItem[] | null>(null);
  const [erro, setErro] = useState("");
  const [projetoId, setProjetoId] = useState("");
  const [sprintId, setSprintId] = useState("");
  const [editando, setEditando] = useState<AvaliacaoHistoricoItem | null>(null);
  const [vendoHistorico, setVendoHistorico] = useState<AvaliacaoHistoricoItem | null>(null);

  const bloqueado = auth?.cargo === "operacional";

  useEffect(() => {
    if (!auth || bloqueado) return;
    getHistoricoAvaliacoes()
      .then(setItens)
      .catch((e: Error) => setErro(e.message));
  }, [auth, bloqueado]);

  const projetos = useMemo(() => {
    const m = new Map<string, string>();
    (itens ?? []).forEach((i) => i.projeto_id && m.set(i.projeto_id, i.projeto_nome));
    return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [itens]);

  const sprintsDoProjeto = useMemo(() => {
    const m = new Map<string, number | null>();
    (itens ?? []).filter((i) => i.projeto_id === projetoId).forEach((i) => m.set(i.sprint_id, i.sprint_numero));
    return [...m.entries()].sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0));
  }, [itens, projetoId]);

  const filtrados = (itens ?? []).filter(
    (i) => (!projetoId || i.projeto_id === projetoId) && (!sprintId || i.sprint_id === sprintId)
  );

  // Agrupa projeto → sprint mantendo a ordem do backend (projeto, sprint desc, operacional).
  const grupos: { chave: string; projeto: string; sprint: number | null; linhas: AvaliacaoHistoricoItem[] }[] = [];
  filtrados.forEach((i) => {
    const chave = `${i.projeto_id}:${i.sprint_id}`;
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.chave === chave) ultimo.linhas.push(i);
    else grupos.push({ chave, projeto: i.projeto_nome, sprint: i.sprint_numero, linhas: [i] });
  });

  function onSalvo(atualizada: AvaliacaoHistoricoItem) {
    setItens((prev) => (prev ?? []).map((i) => (i.id === atualizada.id ? atualizada : i)));
    setEditando(null);
  }

  if (bloqueado) {
    return (
      <main style={pageStyle}>
        <Link href="/" style={linkVoltarStyle}>← Projetos</Link>
        <p style={{ color: "#dc2626", marginTop: 20 }}>Acesso restrito a Gerente, Líder e Owner.</p>
      </main>
    );
  }

  return (
    <main style={pageStyle}>
      <Link href="/" style={linkVoltarStyle}>← Projetos</Link>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#111116", margin: "20px 0 8px" }}>Avaliações do gerente</h1>
      <p style={{ color: "#737380", fontSize: 14, marginBottom: 24 }}>
        Notas da avaliação semanal por operacional e sprint. Corrigir uma nota atualiza o ranking.
      </p>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 24 }}>
        <label style={filtroLabelStyle}>
          Projeto
          <select
            value={projetoId}
            onChange={(e) => { setProjetoId(e.target.value); setSprintId(""); }}
            style={selectStyle}
          >
            <option value="">Todos</option>
            {projetos.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
          </select>
        </label>
        <label style={filtroLabelStyle}>
          Sprint
          <select
            value={sprintId}
            onChange={(e) => setSprintId(e.target.value)}
            disabled={!projetoId}
            style={selectStyle}
          >
            <option value="">Todas</option>
            {sprintsDoProjeto.map(([id, numero]) => <option key={id} value={id}>Sprint {numero ?? "—"}</option>)}
          </select>
        </label>
      </div>

      {erro && <p role="alert" style={{ color: "#dc2626" }}>{erro}</p>}
      {!itens && !erro && <p style={{ color: "#9696a0" }}>Carregando...</p>}
      {itens && filtrados.length === 0 && (
        <p style={{ color: "#9696a0" }}>Nenhuma avaliação registrada{projetoId ? " para este filtro" : " ainda"}.</p>
      )}

      {grupos.map((g) => (
        <section key={g.chave} style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 16, fontWeight: 800, color: "#111116", margin: "0 0 10px" }}>
            {g.projeto} <span style={{ color: "#9696a0", fontWeight: 600 }}>· Sprint {g.sprint ?? "—"}</span>
          </h2>
          <div style={{ overflowX: "auto", background: "#fff", border: "1px solid #e8e8ed", borderRadius: 12 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={thStyle}>Operacional</th>
                  <th style={thStyle}>Avaliador</th>
                  {perguntas(g.linhas[0].modo_trabalho).map((texto, idx) => (
                    <th key={idx} style={{ ...thStyle, textAlign: "center" }} title={texto}>P{idx + 1}</th>
                  ))}
                  <th style={{ ...thStyle, textAlign: "center" }}>Média</th>
                  <th style={thStyle}><span style={srOnly}>Ações</span></th>
                </tr>
              </thead>
              <tbody>
                {g.linhas.map((a) => (
                  <tr key={a.id} style={{ borderTop: "1px solid #f1f1f4" }}>
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 650, color: "#111116" }}>{a.operacional_nome}</span>
                      {a.total_edicoes > 0 && a.ultima_edicao_em && (
                        <span style={badgeEditadaStyle}>
                          editada por {a.ultima_edicao_por} em {formatData(a.ultima_edicao_em)}
                        </span>
                      )}
                    </td>
                    <td style={{ ...tdStyle, color: "#737380" }}>{a.avaliador_nome}</td>
                    {CAMPOS_RESPOSTA.map((c) => (
                      <td key={c} style={{ ...tdStyle, textAlign: "center", fontVariantNumeric: "tabular-nums" }}>{a[c]}</td>
                    ))}
                    <td style={{ ...tdStyle, textAlign: "center", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
                      {mediaGerente100(notasDe(a))}
                    </td>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap", textAlign: "right" }}>
                      <button type="button" onClick={() => setEditando(a)} style={btnLinkStyle}>Editar</button>
                      {a.total_edicoes > 0 && (
                        <button type="button" onClick={() => setVendoHistorico(a)} style={btnLinkStyle}>
                          Histórico ({a.total_edicoes})
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      {editando && <EditarModal avaliacao={editando} onClose={() => setEditando(null)} onSalvo={onSalvo} />}
      {vendoHistorico && <HistoricoModal avaliacao={vendoHistorico} onClose={() => setVendoHistorico(null)} />}
    </main>
  );
}

function EditarModal({
  avaliacao, onClose, onSalvo,
}: {
  avaliacao: AvaliacaoHistoricoItem;
  onClose: () => void;
  onSalvo: (a: AvaliacaoHistoricoItem) => void;
}) {
  const originais = notasDe(avaliacao);
  const [notas, setNotas] = useState<Notas>(originais);
  const [motivo, setMotivo] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  const mudou = CAMPOS_RESPOSTA.some((c) => notas[c] !== originais[c]);
  const podeSalvar = mudou && motivo.trim().length > 0 && !salvando;

  async function salvar() {
    setSalvando(true);
    setErro("");
    try {
      onSalvo(await editarAvaliacao(avaliacao.id, { ...notas, motivo: motivo.trim() }));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Overlay onClose={onClose} titulo={`Corrigir nota · ${avaliacao.operacional_nome}`}>
      <p style={{ fontSize: 13, color: "#737380", margin: "0 0 16px" }}>
        {avaliacao.projeto_nome} · Sprint {avaliacao.sprint_numero ?? "—"} · avaliado por {avaliacao.avaliador_nome}
      </p>
      {perguntas(avaliacao.modo_trabalho).map((texto, idx) => {
        const campo = CAMPOS_RESPOSTA[idx];
        return (
          <fieldset key={campo} style={{ border: "none", padding: 0, margin: "0 0 14px" }}>
            <legend style={{ fontSize: 13, color: "#111116", fontWeight: 600, marginBottom: 6 }}>
              {idx + 1}. {texto}
            </legend>
            <div style={{ display: "flex", gap: 6 }}>
              {[0, 1, 2, 3, 4, 5].map((n) => {
                const ativo = notas[campo] === n;
                return (
                  <button
                    key={n}
                    type="button"
                    aria-pressed={ativo}
                    onClick={() => setNotas((prev) => ({ ...prev, [campo]: n }))}
                    style={{
                      width: 36, height: 36, borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: "pointer",
                      border: ativo ? "2px solid #16a34a" : "1px solid #e8e8ed",
                      background: ativo ? "#f0fdf4" : "#fff",
                      color: "#111116",
                    }}
                  >
                    {n}
                  </button>
                );
              })}
            </div>
          </fieldset>
        );
      })}
      <label htmlFor="motivo-correcao" style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#374151", margin: "8px 0 4px" }}>
        Motivo da correção
      </label>
      <textarea
        id="motivo-correcao"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        rows={3}
        placeholder="Ex.: nota lançada errada, conversei com o gerente"
        style={{ width: "100%", boxSizing: "border-box", border: "1px solid #e8e8ed", borderRadius: 8, padding: 10, fontSize: 13, resize: "vertical" }}
      />
      {erro && <p role="alert" style={{ color: "#dc2626", fontSize: 13, marginTop: 8 }}>{erro}</p>}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
        <button type="button" onClick={onClose} style={btnGhostStyle}>Cancelar</button>
        <button type="button" onClick={salvar} disabled={!podeSalvar} style={{ ...btnPrimaryStyle, opacity: podeSalvar ? 1 : 0.5 }}>
          {salvando ? "Salvando…" : "Salvar correção"}
        </button>
      </div>
    </Overlay>
  );
}

function HistoricoModal({ avaliacao, onClose }: { avaliacao: AvaliacaoHistoricoItem; onClose: () => void }) {
  const [edicoes, setEdicoes] = useState<AvaliacaoEdicaoItem[] | null>(null);
  const [erro, setErro] = useState("");
  const textos = perguntas(avaliacao.modo_trabalho);

  useEffect(() => {
    getEdicoesAvaliacao(avaliacao.id).then(setEdicoes).catch((e: Error) => setErro(e.message));
  }, [avaliacao.id]);

  return (
    <Overlay onClose={onClose} titulo={`Histórico · ${avaliacao.operacional_nome}`}>
      {erro && <p role="alert" style={{ color: "#dc2626" }}>{erro}</p>}
      {!edicoes && !erro && <p style={{ color: "#9696a0" }}>Carregando...</p>}
      {edicoes?.map((e) => (
        <div key={e.id} style={{ borderTop: "1px solid #f1f1f4", padding: "12px 0" }}>
          <p style={{ fontSize: 12, color: "#737380", margin: "0 0 6px" }}>
            {e.editor_nome} · {formatData(e.criado_em)}
          </p>
          <ul style={{ margin: "0 0 6px", paddingLeft: 18, fontSize: 13, color: "#111116" }}>
            {CAMPOS_RESPOSTA.map((c, idx) =>
              e.antes[c] !== e.depois[c] ? (
                <li key={c} title={textos[idx]}>P{idx + 1}: {e.antes[c] ?? "—"} → {e.depois[c] ?? "—"}</li>
              ) : null
            )}
          </ul>
          <p style={{ fontSize: 13, color: "#374151", margin: 0 }}>“{e.motivo}”</p>
        </div>
      ))}
    </Overlay>
  );
}

function Overlay({ titulo, onClose, children }: { titulo: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}
    >
      <div role="dialog" aria-modal="true" aria-label={titulo} style={{ background: "#fff", borderRadius: 16, padding: "24px 28px", width: "100%", maxWidth: 520, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.18)" }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#0f172a", margin: "0 0 12px" }}>{titulo}</h3>
        {children}
      </div>
    </div>
  );
}

const pageStyle: React.CSSProperties = { maxWidth: 1000, margin: "0 auto", padding: "52px 24px" };
const linkVoltarStyle: React.CSSProperties = { fontSize: 13, color: "#9696a0" };
const filtroLabelStyle: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 4, fontSize: 11, fontWeight: 700, color: "#737380", textTransform: "uppercase", letterSpacing: "0.06em" };
const selectStyle: React.CSSProperties = { minWidth: 200, padding: "8px 10px", border: "1px solid #e8e8ed", borderRadius: 8, fontSize: 13, background: "#fff", color: "#111116", textTransform: "none", letterSpacing: 0, fontWeight: 500 };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "10px 12px", fontSize: 11, fontWeight: 700, color: "#737380", textTransform: "uppercase", letterSpacing: "0.06em", cursor: "default" };
const tdStyle: React.CSSProperties = { padding: "10px 12px", verticalAlign: "top" };
const badgeEditadaStyle: React.CSSProperties = { display: "block", marginTop: 4, fontSize: 11, color: "#b45309" };
const btnLinkStyle: React.CSSProperties = { background: "none", border: "none", color: "#16a34a", fontSize: 13, fontWeight: 650, cursor: "pointer", padding: "4px 6px" };
const btnGhostStyle: React.CSSProperties = { background: "#fff", border: "1px solid #e8e8ed", borderRadius: 8, padding: "8px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer", color: "#374151" };
const btnPrimaryStyle: React.CSSProperties = { background: "#111116", border: "none", borderRadius: 8, padding: "8px 14px", fontSize: 13, fontWeight: 700, cursor: "pointer", color: "#fff" };
const srOnly: React.CSSProperties = { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" };
```

- [ ] **Step 4: Link no nav** — em `app/page.tsx`, logo antes da linha `{podeConfigurar && <Link href="/settings" ...`:

```tsx
          {podeConfigurar && <Link href="/avaliacoes" style={navLinkStyle}>Avaliações</Link>}
```

- [ ] **Step 5: Verificar**

Run: `cd docudata-frontend && npx tsc --noEmit -p . && npm test`
Expected: tsc sem erros; todos os testes PASS.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/avaliacoes/page.tsx docudata-frontend/app/page.tsx docudata-frontend/tests/historico-avaliacoes.test.mjs
git commit -m "feat(avaliacoes): tela /avaliacoes com correção de nota e histórico de edições"
```

---

### Task 6: Verificação final

- [ ] **Step 1:** `cd docudata-backend && python -m pytest -q` → 0 falhas.
- [ ] **Step 2:** `cd docudata-frontend && npx tsc --noEmit -p . && npm test` → 0 falhas.
- [ ] **Step 3:** Avisar o usuário: rodar no Supabase o bloco "Histórico e correção de avaliações do gerente (2026-09-25)" do fim de `supabase_schema.sql` (CREATE TABLE + UPDATE retroativo) **antes** do deploy do backend — sem a tabela, `GET /avaliacoes/historico` e `PATCH` quebram. O UPDATE retroativo também corrige o caso Victor/Theo se a causa for avaliação pós-fechamento.
