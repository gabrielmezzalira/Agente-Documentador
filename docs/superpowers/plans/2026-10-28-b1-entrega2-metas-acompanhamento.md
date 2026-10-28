# B1 · Entrega 2 — Metas de funcionalidades e tela `/acompanhamento` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O líder define quais funcionalidades cada projeto tem que entregar em cada sprint e acompanha todos os projetos numa tela só, agrupados por gerente. A tela mostra meta × entregue, planejado × realizado, prazo × escopo, saúde do time e o selo "em risco".

**Architecture:**
- **Banco:** duas tabelas novas (meta atual + eventos), no bloco "Rodada B1" do `supabase_schema.sql`.
- **`services/metas.py`:** regras puras da meta (diferença, meta original, resultado) e a gravação.
- **`services/acompanhamento.py`:** cálculo puro de cada projeto e de cada grupo, mais um carregador em lote.
- **Rotas:** só para líder.
- **Frontend:** página `/acompanhamento` com o modal "Definir meta", e o selo "meta da sprint N" na tela de planejamento do gerente.

Sem piso, sem foto de fechamento e sem histórico de 6 sprints: isso é a entrega 3.

**Tech Stack:** FastAPI + supabase-py, pytest com `tests/fake_supabase.py`; Next.js 15 / React 19, estilos inline e `app/components/ds`.

**Spec:** `docs/superpowers/specs/2026-10-28-acompanhamento-projetos-design.md`. Esta entrega cobre as seções 1 (só as tabelas de meta), 3 e 5 (sem piso e sem histórico), e o item 2 da seção 7.

## Global Constraints

- **Meta:**
  - Uma meta é um conjunto de funcionalidades por sprint. Só líder e owner (`require_role("lider")`) leem e escrevem.
  - A sprint fechada (`sprints.avaliacao_completa_em` preenchido) não aceita mudança: HTTP 409 com `detail="A sprint já foi fechada; a meta não pode mais mudar."`.
  - Funcionalidade de outro projeto, ou já entregue: HTTP 422 com `detail="Funcionalidade inválida para a meta: <id_funcional ou id>"`.
- **Funcionalidade entregue:** `status == "concluida"` e `aprovada_em` preenchido. Para uma sprint fechada, conta como entregue só se `aprovada_em <= sprints.avaliacao_completa_em`.
- **Sprint atual:**
  - **Atual:** a de maior `numero` com `iniciada = true` (mesma regra da tela do projeto).
  - **Próximas:** as que têm `iniciada = false`.
  - **Última fechada:** a de maior `numero` com `avaliacao_completa_em` preenchido.
- **Início da sprint (para a meta original):** `sprints.data_inicio` às 00:00 UTC. Sem `data_inicio`, a meta original é a meta no fim do dia (UTC) do primeiro evento.
- **Meta batida:** só com 100% da meta final entregue. Sem meta → `None` ("sem meta").
- **Em risco** (basta um):
  - (a) `pct_prazo_consumido − pct_escopo_concluido > projects.tolerancia_desvio_pontos`, usando `calcular_bloco_a` de `routers/painel.py`;
  - (b) meta da última sprint fechada com entregues/meta < 0,5;
  - (c) SPI da última sprint fechada < 0,7, com o SPI calculado como em `routers/metricas.py::get_spi`.

  Cada regra que dispara vira um texto em `riscos`: `"prazo à frente do escopo"`, `"meta da última sprint abaixo de 50%"` ou `"SPI da última sprint abaixo de 0,7"`.
- **Gerente do projeto:** `projects.gerente_email` igual a `pessoa.email`, sem diferenciar maiúsculas. Sem gerente → grupo `"Sem gerente"`.
- **Toda leitura grande usa `ler_tudo`** (`services/supabase_paginacao.py`, recebe uma função que monta a query já com `.order`). Leitura em lote por lista de ids, com no máximo 100 por `.in_`. Nada de consulta por task.
- **Migração:**
  - Vai no bloco `-- Rodada B1` no fim de `docudata-backend/supabase_schema.sql` e é aplicada à mão.
  - **O arquivo tem uma mudança local do usuário na linha 1, que nunca pode ser commitada.** Para commitar só o bloco novo:

    ```bash
    git show HEAD:docudata-backend/supabase_schema.sql > /tmp/schema_head.sql
    cat /tmp/bloco_b1.sql >> /tmp/schema_head.sql
    git update-index --add --cacheinfo 100644,$(git hash-object -w /tmp/schema_head.sql),docudata-backend/supabase_schema.sql
    ```

    Antes, acrescente o mesmo bloco também ao arquivo da worktree. Depois do commit, `git diff docudata-backend/supabase_schema.sql` tem que mostrar só a mudança da linha 1.
