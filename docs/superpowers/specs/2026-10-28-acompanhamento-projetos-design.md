# Rodada B1 — Painel de acompanhamento dos projetos

Data: 2026-10-28 · Branch: `feat/fechamento-sprint-piso-meta` (base `origin/main` 648f821)

## Contexto

O líder quer ter mais controle sobre as entregas e o andamento dos projetos: definir, por projeto, quais funcionalidades têm que sair em cada sprint e acompanhar todos os projetos num lugar só, separados por gerente. A proposta institucional também pede um **piso mínimo por pessoa**.

Hoje:
- não existe meta de entrega nem uma visão que junte todos os projetos;
- o **status da funcionalidade é mudado à mão** e ninguém atualiza. Por isso o Painel mostra WIP 0, Throughput 0, "Nenhuma funcionalidade concluída" e uma eficiência de fluxo distorcida, mesmo com as tasks andando;
- o gráfico "SPI por operacional · estimado" não tem piso nem recorte por sprint;
- `projects.pull_piso_pontos` é só o piso técnico do denominador da pontuação pull. Ele não é o piso da proposta e não muda nesta rodada.

A rodada B foi dividida em três partes. Esta é a **B1**. O SPI com "concluído e aprovado", o relógio do cliente que pausa e o bônus por rapidez ficam para B2/B3.

## Decisões

| Tema | Decisão |
|---|---|
| Unidade da meta | **Funcionalidades por sprint.** Não existe meta em pontos; pontos ficam como apoio (SPI e piso). |
| Quem define a meta | Só o líder (ou owner), por projeto e sprint, na tela `/acompanhamento`. O planejamento do gerente é referência, não proposta. |
| Sprints que aceitam meta | A sprint atual e as futuras do projeto. A sprint fechada não aceita mais mudança (409). |
| Mudança da meta | Permitida até a sprint fechar. Toda inclusão ou retirada fica registrada (quem, quando, o quê). O fechamento mostra a **meta original** (como estava quando a sprint começou, ou na primeira definição se ela veio depois) e a **meta final**. |
| Funcionalidade entregue | Aprovada pelo gerente (`status = 'concluida'` e `aprovada_em` preenchido, regra da A1). |
| Resultado da meta | "N de M entregues" ao fechar. A meta só conta como **batida** com 100% das funcionalidades da meta final entregues. Sprint sem meta mostra "sem meta". |
| Andamento de uma funcionalidade | % de tasks concluídas = tasks concluídas ÷ tasks da funcionalidade, sem as extras. |
| Divergência com o planejamento | O painel marca a funcionalidade que está **na meta mas fora do planejamento** do gerente (`sprint_funcionalidades` da sprint) e a que está **planejada mas fora da meta**. |
| Status derivado | O status da funcionalidade passa a ser calculado pelas tasks (seção 2). |
| Agrupamento | Projetos agrupados pelo gerente (`projects.gerente_email` ↔ `pessoa.email`). Projeto sem gerente vai para o grupo "Sem gerente". Cada grupo tem uma linha de resumo. |
| Quem vê | Só líder e owner. O gerente ver o painel dos projetos dele fica fora da B1. |
| Projeto em risco | Basta um destes: (a) % do prazo consumido − % das funcionalidades aprovadas > `projects.tolerancia_desvio_pontos`; (b) meta da última sprint fechada abaixo de 50%; (c) SPI da última sprint fechada < 0,7. O selo mostra qual regra disparou. |
| Realizado da pessoa na sprint | Soma dos `pontos` das tasks da sprint com `coluna_kanban = 'concluida'`, `extra = false` e `operacional_id` da pessoa. |
| Squad da sprint | Operacionais do projeto com pelo menos uma task na sprint. |
| Piso da pessoa na sprint N | `0,5 × máx(mediana_squad(N−1), mediana_subarea(trimestre anterior))`, com uma casa decimal. A mediana do squad vem da foto do fechamento da N−1; se a N−1 não foi fechada, não há mediana do squad. A mediana da subárea usa todos os pares pessoa×sprint de sprints fechadas no trimestre civil anterior, em todos os projetos da mesma `projects.subarea`. O trimestre da sprint é o de `data_fim`; sem `data_fim`, o de `avaliacao_completa_em`. Usa a mediana que existir. Sem nenhuma, a tela mostra "sem histórico para o piso". |
| Abaixo do piso | Só sinaliza. Não muda pontuação nem avaliação. |
| Fechamento | A sprint fecha quando `sprints.avaliacao_completa_em` é preenchido ("Confirmar Avaliação Semanal"). Nesse momento a foto é gravada (seção 4). Antes disso, os números são calculados ao vivo. |
| Tamanho da sprint | Não normaliza pela duração. Limitação registrada. |

