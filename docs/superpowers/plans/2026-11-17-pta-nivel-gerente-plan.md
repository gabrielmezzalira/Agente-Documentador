# PTA e nível escolhido pelo gerente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a subárea PTA (processo seletivo do CITi) fora das métricas reais do CITi e permitir que gerente/líder/owner escolham o nível (1/2/3/5) de uma task sem passar pelo classificador.

**Architecture:** PTA é só mais um valor de `projects.subarea`: o literal do backend, os filtros e o front ganham `pta`; o ranking (`/performance`) filtra por `escopo` em Python depois de ler `projects.subarea`; o aprendizado do classificador ignora tasks de projetos PTA. O nível manual é um status novo (`manual`) em `task_classificacoes`, gravado por um caminho que não chama o modelo (criação com `nivel_gerente` e endpoint `POST /tasks/{id}/nivel-gerente`); a lógica fica em `services/classificador_ciclo.py` e as rotas só validam e delegam.

**Tech Stack:** FastAPI, Pydantic, Supabase (FakeClient nos testes), pytest; Next.js 15 / React 19 com estilos inline e `app/components/ds`, `node --test`, `tsc`.

**Spec:** `docs/superpowers/specs/2026-11-17-pta-nivel-gerente-design.md` (seções 1, 2 e 3 apenas; a seção 4, bugs, é outro plano).

## Global Constraints

- Subáreas válidas: `dados`, `dev`, `produto`, `pta` (CHECK `projects_subarea_check` recriado com as quatro).
- `routers/acompanhamento.py`: padrão do filtro passa a `^(dados|dev|pta)$`. `ProjectSubareaUpdate` (Dados↔Dev) e `encaminhamento` (Produto → Dados/Dev) NÃO mudam.
- Google Docs para `pta`: usa `GOOGLE_REFRESH_TOKEN_PTA`; se vazia, usa `GOOGLE_REFRESH_TOKEN` (conta de Dados). Vale nos três pontos que escolhem a conta (`_get_services`, `_get_template_id`, `_get_root_folder_id`).
- Front: card "PTA" com a descrição "Projetos do processo seletivo do CITi."; `SUBAREAS` ganha `{ slug: "pta", label: "PTA" }`; opção PTA no seletor de `app/acompanhamento/page.tsx`. Os selects de subárea do `SprintDocModal`/`RetroModal` NÃO mudam.
- `GET /performance` ganha `escopo=citi|pta`, padrão `citi`. `citi` = projetos com subárea diferente de `pta`; `pta` = só projetos PTA. Seletor "CITi / PTA" no topo de `/performance`.
- `registrar_conclusao` e `recalcular_diario` ignoram tasks de projetos PTA. A IA ainda classifica task PTA normalmente.
- Níveis válidos: {1, 2, 3, 5}. Status novo `task_classificacoes.status = 'manual'` (CHECK recriado com `aplicada`, `em_revisao`, `provisoria`, `resolvida`, `manual`); a linha guarda `nivel_final` = nível escolhido, `criado_por` = quem escolheu, `modelo` = NULL e `versao_regua`.
- `POST /tasks` aceita `nivel_gerente: Optional[int]`; preenchido por gerente/líder/owner: a IA não é chamada, `pontos` = nível e classificação `status='manual'`; preenchido por operacional: 403; ausente: fluxo atual (IA + `opiniao_nivel`) inalterado.
- `POST /tasks/{id}/nivel-gerente` com `{ nivel }`: gerente/líder/owner com acesso ao projeto; `nivel_travado_em` preenchido: 409 "Nível já travado: a task começou"; senão atualiza `tasks.pontos`, grava classificação `tipo='reclassificacao'` com `status='manual'` e devolve a task com `classificacao_status='manual'`.
- Task manual trava normalmente quando começa; editar texto de task manual NÃO reclassifica nem manda para revisão; `resolver_revisao` não se aplica a task manual; fora do PTA, task manual concluída entra no aprendizado.
- Textos do front: "Definir o nível eu mesmo" (formulário de criação, seletor 1/2/3/5, esconde o campo de opinião), "Mudar nível" (task aberta, enquanto não travou), `Chip` "nível do gerente" no card, "definido pelo gerente" na linha de detalhe, tipo `classificacao_status` ganha `"manual"`.
- Migrações vão COMENTADAS no fim de `docudata-backend/supabase_schema.sql`, com preflight e rollback, no modelo do bloco "Migration v8". Não rodam sozinhas: avisar o usuário no final que as duas precisam rodar no Supabase antes do deploy do backend.
- Commits em português no estilo do repo (`feat(tasks): ...`), terminando com a linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Comandos de backend: `cd docudata-backend && .venv/bin/python -m pytest -q tests/<arquivo>`. Frontend: `cd docudata-frontend && node --test tests/*.test.mjs` e `npx tsc --noEmit`. Antes de push rodar as duas coisas no front.

---

## File Structure

Backend (`docudata-backend/`)
- `models/schemas.py` — `Subarea` ganha `pta`; `TaskCreate.nivel_gerente`; novo `NivelGerenteRequest`.
- `routers/acompanhamento.py`, `services/github_app.py` — aceitam `pta`.
- `services/google_docs.py` — token/template/pasta para `pta`.
- `routers/performance.py`, `services/performance.py` — parâmetro `escopo`.
- `services/classificador_aprendizado.py` — `projeto_e_pta`, ignora PTA.
- `services/classificador_ciclo.py` — `resultado_manual`, `definir_nivel_gerente`, `travar_nivel`/`reclassificar` conscientes do status `manual`.
- `routers/tasks.py` — `nivel_gerente` na criação e endpoint `/nivel-gerente`.
- `supabase_schema.sql` — duas migrações comentadas (subárea `pta`; status `manual`).
- Testes novos: `tests/test_pta_subarea.py`, `tests/test_google_pta.py`, `tests/test_pta_performance_escopo.py`, `tests/test_pta_aprendizado.py`, `tests/test_nivel_gerente.py`, `tests/test_pta_nivel_migracoes.py`.

Frontend (`docudata-frontend/`)
- `app/lib/api.ts` — `Subarea`, `getPerformance(escopo)`, tipo `classificacao_status`, `createTaskKanban`, `definirNivelGerente`.
- `app/page.tsx`, `app/components/shell/navItems.ts`, `app/[subarea]/layout.tsx`, `app/[subarea]/projects/new/page.tsx`, `app/[subarea]/projects/[id]/page.tsx`, `app/acompanhamento/page.tsx` — subárea PTA.
- `app/performance/page.tsx` — seletor de escopo.
- `app/components/TasksKanbanTab.tsx` — nível manual (criação, edição, selos).
- Teste novo: `tests/pta-nivel-gerente.test.mjs`.

---

# Onda 1 — Backend e testes

### Task 1: Subárea PTA no backend e migração do CHECK

**Files:**
- Modify: `docudata-backend/models/schemas.py:46`
- Modify: `docudata-backend/routers/acompanhamento.py:15`
- Modify: `docudata-backend/services/github_app.py:24`
- Modify: `docudata-backend/supabase_schema.sql` (fim do arquivo)
- Test: `docudata-backend/tests/test_pta_subarea.py` (novo)
- Test: `docudata-backend/tests/test_acompanhamento.py` (acrescenta um teste)

**Interfaces:**
- Consumes: `tests/test_acompanhamento.py::_tc(monkeypatch, autenticar, cargo="lider")` (já existe).
- Produces: `models.schemas.Subarea` com `"pta"`; `services.github_app.subarea_github_habilitada("pta") is True`; `GET /acompanhamento?subarea=pta` responde 200.

- [ ] **Step 1: Escrever os testes que falham**

`docudata-backend/tests/test_pta_subarea.py`:

```python
import pytest
from pydantic import ValidationError

from models.schemas import ProjectCreate, ProjectSubareaUpdate


def test_projeto_aceita_subarea_pta():
    assert ProjectCreate(name="PTA 2026", client="CITi", subarea="pta").subarea == "pta"


def test_subarea_invalida_continua_recusada():
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", client="y", subarea="rh")


def test_troca_dados_dev_nao_aceita_pta():
    with pytest.raises(ValidationError):
        ProjectSubareaUpdate(subarea="pta")


def test_github_app_aceita_pta():
    from services.github_app import subarea_github_habilitada
    assert subarea_github_habilitada("pta") is True
```

Acrescentar ao fim de `docudata-backend/tests/test_acompanhamento.py`:

```python
def test_rota_aceita_subarea_pta(monkeypatch, autenticar):
    r = _tc(monkeypatch, autenticar).get("/acompanhamento?subarea=pta")
    assert r.status_code == 200
    j = r.json()
    assert j["subarea"] == "pta" and j["kpis"]["projetos"] == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_pta_subarea.py tests/test_acompanhamento.py::test_rota_aceita_subarea_pta`
Expected: FAIL (`pta` recusado pelo literal e pelo `pattern` da rota com 422).

- [ ] **Step 3: Implementar**

`models/schemas.py` linha 46:

```python
Subarea = Literal["dados", "dev", "produto", "pta"]
```

`routers/acompanhamento.py` linha 15, trocar o `pattern`:

```python
def get_acompanhamento(subarea: str = Query("dados", pattern="^(dados|dev|pta)$"), gerente_email: str | None = Query(None),
```

`services/github_app.py` linha 24:

```python
_SUBAREAS_SUPORTADAS = {"dados", "dev", "produto", "pta"}
```

Anexar ao FIM de `supabase_schema.sql`:

