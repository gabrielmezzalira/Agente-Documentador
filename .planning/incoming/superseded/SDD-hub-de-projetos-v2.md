# SDD Completo — Hub de Projetos: Rename + Módulo de Avaliação de Performance v2

## Contexto para o Claude Code

Este é o sistema hoje chamado Agente Documentador ou DocuData, de Gabriel Mezzalira, Líder de Dados da CITi. Já existem em produção: Kanban de duas camadas (Painel de funcionalidades, aba Tasks de trabalho técnico), histórico de transição de status (`task_transicoes`), SPI de projeto por sprint, throughput, cycle time (p50 e p85), CFD, WIP por operacional com bloqueio de entrada, DoR travando entrada em "Em andamento" sem sprint vinculada, e geração de documentação (Planning e Review) via Gemini injetando o estado do kanban no contexto. Antes de qualquer mudança, leia o código existente e não quebre nenhuma dessas funcionalidades. Este SDD adiciona em cima do que já existe, não substitui.

A aba Tasks tem três colunas de status possíveis: `planejado`, `em_andamento`, `concluida`. Não existe coluna `cancelada`. Todo o desenho abaixo assume só essas três.

## Parte 0 — Rename: Agente Documentador / DocuData → Hub de Projetos

**Objetivo.** O sistema deixou de ser só documentação automática, agora também acompanha performance e fluxo de squad, então o nome precisa refletir o escopo real.

**Escopo do rename, buscar recursivamente (case insensitive) por:** "Agente Documentador", "DocuData", "agente-documentador", "agente_documentador", "docudata" e variações, em nomes de pasta e arquivo, nome de pacote (`package.json`, `pyproject.toml`), nomes de módulo, classe e componente, strings de UI em português exibidas ao usuário, título de página, README e demais docs internas, comentário de código que referencia o nome antigo, nome de variável de ambiente com o prefixo antigo, nome de workflow do GitHub Actions.

**O que não renomear automaticamente, reportar em vez de executar:** nome do repositório no GitHub, nome do projeto Supabase e sua URL, qualquer chave de API já publicada ou compartilhada com terceiro.

**Critério de aceite.** Relatório final com quantas ocorrências foram substituídas, em quais arquivos, e lista separada do que não pôde ser resolvido automaticamente.

## Parte 1 — Confirmação obrigatória em toda transição de status

**Prioridade máxima, base de tudo abaixo.** Nenhuma mudança de coluna acontece sem confirmação explícita, em nenhuma direção.

**Escopo.** Vale para drag and drop manual no kanban, para qualquer chamada de API que mude status, e para o banner de sugestão da IA que hoje detecta tasks mencionadas como concluídas no review. O aceite desse banner deixa de mover a task direto e passa a abrir o mesmo modal de confirmação.

**Fluxo.**

```
AO tentar mudar status de qualquer task, em qualquer direção
MOSTRA modal: "Mover [nome da task] de [status atual] para [novo status]?"
SE confirmar → executa a transição, grava em task_transicoes
SE cancelar → nenhuma mudança, nada é gravado
```

**Motivo.** Protege dois riscos ao mesmo tempo: marcação acidental de concluída, que afeta SPI e pontuação sem entrega real, e reabertura acidental, que geraria registro de retrabalho contra alguém sem motivo verdadeiro.

## Parte 2 — Reabertura de task

**Definição, restrita.** Reabertura é uma transição específica, e só ela: `concluida → em_andamento`. Nenhuma outra movimentação conta como reabertura.

**Modelo de dado**, tabela `task_reaberturas`: `id`, `task_id`, `transicao_id` (referência à linha de `task_transicoes` que registrou o evento), `operacional_id` (responsável pela task no momento), `timestamp`.

**Mecanismo.** Trigger de banco de dados sobre `task_transicoes`, disparado após a confirmação da Parte 1 já ter gravado a transição. Não depende de checagem espalhada pelo código da aplicação.

```
SE nova_transicao.status_anterior == "concluida" E nova_transicao.status_novo == "em_andamento"
ENTÃO grava em task_reaberturas: task_id, transicao_id, operacional_id, timestamp
E incrementa task.contador_reaberturas
```

**Uso.** Alimenta a taxa de retrabalho por operacional na dimensão Qualidade Técnica: reaberturas atribuídas às tasks da pessoa dividido por tasks concluídas por ela no período.

**Decisão em aberto, não resolvida aqui.** Se o motivo da reabertura deve ser campo obrigatório no momento do evento, ou opcional para não gerar atrito no fluxo.

