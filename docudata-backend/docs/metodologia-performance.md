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
| Ranking e score final | Só o Líder |
| Entrega consolidada e evolução de cada operacional | Líder e Gerente |
| Notas cruas do questionário e métricas do projeto | Líder e Gerente |
| Esta metodologia | Líder e Gerente |
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

### 5.1 Entrega e Confiabilidade, peso 20%

**O que mede:** cumpriu o que se comprometeu, dentro do que pegou.

> **Entrega** = (pontos entregues menos pontos perdidos por atraso) ÷ pontos que a
> pessoa pegou, em porcentagem, com teto de 100.

- Somam-se todas as sprints da janela dentro do mesmo projeto.
- **Teto de 100.** Entregar além do que pegou não pontua acima do máximo. Isso
  existe para que puxar task extra no fim da semana não vire alavanca de score.
- **Pontos perdidos por atraso:** quando uma task fica parada muito além do tempo
  esperado para o tamanho dela, o sistema marca um alerta de atraso. Os pontos
  dessa task deixam de contar como entrega. O gerente pode dispensar o alerta na
  própria task, e aí a penalidade não acontece (seção 8.6).
- Se a pessoa não pegou nenhum ponto na janela, a dimensão fica **indisponível**,
  e não vira zero.

**Por que é proporção e não soma bruta:** volume absoluto de pontos mede quem
recebeu as tasks maiores, ou seja, mede a decisão de alocação do gerente e não a
performance da pessoa. Medir o que ela entregou sobre o que ela pegou faz com que
quem cumpriu tudo pontue alto mesmo tendo pego menos.

### 5.2 Avaliação do Gerente, peso 35%

**O que mede:** a leitura estruturada do gerente sobre o operacional, incluindo o
sinal de colaboração.

> **Avaliação do Gerente** = média das seis perguntas do questionário, convertida
> da escala 0 a 5 para 0 a 100.

A pergunta de evolução fica **fora** desta média de propósito: ela é a fonte
exclusiva da dimensão Evolução, e contá-la duas vezes daria peso desproporcional a
uma única pergunta.

Se nenhuma sprint da janela tem avaliação, a dimensão fica indisponível.

**Por que 35% e não mais:** acima disso o ranking vira ranking de opinião de
gerente vestido de dado. Mesmo com 35%, metade do peso continua em dimensões
objetivas, que são as difíceis de gamear. E os 35% só são justos se a calibração
da seção 14 acontecer de fato.

### 5.3 Qualidade Técnica, peso 20%

**O que mede:** o trabalho precisou de pouca correção e seguiu o padrão.

A dimensão combina dois sinais.

> **Retrabalho** = 1 menos (tasks reabertas ÷ tasks concluídas), em porcentagem.
> Sem nenhuma task concluída, o retrabalho é considerado 100.
>
> **Nota de commit** = média das notas de 0 a 10 que a IA deu aos commits do
> período, convertida para 0 a 100.
>
> **Qualidade** = metade da nota de commit mais metade do retrabalho. Sem nota de
> commit no período, Qualidade é o retrabalho puro.

A divisão meio a meio é configurável pela liderança e começa em 50/50. O valor
definitivo é decisão do Líder depois do piloto.

**Reabertura** tem definição estrita: é uma task que estava em Concluída e voltou
para Em Andamento. Voltar de Concluída para Planejado não conta como reabertura.

Não ter concluído nada resulta em qualidade 100, e isso é uma assimetria
consciente: quem não entregou já é penalizado em Entrega, não precisa ser
penalizado duas vezes.

### 5.4 Autonomia, peso 15%

**O que mede:** quanto a pessoa destrava sozinha antes de escalar.

> **Autonomia** = bloqueios que a própria pessoa resolveu ÷ bloqueios que ela teve,
> em porcentagem. Sem nenhum bloqueio registrado, a autonomia é 100.

A contagem vem exclusivamente do bloqueio marcado à mão no Kanban, e o numerador
só cresce quando, ao desmarcar, o gerente informa que quem resolveu foi o
operacional.

Task parada tempo demais **não** entra aqui. Atraso penaliza Entrega, não
Autonomia, porque são coisas diferentes: uma é sobre demora, a outra é sobre
depender dos outros.

Zero bloqueio dando autonomia máxima é a escolha correta de incentivo, porque não
penaliza quem simplesmente não travou. Mas cria um efeito colateral que o gerente
precisa conhecer: registrar bloqueios reduz o teto de Autonomia de quem registrou,
a não ser que ele mesmo resolva. Ver seção 12.

