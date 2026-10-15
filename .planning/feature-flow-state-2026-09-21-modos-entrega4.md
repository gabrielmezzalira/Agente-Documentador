# Feature Flow State
feature: "Modos de Trabalho e Avaliação — Entrega 4 (fechamento de lacunas pós-deploy). Auditoria cética confirmou 3 lacunas reais na Entrega 3 recém-publicada: (1) sem trava de combinação inválida modo_trabalho/modo_avaliacao; (2) gerente ainda atribui task manualmente mesmo em projeto PULL, sem nenhuma restrição; (3) os 3 endpoints de migração de modo (preview/aplicar/desvincular) existem no backend, testados, mas zero botão/chamada no frontend — 100% inacessíveis hoje."
modo: "FULL"
tier: "PADRAO"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js 15 / React 19 (inline styles, sem Tailwind/design-system file)"
etapa: 12
etapa_nome: "Verificação final — automatizada concluída, checklist manual em navegador pendente"
gates_reusados: ["knowledge-graph"]
started_at: "2026-09-21T22:15:00Z"
last_saved: "2026-09-23T22:24:36Z"
status: "em_progresso"

## Concluído
- [x] Etapa 0 — Grafo de conhecimento reaproveitado (graphify-out cobre HEAD b65068a, sem mudanças desde então; gates_reusados: knowledge-graph)
- [x] Etapa 1 — Brainstorm (bounded) concluído e design aprovado pelo usuário
- [x] Etapa 2 — Plano salvo em docs/superpowers/plans/2026-09-21-modos-trabalho-entrega4-fechamento-lacunas.md (10 tasks, Onda 1 = Tasks 1-6 backend, Onda 2 = Tasks 7-10 frontend). Usuário escolheu execução inline (superpowers:executing-plans).
- [x] Onda 1 (backend) — Tasks 1-6 concluídas e commitadas (46005e7, e75d5f9, c14e8df, 09f2beb): modo_avaliacao derivado, PATCH /modos rejeita troca de modo_trabalho, migrar-modo grava modo_avaliacao, create_task/patch_task rejeitam operacional_id em PULL. Suíte completa do backend: 522 testes passando, 0 falhas.
- [x] Onda 2 (frontend) — Tasks 7-9 concluídas e commitadas (7d160a9, d8bde18, b82ae5c): previewMigrarModo/aplicarMigrarModo em api.ts, modal de migração + remoção do dropdown de modo_avaliacao na tela de Configurações, trava de atribuição manual (select "Operacional") escondida em PULL no TaskModal. `npx tsc --noEmit` limpo.
- [x] Task 10 (parcial) — suíte completa do backend rerodada após Onda 2 (522 passando, confirma zero regressão cruzada). Typecheck do frontend limpo.

## Pendência real (não fingir que foi feito)
Push feito para origin/main (b65068a..b82ae5c) a pedido do usuário — ele mesmo vai rodar o checklist de verificação manual (Task 10, Step 3 do plano) e reportar o resultado. Este agente não tem acesso de leitura ao .env (sandbox), por isso não executou o checklist sozinho. Se o usuário reportar algo quebrado, retomar por aqui — não assumir que "deu certo" sem a confirmação dele. Passos que ele vai conferir:
1. Migrar ATRIBUICAO -> PULL pela UI nova (preview mostra contagem correta, confirmar aplica, cancelar não aplica nada).
2. Task antiga com responsável em "planejado" perde o responsável e vira fila após migrar.
3. "Modo de avaliação da Entrega" mostra o texto derivado certo nos dois modos, sem dropdown.
4. Modal de criar/editar task esconde o select "Operacional" em PULL e mostra texto informativo/leitura.
5. /puxar e /devolver continuam funcionando após a migração.

## Contexto relevante
- Usuário com baixa confiança: relatório anterior ("Entrega 3 completa") tinha lacunas reais que só apareceram no uso real. Rigor de revisão não é opcional aqui.
- Auditoria cética completa (fork) confirmou, com arquivo:linha, exatamente as 3 lacunas — fato verificado no código (HEAD = b65068a, já em produção/pushed).
- `docudata-backend/graphify-out` já existe e cobre até b65068a — não regenerado.
- Endpoints já existentes e testados (não recriar): `GET /migrar-modo/preview`, `POST /migrar-modo` (`routers/projects.py:374,419`); `update_modos` (`routers/projects.py:284-328`, precisa mudar); `create_task`/`patch_task` (`routers/tasks.py:256,591`, precisam mudar); `TaskModal` (`TasksKanbanTab.tsx:105-118`, não recebe `modoTrabalho` hoje — precisa receber); tela de Configurações em `page.tsx` (~linha 441-604, `handleSalvarModos` é a causa raiz do bug: PATCH /modos nunca migra tasks).

## Design aprovado (brainstorm bounded, sem spec file)
1. **modo_avaliacao derivado**: `ModosProjetoUpdate` deixa de aceitar `modo_avaliacao`; `update_modos` sempre deriva (PULL→PONTOS_RELATIVO, ATRIBUICAO→PONTOS_ATRIBUIDOS) e grava histórico como hoje. `aplicar_migrar_modo` passa a setar `modo_avaliacao` junto com `modo_trabalho`. Frontend remove dropdown de modo_avaliacao, mostra como texto derivado; bloco piso/teto continua condicionado a PONTOS_RELATIVO sem mudança de lógica.
2. **PATCH /modos rejeita modo_trabalho** (422) — fecha a brecha na origem que causou o bug real (PATCH só trocava o campo, nunca migrava tasks). Continua aceitando pull_exigir_hidratacao/pull_piso_pontos/pull_teto. Frontend: dropdown "Modo de trabalho" na Config deixa de ir pro botão "Salvar" genérico; ao mudar, abre modal que chama GET /migrar-modo/preview automaticamente, mostra contagem, confirma com POST /migrar-modo; cancelar reverte o dropdown sem PATCH. Dados que já migraram errado antes desta entrega NÃO são tocados retroativamente (usuário confirmou: só muda daqui pra frente). POST /desvincular-planejado fica fora de escopo.
3. **Trava de atribuição manual em PULL, absoluta, sem exceção**: `create_task`/`patch_task` rejeitam (422) qualquer `operacional_id` vindo do gerente quando modo_trabalho=PULL. `/puxar` e `/devolver` são endpoints separados (escrevem direto na tabela) — não afetados. Frontend: `TaskModal` passa a receber prop `modoTrabalho`; quando PULL, select "Operacional" some (texto informativo na criação, leitura no modo edição).
4. Testes de back-end cobrindo os 3 pontos nunca pulados (regra invariável do tier).
5. Classificação brainstorming: **bounded** (fluxos já existentes) — sem spec file; próxima etapa vai direto pro /write-plan conforme Etapa 2 do feature-flow-lean (que exige plano com Onda 1/Onda 2 pra todo tier, mesmo bounded).