## 1. Banco (bloco "Rodada B1" no fim de `supabase_schema.sql`, aplicado manualmente)

```sql
-- Meta de funcionalidades por sprint
CREATE TABLE IF NOT EXISTS sprint_meta_funcionalidades (
    sprint_id          uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    funcionalidade_id  uuid NOT NULL REFERENCES funcionalidades(id) ON DELETE CASCADE,
    incluida_por       uuid REFERENCES pessoa(id) ON DELETE SET NULL,
    incluida_em        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (sprint_id, funcionalidade_id)
);
CREATE TABLE IF NOT EXISTS sprint_meta_eventos (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sprint_id          uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    funcionalidade_id  uuid REFERENCES funcionalidades(id) ON DELETE SET NULL,
    acao               text NOT NULL CHECK (acao IN ('incluiu','retirou')),
    pessoa_id          uuid REFERENCES pessoa(id) ON DELETE SET NULL,
    criado_em          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sprint_meta_eventos_sprint ON sprint_meta_eventos(sprint_id, criado_em);

-- Foto do fechamento
CREATE TABLE IF NOT EXISTS sprint_fechamento (
    sprint_id                   uuid PRIMARY KEY REFERENCES sprints(id) ON DELETE CASCADE,
    project_id                  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    subarea                     text NOT NULL,
    trimestre                   text NOT NULL,          -- '2026-T4'
    meta_original               uuid[] NOT NULL DEFAULT '{}',
    meta_final                  uuid[] NOT NULL DEFAULT '{}',
    meta_entregues              int NOT NULL DEFAULT 0,
    meta_batida                 boolean,                -- null = sem meta
    funcs_planejadas            int NOT NULL,
    funcs_planejadas_entregues  int NOT NULL,
    funcs_projeto_total         int NOT NULL,
    funcs_projeto_entregues     int NOT NULL,
    realizado_squad             numeric(8,1) NOT NULL,
    previsto                    numeric(8,1),
    spi                         numeric(6,3),
    mediana_squad               numeric(8,1),
    pessoas_abaixo_piso         int NOT NULL DEFAULT 0,
    fechado_em                  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sprint_fechamento_pessoas (
    sprint_id       uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    operacional_id  uuid NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    realizado       numeric(8,1) NOT NULL,
    puxados         numeric(8,1) NOT NULL,
    piso            numeric(8,1),
    abaixo_piso     boolean,
    PRIMARY KEY (sprint_id, operacional_id)
);
CREATE INDEX IF NOT EXISTS idx_sprint_fechamento_trimestre ON sprint_fechamento(subarea, trimestre);
```

A meta original não precisa de coluna própria. Ela é reconstruída de `sprint_meta_eventos`: o estado da meta no início da sprint (`data_inicio`, ou a foto do início do previsto) ou, se a meta foi definida depois, o estado depois do primeiro dia em que houve evento. A foto do fechamento grava as duas listas.

## 2. Status da funcionalidade derivado das tasks

