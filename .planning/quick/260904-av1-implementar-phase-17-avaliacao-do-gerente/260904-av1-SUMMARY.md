---
phase: 17-avaliacao-do-gerente
plan: 01
subsystem: fullstack
tags: [fastapi, supabase, nextjs, avaliacao, rbac]

requires:
  - phase: 16-rbac-login-leve-e-papeis-de-acesso
    provides: require_not_operacional, get_current_pessoa, useAuth() no frontend, cargo (lider/gerente/operacional)
provides:
  - "tabela avaliacoes_gerente (operacional_id, gerente_id, sprint_id, resposta_1..7 escala 0-5, reaproveitada_de, criado_em, editavel_ate) — dado bruto pra Phase 18 (Motor de Score) consumir"
  - "sprints.avaliacao_completa_em — carimbo de avaliação semanal completa, sem trava adicional de comportamento"
  - "router avaliacoes.py: GET /avaliacoes/{sprint_id}/pendencias, POST /avaliacoes (upsert com janela de 48h), POST /avaliacoes/{sprint_id}/confirmar"
  - "botão Avaliação Semanal + AvaliacaoSemanalModal no SprintCard — pendências, formulário de 7 perguntas, reaproveitar de outro projeto, confirmação explícita"
affects: [18-motor-de-score]

actuals:
  tokens: null
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Upsert via UNIQUE(operacional_id, sprint_id) + janela editavel_ate=criado_em+48h — reenvio dentro da janela faz UPDATE na mesma linha, fora dela retorna 409 sem escrever nada"
    - "reaproveitada_de rastreia a avaliação de origem quando o gerente reusa respostas de outro projeto, mas o pré-preenchimento é sempre client-side (o gerente pode editar antes de salvar) — nunca aplicado automaticamente pelo backend"

key-files:
  created:
    - docudata-backend/routers/avaliacoes.py
    - docudata-backend/tests/test_avaliacoes_pendencias.py
    - docudata-backend/tests/test_avaliacoes_submit.py
    - docudata-backend/tests/test_avaliacao_semanal_confirmar.py
    - docudata-backend/tests/test_avaliacoes_rbac.py
    - docudata-frontend/app/components/AvaliacaoSemanalModal.tsx
  modified:
    - docudata-backend/supabase_schema.sql
    - docudata-backend/models/schemas.py
    - docudata-backend/main.py
    - docudata-frontend/app/lib/api.ts
    - docudata-frontend/app/components/SprintCard.tsx
    - docudata-frontend/app/projects/[id]/page.tsx

key-decisions:
  - "gerente_id nunca aceito no body do POST /avaliacoes — sempre pessoa['id'] da sessão (get_current_pessoa), fechando T-17-02 do threat model"
  - "Sem restrição de 'próprio squad' (AVAL-05 explícito): qualquer cargo=gerente/lider avalia qualquer operacional de qualquer projeto ao qual tenha acesso — aceito como comportamento pedido, não como bug (T-17-01)"
  - "ultima_avaliacao_outro_projeto expõe respostas de avaliação entre projetos diferentes — aceito na mesma postura já assumida em RBAC-02/AVAL-05 de que qualquer gerente acessa qualquer projeto (T-17-03)"
  - "Projeto não tem design-system/MASTER.md nem DESIGN.md formais — Task 3 seguiu diretamente o padrão visual já estabelecido em PlanningModal (inline styles, overlay+box, sem ARIA) em vez de gerar artefatos de design novos"

patterns-established:
  - "Pergunta 6 (evolução) é fixa nas 7 perguntas mas isolada semanticamente das outras 6 — Phase 18 vai lê-la separado de gerente_media para alimentar baseline_evolucao; nenhum cálculo acontece nesta phase"

requirements-completed: [AVAL-01, AVAL-02, AVAL-03, AVAL-04, AVAL-05]

