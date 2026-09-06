# SDD Completo — Hub de Projetos: Rename + Módulo de Avaliação de Performance v3

> Nota de proveniência: esta v3 substitui `SDD-hub-de-projetos-v2.md`. Muda o método de cálculo do SPI do Operacional (Partes 9, 11, 12): soma dentro do mesmo projeto entre sprints do período, depois média simples entre projetos diferentes — em vez de somar pontos entre projetos antes de dividir, como estava na v2. Também resolve 4 das 5 "Decisões em aberto" da v2 (motivo de reabertura, janela de edição de 48h, formato da avaliação do gerente por projeto-sprint com opção de reaproveitar a última avaliação de outro projeto, sinalização de janela parcial). A questão sobre peso diferenciado por arquétipo (substituto do CSAT) permanece em aberto.

Antes do documento, um flag rápido e curto, porque isso já é padrão nesta conversa: a instrução de tirar média entre projetos é uma mudança de método em relação ao que ficou fechado na Parte 9 anterior, que somava pontos entre projetos antes de dividir. Não é incoerente, é uma extensão do mesmo princípio de calibração que você já tinha validado (não deixar volume dominar), só que aplicado num nível acima: soma ainda vale dentro do mesmo projeto ao longo dos sprints, média passa a valer entre projetos diferentes. Registro como decisão tua, aplico assim, e no SDD abaixo já vem tudo revisado e consistente com isso, sem você precisar caçar o que mudou.

Uma clarificação que a mudança expõe e que preciso te devolver, não resolvo sozinho: como cada projeto tem sua própria sequência de sprint, um operacional em dois projetos ao mesmo tempo pode gerar duas avaliações do gerente na mesma semana, uma por projeto, se os dois fecharem sprint perto um do outro. Isso fica marcado como decisão em aberto no fim do documento.

---

## Contexto para o Claude Code

Sistema hoje chamado Agente Documentador ou DocuData, de Gabriel Mezzalira, Líder de Dados da CITi. Em produção: Kanban de duas camadas (Painel de funcionalidades, aba Tasks de trabalho técnico), histórico de transição de status (`task_transicoes`), SPI de projeto por sprint, throughput, cycle time (p50 e p85), CFD, WIP por operacional com bloqueio de entrada, DoR travando entrada em "Em andamento" sem sprint vinculada, geração de documentação (Planning e Review) via Gemini injetando o estado do kanban no contexto. Leia o código existente antes de qualquer mudança, este SDD adiciona em cima, não substitui.

A aba Tasks tem três status: `planejado`, `em_andamento`, `concluida`. Não existe `cancelada`. Cada projeto tem sua própria sequência de sprints, independente das sprints de outros projetos.

## Parte 0 — Rename: Agente Documentador / DocuData → Hub de Projetos

Buscar recursivamente (case insensitive) "Agente Documentador", "DocuData" e variações em: pasta, arquivo, pacote, módulo, classe, componente, string de UI, título de página, documentação, comentário de código, variável de ambiente, workflow do GitHub Actions.

Não renomear automaticamente, reportar em vez de executar: nome do repositório GitHub, nome e URL do projeto Supabase, chave de API já publicada.

Critério de aceite: relatório com o que foi substituído e o que ficou pendente de ação manual.

## Parte 1 — Confirmação obrigatória em toda transição de status

Nenhuma mudança de coluna acontece sem confirmação explícita, em nenhuma direção, incluindo drag and drop manual, chamada de API, e o banner de sugestão da IA que hoje sugere task como concluída no review.

```
AO tentar mudar status de qualquer task
MOSTRA modal: "Mover [task] de [status atual] para [novo status]?"
SE confirmar → executa, grava em task_transicoes
SE cancelar → nada muda, nada é gravado
```

## Parte 2 — Reabertura de task

Reabertura é só uma transição: `concluida → em_andamento`. Nenhuma outra saída de `concluida` conta.

Tabela `task_reaberturas`: `id`, `task_id`, `transicao_id`, `operacional_id`, `timestamp`.

Trigger de banco sobre `task_transicoes`, disparado após confirmação da Parte 1:

```
SE status_anterior == "concluida" E status_novo == "em_andamento"
ENTÃO grava em task_reaberturas
E incrementa task.contador_reaberturas
```

Alimenta taxa de retrabalho da dimensão Qualidade Técnica.

## Parte 3 — Bloqueio manual e resolução

Campos na task: `bloqueado_manual` (booleano), `bloqueado_em`, `bloqueado_por`, `bloqueado_resolvido_por` (enum: `operacional` ou `gerente`), `bloqueado_resolvido_em`.

