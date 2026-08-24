---
status: testing
phase: 12-boletim-de-aceite-encerramento-e-resumo-semanal
source: [12-VERIFICATION.md]
started: 2026-08-24T00:00:00Z
updated: 2026-08-24T00:00:00Z
---

## Current Test

number: 1
name: Fluxo completo boletim end-to-end
expected: |
  Gerente consegue percorrer todo o fluxo na aba Aceite; boletim aparece na lista
  com status correto; status_cliente das funcionalidades muda correspondentemente
awaiting: user response

## Tests

### 1. Fluxo completo boletim: seleção → POST /boletins → preview → enviado → aprovado
expected: Gerente consegue percorrer todo o fluxo na aba Aceite; boletim aparece na lista com status correto; status_cliente das funcionalidades muda correspondentemente
result: [pending]

### 2. PATCH /boletins/{id} com transição inválida (rascunho→aprovado) retorna 422
expected: HTTP 422 com mensagem 'Transição inválida: rascunho → aprovado'
result: [pending]

### 3. PATCH /boletins/{id} com status=ajuste sem retorno_tipo retorna 422
expected: HTTP 422 com 'retorno_tipo é obrigatório quando status = ajuste'
result: [pending]

### 4. Badge "Projeto encerrado" aparece quando todas as funcionalidades têm status_cliente=aprovado
expected: div com texto 'Projeto encerrado — todas as funcionalidades aprovadas' visível no topo da aba Aceite
result: [pending]

### 5. POST /boletins/resumo_semanal retorna markdown estruturado com seções corretas
expected: Markdown com cabeçalho de período dom-sáb, seções de anomalias ou 'Nenhuma anomalia identificada nesta semana.', salvo em generated_docs
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