coverage:
  - id: D1
    description: "Tabela avaliacoes_gerente com UNIQUE(operacional_id, sprint_id); resposta_1..7 restritas a 0-5 via CHECK no banco + Field(ge=0,le=5) no Pydantic"
    requirement: "AVAL-01"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_avaliacoes_submit.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /avaliacoes/{sprint_id}/pendencias retorna só operacionais com >=1 task na sprint sem avaliação ainda; POST /confirmar só grava avaliacao_completa_em quando a lista está vazia, senão 409 listando quem falta"
    requirement: "AVAL-02"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_avaliacoes_pendencias.py, tests/test_avaliacao_semanal_confirmar.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Upsert dentro de editavel_ate=criado_em+48h faz UPDATE na mesma linha; reenvio após a janela retorna 409 sem escrever"
    requirement: "AVAL-03"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_avaliacoes_submit.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "ultima_avaliacao_outro_projeto (respostas + projeto + data) incluído na resposta de pendências quando o operacional tem avaliação prévia em outro projeto; frontend só pré-preenche ao clicar 'Usar essas respostas', nunca automaticamente"
    requirement: "AVAL-04"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_avaliacoes_pendencias.py"
        status: pass
      - kind: other
        ref: "leitura de código: AvaliacaoSemanalModal.tsx reaproveitar() só roda dentro do onClick do botão 'Usar essas respostas'"
        status: pass
    human_judgment: false
  - id: D5
    description: "Toda rota de avaliacoes.router exige require_not_operacional (Gerente/Líder passam, Operacional 403), sem restrição de squad"
    requirement: "AVAL-05"
    verification:
      - kind: unit
        ref: "docudata-backend/tests/test_avaliacoes_rbac.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Botão 'Avaliação Semanal' aparece no SprintCard só pra cargo != operacional; abre modal, lista pendências, permite preencher/reaproveitar, confirma quando a lista zera; sprints local atualiza o chip ✓ sem reload"
    verification:
      - kind: other
        ref: "npx tsc --noEmit (0 erros) + npm run build (compila) — sem teste de componente React neste projeto, mesma convenção das phases anteriores"
        status: pass
    human_judgment: true
    rationale: "Comportamento de UI (fluxo pendências -> formulário -> salvar -> confirmar) não tem teste de componente automatizado; só compilação/build confirmam. Spot-check manual num dev server real não foi executado nesta sessão."

duration: unknown
completed: 2026-09-04
status: complete
---

# Quick Task 260904-av1: Phase 17 — Avaliação do Gerente

**Fluxo completo de "Avaliação Semanal": tabela avaliacoes_gerente + router avaliacoes.py com upsert de 48h e RBAC, mais o botão e modal no SprintCard que fecham a integração ponta a ponta — fecha AVAL-01..05 sem implementar nenhum cálculo de score (isso é Phase 18).**

## Performance

- **Completed:** 2026-09-04
- **Tasks:** 3
- **Files modified:** 10 (6 novos: 1 router + 4 testes + 1 componente; 6 modificados)

## Accomplishments

- `avaliacoes_gerente` (migração) + schemas Pydantic (`AvaliacaoGerenteCreate/Response`, `PendenciaAvaliacaoResponse`, `AvaliacaoAnteriorResponse`, `ConfirmarAvaliacaoResponse`) — dado bruto pronto pra Phase 18 consumir (AVAL-01)
- `routers/avaliacoes.py` — `listar_pendencias` (exclui quem já foi avaliado, inclui `ultima_avaliacao_outro_projeto` quando existe), `criar_ou_atualizar_avaliacao` (upsert com janela de 48h, 409 fora dela), `confirmar_avaliacao_semanal` (409 com lista de pendências se não zerou) — 13 testes cobrindo AVAL-01..05, todos passando
- Botão "Avaliação Semanal" no `SprintCard` (condicionado a `cargo !== "operacional"` via `useAuth()`) + `AvaliacaoSemanalModal.tsx` novo: lista pendências, formulário de 7 perguntas com chips 0-5, bloco de reaproveitar (pré-preenche só ao clicar "Usar essas respostas"), confirmação explícita quando a lista zera
- Integração em `page.tsx`: estado `avaliacaoModal`, render condicional do modal, `onCompleted` atualiza `sprints` local pro chip "✓" aparecer sem reload
- `tsc --noEmit` e `npm run build` sem erros novos; suíte backend 109 passed (4 falhas pré-existentes do MVP original, não relacionadas — confirmado via `git stash`)

## Task Commits

1. **Task 1: Migração avaliacoes_gerente + schemas** - `6205223` (feat)
2. **Task 2: Router avaliacoes.py — pendências, submit, confirmar** - `882f45c` (feat)
3. **Task 3: Frontend — botão + modal Avaliação Semanal** - `33bf1b3` (feat)

## Files Created/Modified

