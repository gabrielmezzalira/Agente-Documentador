# B1 · Dashboard de acompanhamento (BI) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar a tela `/acompanhamento` (cards por gerente) por um dashboard de carteira com 4 blocos — KPIs com variação, fila "Precisa de você", mapa de calor por sprint, risco de prazo e quadro por gerente — e por um painel lateral de detalhe de cada projeto com diagnóstico, meta, sprint a sprint e o time com piso.

**Architecture:**
- **Regras puras novas:**
  - `services/status_projeto.py`: sinais, status, motivos e diagnóstico;
  - `services/piso.py`: piso por pessoa, calculado ao vivo.
- **`services/acompanhamento.py`:** ganha a sprint relativa, a janela de "features entregues", o mapa de calor, os KPIs, a dispersão e o resumo por gerente. A rota `GET /acompanhamento` passa a devolver a resposta do dashboard. A rota nova `GET /acompanhamento/projetos/{id}` devolve o detalhe.
- **Frontend:** reescreve `app/acompanhamento/page.tsx` com gráficos em SVG próprio, cria `ProjetoDetalhePainel.tsx` e reaproveita `DefinirMetaModal.tsx` e o histórico da meta da entrega 2.
- **Banco:** sem migração.

**Tech Stack:** FastAPI + supabase-py, pytest com `tests/fake_supabase.py`; Next.js 15 / React 19, estilos inline, `app/components/ds`, `app/lib/ds.ts`.

**Spec:** `docs/superpowers/specs/2026-10-28-dashboard-acompanhamento-design.md` (complementa `docs/superpowers/specs/2026-10-28-acompanhamento-projetos-design.md`; regras de meta, entregue, SPI, previsto e risco (a)/(b) vêm de lá e da entrega 2 já em produção).

## Global Constraints

- Só líder e owner (`require_role("lider")`) nas duas rotas. Gerente e operacional recebem 403.
- **SPI da sprint:** `spi_de(tasks_da_sprint)` de `services/acompanhamento.py` (realizado sem extras ÷ previsto de `previsto_de`). Sem previsto, `None`.
- **Sprint atual:** a de maior `numero` com `iniciada = true` (`escolher_sprints`). **Sprints relativas:** a atual e as iniciadas anteriores por `numero` decrescente, no máximo 6 (do −5 até a atual).
- **Entregue:**
  - status `concluida` e `aprovada_em` preenchido;
  - numa sprint fechada, só se `aprovada_em <= avaliacao_completa_em` (`funcionalidade_entregue` de `services/metas.py`).
- **Features entregues numa sprint:** funcionalidades do projeto com `aprovada_em` dentro da janela da sprint.
  - **Início da janela:** `data_inicio` às 00:00 UTC. Sem `data_inicio`, o fechamento da sprint anterior. Sem nenhum dos dois, `None`.
  - **Fim da janela:** `avaliacao_completa_em`, ou "agora" na sprint atual não fechada.
  - **Limites:** a janela é fechada no início e aberta no fim.
- **Thresholds e motivos:** valores e textos literais na Task 1.
- **Piso:** `0,5 × máx(mediana_squad(sprint −1), mediana_subarea(trimestre civil anterior))`, com uma casa decimal.
  - **Realizado:** pontos das tasks `concluida` e não extras daquela sprint, por `operacional_id`.
  - **Squad:** operacionais com pelo menos uma task na sprint.
  - **Trimestre de uma sprint:** o de `avaliacao_completa_em`; sem ele, o de `data_fim`; sem nenhum, a sprint fica fora.
  - Usa a mediana que existir; sem nenhuma, devolve `None`.
- **Desempenho:** toda leitura em lote (≤100 ids por `.in_`, `ler_tudo` com `.order`); nada por sprint nem por task. O piso da subárea só é calculado na rota de detalhe.
- **Dado faltando:** nunca devolver 0 no lugar de "não sei". Usar `None` e mostrar "sem dado" na tela.
- **Backend:** `cd docudata-backend && python3 -m pytest -q`. `tests/test_security.py::test_dependencias_separam_browser_automacoes_e_webhooks_publicos` já falha em Python 3.13; não é regressão.
- **Frontend:**
  - `cd docudata-frontend && npx tsc --noEmit && npm test`;
  - a worktree não tem `node_modules`: usar symlink para `../Documentador/docudata-frontend/node_modules`, remover antes do commit e restaurar `tsconfig.tsbuildinfo` e `next-env.d.ts`;
  - sem lib nova; gráficos em SVG à mão, seguindo `app/components/MetricasTab.tsx`; cores de `app/lib/ds.ts`;
  - textos da interface em português.
