# Rodada A1 — Régua, aprovação de funcionalidade e previsto da sprint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pontos viram só nível de dificuldade (1/2/3/5); sai o orçamento de 100 pontos, o preço por ponto, o valor do projeto e a comparação de modos; funcionalidades ganham aprovação do gerente; o previsto da sprint vira "foto do início + o que surgiu".

**Architecture:** Três serviços pequenos e puros concentram as regras (`services/regua.py`, `services/previsto_sprint.py`, `services/aprovacao_funcionalidade.py`) e os routers existentes passam a chamá-los. Onda 1 é só backend com pytest; Onda 2 é frontend (Next.js) com `tsc` e `npm test`. Nenhuma coluna é apagada: as que saem de uso viram órfãs comentadas.

**Tech Stack:** FastAPI + supabase-py (Python 3.12 no CI), pytest, Next.js 15 / React 19 com estilos inline e design system em `app/components/ds`, testes estruturais `node --test tests/*.test.mjs`.

**Spec:** `docs/superpowers/specs/2026-10-22-regua-aprovacao-previsto-design.md`

## Global Constraints

- Níveis válidos da régua: exatamente `(1, 2, 3, 5)`.
- Mensagem de erro da régua, literal: `Use um nível da régua: 1, 2, 3 ou 5`.
- Conversão de legado: 1→1, 2→2, 3 e 4→3, 5 ou mais→5; só em tasks com `coluna_kanban != 'concluida'`.
- Rótulos provisórios: `1 · simples`, `2 · moderada`, `3 · complexa`, `5 · muito complexa`.
- "Concluída e aprovada" = `status == 'concluida'` e `aprovada_em` não nulo.
- Previsto = soma de `pontos` das tasks da sprint com `extra = false` e (`prevista_no_inicio` ou `surgiu_na_sprint`).
- Nenhuma migração destrutiva: `sprints.pontos_orcamento`, `projects.valor_por_ponto` e `projects.valor_projeto` ficam no banco, sem uso.
- Toda mudança de schema vai para o fim de `docudata-backend/supabase_schema.sql` (aplicação manual no Supabase, avisar o usuário).
- Todos os comandos rodam a partir da raiz da worktree `../Documentador-proposta`. Backend: `cd docudata-backend && python3 -m pytest ...`. Frontend: `cd docudata-frontend && npx tsc --noEmit && npm test`.
- O teste `tests/test_security.py::test_dependencias_separam_browser_automacoes_e_webhooks_publicos` já falha localmente em Python 3.13 antes desta rodada (passa no CI em 3.12). Não é regressão; não mexer.
- Mensagens de commit em português, no estilo `feat(escopo): ...`, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Mapa de arquivos

**Backend — criar**
- `docudata-backend/services/regua.py` — níveis, rótulos, conversão de legado, ajuste na reabertura.
- `docudata-backend/services/previsto_sprint.py` — cálculo do previsto e marcas de foto/surgiu.
- `docudata-backend/services/aprovacao_funcionalidade.py` — aprovar, desfazer, revogar.
- Testes: `tests/test_regua.py`, `tests/test_previsto_sprint.py`, `tests/test_aprovacao_funcionalidade.py`, `tests/test_remocao_orcamento.py`.

**Backend — modificar**
- `tests/fake_supabase.py` (ganha `neq` e `delete`)
- `models/schemas.py`, `routers/tasks.py`, `routers/sprints.py`, `routers/projects.py`, `routers/metricas.py`, `routers/funcionalidades.py`, `routers/painel.py`, `services/sprints.py`, `services/spi_health.py`, `supabase_schema.sql`.

**Backend — apagar**
- `services/metricas_comparacao.py`, `tests/test_metricas_comparacao.py`, `tests/test_endpoint_comparacao_modos.py`, `tests/test_sprint_orcamento.py`, `tests/test_sprints_orcamento_derivado.py`, `tests/test_task_orcamento_sprint.py`, `tests/test_valor_projeto.py`.

**Frontend — modificar**
- `app/lib/api.ts`, `app/components/TasksKanbanTab.tsx`, `app/components/SprintCard.tsx`, `app/components/EscopoTab.tsx`, `app/components/MetricasTab.tsx`, `app/components/painel/IndicadoresCards.tsx`, `app/[subarea]/projects/[id]/page.tsx`, `app/components/shell/navItems.ts`, `app/components/shell/ChooserHeader.tsx`, `tests/modos-trabalho-avaliacao-entrega2.test.mjs`.

**Frontend — criar / apagar**
- Criar: `app/lib/regua.ts`, `tests/regua-aprovacao-previsto.test.mjs`.
- Apagar: `app/components/SprintOrcamentoPlanner.tsx`, `app/comparacao-modos/page.tsx` (e a pasta).

---

# ONDA 1 — Back-end

### Task 1: Régua única (serviço + validação nos schemas)

**Files:**
- Create: `docudata-backend/services/regua.py`
- Modify: `docudata-backend/models/schemas.py` (classes `TaskCreate` e `TaskUpdate`, campo `pontos`; e `TaskResponse` ganha `pontos_legado`)
- Modify: `docudata-backend/tests/fake_supabase.py`
- Test: `docudata-backend/tests/test_regua.py`

**Interfaces:**
- Produces:
  - `NIVEIS: tuple[int, ...] = (1, 2, 3, 5)`
  - `ROTULOS: dict[int, str]`
  - `MENSAGEM_NIVEL_INVALIDO: str = "Use um nível da régua: 1, 2, 3 ou 5"`
  - `converter_pontos_legado(pontos: int) -> int`
  - `ajuste_pontos_reabertura(task: dict) -> dict` — devolve `{}` se `task["pontos"]` já está na régua; senão `{"pontos": <convertido>, "pontos_legado": <original>}`.
  - `FakeClient` com `.neq(col, val)` e `.delete()` encadeável com filtros.

- [ ] **Step 1: Escrever os testes que falham**

```python
# docudata-backend/tests/test_regua.py
"""Régua única de dificuldade (spec A1 §1)."""
import pytest
from pydantic import ValidationError

from models.schemas import TaskCreate, TaskUpdate
from services.regua import (
    MENSAGEM_NIVEL_INVALIDO,
    NIVEIS,
    ROTULOS,
    ajuste_pontos_reabertura,
    converter_pontos_legado,
)


def test_niveis_da_regua():
    assert NIVEIS == (1, 2, 3, 5)
    assert ROTULOS == {1: "simples", 2: "moderada", 3: "complexa", 5: "muito complexa"}


@pytest.mark.parametrize("antigo,novo", [(1, 1), (2, 2), (3, 3), (4, 3), (5, 5), (8, 5), (13, 5)])
def test_converter_pontos_legado(antigo, novo):
    assert converter_pontos_legado(antigo) == novo


def test_ajuste_reabertura_vazio_quando_ja_esta_na_regua():
    assert ajuste_pontos_reabertura({"pontos": 3}) == {}


def test_ajuste_reabertura_converte_e_guarda_original():
    assert ajuste_pontos_reabertura({"pontos": 8}) == {"pontos": 5, "pontos_legado": 8}


@pytest.mark.parametrize("pontos", [1, 2, 3, 5])
def test_task_create_aceita_niveis(pontos):
    assert TaskCreate(project_id="p", titulo="t", pontos=pontos).pontos == pontos


@pytest.mark.parametrize("pontos", [0, 4, 8])
def test_task_create_rejeita_fora_da_regua(pontos):
    with pytest.raises(ValidationError) as exc:
        TaskCreate(project_id="p", titulo="t", pontos=pontos)
    assert MENSAGEM_NIVEL_INVALIDO in str(exc.value)


def test_task_update_rejeita_fora_da_regua_e_aceita_none():
    assert TaskUpdate().pontos is None
    with pytest.raises(ValidationError) as exc:
        TaskUpdate(pontos=4)
    assert MENSAGEM_NIVEL_INVALIDO in str(exc.value)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && python3 -m pytest tests/test_regua.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'services.regua'`.

- [ ] **Step 3: Implementar o serviço**

```python
# docudata-backend/services/regua.py
"""Régua única de dificuldade das tasks (spec A1 §1).

Os pontos de uma task são só o nível de dificuldade dela — não existe total de
pontos do projeto. Os rótulos são provisórios até o agente classificador (A2)."""

NIVEIS: tuple[int, ...] = (1, 2, 3, 5)
ROTULOS: dict[int, str] = {1: "simples", 2: "moderada", 3: "complexa", 5: "muito complexa"}
MENSAGEM_NIVEL_INVALIDO = "Use um nível da régua: 1, 2, 3 ou 5"


def converter_pontos_legado(pontos: int) -> int:
    """Nível mais próximo para pontos livres de antes da régua. Espelhada no
    UPDATE da migração em supabase_schema.sql — as duas precisam concordar."""
    if pontos <= 1:
        return 1
    if pontos == 2:
        return 2
    if pontos <= 4:
        return 3
    return 5


def ajuste_pontos_reabertura(task: dict) -> dict:
    """Task concluída antes da régua pode ter pontos fora dela; ao reabrir,
    a constraint do banco exige um nível válido. Guarda o original."""
    pontos = task.get("pontos")
    if pontos in NIVEIS or pontos is None:
        return {}
    return {"pontos": converter_pontos_legado(pontos), "pontos_legado": pontos}
```