- `docudata-backend/supabase_schema.sql` - bloco `-- Phase 17`: tabela `avaliacoes_gerente` + `sprints.avaliacao_completa_em`
- `docudata-backend/models/schemas.py` - schemas de avaliação; `avaliacao_completa_em` em `SprintResponse` (herdado por `SprintStatusResponse`/`SprintBaselineResponse`)
- `docudata-backend/routers/avaliacoes.py` - novo, 3 endpoints
- `docudata-backend/main.py` - `avaliacoes.router` registrado com `dependencies=[Depends(require_not_operacional)]`
- `docudata-backend/tests/test_avaliacoes_pendencias.py`, `test_avaliacoes_submit.py`, `test_avaliacao_semanal_confirmar.py`, `test_avaliacoes_rbac.py` - novos, 13 testes
- `docudata-frontend/app/lib/api.ts` - tipos `AvaliacaoAnterior`/`PendenciaAvaliacao`/`AvaliacaoGerente`, `avaliacao_completa_em` em `SprintWithStatus`, funções `listPendenciasAvaliacao`/`submitAvaliacao`/`confirmarAvaliacaoSemanal`
- `docudata-frontend/app/components/AvaliacaoSemanalModal.tsx` - novo
- `docudata-frontend/app/components/SprintCard.tsx` - import `useAuth`, prop `onOpenAvaliacaoSemanal`, botão condicionado a `cargo`
- `docudata-frontend/app/projects/[id]/page.tsx` - import do modal, estado `avaliacaoModal`, prop passada ao `SprintCard`, render do modal

## Decisions Made

- `gerente_id` nunca vem do body do `POST /avaliacoes` — sempre `pessoa["id"]` da sessão via `get_current_pessoa`
- Sem restrição de "próprio squad" — qualquer `cargo=gerente/lider` avalia qualquer operacional de qualquer projeto ao qual tenha acesso, por instrução explícita de AVAL-05
- `ultima_avaliacao_outro_projeto` expõe respostas entre projetos diferentes — aceito na mesma postura já assumida em RBAC-02
- Sem design-system/DESIGN.md formal no projeto — Task 3 seguiu o padrão visual já existente de `PlanningModal` (inline styles, overlay+box) em vez de gerar artefatos de design novos, evitando trabalho de design redundante

## Deviations from Plan

Nenhum desvio de conteúdo. A sessão que implementou Task 3 encontrou o estado real do repositório divergente do state file de uma sessão paralela de `feature-flow-lean` (que ainda registrava "Etapa 1" apesar de Tasks 1-2 já estarem commitadas) — reconciliado antes de prosseguir; Task 3 foi executada exatamente conforme escrita no plano, sem alteração de código além de nomear a variável de callback do `.map` como `s2` (em vez de `s`, sombreando a variável externa) por clareza.

## Issues Encountered

`bcrypt` não estava instalado no ambiente local usado para rodar os testes — instalado via `pip3 install -r requirements.txt -r requirements-dev.txt` (aviso de conflito de versão do `langchain-google-genai` com um pacote global `hermes`, não relacionado a este projeto, sem impacto nos testes).

## User Setup Required

A migration em `docudata-backend/supabase_schema.sql` (bloco `-- Phase 17`) precisa ser aplicada manualmente no Supabase de produção, mesma convenção das phases anteriores.

## Next Phase Readiness

- AVAL-01..05 fechados. `avaliacoes_gerente` pronta para a Phase 18 (Motor de Score) ler como dado bruto — nenhum cálculo de score/SPI foi implementado aqui.
- Spot-check manual recomendado antes de considerar 100% fechada em produção: aplicar a migration, criar uma task numa sprint atribuída a um operacional, abrir "Avaliação Semanal" no SprintCard, preencher as 7 perguntas, confirmar, e verificar a linha em `avaliacoes_gerente` e `sprints.avaliacao_completa_em` no Supabase.

## Test Results

**Backend:**
```
tests/test_avaliacoes_pendencias.py tests/test_avaliacoes_submit.py tests/test_avaliacao_semanal_confirmar.py tests/test_avaliacoes_rbac.py: 13 passed
Suíte completa: 109 passed, 4 failed (pré-existentes, test_schemas_and_client.py — confirmado via git stash que já falhavam antes desta phase)
```

**Frontend:**
```
npx tsc --noEmit: 0 errors
npm run build: compila sem erros
```

---
*Phase: 17-avaliacao-do-gerente*
*Completed: 2026-09-04*

## Self-Check: PASSED

Todos os arquivos criados/modificados verificados em disco; os três commits de task (`6205223`, `882f45c`, `33bf1b3`) verificados presentes em `git log`; suíte de testes relevante (13 testes) e suíte completa (109 passed) executadas nesta sessão; `npx tsc --noEmit` e `npm run build` executados com sucesso.