- **Commits:**
  - nunca commitar `docudata-backend/supabase_schema.sql` (mudança local do usuário) nem `.planning/`; stage por caminho explícito;
  - mensagens em português, `feat(escopo): ...`, com o trailer `Co-Authored-By` do modelo que escreveu.

---

### Task 1: Status do projeto, motivos e diagnóstico (puro)

**Files:**
- Create: `docudata-backend/services/status_projeto.py`
- Test: `docudata-backend/tests/test_status_projeto.py`

**Interfaces:**
- Produces:
  - `sinais_do_projeto(d: dict) -> list[dict]`. O dict `d` tem: `spi_atual: float|None`, `spis_recentes: list[float|None]` (da mais recente para a mais antiga), `prazo_escopo: dict` (de `calcular_bloco_a`), `tolerancia: float`, `ultima_fechada: dict|None` (`meta_total`, `meta_entregues`), `travadas: int`, `tem_meta_atual: bool`, `tem_planejamento_atual: bool`, `tem_gerente: bool` e `tem_sprint: bool`.
  - Cada sinal é `{"codigo": str, "texto": str}`.
  - `status_de(sinais) -> str`, que devolve `"critico"`, `"atencao"`, `"sem_dados"` ou `"saudavel"`.
  - `motivos(sinais, n=2) -> list[str]`.
  - `diagnostico(status, sinais) -> str`.
  - `ORDEM_STATUS = {"critico": 0, "atencao": 1, "sem_dados": 2, "saudavel": 3}`.

- [ ] **Step 1: Testes que falham** (tabela de casos)

```python
# docudata-backend/tests/test_status_projeto.py
import pytest
from services.status_projeto import sinais_do_projeto, status_de, motivos, diagnostico

BASE = dict(spi_atual=0.95, spis_recentes=[0.95, 0.92, 0.91], prazo_escopo={"sem_dados": False, "pct_prazo_consumido": 40.0, "pct_escopo_concluido": 35.0},
            tolerancia=20, ultima_fechada={"meta_total": 2, "meta_entregues": 2}, travadas=0,
            tem_meta_atual=True, tem_planejamento_atual=True, tem_gerente=True, tem_sprint=True)

def caso(**kw):
    d = dict(BASE); d.update(kw); return d

def codigos(d):
    return [s["codigo"] for s in sinais_do_projeto(d)]

def test_saudavel():
    s = sinais_do_projeto(caso())
    assert s == [] and status_de(s) == "saudavel"

@pytest.mark.parametrize("kw,cod,status", [
    (dict(spi_atual=0.33), "spi_critico", "critico"),
    (dict(prazo_escopo={"sem_dados": False, "pct_prazo_consumido": 95.0, "pct_escopo_concluido": 0.0}), "prazo", "critico"),
    (dict(ultima_fechada={"meta_total": 3, "meta_entregues": 1}), "meta_ruim", "critico"),
    (dict(travadas=5), "travadas", "critico"),
    (dict(travadas=2), "travadas", "atencao"),
    (dict(spi_atual=0.85, spis_recentes=[0.85, 0.8, 0.88]), "spi_caindo", "atencao"),
    (dict(tem_meta_atual=False), "sem_meta", "atencao"),
    (dict(tem_planejamento_atual=False), "sem_planejamento", "sem_dados"),
    (dict(prazo_escopo={"sem_dados": True}), "sem_datas", "sem_dados"),
    (dict(tem_gerente=False), "sem_gerente", "sem_dados"),
    (dict(tem_sprint=False, spi_atual=None, spis_recentes=[], tem_meta_atual=False, tem_planejamento_atual=False), "sem_sprint", "sem_dados"),
])
def test_sinal_e_status(kw, cod, status):
    s = sinais_do_projeto(caso(**kw))
    assert cod in [x["codigo"] for x in s]
    assert status_de(s) == status

def test_spi_caindo_exige_tres_sprints_abaixo_de_09():
    assert "spi_caindo" not in codigos(caso(spi_atual=0.85, spis_recentes=[0.85, 0.95, 0.8]))
    assert "spi_caindo" not in codigos(caso(spi_atual=0.85, spis_recentes=[0.85, 0.8]))

def test_meta_ruim_ignora_sprint_sem_meta():
    assert "meta_ruim" not in codigos(caso(ultima_fechada={"meta_total": 0, "meta_entregues": 0}))
    assert "meta_ruim" not in codigos(caso(ultima_fechada={"meta_total": 2, "meta_entregues": 1}))  # 50% não dispara

def test_sem_sprint_nao_gera_sem_meta_nem_sem_planejamento():
    c = codigos(caso(tem_sprint=False, spi_atual=None, spis_recentes=[], tem_meta_atual=False, tem_planejamento_atual=False))
    assert "sem_meta" not in c and "sem_planejamento" not in c

def test_textos_e_prioridade_dos_motivos():
    s = sinais_do_projeto(caso(spi_atual=0.33, travadas=6, tem_meta_atual=False, tem_gerente=False,
                               prazo_escopo={"sem_dados": False, "pct_prazo_consumido": 95.0, "pct_escopo_concluido": 0.0}))
    assert motivos(s) == ["SPI 0,33", "95% do prazo · 0% entregue"]
    textos = {x["codigo"]: x["texto"] for x in s}
    assert textos["travadas"] == "6 travadas"
    assert textos["sem_meta"] == "sem meta"
    assert textos["sem_gerente"] == "sem gerente"

def test_diagnostico():
    s = sinais_do_projeto(caso(spi_atual=0.33, tem_gerente=False))
    txt = diagnostico(status_de(s), s)
    assert txt.startswith("Crítico.")
    assert "SPI 0,33" in txt
    assert txt.endswith("Falta preencher: sem gerente.")
    assert diagnostico("saudavel", []) == "Saudável."
```

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar**

