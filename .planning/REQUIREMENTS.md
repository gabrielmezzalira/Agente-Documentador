# Requirements: DocuData

**Defined:** 2026-05-22
**Core Value:** O fluxo de ingestão + geração precisa funcionar de ponta a ponta — subir um arquivo, extrair conteúdo estruturado e gerar um documento útil.

## v1 Requirements

### Projetos

- [ ] **PROJ-01**: Gerente pode criar projeto com nome, cliente e descrição
- [ ] **PROJ-02**: Gerente pode visualizar lista de projetos existentes
- [ ] **PROJ-03**: Gerente pode navegar para o dashboard de um projeto específico

### Ingestão

- [ ] **INGS-01**: Gerente pode fazer upload de arquivo (DOCX, PDF, TXT, PNG, JPG, WEBP) associado a um número de sprint
- [ ] **INGS-02**: Sistema exibe feedback de sucesso ou erro após o upload
- [ ] **INGS-03**: Gerente pode visualizar histórico de ingestões do projeto agrupado por sprint (nome do arquivo, data, resumo extraído)

### Extração

- [ ] **EXTR-01**: Sistema extrai conteúdo estruturado (6 campos: resumo, tarefas, decisoes, problemas, contexto_cliente, proximos_passos) via Gemini 2.5 Flash
- [ ] **EXTR-02**: Sistema processa arquivos de texto (DOCX, TXT) extraindo texto puro
- [ ] **EXTR-03**: Sistema processa PDFs com camada de texto via pdfplumber
- [ ] **EXTR-04**: Sistema processa imagens e PDFs escaneados via Gemini 2.5 Flash (visão multimodal)

### Geração

- [ ] **GERA-01**: Gerente pode gerar documento de Status da Sprint (concluído / pendente / bloqueios) para uma sprint específica
- [ ] **GERA-02**: Gerente pode gerar Documento Completo do Projeto (visão geral, timeline, decisões, desafios, estado atual)
- [ ] **GERA-03**: Documento gerado é exibido em markdown renderizado na tela
- [ ] **GERA-04**: Gerente pode copiar o markdown gerado para o clipboard

## v2 Requirements

### Geração

- **GERA-v2-01**: Gerente pode gerar Retrospectiva da Sprint (o que funcionou / não funcionou / aprendizados)
- **GERA-v2-02**: Gerente pode gerar Log de Decisões técnicas cronológico de todo o projeto

### Acesso