### 5.5 Evolução, peso 10%

**O que mede:** quanto a pessoa cresceu em relação a onde estava.

> **Evolução** = a pergunta de evolução do questionário, convertida da escala 0 a 5
> para 0 a 100.

É a única dimensão que compara a pessoa com ela mesma, e não com um padrão
absoluto. É o que dá chance real a quem entrou mais júnior.

---

## 6. Pesos e tipos de projeto

### 6.1 Os cinco pesos

| Dimensão | Peso |
|---|---|
| Avaliação do Gerente | **35%** |
| Entrega e Confiabilidade | **20%** |
| Qualidade Técnica | **20%** |
| Autonomia | **15%** |
| Evolução | **10%** |

Somam 100%. São configuráveis pela liderança, e mudar um peso muda o ranking na
leitura seguinte, sem precisar reprocessar nada. Isso é de propósito: recalibrar
depois do piloto tem que ser barato.

### 6.2 Os dois tipos de projeto

Cada projeto é classificado como:

- **Padrão**, projeto com entrega de código. A avaliação de qualidade de commit
  fica ativa.
- **Consultoria ou discovery**, projeto sem entrega de código. A avaliação de
  commit fica desligada.

### 6.3 Os pesos são iguais nos dois tipos

Decisão do Líder, fechada em definitivo: os cinco pesos são idênticos nos dois
tipos de projeto. Nenhum dado objetivo diferenciava os dois o suficiente para
justificar pesos distintos, e pesos diferentes tornariam o ranking entre projetos
incomparável.

O que muda entre os tipos não é o peso, é a **presença de um sinal** dentro de
Qualidade: em consultoria não existe nota de commit, então Qualidade fica sendo só
o retrabalho. Mesma régua, uma fonte a menos.

### 6.4 Quando a janela mistura projetos

Uma janela pode cobrir mais de um projeto. O tipo aplicado é o do projeto com mais
sprints dentro daquela janela; em empate, vale o projeto da sprint mais recente.

---

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

As perguntas **1, 2, 3, 4, 5 e 7** formam a dimensão Avaliação do Gerente. Cada
uma vale um sexto dos 35%, ou seja, cerca de **5,8% do score final**.

A pergunta **6** é a dimensão Evolução inteira, e vale **10% do score final**.
Ela não entra na média das outras.

Ou seja: a pergunta 5, sobre colaboração, vale por volta de 5,8% do score. É um
sinal real, mas não é uma dimensão própria. Se o acompanhamento mostrar queda de
colaboração, o caminho de correção é aumentar o peso da avaliação do gerente ou
promover a colaboração a dimensão separada.

### 7.2 Como responder bem

- **Ancore na sprint, não na pessoa.** A pergunta é sobre o que aconteceu nesta
  semana, não sobre quem a pessoa é.
- **Use a escala inteira.** Um gerente que só dá 4 e 5 destrói a comparação para
  todos os operacionais dele. A calibração da seção 14 existe justamente para isso.
- **3 é "fez o combinado".** 5 é excepcional, e não "não tenho reclamação".

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
pode ter cinco tasks de 2, ou duas de 3 mais uma de 4. O que não pode é a soma das
tasks passar do que a sprint recebeu.

Na prática:

- **Se a sprint tem orçamento definido**, o sistema recusa uma task nova que faria
  a soma estourar, e diz quantos pontos ainda sobram.
- **Se a sprint não tem orçamento definido**, não há validação nenhuma. Você pode
  trabalhar normalmente e planejar depois.
- **Se você move uma task de uma sprint para outra**, a validação é refeita contra
  a sprint de destino, que é quem vai pagar por aqueles pontos.
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

**Uma task só vai para Concluída com o checklist completo.** Se você criou um
checklist na task e sobrou item aberto, o sistema não deixa concluir. Isso evita a
"concluída" nominal, aquela que volta como reabertura três dias depois e derruba a
nota de Qualidade da pessoa sem necessidade.

**Existe um limite de tasks simultâneas em Em Andamento.** Você configura dois
limites opcionais no projeto: quantas tasks o projeto inteiro pode ter em
andamento, e quantas cada pessoa pode ter. Ao estourar, o sistema recusa e diz qual
limite foi atingido. É o freio contra o squad começar dez coisas e terminar duas.