```sql

-- =============================================================================
-- Migration v11 (2026-11-17): subárea PTA (processo seletivo do CITi)
-- Spec: docs/superpowers/specs/2026-11-17-pta-nivel-gerente-design.md §1
-- NÃO RODA SOZINHA. Cole no SQL Editor do Supabase ANTES do deploy do backend.
-- =============================================================================

-- Preflight (somente leitura)
-- SELECT subarea, count(*) FROM projects GROUP BY subarea ORDER BY 1;
-- SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'projects_subarea_check';

-- v11.1 — alarga o conjunto permitido (nenhum dado existente muda)
-- ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_subarea_check;
-- ALTER TABLE projects ADD CONSTRAINT projects_subarea_check
--   CHECK (subarea IN ('dados','dev','produto','pta'));

-- Rollback (só se NENHUM projeto tiver subarea = 'pta'):
-- ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_subarea_check;
-- ALTER TABLE projects ADD CONSTRAINT projects_subarea_check
--   CHECK (subarea IN ('dados','dev','produto'));
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_pta_subarea.py tests/test_acompanhamento.py tests/test_github_integration.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/routers/acompanhamento.py docudata-backend/services/github_app.py docudata-backend/supabase_schema.sql docudata-backend/tests/test_pta_subarea.py docudata-backend/tests/test_acompanhamento.py
git commit -m "$(cat <<'EOF'
feat(pta): subárea PTA no backend e migração do CHECK de subárea

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Google Docs para PTA (token com fallback para Dados)

**Files:**
- Modify: `docudata-backend/services/google_docs.py` (`_get_services` ~20-30, `_get_template_id` ~417-437, `_get_root_folder_id` ~449-458)
- Test: `docudata-backend/tests/test_google_pta.py` (novo)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `_get_services("pta")` usa `GOOGLE_REFRESH_TOKEN_PTA`, com fallback para `GOOGLE_REFRESH_TOKEN`; `_get_template_id(doc_type, "pta")` prefere `*_PTA` e reaproveita o de Dados (mesmo esquema de `produto`); `_get_root_folder_id("pta")` exige `GDRIVE_FOLDER_ID_PTA` (não cai na pasta de Dados — mesma regra de `dev`/`produto`).

- [ ] **Step 1: Escrever os testes que falham**

`docudata-backend/tests/test_google_pta.py`:

```python
import pytest


def _preparar(monkeypatch):
    import services.google_docs as google_docs

    chamadas = []
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "segredo")

    class FakeCredentials:
        def __init__(self, **kwargs):
            chamadas.append(kwargs)

        def refresh(self, _request):
            return None

    monkeypatch.setattr(google_docs, "OAuthCredentials", FakeCredentials)
    monkeypatch.setattr(google_docs, "Request", lambda: object())
    monkeypatch.setattr(google_docs, "build", lambda service, *_a, **_k: service)
    return google_docs, chamadas


def test_pta_usa_token_proprio_quando_existe(monkeypatch):
    google_docs, chamadas = _preparar(monkeypatch)
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "token-dados")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN_PTA", "token-pta")
    google_docs._get_services("pta")
    assert chamadas[0]["refresh_token"] == "token-pta"


def test_pta_sem_token_proprio_usa_o_de_dados(monkeypatch):
    google_docs, chamadas = _preparar(monkeypatch)
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "token-dados")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN_PTA", "")
    google_docs._get_services("pta")
    assert chamadas[0]["refresh_token"] == "token-dados"


def test_pta_sem_nenhum_token_falha_nomeando_o_de_dados(monkeypatch):
    google_docs, _ = _preparar(monkeypatch)
    monkeypatch.delenv("GOOGLE_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("GOOGLE_REFRESH_TOKEN_PTA", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_REFRESH_TOKEN"):
        google_docs._get_services("pta")