- **Backend:** `cd docudata-backend && python3 -m pytest -q`. `tests/test_security.py::test_dependencias_separam_browser_automacoes_e_webhooks_publicos` já falha em Python 3.13 e não é regressão.
- **Frontend:**
  - `cd docudata-frontend && npx tsc --noEmit && npm test`.
  - A worktree não tem `node_modules`: use um symlink para `../Documentador/docudata-frontend/node_modules`, remova-o antes do commit e restaure `tsconfig.tsbuildinfo` e `next-env.d.ts`.
- **Commits:**
  - Nunca commitar `.planning/` nem a linha 1 do schema. Stage por caminho explícito.
  - Português, no estilo `feat(escopo): ...`, com o trailer `Co-Authored-By` do modelo que escreveu.

---

### Task 1: Migração das metas

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (bloco novo no fim; ver Global Constraints)
- Test: `docudata-backend/tests/test_metas_schema.py`

- [ ] **Step 1: Teste que falha**

```python
# docudata-backend/tests/test_metas_schema.py
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def test_bloco_rodada_b1_tem_as_tabelas_da_meta():
    sql = _SCHEMA.read_text(encoding="utf-8")
    assert "-- Rodada B1" in sql
    bloco = sql.split("-- Rodada B1", 1)[1]
    for trecho in (
        "CREATE TABLE IF NOT EXISTS sprint_meta_funcionalidades",
        "PRIMARY KEY (sprint_id, funcionalidade_id)",
        "CREATE TABLE IF NOT EXISTS sprint_meta_eventos",
        "CHECK (acao IN ('incluiu','retirou'))",
        "idx_sprint_meta_eventos_sprint",
    ):
        assert trecho in bloco, trecho
```

- [ ] **Step 2: Rodar e ver falhar** — `python3 -m pytest tests/test_metas_schema.py -q` → FAIL.

- [ ] **Step 3: Escrever o bloco** em `/tmp/bloco_b1.sql` e acrescentá-lo à worktree e ao índice como descrito nas Global Constraints:

```sql

-- ═══════════════════════════════════════════════════════════════
-- Rodada B1 (2026-10-28): painel de acompanhamento — metas de funcionalidades por sprint.
-- Spec: docs/superpowers/specs/2026-10-28-acompanhamento-projetos-design.md
-- Aplicar manualmente no SQL Editor do Supabase ANTES do deploy do backend.
CREATE TABLE IF NOT EXISTS sprint_meta_funcionalidades (
    sprint_id          uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    funcionalidade_id  uuid NOT NULL REFERENCES funcionalidades(id) ON DELETE CASCADE,
    incluida_por       uuid REFERENCES pessoa(id) ON DELETE SET NULL,
    incluida_em        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (sprint_id, funcionalidade_id)
);
CREATE INDEX IF NOT EXISTS idx_sprint_meta_funcionalidades_func ON sprint_meta_funcionalidades(funcionalidade_id);

CREATE TABLE IF NOT EXISTS sprint_meta_eventos (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sprint_id          uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    funcionalidade_id  uuid REFERENCES funcionalidades(id) ON DELETE SET NULL,
    acao               text NOT NULL CHECK (acao IN ('incluiu','retirou')),
    pessoa_id          uuid REFERENCES pessoa(id) ON DELETE SET NULL,
    criado_em          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sprint_meta_eventos_sprint ON sprint_meta_eventos(sprint_id, criado_em);
```

- [ ] **Step 4: Rodar e ver passar.** Confira com `git diff --cached docudata-backend/supabase_schema.sql`, que deve mostrar só o bloco novo.

- [ ] **Step 5: Commit** do teste e do schema (índice preparado): `feat(metas): migração das metas de funcionalidades por sprint`.

---

### Task 2: Serviço e rotas da meta

**Files:**
- Create: `docudata-backend/services/metas.py`
- Create: `docudata-backend/routers/metas.py`, registrado em `docudata-backend/main.py` como os outros routers
- Modify: `docudata-backend/models/schemas.py` (`MetaUpdate`, `MetaResponse`, `MetaEvento`)
- Test: `docudata-backend/tests/test_metas.py`