**Todo movimento fica registrado com quem estava na task naquele momento.** Essa é
a parte invisível e a mais importante: se a Ana pega uma task, conclui, e depois a
task é passada para o João por algum motivo, os pontos daquela entrega continuam
sendo da Ana. O sistema guarda quem estava com a task no instante em que ela foi
concluída, e é isso que ele lê no fechamento.

### 8.5 Como sinalizar bloqueio de task na tela

Bloqueio é o único dado de Autonomia, então vale detalhar o passo a passo.

**Para marcar um bloqueio:**

1. Vá na aba **Kanban** do projeto e clique na task.
2. Marque a caixa **"Bloqueada"**.
3. Aparecem dois campos: **"Motivo do bloqueio"**, texto livre, e **"Quem
   bloqueou?"**, onde vai o nome de quem identificou.
4. Salve.

A task passa a mostrar uma **borda vermelha** e uma etiqueta vermelha
**"Bloqueada"** no card, então dá para ver o que está travado só de bater o olho
no quadro.

**Para resolver o bloqueio:**

1. Abra a task e **desmarque** a caixa "Bloqueada".
2. Aparece o campo obrigatório **"Quem resolveu?"**, com duas opções:
   **Operacional** ou **Gerente**.
3. Salve. Sem escolher uma das duas, o sistema recusa.

Essa escolha é o dado inteiro da dimensão Autonomia:

- **Operacional** significa que a pessoa destravou sozinha. Conta a favor dela.
- **Gerente** significa que você teve que entrar para destravar. Conta como
  bloqueio ocorrido, sem crédito de autonomia.

Responda com honestidade. Marcar sempre "Operacional" para não prejudicar ninguém
transforma a dimensão em ruído e tira do time a única leitura objetiva sobre
dependência.

### 8.6 Task parada tempo demais

Todo dia o sistema varre as tasks em Em Andamento. Se uma delas está parada há
mais dias do que o dobro dos pontos que ela vale, ou seja, uma task de 3 pontos
parada há 6 dias ou mais, ela ganha uma etiqueta amarela **"⏱ Travada"** no card e
um aviso dentro da task.

**Isso agora tira ponto.** Os pontos daquela task deixam de contar como entrega no
fechamento da semana. A lógica é direta: a pessoa até entregou, mas muito depois do
esperado, então aquela entrega não conta cheia.

O aviso dentro da task traz um campo para o **gerente dispensar o alerta**,
informando o próprio nome. Dispensar tira a etiqueta e **cancela a penalidade**. É
a válvula de escape para quando o atraso não é responsabilidade do operacional,
como dependência de cliente, espera por acesso ou mudança de prioridade.

Ou seja: o alerta é automático, mas a penalidade é revisável pelo gerente. Se você
não dispensar, o sistema entende que o atraso conta.

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
| Pontos que a pessoa pegou | Soma das tasks dela na sprint, concluídas ou não |
| Pontos que a pessoa entregou | Soma das tasks concluídas por ela |
| Pontos perdidos por atraso | Tasks que ficaram paradas tempo demais e não foram dispensadas |
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

### 9.5 Confirmar duas vezes não faz nada, e não dá para desfazer

Se a sprint já foi fechada, clicar em confirmar de novo **não recalcula e não
duplica nada**. O sistema devolve o que já estava guardado. Isso protege contra
clique duplo, aba aberta duas vezes ou colega confirmando junto.

O outro lado dessa proteção é que **não existe botão de refazer o fechamento**. Se
você fechou a semana com o Kanban desatualizado, a foto errada é a que ficou. As
opções são:

1. **Deixar quieto.** Uma semana torta dilui nas janelas de 2 e 4 sprints.
2. **Pedir para a liderança apagar o fechamento** direto na base e refazer. Dá
   trabalho, mexe no marco de tempo da seção 9.4 e pode fazer eventos serem
   recontados. Só vale a pena para erro grande.

A prevenção é o checklist da seção 14 antes de confirmar.

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
5. **Aplica os pesos.** Multiplica cada dimensão pelo peso dela e soma. O
   resultado é o score final, de 0 a 100.
6. **Ordena.** As pessoas são listadas da maior nota para a menor, dentro de cada
   janela.

A média entre projetos é simples, e não ponderada por volume: um projeto pequeno
pesa igual a um grande. Isso protege quem foi alocado parcialmente em algo pequeno
de ver aquele projeto diluído a zero, mas também significa que uma semana ruim num
projeto pequeno machuca tanto quanto num grande.

