# PTA, nível escolhido pelo gerente e correções da auditoria — design

Data: 2026-11-17 · Branch: `feat/pta` (worktree `../Documentador-pta`, a partir de `origin/main` 8d53c3e)

## 1. Subárea PTA

PTA é o processo seletivo do CITi. Funciona como Dados e Dev (kanban, sprints, documentos, GitHub, Google Docs, pontuação por projeto), com duas diferenças: fica fora das métricas reais (seção 2) e é onde o nível manual (seção 3) mais vai ser usado. O nível manual, porém, existe em qualquer subárea.

**Banco (migração manual):** `projects_subarea_check` passa a aceitar `'pta'` (`dados`, `dev`, `produto`, `pta`). O bloco vai comentado no fim do `supabase_schema.sql`, com preflight e rollback, como as outras migrações.

**Backend**
- `models/schemas.py`: `Subarea` ganha `"pta"`.
- `routers/acompanhamento.py`: o padrão do filtro passa a ser `^(dados|dev|pta)$`.
- `services/github_app.py`: `_SUBAREAS_SUPORTADAS` ganha `"pta"`.
- `services/google_docs.py`: para `pta`, usa `GOOGLE_REFRESH_TOKEN_PTA`. Se ela estiver vazia, usa `GOOGLE_REFRESH_TOKEN` (a conta de Dados). Vale nos três pontos que escolhem a conta.
- `encaminhamento` (Produto → Dados/Dev) não muda.

**Frontend**
- `app/page.tsx`: card "PTA", com a descrição "Projetos do processo seletivo do CITi."
- `components/shell/navItems.ts`: `SUBAREAS` ganha `{ slug: "pta", label: "PTA" }`. As rotas `/pta/...` funcionam pelo `[subarea]` que já existe.
- `app/acompanhamento/page.tsx`: opção PTA no seletor.
- Os selects de subárea do `SprintDocModal`/`RetroModal` usam outro vocabulário ("desenvolvimento" etc.) e não mudam.

## 2. PTA fora das métricas reais

- **Performance/ranking** (`GET /performance`): ganha o parâmetro `escopo=citi|pta`, com padrão `citi`.
  - `citi` considera só projetos com subárea diferente de `pta`.
  - `pta` considera só projetos PTA.
  - O filtro entra onde `listar_pessoas_ativas_por_projeto` e o cálculo do ranking escolhem os projetos.
  - Na tela `/performance`, um seletor "CITi / PTA" no topo.
- **Classificador:** `registrar_conclusao` (aprendizado) e `recalcular_diario` ignoram tasks de projetos PTA. Assim, task PTA não vira exemplo, não calibra parâmetros e não aparece como "parecida". Ela ainda pode ser classificada pela IA, que usa os exemplos reais.
- **Acompanhamento:** já filtra por subárea, então PTA só aparece quando selecionado.
- Pontuação, fechamento de sprint, avaliações, métricas e painel são por projeto e não mudam.

## 3. Nível escolhido pelo gerente (todas as subáreas)

**Representação:** um status novo, `manual`, em `task_classificacoes.status`. É uma migração manual: recriar o CHECK com `aplicada`, `em_revisao`, `provisoria`, `resolvida` e `manual`. A linha guarda `nivel_final` = nível escolhido, `criado_por` = quem escolheu, `modelo` = NULL e `versao_regua`. O selo vem do `classificacao_status`, que já é devolvido nas tasks.

**Criação** (`POST /tasks`): `TaskCreate` ganha `nivel_gerente: Optional[int]`, validado em {1, 2, 3, 5}.
- Quando vem preenchido e quem cria é gerente, líder ou owner, a IA não é chamada. `pontos` = nível escolhido e a classificação é gravada com `status='manual'`.
- Quando vem preenchido por um operacional: 403.
- Quando não vem: o fluxo atual (IA mais `opiniao_nivel`) não muda.

**Task existente:** `POST /tasks/{id}/nivel-gerente`, com `{ nivel }`.
- Quem pode: gerente, líder ou owner com acesso ao projeto.
- Se `nivel_travado_em` estiver preenchido: 409 "Nível já travado: a task começou".
- Caso contrário, atualiza `tasks.pontos`, grava uma classificação `tipo='reclassificacao'` com `status='manual'` e devolve a task com `classificacao_status='manual'`.

**Comportamento**
- Task manual trava normalmente quando começa. `travar_nivel` deixa destravadas só as provisórias e as em revisão, então nada muda ali.
- Editar o texto de uma task manual **não** dispara reclassificação (`routers/tasks.py`, ramo `_texto_mudou`). A escolha do gerente prevalece.
- `resolver_revisao` não se aplica a task manual, porque ela não fica em revisão.
- Fora do PTA, task manual concluída entra no aprendizado normalmente: o rótulo é o nível do gerente.

**Frontend** (`TasksKanbanTab.tsx`, `lib/api.ts`)
- No formulário de criação, para gerente, líder e owner: a opção "Definir o nível eu mesmo", com o seletor 1/2/3/5. Com ela marcada, o campo de opinião some.
- Na task aberta, enquanto não travou: a ação "Mudar nível" (mesmo seletor), que chama o endpoint novo.
- Selo: `Chip` "nível do gerente" no card. Na linha de detalhe (:372), o texto fica "definido pelo gerente".
- O tipo `classificacao_status` ganha `"manual"`.

