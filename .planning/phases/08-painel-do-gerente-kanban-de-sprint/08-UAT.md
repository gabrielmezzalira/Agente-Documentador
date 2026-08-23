---
status: testing
phase: 08-painel-do-gerente-kanban-de-sprint
source: [08-VERIFICATION.md]
started: "2026-08-22T00:00:00Z"
updated: "2026-08-22T00:00:00Z"
---

## Current Test

number: 1
name: Bloco A sem_dados placeholder
expected: |
  Abrir a aba Painel em um projeto sem data_inicio/data_fim_contratada.
  Bloco A mostra "Sem dados de contrato" em cinza e um botão "Ir para Configurações".
  Clicar no botão muda a aba ativa para Configurações.
awaiting: user response

## Tests

### 1. Bloco A — placeholder sem dados de contrato
expected: Bloco A renderiza placeholder cinza com "Sem dados de contrato" e botão que navega para Configurações
result: [pending]

### 2. Bloco A — percentuais e badge de desvio
expected: Com data_inicio e data_fim_contratada configurados, Bloco A mostra três barras (Prazo consumido, Escopo concluído, Aprovado pelo cliente). Se (% prazo − % aprovado) > tolerancia, aparece badge laranja "⚠ Desvio de X pts acima da tolerância"
result: [pending]

### 3. Bloco B — três sub-seções com dados reais
expected: Com funcionalidades em em_andamento >7 dias, status_cliente=enviado >5 d.u., e em_ajuste — Bloco B mostra as três sub-seções com os itens corretos e badges coloridos
result: [pending]

### 4. Bloco C — cycle time null com zero concluídas
expected: Em projeto sem funcionalidades concluídas, Bloco C mostra "Nenhuma funcionalidade concluída — cycle time indisponível" no lugar das linhas de cycle time
result: [pending]

### 5. Bloco D — accordion expandir/colapsar
expected: Clicar "▼ ver detalhe" em uma fase expande a lista de funcionalidades com dias. Clicar "▲ fechar" colapsa. Apenas uma fase expandida por vez.
result: [pending]

### 6. Kanban — sprint dropdown com default no mais recente
expected: O dropdown de sprint inicia selecionando o maior número de sprint. Trocar a seleção refíltra as três colunas imediatamente sem recarregar
result: [pending]

### 7. Kanban — badges de sprint múltipla (D-08)
expected: Uma funcionalidade com o mesmo id_funcional em múltiplas sprints aparece com múltiplos chips roxos ("Sprint 1", "Sprint 2") no card do Kanban
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
