# Peso do Gerente, Remoção da Evolução e Ranking por Projeto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Subir o peso do gerente pra 50% em todos os arquétipos, remover por completo a dimensão "Evolução" do sistema de avaliação (pergunta, peso, tela, endpoint, documentação), e dividir o ranking de performance por projeto em vez de cross-projeto.

**Architecture:** Onda 1 (backend) migra os pesos, remove a dimensão Evolução do motor de cálculo (`services/performance.py`) e dos endpoints relacionados, e troca a função de agrupamento do ranking por uma versão por-projeto — sem tocar nas funções de cálculo por dimensão, que já generalizam pro caso de um projeto só. Onda 2 (frontend) reflete essas mudanças: questionário de 6 perguntas, tabela de métricas sem a coluna Evolução, tela de ranking reescrita pra mostrar uma seção por projeto. Onda 3 atualiza a documentação viva do sistema de avaliação.

**Tech Stack:** FastAPI + Pydantic + supabase-py (backend, testes com `unittest.mock.MagicMock`); Next.js 15 / React 19 com inline styles (frontend, sem design system file).

**Spec:** `docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md` — o plano argumenta a partir da spec; quem executar deve ler as duas.

## Global Constraints

- Migração de schema é sempre manual (bloco SQL que o usuário cola no Supabase) — nunca roda sozinha, mesma convenção do projeto inteiro. A task que adiciona esse bloco precisa avisar explicitamente o usuário no fim.
- Nenhuma migração destrutiva: sem `DROP COLUMN`, sem `DROP TABLE` — só `ALTER`/`UPDATE` aditivos ou relaxando constraints (`DROP NOT NULL`), seguindo o padrão já estabelecido neste projeto (nenhum bloco de migração existente até hoje remove coluna ou tabela).
- Depois da migração de `pesos_arquetipo`, todo ranking (inclusive de sprints já fechadas) reflete os pesos novos automaticamente no próximo `GET /performance` — não existe, e não deve ser criado, nenhum mecanismo de "recálculo" separado, porque `score_final` nunca é persistido, só calculado ao vivo. Um teste prova isso (Task 6).
- Remoção de "evolução" é completa: pergunta 6 do questionário, peso na nota final, endpoint/tela de SPI-evolução, endpoint de baseline-evolução, e toda a documentação viva (`docudata-backend/docs/`) — nada com a palavra "evolução" relacionado a essa dimensão de nota deve sobrar no código depois desta feature. Grep final de verificação é obrigatório na última task de cada onda.
- Fora de escopo, não implementar: a tela de comparação lado a lado das avaliações do gerente (feature separada, plano futuro); qualquer automação de reabrir/refechar sprint (não é necessária, ver spec §3); edição de avaliação já enviada por UI dedicada (backend já aceita upsert em 48h, sem UI nova aqui).
- Onda 2 só começa depois da Onda 1 100% verificada (suíte completa de backend verde). Onda 3 (docs) pode rodar em paralelo à Onda 2, mas só é considerada concluída depois que Onda 2 fixar os textos de UI que a documentação referencia.
- Frontend tem duas verificações obrigatórias e independentes: `npx tsc --noEmit` **e** `npm test` (`node --test tests/*.test.mjs`) — rodar as duas, não só o typecheck.
- Commits diretos em `main`, sem branch/PR, um commit por task.
- Isso afeta a nota real de avaliação de pessoas — testar a fórmula de pesos com cuidado redobrado (soma = 1.00 para cada arquétipo, comportamento quando falta uma dimensão continua funcionando corretamente com uma dimensão a menos no mapa de pesos).

---

## ONDA 1 — Backend

### Task 1: Migração de schema — pesos novos + `resposta_6` opcional

**Files:**
- Modify: `docudata-backend/supabase_schema.sql` (final do arquivo, bloco de ALTERs/UPDATEs)
- Test: `docudata-backend/tests/test_pesos_gerente_evolucao_migracao.py`

**Interfaces:**
- Produces: `pesos_arquetipo` com os pesos novos (padrao: gerente=0.50, entrega=0.18, qualidade=0.18, autonomia=0.14, evolucao=0.00; consultoria_discovery: gerente=0.50, entrega=0.24, qualidade=0.12, autonomia=0.14, evolucao=0.00); `avaliacoes_gerente.resposta_6` aceita NULL. Tasks seguintes assumem que o SQL manual já rodou em produção.

- [ ] **Step 1: Escrever o teste que descreve o schema esperado**

Crie `docudata-backend/tests/test_pesos_gerente_evolucao_migracao.py` (mesmo padrão de `tests/test_pendente_aprovacao_schema.py` — lê o `.sql` como texto):

```python
"""Confirma que a migração de pesos (gerente 50%, evolução removida) e a
coluna resposta_6 opcional estão presentes no schema. Ver
docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md."""
from pathlib import Path

_SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


def _texto_schema() -> str:
    return _SCHEMA.read_text()


def test_update_pesos_arquetipo_padrao_presente():
    schema = _texto_schema()
    assert "UPDATE pesos_arquetipo SET" in schema
    assert "peso_gerente = 0.50" in schema
    assert "peso_evolucao = 0.00" in schema
    assert "WHERE arquetipo = 'padrao'" in schema


def test_update_pesos_arquetipo_consultoria_presente():
    schema = _texto_schema()
    assert "WHERE arquetipo = 'consultoria_discovery'" in schema


def test_resposta_6_vira_opcional():
    schema = _texto_schema()
    assert "ALTER TABLE avaliacoes_gerente ALTER COLUMN resposta_6 DROP NOT NULL;" in schema
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_pesos_gerente_evolucao_migracao.py -v`
Expected: FAIL nos três — nada disso existe em `supabase_schema.sql` ainda.

- [ ] **Step 3: Adicionar o bloco de migração no final de `supabase_schema.sql`**

Adicione, depois do último bloco de `ALTER`/`UPDATE` já existente no arquivo:

```sql
-- Entrega "Peso do gerente 50% + remoção da Evolução" (2026-09-23): sobe
-- peso_gerente pra 0.50 nos dois arquétipos, zera peso_evolucao (a dimensão
-- deixa de existir no motor de cálculo — services/performance.py), e
-- redistribui o que sobrou de Entrega/Qualidade/Autonomia mantendo a
-- proporção relativa que já existia entre elas. Ver
-- docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md §2.1.
UPDATE pesos_arquetipo SET
    peso_gerente = 0.50,
    peso_entrega = 0.18,
    peso_qualidade = 0.18,
    peso_autonomia = 0.14,
    peso_evolucao = 0.00
WHERE arquetipo = 'padrao';

UPDATE pesos_arquetipo SET
    peso_gerente = 0.50,
    peso_entrega = 0.24,
    peso_qualidade = 0.12,
    peso_autonomia = 0.14,
    peso_evolucao = 0.00
WHERE arquetipo = 'consultoria_discovery';

-- A pergunta 6 do questionário semanal ("Evoluiu em relação a onde estava no
-- começo do ciclo?") sai do formulário — resposta_6 deixa de ser exigida.
-- Coluna não é removida (dado histórico continua legível, mesma convenção
-- não-destrutiva de toda migração deste projeto). O CHECK existente já
-- permite NULL, não precisa recriar a constraint.
ALTER TABLE avaliacoes_gerente ALTER COLUMN resposta_6 DROP NOT NULL;
```

**Antes deste bloco, confirme os valores atuais de produção do arquétipo 'consultoria_discovery'** (Step 3.5, verificação, não altera nada): se você tiver acesso a rodar uma consulta contra o Supabase de produção, rode `SELECT * FROM pesos_arquetipo WHERE arquetipo = 'consultoria_discovery';` e confirme que `peso_entrega=0.20, peso_qualidade=0.10, peso_autonomia=0.12` (os valores assumidos nesta task, vindos de `docs/superpowers/specs/2026-09-06-peso-arquetipo-performance-design.md`). Se produção divergir desses valores, recalcule a redistribuição do Step 3 usando a proporção REAL entre peso_entrega/peso_qualidade/peso_autonomia daquela linha (mantendo peso_gerente=0.50, peso_evolucao=0.00, e as outras três somando 0.50 na mesma proporção relativa, arredondado a 2 casas decimais somando exatamente 0.50) antes de escrever o SQL acima. Se você não tiver acesso a produção neste momento, prossiga com os valores assumidos acima e sinalize essa suposição no relatório final da task.

- [ ] **Step 4: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_pesos_gerente_evolucao_migracao.py -v`
Expected: PASS nos três.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/supabase_schema.sql docudata-backend/tests/test_pesos_gerente_evolucao_migracao.py
git commit -m "feat(pontuacao): migração de pesos (gerente 50%, evolução zerada) e resposta_6 opcional"
```

**⚠️ Aviso pro usuário nesta task:** o SQL do Step 3 precisa ser rodado manualmente no SQL Editor do Supabase antes de qualquer avaliação nova refletir os pesos corretos em produção. Nenhuma task seguinte depende disso pra passar nos testes automatizados (que usam mocks), mas a feature real (incluindo a correção da avaliação que o usuário considerou injusta) só se aplica depois desse UPDATE rodar.

---

### Task 2: Remover a dimensão Evolução de `services/performance.py`

**Files:**
- Modify: `docudata-backend/services/performance.py:78,179-183,255` (remove `_evolucao_por_projeto`, a chave `"evolucao"` em `sub_scores` e em `mapa_peso`)
- Test: `docudata-backend/tests/test_performance_ranking.py`

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `_calcular_janela` retorna um dict sem a chave `"evolucao"`; `_score_final` normaliza corretamente sem essa dimensão. Task 5 (ranking por projeto) e Task 10 (frontend) assumem que `evolucao` não existe mais na resposta.

- [ ] **Step 1: Escrever o teste que confirma a ausência da dimensão**

Em `docudata-backend/tests/test_performance_ranking.py`, adicione (junto às importações do topo, mantenha `listar_pessoas_ativas` por enquanto — ele é removido só na Task 5):

```python
def test_calcular_janela_nao_tem_mais_a_chave_evolucao():
    linhas = [_linha("2026-09-05T00:00:00+00:00", gerente_media=5.0)]
    client = _mock_client(pontuacao=linhas, projetos=[{"id": "proj-1", "arquetipo": "padrao", "name": "Projeto 1"}])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    ranking = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert "evolucao" not in ranking["sprint"]
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_performance_ranking.py::test_calcular_janela_nao_tem_mais_a_chave_evolucao -v`
Expected: FAIL — `ranking["sprint"]` ainda tem `"evolucao"`.

- [ ] **Step 3: Remover a dimensão em `services/performance.py`**

Delete a função inteira (linhas 179-183 hoje):

```python
def _evolucao_por_projeto(linhas: list[dict]) -> float | None:
    valores = [l["gerente_pergunta6"] for l in linhas if l.get("gerente_pergunta6") is not None]
    if not valores:
        return None
    return round(min(sum(valores) / len(valores) * 20, 100), 2)
```

Em `_calcular_janela`, troque:

```python
    sub_scores = {
        "entrega": _media_cross_projeto(por_projeto, _entrega_por_projeto),
        "gerente": _media_cross_projeto(por_projeto, _gerente_por_projeto),
        "evolucao": _media_cross_projeto(por_projeto, _evolucao_por_projeto),
        "autonomia": _media_cross_projeto(
```

por:

```python
    sub_scores = {
        "entrega": _media_cross_projeto(por_projeto, _entrega_por_projeto),
        "gerente": _media_cross_projeto(por_projeto, _gerente_por_projeto),
        "autonomia": _media_cross_projeto(
```

Em `_score_final`, troque:

```python
    mapa_peso = {
        "entrega": float(pesos["peso_entrega"]),
        "gerente": float(pesos["peso_gerente"]),
        "qualidade": float(pesos["peso_qualidade"]),
        "autonomia": float(pesos["peso_autonomia"]),
        "evolucao": float(pesos["peso_evolucao"]),
    }
```

por:

```python
    mapa_peso = {
        "entrega": float(pesos["peso_entrega"]),
        "gerente": float(pesos["peso_gerente"]),
        "qualidade": float(pesos["peso_qualidade"]),
        "autonomia": float(pesos["peso_autonomia"]),
    }
```

- [ ] **Step 4: Rodar o teste de novo e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_performance_ranking.py::test_calcular_janela_nao_tem_mais_a_chave_evolucao -v`
Expected: PASS.

- [ ] **Step 5: Atualizar `test_score_final_so_com_avaliacao_do_gerente_quando_zero_tasks`**

Esse teste (perto do final do arquivo) hoje testa explicitamente a presença da dimensão Evolução no cálculo de `score_final`. Troque o teste inteiro:

De:
```python
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

Para:
```python
def test_score_final_so_com_avaliacao_do_gerente_quando_zero_tasks():
    """Operacional vinculado ao projeto, zero tasks na sprint, avaliação do
    gerente completa. Entrega fica indisponível (alocados=0), Qualidade fica
    indisponível (sem task concluída nem commit), Autonomia só tem a
    pergunta 3 (sem bloqueio nenhum) — mas Gerente está disponível, então
    score_final não pode ser None (Evolução não existe mais como dimensão,
    ver Task 2 do plano de 2026-09-23)."""
    linha = {
        "projeto_id": "proj-1", "sprint_fim": "2026-09-01T00:00:00Z",
        "entrega_modo": "PONTOS_ATRIBUIDOS",
        "entrega_pontos_concluidos": 0, "entrega_pontos_alocados": 0, "entrega_pontos_penalizados": 0,
        "entrega_pontos_pessoa": None, "entrega_denominador": None, "entrega_nota_relativa": None,
        "bonus_pontos_extra": 0,
        "gerente_media": 4.0, "gerente_pergunta3": 4,
        "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 0, "qualidade_commit_media": None,
        "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
    }
    operacionais = [{"id": "op-a", "nome": "A", "email": "a@x.com", "ativo": True, "project_id": "proj-1"}]
    client = _mock_client(operacionais=operacionais, pontuacao=[dict(linha, operacional_id="op-a")], projetos=[{"id": "proj-1", "arquetipo": "padrao", "name": "Projeto 1"}])

    pessoa = listar_pessoas_ativas(client)[0]
    resultado = calcular_ranking_pessoa(client, pessoa, _PESOS)

    assert resultado["sprint"] is not None
    assert resultado["sprint"]["score_final"] is not None
    assert resultado["sprint"]["entrega"] is None
    assert resultado["sprint"]["qualidade"] is None
    assert resultado["sprint"]["gerente"] == 80.0  # 4.0 * 20
    assert "evolucao" not in resultado["sprint"]
    # score_final = (peso_gerente*80 + peso_autonomia*autonomia) / (peso_gerente+peso_autonomia)
    # autonomia (só pergunta3, sem bloqueio) = min(4*20,100) = 80
    peso_disponivel = 0.35 + 0.15
    esperado = round((0.35 * 80.0 + 0.15 * 80.0) / peso_disponivel, 2)
    assert resultado["sprint"]["score_final"] == esperado
```

