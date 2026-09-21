# Verificação final — Entrega 1 (Base), "Modos de Trabalho e de Avaliação"

> Etapa 12 do feature-flow-lean (verificação final, nunca pulada/reduzida). Esta
> feature não vive em `.planning/phases/` — foi conduzida via `/brainstorm` +
> `/write-plan` (superpowers), fora da infraestrutura de fases numeradas do GSD
> (`gsd-verify-work` exige `phase_dir`/`SUMMARY.md`/ROADMAP.md que não existem
> aqui, e `gsd-tools.cjs` não está instalado neste checkout). Em vez de forçar
> essa infraestrutura, a verificação abaixo aplica o mesmo checklist mínimo do
> feature-flow-lean diretamente, com evidência de execução real (suites de
> teste, build, revisão final de código) coletada nesta sessão — não é UAT
> conversacional com o usuário, já que a sessão rodou em modo "continue
> executando, não pergunte nada".

**Plano:** `docs/superpowers/plans/2026-09-20-modos-trabalho-avaliacao-entrega1.md`
**Spec:** `docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md`
**UI-SPEC:** `docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-ui-spec.md`
**Commits:** `41589f6` (spec) → `5243b31` (plano) → `fe4489e`..`2b93373` (12 tasks + fix rounds)

## Checklist

- [x] **Back-end: testes passando.** Suite completa: 415/416 (1 falha
  pré-existente não relacionada, `test_security.py::test_dependencias_separam_browser_automacoes_e_webhooks_publicos`,
  reconfirmada presente no commit-base via worktree descartável — não é
  regressão desta feature). Teste de regressão golden
  (`test_golden_fixture_multidimensional_trava_de_regressao`) passa com
  valores idênticos — confirma que projetos nos defaults (ATRIBUICAO +
  PONTOS_ATRIBUIDOS) não tiveram NENHUM comportamento alterado.
- [x] **UI: segue o UI-SPEC.** Confirmado na revisão final: paleta/tokens
  reaproveitados sem mudança, chip com mesmo padrão de `statusChip()` já
  usado em `SprintCard.tsx`, seção de config com mesmos tokens
  (`sectionStyle`/`inputStyle`/`btnSecondary`) já usados em `page.tsx`,
  tabela de extrato convertida para `<table>` real após 1 rodada de fix
  (ver Task 12 abaixo) — todas as divergências do UI-SPEC identificadas
  durante os task reviews foram corrigidas antes desta verificação.
- [x] **UI: estados de loading/erro/vazio implementados.** Confirmado por
  task review em cada componente: `ModosTrabalhoSection` (loading do
  histórico, erro de salvamento inline, vazio "Nenhuma troca de modo
  registrada ainda"), `ExtratoPontosCard` (loading, erro de rede inline em
  vermelho, vazio "Nenhum evento de pontuação registrado ainda."), chip do
  SprintCard (oculto quando `elegiveis_avaliacao_count === 0`, sem estado
  vazio "quebrado").
- [x] **UI: variante escolhida fiel ao protótipo.** N/A — Etapa 8
  (prototipagem) foi pulada nesta feature (tier PADRÃO, nenhum componente
  visualmente novo, decisão registrada em `.planning/feature-flow-state.md`).
- [x] **UI: auditoria da Etapa 11 sem issues abertos.** A auditoria fundida
  (motion + Refactoring UI + taste) foi coberta pela revisão final de todo
  o plano: 0 Critical, 0 Important abertos. Achados Minor (extrato sem
  paginação, selects do ExtratoPontosCard sem `<label>`) foram deferidos
  explicitamente, não bloqueiam.
- [x] **UI: acessibilidade básica (WCAG AA).** Verificado item a item nos
  task reviews: chip não depende só de cor (texto "N/M" sempre visível);
  todos os campos de `ModosTrabalhoSection` (2 selects, piso, teto, WIP)
  têm `<label htmlFor>` associado (o gap do input de WIP foi achado e
  corrigido nesta sessão, commit `63013a9`); tabela de extrato usa
  `<th scope="col">` (corrigido nesta sessão, commit `2b93373`). Gap
  residual conhecido e deferido: os 2 `<select>` (operacional/sprint) do
  `ExtratoPontosCard` não têm `<label>` — não bloqueia, listado como
  follow-up opcional na revisão final.
- [x] **Integração back-end ↔ UI funcionando.** Revisão final checou campo a
  campo: todo tipo novo do frontend (`Project` extensions, `SprintWithStatus`
  extensions, `ConfiguracaoHistoricoEntry`, `PontuacaoEvento`) bate
  exatamente com os Pydantic response models do backend (nome, tipo,
  nullability). `npm run build` limpo (type-check completo do frontend
  contra os tipos reais). Todo novo entry point de UI restrita por cargo
  confirmado gateado (chip do SprintCard, aba Configurações, aba Painel) —
  como o app não tem auth por usuário no servidor no v1, esse gate no
  frontend é o único controle de acesso, e a revisão confirmou que nenhum
  ponto novo o contorna.

## Itens fora do escopo desta verificação (não é regressão, não bloqueia)

- **Deploy:** a migração manual do Supabase (schema completo da Entrega 1,
  incluindo a coluna `entrega_modo`) ainda precisa rodar manualmente antes do
  próximo deploy — aviso já registrado desde a Onda 1, sem mudança aqui (ver
  memória `project_manual_migrations.md`).
- **Elegibilidade nova (entrada/saída de operacional no meio do projeto)** —
  fora de escopo da Entrega 1 por decisão consciente na Etapa 1 (fica pra
  Entrega 2).
- **Exportação CSV e métricas comparativas por modo** — mencionadas no
  título da feature mas não fazem parte do plano da Entrega 1 (Base); ficam
  para uma entrega futura.

## Veredito

**Entrega 1 (Base) verificada e completa.** Todos os 7 itens do checklist
mínimo passam com evidência de execução real, não apenas leitura de código.
Nenhum item pendente ou bloqueado. Pronta pra uso — únicos passos externos
restantes são operacionais (rodar a migração manual antes do deploy) e não
de código.