- [ ] **Step 4: Validar nos schemas**

Em `docudata-backend/models/schemas.py`, no topo junto dos outros imports de serviço (se não houver nenhum, adicionar logo após os imports do pydantic):

```python
from services.regua import MENSAGEM_NIVEL_INVALIDO, NIVEIS
```

Em `class TaskCreate`, trocar `pontos: int = Field(..., gt=0)` por `pontos: int` e acrescentar o validador dentro da classe:

```python
    @field_validator("pontos")
    @classmethod
    def pontos_na_regua(cls, v: int) -> int:
        if v not in NIVEIS:
            raise ValueError(MENSAGEM_NIVEL_INVALIDO)
        return v
```

Em `class TaskUpdate`, trocar `pontos: Optional[int] = Field(default=None, gt=0)` por `pontos: Optional[int] = None` e acrescentar:

```python
    @field_validator("pontos")
    @classmethod
    def pontos_na_regua(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in NIVEIS:
            raise ValueError(MENSAGEM_NIVEL_INVALIDO)
        return v
```

Em `class TaskResponse`, logo abaixo de `pontos: int`, acrescentar `pontos_legado: Optional[int] = None`.

Se `services/regua.py` importar algo de `models` no futuro haverá ciclo; hoje não importa, então o import direto é seguro.

- [ ] **Step 5: Estender o FakeClient** (usado nas Tasks 4–8)

Em `docudata-backend/tests/fake_supabase.py`, dentro de `class _Query`, logo após `def eq(...)`:

```python
    def neq(self, col, val):
        self._filtros.append(lambda r: r.get(col) != val)
        return self
```

No `execute`, antes de `if self._op == "update":`:

```python
        if self._op == "delete":
            for r in casadas:
                linhas.remove(r)
            return _Resp([dict(r) for r in casadas])
```

Em `class _Table`, acrescentar:

```python
    def delete(self):
        return _Query(self._tables, self._name, "delete")
```

- [ ] **Step 6: Rodar os testes**

Run: `cd docudata-backend && python3 -m pytest tests/test_regua.py -v`
Expected: PASS (todos).

Run: `cd docudata-backend && python3 -m pytest -q`
Expected: só falham testes que criam task com pontos fora da régua (ex.: `pontos=4` ou `pontos=8` em fixtures). Para cada um, trocar o valor do payload de request para o nível mais próximo (4→3, 8→5) — são dados de teste, não comportamento. Repetir até sobrar apenas a falha pré-existente de `test_security.py`.

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/services/regua.py docudata-backend/models/schemas.py docudata-backend/tests/test_regua.py docudata-backend/tests/fake_supabase.py docudata-backend/tests
git commit -m "feat(regua): pontos de task só aceitam os níveis 1, 2, 3 e 5

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Reabrir task legada converte os pontos

**Files:**
- Modify: `docudata-backend/routers/tasks.py` (função `patch_task`, no bloco que monta `updates`)
- Test: `docudata-backend/tests/test_regua.py` (acrescentar)

**Interfaces:**
- Consumes: `ajuste_pontos_reabertura(task) -> dict` (Task 1).

- [ ] **Step 1: Teste que falha** — acrescentar a `tests/test_regua.py`:

```python
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient


def _client_task_concluida_legada():
    return FakeClient({
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": True}],
        "tasks": [{
            "id": "t1", "project_id": "p1", "sprint_id": "s1", "titulo": "Legada",
            "pontos": 8, "coluna_kanban": "concluida", "bloqueado": False,
            "checklist": [], "ordem": 0, "extra": False, "operacional_id": None,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
        }],
    })


def test_reabrir_task_legada_converte_pontos(monkeypatch, autenticar):
    import routers.tasks as tasks_router
    from main import app

    fake = _client_task_concluida_legada()
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    monkeypatch.setattr(tasks_router, "check_wip", lambda *a, **k: (True, None))
    monkeypatch.setattr(tasks_router, "on_task_transition", lambda *a, **k: False)
    monkeypatch.setattr(tasks_router, "rotear_evento_pos_fechamento", lambda *a, **k: None)
    tc = autenticar(TestClient(app))

    resp = tc.patch("/tasks/t1", json={"coluna_kanban": "em_andamento", "motivo": "voltou"})

    assert resp.status_code == 200, resp.text
    task = fake.tables["tasks"][0]
    assert task["pontos"] == 5
    assert task["pontos_legado"] == 8
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && python3 -m pytest tests/test_regua.py::test_reabrir_task_legada_converte_pontos -v`
Expected: FAIL (`assert 8 == 5`). Se falhar por chamada de tabela que o FakeClient não suporta, adicionar o método mínimo ao FakeClient no mesmo padrão da Task 1 e seguir.

- [ ] **Step 3: Implementar** — em `routers/tasks.py`, importar `from services.regua import ajuste_pontos_reabertura` e, em `patch_task`, logo depois do bloco `if houve_reabertura: updates["contador_reaberturas"] = ...`, acrescentar:

```python
    # Régua (spec A1 §5): task concluída antes da régua pode ter pontos fora
    # dela; ao sair de concluida ela volta a ser trabalho aberto e precisa de
    # um nível válido. O original fica em pontos_legado.
    if coluna_atual == "concluida" and coluna_nova is not None and coluna_nova != "concluida" and data.pontos is None:
        updates.update(ajuste_pontos_reabertura(task))
```

- [ ] **Step 4: Rodar**

Run: `cd docudata-backend && python3 -m pytest tests/test_regua.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_regua.py docudata-backend/tests/fake_supabase.py
git commit -m "feat(regua): reabrir task concluída com pontos antigos converte para a régua

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Remover orçamento, redistribuição, preço por ponto e valor do projeto

**Files:**
- Modify: `docudata-backend/routers/sprints.py` (apagar `update_orcamento` inteiro e o import de `SprintOrcamentoUpdate`; em `list_sprints` apagar a busca de `valor_por_ponto`, a soma `pontos_usados_por_sprint` e as chaves `pontos_usados` e `faturamento_previsto` do dict enriquecido)
- Modify: `docudata-backend/routers/tasks.py` (apagar `_pontos_usados_na_sprint`, `redistribuir_pontos`, o import `RedistribuirPontosRequest`, o bloco de orçamento em `create_task` — de `orcamento = sp_check.data[0].get("pontos_orcamento")` até o `raise` — e o bloco `if data.pontos is not None or data.sprint_id is not None:` inteiro em `patch_task`; em `create_task` o select de sprints vira `.select("id, iniciada")`)
- Modify: `docudata-backend/routers/projects.py` (`create_project`: apagar o `if data.valor_projeto is not None:`; `update_contrato`: apagar `valor_projeto_novo = campos.pop(...)` e todo o `if valor_projeto_novo is not None:` — o `try` passa a começar em `if not payload:`)
- Modify: `docudata-backend/models/schemas.py` (apagar `SprintOrcamentoUpdate`, `RedistribuirPontosRequest`; tirar `valor_projeto` de `ProjectCreate` e `ContratoUpdate`; tirar `valor_projeto`/`valor_por_ponto` de `ProjectResponse`; tirar `pontos_orcamento` de `SprintResponse`; tirar `pontos_usados` e `faturamento_previsto` de `SprintStatusResponse`)
- Delete: `tests/test_sprint_orcamento.py`, `tests/test_sprints_orcamento_derivado.py`, `tests/test_task_orcamento_sprint.py`, `tests/test_valor_projeto.py`
- Modify: `tests/test_task_rbac_operacional.py` (apagar `test_operacional_nao_pode_redistribuir_pontos`), `tests/test_project_modos.py` e `tests/test_sprints_avaliacao_contador.py` (tirar `valor_projeto`/`valor_por_ponto` das fixtures se a resposta validar contra o schema)
- Test: `docudata-backend/tests/test_remocao_orcamento.py`

**Interfaces:**
- Produces: `GET /projects/{id}/sprints` deixa de devolver `pontos_orcamento`, `pontos_usados` e `faturamento_previsto` (a Task 6 acrescenta `previsto`, `planejado_no_inicio` e `surgiu_na_sprint`).

- [ ] **Step 1: Testes que falham**

```python
# docudata-backend/tests/test_remocao_orcamento.py
"""Pontos são só dificuldade: não há mais orçamento, redistribuição nem preço (spec A1 §2)."""
from fastapi.testclient import TestClient

from tests.fake_supabase import FakeClient


def _app(monkeypatch, autenticar, fake):
    import routers.projects as projects_router
    import routers.sprints as sprints_router
    import routers.tasks as tasks_router
    from main import app

    for mod in (projects_router, sprints_router, tasks_router):
        monkeypatch.setattr(mod, "get_client", lambda: fake)
    return autenticar(TestClient(app))


def test_endpoint_de_orcamento_nao_existe(monkeypatch, autenticar):
    tc = _app(monkeypatch, autenticar, FakeClient())
    assert tc.patch("/sprints/s1/orcamento", json={"pontos_orcamento": 10}).status_code in (404, 405)


def test_endpoint_de_redistribuir_nao_existe(monkeypatch, autenticar):
    tc = _app(monkeypatch, autenticar, FakeClient())
    resp = tc.post("/tasks/redistribuir-pontos", json={"sprint_id": "s1", "pontos_novos": 2})
    assert resp.status_code in (404, 405)


