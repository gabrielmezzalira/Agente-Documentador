# Phase 17 — Avaliação do Gerente

**Status:** Aprovado para planejamento (brainstorming concluído em 2026-09-04)
**Fase no ROADMAP:** `.planning/ROADMAP.md`, Phase 17, requisitos AVAL-01..05
**Depende de:** Phase 16 (RBAC — cargo=gerente/lider já existe e é distinguível)
**Afeta:** Phase 18 (Motor de Score — consome `avaliacoes_gerente` como insumo bruto: `resposta_6` alimenta `baseline_evolucao`, as demais alimentam `gerente_media`)

## Contexto e objetivo

Hoje não existe nenhum conceito de "fechar sprint" ou "avaliar operacional" no código — só campos soltos (`baseline_locked_at`, `status_saude`). Esta phase cria o fluxo do zero: a cada sprint, o Gerente (ou Líder) preenche 7 perguntas fixas de escala 0-5 para cada operacional que teve pelo menos uma task naquela sprint, através de um botão **"Avaliação Semanal"** no `SprintCard`. Quando todas as pendências da sprint estão preenchidas, o Gerente confirma explicitamente (mesmo padrão de confirmação obrigatória já usado na Phase 14) e o sistema grava `sprints.avaliacao_completa_em`.

**Decisão de nomenclatura**: o botão e o conceito se chamam "Avaliação Semanal", não "Fechar Sprint" — o carimbo (`avaliacao_completa_em`) marca só que a rodada de avaliação daquela sprint está completa, sem nenhuma outra trava associada (baseline continua com seu próprio lock independente, tasks continuam livres para mover/reabrir).

**Fora de escopo desta phase** (documentado explicitamente):
- Qualquer trava adicional decorrente de "fechar" a sprint além do carimbo de avaliação completa (baseline, movimentação de tasks, etc. continuam exatamente como hoje)
- Cálculo de score, SPI do operacional, ou qualquer agregação — isso é Phase 18, que só lê `avaliacoes_gerente` como dado bruto
- Notificação/lembrete automático de avaliação pendente (fica pra decisão futura, se necessário)

## Decisões-chave (do brainstorming)

| Decisão | Escolha | Alternativa descartada |
|---|---|---|
| Onde vive o gate | Botão "Avaliação Semanal" no `SprintCard` | Fluxo dentro do Composer (planning/review) |
| O que o carimbo trava | Só um registro (`sprints.avaliacao_completa_em`) — nenhuma trava adicional | Fechamento trava a sprint inteira (mover tasks, editar baseline) |
| Mecanismo de "reaproveitar" | Pré-preenche o formulário com a avaliação anterior; Gerente revisa e confirma antes de salvar (avaliação nova e independente, `reaproveitada_de` só para rastreabilidade) | Um clique cria a avaliação nova direto, sem revisão |
| Natureza das 7 perguntas | Todas escala numérica 0-5; pergunta 6 (evolução) fica separada porque a Phase 18 a usa isoladamente em `baseline_evolucao`, as outras 6 entram em `gerente_media` | Mistura numérica + texto livre |
| Quem entra na lista de pendências | Só operacionais com pelo menos 1 task na sprint específica (`tasks.sprint_id`) | Todos os operacionais ativos do projeto |
| Confirmação da avaliação completa | Clique explícito ("Confirmar Avaliação Semanal") — mesmo padrão de confirmação obrigatória da Phase 14 | Gravação automática assim que a última pendência é enviada |

## As 7 perguntas (texto fixo, escala 0-5)

