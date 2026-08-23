# Phase 8: Painel do Gerente + Kanban de Sprint - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-22
**Phase:** 08-painel-do-gerente-kanban-de-sprint
**Areas discussed:** Localização e layout do painel, Kanban (qual sprint / colunas), Backend vs. frontend para cálculos, Squad no Bloco C

---

## Localização e Layout do Painel

| Option | Description | Selected |
|--------|-------------|----------|
| Nova aba 'Painel' | 7a aba, entre Sprints e Tecnologias. Painel + Kanban na mesma aba. | ✓ |
| Seção fixa acima das abas | Painel sempre visível no topo, independente da aba ativa. | |
| Dentro da aba Sprints | Painel e Kanban no topo da aba Sprints, antes das SprintCards. | |

**User's choice:** Nova aba 'Painel'
**Notes:** Usuário pediu esclarecimento sobre o que são os 4 blocos antes de confirmar o layout. Após explicação (Bloco A = Tempo × Escopo, B = Itens travados, C = Métricas de fluxo, D = Tempo por fase), confirmou grid 2×2 + kanban abaixo.

---

### Bloco A sem dados de contrato

| Option | Description | Selected |
|--------|-------------|----------|
| Card cinza 'Sem dados de contrato' | Card visível mas desativado, com link para Configurações. Grid permanece 2×2. | ✓ |
| Card oculto — grid passa a 1×3 | Bloco A some quando sem dados. | |
| Mensagem inline no lugar dos percentuais | Card renderiza normal mas percentuais ficam como '—'. | |

**User's choice:** Card cinza com link para Configurações.
**Notes:** Nenhuma observação adicional.

---

### Detalhe do Bloco D

| Option | Description | Selected |
|--------|-------------|----------|
| Expandir bloco (acordeom) | Lista inline expande abaixo do resumo ao clicar em 'ver detalhe'. | ✓ |
| Modal com tabela | Botão 'Ver todas' abre modal com tabela funcionalidade × fase. | |
| Tooltip ao passar o mouse | Cada linha abre tooltip com funcionalidades. | |

**User's choice:** Acordeom expansível
**Notes:** Usuário pediu esclarecimento sobre o que seria o "detalhe individual". Após explicar (lista de funcionalidades individuais com tempos por fase), confirmou acordeom.

---

## Kanban — Qual Sprint e Colunas

### Sprint exibida

| Option | Description | Selected |
|--------|-------------|----------|
| Sprint mais recente automaticamente | Sem interação, carrega a sprint de maior número. | |
| Seletor de sprint (dropdown) | Dropdown com todas as sprints do projeto. | ✓ |
| Kanban agrega todas as sprints ativas | Exibe funcionalidades de todas as sprints abertas. | |

**User's choice:** Seletor de sprint (dropdown)
**Notes:** Nenhuma observação adicional.

---

### Definição de "Transbordou"

| Option | Description | Selected |
|--------|-------------|----------|
| Carry-over da sprint anterior | sprint_alvo < sprint_selecionada E status != concluida. | |
| Marcação explícita pelo gerente | Novo status ou flag no banco. | |
| Funcionalidade de sprint anterior ainda em_andamento | Semanticamente mais preciso. | |

**Clarificação:** Usuário perguntou se o kanban é de funcionalidades ou de tasks. Após explicar que são funcionalidades (fase 7, com critérios EARS), usuário escolheu remover a coluna Transbordou inteiramente.

---

### Colunas do Kanban

| Option | Description | Selected |
|--------|-------------|----------|
| 4 colunas (SDD original) | Planejado / Em andamento / Concluído / Transbordou | |
| 3 colunas | Planejado (nao_iniciada) / Em andamento (em_andamento + em_ajuste) / Concluído (concluida) | ✓ |

**User's choice:** 3 colunas — Transbordou não faz sentido para funcionalidades que podem span múltiplas sprints.
**Notes:** Usuário explicou que funcionalidades podem ser "destrinchadas" entre sprints — não precisam ser 100% concluídas em uma sprint. Isso tornou a coluna Transbordou redundante.

---

### Indicador multi-sprint

