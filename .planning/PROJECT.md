# DocuData

## What This Is

DocuData é um sistema web que permite a gerentes de projetos de dados do CITi alimentar seus projetos com arquivos do dia a dia (documentos de task, prints de kanban, atas de reunião, PDFs) e receber documentação estruturada gerada automaticamente. Um agente LangGraph processa cada arquivo, extrai conhecimento estruturado e o acumula por projeto e sprint; o gerente pode então gerar documentos sob demanda — status de sprint, retrospectiva, log de decisões ou documento completo do projeto.

## Core Value

O fluxo de ingestão + geração precisa funcionar de ponta a ponta — subir um arquivo, extrair conteúdo estruturado e gerar um documento útil.

## Requirements

### Validated

(Nenhum ainda — aguardando ship para validar)

### Active

- [ ] Gerente pode criar um projeto com nome, cliente e descrição
- [ ] Gerente pode listar e navegar para projetos existentes
- [ ] Gerente pode fazer upload de arquivo (DOCX, PDF, TXT, PNG, JPG, WEBP) associado a uma sprint
- [ ] Sistema extrai conteúdo estruturado (6 campos) do arquivo via Gemini
- [ ] Gerente pode visualizar histórico de ingestões por projeto/sprint
- [ ] Gerente pode gerar documento de Status da Sprint via LangGraph + Gemini
- [ ] Gerente pode gerar documento de Retrospectiva da Sprint via LangGraph + Gemini
- [ ] Gerente pode gerar documento de Log de Decisões (projeto inteiro) via LangGraph + Gemini
- [ ] Gerente pode gerar Documento Completo do Projeto via LangGraph + Gemini
- [ ] Gerente visualiza e copia o documento gerado em markdown renderizado

### Out of Scope

- Autenticação e controle de acesso — MVP compartilhado sem login, toda a subárea usa o mesmo espaço
- Múltiplos usuários simultâneos com isolamento por conta — fora do escopo v1
- Notificações e alertas — não planejado
- Exportação para DOCX/PDF — markdown é suficiente para v1

## Context

- **Organização:** CITi — Subárea de Dados, UFPE
- **Problema raiz:** Conhecimento técnico e de negócio fica retido na memória das pessoas e se perde ao fim de cada projeto/gestão. Gerentes que documentam já terceirizam informalmente para o Claude, sem estrutura replicável.
- **Prazo:** MVP funcional em ~3 dias para uso imediato por toda a subárea de Dados
- **Primeira audiência:** Todos os gerentes da subárea de Dados do CITi — sem fase piloto individual
- **Arquivos reais dos gerentes:** documentos de task para analistas, prints de kanban, atas de reunião, PDFs de cliente

## Constraints

- **Stack:** Next.js (frontend) + FastAPI Python (backend) + LangGraph/LangChain + Gemini 1.5 Flash + Supabase PostgreSQL — stack definida no design doc
- **Modelo de IA:** Gemini 1.5 Flash — aceita imagens e PDFs nativamente, API key gratuita, custo menor
- **Deploy:** Railway (backend) + Vercel (frontend) — conforme design doc
- **Prazo:** ~3 dias para MVP funcional
- **Sem auth v1:** Espaço compartilhado sem isolamento por usuário — decisão consciente para simplificar o MVP

## Key Decisions

| Decisão | Rationale | Outcome |
|----------|-----------|---------|
| Gemini 1.5 Flash como modelo | Aceita imagens e PDFs nativamente, custo menor, API key gratuita | — Pending |
| LangGraph para orquestração dos grafos | Retry granular por nó e estado explícito — facilita debugging e extensão | — Pending |
| Sprint como metadado obrigatório no upload | Permite atribuição retroativa sem ambiguidade de timestamp | — Pending |
| JSON com 6 campos fixos como schema de extração | Permite filtrar, agregar e referenciar campos específicos na compilação de contexto | — Pending |
| Markdown como formato de output de geração | Renderizável no frontend, copiável, portável | — Pending |
| FastAPI separado do Next.js | Permite escalar backend independentemente e usar Python com bibliotecas de dados | — Pending |
| Sem autenticação no v1 | Simplifica MVP — toda a subárea usa espaço compartilhado | — Pending |

## Evolution

Este documento evolui a cada transição de fase e milestone.

**A cada transição de fase** (via `/gsd-transition`):
1. Requisitos invalidados? → Mover para Out of Scope com motivo
2. Requisitos validados? → Mover para Validated com referência de fase
3. Novos requisitos emergiram? → Adicionar em Active
4. Decisões a registrar? → Adicionar em Key Decisions
5. "What This Is" ainda preciso? → Atualizar se divergiu

**A cada milestone** (via `/gsd:complete-milestone`):
1. Revisão completa de todas as seções
2. Verificação do Core Value — ainda é a prioridade certa?
3. Auditoria do Out of Scope — motivos ainda válidos?
4. Atualizar Context com estado atual

---
*Last updated: 2026-05-22 after initialization*
