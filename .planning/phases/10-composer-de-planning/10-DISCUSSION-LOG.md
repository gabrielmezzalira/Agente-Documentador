# Phase 10: Composer de Planning - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-23
**Phase:** 10-Composer de Planning
**Areas discussed:** Onde o rascunho é salvo, O que é o recorte, Como o planning oficial é gerado, Onde o composer vive no frontend

---

## Onde o rascunho é salvo

| Option | Description | Selected |
|--------|-------------|----------|
| Nova tabela no Supabase | Tabela `planning_rascunhos` — sobrevive a troca de browser/máquina | ✓ |
| localStorage do frontend | Simples, zero backend novo; perde ao trocar browser/incognito | |
| Dentro do registro de Sprint | Campos extras na tabela sprints; mistura metadado com estado de wizard | |

**Descarte do rascunho:**

| Option | Description | Selected |
|--------|-------------|----------|
| Ao confirmar o planning oficial | Rascunho some ao confirmar; sempre persistido antes disso | ✓ |
| Ao confirmar OU após 7 dias | TTL de 7 dias evita acumular rascunhos abandonados | |
| Gerente descarta manualmente | Botão 'Descartar rascunho' no wizard | |

---

## O que é o recorte

| Option | Description | Selected |
|--------|-------------|----------|
| Lista de índices dentro de criterios_aceite | `{funcionalidade_id: [0, 2]}` — não altera tabela funcionalidades | ✓ |
| Campo separado na funcionalidade | `criterios_sprint_atual` na tabela funcionalidades | |
| Lista de textos (cópias dos critérios) | Texto copiado no rascunho — resistente a alterações posteriores | |

**Comportamento sem critérios selecionados:**

| Option | Description | Selected |
|--------|-------------|----------|
| Bloqueia avançar no wizard | Botão 'Próximo' desabilitado + aviso inline | ✓ |
| Assume todos os critérios por padrão | Se não mexer no recorte, todos entram | |
| Permite avançar com aviso | Warning mas não bloqueia | |

---

## Como o planning oficial é gerado

| Option | Description | Selected |
|--------|-------------|----------|
| Backend monta markdown diretamente (sem Gemini) | Markdown determinístico, sem custo, instantâneo | |
| Usa Gemini para gerar o texto do planning | Texto mais rico, mas latência e custo adicionais | ✓ |
| Reutiliza POST /sprint-docs/planning existente | Endpoint atual espera multipart/upload; requereria adaptação | |

**Confirmação humana:**

| Option | Description | Selected |
|--------|-------------|----------|
| Preview do markdown + botão 'Confirmar Planning' | Gerente lê e confirma | ✓ |
| Confirmar sem preview | Menos interações, mas sem revisão prévia | |
| Preview + possibilidade de editar o markdown | Editor inline — scope creep | |

**Integração ao fluxo existente:**

| Option | Description | Selected |
|--------|-------------|----------|
| Novo endpoint POST /composer/confirmar | Salva direto em generated_docs sem ingestion | ✓ |
| Reutiliza POST /sprint-docs/planning | Requereria refatoração do endpoint existente | |
| Salva apenas no rascunho | Não integra em generated_docs; desconexo do sistema | |

---

## Onde o composer vive no frontend

| Option | Description | Selected |
|--------|-------------|----------|
| Nova aba 'Planning' no dashboard do projeto | Tabs.tsx existente; wizard dentro da aba | ✓ |
| Nova página /projects/[id]/planning | Rota separada; perde contexto do dashboard | |
| Modal sobre o dashboard | Wizard em modal; dificulta múltiplos passos | |

**Layout do wizard:**

| Option | Description | Selected |
|--------|-------------|----------|
| Steps horizontais no topo + painel abaixo | Barra de progresso visual + Anterior/Próximo | ✓ |
| Accordion com 4 passos expansíveis | Ordem não linear; estado de rascunho fica ambíguo | |
| Sidebar lateral + conteúdo à direita | Padrão novo no sistema; mais complexo | |

**Estado vazio (sem rascunho ativo):**

| Option | Description | Selected |
|--------|-------------|----------|
| Tela de boas-vindas com botão 'Iniciar Planning da Sprint N' | Exibe throughput das 3 últimas sprints antes de começar | ✓ |
| Abre direto no passo 1 vazio | Sem contexto de throughput prévio | |
| Lista de plannings anteriores + botão novo | Histórico fora do escopo desta fase | |

---

## Claude's Discretion

- Estrutura completa do `dados_json` do rascunho
- Schema exato da tabela `planning_rascunhos` (UNIQUE constraint)
- Como throughput de referência é calculado (reutilizar `calcular_bloco_c`)
- Detecção de transbordos via `sprint_alvo == sprint_numero - 1 AND status != 'concluida'`
- Endpoints do composer: GET /rascunho, PATCH /rascunho, POST /gerar, POST /confirmar

## Deferred Ideas

- Histórico de plannings anteriores na aba Planning
- Edição inline do markdown no preview (passo 4)
- Múltiplos rascunhos por sprint simultâneos
- Notificação ao confirmar planning
