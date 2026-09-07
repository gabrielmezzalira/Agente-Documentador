# Sistema de Acompanhamento de Performance

**Metodologia, regras de cálculo e manual do gerente**
Subárea de Dados · CITi · Gestão 26.2

> **Classificação: restrito a Líder e Gerente.**
> Este documento contém a camada oculta do sistema: pesos, fórmulas, fontes de
> dado e mecânica de fechamento. Não é acessível a operacionais dentro do
> sistema e não deve ser repassado fora da liderança. O que pode ser comunicado
> ao time está na seção 13.

---

## Índice

1. [Objetivo](#1-objetivo)
2. [Princípio central: direção pública, cálculo oculto](#2-princípio-central-direção-pública-cálculo-oculto)
3. [Fundamentação](#3-fundamentação)
4. [Como o sistema funciona, em quatro etapas](#4-como-o-sistema-funciona-em-quatro-etapas)
5. [As cinco dimensões](#5-as-cinco-dimensões)
6. [Pesos e tipos de projeto](#6-pesos-e-tipos-de-projeto)
7. [O questionário de sete perguntas](#7-o-questionário-de-sete-perguntas)
8. [Como o dado é produzido no dia a dia](#8-como-o-dado-é-produzido-no-dia-a-dia)
9. [O fechamento da sprint](#9-o-fechamento-da-sprint)
10. [Janelas e ranking](#10-janelas-e-ranking)
11. [A conta final, passo a passo](#11-a-conta-final-passo-a-passo)
12. [Guard-rails e anti-gaming](#12-guard-rails-e-anti-gaming)
13. [Acesso, sigilo e o que divulgar](#13-acesso-sigilo-e-o-que-divulgar)
14. [Manual do gerente](#14-manual-do-gerente)
15. [Casos de borda e regras finas](#15-casos-de-borda-e-regras-finas)
16. [Erros que o sistema devolve e o que fazer](#16-erros-que-o-sistema-devolve-e-o-que-fazer)

---

## 1. Objetivo

O sistema mede a performance individual dos operacionais da subárea de Dados com
finalidade de **ranking**, para incentivar o trabalho e desenvolver as pessoas.
Ele opera em duas camadas: uma **camada pública**, que gera o incentivo, e uma
**camada oculta**, que impede o gaming e mantém a justiça.

Três coisas que o sistema **não** é, e que a liderança precisa segurar:

- **Não é métrica de saúde do squad.** Saúde de projeto é medida em nível de
  time, com o SPI da sprint, o tempo de ciclo e o semáforo de saúde. Ranking
  individual e saúde de squad são coisas separadas: fundidas, nenhuma das duas
  funciona.
- **Não é instrumento de desligamento.** É instrumento de reconhecimento e
  desenvolvimento. Nada aqui foi calibrado para suportar decisão punitiva.
- **Não é auditoria de código.** Nenhuma contagem de commit, de linha ou de task
  entra como moeda. Ver seção 12.

**Ritmo:** a sprint dura **uma semana**. O reconhecimento (top performer ou
techlead do período) é anunciado **a cada duas semanas**, ou seja, a cada duas
sprints fechadas.

---

## 2. Princípio central: direção pública, cálculo oculto

A **camada pública** é a direção. Os operacionais sabem quais comportamentos
contam, que são entregar com qualidade, ajudar o time, ser autônomo, evoluir e
documentar. E sabem que existe reconhecimento periódico para quem mais contribui.

A **camada oculta** é o cálculo: pesos, fórmulas, normalização, notas cruas dos
gerentes e a posição de cada um no ranking nunca são divulgados.

A direção pública gera o incentivo, porque ninguém muda comportamento por uma
recompensa que não sabe que existe. O cálculo oculto impede o gaming dos pesos.
Esse é o ponto de equilíbrio entre incentivar e resistir a manipulação, e é o
único desenho em que "oculto" e "incentiva" coexistem.

Esse princípio não é só um acordo social, ele é imposto pelo próprio sistema:

| O que | Quem enxerga |
|---|---|
| Ranking e score final | Owner e Líder |
| Entrega consolidada e evolução de cada operacional | Owner, Líder e Gerente |
| Notas cruas do questionário e métricas do projeto | Owner, Líder e Gerente |
| Esta metodologia | Owner, Líder e Gerente |
| A versão pública deste documento e o guia do sistema | Todo mundo |
| Kanban, tasks e sprints do próprio projeto | Todos os vinculados ao projeto |

Toda vez que alguém abre a tela de ranking, o acesso fica registrado.

---

## 3. Fundamentação

O desenho segue o consenso de mercado sobre medição de performance em tecnologia.

**SPACE** (Forsgren e outros, ACM Queue, 2021) estabelece que produtividade é
multidimensional e não é capturada por uma métrica única. Métricas de output de
código, como commits, linhas e PRs, medem volume e não valor, e viraram
ativamente enganosas quando a IA gera parte relevante do código. Por isso este
sistema mede em cinco dimensões e nunca usa contagem de código como moeda.

**DX Core 4** (Noda e Tacho, 2024) organiza a medição em dimensões oposicionais,
onde cada uma segura o exagero da outra. Esse é o princípio anti-gaming central:
uma métrica de volume só entra quando outra dimensão a pune ao ser gameada.

**O Google** amarra peso alto no gerente à calibração, que Laszlo Bock chama de
"a alma da avaliação", porque força cada gerente a justificar a nota para os
outros e alinha padrões diferentes. Por isso os 35% no gerente aqui são
inseparáveis da rotina de calibração da seção 14.

**A Microsoft**, ao sair do stack ranking, passou a avaliar a pessoa também pela
contribuição ao sucesso dos outros. Por isso colaboração vive dentro da avaliação
do gerente.

**A Adobe** substituiu a avaliação anual por conversa frequente. Por isso o
feedback aqui é semanal, preso ao fechamento de cada sprint, e não anual.

---

## 4. Como o sistema funciona, em quatro etapas

O sistema não é um contador rodando o tempo todo. Ele é uma sequência de quatro
etapas, e entender essa separação evita quase toda a confusão operacional.

### Etapa 1. Coleta, durante a semana

Enquanto a sprint corre, o sistema observa o trabalho normal de gestão:

- o escopo do projeto dividido em pontos, e quanto desses pontos cada sprint recebeu
- as tasks do Kanban, com seus pontos, quem está com elas e por onde elas passaram
- os bloqueios registrados e quem os resolveu
- as tasks que ficaram paradas tempo demais
- os commits enviados, que recebem uma nota de qualidade avaliada por IA
- os pedidos de mais trabalho, quando alguém termina tudo que tinha

Nada disso é "nota" ainda. É dado bruto vivo, que muda o tempo todo.

### Etapa 2. Fechamento, no fim da sprint

O gerente responde as sete perguntas sobre cada operacional e confirma a Avaliação
Semanal. Nesse instante o sistema tira uma fotografia do estado da sprint e
**trava** uma linha de dado bruto por operacional. A partir daí aquela sprint não
muda mais.

### Etapa 3. Agregação, quando alguém abre a tela

O sistema pega as linhas travadas mais recentes da pessoa, monta a janela de
comparação (1, 2 ou 4 sprints) e calcula as cinco dimensões, cada uma numa escala
de 0 a 100.

### Etapa 4. Ranking

As cinco dimensões viram um número só, o score final, através dos pesos. As
pessoas são ordenadas por esse número, dentro de cada janela.

### O que essa separação implica

- **O score nunca é "ao vivo".** Ele só passa a existir depois que o gerente
  confirma a Avaliação Semanal. Sprint aberta não gera pontuação nenhuma.
- **O fechamento é uma fotografia, não um contador.** O sistema lê como as coisas
  ficaram no momento em que roda. Por isso trocar o responsável de uma task no
  meio da semana não exige nada de ninguém: o cálculo simplesmente lê o resultado.
- **A conta é refeita a cada leitura.** Mudar um peso muda o ranking na hora, sem
  reprocessar nada, porque o que ficou travado foi o dado bruto e não a nota.
- **Nada é reescrito para trás.** Uma sprint fechada não é recalculada.

---

## 5. As cinco dimensões

Cada dimensão vira um número de **0 a 100** antes de ser multiplicada pelo peso.
As fórmulas são fixas e absolutas: nenhuma depende de comparar a pessoa com as
outras. Isso foi decisão explícita contra ranquear por percentil, onde o placar de
alguém muda porque outra pessoa entrou ou saiu do grupo, o que destrói qualquer
leitura de evolução individual.

Todas as contas abaixo são feitas **por projeto primeiro**. Se a janela cobre mais
de um projeto, o valor final da dimensão é a média simples dos valores de cada
projeto.

### 5.1 Entrega e Confiabilidade

**O que mede:** cumpriu o que se comprometeu, dentro do que pegou.

> **Entrega** = (pontos entregues menos pontos descontados por atraso) dividido
> pelos pontos que a pessoa pegou, em porcentagem, com teto de 100.

- Somam-se todas as sprints da janela dentro do mesmo projeto.
- **Teto de 100.** Entregar além do que pegou não pontua acima do máximo. Isso
  existe para que puxar task extra no fim da semana não vire alavanca de score.
  O reconhecimento por trabalho extra vem pelo bônus da seção 5.6.
- Se a pessoa não pegou nenhum ponto na janela, a dimensão fica **indisponível**,
  e não vira zero.

**O desconto por atraso.** Quando uma task fica parada muito além do tempo
esperado para o tamanho dela, o sistema marca um alerta (seção 8.6). Se a pessoa
concluir essa task depois do alerta, os pontos dela são **descontados** da
entrega: a pessoa entregou, mas fora do prazo, então aquela entrega não conta
cheia. O gerente pode dispensar o alerta na própria task e a penalidade não
acontece.

O desconto só existe para task que foi **concluída** depois do alerta. Task que
travou e nunca foi entregue não sofre desconto nenhum, porque os pontos dela já
não estavam nos entregues, e descontar de novo puniria as outras entregas da
pessoa duas vezes pelo mesmo problema.

**Por que é proporção e não soma bruta:** volume absoluto de pontos mede quem
recebeu as tasks maiores, ou seja, mede a decisão de alocação do gerente e não a
performance da pessoa. Medir o que ela entregou sobre o que ela pegou faz com que
quem cumpriu tudo pontue alto mesmo tendo pego menos.

### 5.2 Avaliação do Gerente

**O que mede:** a leitura estruturada do gerente sobre o operacional, incluindo o
sinal de colaboração.

> **Avaliação do Gerente** = média das seis perguntas do questionário, convertida
> da escala 0 a 5 para 0 a 100.

A pergunta de evolução fica **fora** desta média de propósito: ela é a fonte
exclusiva da dimensão Evolução, e contá-la duas vezes daria peso desproporcional
a uma única pergunta.

Se nenhuma sprint da janela tem avaliação, a dimensão fica indisponível.

**Por que é a maior fatia, mas não maior ainda:** acima do que está hoje o
ranking vira ranking de opinião de gerente vestido de dado. Em projeto com
código, metade do peso continua em dimensões objetivas, que são as difíceis de
gamear. E esse peso só é justo se a calibração da seção 14 acontecer de fato.

### 5.3 Qualidade Técnica

**O que mede:** o trabalho precisou de pouca correção e seguiu o padrão.

Aqui vale separar dois nomes que confundem. **Nota de commit** é uma das duas
*fontes*. **Qualidade** é a *dimensão*, que junta as duas fontes num número só:

| Fonte | O que é | O que ela enxerga |
|---|---|---|
| Nota de commit | Uma IA lê a mensagem e o conteúdo de cada commit e dá uma nota de 0 a 10 | Como o trabalho foi feito: clareza, tratamento de erro, documentação, complexidade |
| Retrabalho | Quantas tasks concluídas voltaram para Em Andamento | Se o trabalho realmente estava pronto |

As duas se cobrem. Nota de commit alta com retrabalho alto significa código
bonito que não funcionava. Retrabalho baixo com nota de commit baixa significa
que funcionou, mas está mal feito e vai custar caro depois. Nenhuma das duas
sozinha diz a verdade, por isso a dimensão é a combinação.

> **Retrabalho** = 1 menos (tasks reabertas dividido por tasks concluídas), em
> porcentagem.
>
> **Nota de commit** = média das notas de 0 a 10 do período, convertida para 0 a 100.
>
> **Qualidade** = metade da nota de commit mais metade do retrabalho.

**Sobre a divisão meio a meio.** Hoje as duas fontes pesam igual, 50% cada. Esse
50/50 é um chute inicial, não uma verdade: depois de rodar um ciclo a liderança
vai saber qual das duas é mais confiável na prática do CITi e pode mudar para
70/30, por exemplo. Só a liderança muda isso, e a mudança vale a partir da
leitura seguinte.

Quando falta uma das fontes, a dimensão usa a que sobrou. Em projeto de
consultoria não existe nota de commit, então Qualidade é o retrabalho puro.

**Quem não concluiu nada fica sem nota de Qualidade.** A dimensão fica
indisponível, e não vira 100. Dar nota máxima a quem não entregou nada seria
premiar a ausência de entrega, e a falta de entrega já é penalizada onde deve
ser, que é em Entrega.

**Reabertura** tem definição estrita: é uma task que estava em Concluída e voltou
para Em Andamento. Voltar de Concluída para Planejado não conta como reabertura.

### 5.4 Autonomia

**O que mede:** quanto a pessoa destrava sozinha antes de escalar.

A dimensão combina duas fontes, pelo mesmo motivo de Qualidade: uma é objetiva
mas pode não existir, a outra sempre existe mas é subjetiva.

> **Sinal de bloqueio** = bloqueios que a própria pessoa resolveu dividido pelos
> bloqueios que ela teve, em porcentagem.
>
> **Sinal do gerente** = a pergunta "a pessoa destravou sozinha antes de te
> escalar?", convertida de 0 a 5 para 0 a 100.
>
> **Autonomia** = metade de cada.

Se não houve bloqueio nenhum registrado na janela, Autonomia é só a leitura do
gerente. Se não houve avaliação, é só o sinal de bloqueio. Se não houver nenhum
dos dois, a dimensão fica indisponível.

Essa segunda fonte existe por um motivo prático: na maior parte das semanas
ninguém marca bloqueio nenhum. Antes disso, Autonomia dava 100 fixo nesses casos
e a dimensão virava peso morto, premiando igualmente quem nunca travou e quem
travou o tempo todo sem registrar.

Task parada tempo demais **não** entra aqui. Atraso penaliza Entrega, não
Autonomia, porque são coisas diferentes: uma é sobre demora, a outra é sobre
depender dos outros.

### 5.5 Evolução

**O que mede:** quanto a pessoa cresceu em relação a onde estava.

> **Evolução** = a pergunta de evolução do questionário, convertida da escala 0 a
> 5 para 0 a 100.

É a única dimensão que compara a pessoa com ela mesma, e não com um padrão
absoluto. É o que dá chance real a quem entrou mais júnior.

### 5.6 Bônus de task extra

Não é uma dimensão, é um acréscimo direto no score final.

Quando o operacional termina tudo o que tinha e pede mais trabalho (seção 8.9), a
task concedida é marcada como **extra**. Ela não consome o orçamento de pontos da
sprint e não entra em Entrega. Se for concluída antes do fechamento:

> **Bônus** = 1 ponto de score por ponto de task extra concluída, somado ao score
> final, **até o limite de 5 pontos** por janela.

Duas escolhas de desenho por trás disso:

- **Não entra em Entrega** porque a task extra não consumiu orçamento. Colocá-la
  no denominador puniria justamente quem pediu mais trabalho, e no numerador não
  faria efeito nenhum por causa do teto de 100.
- **Tem teto** porque sem ele o ranking viraria "quem pediu mais task", que é
  exatamente o tipo de métrica de volume que o resto do sistema evita. O gerente
  também controla a torneira, já que é ele quem decide conceder.

## 6. Pesos e tipos de projeto

### 6.1 Os dois tipos de projeto

Cada projeto é classificado como:

- **Padrão**, projeto com entrega de código. A avaliação de qualidade de commit
  fica ativa.
- **Consultoria ou discovery**, projeto sem entrega de código. A avaliação de
  commit fica desligada.

### 6.2 Os pesos

| Dimensão | Projeto padrão | Consultoria ou discovery |
|---|---|---|
| Avaliação do Gerente | **35%** | **50%** |
| Entrega e Confiabilidade | **20%** | **20%** |
| Qualidade Técnica | **20%** | **10%** |
| Autonomia | **15%** | **12%** |
| Evolução | **10%** | **8%** |

Cada coluna soma 100%.

**Por que consultoria pesa mais no gerente.** Em projeto sem código, metade dos
sinais objetivos simplesmente não existe: não há commit para avaliar, e Qualidade
fica reduzida ao retrabalho de Kanban, que num projeto de discovery diz muito
pouco. Insistir em pesos iguais nos dois tipos seria fingir que existe medição
objetiva onde ela não existe. O peso maior no gerente reconhece que, nesse tipo
de projeto, quem tem a leitura real é ele.

O preço dessa escolha é que a nota de alguém em consultoria depende mais do
julgamento de uma pessoa só. É mais um motivo para a calibração da seção 14 ser
levada a sério, e é o principal ponto a observar no primeiro ciclo.

Os pesos são configuráveis pela liderança, e mudar um peso muda o ranking na
leitura seguinte, sem precisar reprocessar nada. Isso é de propósito: recalibrar
depois de rodar um ciclo tem que ser barato.

### 6.3 Quando a janela mistura projetos

Uma janela pode cobrir mais de um projeto, inclusive de tipos diferentes. Os
pesos aplicados são os do projeto com mais sprints dentro daquela janela; em
empate, vale o projeto da sprint mais recente.

## 7. O questionário de sete perguntas

O gerente responde **por operacional, por sprint**, ou seja, toda semana, numa
escala de **0 a 5**. Todas as sete são obrigatórias, não existe "não sei".

| # | Pergunta | Âncora 0 | Âncora 5 |
|---|---|---|---|
| 1 | Entregou o que se comprometeu dentro do combinado nesta sprint? | quase nada do previsto | tudo no prazo |
| 2 | A qualidade da entrega precisou de pouca ou nenhuma correção? | refiz quase tudo | entrou limpo |
| 3 | A pessoa destravou sozinha antes de te escalar? | dependeu de mim o tempo todo | resolveu sozinha |
| 4 | A comunicação da entrega foi clara a ponto de você não precisar perguntar? | tive que decifrar | entendi de primeira |
| 5 | Ajudou, desbloqueou ou ensinou outro membro nesta sprint? | não interagiu | foi peça de apoio do squad |
| 6 | Evoluiu em relação a onde estava no começo do ciclo? | estagnou | salto claro |
| 7 | Trouxe algo além do que foi pedido? | fez o mínimo | antecipou problema ou propôs melhoria |

### 7.1 Para onde vai cada pergunta

| Pergunta | Alimenta | Peso no score, em projeto padrão |
|---|---|---|
| 1, 2, 4, 5, 7 | Avaliação do Gerente | cerca de 5,8% cada |
| 3 | Avaliação do Gerente **e** metade de Autonomia | cerca de 5,8% mais 7,5% |
| 6 | Evolução, sozinha | 10% |

A pergunta 6 não entra na média das outras seis: ela é a dimensão Evolução
inteira.

A pergunta 3 é a única que alimenta duas coisas, e de propósito. Ela entra na
média do gerente como qualquer outra, e ao mesmo tempo sustenta metade de
Autonomia nas semanas em que ninguém registrou bloqueio, que são a maioria.

A pergunta 5, sobre colaboração, vale por volta de 5,8% do score. É um sinal real,
mas não é uma dimensão própria. Se o acompanhamento mostrar queda de colaboração,
o caminho de correção é aumentar o peso da avaliação do gerente ou promover a
colaboração a dimensão separada.

Em projeto de consultoria todos esses pesos sobem, porque a avaliação do gerente
vale 50% em vez de 35%.

### 7.2 Como responder bem

- **Ancore na sprint, não na pessoa.** A pergunta é sobre o que aconteceu nesta
  semana, não sobre quem a pessoa é.
- **Use a escala inteira.** Um gerente que só dá 4 e 5 destrói a comparação para
  todos os operacionais dele. A calibração da seção 14 existe justamente para isso.
- **3 é "fez o combinado".** 5 é excepcional, e não "não tenho reclamação".
- **Cuidado redobrado com a pergunta 3.** Ela é a que mais pesa depois da 6, e na
  maioria das semanas é a única fonte de Autonomia. Responda pensando em quantas
  vezes você precisou entrar para destravar a pessoa, não na impressão geral.

### 7.3 Janela de correção de 48 horas

Uma avaliação salva pode ser editada por **48 horas** a partir do momento em que
foi criada. Depois disso o sistema recusa a alteração.

Isso protege a integridade do dado sem impedir correção de erro honesto. Repare
que o prazo conta da criação, e não da última edição.

### 7.4 Reaproveitar avaliação de outro projeto

Se a mesma pessoa já foi avaliada recentemente em outro projeto, o sistema oferece
"usar essas respostas" e preenche as sete notas a partir da última avaliação
encontrada.

Use com cuidado. É um atalho para quem acompanha a mesma pessoa em dois projetos e
teve a mesma leitura. Não é um botão de repetir nota, porque a avaliação
reaproveitada entra na conta com o mesmo peso de uma avaliação pensada.

---

## 8. Como o dado é produzido no dia a dia

Nada nesta seção é "preencher planilha de performance". É o trabalho normal de
gestão de sprint. O ponto é que **o sistema só enxerga o que passou pelo Kanban**.

### 8.1 Os 100 pontos do projeto

Todo projeto vale **100 pontos, fixo**. Não é um número que o gerente escolhe.

Se o gerente informar o valor do projeto em reais, cada ponto passa a valer um
centésimo desse valor, e o faturamento previsto de cada sprint sai daí
automaticamente. O valor do projeto só pode ser mudado enquanto nenhuma sprint
tiver recebido orçamento de pontos: depois disso ele congela, porque mudá-lo
desalinharia em silêncio todo o faturamento já calculado.

### 8.2 Quanto cada sprint recebe dos 100 pontos

No planejamento, na aba Escopo, o gerente distribui os 100 pontos entre as sprints.
Se o projeto tem 10 sprints previstas e todas são parecidas, cada uma recebe por
volta de 10 pontos. Se uma sprint concentra a parte pesada, ela recebe mais.

Três regras governam essa distribuição:

- A soma de todas as sprints **não pode passar de 100**, porque 100 é o projeto
  inteiro.
- Uma sprint **não pode receber menos pontos do que as tasks dela já somam**. Não
  dá para prometer menos do que já foi gasto.
- Sprint sem orçamento definido não entra na soma e não trava nada. Planejamento
  incompleto não impede trabalhar.

Ao marcar o projeto como entregue, se a soma não for exatamente 100 o sistema
avisa, mas não bloqueia. Exigir 100 exato só incentivaria inflar pontos para
fechar a conta.

### 8.3 Quantos pontos cada task vale

Os pontos da sprint são divididos entre as tasks dela. Uma sprint de 10 pontos
pode ter cinco tasks de 2, ou duas de 3 mais uma de 4. O que não pode é a soma
das tasks passar do que a sprint recebeu.

Na prática:

- **Se a sprint tem orçamento definido**, o sistema recusa uma task nova que faria
  a soma estourar, e diz quantos pontos ainda sobram.
- **Se estourou mas o trabalho existe mesmo**, aparece o botão **"Redistribuir
  pontos"**. Ele encolhe proporcionalmente as tasks que já estão na sprint para
  abrir espaço, e mostra o antes e o depois de cada uma. Cada task fica com no
  mínimo 1 ponto, então sprint muito cheia pode não conseguir abrir o espaço
  pedido, e aí o sistema diz qual é o máximo liberável.
- **Se a sprint não tem orçamento definido**, não há validação nenhuma. Você pode
  trabalhar normalmente e planejar depois.
- **Se você move uma task de uma sprint para outra**, a validação é refeita contra
  a sprint de destino, que é quem vai pagar por aqueles pontos.
- **Task marcada como extra não entra nessa conta.** Ela é trabalho concedido
  além do planejado, então por definição não cabe no orçamento e não é validada
  contra ele (seção 8.9).
- **Tasks e sprints criadas antes desta regra existir** não são revalidadas. Nada
  quebra retroativamente.

**Por que isso importa para o acompanhamento:** os pontos da task são o
denominador de Entrega. Se uma task de 2 pontos é cadastrada como 8, a Entrega
daquela pessoa naquela semana perde o sentido. Pontuar task com honestidade é a
única disciplina que Entrega exige do gerente.

### 8.4 O caminho de uma task no Kanban

O Kanban tem três colunas: **Planejado**, **Em Andamento** e **Concluída**. Quatro
regras controlam o movimento entre elas.

**Uma task só entra em Em Andamento se estiver ligada a uma sprint.** Sem sprint,
não existe a quem creditar aquele trabalho quando a semana fechar, então o sistema
recusa o movimento e pede que você escolha a sprint antes.

**Uma task só vai para Concluída com o checklist completo.** O checklist é uma
lista de itens que você monta já na criação da task, e pode editar depois a
qualquer momento. O card mostra quantos já foram marcados, no formato "3/5". Se sobrou item desmarcado, o sistema recusa mover para
Concluída. Task sem checklist nenhum não trava nada: a regra só vale se você
criou a lista. É o freio contra a "concluída" nominal, aquela que volta como
reabertura três dias depois e derruba a nota de Qualidade da pessoa sem
necessidade.

**Existe um limite de tasks simultâneas em Em Andamento.** Você configura dois
limites opcionais no projeto: quantas tasks o projeto inteiro pode ter em
andamento, e quantas cada pessoa pode ter. Ao estourar, o sistema recusa e diz qual
limite foi atingido. É o freio contra o squad começar dez coisas e terminar duas.

**Todo movimento fica registrado com quem estava na task naquele momento.** Se a
Ana está com uma task e passa para o João antes de terminar, os pontos vão junto:
quem entrega é quem recebe. O que o registro impede é o caso inverso, de uma task
que a Ana já concluiu ser repassada depois e o crédito ir para alguém que não fez
o trabalho.

### 8.5 Como sinalizar bloqueio de task na tela

Bloqueio é uma das duas fontes de Autonomia, e é marcado por **quem está travado**,
ou seja, o próprio operacional. Ele tem acesso ao Kanban do projeto dele e é quem
sente o problema na hora em que acontece.

**Para marcar um bloqueio:**

1. Abra a task no Kanban do projeto.
2. Marque a caixa **"Bloqueada"**.
3. Preencha **"Motivo do bloqueio"** e **"Quem bloqueou?"**.
4. Salve.

A task passa a mostrar uma **borda vermelha** e uma etiqueta **"Bloqueada"** no
card, então o gerente vê o que está travado só de bater o olho no quadro. Esse é o
ganho imediato, independente de pontuação: bloqueio deixa de ser algo que só
aparece na daily se a pessoa lembrar de falar.

**O que conta como bloqueio.** Qualquer coisa que impeça o trabalho de continuar e
que não dependa só de a pessoa sentar e fazer:

- esperando resposta ou material do cliente
- esperando acesso, credencial ou permissão
- esperando outra task terminar
- dúvida técnica que a pessoa não conseguiu resolver sozinha
- decisão de escopo ou de prioridade que ainda não foi tomada

Não é bloqueio: task difícil, task grande, ou task que a pessoa não começou.

**Para resolver:**

1. Abra a task e **desmarque** a caixa "Bloqueada".
2. Escolha no campo obrigatório **"Quem resolveu?"** entre **Operacional** e
   **Gerente**.
3. Salve. Sem escolher uma das duas, o sistema recusa.

Essa escolha é o sinal objetivo de Autonomia: **Operacional** significa que a
pessoa destravou sozinha e conta a favor dela; **Gerente** significa que alguém
precisou entrar, e conta como bloqueio ocorrido sem crédito de autonomia.

**Se ninguém marcar bloqueio, nada quebra.** Nesse caso Autonomia é calculada só
pela pergunta 3 do questionário. O registro de bloqueio é o que torna a dimensão
mais precisa, não o que a torna possível.

### 8.6 Task parada tempo demais

Todo dia o sistema varre as tasks em Em Andamento. Se uma delas está parada há
mais tempo do que o esperado para o tamanho dela, ganha uma etiqueta amarela
**"Travada"** no card e um aviso dentro da task.

O limite é de **um dia e meio por ponto**:

| Tamanho da task | Vira "travada" depois de |
|---|---|
| 1 ponto | 2 dias |
| 2 pontos | 3 dias |
| 3 pontos | 5 dias |
| 4 pontos | 6 dias |
| 5 pontos | 8 dias |
| 8 pontos | 12 dias |

O número é proporcional de propósito: uma task de 1 ponto parada há três dias é um
problema, e uma de 8 pontos no terceiro dia é normal. Com sprint de uma semana,
tasks acima de 4 pontos só travam depois do fim da sprint, o que é mais um motivo
para quebrar trabalho grande em tasks menores.

**O efeito na nota.** Se a task for concluída depois do alerta, os pontos dela são
descontados da Entrega da pessoa. Se ela nunca for concluída, não há desconto
nenhum, porque os pontos já não estavam contando como entrega.

O aviso dentro da task traz um campo para o **gerente dispensar o alerta**,
informando o próprio nome. Dispensar tira a etiqueta e **cancela o desconto**. É a
válvula de escape para quando o atraso não é responsabilidade do operacional, como
dependência de cliente, espera por acesso ou mudança de prioridade. O alerta é
automático, mas a penalidade é sempre revisável pelo gerente.

Atraso penaliza **Entrega**, e nunca Autonomia. Bloqueio é uma coisa, demora é
outra.

### 8.7 A nota de qualidade dos commits

Quando um commit chega ao sistema, vindo da integração instalada no repositório do
projeto, e **somente em projetos do tipo Padrão**, uma IA lê a mensagem e o
conteúdo da mudança e devolve uma nota de **0 a 10** com uma frase curta
justificando. Ela olha três coisas:

- a complexidade do que foi resolvido naquele commit
- a qualidade da documentação e da mensagem de commit
- a aderência a boas práticas, como nomes claros, tratamento de erro e testes
  quando cabe

A IA é instruída a nunca listar pendências a corrigir. Ela devolve só a nota e o
porquê, no espírito de um placar.

**Como o commit encontra a pessoa,** nesta ordem:

1. pelo **usuário do GitHub** cadastrado no operacional
2. se não achar, pelo **e-mail** cadastrado no operacional
3. se não achar nenhum dos dois, a nota é gravada sem dono e **não conta para
   ninguém**

> **Ação obrigatória do gerente:** preencher o usuário do GitHub de cada
> operacional. Sem isso os commits da pessoa não pontuam em Qualidade e ela fica
> avaliada só pelo retrabalho, em silêncio, sem nenhum erro aparecer na tela.

Se a avaliação da IA falhar por qualquer motivo, o commit continua sendo registrado
normalmente. A nota é um extra, não um pré-requisito.

### 8.8 Como a planning se conecta com as tasks

O documento de planning não é escrito à parte do Kanban: ele é montado a partir
dele. O caminho é este.

1. **Antes de abrir a planning**, cadastre as tasks da sprint no Kanban, com
   pontos e responsável. É delas que sai o backlog do documento.
2. **Ao abrir a planning** no card da sprint, a tela já mostra as tasks que estão
   naquela sprint, com coluna, pontos e se alguma está bloqueada. Você não precisa
   listar nada à mão.
3. **Se as tasks estiverem fora do sistema**, num Notion ou numa planilha, o link
   no topo da tela leva para a importação: você sobe um print ou cola o texto, e a
   IA extrai as tasks e correlaciona com as funcionalidades do escopo.
4. **Você escreve o contexto da sprint** num campo de texto livre, sem formatação
   nenhuma. É onde entra o que o Kanban não consegue dizer: por que a sprint é
   curta, o que mudou com o cliente, quem entrou agora, o que preocupa. Esse texto
   vai como insumo para a IA, não como documento final.
5. **Você completa os campos estruturados**: período, horas disponíveis e
   estimadas, dependências, riscos, carry-over da sprint anterior, e quais
   funcionalidades do escopo entram nesta sprint.
6. **A IA gera o documento** juntando tudo: as tasks do Kanban, o seu texto livre,
   os campos estruturados, as funcionalidades selecionadas com os critérios de
   aceite recortados, o que transbordou da sprint anterior e o ritmo médio das
   últimas sprints.
7. **Você revisa e confirma.** Só na confirmação o documento é salvo.

Se preferir escrever o documento inteiro na mão, sem IA nenhuma, existe o caminho
"Escrever sem IA". Ele salva exatamente o que você escrever, sem formatação
obrigatória.

**Por que isso importa para o acompanhamento:** o Kanban é a fonte, e ele alimenta
duas coisas ao mesmo tempo. A documentação da sprint sai dele, e a pontuação de
cada pessoa também. Manter o Kanban fiel à realidade não é burocracia a mais: é o
que faz os dois funcionarem sem trabalho dobrado.

### 8.9 Pedir mais trabalho quando a fila zera

Veio de um feedback real: operacional termina o que tinha e não tem proximidade,
ou não sabe como pedir mais task, e fica parado. O custo disso é duplo, porque o
projeto perde capacidade e a pessoa perde Entrega por um motivo que não é dela.

Como funciona:

1. Quando o operacional não tem **nenhuma task em aberto**, aparece no Kanban dele
   o botão **"Quero mais uma task"**.
2. Ao clicar, o gerente recebe um **e-mail** e o pedido aparece no topo do Kanban
   dele.
3. O gerente pode **criar uma task extra** para a pessoa ou responder **"nada
   agora"**. Recusar é uma resposta legítima e não penaliza ninguém.
4. Ao criar a task, o gerente marca a caixa **"Task extra"**. Isso faz duas coisas:
   a task não consome o orçamento de pontos da sprint, e os pontos dela não entram
   em Entrega.
5. Se a pessoa concluir a task extra antes do fechamento, ela ganha o bônus da
   seção 5.6.

O botão só aparece com a fila zerada, então não dá para pedir task nova enquanto
há trabalho parado. E um pedido em aberto não vira dez: enquanto o gerente não
responde, o botão mostra que o pedido está aguardando.

---

## 9. O fechamento da sprint

É o momento em que o dado bruto vira pontuação travada. É o único momento em que
isso acontece.

### 9.1 Pré-condição: nenhuma avaliação pendente

A confirmação da Avaliação Semanal só roda se **todo operacional com pelo menos
uma task na sprint** já tiver sido avaliado. Se faltar alguém, o sistema recusa e
lista os nomes.

Isso é deliberado. Um fechamento parcial produziria pessoas sem nota do gerente,
que seriam ranqueadas só pelas dimensões objetivas, numa comparação injusta e
invisível (ver seção 11.3).

### 9.2 O que fica guardado

Para cada operacional com dado na sprint, fica registrado:

| O que | De onde vem |
|---|---|
| Média das seis perguntas do gerente | Questionário |
| Nota de evolução | Pergunta 6 do questionário |
| Nota de autonomia percebida | Pergunta 3 do questionário |
| Pontos que a pessoa pegou | Soma das tasks dela na sprint, concluídas ou não |
| Pontos que a pessoa entregou | Soma das tasks concluídas por ela |
| Pontos descontados por atraso | Tasks concluídas depois do alerta de atraso, sem dispensa do gerente |
| Pontos de task extra concluída | Tasks marcadas como extra que ficaram prontas na semana |
| Tasks concluídas e tasks reabertas | Kanban |
| Bloqueios que teve e quantos resolveu sozinha | Kanban |
| Nota média dos commits | Avaliação de IA no período |

Entra na lista quem tiver qualquer um desses dados, mesmo que não tenha concluído
nada.

### 9.3 Quem recebe os pontos de uma task

Os pontos de uma task concluída vão para **quem estava com ela no momento em que
foi concluída**, e não para quem está com ela agora. Tasks não concluídas contam
como "pegou" para o responsável atual.

É por isso que trocar responsável no meio da semana não exige nada de você.

### 9.4 Por que nada é contado duas vezes

Reabertura, bloqueio, atraso e nota de commit são eventos com data e hora, e não
campos fixos da sprint. Se o sistema simplesmente lesse "todos os eventos do
projeto" a cada fechamento, um bloqueio da semana passada seria contado de novo
nesta semana, e de novo na próxima.

Para evitar isso, cada fechamento anota a data e hora em que rodou. O fechamento
seguinte só considera eventos que aconteceram **depois** do fechamento anterior
daquele projeto.

Um exemplo. A Ana teve dois bloqueios na semana 1 e um bloqueio na semana 2:

- O fechamento da semana 1 roda na sexta e conta os dois bloqueios.
- O fechamento da semana 2 roda na sexta seguinte e olha só o que aconteceu depois
  da sexta anterior. Ele conta um bloqueio, não três.

No primeiro fechamento do projeto ainda não existe marco anterior, então todo o
histórico entra de uma vez. Isso é esperado.

### 9.5 Confirmar duas vezes não faz nada, e o Líder pode reabrir

Se a sprint já foi fechada, clicar em confirmar de novo **não recalcula e não
duplica nada**. O sistema devolve o que já estava guardado. Isso protege contra
clique duplo, aba aberta duas vezes ou colega confirmando junto.

**Se o fechamento foi feito com dado errado, o Líder pode reabrir.** No card da
sprint aparece o botão **"Reabrir fechamento"**, visível só para o Líder. Ele
apaga a pontuação travada daquela sprint e devolve a sprint ao estado aberto, para
o gerente corrigir o Kanban e confirmar de novo.

Três coisas importantes sobre reabrir:

- **As respostas do questionário não são apagadas.** O gerente não precisa
  responder as sete perguntas de todo mundo outra vez, e a janela de 48 horas de
  edição continua valendo como antes.
- **O marco de tempo se ajusta sozinho.** Aquele marco que evita contar o mesmo
  bloqueio duas vezes (seção 9.4) é derivado do fechamento mais recente do
  projeto, então apagar o fechamento devolve o marco ao estado anterior sem
  ninguém precisar fazer nada.
- **É restrito ao Líder** porque mexe em dado que já entrou no ranking. Se você é
  gerente e precisa corrigir uma semana fechada, peça a ele.

Ainda assim, reabrir é conserto e não rotina. A prevenção é o checklist da seção
14 antes de confirmar.

### 9.6 Coisas que acontecem depois do fechamento

Se uma task de uma sprint já fechada é reaberta, ou um bloqueio dela é resolvido
depois, o evento não é perdido nem reescreve a semana fechada. Ele é redirecionado
para a **sprint aberta do projeto** e entra no fechamento seguinte. Se não houver
sprint aberta, o evento fica só no histórico e não afeta pontuação nenhuma.

---

## 10. Janelas e ranking

### 10.1 Uma pessoa é uma pessoa, mesmo em vários projetos

Cada projeto tem sua própria lista de operacionais. Quem trabalha em dois projetos
aparece nas duas listas.

**No ranking essas aparições viram uma pessoa só.** O sistema junta tudo pelo
**e-mail** cadastrado, calcula cada dimensão dentro de cada projeto e depois tira
a **média simples** entre os projetos. Quem está em dois projetos é avaliado pela
média dos dois, não pela soma nem pelo melhor deles.

A consequência prática é dura mas necessária: **se o e-mail estiver diferente ou
em branco nos dois cadastros, o sistema não tem como saber que é a mesma pessoa**,
e ela aparece duas vezes no ranking, com metade do histórico cada. Por isso, ao
adicionar um operacional que já existe em outro projeto, use o atalho **"Já
trabalha em outro projeto?"** no formulário: ele preenche nome, e-mail, papel e
usuário do GitHub a partir do cadastro que já existe, e evita o erro de digitação
que parte a pessoa em duas.

Operacional desativado sai do ranking na hora.

### 10.2 As três janelas

Como a sprint dura uma semana, as janelas são:

| Janela | Cobre | Equivale a |
|---|---|---|
| Última sprint | 1 sprint | 1 semana |
| Últimas 2 sprints | 2 sprints | 2 semanas |
| Últimas 4 sprints | 4 sprints | 4 semanas |

A janela de 2 sprints é a que casa com o ritmo de reconhecimento, que é quinzenal.

**As janelas contam sprints, não dias de calendário.** Quem ficou duas semanas
fora tem a mesma janela de 4 sprints que todo mundo, só que composta por sprints
mais antigas. É intencional: compara volume de trabalho equivalente, e não período
de tempo equivalente.

Sprints em que a pessoa não pegou nenhum ponto não existem para o ranking, elas
são puladas.

Se a pessoa tem menos sprints do que a janela pede, a nota é calculada com o que
existe e a tela mostra **"janela parcial"**. Nota parcial não é comparável com
nota cheia, trate como indicativa.

---

## 11. A conta final, passo a passo

### 11.1 O caminho

1. **Junta a pessoa.** Todas as aparições dela, em todos os projetos, viram uma
   pessoa só, casadas pelo e-mail.
2. **Monta a janela.** Pega as sprints fechadas mais recentes em que ela pegou
   pontos: 1, 2 ou 4, conforme a janela escolhida na tela.
3. **Calcula cada dimensão dentro de cada projeto.** As cinco fórmulas da seção 5,
   aplicadas só às sprints daquela janela, projeto por projeto.
4. **Tira a média entre projetos.** Se a janela cobre mais de um projeto, cada
   dimensão vira a média simples dos valores por projeto. Projeto onde a dimensão
   não existe é ignorado, e não entra como zero.
5. **Aplica os pesos.** Multiplica cada dimensão pelo peso dela e soma. Os
   pesos dependem do tipo de projeto (seção 6).
6. **Soma o bônus de task extra**, se houver, respeitando o teto de 5 pontos. O
   resultado é o score final, de 0 a 100.
7. **Ordena.** As pessoas são listadas da maior nota para a menor, dentro de cada
   janela.

A média entre projetos é simples, e não ponderada por volume: um projeto pequeno
pesa igual a um grande. Isso protege quem foi alocado parcialmente em algo pequeno
de ver aquele projeto diluído a zero, mas também significa que uma semana ruim num
projeto pequeno machuca tanto quanto num grande.

### 11.2 Um exemplo do começo ao fim

A Maria, na janela de duas sprints, nos dois casos no mesmo projeto padrão.

| O que aconteceu | Sprint 12 | Sprint 13 |
|---|---|---|
| Pontos que ela pegou | 14 | 10 |
| Pontos que ela entregou | 12 | 10 |
| Pontos descontados por atraso | 0 | 2 |
| Média das seis perguntas do gerente | 4,17 | 4,50 |
| Nota de evolução, pergunta 6 | 4 | 5 |
| Nota de autonomia percebida, pergunta 3 | 4 | 5 |
| Tasks concluídas | 6 | 4 |
| Tasks reabertas | 1 | 0 |
| Bloqueios que teve | 3 | 1 |
| Bloqueios que resolveu sozinha | 2 | 1 |
| Nota média dos commits | 7,5 | 8,5 |

**As cinco dimensões:**

| Dimensão | Conta | Resultado |
|---|---|---|
| Entrega | (12 mais 10 menos 2) sobre (14 mais 10) | **83,33** |
| Avaliação do Gerente | média de 4,17 e 4,50, vezes 20 | **86,70** |
| Qualidade | retrabalho 90,00 e commits 80,00, meio a meio | **85,00** |
| Autonomia | bloqueios 75,00 e pergunta 3 em 90,00, meio a meio | **82,50** |
| Evolução | média de 4 e 5, vezes 20 | **90,00** |

O retrabalho saiu de 1 task reaberta em 10 concluídas, que dá 90. A nota de
commits foi a média de 7,5 e 8,5, que dá 8,0, convertida para 80. O sinal de
bloqueio foi 3 resolvidos sozinha em 4 bloqueios, que dá 75.

**O score final:**

| Dimensão | Nota | Peso | Contribuição |
|---|---|---|---|
| Avaliação do Gerente | 86,70 | 35% | 30,35 |
| Entrega | 83,33 | 20% | 16,67 |
| Qualidade | 85,00 | 20% | 17,00 |
| Autonomia | 82,50 | 15% | 12,38 |
| Evolução | 90,00 | 10% | 9,00 |
| | | | **85,39** |

Três coisas para reparar neste exemplo:

**O atraso custou caro.** Sem os 2 pontos descontados na sprint 13, a Entrega
teria sido 91,67 e o score subiria para 87,06. Uma task entregue fora do prazo
custou 1,67 ponto de score.

**A task extra teria compensado.** Se a Maria tivesse pedido e concluído uma task
extra de 3 pontos, o bônus levaria o score de 85,39 para **88,39**.

**Em consultoria a mesma pessoa daria 85,62.** Com os pesos de consultoria, a
leitura do gerente (86,70) puxa mais e a Qualidade pesa menos. A diferença é
pequena aqui porque as notas dela são parecidas entre si; quanto mais desigual o
perfil da pessoa, mais os dois tipos de projeto divergem.

### 11.3 O que acontece quando falta uma dimensão

Se uma dimensão não pode ser calculada, ela **não vira zero**. Ela sai da conta, e
o resultado é dividido pela soma dos pesos que sobraram.

Voltando à Maria: se ela não tivesse sido avaliada pelo gerente em nenhuma das duas
sprints, sumiriam a Avaliação do Gerente e a Evolução, e a Autonomia cairia para
75,00, porque perderia a fonte da pergunta 3 e sobraria só o sinal de bloqueio.
Restariam Entrega, Qualidade e Autonomia, que somam 55% de peso. A conta seria
16,67 mais 17,00 mais 11,25, dividido por 0,55, dando **81,67**.

Isso é matematicamente correto e comportamentalmente perigoso, porque coloca na
mesma tabela alguém medido por cinco dimensões e alguém medido por três. A defesa
contra isso é a trava da seção 9.1, que impede fechar a semana com avaliação
faltando. Enquanto essa trava for respeitada, o caso não acontece.

Se você vir alguém com um traço no lugar da nota do gerente, o score daquela pessoa
não é comparável com o dos outros.

Quem não tem nenhuma dimensão calculável simplesmente não aparece no ranking.

---

## 12. Guard-rails e anti-gaming

O princípio: **uma métrica de volume só é admitida quando outra dimensão a pune ao
ser gameada.**

### 12.1 A regra dura

> Contagem de task, de commit e de linha é guard-rail, nunca moeda.

Sob IA, commit e linha são quase de graça. Servem para cruzar com qualidade, jamais
para pontuar sozinhos. Nenhuma dessas contagens aparece em nenhuma das cinco
fórmulas.

### 12.2 Como cada tentativa de gaming se anula

| Tentativa | O que a segura |
|---|---|
| Fatiar task para inflar contagem | Entrega é proporção, então o denominador cresce junto. E o número de tasks concluídas sobe sem melhorar o retrabalho |
| Pegar poucas tasks para garantir 100% de Entrega | Entrega tem teto 100, então não há ganho. E a leitura do gerente enxerga volume baixo |
| Pegar muitas tasks e entregar metade | O que pegou cresce, o que entregou não. Entrega despenca |
| Segurar task por semanas para entregar "perfeita" | O alerta de atraso desconta os pontos dela da Entrega |
| Pedir task extra sem parar para acumular bônus | O bônus tem teto de 5 pontos, e quem concede é o gerente |
| Não concluir nada para escapar da nota de Qualidade | Qualidade fica indisponível, mas Entrega vai a zero, que pesa mais |
| Commit trivial em volume | A nota é por commit e entra como média, não como soma. Commit trivial puxa a média para baixo |
| Inflar linha de código com IA | Não existe contagem de linha em lugar nenhum, e a nota de commit avalia complexidade e aderência, não tamanho |
| Marcar task como concluída sem estar | O checklist bloqueia a conclusão, e a reabertura depois derruba a Qualidade |
| Nunca registrar bloqueio para manter Autonomia alta | A pergunta 3 do gerente sustenta metade da dimensão, e sozinha quando não há bloqueio |
| Gerente inflar as notas do próprio squad | Só a calibração entre gerentes segura. É defesa social, não técnica |

### 12.3 Onde o sistema ainda é frágil

**A calibração é a única defesa contra inflação de nota.** Em projeto padrão o
gerente responde por 35% do score, e em consultoria por 50%. Nada no sistema
detecta um gerente que dá 5 para todo mundo. Só outro gerente, olhando os mesmos
casos, consegue.

**Bloqueio ainda depende de alguém registrar.** Agora quem marca é o operacional,
que é quem sente o problema, e a pergunta 3 cobre as semanas sem registro. Mas um
time que nunca registra bloqueio deixa Autonomia inteiramente na mão da percepção
do gerente.

### 12.4 O que nunca entra na conta

- número de commits, de linhas, de PRs ou de arquivos
- número de tasks, porque só os pontos contam, e só como proporção
- tempo de ciclo e SPI da sprint, que são métricas de saúde do squad
- horas trabalhadas, presença ou tempo de resposta

---

## 13. Acesso, sigilo e o que divulgar

### 13.1 Quem vê o quê

| Recurso | Owner | Líder | Gerente | Operacional |
|---|---|---|---|---|
| Alterar o cargo das pessoas | ✅ | ❌ | ❌ | ❌ |
| Ver quem tem acesso ao sistema | ✅ | ✅ | ❌ | ❌ |
| Ranking e score final | ✅ | ✅ | ❌ | ❌ |
| Reabrir um fechamento de sprint | ✅ | ✅ | ❌ | ❌ |
| Entrega consolidada e evolução por pessoa | ✅ | ✅ | ✅ | ❌ |
| Preencher e ler o questionário | ✅ | ✅ | ✅ | ❌ |
| Métricas e painel do projeto | ✅ | ✅ | ✅ | ❌ |
| Esta metodologia | ✅ | ✅ | ✅ | ❌ |
| Guia do sistema e versão pública do acompanhamento | ✅ | ✅ | ✅ | ✅ |
| Kanban, tasks e sprints | ✅ | ✅ | ✅ | ✅ só nos projetos em que está |

**Owner** é o cargo acima de Líder. Alcança tudo o que o Líder alcança, e é o
único que promove ou rebaixa alguém, na tela de Pessoas. Um Owner não consegue
mudar o próprio cargo: para sair, precisa promover outra pessoa a Owner antes.
Toda troca de cargo fica registrada.

O gerente **não** enxerga o score final nem a posição de ninguém no ranking. Ele
produz o insumo, que são as sete notas, e enxerga a entrega consolidada e a
evolução de cada pessoa do projeto dele, que é o que sustenta a conversa de
feedback. O resultado do cálculo é do Líder.

**Onde o gerente vê isso:** aba **Métricas** do projeto, no bloco "Entrega e
evolução por pessoa". Ele mostra, para cada operacional, a entrega consolidada dos
fechamentos, a nota de evolução, quantas sprints já foram avaliadas e quantos
pontos a pessoa perdeu por atraso. É o mesmo dado que alimenta o ranking, sem
mostrar o ranking.

Qualquer conta de gerente acessa os dados de gestão de qualquer projeto, e não só
dos que ela gerencia. A única restrição por projeto é a do operacional, que só
alcança os projetos em que está vinculado.

### 13.2 Auditoria

Toda vez que alguém abre a tela de ranking, fica registrado quem abriu e quando.
Leitura de score deixa rastro.

### 13.3 O que divulgar e o que não divulgar

**Pode e deve ser dito ao time:**

- Que a contribuição é acompanhada em entrega, qualidade, autonomia, ajuda ao time
  e evolução.
- Que existe reconhecimento periódico para quem mais contribui no conjunto.
- Que **ajudar os outros conta a favor**, e não contra.
- Que nenhuma métrica isolada define a posição de ninguém.
- Que o objetivo é reconhecer e desenvolver.

Isso tudo está escrito no documento **"Como sua contribuição é acompanhada"**,
que qualquer pessoa logada consegue abrir na tela de Documentos. Ele é a versão
pública desta metodologia: traz as cinco direções, o que não conta, o que se
espera do operacional no dia a dia e como funciona o reconhecimento, sem nenhum
peso, fórmula ou nota. Aponte o time para lá em vez de explicar de boca, porque
explicação de boca é onde os pesos vazam.

**Nunca deve ser dito:**

- Os pesos e as fórmulas.
- A nota de ninguém, nem a posição no ranking.
- As notas cruas do questionário.
- Qual coisa contável pesa mais.
- Que os critérios nunca mudam, porque os pesos serão recalibrados com dado real.

**Na divulgação:** anuncie apenas o **destaque do período**, a cada duas semanas. O
restante da lista fica com a liderança. Escolha alguém cuja contribuição inclua
visivelmente ter ajudado o time, porque quem é premiado em público vira o modelo do
que é premiado. Se quem ganha é quem puxou os outros, o time lê que ajudar ganha.

O anúncio é feito pela liderança, fora do sistema.

---

## 14. Manual do gerente

### 14.1 Antes da primeira sprint

1. **Preencha o contrato do projeto:** tipo de projeto (Padrão ou Consultoria),
   datas e, se houver, o valor em reais. Lembre que o valor congela assim que a
   primeira sprint receber orçamento de pontos.
2. **Cadastre os operacionais com e-mail e usuário do GitHub.** Os dois são
   obrigatórios na prática, mesmo que o formulário aceite em branco. Sem e-mail a
   pessoa não é reconhecida entre projetos. Sem usuário do GitHub os commits dela
   não pontuam.
   Se a pessoa já está em outro projeto, use o atalho **"Já trabalha em outro
   projeto?"** e selecione o nome dela: o cadastro vem preenchido e o e-mail sai
   igual, que é o que mantém ela como uma pessoa só.
3. **Distribua os 100 pontos entre as sprints,** na aba Escopo. Pode ser aos
   poucos, sprint sem orçamento não trava nada.
4. **Configure os limites de tasks simultâneas** se o squad tende a começar muita
   coisa ao mesmo tempo.

### 14.2 Durante a semana

O trabalho é o Kanban normal. Quatro coisas exigem atenção:

1. **Pontue as tasks com honestidade.** Os pontos são o denominador de Entrega.
2. **Ao desmarcar um bloqueio, informe com honestidade quem resolveu.** Quem marca
   o bloqueio é o operacional; a resposta sobre quem destravou é sua.
3. **Mantenha o responsável da task correto.** Quem está com a task quando ela é
   concluída é quem recebe os pontos.
4. **Responda os pedidos de task extra.** Quando alguém zera a fila, você recebe
   um e-mail e o pedido aparece no topo do Kanban. Conceder ou dizer "nada agora"
   são as duas respostas válidas; deixar sem resposta é a única errada, porque a
   pessoa fica parada e perde Entrega por um motivo que não é dela.

E fique de olho na etiqueta amarela de atraso. Se o atraso não é culpa do
operacional, **dispense o alerta na task**, porque senão ele vai descontar pontos
de Entrega no fechamento.

Fora isso, não existe nada "de performance" para fazer durante a semana. Se o
Kanban reflete a realidade, o dado está sendo coletado.

### 14.3 O fechamento, na sexta

No card da sprint, botão **"Avaliação Semanal"**:

1. O sistema lista todos os operacionais **pendentes**, que são todos os que
   tiveram pelo menos uma task na sprint.
2. Clique num nome e responda as **sete perguntas**, de 0 a 5. Todas obrigatórias.
   Se a pessoa foi avaliada recentemente em outro projeto, aparece a opção de
   reaproveitar aquelas respostas. Use só se a leitura for de fato a mesma.
3. **Salve.** A pessoa sai da lista de pendentes.
4. Repita até a lista zerar.
5. Clique em **"Confirmar Avaliação Semanal"**.

**O passo 5 fecha a semana.** Antes de clicar, confira cinco coisas:

- Todas as tasks estão na coluna certa?
- Os bloqueios resolvidos foram desmarcados com o responsável correto?
- Os responsáveis das tasks estão como de fato foram?
- Algum alerta de atraso precisa ser dispensado?
- As tasks concedidas fora do planejado estão marcadas como extra?

Depois de confirmado, as tasks daquela sprint não podem mais ser excluídas, e
confirmar de novo não recalcula nada. Se você errou, o Líder consegue reabrir o
fechamento (seção 9.5), mas trate isso como conserto e não como rotina.

### 14.4 Prazo de correção

Você tem **48 horas a partir da criação** de cada avaliação para corrigir as notas.
Percebeu um erro de leitura no dia seguinte, ainda dá tempo. Na semana seguinte,
não.

### 14.5 Calibração entre gerentes

Não é negociável, porque o gerente pesa 35% em projeto padrão e 50% em
consultoria.

**Uma vez por ciclo**, os gerentes se reúnem, olham casos reais de operacionais e
combinam o que é um 3 e o que é um 5. Cada gerente justifica a própria nota para os
outros.

Sem calibração, peso alto no gerente faz o ranking medir **de qual gerente a pessoa
é**, e não como ela performou. A calibração tira a pressão de inflar nota, alinha
padrões diferentes e reduz viés. É a peça que torna os 35% justos em vez de ruído.

O sistema não força nem acompanha a calibração. É rotina humana, e é a única defesa
contra o último item da tabela da seção 12.

### 14.6 O que o gerente não faz

- Não vê score final nem ranking, isso é do Líder.
- Não ajusta pesos.
- Não reabre fechamento, isso é do Líder.
- Não marca bloqueio pelo operacional. Ele registra, você responde quem resolveu.
- Não comunica posição no ranking a operacional. A comunicação de reconhecimento
  segue a seção 13 e é feita pela liderança.

---

## 15. Casos de borda e regras finas

### 15.1 Trocar o responsável de uma task no meio da semana

Não exige nada além de trocar no sistema. Os pontos de uma task concluída ficam com
quem estava com ela na conclusão. Tasks não concluídas contam como "pegou" para o
responsável atual.

### 15.2 Pessoa em dois ou mais projetos

Cada projeto gera seu próprio registro por sprint. A janela junta as sprints mais
recentes independentemente do projeto, e cada dimensão vira a média simples entre
os projetos. Ver seção 10.1.

### 15.3 Pessoa cadastrada sem e-mail

Vira duas pessoas diferentes no ranking, uma por projeto, cada uma com metade do
histórico. Não aparece nenhum aviso. É o erro de cadastro mais caro do sistema.

### 15.4 Pessoa que sai do projeto no meio da execução

Este é o caso importante, e ele tem dois caminhos que não se confundem.

**"Remover do projeto"** tira a pessoa do Kanban e das avaliações, mas **preserva
todo o histórico de pontuação dela**. As sprints que ela já fechou continuam
contando no acompanhamento, e ela continua no ranking com o que construiu. As
tasks que ainda estavam com ela ficam sem responsável, para o gerente
redistribuir. É o caminho certo quando alguém troca de projeto.

**Excluir**, no botão vermelho, apaga a pessoa e **toda a pontuação dela**. É
irreversível e quase sempre a escolha errada: use só quando o cadastro foi um erro
desde o começo, como duplicata ou nome de teste.

Se a pessoa vai continuar no CITi em outro projeto, o certo é remover daqui e
adicionar lá pelo atalho "Já trabalha em outro projeto?", com o **mesmo e-mail**.
Assim o histórico dos dois projetos continua sendo da mesma pessoa.

### 15.5 Operacional desativado

Sai do ranking imediatamente. O histórico dele continua guardado, mas não é lido.

### 15.6 Sprint sem nenhuma task

O fechamento não cria registro para ninguém, e aquela sprint não entra na janela de
ninguém.

### 15.7 Fechamento feito com dado errado

O Líder reabre pelo botão no card da sprint. Ver seção 9.5.

### 15.8 Excluir task depois do fechamento

Bloqueado enquanto a sprint estiver fechada. A pontuação já foi travada e aquela
task faz parte da conta. Se for mesmo necessário, o Líder reabre o fechamento
primeiro.

### 15.9 Projeto de consultoria

Sem nota de commit, Qualidade vira só o retrabalho, e o peso dela cai de 20% para
10% justamente por isso. Projeto de consultoria com pouca movimentação de Kanban
tende a ter Qualidade indisponível para várias pessoas, e nesse caso o score delas
é redistribuído entre as outras dimensões (seção 11.3), com a leitura do gerente
pesando ainda mais do que os 50% nominais.

## 16. Erros que o sistema devolve e o que fazer

| Mensagem | Quando aparece | O que fazer |
|---|---|---|
| "Ainda há avaliações pendentes" | Confirmar a Avaliação Semanal com gente por avaliar | Avaliar os nomes listados e confirmar de novo |
| "Janela de edição de 48h já encerrada" | Editar avaliação antiga | Não há correção pela tela. Se for grave, o Líder reabre o fechamento |
| "Orçamento da sprint excedido" | Task com pontos além do que a sprint recebeu | Usar o botão "Redistribuir pontos", reduzir os pontos, mover a task para outra sprint, ou marcá-la como extra se for trabalho concedido além do planejado |
| "Não dá para abrir N pontos" | Redistribuir numa sprint onde as tasks já estão no mínimo | A mensagem diz qual é o máximo liberável. Aumentar o orçamento da sprint ou mover alguma task |
| "Restam só N pontos para distribuir entre as sprints" | Orçamento de sprint estourando os 100 do projeto | Reduzir o orçamento de outra sprint primeiro |
| "Associe a task a uma sprint antes de movê-la" | Mover para Em Andamento uma task sem sprint | Escolher a sprint e mover de novo |
| "Itens do checklist ainda não concluídos" | Concluir task com checklist aberto | Marcar os itens ou tirá-los do checklist |
| "Limite atingido" ao mover para Em Andamento | Estourou o limite de tasks simultâneas | Concluir ou devolver outra task antes |
| "Informe quem resolveu o bloqueio" | Desmarcar bloqueio sem escolher o responsável | Escolher Operacional ou Gerente, com honestidade, porque isso alimenta a Autonomia |
| "Você ainda tem N tasks em aberto" | Pedir nova task com trabalho pendente | Concluir o que está em aberto primeiro. O botão só existe para quem zerou a fila |
| "A pontuação desta sprint já foi travada" | Excluir task de sprint fechada | Pedir ao Líder para reabrir o fechamento, ou deixar como está |
| "Esta sprint não está fechada" | Reabrir uma sprint que nunca foi confirmada | Nada a fazer, ela já está aberta |
| "Acesso restrito" | Gerente tentando abrir o ranking | Comportamento correto, o score final é do Líder |
