---
status: complete
date: 2026-09-06
revisao: 2026-09-07
slug: doc-metodologia-performance
---

## Entrega 1 (2026-09-06) — documento servido sob RBAC

Documento de metodologia do Sistema de Acompanhamento de Performance, servido
dentro do sistema com acesso restrito a Líder e Gerente.

| Arquivo | Mudança |
|---|---|
| `docudata-backend/docs/metodologia-performance.md` | **novo** — o documento |
| `docudata-backend/routers/metodologia.py` | **novo** — serve o markdown |
| `docudata-backend/main.py` | router registrado com `require_not_operacional` |
| `docudata-backend/tests/test_metodologia_rbac.py` | **novo** — 5 testes |
| `docudata-frontend/app/metodologia/page.tsx` | **novo** — página |
| `docudata-frontend/app/lib/api.ts` | `getMetodologia(slug)` |
| `docudata-frontend/app/page.tsx` | link no header para não-operacional |
| `docudata-frontend/package.json` | `remark-gfm@^4` (tabelas GFM) |

## Entrega 2 (2026-09-07) — revisão do Líder

O Líder revisou o documento e devolveu feedback que mudou **o sistema**, não só o
texto. Três decisões tomadas por ele nesta sessão:

### 1. A pergunta de evolução sai da média do gerente

Antes ela contava duas vezes: dentro da média das 7 e isolada em Evolução, o que
lhe dava 15% do score final. Decisão: vale o mesmo que as outras. A média do
gerente passa a ser das **6 perguntas restantes** e a pergunta 6 fica exclusiva de
Evolução.

Isso **reverte** a decisão da Phase 19, que tratava a sobreposição como proposital.

### 2. Task parada tempo demais passa a penalizar Entrega

Antes o travamento automático era alerta puro, com um NFR explícito dizendo que
nunca tocaria fórmula de score. Decisão do Líder: passa a contar.

Desenho escolhido (ele descartou "contar como bloqueio", que penalizaria Autonomia):

- Cada marcação do job diário grava um evento em `task_travamentos`, com os pontos
  da task, no mesmo padrão de `task_reaberturas` — assim o cutoff do fechamento
  evita dupla contagem.
- O override do alerta pelo gerente marca os eventos abertos daquela task como
  `dispensado`, cancelando a penalidade. É a válvula de escape para atraso que não
  é culpa do operacional.
- O fechamento soma os pontos penalizados em
  `pontuacao_operacional_sprint.entrega_pontos_penalizados`, e Entrega passa a ser
  `(concluídos − penalizados) ÷ alocados`, com piso em 0.

### 3. SPI travado e Evolução liberados para o Gerente

Score final e ranking seguem exclusivos do Líder. Novo bloco "Entrega e evolução
por pessoa" na aba Métricas do projeto, alimentado por um endpoint novo com
`require_not_operacional`.

### 4. Selecionar operacional já existente ao vincular a outro projeto

Causa raiz do problema de identidade: o formulário de operacional **nem tinha
campo de e-mail**, e o ranking casa identidade por e-mail. Recadastrar a mesma
pessoa partia ela em duas no ranking. Agora o formulário tem e-mail, mostra o
e-mail (ou o aviso "sem e-mail") na lista, e oferece as pessoas já cadastradas em
outros projetos para preencher o cadastro com um clique.

### Reescrita completa do documento

Instruções do Líder aplicadas: sprint dura **1 semana** (reconhecimento a cada 2);
zero referência a código (nome de arquivo, tabela, coluna, função, endpoint ou
variável); linguagem de alto nível; sem blocos de pseudocódigo; exemplo numérico
com rótulos em português; seções 8.3, 8.4, 9.4 e 9.5 reescritas porque ele não
tinha entendido; explicação passo a passo de como sinalizar bloqueio na tela;
explicação de que a mesma pessoa em dois projetos é uma pessoa só; removidas as
seções 15.9, 17, 18, 19 e os dois anexos; **nenhum travessão no texto**.

### Arquivos da entrega 2

| Arquivo | Mudança |
|---|---|
| `docudata-backend/docs/metodologia-performance.md` | reescrito por inteiro |
| `docudata-backend/supabase_schema.sql` | `task_travamentos` + `entrega_pontos_penalizados` |
| `docudata-backend/services/travamento_checker.py` | grava o evento de travamento |
| `docudata-backend/services/pontuacao.py` | média de 6 perguntas; soma penalidade; SPI desconta; SPI+Evolução por projeto |
| `docudata-backend/services/performance.py` | Entrega desconta penalidade, com piso em 0 |
| `docudata-backend/routers/tasks.py` | override dispensa os travamentos abertos da task |
| `docudata-backend/routers/pontuacao.py` | SPI aberto ao gerente; endpoint de SPI+Evolução do projeto |
| `docudata-backend/routers/operacionais.py` | lista pessoas de outros projetos |
| `docudata-backend/models/schemas.py` | 2 schemas novos |
| `docudata-frontend/app/components/MetricasTab.tsx` | bloco "Entrega e evolução por pessoa" |
| `docudata-frontend/app/projects/[id]/page.tsx` | campo de e-mail e seletor de pessoa existente |
| `docudata-frontend/app/lib/api.ts` | 2 funções novas |
| `docudata-backend/tests/*` | 6 testes novos, 3 atualizados |

### Verificação

- `pytest` — 200 passed, 4 failed. As 4 falhas são **pré-existentes**
  (`test_schemas_and_client.py` afirma que `ConteudoEstruturado` tem 6 campos; o
  schema tem 8 desde a fase de tecnologias). Confirmado com `git stash`.
- `npm run build` — compilado.
- Aritmética do exemplo da seção 11.2 conferida contra o código.

### Pendência bloqueante

Duas migrações manuais no Supabase antes da mudança valer em produção:
`task_travamentos` e `pontuacao_operacional_sprint.entrega_pontos_penalizados`.
Rodar `supabase_schema.sql` inteiro, que é idempotente.