Ao desmarcar `bloqueado_manual`, o sistema pergunta quem resolveu. Alimenta a dimensão Autonomia: proporção de bloqueios manuais resolvidos pelo próprio operacional sobre o total de bloqueios manuais que ele teve no período.

## Parte 4 — Travamento automático por tempo (alerta, nunca pontuação)

Limiar proporcional ao ponto da task: 1 ponto = 2 dias, 2 pontos = 4 dias, 3 pontos = 6 dias. Âncora: timestamp de entrada em `em_andamento` (`entrou_em_andamento_em`), reinicia em cada reentrada, inclusive por reabertura.

```
limiar_dias = pontos_da_task × 2
JOB DIÁRIO, para cada task em "em_andamento":
SE dias_desde(entrou_em_andamento_em) ≥ limiar_dias E travado_override != true
ENTÃO travado_automatico = true
SENÃO travado_automatico = false
```

Override do gerente: `travado_override`, `travado_override_por`, `travado_override_em`, suprime exibição sem apagar o histórico de que o sistema sinalizou. Reseta ao sair de `em_andamento` ou reentrar.

Visível só para Líder e Gerente. `travado_automatico` nunca alimenta a fórmula de score, em nenhuma dimensão. Só `bloqueado_manual` alimenta Autonomia.

## Parte 5 — Avaliação do Gerente (35% do score)

Tabela `avaliacoes_gerente`: `id`, `operacional_id`, `gerente_id`, `sprint_id` (projeto-específico), `data_preenchimento`, `resposta_1` a `resposta_7` (0 a 5), `criado_em`, `editavel_ate`.

As sete perguntas, texto fixo:

1. Entregou o que se comprometeu dentro do combinado nesta sprint? (0 = quase nada do previsto, 5 = tudo no prazo)
2. A qualidade da entrega precisou de pouca ou nenhuma correção? (0 = refiz quase tudo, 5 = entrou limpo)
3. A pessoa destravou sozinha antes de te escalar? (0 = dependeu de mim o tempo todo, 5 = resolveu sozinha)
4. A comunicação da entrega foi clara a ponto de você não precisar perguntar? (0 = tive que decifrar, 5 = entendi de primeira)
5. Ajudou, desbloqueou ou ensinou outro membro nesta sprint? (0 = não interagiu, 5 = foi peça de apoio do squad)
6. Evoluiu em relação a onde estava no começo do ciclo? (0 = estagnou, 5 = salto claro)
7. Trouxe algo além do que foi pedido? (0 = fez o mínimo, 5 = antecipou problema ou propôs melhoria)

Uma avaliação por operacional, por gerente, por sprint (sprint aqui é sempre de um projeto específico). Editável por 48h após envio, depois trava. Aparece automaticamente no fechamento de sprint, bloqueia o fechamento até estar completa.

**Resolvido nesta v3:** avaliação do gerente é uma resposta por operacional por projeto-sprint (não agrega os projetos num único formulário semanal). Quando um gerente vai avaliar um operacional que também está em outro projeto, a UI deve oferecer a opção de reaproveitar a última avaliação feita nesse outro projeto, mostrando a data em que foi feita e de qual projeto veio, em vez de forçar preenchimento do zero. Isso não elimina a possibilidade de duas avaliações na mesma semana — só reduz o atrito de preenchê-las.

Acesso: gerente só vê e preenche avaliação dos operacionais do próprio squad.

## Parte 6 — Controle de acesso e papéis (RBAC)

Papéis: Líder (Gabriel), Gerente, Operacional.

Líder: acesso total, único que vê peso, fórmula, score individual e ranking.

Gerente: vê fluxo, cycle time, SPI de projeto, CFD, WIP do próprio squad, preenche avaliação, vê `bloqueado_manual` e `travado_automatico` do próprio squad. Não vê peso, score final, ranking.

Operacional: vê os próprios cards e tasks. Não vê score, ranking, nota do gerente, `travado_automatico`.

Enforcement no backend, não só na UI. O módulo de Performance (Parte 12) fica em rota própria (`/performance`), fora do contexto de projetos, com middleware de autorização dedicado, não compartilhado com as rotas de projeto.

Log de auditoria: toda leitura de score, peso, avaliação, fica registrada com autor e timestamp.

## Parte 7 — Baseline de Evolução

Tabela `baseline_evolucao`: `operacional_id`, `ciclo`, `data_snapshot`, `nota_inicial`, `observacoes`. Snapshot no início de cada ciclo, ponto zero para medir crescimento. Evolução é sempre pessoa contra ela mesma, nunca contra outra pessoa.

## Parte 8 — Trava do baseline do SprintCard