```python
# docudata-backend/services/status_projeto.py
"""Status do projeto no dashboard (B1): sinais → status, motivos e diagnóstico."""

ORDEM_STATUS = {"critico": 0, "atencao": 1, "sem_dados": 2, "saudavel": 3}
PRIORIDADE = ["spi_critico", "prazo", "meta_ruim", "travadas", "spi_caindo", "sem_meta",
              "sem_sprint", "sem_planejamento", "sem_datas", "sem_gerente"]
FALTA = {"sem_sprint", "sem_planejamento", "sem_datas", "sem_gerente"}
ROTULO = {"critico": "Crítico.", "atencao": "Atenção.", "sem_dados": "Faltam dados.", "saudavel": "Saudável."}


def _num(v: float, casas: int = 2) -> str:
    return f"{v:.{casas}f}".rstrip("0").rstrip(".").replace(".", ",") if casas else f"{v:.0f}"


def sinais_do_projeto(d: dict) -> list[dict]:
    s: list[dict] = []
    def add(codigo, texto):
        s.append({"codigo": codigo, "texto": texto})

    spi = d.get("spi_atual")
    if spi is not None and spi < 0.7:
        add("spi_critico", f"SPI {_num(spi)}")
    pe = d.get("prazo_escopo") or {}
    if not pe.get("sem_dados", True):
        if pe["pct_prazo_consumido"] - pe["pct_escopo_concluido"] > (d.get("tolerancia") or 0):
            add("prazo", f"{_num(pe['pct_prazo_consumido'], 0)}% do prazo · {_num(pe['pct_escopo_concluido'], 0)}% entregue")
    uf = d.get("ultima_fechada") or {}
    if uf.get("meta_total"):
        if uf["meta_entregues"] / uf["meta_total"] < 0.5:
            add("meta_ruim", f"meta da última sprint {uf['meta_entregues']}/{uf['meta_total']}")
    if d.get("travadas", 0) > 0:
        add("travadas", f"{d['travadas']} travada" + ("s" if d["travadas"] > 1 else ""))
    rec = [x for x in d.get("spis_recentes") or [] if x is not None][:3]
    if len(rec) == 3 and all(x < 0.9 for x in rec) and not any(x["codigo"] == "spi_critico" for x in s):
        add("spi_caindo", "SPI abaixo de 0,9 há 3 sprints")
    if not d.get("tem_sprint"):
        add("sem_sprint", "nenhuma sprint iniciada")
    else:
        if not d.get("tem_meta_atual"):
            add("sem_meta", "sem meta")
        if not d.get("tem_planejamento_atual"):
            add("sem_planejamento", "sem planejamento")
    if pe.get("sem_dados", True):
        add("sem_datas", "sem datas do contrato")
    if not d.get("tem_gerente"):
        add("sem_gerente", "sem gerente")
    return sorted(s, key=lambda x: PRIORIDADE.index(x["codigo"]))


def status_de(sinais: list[dict]) -> str:
    cods = {x["codigo"] for x in sinais}
    travadas = next((int(x["texto"].split()[0]) for x in sinais if x["codigo"] == "travadas"), 0)
    if cods & {"spi_critico", "prazo", "meta_ruim"} or travadas >= 5:
        return "critico"
    if cods & {"spi_caindo", "travadas", "sem_meta"}:
        return "atencao"
    if cods & FALTA:
        return "sem_dados"
    return "saudavel"


def motivos(sinais: list[dict], n: int = 2) -> list[str]:
    return [x["texto"] for x in sinais[:n]]


def diagnostico(status: str, sinais: list[dict]) -> str:
    partes = [ROTULO[status]]
    fatos = [x["texto"] for x in sinais if x["codigo"] not in FALTA]
    if fatos:
        partes.append(" · ".join(fatos) + ".")
    falta = [x["texto"] for x in sinais if x["codigo"] in FALTA]
    if falta:
        partes.append("Falta preencher: " + ", ".join(falta) + ".")
    return " ".join(partes)
```

