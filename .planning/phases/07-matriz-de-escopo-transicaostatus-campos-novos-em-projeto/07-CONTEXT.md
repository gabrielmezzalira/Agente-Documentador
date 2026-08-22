# Phase 7 Context — Matriz de Escopo + TransicaoStatus + Campos Novos em Projeto

**Phase:** 07
**Date:** 2026-08-22
**Status:** Context captured — ready for planning

---

## Domain

Esta fase entrega três coisas interdependentes que devem nascer juntas:

1. **Entidade `Funcionalidade`** com máquina de estados manual (nao_iniciada → em_andamento → concluida / em_ajuste) e `status_cliente`
2. **Importação em massa via Gemini** — gerente cola texto do contrato, Gemini propõe funcionalidades com critérios em EARS para revisão item a item
3. **`TransicaoStatus`** — registra automaticamente cada mudança de status com autor, timestamp e duração da fase anterior, desde a primeira transição de qualquer funcionalidade nova

**Por que as três juntas:** se `TransicaoStatus` for adicionado depois, projetos que já estiverem rodando perdem o histórico inicial. Nascer junto com a matriz garante dado completo desde o primeiro dia de qualquer projeto novo.

---

## Canonical Refs

- SDD v1.1 fornecido pelo usuário (§4.1, §4.2, §4.3, §4.6, §5 M1) — fonte de verdade de requisitos
- `.planning/ROADMAP.md` §Phase 7 — success criteria e scope
- `docudata-backend/models/schemas.py` — padrão de Pydantic models existente
- `docudata-backend/routers/projects.py` — padrão de routers e supabase-py existente
- `docudata-backend/graphs/extraction_graph.py` — padrão de LangGraph StateGraph + retry JSON
- `docudata-backend/graphs/generation_graph.py` — padrão de grafo mais simples sem multimodal

---

## Decisions

### Importação em massa via IA

- **Entra na Fase 7** junto com o CRUD manual — não é deferida
- **Arquitetura:** LangGraph — grafo novo em `graphs/import_graph.py`, seguindo o padrão do `extraction_graph.py` (StateGraph com TypedDict, nós retornando partial dicts, retry JSON)
  - Nós esperados: receber_texto → gerar_proposta → estruturar_json → (retry se JSON inválido) → retornar_proposta
  - A proposta **nunca é salva automaticamente** — sempre retorna para revisão humana
- **Revisão:** item a item com checkbox — gerente marca quais funcionalidades confirmar e quais descartar antes de salvar
- **Endpoints:**
  - `POST /funcionalidades/importar` — recebe texto do contrato, retorna lista de funcionalidades propostas (sem salvar nada)
  - `POST /funcionalidades/importar/confirmar` — recebe lista com marcações confirmed/rejected, cria as confirmadas, descarta as rejeitadas

### Critérios de aceite EARS

- **Texto livre — sem validação de formato no backend**
- O Gemini gera sugestões no formato EARS via prompt ("Quando [evento], o sistema deve [resposta]"), mas o gerente pode editar livremente
- O backend exige apenas que ao menos um critério exista por funcionalidade (requisito M1 do SDD) — não valida formato

### TransicaoStatus — onde calcular

- **Cálculo no Python, no handler do PATCH de status**
- Ao receber `PATCH /funcionalidades/{id}` com mudança de `status` ou `status_cliente`:
  1. Handler busca a transição anterior do mesmo campo nessa funcionalidade (ORDER BY timestamp DESC LIMIT 1)
  2. Calcula `duracao_fase_anterior_segundos` = timestamp_agora − timestamp_anterior (ou timestamp_criacao se for a primeira transição)
  3. Insere registro em `transicoes_status` com todos os campos
- Vantagem: testável com pytest (monkeypatch no supabase_client), sem trigger SQL para debugar
- **Sem transaction explícita no MVP:** aceita a janela de inconsistência de dois PATCHes simultâneos (improvável em uso real — um gerente por projeto)

### Campos novos em Projeto

