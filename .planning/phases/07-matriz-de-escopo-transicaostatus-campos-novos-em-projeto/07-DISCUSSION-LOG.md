# Phase 7 Discussion Log

**Date:** 2026-08-22
**Mode:** BACK-ONLY (feature-flow)

## Área 1 — Importação em massa

**Pergunta:** A importação em massa entra na Fase 7?
**Resposta:** Sim, entra junto com o CRUD manual.

**Pergunta:** LangGraph ou chamada direta ao Gemini?
**Resposta:** LangGraph — grafo novo.

**Pergunta:** Revisão item a item ou tudo ou nada?
**Resposta:** Item a item com checkbox.

## Área 2 — Critérios de aceite EARS

**Pergunta:** Backend valida formato EARS ou texto livre?
**Resposta:** Texto livre — sem validação de formato. Gemini gera sugestões EARS via prompt, gerente edita livremente.

## Área 3 — TransicaoStatus: onde calcular

**Pergunta:** Cálculo no Python (handler PATCH) ou trigger Supabase?
**Resposta:** Python — no handler PATCH. Mais testável, sem dependência de trigger SQL.

## Área 4 — Campos novos em Projeto

**Pergunta:** Endpoint existente PATCH /projects/{id} ou separado?
**Resposta:** Endpoint separado PATCH /projects/{id}/contrato.

## Ideias diferidas

- Validação de formato EARS
- Transação explícita para race condition em TransicaoStatus
- Vínculo automático funcionalidade ↔ branch (descartado no SDD)
- RLS nas tabelas novas (junto com auth geral)