**Interfaces:**
- Produces (puras):
  - `diferenca_meta(atual: set[str], nova: set[str]) -> tuple[set[str], set[str]]`, que devolve `(incluir, retirar)`;
  - `meta_em(eventos: list[dict], ate: datetime) -> set[str]`, que reaplica os eventos (ordenados por `criado_em`) até o instante;
  - `meta_original(eventos: list[dict], inicio: datetime | None) -> set[str]`;
  - `resultado_meta(meta: set[str], entregues: set[str]) -> dict`, que devolve `{"total": int, "entregues": int, "batida": bool | None}`;
  - `funcionalidade_entregue(func: dict, fechada_em: str | None) -> bool`.
- Produces (I/O):
  - `ler_meta(client, sprint_id) -> set[str]`;
  - `substituir_meta(client, sprint_id, funcionalidade_ids: list[str], pessoa_id) -> set[str]`;
  - `eventos_da_meta(client, sprint_ids: list[str]) -> list[dict]` (em lote);
  - `metas_das_sprints(client, sprint_ids: list[str]) -> dict[str, set[str]]` (em lote).
- Rotas, com `require_role("lider")`:
  - `GET /sprints/{sprint_id}/meta` devolve `{"sprint_id", "funcionalidade_ids": [...]}`;
  - `PUT /sprints/{sprint_id}/meta` recebe `{"funcionalidade_ids": [...]}` e devolve o mesmo formato;
  - `GET /sprints/{sprint_id}/meta/eventos` devolve `[{funcionalidade_id, titulo, acao, pessoa_nome, criado_em}]`.

- [ ] **Step 1: Testes que falham**

```python
# docudata-backend/tests/test_metas.py (parte pura)
from datetime import datetime, timezone
from services.metas import diferenca_meta, meta_em, meta_original, resultado_meta, funcionalidade_entregue

def ev(f, acao, dia, hora=12):
    return {"funcionalidade_id": f, "acao": acao, "criado_em": datetime(2026, 11, dia, hora, tzinfo=timezone.utc).isoformat()}

def test_diferenca():
    assert diferenca_meta({"a", "b"}, {"b", "c"}) == ({"c"}, {"a"})

def test_meta_em_reaplica_eventos():
    evs = [ev("a", "incluiu", 1), ev("b", "incluiu", 1), ev("a", "retirou", 3)]
    assert meta_em(evs, datetime(2026, 11, 2, tzinfo=timezone.utc)) == {"a", "b"}
    assert meta_em(evs, datetime(2026, 11, 4, tzinfo=timezone.utc)) == {"b"}

def test_meta_original_com_inicio():
    evs = [ev("a", "incluiu", 1), ev("b", "incluiu", 5)]
    assert meta_original(evs, datetime(2026, 11, 3, tzinfo=timezone.utc)) == {"a"}

def test_meta_original_sem_inicio_usa_fim_do_dia_do_primeiro_evento():
    evs = [ev("a", "incluiu", 1, 9), ev("b", "incluiu", 1, 18), ev("c", "incluiu", 2)]
    assert meta_original(evs, None) == {"a", "b"}

def test_meta_original_definida_depois_do_inicio():
    evs = [ev("a", "incluiu", 6, 9), ev("b", "incluiu", 6, 10)]
    assert meta_original(evs, datetime(2026, 11, 3, tzinfo=timezone.utc)) == {"a", "b"}

def test_resultado_meta():
    assert resultado_meta(set(), set()) == {"total": 0, "entregues": 0, "batida": None}
    assert resultado_meta({"a", "b"}, {"a"}) == {"total": 2, "entregues": 1, "batida": False}
    assert resultado_meta({"a"}, {"a", "x"}) == {"total": 1, "entregues": 1, "batida": True}

def test_entregue_respeita_fechamento():
    f = {"status": "concluida", "aprovada_em": "2026-11-10T10:00:00+00:00"}
    assert funcionalidade_entregue(f, None) is True
    assert funcionalidade_entregue(f, "2026-11-09T23:00:00+00:00") is False
    assert funcionalidade_entregue(f, "2026-11-10T12:00:00+00:00") is True
    assert funcionalidade_entregue({"status": "em_andamento", "aprovada_em": None}, None) is False
```

