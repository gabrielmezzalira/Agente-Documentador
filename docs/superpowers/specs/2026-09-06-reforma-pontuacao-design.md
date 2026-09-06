# Reforma do Modelo de Pontuação — Design

**Status:** aprovado em brainstorm, pendente de plano de implementação
**Path:** Architectural (restructuring que altera interfaces entre Escopo, Sprints, Tasks e Motor de Score, todos já em produção)

## 1. Problema

`sprints.pontos_previstos` (Phase 12) e `tasks.pontos` (Wave Kanban) são campos livres, sem nenhuma trava entre eles: o gerente digita qualquer total de sprint e qualquer pontuação de task, sem exigir que a soma bata. O Motor de Score (Phase 18/19) — que calcula SPI e ranking — consome esses números sem garantia nenhuma de consistência.

O modelo real que o usuário usa fora do sistema (planilha "Cronograma DEV projeto", aba Cronograma) tem uma disciplina que o DocuData não impõe: um valor de projeto fixo é definido uma vez, dividido em um total de pontos, e cada item de trabalho carrega sua fatia desses pontos — nunca solto.

## 2. Objetivo

1. O total de pontos de um projeto é sempre **100**, fixo — nunca um número que o gerente escolhe por projeto.
2. Esses 100 pontos são divididos entre as **sprints** no planejamento (aba Escopo), antes da execução.
3. Dentro de cada sprint, os pontos das **tasks** (Kanban) são distribuídos a partir do orçamento já fixado da sprint — validação simples e local, não mais contra o total do projeto inteiro toda vez.
4. Se o gerente informar o valor em R$ do projeto, cada ponto vira uma fração desse valor (`valor_por_ponto = valor_projeto / 100`), e sprints/tasks passam a ter faturamento previsto/realizado derivado automaticamente.

> **Nota operacional:** `supabase_schema.sql` não roda sozinho contra o banco de produção — as duas `ALTER TABLE` desta seção precisam ser aplicadas manualmente no Supabase depois do deploy (mesma rotina já seguida nas reformas anteriores).

## 3. Modelo de dados

