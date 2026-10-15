# Feature Flow State
feature: "Commits via GitHub Action independente do GitHub App — (1) chave de ingestão por projeto + workflow que manda todos os commits do push de qualquer branch + botão copiar workflow na tela; (2) sem duplicata entre App e Action."
modo: "FULL"
tier: "PADRAO"
stack: "FastAPI (Python) + Supabase PostgreSQL + Next.js 15 / React 19 (inline styles)"
etapa: 0
etapa_nome: "Brainstorm (bounded) — design apresentado, aguardando aprovação"
gates_reusados: ["knowledge-graph"]
started_at: "2026-09-24T02:15:00Z"
last_saved: "2026-09-24T12:56:08Z"
status: "em_progresso"

## Concluído
- [x] Etapa 0 — graphify-out reaproveitado
- [ ] Etapa 1 — Brainstorm ← PRÓXIMA

## Contexto relevante
- Feature anterior (dependência do cliente) commitada, NÃO pushada, estado em .planning/feature-flow-state-2026-09-23-dependencia-cliente.md.
- Causa raiz confirmada: merge f74f812 (PR #1 GitHub App, 12/09 16:39 -03) trouxe core/security.py e passou a exigir X-Docudata-Key em /ingest/commit e /current-sprint (main.py:186 app_key). Workflows nos repos não mandam/erram a chave → 401 desde então. Último commit registrado 12/09 14:47 -03. Commits antes vinham de várias branches (não era só main) — via Action.
- commit_qualidade 100% sem operacional_id: esperado, vínculo github_login/email só foi configurado recentemente (usuário confirmou). Não é escopo.
- Usuário colou DOCUDATA_APP_SECRET no chat — NUNCA gravar em arquivo/memória; recomendar rotação depois que chave por projeto estiver em uso.
- Rate limit /ingest/commit: GEMINI_RATE_LIMIT = 20/min (core/rate_limit.py).
- Dedup atual (commit_ja_ingerido) só funciona com repositorio_id (caminho App).
- UI GitHub App: aba config de app/[subarea]/projects/[id]/page.tsx:1634 (githubVisible depende de capabilities do App).
- Frontend conhece URL do backend via process.env.NEXT_PUBLIC_API_URL (next.config rewrites).