Testes de rota com `TestClient` + `fake_supabase`, seguindo os testes de rota existentes de líder (procure um que use `require_role("lider")`, por exemplo os de `routers/classificador.py`):
- PUT inclui {a, b} → 2 linhas na meta e 2 eventos `incluiu` com `pessoa_id`;
- PUT {b, c} → eventos `incluiu c` e `retirou a`; meta {b, c};
- PUT numa sprint fechada → 409 com o detail exato;
- funcionalidade de outro projeto → 422; funcionalidade entregue → 422;
- gerente → 403; operacional → 403;
- GET eventos em ordem cronológica, com o título e o nome da pessoa.

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar**

```python
# docudata-backend/services/metas.py
"""Meta de funcionalidades por sprint (Rodada B1, entrega 2)."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from services.supabase_paginacao import ler_tudo

LOTE = 100


def _dt(v) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def diferenca_meta(atual: set[str], nova: set[str]) -> tuple[set[str], set[str]]:
    return nova - atual, atual - nova


def meta_em(eventos: list[dict], ate: datetime) -> set[str]:
    meta: set[str] = set()
    for e in sorted(eventos, key=lambda e: _dt(e["criado_em"])):
        if _dt(e["criado_em"]) > ate:
            break
        if e["acao"] == "incluiu":
            meta.add(e["funcionalidade_id"])
        else:
            meta.discard(e["funcionalidade_id"])
    return meta


def meta_original(eventos: list[dict], inicio: datetime | None) -> set[str]:
    if not eventos:
        return set()
    if inicio is not None:
        antes = meta_em(eventos, inicio)
        if antes:
            return antes
    primeiro = min(_dt(e["criado_em"]) for e in eventos)
    fim_do_dia = datetime(primeiro.year, primeiro.month, primeiro.day, tzinfo=timezone.utc) + timedelta(days=1) - timedelta(microseconds=1)
    return meta_em(eventos, fim_do_dia)


def resultado_meta(meta: set[str], entregues: set[str]) -> dict:
    if not meta:
        return {"total": 0, "entregues": 0, "batida": None}
    n = len(meta & entregues)
    return {"total": len(meta), "entregues": n, "batida": n == len(meta)}


def funcionalidade_entregue(func: dict, fechada_em: str | None) -> bool:
    if func.get("status") != "concluida" or not func.get("aprovada_em"):
        return False
    return fechada_em is None or _dt(func["aprovada_em"]) <= _dt(fechada_em)
```

Na mesma `services/metas.py`:
- `ler_meta` e `metas_das_sprints` leem `sprint_meta_funcionalidades` em lotes de `LOTE` ids com `.in_("sprint_id", lote)`;
- `eventos_da_meta` lê `sprint_meta_eventos` com `ler_tudo` ordenado por `criado_em, id`, em lotes de ids;
- `substituir_meta(client, sprint_id, ids, pessoa_id)`:
  1. busca a sprint (404 se não existir) e responde 409 se `avaliacao_completa_em` estiver preenchido;
  2. busca as funcionalidades pedidas. Se alguma for de outro `project_id` ou já estiver entregue (`funcionalidade_entregue(f, None)`), responde 422 com o `detail` das Global Constraints, usando o `id_funcional` da primeira inválida;
  3. calcula `diferenca_meta(ler_meta(...), set(ids))`;
  4. faz o insert de cada inclusão em `sprint_meta_funcionalidades` (com `incluida_por`) e o delete das retiradas;
  5. insere um evento por inclusão ou retirada;
  6. devolve a meta nova.

`routers/metas.py` só faz validação HTTP e chama o serviço. Nome do evento: `pessoa.nome` via lookup em lote em `pessoa`.

- [ ] **Step 4: Rodar a suíte inteira.**

- [ ] **Step 5: Commit:** `feat(metas): meta de funcionalidades por sprint com histórico de mudanças`.

---

### Task 3: Cálculo e rota do acompanhamento

**Files:**
- Create: `docudata-backend/services/acompanhamento.py`
- Create: `docudata-backend/routers/acompanhamento.py`, registrado em `main.py`
- Modify: `docudata-backend/models/schemas.py` (modelos de resposta, espelhando o JSON abaixo)
- Test: `docudata-backend/tests/test_acompanhamento.py`