### 3.1 `projects` — novo campo

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS valor_projeto numeric(10,2);
```

`valor_por_ponto` **já existe** no schema desde a Phase 12 (`ALTER TABLE projects ADD COLUMN IF NOT EXISTS valor_por_ponto numeric(10,2);`) mas nunca foi lido em nenhum código — é reaproveitado aqui, não recriado. Não confundir com `projects.budget_usd`, que é o teto de custo de IA (Gemini), um conceito totalmente diferente.

Quando `valor_projeto` é definido (criado ou editado), o backend calcula e grava `valor_por_ponto = valor_projeto / 100` no mesmo request.

**Trava de edição:** `valor_projeto`/`valor_por_ponto` só podem ser alterados enquanto **nenhuma sprint do projeto tiver `pontos_orcamento` definido**. Assim que a primeira sprint recebe um orçamento de pontos, o valor do projeto fica congelado — mudar `valor_por_ponto` depois disso silenciosamente desalinharia o faturamento previsto já calculado para as sprints existentes. Sem coluna de "lock" nova — a trava é derivada (existe alguma sprint com `pontos_orcamento IS NOT NULL`?).

### 3.2 `sprints` — novo campo, campo antigo aposentado

```sql
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS pontos_orcamento int CHECK (pontos_orcamento IS NULL OR pontos_orcamento >= 0);
```

- `pontos_orcamento`: quantos dos 100 pontos do projeto esta sprint recebe. Definido no planejamento (aba Escopo), não na aba Sprints.
- `pontos_previstos`, `faturamento_previsto`, `baseline_locked_at` (colunas Phase 12): **aposentados** — ninguém mais escreve neles. Ficam no schema sem uso (sem migração destrutiva; não vale o risco de dropar coluna em produção por uma reforma que já mexe em várias frentes). `faturamento_previsto` passa a ser **calculado em memória** como `pontos_orcamento × valor_por_ponto` sempre que a sprint é servida via API — nunca mais uma coluna gravada.

### 3.3 `funcionalidades` — sem mudança

Continuam sem pontos próprios. Servem só como agrupador visual/organizacional do escopo (Phase 7) — `sprint_alvo` (texto livre) não precisa virar FK real pra essa reforma funcionar.

### 3.4 `tasks` — sem mudança de schema

`tasks.pontos` continua exatamente como é hoje (`int NOT NULL CHECK (pontos > 0)`). O que muda é só a validação na escrita (seção 4.2).

## 4. Validações — dois níveis independentes

### 4.1 Orçamento de sprint (planejamento, aba Escopo)

Ao definir/editar `sprints.pontos_orcamento` de uma sprint:

- **Teto do projeto:** soma de `pontos_orcamento` de todas as sprints do projeto (substituindo o valor da sprint em questão pelo novo) não pode passar de 100 → 409 "restam só N pontos pra distribuir entre as sprints" se estourar.
- **Não pode encolher abaixo do já usado:** se a sprint já tem tasks com pontos somando mais do que o novo `pontos_orcamento` proposto, bloqueia com 409 — não dá pra prometer menos do que já foi gasto.
- Sprints sem `pontos_orcamento` definido (`NULL`) não entram na soma e não têm teto nenhum ainda — planejamento incompleto não trava o app.

### 4.2 Orçamento de task (execução, Kanban)

Ao criar ou editar uma task com `pontos` e `sprint_id`:

- Se a sprint de destino **tem** `pontos_orcamento` definido: soma de `pontos` de todas as tasks já naquela sprint (excluindo a própria task, se for edição) + os pontos da task ≤ `pontos_orcamento` da sprint → 409 "restam só N pontos no orçamento desta sprint" se estourar.
- Se a sprint de destino **não tem** `pontos_orcamento` definido: sem validação — mesmo comportamento livre de hoje. Não força o gerente a planejar formalmente antes de poder trabalhar.
- Mover uma task de sprint (`sprint_id` muda via `PATCH /tasks/{id}`) reavalia contra o orçamento da sprint de **destino**, não da origem.

Dados já existentes (tasks/sprints anteriores a esta reforma) nunca são revalidados retroativamente — só escrita nova passa pelas checagens acima. Mesmo padrão usado no fix de duplicata de operacional do backlog anterior.

## 5. "Marcar como entregue" — aviso não-bloqueante

O botão já existente (`PATCH /projects/{id}/delivered`) não muda no backend. O frontend, antes de chamar o endpoint, soma `pontos_orcamento` de todas as sprints do projeto (dado que já tem em mãos, vindo de `GET /projects/{id}/sprints`) e, se a soma for diferente de 100, mostra um `confirm()` com o saldo ("62/100 pontos alocados entre as sprints — marcar como entregue mesmo assim?") antes de prosseguir. Não bloqueia — forçar 100 exato incentivaria inflar pontos artificialmente só pra fechar a conta.

## 6. API — resumo das mudanças

| Rota | Mudança |
|---|---|
| `POST /projects` | `ProjectCreate` ganha `valor_projeto: Optional[float]`. Se vier, calcula e grava `valor_por_ponto` junto. |
| `PATCH /projects/{id}/contrato` | `ContratoUpdate` ganha `valor_projeto: Optional[float]`. Só quando `valor_projeto` vier preenchido no payload: recalcula `valor_por_ponto` e grava os dois, ou bloqueia com 409 se já existe alguma sprint do projeto com `pontos_orcamento` definido. Os demais campos do contrato (`arquetipo`, datas, tolerância) continuam sendo atualizáveis normalmente mesmo com o valor travado — a trava é só sobre `valor_projeto`. |
| `PATCH /sprints/{sprint_id}/baseline` | **Removido.** Substituído pela rota abaixo. `SprintBaselineUpdate`/`SprintBaselineResponse` removidos de `models/schemas.py`. |
| `PATCH /sprints/{sprint_id}/orcamento` (novo) | Body `{ pontos_orcamento: int }`. Validações da seção 4.1. |
| `GET /projects/{id}/sprints` | Resposta de cada sprint ganha `pontos_orcamento` (já vem via `select("*")`), `pontos_usados` (soma de `tasks.pontos` daquela sprint, calculado na mesma passada de agregação que já existe pra `tem_planning`/`dailys_count`), e `faturamento_previsto` (calculado, `pontos_orcamento × valor_por_ponto` do projeto — busca o `valor_por_ponto` do projeto uma vez por chamada). |
| `POST /tasks`, `PATCH /tasks/{id}` | Validação da seção 4.2 antes de gravar `pontos`/`sprint_id`. |

## 7. UI — resumo das mudanças

| Onde | Mudança |
|---|---|
| `EscopoTab.tsx` | Novo bloco de planejamento: lista as sprints do projeto com um input de `pontos_orcamento` cada, mais um total rodando ("35/100 pontos alocados"). Bloqueia visualmente (desabilita input ou mostra erro) se a soma passaria de 100. |
| `PainelTab.tsx` (formulário de Contrato, onde já vive `arquetipo`/datas/tolerância) | Novo campo `valor_projeto` (R$, opcional). Desabilitado/somente-leitura se alguma sprint já tiver `pontos_orcamento` definido — com texto explicando por quê. |
| `SprintCard.tsx` | O link de Baseline (adicionado no backlog anterior) é removido. Em seu lugar, um texto derivado somente-leitura: "`{pontos_orcamento} pts · R$ {faturamento_previsto} previstos`" (ou "orçamento não definido" se `pontos_orcamento` for null) — mais o saldo de uso: "`{pontos_usados}/{pontos_orcamento} pts em tasks`". |
| `app/lib/api.ts` | `updateSprintBaseline` removido. Novo `updateSprintOrcamento(sprintId, pontos)`. `createProject`/`updateContrato` ganham `valor_projeto` no payload. |
| Botão "Marcar como entregue" (Configurações, `page.tsx`) | Ganha o `confirm()` não-bloqueante da seção 5 antes de chamar `toggleDelivered`. |

## 8. Fora de escopo (YAGNI)

- Divisão automática de pontos entre sprints (proporcional a nº de funcionalidades, etc.) — o gerente digita manualmente, como na planilha.
- Redistribuição/rebalanceamento retroativo de pontos já usados (rescaling) — poderia quebrar pontuação já travada pela Avaliação Semanal (Phase 18/19). Não faz parte desta reforma.
- Tornar `funcionalidades.sprint_alvo` uma FK real pra `sprints.id` — não é necessário pra esta reforma funcionar; fica como possível reforma futura, separada.
- Migração/backfill de dados existentes — não há dados reais de pontuação em produção ainda (confirmado no UAT da Phase 19); qualquer sprint/task pré-existente simplesmente começa com `pontos_orcamento = NULL` (sem orçamento, sem trava) até o gerente definir.

## 9. Testes (visão geral — detalhado no plano)

- Backend: validação de teto de projeto (100) e de sprint ao definir orçamento; validação de teto de task ao criar/editar/mover; trava de edição de `valor_projeto` após primeiro orçamento de sprint; `GET /sprints` retornando `pontos_usados`/`faturamento_previsto` corretos.
- Frontend: sem framework de teste automatizado no repo (consistente com o resto do projeto) — verificação via `npm run build` + checagem manual.
