## Feature Flow em Progresso

> **Sessão anterior encerrada com feature-flow ativo.**
> Use `/feature-flow` para retomar de onde parou.

- **Feature:** Reforma do modelo de pontuação — 100 pontos fixos por projeto, orçamento por sprint (Escopo), distribuídos em tasks (Kanban)
- **Etapa atual:** Verificação final / finishing-a-development-branch
- **Última sessão:** 2026-09-12T17:39:56Z

Para retomar: `/feature-flow` — a skill vai detectar o estado automaticamente.

---

## Quick Tasks Completed

| ID | Task | Commits | Concluída |
|----|------|---------|-----------|
| 260912-lwl | Remover do código a trilha de acompanhamento do cliente e corrigir o alarme de desvio do Painel | `12f2ec6`, `208d9c4`, `eb6ce98` | 2026-09-12 |

**260912-lwl — pontos a lembrar:**
- O desvio do Painel agora é `pct_prazo_consumido − pct_escopo_concluido` (antes comparava com `pct_aprovado_cliente`, sempre 0).
- `calcular_bloco_b` perdeu um parâmetro e três chaves do retorno; `GET /projects/{id}/painel` não devolve mais `cobertura_aceite`.
- **Migração manual pendente: nenhuma.** O banco ficou intocado de propósito — `funcionalidades.status_cliente`, `funcionalidades.data_aprovacao_cliente`, `funcionalidades.testes_e2e`, `execucoes_aceite` e `boletins_aceite` continuam existindo no Supabase, órfãs, sem nada lendo ou escrevendo. Marcadas por comentário em `supabase_schema.sql`.
- `RELATORIO-DOCUDATA.md` entrou no versionamento nesta task (era untracked).
