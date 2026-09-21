# Modos de Trabalho e de Avaliação — Entrega 3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar a lacuna deixada pela Entrega 2 real: implementar a fórmula `PONTOS_RELATIVO` de verdade, a fila de puxada real (hidratação, pull atômico, devolução) e a migração estruturada de modo `ATRIBUICAO ↔ PULL` no meio de um projeto — tudo o que o roadmap original da Entrega 1 previa para "Entrega 2 — O experimento roda" e nunca foi construído.

**Architecture:** Três ondas sequenciais, cada uma implementável e verificável isoladamente. **Onda A** (Tasks 1-6, back-end + 1 UI): fórmula relativa no motor de score. **Onda B** (Tasks 7-13, back-end puro): schema de fila + hidratação + migração de modo — o schema/hidratação nasce aqui porque a migração já precisa gravar nessas colunas, mesmo sendo conceitualmente parte da fila (ver spec §1.1). **Onda C** (Tasks 14-17, back-end + UI): pull atômico, devolução, pergunta condicional, botões no Kanban.

**Tech Stack:** FastAPI + Supabase PostgreSQL (`supabase-py` v2 sync) no backend; Next.js 15 / React 19 com inline `style={{}}` no frontend (sem Tailwind/design-system formal).

**Spec:** `docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega3-design.md`

## Global Constraints

- Schema sempre idempotente (`ADD COLUMN IF NOT EXISTS` / `CREATE TABLE IF NOT EXISTS`), anexado ao final de `docudata-backend/supabase_schema.sql`, **nunca** migração automática — precisa ser colado manualmente no SQL Editor do Supabase depois do merge.
- Antes de escrever qualquer bloco novo no schema, rode `grep -n "Migration v5" docudata-backend/supabase_schema.sql` e confirme que o bloco comentado ainda existe mais abaixo — o novo SQL vai **antes** dele (mesma regra que já corrigiu `test_migration_v5_e_somente_aditiva_e_comentada` na Entrega 1).
- Golden regression: nenhuma sprint com `modo_avaliacao == 'PONTOS_ATRIBUIDOS'` pode ter sua nota alterada por nenhuma task desta entrega. Onde uma task tocar `services/pontuacao.py` ou `services/performance.py`, a suíte completa (`pytest -q`) roda ao final da task, não só o teste novo.
- Nenhuma sprint já fechada (linha já travada em `pontuacao_operacional_sprint`) pode ser recalculada por esta entrega (E3-D4 do spec).
- RBAC de `pessoa` (login) nunca é igual a `operacional_id` (registro por projeto) — os dois são tabelas diferentes, reconciliadas por e-mail (`operacionais.email == pessoa.email`, mesmo padrão de `services/auth.py::require_project_access`). O spec original tem uma pseudocódigo simplificado (`pessoa.id == task.operacional_id`) que **não é literal** — Task 15 corrige isso.
- Um commit por task, TDD (teste falhando → implementação → passa) em todas as tasks de back-end.

---

## Onda A — Motor de score

### Task 1: Schema — colunas congeladas de `PONTOS_RELATIVO`

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (anexar ao final, antes do bloco comentado `Migration v5`)
- Test: `docudata-backend/tests/test_modos_schema.py`

**Interfaces:**
- Produces: colunas `pontuacao_operacional_sprint.entrega_pontos_pessoa` (numeric), `entrega_denominador` (numeric), `entrega_nota_relativa` (numeric) — consumidas pela Task 2 (grava) e Task 3 (lê).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_modos_schema.py — adicionar ao final do arquivo
def test_schema_tem_colunas_da_formula_pontos_relativo():
    schema = open("supabase_schema.sql").read()
    assert "ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_pontos_pessoa numeric(10,2);" in schema
    assert "ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_denominador numeric(10,2);" in schema
    assert "ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_nota_relativa numeric(6,2);" in schema
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-backend && pytest tests/test_modos_schema.py::test_schema_tem_colunas_da_formula_pontos_relativo -v`
Expected: FAIL (assertion error — string não encontrada)

- [ ] **Step 3: Append the migration block**

Antes, rode `grep -n "Migration v5" docudata-backend/supabase_schema.sql` pra confirmar a posição. Insira logo após a linha `ALTER TABLE operacionais ALTER COLUMN data_entrada SET DEFAULT now();` (fim do bloco da Entrega 2) e antes do comentário `-- Migration v5`:

```sql
-- ═══════════════════════════════════════════════════════════════
-- Modos de Trabalho e de Avaliação — Entrega 3, Onda A: fórmula
-- PONTOS_RELATIVO (spec
-- docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega3-design.md §2)
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_pontos_pessoa numeric(10,2);
ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_denominador numeric(10,2);
ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS entrega_nota_relativa numeric(6,2);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_modos_schema.py -v`
Expected: PASS (todos os testes do arquivo, não só o novo)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/supabase_schema.sql docudata-backend/tests/test_modos_schema.py
git commit -m "feat(schema): colunas congeladas da fórmula PONTOS_RELATIVO (Entrega 3)"
```

---

### Task 2: Fórmula `PONTOS_RELATIVO` em `calcular_e_travar_pontuacao`

**Files:**
- Modify: `docudata-backend/services/pontuacao.py:40-43` (select de `projeto_resp`), `:200-238` (loop de `linhas`)
- Test: `docudata-backend/tests/test_pontuacao_fechamento.py`

