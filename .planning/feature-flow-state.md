# Feature Flow State
feature: "Modos de Trabalho e de Avaliação — Entrega 2. (1) elegibilidade nova por entrada/saída de operacional no meio do projeto; (2) métricas comparativas entre modo A (ATRIBUICAO/PONTOS_ATRIBUIDOS) e modo B (PULL/PONTOS_RELATIVO), dentro do projeto e entre projetos. CSV export removido do escopo (usuário confirmou que não precisa)."
modo: "FULL"
tier: "PADRAO"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js 15 / React 19 (inline styles, sem Tailwind/design-system file, recharts já instalado)"
etapa: 12
etapa_nome: "Concluído"
gates_reusados: ["design-system", "design-doc (impeccable)", "libs (recharts)"]
started_at: "2026-09-21T11:00:00Z"
last_saved: "2026-09-21T13:10:00Z"
status: "concluido"

## Concluído
- [x] Etapa 0 — Onboarding de repositório: grafos reextraídos (AST puro, sem LLM). `docudata-backend/graphify-out` 1830 nós / 4366 edges (cobre até commit 2b93373). `docudata-frontend/graphify-out` 755 nós / 1472 edges.
- [x] Etapa 1 — Requisitos via `/brainstorm` (arquitetural, spec completa): `docs/superpowers/specs/2026-09-21-modos-trabalho-avaliacao-entrega2-design.md` (commit fe3f9f7). Decisões fechadas com o usuário: (1) vínculo temporal = colunas simples `data_entrada`/`data_saida` em `operacionais` (não tabela de histórico — sem suporte a múltiplos ciclos de entrada/saída); (2) elegibilidade = vínculo no momento do fechamento da sprint, sem proração (redefine "elegível" de "tem task" pra "está vinculado" — corrige o bug de PULL da Entrega 1 onde quem não puxava nada sumia, e resolve RF-C7 de quebra); (3) CSV export removido do escopo a pedido do usuário; (4) métricas comparativas cobrem AMBOS os escopos — dentro do projeto (sprints agrupadas por modo congelado) e entre projetos (seletor de 2+ projetos, mesma agregação). Efeito colateral assumido: contagem de avaliação pendente pode subir retroativamente em projetos PULL já com sprints fechadas (pontuação já travada não é recalculada, só a contagem de pendências daqui pra frente).
- [x] Etapa 2 — Plano de implementação via `/write-plan`: `docs/superpowers/plans/2026-09-21-modos-trabalho-avaliacao-entrega2.md` (commit 4ab20ea). 14 tasks em 2 ondas (backend Tasks 1-10, frontend Tasks 11-14), TDD completo, código exato pra cada step. Ponto mais delicado (Task 6): `calcular_e_travar_pontuacao` precisa criar linha zerada pra todo vinculado sem task, não só "não filtrar mais quem tem 0 alocado" — sem isso a Task 7 (remover o filtro de `_sequencia_pessoal`) não teria efeito nenhum, já que a linha nunca existiria pra começo de conversa. Descoberta feita durante a escrita do plano (não estava no spec original), ruling registrado no próprio plano.
- [x] Etapa 3 — Execução do back-end (Onda 1), Tasks 1-10. Todas revisadas individualmente e aprovadas — 6 tasks tiveram findings reais corrigidos (Task 1: backfill no-op por semântica de DDL do Postgres; Task 2: regressão em teste existente causada pelo próprio schema change, corrigida antes da review; Task 4: gap de cobertura no boundary exato de elegibilidade; Task 5 — o bug fix em si: mudança de comportamento auto-reportada e verificada correta, 3 arquivos de teste não listados no brief corrigidos como ripple effect esperado; Task 6 — task de maior risco: golden regression reverificado 2x (re-run + hand-trace); Task 9: mock do próprio plano tinha uma falha latente, corrigida com filtro defensivo verificado seguro). Suite final: 475 passed/1 failed (falha pré-existente conhecida, não relacionada). Golden regression confirmado intacto no fechamento da onda.
- [x] Etapa 4/5/6 — Gates de reuso (Design System / Impeccable / Bibliotecas): PADRAO reaproveitado da Entrega 1 — mesma convenção inline-style, `recharts` já em uso (MetricasTab.tsx), nenhum componente visualmente novo nas Tasks 11-14. Nada gerado/regenerado.
- [x] Etapa 7/8/9 — Contrato de UI reaproveitado da seção 3.3 do spec (sem UI-SPEC.md formal, tier PADRÃO) + prototipagem pulada (nenhum padrão visual novo) + auditoria de motion/taste sem achados (feature não introduz animação nova).
- [x] Etapa 10 — Execução da UI (Onda 2). Tasks 11-13 (api.ts, ElegibilidadeCard em PainelTab, comparação dentro do projeto em MetricasTab) já estavam commitadas ao retomar esta sessão (`9a18565`, `26d2254`, `fbcffc3`). Task 14 (página `/comparacao-modos` entre projetos) implementada nesta sessão: TDD completo (teste falhando → implementação → passa), seguindo o padrão real de página top-level cargo-gateada (`useAuth`, restrição lider/owner, link "← Projetos") em vez do snippet incompleto do plano, que omitia isso apesar de listá-lo em "Interfaces". Nav link adicionado em `page.tsx` (não estava no plano, necessário pra tornar a página alcançável). Commit `80f2ff4`.
- [x] Etapa 11 — Auditoria final fundida: revisão da Task 14 (única peça de UI ainda não revisada) achou 1 issue Minor — card de resultado ficava silenciosamente vazio após busca sem match, sem distinguir "não buscou ainda" de "buscou e não achou nada" (diferente da Task 13, aqui a busca é ação explícita do usuário). Corrigido no commit `5e0f715`. Sem achados de motion (feature não introduz animação nova) nem de acessibilidade novos além do gap já deferido na Entrega 1 (select sem `<label>` em `ElegibilidadeCard`, mesmo padrão).
- [x] Etapa 12 — Verificação final: `docs/superpowers/plans/2026-09-21-modos-trabalho-avaliacao-entrega2-VERIFICACAO.md`. Backend 475 passed/1 failed (pré-existente, mesma de sempre), golden regression reconfirmado isolado, frontend 26/26 + build limpo. Veredito: Entrega 2 completa, sem pendência de código. Único passo externo restante é a migração manual do Supabase antes do próximo deploy (já valia pra Entrega 1, soma o schema novo da Task 1 desta entrega no mesmo lote).