**Interfaces:**
- Consumes: `services/metas.py` (Task 2); `calcular_bloco_a` de `routers/painel.py` (se importar do router criar ciclo, mova a função para `services/painel_calculos.py` e reexporte no router); `previsto_da_sprint` de `services/previsto_sprint.py`.
- Produces: `GET /acompanhamento?subarea=dados|dev` (`require_role("lider")`), com este JSON:

```json
{
  "subarea": "dados",
  "totais": {"projetos": 0, "em_risco": 0, "metas_fechadas": 0, "metas_batidas": 0},
  "grupos": [
    {
      "gerente": {"nome": "Ana", "email": "ana@citi.org.br"},
      "resumo": {"projetos": 0, "em_risco": 0, "metas_fechadas": 0, "metas_batidas": 0, "pct_funcs_aprovadas": 0.0},
      "projetos": [
        {
          "id": "uuid", "nome": "Projeto", "cliente": "Cliente",
          "sprint_atual": {"id": "uuid", "numero": 3} ,
          "proximas_sprints": [{"id": "uuid", "numero": 4}],
          "meta": {"total": 3, "entregues": 1, "batida": null,
                   "funcionalidades": [{"id": "uuid", "id_funcional": "F3", "titulo": "...", "status": "em_andamento",
                                        "aprovada": false, "pct_tasks": 50.0, "planejada_na_sprint": true}]},
          "planejadas_fora_da_meta": [{"id": "uuid", "id_funcional": "F7", "titulo": "..."}],
          "planejado": {"funcs_planejadas": 4, "funcs_planejadas_entregues": 1, "spi": 0.82},
          "prazo_escopo": {"sem_dados": false, "pct_prazo_consumido": 40.0, "pct_escopo_concluido": 25.0, "desvio_detectado": false},
          "saude": {"tasks_travadas": 1, "wip": 2, "p85_horas": 30.5},
          "riscos": ["meta da última sprint abaixo de 50%"],
          "ultima_fechada": {"numero": 2, "meta_total": 2, "meta_entregues": 0, "meta_batida": false, "spi": 0.6}
        }
      ]
    }
  ]
}
```

Regras de cálculo, todas em funções puras com teste, que recebem dicts já carregados:
- `pct_tasks(tasks_da_func)` = concluídas ÷ total × 100, sem as extras e com uma casa decimal. Sem tasks → `None`.
- **`meta`:** a meta atual da `sprint_atual` (`metas_das_sprints`). As funcionalidades vêm ordenadas por `id_funcional`. `planejada_na_sprint` indica se a funcionalidade está em `sprint_funcionalidades` da sprint atual.
- **`planejadas_fora_da_meta`:** as de `sprint_funcionalidades` da sprint atual que não estão na meta.
- **`planejado`:** `funcs_planejadas` = nº em `sprint_funcionalidades` da sprint atual; `funcs_planejadas_entregues` = as entregues entre elas; `spi` = SPI da sprint atual (a mesma conta de `get_spi`: realizado sem extras ÷ previsto, ou `None`).
- **`prazo_escopo`:** `calcular_bloco_a(projeto, funcionalidades_do_projeto)`.
- **`saude`:**
  - `tasks_travadas` = tasks do projeto com `travado_automatico = true` e `coluna_kanban != "concluida"`;
  - `wip` = funcionalidades com `status == "em_andamento"`;
  - `p85_horas` = percentil 85 de `tempo_limpo_s / 3600` em `task_aprendizado`, para as tasks do projeto com `concluida_em` nos últimos 30 dias e `excluida = false` (`statistics.quantiles(n=100)[84]`; com 1 amostra, o próprio valor; com 0, `None`).
- **`ultima_fechada`:** a meta final é a meta atual daquela sprint. Os entregues usam `funcionalidade_entregue(f, sprint.avaliacao_completa_em)`. O SPI da sprint é calculado como acima.
- **`riscos`:** regras (a), (b) e (c) das Global Constraints, nessa ordem.
- **Grupo por gerente:**
  - `resumo.metas_fechadas` = nº de projetos do grupo com `ultima_fechada.meta_total > 0`;
  - `metas_batidas` = quantos desses têm `meta_batida`;
  - `pct_funcs_aprovadas` = aprovadas ÷ total de funcionalidades dos projetos do grupo × 100;
  - os grupos vêm ordenados por nome do gerente, com "Sem gerente" por último; os projetos, por nome.