def test_criar_task_nao_e_bloqueada_por_orcamento(monkeypatch, autenticar):
    fake = FakeClient({
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False, "pontos_orcamento": 1}],
        "tasks": [],
    })
    tc = _app(monkeypatch, autenticar, fake)
    resp = tc.post("/tasks", json={"project_id": "p1", "titulo": "Grande", "pontos": 5, "sprint_id": "s1"})
    assert resp.status_code == 201, resp.text


def test_contrato_ignora_valor_projeto(monkeypatch, autenticar):
    fake = FakeClient({"projects": [{"id": "p1", "name": "P", "client": "C", "created_at": "2026-01-01T00:00:00+00:00"}]})
    tc = _app(monkeypatch, autenticar, fake)
    resp = tc.patch("/projects/p1/contrato", json={"tolerancia_desvio_pontos": 10, "valor_projeto": 1000})
    assert resp.status_code == 200, resp.text
    assert "valor_projeto" not in fake.tables["projects"][0]
    assert "valor_por_ponto" not in resp.json()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && python3 -m pytest tests/test_remocao_orcamento.py -v`
Expected: FAIL nos quatro (endpoints ainda existem; criação bloqueada com 409; `valor_projeto` gravado).

- [ ] **Step 3: Aplicar as remoções listadas em "Files"**, apagar os quatro arquivos de teste de orçamento e o teste de RBAC de redistribuir. Em `update_contrato`, o corpo do `try` fica:

```python
    campos = data.model_dump()
    payload = {k: v for k, v in campos.items() if v is not None}

    try:
        if not payload:
            raise HTTPException(status_code=422, detail="Nenhum campo fornecido")
        for k, v in list(payload.items()):
            if hasattr(v, "isoformat"):
                payload[k] = v.isoformat()
        response = client.table("projects").update(payload).eq("id", project_id).execute()
```

(Pydantic ignora o campo extra `valor_projeto` no JSON porque o schema não declara mais o campo; é isso que o 4º teste verifica.) Atualizar a docstring de `update_contrato` para "datas, tolerância, garantia e arquétipo". Em `ProjectResponse`, como `_sanitize` filtra o retorno, conferir que `valor_projeto`/`valor_por_ponto` não aparecem no dict devolvido — se `_sanitize` usa a lista de colunas da linha 38 de `projects.py`, tirar os dois nomes dela.

- [ ] **Step 4: Rodar**

Run: `cd docudata-backend && python3 -m pytest tests/test_remocao_orcamento.py -v` → PASS.
Run: `cd docudata-backend && python3 -m pytest -q` → corrigir qualquer teste que ainda monte fixture com `pontos_orcamento`/`valor_*` *e* faça assert sobre esses campos (apagar só o assert desses campos). Deve sobrar só a falha pré-existente de `test_security.py`.

- [ ] **Step 5: Commit**

```bash
git add -A docudata-backend
git commit -m "refactor(pontos): remove orçamento de 100 pontos, redistribuição, preço por ponto e valor do projeto

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Remover a comparação de modos (backend)

**Files:**
- Modify: `docudata-backend/routers/metricas.py` (apagar o import da linha `from services.metricas_comparacao import ...` e as duas rotas `get_comparacao_modos` e `get_comparacao_modos_entre_projetos`)
- Delete: `docudata-backend/services/metricas_comparacao.py`, `tests/test_metricas_comparacao.py`, `tests/test_endpoint_comparacao_modos.py`
- Test: `docudata-backend/tests/test_remocao_orcamento.py` (acrescentar)

- [ ] **Step 1: Teste que falha** — acrescentar:

```python
def test_comparacao_de_modos_nao_existe(monkeypatch, autenticar):
    import routers.metricas as metricas_router
    fake = FakeClient({"projects": [{"id": "p1"}]})
    monkeypatch.setattr(metricas_router, "get_client", lambda: fake)
    tc = _app(monkeypatch, autenticar, fake)
    assert tc.get("/metricas/p1/comparacao-modos").status_code == 404
    assert tc.get("/metricas/comparacao-modos?projeto_ids=p1").status_code in (404, 422)
```

(`/metricas/comparacao-modos` sem a rota pode cair em `/{project_id}/...` e devolver 404 ou 422; os dois provam que a rota sumiu.)

- [ ] **Step 2: Rodar e ver falhar** — `python3 -m pytest tests/test_remocao_orcamento.py::test_comparacao_de_modos_nao_existe -v` → FAIL (200).
- [ ] **Step 3: Apagar** o que está em "Files".
- [ ] **Step 4: Rodar** — o teste passa; `python3 -m pytest -q` só com a falha pré-existente. `grep -rn metricas_comparacao docudata-backend --include=*.py` não retorna nada.
- [ ] **Step 5: Commit**

```bash
git add -A docudata-backend
git commit -m "refactor(metricas): remove a comparação de modos

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Previsto da sprint — serviço e marcas de foto/surgiu

**Files:**
- Create: `docudata-backend/services/previsto_sprint.py`
- Modify: `docudata-backend/services/sprints.py` (`iniciar_sprint_e_ancorar_tasks`)
- Modify: `docudata-backend/routers/tasks.py` (`create_task` e `patch_task`)
- Modify: `docudata-backend/models/schemas.py` (`TaskResponse` ganha `prevista_no_inicio: bool = False` e `surgiu_na_sprint: bool = False`)
- Modify: `docudata-backend/tests/test_iniciar_sprint_ancora_tasks.py` (testes unitários do helper passam a usar FakeClient)
- Test: `docudata-backend/tests/test_previsto_sprint.py`

**Interfaces:**
- Produces:
  - `previsto_da_sprint(client, sprint_id: str) -> dict` → `{"previsto": int, "planejado_no_inicio": int, "surgiu_na_sprint": int}`
  - `marcar_foto_do_inicio(client, sprint_id: str) -> None`
  - `marcas_ao_entrar_na_sprint(sprint_iniciada: bool, extra: bool) -> dict` → `{"prevista_no_inicio": bool, "surgiu_na_sprint": bool}`

- [ ] **Step 1: Testes que falham**

```python
# docudata-backend/tests/test_previsto_sprint.py
"""Previsto da sprint = foto do início + o que surgiu, sem extras (spec A1 §4)."""
from services.previsto_sprint import (
    marcar_foto_do_inicio,
    marcas_ao_entrar_na_sprint,
    previsto_da_sprint,
)
from services.sprints import iniciar_sprint_e_ancorar_tasks
from tests.fake_supabase import FakeClient


def _task(id_, pontos, sprint="s1", **extra):
    base = {"id": id_, "sprint_id": sprint, "pontos": pontos, "extra": False,
            "prevista_no_inicio": False, "surgiu_na_sprint": False,
            "coluna_kanban": "planejado", "entrou_em_andamento_em": None}
    base.update(extra)
    return base


def test_previsto_soma_foto_e_surgiu_sem_extras():
    fake = FakeClient({"tasks": [
        _task("a", 3, prevista_no_inicio=True),
        _task("b", 2, prevista_no_inicio=True),
        _task("c", 5, surgiu_na_sprint=True),
        _task("d", 5, extra=True, surgiu_na_sprint=True),
        _task("e", 1),                      # sem marca: sprint ainda não começou para ela
        _task("f", 3, sprint="s2", prevista_no_inicio=True),
    ]})
    assert previsto_da_sprint(fake, "s1") == {"previsto": 10, "planejado_no_inicio": 5, "surgiu_na_sprint": 5}


def test_previsto_sprint_vazia():
    assert previsto_da_sprint(FakeClient({"tasks": []}), "s1") == {"previsto": 0, "planejado_no_inicio": 0, "surgiu_na_sprint": 0}


def test_marcas_ao_entrar_na_sprint():
    assert marcas_ao_entrar_na_sprint(sprint_iniciada=True, extra=False) == {"prevista_no_inicio": False, "surgiu_na_sprint": True}
    assert marcas_ao_entrar_na_sprint(sprint_iniciada=True, extra=True) == {"prevista_no_inicio": False, "surgiu_na_sprint": False}
    assert marcas_ao_entrar_na_sprint(sprint_iniciada=False, extra=False) == {"prevista_no_inicio": False, "surgiu_na_sprint": False}


def test_foto_do_inicio_marca_so_nao_extras_da_sprint():
    fake = FakeClient({"tasks": [_task("a", 3), _task("b", 2, extra=True), _task("c", 1, sprint="s2")]})
    marcar_foto_do_inicio(fake, "s1")
    marcadas = {t["id"]: t["prevista_no_inicio"] for t in fake.tables["tasks"]}
    assert marcadas == {"a": True, "b": False, "c": False}


def test_iniciar_sprint_tira_a_foto_e_ancora():
    fake = FakeClient({
        "sprints": [{"id": "s1", "iniciada": False}],
        "tasks": [_task("a", 3), _task("b", 2, coluna_kanban="concluida")],
    })
    iniciar_sprint_e_ancorar_tasks(fake, "s1")
    a, b = fake.tables["tasks"]
    assert fake.tables["sprints"][0]["iniciada"] is True
    assert a["prevista_no_inicio"] is True and a["entrou_em_andamento_em"] is not None
    assert b["prevista_no_inicio"] is True and b["entrou_em_andamento_em"] is None
```

- [ ] **Step 2: Rodar e ver falhar** — `cd docudata-backend && python3 -m pytest tests/test_previsto_sprint.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementar o serviço**

