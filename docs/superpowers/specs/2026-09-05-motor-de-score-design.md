# Phase 18 — Motor de Score: Dado Bruto por Sprint + SPI do Operacional + Baseline de Evolução

**Status:** Aprovado para planejamento (brainstorming concluído em 2026-09-05)
**Fase no ROADMAP:** `.planning/ROADMAP.md`, Phase 18, requisitos SCORE-01..05
**Depende de:** Phase 14 (reaberturas/bloqueio manual — insumo de qualidade/autonomia), Phase 17 (avaliação do gerente — insumo de `gerente_media`/`gerente_pergunta6`), Phase 16 (RBAC — `require_role("lider")` protege leitura de score)
**Afeta:** Phase 19 (Peso por Arquétipo + Ranking — consome `pontuacao_operacional_sprint` travada como sequência pessoal do operacional)

## Contexto e objetivo

Hoje `pontuacao_operacional_sprint` e `baseline_evolucao` não existem. Esta phase cria a linha travada por operacional/sprint/projeto que acumula os insumos brutos de score, e o mecanismo de fechamento que a calcula e trava. Diferente de um contador incremental mantido ao longo da sprint, a linha é **calculada uma única vez, no momento do fechamento**, a partir do estado final de `tasks`/`task_transicoes`/`task_reaberturas`/`avaliacoes_gerente` — isso resolve reatribuição mid-sprint sem precisar reagir a cada mudança individual.