Note que este Step mantém `listar_pessoas_ativas` (a função antiga) — ela só é renomeada/substituída na Task 5. `_PESOS` (o dict de pesos de teste no topo do arquivo) continua com os valores antigos (0.35 etc.) nesta task — são valores arbitrários de teste pra exercitar a fórmula, não precisam bater com os valores reais de produção da Task 1; `peso_disponivel` no teste acima usa `0.35 + 0.15` porque são os valores de `_PESOS["padrao"]["peso_gerente"]` e `_PESOS["padrao"]["peso_autonomia"]` como já estão no arquivo.

- [ ] **Step 6: Rodar a suíte de performance inteira e confirmar que passa**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_performance_ranking.py -v`
Expected: PASS em tudo.

- [ ] **Step 7: Commit**

```bash
git add docudata-backend/services/performance.py docudata-backend/tests/test_performance_ranking.py
git commit -m "feat(performance): remove a dimensão Evolução do motor de cálculo do score final"
```

---

### Task 3: `resposta_6` opcional em `models/schemas.py`

**Files:**
- Modify: `docudata-backend/models/schemas.py:661-701` (`AvaliacaoGerenteCreate`, `AvaliacaoGerenteResponse`, `AvaliacaoAnteriorResponse`)
- Test: `docudata-backend/tests/test_task_schemas.py` (ou novo arquivo `docudata-backend/tests/test_avaliacao_schemas.py` se `test_task_schemas.py` não for o lugar certo — confira o padrão de nomes já usado antes de decidir)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `AvaliacaoGerenteCreate.resposta_6: Optional[int] = None`; `AvaliacaoGerenteResponse.resposta_6: Optional[int] = None`; `AvaliacaoAnteriorResponse.resposta_6: Optional[int] = None`. Task 4 (frontend `AvaliacaoSemanalModal.tsx`) e Task 11 assumem que o backend aceita o payload sem `resposta_6`.

- [ ] **Step 1: Escrever o teste que descreve o schema esperado**

Crie `docudata-backend/tests/test_avaliacao_schemas.py`:

```python
"""resposta_6 (a antiga pergunta de evolução) vira opcional nos schemas de
avaliação — o questionário passou a ter 6 perguntas. Ver
docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md."""
import pytest
from pydantic import ValidationError

from models.schemas import AvaliacaoAnteriorResponse, AvaliacaoGerenteCreate, AvaliacaoGerenteResponse


def test_avaliacao_gerente_create_aceita_sem_resposta_6():
    data = AvaliacaoGerenteCreate(
        operacional_id="op-1", sprint_id="sprint-1",
        resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_7=5,
    )
    assert data.resposta_6 is None


def test_avaliacao_gerente_create_ainda_aceita_resposta_6_explicita():
    data = AvaliacaoGerenteCreate(
        operacional_id="op-1", sprint_id="sprint-1",
        resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_6=0, resposta_7=5,
    )
    assert data.resposta_6 == 0


def test_avaliacao_gerente_create_resposta_6_fora_de_0_5_ainda_rejeita():
    with pytest.raises(ValidationError):
        AvaliacaoGerenteCreate(
            operacional_id="op-1", sprint_id="sprint-1",
            resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_6=9, resposta_7=5,
        )


def test_avaliacao_gerente_response_aceita_resposta_6_none():
    resp = AvaliacaoGerenteResponse(
        id="a1", operacional_id="op-1", gerente_id="ger-1", sprint_id="sprint-1",
        resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_7=5,
        criado_em="2026-09-23T00:00:00Z", editavel_ate="2026-09-25T00:00:00Z",
    )
    assert resp.resposta_6 is None


def test_avaliacao_anterior_response_aceita_resposta_6_none():
    resp = AvaliacaoAnteriorResponse(
        avaliacao_id="a1", project_name="Projeto X", criado_em="2026-09-23T00:00:00Z",
        resposta_1=5, resposta_2=4, resposta_3=3, resposta_4=2, resposta_5=1, resposta_7=5,
    )
    assert resp.resposta_6 is None
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_avaliacao_schemas.py -v`
Expected: FAIL em `test_avaliacao_gerente_create_aceita_sem_resposta_6`, `test_avaliacao_gerente_response_aceita_resposta_6_none` e `test_avaliacao_anterior_response_aceita_resposta_6_none` (campo obrigatório ausente); os outros dois já passam mesmo antes da mudança (não removem cobertura, só confirmam comportamento que não pode quebrar).

- [ ] **Step 3: Implementar em `models/schemas.py`**

Troque:

```python
class AvaliacaoGerenteCreate(BaseModel):
    operacional_id: str
    sprint_id: str
    resposta_1: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_2: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_3: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_4: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_5: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_6: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_7: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    reaproveitada_de: Optional[str] = None


class AvaliacaoGerenteResponse(BaseModel):
    id: str
    operacional_id: str
    gerente_id: str
    sprint_id: str
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: int
    resposta_7: int
    reaproveitada_de: Optional[str] = None
    criado_em: datetime
    editavel_ate: datetime


class AvaliacaoAnteriorResponse(BaseModel):
    avaliacao_id: str
    project_name: str
    criado_em: datetime
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: int
    resposta_7: int