**FEATURE CONCLUÍDA.**

## Contexto relevante (levantamento já feito — não repetir)

### Decisão de tier (sem pergunta ao usuário, sessão em modo "continue sempre")
PADRAO: nenhum dos 3 itens exige padrão visual genuinamente novo — `recharts` já está em `package.json` e já é usado em `MetricasTab.tsx` (gráficos e tabelas), CSV export é geração client-side simples sem lib nova, elegibilidade é lógica de backend + extensão da UI de config já existente. Se a exploração de requisitos (Etapa 1) revelar que "métricas comparativas modo A x B" precisa de um tipo de visualização sem análogo em `MetricasTab.tsx`, subir o tier pra COMPLEXA (Regra Inviolável 4).

### Entrega 1 (Base) — completa, referência
- Plano: `docs/superpowers/plans/2026-09-20-modos-trabalho-avaliacao-entrega1.md`
- Spec: `docs/superpowers/specs/2026-09-20-modos-trabalho-avaliacao-design.md`
- Verificação: `docs/superpowers/plans/2026-09-20-modos-trabalho-avaliacao-entrega1-VERIFICACAO.md`
- Commits: `fe4489e`..`2b93373` (main direto)
- **AVISO DE DEPLOY AINDA PENDENTE:** migração manual do Supabase da Entrega 1 (`projects.modo_*`, `configuracao_historico`, `sprints.modo_*`/`hibrida`, `pontuacao_eventos`, `pontuacao_operacional_sprint.entrega_modo`) — ver `docudata-backend/supabase_schema.sql:684-733` e memória `project_manual_migrations.md`. Se ainda não rodou em produção, qualquer schema novo da Entrega 2 deve ser somado ao mesmo lote de migração pendente, não rodado isoladamente.

### Modelo de dados já existente (não recriar)
- `projects.modo_trabalho` (ATRIBUICAO/PULL), `modo_avaliacao` (PONTOS_ATRIBUIDOS/PONTOS_RELATIVO), `pull_exigir_hidratacao`, `pull_piso_pontos`, `pull_teto`
- `sprints.modo_trabalho`/`modo_avaliacao` (congelados no fechamento), `hibrida`
- `pontuacao_eventos` (ledger auditável), `pontuacao_operacional_sprint.entrega_modo`
- `configuracao_historico` (log de troca de modo)

### Achados relevantes pra elegibilidade (item 1) — do brainstorm da Entrega 1
- Hoje não existe conceito de "entrada/saída de operacional no meio do projeto" no schema — precisa investigar se `operacionais` tem vínculo temporal com `projects` ou é só um vínculo binário sem histórico.
- RF-C7 do SDD original (listar elegíveis da sprint com contagem de cada um, auditável) foi adiado pra cá — `routers/metodologia.py` hoje só serve markdown estático, não tem endpoint dinâmico.

### Stack e convenções do frontend (reaproveitar, não regenerar)
- Sem Tailwind, sem design-system/MASTER.md, sem DESIGN.md formal — inline `style={{}}`, tokens repetidos (paleta verde `#22c55e`/`#166534`, cinzas `#f4f4f7`/`#f7f7fa`/`#9696a0`/`#b8b8c0`, alerta `#dc2626`).
- `MetricasTab.tsx` já tem padrão de `<table>` (`thSt`/`tdSt` consts locais) e usa `recharts` — reaproveitar pra métricas comparativas em vez de inventar visualização nova.
- Sub-componentes sempre inline no arquivo que usa (nunca arquivo novo pra componente pequeno).

---

## Histórico — Entrega 1 (Base), concluída 2026-09-21

<details>
Todas as 12 tasks implementadas, revisadas individualmente, revisão final de todo o plano limpa (Ready to merge: Yes), verificação final documentada. Ver `docs/superpowers/plans/2026-09-20-modos-trabalho-avaliacao-entrega1-VERIFICACAO.md` pro relatório completo e `docs/superpowers/plans/2026-09-20-modos-trabalho-avaliacao-entrega1.md` pro plano com as 12 tasks.

Achados que ainda podem ser relevantes pra Entrega 2:
- `services/performance.py::_sequencia_pessoal` filtra `.gt("entrega_pontos_alocados", 0)` — em PULL quem não puxou nada some da sequência em vez de aparecer com 0.
- `routers/avaliacoes.py::_operacionais_com_task_na_sprint` deriva quem é avaliado a partir de `tasks.operacional_id` — em PULL quem não puxou nada nunca é avaliado.
- `routers/metodologia.py` serve markdown estático — RF-C7 (listar elegíveis com contagem, auditável) precisa de endpoint dinâmico, ainda não existe.
- Motor de score: `services/pontuacao.py::calcular_e_travar_pontuacao`, `services/performance.py` (5 dimensões, janelas sprint/quinzenal/mensal), `_score_final` redistribui peso de dimensão indisponível.
- Banco: `supabase_schema.sql` nunca roda sozinho — sempre migração manual (memória `project_manual_migrations.md`).
</details>
