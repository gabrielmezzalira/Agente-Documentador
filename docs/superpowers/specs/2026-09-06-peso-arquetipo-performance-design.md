# Phase 19 — Peso por Arquétipo + Área de Performance e Ranking

**Status:** Aprovado para planejamento (brainstorming concluído em 2026-09-06)
**Fase no ROADMAP:** `.planning/ROADMAP.md`, Phase 19, requisitos PERF-01..06
**Depende de:** Phase 16 (RBAC — `require_role("lider")`), Phase 18 (Motor de Score — `pontuacao_operacional_sprint` travada)
**Afeta:** `services/pontuacao.py` da Phase 18 recebe duas correções/adições (ver seção 1 e 2) — código já commitado e pushed, mas nenhuma migração ainda foi aplicada no Supabase, então não há dado real gerado com a fórmula antiga a corrigir.

## Contexto e objetivo

O ROADMAP fala em "5 pesos" e "breakdown por dimensão" pra Phase 19 mas nunca define quais são as 5 dimensões nem como cada uma vira um número comparável antes de multiplicar pelo peso — sem isso não existe ranking calculável. O brainstorming fechou essas definições com o Líder, e no processo surgiram duas mudanças de escopo:

1. **Correção retroativa na Phase 18**: `gerente_media` deveria ser a média das 7 respostas do questionário (não 6, como foi implementado). A `resposta_6` (evolução) entra duas vezes por design — uma vez dentro da média geral, outra vez isolada em `gerente_pergunta6` — o mesmo padrão de sobreposição proposital já usado pela pergunta 3 (autonomia) com a dimensão Autonomia calculada por dado de sistema. Não é duplicação a remover.
2. **Escopo novo**: uma dimensão de Qualidade Técnica agora combina o sinal que já existia (taxa de retrabalho) com um sinal novo — nota de qualidade de commit avaliada por IA, estendendo o pipeline de ingestão de commit que já existe (Phase 4) em vez de criar um gatilho novo.