### 11.2 Um exemplo do começo ao fim

A Maria, na janela de duas sprints, nos dois casos no mesmo projeto de tipo Padrão.

| O que aconteceu | Sprint 12 | Sprint 13 |
|---|---|---|
| Pontos que ela pegou | 14 | 10 |
| Pontos que ela entregou | 12 | 10 |
| Pontos perdidos por atraso | 0 | 2 |
| Média das seis perguntas do gerente | 4,17 | 4,50 |
| Nota de evolução | 4 | 5 |
| Tasks concluídas | 6 | 4 |
| Tasks reabertas | 1 | 0 |
| Bloqueios que teve | 3 | 1 |
| Bloqueios que resolveu sozinha | 2 | 1 |
| Nota média dos commits | 7,5 | 8,5 |

**As cinco dimensões:**

| Dimensão | Conta | Resultado |
|---|---|---|
| Entrega | (12 + 10 menos 2) sobre (14 + 10) | **83,33** |
| Avaliação do Gerente | média de 4,17 e 4,50, vezes 20 | **86,70** |
| Qualidade | retrabalho 90,00 e commits 80,00, meio a meio | **85,00** |
| Autonomia | 3 resolvidos sobre 4 bloqueios | **75,00** |
| Evolução | média de 4 e 5, vezes 20 | **90,00** |

O retrabalho saiu de 1 task reaberta em 10 concluídas, que dá 90. A nota de
commits foi a média de 7,5 e 8,5, que dá 8,0, convertida para 80.

**O score final:**

| Dimensão | Nota | Peso | Contribuição |
|---|---|---|---|
| Avaliação do Gerente | 86,70 | 35% | 30,35 |
| Entrega | 83,33 | 20% | 16,67 |
| Qualidade | 85,00 | 20% | 17,00 |
| Autonomia | 75,00 | 15% | 11,25 |
| Evolução | 90,00 | 10% | 9,00 |
| | | | **84,26** |

Repare no efeito do atraso: sem os 2 pontos penalizados na sprint 13, a Entrega
teria sido 91,67 e o score final subiria para 85,93. Uma task travada custou 1,67
ponto de score.

### 11.3 O que acontece quando falta uma dimensão

Se uma dimensão não pode ser calculada, ela **não vira zero**. Ela sai da conta, e
o resultado é dividido pela soma dos pesos que sobraram.

Voltando à Maria: se ela não tivesse sido avaliada pelo gerente em nenhuma das duas
sprints, sumiriam a Avaliação do Gerente e a Evolução. Sobrariam Entrega,
Qualidade e Autonomia, que somam 55% de peso. A conta seria 16,67 mais 17,00 mais
11,25, dividido por 0,55, dando **81,67**.

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
| Pegar poucas tasks para garantir 100% de Entrega | Entrega tem teto 100, então não há ganho. E a leitura do gerente, que vale 35%, enxerga volume baixo |
| Pegar muitas tasks e entregar metade | O que pegou cresce, o que entregou não. Entrega despenca |
| Segurar task por semanas para entregar "perfeita" | O alerta de atraso tira os pontos dela da Entrega |
| Commit trivial em volume | A nota é por commit e entra como média, não como soma. Commit trivial puxa a média para baixo |
| Inflar linha de código com IA | Não existe contagem de linha em lugar nenhum, e a nota de commit avalia complexidade e aderência, não tamanho |
| Marcar task como concluída sem estar | O checklist bloqueia a conclusão, e a reabertura depois derruba a Qualidade |
| Nunca registrar bloqueio para manter Autonomia em 100 | Segurada só em parte, ver abaixo |
| Gerente inflar as notas do próprio squad | Só a calibração entre gerentes segura. É defesa social, não técnica |

### 12.3 O buraco conhecido: não registrar bloqueio

Autonomia é 100 quando não há bloqueio nenhum. Não registrar bloqueio garante nota
máxima em 15% do score, e nada no sistema impede isso.

As defesas hoje são indiretas. A pergunta 3 do questionário captura a percepção
real do gerente sobre dependência, e vale por volta de 5,8%. E bloqueio não
registrado costuma virar task parada, que agora dispara o alerta de atraso e
penaliza Entrega.

Ainda assim é o vetor de gaming mais aberto do sistema.

### 12.4 O que nunca entra na conta

