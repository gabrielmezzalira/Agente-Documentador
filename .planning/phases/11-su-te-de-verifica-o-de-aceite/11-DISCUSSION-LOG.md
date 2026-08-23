# Phase 11: Suíte de Verificação de Aceite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-23
**Phase:** 11-Suíte de Verificação de Aceite
**Areas discussed:** Onde os gates rodam, Schema de ExecucaoAceite, Vínculo id_funcional ↔ teste E2E, Visualização no frontend

---

## Onde os gates rodam

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| GitHub Actions no repo do projeto | CI do repo, dispatch via repository_dispatch, POST de volta ao DocuData | ✓ |
| Stubs por ora | Gates simulados como sem_cobertura; CI real em fase futura | |
| Background task no DocuData | Backend clona e roda gates — requer git+docker no Railway | |

**Escolha do usuário:** GitHub Actions no repo do projeto (mesmo padrão do revisor, Phase 9)
**Notas:** Dispatch assíncrono (asyncio.create_task) para não bloquear o response 200 do PATCH.

---

## Schema de ExecucaoAceite

**Notas:** Usuário pediu explicação adicional. Após esclarecimento sobre o que é ExecucaoAceite, foi definido: 5 gates fixos (build, testes_unitarios, e2e, acessibilidade, performance), CI faz POST /ingest/aceite com resultado por gate, mesmo padrão do revisor.

---

## Vínculo id_funcional ↔ teste E2E

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| CI detecta por nome de arquivo | Busca padrão *[id_funcional]* no repo | |
| Tag/anotação no código do teste | @funcional: FUNC-001 no teste | |
| Todos sem_cobertura por ora | E2E link é deferred | |
| Gerente define manualmente no DocuData | Campo testes_e2e na funcionalidade | ✓ |

**Escolha do usuário:** O gerente define manualmente no DocuData quais testes cobrem cada funcionalidade.
**Notas:** Campo `testes_e2e: list[str]` na tabela funcionalidades. Interface de gestão no frontend é deferred.

---

## Visualização no frontend

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Badge no Kanban + entrada no Bloco B | Badge no card do Kanban + sub-seção no Bloco B | ✓ (recomendado por Claude) |
| Apenas no Bloco B | Kanban não muda | |
| Aba separada 'Aceite' | Nova aba no dashboard | |

**Escolha do usuário:** Pediu recomendação — Claude recomendou badge no Kanban + Bloco B.
**Notas:** Badge no card da coluna Concluído quando gate falhou ou erro. Sub-seção no Bloco B sem afetar % de escopo (Bloco A).

---

## Claude's Discretion

- Token GitHub e repo armazenados em campos novos em `projects` (`github_token`, `github_repo`)
- Se não configurado, todos os gates = `sem_cobertura` imediatamente (sem tentar dispatch)
- `cobertura_aceite` exibido no Painel (calculado como funcionalidades concluídas com aceite / total concluídas)

## Deferred Ideas

- Interface de gestão de testes E2E no frontend
- Histórico paginado de ExecucaoAceite
- Suporte a outros CIs além do GitHub Actions
- Re-disparo manual da suíte
- Notificações (Slack/email)