```python
# docudata-backend/services/previsto_sprint.py
"""Previsto da sprint (spec A1 §4): foto das tasks no início + tasks que
surgiram depois que ela começou. Task extra nunca entra — é trabalho concedido
além do planejado."""


def marcas_ao_entrar_na_sprint(sprint_iniciada: bool, extra: bool) -> dict:
    """Marcas de uma task que acaba de entrar numa sprint (criada nela ou
    movida para ela). A foto do início pertence à sprint de origem, então
    prevista_no_inicio sempre zera; se a sprint destino ainda não começou, a
    foto será tirada quando ela começar."""
    return {"prevista_no_inicio": False, "surgiu_na_sprint": bool(sprint_iniciada and not extra)}


def marcar_foto_do_inicio(client, sprint_id: str) -> None:
    (
        client.table("tasks")
        .update({"prevista_no_inicio": True})
        .eq("sprint_id", sprint_id)
        .eq("extra", False)
        .execute()
    )


def previsto_da_sprint(client, sprint_id: str) -> dict:
    tasks = (
        client.table("tasks")
        .select("pontos, extra, prevista_no_inicio, surgiu_na_sprint")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    planejado = sum(t["pontos"] for t in tasks if not t.get("extra") and t.get("prevista_no_inicio"))
    surgiu = sum(
        t["pontos"] for t in tasks
        if not t.get("extra") and t.get("surgiu_na_sprint") and not t.get("prevista_no_inicio")
    )
    return {"previsto": planejado + surgiu, "planejado_no_inicio": planejado, "surgiu_na_sprint": surgiu}
```

- [ ] **Step 4: Tirar a foto ao iniciar** — em `services/sprints.py`, importar `from services.previsto_sprint import marcar_foto_do_inicio` e, em `iniciar_sprint_e_ancorar_tasks`, logo após o `update` que marca `iniciada: True`:

```python
    marcar_foto_do_inicio(client, sprint_id)
```

Atualizar a docstring: "…e tira a foto do previsto (tasks não extras da sprint ganham prevista_no_inicio)."

- [ ] **Step 5: Marcar ao criar e mover** — em `routers/tasks.py`, importar `from services.previsto_sprint import marcas_ao_entrar_na_sprint`.

Em `create_task`, depois do bloco que define `entrou_em_andamento_em` e antes do `insert`:

```python
    if data.sprint_id:
        sprint_iniciada = bool(sp_check.data[0].get("iniciada")) if sp_check.data else False
        payload.update(marcas_ao_entrar_na_sprint(sprint_iniciada, data.extra))
```

Em `patch_task`, depois do loop `for field in (...)` que preenche `updates`:

```python
    if data.sprint_id is not None and str(data.sprint_id) != str(task.get("sprint_id") or ""):
        sp_dest = client.table("sprints").select("iniciada").eq("id", data.sprint_id).execute()
        destino_iniciada = bool(sp_dest.data and sp_dest.data[0].get("iniciada"))
        extra_efetivo = data.extra if data.extra is not None else bool(task.get("extra"))
        updates.update(marcas_ao_entrar_na_sprint(destino_iniciada, extra_efetivo))
```

- [ ] **Step 6: Ajustar os testes antigos do helper** — em `tests/test_iniciar_sprint_ancora_tasks.py`, substituir `test_iniciar_sprint_marca_iniciada_e_ancora_tasks_pendentes` e `test_iniciar_sprint_sem_tasks_pendentes_nao_toca_tasks` (e o `_make_mock_client` se ficar sem uso) por versões com FakeClient:

```python
from tests.fake_supabase import FakeClient


def test_iniciar_sprint_marca_iniciada_e_ancora_tasks_pendentes():
    fake = FakeClient({
        "sprints": [{"id": "sprint-1", "iniciada": False}],
        "tasks": [
            {"id": "task-1", "sprint_id": "sprint-1", "coluna_kanban": "planejado", "entrou_em_andamento_em": None, "extra": False},
            {"id": "task-2", "sprint_id": "sprint-1", "coluna_kanban": "em_andamento", "entrou_em_andamento_em": None, "extra": False},
        ],
    })
    iniciar_sprint_e_ancorar_tasks(fake, "sprint-1")
    assert fake.tables["sprints"][0]["iniciada"] is True
    assert all(t["entrou_em_andamento_em"] is not None for t in fake.tables["tasks"])


def test_iniciar_sprint_sem_tasks_pendentes_nao_toca_tasks():
    fake = FakeClient({"sprints": [{"id": "sprint-1", "iniciada": False}], "tasks": []})
    iniciar_sprint_e_ancorar_tasks(fake, "sprint-1")
    assert fake.tables["sprints"][0]["iniciada"] is True
    assert fake.tables["tasks"] == []
```

- [ ] **Step 7: Rodar** — `python3 -m pytest tests/test_previsto_sprint.py tests/test_iniciar_sprint_ancora_tasks.py -v` → PASS; `python3 -m pytest -q` → só a falha pré-existente. Se algum teste MagicMock de `create_task`/`patch_task` quebrar porque o novo `select("iniciada")` em sprints não estava mockado, acrescentar `"iniciada": False` ao dado de sprint daquele mock.

- [ ] **Step 8: Commit**

```bash
git add docudata-backend
git commit -m "feat(sprint): previsto = foto do início + tasks que surgiram na sprint

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: SPI, saúde e lista de sprints usam o previsto

**Files:**
- Modify: `docudata-backend/routers/metricas.py` (`get_spi`)
- Modify: `docudata-backend/services/spi_health.py`
- Modify: `docudata-backend/routers/sprints.py` (`list_sprints`)
- Modify: `docudata-backend/models/schemas.py` (`SprintStatusResponse` ganha `previsto: int = 0`, `planejado_no_inicio: int = 0`, `surgiu_na_sprint: int = 0`)
- Test: `docudata-backend/tests/test_previsto_sprint.py` (acrescentar)

**Interfaces:**
- Consumes: `previsto_da_sprint(client, sprint_id)` (Task 5).
- Produces: `GET /metricas/{id}/spi` → itens `{"sprint_numero", "pontos_previstos", "pontos_realizados", "spi"}` com `pontos_previstos = previsto` (ou `None` quando 0); `GET /projects/{id}/sprints` com `previsto`, `planejado_no_inicio`, `surgiu_na_sprint`.

- [ ] **Step 1: Testes que falham** — acrescentar:

```python
from fastapi.testclient import TestClient

from services.spi_health import auto_update_sprint_health


def _fake_spi():
    return FakeClient({
        "projects": [{"id": "p1"}],
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "iniciada": True, "status_saude": None}],
        "tasks": [
            _task("a", 5, prevista_no_inicio=True, coluna_kanban="concluida"),
            _task("b", 3, prevista_no_inicio=True),
            _task("c", 2, surgiu_na_sprint=True, coluna_kanban="concluida"),
        ],
    })


def test_spi_usa_previsto(monkeypatch, autenticar):
    import routers.metricas as metricas_router
    from main import app
    fake = _fake_spi()
    monkeypatch.setattr(metricas_router, "get_client", lambda: fake)
    tc = autenticar(TestClient(app))
    item = tc.get("/metricas/p1/spi").json()[0]
    assert item["pontos_previstos"] == 10
    assert item["pontos_realizados"] == 7
    assert item["spi"] == 0.7


def test_saude_usa_previsto():
    fake = _fake_spi()
    assert auto_update_sprint_health(fake, "s1") == "amarelo"
    assert fake.tables["sprints"][0]["status_saude"] == "amarelo"


def test_saude_sem_previsto_nao_altera():
    fake = FakeClient({"sprints": [{"id": "s1", "status_saude": "verde"}], "tasks": []})
    assert auto_update_sprint_health(fake, "s1") is None
    assert fake.tables["sprints"][0]["status_saude"] == "verde"
```

- [ ] **Step 2: Rodar e ver falhar** — `python3 -m pytest tests/test_previsto_sprint.py -v` → os três novos falham.

- [ ] **Step 3: SPI** — em `routers/metricas.py`, importar `from services.previsto_sprint import previsto_da_sprint`; em `get_spi`, o select de sprints vira `.select("id, numero")` e o laço passa a:

```python
    for s in sprints:
        tasks = (
            client.table("tasks")
            .select("pontos, coluna_kanban, extra")
            .eq("sprint_id", s["id"])
            .execute()
            .data or []
        )
        pontos_realizados = sum(
            t["pontos"] for t in tasks if t["coluna_kanban"] == "concluida" and not t.get("extra")
        )
        previsto = previsto_da_sprint(client, s["id"])["previsto"]
        pontos_previstos = previsto or None
        spi = round(pontos_realizados / previsto, 3) if previsto > 0 else None
        result.append({
            "sprint_numero": s["numero"],
            "pontos_previstos": pontos_previstos,
            "pontos_realizados": pontos_realizados,
            "spi": spi,
        })
```

Docstring: `"""SPI por sprint: realizado (tasks concluídas, sem extras) ÷ previsto (foto do início + o que surgiu)."""`

- [ ] **Step 4: Saúde** — reescrever `services/spi_health.py`:

```python
"""
Auto-derivação de status_saude a partir do SPI da sprint.

  SPI >= 0.9 → verde · SPI >= 0.7 → amarelo · SPI < 0.7 → vermelho
  previsto = 0 (sprint sem tasks previstas) → não altera (mantém manual)

SPI = pontos concluídos (sem extras) ÷ previsto (services/previsto_sprint.py).
Chamado depois que uma task vai para concluída.
"""
from services.previsto_sprint import previsto_da_sprint