**Interfaces:**
- Consumes: `listar_vinculados_no_projeto(client, project_id, momento_iso) -> list[dict]` (já existe, `services/elegibilidade.py`); `pontos_concluidos: dict[str, int]` (já calculado no loop de tasks existente).
- Produces: cada linha inserida em `pontuacao_operacional_sprint` ganha `entrega_pontos_pessoa`, `entrega_denominador`, `entrega_nota_relativa` — `None` quando `modo_avaliacao != 'PONTOS_RELATIVO'`, valores calculados quando é.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pontuacao_fechamento.py — adicionar ao final do arquivo
def test_formula_pontos_relativo_usa_piso_e_teto_do_projeto():
    """3 vinculados: A concluiu 6 pontos, B concluiu 2, C não concluiu nada.
    denominador_bruto = (6+2+0)/3 = 2.667; piso=1 não altera (2.667 > 1);
    teto=1.5.
    A: bruta = 6/2.667=2.25 -> min(2.25,1.5)=1.5 -> nota=100
    B: bruta = 2/2.667=0.75 -> min(0.75,1.5)=0.75 -> nota=50.0
    C: bruta = 0/2.667=0 -> nota=0
    """
    operacionais = [
        {"id": "op-a", "nome": "A", "email": "a@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None},
        {"id": "op-b", "nome": "B", "email": "b@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None},
        {"id": "op-c", "nome": "C", "email": "c@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None},
    ]
    tasks = [
        {"id": "t1", "operacional_id": "op-a", "pontos": 6, "coluna_kanban": "concluida", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
        {"id": "t2", "operacional_id": "op-b", "pontos": 2, "coluna_kanban": "concluida", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
    ]
    capture = []
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=tasks,
        operacionais=operacionais,
        projeto={"modo_trabalho": "PULL", "modo_avaliacao": "PONTOS_RELATIVO", "pull_piso_pontos": 1, "pull_teto": 1.5},
        insert_capture=capture,
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    por_op = {r["operacional_id"]: r for r in resultado}
    assert por_op["op-a"]["entrega_nota_relativa"] == 100.0
    assert por_op["op-b"]["entrega_nota_relativa"] == 50.0
    assert por_op["op-c"]["entrega_nota_relativa"] == 0.0
    assert por_op["op-a"]["entrega_pontos_pessoa"] == 6
    assert por_op["op-a"]["entrega_denominador"] == round(8 / 3, 2)


def test_formula_pontos_atribuidos_nao_grava_colunas_relativas():
    tasks = [
        {"id": "t1", "operacional_id": "op-a", "pontos": 6, "coluna_kanban": "concluida", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
    ]
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=tasks,
        operacionais=[{"id": "op-a", "nome": "A", "email": "a@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None}],
        projeto={"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS", "pull_piso_pontos": 1, "pull_teto": 1.5},
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    assert resultado[0]["entrega_pontos_pessoa"] is None
    assert resultado[0]["entrega_denominador"] is None
    assert resultado[0]["entrega_nota_relativa"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pontuacao_fechamento.py -k pontos_relativo -v`
Expected: FAIL (KeyError: 'entrega_nota_relativa' — campo ainda não existe no dict inserido)

- [ ] **Step 3: Write the implementation**

Em `services/pontuacao.py`, linha 40, estenda o select do projeto:

```python
    projeto_resp = client.table("projects").select(
        "modo_trabalho, modo_avaliacao, pull_piso_pontos, pull_teto"
    ).eq("id", project_id).execute()
```

Logo antes do loop `for operacional_id in operacional_ids:` (linha ~203), adicione o cálculo do denominador (uma vez, fora do loop):

```python
    denominador_relativo = None
    if modo_avaliacao == "PONTOS_RELATIVO":
        valores_concluidos = [pontos_concluidos.get(op, 0) for op in vinculados_ids] or [0]
        denominador_bruto = sum(valores_concluidos) / len(valores_concluidos)
        piso = float(projeto_row.get("pull_piso_pontos") or 1)
        denominador_relativo = max(denominador_bruto, piso)
```

Dentro do loop, ao montar cada `linha` (antes do `linhas.append({...})`), calcule os 3 valores:

```python
        entrega_pontos_pessoa = None
        entrega_denominador = None
        entrega_nota_relativa = None
        if modo_avaliacao == "PONTOS_RELATIVO":
            teto = float(projeto_row.get("pull_teto") or 1.5)
            entrega_pontos_pessoa = pontos_concluidos.get(operacional_id, 0)
            entrega_denominador = round(denominador_relativo, 2)
            entrega_bruta = entrega_pontos_pessoa / denominador_relativo if denominador_relativo else 0
            entrega_nota_relativa = round(min(entrega_bruta, teto) * 100 / teto, 2)
```

E adicione os 3 campos ao dict `linhas.append({...})` existente:

```python
            "entrega_pontos_pessoa": entrega_pontos_pessoa,
            "entrega_denominador": entrega_denominador,
            "entrega_nota_relativa": entrega_nota_relativa,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pontuacao_fechamento.py -v`
Expected: PASS (arquivo inteiro — inclui a golden regression dos testes já existentes)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "feat(pontuacao): implementa fórmula PONTOS_RELATIVO com piso/teto (Entrega 3)"
```

---

### Task 3: `performance.py` passa a ler a nota relativa congelada

**Files:**
- Modify: `docudata-backend/services/performance.py:118-129`
- Test: `docudata-backend/tests/test_performance_ranking.py`

**Interfaces:**
- Consumes: `linha["entrega_modo"]`, `linha["entrega_nota_relativa"]` (gravadas pela Task 2).
- Produces: `_entrega_por_projeto(linhas) -> float | None` — assinatura e nome **inalterados** (3 testes existentes chamam essa função direto, golden regression depende disso). Internamente delega a `_entrega_atribuicao` e `_entrega_relativa`, novas, privadas.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_performance_ranking.py — adicionar ao final do arquivo
def test_entrega_por_projeto_usa_nota_relativa_quando_modo_e_relativo():
    from services.performance import _entrega_por_projeto
    linhas = [{"entrega_modo": "PONTOS_RELATIVO", "entrega_nota_relativa": 80.0}]
    assert _entrega_por_projeto(linhas) == 80.0


def test_entrega_por_projeto_media_relativa_entre_sprints_da_janela():
    from services.performance import _entrega_por_projeto
    linhas = [
        {"entrega_modo": "PONTOS_RELATIVO", "entrega_nota_relativa": 80.0},
        {"entrega_modo": "PONTOS_RELATIVO", "entrega_nota_relativa": 40.0},
    ]
    assert _entrega_por_projeto(linhas) == 60.0


def test_entrega_por_projeto_janela_mista_pondera_por_quantidade_de_sprints():
    from services.performance import _entrega_por_projeto
    # 2 sprints ATRIBUICAO (rate agregado 50%) + 1 sprint PULL (nota 80) —
    # média ponderada por contagem: (50*2 + 80*1) / 3 = 60.0
    linhas = [
        {"entrega_modo": "PONTOS_ATRIBUIDOS", "entrega_pontos_concluidos": 5, "entrega_pontos_alocados": 10, "entrega_pontos_penalizados": 0},
        {"entrega_modo": "PONTOS_ATRIBUIDOS", "entrega_pontos_concluidos": 5, "entrega_pontos_alocados": 10, "entrega_pontos_penalizados": 0},
        {"entrega_modo": "PONTOS_RELATIVO", "entrega_nota_relativa": 80.0},
    ]
    assert _entrega_por_projeto(linhas) == 60.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_performance_ranking.py -k "entrega_por_projeto and (relativ or mista)" -v`
Expected: FAIL — a primeira dá `KeyError: 'entrega_pontos_concluidos'` (função atual ignora `entrega_modo` e tenta ler os campos de ATRIBUIÇÃO sempre)

- [ ] **Step 3: Write the implementation**

Substitua a função `_entrega_por_projeto` em `services/performance.py:118-129` por:

```python
def _entrega_por_projeto(linhas: list[dict]) -> float | None:
    """Combina os dois modos de avaliação de Entrega dentro de uma janela.
    Na prática o caso comum é homogêneo (projeto nunca trocou de modo); o
    caso misto só acontece se o projeto migrou de ATRIBUICAO<->PULL no meio
    do período coberto pela janela (Onda B desta entrega)."""
    atribuidas = [l for l in linhas if l.get("entrega_modo") != "PONTOS_RELATIVO"]
    relativas = [l for l in linhas if l.get("entrega_modo") == "PONTOS_RELATIVO"]

    score_atribuicao = _entrega_atribuicao(atribuidas)
    score_relativo = _entrega_relativa(relativas)

    if score_atribuicao is None:
        return score_relativo
    if score_relativo is None:
        return score_atribuicao
    # Janela mista: as duas fórmulas não são comensuráveis em pontos brutos
    # (uma soma pontos, a outra já é nota 0-100 por sprint), então pondera
    # pela quantidade de sprints de cada regime em vez de tentar somar pontos
    # de bases diferentes. Decisão de plano (Entrega 3, Task 3) — não coberta
    # explicitamente pelo spec original, que não previa migração mid-window.
    peso_atrib = len(atribuidas)
    peso_rel = len(relativas)
    return round((score_atribuicao * peso_atrib + score_relativo * peso_rel) / (peso_atrib + peso_rel), 2)


def _entrega_atribuicao(linhas: list[dict]) -> float | None:
    """Entrega desconta os pontos penalizados por travamento automático: uma task
    que ficou parada muito além do tempo esperado não conta como entrega cheia
    (decisão do Líder, 2026-09-07). O gerente pode dispensar o travamento no
    alerta da task, e aí ele não penaliza."""
    if not linhas:
        return None
    concluidos = sum(l["entrega_pontos_concluidos"] for l in linhas)
    penalizados = sum(l.get("entrega_pontos_penalizados") or 0 for l in linhas)
    alocados = sum(l["entrega_pontos_alocados"] for l in linhas)
    if alocados <= 0:
        return None
    efetivos = max(concluidos - penalizados, 0)
    return round(min(efetivos / alocados * 100, 100), 2)


def _entrega_relativa(linhas: list[dict]) -> float | None:
    """PONTOS_RELATIVO: a nota já vem normalizada (0-100) por sprint,
    congelada no fechamento (services/pontuacao.py::calcular_e_travar_pontuacao)
    — aqui só faz a média simples entre as sprints da janela, sem reprocessar
    piso/teto (esses já foram aplicados na hora do congelamento)."""
    if not linhas:
        return None
    valores = [l["entrega_nota_relativa"] for l in linhas if l.get("entrega_nota_relativa") is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_performance_ranking.py -v`
Expected: PASS (arquivo inteiro — os 3 testes pré-existentes de `_entrega_por_projeto` continuam passando porque suas linhas de fixture não têm `entrega_modo == 'PONTOS_RELATIVO'`, então caem 100% no branch `atribuidas`, idêntico a antes)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/performance.py docudata-backend/tests/test_performance_ranking.py
git commit -m "feat(performance): Entrega lê nota PONTOS_RELATIVO congelada quando aplicável (Entrega 3)"
```

---

### Task 4: Golden regression explícita — fechamento completo em ATRIBUIÇÃO

**Files:**
- Test: `docudata-backend/tests/test_pontuacao_fechamento.py`

**Interfaces:**
- Consumes: `calcular_e_travar_pontuacao` (Task 2).

- [ ] **Step 1: Write the failing test**

(Este teste só falha se uma regressão for introduzida depois — nesta task ele já nasce passando porque a Task 2 já implementa o comportamento certo. Ainda assim, siga TDD: escreva e rode antes de seguir, não pule a checagem.)

```python
# tests/test_pontuacao_fechamento.py — adicionar ao final do arquivo
def test_golden_regression_atribuicao_nao_muda_apos_entrega_3():
    """Mesmo cenário de teste pré-existente do motor de score, sem nenhum
    campo de PONTOS_RELATIVO no projeto — reafirma que a Entrega 3 é
    estritamente aditiva para projetos em ATRIBUICAO."""
    tasks = [
        {"id": "t1", "operacional_id": "op-a", "pontos": 5, "coluna_kanban": "concluida", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
        {"id": "t2", "operacional_id": "op-a", "pontos": 3, "coluna_kanban": "planejado", "extra": False, "bloqueado_resolvido_por": None, "bloqueado_resolvido_em": None},
    ]
    client = _mock_client(
        sprint={"id": "sprint-1", "project_id": "proj-1"},
        tasks=tasks,
        operacionais=[{"id": "op-a", "nome": "A", "email": "a@x.com", "data_entrada": "2026-01-01T00:00:00+00:00", "data_saida": None}],
        projeto={"modo_trabalho": "ATRIBUICAO", "modo_avaliacao": "PONTOS_ATRIBUIDOS", "pull_piso_pontos": 1, "pull_teto": 1.5},
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = resultado[0]
    assert linha["entrega_pontos_concluidos"] == 5
    assert linha["entrega_pontos_alocados"] == 8
    assert linha["entrega_modo"] == "PONTOS_ATRIBUIDOS"
    assert linha["entrega_pontos_pessoa"] is None
    assert linha["entrega_denominador"] is None
    assert linha["entrega_nota_relativa"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pontuacao_fechamento.py::test_golden_regression_atribuicao_nao_muda_apos_entrega_3 -v`
Expected: Se a Task 2 foi implementada corretamente, este teste já **passa** na primeira execução — rode mesmo assim pra confirmar (não é um passo vazio: se falhar aqui, a Task 2 tem um bug e precisa ser corrigida antes de continuar).

- [ ] **Step 3: (sem implementação — este teste é só de confirmação)**

- [ ] **Step 4: Run full suite to confirm no regression**

Run: `pytest -q`
Expected: mesmo `475 passed, 1 failed` de antes da Entrega 3 (a falha é `test_security.py::test_dependencias_separam_browser_automacoes_e_webhooks_publicos`, pré-existente e não relacionada — confirmado por auditoria anterior) mais os testes novos desta entrega passando.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "test(pontuacao): golden regression explícita pós-Entrega 3 pra ATRIBUICAO"
```

---

### Task 5: Fechamento com zero tasks — score só com avaliação do gerente

**Files:**
- Test: `docudata-backend/tests/test_performance_ranking.py`

**Interfaces:**
- Consumes: `calcular_ranking_pessoa(client, pessoa, pesos_por_arquetipo) -> dict` (já existe).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_performance_ranking.py — adicionar ao final do arquivo
def test_score_final_so_com_avaliacao_do_gerente_quando_zero_tasks():
    """Operacional vinculado ao projeto, zero tasks na sprint, avaliação do
    gerente completa. Entrega fica indisponível (alocados=0), Qualidade fica
    indisponível (sem task concluída nem commit), Autonomia só tem a
    pergunta 3 (sem bloqueio nenhum) — mas Gerente e Evolução estão
    disponíveis, então score_final não pode ser None."""
    linha = {
        "projeto_id": "proj-1", "sprint_fim": "2026-09-01T00:00:00Z",
        "entrega_modo": "PONTOS_ATRIBUIDOS",
        "entrega_pontos_concluidos": 0, "entrega_pontos_alocados": 0, "entrega_pontos_penalizados": 0,
        "entrega_pontos_pessoa": None, "entrega_denominador": None, "entrega_nota_relativa": None,
        "bonus_pontos_extra": 0,
        "gerente_media": 4.0, "gerente_pergunta6": 5, "gerente_pergunta3": 4,
        "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 0, "qualidade_commit_media": None,
        "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
    }
    operacionais = [{"id": "op-a", "nome": "A", "email": "a@x.com", "ativo": True}]
    client = _mock_client(operacionais=operacionais, pontuacao=[dict(linha, operacional_id="op-a")], projetos=[{"id": "proj-1", "arquetipo": "padrao"}])

    pessoa = listar_pessoas_ativas(client)[0]
    resultado = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert resultado["sprint"] is not None
    assert resultado["sprint"]["score_final"] is not None
    assert resultado["sprint"]["entrega"] is None
    assert resultado["sprint"]["qualidade"] is None
    assert resultado["sprint"]["gerente"] == 80.0  # 4.0 * 20
    assert resultado["sprint"]["evolucao"] == 100.0  # 5 * 20
    # score_final = (peso_gerente*80 + peso_evolucao*100 + peso_autonomia*autonomia) / (peso_gerente+peso_evolucao+peso_autonomia)
    # autonomia (só pergunta3, sem bloqueio) = min(4*20,100) = 80
    peso_disponivel = 0.35 + 0.10 + 0.15
    esperado = round((0.35 * 80.0 + 0.10 * 100.0 + 0.15 * 80.0) / peso_disponivel, 2)
    assert resultado["sprint"]["score_final"] == esperado
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_performance_ranking.py::test_score_final_so_com_avaliacao_do_gerente_quando_zero_tasks -v`
Expected: se o comportamento já existir (confirmado por leitura de código antes desta plan), o teste **passa** de primeira — rode assim mesmo pra ter cobertura formal do caminho. Se falhar, há uma regressão real em `_score_final`/`_entrega_por_projeto` a corrigir antes de prosseguir.

- [ ] **Step 3: (sem implementação nova — comportamento já existe em `_score_final`, `services/performance.py:209-224`)**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_performance_ranking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/tests/test_performance_ranking.py
git commit -m "test(performance): cobre score final calculado só com avaliação do gerente (Entrega 3)"
```

---

### Task 6: UI — sinalizar "sem task formal" no dado de Entrega/SPI

**Files:**
- Modify: `docudata-frontend/app/components/MetricasTab.tsx:343-352`
- Test: `docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs` (novo)

**Interfaces:**
- Consumes: `SpiEvolucaoOperacional` (já existe em `app/lib/api.ts:1964-1971`, campos `spi: number | null`, `sprints_avaliadas: number`).

- [ ] **Step 1: Write the failing test**

```javascript
// docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs (novo arquivo)
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("MetricasTab explica SPI nulo com sprints avaliadas em vez de deixar travessão sem contexto", () => {
  const src = readFileSync(
    new URL("../app/components/MetricasTab.tsx", import.meta.url),
    "utf-8"
  );
  assert.match(src, /sprints_avaliadas > 0/);
  assert.match(src, /Sem task alocada nesta sprint/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd docudata-frontend && node --test tests/modos-trabalho-avaliacao-entrega3.test.mjs`
Expected: FAIL (padrões ainda não existem no arquivo)

- [ ] **Step 3: Write the implementation**

Em `app/components/MetricasTab.tsx`, substitua a célula de SPI (linhas 346-348):

```tsx
                    <td
                      style={{ ...tdSt, fontWeight: 700, color: op.spi === null ? "#94a3b8" : spiColor(op.spi / 100) }}
                      title={op.spi === null && op.sprints_avaliadas > 0 ? "Sem task alocada nesta sprint — score calculado com o restante das dimensões (avaliação do gerente, evolução, autonomia)" : undefined}
                    >
                      {op.spi === null ? "—" : op.spi}
                    </td>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/modos-trabalho-avaliacao-entrega3.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/components/MetricasTab.tsx docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs
git commit -m "fix(metricas): tooltip explica SPI nulo por ausência de task, não deixa travessão mudo (Entrega 3)"
```

---

## Onda B — Migração estruturada de modo

> Esta onda começa com o schema e a função de hidratação (conceitualmente parte da Onda C, ver spec §1.1) porque `POST /projects/{id}/migrar-modo` já precisa gravar `rascunho`/`entrou_na_fila_em`/`pull_em` ao mover tasks.

### Task 7: Schema — colunas de fila em `tasks` + tabela `migracoes_modo`

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (anexar após o bloco da Task 1, antes de `Migration v5`)
- Test: `docudata-backend/tests/test_modos_schema.py`

**Interfaces:**
- Produces: `tasks.entrou_na_fila_em`, `tasks.pull_em`, `tasks.atribuida_manualmente`, `tasks.motivo_atribuicao_manual`, `tasks.rascunho`, `tasks.motivo_rascunho`, `tasks.ordem_fila`; tabela `migracoes_modo(id, project_id, de_modo, para_modo, contagem, aplicado_por, created_at)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_modos_schema.py — adicionar ao final
def test_schema_tem_colunas_de_fila_em_tasks():
    schema = open("supabase_schema.sql").read()
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS entrou_na_fila_em timestamptz;" in schema
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS pull_em timestamptz;" in schema
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS atribuida_manualmente boolean NOT NULL DEFAULT false;" in schema
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS rascunho boolean NOT NULL DEFAULT false;" in schema
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ordem_fila int;" in schema


def test_schema_tem_tabela_migracoes_modo():
    schema = open("supabase_schema.sql").read()
    assert "CREATE TABLE IF NOT EXISTS migracoes_modo (" in schema
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_modos_schema.py -k "fila_em_tasks or migracoes_modo" -v`
Expected: FAIL

- [ ] **Step 3: Append the migration block**

Insira após o bloco da Task 1 (ainda antes de `-- Migration v5`):

```sql
-- ═══════════════════════════════════════════════════════════════
-- Modos de Trabalho e de Avaliação — Entrega 3, Ondas B/C: fila
-- real (hidratação, pull, devolução) e migração estruturada de modo
-- (spec docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega3-design.md §3/§4)
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS entrou_na_fila_em timestamptz;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS pull_em timestamptz;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS atribuida_manualmente boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS motivo_atribuicao_manual text;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS rascunho boolean NOT NULL DEFAULT false;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS motivo_rascunho text;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ordem_fila int;

CREATE TABLE IF NOT EXISTS migracoes_modo (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    de_modo         text NOT NULL,
    para_modo       text NOT NULL,
    contagem        jsonb NOT NULL,
    aplicado_por    uuid REFERENCES pessoa(id),
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_migracoes_modo_project ON migracoes_modo(project_id, created_at DESC);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_modos_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/supabase_schema.sql docudata-backend/tests/test_modos_schema.py
git commit -m "feat(schema): colunas de fila em tasks e tabela migracoes_modo (Entrega 3)"
```

---

### Task 8: Pydantic — `TaskResponse`/`TaskCreate`/`TaskUpdate` ganham os campos de fila

**Files:**
- Modify: `docudata-backend/models/schemas.py:455-540`
- Test: `docudata-backend/tests/test_task_schemas.py` (novo, ou adicionar a um arquivo de schema existente se houver)

**Interfaces:**
- Produces: `TaskResponse` com `entrou_na_fila_em: Optional[datetime]`, `pull_em: Optional[datetime]`, `atribuida_manualmente: bool`, `motivo_atribuicao_manual: Optional[str]`, `rascunho: bool`, `motivo_rascunho: Optional[str]`, `ordem_fila: Optional[int]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_task_schemas.py (novo)
from models.schemas import TaskResponse


def test_task_response_aceita_campos_de_fila():
    resp = TaskResponse(
        id="t1", project_id="p1", titulo="X", pontos=3, coluna_kanban="planejado",
        bloqueado=False, checklist=[], ordem=0,
        created_at="2026-09-01T00:00:00Z", updated_at="2026-09-01T00:00:00Z",
        entrou_na_fila_em="2026-09-01T00:00:00Z", pull_em=None,
        atribuida_manualmente=False, motivo_atribuicao_manual=None,
        rascunho=True, motivo_rascunho="Faltam: descrição, checklist", ordem_fila=2,
    )
    assert resp.rascunho is True
    assert resp.motivo_rascunho == "Faltam: descrição, checklist"


def test_task_response_campos_de_fila_tem_default_seguro():
    resp = TaskResponse(
        id="t1", project_id="p1", titulo="X", pontos=3, coluna_kanban="planejado",
        bloqueado=False, checklist=[], ordem=0,
        created_at="2026-09-01T00:00:00Z", updated_at="2026-09-01T00:00:00Z",
    )
    assert resp.rascunho is False
    assert resp.atribuida_manualmente is False
    assert resp.ordem_fila is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_schemas.py -v`
Expected: FAIL (`TypeError: unexpected keyword argument 'entrou_na_fila_em'` ou validação rejeitando campo desconhecido)

- [ ] **Step 3: Write the implementation**

Em `models/schemas.py`, adicione ao final de `TaskResponse` (depois de `updated_at: datetime`, linha 540):

```python
    entrou_na_fila_em: Optional[datetime] = None
    pull_em: Optional[datetime] = None
    atribuida_manualmente: bool = False
    motivo_atribuicao_manual: Optional[str] = None
    rascunho: bool = False
    motivo_rascunho: Optional[str] = None
    ordem_fila: Optional[int] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_task_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/tests/test_task_schemas.py
git commit -m "feat(schemas): TaskResponse ganha os campos de fila (Entrega 3)"
```

---

### Task 9: Função de hidratação

**Files:**
- Create: `docudata-backend/services/hidratacao.py`
- Test: `docudata-backend/tests/test_hidratacao.py`

**Interfaces:**
- Produces: `calcular_hidratacao(task: dict) -> tuple[bool, str | None]` — `(rascunho, motivo_rascunho)`. `task` precisa das chaves `titulo`, `pontos`, `descricao`, `checklist`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hidratacao.py (novo)
from services.hidratacao import calcular_hidratacao


def test_task_completa_nao_e_rascunho():
    task = {"titulo": "Fazer X", "pontos": 3, "descricao": "detalhe", "checklist": [{"texto": "a", "done": False}]}
    rascunho, motivo = calcular_hidratacao(task)
    assert rascunho is False
    assert motivo is None


def test_task_sem_descricao_nem_checklist_e_rascunho_com_motivo():
    task = {"titulo": "Fazer X", "pontos": 3, "descricao": None, "checklist": []}
    rascunho, motivo = calcular_hidratacao(task)
    assert rascunho is True
    assert motivo == "Faltam: descrição, checklist"


def test_task_sem_pontos_e_rascunho():
    task = {"titulo": "Fazer X", "pontos": 0, "descricao": "detalhe", "checklist": [{"texto": "a", "done": False}]}
    rascunho, motivo = calcular_hidratacao(task)
    assert rascunho is True
    assert motivo == "Faltam: pontos"


def test_task_sem_titulo_e_rascunho():
    task = {"titulo": "", "pontos": 3, "descricao": "detalhe", "checklist": [{"texto": "a", "done": False}]}
    rascunho, motivo = calcular_hidratacao(task)
    assert rascunho is True
    assert motivo == "Faltam: título"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hidratacao.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'services.hidratacao'`)

- [ ] **Step 3: Write the implementation**

```python
# services/hidratacao.py
"""Hidratação de task (Entrega 3, Onda B/C) — spec
docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega3-design.md §4.1.

Só é consultada quando o projeto está em modo PULL com
pull_exigir_hidratacao=true (o chamador decide isso, não esta função — aqui
é só a regra pura de "o que falta")."""


def calcular_hidratacao(task: dict) -> tuple[bool, str | None]:
    """Retorna (rascunho, motivo_rascunho). Task hidratada tem título, pontos
    > 0, descrição não vazia e pelo menos 1 item de checklist."""
    faltando = []
    if not (task.get("titulo") or "").strip():
        faltando.append("título")
    if not (task.get("pontos") or 0) > 0:
        faltando.append("pontos")
    if not (task.get("descricao") or "").strip():
        faltando.append("descrição")
    if not (task.get("checklist") or []):
        faltando.append("checklist")

    if not faltando:
        return False, None
    return True, f"Faltam: {', '.join(faltando)}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_hidratacao.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/hidratacao.py docudata-backend/tests/test_hidratacao.py
git commit -m "feat(hidratacao): função pura de cálculo de rascunho (Entrega 3)"
```

---

### Task 10: Hook de hidratação em `create_task`/`patch_task`

**Files:**
- Modify: `docudata-backend/routers/tasks.py:298-329` (`create_task`), `:606-618` (`patch_task`)
- Test: `docudata-backend/tests/test_tasks_hidratacao.py` (novo)

**Interfaces:**
- Consumes: `calcular_hidratacao(task: dict) -> tuple[bool, str | None]` (Task 9).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tasks_hidratacao.py (novo)
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(projeto, tasks_insert_capture=None, tasks_update_capture=None):
    tasks_insert_capture = tasks_insert_capture if tasks_insert_capture is not None else []
    tasks_update_capture = tasks_update_capture if tasks_update_capture is not None else []
    existente = {"id": "t1", "project_id": "proj-1", "titulo": "X", "pontos": 1, "coluna_kanban": "planejado", "operacional_id": None, "created_at": "2026-09-01T00:00:00+00:00"}
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
                resp.data = [existente]
                q.execute = MagicMock(return_value=resp)
                return q

            def insert_side_effect(payload):
                tasks_insert_capture.append(payload)
                q = MagicMock()
                resp = MagicMock()
                resp.data = [dict(existente, **payload, id="t-novo")]
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                tasks_update_capture.append(payload)
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [dict(existente, **payload)]
                q.execute = MagicMock(return_value=resp)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.insert = MagicMock(side_effect=insert_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
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
    return client, tasks_insert_capture, tasks_update_capture


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto):
        import routers.tasks as tasks_router
        from main import app
        client, ins, upd = _mock_client(projeto)
        monkeypatch.setattr(tasks_router, "get_client", lambda: client)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc, ins, upd
    return _make


def test_create_task_marca_rascunho_em_projeto_pull_com_hidratacao_exigida(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": True})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Sem descrição", "pontos": 2})

    assert resp.status_code == 201
    assert ins[0]["rascunho"] is True
    assert ins[0]["motivo_rascunho"] == "Faltam: descrição, checklist"


def test_create_task_nao_marca_rascunho_em_projeto_atribuicao(make_client):
    tc, ins, _ = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True})

    resp = tc.post("/tasks", json={"project_id": "proj-1", "titulo": "Sem descrição", "pontos": 2})

    assert resp.status_code == 201
    assert "rascunho" not in ins[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tasks_hidratacao.py -v`
Expected: FAIL (payload de insert não tem `rascunho`)

- [ ] **Step 3: Write the implementation**

Em `routers/tasks.py`, adicione o import no topo:

```python
from services.hidratacao import calcular_hidratacao
```

Em `create_task`, estenda o select que já existe na checagem de projeto (linha ~250-252) — de `select("id")` para `select("id, modo_trabalho, pull_exigir_hidratacao")` — reaproveitando a mesma query em vez de uma segunda chamada. Guarde o resultado (`projeto_row = check.data[0]`) e, antes do `resp = client.table("tasks").insert(payload).execute()` (linha ~322), adicione:

```python
    if projeto_row.get("modo_trabalho") == "PULL" and projeto_row.get("pull_exigir_hidratacao"):
        rascunho, motivo = calcular_hidratacao(payload)
        payload["rascunho"] = rascunho
        payload["motivo_rascunho"] = motivo
```

Em `patch_task`, logo antes de `result = client.table("tasks").update(updates).eq("id", task_id).execute()` (linha ~634), adicione:

```python
    proj_modo = client.table("projects").select("modo_trabalho, pull_exigir_hidratacao").eq("id", project_id).execute()
    projeto_row = proj_modo.data[0] if proj_modo.data else {}
    if projeto_row.get("modo_trabalho") == "PULL" and projeto_row.get("pull_exigir_hidratacao"):
        task_apos_update = {**task, **updates}
        rascunho, motivo = calcular_hidratacao(task_apos_update)
        updates["rascunho"] = rascunho
        updates["motivo_rascunho"] = motivo
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tasks_hidratacao.py -v && pytest tests/test_tasks*.py -v`
Expected: PASS em todos (o segundo comando confirma que não quebrou nenhum teste existente de `routers/tasks.py`)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_tasks_hidratacao.py
git commit -m "feat(tasks): recalcula hidratação em toda escrita quando projeto é PULL (Entrega 3)"
```

---

### Task 11: `GET /projects/{id}/migrar-modo/preview`

**Files:**
- Modify: `docudata-backend/routers/projects.py` (adicionar rota)
- Test: `docudata-backend/tests/test_migracao_modo.py` (novo)

**Interfaces:**
- Produces: `GET /projects/{id}/migrar-modo/preview?para=PULL` → `{"entrando_na_fila": int, "mantem_responsavel": int, "vira_rascunho": int, "sem_alteracao": int}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migracao_modo.py (novo)
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(projeto, tasks):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [projeto] if projeto else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "tasks":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = tasks
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(projeto, tasks):
        import routers.projects as projects_router
        from main import app
        mock_sb = _mock_client(projeto, tasks)
        monkeypatch.setattr(projects_router, "get_client", lambda: mock_sb)
        tc = autenticar(TestClient(app), cargo="gerente")
        return tc
    return _make


def test_preview_migracao_conta_tasks_por_categoria(make_client):
    tasks = [
        {"id": "t1", "coluna_kanban": "planejado", "operacional_id": "op-a", "titulo": "X", "pontos": 3, "descricao": "d", "checklist": [{"texto": "a", "done": False}], "bloqueado": False},
        {"id": "t2", "coluna_kanban": "planejado", "operacional_id": None, "titulo": "Y", "pontos": 2, "descricao": None, "checklist": [], "bloqueado": False},
        {"id": "t3", "coluna_kanban": "em_andamento", "operacional_id": "op-b", "titulo": "Z", "pontos": 5, "descricao": "d", "checklist": [], "bloqueado": False},
        {"id": "t4", "coluna_kanban": "concluida", "operacional_id": "op-a", "titulo": "W", "pontos": 4, "descricao": "d", "checklist": [], "bloqueado": False},
        {"id": "t5", "coluna_kanban": "planejado", "operacional_id": "op-c", "titulo": "V", "pontos": 1, "descricao": "d", "checklist": [], "bloqueado": True},
    ]
    tc = make_client(projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True}, tasks=tasks)

    resp = tc.get("/projects/proj-1/migrar-modo/preview?para=PULL")

    assert resp.status_code == 200
    body = resp.json()
    assert body["entrando_na_fila"] == 1  # t1: planejado com responsável, hidratada
    assert body["vira_rascunho"] == 1  # t2: planejado sem descrição/checklist
    assert body["mantem_responsavel"] == 2  # t3: em_andamento; t5: bloqueada (mantém responsável mesmo planejada)
    assert body["sem_alteracao"] == 1  # t4: concluida
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_migracao_modo.py::test_preview_migracao_conta_tasks_por_categoria -v`
Expected: FAIL (404 — rota não existe)

- [ ] **Step 3: Write the implementation**

Em `routers/projects.py`, adicione o import `from services.hidratacao import calcular_hidratacao` e, ao final do arquivo, a rota:

```python
@router.get("/{project_id}/migrar-modo/preview")
async def preview_migrar_modo(
    project_id: str,
    para: str = Query(...),
    _pessoa: dict = Depends(require_not_operacional),
):
    """RF-M1/M2 (Entrega 3): dry-run — conta quantas tasks cairiam em cada
    categoria se a migração fosse aplicada agora, sem gravar nada."""
    if para not in ("ATRIBUICAO", "PULL"):
        raise HTTPException(status_code=422, detail="para deve ser ATRIBUICAO ou PULL")
    client = get_client()
    check = client.table("projects").select("id").eq("id", project_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = client.table("tasks").select("id, coluna_kanban, operacional_id, titulo, pontos, descricao, checklist, bloqueado").eq("project_id", project_id).execute().data or []

    contagem = {"entrando_na_fila": 0, "vira_rascunho": 0, "mantem_responsavel": 0, "sem_alteracao": 0}
    for task in tasks:
        coluna = task.get("coluna_kanban")
        # "Bloqueada" no spec original é um estado lógico (RF-M2), mas neste
        # schema bloqueio é o booleano tasks.bloqueado, ortogonal à coluna —
        # checa primeiro, antes de dispachar por coluna, e nunca reclassifica
        # (mantém responsável e estado de bloqueio, igual o spec pede).
        if task.get("bloqueado"):
            contagem["mantem_responsavel"] += 1
        elif coluna == "concluida":
            contagem["sem_alteracao"] += 1
        elif coluna == "planejado":
            if para == "PULL":
                rascunho, _ = calcular_hidratacao(task)
                if rascunho:
                    contagem["vira_rascunho"] += 1
                else:
                    contagem["entrando_na_fila"] += 1
            else:
                contagem["sem_alteracao"] += 1
        elif coluna == "em_andamento":
            contagem["mantem_responsavel"] += 1
        else:
            contagem["sem_alteracao"] += 1

    return contagem
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_migracao_modo.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/projects.py docudata-backend/tests/test_migracao_modo.py
git commit -m "feat(projects): GET /migrar-modo/preview — dry-run de migração de modo (Entrega 3)"
```

---

### Task 12: `POST /projects/{id}/migrar-modo`

**Files:**
- Modify: `docudata-backend/routers/projects.py`
- Test: `docudata-backend/tests/test_migracao_modo.py`

**Interfaces:**
- Produces: `POST /projects/{id}/migrar-modo` body `{"para": "PULL"}` → aplica a tabela de comportamento do spec §3.2, grava `migracoes_modo`, marca `sprints.hibrida=true` na sprint ativa.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migracao_modo.py — estender _mock_client pra cobrir update de tasks/sprints/insert de migracoes_modo, e adicionar:

def test_aplicar_migracao_para_pull_reclassifica_tasks_e_grava_auditoria(make_client_completo, monkeypatch):
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: "sprint-1")
    tc, tasks_update, migracoes_insert, sprints_update = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "ATRIBUICAO", "pull_exigir_hidratacao": True},
        tasks=[
            {"id": "t1", "coluna_kanban": "planejado", "operacional_id": "op-a", "titulo": "X", "pontos": 3, "descricao": "d", "checklist": [{"texto": "a", "done": False}], "bloqueado": False},
            {"id": "t4", "coluna_kanban": "concluida", "operacional_id": "op-a", "titulo": "W", "pontos": 4, "descricao": "d", "checklist": [], "bloqueado": False},
            {"id": "t5", "coluna_kanban": "planejado", "operacional_id": "op-c", "titulo": "V", "pontos": 1, "descricao": "d", "checklist": [], "bloqueado": True},
        ],
    )

    resp = tc.post("/projects/proj-1/migrar-modo", json={"para": "PULL"})

    assert resp.status_code == 200
    # Só t1 (planejado, não bloqueada) sofre update — t4 (concluída) e t5
    # (bloqueada) nunca disparam client.table("tasks").update(...), então a
    # lista capturada tem exatamente 1 entrada.
    assert len(tasks_update) == 1
    assert tasks_update[0]["operacional_id"] is None
    assert "entrou_na_fila_em" in tasks_update[0]
    assert migracoes_insert[0]["de_modo"] == "ATRIBUICAO"
    assert migracoes_insert[0]["para_modo"] == "PULL"
    assert migracoes_insert[0]["contagem"]["mantem_responsavel"] == 1  # t5, bloqueada
    assert migracoes_insert[0]["contagem"]["sem_alteracao"] == 1  # t4, concluída
    assert sprints_update[0]["hibrida"] is True
```

(A fixture `make_client_completo` estende o `_mock_client` desta task com handlers de `update` para `tasks`/`sprints` e `insert` para `migracoes_modo`, seguindo o mesmo padrão de captura por lista já usado nas Tasks 2 e 11 — escreva-a no mesmo arquivo antes do teste.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_migracao_modo.py::test_aplicar_migracao_para_pull_reclassifica_tasks_e_grava_auditoria -v`
Expected: FAIL (404 — rota não existe)

- [ ] **Step 3: Write the implementation**

```python
class MigrarModoRequest(BaseModel):
    para: Literal["ATRIBUICAO", "PULL"]
```

(adicionar em `models/schemas.py`, importar em `routers/projects.py`)

```python
@router.post("/{project_id}/migrar-modo")
async def aplicar_migrar_modo(
    project_id: str,
    data: MigrarModoRequest,
    pessoa: dict = Depends(require_not_operacional),
):
    """RF-M1..M8 (Entrega 3): aplica a migração de modo. Nunca escreve em
    task_transicoes/task_reaberturas (RF-M3) — reclassificação estrutural,
    não movimento de Kanban."""
    client = get_client()
    proj = client.table("projects").select("id, modo_trabalho").eq("id", project_id).execute()
    if not proj.data:
        raise HTTPException(status_code=404, detail="Project not found")
    de_modo = proj.data[0].get("modo_trabalho") or "ATRIBUICAO"

    tasks = client.table("tasks").select("id, coluna_kanban, operacional_id, titulo, pontos, descricao, checklist, bloqueado").eq("project_id", project_id).execute().data or []

    contagem = {"entrando_na_fila": 0, "vira_rascunho": 0, "mantem_responsavel": 0, "sem_alteracao": 0}
    for task in tasks:
        coluna = task.get("coluna_kanban")
        if task.get("bloqueado"):
            # Mantém responsável e estado de bloqueio — nunca reclassifica.
            contagem["mantem_responsavel"] += 1
        elif coluna == "planejado" and data.para == "PULL":
            rascunho, motivo = calcular_hidratacao(task)
            updates = {
                "operacional_id": None,
                "rascunho": rascunho,
                "motivo_rascunho": motivo,
                "entrou_na_fila_em": datetime.now(timezone.utc).isoformat(),
            }
            client.table("tasks").update(updates).eq("id", task["id"]).execute()
            contagem["vira_rascunho" if rascunho else "entrando_na_fila"] += 1
        elif coluna == "planejado" and data.para == "ATRIBUICAO":
            client.table("tasks").update({"rascunho": False, "motivo_rascunho": None, "entrou_na_fila_em": None}).eq("id", task["id"]).execute()
            contagem["sem_alteracao"] += 1
        elif coluna == "em_andamento":
            if data.para == "PULL":
                client.table("tasks").update({"pull_em": datetime.now(timezone.utc).isoformat()}).eq("id", task["id"]).execute()
            contagem["mantem_responsavel"] += 1
        else:
            contagem["sem_alteracao"] += 1

    client.table("migracoes_modo").insert({
        "project_id": project_id,
        "de_modo": de_modo,
        "para_modo": data.para,
        "contagem": contagem,
        "aplicado_por": pessoa["id"],
    }).execute()

    sprint_ativa_id = get_current_sprint_id(client, project_id)
    if sprint_ativa_id:
        client.table("sprints").update({"hibrida": True}).eq("id", sprint_ativa_id).execute()

    return {"de_modo": de_modo, "para_modo": data.para, "contagem": contagem}
```

Adicione os imports que faltarem no topo de `routers/projects.py`: `from datetime import datetime, timezone`, `from services.hidratacao import calcular_hidratacao`, `from services.sprints import get_current_sprint_id` (helper já existente e testado — resolve "sprint ativa" pela mesma lógica que `services/pontuacao.py::rotear_evento_pos_fechamento` já usa, em vez de reinventar a query), `Literal` de `typing` (já importado), `MigrarModoRequest` de `models.schemas`.

No teste (`test_aplicar_migracao_para_pull_reclassifica_tasks_e_grava_auditoria`), a fixture `make_client_completo` deve dar `monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: "sprint-1")` em vez de simular as tabelas `sprints`/`ingestions` que `get_current_sprint_id` consultaria por trás — mais simples e não re-testa uma função que já tem sua própria suíte (`services/sprints.py`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_migracao_modo.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/projects.py docudata-backend/models/schemas.py docudata-backend/tests/test_migracao_modo.py
git commit -m "feat(projects): POST /migrar-modo aplica migração estruturada com auditoria (Entrega 3)"
```

---

### Task 13: `POST /projects/{id}/desvincular-planejado`

**Files:**
- Modify: `docudata-backend/routers/projects.py`
- Test: `docudata-backend/tests/test_migracao_modo.py`

**Interfaces:**
- Produces: `POST /projects/{id}/desvincular-planejado` → limpa `operacional_id` de toda task `coluna_kanban='planejado'` da sprint ativa; retorna `{"desvinculadas": int}`.

- [ ] **Step 1: Write the failing test**

```python
def test_desvincular_planejado_limpa_responsavel_so_de_tasks_planejadas(make_client_completo, monkeypatch):
    tc, tasks_update, _, _ = make_client_completo(
        projeto={"id": "proj-1", "modo_trabalho": "PULL", "pull_exigir_hidratacao": False},
        tasks=[
            {"id": "t1", "coluna_kanban": "planejado", "operacional_id": "op-a", "sprint_id": "sprint-1", "titulo": "X", "pontos": 3, "descricao": "d", "checklist": [], "bloqueado": False},
            {"id": "t2", "coluna_kanban": "em_andamento", "operacional_id": "op-b", "sprint_id": "sprint-1", "titulo": "Y", "pontos": 2, "descricao": "d", "checklist": [], "bloqueado": False},
        ],
    )
    import routers.projects as projects_router
    monkeypatch.setattr(projects_router, "get_current_sprint_id", lambda client, project_id: "sprint-1")

    resp = tc.post("/projects/proj-1/desvincular-planejado")

    assert resp.status_code == 200
    assert resp.json() == {"desvinculadas": 1}
    assert tasks_update[0]["operacional_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_migracao_modo.py::test_desvincular_planejado_limpa_responsavel_so_de_tasks_planejadas -v`
Expected: FAIL (404 — rota não existe)

- [ ] **Step 3: Write the implementation**

```python
@router.post("/{project_id}/desvincular-planejado")
async def desvincular_planejado(project_id: str, _pessoa: dict = Depends(require_not_operacional)):
    """RF-M7 (Entrega 3): ação em massa independente de troca de modo — abre
    a fila numa sprint em andamento sem migrar o projeto inteiro."""
    client = get_client()
    sprint_id = get_current_sprint_id(client, project_id)
    if not sprint_id:
        return {"desvinculadas": 0}

    tasks = client.table("tasks").select("id, coluna_kanban, sprint_id").eq("project_id", project_id).eq("sprint_id", sprint_id).eq("coluna_kanban", "planejado").execute().data or []
    for task in tasks:
        client.table("tasks").update({"operacional_id": None}).eq("id", task["id"]).execute()

    return {"desvinculadas": len(tasks)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_migracao_modo.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/projects.py docudata-backend/tests/test_migracao_modo.py
git commit -m "feat(projects): POST /desvincular-planejado — abre fila sem trocar de modo (Entrega 3)"
```

---

## Onda C — Fila real

### Task 14: `POST /tasks/{id}/puxar` (pull atômico)

**Files:**
- Modify: `docudata-backend/routers/tasks.py`
- Test: `docudata-backend/tests/test_pull_devolver.py` (novo)

**Interfaces:**
- Consumes: `check_wip(client, project_id, operacional_id, coluna_destino) -> tuple[bool, str | None]` (já existe, `services/wip_check.py`).
- Produces: `POST /tasks/{id}/puxar` → 200 com `TaskResponse` atualizada, 409 se já puxada por outra pessoa ou se WIP estourado, 403 se a task está fora da fila (rascunho ou já tem responsável).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pull_devolver.py (novo)
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _mock_client(task, operacional_da_pessoa=None, wip_config=None, update_rowcount=1):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "tasks":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = [task] if task else []
                q.execute = MagicMock(return_value=resp)
                return q

            def update_side_effect(payload):
                q = MagicMock()

                def eq_effect(*a, **kw):
                    return q

                def execute_effect():
                    resp = MagicMock()
                    if update_rowcount == 0:
                        resp.data = []
                    else:
                        resp.data = [dict(task, **payload)]
                    return resp

                q.eq = MagicMock(side_effect=eq_effect)
                q.execute = MagicMock(side_effect=execute_effect)
                return q

            tbl.select = MagicMock(side_effect=select_side_effect)
            tbl.update = MagicMock(side_effect=update_side_effect)
        elif name == "operacionais":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [operacional_da_pessoa] if operacional_da_pessoa else []
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"wip_config": wip_config or {}}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


@pytest.fixture
def make_client(monkeypatch, autenticar):
    def _make(task, operacional_da_pessoa, cargo="operacional", wip_config=None, update_rowcount=1):
        import routers.tasks as tasks_router
        from main import app
        mock_sb = _mock_client(task, operacional_da_pessoa, wip_config, update_rowcount)
        monkeypatch.setattr(tasks_router, "get_client", lambda: mock_sb)
        # A fixture `autenticar` (tests/conftest.py) sempre autentica como
        # "pessoa@citi.org.br", sem parâmetro de e-mail — por isso o
        # `operacional_da_pessoa` de cada teste usa esse mesmo e-mail (é
        # como o mock resolve "qual operacional é o usuário logado").
        tc = autenticar(TestClient(app), cargo=cargo)
        return tc
    return _make


def test_puxar_task_disponivel_atribui_a_quem_puxou(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": False, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 200
    assert resp.json()["operacional_id"] == "op-a"


def test_puxar_task_ja_puxada_da_409(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": False, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"}, update_rowcount=0)

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 409


def test_puxar_task_rascunho_da_403(make_client):
    task = {"id": "t1", "project_id": "proj-1", "operacional_id": None, "rascunho": True, "coluna_kanban": "planejado", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False}
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/puxar")

    assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pull_devolver.py -v`
Expected: FAIL (404 — rota não existe)

- [ ] **Step 3: Write the implementation**

Em `routers/tasks.py`, adicione:

```python
def _resolver_operacional_id_da_pessoa(client, project_id: str, pessoa_email: str) -> Optional[str]:
    """pessoa (login) e operacionais (registro por projeto) são tabelas
    diferentes, reconciliadas por e-mail — nunca pelo mesmo id (mesmo padrão
    de services/auth.py::require_project_access)."""
    resp = client.table("operacionais").select("id").eq("project_id", project_id).eq("email", pessoa_email).execute()
    return resp.data[0]["id"] if resp.data else None


@router.post("/{task_id}/puxar", response_model=TaskResponse)
async def puxar_task(task_id: str, pessoa: dict = Depends(get_current_pessoa)):
    client = get_client()
    resp = client.table("tasks").select("*").eq("id", task_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = resp.data[0]

    if task.get("rascunho") or task.get("operacional_id") is not None:
        raise HTTPException(status_code=403, detail="Esta task não está disponível na fila.")

    operacional_id = _resolver_operacional_id_da_pessoa(client, task["project_id"], pessoa["email"])
    if not operacional_id:
        raise HTTPException(status_code=403, detail="Você não está vinculado a este projeto.")

    ok, motivo = check_wip(client, task["project_id"], operacional_id, "em_andamento")
    if not ok:
        raise HTTPException(status_code=409, detail=motivo)

    agora = datetime.now(timezone.utc).isoformat()
    updates = {
        "operacional_id": operacional_id,
        "coluna_kanban": "em_andamento",
        "entrou_em_andamento_em": agora,
        "pull_em": agora,
        "ordem_fila": None,
    }
    result = (
        client.table("tasks")
        .update(updates)
        .eq("id", task_id)
        .eq("operacional_id", None)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=409, detail="Esta task já foi puxada.")

    return result.data[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pull_devolver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_pull_devolver.py
git commit -m "feat(tasks): POST /puxar — pull atômico da fila (Entrega 3)"
```

---

### Task 15: `POST /tasks/{id}/devolver`

**Files:**
- Modify: `docudata-backend/routers/tasks.py`, `docudata-backend/services/pontuacao.py` (nova função pública)
- Test: `docudata-backend/tests/test_pull_devolver.py`

**Interfaces:**
- Consumes: `_resolver_operacional_id_da_pessoa` (Task 14).
- Produces: `services/pontuacao.py::pontos_travamento_ativo(client, task_id) -> int` (pública, reaproveita a mesma tabela que `_somar_travamentos` já lê). `POST /tasks/{id}/devolver` → 200, RBAC: dono da task ou gerente/líder.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pull_devolver.py — adicionar

def test_devolver_task_limpa_responsavel_e_volta_pra_fila(make_client):
    task = {
        "id": "t1", "project_id": "proj-1", "operacional_id": "op-a", "rascunho": False,
        "coluna_kanban": "em_andamento", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
        "travado_automatico": False,
    }
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/devolver")

    assert resp.status_code == 200
    body = resp.json()
    assert body["operacional_id"] is None
    assert body["coluna_kanban"] == "planejado"


def test_devolver_task_de_outra_pessoa_da_403_para_operacional(make_client):
    task = {
        "id": "t1", "project_id": "proj-1", "operacional_id": "op-b", "rascunho": False,
        "coluna_kanban": "em_andamento", "titulo": "X", "pontos": 3, "checklist": [], "bloqueado": False,
        "travado_automatico": False,
    }
    # operacional_da_pessoa resolve pra "op-a" (via e-mail pessoa@citi.org.br),
    # mas a task pertence a "op-b" — RBAC deve barrar.
    tc = make_client(task, operacional_da_pessoa={"id": "op-a", "email": "pessoa@citi.org.br", "project_id": "proj-1"})

    resp = tc.post("/tasks/t1/devolver")

    assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pull_devolver.py -k devolver -v`
Expected: FAIL (404 — rota não existe)

- [ ] **Step 3: Write the implementation**

Em `services/pontuacao.py`, adicione (função pública nova, sem tocar `_somar_travamentos`):

```python
def pontos_travamento_ativo(client, task_id: str) -> int:
    """Pontos que um travamento automático não dispensado desta task
    representaria — mesma query que _somar_travamentos já faz por trás,
    mas para uma única task (usada pela devolução, routers/tasks.py, pra
    registrar o evento no extrato sem duplicar a regra de cálculo)."""
    rows = (
        client.table("task_travamentos")
        .select("pontos")
        .eq("task_id", task_id)
        .eq("dispensado", False)
        .execute()
        .data or []
    )
    return sum(r.get("pontos") or 0 for r in rows)
```

Em `routers/tasks.py`, adicione o import `from services.pontuacao import pontos_travamento_ativo` (a par de `rotear_evento_pos_fechamento`, já importado) e a rota:

```python
@router.post("/{task_id}/devolver", response_model=TaskResponse)
async def devolver_task(task_id: str, pessoa: dict = Depends(get_current_pessoa)):
    """D5/D6 (Entrega 3): o operacional dono da task ou gerente/líder pode
    devolver. Se a task já estava travado_automatico, registra a mesma
    penalidade que um travamento normal geraria — sem punir devolução antes
    de travar (incentivaria segurar a task)."""
    client = get_client()
    resp = client.table("tasks").select("*").eq("id", task_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    task = resp.data[0]

    if pessoa["cargo"] not in ("owner", "lider", "gerente"):
        meu_operacional_id = _resolver_operacional_id_da_pessoa(client, task["project_id"], pessoa["email"])
        if meu_operacional_id != task.get("operacional_id"):
            raise HTTPException(status_code=403, detail="Só quem está com a task (ou gerente/líder) pode devolvê-la.")

    if task.get("travado_automatico"):
        pontos = pontos_travamento_ativo(client, task_id)
        if pontos > 0:
            client.table("pontuacao_eventos").insert({
                "operacional_id": task["operacional_id"],
                "sprint_id": task.get("sprint_id"),
                "projeto_id": task["project_id"],
                "task_id": task_id,
                "tipo": "devolucao_penalidade",
                "pontos": -pontos,
                "descricao": "Devolução após travamento automático",
            }).execute()

    agora = datetime.now(timezone.utc).isoformat()
    fila = client.table("tasks").select("ordem_fila").eq("project_id", task["project_id"]).eq("coluna_kanban", "planejado").execute().data or []
    max_ordem = max((t.get("ordem_fila") or 0) for t in fila) if fila else 0

    updates = {
        "operacional_id": None,
        "coluna_kanban": "planejado",
        "pull_em": None,
        "entrou_em_andamento_em": None,
        "travado_automatico": False,
        "ordem_fila": max_ordem + 1,
    }
    result = client.table("tasks").update(updates).eq("id", task_id).execute()
    return result.data[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pull_devolver.py -v && pytest -q`
Expected: PASS em tudo (o segundo comando é a suíte completa — confirma golden regression intacta)

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/services/pontuacao.py docudata-backend/tests/test_pull_devolver.py
git commit -m "feat(tasks): POST /devolver — devolução com penalidade condicional (Entrega 3)"
```

---

### Task 16: Frontend — pergunta 1 da Avaliação Semanal condicional por modo

**Files:**
- Modify: `docudata-frontend/app/components/AvaliacaoSemanalModal.tsx:11-31,162`
- Modify: `docudata-frontend/app/[subarea]/projects/[id]/page.tsx:1853-1856`
- Test: `docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs`

**Interfaces:**
- Produces: `AvaliacaoSemanalModal` ganha a prop `modoTrabalho: "ATRIBUICAO" | "PULL"`.

- [ ] **Step 1: Write the failing test**

```javascript
// tests/modos-trabalho-avaliacao-entrega3.test.mjs — adicionar

test("pergunta 1 da Avaliação Semanal muda de texto conforme o modo de trabalho", () => {
  const src = readFileSync(
    new URL("../app/components/AvaliacaoSemanalModal.tsx", import.meta.url),
    "utf-8"
  );
  assert.match(src, /modoTrabalho/);
  assert.match(src, /Puxou e entregou num ritmo consistente\?/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/modos-trabalho-avaliacao-entrega3.test.mjs`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

Em `AvaliacaoSemanalModal.tsx`, substitua o array `PERGUNTAS` (linhas 11-19) por uma função:

```tsx
function perguntas(modoTrabalho: "ATRIBUICAO" | "PULL"): string[] {
  return [
    modoTrabalho === "PULL"
      ? "Puxou e entregou num ritmo consistente?"
      : "Entregou o que se comprometeu dentro do combinado nesta sprint?",
    "A qualidade da entrega precisou de pouca ou nenhuma correção?",
    "A pessoa destravou sozinha antes de te escalar?",
    "A comunicação da entrega foi clara a ponto de você não precisar perguntar?",
    "Ajudou, desbloqueou ou ensinou outro membro nesta sprint?",
    "Evoluiu em relação a onde estava no começo do ciclo?",
    "Trouxe algo além do que foi pedido?",
  ];
}
```

Atualize a interface `Props` (linha 21-26) pra incluir `modoTrabalho: "ATRIBUICAO" | "PULL";`, a assinatura do componente (linha 31) pra receber `modoTrabalho`, e o uso em `PERGUNTAS.map` (linha 162) pra `perguntas(modoTrabalho).map(...)`.

Em `app/[subarea]/projects/[id]/page.tsx`, no render de `<AvaliacaoSemanalModal>` (linha 1853), adicione a prop:

```tsx
        <AvaliacaoSemanalModal
          sprintId={avaliacaoModal.sprintId}
          sprintNumero={avaliacaoModal.sprintNumero}
          modoTrabalho={project?.modo_trabalho ?? "ATRIBUICAO"}
          onClose={() => setAvaliacaoModal(null)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/modos-trabalho-avaliacao-entrega3.test.mjs && npx tsc --noEmit`
Expected: PASS, sem erro de tipo

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/components/AvaliacaoSemanalModal.tsx "docudata-frontend/app/[subarea]/projects/[id]/page.tsx" docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs
git commit -m "feat(avaliacao): pergunta 1 condicional por modo de trabalho (Entrega 3)"
```

---

### Task 17: Frontend — botões Puxar/Devolver e badge de rascunho no Kanban

**Files:**
- Modify: `docudata-frontend/app/components/TasksKanbanTab.tsx` (`TaskCard`, `TaskViewModal`, `TasksKanbanTab`)
- Modify: `docudata-frontend/app/lib/api.ts` (novas funções + campos do tipo `TaskKanbanResponse`)
- Test: `docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs`

**Interfaces:**
- Produces: `puxarTask(taskId: string): Promise<TaskKanbanResponse>`, `devolverTask(taskId: string): Promise<TaskKanbanResponse>` em `api.ts`. `TaskCard`/`TaskViewModal` ganham prop `modoTrabalho`; `TasksKanbanTab` ganha prop `modoTrabalho` e a repassa.

- [ ] **Step 1: Write the failing test**

```javascript
// tests/modos-trabalho-avaliacao-entrega3.test.mjs — adicionar

test("api.ts expõe puxarTask e devolverTask", () => {
  const src = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");
  assert.match(src, /export async function puxarTask/);
  assert.match(src, /export async function devolverTask/);
});

test("Kanban mostra badge de rascunho e ações de puxar/devolver conforme o modo", () => {
  const src = readFileSync(
    new URL("../app/components/TasksKanbanTab.tsx", import.meta.url),
    "utf-8"
  );
  assert.match(src, /rascunho/);
  assert.match(src, /puxarTask/);
  assert.match(src, /devolverTask/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/modos-trabalho-avaliacao-entrega3.test.mjs`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

Em `app/lib/api.ts`, adicione ao `TaskKanbanResponse` (após `extra: boolean;`, linha 1630):

```ts
  entrou_na_fila_em?: string | null;
  pull_em?: string | null;
  atribuida_manualmente: boolean;
  motivo_atribuicao_manual?: string | null;
  rascunho: boolean;
  motivo_rascunho?: string | null;
  ordem_fila?: number | null;
```

E ao final do arquivo:

```ts
export async function puxarTask(taskId: string): Promise<TaskKanbanResponse> {
  const res = await apiFetch(`${API}/tasks/${taskId}/puxar`, { method: "POST" });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? "Erro ao puxar task");
  return res.json();
}

export async function devolverTask(taskId: string): Promise<TaskKanbanResponse> {
  const res = await apiFetch(`${API}/tasks/${taskId}/devolver`, { method: "POST" });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? "Erro ao devolver task");
  return res.json();
}
```

Em `app/components/TasksKanbanTab.tsx`, importe as duas funções novas junto das existentes. Adicione `rascunho` como badge em `TaskCard` (após o badge de `travado_automatico`, linha ~796):

```tsx
        {task.rascunho && (
          <span style={{ ...chip, background: "#fef3c7", color: "#a16207" }} title={task.motivo_rascunho ?? undefined}>
            📝 Rascunho
          </span>
        )}
```

Em `TaskViewModal`, adicione as props `modoTrabalho: "ATRIBUICAO" | "PULL"` e `meuOperacionalId: string | null` (repassadas por `TasksKanbanTab`, que já resolve `meuOperacional` internamente — thread a mesma variável já usada na linha ~839 do arquivo). Adicione, antes do botão "Fechar" (linha ~649):

```tsx
        {modoTrabalho === "PULL" && !task.operacional_id && !task.rascunho && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
            <button
              type="button"
              onClick={async () => {
                const atualizada = await puxarTask(task.id);
                onSaved(atualizada);
              }}
              style={btnPrimary}
            >
              Puxar esta task
            </button>
          </div>
        )}
        {modoTrabalho === "PULL" && task.operacional_id && (meuOperacionalId === task.operacional_id) && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
            <button
              type="button"
              onClick={async () => {
                const atualizada = await devolverTask(task.id);
                onSaved(atualizada);
              }}
              style={{ ...btnPrimary, background: "#fff", color: "#dc2626", border: "1px solid #fecaca" }}
            >
              Devolver à fila
            </button>
          </div>
        )}
```

Repasse `modoTrabalho`/`meuOperacionalId` de `TasksKanbanTab` (assinatura na linha 811, `Props` correspondente) para `TaskViewModal` no ponto onde ele é renderizado, e adicione `modoTrabalho: "ATRIBUICAO" | "PULL";` à interface `Props` do componente principal — o chamador (`page.tsx`, mesmo padrão da Task 16) passa `project?.modo_trabalho ?? "ATRIBUICAO"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/modos-trabalho-avaliacao-entrega3.test.mjs && npx tsc --noEmit && npm run build`
Expected: PASS, build limpo

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/lib/api.ts docudata-frontend/app/components/TasksKanbanTab.tsx "docudata-frontend/app/[subarea]/projects/[id]/page.tsx" docudata-frontend/tests/modos-trabalho-avaliacao-entrega3.test.mjs
git commit -m "feat(kanban): botões Puxar/Devolver e badge de rascunho (Entrega 3)"
```