1. Entregou o que se comprometeu dentro do combinado nesta sprint? (0 = quase nada do previsto, 5 = tudo no prazo)
2. A qualidade da entrega precisou de pouca ou nenhuma correção? (0 = refiz quase tudo, 5 = entrou limpo)
3. A pessoa destravou sozinha antes de te escalar? (0 = dependeu de mim o tempo todo, 5 = resolveu sozinha)
4. A comunicação da entrega foi clara a ponto de você não precisar perguntar? (0 = tive que decifrar, 5 = entendi de primeira)
5. Ajudou, desbloqueou ou ensinou outro membro nesta sprint? (0 = não interagiu, 5 = foi peça de apoio do squad)
6. Evoluiu em relação a onde estava no começo do ciclo? (0 = estagnou, 5 = salto claro) — **isolada para `baseline_evolucao` na Phase 18**
7. Trouxe algo além do que foi pedido? (0 = fez o mínimo, 5 = antecipou problema ou propôs melhoria)

Texto fixo, não editável pelo usuário — hardcoded no frontend (array de labels) e documentado em comentário no backend (`models/schemas.py`).

## Modelo de dados

```sql
CREATE TABLE avaliacoes_gerente (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    operacional_id    uuid NOT NULL REFERENCES operacionais(id) ON DELETE CASCADE,
    gerente_id        uuid NOT NULL REFERENCES pessoa(id),
    sprint_id         uuid NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
    resposta_1        int NOT NULL CHECK (resposta_1 BETWEEN 0 AND 5),
    resposta_2        int NOT NULL CHECK (resposta_2 BETWEEN 0 AND 5),
    resposta_3        int NOT NULL CHECK (resposta_3 BETWEEN 0 AND 5),
    resposta_4        int NOT NULL CHECK (resposta_4 BETWEEN 0 AND 5),
    resposta_5        int NOT NULL CHECK (resposta_5 BETWEEN 0 AND 5),
    resposta_6        int NOT NULL CHECK (resposta_6 BETWEEN 0 AND 5),
    resposta_7        int NOT NULL CHECK (resposta_7 BETWEEN 0 AND 5),
    reaproveitada_de  uuid REFERENCES avaliacoes_gerente(id),
    criado_em         timestamptz NOT NULL DEFAULT now(),
    editavel_ate      timestamptz NOT NULL,
    UNIQUE (operacional_id, sprint_id)
);

ALTER TABLE sprints ADD COLUMN IF NOT EXISTS avaliacao_completa_em timestamptz;
```

- `editavel_ate = criado_em + 48h`, calculado no servidor no momento da criação (nunca recalculado num reenvio dentro da janela — a janela é fixa a partir do primeiro envio).
- `UNIQUE (operacional_id, sprint_id)`: reenvio dentro da janela de 48h é `UPDATE` (upsert), não uma segunda linha.
- `reaproveitada_de` é só rastreabilidade — não participa de nenhum cálculo.
- Sem tabela de "quem está pendente" — pendência é sempre calculada em runtime (tasks da sprint menos quem já tem avaliação).

## Endpoints — `docudata-backend/routers/avaliacoes.py`

Protegido com `require_not_operacional` (mesmo padrão de `metricas.router`/`painel.router` — Gerente e Líder passam, Operacional recebe 403 em qualquer rota).

| Rota | Método | Descrição |
|---|---|---|
| `GET /avaliacoes/{sprint_id}/pendencias` | GET | Lista operacionais com task na sprint para os quais ainda não existe nenhuma linha em `avaliacoes_gerente` (`operacional_id`+`sprint_id`). Uma vez criada, a linha nunca é removida — só fica somente-leitura após `editavel_ate` — então "pendente" é estritamente "nenhuma avaliação enviada ainda". Cada item: `{operacional_id, nome, ultima_avaliacao_outro_projeto: {respostas, projeto_nome, data} \| null}` |
| `POST /avaliacoes` | POST | Upsert por `(operacional_id, sprint_id)`. Corpo: `{operacional_id, sprint_id, resposta_1..7, reaproveitada_de?}`. Se já existe linha e `now() > editavel_ate` → 409. `gerente_id` vem da sessão (`pessoa.id`), nunca do body |
| `POST /sprints/{sprint_id}/avaliacao-semanal/confirmar` | POST | Verifica que a lista de pendências está vazia; se sim, grava `sprints.avaliacao_completa_em = now()`; se não, 409 com a lista de quem falta |