Campo de pontos previstos do SprintCard vira somente leitura assim que a sprint entra em estado ativo. Revisão posterior gera registro separado de replanejamento, preservando o valor original para o SPI histórico.

## Parte 9 — SPI do Operacional (revisado: soma dentro do projeto, média entre projetos)

Métrica de nível de pessoa. Cálculo em duas camadas, refletindo a decisão de calibração desta mensagem.

**Camada 1, dentro de um mesmo projeto:** soma os pontos concluídos e os pontos alocados do operacional em todos os sprints daquele projeto dentro do período, divide uma vez.

```
SPI_projeto_X = Σ pontos concluídos pelo operacional no projeto X (sprints do período)
              ÷ Σ pontos alocados ao operacional no projeto X (sprints do período)
```

**Camada 2, entre projetos diferentes:** se o operacional atuou em mais de um projeto no período, tira a média simples dos SPIs de cada projeto.

```
SE operacional atuou em 1 projeto no período:
    SPI_operacional = SPI_projeto_único

SE operacional atuou em N projetos no período:
    SPI_operacional = (SPI_projeto_1 + SPI_projeto_2 + ... + SPI_projeto_N) ÷ N
```

Isso evita que um projeto grande domine o número só por volume, mantendo a mesma lógica de calibração que já vale para pontos dentro de um projeto, agora estendida para o portfólio de projetos da pessoa.

Normalização: multiplica por 100, teto em 100.

## Parte 10 — Peso por Arquétipo de Projeto

Tabela `pesos_arquetipo`: `arquetipo`, cinco colunas de peso.

| Dimensão | Dev | Consultoria | Agente IA |
|---|---|---|---|
| Avaliação do Gerente | 35% | 35% | 35% |
| Entrega e Confiabilidade | 20% | 20% | 20% |
| Qualidade (Técnica/Artefato) | 20% | 20% | 20% |
| Autonomia | 15% | 15% | 15% |
| Evolução | 10% | 10% | 10% |

Os três arquétipos usam o mesmo peso hoje, por decisão pendente sobre o que substitui o CSAT removido. Como os pesos são idênticos entre arquétipos no momento, a seleção de qual arquétipo usar não afeta o resultado ainda, mas o campo já fica implementado para quando isso mudar.

## Parte 11 — Cálculo por sprint, camada de dado bruto (revisado: grão por projeto)

**Unidade atômica.** Todo cálculo nasce no nível de um sprint de um projeto específico. Score de sprint isolado, quinzenal e mensal são agregações em cima dessa unidade.

Tabela `pontuacao_operacional_sprint`, uma linha por operacional por sprint de um projeto:

- `operacional_id`, `sprint_id`, `projeto_id` (denormalizado do sprint, para agrupar sem join)
- `sprint_fim` (data de fechamento, usada para ordenar a sequência pessoal do operacional)
- `gerente_media` (0 a 5, média das sete respostas daquele sprint naquele projeto)
- `gerente_pergunta6` (0 a 5, isolada, alimenta Evolução)
- `entrega_pontos_concluidos`, `entrega_pontos_alocados` (soma bruta daquele sprint, dentro daquele projeto)
- `qualidade_reaberturas`, `qualidade_tasks_concluidas` (contagem bruta daquele sprint, dentro daquele projeto)
- `autonomia_bloqueios_resolvidos_proprio`, `autonomia_bloqueios_totais` (contagem bruta daquele sprint, dentro daquele projeto)
- `arquetipo` (do projeto)
- `finalizado_em`

Gravada e travada no fechamento da sprint, junto com a exigência da avaliação completa. Somente leitura depois disso.

Reabertura ou resolução de bloqueio ocorrida após o fechamento do sprint de origem é atribuída ao sprint ativo no momento do evento, nunca reabre uma linha travada.

## Parte 12 — Área de Performance e Ranking (revisada: janela por contagem de sprint do operacional)

**Localização.** Rota própria `/performance`, fora de "Projetos", acesso exclusivo do Líder.

**A sequência pessoal do operacional.** Para cada operacional, monta-se a lista de todas as linhas em `pontuacao_operacional_sprint` onde ele teve `entrega_pontos_alocados > 0`, ordenada por `sprint_fim` decrescente. Essa lista pode misturar sprints de projetos diferentes, ordenados só pelo tempo de fechamento.

**Os três filtros, por contagem, não por calendário:**

| Filtro | Janela |
|---|---|
| Sprint / semanal | Última 1 linha da sequência pessoal |
| Quinzenal | Últimas 2 linhas |
| Mensal | Últimas 4 linhas |

**Agregação dentro da janela, duas camadas, replicando a Parte 9:**