Observação: o teste `test_sinal_e_status` com `spi_atual=0.85, spis_recentes=[0.85, 0.8, 0.88]` espera `spi_caindo`. Ajuste `_num` se a formatação de `0,33` ou `95` divergir dos textos do teste; **os textos do teste são o contrato**.

- [ ] **Step 4: Rodar e ver passar.**
- [ ] **Step 5: Commit:** `feat(acompanhamento): status do projeto, motivos e diagnóstico por regras`.

---

### Task 2: Dados do dashboard (`GET /acompanhamento`)

**Files:**
- Modify: `docudata-backend/services/acompanhamento.py`, `docudata-backend/routers/acompanhamento.py`, `docudata-backend/models/schemas.py`
- Test: `docudata-backend/tests/test_acompanhamento.py` (atualizar os testes de forma do JSON; manter os de regra que continuam valendo)

**Interfaces:**
- Consumes: Task 1 (`sinais_do_projeto`, `status_de`, `motivos`, `diagnostico`, `ORDEM_STATUS`); entrega 2 (`spi_de`, `previsto_de`, `escolher_sprints`, `calcular_projeto`, `funcionalidade_entregue`, `metas_das_sprints`, `calcular_bloco_a`).
- Produces (funções puras novas):
  - `sprints_relativas(sprints) -> list[dict]`: até 6, da atual para trás; cada item com `numero`, `id` e `rel` (0, −1, …);
  - `janela_da_sprint(sprint, anterior, agora) -> tuple[datetime|None, datetime]`;
  - `features_entregues_na_janela(funcs, inicio, fim) -> int | None`: devolve `None` se `inicio` for `None`;
  - `variacao(atual, anterior) -> float | None`.
- `GET /acompanhamento?subarea=dados|dev&gerente_email=` devolve este JSON:

```json
{
  "subarea": "dados",
  "filtro_gerente": null,
  "gerentes": [{"nome": "Felipe Coutinho", "email": "felipe@citi.org.br"}],
  "kpis": {
    "projetos": 6, "criticos": 2, "atencao": 1, "sem_dados": 2, "saudaveis": 1,
    "features_entregues": 4, "features_entregues_var": 2,
    "spi_medio": 0.78, "spi_medio_var": -0.09,
    "metas_batidas": 1, "metas_fechadas": 3, "projetos_sem_meta": 3,
    "tasks_travadas": 11
  },
  "fila": [{"projeto_id": "uuid", "nome": "Acreditar – Dados", "gerente": "Felipe Coutinho", "status": "critico", "motivos": ["SPI 0,33", "95% do prazo · 0% entregue"]}],
  "mapa": [{"projeto_id": "uuid", "nome": "Acreditar – Dados",
            "sprints": [{"rel": -5, "numero": 1, "spi": 0.95, "meta_total": 0, "meta_entregues": 0, "meta_batida": null}]}],
  "dispersao": {"pontos": [{"projeto_id": "uuid", "nome": "Visus", "pct_prazo": 100.0, "pct_escopo": 0.0, "travadas": 6, "status": "critico"}],
                "sem_datas": 4},
  "por_gerente": [{"nome": "Felipe Coutinho", "email": "felipe@citi.org.br", "projetos": 2, "criticos": 2, "atencao": 0, "metas_batidas": 0, "metas_fechadas": 1}],
  "projetos": [{"id": "uuid", "nome": "...", "status": "critico", "motivos": ["..."], "diagnostico": "..."}]
}
```

