# Rodada B1 — Fechamento da sprint: piso por pessoa, meta do squad e histórico

Data: 2026-10-28 · Branch: `feat/fechamento-sprint-piso-meta` (base `origin/main` d5b2968)

## Contexto

A proposta institucional pede um **piso mínimo por pessoa** e uma **meta por sprint**. Hoje:
- o gráfico "SPI por operacional · estimado" (aba Métricas) mostra puxados × realizados de todo o projeto, sem piso e sem recorte por sprint;
- `projects.pull_piso_pontos` é só o piso técnico do denominador da pontuação pull. Ele não é o piso da proposta e não muda nesta rodada;
- não existe meta, nem visão histórica por sprint, nem um lugar onde o líder veja todos os projetos no fim da sprint.

A rodada B foi dividida em três partes. Esta é a **B1**. O SPI com "concluído e aprovado", o relógio do cliente que pausa e o bônus por rapidez ficam para B2/B3.

## Decisões

| Tema | Decisão |
|---|---|
| Realizado da pessoa na sprint | Soma dos `pontos` das tasks com `sprint_id` da sprint, `coluna_kanban = 'concluida'`, `extra = false` e `operacional_id` da pessoa. Não depende da aprovação da funcionalidade. |
| Squad da sprint | Operacionais do projeto com pelo menos uma task da sprint (puxada ou atribuída). Quem não teve task na sprint fica fora da mediana. |
| Piso da pessoa na sprint N | `0,5 × máx(mediana_squad(N−1), mediana_subarea(trimestre anterior))`, arredondado para uma casa decimal. |
| Mediana do squad | Mediana dos realizados das pessoas do squad na sprint N−1 do mesmo projeto, lida da foto do fechamento da N−1. Se a N−1 ainda não foi fechada (ou não existe), não há mediana do squad. |
| Mediana da subárea | Mediana dos realizados de todos os pares pessoa×sprint de sprints fechadas no trimestre civil anterior, em todos os projetos da mesma `projects.subarea` (dados ou dev). O trimestre da sprint é o de `data_fim`; sem `data_fim`, o de `avaliacao_completa_em`. |
| Sem histórico | Usa a mediana que existir. Sem nenhuma, a pessoa fica sem piso e a tela mostra "sem histórico para o piso". |
| Abaixo do piso | Só sinaliza: destaque no gráfico, na tela `/sprints` e na contagem "N abaixo do piso". Não muda pontuação nem avaliação. |
| Meta | Opcional, em pontos inteiros > 0, por sprint. Quem define é o líder (ou owner) na tela `/sprints`, normalmente para a próxima sprint. Pode ser editada ou removida enquanto a sprint não foi fechada. |
| Meta atingida | Realizado do squad (soma dos realizados, sem extras) ≥ meta. Sem meta, mostra "sem meta". |
| Funcionalidade entregue | Aprovada pelo gerente (regra da A1). Cada funcionalidade mostra também o % de tasks concluídas (concluídas ÷ total de tasks da funcionalidade, sem contar tasks extras). |
| % da sprint | Funcionalidades planejadas na sprint (`sprint_funcionalidades`) que estão aprovadas ÷ planejadas. |
| % do projeto | Funcionalidades aprovadas ÷ total de funcionalidades do projeto (mesma conta do painel da A1). |
| Quando fecha | A sprint está fechada quando `sprints.avaliacao_completa_em` é preenchido ("Confirmar Avaliação Semanal"). É o mesmo critério do selo "Fechada" no `SprintCard`. |
| Foto do fechamento | Ao confirmar a Avaliação Semanal, grava `sprint_fechamento` (squad) e `sprint_fechamento_pessoas` (por pessoa). Antes de fechar, os mesmos números são calculados ao vivo. |
| Tamanho da sprint | Não normaliza pela duração. Limitação registrada; revisitar se houver projetos com cadências muito diferentes. |

## 1. Banco (bloco "Rodada B1" no fim de `supabase_schema.sql`, aplicado manualmente)