def test_template_de_pta_prefere_o_proprio_e_reaproveita_o_de_dados(monkeypatch):
    from services.google_docs import _get_template_id
    for nome in ("GDOCS_TEMPLATE_ID_PLANNING_PTA", "GDOCS_TEMPLATE_ID_PTA",
                 "GDOCS_TEMPLATE_ID_PLANNING", "GDOCS_TEMPLATE_ID"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("GDOCS_TEMPLATE_ID", "modelo-dados")
    assert _get_template_id("planning", "pta") == "modelo-dados"
    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PTA", "modelo-pta")
    assert _get_template_id("planning", "pta") == "modelo-pta"
    monkeypatch.setenv("GDOCS_TEMPLATE_ID_PLANNING_PTA", "planning-pta")
    assert _get_template_id("planning", "pta") == "planning-pta"


def test_pasta_raiz_de_pta_usa_env_propria_e_nunca_cai_em_dados(monkeypatch):
    from services.google_docs import _get_root_folder_id
    monkeypatch.setenv("GDRIVE_FOLDER_ID", "pasta-dados")
    monkeypatch.delenv("GDRIVE_FOLDER_ID_PTA", raising=False)
    with pytest.raises(RuntimeError, match="GDRIVE_FOLDER_ID_PTA"):
        _get_root_folder_id("pta")
    monkeypatch.setenv("GDRIVE_FOLDER_ID_PTA", "pasta-pta")
    assert _get_root_folder_id("pta") == "pasta-pta"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_google_pta.py`
Expected: FAIL ("Subárea inválida para ...").

- [ ] **Step 3: Implementar**

Em `_get_services`, antes do `else:` (depois do ramo `produto`):

```python
    elif subarea == "pta":
        # PTA tem conta própria se houver token; senão usa a conta de Dados.
        refresh_token_env = (
            "GOOGLE_REFRESH_TOKEN_PTA"
            if os.environ.get("GOOGLE_REFRESH_TOKEN_PTA", "").strip()
            else "GOOGLE_REFRESH_TOKEN"
        )
```

Em `_get_template_id`, antes do `else:`:

```python
    elif subarea == "pta":
        candidates = [
            f"{typed_env}_PTA" if typed_env else None,
            "GDOCS_TEMPLATE_ID_PTA",
            typed_env,
            "GDOCS_TEMPLATE_ID",
        ]
```

Em `_get_root_folder_id`, antes do `else:`:

```python
    elif subarea == "pta":
        env_name = "GDRIVE_FOLDER_ID_PTA"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_google_pta.py tests/test_google_produto.py tests/test_google_drive_subarea.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/google_docs.py docudata-backend/tests/test_google_pta.py
git commit -m "$(cat <<'EOF'
feat(pta): Google Docs de PTA com token próprio e fallback para Dados

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Ranking de performance com `escopo=citi|pta`

**Files:**
- Modify: `docudata-backend/services/performance.py:21-52` (`listar_pessoas_ativas_por_projeto`)
- Modify: `docudata-backend/routers/performance.py`
- Test: `docudata-backend/tests/test_pta_performance_escopo.py` (novo)

**Interfaces:**
- Consumes: `tests/test_performance_endpoint.py::_mock_client`, `_client_as`, `_LINHA` (já existem; o mock de `projects` devolve a lista `projetos` inteira, então o filtro precisa ser em Python).
- Produces: `listar_pessoas_ativas_por_projeto(client, escopo: str = "citi") -> dict[str, dict]`; `GET /performance?escopo=citi|pta` (padrão `citi`, outro valor: 422).

- [ ] **Step 1: Escrever os testes que falham**

`docudata-backend/tests/test_pta_performance_escopo.py`:

```python
from tests.test_performance_endpoint import _LINHA, _client_as, _mock_client


def _cenario():
    return _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-2", "nome": "Bia", "email": "bia@citi.com", "ativo": True, "project_id": "proj-pta"},
        ],
        pontuacao=[
            dict(_LINHA, operacional_id="op-1", projeto_id="proj-1"),
            dict(_LINHA, operacional_id="op-2", projeto_id="proj-pta"),
        ],
        projetos=[
            {"id": "proj-1", "arquetipo": "padrao", "name": "Projeto CITi", "subarea": "dados"},
            {"id": "proj-pta", "arquetipo": "padrao", "name": "PTA 2026", "subarea": "pta"},
        ],
    )


def test_padrao_e_citi_e_exclui_pta(monkeypatch):
    tc = _client_as(monkeypatch, _cenario(), "lider")
    r = tc.get("/performance")
    assert r.status_code == 200
    assert [p["projeto_id"] for p in r.json()["projetos"]] == ["proj-1"]


def test_escopo_pta_so_traz_projetos_pta(monkeypatch):
    tc = _client_as(monkeypatch, _cenario(), "lider")
    r = tc.get("/performance?escopo=pta")
    assert r.status_code == 200
    assert [p["projeto_id"] for p in r.json()["projetos"]] == ["proj-pta"]


def test_escopo_citi_explicito_igual_ao_padrao(monkeypatch):
    tc = _client_as(monkeypatch, _cenario(), "lider")
    r = tc.get("/performance?escopo=citi")
    assert [p["projeto_id"] for p in r.json()["projetos"]] == ["proj-1"]


def test_escopo_invalido_422(monkeypatch):
    tc = _client_as(monkeypatch, _cenario(), "lider")
    assert tc.get("/performance?escopo=todos").status_code == 422


def test_projeto_sem_subarea_conta_como_citi(monkeypatch):
    client = _mock_client(
        operacionais=[{"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"}],
        pontuacao=[dict(_LINHA, operacional_id="op-1", projeto_id="proj-1")],
        projetos=[{"id": "proj-1", "arquetipo": "padrao", "name": "Legado"}],
    )
    tc = _client_as(monkeypatch, client, "lider")
    assert [p["projeto_id"] for p in tc.get("/performance").json()["projetos"]] == ["proj-1"]
    assert tc.get("/performance?escopo=pta").json()["projetos"] == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_pta_performance_escopo.py`
Expected: FAIL (`test_padrao_e_citi_e_exclui_pta` traz os dois projetos; escopo inválido devolve 200).

- [ ] **Step 3: Implementar**

`services/performance.py`, substituir a assinatura e o começo de `listar_pessoas_ativas_por_projeto` (o corpo do agrupamento continua igual):

```python
def listar_pessoas_ativas_por_projeto(client, escopo: str = "citi") -> dict[str, dict]:
    """... (docstring atual) ...

    `escopo` separa o PTA das métricas reais: "citi" (padrão) só considera
    projetos cuja subárea não é `pta`; "pta" só considera os projetos PTA.
    Projeto sem subárea (legado) conta como CITi."""
    rows = (
        client.table("operacionais")
        .select("id, nome, email, ativo, project_id")
        .eq("ativo", True)
        .execute()
        .data or []
    )
    if not rows:
        return {}
    projeto_ids = list({r["project_id"] for r in rows})
    projetos_rows = client.table("projects").select("id, name, subarea").in_("id", projeto_ids).execute().data or []
    nomes_projeto = {p["id"]: p["name"] for p in projetos_rows}
    e_pta = {p["id"]: p.get("subarea") == "pta" for p in projetos_rows}
    quer_pta = escopo == "pta"
    rows = [r for r in rows if e_pta.get(r["project_id"], False) == quer_pta]
    if not rows:
        return {}
```

(manter a docstring original acrescentando o parágrafo de `escopo`; remover as linhas antigas equivalentes `projeto_ids = ...`/`projetos_rows = ...`/`nomes_projeto = ...`).

`routers/performance.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
...
@router.get("/performance", response_model=PerformanceResponse, dependencies=[Depends(require_role("lider"))])
async def performance(escopo: str = Query("citi", pattern="^(citi|pta)$"), pessoa: dict = Depends(get_current_pessoa)):
    registrar_auditoria(pessoa, "/performance", "acesso")
    ...
    for projeto_id, info in listar_pessoas_ativas_por_projeto(client, escopo).items():
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_pta_performance_escopo.py tests/test_performance_endpoint.py tests/test_performance_ranking.py tests/test_performance_sequencia.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/performance.py docudata-backend/routers/performance.py docudata-backend/tests/test_pta_performance_escopo.py
git commit -m "$(cat <<'EOF'
feat(performance): ranking separa CITi e PTA pelo parâmetro escopo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Aprendizado do classificador ignora projetos PTA

**Files:**
- Modify: `docudata-backend/services/classificador_aprendizado.py` (`registrar_conclusao`, `registrar_opiniao_operacional`, `recalcular_diario`; função nova `projeto_e_pta`)
- Test: `docudata-backend/tests/test_pta_aprendizado.py` (novo)

**Interfaces:**
- Consumes: `tests/test_classificador_aprendizado.py::_fake()` (FakeClient com `t1` concluída, sem `project_id`).
- Produces: `projeto_e_pta(client, project_id: str | None) -> bool`; `registrar_conclusao` não grava exemplo nem recalcula para task PTA; `registrar_opiniao_operacional` ignora em silêncio (no-op) a opinião em task PTA; `recalcular_diario` não tenta criar exemplo de task PTA.

- [ ] **Step 1: Escrever os testes que falham**

`docudata-backend/tests/test_pta_aprendizado.py`:

```python
import pytest
from fastapi import HTTPException

import services.classificador_aprendizado as ap
from tests.test_classificador_aprendizado import _fake


def _com_projeto(subarea):
    fake = _fake()
    fake.tables["tasks"][0]["project_id"] = "p1"
    fake.tables["projects"] = [{"id": "p1", "subarea": subarea}]
    return fake


def test_projeto_e_pta():
    fake = _com_projeto("pta")
    assert ap.projeto_e_pta(fake, "p1") is True
    assert ap.projeto_e_pta(fake, "outro") is False
    assert ap.projeto_e_pta(fake, None) is False


def test_conclusao_de_task_pta_nao_vira_exemplo_nem_calibra():
    fake = _com_projeto("pta")
    ap.registrar_conclusao(fake, "t1")
    assert fake.tables["task_aprendizado"] == []
    assert fake.tables["classificador_parametros"] == []
    assert fake.tables["classificador_parametros_hist"] == []


def test_conclusao_de_task_de_outra_subarea_continua_virando_exemplo():
    fake = _com_projeto("dados")
    ap.registrar_conclusao(fake, "t1")
    assert len(fake.tables["task_aprendizado"]) == 1


def test_opiniao_do_operacional_em_task_pta_e_ignorada_sem_erro():
    # O front abre o diálogo de opinião ao concluir; em PTA a opinião é
    # descartada em silêncio para o candidato não ver erro.
    fake = _com_projeto("pta")
    ap.registrar_opiniao_operacional(fake, "t1", 3)
    assert fake.tables["task_aprendizado"] == []


def test_recalculo_diario_pula_task_pta(monkeypatch):
    fake = _com_projeto("pta")
    fake.tables["tasks"].append({"id": "t2", "project_id": "p2", "coluna_kanban": "concluida"})
    fake.tables["projects"].append({"id": "p2", "subarea": "dev"})
    fake.tables["tasks"][0]["coluna_kanban"] = "concluida"
    criadas = []
    import services.supabase_client as sc
    monkeypatch.setattr(sc, "get_client", lambda: fake)
    monkeypatch.setattr(ap, "registrar_conclusao", lambda c, t: criadas.append(t))
    monkeypatch.setattr(ap, "recalcular_tudo", lambda c: None)
    ap.recalcular_diario()
    assert criadas == ["t2"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_pta_aprendizado.py`
Expected: FAIL (`projeto_e_pta` não existe).

- [ ] **Step 3: Implementar**

Em `services/classificador_aprendizado.py`, logo depois de `_agora()`:

```python
def projeto_e_pta(client, project_id: str | None) -> bool:
    """PTA fica fora das métricas reais: não vira exemplo nem calibra parâmetros."""
    if not project_id:
        return False
    rows = client.table("projects").select("id, subarea").eq("id", project_id).execute().data or []
    return bool(rows) and rows[0].get("subarea") == "pta"
```

Em `registrar_conclusao`, incluir `project_id` no select e sair cedo:

```python
    resp = client.table("tasks").select("id, project_id, pontos, operacional_id, pull_em, entrou_em_andamento_em, updated_at").eq("id", task_id).execute()
    if not resp.data:
        return
    task = resp.data[0]
    if projeto_e_pta(client, task.get("project_id")):
        return
```

Em `registrar_opiniao_operacional`, antes da função interna `_existe`:

```python
    tarefa = client.table("tasks").select("id, project_id").eq("id", task_id).execute().data
    if tarefa and projeto_e_pta(client, tarefa[0].get("project_id")):
        return
```

Em `recalcular_diario`, trocar o cálculo de `concluidas`:

```python
        pta = {r["id"] for r in ler_tudo(lambda: client.table("projects").select("id").eq("subarea", "pta").order("id"))}
        concluidas = {
            r["id"]
            for r in ler_tudo(lambda: client.table("tasks").select("id, project_id").eq("coluna_kanban", "concluida").order("id"))
            if r.get("project_id") not in pta
        }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_pta_aprendizado.py tests/test_classificador_aprendizado.py tests/test_classificador_ciclo.py`
Expected: PASS (inclusive `test_recalcular_diario_cria_exemplo_faltante`: lá as tasks não têm `project_id`, logo `None not in pta`).

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/classificador_aprendizado.py docudata-backend/tests/test_pta_aprendizado.py
git commit -m "$(cat <<'EOF'
feat(classificador): aprendizado ignora tasks de projetos PTA

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Status `manual` no ciclo do classificador (serviço + migração)

**Files:**
- Modify: `docudata-backend/services/classificador_ciclo.py` (`gravar_classificacao`, `travar_nivel`, `reclassificar`; funções novas `resultado_manual`, `definir_nivel_gerente`)
- Modify: `docudata-backend/supabase_schema.sql` (fim do arquivo)
- Test: `docudata-backend/tests/test_nivel_gerente.py` (novo, parte de serviço)
- Test: `docudata-backend/tests/test_pta_nivel_migracoes.py` (novo)

**Interfaces:**
- Consumes: `ciclo.gravar_classificacao(client, task_id, resultado, *, tipo, criado_por, texto)`, `ciclo._travar_se_em_trabalho(client, task)`, `ciclo.classificacao_atual(client, task_id)` (já existem).
- Produces:
  - `ciclo.resultado_manual(nivel: int) -> dict` (`status="manual"`, `nivel_final=nivel`, colunas de classificação `None`, `faltando=[]`, `ajuste_tempo=0`, `vetor=None`).
  - `ciclo.definir_nivel_gerente(client, task_id: str, nivel: int, pessoa_id: str) -> dict` — levanta 404 (task inexistente), 409 `"Nível já travado: a task começou"`, 409 se concluída; grava `tipo='reclassificacao'`, `status='manual'`; trava se a task já está em trabalho; devolve o resultado manual.
  - `travar_nivel` passa a travar task com classificação `manual`; `reclassificar` devolve 409 para task `manual`.

- [ ] **Step 1: Escrever os testes que falham**

`docudata-backend/tests/test_nivel_gerente.py` (helpers copiados de `test_classificador_ciclo.py`; o arquivo cresce nas Tasks 6 e 7):

```python
"""Nível escolhido pelo gerente (spec PTA §3)."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import services.classificador_ciclo as ciclo
from tests.fake_supabase import FakeClient

pytestmark = pytest.mark.classificador_real


def _fake():
    return FakeClient({
        "projects": [{"id": "p1", "modo_trabalho": "ATRIBUICAO"}],
        "sprints": [{"id": "s1", "project_id": "p1", "numero": 1, "iniciada": False},
                    {"id": "s2", "project_id": "p1", "numero": 2, "iniciada": True}],
        "operacionais": [{"id": "op1", "project_id": "p1", "email": "pessoa@citi.org.br"}],
        "tasks": [], "task_classificacoes": [], "task_aprendizado": [],
    }, defaults={"tasks": {"bloqueado": False, "created_at": "2026-01-01T00:00:00+00:00",
                           "updated_at": "2026-01-01T00:00:00+00:00"}})


def _task(**kw):
    base = {"id": "t1", "project_id": "p1", "titulo": "Login", "descricao": "d", "checklist": [],
            "pontos": 2, "coluna_kanban": "planejado", "ordem": 0, "bloqueado": False,
            "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
            "nivel_travado_em": None, "sprint_id": "s1"}
    base.update(kw)
    return base


def _clas(status="aplicada", nivel=3, task_id="t1", criado_em="2026-01-01T00:00:00+00:00", **kw):
    return {"id": f"c-{status}-{criado_em}", "task_id": task_id, "tipo": "criacao", "criado_por": "pessoa-teste",
            "criado_em": criado_em, "status": status, "nivel_final": nivel, **kw}


def _tc(monkeypatch, autenticar, fake, cargo="gerente"):
    import routers.tasks as tasks_router
    from main import app
    monkeypatch.setattr(tasks_router, "get_client", lambda: fake)
    monkeypatch.setattr(ciclo, "get_client", lambda: fake)
    return autenticar(TestClient(app), cargo)


# --- serviço ---

def test_resultado_manual_tem_o_formato_de_classificacao():
    r = ciclo.resultado_manual(5)
    assert r["status"] == "manual" and r["nivel_final"] == 5
    assert r["faltando"] == [] and r["vetor"] is None and r["ajuste_tempo"] == 0
    assert r["nivel_geral"] is None and r["opiniao_gerente"] is None


def test_gravar_classificacao_manual_nao_registra_modelo():
    fake = _fake()
    fake.tables["tasks"].append(_task())
    ciclo.gravar_classificacao(fake, "t1", ciclo.resultado_manual(3), tipo="criacao", criado_por="g1", texto="")
    linha = fake.tables["task_classificacoes"][0]
    assert linha["status"] == "manual" and linha["modelo"] is None and linha["nivel_final"] == 3
    assert linha["criado_por"] == "g1" and linha["versao_regua"]
    assert fake.tables["tasks"][0]["pontos"] == 3


def test_definir_nivel_gerente_grava_reclassificacao_manual_e_atualiza_pontos():
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("em_revisao", 2))
    ciclo.definir_nivel_gerente(fake, "t1", 5, "g1")
    novas = [c for c in fake.tables["task_classificacoes"] if c["tipo"] == "reclassificacao"]
    assert len(novas) == 1 and novas[0]["status"] == "manual" and novas[0]["criado_por"] == "g1"
    assert fake.tables["tasks"][0]["pontos"] == 5
    assert fake.tables["tasks"][0]["nivel_travado_em"] is None  # planejado: segue destravada


def test_definir_nivel_gerente_em_andamento_trava_em_seguida():
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="em_andamento"))
    fake.tables["task_classificacoes"].append(_clas("provisoria", 2))
    ciclo.definir_nivel_gerente(fake, "t1", 3, "g1")
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


def test_definir_nivel_gerente_travada_409():
    fake = _fake()
    fake.tables["tasks"].append(_task(nivel_travado_em="2026-01-02T00:00:00+00:00"))
    with pytest.raises(HTTPException) as exc:
        ciclo.definir_nivel_gerente(fake, "t1", 3, "g1")
    assert exc.value.status_code == 409 and exc.value.detail == "Nível já travado: a task começou"
    assert fake.tables["task_classificacoes"] == []


def test_definir_nivel_gerente_concluida_409_e_inexistente_404():
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="concluida"))
    with pytest.raises(HTTPException) as exc:
        ciclo.definir_nivel_gerente(fake, "t1", 3, "g1")
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc2:
        ciclo.definir_nivel_gerente(fake, "nao-existe", 3, "g1")
    assert exc2.value.status_code == 404


def test_travar_nivel_trava_task_manual():
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    ciclo.travar_nivel(fake, ["t1"])
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


async def test_reclassificar_task_manual_409():
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    with pytest.raises(HTTPException) as exc:
        await ciclo.reclassificar(fake, "t1", "lider-1")
    assert exc.value.status_code == 409
    assert len(fake.tables["task_classificacoes"]) == 1


def test_resolver_revisao_nao_se_aplica_a_task_manual():
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    with pytest.raises(HTTPException) as exc:
        ciclo.resolver_revisao(fake, "t1", 2, "motivo", "lider-1")
    assert exc.value.status_code == 409
```

`docudata-backend/tests/test_pta_nivel_migracoes.py`:

```python
from pathlib import Path

SCHEMA = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text(encoding="utf-8")


def _bloco(titulo: str) -> str:
    inicio = SCHEMA.index(titulo)
    return SCHEMA[inicio:]


def test_migracao_subarea_pta_comentada_com_preflight_e_rollback():
    b = _bloco("Migration v11 (2026-11-17): subárea PTA")
    assert "CHECK (subarea IN ('dados','dev','produto','pta'))" in b
    assert "Preflight" in b and "Rollback" in b
    for linha in b.split("Migration v12")[0].splitlines():
        assert not linha.strip() or linha.startswith("--"), linha


def test_migracao_status_manual_comentada_com_preflight_e_rollback():
    b = _bloco("Migration v12 (2026-11-17): status manual")
    assert "'aplicada','em_revisao','provisoria','resolvida','manual'" in b
    assert "Preflight" in b and "Rollback" in b
    for linha in b.splitlines():
        assert not linha.strip() or linha.startswith("--"), linha
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_nivel_gerente.py tests/test_pta_nivel_migracoes.py`
Expected: FAIL (`resultado_manual`/`definir_nivel_gerente` não existem; bloco v12 ausente).

- [ ] **Step 3: Implementar**

`services/classificador_ciclo.py`:

1. Depois de `_resultado_provisorio`:

```python
def resultado_manual(nivel: int) -> dict:
    """Nível escolhido pelo gerente: não passa pelo modelo (spec PTA §3)."""
    r = {c: None for c in _COLUNAS_CLASSIFICACAO}
    r.update({
        "status": "manual", "faltando": [], "ajuste_tempo": 0, "vetor": None,
        "nivel_final": nivel,
    })
    return r
```

2. Em `gravar_classificacao`, trocar a linha do modelo:

```python
        "modelo": None if resultado["status"] in ("provisoria", "manual") else MODELO_CLASSIFICADOR,
```

3. Em `travar_nivel`, incluir `manual`:

```python
        if atual is None or atual["status"] in ("aplicada", "resolvida", "manual"):
```

4. Em `reclassificar`, depois do bloco `concluida`:

```python
    atual = classificacao_atual(client, task_id)
    if atual and atual["status"] == "manual":
        raise HTTPException(status_code=409, detail="O nível desta task foi escolhido pelo gerente.")
```

5. Depois de `resolver_revisao`:

```python
def definir_nivel_gerente(client, task_id: str, nivel: int, pessoa_id: str) -> dict:
    """Gerente/líder/owner escolhe o nível da task, sem o classificador. Só
    enquanto o nível não travou; se a task já está em trabalho, trava em seguida."""
    rows = client.table("tasks").select("*").eq("id", task_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    task = rows[0]
    if task.get("nivel_travado_em"):
        raise HTTPException(status_code=409, detail="Nível já travado: a task começou")
    if task.get("coluna_kanban") == "concluida":
        raise HTTPException(status_code=409, detail="A task já foi concluída: o nível não pode mais ser alterado.")
    resultado = resultado_manual(nivel)
    gravar_classificacao(client, task_id, resultado, tipo="reclassificacao", criado_por=pessoa_id, texto="")
    _travar_se_em_trabalho(client, task)
    return resultado
```

`supabase_schema.sql` — acrescentar ao fim:

```sql

-- =============================================================================
-- Migration v12 (2026-11-17): status manual em task_classificacoes (nível escolhido pelo gerente)
-- Spec: docs/superpowers/specs/2026-11-17-pta-nivel-gerente-design.md §3
-- NÃO RODA SOZINHA. Cole no SQL Editor do Supabase ANTES do deploy do backend.
-- =============================================================================

-- Preflight (somente leitura): nome real da constraint e distribuição atual
-- SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--   WHERE conrelid = 'task_classificacoes'::regclass AND contype = 'c';
-- SELECT status, count(*) FROM task_classificacoes GROUP BY 1 ORDER BY 1;

-- v12.1 — recria o CHECK com o status novo (nenhum dado existente muda).
-- A constraint inline foi criada sem nome: o Postgres a chama task_classificacoes_status_check
-- (confirme no preflight; se o nome for outro, use-o no DROP).
-- ALTER TABLE task_classificacoes DROP CONSTRAINT IF EXISTS task_classificacoes_status_check;
-- ALTER TABLE task_classificacoes ADD CONSTRAINT task_classificacoes_status_check
--   CHECK (status IN ('aplicada','em_revisao','provisoria','resolvida','manual'));

-- Rollback (só se NENHUMA linha tiver status = 'manual'; senão converta-as antes):
-- ALTER TABLE task_classificacoes DROP CONSTRAINT IF EXISTS task_classificacoes_status_check;
-- ALTER TABLE task_classificacoes ADD CONSTRAINT task_classificacoes_status_check
--   CHECK (status IN ('aplicada','em_revisao','provisoria','resolvida'));
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_nivel_gerente.py tests/test_pta_nivel_migracoes.py tests/test_classificador_ciclo.py tests/test_classificador_rotas.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/classificador_ciclo.py docudata-backend/supabase_schema.sql docudata-backend/tests/test_nivel_gerente.py docudata-backend/tests/test_pta_nivel_migracoes.py
git commit -m "$(cat <<'EOF'
feat(classificador): status manual para o nível escolhido pelo gerente

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `nivel_gerente` na criação de task (`POST /tasks`)

**Files:**
- Modify: `docudata-backend/models/schemas.py` (`TaskCreate` ~477-490)
- Modify: `docudata-backend/routers/tasks.py` (`create_task` ~335-340)
- Test: `docudata-backend/tests/test_nivel_gerente.py` (acrescenta)

**Interfaces:**
- Consumes: `ciclo.resultado_manual(nivel)` (Task 5); helpers `_fake`, `_tc` do próprio `tests/test_nivel_gerente.py`.
- Produces: `TaskCreate.nivel_gerente: Optional[int]` validado em {1,2,3,5}; `POST /tasks` com `nivel_gerente` devolve `pontos == nivel` e `classificacao_status == "manual"`, sem chamar `classificar_para_criacao`/modelo.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_nivel_gerente.py`:

```python
# --- criação ---

BODY = {"project_id": "p1", "titulo": "Nova", "descricao": "algo claro"}


@pytest.fixture
def modelo_proibido(monkeypatch):
    async def explode(**kw):
        raise AssertionError("o classificador não pode ser chamado quando o gerente define o nível")

    monkeypatch.setattr(ciclo, "classificar", explode)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")


@pytest.mark.parametrize("cargo", ["gerente", "lider", "owner"])
def test_criar_com_nivel_gerente_nao_chama_ia(monkeypatch, autenticar, modelo_proibido, cargo):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake, cargo).post("/tasks", json={**BODY, "nivel_gerente": 5})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["pontos"] == 5 and body["classificacao_status"] == "manual"
    linhas = fake.tables["task_classificacoes"]
    assert len(linhas) == 1 and linhas[0]["tipo"] == "criacao" and linhas[0]["status"] == "manual"
    assert linhas[0]["nivel_final"] == 5 and linhas[0]["modelo"] is None
    assert fake.tables["tasks"][0]["pontos"] == 5


def test_criar_com_nivel_gerente_ignora_opiniao(monkeypatch, autenticar, modelo_proibido):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks", json={**BODY, "nivel_gerente": 3, "opiniao_nivel": 5})
    assert resp.status_code == 201 and resp.json()["pontos"] == 3
    assert fake.tables["task_classificacoes"][0]["opiniao_gerente"] is None


def test_criar_com_nivel_gerente_em_sprint_iniciada_trava(monkeypatch, autenticar, modelo_proibido):
    resp = _tc(monkeypatch, autenticar, _fake()).post("/tasks", json={**BODY, "nivel_gerente": 2, "sprint_id": "s2"})
    assert resp.status_code == 201 and resp.json()["nivel_travado_em"] is not None


def test_criar_com_nivel_gerente_operacional_403(monkeypatch, autenticar, modelo_proibido):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake, "operacional").post("/tasks", json={**BODY, "nivel_gerente": 3})
    assert resp.status_code == 403
    assert fake.tables["tasks"] == []


@pytest.mark.parametrize("invalido", [0, 4, 8, -1])
def test_criar_com_nivel_gerente_fora_da_regua_422(monkeypatch, autenticar, modelo_proibido, invalido):
    fake = _fake()
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks", json={**BODY, "nivel_gerente": invalido})
    assert resp.status_code == 422 and fake.tables["tasks"] == []


def test_criar_sem_nivel_gerente_segue_o_fluxo_da_ia(monkeypatch, autenticar):
    chamadas = []

    async def fake_cls(**kw):
        chamadas.append(kw)
        return {"status": "aplicada", "faltando": [], "sinais": {}, "nivel_sinais": 3, "parecidas": [],
                "nivel_parecidas": None, "nivel_geral": 3, "justificativa_geral": "ia", "nivel_combinado": 3,
                "ajuste_tempo": 0, "nivel_final": 3, "motivo_revisao": None, "parametros": {}, "vetor": None}

    monkeypatch.setattr(ciclo, "classificar", fake_cls)
    monkeypatch.setattr(ciclo, "get_gemini_api_key", lambda: "k")
    resp = _tc(monkeypatch, autenticar, _fake()).post("/tasks", json=BODY)
    assert resp.status_code == 201 and resp.json()["classificacao_status"] == "aplicada" and len(chamadas) == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_nivel_gerente.py -k "criar"`
Expected: FAIL (campo ignorado: a IA é chamada e `modelo_proibido` explode; 422 não acontece).

- [ ] **Step 3: Implementar**

`models/schemas.py`, em `TaskCreate`:

```python
    opiniao_nivel: Optional[int] = None
    nivel_gerente: Optional[int] = None  # gerente/líder/owner escolhe o nível: não passa pelo classificador
```

e no validator:

```python
    @field_validator("pontos", "opiniao_nivel", "nivel_gerente")
```

`routers/tasks.py`, em `create_task`, substituir a chamada do classificador:

```python
    # O nível vem do agente (spec A2): o `pontos` enviado pelo cliente é ignorado.
    # Um 422 com `faltando` sai aqui, antes de criar a task. Exceção: quando o
    # gerente escolhe o nível (`nivel_gerente`), o modelo nem é chamado. Operacional
    # já não chega aqui (require_not_operacional → 403).
    if data.nivel_gerente is not None:
        resultado = ciclo.resultado_manual(data.nivel_gerente)
    else:
        resultado = await ciclo.classificar_para_criacao(
            client, titulo=data.titulo, descricao=data.descricao, checklist=data.checklist,
            opiniao_gerente=data.opiniao_nivel, gerente_id=pessoa["id"],
        )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_nivel_gerente.py tests/test_classificador_ciclo.py tests/test_requer_aprovacao_persistencia.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/routers/tasks.py docudata-backend/tests/test_nivel_gerente.py
git commit -m "$(cat <<'EOF'
feat(tasks): gerente pode definir o nível na criação, sem o classificador

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: `POST /tasks/{id}/nivel-gerente` e regressão de edição de texto

**Files:**
- Modify: `docudata-backend/models/schemas.py` (`RevisaoNivelRequest` ~610; classe nova `NivelGerenteRequest`)
- Modify: `docudata-backend/routers/tasks.py` (import + endpoint novo depois de `revisar_nivel_task` ~760)
- Test: `docudata-backend/tests/test_nivel_gerente.py` (acrescenta)

**Interfaces:**
- Consumes: `ciclo.definir_nivel_gerente(client, task_id, nivel, pessoa_id)` (Task 5); `_com_classificacao_status(client, [task])` e `require_project_access` (já em `routers/tasks.py`).
- Produces: `NivelGerenteRequest(nivel: int)` (validado em {1,2,3,5}); `POST /tasks/{task_id}/nivel-gerente` → `TaskResponse` com `classificacao_status == "manual"` (403 operacional, 404 task inexistente, 409 travada/concluída, 422 nível fora da régua).

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_nivel_gerente.py`:

```python
# --- endpoint /nivel-gerente ---

@pytest.mark.parametrize("cargo", ["gerente", "lider", "owner"])
def test_nivel_gerente_troca_o_nivel(monkeypatch, autenticar, cargo):
    fake = _fake()
    fake.tables["tasks"].append(_task(pontos=2))
    fake.tables["task_classificacoes"].append(_clas("aplicada", 2))
    resp = _tc(monkeypatch, autenticar, fake, cargo).post("/tasks/t1/nivel-gerente", json={"nivel": 5})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pontos"] == 5 and body["classificacao_status"] == "manual"
    assert fake.tables["tasks"][0]["pontos"] == 5
    ultima = [c for c in fake.tables["task_classificacoes"] if c["tipo"] == "reclassificacao"]
    assert len(ultima) == 1 and ultima[0]["status"] == "manual" and ultima[0]["criado_por"] == "pessoa-teste"


def test_nivel_gerente_operacional_403(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    resp = _tc(monkeypatch, autenticar, fake, "operacional").post("/tasks/t1/nivel-gerente", json={"nivel": 3})
    assert resp.status_code == 403
    assert fake.tables["task_classificacoes"] == []


def test_nivel_gerente_task_travada_409(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task(nivel_travado_em="2026-01-02T00:00:00+00:00"))
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks/t1/nivel-gerente", json={"nivel": 3})
    assert resp.status_code == 409 and resp.json()["detail"] == "Nível já travado: a task começou"
    assert fake.tables["tasks"][0]["pontos"] == 2


def test_nivel_gerente_task_inexistente_404(monkeypatch, autenticar):
    resp = _tc(monkeypatch, autenticar, _fake()).post("/tasks/nao-existe/nivel-gerente", json={"nivel": 3})
    assert resp.status_code == 404


@pytest.mark.parametrize("invalido", [0, 4, 7])
def test_nivel_gerente_fora_da_regua_422(monkeypatch, autenticar, invalido):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    resp = _tc(monkeypatch, autenticar, fake).post("/tasks/t1/nivel-gerente", json={"nivel": invalido})
    assert resp.status_code == 422 and fake.tables["task_classificacoes"] == []


def test_task_manual_comeca_e_trava(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={"coluna_kanban": "em_andamento"})
    assert resp.status_code == 200, resp.text
    assert fake.tables["tasks"][0]["nivel_travado_em"] is not None


@pytest.mark.parametrize("campo,valor", [("titulo", "Outro título"), ("descricao", "outra"),
                                         ("checklist", [{"texto": "novo", "done": False}])])
def test_editar_texto_de_task_manual_nao_manda_para_revisao(monkeypatch, autenticar, campo, valor):
    fake = _fake()
    fake.tables["tasks"].append(_task(checklist=[{"texto": "a", "done": False}]))
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    resp = _tc(monkeypatch, autenticar, fake).patch("/tasks/t1", json={campo: valor})
    assert resp.status_code == 200, resp.text
    assert fake.tables["task_classificacoes"][0]["status"] == "manual"
    assert len(fake.tables["task_classificacoes"]) == 1  # sem reclassificação
    assert fake.tables["tasks"][0]["pontos"] == 2  # PATCH não mexe no nível


def test_reclassificar_task_manual_pela_rota_409(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    resp = _tc(monkeypatch, autenticar, fake, "lider").post("/tasks/t1/reclassificar")
    assert resp.status_code == 409


def test_get_task_traz_status_manual(monkeypatch, autenticar):
    fake = _fake()
    fake.tables["tasks"].append(_task())
    fake.tables["task_classificacoes"].append(_clas("manual", 3))
    assert _tc(monkeypatch, autenticar, fake).get("/tasks/t1").json()["classificacao_status"] == "manual"


def test_task_manual_concluida_entra_no_aprendizado_fora_do_pta():
    import services.classificador_aprendizado as ap
    fake = _fake()
    fake.tables["tasks"].append(_task(coluna_kanban="concluida", pontos=3, operacional_id="op1"))
    fake.tables["task_classificacoes"].append(_clas("manual", 3, opiniao_gerente=None))
    fake.tables["task_transicoes"] = [
        {"task_id": "t1", "campo": "coluna_kanban", "de": "planejado", "para": "em_andamento",
         "timestamp": "2026-10-01T08:00:00+00:00", "bloqueio_tipo": None},
        {"task_id": "t1", "campo": "coluna_kanban", "de": "em_andamento", "para": "concluida",
         "timestamp": "2026-10-01T12:00:00+00:00", "bloqueio_tipo": None},
    ]
    fake.tables["classificador_parametros"] = []
    fake.tables["classificador_parametros_hist"] = []
    ap.registrar_conclusao(fake, "t1")
    ex = fake.tables["task_aprendizado"][0]
    assert ex["nivel_sugerido"] == 3
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_nivel_gerente.py -k "nivel_gerente or manual"`
Expected: FAIL (rota inexistente: 404/405 nos testes do endpoint; os de regressão já passam — `test_editar_texto_de_task_manual...` confirma o comportamento que o código já tem, porque o ramo `_texto_mudou` só olha `aplicada`/`resolvida`).

- [ ] **Step 3: Implementar**

`models/schemas.py`, depois de `RevisaoNivelRequest` (copiar o validator que ele já usa para validar a régua; se ele usa `NIVEIS`/`MENSAGEM_NIVEL_INVALIDO`, usar o mesmo):

```python
class NivelGerenteRequest(BaseModel):
    nivel: int

    @field_validator("nivel")
    @classmethod
    def nivel_na_regua(cls, v: int) -> int:
        if v not in NIVEIS:
            raise ValueError(MENSAGEM_NIVEL_INVALIDO)
        return v
```

`routers/tasks.py`: adicionar `NivelGerenteRequest` ao bloco `from models.schemas import (...)` e o endpoint depois de `revisar_nivel_task`:

```python
@router.post("/{task_id}/nivel-gerente", response_model=TaskResponse)
async def definir_nivel_gerente_task(
    task_id: str, data: NivelGerenteRequest, pessoa: dict = Depends(require_role("gerente")),
):
    """Gerente/líder/owner escolhe o nível da task, sem o classificador (spec PTA §3)."""
    client = get_client()
    rows = client.table("tasks").select("id, project_id").eq("id", task_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    await require_project_access(rows[0]["project_id"], pessoa)
    ciclo.definir_nivel_gerente(client, task_id, data.nivel, pessoa["id"])
    fresca = client.table("tasks").select("*").eq("id", task_id).execute().data[0]
    return _com_classificacao_status(client, [fresca])[0]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q tests/test_nivel_gerente.py tests/test_classificador_ciclo.py tests/test_rbac_gate.py`
Expected: PASS

- [ ] **Step 5: Rodar a suíte inteira do backend**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q`
Expected: PASS (nenhuma regressão nos testes que criam task com o classificador falso do `conftest.py`).

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/routers/tasks.py docudata-backend/tests/test_nivel_gerente.py
git commit -m "$(cat <<'EOF'
feat(tasks): endpoint /nivel-gerente para trocar o nível enquanto não travou

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

# Onda 2 — Frontend

Pré-requisito: Onda 1 concluída (o front só é testado estaticamente + `tsc`, mas o contrato vem do backend).

### Task 8: Subárea PTA no frontend

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts:177`
- Modify: `docudata-frontend/app/page.tsx:8-11`
- Modify: `docudata-frontend/app/components/shell/navItems.ts:3-6`
- Modify: `docudata-frontend/app/[subarea]/layout.tsx:3`
- Modify: `docudata-frontend/app/[subarea]/projects/new/page.tsx:10`
- Modify: `docudata-frontend/app/[subarea]/projects/[id]/page.tsx:877` e `:1763`
- Modify: `docudata-frontend/app/acompanhamento/page.tsx:12-15`
- Test: `docudata-frontend/tests/pta-nivel-gerente.test.mjs` (novo)

**Interfaces:**
- Consumes: nada de tasks anteriores (só o contrato: `projects.subarea` aceita `"pta"`).
- Produces: `Subarea = "dados" | "dev" | "pta"`; rota `/pta` e `/pta/projects/...` válidas (o layout dinâmico `[subarea]` hoje dá `notFound()` para qualquer slug fora de dados/dev — ver Step 3); `SUBAREAS` com PTA.

- [ ] **Step 1: Escrever o teste que falha**

`docudata-frontend/tests/pta-nivel-gerente.test.mjs`:

```js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("subárea PTA: tipo, card, menu, layout, cadastro e acompanhamento", () => {
  assert.ok(ler("app/lib/api.ts").includes('export type Subarea = "dados" | "dev" | "pta";'));
  const home = ler("app/page.tsx");
  assert.ok(home.includes('slug: "pta", title: "PTA", description: "Projetos do processo seletivo do CITi."'));
  assert.ok(ler("app/components/shell/navItems.ts").includes('{ slug: "pta", label: "PTA" }'));
  assert.ok(ler("app/[subarea]/layout.tsx").includes('new Set(["dados", "dev", "pta"])'));
  assert.ok(ler("app/[subarea]/projects/new/page.tsx").includes('pta: "PTA"'));
  assert.ok(ler("app/acompanhamento/page.tsx").includes('{ value: "pta", label: "PTA" }'));
  assert.ok(ler("app/[subarea]/projects/[id]/page.tsx").includes('sub === "pta" ? "PTA"'));
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-frontend && node --test tests/pta-nivel-gerente.test.mjs`
Expected: FAIL

- [ ] **Step 3: Implementar**

- `app/lib/api.ts:177`: `export type Subarea = "dados" | "dev" | "pta";`
- `app/page.tsx`: acrescentar ao array `subareas`:
  `  { slug: "pta", title: "PTA", description: "Projetos do processo seletivo do CITi." },`
- `navItems.ts`: `SUBAREAS` ganha `  { slug: "pta", label: "PTA" },` depois de Dev.
- `app/[subarea]/layout.tsx`: `const SUBAREAS = new Set(["dados", "dev", "pta"]);` (a spec dizia que `/pta/...` já funcionava pelo `[subarea]`, mas este layout barra o slug).
- `app/[subarea]/projects/new/page.tsx:10`: `const LABEL: Record<Subarea, string> = { dados: "Dados", dev: "Dev", pta: "PTA" };`
- `app/[subarea]/projects/[id]/page.tsx:877`: `const rotuloSubarea = (sub: Subarea) => (sub === "dev" ? "Dev" : sub === "pta" ? "PTA" : "Dados");` e, no `<select id="project-subarea">`, depois da opção Dev: `{project.subarea === "pta" && <option value="pta">PTA</option>}` (só para o select exibir o valor atual; o backend continua aceitando só Dados/Dev na troca).
- `app/acompanhamento/page.tsx`: acrescentar `  { value: "pta", label: "PTA" },` ao array `SUBAREAS`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-frontend && node --test tests/*.test.mjs && npx tsc --noEmit`
Expected: PASS (sem erros de tipo; se algum `Record<Subarea, ...>` não listado aqui quebrar, completar com `pta`).

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app docudata-frontend/tests/pta-nivel-gerente.test.mjs
git commit -m "$(cat <<'EOF'
feat(pta): subárea PTA no menu, na home, no cadastro e no acompanhamento

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

(Não adicionar `docudata-frontend/next-env.d.ts` nem `tsconfig.tsbuildinfo`, que o `tsc` pode modificar.)

---

### Task 9: Seletor CITi / PTA em `/performance`

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts` (`getPerformance`, ~2241)
- Modify: `docudata-frontend/app/performance/page.tsx`
- Test: `docudata-frontend/tests/pta-nivel-gerente.test.mjs` (acrescenta)

**Interfaces:**
- Consumes: `GET /performance?escopo=` (Task 3); `SegmentedControl` de `../components/ds`.
- Produces: `getPerformance(escopo: EscopoPerformance = "citi"): Promise<PerformanceResponse>`; `export type EscopoPerformance = "citi" | "pta"`.

- [ ] **Step 1: Escrever o teste que falha**

Acrescentar a `tests/pta-nivel-gerente.test.mjs`:

```js
test("performance: escopo CITi/PTA vai da tela até a API", () => {
  const api = ler("app/lib/api.ts");
  assert.ok(api.includes('export type EscopoPerformance = "citi" | "pta";'));
  assert.ok(api.includes("getPerformance(escopo: EscopoPerformance = \"citi\")"));
  assert.ok(api.includes("`${API}/performance?escopo=${escopo}`"));
  const pagina = ler("app/performance/page.tsx");
  assert.ok(pagina.includes('label="Escopo do ranking"'));
  assert.ok(pagina.includes('{ value: "citi", label: "CITi" }'));
  assert.ok(pagina.includes('{ value: "pta", label: "PTA" }'));
  assert.ok(pagina.includes("getPerformance(escopo)"));
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-frontend && node --test tests/pta-nivel-gerente.test.mjs`
Expected: FAIL

- [ ] **Step 3: Implementar**

`app/lib/api.ts`:

```ts
export type EscopoPerformance = "citi" | "pta";

export async function getPerformance(escopo: EscopoPerformance = "citi"): Promise<PerformanceResponse> {
  const res = await apiFetch(`${API}/performance?escopo=${escopo}`);
  if (!res.ok) throw new Error("Erro ao buscar ranking de performance");
  return res.json();
}
```

`app/performance/page.tsx`:
- import: `import { getPerformance, type EscopoPerformance, type PerformanceResponse, type PerformanceOperacional } from "../lib/api";`
- depois de `JANELAS`:

```tsx
const ESCOPOS: { value: EscopoPerformance; label: string }[] = [
  { value: "citi", label: "CITi" },
  { value: "pta", label: "PTA" },
];
```

- estado e efeito:

```tsx
  const [escopo, setEscopo] = useState<EscopoPerformance>("citi");
  ...
  useEffect(() => {
    if (!auth || (auth.cargo !== "lider" && auth.cargo !== "owner")) return;
    setDados(null);
    setErro("");
    getPerformance(escopo)
      .then(setDados)
      .catch((e: Error) => setErro(e.message));
  }, [auth, escopo]);
```

- `actions` do `PageHeader`:

```tsx
        actions={
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <SegmentedControl label="Escopo do ranking" options={ESCOPOS} value={escopo} onChange={setEscopo} />
            <SegmentedControl label="Janela de tempo" options={JANELAS} value={janela} onChange={setJanela} />
          </div>
        }
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-frontend && node --test tests/*.test.mjs && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/lib/api.ts docudata-frontend/app/performance/page.tsx docudata-frontend/tests/pta-nivel-gerente.test.mjs
git commit -m "$(cat <<'EOF'
feat(performance): seletor CITi / PTA no topo do ranking

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Contrato do nível manual em `lib/api.ts`

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts` (tipo em ~1747; `createTaskKanban` ~1782-1794; função nova depois de `resolverRevisaoNivel` ~1845)
- Test: `docudata-frontend/tests/pta-nivel-gerente.test.mjs` (acrescenta)

**Interfaces:**
- Consumes: `POST /tasks` com `nivel_gerente` (Task 6) e `POST /tasks/{id}/nivel-gerente` (Task 7); `erroDetail(res, padrao)` e `TaskKanbanResponse` (já existem em `api.ts`).
- Produces: `TaskKanbanResponse.classificacao_status` aceita `"manual"`; `createTaskKanban({..., nivel_gerente?: number})`; `definirNivelGerente(id: string, nivel: number): Promise<TaskKanbanResponse>`.

- [ ] **Step 1: Escrever o teste que falha**

```js
test("api: nível escolhido pelo gerente", () => {
  const api = ler("app/lib/api.ts");
  assert.ok(api.includes('"aplicada" | "em_revisao" | "provisoria" | "resolvida" | "manual"'));
  assert.ok(api.includes("nivel_gerente?: number;"));
  assert.ok(api.includes("export async function definirNivelGerente(id: string, nivel: number): Promise<TaskKanbanResponse>"));
  assert.ok(api.includes("`${API}/tasks/${id}/nivel-gerente`"));
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-frontend && node --test tests/pta-nivel-gerente.test.mjs`
Expected: FAIL

- [ ] **Step 3: Implementar**

Em `app/lib/api.ts`:
- linha ~1747: `classificacao_status?: "aplicada" | "em_revisao" | "provisoria" | "resolvida" | "manual" | null;`
- em `createTaskKanban`, junto de `opiniao_nivel?: number;`: `  nivel_gerente?: number;`
- depois de `resolverRevisaoNivel`:

```ts
export async function definirNivelGerente(id: string, nivel: number): Promise<TaskKanbanResponse> {
  const res = await apiFetch(`${API}/tasks/${id}/nivel-gerente`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nivel }),
  });
  if (!res.ok) throw await erroDetail(res, "Erro ao definir o nível da task");
  return res.json();
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-frontend && node --test tests/*.test.mjs && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/lib/api.ts docudata-frontend/tests/pta-nivel-gerente.test.mjs
git commit -m "$(cat <<'EOF'
feat(tasks): cliente da API para o nível escolhido pelo gerente

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Formulário de criação — "Definir o nível eu mesmo"

**Files:**
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx` (`TaskModal`: estados ~149-151; `handleSubmit` ~213-221; bloco de opinião ~498-511)
- Test: `docudata-frontend/tests/pta-nivel-gerente.test.mjs` (acrescenta)

**Interfaces:**
- Consumes: `createTaskKanban({..., nivel_gerente})` (Task 10); `NIVEIS`, `rotuloNivel` (já importados), `DsSelect`.
- Produces: no modo `create`, gerente/líder/owner vê o checkbox "Definir o nível eu mesmo"; marcado, mostra o seletor 1/2/3/5 (`id="task-nivel-gerente"`) e esconde o campo de opinião; o submit envia `nivel_gerente` e não envia `opiniao_nivel`. Operacional não vê o checkbox.

- [ ] **Step 1: Escrever o teste que falha**

```js
test("criação: gerente define o nível e a opinião some", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(k.includes("Definir o nível eu mesmo"));
  assert.ok(k.includes('id="task-nivel-proprio"'));
  assert.ok(k.includes('id="task-nivel-gerente"'));
  assert.ok(k.includes("nivel_gerente: Number(nivelGerente)"));
  assert.ok(k.includes("Escolha o nível da task."));
  assert.match(k, /\{mode === "create" && !nivelProprio && \(/);
  assert.ok(k.includes('const ehGerente = !!auth && auth.cargo !== "operacional";'));
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-frontend && node --test tests/pta-nivel-gerente.test.mjs`
Expected: FAIL

- [ ] **Step 3: Implementar**

Em `TaskModal`, ao lado de `ehLider`/`opiniao`:

```tsx
  const ehGerente = !!auth && auth.cargo !== "operacional";
  const [nivelProprio, setNivelProprio] = useState(false);
  const [nivelGerente, setNivelGerente] = useState("");
```

Em `handleSubmit`, depois da validação do título:

```tsx
    if (mode === "create" && nivelProprio && !nivelGerente) { setErr("Escolha o nível da task."); return; }
```

e no payload do `createTaskKanban`, trocar a linha de `opiniao_nivel`:

```tsx
          ...(nivelProprio && nivelGerente
            ? { nivel_gerente: Number(nivelGerente) }
            : opiniao ? { opiniao_nivel: Number(opiniao) } : {}),
```

No JSX, antes do bloco de opinião (`{mode === "create" && (<div> ... task-opiniao`), inserir o checkbox/seletor e trocar a condição do bloco de opinião:

```tsx
          {mode === "create" && ehGerente && (
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
                <input
                  id="task-nivel-proprio"
                  type="checkbox"
                  checked={nivelProprio}
                  onChange={(e) => { setNivelProprio(e.target.checked); if (!e.target.checked) setNivelGerente(""); }}
                />
                <span style={{ fontSize: 13, fontWeight: 600, color: "#c3cbc6" }}>Definir o nível eu mesmo</span>
              </label>
              {nivelProprio && (
                <div style={{ marginTop: 8 }}>
                  <label htmlFor="task-nivel-gerente" style={labelSt}>Nível da task</label>
                  <DsSelect id="task-nivel-gerente" value={nivelGerente} onChange={(e) => setNivelGerente(e.target.value)}>
                    <option value="">escolha o nível</option>
                    {NIVEIS.map((n) => (
                      <option key={n} value={n}>{rotuloNivel(n)}</option>
                    ))}
                  </DsSelect>
                  <p style={{ fontSize: 12, color: "#8a948e", margin: "6px 0 0" }}>
                    O classificador não é consultado: o nível fica como você escolheu.
                  </p>
                </div>
              )}
            </div>
          )}

          {mode === "create" && !nivelProprio && (
            <div>
              <label htmlFor="task-opiniao" ...>   {/* bloco de opinião existente, inalterado */}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-frontend && node --test tests/*.test.mjs && npx tsc --noEmit`
Expected: PASS (inclui `tests/classificador.test.mjs`, que ainda exige o texto "Não define o nível. É usada pelo classificador como mais uma referência.").

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/components/TasksKanbanTab.tsx docudata-frontend/tests/pta-nivel-gerente.test.mjs
git commit -m "$(cat <<'EOF'
feat(tasks): formulário de criação permite definir o nível manualmente

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Task aberta — "Mudar nível" e selos de nível do gerente

**Files:**
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx` (estado e handler em `TaskModal`; linha de detalhe ~372; bloco Reclassificar ~513-527; `title` dos chips ~812 e ~1050; `Chip` ~1052)
- Test: `docudata-frontend/tests/pta-nivel-gerente.test.mjs` (acrescenta)

**Interfaces:**
- Consumes: `definirNivelGerente(id, nivel): Promise<TaskKanbanResponse>` (Task 10); `ehGerente` (Task 11); `onSaved(saved: TaskKanbanResponse, created?: boolean)` e `onClose` já existentes no `TaskModal`; `Chip` de `./ds`.
- Produces: função `origemNivel(status)` no módulo (`"definido pelo gerente"` | `"definido pelo classificador"`); ação "Mudar nível" na task aberta quando `!task.nivel_travado_em` e a task não está concluída; `Chip` "nível do gerente" nos cards; botão "Reclassificar" oculto para task `manual`.

- [ ] **Step 1: Escrever o teste que falha**

```js
test("task aberta: Mudar nível e selos do gerente", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(k.includes("definirNivelGerente"));
  assert.ok(k.includes("Mudar nível"));
  assert.ok(k.includes('id="task-mudar-nivel"'));
  assert.ok(k.includes("function origemNivel("));
  assert.ok(k.includes('"definido pelo gerente"'));
  assert.ok(k.includes("nível do gerente"));
  assert.ok(k.includes('task.classificacao_status === "manual"'));
  assert.ok(!k.includes("· definido pelo classificador`"), "os títulos dos chips usam origemNivel");
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-frontend && node --test tests/pta-nivel-gerente.test.mjs`
Expected: FAIL

- [ ] **Step 3: Implementar**

1. Importar `definirNivelGerente` no bloco de imports de `../lib/api`.
2. Função de módulo (perto dos outros helpers, fora dos componentes):

```tsx
function origemNivel(status?: string | null): string {
  return status === "manual" ? "definido pelo gerente" : "definido pelo classificador";
}
```

3. Linha de detalhe (~372):

```tsx
              nível {task.pontos} · {task.classificacao_status === "provisoria" ? "provisório" : task.classificacao_status === "em_revisao" ? "em revisão" : origemNivel(task.classificacao_status)}
```

4. `title` dos dois chips de pontos (~812 e ~1050): `title={`${rotuloNivel(task.pontos)} · ${origemNivel(task.classificacao_status)}`}`.
5. Depois do `Chip` provisório/em revisão (~1052-1054) acrescentar:

```tsx
        {task.classificacao_status === "manual" && <Chip tone="green">nível do gerente</Chip>}
```

6. Em `TaskModal`, estado e handler:

```tsx
  const [novoNivel, setNovoNivel] = useState("");
  const [mudandoNivel, setMudandoNivel] = useState(false);

  async function handleMudarNivel() {
    if (!task || !novoNivel) return;
    setMudandoNivel(true);
    setErr("");
    try {
      const atualizada = await definirNivelGerente(task.id, Number(novoNivel));
      onSaved(atualizada);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao mudar o nível");
    } finally {
      setMudandoNivel(false);
    }
  }
```

7. No bloco do `ehLider` (Reclassificar), esconder o botão quando a task é manual: trocar `task.nivel_travado_em ? (...) : (...)` por manter a estrutura e envolver o botão em `task.classificacao_status !== "manual" &&`. Logo depois desse bloco, inserir:

```tsx
          {mode === "edit" && task && ehGerente && !task.nivel_travado_em && task.coluna_kanban !== "concluida" && (
            <div>
              <label htmlFor="task-mudar-nivel" style={labelSt}>Escolher o nível eu mesmo</label>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <DsSelect id="task-mudar-nivel" value={novoNivel} onChange={(e) => setNovoNivel(e.target.value)}>
                  <option value="">escolha o nível</option>
                  {NIVEIS.map((n) => (
                    <option key={n} value={n}>{rotuloNivel(n)}</option>
                  ))}
                </DsSelect>
                <button type="button" onClick={handleMudarNivel} disabled={!novoNivel || mudandoNivel || saving || edicaoPendente} style={btnGhost}>
                  {mudandoNivel ? "Salvando…" : "Mudar nível"}
                </button>
              </div>
              {edicaoPendente && <p style={{ fontSize: 12, color: "#8a948e", margin: "6px 0 0" }}>Salve as edições antes de mudar o nível</p>}
            </div>
          )}
```

(O tipo de `task.coluna_kanban` já existe em `TaskKanbanResponse`.)

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-frontend && node --test tests/*.test.mjs && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/components/TasksKanbanTab.tsx docudata-frontend/tests/pta-nivel-gerente.test.mjs
git commit -m "$(cat <<'EOF'
feat(tasks): Mudar nível na task aberta e selo "nível do gerente"

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Verificação final das duas ondas

**Files:** nenhum arquivo novo.

**Interfaces:**
- Consumes: tudo acima.
- Produces: confirmação de que backend e frontend passam inteiros e lembrete das migrações manuais.

- [ ] **Step 1: Backend inteiro**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 2: Frontend inteiro**

Run: `cd docudata-frontend && node --test tests/*.test.mjs && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 3: Conferir que nenhum artefato do `tsc` entrou nos commits**

Run: `git status --short` e `git diff --stat origin/main..HEAD -- docudata-frontend/next-env.d.ts docudata-frontend/tsconfig.tsbuildinfo`
Expected: nenhum dos dois arquivos aparece no diff da branch (se aparecerem, `git checkout origin/main -- <arquivo>` e novo commit `chore: desfaz artefatos do tsc`).

- [ ] **Step 4: Avisar o usuário (não executar)**

Registrar na resposta final: as migrações v9 (CHECK de subárea com `pta`) e v10 (CHECK de status com `manual`) estão COMENTADAS no fim de `docudata-backend/supabase_schema.sql` e precisam rodar no SQL Editor do Supabase, com o preflight, ANTES do deploy do backend; novas envs opcionais: `GOOGLE_REFRESH_TOKEN_PTA`, `GDRIVE_FOLDER_ID_PTA` (obrigatória para exportar docs PTA), `GDOCS_TEMPLATE_ID_PTA` e variantes `_PLANNING_PTA` etc. (opcionais, caem no template de Dados).

---

## Self-Review

**1. Cobertura da spec**
- §1 Banco (CHECK com `pta`, comentado com preflight/rollback): Task 1. Backend (`Subarea`, acompanhamento, github_app, google_docs): Tasks 1 e 2. Front (card, `SUBAREAS`, acompanhamento): Task 8. `encaminhamento` e selects do `SprintDocModal`/`RetroModal` intocados: declarado em Global Constraints.
- §2 `escopo` no ranking: Task 3 (back) e Task 9 (front). Classificador ignora PTA (`registrar_conclusao`, `recalcular_diario`): Task 4. Acompanhamento só filtra por subárea: Task 1 (pattern).
- §3 Status `manual` + migração: Task 5. Criação com `nivel_gerente` (incl. 403 operacional, validador): Task 6. Endpoint `/nivel-gerente` (409 travada, `classificacao_status='manual'`): Task 7. Trava normal, edição de texto sem reclassificação, `resolver_revisao` não aplicável, aprendizado fora do PTA: Tasks 5 e 7. Front (criação, "Mudar nível", selo, "definido pelo gerente", tipo `"manual"`): Tasks 10-12.
- Seção 4 (bugs) e seção 5 (GitHub App): fora do escopo, não cobertas.

**2. Placeholders:** sem TBD/TODO; todos os passos de código trazem o código. Dois pontos pedem leitura local (não são placeholders de lógica): o validator de `NivelGerenteRequest` reutiliza `NIVEIS`/`MENSAGEM_NIVEL_INVALIDO` já usados por `TaskCreate`; o bloco de opinião da Task 11 é mantido como está, só muda a condição externa.

**3. Consistência de tipos/nomes:** `resultado_manual`, `definir_nivel_gerente(client, task_id, nivel, pessoa_id)`, `NivelGerenteRequest.nivel`, `nivel_gerente` (campo de `TaskCreate`), `definirNivelGerente(id, nivel)`, `EscopoPerformance`, `getPerformance(escopo)`, `listar_pessoas_ativas_por_projeto(client, escopo)`, `projeto_e_pta(client, project_id)`, `origemNivel(status)`, `ehGerente` — usados com a mesma grafia nas tasks que os definem e consomem.

**Divergências spec × código real (decisões tomadas no plano)**
- `travar_nivel` usa lista branca (`aplicada`, `resolvida`), não "só provisória/em revisão ficam destravadas" como a spec supõe: sem mexer, task `manual` nunca travaria. A Task 5 inclui `manual` na lista.
- `app/[subarea]/layout.tsx` dá `notFound()` para slug fora de `dados`/`dev`: a spec diz que `/pta/...` já funciona; precisou de `pta` no `Set` (Task 8).
- `POST /tasks` já usa `require_not_operacional`: o 403 de operacional com `nivel_gerente` vem do endpoint inteiro, sem checagem extra (coberto por teste).
- `reclassificar` (líder) rodaria o modelo por cima de task manual: a Task 5 devolve 409 (decisão do plano, a spec não cobre). `definir_nivel_gerente` também recusa task concluída (espelha `reclassificar`).
- `registrar_opiniao_operacional` em task PTA: no-op silencioso (o front abre o diálogo de opinião ao concluir; candidato não deve ver erro).
- Google Docs PTA: a spec só fala do token; o plano espelha `produto` para template (cai no de Dados) e exige `GDRIVE_FOLDER_ID_PTA` sem cair na pasta de Dados.
- Frontend `Subarea` hoje não tem `produto`; só `pta` foi acrescentado.
