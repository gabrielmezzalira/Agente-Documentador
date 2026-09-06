# Constraints (from SPEC-type documents)

Source document: `SDD Completo — Hub de Projetos: Rename + Módulo de Avaliação de Performance v3`
Classification: `SPEC`, confidence `high`, `locked: false`, `precedence: null` (default SPEC ordering applies), `manifest_override: true`, `cross_refs: ["SDD-hub-de-projetos-v2.md"]`.

**Re-synthesis note:** This is a RE-SYNTHESIS run. The v2 classification/source has been moved to `.planning/intel/classifications/superseded/` and excluded from this ingest set. v3 is a revision of the same SPEC lineage, not a competing document — its content **fully replaces** the v2-derived entries below, it is not merged or averaged with them. v3's own provenance note states it supersedes v2 and explicitly flags the Parte 9/11/12 method change as an intentional author decision, not an error. The cross_ref to `SDD-hub-de-projetos-v2.md` points to a doc outside this run's active classification set (it lives only in `superseded/`) — no cycle exists because v2 is not part of the traversable graph in this run; this is a provenance pointer, not a live cross-reference to synthesize.

---

## Parte 0 — Rename: Agente Documentador / DocuData → Hub de Projetos
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-0
- type: nfr
- content: Buscar recursivamente (case insensitive) "Agente Documentador", "DocuData" e variações em: pasta, arquivo, pacote, módulo, classe, componente, string de UI, título de página, documentação, comentário de código, variável de ambiente, workflow do GitHub Actions. Não renomear automaticamente, reportar em vez de executar: nome do repositório GitHub, nome e URL do projeto Supabase, chave de API já publicada. Critério de aceite: relatório com o que foi substituído e o que ficou pendente de ação manual.
- scope: rename de identidade do produto (não renomear cegamente)
- change from v2: text is unchanged (condensed wording, same substance) — see WARNING in INGEST-CONFLICTS.md, still applies unmodified.

## Parte 1 — Confirmação obrigatória em toda transição de status
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-1
- type: protocol
- content: Nenhuma mudança de coluna acontece sem confirmação explícita, em nenhuma direção, incluindo drag and drop manual, chamada de API, e o banner de sugestão da IA que hoje sugere task como concluída no review. Fluxo: ao tentar mudar status de qualquer task, mostra modal "Mover [task] de [status atual] para [novo status]?"; se confirmar, executa e grava em task_transicoes; se cancelar, nada muda, nada é gravado.
- scope: task_transicoes, kanban de Tasks, banner de sugestão da IA (task_sugestoes)
- change from v2: none — same rule.