Regras:
- **`mapa[].sprints`:** sempre 6 posições (`rel` −5…0). Posição sem sprint → `{"rel": r, "numero": null, "spi": null, ...}`. A meta de cada sprint vem de `metas_das_sprints` e os entregues de `funcionalidade_entregue(f, sprint.avaliacao_completa_em)`.
- **`kpis`:**
  - `features_entregues` = soma de `features_entregues_na_janela` da sprint atual de cada projeto (ignora `None`); `_var` = essa soma − a mesma soma na sprint −1, ou `None` se nenhum projeto tiver as duas;
  - `spi_medio` = média dos `spi_atual` não nulos; `_var` = `spi_medio` − média dos SPIs da −1, com os mesmos cuidados;
  - `metas_*` seguem a entrega 2: `metas_fechadas` = projetos cuja última sprint fechada tinha meta; `projetos_sem_meta` = projetos com sprint atual e sem meta;
  - arredondamento: SPI com 2 casas, variações com 2 casas.
- **`fila`:** projetos com status ≠ `saudavel`, ordenados por `ORDEM_STATUS` e depois pelo número de sinais (mais sinais primeiro) e pelo nome.
- **`dispersao.pontos`:** só projetos com datas do contrato; `sem_datas` é a contagem dos outros.
- **`por_gerente`:** ordenado por nome, com "Sem gerente" no fim.
- **`gerentes`:** a lista para o filtro, sempre com todos os gerentes da subárea, mesmo com o filtro aplicado.
- **Filtro `gerente_email`:** aplicado (sem diferenciar maiúsculas) antes de calcular kpis, fila, mapa e dispersão. `gerente_email=sem` filtra os projetos sem gerente.
- **Sinais de cada projeto:** montados com os dados que `calcular_projeto` já produz, mais `spis_recentes` (os SPIs do mapa, do mais recente para trás), `tem_meta_atual`, `tem_planejamento_atual`, `tem_gerente` e `tem_sprint`.

- [ ] **Step 1: Testes que falham.**
  - **Puras:** `sprints_relativas` com 2 sprints e com 8; `janela_da_sprint` com e sem `data_inicio`; `features_entregues_na_janela` nos limites (inclusivo no início, exclusivo no fim) e com `None`; `variacao`.
  - **Rota com `fake_supabase`**, com 2 gerentes e 4 projetos (um crítico, um saudável, um sem datas, um sem gerente):
    - os kpis batem;
    - a fila está na ordem certa e sem o saudável;
    - o mapa tem 6 posições;
    - a dispersão exclui o projeto sem datas (`sem_datas == 1`);
    - o filtro por gerente e o `gerente_email=sem` funcionam;
    - gerente e operacional recebem 403.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.** Reaproveite os carregamentos em lote de `montar_acompanhamento`; não acrescente consultas por sprint.
- [ ] **Step 4: Rodar a suíte inteira.**
- [ ] **Step 5: Commit:** `feat(acompanhamento): dados do dashboard (kpis, fila, mapa por sprint, dispersão, por gerente)`.

---

### Task 3: Piso ao vivo e detalhe do projeto (`GET /acompanhamento/projetos/{id}`)

**Files:**
- Create: `docudata-backend/services/piso.py`
- Modify: `docudata-backend/services/acompanhamento.py` (`montar_detalhe(client, projeto_id, agora=None)`), `docudata-backend/routers/acompanhamento.py`, `docudata-backend/models/schemas.py`
- Test: `docudata-backend/tests/test_piso.py`, `docudata-backend/tests/test_acompanhamento.py` (acrescentar)

**Interfaces:**
- Produces (puras, em `services/piso.py`):
  - `realizados_por_pessoa(tasks) -> dict[str, float]`: considera só `coluna_kanban == "concluida"`, sem extras e com `operacional_id`;
  - `squad(tasks) -> set[str]`: operacionais com pelo menos uma task;
  - `mediana(valores) -> float | None`;
  - `piso(mediana_squad, mediana_subarea) -> float | None`;
  - `trimestre_de(sprint) -> str | None`, no formato `"2026-T4"`;
  - `trimestre_anterior(t) -> str`.