def auto_update_sprint_health(client, sprint_id: str) -> str | None:
    previsto = previsto_da_sprint(client, sprint_id)["previsto"]
    if previsto <= 0:
        return None

    tasks = (
        client.table("tasks")
        .select("pontos, coluna_kanban, extra")
        .eq("sprint_id", sprint_id)
        .execute()
        .data or []
    )
    realizados = sum(t["pontos"] for t in tasks if t["coluna_kanban"] == "concluida" and not t.get("extra"))
    spi = realizados / previsto

    if spi >= 0.9:
        novo_status = "verde"
    elif spi >= 0.7:
        novo_status = "amarelo"
    else:
        novo_status = "vermelho"

    client.table("sprints").update({"status_saude": novo_status}).eq("id", sprint_id).execute()
    return novo_status
```

- [ ] **Step 5: Lista de sprints** — em `routers/sprints.py`, importar `previsto_da_sprint` e, no dict de `enriched.append({...})`, acrescentar `**previsto_da_sprint(client, sprint["id"]),` (as chaves `pontos_usados` e `faturamento_previsto` já saíram na Task 3). Acrescentar os três campos a `SprintStatusResponse`.

- [ ] **Step 6: Rodar** — `python3 -m pytest tests/test_previsto_sprint.py tests/test_rbac_gate.py tests/test_sprints_avaliacao_contador.py -v` → PASS (se o mock MagicMock de `test_sprints_avaliacao_contador.py` não suportar a consulta extra de tasks, devolver `[]` para `tasks` nesse mock). `python3 -m pytest -q` → só a falha pré-existente.

- [ ] **Step 7: Commit**

```bash
git add docudata-backend
git commit -m "feat(spi): SPI e saúde da sprint usam o previsto no lugar do orçamento

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Aprovação de funcionalidade pelo gerente

**Files:**
- Create: `docudata-backend/services/aprovacao_funcionalidade.py`
- Modify: `docudata-backend/routers/funcionalidades.py` (duas rotas novas; `list_funcionalidades` e `get_funcionalidade` devolvem `aprovada_por_nome`; o PATCH de status chama a revogação)
- Modify: `docudata-backend/routers/tasks.py` (`create_task` e `patch_task` chamam a revogação)
- Modify: `docudata-backend/models/schemas.py` (`FuncionalidadeResponse` ganha `aprovada_em: Optional[datetime] = None`, `aprovada_por: Optional[str] = None`, `aprovada_por_nome: Optional[str] = None`)
- Test: `docudata-backend/tests/test_aprovacao_funcionalidade.py`

**Interfaces:**
- Produces:
  - `aprovar(client, funcionalidade_id: str, pessoa_id: str) -> dict` — levanta `HTTPException` 404/409.
  - `desfazer_aprovacao(client, funcionalidade_id: str, autor: str | None) -> dict` — 404/409.
  - `revogar_se_aprovada(client, funcionalidade_id: str | None, motivo: str) -> bool`
  - `nomes_dos_aprovadores(client, funcs: list[dict]) -> list[dict]` — devolve as funcs com `aprovada_por_nome`.
  - Rotas: `POST /funcionalidades/{id}/aprovar`, `DELETE /funcionalidades/{id}/aprovacao` (ambas `require_not_operacional`).

- [ ] **Step 1: Testes que falham**

```python
# docudata-backend/tests/test_aprovacao_funcionalidade.py
"""Funcionalidade concluída e aprovada pelo gerente (spec A1 §3)."""
from fastapi.testclient import TestClient

from services.aprovacao_funcionalidade import revogar_se_aprovada
from tests.fake_supabase import FakeClient


def _fake(status="concluida", aprovada_em=None):
    return FakeClient({
        "pessoa": [{"id": "pessoa-teste", "nome": "Gabriel"}],
        "funcionalidades": [{
            "id": "f1", "project_id": "p1", "id_funcional": "F1", "titulo": "Login",
            "criterios_aceite": [], "prioridade": "must", "status": status,
            "aprovada_em": aprovada_em, "aprovada_por": None,
            "created_at": "2026-01-01T00:00:00+00:00",
        }],
        "transicoes_status": [],
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "iniciada": False}],
        "tasks": [],
    })


def _tc(monkeypatch, autenticar, fake, cargo="gerente"):
    import routers.funcionalidades as func_router
    import routers.tasks as tasks_router
    from main import app
    monkeypatch.setattr(func_router, "get_client", lambda: fake)
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    return autenticar(TestClient(app), cargo)


def test_aprovar_funcionalidade_concluida(monkeypatch, autenticar):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 200, resp.text
    f = fake.tables["funcionalidades"][0]
    assert f["aprovada_em"] is not None and f["aprovada_por"] == "pessoa-teste"
    assert resp.json()["aprovada_por_nome"] == "Gabriel"
    t = fake.tables["transicoes_status"][0]
    assert (t["campo"], t["de"], t["para"]) == ("aprovacao", "pendente", "aprovada")


def test_aprovar_nao_concluida_409(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake(status="em_andamento")).post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 409


def test_aprovar_duas_vezes_409(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake(aprovada_em="2026-10-01T00:00:00+00:00")).post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 409


def test_operacional_nao_aprova(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake(), cargo="operacional").post("/funcionalidades/f1/aprovar")
    assert resp.status_code == 403


def test_desfazer_aprovacao(monkeypatch, autenticar):
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    resp = _tc(monkeypatch, autenticar, fake).delete("/funcionalidades/f1/aprovacao")
    assert resp.status_code == 200, resp.text
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None
    assert fake.tables["transicoes_status"][0]["para"] == "pendente"


def test_desfazer_sem_aprovacao_409(monkeypatch, autenticar):
    assert _tc(monkeypatch, autenticar, _fake()).delete("/funcionalidades/f1/aprovacao").status_code == 409


def test_revogar_se_aprovada():
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    assert revogar_se_aprovada(fake, "f1", "revogada: task reaberta") is True
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None
    assert fake.tables["transicoes_status"][0]["motivo"] == "revogada: task reaberta"
    assert revogar_se_aprovada(fake, "f1", "x") is False
    assert revogar_se_aprovada(fake, None, "x") is False


def test_task_nova_em_funcionalidade_aprovada_revoga(monkeypatch, autenticar):
    fake = _fake(aprovada_em="2026-10-01T00:00:00+00:00")
    resp = _tc(monkeypatch, autenticar, fake).post(
        "/tasks", json={"project_id": "p1", "titulo": "Ajuste", "pontos": 1, "funcionalidade_id": "f1"}
    )
    assert resp.status_code == 201, resp.text
    assert fake.tables["funcionalidades"][0]["aprovada_em"] is None
```

- [ ] **Step 2: Rodar e ver falhar** — `python3 -m pytest tests/test_aprovacao_funcionalidade.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Serviço**

```python
# docudata-backend/services/aprovacao_funcionalidade.py
"""Aprovação de funcionalidade pelo gerente (spec A1 §3).

"Concluída e aprovada" = status 'concluida' e aprovada_em preenchido. O status
não ganha valor novo para não quebrar quem já lê status. Toda mudança de
aprovação vira linha em transicoes_status com campo 'aprovacao'."""
from datetime import datetime, timezone

from fastapi import HTTPException


def _buscar(client, funcionalidade_id: str) -> dict:
    resp = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Funcionalidade not found")
    return resp.data[0]


