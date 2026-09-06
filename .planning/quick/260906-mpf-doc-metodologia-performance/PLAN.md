---
task: Documento de metodologia do Sistema de Acompanhamento de Performance, servido no app com acesso restrito a Líder e Gerente
date: 2026-09-06
slug: doc-metodologia-performance
mode: quick (inline)
---

## Objetivo

Escrever o documento de metodologia do Sistema de Acompanhamento de Performance da
subárea de Dados — como funciona, todas as regras, e o manual de uso pelo gerente —
fiel ao que está implementado, e disponibilizá-lo dentro do DocuData com acesso
restrito a `cargo ∈ {lider, gerente}` (bloqueado para `operacional`).

## Decisões

1. **Onde o markdown mora:** `docudata-backend/docs/metodologia-performance.md`.
   Fonte única. Fica junto do backend porque é o backend que o serve — evita
   duplicar o conteúdo no bundle do frontend e evita expor o arquivo estático
   sem gate (o que aconteceria em `frontend/public/`).
2. **Como é servido:** `GET /metodologia/performance` retornando `{ conteudo }`,
   com `Depends(require_not_operacional)` — o mesmo gate já usado por
   `painel`, `operacionais`, `metricas` e `avaliacoes` em `main.py`.
3. **Frontend:** página `/metodologia` renderizando com `react-markdown`
   (dependência já presente), com bloqueio client-side para `operacional`
   no mesmo padrão de `app/performance/page.tsx`. Link no header da home
   visível quando `auth?.cargo !== "operacional"`.
4. **Conteúdo:** descreve o sistema **como implementado** (fórmulas de
   `services/performance.py`, fechamento de `services/pontuacao.py`, regras de
   Kanban/Escopo de `routers/tasks.py`/`routers/sprints.py`, questionário de
   `AvaliacaoSemanalModal.tsx`), e registra num anexo as divergências entre a
   metodologia de referência e o que o código faz hoje.

## Tarefas

1. `docudata-backend/docs/metodologia-performance.md` — o documento.
2. `docudata-backend/routers/metodologia.py` — rota que serve o markdown.
3. `docudata-backend/main.py` — registrar o router com `require_not_operacional`.
4. `docudata-backend/tests/test_metodologia_rbac.py` — 401 sem cookie, 403 para
   operacional, 200 para gerente e líder, conteúdo não vazio.
5. `docudata-frontend/app/lib/api.ts` — `getMetodologiaPerformance()`.
6. `docudata-frontend/app/metodologia/page.tsx` — página renderizada.
7. `docudata-frontend/app/page.tsx` — link no header para não-operacional.

## Fora de escopo

- Alterar qualquer fórmula, peso ou regra do motor de score. Documentação apenas.
- Editor de conteúdo no app — o markdown é versionado no git, não editável pela UI.
