# Route-Merge Draft — SDD v3 "Hub de Projetos: Performance v3" → ROADMAP.md additions

**STATUS: APPLIED** — ver `ROADMAP.md` Phases 13-19, aplicado em 2026-09-02. Numeração final difere deste rascunho: Gabriel pediu uma fase própria para o `.continue-here.md` (waves 5-6) antes das fases do SDD (risco R6), então o que este rascunho chama de "Phase 13-18" virou **Phase 14-19**, com uma nova **Phase 13** (Kanban de Tasks — Métricas + Ganchos) na frente. RBAC (Phase 16) foi reescrito para usar login leve por cargo em vez do modelo squad↔gerente proposto em R2 — ver `.planning/intel/decisions.md` #4 e #5. Este arquivo permanece como histórico do rascunho original; não reflete mais a numeração final.

**Status original (histórico):** DRAFT — not yet applied to ROADMAP.md / REQUIREMENTS.md / PROJECT.md. Needs human review of the "Riscos e perguntas" section before writing.
**Source:** `.planning/intel/constraints.md` (SDD v3, Partes 0-12) + `.planning/intel/decisions.md` (Gabriel's 3 resolutions).
**Next free phase number:** 14 — wait, see risk R0 below. ROADMAP.md's last phase is **Phase 12**, so the next free number is **Phase 13**. (Numbering below uses 13-18.)

Parte 0 (rename) is **excluded** from these phase additions — Gabriel deferred it (decisions.md #1). Noted as a backlog item only, see bottom of this file.

---

## Proposed phases (13-18)

### Phase 13: Confirmação de Transição + Reabertura + Bloqueio Manual

**Goal:** Nenhuma mudança de status de task acontece sem confirmação explícita do usuário (qualquer caminho: drag-and-drop, API, banner de IA); reabertura (`concluida → em_andamento`) é rastreada em tabela própria; bloqueio manual captura quem resolveu.
**Mode:** standard
**Depends on:** Phase 11 (última fase que mexeu em `tasks`/kanban de forma estrutural — na prática independe, mas mantém ordem cronológica do roadmap)
**Requirements:** TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05
**Success Criteria:**
  1. Qualquer tentativa de mudar `coluna_kanban`/status de uma task (drag-and-drop manual, chamada de API, aceite do banner de sugestão da IA) exige confirmação explícita antes de gravar — cancelar não grava nada.
  2. `resolve_task_sugestao` (hoje grava direto sem passar por `task_transicoes` — ver `docudata-backend/routers/tasks.py` linhas 181-206) passa a abrir o mesmo modal/fluxo de confirmação e grava a transição normalmente.
  3. Nova tabela `task_reaberturas` (id, task_id, transicao_id, operacional_id, timestamp) recebe um registro sempre que uma `task_transicoes` confirmada tiver `status_anterior=concluida` e `status_novo=em_andamento`; `task.contador_reaberturas` incrementa junto. Motivo da reabertura é campo **opcional** (decisão Gabriel).
  4. Task ganha `bloqueado_manual`, `bloqueado_em`, `bloqueado_por`, `bloqueado_resolvido_por` (enum operacional|gerente), `bloqueado_resolvido_em`; desmarcar `bloqueado_manual` exige informar quem resolveu antes de salvar.
  5. Nenhuma outra saída de `concluida` além de `concluida → em_andamento` é tratada como reabertura.
**UI hint:** yes

### Phase 14: Travamento Automático por Tempo + Trava do Baseline do SprintCard

**Goal:** Tasks paradas em `em_andamento` além de um limiar proporcional a pontos viram alerta visível só para Líder/Gerente (nunca pontuação); o baseline de pontos do SprintCard trava assim que a sprint fica ativa.
**Mode:** standard
**Depends on:** Phase 13 (usa `entrou_em_andamento_em` e o novo fluxo de reabertura para resetar o relógio)
**Requirements:** ALERT-01, ALERT-02, ALERT-03
**Success Criteria:**
  1. Job diário marca `travado_automatico=true` quando `dias_desde(entrou_em_andamento_em) >= pontos_da_task * 2` e não há `travado_override=true`; reseta ao sair de `em_andamento` ou reentrar (inclusive por reabertura).
  2. Override do gerente (`travado_override`, `travado_override_por`, `travado_override_em`) suprime a exibição sem apagar o histórico de que o sistema sinalizou.
  3. `travado_automatico`/override são visíveis só para Líder e Gerente (depende do RBAC da Phase 15 para enforcement real no backend — ver risco R1); nunca alimentam nenhuma fórmula de score.
  4. Campo de pontos previstos do SprintCard vira somente leitura assim que a sprint entra em estado ativo; revisão posterior gera registro separado de replanejamento, preservando o valor original para o SPI histórico.
**UI hint:** yes (alertas no kanban/painel) — mas enforcement de visibilidade real fica pendente até Phase 15.

### Phase 15: RBAC — Papéis e Autorização

**Goal:** O sistema distingue Líder/Gerente/Operacional em toda leitura de score/peso/avaliação/ranking, com enforcement no backend (não só UI); rota `/performance` isolada com middleware próprio; log de auditoria em toda leitura sensível.
**Mode:** standard
**Depends on:** Nothing novo do SDD (mas é pré-requisito de facto para Phases 16-18) — **ver risco R1, este é o maior risco do lote**
**Requirements:** RBAC-01, RBAC-02, RBAC-03, RBAC-04
**Success Criteria:**
  1. Existe um mecanismo de identidade de request (login leve, API key por papel, ou equivalente — **a definir, SDD não especifica**, ver R1) que resolve `papel ∈ {lider, gerente, operacional}` e, para gerente, `gerente_id`/squad.
  2. Nenhum payload de API retorna score, peso, fórmula ou ranking para papel Gerente ou Operacional — testável diretamente via API (não só oculto no frontend).
  3. Gerente só lê/escreve dados (fluxo, cycle time, SPI de projeto, CFD, WIP, avaliação, `bloqueado_manual`, `travado_automatico`) do próprio squad.
  4. Rota `/performance` retorna 403 para Gerente ou Operacional, testável direto por API; middleware de autorização é dedicado, não reaproveita o das rotas de projeto.
  5. Toda leitura de score/peso/avaliação grava log de auditoria (autor, o quê, quando).
**UI hint:** yes (algum tipo de seleção/login de papel precisa existir na UI)

### Phase 16: Avaliação do Gerente

**Goal:** Gerente preenche 7 perguntas fixas por operacional a cada fechamento de sprint (por projeto-sprint), com opção de reaproveitar a última avaliação de outro projeto; fechamento de sprint fica bloqueado até completo.
**Mode:** standard
**Depends on:** Phase 15 (RBAC — só gerente do squad preenche/vê)
**Requirements:** AVAL-01, AVAL-02, AVAL-03, AVAL-04, AVAL-05
**Success Criteria:**
  1. Nova tabela `avaliacoes_gerente` (id, operacional_id, gerente_id, sprint_id, data_preenchimento, resposta_1..7, criado_em, editavel_ate) — uma avaliação por operacional/gerente/sprint (sprint sempre de um projeto específico).
  2. As 7 perguntas de texto fixo (não editáveis) aparecem automaticamente no fechamento de sprint para cada operacional do squad; fechamento fica bloqueado enquanto houver avaliação pendente.
  3. Avaliação é editável por 48h após envio, depois trava.
  4. Ao avaliar um operacional que também está em outro projeto, a UI oferece reaproveitar a última avaliação desse outro projeto, mostrando data e projeto de origem — sem forçar formulário em branco. Pode gerar mais de uma avaliação na mesma semana calendário se dois projetos fecharem sprint perto um do outro — comportamento aceito, não é bug.
  5. Gerente só vê/preenche avaliação dos operacionais do próprio squad (depende de Phase 15 ter noção de squad↔gerente — ver risco R2).
**UI hint:** yes

### Phase 17: Motor de Score — Camada de Dado Bruto + SPI do Operacional + Baseline de Evolução

**Goal:** Uma linha travada por operacional/sprint/projeto acumula os insumos brutos de cada dimensão; SPI do Operacional agrega em duas camadas (soma dentro do projeto, média entre projetos); baseline de evolução mede a pessoa contra ela mesma.
**Mode:** standard
**Depends on:** Phase 13 (reaberturas/bloqueios), Phase 16 (avaliação do gerente como insumo)
**Requirements:** SCORE-01, SCORE-02, SCORE-03, SCORE-04, SCORE-05
**Success Criteria:**
  1. Nova tabela `pontuacao_operacional_sprint` (operacional_id, sprint_id, projeto_id, sprint_fim, gerente_media, gerente_pergunta6, entrega_pontos_concluidos, entrega_pontos_alocados, qualidade_reaberturas, qualidade_tasks_concluidas, autonomia_bloqueios_resolvidos_proprio, autonomia_bloqueios_totais, arquetipo, finalizado_em) é gravada e travada no fechamento da sprint, junto com a exigência da avaliação completa (Phase 16) — somente leitura depois.
  2. Reabertura/resolução de bloqueio ocorrida após o fechamento do sprint de origem é atribuída ao sprint ativo no momento do evento, nunca reabre uma linha travada.
  3. Quando uma task é reatribuída de um operacional para outro no meio do período, `entrega_pontos_alocados` é **recalculado** para o(s) operacional(is) afetado(s) — não fica todo com quem está com a task no fechamento (decisão Gabriel; mecânica exata de recálculo — o que acontece com o lado que perde a task vs. o que ganha — precisa ser fechada durante o planning desta fase, ver risco R3).
  4. `SPI_projeto_X = Σ pontos concluídos no projeto X ÷ Σ pontos alocados no projeto X` (uma vez por projeto, dentro do período); `SPI_operacional` = `SPI_projeto_único` se atuou em 1 projeto, ou média simples de `SPI_projeto_1..N` se atuou em N projetos no período. Normalizado × 100, teto 100.
  5. Nova tabela `baseline_evolucao` (operacional_id, ciclo, data_snapshot, nota_inicial, observacoes) captura snapshot no início de cada ciclo; Evolução é sempre pessoa contra ela mesma.
**UI hint:** no (camada de dado — sem tela própria nesta fase; consumida pela Phase 18)

### Phase 18: Peso por Arquétipo + Área de Performance e Ranking

**Goal:** `/performance` (só Líder) mostra ranking por 3 janelas contadas por sprints da sequência pessoal do operacional (não calendário), com breakdown por dimensão, comparação entre janelas e anúncio de top performer.
**Mode:** standard
**Depends on:** Phase 15 (RBAC/rota isolada), Phase 17 (dado bruto travado)
**Requirements:** PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06
**Success Criteria:**
  1. Campo `arquetipo` no projeto (dev/consultoria/agente_ia) e tabela `pesos_arquetipo` existem com os 5 pesos default, **idênticos entre arquétipos e fixos permanentemente** (decisão Gabriel — não há diferenciação objetiva a implementar; não bloquear nesta fase por causa disso).
  2. Sequência pessoal do operacional = todas as linhas de `pontuacao_operacional_sprint` com `entrega_pontos_alocados > 0`, ordenadas por `sprint_fim` desc, podendo misturar projetos. Janelas por contagem: sprint=última 1 linha, quinzenal=últimas 2, mensal=últimas 4 — nunca por data de calendário.
  3. Agregação em duas camadas dentro da janela (agrupa por projeto, depois — se mais de um projeto — média simples entre os valores já calculados por projeto, não ponderada por volume), replicando o método da Phase 17.
  4. Arquétipo da janela = arquétipo do projeto com mais linhas (sprints) na janela, não mais pontos; empate quebrado pela linha mais recente.
  5. Janela incompleta (operacional com menos linhas do que a janela pede) calcula com o que existe e vem **sinalizada visualmente como "janela parcial"** no ranking (decisão Gabriel).
  6. Tela do Líder: ranking completo por janela, breakdown por dimensão, comparação entre as 3 janelas, botão de anúncio do top performer (nome + frase, sem número) para qualquer janela.
**UI hint:** yes

---

## REQUIREMENTS.md — entradas novas propostas (### Active)

```
### Hub de Projetos — Confirmação, Reabertura, Bloqueio (Phase 13)
- [ ] TRANS-01: Toda transição de status de task exige confirmação explícita antes de gravar, em qualquer caminho
- [ ] TRANS-02: Banner de sugestão da IA passa a exigir confirmação (hoje grava direto sem task_transicoes)
- [ ] TRANS-03: Reabertura (concluida → em_andamento) é registrada em task_reaberturas com motivo opcional
- [ ] TRANS-04: Bloqueio manual captura quem resolveu (operacional | gerente) ao desmarcar
- [ ] TRANS-05: Nenhuma outra saída de concluida conta como reabertura

### Hub de Projetos — Alertas e Integridade (Phase 14)
- [ ] ALERT-01: Task travada automaticamente após limiar proporcional a pontos (1pt=2d, 2pt=4d, 3pt=6d), nunca alimenta score
- [ ] ALERT-02: Override do gerente é auditável e não apaga o histórico do alerta
- [ ] ALERT-03: Baseline de pontos do SprintCard trava ao iniciar a sprint; revisão posterior fica em registro separado

### Hub de Projetos — RBAC (Phase 15)
- [ ] RBAC-01: Sistema resolve papel (Líder/Gerente/Operacional) por request, com enforcement no backend
- [ ] RBAC-02: Nenhum endpoint retorna score/peso/ranking para Gerente ou Operacional
- [ ] RBAC-03: Rota /performance isolada, 403 para não-Líder, middleware dedicado
- [ ] RBAC-04: Toda leitura de score/peso/avaliação é auditada (autor, quando)

### Hub de Projetos — Avaliação do Gerente (Phase 16)
- [ ] AVAL-01: Gerente preenche 7 perguntas fixas por operacional por projeto-sprint
- [ ] AVAL-02: Fechamento de sprint bloqueado até avaliação completa
- [ ] AVAL-03: Avaliação editável por 48h, depois trava
- [ ] AVAL-04: UI oferece reaproveitar última avaliação de outro projeto (data + projeto de origem)
- [ ] AVAL-05: Gerente só vê/preenche avaliação do próprio squad

### Hub de Projetos — Motor de Score (Phase 17)
- [ ] SCORE-01: pontuacao_operacional_sprint gravada e travada no fechamento de cada sprint
- [ ] SCORE-02: Eventos pós-fechamento (reabertura/bloqueio) atribuídos ao sprint ativo no momento, nunca reabrem linha travada
- [ ] SCORE-03: Reatribuição de task mid-período recalcula entrega_pontos_alocados do(s) operacional(is) afetado(s)
- [ ] SCORE-04: SPI do Operacional soma dentro do projeto, tira média simples entre projetos diferentes
- [ ] SCORE-05: baseline_evolucao registra ponto zero por ciclo, pessoa contra ela mesma

### Hub de Projetos — Performance e Ranking (Phase 18)
- [ ] PERF-01: pesos_arquetipo com 5 pesos default, idênticos entre arquétipos, sem diferenciação a implementar
- [ ] PERF-02: Janelas sprint/quinzenal/mensal contadas por linhas da sequência pessoal, não calendário
- [ ] PERF-03: Agregação em duas camadas (por projeto, depois média simples entre projetos) replicada da Phase 17
- [ ] PERF-04: Arquétipo da janela = projeto com mais linhas, empate pela mais recente
- [ ] PERF-05: Janela parcial sinalizada visualmente no ranking
- [ ] PERF-06: Tela do Líder com ranking, breakdown, comparação de janelas, anúncio de top performer
```

## PROJECT.md — nota (não aplicada ainda)

Quando o rename (Parte 0) for retomado como fase própria (decisão Gabriel: adiado, não agora):
- Título `# DocuData` → `# Hub de Projetos`, corpo do "What This Is" atualizado.
- `## Out of Scope` precisa **remover** a linha "Autenticação e controle de acesso — MVP compartilhado sem login" (contradita pela Phase 15/RBAC deste lote — ver risco R1) e registrar a mudança em `## Key Decisions`.
- Este lote (Phases 13-18) já contradiz esse Out of Scope mesmo sem o rename — sinalizar isso em PROJECT.md ao aplicar as fases, não só no rename.

---

## Riscos e perguntas para revisão humana antes de aplicar

**R1 — RBAC sem nenhum mecanismo de autenticação existente (risco maior do lote).** PROJECT.md hoje lista "Autenticação e controle de acesso" como Out of Scope explícito ("MVP compartilhado sem login"). O SDD Parte 6 assume que dá para saber "quem está fazendo a request" para aplicar RBAC de verdade no backend — mas o sistema não tem login, sessão, nem qualquer identidade de usuário hoje. Phase 15 como desenhada não pode ser implementada sem primeiro decidir *como* a identidade/papel chega em cada request (login simples com senha por papel? API key fixa por papel, escolhida no client? Um seletor de "estou entrando como Líder/Gerente X/Operacional Y" sem senha, só para o MVP?). **Preciso que você decida o mecanismo mínimo antes do planning da Phase 15** — o SDD não especifica isso, e é o maior risco de escopo do lote inteiro.

**R2 — "Squad" não tem dono (Gerente) modelado.** `Project.squad` existe hoje como texto livre (da Phase 4), mas não há relação estruturada "este squad pertence a este Gerente" em lugar nenhum do schema atual. Parte 5 e Parte 6 dependem de "gerente só vê/avalia operacionais do próprio squad" — isso precisa de um jeito de amarrar squad↔gerente, que também não existe. Deve ser resolvido dentro do RBAC (Phase 15) ou você prefere modelar isso separado?

**R3 — Mecânica exata da recalculação de pontos em reatribuição de task (decisão Gabriel #2, ainda incompleta).** Você disse "os pontos previstos daquele operacional é recalculado" — isso estabelece o princípio, mas faltam os detalhes mecânicos: quando a task sai do operacional A e vai para o B no meio do sprint, o `entrega_pontos_alocados` de A diminui os pontos da task e o de B aumenta na mesma hora? E se a task já estava `concluida` por A antes de ser reatribuída — os `entrega_pontos_concluidos` de A também migram para B, ou ficam com quem completou de fato? Isso precisa ser fechado no planning detalhado da Phase 17, não neste ingest.

**R4 — Prefixo de requirements novo em vez de continuar M9+.** ROADMAP.md usa M1-M8 (§5) nas Phases 4-12, referenciando um documento externo que não está em `.planning/` — e REQUIREMENTS.md nunca foi atualizado para rastrear M1-M8 (está parado em 2026-05-22, só com PROJ-/INGS-/EXTR-/GERA-/ACES-). Este draft optou por prefixos descritivos novos (TRANS-, ALERT-, RBAC-, AVAL-, SCORE-, PERF-) em vez de continuar a numeração M9+ — para não perpetuar a referência a um "§5" que não existe no repo. Confirma que está OK, ou prefere que eu tente reconstruir/alinhar com o esquema M-number mesmo assim?

**R5 — Granularidade das fases (6 fases vs. menos).** O agrupamento acima segue a sugestão original (A-F ≈ Phases 13-18). Alternativas razoáveis: dobrar RBAC (Phase 15) dentro da Phase 13 (já que ambas mexem no fluxo de tasks) para reduzir de 6 para 5 fases; ou juntar Phase 17+18 (motor de score + ranking) já que são o mesmo "produto" visto de dois ângulos. Mantive separado porque RBAC é infraestrutura transversal (não é UX de task) e porque a camada de dado bruto (17) trava independente da tela de ranking (18) — mas é sua chamada se preferir menos fases.

**R6 — Dependência declarada da Phase 13 em "Phase 11" é só ordem cronológica, não uma dependência técnica real.** As Partes 1-3 do SDD mexem em `tasks`/`task_transicoes`, que foram criadas fora deste roadmap (aparecem em `.planning/.continue-here.md` de uma thread "kanban-tasks-spi" que não tem fase própria neste ROADMAP.md — ver nota abaixo). Só sinalizando que a numeração de fases deste projeto pode estar dessincronizada com o código real de tasks/operacionais/sprints, que já existe e funciona segundo `.planning/.continue-here.md`.

**Nota separada, fora do escopo deste draft:** `.planning/.continue-here.md` descreve um "Kanban de Tasks, Operacionais, Pontos e SPI" com waves 1-4b concluídas e wave 5 (Métricas) e wave 6 (opcional) pendentes, tocando exatamente as mesmas tabelas (`tasks`, `operacionais`, `sprints`, SPI) que este SDD estende — mas essa thread não tem uma entrada correspondente em `ROADMAP.md` (não há "Phase: Kanban de Tasks" nas Phases 1-12 listadas). Antes de rodar `/gsd-plan-phase 13`, vale confirmar se essa wave 5/6 pendente do continue-here.md já está coberta por alguma das Phases 13-18 propostas aqui ou se é um terceiro fio solto que precisa de fase própria.