## Parte 3 — Bloqueio manual e resolução (dado de Autonomia)

**Campo já existente**, `bloqueado`, hoje um flag booleano solto sem histórico de quem resolveu. Passa a ter estrutura completa.

**Campos novos na task:** `bloqueado_manual` (booleano, substitui o flag antigo), `bloqueado_em` (timestamp de quando foi marcado), `bloqueado_por` (quem marcou), `bloqueado_resolvido_por` (enum: `operacional` ou `gerente`, preenchido no momento em que o flag é desmarcado), `bloqueado_resolvido_em` (timestamp).

**Regra.** Quando alguém desmarca `bloqueado_manual`, o sistema pergunta quem resolveu, o próprio operacional ou o gerente precisou intervir. Essa resposta é o dado que faltava para a dimensão Autonomia funcionar de verdade.

**Cálculo derivado.** Proporção de bloqueios manuais resolvidos pelo próprio operacional sobre o total de bloqueios manuais que ele teve no período. Alimenta a dimensão Autonomia do score.

## Parte 4 — Travamento automático por tempo (alerta, nunca pontuação)

**Regra de negócio, confirmada por você.** Task em `em_andamento` além do limiar vira `travado_automatico`, com limiar proporcional ao ponto da task:

| Pontos da task | Limiar |
|---|---|
| 1 ponto | 2 dias |
| 2 pontos | 4 dias |
| 3 pontos | 6 dias |

**Âncora.** O relógio começa a contar do momento em que a task entrou em `em_andamento`, nunca da criação da task. Se a task é reaberta (Parte 2), o relógio reinicia a partir da reentrada, não soma o tempo anterior.

**Campo de apoio.** `entrou_em_andamento_em` (timestamp), atualizado toda vez que uma transição confirmada leva a task para `em_andamento`, incluindo reabertura. Existe como campo denormalizado na própria task para o job diário não precisar varrer o histórico completo de transições a cada execução, mas o valor sempre corresponde à transição mais recente registrada em `task_transicoes`.

**Mecanismo, job agendado, não trigger de evento.** Roda uma vez por dia, varre tasks em `em_andamento`, calcula dias desde `entrou_em_andamento_em`, compara com o limiar da tabela acima.

```
limiar_dias = pontos_da_task × 2

JOB DIÁRIO, para cada task com status == "em_andamento":
SE dias_desde(task.entrou_em_andamento_em) ≥ limiar_dias
E task.travado_override != true
ENTÃO task.travado_automatico = true
SENÃO task.travado_automatico = false
```

**Override do gerente.** Campos `travado_override` (booleano), `travado_override_por`, `travado_override_em`. Quando o gerente marca que o alerta foi engano, o sistema grava o override e suprime a exibição do alerta para aquela permanência em `em_andamento`, mas preserva o histórico de que o sistema sinalizou e o gerente corrigiu, como dado de auditoria sobre uso do próprio alerta.

**Reset.** `travado_automatico` e `travado_override` voltam a nulo sempre que a task sai de `em_andamento`, seja para `concluida` ou para `planejado`, e sempre que reentra em `em_andamento` depois de uma reabertura.

**Visibilidade.** `travado_automatico` e seu override são visíveis só para Líder e Gerente, nunca para o operacional.

**Regra crítica de exclusão do score.** `travado_automatico` nunca alimenta a fórmula de pontuação, em nenhuma dimensão. Ele é alerta operacional para o gerente agir, não insumo de avaliação. Só `bloqueado_manual` e sua resolução (Parte 3) alimentam a dimensão Autonomia.

## Parte 5 — Avaliação do Gerente (35% do score)

**Modelo de dado**, tabela `avaliacoes_gerente`: `id`, `operacional_id`, `gerente_id`, `sprint_id`, `data_preenchimento`, `resposta_1` a `resposta_7` (inteiro 0 a 5), `criado_em`, `editavel_ate` (timestamp).

**As sete perguntas, texto fixo, não editável pelo gerente:**

1. Entregou o que se comprometeu dentro do combinado nesta sprint? (0 = quase nada do previsto, 5 = tudo no prazo)
2. A qualidade da entrega precisou de pouca ou nenhuma correção? (0 = refiz quase tudo, 5 = entrou limpo)
3. A pessoa destravou sozinha antes de te escalar? (0 = dependeu de mim o tempo todo, 5 = resolveu sozinha)
4. A comunicação da entrega foi clara a ponto de você não precisar perguntar? (0 = tive que decifrar, 5 = entendi de primeira)
5. Ajudou, desbloqueou ou ensinou outro membro nesta sprint? (0 = não interagiu, 5 = foi peça de apoio do squad)
6. Evoluiu em relação a onde estava no começo do ciclo? (0 = estagnou, 5 = salto claro)
7. Trouxe algo além do que foi pedido? (0 = fez o mínimo, 5 = antecipou problema ou propôs melhoria)