def _registrar(client, func: dict, de: str, para: str, autor: str | None, motivo: str | None, agora: datetime) -> None:
    anterior = (
        client.table("transicoes_status")
        .select("timestamp")
        .eq("funcionalidade_id", func["id"])
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    base = anterior.data[0]["timestamp"] if anterior.data else func.get("created_at")
    duracao = None
    if base:
        inicio = datetime.fromisoformat(str(base).replace("Z", "+00:00"))
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        duracao = int((agora - inicio).total_seconds())
    client.table("transicoes_status").insert({
        "funcionalidade_id": func["id"],
        "campo": "aprovacao",
        "de": de,
        "para": para,
        "autor": autor,
        "timestamp": agora.isoformat(),
        "motivo": motivo,
        "duracao_fase_anterior_segundos": duracao,
    }).execute()


def nomes_dos_aprovadores(client, funcs: list[dict]) -> list[dict]:
    ids = sorted({f["aprovada_por"] for f in funcs if f.get("aprovada_por")})
    nomes: dict[str, str] = {}
    if ids:
        rows = client.table("pessoa").select("id, nome").in_("id", ids).execute().data or []
        nomes = {r["id"]: r["nome"] for r in rows}
    return [{**f, "aprovada_por_nome": nomes.get(f.get("aprovada_por"))} for f in funcs]


def aprovar(client, funcionalidade_id: str, pessoa_id: str) -> dict:
    func = _buscar(client, funcionalidade_id)
    if func.get("status") != "concluida":
        raise HTTPException(status_code=409, detail="Só dá para aprovar uma funcionalidade concluída.")
    if func.get("aprovada_em"):
        raise HTTPException(status_code=409, detail="Funcionalidade já está aprovada.")
    agora = datetime.now(timezone.utc)
    _registrar(client, func, "pendente", "aprovada", pessoa_id, None, agora)
    resp = client.table("funcionalidades").update({
        "aprovada_em": agora.isoformat(),
        "aprovada_por": pessoa_id,
    }).eq("id", funcionalidade_id).execute()
    return nomes_dos_aprovadores(client, resp.data)[0]


def desfazer_aprovacao(client, funcionalidade_id: str, autor: str | None) -> dict:
    func = _buscar(client, funcionalidade_id)
    if not func.get("aprovada_em"):
        raise HTTPException(status_code=409, detail="Funcionalidade não está aprovada.")
    agora = datetime.now(timezone.utc)
    _registrar(client, func, "aprovada", "pendente", autor, "desfeita pelo gerente", agora)
    resp = client.table("funcionalidades").update({
        "aprovada_em": None,
        "aprovada_por": None,
    }).eq("id", funcionalidade_id).execute()
    return nomes_dos_aprovadores(client, resp.data)[0]


def revogar_se_aprovada(client, funcionalidade_id: str | None, motivo: str) -> bool:
    """Funcionalidade aprovada que deixa de estar pronta (task reaberta, task
    nova, status mudado à mão) perde a aprovação. Devolve True se revogou."""
    if not funcionalidade_id:
        return False
    resp = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
    if not resp.data or not resp.data[0].get("aprovada_em"):
        return False
    func = resp.data[0]
    _registrar(client, func, "aprovada", "pendente", None, motivo, datetime.now(timezone.utc))
    client.table("funcionalidades").update({"aprovada_em": None, "aprovada_por": None}).eq("id", funcionalidade_id).execute()
    return True
```

- [ ] **Step 4: Rotas** — em `routers/funcionalidades.py`, acrescentar ao import do fastapi `Depends`, importar `from services.auth import require_not_operacional` e `from services.aprovacao_funcionalidade import aprovar, desfazer_aprovacao, nomes_dos_aprovadores, revogar_se_aprovada`. Antes de `@router.get("/{funcionalidade_id}", ...)`:

```python
@router.post("/{funcionalidade_id}/aprovar", response_model=FuncionalidadeResponse)
async def aprovar_funcionalidade(funcionalidade_id: str, pessoa: dict = Depends(require_not_operacional)):
    return aprovar(get_client(), funcionalidade_id, pessoa["id"])


@router.delete("/{funcionalidade_id}/aprovacao", response_model=FuncionalidadeResponse)
async def desfazer_aprovacao_funcionalidade(funcionalidade_id: str, pessoa: dict = Depends(require_not_operacional)):
    return desfazer_aprovacao(get_client(), funcionalidade_id, pessoa["id"])
```

Em `list_funcionalidades`: `return nomes_dos_aprovadores(client, response.data or [])`. Em `get_funcionalidade`: envolver o retorno com `nomes_dos_aprovadores(client, [linha])[0]`. No PATCH de funcionalidade, depois de gravar o update, se `data.status` veio e é diferente de `"concluida"`: `revogar_se_aprovada(client, funcionalidade_id, "revogada: status alterado")`.

- [ ] **Step 5: Revogar a partir das tasks** — em `routers/tasks.py`, importar `revogar_se_aprovada`.
  - `create_task`, logo após o insert bem-sucedido: `revogar_se_aprovada(client, data.funcionalidade_id, "revogada: task nova")`.
  - `patch_task`, depois do `client.table("tasks").update(updates)...`:

```python
    func_efetiva = data.funcionalidade_id if data.funcionalidade_id is not None else task.get("funcionalidade_id")
    if coluna_atual == "concluida" and coluna_nova is not None and coluna_nova != "concluida":
        revogar_se_aprovada(client, func_efetiva, "revogada: task reaberta")
    elif data.funcionalidade_id is not None and data.funcionalidade_id != task.get("funcionalidade_id"):
        revogar_se_aprovada(client, data.funcionalidade_id, "revogada: task nova")
```

- [ ] **Step 6: Rodar** — `python3 -m pytest tests/test_aprovacao_funcionalidade.py -v` → PASS; `python3 -m pytest -q` → só a pré-existente. Se o FakeClient precisar de `.single()` em alguma rota, implementar `single()` devolvendo `self` e ajustando `execute` para `_Resp(lista[0] if lista else None)` quando marcado.

- [ ] **Step 7: Commit**

```bash
git add docudata-backend
git commit -m "feat(funcionalidades): aprovação do gerente com revogação automática

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Escopo concluído do painel conta aprovadas

**Files:**
- Modify: `docudata-backend/routers/painel.py` (`calcular_bloco_a`)
- Modify: `docudata-backend/tests/test_painel_desvio_escopo.py`

- [ ] **Step 1: Teste que falha** — em `tests/test_painel_desvio_escopo.py`, trocar `_funcs` para aprovar as concluídas e acrescentar um caso de concluída não aprovada:

```python
def _funcs(total: int, aprovadas: int) -> list[dict]:
    return [
        {"id": f"f-{i}", "titulo": f"Func {i}",
         "status": "concluida" if i < aprovadas else "em_andamento",
         "aprovada_em": "2026-10-01T00:00:00+00:00" if i < aprovadas else None}
        for i in range(total)
    ]


def test_concluida_sem_aprovacao_nao_conta_no_escopo():
    funcs = _funcs(4, 1) + [{"id": "f-x", "titulo": "X", "status": "concluida", "aprovada_em": None}]
    bloco = calcular_bloco_a(_projeto(50, 50, tolerancia=100), funcs)
    assert bloco["pct_escopo_concluido"] == 20.0
```

- [ ] **Step 2: Rodar e ver falhar** — `python3 -m pytest tests/test_painel_desvio_escopo.py -v` → o novo falha (40.0).
- [ ] **Step 3: Implementar** — em `calcular_bloco_a`:

```python
    concluidas = sum(1 for f in funcs if f.get("status") == "concluida" and f.get("aprovada_em"))
```

- [ ] **Step 4: Rodar** — PASS; suíte inteira só com a pré-existente.
- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/painel.py docudata-backend/tests/test_painel_desvio_escopo.py
git commit -m "feat(painel): escopo concluído conta só funcionalidades aprovadas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Migração SQL

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (acrescentar no fim)
- Test: `docudata-backend/tests/test_regua.py` (acrescentar teste de coerência)

- [ ] **Step 1: Teste que falha** — garante que o SQL e a função Python concordam:

```python
from pathlib import Path


def test_migracao_regua_espelha_converter_pontos_legado():
    sql = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text(encoding="utf-8")
    bloco = sql.split("Rodada A1")[1]
    assert "WHEN pontos <= 1 THEN 1" in bloco
    assert "WHEN pontos = 2 THEN 2" in bloco
    assert "WHEN pontos <= 4 THEN 3" in bloco
    assert "ELSE 5" in bloco
    assert "CHECK (pontos IN (1, 2, 3, 5) OR coluna_kanban = 'concluida')" in bloco
    for coluna in ("pontos_legado", "aprovada_em", "aprovada_por", "prevista_no_inicio", "surgiu_na_sprint"):
        assert coluna in bloco
```

- [ ] **Step 2: Rodar e ver falhar** — `IndexError` (bloco ainda não existe).
- [ ] **Step 3: Acrescentar ao fim de `supabase_schema.sql`:**

```sql
-- ═══════════════════════════════════════════════════════════════
-- Rodada A1 (2026-10-22): régua única 1/2/3/5, aprovação de
-- funcionalidade pelo gerente e previsto da sprint (foto do início +
-- o que surgiu). Spec: docs/superpowers/specs/2026-10-22-regua-aprovacao-previsto-design.md
-- Aplicar imediatamente ANTES do deploy do backend desta rodada.
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS pontos_legado int;

-- Espelha services/regua.py::converter_pontos_legado. Concluídas ficam como
-- estão: o fechamento das sprints já registrou os números delas.
UPDATE tasks
SET pontos_legado = pontos,
    pontos = CASE
        WHEN pontos <= 1 THEN 1
        WHEN pontos = 2 THEN 2
        WHEN pontos <= 4 THEN 3
        ELSE 5
    END
WHERE coluna_kanban <> 'concluida' AND pontos NOT IN (1, 2, 3, 5);

ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_pontos_check;
ALTER TABLE tasks ADD CONSTRAINT tasks_pontos_check
    CHECK (pontos IN (1, 2, 3, 5) OR coluna_kanban = 'concluida');

ALTER TABLE funcionalidades ADD COLUMN IF NOT EXISTS aprovada_em  timestamptz;
ALTER TABLE funcionalidades ADD COLUMN IF NOT EXISTS aprovada_por uuid REFERENCES pessoa(id) ON DELETE SET NULL;

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS prevista_no_inicio boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS surgiu_na_sprint   boolean NOT NULL DEFAULT false;

-- Aproximação: sprints já iniciadas não têm registro de quais tasks estavam
-- lá no começo; as tasks atuais (não extras) viram a foto.
UPDATE tasks t
SET prevista_no_inicio = true
FROM sprints s
WHERE t.sprint_id = s.id AND s.iniciada = true AND t.extra = false AND t.prevista_no_inicio = false;

COMMENT ON COLUMN sprints.pontos_orcamento IS 'ORFA desde 2026-10-22 (rodada A1): orçamento de 100 pontos removido; previsto vem de services/previsto_sprint.py';
COMMENT ON COLUMN projects.valor_por_ponto  IS 'ORFA desde 2026-10-22 (rodada A1): pontos são só dificuldade';
COMMENT ON COLUMN projects.valor_projeto    IS 'ORFA desde 2026-10-22 (rodada A1): campo saiu da tela';
```

- [ ] **Step 4: Rodar** — `python3 -m pytest tests/test_regua.py -v` → PASS.
- [ ] **Step 5: Commit**

```bash
git add docudata-backend/supabase_schema.sql docudata-backend/tests/test_regua.py
git commit -m "chore(schema): migração da rodada A1 (régua, aprovação, previsto)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Fim da Onda 1.** Rodar `cd docudata-backend && python3 -m pytest -q` e confirmar: tudo passa exceto a falha pré-existente de `test_security.py`. Só então começar a Onda 2.

---

# ONDA 2 — UI e integração

### Task 10: Cliente da API

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`
- Create: `docudata-frontend/app/lib/regua.ts`

**Interfaces:**
- Produces (em `regua.ts`): `export const NIVEIS = [1, 2, 3, 5] as const; export type Nivel = typeof NIVEIS[number]; export const ROTULO_NIVEL: Record<Nivel, string>; export function rotuloNivel(p: number): string`.
- Produces (em `api.ts`): `aprovarFuncionalidade(id: string): Promise<Funcionalidade>`, `desfazerAprovacaoFuncionalidade(id: string): Promise<Funcionalidade>`; campos novos `Funcionalidade.aprovada_em/aprovada_por/aprovada_por_nome`, `SprintWithStatus.previsto/planejado_no_inicio/surgiu_na_sprint`, `Task.pontos_legado`.

- [ ] **Step 1: Criar `app/lib/regua.ts`**

```ts
/** Régua única de dificuldade (espelha docudata-backend/services/regua.py). */
export const NIVEIS = [1, 2, 3, 5] as const;
export type Nivel = (typeof NIVEIS)[number];

export const ROTULO_NIVEL: Record<Nivel, string> = {
  1: "simples",
  2: "moderada",
  3: "complexa",
  5: "muito complexa",
};

/** "3 · complexa"; valor fora da régua (task concluída antiga) mostra só o número. */
export function rotuloNivel(p: number): string {
  return (NIVEIS as readonly number[]).includes(p) ? `${p} · ${ROTULO_NIVEL[p as Nivel]}` : `${p}`;
}
```

- [ ] **Step 2: Editar `api.ts`**
  - `Project`: apagar `valor_projeto` e `valor_por_ponto`.
  - Payload de criar projeto (linha ~390) e de `updateContrato` (linha ~543): apagar `valor_projeto`.
  - `SprintWithStatus`: trocar `pontos_orcamento`, `pontos_usados`, `faturamento_previsto` por `previsto: number; planejado_no_inicio: number; surgiu_na_sprint: number;`. Se `pontos_orcamento` estiver em `Sprint`, apagar de lá também.
  - Apagar `updateSprintOrcamento`, `redistribuirPontos` (e o tipo do retorno dele), `ComparacaoModoPonto`, `getComparacaoModos`, `getComparacaoModosEntreProjetos`.
  - Na interface da funcionalidade (procurar `status_cliente` ou `criterios_aceite: string[]` para achar), acrescentar `aprovada_em?: string | null; aprovada_por?: string | null; aprovada_por_nome?: string | null;`.
  - Na interface de task, acrescentar `pontos_legado?: number | null;`.
  - Acrescentar, perto das outras funções de funcionalidade, no mesmo padrão de erro do arquivo:

```ts
export async function aprovarFuncionalidade(id: string): Promise<Funcionalidade> {
  const res = await apiFetch(`${API}/funcionalidades/${id}/aprovar`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao aprovar funcionalidade");
  }
  return res.json();
}

export async function desfazerAprovacaoFuncionalidade(id: string): Promise<Funcionalidade> {
  const res = await apiFetch(`${API}/funcionalidades/${id}/aprovacao`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao desfazer aprovação");
  }
  return res.json();
}
```

(Usar o nome real da interface de funcionalidade do arquivo no lugar de `Funcionalidade`, se for outro.)

- [ ] **Step 3: Rodar** — `cd docudata-frontend && npx tsc --noEmit`. Os erros esperados são exatamente os usos dos símbolos apagados nos componentes; anotar a lista — as Tasks 11–14 resolvem cada um. Não commitar ainda se o build quebrar: esta task é commitada junto com a Task 11.

---

### Task 11: Kanban — seletor de nível e fim da redistribuição

**Files:**
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx`

- [ ] **Step 1:** Remover o import `redistribuirPontos`, os estados `orcamentoEstourado` e `redistribuindo`, a função `handleRedistribuir`, a linha `setOrcamentoEstourado(msg.includes(...))` e o bloco JSX `{orcamentoEstourado && sprintId && (...)}`.
- [ ] **Step 2:** Trocar o input numérico de pontos (`type="number" min={1} value={pontos}`) por um `Select` do design system, mantendo id/label do campo existente:

```tsx
<Select
  id="task-pontos"
  value={String(pontos)}
  onChange={(e) => setPontos(Number(e.target.value))}
>
  {NIVEIS.map((n) => (
    <option key={n} value={n}>{rotuloNivel(n)}</option>
  ))}
</Select>
```

Importar `Select` de `./ds` (se ainda não importado) e `{ NIVEIS, rotuloNivel }` de `../lib/regua`. Estado inicial: `useState(task?.pontos && (NIVEIS as readonly number[]).includes(task.pontos) ? task.pontos : 1)`. Trocar a validação `if (pontos < 1)` por `if (!(NIVEIS as readonly number[]).includes(pontos)) { setErr("Use um nível da régua: 1, 2, 3 ou 5"); return; }`.
- [ ] **Step 3:** Nos dois chips `{task.pontos}pt` do card, trocar por `{task.pontos}pt` com `title={rotuloNivel(task.pontos)}`.
- [ ] **Step 4:** Tutorial "Pontos da task": novo texto — `"Os pontos são o nível de dificuldade da task, numa régua única para todos os projetos: 1 (simples), 2 (moderada), 3 (complexa) e 5 (muito complexa). Não existe total de pontos do projeto; os pontos só são somados dentro de uma sprint, para comparar o que foi entregue com o que estava previsto."`. No tutorial de task extra, tirar a menção a "não consome o orçamento de pontos da sprint" e escrever `"não entra no previsto da sprint e, se concluída antes do fechamento, vira bônus."`.
- [ ] **Step 5:** `npx tsc --noEmit` — sem erros neste arquivo.
- [ ] **Step 6: Commit (Tasks 10 + 11)**

```bash
git add docudata-frontend/app/lib docudata-frontend/app/components/TasksKanbanTab.tsx
git commit -m "feat(ui): seletor de nível da régua no Kanban e fim da redistribuição de pontos

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Sprints, Planejamento e Painel sem orçamento nem valor

**Files:**
- Delete: `docudata-frontend/app/components/SprintOrcamentoPlanner.tsx`
- Modify: `docudata-frontend/app/components/EscopoTab.tsx`, `docudata-frontend/app/components/SprintCard.tsx`, `docudata-frontend/app/[subarea]/projects/[id]/page.tsx`, `docudata-frontend/app/components/painel/IndicadoresCards.tsx`, `docudata-frontend/app/components/MetricasTab.tsx`

- [ ] **Step 1: EscopoTab** — apagar o import e o uso de `<SprintOrcamentoPlanner .../>` e os dois itens de tutorial "Distribuir os 100 pontos" e "Valor do projeto". Se `onSprintUpdated`/`onSprintCreated` ficarem sem uso, remover das props do EscopoTab e do lugar que as passa em `page.tsx`.
- [ ] **Step 2: SprintCard** — substituir o bloco que começa em `{sprint.pontos_orcamento == null ? (` (com "Orçamento de pontos não definido", `pontos_usados/pontos_orcamento` e `faturamento_previsto`) por:

```tsx
<span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.text2 }}>
  Previsto {sprint.previsto} pts
  {sprint.surgiu_na_sprint > 0 && ` · ${sprint.planejado_no_inicio} planejados + ${sprint.surgiu_na_sprint} surgiram na sprint`}
</span>
```

Apagar a prop/comentário "Leva à aba Planejamento, onde o orçamento de pontos é definido" se ela só servia ao estado sem orçamento.
- [ ] **Step 3: page.tsx** — apagar o aviso `totalOrcamento !== 100` (o "marcar como entregue" segue sem esse confirm); trocar `{s.pontos_orcamento != null ? ... : "sem orçamento"}` por `{`Previsto ${s.previsto} pts`}`; reescrever o tutorial "Orçamento de pontos da sprint" como `{ title: "Previsto da sprint", body: "Quando a sprint começa, as tasks que estão nela viram a foto do planejado. Tasks criadas ou movidas para a sprint depois disso entram como 'surgiram na sprint'. Previsto = planejado + o que surgiu; tasks extras ficam de fora." }`.
- [ ] **Step 4: IndicadoresCards (TempoEscopoCard)** — apagar o estado `valorProjeto`, a constante `valorTravado`, o `Field` "Valor do projeto (R$)" e a chave `valor_projeto` do `updateContrato`; a prop `sprints` só existia para `valorTravado` — removê-la do componente e de quem o chama. Trocar `INFO.escopo` por `"Funcionalidades aprovadas pelo gerente ÷ total de funcionalidades do projeto. Cada funcionalidade pesa igual."`.
- [ ] **Step 5: MetricasTab** — no `TOOLTIPS.spi`, novo texto: `"SPI = pontos concluídos ÷ pontos previstos na sprint (as tasks que estavam nela quando começou + as que surgiram depois; extras ficam de fora). 1,0 = entregou o previsto. ≥0,9 saudável (verde) · 0,7–0,9 atenção (amarelo) · <0,7 crítico (vermelho)."`. No estado vazio do SPI, trocar o texto e o botão que levam a "definir orçamento" por `"O SPI aparece quando a sprint começa com tasks dentro dela."` e remover a prop `onGoToPlanejamento` se ficar sem uso (e de quem a passa). Apagar o item de tutorial "Como definir o previsto da sprint".
- [ ] **Step 6: Rodar** — `cd docudata-frontend && npx tsc --noEmit` (sem erros nestes arquivos) e `grep -rn "pontos_orcamento\|faturamento_previsto\|valor_projeto\|SprintOrcamentoPlanner\|100 pontos" app --include=*.tsx --include=*.ts` → nada.
- [ ] **Step 7: Commit**

```bash
git add -A docudata-frontend/app
git commit -m "feat(ui): sprints mostram o previsto; sai orçamento, valor do projeto e os 100 pontos

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Remover a comparação de modos (frontend)

**Files:**
- Delete: `docudata-frontend/app/comparacao-modos/page.tsx` (e a pasta)
- Modify: `docudata-frontend/app/components/shell/navItems.ts`, `docudata-frontend/app/components/shell/ChooserHeader.tsx`, `docudata-frontend/app/components/MetricasTab.tsx`, `docudata-frontend/tests/modos-trabalho-avaliacao-entrega2.test.mjs`

- [ ] **Step 1:** Apagar a página; em `navItems.ts` e `ChooserHeader.tsx` apagar o item/link para `/comparacao-modos`; em `MetricasTab.tsx` apagar o estado, o `useEffect`/fetch de `getComparacaoModos`, o import e o bloco JSX da comparação.
- [ ] **Step 2:** Em `tests/modos-trabalho-avaliacao-entrega2.test.mjs`, apagar os `test(...)` que verificam a comparação de modos (procurar `comparacao`). Não mexer nos outros testes do arquivo.
- [ ] **Step 3:** `npx tsc --noEmit && npm test` → verdes; `grep -rni "comparacao" app tests` → nada.
- [ ] **Step 4: Commit**

```bash
git add -A docudata-frontend
git commit -m "refactor(ui): remove a comparação de modos

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Aprovação de funcionalidade na aba Escopo

**Files:**
- Modify: `docudata-frontend/app/components/EscopoTab.tsx`

**Interfaces:**
- Consumes: `aprovarFuncionalidade`, `desfazerAprovacaoFuncionalidade` (Task 10). O cargo da sessão: usar o mesmo mecanismo que as outras telas usam para esconder ações de gerente (procurar `cargo === "operacional"` ou `isOperacional` em `app/`; reutilizar o hook/prop existente, não criar um novo).

- [ ] **Step 1:** Na linha da funcionalidade, ao lado do chip de status (`<Chip tone={statusTone(f.status)}>...`), renderizar:

```tsx
{f.status === "concluida" && (f.aprovada_em ? (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 12.5, color: ds.text2 }}>
    <Chip tone="green" dot>
      Aprovada em {new Date(f.aprovada_em).toLocaleDateString("pt-BR")}{f.aprovada_por_nome ? ` por ${f.aprovada_por_nome}` : ""}
    </Chip>
    {podeAprovar && (
      <button type="button" className="ds-text-btn" onClick={() => handleDesfazer(f.id)} disabled={aprovandoId === f.id}
        style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 12.5, color: ds.muted }}>
        Desfazer aprovação
      </button>
    )}
  </span>
) : (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
    <Chip tone="amber">Aguardando aprovação</Chip>
    {podeAprovar && (
      <Button size="sm" variant="primary" onClick={() => handleAprovar(f.id)} disabled={aprovandoId === f.id}>
        {aprovandoId === f.id ? "Aprovando..." : "Aprovar"}
      </Button>
    )}
  </span>
))}
```

(Se `Chip` não aceitar `tone="amber"`, usar o tom de atenção que o componente oferece — conferir em `app/components/ds/Chip.tsx`; se `Button` não tiver `size="sm"`, omitir.)
- [ ] **Step 2:** Estado e handlers no componente:

```tsx
const [aprovandoId, setAprovandoId] = useState<string | null>(null);

async function handleAprovar(id: string) {
  setAprovandoId(id);
  setErr("");
  try {
    const atualizada = await aprovarFuncionalidade(id);
    setFuncs((fs) => fs.map((f) => (f.id === id ? { ...f, ...atualizada } : f)));
  } catch (e) {
    setErr(e instanceof Error ? e.message : "Erro ao aprovar.");
  } finally {
    setAprovandoId(null);
  }
}

async function handleDesfazer(id: string) {
  setAprovandoId(id);
  setErr("");
  try {
    const atualizada = await desfazerAprovacaoFuncionalidade(id);
    setFuncs((fs) => fs.map((f) => (f.id === id ? { ...f, ...atualizada } : f)));
  } catch (e) {
    setErr(e instanceof Error ? e.message : "Erro ao desfazer aprovação.");
  } finally {
    setAprovandoId(null);
  }
}
```

(Usar os nomes reais do estado de lista e de erro do EscopoTab no lugar de `setFuncs`/`setErr`, e o erro já exibido pelo componente via `ErrorNotice`.) `podeAprovar` = cargo da sessão diferente de `"operacional"`.
- [ ] **Step 3:** Tutorial "Status das funcionalidades": novo texto — `"Cada funcionalidade passa por Não iniciada → Em andamento → Concluída. Concluída ainda precisa da sua aprovação: só funcionalidades aprovadas contam no 'Escopo concluído' do Painel. Se uma task dela for reaberta ou entrar task nova, a aprovação cai e ela volta a aguardar."`
- [ ] **Step 4:** `npx tsc --noEmit` → sem erros.
- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/components/EscopoTab.tsx
git commit -m "feat(ui): gerente aprova funcionalidade concluída na aba Escopo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Testes estruturais do frontend e verificação final

**Files:**
- Create: `docudata-frontend/tests/regua-aprovacao-previsto.test.mjs`

- [ ] **Step 1: Escrever os testes** (mesmo estilo dos `.test.mjs` existentes: lê o fonte e verifica presença/ausência)

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("régua do frontend espelha a do backend", () => {
  const regua = ler("app/lib/regua.ts");
  assert.match(regua, /NIVEIS = \[1, 2, 3, 5\]/);
  for (const r of ["simples", "moderada", "complexa", "muito complexa"]) assert.ok(regua.includes(r));
});

test("Kanban usa seletor de nível e não tem mais redistribuição", () => {
  const kanban = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(kanban.includes("rotuloNivel"));
  assert.ok(!kanban.includes('type="number" min={1} value={pontos}'));
  assert.ok(!kanban.includes("redistribuirPontos"));
});

test("orçamento, valor do projeto e comparação de modos saíram", () => {
  assert.ok(!existsSync(new URL("../app/components/SprintOrcamentoPlanner.tsx", import.meta.url)));
  assert.ok(!existsSync(new URL("../app/comparacao-modos/page.tsx", import.meta.url)));
  const api = ler("app/lib/api.ts");
  for (const s of ["updateSprintOrcamento", "redistribuirPontos", "getComparacaoModos", "faturamento_previsto", "valor_por_ponto"]) {
    assert.ok(!api.includes(s), s);
  }
  assert.ok(!ler("app/components/painel/IndicadoresCards.tsx").includes("valor_projeto"));
});

test("SprintCard mostra o previsto", () => {
  const card = ler("app/components/SprintCard.tsx");
  assert.ok(card.includes("sprint.previsto"));
  assert.ok(card.includes("surgiram na sprint"));
  assert.ok(!card.includes("pontos_orcamento"));
});

test("Escopo tem aprovação de funcionalidade", () => {
  const escopo = ler("app/components/EscopoTab.tsx");
  assert.ok(escopo.includes("aprovarFuncionalidade"));
  assert.ok(escopo.includes("Aguardando aprovação"));
  assert.ok(escopo.includes("Desfazer aprovação"));
});
```

- [ ] **Step 2: Rodar** — `cd docudata-frontend && npm test` → todos passam (os novos e os antigos).
- [ ] **Step 3: Verificação completa**

```bash
cd docudata-backend && python3 -m pytest -q
cd ../docudata-frontend && npx tsc --noEmit && npm test && npm run build && npm audit --omit=dev --audit-level=high
```

Expected: backend só com a falha pré-existente de `test_security.py`; frontend tudo verde, build ok, `found 0 vulnerabilities`.
- [ ] **Step 4: Commit**

```bash
git add docudata-frontend/tests/regua-aprovacao-previsto.test.mjs
git commit -m "test(ui): régua, aprovação e previsto no frontend

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Avisar o usuário** da migração manual (bloco "Rodada A1" no fim de `supabase_schema.sql`) e da ordem de deploy: migração imediatamente antes do backend, frontend em seguida.