- `GET /acompanhamento/projetos/{id}` (`require_role("lider")`, 404 se não existir) devolve este JSON:

```json
{
  "projeto": {"id": "uuid", "nome": "...", "cliente": "...", "gerente": "Felipe Coutinho"},
  "status": "critico", "diagnostico": "Crítico. SPI 0,33 · ... Falta preencher: sem meta.", "sinais": [{"codigo": "...", "texto": "..."}],
  "numeros": {"spi_atual": 0.33, "pct_prazo": 95.0, "pct_escopo": 0.0, "prazo_sem_dados": false, "travadas": 5, "p85_horas": 30.0},
  "sprint_atual": {"id": "uuid", "numero": 4, "fechada": false},
  "proximas_sprints": [{"id": "uuid", "numero": 5, "fechada": false}],
  "meta": {"total": 3, "entregues": 1, "batida": null, "funcionalidades": [{"id": "uuid", "id_funcional": "F3", "titulo": "...", "status": "concluida", "aprovada": true, "pct_tasks": 100.0, "planejada_na_sprint": true}]},
  "planejadas_fora_da_meta": [{"id": "uuid", "id_funcional": "F8", "titulo": "..."}],
  "sprints": [{"numero": 1, "previsto": 20, "realizado": 18, "spi": 0.9, "meta_batida": true}],
  "time": {"sprint_numero": 4, "mediana_squad": 6.0, "mediana_subarea": 5.0, "pessoas": [{"operacional_id": "uuid", "nome": "Ana", "realizado": 6.0, "piso": 3.0, "abaixo": false}]}
}
```

Regras:
- **`sprints`:** até 6 sprints iniciadas, da mais antiga para a mais recente, com previsto e realizado (`previsto_de` e realizado sem extras).
- **`time.pessoas`:** o squad da sprint atual, com `nome` vindo de `operacionais`.
  - **`mediana_squad`:** a mediana dos realizados do squad na sprint −1.
  - **`mediana_subarea`:** a mediana dos realizados de todos os pares pessoa×sprint de sprints da mesma subárea com `trimestre_de` igual ao trimestre anterior ao da sprint atual. O trimestre da sprint atual é `trimestre_de(sprint_atual)`; se for `None`, use o trimestre de "agora".
  - **Leitura:** as tasks dessas sprints são lidas em lote: primeiro as sprints da subárea, depois as tasks por `.in_("sprint_id", lote)`.
  - **Sem squad:** `pessoas` vem vazio.
  - **`abaixo`:** `None` quando o piso é `None`.
- **Status, sinais e diagnóstico:** os mesmos do dashboard, saídos das mesmas funções.

- [ ] **Step 1: Testes que falham.**
  - **`test_piso.py`:**
    - mediana com número par, ímpar e vazio;
    - piso: as duas medianas (usa a maior), só uma, nenhuma (`None`) e arredondamento com 1 casa;
    - `trimestre_de` com fechamento, só com `data_fim` e sem nenhum dos dois;
    - virada T1 → T4 do ano anterior;
    - `realizados_por_pessoa` ignora extras, tasks não concluídas e tasks sem operacional.
  - **Rota:**
    - a forma do JSON;
    - o time com uma pessoa abaixo do piso;
    - um projeto sem sprint −1 (usa só a mediana da subárea);
    - 404 para projeto inexistente;
    - 403 para gerente.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar a suíte inteira.**
- [ ] **Step 5: Commit:** `feat(acompanhamento): detalhe do projeto com sprint a sprint e piso por pessoa`.

---