- `services/status_funcionalidade.py` é puro + gancho:
  - `status_derivado(tasks)`:
    - sem tasks (ignorando as extras) devolve `None` e não mexe no status;
    - todas as tasks em `planejado` devolve `nao_iniciada`;
    - todas em `concluida` devolve `concluida`;
    - qualquer outro caso devolve `em_andamento`.
  - `sincronizar_status(client, funcionalidade_id, autor)` recalcula o status. Se mudou, grava o status novo e uma linha em `transicoes_status` (`campo='status'`, com `duracao_fase_anterior_segundos` calculada como as transições manuais já fazem) e chama `revogar_se_aprovada` quando o status sai de `concluida`.
- **Ganchos:** ao final de criar, mover, editar (trocar de funcionalidade, nos dois lados), excluir, puxar, devolver e aprovar task, em `routers/tasks.py`. É best-effort com log: a operação da task nunca falha por causa disso.
- **Edição manual do status:** fica bloqueada para funcionalidade com tasks (409 "O status vem das tasks"). Sem tasks, continua manual. O status `em_ajuste` continua manual.
- **Backfill:** `scripts/status_funcionalidade_backfill.py` roda `sincronizar_status` em todas as funcionalidades. Ele é idempotente e pode ser rodado de novo.
- O Painel (WIP, Throughput, eficiência de fluxo, itens em atenção) não muda de código. Ele passa a receber status de verdade.

## 3. Metas de funcionalidades (backend)

- Rotas, todas com `require_role("lider")`:
  - `GET /acompanhamento?subarea=` monta a tela inteira (seção 5) numa chamada, com leitura em lote por projeto. Usa `ler_tudo` em toda leitura grande.
  - `PUT /sprints/{sprint_id}/meta` com `{funcionalidade_ids: uuid[]}` substitui a meta. Grava a diferença em `sprint_meta_eventos`. Responde 409 se a sprint já foi fechada e 422 se alguma funcionalidade for de outro projeto ou já estiver entregue.
  - `GET /sprints/{sprint_id}/meta/eventos` devolve o histórico das mudanças.
- `GET /metricas/{project_id}/piso?sprint_id=` (`require_not_operacional`, a mesma regra da aba Métricas) devolve, por pessoa, os puxados, o realizado, o piso e se ela está abaixo dele.

## 4. Foto do fechamento

- `services/fechamento.py`:
  - funções puras com testes: `realizados_por_pessoa`, `mediana`, `piso`, `trimestre_de`, `trimestre_anterior`, `meta_original`, `resultado_meta` e `regras_de_risco`;
  - `calcular_fechamento(client, sprint_id)` calcula ao vivo;
  - `gravar_fechamento(client, sprint_id)` faz upsert idempotente por `sprint_id`.
- **Quando grava:** no mesmo ponto em que a Avaliação Semanal preenche `avaliacao_completa_em`. É best-effort com log, para não quebrar a confirmação. Se a avaliação for refeita, a foto é regravada.
- **Backfill:** `scripts/fechamento_backfill.py` grava a foto das sprints que já estão fechadas, em ordem de data, para o piso e o histórico começarem preenchidos. Roda depois do backfill do status.

## 5. Frontend

**Tela `/acompanhamento`** (nova; item "Acompanhamento" no menu, só `isOwnerOrLider`, logo depois de "Performance")
- **Topo:**
  - filtro de subárea (Dados / Dev);
  - contadores: projetos, em risco, metas batidas nas últimas sprints fechadas.
- **Um grupo por gerente**, com a linha de resumo:
  - nº de projetos;
  - % de metas batidas nas últimas 6 sprints fechadas dos projetos dele;
  - % de funcionalidades aprovadas no total;
  - nº de projetos em risco.