| Option | Description | Selected |
|--------|-------------|----------|
| Badge na funcionalidade com as sprints | Chip 'Sprint 1 · Sprint 2' no card. | ✓ |
| Sem indicador | Simples — o gerente sabe que é multi-sprint. | |
| Contador no header da coluna | Número indicando quantas funcionalidades vêm de sprints anteriores. | |

**User's choice:** Badge no card com as sprints em que a funcionalidade aparece.

---

## Backend vs. Frontend para Cálculos

### Onde ficam os cálculos

| Option | Description | Selected |
|--------|-------------|----------|
| Endpoint dedicado GET /projects/{id}/painel | Backend calcula e retorna JSON. Frontend só renderiza. | ✓ |
| Frontend calcula a partir dos dados carregados | JS calcula percentis, dias úteis etc. | |
| Híbrido | Blocos A/B no frontend, C/D via endpoint. | |

**User's choice:** Endpoint dedicado.
**Notes:** Nenhuma observação adicional.

---

### Registro do desvio (Bloco A)

| Option | Description | Selected |
|--------|-------------|----------|
| Só alerta visual — sem persistir no banco | desvio_detectado: bool no response. | ✓ |
| Gravar em tabela de alertas | Nova tabela com histórico de detecções. | |
| Gravar campo em projects | Campo ultimo_desvio_detectado_em. | |

**User's choice:** Só alerta visual.

---

### Cálculo de "travadas" no Bloco B

| Option | Description | Selected |
|--------|-------------|----------|
| MAX(transicoes_status.timestamp) | Se hoje - ultima_transicao > 7 dias E status = em_andamento. | ✓ |
| updated_at da tabela funcionalidades | Mais simples mas menos preciso. | |
| Data da última transição para em_andamento | Conta só o tempo desde que entrou em em_andamento. | |

**User's choice:** MAX(transicoes_status.timestamp) — usa dados já existentes.

---

## Squad no Bloco C

### O que é "squad"

**User's clarification:** "o responsavel é algum membro do squad" — `responsavel` é uma pessoa, não um squad. Cada projeto tem um único squad.

| Option | Description | Selected |
|--------|-------------|----------|
| responsavel = squad | Agrupar por responsavel como proxy. | |
| Novo campo squad nas funcionalidades | Migration + campo squad separado. | |
| Sem agrupamento — métricas do projeto inteiro | Cada projeto = um squad, sem breakdown. | ✓ |

**User's choice:** Sem agrupamento — projeto inteiro é o squad.
**Notes:** Usuário esclareceu que cada projeto tem um único squad. Métricas do Bloco C agregam o projeto todo.

---

### Janela de tempo do Bloco C

| Option | Description | Selected |
|--------|-------------|----------|
| Projeto inteiro desde a primeira funcionalidade | Sem janela deslizante. | ✓ |
| Últimas 4 semanas | Janela deslizante. | |
| Sprint selecionada no dropdown do kanban | Coerente visualmente mas cycle time curto demais. | |

**User's choice:** Projeto inteiro.

---

### Cycle time

| Option | Description | Selected |
|--------|-------------|----------|
| De em_andamento até concluida | Exclui tempo de fila em nao_iniciada. | ✓ |
| De nao_iniciada até concluida (lead time) | Inclui tempo de espera. | |
| De em_andamento até aprovado pelo cliente | Inclui aprovação do cliente. | |

**User's choice:** De em_andamento até concluida.

---

## Claude's Discretion

- **Fórmula de eficiência de fluxo (Bloco D):** usuário não especificou. Claude decide — sugestão: `tempo_em_andamento / tempo_total × 100%`.
- **Cálculo de dias úteis (Bloco B):** aproximar como `dias_corridos × 5/7` sem biblioteca de feriados.
- **Throughput (Bloco C):** funcionalidades concluídas por semana, média sobre semanas com atividade.
- **p50/p85:** percentil da distribuição de cycle times de funcionalidades concluídas; `null` se nenhuma concluída.

## Deferred Ideas

- Coluna "Transbordou" (SDD original com 4 colunas) — removida por decisão do usuário.
- Histórico persistido de alertas de desvio — banco opcional para análise futura.
- Filtro por janela deslizante no Bloco C — deferido para v2.
- Drag-and-drop no kanban para mudar status — kanban é read-only nesta fase.
- Múltiplos squads por projeto com campo `squad` nas funcionalidades — deferido.