- **ACES-v2-01**: Autenticação com email/senha → **absorvido por RBAC-01 (Phase 16)**, ver seção "v3 Requirements" abaixo — 2026-09-02
- **ACES-v2-02**: Isolamento de projetos por usuário → **parcialmente absorvido por RBAC-02 (Phase 16)**: isolamento por projeto aplica-se só a cargo=operacional; Líder e Gerente têm acesso a todos os projetos por design (decisão Gabriel, ver `.planning/intel/decisions.md` #4) — 2026-09-02

## v3 Requirements — Hub de Projetos: Rename + Avaliação de Performance (SDD v3, ingerido 2026-09-02)

Fonte: `.planning/incoming/SDD-hub-de-projetos-v3.md`, sintetizado em `.planning/intel/constraints.md` e `.planning/intel/decisions.md`. Mapeado para ROADMAP.md Phases 13-19. Parte 0 (rename DocuData → Hub de Projetos) foi **deferida** (decisão Gabriel) — não gerou requirements nem fase nesta rodada.

### Kanban de Tasks — Métricas (Phase 13)

- [ ] **MET-01**: SPI por operacional (Σ pontos_realizados ÷ Σ pontos_previstos) exposto via API
- [ ] **MET-02**: Cycle-time (p50, p85) exposto via API
- [ ] **MET-03**: Throughput exposto via API
- [ ] **MET-04**: CFD (cumulative flow diagram) calculável a partir de task_transicoes
- [ ] **MET-05**: MetricasTab.tsx (Recharts) exibe SPI/cycle-time/throughput/CFD
- [ ] **MET-06**: Performance por operacional exposta via API
- [ ] **MET-07** *(opcional)*: Ganchos daily/commit/retrospectiva alimentam sinais de saúde do projeto
- [ ] **MET-08** *(opcional)*: DoR/DoD bloqueante na transição de status de task
- [ ] **MET-09** *(opcional)*: status_saude auto-derivado do SPI

### Confirmação, Reabertura, Bloqueio (Phase 14)

- [ ] **TRANS-01**: Toda transição de status de task exige confirmação explícita antes de gravar, em qualquer caminho
- [ ] **TRANS-02**: Banner de sugestão da IA passa a exigir confirmação (hoje grava direto sem task_transicoes)
- [ ] **TRANS-03**: Reabertura (concluida → em_andamento) é registrada em task_reaberturas com motivo opcional
- [ ] **TRANS-04**: Bloqueio manual captura quem resolveu (operacional | gerente) ao desmarcar
- [ ] **TRANS-05**: Nenhuma outra saída de concluida conta como reabertura

### Alertas e Integridade (Phase 15)

- [ ] **ALERT-01**: Task travada automaticamente após limiar proporcional a pontos (1pt=2d, 2pt=4d, 3pt=6d), nunca alimenta score
- [ ] **ALERT-02**: Override do gerente é auditável e não apaga o histórico do alerta
- [ ] **ALERT-03**: Baseline de pontos do SprintCard trava ao iniciar a sprint; revisão posterior fica em registro separado

### RBAC (Phase 16)

- [ ] **RBAC-01**: Login email/senha resolve cargo (Líder/Gerente/Operacional) por pessoa cadastrada manualmente
- [ ] **RBAC-02**: Cargo determina acesso — Líder/Gerente sem restrição de projeto; Operacional só nos projetos vinculados
- [ ] **RBAC-03**: Nenhum endpoint retorna score/peso/ranking para Gerente ou Operacional
- [ ] **RBAC-04**: Rota /performance isolada, 403 para não-Líder, middleware dedicado
- [ ] **RBAC-05**: Toda leitura de score/peso/avaliação é auditada (autor, quando)

### Avaliação do Gerente (Phase 17)

- [ ] **AVAL-01**: Gerente preenche 7 perguntas fixas por operacional por projeto-sprint
- [ ] **AVAL-02**: Fechamento de sprint bloqueado até avaliação completa
- [ ] **AVAL-03**: Avaliação editável por 48h, depois trava
- [ ] **AVAL-04**: UI oferece reaproveitar última avaliação de outro projeto (data + projeto de origem)
- [ ] **AVAL-05**: Qualquer gerente avalia operacionais de qualquer projeto ao qual tenha acesso (sem restrição de squad)

### Motor de Score (Phase 18)

- [ ] **SCORE-01**: pontuacao_operacional_sprint gravada e travada no fechamento de cada sprint
- [ ] **SCORE-02**: Eventos pós-fechamento (reabertura/bloqueio) atribuídos ao sprint ativo no momento, nunca reabrem linha travada
- [ ] **SCORE-03**: Reatribuição de task mid-período recalcula entrega_pontos_alocados do(s) operacional(is) afetado(s)
- [ ] **SCORE-04**: SPI do Operacional soma dentro do projeto, tira média simples entre projetos diferentes
- [ ] **SCORE-05**: baseline_evolucao registra ponto zero por ciclo, pessoa contra ela mesma

### Performance e Ranking (Phase 19)

- [ ] **PERF-01**: pesos_arquetipo com 5 pesos default, idênticos entre arquétipos, sem diferenciação a implementar
- [ ] **PERF-02**: Janelas sprint/quinzenal/mensal contadas por linhas da sequência pessoal, não calendário
- [ ] **PERF-03**: Agregação em duas camadas (por projeto, depois média simples entre projetos) replicada da Phase 18
- [ ] **PERF-04**: Arquétipo da janela = projeto com mais linhas, empate pela mais recente
- [ ] **PERF-05**: Janela parcial sinalizada visualmente no ranking
- [ ] **PERF-06**: Tela do Líder com ranking, breakdown, comparação de janelas, anúncio de top performer

## Out of Scope

| Feature | Reason |
|---------|--------|
| ~~Autenticação / login~~ | **Revisto 2026-09-02**: login leve por cargo entra em escopo via RBAC-01 (Phase 16, SDD v3) — ver `.planning/intel/decisions.md` #4. Isolamento por projeto continua fora de escopo para Líder/Gerente; só Operacional é restrito por projeto. |
| Exportação DOCX/PDF | Clipboard é suficiente; export adiciona dependências desnecessárias |
| Editor de texto no documento gerado | Transforma DocuData em Notion — gerentes querem parar de escrever, não escrever mais |
| Notificações (email, Slack) | Integração complexa sem necessidade validada |
| Busca em conteúdo ingerido | Requer infraestrutura de full-text search sem demanda validada |
| Versionamento de documentos gerados | Regenerar sob demanda é suficiente para v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROJ-01 | Phase 1 | Pending |
| PROJ-02 | Phase 1 | Pending |
| PROJ-03 | Phase 1 | Pending |
| INGS-01 | Phase 1 | Pending |
| INGS-02 | Phase 1 | Pending |
| EXTR-01 | Phase 1 | Pending |
| EXTR-02 | Phase 1 | Pending |
| INGS-03 | Phase 2 | Pending |
| EXTR-03 | Phase 2 | Pending |
| EXTR-04 | Phase 2 | Pending |
| GERA-01 | Phase 2 | Pending |
| GERA-02 | Phase 2 | Pending |
| GERA-03 | Phase 3 | Pending |
| GERA-04 | Phase 3 | Pending |
| MET-01..09 | Phase 13 | Pending |
| TRANS-01..05 | Phase 14 | Pending |
| ALERT-01..03 | Phase 15 | Pending |
| RBAC-01..05 | Phase 16 | Pending |
| AVAL-01..05 | Phase 17 | Pending |
| SCORE-01..05 | Phase 18 | Pending |
| PERF-01..06 | Phase 19 | Pending |

**Coverage:**
- v1 requirements: 14 total, mapped to phases: 14, unmapped: 0 ✓
- v3 requirements (Hub de Projetos, SDD v3): 38 total, mapped to Phases 13-19: 38, unmapped: 0 ✓
- **Gap pré-existente, não introduzido por este ingest:** os requirements das Phases 4-12 (TMPL-, FORM-, GH-, VAL-, M1-M8/§5, §4.1-§4.6) nunca foram formalizados nesta tabela — ROADMAP.md referencia um documento externo "§5" que não existe em `.planning/`. Este arquivo ficou parado em 2026-05-22 até esta atualização; considerar reconstruir a rastreabilidade das Phases 4-12 separadamente.

---
*Requirements defined: 2026-05-22*
*Last updated: 2026-09-02 — v3 Requirements (Hub de Projetos: RBAC + Avaliação de Performance, Phases 13-19) adicionados via /gsd-ingest-docs (SDD-hub-de-projetos-v3.md); ACES-v2-01/02 e a linha "Autenticação / login" do Out of Scope reconciliadas com RBAC-01/02.*