- número de commits, de linhas, de PRs ou de arquivos
- número de tasks, porque só os pontos contam, e só como proporção
- tempo de ciclo e SPI da sprint, que são métricas de saúde do squad
- horas trabalhadas, presença ou tempo de resposta

---

## 13. Acesso, sigilo e o que divulgar

### 13.1 Quem vê o quê

| Recurso | Líder | Gerente | Operacional |
|---|---|---|---|
| Ranking e score final | ✅ | ❌ | ❌ |
| Entrega consolidada e evolução por pessoa | ✅ | ✅ | ❌ |
| Preencher e ler o questionário | ✅ | ✅ | ❌ |
| Métricas e painel do projeto | ✅ | ✅ | ❌ |
| Esta metodologia | ✅ | ✅ | ❌ |
| Kanban, tasks e sprints | ✅ | ✅ | ✅ só nos projetos em que está |

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

O trabalho é o Kanban normal. Três coisas exigem disciplina:

1. **Pontue as tasks com honestidade.** Os pontos são o denominador de Entrega.
2. **Registre bloqueio quando houver bloqueio,** e ao resolver informe com
   honestidade quem resolveu. Esse único campo carrega 15% do score.
3. **Mantenha o responsável da task correto.** Quem está com a task quando ela é
   concluída é quem recebe os pontos.

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

**O passo 5 não tem volta.** Antes de clicar, confira quatro coisas:

- Todas as tasks estão na coluna certa?
- Os bloqueios resolvidos foram desmarcados com o responsável correto?
- Os responsáveis das tasks estão como de fato foram?
- Algum alerta de atraso precisa ser dispensado?

Depois de confirmado, as tasks daquela sprint não podem mais ser excluídas, e
confirmar de novo não recalcula nada.

### 14.4 Prazo de correção

Você tem **48 horas a partir da criação** de cada avaliação para corrigir as notas.
Percebeu um erro de leitura no dia seguinte, ainda dá tempo. Na semana seguinte,
não.

### 14.5 Calibração entre gerentes

Não é negociável, porque o gerente pesa 35%.

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
- Não reabre fechamento.
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

### 15.4 Operacional desativado

Sai do ranking imediatamente. O histórico dele continua guardado, mas não é lido.

### 15.5 Sprint sem nenhuma task

O fechamento não cria registro para ninguém, e aquela sprint não entra na janela de
ninguém.

### 15.6 Fechamento feito com dado errado

Não há caminho pela tela. Ver seção 9.5.

### 15.7 Excluir task depois do fechamento

Bloqueado. A pontuação da semana já foi travada e aquela task faz parte da conta.

### 15.8 Projeto de consultoria

Sem nota de commit, Qualidade vira só o retrabalho. Como retrabalho é 100 quando
não há tasks concluídas, projeto de consultoria com pouca movimentação de Kanban
tende a mostrar Qualidade artificialmente alta. Leia com desconto.

---

## 16. Erros que o sistema devolve e o que fazer

| Mensagem | Quando aparece | O que fazer |
|---|---|---|
| "Ainda há avaliações pendentes" | Confirmar a Avaliação Semanal com gente por avaliar | Avaliar os nomes listados e confirmar de novo |
| "Janela de edição de 48h já encerrada" | Editar avaliação antiga | Não há correção. Registre o desvio para a leitura do Líder |
| "Orçamento da sprint excedido" | Task com pontos além do que a sprint recebeu | Reduzir os pontos, mover a task para outra sprint, ou aumentar o orçamento da sprint se ainda houver saldo nos 100 |
| "Restam só N pontos para distribuir entre as sprints" | Orçamento de sprint estourando os 100 do projeto | Reduzir o orçamento de outra sprint primeiro |
| "Associe a task a uma sprint antes de movê-la" | Mover para Em Andamento uma task sem sprint | Escolher a sprint e mover de novo |
| "Itens do checklist ainda não concluídos" | Concluir task com checklist aberto | Marcar os itens ou tirá-los do checklist |
| "Limite atingido" ao mover para Em Andamento | Estourou o limite de tasks simultâneas | Concluir ou devolver outra task antes |
| "Informe quem resolveu o bloqueio" | Desmarcar bloqueio sem escolher o responsável | Escolher Operacional ou Gerente, com honestidade, porque isso é a Autonomia |
| "A pontuação desta sprint já foi travada" | Excluir task de sprint fechada | Não é possível, a task faz parte da conta já travada |
| "Acesso restrito" | Gerente tentando abrir o ranking | Comportamento correto, o score final é do Líder |