- **Cada projeto numa linha compacta:**
  - nome e selo "em risco" (com a regra);
  - **Meta × entregue** da sprint atual: "1 de 3", com mini-barras por funcionalidade;
  - **Planejado × realizado:** funcionalidades planejadas × entregues, e o SPI;
  - **Prazo × escopo:** % do prazo × % de funcionalidades aprovadas;
  - **Saúde do time:** quantas pessoas estão abaixo do piso, tasks travadas, WIP e p85 do cycle time.
- **Ao expandir o projeto:**
  - a lista das funcionalidades da meta, com status, % de tasks, selo "aprovada" e as marcas de divergência ("fora do planejamento" / "planejada, fora da meta");
  - o botão **"Definir meta"**, que abre um modal com a lista das funcionalidades não entregues do projeto: checkbox, prioridade, % de tasks e selo "planejada nesta sprint". Ele tem um seletor de sprint (atual ou próximas);
  - o link "histórico de mudanças da meta";
  - o histórico das últimas 6 sprints numa tabela compacta (sprint, meta "N de M" e batida, funcionalidades planejadas × entregues, SPI, abaixo do piso);
  - a lista das pessoas, com realizado e piso.
- **Estados e acesso:** carregando, vazio e erro seguem `app/performance/page.tsx`. Para outros cargos, mostra o aviso padrão de acesso restrito.

**Aba Métricas do projeto**
- "SPI por operacional" ganha o seletor de sprint:
  - o padrão é a sprint atual; "Todas as sprints" mantém a leitura de hoje, sem piso;
  - com piso, aparece uma marca horizontal por pessoa, e a barra de realizados de quem está abaixo fica âmbar;
  - a legenda ganha "Piso"; sem histórico, mostra "sem histórico para o piso".

**Planejamento (gerente)**
- A funcionalidade que está na meta da sprint mostra o selo "meta da sprint N" (só leitura).
- O seletor manual de status fica desabilitado quando a funcionalidade tem tasks, com a dica "O status vem das tasks".

Tudo com `app/components/ds`, sem lib nova.

## 6. Testes

- **Backend:**
  - **Status derivado:**
    - tabela de casos, incluindo extras ignoradas e funcionalidade sem tasks;
    - ganchos de criar, mover, trocar de funcionalidade e excluir;
    - revoga a aprovação quando volta de `concluida`;
    - o 409 na edição manual.
  - **Meta:**
    - substituição gera os eventos certos;
    - 409 em sprint fechada;
    - 422 com funcionalidade de outro projeto ou já entregue;
    - meta original × final.
  - **Fechamento:**
    - mediana com número par e ímpar;
    - piso com uma, duas ou nenhuma mediana;
    - virada de trimestre (T1 → T4 do ano anterior);
    - regras de risco;
    - gravação idempotente;
    - a confirmação da avaliação grava a foto e continua respondendo se a gravação falhar.
  - **Permissões:** gerente e operacional recebem 403 em `/acompanhamento` e na meta.
- **Frontend:** `tsc --noEmit`, `npm test`, um teste estrutural da `/acompanhamento` (blocos, "Definir meta", menu só líder/owner) e um da marca do piso.

## 7. Entregas (cada uma vai para produção separada)

1. **Status derivado:** seção 2, com o backfill. Sem migração. Sozinha, já conserta o Painel.
2. **Metas e `/acompanhamento`:** seções 1 (só as tabelas de meta), 3 e 5, sem o piso e sem o histórico. As regras de risco (b) e (c) calculam a última sprint fechada ao vivo até existir a foto. Precisa de migração.
3. **Piso e fechamento:** seções 1 (as tabelas de foto) e 4, o piso no `/acompanhamento` e na aba Métricas, o histórico e o backfill. Precisa de migração.

## Fora de escopo

- SPI com "concluído e aprovado", relógio do cliente e bônus por rapidez (B2/B3).
- O gerente ver o painel dos projetos dele.
- Meta em pontos; marcos com data e burnup.
- Normalizar pela duração da sprint.
- Notificações no fim da sprint.
- Mudar `projects.pull_piso_pontos` ou a pontuação.