## 4. Correções da auditoria (pull × normal, desempenho, análise)

A auditoria leu o código da main. Os achados confirmados que entram nesta rodada:

| # | Bug | Correção |
|---|---|---|
| 1 | Em Pull, salvar o modal de uma task com dono dá 422, porque o front reenvia `operacional_id` | Back: em Pull, aceitar `operacional_id` igual ao atual (sem mudança). Front: não enviar `operacional_id` em Pull |
| 2 | Em Pull, a âncora do travamento conta o tempo na fila e penaliza quem puxa | Ao iniciar a sprint, não ancorar task da fila (sem dono) de projeto Pull. Arrastar para puxar reancora sempre, como o `/puxar`. O job ignora task sem dono |
| 4 | Devolver task travada penaliza o dono antigo quando outra pessoa conclui | Ao devolver, marcar como dispensados os `task_travamentos` ativos da task |
| 5 | Pela interface, o operacional arrasta a task de um colega do mesmo projeto (para Concluída, ou de volta para Planejado, onde em Pull ela fica presa com dono e fora da fila). Além disso, PATCH e mover não checam se a pessoa está na equipe do projeto. Explorar isso exigiria chamar a API com o UUID da task, então o risco é baixo | Back: operacional só move task própria (ou puxa da fila, em Pull) e precisa estar na equipe do projeto. Front: para o operacional, card de outra pessoa não é arrastável |
| 6 | `/puxar` não exige sprint (o DoR que o PATCH exige) | O mesmo 422 do PATCH |
| 7 | `/devolver` aceita task concluída e projeto em Atribuição | 422 fora de Pull e para colunas diferentes de `em_andamento`/`em_ajuste` |
| 8 | Reconfirmar avaliação de sprint fechada sobrescreve `avaliacao_completa_em` | Se já estiver fechada, não regravar a data (resposta idempotente) |
| 9 | Reabrir a sprint não apaga `pontuacao_eventos`, e reconfirmar duplica o extrato | Reabrir apaga os eventos daquela sprint |
| 10 | O snapshot do modo da sprint é lido no fechamento, com o modo atual | Gravar `sprints.modo_trabalho`/`modo_avaliacao` quando a sprint inicia. O fechamento usa o snapshot, e o modo atual só se o snapshot estiver nulo. `hibrida` só quando `de != para` |
| 11 | Avaliações históricas usam o modo atual do projeto | Usar o snapshot da sprint, com o modo do projeto como fallback |
| 12 | Cycle time ignora `pull_em` se existe transição antiga | Usar `pull_em` sempre que ele for posterior à transição `em_andamento` |
| 13 | Cycle time com sprint inexistente devolve tudo | Lista vazia |
| 14 | Voltar de Pull para Atribuição mantém WIP 1 por pessoa | Ao sair de Pull, restaurar o WIP por pessoa anterior, gravado no histórico de configuração |
| 18 | Em Atribuição, "Sem operacional" não desatribui | PATCH aceita `operacional_id: null` explícito (via `model_fields_set`). O front envia `null` |
| — | `commit_extraction.py` ainda grava `input_tokens`/`cost_usd`, mas o custo de IA foi removido do produto | Parar de gravar |

**Ficam de fora** (pedem decisão de produto, não são bug claro):
- #3: Entrega relativa sem penalidade de travamento em Pull.
- #15: piso e mediana em Pull ignoram quem não puxou nada.
- #16: SPI individual misturando sprints Pull e Atribuição.
- #17: WIP do Acompanhamento diferente do Painel.
- O caso já conhecido de remover operacional deixando tasks sem dono.

## 5. GitHub App (verificado em produção em 2026-11-17, só leitura)

- 6 repositórios ativos (PAAI, Acreditar Back/Front, Chatbot Imobiliária, PMO, ARA). ARA foi conectado em 2026-11-10, então a autenticação do App funciona.
- **A última entrega de webhook registrada é de 2026-09-11, e a última ingestão de commit é de 2026-09-12.** Desde então, nenhum push chegou ao DocuData.
- O backend de produção responde ao webhook com 401 para assinatura inválida, o que mostra que o segredo está configurado.
- Causa provável: a URL do webhook no App aponta para um domínio antigo (`docudata-backend.up.railway.app` devolve 404), ou o segredo mudou na transferência do App. Entregas com assinatura errada não são registradas.
- Conferir em GitHub → Settings → Developer settings → GitHub Apps → (o App) → Advanced → Recent Deliveries. Não é mudança de código.

## Testes

- pytest:
  - CHECK e literal `pta`.
  - Filtro `escopo` do ranking.
  - Aprendizado ignora PTA.
  - Nível manual: criação, 403 para operacional, troca, 409 depois de travada, edição de texto sem reclassificação.
  - Um teste de regressão por bug corrigido.
- Frontend: `npx tsc --noEmit` e `npm test`.
- Migrações: as duas (subárea e status `manual`) são aditivas e precisam rodar no Supabase antes do deploy do backend.