**Reaproveitar de outro projeto**: busca por `operacionais.email` (do operacional sendo avaliado) igual em outro `project_id`, pega a `avaliacoes_gerente` mais recente (`ORDER BY criado_em DESC LIMIT 1`) daquele `operacional_id` diferente (o `operacional_id` de lá, não o daqui — são linhas distintas em `operacionais` por serem por-projeto).

## Frontend

**`SprintCard`**: botão "Avaliação Semanal", visível só para `cargo !== "operacional"` (`useAuth()`, mesmo padrão da Phase 16). Badge "{N} pendentes" quando há pendências; chip verde "✓ Avaliada" quando `avaliacao_completa_em` não é null.

**`AvaliacaoSemanalModal`** (novo componente, mesmo estilo dos modais existentes — `ConfirmTransicaoModal`, `PlanningModal`):
1. Lista pendências (`GET /avaliacoes/{sprint_id}/pendencias`)
2. Clicar num operacional abre o formulário das 7 perguntas — cada uma como 6 chips numerados (0-5), mesmo padrão visual já usado no app
3. Se `ultima_avaliacao_outro_projeto` existe, mostra faixa "Reaproveitar avaliação de {projeto} em {data}?" — clicar pré-preenche os 7 chips (editáveis depois) e seta `reaproveitada_de`
4. "Salvar avaliação" → `POST /avaliacoes` → volta pra lista, uma pendência a menos
5. Lista vazia → aparece "Confirmar Avaliação Semanal" → `POST .../confirmar` → fecha modal, `SprintCard` atualiza pro chip "✓ Avaliada"

**Edição dentro de 48h**: avaliações já enviadas mas com `editavel_ate` no futuro aparecem na lista com chip "editável até HH:mm", reabrem no mesmo formulário; reenviar é o mesmo `POST /avaliacoes` (upsert). Após `editavel_ate`, somente-leitura.

## Testes

Mesmo padrão pytest + `TestClient` + `MagicMock` já usado no projeto:
- `test_avaliacoes_pendencias.py` — lista corretamente operacionais com task na sprint sem avaliação; exclui quem já tem avaliação; inclui `ultima_avaliacao_outro_projeto` quando existe
- `test_avaliacoes_submit.py` — cria avaliação nova (`resposta_1..7` válidas, 0-5); upsert dentro de 48h atualiza a mesma linha; fora de 48h → 409; `resposta` fora de 0-5 → 422 (validação Pydantic); `gerente_id` sempre vem da sessão, nunca do body
- `test_avaliacao_semanal_confirmar.py` — confirma com todas pendências resolvidas → grava `avaliacao_completa_em`; confirma com pendência → 409 listando quem falta
- `test_avaliacoes_rbac.py` — cargo=operacional → 403 em qualquer rota de `avaliacoes.router`; cargo=gerente/lider → passa

## Success criteria (do ROADMAP.md, mapeados)

1. ✅ Tabela `avaliacoes_gerente` com os campos do ROADMAP (mais `reaproveitada_de`, adição não conflitante) — uma avaliação por operacional/gerente/sprint via `UNIQUE (operacional_id, sprint_id)`
2. ✅ 7 perguntas fixas aparecem automaticamente pra cada operacional pendente da sprint; "Avaliação Semanal" (renomeado de "fechamento") fica sem confirmar enquanto houver pendência
3. ✅ Avaliação editável por 48h (`editavel_ate`), depois somente-leitura
4. ✅ Reaproveitar avaliação de outro projeto — pré-preenche, Gerente revisa e confirma, sem forçar formulário em branco
5. ✅ Qualquer `cargo=gerente` (ou `lider`) avalia operacionais de qualquer projeto ao qual tenha acesso — `require_not_operacional`, sem restrição de squad
