# Phase 12: Boletim de Aceite, Encerramento e Resumo Semanal - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-23
**Phase:** 12-boletim-de-aceite-encerramento-e-resumo-semanal
**Areas discussed:** Modelo do boletim, Resumo semanal, Evidência visual, Onde vive no frontend

---

## Modelo do Boletim

| Option | Description | Selected |
|--------|-------------|----------|
| Por lote | Um único boletim agrupa N funcionalidades; mais prático para envio ao cliente | ✓ |
| Por funcionalidade | Um boletim distinto por funcionalidade; mais granular | |

**User's choice:** Por lote

---

| Option | Description | Selected |
|--------|-------------|----------|
| Nova tabela `boletins_aceite` | Tabela própria com status e histórico; status_cliente derivado do boletim | ✓ |
| Em `funcionalidades` diretamente | Adicionar campos em funcionalidades; boletim em generated_docs | |

**User's choice:** Nova tabela `boletins_aceite`

---

| Option | Description | Selected |
|--------|-------------|----------|
| Gemini gera | Mesmo padrão do Composer (Phase 10) — preview → confirmar | ✓ |
| Formulário manual | Gerente preenche título e critérios manualmente | |

**User's choice:** Gemini gera

---

## Resumo Semanal

| Option | Description | Selected |
|--------|-------------|----------|
| On-demand (botão no dashboard) | Gerente clica "Gerar Resumo desta Semana"; sem cron | ✓ |
| Automático via GitHub Actions | Workflow semanal, igual ao revisor diário (Phase 9) | |
| Ambos | Botão on-demand + workflow semanal | |

**User's choice:** On-demand

---

| Option | Description | Selected |
|--------|-------------|----------|
| Listagem estruturada pura | Backend formata em markdown sem chamar Gemini | ✓ |
| Gemini elabora o texto | Resumo narrativo gerado pelo LLM | |

**User's choice:** Listagem estruturada pura

---

| Option | Description | Selected |
|--------|-------------|----------|
| Semana atual (dom–sáb, calendário fixo) | Semana em curso no momento do clique | ✓ |
| Últimos 7 dias a partir de agora | Janela deslizante | |

**User's choice:** Semana atual (dom–sáb)

---

## Evidência Visual no Boletim

| Option | Description | Selected |
|--------|-------------|----------|
| Campo de URL/link externo | Gerente cola link (Loom, Drive, deploy preview) | |
| Upload de imagem no DocuData | Imagem enviada ao Supabase Storage | |
| Texto markdown editável | Campo de texto livre | |

**User's choice:** "pode tirar isso, nao precisa" — **removido do escopo**
**Notes:** Após explicação do que é evidência visual, o usuário decidiu remover completamente da fase.

---

## Onde vive no Frontend

| Option | Description | Selected |
|--------|-------------|----------|
| Nova aba no dashboard | Aba "Aceite" no Tabs.tsx, mesmo padrão do Composer | ✓ |
| Modal a partir do Kanban | Botão "Gerar Boletim" na coluna Concluído | |
| Tela separada `/projects/[id]/aceite` | Rota própria | |

**User's choice:** Nova aba no dashboard

---

| Option | Description | Selected |
|--------|-------------|----------|
| Na mesma aba "Aceite" | Seção inferior da aba com botão "Gerar Resumo" | ✓ |
| Na aba Painel | Ao lado do Bloco A/B/C do Painel | |

**User's choice:** Na mesma aba "Aceite"

---

| Option | Description | Selected |
|--------|-------------|----------|
| Exibido na aba Aceite com botão copiar | react-markdown + copiar, padrão existente | |
| Download como arquivo .md | Download direto no browser | |

**User's choice:** "nao precisa gerar o termo de encerramento" — **removido do escopo**
**Notes:** Termo de Encerramento removido. Substituído por sinalização simples (badge/mensagem) quando 100% aprovado.

---

## Claude's Discretion

- Estrutura dos endpoints: `POST /boletins`, `PATCH /boletins/{id}`, `GET /boletins/{project_id}`
- Preview antes de confirmar: igual ao Composer (Phase 10)
- Resumo semanal salvo em `generated_docs` com `doc_type = 'resumo_semanal'`
- "Mudanças de escopo" exibidas como lista separada passiva na aba Aceite

## Deferred Ideas

- Evidência visual no boletim (upload de imagem ou URL) — removido pelo usuário
- Termo de Encerramento como documento gerado — removido pelo usuário
- Notificação por e-mail ao cliente com o boletim — nova funcionalidade, fase futura
- Geração automática do resumo semanal via GitHub Actions/cron — extensão futura