```sql
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS meta_pontos int CHECK (meta_pontos IS NULL OR meta_pontos > 0);
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS meta_definida_por uuid REFERENCES pessoa(id) ON DELETE SET NULL;
ALTER TABLE sprints ADD COLUMN IF NOT EXISTS meta_definida_em timestamptz;

CREATE TABLE IF NOT EXISTS sprint_fechamento (
    sprint_id                 uuid PRIMARY KEY REFERENCES sprints(id) ON DELETE CASCADE,
    project_id                uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    subarea                   text NOT NULL,
    trimestre                 text NOT NULL,          -- '2026-T4'
    realizado_squad           numeric(8,1) NOT NULL,
    previsto                  numeric(8,1),
    meta_pontos               int,
    meta_atingida             boolean,
    spi                       numeric(6,3),
    funcs_planejadas          int NOT NULL,
    funcs_planejadas_entregues int NOT NULL,
    funcs_projeto_total       int NOT NULL,
    funcs_projeto_entregues   int NOT NULL,
    mediana_squad             numeric(8,1),
    pessoas_abaixo_piso       int NOT NULL DEFAULT 0,
    fechado_em                timestamptz NOT NULL DEFAULT now()
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

A foto é idempotente (upsert por `sprint_id`). Se uma avaliação for refeita, a foto é regravada no mesmo ponto. Não há backfill automático: um script `scripts/fechamento_backfill.py` grava a foto das sprints que já estão fechadas, para o histórico e a mediana da subárea começarem preenchidos.

## 2. Backend

- `services/fechamento.py` (puro + leitura):
  - `realizados_por_pessoa(tasks)`, `mediana(valores)`, `piso(mediana_squad, mediana_subarea)`, `trimestre_de(sprint)` e `trimestre_anterior(t)` são funções puras com testes;
  - `calcular_fechamento(client, sprint_id)` monta os números ao vivo (squad e pessoas);
  - `gravar_fechamento(client, sprint_id)` grava a foto. Ela é chamada no mesmo ponto em que a Avaliação Semanal grava `avaliacao_completa_em`, em modo best-effort com log, para não quebrar a confirmação.
- Rotas (`routers/fechamento.py`, todas com `require_role("lider")`, exceto onde indicado):
  - `GET /fechamento?subarea=` lista os projetos com a sprint atual (ao vivo) e as últimas 6 fechadas (foto), mais a próxima sprint e a meta dela;
  - `PUT /sprints/{id}/meta` com `{meta_pontos: int | null}` responde 409 se a sprint já foi fechada;
  - `GET /metricas/{project_id}/piso?sprint_id=` (`require_not_operacional`, a mesma regra da aba Métricas) devolve, por pessoa, os puxados, o realizado, o piso e se ela está abaixo dele.
- Paginação com `ler_tudo` em toda leitura de tasks e fotos.

## 3. Frontend

- **`/sprints`** (nova; item "Sprints" no menu, só `isOwnerOrLider`, logo depois de "Performance"):
  - filtro de subárea (Dados / Dev);
  - um card por projeto com:
    - a sprint atual ou a última fechada: realizado × previsto × meta (chip "meta atingida" ou "abaixo da meta");
    - "N abaixo do piso", que expande a lista por pessoa;
    - "% das funcionalidades da sprint entregues" e "% do projeto";
    - a lista das funcionalidades da sprint, cada uma com o % de tasks concluídas e o selo "aprovada";
    - o histórico das últimas 6 sprints numa tabela compacta (sprint, realizado, previsto, meta, atingida, SPI, % de funcionalidades);
    - o campo "Meta da próxima sprint" com salvar e limpar.
  - Estados de carregando, vazio e erro seguem `app/performance/page.tsx`. Para outros cargos, mostra o aviso padrão de acesso restrito.
- **Aba Métricas, "SPI por operacional":**
  - ganha o seletor de sprint (padrão: a atual; a opção "Todas as sprints" mantém a leitura de hoje, sem piso);
  - quando há piso, desenha uma marca horizontal sobre cada pessoa, e a barra de realizados de quem está abaixo fica em âmbar;
  - a legenda ganha "Piso". Sem piso, mostra "sem histórico para o piso".
  - Aparece também o bloco "Histórico das sprints" com a mesma tabela compacta da `/sprints`.
- Usa os componentes de `app/components/ds`, sem lib nova.

## 4. Testes

- Backend:
  - funções puras: mediana com número par e ímpar, piso com uma, duas ou nenhuma mediana, troca de trimestre (T1 → T4 do ano anterior), exclusão das extras;
  - `gravar_fechamento` é idempotente;
  - a confirmação da avaliação grava a foto e continua respondendo se a gravação falhar;
  - permissões das rotas: gerente e operacional recebem 403 em `/fechamento` e na meta;
  - meta em sprint fechada responde 409.
- Frontend: `tsc --noEmit`, `npm test` e um teste estrutural da `/sprints` e da linha do piso.

## Fora de escopo

- SPI com "concluído e aprovado" e as outras partes de B2/B3 (relógio do cliente, bônus por rapidez).
- Normalizar pela duração da sprint.
- Notificar o líder no fim da sprint (e-mail/Slack).
- Mudar `projects.pull_piso_pontos` ou a pontuação.