**Fora de escopo desta phase** (documentado explicitamente):
- Botão de "anúncio do top performer" do critério de sucesso 6 original do ROADMAP — descopado pelo Líder nesta sessão. A tela entrega só o ranking; não há geração de frase nem botão de anúncio.
- Diferenciação de pesos por arquétipo — decisão fechada e permanente (`.planning/intel/decisions.md` #3): os 5 pesos principais são idênticos entre `padrao` e `consultoria_discovery`. O que muda por arquétipo é a *presença* do sinal de commit dentro de Qualidade, não o peso das dimensões entre si.
- Ajuste fino do peso interno commit-vs-retrabalho dentro de Qualidade — fica como coluna configurável (`peso_commit_qualidade`), começando em 0.5; o valor final é decisão do Líder depois de rodar o piloto, não desta phase.

## Decisões-chave (do brainstorming)

| Decisão | Escolha | Alternativa descartada |
|---|---|---|
| As 5 dimensões e pesos | Gerente 35% · Entrega 20% · Qualidade 20% · Autonomia 15% · Evolução 10% | 4 dimensões fundindo Autonomia em Qualidade |
| `gerente_media` (correção Phase 18) | Média das 7 respostas; pergunta 6 entra duas vezes por design (média geral + isolada em Evolução) | Excluir pergunta 6 da média geral (era a decisão anterior, agora revertida) |
| Normalização por dimensão | Escala fixa por dimensão (fórmulas determinísticas, sem depender de outros operacionais) | Percentil relativo ao grupo (instável — placar de alguém muda por causa de outra pessoa entrar/sair) |
| Qualidade de commit via IA | Entra na Phase 19, estendendo `POST /ingest/commit` existente (não cria gatilho novo) | Fase separada (20) que a Phase 19 só prepararia |
| Peso interno commit-vs-retrabalho em Qualidade | Coluna configurável em `pesos_arquetipo`, default 0.5 | Hardcoded no código |
| Anúncio de top performer | Descopado — só ranking | Frase gerada por Gemini / template fixo |
| Valores de `arquetipo` | `padrao` \| `consultoria_discovery` (2 valores) | `dev` \| `consultoria` \| `agente_ia` (3 valores, como o texto original do ROADMAP sugeria) |
| Onde definir `arquetipo` do projeto | Aba Escopo do projeto (`EscopoTab.tsx`), junto dos outros campos de contrato | Campo obrigatório na criação do projeto |

## Modelo de dados

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS arquetipo text NOT NULL DEFAULT 'padrao'
    CHECK (arquetipo IN ('padrao', 'consultoria_discovery'));

CREATE TABLE IF NOT EXISTS pesos_arquetipo (
    arquetipo               text PRIMARY KEY CHECK (arquetipo IN ('padrao', 'consultoria_discovery')),
    peso_gerente            numeric(3,2) NOT NULL DEFAULT 0.35,
    peso_entrega            numeric(3,2) NOT NULL DEFAULT 0.20,
    peso_qualidade          numeric(3,2) NOT NULL DEFAULT 0.20,
    peso_autonomia          numeric(3,2) NOT NULL DEFAULT 0.15,
    peso_evolucao           numeric(3,2) NOT NULL DEFAULT 0.10,
    peso_commit_qualidade   numeric(3,2) NOT NULL DEFAULT 0.50
);
INSERT INTO pesos_arquetipo (arquetipo) VALUES ('padrao'), ('consultoria_discovery')
    ON CONFLICT (arquetipo) DO NOTHING;

CREATE TABLE IF NOT EXISTS commit_qualidade (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_hash     text        NOT NULL,
    task_id         uuid        REFERENCES tasks(id) ON DELETE SET NULL,
    operacional_id  uuid        REFERENCES operacionais(id) ON DELETE SET NULL,
    projeto_id      uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    nota            int         NOT NULL CHECK (nota BETWEEN 0 AND 10),
    evidencia       text,
    criado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_commit_qualidade_operacional ON commit_qualidade(operacional_id);

ALTER TABLE pontuacao_operacional_sprint ADD COLUMN IF NOT EXISTS qualidade_commit_media numeric(4,2);
```

`task_id` só é populado se a mensagem do commit tiver `[task:<uuid>]` — mesma convenção já usada por `[sprint:N]` em `docudata_agent.py`. Sem essa tag, fica `null` (rastreabilidade apenas — nada na agregação de score depende de `task_id`).

## Correção retroativa — `services/pontuacao.py::calcular_e_travar_pontuacao`

Trocar:
```python
notas = [aval["resposta_1"], aval["resposta_2"], aval["resposta_3"], aval["resposta_4"], aval["resposta_5"], aval["resposta_7"]]
```
por:
```python
notas = [aval["resposta_1"], aval["resposta_2"], aval["resposta_3"], aval["resposta_4"], aval["resposta_5"], aval["resposta_6"], aval["resposta_7"]]
```
`gerente_pergunta6` continua sendo gravado separadamente, sem mudança — a sobreposição é proposital.

## Extensão — `qualidade_commit_media` no fechamento

No mesmo `calcular_e_travar_pontuacao`, usando o `cutoff` já calculado (Phase 18, correção do achado de dupla contagem): para cada operacional, busca `commit_qualidade` do `projeto_id` e `operacional_id` com `criado_em > cutoff` (ou todos, se `cutoff is None`), grava a média de `nota` em `qualidade_commit_media` (null se não houver nenhum commit no período — comum pra `consultoria_discovery` e pra sprints sem commit registrado).

## Pipeline de qualidade de commit — extensão de `POST /ingest/commit`

Em `routers/commit_ingest.py::ingest_commit`, depois da extração de conhecimento já existente (Phase 4):

1. Se `projects.arquetipo != 'padrao'`, pula (sem sinal de commit pra consultoria/discovery).
2. Segunda chamada Gemini, mesmo `diff`/`commit_message` já coletados, prompt novo pedindo `{nota: int 0-10, evidencia: string curta}` avaliando complexidade da tarefa resolvida, qualidade da documentação/mensagens de commit, e aderência a boas práticas (nomes claros, tratamento de erro, testes quando cabível). Nunca lista pendência — só o placar com o porquê.
3. Resolve `operacional_id`: busca `operacionais` do `projeto_id` cujo `email` bate com o `author` do commit (mesmo campo já coletado pelo agente); sem match, grava `operacional_id = null`.
4. Extrai `task_id` de `[task:<uuid>]` na mensagem do commit, se presente.
5. Insere em `commit_qualidade`. Best-effort — falha na segunda chamada Gemini não derruba a ingestão de conhecimento já existente (que continua funcionando exatamente como hoje).

`docudata_agent.py` (o script instalado nos repositórios cliente) não muda — já envia tudo que o backend precisa.

## Cálculo de ranking — novo `services/performance.py`

```python
JANELAS = {"sprint": 1, "quinzenal": 2, "mensal": 4}
```

1. **Sequência pessoal**: `pontuacao_operacional_sprint` do operacional com `entrega_pontos_alocados > 0`, `ORDER BY sprint_fim DESC`. Janela = as N primeiras linhas dessa sequência (podendo misturar projetos). Menos linhas que N → `janela_parcial: true`, calcula com o que existe.
2. **Por dimensão, duas camadas** (agrupa as linhas da janela por `projeto_id`, calcula um valor por projeto, depois — se mais de um projeto — média simples entre os valores por projeto):
   - **Entrega** = mesma fórmula de `calcular_spi_operacional` (Phase 18) restrita às linhas da janela.
   - **Gerente** = média(`gerente_media` das linhas do projeto) × 20 → escala 0-100.
   - **Evolução** = média(`gerente_pergunta6` das linhas do projeto) × 20 → escala 0-100.
   - **Autonomia** = `Σautonomia_bloqueios_resolvidos_proprio ÷ Σautonomia_bloqueios_totais × 100` por projeto; `totais = 0` → 100 (sem bloqueio é autonomia máxima).
   - **Qualidade** = por projeto: `retrabalho = (1 − Σqualidade_reaberturas ÷ Σqualidade_tasks_concluidas) × 100` (`tasks_concluidas = 0` → 100); se houver `qualidade_commit_media` não-nulo nas linhas do projeto, `qualidade = peso_commit_qualidade × (média(qualidade_commit_media) × 10) + (1 − peso_commit_qualidade) × retrabalho`; sem dado de commit, `qualidade = retrabalho`.
3. **Score final** = `Σ(peso_dimensao × subscore_dimensao)`, pesos de `pesos_arquetipo` — já soma 100, sem normalização extra.
4. **Arquétipo da janela** = `arquetipo` do projeto com mais linhas na janela; empate → linha mais recente desempata.
5. Retorna, por operacional e por janela: score final, os 5 sub-scores, `janela_parcial`, `arquetipo_usado` (pra decidir qual `pesos_arquetipo` aplicar).

## `GET /performance`

`require_role("lider")` (já existe como stub em `routers/performance.py` — Phase 16 criou a rota vazia, Phase 19 implementa de fato). O stub já chama `registrar_auditoria(pessoa, "/performance", "acesso")` — exigência vinculante da Phase 16 ("toda leitura de score, peso ou avaliação de gerente grava log de auditoria"). Preservar essa chamada ao implementar o corpo real do endpoint, não só o `require_role`.

Resposta: ranking das 3 janelas (lista de operacionais ordenada por score desc, com os 5 sub-scores e `janela_parcial`), pra permitir comparação entre janelas no frontend sem 3 requests separados.

## Frontend `/performance`

Tela nova, fora de `/projects/[id]` (é cross-projeto — a sequência pessoal do operacional mistura projetos). Sem design system formal no repo (tier COMPLEXA) — tabela de ranking + seletor de janela + breakdown por dimensão (barra ou lista por sub-score), seguindo o padrão visual já usado em `MetricasTab.tsx`/`PainelTab.tsx` (cards + tabelas, zero className exótico) em vez de inventar um padrão novo.

## Testes

- `test_gerente_media_sete_respostas.py` (ou extensão de `test_pontuacao_fechamento.py`) — `gerente_media` usa as 7 respostas.
- `test_qualidade_commit_media_fechamento.py` — `qualidade_commit_media` calculado com o mesmo `cutoff` das outras dimensões; `null` quando não há commit no período.
- `test_commit_qualidade_pipeline.py` — segunda chamada Gemini só roda pra `arquetipo=padrao`; resolve `operacional_id` por email; extrai `task_id` de `[task:uuid]`; best-effort (falha não derruba a ingestão de conhecimento).
- `test_performance_ranking.py` — agregação de duas camadas com janela cobrindo 1 e >1 projeto; arquétipo da janela por contagem de linhas com empate; janela parcial; blend de Qualidade com e sem `qualidade_commit_media`; score final = soma ponderada.
- `test_performance_rbac.py` — `GET /performance` 403 pra gerente/operacional, 200 pra líder.

## Success criteria (do ROADMAP.md, mapeados)

1. ✅ `projects.arquetipo` + `pesos_arquetipo` com pesos default, idênticos entre arquétipos, fixos (decisão #3) — 2 valores de arquétipo em vez dos 3 do texto original do ROADMAP, decisão do Líder nesta sessão
2. ✅ Sequência pessoal por `entrega_pontos_alocados > 0`, desc por `sprint_fim`, janelas por contagem (1/2/4), nunca calendário
3. ✅ Agregação em duas camadas dentro da janela, replicando o método de `calcular_spi_operacional` — estendido às outras 4 dimensões
4. ✅ Arquétipo da janela = projeto com mais linhas, empate por mais recente
5. ✅ Janela incompleta calcula com o que existe, `janela_parcial: true`
6. ⚠️ Tela do Líder: ranking completo por janela, breakdown por dimensão, comparação entre janelas — **sem** o botão de anúncio de top performer (descopado nesta sessão)
