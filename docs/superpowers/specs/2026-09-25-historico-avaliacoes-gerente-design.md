# Histórico e correção de avaliações do gerente — Design

Data: 2026-09-25 · Status: aprovado

## Problema

1. Não existe tela para ver as notas da avaliação semanal (`avaliacoes_gerente`) por operacional/sprint — conferir exige SQL.
2. Nota dada errado não tem caminho de correção depois das 48h (`editavel_ate`).
3. Bug: `pontuacao_operacional_sprint.gerente_media`/`gerente_pergunta3`/`gerente_pergunta6` são congelados em `calcular_e_travar_pontuacao` no fechamento e nada os recalcula. Avaliação criada/editada depois do fechamento (permitido dentro das 48h) nunca chega ao ranking — caso Victor Lemos/Theo (Gerente 100 com dois 4).

## Decisões (confirmadas com o usuário)

- **Visibilidade:** gerente, líder e owner veem todas as avaliações de todos os projetos. Operacional não acessa (router já tem `require_not_operacional`).
- **Edição:** qualquer não-operacional edita qualquer avaliação, sem prazo.
- **Auditoria:** toda edição pela tela nova grava log com editor, antes/depois e **motivo obrigatório**.
- **Ranking:** edição sincroniza só os campos de gerente do snapshot congelado (não reabre a sprint — preserva Entrega/Autonomia e correções manuais já aplicadas).

## Banco (migração manual — `supabase_schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS avaliacoes_gerente_edicoes (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    avaliacao_id  uuid        NOT NULL REFERENCES avaliacoes_gerente(id) ON DELETE CASCADE,
    editor_id     uuid        NOT NULL REFERENCES pessoa(id),
    antes         jsonb       NOT NULL,   -- {resposta_1..resposta_7}
    depois        jsonb       NOT NULL,
    motivo        text        NOT NULL CHECK (length(trim(motivo)) > 0),
    criado_em     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_aval_edicoes_avaliacao ON avaliacoes_gerente_edicoes(avaliacao_id);
```

Mais um UPDATE retroativo idempotente que reescreve `gerente_media` (média de 1,2,3,4,5,7, 2 casas), `gerente_pergunta3` e `gerente_pergunta6` de toda linha de `pontuacao_operacional_sprint` a partir da avaliação atual do mesmo `(sprint_id, operacional_id)`.

## Backend

**`services/pontuacao.py::sincronizar_snapshot_gerente(client, avaliacao: dict) -> None`**
Recebe a linha de `avaliacoes_gerente` (com `sprint_id`, `operacional_id`, respostas). Se existir linha em `pontuacao_operacional_sprint` para o par, atualiza os três campos com a mesma fórmula de `calcular_e_travar_pontuacao` (extrair a fórmula pra um helper `_media_gerente(aval)` usado pelos dois). Sem linha (sprint aberta) → no-op.

**`routers/avaliacoes.py`** (router já exige não-operacional):

| Rota | Comportamento |
|---|---|
| `GET /avaliacoes/historico?project_id=&sprint_id=` | Lista avaliações (filtros opcionais), ordenadas por projeto, sprint desc, operacional. Cada item: `id`, respostas, `projeto_id/nome`, `sprint_id/numero`, `operacional_id/nome`, `avaliador_nome`, `criado_em`, `total_edicoes`, `ultima_edicao_em`, `ultima_edicao_por`. |
| `PATCH /avaliacoes/{id}` | Body: `resposta_1..5`, `resposta_7` (int 0-5), `motivo` (str não vazia após trim). 404 se não existir; 422 validação. Grava `avaliacoes_gerente_edicoes` (antes/depois com as 7 chaves), atualiza a avaliação (não mexe em `editavel_ate`/`gerente_id`), chama `sincronizar_snapshot_gerente`. Retorna o item no formato do histórico. Sem mudança real nas respostas → 422 "Nenhuma nota alterada". |
| `GET /avaliacoes/{id}/edicoes` | Lista edições desc: `editor_nome`, `antes`, `depois`, `motivo`, `criado_em`. |

**Correção do bug:** `POST /avaliacoes` chama `sincronizar_snapshot_gerente` após o upsert (insert ou update).

Rotas estáticas (`/historico`) declaradas antes de rotas com parâmetro para não colidir com `/{sprint_id}/...`.

## Frontend

- `app/lib/perguntasAvaliacao.ts`: `perguntas(modoTrabalho)` e mapa índice→`resposta_N` extraídos de `AvaliacaoSemanalModal.tsx` (que passa a importar daqui).
- `app/lib/api.ts`: `getHistoricoAvaliacoes`, `editarAvaliacao`, `getEdicoesAvaliacao` + tipos.
- `app/avaliacoes/page.tsx`: guarda de cargo (não-operacional; operacional vê aviso), filtros projeto/sprint, lista agrupada projeto → sprint, linha por operacional com avaliador, as 6 notas (tooltip com a pergunta), média 0-100 (`média × 20`), selo "editada" com autor/data. Estados loading/erro/vazio.
- Modal de edição: 6 seletores 0-5 pré-preenchidos, textarea de motivo obrigatório, botão desabilitado sem mudança ou sem motivo.
- "Ver histórico": painel/modal com as edições (antes → depois só das perguntas que mudaram, motivo, editor, data).
- `app/page.tsx`: link "Avaliações" no nav global para `podeConfigurar` (gerente/líder/owner).
- Padrão visual: inline styles, mesmo estilo de `app/performance/page.tsx`.

## Testes

- pytest: PATCH (0-5, motivo obrigatório, sem mudança → 422, 404, log gravado com antes/depois, snapshot sincronizado com sprint fechada, no-op com sprint aberta); POST sincroniza snapshot; GET historico com filtros e contagem de edições; operacional → 403.
- Frontend: `tsc --noEmit` + `npm test`.

## Fora do escopo

Vínculo gerente→projeto, apagar avaliação, criar avaliação pela tela nova.
