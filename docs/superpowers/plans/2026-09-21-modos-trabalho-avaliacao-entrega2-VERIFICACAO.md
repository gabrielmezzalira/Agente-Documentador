# Verificação final — Entrega 2, "Modos de Trabalho e de Avaliação"

> Etapa 12 do feature-flow-lean (verificação final, nunca pulada/reduzida).
> Mesma justificativa da Entrega 1: feature conduzida via `/brainstorm` +
> `/write-plan` (superpowers), fora da infraestrutura de fases numeradas do
> GSD — `gsd-verify-work` exige `phase_dir`/`SUMMARY.md`/ROADMAP.md que não
> existem aqui. Checklist mínimo do feature-flow-lean aplicado diretamente,
> com evidência de execução real coletada nesta sessão (suites de teste,
> build, revisão de código) — sessão em modo "continue executando".

**Spec:** `docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md`
**Plano:** `docs/superpowers/plans/2026-09-21-modos-trabalho-avaliacao-entrega2.md`
**Commits (Onda 1, back-end):** Tasks 1-10 — ver `.planning/feature-flow-state.md`, Etapa 3
**Commits (Onda 2, front-end):** `9a18565` (Task 11 — api.ts), `26d2254` (Task 12 —
PainelTab/elegibilidade), `fbcffc3` (Task 13 — MetricasTab/comparação dentro do
projeto), `80f2ff4` (Task 14 — página de comparação entre projetos),
`5e0f715` (fix de auditoria — estado vazio explícito nessa página)

## Checklist

- [x] **Back-end: testes passando.** Suite completa: 475 passed / 1 failed
  (`test_security.py::test_dependencias_separam_browser_automacoes_e_webhooks_publicos`
  — mesma falha pré-existente já documentada na verificação da Onda 1 desta
  mesma entrega e na Entrega 1, não relacionada). Teste de regressão golden
  (`test_golden_fixture_multidimensional_trava_de_regressao`) reconfirmado
  passando nesta sessão, isolado (`pytest -k golden` → 1 passed).
- [x] **UI: segue o contrato (seção 3.3 do spec).** `BarChart` agrupado do
  `recharts`, mesmo padrão visual de "SPI por sprint"/"SPI por operacional"
  já usado em `MetricasTab.tsx` — reaproveitado sem variação nas Tasks 13 e
  14. Nenhuma lib nova, nenhum padrão visual novo (tier PADRÃO confirmado
  correto retroativamente). Multi-seleção de projetos na Task 14 usa
  checkboxes com `<label>` em vez do `<select multiple>` sugerido no spec —
  decisão tomada no plano (Task 14), mais acessível que `<select multiple>`
  nativo, não é divergência não-intencional.
- [x] **UI: estados de loading/erro/vazio implementados.**
  `ElegibilidadeCard` (Task 12): loading ("Carregando..."), erro inline em
  vermelho, vazio ("Ninguém vinculado a este projeto nesta consulta.").
  Comparação dentro do projeto (Task 13): seção só aparece com ≥2 grupos de
  modo — padrão silencioso já usado pelas outras seções de gráfico do mesmo
  arquivo, não é regressão nova. Comparação entre projetos (Task 14): loading
  no botão ("Comparando..."), erro inline em vermelho, e — achado na
  auditoria desta sessão e corrigido no commit `5e0f715` — estado vazio
  explícito após busca sem resultado (diferente da Task 13, aqui a busca é
  ação do usuário, então silenciar o card escondia se a busca rodou de
  verdade).
- [x] **UI: variante escolhida fiel ao protótipo.** N/A — Etapa 8
  (prototipagem) foi pulada (tier PADRÃO, nenhum padrão visual novo,
  registrado em `.planning/feature-flow-state.md`).
- [x] **UI: auditoria da Etapa 11 sem issues abertos.** Auditoria fundida
  (Refactoring UI + taste; sem motion novo nesta feature) rodada nesta
  sessão sobre a Task 14 (única peça de UI ainda não revisada) — 1 issue
  Minor encontrado (estado vazio ausente) e corrigido antes desta
  verificação. Tasks 11-13 já tinham sido revisadas em sessão anterior sem
  issues abertos (ver histórico do commit).
- [x] **UI: acessibilidade básica (WCAG AA).** Checkboxes da Task 14 com
  `<label>` envolvendo o input (associação implícita); tabela da
  `ElegibilidadeCard` usa `<th scope="col">`; página nova segue o mesmo
  padrão de guard de cargo (lider/owner) + link "← Projetos" das páginas
  irmãs (`/performance`, `/pessoas`); botão "Comparar" com estado
  `disabled`+`opacity` visualmente distinto, não depende só de cor (texto
  muda para "Comparando..."). Gap conhecido e não-novo: o `<select>` de
  sprint em `ElegibilidadeCard` não tem `<label htmlFor>` explícito — mesmo
  padrão já deferido como não-bloqueante na verificação da Entrega 1.
- [x] **Integração back-end ↔ UI funcionando.** `ComparacaoModoPonto` (Task
  11, `api.ts`) bate campo a campo com o retorno de
  `comparar_modos_do_projeto`/`comparar_modos_entre_projetos`
  (`services/metricas_comparacao.py`); `ElegivelPonto` bate com o response
  do endpoint RF-C7 (Task 8). `npm run build` limpo (type-check completo).
  Endpoint `GET /metricas/comparacao-modos` (entre projetos, Task 10) sem
  restrição de cargo no back-end — consistente com o resto da API neste MVP
  (sem auth por endpoint no v1); o guard de cargo na página nova é
  client-side, mesmo modelo já usado por `/performance` e `/pessoas`.

## Itens fora do escopo desta verificação (não é regressão, não bloqueia)

- **Deploy:** migração manual do Supabase ainda pendente — a Task 1 desta
  entrega (`operacionais.data_entrada`/`data_saida`) precisa entrar no
  mesmo lote da migração já pendente da Entrega 1 (ver memória
  `project_manual_migrations.md` e aviso no plano, linha 2236).
- **Exportação CSV** — removida do escopo a pedido do usuário (Etapa 1).
- **Proração por tempo parcial numa sprint e histórico de múltiplos ciclos
  de entrada/saída** — rejeitados conscientemente na Etapa 1 (spec, seção
  4).

## Veredito

**Entrega 2 verificada e completa.** Todos os 7 itens do checklist mínimo
passam com evidência de execução real (suites de teste rodadas nesta
sessão, build limpo, revisão de código linha a linha da última peça de UI
pendente). Único achado da auditoria final (estado vazio ausente na página
de comparação entre projetos) foi corrigido antes de fechar. Nenhum item
pendente ou bloqueado no código. Único passo externo restante antes do
próximo deploy é operacional (rodar a migração manual do Supabase), não de
código.