```

por (nota: `resposta_1`..`resposta_5` e `resposta_7` continuam obrigatórios nos três modelos — só `resposta_6` muda):

```python
class AvaliacaoGerenteCreate(BaseModel):
    operacional_id: str
    sprint_id: str
    resposta_1: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_2: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_3: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_4: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_5: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_6: Optional[int] = Field(default=None, ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    resposta_7: int = Field(..., ge=_RESPOSTA_MIN, le=_RESPOSTA_MAX)
    reaproveitada_de: Optional[str] = None


class AvaliacaoGerenteResponse(BaseModel):
    id: str
    operacional_id: str
    gerente_id: str
    sprint_id: str
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: Optional[int] = None
    resposta_7: int
    reaproveitada_de: Optional[str] = None
    criado_em: datetime
    editavel_ate: datetime


class AvaliacaoAnteriorResponse(BaseModel):
    avaliacao_id: str
    project_name: str
    criado_em: datetime
    resposta_1: int
    resposta_2: int
    resposta_3: int
    resposta_4: int
    resposta_5: int
    resposta_6: Optional[int] = None
    resposta_7: int
```

- [ ] **Step 4: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_avaliacao_schemas.py -v`
Expected: PASS nos cinco.

- [ ] **Step 5: Rodar a suíte de avaliações existente pra confirmar que nada quebrou**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_avaliacoes_submit.py tests/test_avaliacoes_pendencias.py tests/test_avaliacoes_rbac.py -v`
Expected: PASS em tudo — esses arquivos já mandam `resposta_6` explicitamente em todos os payloads de teste, então continuam passando sem nenhuma edição neles (campo virar opcional não quebra quem já manda o valor).

- [ ] **Step 6: Commit**

```bash
git add docudata-backend/models/schemas.py docudata-backend/tests/test_avaliacao_schemas.py
git commit -m "feat(avaliacoes): resposta_6 vira opcional nos schemas — questionário passa a ter 6 perguntas"
```

---

### Task 4: `POST /avaliacoes` aceita payload sem `resposta_6`

**Files:**
- Modify: `docudata-backend/tests/test_avaliacoes_submit.py`

**Interfaces:**
- Consumes: `AvaliacaoGerenteCreate.resposta_6: Optional[int]` (Task 3).
- Produces: nenhuma outra task consome isso.

`routers/avaliacoes.py::criar_ou_atualizar_avaliacao` já não precisa de nenhuma mudança de código — o payload que ele monta (`"resposta_6": data.resposta_6`) já funciona corretamente com `data.resposta_6` sendo `None` (o cliente Supabase grava `NULL`). Esta task só adiciona o teste que prova isso.

- [ ] **Step 1: Escrever o teste**

Em `docudata-backend/tests/test_avaliacoes_submit.py`, adicione (usando os mesmos helpers `_mock_client`/`_patch_and_client` já existentes no arquivo):

```python
def test_cria_avaliacao_sem_resposta_6(monkeypatch):
    mock_sb, calls = _mock_client()
    tc = _patch_and_client(monkeypatch, mock_sb)
    body_sem_resposta_6 = {k: v for k, v in _BODY_VALIDO.items() if k != "resposta_6"}

    resp = tc.post("/avaliacoes", json=body_sem_resposta_6)

    assert resp.status_code == 201
    assert calls["insert"][0]["resposta_6"] is None
```

- [ ] **Step 2: Rodar o teste e confirmar que já passa**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_avaliacoes_submit.py::test_cria_avaliacao_sem_resposta_6 -v`
Expected: PASS de primeira — não deveria precisar de nenhuma mudança em `routers/avaliacoes.py`, já que `data.resposta_6` (Pydantic) já resolve pra `None` quando o campo não vem no JSON, e o dict `payload["resposta_6"] = data.resposta_6` grava esse `None` sem erro. Se este teste FALHAR, pare e investigue antes de prosseguir — significa que existe uma validação ou transformação em `routers/avaliacoes.py` não coberta pela pesquisa deste plano, e a Task 3 sozinha não é suficiente.

- [ ] **Step 3: Rodar a suíte inteira de avaliações**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_avaliacoes_submit.py tests/test_avaliacoes_pendencias.py tests/test_avaliacoes_rbac.py -v`
Expected: PASS em tudo.

- [ ] **Step 4: Commit**

```bash
git add docudata-backend/tests/test_avaliacoes_submit.py
git commit -m "test(avaliacoes): confirma que POST /avaliacoes aceita payload sem resposta_6"
```

---

### Task 5: SPI-evolução vira SPI; `POST /baseline-evolucao` é removido

**Files:**
- Modify: `docudata-backend/services/pontuacao.py:472-522` (renomeia `listar_spi_evolucao_do_projeto` → `listar_spi_do_projeto`, remove os campos de evolução)
- Modify: `docudata-backend/routers/pontuacao.py` (renomeia rota/função, remove `POST /baseline-evolucao` inteiro)
- Modify: `docudata-backend/models/schemas.py:746-758,814-820` (remove `BaselineEvolucaoCreate`/`Response`, renomeia `SpiEvolucaoOperacionalResponse` → `SpiPorOperacionalDoProjetoResponse` sem o campo `evolucao`)
- Delete: `docudata-backend/tests/test_baseline_evolucao.py`
- Test: `docudata-backend/tests/test_spi_por_operacional_do_projeto.py` (novo, substitui a cobertura perdida)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `GET /projects/{id}/spi` (rota nova, substitui `/spi-evolucao`), `listar_spi_do_projeto(client, projeto_id) -> list[dict]` sem campo `evolucao`. Task 10 (frontend `api.ts`) e Task 12 (`MetricasTab.tsx`) consomem a rota nova.

- [ ] **Step 1: Escrever o teste da rota nova**

Crie `docudata-backend/tests/test_spi_por_operacional_do_projeto.py` (mesmo padrão de mock de `test_baseline_evolucao.py`, adaptado):

```python
"""GET /projects/{id}/spi — substitui /spi-evolucao (a dimensão Evolução foi
removida, ver docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md)."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.auth import criar_jwt


def _mock_client(operacionais=None, pontuacao=None):
    operacionais = operacionais or []
    pontuacao = pontuacao or []
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "projects":
            q = MagicMock()
            q.eq = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "proj-1"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "operacionais":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = operacionais
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        elif name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.eq = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _client_as(monkeypatch, mock_supabase, cargo):
    monkeypatch.setenv("JWT_SECRET", "test-secret-nao-usar-em-producao")
    import routers.pontuacao as pontuacao_router
    monkeypatch.setattr(pontuacao_router, "get_client", lambda: mock_supabase)
    from main import app
    tc = TestClient(app)
    tc.cookies.set("docudata_session", criar_jwt("pessoa-1", "p@citi.com", cargo))
    return tc


def test_spi_do_projeto_nao_tem_mais_campo_evolucao(monkeypatch):
    mock_sb = _mock_client(
        operacionais=[{"id": "op-1", "nome": "Ana"}],
        pontuacao=[{
            "operacional_id": "op-1", "entrega_pontos_concluidos": 9,
            "entrega_pontos_alocados": 10, "entrega_pontos_penalizados": 0,
        }],
    )
    tc = _client_as(monkeypatch, mock_sb, "gerente")

    resp = tc.get("/projects/proj-1/spi")

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["spi"] == 90.0
    assert "evolucao" not in body[0]


def test_spi_do_projeto_operacional_recebe_403(monkeypatch):
    mock_sb = _mock_client()
    tc = _client_as(monkeypatch, mock_sb, "operacional")

    resp = tc.get("/projects/proj-1/spi")

    assert resp.status_code == 403


def test_baseline_evolucao_endpoint_nao_existe_mais(monkeypatch):
    mock_sb = _mock_client()
    tc = _client_as(monkeypatch, mock_sb, "lider")

    resp = tc.post("/baseline-evolucao", json={"operacional_id": "op-1", "ciclo": "2026-S2"})

    assert resp.status_code == 404
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_spi_por_operacional_do_projeto.py -v`
Expected: FAIL em `test_spi_do_projeto_nao_tem_mais_campo_evolucao` e `test_spi_do_projeto_operacional_recebe_403` (rota `/projects/{id}/spi` não existe ainda, só `/spi-evolucao`); `test_baseline_evolucao_endpoint_nao_existe_mais` PASSA de cara (o endpoint antigo ainda existe e vai dar 201/outro código, não 404 — ajuste: se der outro código que não seja 404, confirme que é porque o endpoint antigo responde normalmente, o que é o esperado ANTES da remoção).

- [ ] **Step 3: Deletar o teste antigo de baseline-evolução**

```bash
git rm docudata-backend/tests/test_baseline_evolucao.py
```

- [ ] **Step 4: Renomear e limpar `listar_spi_evolucao_do_projeto` em `services/pontuacao.py`**

Troque:

```python
def listar_spi_evolucao_do_projeto(client, projeto_id: str) -> list[dict]:
    """SPI travado + Evolução por operacional do projeto, para a leitura do
    gerente (a tela do Líder é cross-projeto; esta é do projeto dele).

    Diferente do proxy ao vivo da aba Métricas: aqui só entra o que já foi
    travado pela Avaliação Semanal, que é o mesmo dado que alimenta o ranking."""
    operacionais = (
        client.table("operacionais")
        .select("id, nome")
        .eq("project_id", projeto_id)
        .eq("ativo", True)
        .order("nome", desc=False)
        .execute()
        .data or []
    )
    if not operacionais:
        return []

    linhas = (
        client.table("pontuacao_operacional_sprint")
        .select("operacional_id, entrega_pontos_concluidos, entrega_pontos_alocados, entrega_pontos_penalizados, gerente_pergunta6")
        .eq("projeto_id", projeto_id)
        .execute()
        .data or []
    )
    por_operacional: dict[str, list[dict]] = {}
    for linha in linhas:
        por_operacional.setdefault(linha["operacional_id"], []).append(linha)

    resultado = []
    for op in operacionais:
        minhas = por_operacional.get(op["id"], [])
        concluidos = sum(l["entrega_pontos_concluidos"] for l in minhas)
        penalizados = sum(l.get("entrega_pontos_penalizados") or 0 for l in minhas)
        alocados = sum(l["entrega_pontos_alocados"] for l in minhas)
        spi = None
        if alocados > 0:
            spi = round(min(max(concluidos - penalizados, 0) / alocados * 100, 100), 2)

        notas6 = [l["gerente_pergunta6"] for l in minhas if l.get("gerente_pergunta6") is not None]
        evolucao = round(min(sum(notas6) / len(notas6) * 20, 100), 2) if notas6 else None

        resultado.append({
            "operacional_id": op["id"],
            "nome": op["nome"],
            "spi": spi,
            "evolucao": evolucao,
            "sprints_avaliadas": len(minhas),
            "pontos_penalizados": penalizados,
        })
    return resultado
```

por:

```python
def listar_spi_do_projeto(client, projeto_id: str) -> list[dict]:
    """SPI travado por operacional do projeto, para a leitura do gerente (a
    tela do Líder é cross-projeto; esta é do projeto dele).

    Diferente do proxy ao vivo da aba Métricas: aqui só entra o que já foi
    travado pela Avaliação Semanal, que é o mesmo dado que alimenta o ranking."""
    operacionais = (
        client.table("operacionais")
        .select("id, nome")
        .eq("project_id", projeto_id)
        .eq("ativo", True)
        .order("nome", desc=False)
        .execute()
        .data or []
    )
    if not operacionais:
        return []

    linhas = (
        client.table("pontuacao_operacional_sprint")
        .select("operacional_id, entrega_pontos_concluidos, entrega_pontos_alocados, entrega_pontos_penalizados")
        .eq("projeto_id", projeto_id)
        .execute()
        .data or []
    )
    por_operacional: dict[str, list[dict]] = {}
    for linha in linhas:
        por_operacional.setdefault(linha["operacional_id"], []).append(linha)

    resultado = []
    for op in operacionais:
        minhas = por_operacional.get(op["id"], [])
        concluidos = sum(l["entrega_pontos_concluidos"] for l in minhas)
        penalizados = sum(l.get("entrega_pontos_penalizados") or 0 for l in minhas)
        alocados = sum(l["entrega_pontos_alocados"] for l in minhas)
        spi = None
        if alocados > 0:
            spi = round(min(max(concluidos - penalizados, 0) / alocados * 100, 100), 2)

        resultado.append({
            "operacional_id": op["id"],
            "nome": op["nome"],
            "spi": spi,
            "sprints_avaliadas": len(minhas),
            "pontos_penalizados": penalizados,
        })
    return resultado
```

- [ ] **Step 5: Atualizar `routers/pontuacao.py`**

Troque o docstring do módulo (linha 1) de:
```python
"""Router do Motor de Score: SPI do operacional, evolução e baseline.
```
para:
```python
"""Router do Motor de Score: SPI do operacional.
```

Troque o comentário nas linhas 3-6 de:
```python
Acesso: o ranking e o score final continuam exclusivos do Líder
(routers/performance.py). SPI travado e Evolução por operacional foram abertos
ao Gerente em 2026-09-07 (decisão do Líder) para sustentar a conversa de
feedback — Operacional segue sem acesso a nenhum payload de score.
```
para:
```python
Acesso: o ranking e o score final continuam exclusivos do Líder
(routers/performance.py). SPI travado por operacional foi aberto ao Gerente
em 2026-09-07 (decisão do Líder) para sustentar a conversa de feedback —
Operacional segue sem acesso a nenhum payload de score.
```

Troque o import (linha 16-22) de:
```python
from models.schemas import (
    BaselineEvolucaoCreate,
    BaselineEvolucaoResponse,
    PontuacaoEventoResponse,
    SpiEvolucaoOperacionalResponse,
    SpiOperacionalResponse,
)
```
para:
```python
from models.schemas import (
    PontuacaoEventoResponse,
    SpiOperacionalResponse,
    SpiPorOperacionalDoProjetoResponse,
)
```

Troque o import de serviço (linha 24) de:
```python
from services.pontuacao import calcular_spi_operacional, listar_extrato_pontos, listar_spi_evolucao_do_projeto
```
para:
```python
from services.pontuacao import calcular_spi_operacional, listar_extrato_pontos, listar_spi_do_projeto
```

Troque o endpoint (linhas 40-52) de:
```python
@router.get(
    "/projects/{projeto_id}/spi-evolucao",
    response_model=list[SpiEvolucaoOperacionalResponse],
    dependencies=[Depends(require_not_operacional)],
)
async def get_spi_evolucao_do_projeto(projeto_id: str):
    """SPI travado e Evolução de cada operacional do projeto — a leitura que o
    gerente usa na conversa de feedback. Não expõe score final nem ranking."""
    client = get_client()
    projeto = client.table("projects").select("id").eq("id", projeto_id).execute()
    if not projeto.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return listar_spi_evolucao_do_projeto(client, projeto_id)
```
para:
```python
@router.get(
    "/projects/{projeto_id}/spi",
    response_model=list[SpiPorOperacionalDoProjetoResponse],
    dependencies=[Depends(require_not_operacional)],
)
async def get_spi_do_projeto(projeto_id: str):
    """SPI travado de cada operacional do projeto — a leitura que o gerente
    usa na conversa de feedback. Não expõe score final nem ranking."""
    client = get_client()
    projeto = client.table("projects").select("id").eq("id", projeto_id).execute()
    if not projeto.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return listar_spi_do_projeto(client, projeto_id)
```

Remova inteiramente o endpoint `POST /baseline-evolucao` (a função `criar_baseline_evolucao`, do `@router.post("/baseline-evolucao"...)` até o `return resp.data[0]` que fecha a função — o bloco inteiro que hoje fica entre o endpoint de `/spi-evolucao` e o endpoint de `/{operacional_id}/extrato`).

- [ ] **Step 6: Remover os schemas em `models/schemas.py`**

Delete inteiramente `BaselineEvolucaoCreate` e `BaselineEvolucaoResponse` (linhas 746-758 hoje):

```python
class BaselineEvolucaoCreate(BaseModel):
    operacional_id: str
    ciclo: str
    observacoes: Optional[str] = None


class BaselineEvolucaoResponse(BaseModel):
    id: str
    operacional_id: str
    ciclo: str
    data_snapshot: datetime
    nota_inicial: Optional[float] = None
    observacoes: Optional[str] = None
```

Troque (linhas 814-820 hoje):
```python
class SpiEvolucaoOperacionalResponse(BaseModel):
    operacional_id: str
    nome: str
    spi: Optional[float] = None
    evolucao: Optional[float] = None
    sprints_avaliadas: int
    pontos_penalizados: int
```
por:
```python
class SpiPorOperacionalDoProjetoResponse(BaseModel):
    operacional_id: str
    nome: str
    spi: Optional[float] = None
    sprints_avaliadas: int
    pontos_penalizados: int
```

- [ ] **Step 7: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_spi_por_operacional_do_projeto.py -v`
Expected: PASS nos três (o terceiro, `test_baseline_evolucao_endpoint_nao_existe_mais`, agora dá 404 de verdade porque o endpoint foi removido).

- [ ] **Step 8: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/routers/pontuacao.py docudata-backend/models/schemas.py docudata-backend/tests/test_baseline_evolucao.py docudata-backend/tests/test_spi_por_operacional_do_projeto.py
git commit -m "feat(pontuacao): GET /projects/{id}/spi substitui /spi-evolucao; remove POST /baseline-evolucao"
```

---

### Task 6: Prova de que o ranking recalcula ao vivo com os pesos novos (sem reabrir sprint)

**Files:**
- Test: `docudata-backend/tests/test_pesos_recalculam_ao_vivo.py`

**Interfaces:**
- Consumes: `calcular_ranking_pessoa` (já existente, sem mudança nesta task).
- Produces: nenhuma outra task consome isso — é a prova da spec §3.

- [ ] **Step 1: Escrever o teste**

Crie `docudata-backend/tests/test_pesos_recalculam_ao_vivo.py`:

```python
"""Prova a afirmação da spec §3: score_final nunca é persistido, é sempre
calculado na hora a partir de pesos_arquetipo — então mudar os pesos muda o
ranking no próximo GET /performance, sem precisar reabrir nenhuma sprint.
Ver docs/superpowers/specs/2026-09-23-avaliacao-peso-gerente-evolucao-ranking-design.md §3."""
from unittest.mock import MagicMock

from services.performance import calcular_ranking_pessoa


def _mock_client(pontuacao):
    client = MagicMock()

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "pontuacao_operacional_sprint":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            q.order = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = pontuacao
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        elif name == "projects":
            q = MagicMock()
            q.in_ = MagicMock(return_value=q)
            resp = MagicMock()
            resp.data = [{"id": "proj-1", "arquetipo": "padrao"}]
            q.execute = MagicMock(return_value=resp)
            tbl.select = MagicMock(return_value=q)
        return tbl

    client.table = MagicMock(side_effect=table_side_effect)
    return client


_LINHA_TRAVADA = {
    "operacional_id": "op-1", "sprint_id": "sprint-1", "projeto_id": "proj-1",
    "sprint_fim": "2026-09-05T00:00:00+00:00", "gerente_media": 5.0,
    "entrega_pontos_concluidos": 5, "entrega_pontos_alocados": 10,
    "qualidade_reaberturas": 0, "qualidade_tasks_concluidas": 1,
    "autonomia_bloqueios_resolvidos_proprio": 0, "autonomia_bloqueios_totais": 0,
    "qualidade_commit_media": None,
}


def test_score_muda_quando_pesos_mudam_sem_tocar_na_linha_travada():
    """A MESMA linha de pontuacao_operacional_sprint (já 'travada', como
    se tivesse sido escrita antes da migração de pesos) produz score_final
    diferente dependendo só de qual pesos_arquetipo é passado — prova que o
    cálculo é ao vivo, não lido de um valor congelado."""
    client = _mock_client(pontuacao=[_LINHA_TRAVADA])
    pessoa = {"email": "ana@citi.com", "nome": "Ana", "operacional_ids": ["op-1"]}

    pesos_antigos = {"padrao": {
        "arquetipo": "padrao", "peso_gerente": 0.35, "peso_entrega": 0.20,
        "peso_qualidade": 0.20, "peso_autonomia": 0.15, "peso_evolucao": 0.10,
        "peso_commit_qualidade": 0.50,
    }}
    pesos_novos = {"padrao": {
        "arquetipo": "padrao", "peso_gerente": 0.50, "peso_entrega": 0.18,
        "peso_qualidade": 0.18, "peso_autonomia": 0.14, "peso_evolucao": 0.00,
        "peso_commit_qualidade": 0.50,
    }}

    score_com_pesos_antigos = calcular_ranking_pessoa(client, pessoa, pesos_antigos)["sprint"]["score_final"]
    score_com_pesos_novos = calcular_ranking_pessoa(client, pessoa, pesos_novos)["sprint"]["score_final"]

    assert score_com_pesos_antigos != score_com_pesos_novos
```

- [ ] **Step 2: Rodar o teste e confirmar que passa de primeira**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_pesos_recalculam_ao_vivo.py -v`
Expected: PASS — este teste não exige nenhuma mudança de código, ele só documenta e prova um comportamento que já existe (`calcular_ranking_pessoa` sempre recebe `pesos_por_arquetipo` como argumento e nunca lê um `score_final` gravado). Se este teste FALHAR, é sinal de que uma das tasks anteriores introduziu persistência de `score_final` em algum lugar — pare e investigue, isso violaria a spec §3.

- [ ] **Step 3: Commit**

```bash
git add docudata-backend/tests/test_pesos_recalculam_ao_vivo.py
git commit -m "test(performance): prova que score_final recalcula ao vivo com pesos novos, sem reabrir sprint"
```

---

### Task 7: Ranking por projeto — `services/performance.py` e `routers/performance.py`

**Files:**
- Modify: `docudata-backend/services/performance.py:19-29` (substitui `listar_pessoas_ativas` por `listar_pessoas_ativas_por_projeto`)
- Modify: `docudata-backend/routers/performance.py` (arquivo inteiro)
- Modify: `docudata-backend/models/schemas.py:794-797` (`PerformanceResponse` aninhado)
- Test: `docudata-backend/tests/test_performance_ranking.py`, `docudata-backend/tests/test_performance_endpoint.py`

**Interfaces:**
- Consumes: `calcular_ranking_pessoa` (sem mudança).
- Produces: `listar_pessoas_ativas_por_projeto(client) -> dict[str, dict]` no formato `{projeto_id: {"projeto_nome": str, "pessoas": [...]}}`; `GET /performance` retorna `{"projetos": [{"projeto_id", "projeto_nome", "sprint", "quinzenal", "mensal"}, ...]}`. Task 13 (frontend `performance/page.tsx`) consome esse formato novo.

- [ ] **Step 1: Escrever o teste da nova função de agrupamento**

Em `docudata-backend/tests/test_performance_ranking.py`, troque o import do topo:

```python
from services.performance import listar_pessoas_ativas, calcular_ranking_pessoa, JANELAS
```

por:

```python
from services.performance import listar_pessoas_ativas_por_projeto, calcular_ranking_pessoa, JANELAS
```

Troque o teste `test_listar_pessoas_ativas_agrupa_por_email` (linhas 84-96 hoje):

```python
def test_listar_pessoas_ativas_agrupa_por_email():
    client = _mock_client(operacionais=[
        {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
        {"id": "op-2", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
        {"id": "op-3", "nome": "Bia", "email": None, "ativo": True},
    ])

    pessoas = listar_pessoas_ativas(client)

    ana = next(p for p in pessoas if p["email"] == "ana@citi.com")
    assert sorted(ana["operacional_ids"]) == ["op-1", "op-2"]
    bia = next(p for p in pessoas if p["nome"] == "Bia")
    assert bia["operacional_ids"] == ["op-3"]
```

por:

```python
def test_listar_pessoas_ativas_por_projeto_agrupa_por_projeto_e_email():
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-2", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-3", "nome": "Bia", "email": None, "ativo": True, "project_id": "proj-1"},
            {"id": "op-4", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-2"},
        ],
        projetos=[{"id": "proj-1", "name": "Projeto 1"}, {"id": "proj-2", "name": "Projeto 2"}],
    )

    por_projeto = listar_pessoas_ativas_por_projeto(client)

    assert set(por_projeto.keys()) == {"proj-1", "proj-2"}
    assert por_projeto["proj-1"]["projeto_nome"] == "Projeto 1"
    assert por_projeto["proj-2"]["projeto_nome"] == "Projeto 2"

    pessoas_proj1 = por_projeto["proj-1"]["pessoas"]
    ana_proj1 = next(p for p in pessoas_proj1 if p["email"] == "ana@citi.com")
    assert sorted(ana_proj1["operacional_ids"]) == ["op-1", "op-2"]
    bia_proj1 = next(p for p in pessoas_proj1 if p["nome"] == "Bia")
    assert bia_proj1["operacional_ids"] == ["op-3"]

    # Ana em proj-1 (op-1/op-2) e Ana em proj-2 (op-4) NÃO se juntam — a
    # mesma pessoa aparece separadamente em cada projeto (decisão de
    # 2026-09-23: o ranking deixou de juntar pessoas entre projetos).
    pessoas_proj2 = por_projeto["proj-2"]["pessoas"]
    ana_proj2 = next(p for p in pessoas_proj2 if p["email"] == "ana@citi.com")
    assert ana_proj2["operacional_ids"] == ["op-4"]
```

Adicione um teste novo provando que o cálculo de ranking (não só o agrupamento) fica isolado por projeto — para isso, primeiro atualize `_mock_client` (topo do arquivo) pra filtrar `pontuacao_operacional_sprint` por `operacional_id` de verdade (hoje ele devolve a lista inteira sem filtrar, o que mascararia vazamento entre projetos neste teste específico — mesmo padrão já usado em `test_performance_endpoint.py`). Troque:

```python
        elif name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                q.in_ = MagicMock(return_value=q)
                q.gt = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                resp = MagicMock()
                resp.data = pontuacao
                q.execute = MagicMock(return_value=resp)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
```

por:

```python
        elif name == "pontuacao_operacional_sprint":
            def select_side_effect(cols):
                q = MagicMock()
                state = {"ids": None}

                def in_side_effect(field, values):
                    state["ids"] = set(values)
                    return q

                def execute_side_effect():
                    resp = MagicMock()
                    if state["ids"] is None:
                        resp.data = pontuacao
                    else:
                        resp.data = [p for p in pontuacao if p["operacional_id"] in state["ids"]]
                    return resp

                q.in_ = MagicMock(side_effect=in_side_effect)
                q.gt = MagicMock(return_value=q)
                q.order = MagicMock(return_value=q)
                q.execute = MagicMock(side_effect=execute_side_effect)
                return q
            tbl.select = MagicMock(side_effect=select_side_effect)
```

Essa troca não muda o comportamento de nenhum teste já existente no arquivo (todos eles só têm as linhas de UM operacional na lista `pontuacao`, então filtrar por id ou não filtrar dá o mesmo resultado) — só passa a filtrar de verdade quando mais de um operacional aparece na mesma lista, que é exatamente o caso do teste novo abaixo. Adicione, depois do teste de agrupamento:

```python
def test_pessoa_em_dois_projetos_aparece_separada_com_notas_diferentes():
    linhas = [
        _linha("2026-09-05T00:00:00+00:00", projeto_id="proj-1", operacional_id="op-1", entrega_pontos_concluidos=10, entrega_pontos_alocados=10),
        _linha("2026-09-05T00:00:00+00:00", projeto_id="proj-2", operacional_id="op-2", entrega_pontos_concluidos=2, entrega_pontos_alocados=10),
    ]
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-2", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-2"},
        ],
        pontuacao=linhas,
        projetos=[
            {"id": "proj-1", "arquetipo": "padrao", "name": "Projeto 1"},
            {"id": "proj-2", "arquetipo": "padrao", "name": "Projeto 2"},
        ],
    )

    por_projeto = listar_pessoas_ativas_por_projeto(client)
    ranking_proj1 = calcular_ranking_pessoa(client, por_projeto["proj-1"]["pessoas"][0], _PESOS)
    ranking_proj2 = calcular_ranking_pessoa(client, por_projeto["proj-2"]["pessoas"][0], _PESOS)

    # proj-1: Ana entregou 10/10 = 100; proj-2: Ana entregou 2/10 = 20 — notas
    # diferentes por projeto, sem nenhuma média cross-projeto. Antes desta
    # mudança essas duas linhas teriam virado UMA pessoa só, com entrega
    # média (100+20)/2 = 60.0.
    assert ranking_proj1["sprint"]["entrega"] == 100.0
    assert ranking_proj2["sprint"]["entrega"] == 20.0
```

Por fim, atualize `test_score_final_so_com_avaliacao_do_gerente_quando_zero_tasks` (já editado na Task 2 pra remover a asserção de evolução) trocando sua linha `pessoa = listar_pessoas_ativas(client)[0]` por:

```python
    pessoa = list(listar_pessoas_ativas_por_projeto(client)["proj-1"]["pessoas"])[0]
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_performance_ranking.py -v`
Expected: FAIL nos testes que chamam `listar_pessoas_ativas_por_projeto` (função ainda não existe) — `ImportError` faz o arquivo inteiro falhar na coleta, o que é esperado neste ponto.

- [ ] **Step 3: Substituir `listar_pessoas_ativas` em `services/performance.py`**

Troque:

```python
def listar_pessoas_ativas(client) -> list[dict]:
    """Agrupa operacionais ativos por e-mail — uma pessoa pode ter uma linha
    `operacionais` por projeto. Sem e-mail, cada linha vira sua própria pessoa
    (não dá pra casar identidade cross-projeto sem um identificador comum)."""
    rows = client.table("operacionais").select("id, nome, email, ativo").eq("ativo", True).execute().data or []
    por_chave: dict[str, dict] = {}
    for row in rows:
        chave = row.get("email") or row["id"]
        pessoa = por_chave.setdefault(chave, {"email": chave, "nome": row["nome"], "operacional_ids": []})
        pessoa["operacional_ids"].append(row["id"])
    return list(por_chave.values())
```

por:

```python
def listar_pessoas_ativas_por_projeto(client) -> dict[str, dict]:
    """Agrupa operacionais ativos por projeto e, dentro de cada projeto, por
    e-mail — o ranking passa a ser por projeto, não mais cross-projeto
    (decisão do usuário, 2026-09-23: "eu quero que o ranking seja dividido
    por projeto, nao geral"). Retorna {projeto_id: {"projeto_nome": str,
    "pessoas": [...]}}. Sem e-mail, cada linha vira sua própria pessoa (mesmo
    racional da função anterior)."""
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
    projetos_rows = client.table("projects").select("id, name").in_("id", projeto_ids).execute().data or []
    nomes_projeto = {p["id"]: p["name"] for p in projetos_rows}

    por_projeto: dict[str, dict] = {}
    for row in rows:
        pid = row["project_id"]
        projeto = por_projeto.setdefault(pid, {"projeto_nome": nomes_projeto.get(pid, "Projeto"), "pessoas": {}})
        chave = row.get("email") or row["id"]
        pessoa = projeto["pessoas"].setdefault(chave, {"email": chave, "nome": row["nome"], "operacional_ids": []})
        pessoa["operacional_ids"].append(row["id"])

    return {
        pid: {"projeto_nome": info["projeto_nome"], "pessoas": list(info["pessoas"].values())}
        for pid, info in por_projeto.items()
    }
```

- [ ] **Step 4: Reescrever `routers/performance.py`**

Troque o arquivo inteiro:

```python
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import PerformanceResponse
from services.audit import registrar_auditoria
from services.auth import get_current_pessoa, require_role
from services.performance import listar_pessoas_ativas, calcular_ranking_pessoa
from services.supabase_client import get_client

router = APIRouter(tags=["performance"])


@router.get("/performance", response_model=PerformanceResponse, dependencies=[Depends(require_role("lider"))])
async def performance(pessoa: dict = Depends(get_current_pessoa)):
    registrar_auditoria(pessoa, "/performance", "acesso")
    client = get_client()

    pesos_rows = client.table("pesos_arquetipo").select("*").execute().data or []
    pesos_por_arquetipo = {r["arquetipo"]: r for r in pesos_rows}
    if not pesos_por_arquetipo:
        raise HTTPException(status_code=500, detail="pesos_arquetipo não configurado")

    janelas: dict[str, list[dict]] = {"sprint": [], "quinzenal": [], "mensal": []}
    for pessoa_ranking in listar_pessoas_ativas(client):
        ranking = calcular_ranking_pessoa(client, pessoa_ranking, pesos_por_arquetipo)
        for nome_janela, dados in ranking.items():
            if dados is None or dados.get("score_final") is None:
                continue
            janelas[nome_janela].append({
                "email": pessoa_ranking["email"],
                "nome": pessoa_ranking["nome"],
                **dados,
            })

    for nome_janela in janelas:
        janelas[nome_janela].sort(key=lambda r: r["score_final"], reverse=True)

    return janelas
```

por:

```python
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import PerformanceResponse
from services.audit import registrar_auditoria
from services.auth import get_current_pessoa, require_role
from services.performance import listar_pessoas_ativas_por_projeto, calcular_ranking_pessoa
from services.supabase_client import get_client

router = APIRouter(tags=["performance"])


@router.get("/performance", response_model=PerformanceResponse, dependencies=[Depends(require_role("lider"))])
async def performance(pessoa: dict = Depends(get_current_pessoa)):
    registrar_auditoria(pessoa, "/performance", "acesso")
    client = get_client()

    pesos_rows = client.table("pesos_arquetipo").select("*").execute().data or []
    pesos_por_arquetipo = {r["arquetipo"]: r for r in pesos_rows}
    if not pesos_por_arquetipo:
        raise HTTPException(status_code=500, detail="pesos_arquetipo não configurado")

    projetos_resultado = []
    for projeto_id, info in listar_pessoas_ativas_por_projeto(client).items():
        janelas: dict[str, list[dict]] = {"sprint": [], "quinzenal": [], "mensal": []}
        for pessoa_ranking in info["pessoas"]:
            ranking = calcular_ranking_pessoa(client, pessoa_ranking, pesos_por_arquetipo)
            for nome_janela, dados in ranking.items():
                if dados is None or dados.get("score_final") is None:
                    continue
                janelas[nome_janela].append({
                    "email": pessoa_ranking["email"],
                    "nome": pessoa_ranking["nome"],
                    **dados,
                })
        for nome_janela in janelas:
            janelas[nome_janela].sort(key=lambda r: r["score_final"], reverse=True)
        if any(janelas.values()):
            projetos_resultado.append({
                "projeto_id": projeto_id,
                "projeto_nome": info["projeto_nome"],
                **janelas,
            })

    projetos_resultado.sort(key=lambda p: p["projeto_nome"])
    return {"projetos": projetos_resultado}
```

- [ ] **Step 5: Reestruturar `PerformanceResponse` em `models/schemas.py`**

Troque:

```python
class PerformanceResponse(BaseModel):
    sprint: list[PerformanceOperacionalResponse] = []
    quinzenal: list[PerformanceOperacionalResponse] = []
    mensal: list[PerformanceOperacionalResponse] = []
```

por:

```python
class PerformanceProjetoResponse(BaseModel):
    projeto_id: str
    projeto_nome: str
    sprint: list[PerformanceOperacionalResponse] = []
    quinzenal: list[PerformanceOperacionalResponse] = []
    mensal: list[PerformanceOperacionalResponse] = []


class PerformanceResponse(BaseModel):
    projetos: list[PerformanceProjetoResponse] = []
```

- [ ] **Step 6: Atualizar `test_performance_endpoint.py`**

Troque a fixture de operacionais e projetos em `test_ranking_ordenado_por_score_desc` (adiciona `project_id`/`name`) e a asserção do body:

```python
def test_ranking_ordenado_por_score_desc(monkeypatch):
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True},
            {"id": "op-2", "nome": "Bia", "email": "bia@citi.com", "ativo": True},
        ],
        pontuacao=[
            dict(_LINHA, operacional_id="op-1", entrega_pontos_concluidos=10, entrega_pontos_alocados=10),
            dict(_LINHA, operacional_id="op-2", entrega_pontos_concluidos=2, entrega_pontos_alocados=10),
        ],
        projetos=[{"id": "proj-1", "arquetipo": "padrao"}],
    )
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/performance")

    assert resp.status_code == 200
    body = resp.json()
    assert [p["nome"] for p in body["sprint"]] == ["Ana", "Bia"]
```

por:

```python
def test_ranking_ordenado_por_score_desc(monkeypatch):
    client = _mock_client(
        operacionais=[
            {"id": "op-1", "nome": "Ana", "email": "ana@citi.com", "ativo": True, "project_id": "proj-1"},
            {"id": "op-2", "nome": "Bia", "email": "bia@citi.com", "ativo": True, "project_id": "proj-1"},
        ],
        pontuacao=[
            dict(_LINHA, operacional_id="op-1", entrega_pontos_concluidos=10, entrega_pontos_alocados=10),
            dict(_LINHA, operacional_id="op-2", entrega_pontos_concluidos=2, entrega_pontos_alocados=10),
        ],
        projetos=[{"id": "proj-1", "arquetipo": "padrao", "name": "Projeto 1"}],
    )
    tc = _client_as(monkeypatch, client, "lider")

    resp = tc.get("/performance")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["projetos"]) == 1
    assert body["projetos"][0]["projeto_id"] == "proj-1"
    assert body["projetos"][0]["projeto_nome"] == "Projeto 1"
    assert [p["nome"] for p in body["projetos"][0]["sprint"]] == ["Ana", "Bia"]
```

- [ ] **Step 7: Rodar os testes de novo e confirmar que passam**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_performance_ranking.py tests/test_performance_endpoint.py -v`
Expected: PASS em tudo.

- [ ] **Step 8: Commit**

```bash
git add docudata-backend/services/performance.py docudata-backend/routers/performance.py docudata-backend/models/schemas.py docudata-backend/tests/test_performance_ranking.py docudata-backend/tests/test_performance_endpoint.py
git commit -m "feat(performance): ranking passa a ser por projeto, não mais cross-projeto"
```

---

### Task 8: Ajustes cosméticos em comentários/nomes de teste que ainda citam "evolução"

**Files:**
- Modify: `docudata-backend/services/pontuacao.py:216-221` (comentário)
- Modify: `docudata-backend/tests/test_pontuacao_fechamento.py` (comentário + rename de um teste)

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: nenhuma outra task consome isso — é limpeza final de referências textuais, exigida pelo Global Constraint de remoção completa.

`calcular_e_travar_pontuacao` (`services/pontuacao.py`) não muda de comportamento nesta task — `gerente_pergunta6 = aval["resposta_6"]` continua funcionando igual (agora só que `resposta_6` pode ser `None`). Só o comentário que hoje descreve isso como "fonte exclusiva da dimensão Evolução" precisa mudar, porque essa dimensão não existe mais.

- [ ] **Step 1: Atualizar o comentário em `services/pontuacao.py`**

Troque:

```python
            # A resposta 6 (evolução) fica FORA desta média de propósito: ela é a
            # fonte exclusiva da dimensão Evolução (gerente_pergunta6 abaixo).
            # Contá-la aqui também daria peso triplo a uma única pergunta —
            # revertido por decisão do Líder em 2026-09-07.
```

por:

```python
            # A resposta 6 fica FORA desta média de propósito. Historicamente
            # era a fonte exclusiva da dimensão Evolução (removida em
            # 2026-09-23) — o campo continua existindo por compat com dado
            # antigo, mas não alimenta mais nenhuma dimensão de score.
```

- [ ] **Step 2: Atualizar comentário e nome de teste em `test_pontuacao_fechamento.py`**

Troque o comentário em `test_calcula_entrega_qualidade_autonomia_gerente_para_task_simples`:

```python
    # Média das 6 perguntas: a resposta_6 (evolução) fica fora, é exclusiva de Evolução.
    assert linha["gerente_media"] == round((5 + 4 + 3 + 4 + 5 + 3) / 6, 2)
```

por:

```python
    # Média das seis perguntas do questionário; resposta_6 (campo legado, a
    # antiga pergunta de evolução) não entra nessa média.
    assert linha["gerente_media"] == round((5 + 4 + 3 + 4 + 5 + 3) / 6, 2)
```

Renomeie e atualize o comentário de `test_gerente_media_exclui_a_pergunta_de_evolucao`:

```python
def test_gerente_media_exclui_a_pergunta_de_evolucao(monkeypatch):
    aval = {
        "operacional_id": "op-1",
        "resposta_1": 5, "resposta_2": 5, "resposta_3": 5, "resposta_4": 5,
        "resposta_5": 5, "resposta_6": 0, "resposta_7": 5,
    }
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 1, "coluna_kanban": "em_andamento"}],
        avaliacoes=[aval],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    # resposta_6=0 NÃO derruba a média do gerente: ela vive só na dimensão
    # Evolução, via gerente_pergunta6 (decisão do Líder, 2026-09-07).
    assert linha["gerente_media"] == round((5 + 5 + 5 + 5 + 5 + 5) / 6, 2)
    assert linha["gerente_pergunta6"] == 0
```

por:

```python
def test_gerente_media_exclui_a_resposta_6(monkeypatch):
    aval = {
        "operacional_id": "op-1",
        "resposta_1": 5, "resposta_2": 5, "resposta_3": 5, "resposta_4": 5,
        "resposta_5": 5, "resposta_6": 0, "resposta_7": 5,
    }
    client = _mock_client(
        sprint=_SPRINT,
        tasks=[{"id": "task-1", "operacional_id": "op-1", "pontos": 1, "coluna_kanban": "em_andamento"}],
        avaliacoes=[aval],
    )

    resultado = calcular_e_travar_pontuacao(client, "sprint-1")

    linha = next(l for l in resultado if l["operacional_id"] == "op-1")
    # resposta_6=0 NÃO derruba a média do gerente — mesmo que alguém ainda
    # mande esse campo legado (via reaproveitar de uma avaliação antiga, por
    # exemplo), ele nunca entrou nessa média e continua não entrando.
    assert linha["gerente_media"] == round((5 + 5 + 5 + 5 + 5 + 5) / 6, 2)
    assert linha["gerente_pergunta6"] == 0
```

- [ ] **Step 3: Rodar a suíte de pontuação inteira**

Run: `cd docudata-backend && .venv/bin/python -m pytest tests/test_pontuacao_fechamento.py -v`
Expected: PASS em tudo (nenhuma lógica mudou, só texto).

- [ ] **Step 4: Commit**

```bash
git add docudata-backend/services/pontuacao.py docudata-backend/tests/test_pontuacao_fechamento.py
git commit -m "chore(pontuacao): atualiza comentários e nome de teste que citavam a dimensão Evolução removida"
```

---

### Task 9: Verificação final da Onda 1

**Files:** nenhum arquivo novo — só verificação.

- [ ] **Step 1: Rodar a suíte completa do backend**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q`
Expected: PASS em tudo (todos os arquivos de `tests/`, não só os tocados nesta onda).

- [ ] **Step 2: Grep de verificação — nenhuma referência solta a "evolução" ligada à dimensão de nota**

Run: `cd docudata-backend && grep -rni "evolu" --include="*.py" . | grep -v "\.venv\|__pycache__"`

Expected: as únicas ocorrências restantes devem ser (a) o comentário novo em `services/pontuacao.py` que MENCIONA a remoção histórica (linha do Step 1 da Task 8 — isso é esperado, é sobre a mudança, não sobre a dimensão viva) e (b) qualquer ocorrência do prefixo "devolu" (devolver, devolucao_penalidade — falso positivo do grep por causa da substring, não relacionado). Se aparecer qualquer outra ocorrência de "evolucao"/"evolução" fora desses dois casos, ela precisa ser resolvida antes de prosseguir pra Onda 2 — pare e trate como um achado desta task, não ignore.

- [ ] **Step 3: Confirmar com o usuário antes de avançar pra Onda 2**

Reporte quantos testes novos foram adicionados e o resultado da suíte completa e do grep. Lembre explicitamente o usuário de rodar o SQL da Task 1 em produção antes de testar qualquer coisa desta feature ao vivo — nenhuma task seguinte depende disso pra passar nos testes automatizados (que usam mocks), mas a feature real (inclusive a correção da avaliação que ele considerou injusta) só se aplica depois desse UPDATE rodar. Só prossiga pra Onda 2 depois de confirmação explícita.

---

## ONDA 2 — Frontend

### Task 10: `api.ts` — tipos e funções

**Files:**
- Modify: `docudata-frontend/app/lib/api.ts:312-346,713-724,1954-1977,2039-2052`

**Interfaces:**
- Produces: `AvaliacaoAnterior.resposta_6: number | null`; `AvaliacaoGerente.resposta_6: number | null`; `submitAvaliacao`'s param `resposta_6?: number`; `PerformanceOperacional` sem `evolucao`; `PerformanceResponse`/`PerformanceProjeto` aninhado; `SpiPorOperacionalDoProjeto` (renomeado, sem `evolucao`); `getSpiDoProjeto` (renomeado). Tasks 11, 12 e 13 consomem esses tipos/funções.

- [ ] **Step 1: Atualizar `AvaliacaoAnterior` e `AvaliacaoGerente`**

Troque (linhas 312-323):
```typescript
export interface AvaliacaoAnterior {
  avaliacao_id: string;
  project_name: string;
  criado_em: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number;
  resposta_7: number;
}
```
por:
```typescript
export interface AvaliacaoAnterior {
  avaliacao_id: string;
  project_name: string;
  criado_em: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number | null;
  resposta_7: number;
}
```

Troque (linhas 331-346):
```typescript
export interface AvaliacaoGerente {
  id: string;
  operacional_id: string;
  gerente_id: string;
  sprint_id: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number;
  resposta_7: number;
  reaproveitada_de: string | null;
  criado_em: string;
  editavel_ate: string;
}
```
por:
```typescript
export interface AvaliacaoGerente {
  id: string;
  operacional_id: string;
  gerente_id: string;
  sprint_id: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number | null;
  resposta_7: number;
  reaproveitada_de: string | null;
  criado_em: string;
  editavel_ate: string;
}
```

- [ ] **Step 2: Atualizar `submitAvaliacao`**

Troque (linhas 713-724):
```typescript
export async function submitAvaliacao(data: {
  operacional_id: string;
  sprint_id: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number;
  resposta_7: number;
  reaproveitada_de?: string;
}): Promise<AvaliacaoGerente> {
```
por:
```typescript
export async function submitAvaliacao(data: {
  operacional_id: string;
  sprint_id: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6?: number;
  resposta_7: number;
  reaproveitada_de?: string;
}): Promise<AvaliacaoGerente> {
```

(o corpo da função, que só monta `JSON.stringify(data)` e faz o POST, não muda.)

- [ ] **Step 3: Atualizar `PerformanceOperacional` e `PerformanceResponse`**

Troque (linhas 1954-1971):
```typescript
export interface PerformanceOperacional {
  email: string;
  nome: string;
  score_final: number;
  entrega?: number | null;
  gerente?: number | null;
  qualidade?: number | null;
  autonomia?: number | null;
  evolucao?: number | null;
  janela_parcial: boolean;
  arquetipo_usado: string;
}

export interface PerformanceResponse {
  sprint: PerformanceOperacional[];
  quinzenal: PerformanceOperacional[];
  mensal: PerformanceOperacional[];
}
```
por:
```typescript
export interface PerformanceOperacional {
  email: string;
  nome: string;
  score_final: number;
  entrega?: number | null;
  gerente?: number | null;
  qualidade?: number | null;
  autonomia?: number | null;
  janela_parcial: boolean;
  arquetipo_usado: string;
}

export interface PerformanceProjeto {
  projeto_id: string;
  projeto_nome: string;
  sprint: PerformanceOperacional[];
  quinzenal: PerformanceOperacional[];
  mensal: PerformanceOperacional[];
}

export interface PerformanceResponse {
  projetos: PerformanceProjeto[];
}
```

(`getPerformance()`, logo abaixo, não precisa mudar — só busca e devolve o JSON; o novo formato já é o que a API retorna a partir da Task 7 do backend.)

- [ ] **Step 4: Renomear `SpiEvolucaoOperacional`/`getSpiEvolucaoProjeto`**

Troque (linhas 2037-2052):
```typescript
// SPI travado + Evolução por operacional do projeto (Líder e Gerente)

export interface SpiEvolucaoOperacional {
  operacional_id: string;
  nome: string;
  spi: number | null;
  evolucao: number | null;
  sprints_avaliadas: number;
  pontos_penalizados: number;
}

export async function getSpiEvolucaoProjeto(projectId: string): Promise<SpiEvolucaoOperacional[]> {
  const res = await apiFetch(`${API}/projects/${projectId}/spi-evolucao`);
  if (!res.ok) throw new Error("Erro ao buscar SPI e evolução por operacional");
  return res.json();
}
```
por:
```typescript
// SPI travado por operacional do projeto (Líder e Gerente)

export interface SpiPorOperacionalDoProjeto {
  operacional_id: string;
  nome: string;
  spi: number | null;
  sprints_avaliadas: number;
  pontos_penalizados: number;
}

export async function getSpiDoProjeto(projectId: string): Promise<SpiPorOperacionalDoProjeto[]> {
  const res = await apiFetch(`${API}/projects/${projectId}/spi`);
  if (!res.ok) throw new Error("Erro ao buscar SPI por operacional");
  return res.json();
}
```

- [ ] **Step 5: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: erros nos arquivos que ainda usam `PerformanceResponse` no formato antigo, `SpiEvolucaoOperacional`/`getSpiEvolucaoProjeto`, e o payload de 7 respostas em `AvaliacaoSemanalModal.tsx`/`performance/page.tsx`/`MetricasTab.tsx` — esses são esperados até as Tasks 11-13. Confirme que os erros são exatamente sobre esses símbolos e não algo inesperado.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/lib/api.ts
git commit -m "feat(api): resposta_6 opcional, remove evolucao, PerformanceResponse por projeto, spi renomeado"
```

---

### Task 11: `AvaliacaoSemanalModal.tsx` — questionário de 6 perguntas

**Files:**
- Modify: `docudata-frontend/app/components/AvaliacaoSemanalModal.tsx`

**Interfaces:**
- Consumes: `submitAvaliacao` (Task 10, `resposta_6` opcional).
- Produces: nenhuma outra task consome isso.

- [ ] **Step 1: Remover a pergunta de evolução e ajustar o tipo `Respostas`**

Troque:
```typescript
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
por:
```typescript
function perguntas(modoTrabalho: "ATRIBUICAO" | "PULL"): string[] {
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
```

Troque:
```typescript
type Respostas = [number, number, number, number, number, number, number];
const RESPOSTAS_VAZIAS: Respostas = [-1, -1, -1, -1, -1, -1, -1];
```
por:
```typescript
type Respostas = [number, number, number, number, number, number];
const RESPOSTAS_VAZIAS: Respostas = [-1, -1, -1, -1, -1, -1];
```

- [ ] **Step 2: Ajustar `reaproveitar()`**

Troque:
```typescript
  function reaproveitar(p: PendenciaAvaliacao) {
    if (!p.ultima_avaliacao_outro_projeto) return;
    const a = p.ultima_avaliacao_outro_projeto;
    setRespostas([a.resposta_1, a.resposta_2, a.resposta_3, a.resposta_4, a.resposta_5, a.resposta_6, a.resposta_7]);
    setReaproveitadaDe(a.avaliacao_id);
  }
```
por:
```typescript
  function reaproveitar(p: PendenciaAvaliacao) {
    if (!p.ultima_avaliacao_outro_projeto) return;
    const a = p.ultima_avaliacao_outro_projeto;
    setRespostas([a.resposta_1, a.resposta_2, a.resposta_3, a.resposta_4, a.resposta_5, a.resposta_7]);
    setReaproveitadaDe(a.avaliacao_id);
  }
```

- [ ] **Step 3: Ajustar `salvar()`**

Troque:
```typescript
  async function salvar() {
    if (!avaliando || respostas.includes(-1)) {
      setErr("Responda todas as 7 perguntas antes de salvar.");
      return;
    }
    setSaving(true);
    setErr("");
    try {
      await submitAvaliacao({
        operacional_id: avaliando.operacional_id,
        sprint_id: sprintId,
        resposta_1: respostas[0],
        resposta_2: respostas[1],
        resposta_3: respostas[2],
        resposta_4: respostas[3],
        resposta_5: respostas[4],
        resposta_6: respostas[5],
        resposta_7: respostas[6],
        reaproveitada_de: reaproveitadaDe,
      });
      setAvaliando(null);
      await carregarPendencias();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao salvar avaliação");
    } finally {
      setSaving(false);
    }
  }
```
por:
```typescript
  async function salvar() {
    if (!avaliando || respostas.includes(-1)) {
      setErr("Responda todas as 6 perguntas antes de salvar.");
      return;
    }
    setSaving(true);
    setErr("");
    try {
      await submitAvaliacao({
        operacional_id: avaliando.operacional_id,
        sprint_id: sprintId,
        resposta_1: respostas[0],
        resposta_2: respostas[1],
        resposta_3: respostas[2],
        resposta_4: respostas[3],
        resposta_5: respostas[4],
        resposta_7: respostas[5],
        reaproveitada_de: reaproveitadaDe,
      });
      setAvaliando(null);
      await carregarPendencias();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao salvar avaliação");
    } finally {
      setSaving(false);
    }
  }
```

Note que o JSX que renderiza `perguntas(modoTrabalho).map((pergunta, i) => ...)` (mais abaixo no arquivo) não precisa de nenhuma mudança — ele já itera sobre o array de perguntas, que agora tem 6 itens em vez de 7, e usa `respostas[i]`/`setRespostas` genericamente por índice.

- [ ] **Step 4: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: sem erros novos neste arquivo.

- [ ] **Step 5: Commit**

```bash
git add docudata-frontend/app/components/AvaliacaoSemanalModal.tsx
git commit -m "feat(avaliacoes): questionário semanal passa a ter 6 perguntas — remove a pergunta de evolução"
```

---

### Task 12: `MetricasTab.tsx` — remove a coluna Evolução

**Files:**
- Modify: `docudata-frontend/app/components/MetricasTab.tsx:26,34,77,127,142,151,173,334,347,353,357-364`

**Interfaces:**
- Consumes: `getSpiDoProjeto`, `SpiPorOperacionalDoProjeto` (Task 10).
- Produces: nenhuma outra task consome isso.

- [ ] **Step 1: Atualizar imports**

Troque (linhas 20-37, só as linhas relevantes):
```typescript
  getMetricasPerformanceOperacional,
  getSpiEvolucaoProjeto,
  getMetricasCycleTimeStats,
  getComparacaoModos,
  type SpiPoint,
  type ThroughputPoint,
  type CycleTimePoint,
  type CfdPoint,
  type PerformanceOperacionalPoint,
  type SpiEvolucaoOperacional,
  type CycleTimeStats,
  type ComparacaoModoPonto,
```
por:
```typescript
  getMetricasPerformanceOperacional,
  getSpiDoProjeto,
  getMetricasCycleTimeStats,
  getComparacaoModos,
  type SpiPoint,
  type ThroughputPoint,
  type CycleTimePoint,
  type CfdPoint,
  type PerformanceOperacionalPoint,
  type SpiPorOperacionalDoProjeto,
  type CycleTimeStats,
  type ComparacaoModoPonto,
```

- [ ] **Step 2: Renomear o estado e o fetch**

Troque:
```typescript
  const [spiEvolucao, setSpiEvolucao] = useState<SpiEvolucaoOperacional[]>([]);
```
por:
```typescript
  const [spiPorPessoa, setSpiPorPessoa] = useState<SpiPorOperacionalDoProjeto[]>([]);
```

Troque:
```typescript
      getSpiEvolucaoProjeto(projectId).catch(() => [] as SpiEvolucaoOperacional[]),
    ])
      .then(([s, t, ct, c, po, cts, se]) => {
        setSpi(s);
        setThroughput(t);
        setCycleTime(ct);
        setCfd(c);
        setPerfOp(po);
        setCtStats(cts);
        setSpiEvolucao(se);
        setErr("");
      })
```
por:
```typescript
      getSpiDoProjeto(projectId).catch(() => [] as SpiPorOperacionalDoProjeto[]),
    ])
      .then(([s, t, ct, c, po, cts, se]) => {
        setSpi(s);
        setThroughput(t);
        setCycleTime(ct);
        setCfd(c);
        setPerfOp(po);
        setCtStats(cts);
        setSpiPorPessoa(se);
        setErr("");
      })
```

- [ ] **Step 3: Atualizar o texto do tutorial e do tooltip**

Troque:
```typescript
    { title: "Entrega e evolução por pessoa", body: "Este é o dado consolidado: só entra o que já foi travado pelo fechamento da Avaliação Semanal, e é o mesmo que alimenta o acompanhamento de performance. Mostra a entrega de cada pessoa (já descontando o que foi penalizado por task travada), a nota de evolução dada por você, quantas sprints já foram avaliadas, e quantos pontos ela perdeu por atraso. Use na conversa de feedback." },
```
por:
```typescript
    { title: "Entrega por pessoa", body: "Este é o dado consolidado: só entra o que já foi travado pelo fechamento da Avaliação Semanal, e é o mesmo que alimenta o acompanhamento de performance. Mostra a entrega de cada pessoa (já descontando o que foi penalizado por task travada), quantas sprints já foram avaliadas, e quantos pontos ela perdeu por atraso. Use na conversa de feedback." },
```

Troque a entrada `spievol` no mapa de tooltips (por volta da linha 77):
```typescript
  spievol: "Só entra o que já foi travado pelo fechamento da Avaliação Semanal — é o mesmo dado que alimenta o acompanhamento de performance. SPI = pontos entregues sobre pontos que a pessoa pegou, já descontando o que foi penalizado por task parada tempo demais. Evolução = leitura do gerente sobre o quanto a pessoa cresceu, na escala 0 a 100.",
```
por:
```typescript
  spievol: "Só entra o que já foi travado pelo fechamento da Avaliação Semanal — é o mesmo dado que alimenta o acompanhamento de performance. SPI = pontos entregues sobre pontos que a pessoa pegou, já descontando o que foi penalizado por task parada tempo demais.",
```

(mantenha a chave `spievol` como está — é só um id interno, não texto visível; só o conteúdo muda.)

- [ ] **Step 4: Remover a coluna da tabela**

Troque:
```typescx
      {/* SPI travado e Evolução por operacional */}
      <div style={section}>
        <p style={title}>Entrega e evolução por pessoa <InfoTooltip id="spievol" /></p>
        <p style={subtitle}>
          Dado consolidado nos fechamentos de sprint. Use na conversa de feedback.
        </p>
        {spiEvolucao.length === 0 ? (
          <p style={empty}>Nenhum operacional cadastrado neste projeto.</p>
        ) : (
          <div style={{ overflowX: "auto", marginTop: 12 }}>
            <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={thSt}>Pessoa</th>
                  <th style={thSt}>Entrega</th>
                  <th style={thSt}>Evolução</th>
                  <th style={thSt}>Sprints avaliadas</th>
                  <th style={thSt}>Pontos perdidos por atraso</th>
                </tr>
              </thead>
              <tbody>
                {spiEvolucao.map((op) => (
                  <tr key={op.operacional_id}>
                    <td style={tdSt}>{op.nome}</td>
                    <td
                      style={{ ...tdSt, fontWeight: 700, color: op.spi === null ? "#94a3b8" : spiColor(op.spi / 100) }}
                      title={op.spi === null && op.sprints_avaliadas > 0 ? "Sem task alocada nesta sprint — score calculado com o restante das dimensões (avaliação do gerente, evolução, autonomia)" : undefined}
                    >
                      {op.spi === null ? "—" : op.spi}
                    </td>
                    <td style={{ ...tdSt, fontWeight: 700, color: op.evolucao === null ? "#94a3b8" : "#0f172a" }}>
                      {op.evolucao === null ? "—" : op.evolucao}
                    </td>
                    <td style={tdSt}>{op.sprints_avaliadas}</td>
                    <td style={{ ...tdSt, color: op.pontos_penalizados > 0 ? "#dc2626" : "#94a3b8" }}>
                      {op.pontos_penalizados || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
```
por:
```typescript
      {/* SPI travado por operacional */}
      <div style={section}>
        <p style={title}>Entrega por pessoa <InfoTooltip id="spievol" /></p>
        <p style={subtitle}>
          Dado consolidado nos fechamentos de sprint. Use na conversa de feedback.
        </p>
        {spiPorPessoa.length === 0 ? (
          <p style={empty}>Nenhum operacional cadastrado neste projeto.</p>
        ) : (
          <div style={{ overflowX: "auto", marginTop: 12 }}>
            <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={thSt}>Pessoa</th>
                  <th style={thSt}>Entrega</th>
                  <th style={thSt}>Sprints avaliadas</th>
                  <th style={thSt}>Pontos perdidos por atraso</th>
                </tr>
              </thead>
              <tbody>
                {spiPorPessoa.map((op) => (
                  <tr key={op.operacional_id}>
                    <td style={tdSt}>{op.nome}</td>
                    <td
                      style={{ ...tdSt, fontWeight: 700, color: op.spi === null ? "#94a3b8" : spiColor(op.spi / 100) }}
                      title={op.spi === null && op.sprints_avaliadas > 0 ? "Sem task alocada nesta sprint — score calculado com o restante das dimensões (avaliação do gerente, autonomia)" : undefined}
                    >
                      {op.spi === null ? "—" : op.spi}
                    </td>
                    <td style={tdSt}>{op.sprints_avaliadas}</td>
                    <td style={{ ...tdSt, color: op.pontos_penalizados > 0 ? "#dc2626" : "#94a3b8" }}>
                      {op.pontos_penalizados || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
```

(o bloco acima usa a marcação `typescx` só de propósito de destaque no plano — o arquivo real é `.tsx`, edite como TSX normal.)

- [ ] **Step 5: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: sem erros novos neste arquivo.

- [ ] **Step 6: Commit**

```bash
git add docudata-frontend/app/components/MetricasTab.tsx
git commit -m "feat(metricas): remove a coluna Evolução da tabela de entrega por pessoa"
```

---

### Task 13: `performance/page.tsx` — ranking por projeto

**Files:**
- Modify: `docudata-frontend/app/performance/page.tsx` (arquivo inteiro)

**Interfaces:**
- Consumes: `PerformanceResponse`/`PerformanceProjeto`/`PerformanceOperacional` (Task 10).
- Produces: nenhuma outra task consome isso — é o fim da cadeia de UI desta feature.

- [ ] **Step 1: Reescrever o arquivo inteiro**

Troque todo o conteúdo de `docudata-frontend/app/performance/page.tsx` por:

```typescript
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../components/AuthGuard";
import { getPerformance, type PerformanceResponse, type PerformanceOperacional } from "../lib/api";

const JANELA_LABEL: Record<string, string> = {
  sprint: "Última sprint",
  quinzenal: "Últimas 2 sprints",
  mensal: "Últimas 4 sprints",
};

const DIMENSAO_LABEL: Record<string, string> = {
  entrega: "Entrega",
  gerente: "Gerente",
  qualidade: "Qualidade",
  autonomia: "Autonomia",
};

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 12,
  padding: "20px 24px",
  marginBottom: 20,
};

const projetoHeading: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 800,
  color: "#111116",
  margin: "32px 0 12px",
};

export default function PerformancePage() {
  const auth = useAuth();
  const [janela, setJanela] = useState<"sprint" | "quinzenal" | "mensal">("sprint");
  const [dados, setDados] = useState<PerformanceResponse | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!auth || (auth.cargo !== "lider" && auth.cargo !== "owner")) return;
    getPerformance()
      .then(setDados)
      .catch((e: Error) => setErro(e.message));
  }, [auth]);

  if (auth && auth.cargo !== "lider" && auth.cargo !== "owner") {
    return (
      <main style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px" }}>
        <Link href="/" style={linkProjetosStyle}>← Projetos</Link>
        <p style={{ color: "#dc2626", marginTop: 20 }}>Acesso restrito a Líder e Owner.</p>
      </main>
    );
  }

  const projetos = dados?.projetos ?? [];

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "52px 24px" }}>
      <Link href="/" style={linkProjetosStyle}>← Projetos</Link>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#111116", margin: "20px 0 24px" }}>Performance</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {(["sprint", "quinzenal", "mensal"] as const).map((j) => (
          <button
            key={j}
            onClick={() => setJanela(j)}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: j === janela ? "2px solid #16a34a" : "1px solid #e8e8ed",
              background: j === janela ? "#f0fdf4" : "#fff",
              color: "#111116",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {JANELA_LABEL[j]}
          </button>
        ))}
      </div>

      {erro && <p style={{ color: "#dc2626" }}>{erro}</p>}

      {!dados && !erro && <p style={{ color: "#9696a0" }}>Carregando...</p>}

      {dados && projetos.length === 0 && (
        <p style={{ color: "#9696a0" }}>Nenhum projeto com dado suficiente nesta janela.</p>
      )}

      {projetos.map((projeto) => {
        const lista: PerformanceOperacional[] = projeto[janela];
        return (
          <section key={projeto.projeto_id}>
            <h2 style={projetoHeading}>{projeto.projeto_nome}</h2>

            {lista.length === 0 && (
              <p style={{ color: "#9696a0" }}>Nenhum operacional com dado suficiente nesta janela.</p>
            )}

            {lista.map((op, i) => (
              <div key={op.email} style={card}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <span style={{ fontSize: 16, fontWeight: 700, color: "#111116" }}>
                    {i + 1}. {op.nome}
                  </span>
                  <span style={{ fontSize: 20, fontWeight: 800, color: "#16a34a" }}>{op.score_final}</span>
                </div>
                {op.janela_parcial && (
                  <p style={{ fontSize: 12, color: "#d97706", marginBottom: 8 }}>Janela parcial — dado insuficiente ainda</p>
                )}
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                  {(["entrega", "gerente", "qualidade", "autonomia"] as const).map((dim) => (
                    <div key={dim}>
                      <p style={{ fontSize: 11, color: "#9696a0", textTransform: "uppercase", marginBottom: 2 }}>
                        {DIMENSAO_LABEL[dim]}
                      </p>
                      <p style={{ fontSize: 14, fontWeight: 600, color: "#111116" }}>{op[dim] ?? "—"}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </section>
        );
      })}
    </main>
  );
}

const linkProjetosStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#9696a0",
};
```

- [ ] **Step 2: Typecheck**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: limpo — este era o último arquivo com erro pendente de `PerformanceResponse`/`evolucao`.

- [ ] **Step 3: Commit**

```bash
git add docudata-frontend/app/performance/page.tsx
git commit -m "feat(performance): ranking exibido por projeto, uma seção por projeto"
```

---

### Task 14: Testes de frontend

**Files:**
- Modify: `docudata-frontend/tests/pendente-aprovacao.test.mjs` (ou novo arquivo `docudata-frontend/tests/avaliacao-peso-gerente-evolucao-ranking.test.mjs`)

**Interfaces:**
- Consumes: nada de outras tasks — só lê os arquivos-fonte já editados.

- [ ] **Step 1: Escrever o teste estrutural**

Crie `docudata-frontend/tests/avaliacao-peso-gerente-evolucao-ranking.test.mjs` (mesmo padrão de `readFileSync` + asserções de string usado em `pendente-aprovacao.test.mjs`):

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const MODAL = readFileSync(new URL("../app/components/AvaliacaoSemanalModal.tsx", import.meta.url), "utf-8");
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");
const METRICAS = readFileSync(new URL("../app/components/MetricasTab.tsx", import.meta.url), "utf-8");
const PERFORMANCE_PAGE = readFileSync(new URL("../app/performance/page.tsx", import.meta.url), "utf-8");

test("questionário semanal não pergunta mais sobre evolução", () => {
  assert.doesNotMatch(MODAL, /Evoluiu em relação a onde estava/);
  assert.match(MODAL, /Respostas = \[number, number, number, number, number, number\]/);
});

test("api.ts não expõe mais evolucao nem spi-evolucao", () => {
  assert.doesNotMatch(API, /evolucao/i);
  assert.doesNotMatch(API, /spi-evolucao/);
  assert.match(API, /export async function getSpiDoProjeto/);
  assert.match(API, /projetos: PerformanceProjeto\[\]/);
});

test("MetricasTab não mostra mais a coluna Evolução", () => {
  assert.doesNotMatch(METRICAS, />Evolução</);
  assert.match(METRICAS, /Entrega por pessoa/);
});

test("performance/page.tsx renderiza uma seção por projeto", () => {
  assert.match(PERFORMANCE_PAGE, /projeto\.projeto_nome/);
  assert.match(PERFORMANCE_PAGE, /projetos\.map/);
  assert.doesNotMatch(PERFORMANCE_PAGE, /evolucao/i);
});
```

- [ ] **Step 2: Rodar `npm test` e confirmar que passa**

Run: `cd docudata-frontend && npm test`
Expected: PASS em todos os testes (novos e os já existentes — nenhum arquivo anterior foi quebrado pelas Tasks 10-13).

- [ ] **Step 3: Rodar o typecheck de novo, por garantia**

Run: `cd docudata-frontend && npx tsc --noEmit`
Expected: limpo.

- [ ] **Step 4: Commit**

```bash
git add docudata-frontend/tests/avaliacao-peso-gerente-evolucao-ranking.test.mjs
git commit -m "test(avaliacoes): cobertura estrutural das mudanças de peso, evolução e ranking por projeto"
```

---

### Task 15: Verificação final da Onda 2

**Files:** nenhum arquivo novo — só verificação.

- [ ] **Step 1: Suíte completa do backend, de novo**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q`
Expected: PASS — confirma que nada na Onda 2 (só frontend) quebrou o backend.

- [ ] **Step 2: Typecheck e testes do frontend, juntos**

Run: `cd docudata-frontend && npx tsc --noEmit && npm test`
Expected: os dois limpos/verdes.

- [ ] **Step 3: Grep de verificação no frontend**

Run: `cd docudata-frontend && grep -rni "evolu" app/ | grep -v "\.next"`
Expected: nenhuma ocorrência (nem falso positivo de "devolu" — confira se aparecer algo).

- [ ] **Step 4: Relatar ao usuário**

Resuma o que foi verificado automaticamente (testes + typecheck + greps) nas Ondas 1 e 2. Confirme que a Onda 3 (documentação) é o próximo passo.

---

## ONDA 3 — Documentação

### Task 16: `docs/metodologia-performance.md` — pesos, evolução e ranking por projeto

**Files:**
- Modify: `docudata-backend/docs/metodologia-performance.md`

**Interfaces:**
- Consumes: nada de código — texto puro, mas os valores numéricos precisam bater com a Task 1 (pesos) e a estrutura da Task 7 (ranking por projeto).
- Produces: nenhuma outra task consome isso.

Este é um arquivo de 1256 linhas; a lista abaixo cobre cada trecho identificado nesta pesquisa. Aplique as substituições exatamente como descrito — se ao abrir o arquivo você encontrar uma seção adicional com "evolução" não listada aqui, resolva-a também antes de considerar a task concluída (o grep final do Step 2 vai flagrar qualquer uma que passar batido).

- [ ] **Step 1: Aplicar as edições**

**Índice (linha ~20):** troque `5. [As cinco dimensões](#5-as-cinco-dimensões)` por `5. [As quatro dimensões](#5-as-quatro-dimensões)`.

**§5 (linha ~165), cabeçalho:** troque `## 5. As cinco dimensões` por `## 5. As quatro dimensões`. O parágrafo logo abaixo ("Cada dimensão vira um número...") não muda — a frase "destrói qualquer leitura de evolução individual" ali usa "evolução" no sentido geral de crescimento pessoal, não como nome da dimensão removida; não mexa nessa frase.

**§5.2 Avaliação do Gerente (linha ~208-218):** troque:
```
A pergunta de evolução fica **fora** desta média de propósito: ela é a fonte
exclusiva da dimensão Evolução, e contá-la duas vezes daria peso desproporcional
a uma única pergunta.
```
por:
```
Isso é a média simples das seis perguntas do questionário — o questionário
não tem mais uma sétima pergunta de evolução (removida em 2026-09-23).
```

**§5.5 Evolução (linha ~296-305):** delete a seção inteira:
```
### 5.5 Evolução

**O que mede:** quanto a pessoa cresceu em relação a onde estava.

> **Evolução** = a pergunta de evolução do questionário, convertida da escala 0 a
> 5 para 0 a 100.

É a única dimensão que compara a pessoa com ela mesma, e não com um padrão
absoluto. É o que dá chance real a quem entrou mais júnior.

```

**§5.6 Bônus de task extra (linha ~306, renumerar):** troque `### 5.6 Bônus de task extra` por `### 5.5 Bônus de task extra`.

**§6.2 Os pesos (linha ~337-347):** troque a tabela:
```
| Dimensão | Projeto padrão | Consultoria ou discovery |
|---|---|---|
| Avaliação do Gerente | **35%** | **50%** |
| Entrega e Confiabilidade | **20%** | **20%** |
| Qualidade Técnica | **20%** | **10%** |
| Autonomia | **15%** | **12%** |
| Evolução | **10%** | **8%** |

Cada coluna soma 100%.
```
por:
```
| Dimensão | Projeto padrão | Consultoria ou discovery |
|---|---|---|
| Avaliação do Gerente | **50%** | **50%** |
| Entrega e Confiabilidade | **18%** | **24%** |
| Qualidade Técnica | **18%** | **12%** |
| Autonomia | **14%** | **14%** |

Cada coluna soma 100%. (Atualizado em 2026-09-23: a dimensão Evolução foi
removida e o peso do gerente subiu para 50% nos dois tipos de projeto — o
que sobrou de Entrega/Qualidade/Autonomia foi redistribuído mantendo a
proporção relativa que já existia entre as três.)
```

**§7, tabela das sete perguntas (linha ~370-383):** troque o título `## 7. O questionário de sete perguntas` por `## 7. O questionário de seis perguntas`, o texto "Todas as sete são obrigatórias" por "Todas as seis são obrigatórias", e a tabela:
```
| # | Pergunta | Âncora 0 | Âncora 5 |
|---|---|---|---|
| 1 | Entregou o que se comprometeu dentro do combinado nesta sprint? | quase nada do previsto | tudo no prazo |
| 2 | A qualidade da entrega precisou de pouca ou nenhuma correção? | refiz quase tudo | entrou limpo |
| 3 | A pessoa destravou sozinha antes de te escalar? | dependeu de mim o tempo todo | resolveu sozinha |
| 4 | A comunicação da entrega foi clara a ponto de você não precisar perguntar? | tive que decifrar | entendi de primeira |
| 5 | Ajudou, desbloqueou ou ensinou outro membro nesta sprint? | não interagiu | foi peça de apoio do squad |
| 6 | Evoluiu em relação a onde estava no começo do ciclo? | estagnou | salto claro |
| 7 | Trouxe algo além do que foi pedido? | fez o mínimo | antecipou problema ou propôs melhoria |
```
por:
```
| # | Pergunta | Âncora 0 | Âncora 5 |
|---|---|---|---|
| 1 | Entregou o que se comprometeu dentro do combinado nesta sprint? | quase nada do previsto | tudo no prazo |
| 2 | A qualidade da entrega precisou de pouca ou nenhuma correção? | refiz quase tudo | entrou limpo |
| 3 | A pessoa destravou sozinha antes de te escalar? | dependeu de mim o tempo todo | resolveu sozinha |
| 4 | A comunicação da entrega foi clara a ponto de você não precisar perguntar? | tive que decifrar | entendi de primeira |
| 5 | Ajudou, desbloqueou ou ensinou outro membro nesta sprint? | não interagiu | foi peça de apoio do squad |
| 6 | Trouxe algo além do que foi pedido? | fez o mínimo | antecipou problema ou propôs melhoria |
```

**§7.1 Para onde vai cada pergunta (linha ~385-406):** troque:
```
### 7.1 Para onde vai cada pergunta

| Pergunta | Alimenta | Peso no score, em projeto padrão |
|---|---|---|
| 1, 2, 4, 5, 7 | Avaliação do Gerente | cerca de 5,8% cada |
| 3 | Avaliação do Gerente **e** metade de Autonomia | cerca de 5,8% mais 7,5% |
| 6 | Evolução, sozinha | 10% |

A pergunta 6 não entra na média das outras seis: ela é a dimensão Evolução
inteira.

A pergunta 3 é a única que alimenta duas coisas, e de propósito. Ela entra na
média do gerente como qualquer outra, e ao mesmo tempo sustenta metade de
Autonomia nas semanas em que ninguém registrou bloqueio, que são a maioria.

A pergunta 5, sobre colaboração, vale por volta de 5,8% do score. É um sinal real,
mas não é uma dimensão própria. Se o acompanhamento mostrar queda de colaboração,
o caminho de correção é aumentar o peso da avaliação do gerente ou promover a
colaboração a dimensão separada.

Em projeto de consultoria todos esses pesos sobem, porque a avaliação do gerente
vale 50% em vez de 35%.
```
por:
```
### 7.1 Para onde vai cada pergunta

| Pergunta | Alimenta | Peso no score, em projeto padrão |
|---|---|---|
| 1, 2, 4, 5, 6 | Avaliação do Gerente | cerca de 8,3% cada |
| 3 | Avaliação do Gerente **e** metade de Autonomia | cerca de 8,3% mais 7% |

A pergunta 3 é a única que alimenta duas coisas, e de propósito. Ela entra na
média do gerente como qualquer outra, e ao mesmo tempo sustenta metade de
Autonomia nas semanas em que ninguém registrou bloqueio, que são a maioria.

A pergunta 5, sobre colaboração, vale por volta de 8,3% do score. É um sinal
real, mas não é uma dimensão própria. Se o acompanhamento mostrar queda de
colaboração, o caminho de correção é aumentar o peso da avaliação do gerente
ou promover a colaboração a dimensão separada.

Em consultoria e em projeto padrão a avaliação do gerente pesa igual, 50% —
a diferença entre os dois tipos de projeto está só na divisão do resto entre
Entrega, Qualidade e Autonomia (seção 6.2).
```

**§7.2 (linha ~408-417), item "Cuidado redobrado com a pergunta 3":** troque:
```
- **Cuidado redobrado com a pergunta 3.** Ela é a que mais pesa depois da 6, e na
  maioria das semanas é a única fonte de Autonomia. Responda pensando em quantas
  vezes você precisou entrar para destravar a pessoa, não na impressão geral.
```
por:
```
- **Cuidado redobrado com a pergunta 3.** Na maioria das semanas ela é a única
  fonte de Autonomia. Responda pensando em quantas vezes você precisou entrar
  para destravar a pessoa, não na impressão geral.
```

**§7.4 (linha ~427-435):** troque "preenche as sete notas a partir da última avaliação" por "preenche as seis notas a partir da última avaliação".

**§9.2 O que fica guardado (linha ~715-730):** remova a linha `| Nota de evolução | Pergunta 6 do questionário |` da tabela.

**§10.1 (linha ~800-818), renomear e reescrever por completo:** troque:
```
### 10.1 Uma pessoa é uma pessoa, mesmo em vários projetos

Cada projeto tem sua própria lista de operacionais. Quem trabalha em dois projetos
aparece nas duas listas.

**No ranking essas aparições viram uma pessoa só.** O sistema junta tudo pelo
**e-mail** cadastrado, calcula cada dimensão dentro de cada projeto e depois tira
a **média simples** entre os projetos. Quem está em dois projetos é avaliado pela
média dos dois, não pela soma nem pelo melhor deles.

A consequência prática é dura mas necessária: **se o e-mail estiver diferente ou
em branco nos dois cadastros, o sistema não tem como saber que é a mesma pessoa**,
e ela aparece duas vezes no ranking, com metade do histórico cada. Por isso, ao
adicionar um operacional que já existe em outro projeto, use o atalho **"Já
trabalha em outro projeto?"** no formulário: ele preenche nome, e-mail, papel e
usuário do GitHub a partir do cadastro que já existe, e evita o erro de digitação
que parte a pessoa em duas.

Operacional desativado sai do ranking na hora.
```
por:
```
### 10.1 O ranking é por projeto

Cada projeto tem sua própria lista de operacionais e seu próprio ranking.
Quem trabalha em dois projetos aparece **separadamente** em cada um, com a
nota calculada só com os dados daquele projeto — não existe mais nenhuma
média entre projetos (mudança de 2026-09-23; antes disso o sistema juntava
as aparições de uma pessoa pelo e-mail e tirava a média entre os projetos).

Dentro de um mesmo projeto, se a mesma pessoa tiver mais de um cadastro
`operacionais` (raro — normalmente é um cadastro por pessoa por projeto), o
sistema ainda junta essas linhas pelo **e-mail**, do jeito que sempre fez.
Cadastros sem e-mail nesse cenário raro viram entradas separadas dentro do
mesmo projeto — bem menos custoso do que era antes, já que hoje o e-mail só
importa dentro de um projeto, nunca mais entre projetos.

Operacional desativado sai do ranking na hora.
```

**§11.1 O caminho (linha ~848-869):** troque:
```
1. **Junta a pessoa.** Todas as aparições dela, em todos os projetos, viram uma
   pessoa só, casadas pelo e-mail.
2. **Monta a janela.** Pega as sprints fechadas mais recentes em que ela pegou
   pontos: 1, 2 ou 4, conforme a janela escolhida na tela.
3. **Calcula cada dimensão dentro de cada projeto.** As cinco fórmulas da seção 5,
   aplicadas só às sprints daquela janela, projeto por projeto.
4. **Tira a média entre projetos.** Se a janela cobre mais de um projeto, cada
   dimensão vira a média simples dos valores por projeto. Projeto onde a dimensão
   não existe é ignorado, e não entra como zero.
5. **Aplica os pesos.** Multiplica cada dimensão pelo peso dela e soma. Os
   pesos dependem do tipo de projeto (seção 6).
6. **Soma o bônus de task extra**, se houver, respeitando o teto de 5 pontos. O
   resultado é o score final, de 0 a 100.
7. **Ordena.** As pessoas são listadas da maior nota para a menor, dentro de cada
   janela.

A média entre projetos é simples, e não ponderada por volume: um projeto pequeno
pesa igual a um grande. Isso protege quem foi alocado parcialmente em algo pequeno
de ver aquele projeto diluído a zero, mas também significa que uma semana ruim num
projeto pequeno machuca tanto quanto num grande.
```
por:
```
1. **Escolhe o projeto.** O ranking é calculado um projeto de cada vez — não
   existe mais o passo de juntar as aparições de uma pessoa entre projetos
   (seção 10.1).
2. **Monta a janela.** Pega as sprints fechadas mais recentes daquele projeto
   em que a pessoa pegou pontos: 1, 2 ou 4, conforme a janela escolhida na
   tela.
3. **Calcula cada dimensão.** As quatro fórmulas da seção 5, aplicadas só às
   sprints daquela janela, dentro daquele projeto.
4. **Aplica os pesos.** Multiplica cada dimensão pelo peso dela e soma. Os
   pesos dependem do tipo de projeto (seção 6).
5. **Soma o bônus de task extra**, se houver, respeitando o teto de 5 pontos. O
   resultado é o score final, de 0 a 100.
6. **Ordena.** Dentro de cada projeto, as pessoas são listadas da maior nota
   para a menor, dentro de cada janela.
```

**§11.2 Um exemplo do começo ao fim (linha ~871-926):** troque a tabela "As cinco dimensões" e tudo que segue:
```
**As cinco dimensões:**

| Dimensão | Conta | Resultado |
|---|---|---|
| Entrega | (12 mais 10 menos 2) sobre (14 mais 10) | **83,33** |
| Avaliação do Gerente | média de 4,17 e 4,50, vezes 20 | **86,70** |
| Qualidade | retrabalho 90,00 e commits 80,00, meio a meio | **85,00** |
| Autonomia | bloqueios 75,00 e pergunta 3 em 90,00, meio a meio | **82,50** |
| Evolução | média de 4 e 5, vezes 20 | **90,00** |

O retrabalho saiu de 1 task reaberta em 10 concluídas, que dá 90. A nota de
commits foi a média de 7,5 e 8,5, que dá 8,0, convertida para 80. O sinal de
bloqueio foi 3 resolvidos sozinha em 4 bloqueios, que dá 75.

**O score final:**

| Dimensão | Nota | Peso | Contribuição |
|---|---|---|---|
| Avaliação do Gerente | 86,70 | 35% | 30,35 |
| Entrega | 83,33 | 20% | 16,67 |
| Qualidade | 85,00 | 20% | 17,00 |
| Autonomia | 82,50 | 15% | 12,38 |
| Evolução | 90,00 | 10% | 9,00 |
| | | | **85,39** |

Três coisas para reparar neste exemplo:

**O atraso custou caro.** Sem os 2 pontos descontados na sprint 13, a Entrega
teria sido 91,67 e o score subiria para 87,06. Uma task entregue fora do prazo
custou 1,67 ponto de score.

**A task extra teria compensado.** Se a Maria tivesse pedido e concluído uma task
extra de 3 pontos, o bônus levaria o score de 85,39 para **88,39**.

**Em consultoria a mesma pessoa daria 85,62.** Com os pesos de consultoria, a
leitura do gerente (86,70) puxa mais e a Qualidade pesa menos. A diferença é
pequena aqui porque as notas dela são parecidas entre si; quanto mais desigual o
perfil da pessoa, mais os dois tipos de projeto divergem.
```
por:
```
**As quatro dimensões:**

| Dimensão | Conta | Resultado |
|---|---|---|
| Entrega | (12 mais 10 menos 2) sobre (14 mais 10) | **83,33** |
| Avaliação do Gerente | média de 4,17 e 4,50, vezes 20 | **86,70** |
| Qualidade | retrabalho 90,00 e commits 80,00, meio a meio | **85,00** |
| Autonomia | bloqueios 75,00 e pergunta 3 em 90,00, meio a meio | **82,50** |

O retrabalho saiu de 1 task reaberta em 10 concluídas, que dá 90. A nota de
commits foi a média de 7,5 e 8,5, que dá 8,0, convertida para 80. O sinal de
bloqueio foi 3 resolvidos sozinha em 4 bloqueios, que dá 75.

**O score final:**

| Dimensão | Nota | Peso | Contribuição |
|---|---|---|---|
| Avaliação do Gerente | 86,70 | 50% | 43,35 |
| Entrega | 83,33 | 18% | 15,00 |
| Qualidade | 85,00 | 18% | 15,30 |
| Autonomia | 82,50 | 14% | 11,55 |
| | | | **85,20** |

Três coisas para reparar neste exemplo:

**O atraso custou caro.** Sem os 2 pontos descontados na sprint 13, a Entrega
teria sido 91,67 e o score subiria para 86,70. Uma task entregue fora do prazo
custou 1,50 ponto de score.

**A task extra teria compensado.** Se a Maria tivesse pedido e concluído uma task
extra de 3 pontos, o bônus levaria o score de 85,20 para **88,20**.

**Em consultoria a mesma pessoa daria 85,10.** Com os pesos de consultoria a
diferença ficou pequena: a avaliação do gerente pesa igual nos dois tipos de
projeto agora (50%), e Autonomia também (14%) — a única diferença real está em
como Entrega e Qualidade dividem o resto (seção 6.2).
```

**§11.3 O que acontece quando falta uma dimensão (linha ~928-947):** troque:
```
Voltando à Maria: se ela não tivesse sido avaliada pelo gerente em nenhuma das duas
sprints, sumiriam a Avaliação do Gerente e a Evolução, e a Autonomia cairia para
75,00, porque perderia a fonte da pergunta 3 e sobraria só o sinal de bloqueio.
Restariam Entrega, Qualidade e Autonomia, que somam 55% de peso. A conta seria
16,67 mais 17,00 mais 11,25, dividido por 0,55, dando **81,67**.
```
por:
```
Voltando à Maria: se ela não tivesse sido avaliada pelo gerente em nenhuma das duas
sprints, sumiria a Avaliação do Gerente, e a Autonomia cairia para 75,00, porque
perderia a fonte da pergunta 3 e sobraria só o sinal de bloqueio. Restariam
Entrega, Qualidade e Autonomia, que somam 50% de peso. A conta seria 15,00 mais
15,30 mais 10,50, dividido por 0,50, dando **81,60**.
```

**§13.1 Quem vê o quê (linha ~1005-1016):** troque `| Entrega consolidada e evolução por pessoa | ✅ | ✅ | ✅ | ❌ |` por `| Entrega consolidada por pessoa | ✅ | ✅ | ✅ | ❌ |`.

**§13.1, parágrafo logo abaixo (linha ~1023-1032):** troque:
```
O gerente **não** enxerga o score final nem a posição de ninguém no ranking. Ele
produz o insumo, que são as sete notas, e enxerga a entrega consolidada e a
evolução de cada pessoa do projeto dele, que é o que sustenta a conversa de
feedback. O resultado do cálculo é do Líder.

**Onde o gerente vê isso:** aba **Métricas** do projeto, no bloco "Entrega e
evolução por pessoa". Ele mostra, para cada operacional, a entrega consolidada dos
fechamentos, a nota de evolução, quantas sprints já foram avaliadas e quantos
pontos a pessoa perdeu por atraso. É o mesmo dado que alimenta o ranking, sem
mostrar o ranking.
```
por:
```
O gerente **não** enxerga o score final nem a posição de ninguém no ranking. Ele
produz o insumo, que são as seis notas, e enxerga a entrega consolidada de cada
pessoa do projeto dele, que é o que sustenta a conversa de feedback. O resultado
do cálculo é do Líder.

**Onde o gerente vê isso:** aba **Métricas** do projeto, no bloco "Entrega por
pessoa". Ele mostra, para cada operacional, a entrega consolidada dos
fechamentos, quantas sprints já foram avaliadas e quantos pontos a pessoa perdeu
por atraso. É o mesmo dado que alimenta o ranking, sem mostrar o ranking.
```

**§13.3 O que divulgar (linha ~1043-1058):** troque:
```
- Que a contribuição é acompanhada em entrega, qualidade, autonomia, ajuda ao time
  e evolução.
```
por:
```
- Que a contribuição é acompanhada em entrega, qualidade, autonomia e ajuda ao
  time.
```

E troque "traz as cinco direções" por "traz as quatro direções" no mesmo bloco (procure "cinco direções" na §13.3).

**§14 Manual do gerente (linha ~1124):** troque "responda as **sete perguntas**" por "responda as **seis perguntas**".

**§15.2 Pessoa em dois ou mais projetos (linha ~1184-1188):** troque:
```
### 15.2 Pessoa em dois ou mais projetos

Cada projeto gera seu próprio registro por sprint. A janela junta as sprints mais
recentes independentemente do projeto, e cada dimensão vira a média simples entre
os projetos. Ver seção 10.1.
```
por:
```
### 15.2 Pessoa em dois ou mais projetos

Cada projeto gera seu próprio registro por sprint e seu próprio ranking. A pessoa
aparece separadamente em cada projeto em que atua, com a nota calculada só com os
dados daquele projeto — sem nenhuma média entre projetos. Ver seção 10.1.
```

**§15.3 Pessoa cadastrada sem e-mail (linha ~1190-1193):** troque:
```
### 15.3 Pessoa cadastrada sem e-mail

Vira duas pessoas diferentes no ranking, uma por projeto, cada uma com metade do
histórico. Não aparece nenhum aviso. É o erro de cadastro mais caro do sistema.
```
por:
```
### 15.3 Pessoa cadastrada sem e-mail

Como o ranking já é por projeto (seção 10.1), o e-mail só importa quando a mesma
pessoa tem mais de um cadastro `operacionais` **dentro do mesmo projeto** — cenário
raro. Nesse caso, cadastros sem e-mail em comum viram entradas separadas dentro
daquele projeto em vez de se juntarem. Não há mais o risco antigo de dividir o
histórico de alguém entre dois projetos diferentes por falta de e-mail.
```

- [ ] **Step 2: Grep de verificação no arquivo**

Run: `cd docudata-backend && grep -ni "evolu" docs/metodologia-performance.md`
Expected: nenhuma ocorrência.

- [ ] **Step 3: Commit**

```bash
git add docudata-backend/docs/metodologia-performance.md
git commit -m "docs(performance): atualiza metodologia — peso do gerente 50%, remove Evolução, ranking por projeto"
```

---

### Task 17: `docs/acompanhamento-publico.md` e `docs/guia-do-sistema.md`

**Files:**
- Modify: `docudata-backend/docs/acompanhamento-publico.md:26-47,116-138`
- Modify: `docudata-backend/docs/guia-do-sistema.md:172-173`

**Interfaces:**
- Consumes: nada de código.
- Produces: nenhuma outra task consome isso.

- [ ] **Step 1: `acompanhamento-publico.md` — "O que conta" perde o item Evolução**

Troque:
```
## O que conta

Cinco coisas, olhadas juntas e não isoladamente:

**Entrega.** Você fez o que se comprometeu a fazer na sprint. O que importa é a
proporção: entregar tudo o que você pegou vale mais do que pegar muito e entregar
metade. Pegar menos e cumprir não te prejudica.

**Qualidade.** O trabalho precisou de pouca correção e seguiu o padrão. Entra o
retrabalho (quanto do que foi dado como pronto voltou) e, em projetos com código,
uma leitura automática dos seus commits, que olha clareza, documentação e boas
práticas.

**Autonomia.** Quanto você destrava sozinho antes de escalar. Registrar um
bloqueio não é confessar fraqueza: é informação de gestão que o time precisa. O
que conta a favor é resolver.

**Ajuda ao time.** Desbloquear, ensinar e apoiar outra pessoa conta a favor, não
contra. Isso é medido de propósito, porque um time onde ninguém ajuda entrega
menos.

**Evolução.** Quanto você cresceu em relação a onde você estava no começo do
ciclo. Esta é a única coisa que compara você com você mesmo, e não com os outros.
É o que dá chance real a quem entrou mais júnior.
```
por:
```
## O que conta

Quatro coisas, olhadas juntas e não isoladamente:

**Entrega.** Você fez o que se comprometeu a fazer na sprint. O que importa é a
proporção: entregar tudo o que você pegou vale mais do que pegar muito e entregar
metade. Pegar menos e cumprir não te prejudica.

**Qualidade.** O trabalho precisou de pouca correção e seguiu o padrão. Entra o
retrabalho (quanto do que foi dado como pronto voltou) e, em projetos com código,
uma leitura automática dos seus commits, que olha clareza, documentação e boas
práticas.

**Autonomia.** Quanto você destrava sozinho antes de escalar. Registrar um
bloqueio não é confessar fraqueza: é informação de gestão que o time precisa. O
que conta a favor é resolver.

**Ajuda ao time.** Desbloquear, ensinar e apoiar outra pessoa conta a favor, não
contra. Isso é medido de propósito, porque um time onde ninguém ajuda entrega
menos.
```

- [ ] **Step 2: `acompanhamento-publico.md` — os outros dois trechos**

Troque `As cinco direções acima são o que` por `As quatro direções acima são o que`.

Troque:
```
Pergunte ao seu gerente. Ele enxerga sua entrega consolidada e sua evolução, e a
conversa de feedback existe para isso.
```
por:
```
Pergunte ao seu gerente. Ele enxerga sua entrega consolidada, e a conversa de
feedback existe para isso.
```

Troque:
```
O que não vai mudar é a direção: entregar com qualidade, ajudar o time, ser
autônomo e evoluir.
```
por:
```
O que não vai mudar é a direção: entregar com qualidade, ajudar o time e ser
autônomo.
```

- [ ] **Step 3: `guia-do-sistema.md`**

Troque:
```
- **Entrega e evolução por pessoa**: o dado consolidado dos fechamentos de sprint.
  É o que sustenta a conversa de feedback.
```
por:
```
- **Entrega por pessoa**: o dado consolidado dos fechamentos de sprint. É o que
  sustenta a conversa de feedback.
```

- [ ] **Step 4: Grep de verificação nos dois arquivos**

Run: `cd docudata-backend && grep -ni "evolu" docs/acompanhamento-publico.md docs/guia-do-sistema.md`
Expected: nenhuma ocorrência.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/docs/acompanhamento-publico.md docudata-backend/docs/guia-do-sistema.md
git commit -m "docs(performance): atualiza guia público e guia do sistema — remove referências à Evolução"
```

---

### Task 18: Verificação final completa

**Files:** nenhum arquivo novo — só verificação.

- [x] **Step 1: Suíte completa do backend**

Run: `cd docudata-backend && .venv/bin/python -m pytest -q`
Expected: PASS.

- [x] **Step 2: Typecheck e testes do frontend**

Run: `cd docudata-frontend && npx tsc --noEmit && npm test`
Expected: os dois limpos/verdes.

- [x] **Step 3: Grep final de verificação em todo o repositório (código e docs vivos)**

Run:
```bash
cd docudata-backend && grep -rni "evolu" --include="*.py" --include="*.md" . | grep -v "\.venv\|__pycache__\|docs/superpowers\|\.planning"
cd ../docudata-frontend && grep -rni "evolu" app/ | grep -v "\.next"
```
Expected: nenhuma ocorrência relacionada à dimensão de nota removida (falsos positivos de "devolu"/"devolução" são esperados e não contam).

- [ ] **Step 4: Checklist manual (reportar ao usuário, não pode ser verificado automaticamente sem ambiente real)**

Peça pro usuário, depois de rodar o SQL da Task 1 em produção:
1. Abrir `/performance` e confirmar que o ranking aparece dividido em seções por projeto, cada uma com suas próprias 3 janelas.
2. Abrir a Avaliação Semanal de uma sprint e confirmar que o questionário agora tem 6 perguntas (sem a de evolução).
3. Abrir a aba Métricas de um projeto e confirmar que a tabela "Entrega por pessoa" não tem mais a coluna Evolução.
4. Conferir que a nota que ele considerou injusta já aparece recalculada com o peso novo do gerente, sem precisar reabrir nenhuma sprint.

- [x] **Step 5: Relatar ao usuário**

Resuma o que foi verificado automaticamente (testes + typecheck + greps) e liste o checklist manual do Step 4 como pendente de confirmação dele.

---

## Self-Review

**Cobertura da spec:** §2.1 (pesos) → Task 1. §2.2 (remoção completa da evolução) → Tasks 2, 3, 5, 8, 11, 12, 16, 17. §2.3 (ranking por projeto) → Task 7, 13. §3 (recálculo ao vivo) → Task 6. §4 (modelo de dados) → Tasks 1, 3, 5, 7. §5 (endpoints) → Tasks 4, 5, 7. §6 (frontend) → Tasks 10-13. §7 (fora de escopo) → nenhuma task cobre de propósito. §8 (testes) → distribuído em cada task.

**Consistência de tipos:** `resposta_6: Optional[int]` (Python) e `resposta_6?: number`/`resposta_6: number | null` (TypeScript, dependendo se é payload de entrada ou resposta) coerentes entre backend e frontend. `listar_pessoas_ativas_por_projeto` retorna `dict[str, dict]` com chaves `projeto_nome`/`pessoas`, consumido de forma consistente em `routers/performance.py` (Task 7) e nos testes (mesma task). `PerformanceProjetoResponse`/`PerformanceProjeto` (Python/TypeScript) têm os mesmos campos (`projeto_id`, `projeto_nome`, `sprint`, `quinzenal`, `mensal`). `SpiPorOperacionalDoProjetoResponse`/`SpiPorOperacionalDoProjeto` idem.

**Placeholders:** nenhum "TBD"/"adicionar validação apropriada" — todo código é literal. As edições de documentação (Tasks 16-17) dão o texto exato antes/depois em vez de instruções vagas de "atualizar conforme necessário".