**Regras de negócio.** Uma avaliação por operacional, por gerente, por sprint. Fica editável por 48 horas após envio, suposição a confirmar, e trava depois. O formulário aparece automaticamente para o gerente no fechamento de cada sprint, para cada operacional do próprio squad, e o fechamento da sprint fica bloqueado enquanto houver avaliação pendente, seguindo o mesmo padrão de trava que o DoR já aplica na aba Tasks.

**Acesso.** Cada gerente só vê e preenche avaliação dos operacionais do próprio squad, e nunca vê a avaliação que outro gerente deu a um operacional.

## Parte 6 — Controle de acesso e papéis (RBAC)

**Papéis.** Líder (Gabriel), Gerente, Operacional.

**Líder.** Acesso total, único papel que vê peso de dimensão, fórmula, score individual calculado e ranking completo.

**Gerente.** Vê fluxo, cycle time, SPI de projeto, CFD e WIP do próprio squad, preenche a avaliação da Parte 5, vê `bloqueado_manual` e `travado_automatico` das tasks do próprio squad. Não vê peso de nenhuma dimensão, não vê score final calculado de ninguém, não vê ranking.

**Operacional.** Vê os próprios cards e tasks. Não vê score, não vê ranking, não vê a nota que o gerente deu a ele nas sete perguntas, não vê `travado_automatico`.

**Enforcement.** Restrição aplicada no backend, na camada de API, não só escondida na UI. Todo endpoint que retorna score, peso, avaliação de gerente, ou flags de bloqueio checa o papel de quem chama antes de responder.

**Log de auditoria.** Toda leitura de score, peso, ou avaliação de gerente fica registrada, quem acessou, o quê, quando.

## Parte 7 — Baseline de Evolução

**Modelo de dado**, tabela `baseline_evolucao`: `operacional_id`, `ciclo`, `data_snapshot`, `nota_inicial`, `observacoes`.

**Regra.** No início de cada ciclo, captura um snapshot da avaliação do gerente sobre o operacional, servindo de ponto zero. A dimensão Evolução, em qualquer momento do ciclo, é a diferença entre a média das avaliações do período corrente e esse ponto zero, nunca comparada contra outra pessoa.

## Parte 8 — Trava do baseline do SprintCard

**Regra.** O campo de pontos previstos (baseline do SPI de projeto) do SprintCard vira somente leitura assim que a sprint entra em estado ativo, seja pela data de início alcançada ou pelo gerente iniciando a sprint manualmente. Revisão posterior gera um registro separado de replanejamento, com motivo e timestamp, preservando o valor original intacto para o cálculo histórico do SPI.

## Parte 9 — SPI do Operacional

**Definição.** Métrica de nível de pessoa, agregando através de todos os projetos em que ela atuou no período. Diferente do SPI de projeto que já existe na aba Métricas, que mede o projeto como um todo.

**Fórmula, com agregação correta para múltiplos projetos.**

```
SPI_operacional = Σ (pontos das tasks concluídas pelo operacional, todos os projetos, no período)
                   ÷ Σ (pontos das tasks alocadas ao operacional, todos os projetos, no mesmo período)
```

Soma os pontos primeiro, através de todos os projetos, e divide uma vez só. Nunca calcula o SPI de cada projeto separado e tira a média dos SPIs, porque isso faz um projeto pequeno pesar igual a um grande e distorce o número na direção errada.

**Duas janelas de cálculo.** Por sprint, para visibilidade rápida no dashboard do gerente. Cumulativa do ciclo inteiro, que é a que alimenta a dimensão Entrega e Confiabilidade do score final.

**Normalização.** Multiplica por 100, com teto em 100 mesmo que ultrapasse 1.

**Decisão em aberto.** Se uma task é reatribuída de um operacional para outro no meio do período, hoje os pontos inteiros vão para quem está com a task no fechamento. Revisar se isso gerar distorção na prática.

## Parte 10 — Peso por Arquétipo de Projeto

**Modelo de dado.** Campo `arquetipo` no projeto (enum: `dev`, `consultoria`, `agente_ia`). Tabela `pesos_arquetipo`: `arquetipo`, `peso_avaliacao_gerente`, `peso_entrega`, `peso_qualidade`, `peso_autonomia`, `peso_evolucao`.

