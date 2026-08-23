---
id: "09-02"
phase: "09-revisor-diario-generalizado"
plan: "02"
status: complete
completed_at: "2026-08-23T00:00:00Z"
---

# Plan 09-02 Summary — Agente cliente + workflow + frontend toggle

## What Was Built

**revisor_agent.py (`docudata-backend/hooks/revisor_agent.py`):**
- Apenas Python stdlib (os, subprocess, json, urllib.request, urllib.error, datetime)
- Guarda DOCUDATA_API_URL e DOCUDATA_PROJECT_ID: encerra com SystemExit(0) silencioso se ausentes
- `git log --since="24 hours ago" --no-merges --pretty=%H|%s` — lista commits do período
- Guard de commits vazios: encerra silenciosamente sem chamar POST /ingest/revisao (D-02)
- Agrega diffs de cada commit via `git show hash --unified=3 --no-color`
- Trunca diff em 100.000 chars com sufixo `[DIFF TRUNCADO EM 100k CHARS]` (D-04)
- Guard adicional: encerra se diff agregado vazio após joins
- Envia payload completo a `POST /ingest/revisao` com: project_id, data_revisao, diff_agregado, commits_analisados, diff_chars_total, lista_commits

**revisor.yml (`docudata-backend/hooks/revisor.yml`):**
- `on.schedule.cron: '0 8 * * *'` — cron diário 08:00 UTC / 05:00 BRT (D-01)
- `workflow_dispatch: {}` — permite trigger manual para teste
- `continue-on-error: true` em job e step run (D-09 best-effort)
- `permissions: contents: read` — somente leitura
- `fetch-depth: 0` — histórico completo para git log --since funcionar

**api.ts (`docudata-frontend/app/lib/api.ts`):**
- Interface `AchadoCritico` exportada com 5 campos (severidade, confianca, referencia, descricao_tecnica, descricao_gerente)
- Interface `BlocoB` expandida com 4 campos opcionais: achados_criticos?, relatorio_gerente?, relatorio_tecnico?, data_revisao?
- Retrocompatibilidade garantida (campos opcionais — projetos sem revisor não quebram)

**PainelTab.tsx (`docudata-frontend/app/components/PainelTab.tsx`):**
- `AchadoCritico` importado de api.ts
- `BlocoBCard` tem `useState<"gerente" | "tecnico">("gerente")` local (D-08)
- Sub-seção "Achados do Revisor" só renderiza quando `bloco.achados_criticos !== undefined`
- Toggle "Gerente"/"Técnico" com botões inline-styled; padrão inicial "gerente" (D-08)
- Exibe data_revisao quando presente
- Lista achados com borderLeft vermelho, chip de severidade colorido por nível
- Exibe referencia (arquivo:linha) apenas no modo "Técnico"
- Texto da descrição alterna entre descricao_gerente / descricao_tecnica
- Caixa de relatório consolidado com background #f7f7fa, alterna entre gerente/técnico
- Zero className em todo o arquivo (constraint mantida)

## Self-Check: PASSED

- `revisor_agent.py` — `ast.parse` confirma apenas stdlib
- `revisor.yml` — cron `0 8 * * *`, fetch-depth 0, continue-on-error true em job e step
- `api.ts` — AchadoCritico presente, achados_criticos? em BlocoB
- `PainelTab.tsx` — zero className, visaoRelatorio, achados_criticos presentes
- `npx tsc --noEmit` → sem erros

## Artifacts Modified

- `docudata-backend/hooks/revisor_agent.py` — criado (novo arquivo)
- `docudata-backend/hooks/revisor.yml` — criado (novo arquivo)
- `docudata-frontend/app/lib/api.ts` — AchadoCritico + BlocoB expandida
- `docudata-frontend/app/components/PainelTab.tsx` — import + visaoRelatorio state + achados section
