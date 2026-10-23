# Feature Flow State
feature: "Rodada A2 — classificador do nível da task (régua 1/2/3/5): propõe o nível ao criar a task, gerente confirma ou altera com motivo registrado; busca tasks concluídas parecidas no histórico de todos os projetos; tempo em Em Andamento ajusta no máximo um degrau; modo sombra no primeiro trimestre; critérios/rótulos da régua."
modo: "FULL"
tier: "PADRAO"
stack: "FastAPI (Python) + LangGraph/LangChain + Gemini + Supabase PostgreSQL + Next.js 15 / React 19 (inline styles, design system em app/components/ds)"
etapa: 1
etapa_nome: "Plano de implementação (aguardando revisão da spec pelo usuário)"
gates_reusados: ["knowledge-graph"]
started_at: "2026-10-22T19:00:00Z"
last_saved: "2026-10-23T12:00:00Z"
status: "em_progresso"

## Concluído
- [x] Etapa 0 — graphify-out reaproveitado (docudata-backend/graphify-out, docudata-frontend/app/graphify-out)
- [x] Etapa 1 — Brainstorm A2 (spec docs/superpowers/specs/2026-10-23-classificador-nivel-design.md)
- [ ] Etapa 2 — Plano ← PRÓXIMA (após o usuário revisar a spec)

## Contexto relevante
- Worktree ../Documentador-proposta, branch feat/classificador-nivel a partir de origin/main e787d78 (A1 em produção).
- Estado da A1 arquivado em .planning/feature-flow-state-2026-10-22-rodada-a1.md.
- Texto da proposta (colado pelo usuário): classificador lê título, descrição e checklist; procura tasks concluídas parecidas no histórico de todos os projetos; nível vem do conteúdo, pontos antigos só ponto de partida; tempo em Em Andamento das parecidas ajusta no máximo um degrau; gerente confirma/altera com motivo registrado; base cresce com cada task concluída; rito mensal CTO+heads revisam divergências e recalibram; modo sombra no 1º trimestre, vale quando cada nível tiver exemplos concluídos suficientes.
- Hoje: única criação de task é o modal "Nova task" do Kanban (TasksKanbanTab.tsx → POST /tasks); ordem dos campos: Título, Sprint, Pontos, Operacional, Extra/Requer aprovação, Checklist, Funcionalidade, Descrição (opcional). Pontos vêm antes do conteúdo que o classificador precisa.
- Régua proposta (rascunho, não aprovado): 1 simples / 2 moderada / 3 complexa / 5 muito complexa, com critérios por nível.

## Decisões do brainstorm (2026-10-22/23)
1. O AGENTE define o nível; gerente não escolhe nem altera (diverge da proposta, decisão do usuário). Seletor de pontos sai do modal.
2. Ajuste numérico vale na hora, a cada task concluída (tempo típico por nível, ritmo por pessoa, pesos dos sinais, viés por gerente).
3. Tasks parecidas via embeddings no pgvector (Supabase); verificar cedo se o modelo de embedding responde com a chave atual (chaves novas só 3.5+).
4. Tempo real "limpo" = primeiro Em Andamento → última conclusão, descontando bloqueio de CLIENTE e tempo em pendente_aprovacao; bloqueio interno conta; reaberta soma trechos e fica marcada. Gravar bloqueio_tipo na transição a partir da A2 (antigos sem tipo = interno).
5. Tempo típico = MÉDIA (não mediana). Mostrar média total e média sem excluídas; tasks > 3× média do nível viram alerta; líder/owner decidem tirar ou manter na contagem (reversível).
6. Sem modo sombra/selo; classificador vale desde o 1º dia.
7. Tela de acompanhamento do classificador, só líder/owner: tempo típico por nível + evolução; alertas; acurácia contra o TEMPO REAL (exata, ±1, matriz de confusão, precisão/cobertura por nível, erro médio em degraus, evolução mensal); pesos dos sinais e viés por gerente.
8. Critérios: 6 sinais 0–2 com evidência citada (partes do sistema, novidade, incerteza, dependência externa, tamanho, risco) — lista não contestada pelo usuário; texto insuficiente → agente pede o que falta antes de criar.
9. Antimanipulação: 3 leituras (sinais com pesos ocultos, parecidas pelo tempo real, avaliação geral) + divergência grande vai para revisão de líder/owner; evidência obrigatória e ignorar enchimento; viés por gerente aprendido pelo tempo; sem reclassificar por edição (só líder/owner); nível trava ao entrar em Em Andamento / início da sprint.
10. Gerente VÊ o nível depois de salvar.
11. Ritmo do operacional normaliza o tempo ao aprender; nunca entra na classificação de task nova.
