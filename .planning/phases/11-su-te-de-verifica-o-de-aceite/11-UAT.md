---
status: partial
phase: 11-su-te-de-verifica-o-de-aceite
source: [11-VERIFICATION.md]
started: 2026-08-23T21:00:00Z
updated: 2026-08-23T22:00:00Z
---

## Current Test

[testing paused — 6 items outstanding]

## Tests

### 1. Migration SQL aplicada no Supabase
expected: |
  Executar bloco Phase 11 em supabase_schema.sql no SQL Editor do Supabase.
  SELECT * FROM execucoes_aceite LIMIT 1 — sem erro.
  \d projects mostra colunas github_token e github_repo.
  \d funcionalidades mostra coluna testes_e2e.
result: skipped
reason: "Usuário pausou UAT para discutir a próxima fase"

### 2. PATCH /funcionalidades/{id} com status=concluida — timing e background
expected: |
  PATCH retorna HTTP 200 imediatamente (não espera o background task).
  Após alguns segundos, linha aparece em execucoes_aceite no Supabase (5 gates sem_cobertura se github não configurado).
result: [pending]

### 3. POST /ingest/aceite end-to-end com UUID real
expected: |
  POST /ingest/aceite com payload {"funcionalidade_id": "<uuid>", "commit_sha": "abc123", "gates": [{"nome":"build","resultado":"passou"}]}
  Retorna {"status": "ok", "funcionalidade_id": "<uuid>"}.
  Linha em execucoes_aceite tem gates e concluido_em preenchidos.
result: [pending]

### 4. GET /projects/{id}/painel retorna cobertura_aceite no root
expected: |
  GET /projects/{id}/painel retorna JSON com campo cobertura_aceite: float | null no nível raiz.
  bloco_a.pct_escopo_concluido não é alterado pela presença de dados de aceite.
result: [pending]

### 5. Browser — badge ⚠ aceite no Kanban coluna Concluído
expected: |
  Funcionalidade concluída com gate falhou/erro exibe badge ⚠ aceite vermelho.
  Inspeção DOM: zero className no badge e nos elementos de aceite (apenas style={{}}).
result: [pending]

### 6. Browser — Bloco B sub-seção Cobertura de Aceite
expected: |
  Painel exibe sub-seção "Cobertura de Aceite" no Bloco B listando funcionalidades concluídas com suíte falhando.
  Nenhum className nos elementos adicionados (apenas style={{}}).
result: [pending]

### 7. GitHub Actions workflow trigger
expected: |
  POST /repos/{owner}/{repo}/dispatches com event_type docudata-aceite dispara o workflow aceite.yml.
  Workflow corre aceite_agent.py e faz POST /ingest/aceite ao DocuData.
  Job completa com continue-on-error (nunca falha o CI do projeto mesmo se aceite_agent falhar).
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 6
skipped: 1
blocked: 0

## Gaps