### Task 4: Tela do dashboard

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts`
  - tipos que espelham o JSON das Tasks 2 e 3;
  - `getAcompanhamento(subarea, gerenteEmail?)` com o formato novo;
  - `getDetalheProjeto(id)`.
- Rewrite: `docudata-frontend/app/acompanhamento/page.tsx`
- Create: `docudata-frontend/app/components/acompanhamento/MapaCalor.tsx`, `docudata-frontend/app/components/acompanhamento/DispersaoPrazo.tsx`
- Test: `docudata-frontend/tests/acompanhamento.test.mjs` (reescrever)

**Layout** (o mockup aprovado está em `.superpowers/brainstorm/*/content/layout-combinado.html`; use-o como referência visual):
- **Topo:**
  - título `Acompanhamento dos projetos` e subtítulo `Saúde da carteira por sprint, e quem precisa de você.`;
  - à direita, `SegmentedControl` Dados/Dev e um `Select` de gerente com `Todos os gerentes`, cada gerente e `Sem gerente`.
  - Cada mudança refaz a busca, com guarda contra resposta antiga (padrão da entrega 2).
- **Bloco 1:** grid de 5 `Card` KPI.
  - **Rótulos:** `Projetos`, `Features entregues`, `SPI médio`, `Metas batidas` e `Tasks travadas`.
  - **Subtextos:**
    - `N críticos · M atenção`;
    - variação `▲ 2` / `▼ 0,09`, verde quando melhora e vermelho quando piora; para travadas não há variação;
    - em Metas batidas, `A de B` com o subtexto `N projetos sem meta`;
    - variação `None` mostra `sem comparação`.
  - **Layout:** em tela estreita, 2 colunas.
- **Bloco 2, `Precisa de você`:**
  - **Linha:** bolinha de status (vermelho/âmbar/cinza), nome, gerente em cinza e os chips dos motivos (vermelho se crítico, âmbar se atenção, cinza se faltam dados).
  - **Interação:** a linha é um `<button>` acessível que abre o detalhe.
  - **Vazio:** `Nenhum projeto precisa de atenção agora.`
- **Bloco 3, `Evolução por sprint`:** `MapaCalor`, um grid CSS ou SVG.
  - **Colunas:** `−5 … −1` e `atual`.
  - **Células:** verde se SPI ≥ 0,9, âmbar se ≥ 0,7, vermelho se < 0,7, cinza se não houver dado. Cada célula tem `role="img"` e `aria-label` `Sprint N · SPI X · meta A/B` (ou `sem dado`).
  - **Legenda:** `≥ 0,9`, `0,7–0,9`, `< 0,7`, `sem dado`.
  - **Interação:** o nome do projeto é um botão que abre o detalhe.
- **Bloco 4, `Risco de prazo`:** `DispersaoPrazo` em SVG, com o painel `Por gerente` ao lado.
  - **Dispersão:**
    - eixos de 0 a 100%, com rótulos `% do prazo consumido` e `% das funcionalidades aprovadas`;
    - diagonal tracejada;
    - bolha na cor do status, com raio `4 + 2*sqrt(travadas)` e `<title>` com nome, prazo, escopo e travadas;
    - clicar abre o detalhe;
    - nota `N projetos sem datas do contrato` quando `sem_datas > 0`.
  - **Por gerente:** linhas com `nome · N proj · X críticos · Y atenção · metas A/B`; clicar aplica o filtro daquele gerente.
- **Estados:**
  - carregando, vazio (`Nenhum projeto nesta subárea.`) e erro com `ErrorNotice`;
  - guarda de cargo com o aviso padrão de acesso restrito, como hoje.
- **Detalhe:** o estado `projetoAberto` abre o `ProjetoDetalhePainel` (Task 5). Nesta task, deixe um placeholder simples que mostre o nome do projeto.

- [ ] **Step 1: Teste estrutural que falha**

```js
// docudata-frontend/tests/acompanhamento.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("dashboard de acompanhamento tem os 4 blocos e filtros", () => {
  const p = ler("app/acompanhamento/page.tsx");
  for (const s of ["Acompanhamento dos projetos", "Precisa de você", "Evolução por sprint", "Risco de prazo", "Por gerente",
                   "Features entregues", "SPI médio", "Metas batidas", "Tasks travadas", "Todos os gerentes",
                   "Nenhum projeto precisa de atenção agora.", "sem comparação"]) assert.ok(p.includes(s), s);
});

test("mapa de calor e dispersão", () => {
  assert.ok(existsSync(new URL("../app/components/acompanhamento/MapaCalor.tsx", import.meta.url)));
  const m = ler("app/components/acompanhamento/MapaCalor.tsx");
  for (const s of ["sem dado", "≥ 0,9", "0,7–0,9", "< 0,7", "aria-label"]) assert.ok(m.includes(s), s);
  const d = ler("app/components/acompanhamento/DispersaoPrazo.tsx");
  for (const s of ["% do prazo consumido", "% das funcionalidades aprovadas", "sem datas do contrato", "<title>"]) assert.ok(d.includes(s), s);
});

test("api e menu", () => {
  const api = ler("app/lib/api.ts");
  for (const s of ["getAcompanhamento", "getDetalheProjeto", "definirMetaSprint", "getEventosMeta"]) assert.ok(api.includes(s), s);
  assert.match(ler("app/components/shell/navItems.ts"), /isOwnerOrLider\(cargo\)[\s\S]{0,200}\/acompanhamento/);
});
```

- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.**
- [ ] **Step 4:** `npx tsc --noEmit && npm test`.
- [ ] **Step 5: Commit:** `feat(ui): dashboard de acompanhamento (KPIs, fila, mapa por sprint, risco de prazo)`.

---

### Task 5: Painel de detalhe do projeto e verificação final

**Files:**
- Create: `docudata-frontend/app/components/acompanhamento/ProjetoDetalhePainel.tsx`
- Modify: `docudata-frontend/app/acompanhamento/page.tsx` (troca o placeholder pelo painel)
- Modify: `docudata-frontend/app/components/DefinirMetaModal.tsx` só se for preciso para receber as sprints do detalhe. Mantenha as regras da entrega 2: só sprints abertas, `metaCarregada` amarrado ao `sprintId` e Salvar exigindo as funcionalidades carregadas.
- Test: `docudata-frontend/tests/acompanhamento.test.mjs` (acrescentar)

**Painel:** `Modal` do design system com `width={760}` e título `<nome> · <gerente>`. Carrega com `getDetalheProjeto` (estados de carregando e erro). Contém:
1. **Diagnóstico:** caixa com a borda na cor do status e o texto de `diagnostico`.
2. **4 números:** `SPI da sprint atual`, `Prazo × escopo` (`95% · 0%` ou `sem datas`), `Tasks travadas` e `p85 tempo limpo` (`30h` ou `sem dado`).
3. **`Sprint N (atual) · meta A de B entregue`** com o botão `Definir meta`, que abre o `DefinirMetaModal` e, depois de salvar, recarrega o detalhe e o dashboard.
   - Abaixo, as funcionalidades da meta, cada uma com selos e um `ProgressBar` de % de tasks.
   - Depois: `Planejadas fora da meta:` e o link `Histórico de mudanças da meta`, que reaproveita o histórico da entrega 2.
   - Sem meta: `Sem meta nesta sprint.` com o botão.
4. **`Sprint a sprint`:** barras em SVG de previsto (cinza) × realizado (na cor do SPI). Um ● embaixo marca as sprints com `meta_batida`. A legenda é `previsto · realizado · ● meta batida`.
5. **`Time · sprint N`:** uma linha por pessoa com o nome, o realizado em pts e o chip `acima` (verde) ou `abaixo do piso (X)` (vermelho).
   - Piso `None` → `sem histórico para o piso`.
   - Squad vazio → `Ninguém com task nesta sprint.`

- [ ] **Step 1: Teste estrutural que falha** (acrescentar)

```js
test("painel de detalhe do projeto", () => {
  const p = ler("app/components/acompanhamento/ProjetoDetalhePainel.tsx");
  for (const s of ["Definir meta", "Sprint a sprint", "abaixo do piso", "sem histórico para o piso", "Planejadas fora da meta:",
                   "Histórico de mudanças da meta", "Sem meta nesta sprint.", "meta batida"]) assert.ok(p.includes(s), s);
  assert.ok(ler("app/acompanhamento/page.tsx").includes("ProjetoDetalhePainel"));
});
```

- [ ] **Step 2: Implementar.**
- [ ] **Step 3: Verificação completa:**

```bash
cd docudata-backend && python3 -m pytest -q
cd ../docudata-frontend && npx tsc --noEmit && npm test && npm run build && npm audit --omit=dev --audit-level=high
```

Esperado: no backend, só a falha pré-existente; no frontend, tudo verde, build ok e `found 0 vulnerabilities`.

- [ ] **Step 4: Commit:** `feat(ui): painel de detalhe do projeto com diagnóstico, meta, sprint a sprint e time`.

---

## Depois (controlador)

1. Revisão final, onda de correção e re-revisão.
2. Push e PR (sem migração).
3. Merge, se o usuário autorizar.
4. Conferir em produção junto com o backfill do status (entrega 1).