**Valores default:**

| Dimensão | Dev | Consultoria | Agente IA |
|---|---|---|---|
| Avaliação do Gerente | 35% | 35% | 35% |
| Entrega e Confiabilidade | 20% | 20% | 20% |
| Qualidade (Técnica ou do Artefato) | 20% | 20% | 20% |
| Autonomia | 15% | 15% | 15% |
| Evolução | 10% | 10% | 10% |

Os três arquétipos usam o mesmo peso por enquanto, suposição a confirmar. Se você quiser diferenciar consultoria ou agente de IA, precisa indicar qual dado objetivo entra para justificar o desvio de peso.

**Regra de seleção quando a pessoa atua em mais de um arquétipo no período.** Usa o arquétipo do projeto onde ela concentrou mais pontos alocados. Critério de desempate para empate exato ainda não definido, decisão em aberto.

## Parte 11 — Motor de cálculo do score (camada oculta)

**Fórmula.**

```
Score = (Avaliação_Gerente × peso_gerente)
      + (Entrega × peso_entrega)
      + (Qualidade × peso_qualidade)
      + (Autonomia × peso_autonomia)
      + (Evolução × peso_evolucao)
```

Cada termo normalizado de 0 a 100 antes de multiplicar pelo peso. Peso vem da tabela de arquétipo conforme a regra da Parte 10.

**Componentes de cada dimensão:**

- Avaliação do Gerente: média das sete respostas por sprint, agregada no ciclo, escala 0-5 multiplicada por 20.
- Entrega e Confiabilidade: SPI de projeto (nível macro) e SPI do Operacional da Parte 9 (nível pessoa), ambos normalizados de 0 a 100.
- Qualidade Técnica ou do Artefato: taxa de retrabalho invertida, 100 menos a taxa de reabertura em percentual, piso em zero.
- Autonomia: proporção de bloqueios manuais resolvidos pelo próprio operacional, da Parte 3.
- Evolução: diferença entre a média do período corrente e a baseline da Parte 7, normalizada.

**Regra de exposição.** O score calculado nunca trafega em nenhum endpoint para os papéis Gerente ou Operacional. Só o papel Líder consulta o score bruto e o ranking completo.

**Saída pública.** Função separada elege o top performer do ciclo e gera só um output seguro: nome da pessoa mais uma frase genérica de justificativa sem número nenhum.

## Requisitos não funcionais

Peso, fórmula e score bruto nunca aparecem em payload de API destinado a papel Gerente ou Operacional, mesmo que o campo simplesmente não seja exibido no frontend, o backend não retorna o dado. Toda escrita em avaliação de gerente, baseline, bloqueio e score fica em log de auditoria com autor e timestamp. A trava do SprintCard, do formulário de avaliação, e o modal de confirmação de transição são validados no backend, não só desabilitados visualmente no frontend. O job de travamento automático roda uma vez por dia e nunca escreve em campo que alimenta o score.

## Critérios de aceite (Definition of Done)

Rename concluído com relatório de pendência manual entregue. Toda mudança de status, em qualquer direção e por qualquer caminho incluindo sugestão da IA, exige confirmação explícita antes de gravar. Reabertura só é registrada quando a transição exata é `concluida → em_andamento`. Bloqueio manual captura quem resolveu no momento de desmarcar. Task em `em_andamento` além do limiar por ponto vira `travado_automatico`, visível só para Líder e Gerente, nunca usada no score, com override do gerente registrado e auditável. Gerente preenche as sete perguntas por operacional ao fechar sprint, e o fechamento é bloqueado até isso acontecer. Operacional, logado com o próprio usuário, não consegue acessar via API nenhum score, peso, ranking, ou `travado_automatico` de si mesmo. SPI do Operacional soma pontos através de projetos antes de dividir, nunca faz média de proporções. Baseline de sprint fica travado após início e qualquer revisão fica registrada à parte. Score final por pessoa existe internamente mas nenhum endpoint acessível por Gerente ou Operacional o retorna.

## Decisões em aberto, não resolver sem confirmar com Gabriel

Se o motivo da reabertura é campo obrigatório ou opcional no momento do evento. Janela exata de trava de edição da avaliação do gerente, usada 48h como suposição. Critério de desempate quando o operacional atuou em arquétipos diferentes com pontos empatados no mesmo período. Regra de atribuição de pontos quando uma task é reatribuída de um operacional para outro no meio do período. Se algum dado objetivo deve diferenciar o peso de consultoria ou agente de IA agora que CSAT foi removido.