**Fora de escopo desta phase** (documentado explicitamente):
- `projects.arquetipo` e `pesos_arquetipo` (tabela) são Phase 19 — a coluna `arquetipo` em `pontuacao_operacional_sprint` fica nullable e não populada nesta phase (grava `null`); Phase 19 decide como/se faz backfill ao introduzir o campo no projeto. Sem impacto de cálculo: pesos são iguais entre arquétipos (decisão Gabriel, `.planning/intel/decisions.md` #3), então a ausência do valor não distorce nenhuma fórmula desta phase.
- Ranking, breakdown por dimensão, comparação entre janelas — tudo isso é Phase 19. Esta phase expõe só um `GET` simples de SPI por operacional, suficiente para verificação.
- Notificação/lembrete de fechamento pendente.

## Decisões-chave (do brainstorming)

| Decisão | Escolha | Alternativa descartada |
|---|---|---|
| Trigger de fechamento | Estender `POST /avaliacoes/{sprint_id}/confirmar` (Phase 17) — mesmo request calcula e trava `pontuacao_operacional_sprint` | Endpoint novo `POST /sprints/{id}/encerrar` separado da avaliação; fechamento automático por job |
| Recálculo na reatribuição mid-sprint | "Transferência só do que falta": pontos de task já **concluída** antes da troca ficam com quem entregou (histórico); pontos de task **ainda aberta** migram pro operacional atual | Transferência total (inclusive de tasks já concluídas); recálculo do zero sem rastrear histórico de quem completou |
| Atribuição de evento pós-fechamento (reabertura/bloqueio resolvido numa task cujo sprint já fechou) | Sprint retornada por `GET /projects/{project_id}/current-sprint` no momento do evento | Última sprint não travada do projeto (sem depender de planning ingestion); evento não conta pra nenhuma sprint |
| Definição de "ciclo" (`baseline_evolucao`) | Texto livre informado pelo Líder no momento em que aciona o snapshot manualmente — sem calendário fixo | Ciclo automático por período calendário fixo (trimestral/semestral); ciclo = primeira sprint do operacional no sistema |
| Como saber "quem completou" uma task já reatribuída | Nova coluna `task_transicoes.operacional_id` — snapshot do operacional no momento de cada transição, gravado pelo hook já existente (`_registrar_task_transicao`) | Reconstruir por replay de transições `campo=operacional_id` no momento da leitura (mais lento, mais frágil, sem persistência) |
| Idempotência do fechamento | Sprint já travada (`finalizado_em` setado em suas linhas) → confirmar de novo é no-op, retorna as linhas existentes sem recalcular | Erro 409 ao tentar confirmar de novo |

## Modelo de dados

```sql
-- Snapshot do operacional no momento de cada transição — permite saber
-- "quem estava com a task" em qualquer ponto do histórico, mesmo após
-- reatribuição posterior.
ALTER TABLE task_transicoes ADD COLUMN IF NOT EXISTS operacional_id uuid REFERENCES operacionais(id);

CREATE TABLE pontuacao_operacional_sprint (
    id                                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id                      uuid NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    sprint_id                           uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    projeto_id                          uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sprint_fim                          timestamptz NOT NULL,
    gerente_media                       numeric(4,2),
    gerente_pergunta6                   int,
    entrega_pontos_concluidos           int NOT NULL DEFAULT 0,
    entrega_pontos_alocados             int NOT NULL DEFAULT 0,
    qualidade_reaberturas               int NOT NULL DEFAULT 0,
    qualidade_tasks_concluidas          int NOT NULL DEFAULT 0,
    autonomia_bloqueios_resolvidos_proprio int NOT NULL DEFAULT 0,
    autonomia_bloqueios_totais          int NOT NULL DEFAULT 0,
    arquetipo                           text,
    finalizado_em                       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (operacional_id, sprint_id)
);

CREATE TABLE baseline_evolucao (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id  uuid NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    ciclo           text NOT NULL,
    data_snapshot   timestamptz NOT NULL DEFAULT now(),
    nota_inicial    numeric(5,2),
    observacoes     text
);

-- Ledger desacoplado para eventos de qualidade/autonomia ocorridos numa task
-- cujo sprint de origem já fechou (pontuacao_operacional_sprint travada).
-- Existe só para não precisar reatribuir task.sprint_id (que serve outras
-- telas) nem tratar bloqueio como um histórico repetível (hoje é campo único
-- na task, não uma tabela de eventos).
CREATE TABLE eventos_pontuacao_tardios (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id  uuid NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    sprint_id_alvo  uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    dimensao        text NOT NULL CHECK (dimensao IN (
                        'qualidade_reaberturas',
                        'autonomia_bloqueios_totais',
                        'autonomia_bloqueios_resolvidos_proprio'
                    )),
    task_id         uuid REFERENCES tasks(id),
    criado_em       timestamptz NOT NULL DEFAULT now()
);
```

- `UNIQUE (operacional_id, sprint_id)` em `pontuacao_operacional_sprint` garante que o fechamento nunca duplica linha para o mesmo operacional na mesma sprint.
- `gerente_media`/`gerente_pergunta6` ficam `NULL` se o operacional não tiver `avaliacoes_gerente` para essa sprint (não deveria acontecer — o gate de pendências da Phase 17 já bloqueia o fechamento nesse caso — mas a coluna aceita null em vez de assumir 0, para não distorcer médias futuras).

## Fechamento de sprint — extensão de `POST /avaliacoes/{sprint_id}/confirmar`

Depois do gate de pendências existente (sem mudança), antes de gravar `sprints.avaliacao_completa_em`:

1. Se já existir alguma linha `pontuacao_operacional_sprint` para este `sprint_id` (checagem por `sprint_id`, não por operacional individual): pula o cálculo inteiro, retorna as linhas existentes — idempotente.
2. Busca todas as `tasks` com `sprint_id` = esta sprint (estado final, sem replay de sprint histórico — uma task que mudou de sprint reflete a sprint atual dela).
3. Para cada task `concluida`: busca a transição mais recente em `task_transicoes` com `campo='coluna_kanban' AND para='concluida'` para aquele `task_id`, lê seu `operacional_id` (snapshot). Se não existir tal transição (task criada direto como `concluida`, caso raro), usa `task.operacional_id` atual como fallback.
   → agrupa pontos por esse operacional em `entrega_pontos_concluidos` e conta em `qualidade_tasks_concluidas`.
4. Para cada task **não** `concluida` (planejado/em_andamento): soma seus pontos ao `entrega_pontos_alocados` do `task.operacional_id` **atual**.
   → `entrega_pontos_alocados` final de cada operacional = pontos do passo 4 + `entrega_pontos_concluidos` do passo 3 (a entrega conta como alocação cumprida).
5. `qualidade_reaberturas`: conta linhas de `task_reaberturas` cujo `task_id` pertence a uma task desta sprint, agrupado por `task_reaberturas.operacional_id`.
6. `autonomia_bloqueios_totais`/`_resolvidos_proprio`: para tasks desta sprint com `bloqueado_resolvido_em` não nulo, agrupa por `task.operacional_id` atual; `_resolvidos_proprio` conta só onde `bloqueado_resolvido_por = 'operacional'`.
7. `gerente_media` = média de `resposta_1..5,7` (pergunta 6 fica isolada) da linha em `avaliacoes_gerente` daquele operacional+sprint; `gerente_pergunta6` = `resposta_6` da mesma linha.
8. Monta o conjunto de operacionais = união de quem apareceu em qualquer um dos passos acima (normalmente igual à lista de pendências da Phase 17, já que só quem tem task na sprint é avaliado).
9. Insere uma linha por operacional em `pontuacao_operacional_sprint` com `sprint_fim = now()`, `arquetipo = null`.
10. Segue o fluxo já existente: grava `sprints.avaliacao_completa_em`.

Tudo dentro do mesmo handler de `avaliacoes.py` (nova função auxiliar `_calcular_e_travar_pontuacao(client, sprint_id, project_id)`), sem grafo/LLM — cálculo puramente determinístico em Python + queries Supabase.

## Reatribuição mid-sprint

Nenhuma mudança em `PATCH /tasks/{id}` além da que a Etapa "modelo de dados" já cobre: `_registrar_task_transicao` passa a gravar `operacional_id=task_atual.get("operacional_id")` (o valor **antes** da mudança) em toda transição, não só nas de `campo='operacional_id'`. Isso é suficiente para o passo 3 do cálculo reconstruir corretamente "quem completou", mesmo que a task tenha sido reatribuída depois.

## Eventos pós-fechamento (reabertura / bloqueio resolvido em task de sprint já travada)

Em `patch_task` (`routers/tasks.py`), no ponto em que hoje se chama `_registrar_reabertura` ou se grava `bloqueado_resolvido_em`:

1. Verifica se `pontuacao_operacional_sprint` já tem linha travada para `task.sprint_id` (`finalizado_em` setado).
2. Se **não** travada: comportamento atual, sem mudança — o evento será capturado normalmente pelos passos 5/6 do fechamento dessa sprint (filtro por `task.sprint_id`, como já descrito).
3. Se **travada**: chama a função de serviço por trás de `GET /projects/{project_id}/current-sprint` (reaproveitada diretamente, não via HTTP interno) para achar a sprint ativa no momento do evento.
   - Se a sprint ativa **também** já estiver travada (ou não existir nenhuma sprint), o evento só fica registrado em `task_transicoes`/`task_reaberturas`/`tasks.bloqueado_resolvido_em` (histórico preservado) — não grava nada em `eventos_pontuacao_tardios`. Não bloqueia a operação do usuário.
   - Caso contrário, insere uma linha em `eventos_pontuacao_tardios` (`operacional_id` = quem está com a task agora, `sprint_id_alvo` = a sprint ativa, `dimensao` = `'qualidade_reaberturas'` para reabertura ou `'autonomia_bloqueios_totais'` (+ `'autonomia_bloqueios_resolvidos_proprio'` se `bloqueado_resolvido_por='operacional'`) para bloqueio resolvido, `task_id` para rastreabilidade).

No fechamento (passos 5/6 do algoritmo), depois de contar pelas tasks com `sprint_id` = sprint sendo fechada, soma também as linhas de `eventos_pontuacao_tardios` com `sprint_id_alvo` = essa sprint, por operacional. Isso mantém os passos 3/4 (entrega) e a contagem normal de 5/6 inalterados — o ledger só cobre exatamente o caso tardio decidido na Pergunta 3, sem introduzir janela de tempo nem reprocessar sprints já fechadas.

## `baseline_evolucao` — endpoint manual

`POST /baseline-evolucao` (novo router ou dentro de `operacionais.py`), protegido com `require_role("lider")`.

Corpo: `{operacional_id: str, ciclo: str, observacoes: Optional[str]}`.

`nota_inicial` = SPI do operacional calculado on-the-fly (mesma fórmula do `GET /operacionais/{id}/spi` abaixo) a partir de todas as `pontuacao_operacional_sprint` travadas até o momento do request. `data_snapshot = now()`.

## `SPI_operacional` — `GET /operacionais/{id}/spi`

Protegido com `require_role("lider")` (não `require_not_operacional` — RBAC da Phase 16 restringe score/SPI a Líder, Gerente **não** vê, decisão em `.planning/intel/decisions.md` #4 / ROADMAP Phase 16 critério 3).

Cálculo:
1. Busca todas `pontuacao_operacional_sprint` do operacional.
2. Agrupa por `projeto_id`: `SPI_projeto = Σ entrega_pontos_concluidos / Σ entrega_pontos_alocados` (nulo se denominador 0).
3. `SPI_operacional` = `SPI_projeto` único se atuou em 1 projeto; média simples de `SPI_projeto_1..N` se N projetos.
4. Normalizado × 100, teto 100.

Resposta: `{operacional_id, spi: float | null, por_projeto: [{projeto_id, spi}]}`.

## Testes

Mesmo padrão pytest + `TestClient` + `MagicMock` já usado no projeto:
- `test_pontuacao_fechamento.py` — fechamento calcula e trava corretamente entrega/qualidade/autonomia/gerente; chamar `confirmar` duas vezes não duplica nem recalcula (idempotência)
- `test_pontuacao_reatribuicao.py` — task concluída por operacional A, depois reatribuída pra B antes do fechamento → pontos concluídos ficam com A, task ainda aberta reatribuída fica alocada a B
- `test_pontuacao_evento_pos_fechamento.py` — reabertura numa task de sprint já travada grava linha em `eventos_pontuacao_tardios` apontando pra sprint retornada por `current-sprint`; fechamento dessa sprint ativa soma o ledger junto com a contagem normal; se a sprint atual também estiver travada, nenhuma linha de ledger é criada e o evento fica só em `task_transicoes`
- `test_baseline_evolucao.py` — snapshot manual grava `nota_inicial` = SPI calculado no momento; `require_role("lider")` bloqueia gerente/operacional
- `test_spi_operacional.py` — SPI de 1 projeto = SPI daquele projeto; SPI de N projetos = média simples; RBAC bloqueia não-líder

## Success criteria (do ROADMAP.md, mapeados)

1. ✅ `pontuacao_operacional_sprint` gravada e travada no fechamento (extensão de `POST /avaliacoes/{sprint_id}/confirmar`), condicionada à avaliação completa (gate já existente da Phase 17)
2. ✅ Evento pós-fechamento atribuído à sprint ativa no momento do evento via `current-sprint`; nunca reabre linha travada
3. ✅ Reatribuição mid-período: `entrega_pontos_alocados` recalculado corretamente no fechamento — "transferência só do que falta" (mecânica fechada nesta spec, resolvendo a decisão de princípio de `decisions.md` #2)
4. ✅ `SPI_operacional` em duas camadas (soma por projeto, depois média simples entre projetos), teto 100
5. ✅ `baseline_evolucao` captura snapshot manual por ciclo (texto livre informado pelo Líder), sempre pessoa contra ela mesma