**Carregador** `montar_acompanhamento(client, subarea)`:
1. lê os projetos da subárea;
2. lê, em lote pelos ids dos projetos: sprints, funcionalidades, tasks (`id, project_id, sprint_id, funcionalidade_id, coluna_kanban, extra, pontos, travado_automatico, prevista_no_inicio`), `sprint_funcionalidades` das sprints relevantes, `task_aprendizado` dos últimos 30 dias (filtrado pelos ids das tasks), as metas e as pessoas dos `gerente_email`.

Use `ler_tudo` + `.in_` em lotes de 100. O previsto da sprint deve ser calculado a partir das tasks já carregadas, sem chamar `previsto_da_sprint` por sprint. Antes, leia `services/previsto_sprint.py` e replique a regra numa função pura `previsto_de(tasks_da_sprint)`, com teste que confirme que ela bate com `previsto_da_sprint` no mesmo cenário.

- [ ] **Step 1: Testes que falham.**
  - Funções puras: `pct_tasks`, meta × planejado (as duas listas de divergência), `ultima_fechada` respeitando `aprovada_em` posterior ao fechamento, as três regras de risco isoladas, o resumo do grupo, a ordem dos grupos e "Sem gerente".
  - Rota com `fake_supabase`: 2 gerentes, 3 projetos (um sem gerente) e uma meta, conferindo a forma do JSON e alguns números.
  - Gerente e operacional recebem 403.
  - `subarea` inválida → 422.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar a suíte inteira.**
- [ ] **Step 5: Commit:** `feat(acompanhamento): painel dos projetos agrupado por gerente (meta, planejado, prazo, saúde, risco)`.

---

### Task 4: Tela `/acompanhamento`

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`
  - tipos que espelham o JSON da Task 3;
  - `getAcompanhamento(subarea)`, `getMetaSprint(sprintId)`, `definirMetaSprint(sprintId, funcionalidadeIds)` e `getEventosMeta(sprintId)`;
  - erros com o `detail` do backend, no padrão das funções existentes.
- Create: `docudata-frontend/app/acompanhamento/page.tsx`
- Create: `docudata-frontend/app/components/DefinirMetaModal.tsx`
- Modify: `docudata-frontend/app/components/shell/navItems.ts` (item `Acompanhamento` → `/acompanhamento`, só com `isOwnerOrLider(cargo)`, logo depois de `Performance`)
- Test: `docudata-frontend/tests/acompanhamento.test.mjs`

**Layout:** siga `app/performance/page.tsx` e `app/classificador/page.tsx` (shell, guarda de cargo com o aviso padrão de acesso restrito, `ErrorNotice`, carregando e vazio) e os componentes de `app/components/ds` (`Card`, `Chip`, `Button`, `SegmentedControl`, `Modal`, `ProgressBar`).

**Topo:**
- título literal `Acompanhamento dos projetos`;
- `SegmentedControl` com `Dados` e `Dev`;
- três contadores: `Projetos`, `Em risco` e `Metas batidas` (no formato `N de M`, sobre as últimas sprints fechadas).

**Por gerente:**
- cabeçalho com o nome e a linha de resumo: `N projetos · X em risco · metas batidas A de B · Y% das funcionalidades aprovadas`.

**Linha do projeto (compacta):**
- nome + cliente;
- chip vermelho `em risco` com `title` listando os `riscos`;
- **Meta:** `1 de 3` com uma mini-barra por funcionalidade (verde se aprovada; senão, o % de tasks em `ProgressBar`). Sem meta, `sem meta`;
- **Planejado:** `1 de 4 planejadas` · `SPI 0,82`;
- **Prazo × escopo:** `40% do prazo · 25% entregue`, ou `sem datas do contrato`;
- **Saúde:** `1 travada · WIP 2 · p85 30h`.

**Ao expandir o projeto:**
- a lista da meta: `id_funcional`, título, status, `% tasks`, selo `aprovada` e o chip âmbar `fora do planejamento` quando `!planejada_na_sprint`;
- abaixo, `Planejadas fora da meta:` com os chips;
- a linha `Última sprint fechada (SN): meta A de B · SPI X`;
- o botão `Definir meta`, que abre o `DefinirMetaModal`;
- o link `Histórico de mudanças da meta`, que lista os eventos (`incluiu`/`retirou` · funcionalidade · pessoa · data).

**`DefinirMetaModal`:**
- seletor de sprint (a atual e as próximas, com `Sprint N (atual)`);
- carrega `getMetaSprint` e as funcionalidades do projeto (use a função de listagem de funcionalidades que já existe em `api.ts`);
- lista só as funcionalidades não entregues, cada uma com checkbox, `id_funcional`, título, prioridade, `% tasks` e o selo `planejada nesta sprint`. O % e o selo vêm do JSON do acompanhamento para a sprint atual; para sprints futuras, use `sprint_funcionalidades` se já houver função em `api.ts`, ou omita o selo;
- botões `Cancelar` e `Salvar meta`. Ao salvar, chama `definirMetaSprint`, recarrega a tela e fecha;
- erros 409/422 aparecem em `ErrorNotice` dentro do modal.

- [ ] **Step 1: Teste estrutural que falha**

```js
// docudata-frontend/tests/acompanhamento.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("tela /acompanhamento existe com os blocos e o modal de meta", () => {
  assert.ok(existsSync(new URL("../app/acompanhamento/page.tsx", import.meta.url)));
  const p = ler("app/acompanhamento/page.tsx");
  for (const s of ["Acompanhamento dos projetos", "Em risco", "Metas batidas", "Definir meta", "Histórico de mudanças da meta", "Planejadas fora da meta:", "sem meta"]) {
    assert.ok(p.includes(s), s);
  }
  const m = ler("app/components/DefinirMetaModal.tsx");
  for (const s of ["Salvar meta", "planejada nesta sprint"]) assert.ok(m.includes(s), s);
});