## Parte 2 — Reabertura de task
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-2
- type: schema
- content: Reabertura definida estritamente como a transição `concluida → em_andamento`; nenhuma outra saída de `concluida` conta. Nova tabela `task_reaberturas`: id, task_id, transicao_id, operacional_id, timestamp. Trigger de banco sobre task_transicoes, disparado após a confirmação da Parte 1. Regra: se status_anterior == "concluida" E status_novo == "em_andamento", grava em task_reaberturas e incrementa task.contador_reaberturas. Alimenta a taxa de retrabalho da dimensão Qualidade Técnica.
- scope: task_reaberturas, dimensão Qualidade Técnica
- change from v2: **resolved in v3** — motivo da reabertura é campo **opcional** (v2 left this as an open question; v3's "Decisões em aberto" section resolves it explicitly). See source: .planning/incoming/SDD-hub-de-projetos-v3.md#decisoes-em-aberto.

## Parte 3 — Bloqueio manual e resolução (dado de Autonomia)
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-3
- type: schema
- content: Campos na task: `bloqueado_manual` (booleano), `bloqueado_em`, `bloqueado_por`, `bloqueado_resolvido_por` (enum: operacional | gerente), `bloqueado_resolvido_em`. Ao desmarcar `bloqueado_manual`, o sistema pergunta quem resolveu. Alimenta a dimensão Autonomia: proporção de bloqueios manuais resolvidos pelo próprio operacional sobre o total de bloqueios manuais que ele teve no período.
- scope: task.bloqueado_manual e campos relacionados, dimensão Autonomia
- change from v2: none — same rule.

## Parte 4 — Travamento automático por tempo (alerta, nunca pontuação)
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-4
- type: protocol
- content: Limiar proporcional ao ponto da task (1 ponto = 2 dias, 2 pontos = 4 dias, 3 pontos = 6 dias; `limiar_dias = pontos_da_task × 2`). Âncora: `entrou_em_andamento_em`, reinicia em cada reentrada, inclusive por reabertura. Job diário varre tasks em em_andamento e compara dias decorridos ao limiar. Override do gerente: `travado_override`, `travado_override_por`, `travado_override_em` — suprime exibição sem apagar histórico. Reseta ao sair de em_andamento ou reentrar. Visível só para Líder e Gerente. `travado_automatico` nunca alimenta a fórmula de score, em nenhuma dimensão; só `bloqueado_manual` alimenta Autonomia.
- scope: task.travado_automatico, job diário, dimensão Autonomia (exclusão explícita)
- change from v2: none — same rule.

## Parte 5 — Avaliação do Gerente (35% do score)
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-5
- type: schema
- content: Tabela `avaliacoes_gerente`: id, operacional_id, gerente_id, sprint_id (projeto-específico), data_preenchimento, resposta_1 a resposta_7 (0-5), criado_em, editavel_ate. Sete perguntas de texto fixo cobrindo: entrega no prazo, qualidade sem retrabalho, autonomia para destravar, clareza de comunicação, apoio a colegas, evolução no ciclo, contribuição além do pedido. Uma avaliação por operacional, por gerente, por sprint — sprint aqui é sempre de um projeto específico. Editável por 48h após envio, depois trava. Aparece automaticamente no fechamento de sprint, bloqueia o fechamento até completa. Acesso: gerente só vê e preenche avaliação dos operacionais do próprio squad.
- scope: avaliacoes_gerente, fechamento de sprint, dimensão Avaliação do Gerente
- change from v2: **resolved in v3, and new UI affordance added.** v2 left "editável por 48h" as a suposição a confirmar and did not specify whether the evaluation form is per-project-sprint or aggregated weekly across projects. v3 explicitly resolves both: (1) editável por 48h is confirmed, not just assumed; (2) avaliação do gerente é uma resposta por operacional por projeto-sprint (não agrega os projetos num único formulário semanal) — when a manager is evaluating an operacional who is also on another project, the UI must offer the option to reuse the last evaluation made on that other project, showing the date and originating project, instead of forcing a blank form. This explicitly can produce more than one evaluation for the same operacional in the same calendar week if two projects close sprints close together — accepted as a consequence of the per-project-sprint design, not a bug.

## Parte 6 — Controle de acesso e papéis (RBAC)
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-6
- type: nfr
- content: Três papéis — Líder (Gabriel): acesso total, único que vê peso, fórmula, score individual e ranking. Gerente: vê fluxo/cycle time/SPI de projeto/CFD/WIP do próprio squad, preenche avaliação, vê bloqueado_manual e travado_automatico do próprio squad; não vê peso, score final ou ranking. Operacional: vê os próprios cards/tasks; não vê score, ranking, nota do gerente, nem travado_automatico. Enforcement no backend, não só UI. Log de auditoria obrigatório para toda leitura de score, peso ou avaliação.
- scope: RBAC transversal a todos os endpoints de score/avaliação/bloqueio
- change from v2: **new in v3** — o módulo de Performance (Parte 12) fica em rota própria (`/performance`), fora do contexto de projetos, com middleware de autorização dedicado, não compartilhado com as rotas de projeto. v2 did not specify a dedicated route/middleware for the performance module.

## Parte 7 — Baseline de Evolução
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-7
- type: schema
- content: Nova tabela `baseline_evolucao`: operacional_id, ciclo, data_snapshot, nota_inicial, observacoes. Snapshot no início de cada ciclo, ponto zero para medir crescimento. Evolução é sempre pessoa contra ela mesma, nunca contra outra pessoa.
- scope: baseline_evolucao, dimensão Evolução
- change from v2: none — same rule.

## Parte 8 — Trava do baseline do SprintCard
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-8
- type: protocol
- content: O campo de pontos previstos do SprintCard vira somente leitura assim que a sprint entra em estado ativo. Revisão posterior gera registro separado de replanejamento, preservando o valor original para o SPI histórico.
- scope: SprintCard, baseline do SPI de projeto
- change from v2: none — same rule.

## Parte 9 — SPI do Operacional (revisado: soma dentro do projeto, média entre projetos)
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-9
- type: nfr
- content: Métrica de nível de pessoa, cálculo em duas camadas. **Camada 1 (dentro de um mesmo projeto):** soma os pontos concluídos e os pontos alocados do operacional em todos os sprints daquele projeto dentro do período, divide uma vez — `SPI_projeto_X = Σ pontos concluídos no projeto X ÷ Σ pontos alocados no projeto X`. **Camada 2 (entre projetos diferentes):** se o operacional atuou em mais de um projeto no período, tira a média simples dos SPIs de cada projeto — `SPI_operacional = SPI_projeto_único` se atuou em 1 projeto, ou `(SPI_projeto_1 + ... + SPI_projeto_N) ÷ N` se atuou em N projetos. Objetivo declarado: evita que um projeto grande domine o número só por volume, mantendo a mesma lógica de calibração já usada dentro de um projeto, agora estendida ao portfólio da pessoa. Normalização: × 100, teto em 100.
- scope: SPI_operacional, dimensão Entrega e Confiabilidade
- **change from v2 — METHOD CHANGE, explicit and author-acknowledged, not an error:** v2 said the opposite structure — sum completed points across ALL projects first, sum allocated points across all projects, divide once (never average per-project SPIs, because that would "distorcer o peso de projetos pequenos vs. grandes"). v3 inverts this: sum stays within a single project across its own sprints (one SPI per project), then a simple average is taken across projects when the operator worked on more than one in the period. The v3 document's own provenance note (top of file) and inline flag before Parte 9 both call this out explicitly as an intentional calibration extension chosen by the document's author (Gabriel), not a contradiction to reconcile. **This entry OVERWRITES the v2-derived entry entirely — do not merge or average the two calculation methods.**
- **status note carried over from v2 — unclear in v3, needs confirmation:** v2 had an explicit "Decisão em aberto" at the end of its Parte 9: what happens to points when a task is reassigned from one operacional to another mid-period (today, all points go to whoever holds the task at sprint close; open question whether this distorts results in practice). **v3's Parte 9 does not restate this open question, and v3's "Decisões em aberto" section does not mention it either — neither resolved nor explicitly re-opened.** Do not assume it was silently resolved or silently dropped. Flagged separately below and in decisions.md as needing explicit confirmation from Gabriel.

## Parte 10 — Peso por Arquétipo de Projeto
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-10
- type: schema
- content: Campo `arquetipo` no projeto (enum: dev, consultoria, agente_ia). Nova tabela `pesos_arquetipo` com cinco colunas de peso. Valores default, idênticos entre os três arquétipos hoje: Avaliação do Gerente 35%, Entrega e Confiabilidade 20%, Qualidade (Técnica/Artefato) 20%, Autonomia 15%, Evolução 10%. Como os pesos são idênticos entre arquétipos no momento, a seleção de qual arquétipo usar não afeta o resultado ainda, mas o campo já fica implementado para quando isso mudar.
- scope: pesos_arquetipo (definição de tabela e pesos default)
- **change from v2 — scope narrowed, selection rule relocated:** v2's Parte 10 also stated the person-to-archetype selection rule ("usa o arquétipo do projeto onde concentrou mais pontos alocados; critério de desempate não definido"). **v3's Parte 10 no longer states any selection rule** — it only defines the weight table and default values. The selection rule now lives in v3 Parte 12 ("Arquétipo da janela") under a **different criterion**: most sprint-rows (lines) within the window, not most points, with ties broken by the most recent row. See Parte 12 entry below — do not conflate v2's "mais pontos" rule with v3's "mais linhas" rule; they are materially different selection criteria for the same underlying question.

## Parte 11 — Cálculo por sprint, camada de dado bruto (revisado: grão por projeto)
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-11
- type: schema
- content: **Unidade atômica de todo o cálculo:** um sprint de um projeto específico; score de sprint isolado, quinzenal e mensal são agregações em cima dessa unidade. Nova tabela `pontuacao_operacional_sprint`, uma linha por operacional por sprint de um projeto, com colunas: operacional_id, sprint_id, projeto_id (denormalizado do sprint, para agrupar sem join), sprint_fim (data de fechamento, usada para ordenar a sequência pessoal do operacional), gerente_media (0-5, média das sete respostas daquele sprint naquele projeto), gerente_pergunta6 (0-5, isolada, alimenta Evolução), entrega_pontos_concluidos, entrega_pontos_alocados (soma bruta daquele sprint, dentro daquele projeto), qualidade_reaberturas, qualidade_tasks_concluidas (contagem bruta daquele sprint, dentro daquele projeto), autonomia_bloqueios_resolvidos_proprio, autonomia_bloqueios_totais (contagem bruta daquele sprint, dentro daquele projeto), arquetipo (do projeto), finalizado_em. Gravada e travada no fechamento da sprint, junto com a exigência da avaliação completa — somente leitura depois. Reabertura ou resolução de bloqueio ocorrida após o fechamento do sprint de origem é atribuída ao sprint ativo no momento do evento, nunca reabre uma linha travada.
- scope: pontuacao_operacional_sprint (camada de dado bruto locked-at-sprint-close), grão = operacional × sprint × projeto
- **change from v2 — new lower-level design, not a rename:** v2's old "Parte 11 — Motor de cálculo do score" combined raw aggregation and the score formula in a single section, with no per-sprint-per-project locked raw table. v3 splits this into two sections: Parte 11 is now purely this new raw-data layer (the `pontuacao_operacional_sprint` table, locked at sprint close, grain = one row per operacional per sprint per project) — this table and its lock-at-close semantics did not exist in v2 at all. The score formula itself moved to Parte 12 (see below). Treat this as new substance, not a restructuring of identical content.

## Parte 12 — Área de Performance e Ranking (revisada: janela por contagem de sprint do operacional)
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#parte-12
- type: nfr
- content: **Localização:** rota própria `/performance`, fora de "Projetos", acesso exclusivo do Líder. **Sequência pessoal do operacional:** para cada operacional, lista de todas as linhas em pontuacao_operacional_sprint onde ele teve entrega_pontos_alocados > 0, ordenada por sprint_fim decrescente — pode misturar sprints de projetos diferentes, ordenadas só pelo tempo de fechamento. **Três filtros, por contagem, não por calendário:** Sprint/semanal = última 1 linha da sequência pessoal; Quinzenal = últimas 2 linhas; Mensal = últimas 4 linhas. **Agregação dentro da janela, duas camadas (replica Parte 9):** Passo 1, agrupa linhas selecionadas por projeto_id. Passo 2, dentro de cada grupo, soma numerador/denominador de cada dimensão-proporção e tira média simples de gerente_media/gerente_pergunta6 daquele projeto. Passo 3, se a janela tiver mais de um projeto, tira a média simples dos valores já calculados por projeto (não pondera por volume). **Arquétipo da janela** (suposição a confirmar): usa o arquétipo do projeto com mais linhas (sprints) dentro da janela, não mais pontos; empate quebrado pela linha mais recente. Hoje não muda o resultado (pesos idênticos entre arquétipos), campo fica pronto. **Score final da janela:** mesma fórmula de Parte 9/11 combinando as cinco dimensões pelos pesos de pesos_arquetipo. **Tela (só Líder):** ranking completo ordenado por score na janela selecionada, breakdown por dimensão, comparação entre as três janelas para o mesmo operacional, botão de gerar anúncio do top performer (nome + frase, sem número) para qualquer janela. **Janela incompleta:** se o operacional tem menos linhas do que a janela pede, calcula com o que existe.
- scope: /performance (rota exclusiva do Líder), ranking, top performer, seleção de arquétipo por janela
- **change from v2 — new section entirely:** v2 had no equivalent explicit "Área de Performance e Ranking" section; its old Parte 11 folded ranking/top-performer output into the score-motor section with no count-based window logic. v3 Parte 12 introduces: (a) the personal-sequence concept ordered by sprint_fim across projects, (b) sprint/quinzenal/mensal windows defined by count of the operator's own sprint-rows (not calendar dates), (c) the two-layer per-window aggregation replicating Parte 9's method, (d) the archetype-selection-by-most-sprint-rows-in-window rule (relocated and changed from v2's Parte 10 "mais pontos" rule — see Parte 10 entry above), and (e) the tie-break rule "empate quebrado pela linha mais recente" — this specific tie-break resolves the v2 open item on archetype tie-breaking, but is stated in the Parte 12 body text, NOT in v3's "Decisões em aberto" section. Surfaced as auto-resolved in INGEST-CONFLICTS.md (source: Parte 12 body, not the open-decisions section). **Resolved in v3 (also stated in "Decisões em aberto"):** janela incompleta deve vir sinalizada visualmente como "janela parcial" no ranking — v2 had no equivalent rule.

## Requisitos não funcionais
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#requisitos-nao-funcionais
- type: nfr
- content: Peso, fórmula e score bruto nunca em payload de API para Gerente ou Operacional. Toda escrita em avaliação, baseline, bloqueio e score em log de auditoria. Trava de SprintCard, formulário de avaliação e modal de confirmação de transição (Parte 1) validados no backend. Job de travamento automático (Parte 4) nunca escreve em campo que alimenta o score.
- scope: toda a superfície de API relacionada a score/avaliação/bloqueio/baseline
- change from v2: none of substance — same rules, condensed wording.

## Critérios de aceite (Definition of Done)
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#criterios-de-aceite-definition-of-done
- type: nfr
- content: Rename concluído com relatório. Toda transição de status exige confirmação, em qualquer direção e por qualquer caminho (incluindo sugestão da IA). Reabertura só registrada em concluida → em_andamento. Bloqueio manual captura quem resolveu. Travamento automático usa limiar por ponto, ancorado em entrada em em_andamento, nunca alimenta score, com override auditável. Sete perguntas do gerente bloqueiam fechamento de sprint até completas. Operacional não acessa via API nenhum score, peso, ranking ou travado_automatico de si mesmo. **SPI do Operacional soma dentro do projeto antes de dividir, e tira média simples entre projetos diferentes.** Janela sprint/quinzenal/mensal é contada por linhas da sequência pessoal do operacional, não por data de calendário. Baseline de sprint travado após início, qualquer revisão registrada à parte. Rota `/performance` retorna 403 para Gerente ou Operacional, testável direto por API.
- scope: critérios de aceite de todo o SDD (Partes 0-12)
- **change from v2 — SPI DoD line overwritten, not merged:** v2's DoD line read "SPI do Operacional soma pontos através de projetos antes de dividir, nunca faz média de proporções" — this is now **stale and superseded** per the Parte 9 method change above. v3's DoD line is the opposite: sum within project, then simple average across projects. Also new in v3's DoD (no v2 equivalent): the count-based window rule and the `/performance` 403 enforcement criterion.

## Decisões em aberto — não resolver sem confirmar com Gabriel
- source: .planning/incoming/SDD-hub-de-projetos-v3.md#decisoes-em-aberto
- type: nfr
- content: Of the 5 open items recorded in v2, v3 explicitly marks 4 as resolved and 1 as still open:
  1. **Resolvido nesta v3:** motivo da reabertura (Parte 2) é campo **opcional**.
  2. **Resolvido nesta v3:** janela de edição da avaliação do gerente (Parte 5) é **48h** — confirmed, no longer a suposição a confirmar.
  3. **Resolvido nesta v3:** avaliação do gerente é uma resposta por operacional por projeto-sprint (como desenhado), não agregada por semana calendário; quando o gerente for avaliar um operacional que está em outro projeto também, a UI oferece a opção de reaproveitar a última avaliação feita no outro projeto (mostrando data e projeto de origem); isso pode gerar mais de uma avaliação na mesma semana calendário se o operacional estiver em dois projetos com sprints fechando perto — **aceito como consequência do desenho por projeto-sprint**, não tratado como problema a resolver.
  4. **Resolvido nesta v3:** janela parcial (operacional com menos sprints do que a janela pede) deve vir sinalizada visualmente no ranking.
  5. **Ainda em aberto, sem alteração:** se algum dado objetivo deve diferenciar o peso entre arquétipos agora que CSAT foi removido (Parte 10).
- scope: itens não resolvidos — requerem decisão explícita do Líder antes de planejamento detalhado
- **Not mentioned in v3 at all — carried over from v2, status unclear:** v2's open item #4, "regra de atribuição de pontos quando uma task é reatribuída de um operacional para outro no meio do período" (Parte 9), is absent from both v3's Parte 9 body and v3's "Decisões em aberto" section. It is neither restated as open nor marked resolved. **This must not be silently treated as resolved or silently dropped** — needs explicit confirmation from Gabriel on whether it is still an open question or was intentionally dropped. Also note: **Parte 12's tie-break rule for archetype selection ("empate quebrado pela linha mais recente")** effectively resolves v2's old open item #3 (archetype tie-break) but is stated in the Parte 12 body text, not listed in this "Decisões em aberto" section — see the auto-resolved INFO entry in INGEST-CONFLICTS.md.

---
*Synthesized by gsd-doc-synthesizer — re-synthesis run. All entries traced to `SDD-hub-de-projetos-v3.md`. This file fully replaces (does not merge with) the prior v2-derived constraints.md content. No competing SPEC found in this batch (only one active classified document; v2 excluded per supersession).*