- **Endpoint separado:** `PATCH /projects/{id}/contrato`
- Campos: `data_inicio` (date), `data_fim_contratada` (date), `tolerancia_desvio_pontos` (int, default 20), `periodo_garantia_dias` (int, default 30)
- Projetos existentes sem esses campos: campos ficam `null` no banco — **compatibilidade retroativa garantida** (todos os outros endpoints continuam funcionando sem tocar nesses campos)
- Migration Supabase: ALTER TABLE projects ADD COLUMN para cada campo com DEFAULT null

---

## Code Context

### Padrões reutilizáveis existentes

| Padrão | Onde está | Usar em |
|---|---|---|
| StateGraph com TypedDict + retry JSON | `graphs/extraction_graph.py` | `graphs/import_graph.py` |
| `ChatGoogleGenerativeAI` + `JsonOutputParser` | `graphs/extraction_graph.py` | nó gerar_proposta |
| Router FastAPI com `supabase-py` direto | `routers/projects.py`, `routers/sprints.py` | `routers/funcionalidades.py` |
| Pydantic BaseModel para request/response | `models/schemas.py` | schemas de Funcionalidade e TransicaoStatus |
| Monkeypatch de `get_client` em testes | `tests/test_project_usage.py` | testes de funcionalidades |

### Tabelas Supabase a criar

```sql
-- funcionalidades
CREATE TABLE funcionalidades (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  id_funcional text NOT NULL,
  titulo text NOT NULL,
  descricao text,
  criterios_aceite text[] NOT NULL,  -- lista de strings
  prioridade text NOT NULL DEFAULT 'should',  -- must/should/could/wont
  status text NOT NULL DEFAULT 'nao_iniciada',
  status_cliente text NOT NULL DEFAULT 'nao_enviado',
  data_aprovacao_cliente date,
  responsavel text,
  sprint_alvo uuid REFERENCES sprints(id),
  created_at timestamptz DEFAULT now()
);

-- transicoes_status
CREATE TABLE transicoes_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  funcionalidade_id uuid REFERENCES funcionalidades(id) ON DELETE CASCADE,
  campo text NOT NULL,  -- 'status' ou 'status_cliente'
  de text NOT NULL,
  para text NOT NULL,
  autor text,
  timestamp timestamptz DEFAULT now(),
  motivo text,
  duracao_fase_anterior_segundos integer
);
```

### Campos novos em projects (migration)
```sql
ALTER TABLE projects ADD COLUMN data_inicio date;
ALTER TABLE projects ADD COLUMN data_fim_contratada date;
ALTER TABLE projects ADD COLUMN tolerancia_desvio_pontos integer DEFAULT 20;
ALTER TABLE projects ADD COLUMN periodo_garantia_dias integer DEFAULT 30;
```

---

## Constraints

- **Compatibilidade retroativa:** projetos sem funcionalidades cadastradas continuam funcionando exatamente como hoje — sem erro, sem bloqueio. Todos os endpoints existentes não são alterados.
- **Marcação manual soberana:** nenhuma automação reverte ou bloqueia transição de status feita pelo gerente. `TransicaoStatus` registra, não decide.
- **Importação nunca salva sem confirmação humana:** `POST /funcionalidades/importar` só retorna proposta; `POST /funcionalidades/importar/confirmar` é o único que grava.
- **Sem auth no MVP:** campos `autor` em `TransicaoStatus` ficam como string livre (o gerente digita o nome) ou null — sem sistema de usuários ainda.

---

## Deferred Ideas

- Vínculo automático funcionalidade ↔ branch/commit por convenção de nome — descartado no SDD por inviabilidade operacional; não reintroduzir sem decisão explícita
- Validação de formato EARS (começar com "Quando") — deferida; texto livre suficiente para o MVP
- Transação explícita para evitar race condition em TransicaoStatus — deferida; improvável em uso real com um gerente por projeto
- RLS (Row Level Security) nas tabelas novas — deferido junto com autenticação geral (fora do escopo v1)