test("api e menu do acompanhamento", () => {
  const api = ler("app/lib/api.ts");
  for (const s of ["getAcompanhamento", "definirMetaSprint", "getMetaSprint", "getEventosMeta"]) assert.ok(api.includes(s), s);
  assert.match(ler("app/components/shell/navItems.ts"), /isOwnerOrLider\(cargo\)[\s\S]{0,200}\/acompanhamento/);
});
```

- [ ] **Step 2: Rodar e ver falhar** — `npm test`.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4:** `npx tsc --noEmit && npm test`.
- [ ] **Step 5: Commit:** `feat(ui): tela de acompanhamento dos projetos com metas por sprint`.

---

### Task 5: Selo da meta no planejamento do gerente e verificação final

**Files:**
- Modify: `docudata-backend/routers/funcionalidades.py` e o helper de enriquecimento em lote (`com_tem_tasks`, em `services/aprovacao_funcionalidade.py`)
  - acrescente `meta_sprints: list[int]`, com os números das sprints ainda não fechadas cuja meta contém a funcionalidade, calculado em lote;
  - o gerente pode ler esse campo, porque a meta é só leitura para ele.
- Modify: o componente onde o gerente vê as funcionalidades por sprint e a aba Escopo. Encontre com `grep -rln "tem_tasks" docudata-frontend/app/components`.
- Modify: `docudata-frontend/app/lib/api.ts` (`meta_sprints?: number[]` no tipo de funcionalidade)
- Test: `docudata-backend/tests/test_metas.py` (acrescentar) e `docudata-frontend/tests/acompanhamento.test.mjs` (acrescentar)

- [ ] **Step 1: Testes que falham:**
  - a resposta de funcionalidade traz `meta_sprints == [3]` quando ela está na meta da sprint 3 aberta, e `[]` depois que a sprint 3 fecha;
  - teste estrutural: o literal `meta da sprint` aparece no componente da aba Escopo.
- [ ] **Step 2: Implementar:**
  - backend em lote, com uma consulta em `sprint_meta_funcionalidades` pelos ids das funcionalidades e um join com `sprints` para o número e o fechamento;
  - frontend: um `Chip` violeta `meta da sprint N` ao lado do status, para cada número em `meta_sprints`.
- [ ] **Step 3: Verificação completa:**

```bash
cd docudata-backend && python3 -m pytest -q
cd ../docudata-frontend && npx tsc --noEmit && npm test && npm run build && npm audit --omit=dev --audit-level=high
```

Esperado: no backend, só a falha pré-existente. No frontend, tudo verde, build ok e `found 0 vulnerabilities`.

- [ ] **Step 4: Commit:** `feat(metas): selo da meta da sprint no planejamento do gerente`.

---

## Depois da entrega (controlador)

1. Revisão final da entrega, onda de correção e re-revisão.
2. Push e PR.
3. O usuário aplica o bloco "Rodada B1" no SQL Editor.
4. Merge: migração → backend → frontend.
5. Conferir `/acompanhamento` em produção e definir uma meta de teste.