Passo 1, agrupa as linhas selecionadas por `projeto_id`. Passo 2, dentro de cada grupo de projeto, soma numerador e denominador de cada dimensão-proporção across as linhas daquele projeto na janela, e tira a média simples das linhas de `gerente_media` e `gerente_pergunta6` daquele projeto. Passo 3, se a janela tiver mais de um projeto, tira a média simples dos valores já calculados por projeto, projeto a projeto, não pondera por volume.

```
Para cada projeto presente na janela:
  Entrega_projeto = Σ entrega_pontos_concluidos ÷ Σ entrega_pontos_alocados (linhas daquele projeto na janela)
  Qualidade_projeto = 100 − ((Σ qualidade_reaberturas ÷ Σ qualidade_tasks_concluidas) × 100)
  Autonomia_projeto = Σ autonomia_bloqueios_resolvidos_proprio ÷ Σ autonomia_bloqueios_totais
  Gerente_projeto = média de gerente_media (linhas daquele projeto na janela)
  Evolução_projeto = média de gerente_pergunta6 (linhas daquele projeto na janela) vs baseline

SE só 1 projeto na janela:
  valor_final_dimensão = valor_do_projeto_único

SE mais de 1 projeto na janela:
  valor_final_dimensão = média simples entre os projetos
```

**Arquétipo da janela**, suposição a confirmar: usa o arquétipo do projeto com mais linhas (sprints) dentro da janela, não mais pontos, para manter coerência com a lógica de não deixar volume dominar. Empate quebrado pela linha mais recente. Hoje isso não muda o resultado porque os pesos são idênticos entre arquétipos, mas o campo fica pronto.

**Score final da janela**, mesma fórmula:

```
Score = (Avaliação_Gerente × peso_gerente)
      + (Entrega × peso_entrega)
      + (Qualidade × peso_qualidade)
      + (Autonomia × peso_autonomia)
      + (Evolução × peso_evolucao)
```

**O que a tela mostra, só Líder.** Ranking completo ordenado por score na janela selecionada. Breakdown por dimensão de cada operacional. Comparação entre as três janelas para o mesmo operacional. Botão de gerar o anúncio do top performer (nome mais frase, sem número), disponível para qualquer uma das três janelas.

**Caso de janela incompleta.** Se o operacional tem menos linhas na sequência pessoal do que a janela pede (ex: mensal pede 4, ele só tem 2 porque é novo no ciclo), calcula com o que existe. **Resolvido nesta v3:** deve vir com aviso visual de "janela parcial" no ranking.

## Requisitos não funcionais

Peso, fórmula e score bruto nunca em payload de API para Gerente ou Operacional. Toda escrita em avaliação, baseline, bloqueio e score em log de auditoria. Trava de SprintCard, formulário de avaliação e modal de confirmação de transição validados no backend. Job de travamento automático nunca escreve em campo que alimenta o score.

## Critérios de aceite (Definition of Done)

Rename concluído com relatório. Toda transição de status exige confirmação. Reabertura só registrada em `concluida → em_andamento`. Bloqueio manual captura quem resolveu. Travamento automático usa limiar por ponto, ancorado em entrada em `em_andamento`, nunca alimenta score, com override auditável. Sete perguntas do gerente bloqueiam fechamento de sprint até completas. Operacional não acessa via API nenhum score, peso, ranking ou `travado_automatico` de si mesmo. SPI do Operacional soma dentro do projeto antes de dividir, e tira média simples entre projetos diferentes. Janela sprint/quinzenal/mensal é contada por linhas da sequência pessoal do operacional, não por data de calendário. Baseline de sprint travado após início. Rota `/performance` retorna 403 para Gerente ou Operacional, testável direto por API.

## Decisões em aberto, não resolver sem confirmar com Gabriel

- **Resolvido nesta v3:** motivo da reabertura é opcional.
- **Resolvido nesta v3:** janela de edição da avaliação do gerente é 48h.
- **Resolvido nesta v3:** Avaliação do Gerente é uma resposta por operacional por projeto-sprint (como desenhado), não agregada por semana calendário. Quando o gerente for avaliar um operacional que está em outro projeto também, a UI oferece a opção de reaproveitar a última avaliação feita no outro projeto, indicando data e projeto de origem. Isso pode gerar mais de uma avaliação na mesma semana calendário se o operacional estiver em dois projetos com sprints fechando perto — aceito como consequência do desenho por projeto-sprint.
- **Resolvido nesta v3:** janela parcial (operacional com menos sprints do que a janela pede) deve vir sinalizada visualmente no ranking.
- **Ainda em aberto:** se algum dado objetivo deve diferenciar peso entre arquétipos agora que CSAT saiu.
