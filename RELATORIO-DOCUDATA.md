# DocuData — Relatório de Funcionalidades

Subárea de Dados · CITi

Este documento descreve tudo o que o DocuData faz e como cada funcionalidade
funciona, do ponto de vista de quem usa. Estado do sistema em 12/09/2026.

---

## 1. O que o DocuData é

O DocuData nasceu de um problema: documentar projeto de dados custa caro e quase
ninguém faz. O conhecimento — decisões técnicas, contexto de cliente, o porquê das
escolhas — fica na cabeça das pessoas e some quando o projeto acaba ou a gestão troca.

A solução foi inverter o fluxo. Em vez de pedir que alguém pare para escrever
documentação, o sistema lê o que o time já produz naturalmente — o kanban, as atas, os
prints, os PDFs, os commits — e monta os documentos sozinho.

Ao longo do desenvolvimento, essa mesma base de informação passou a alimentar mais duas
coisas. Hoje o DocuData faz três trabalhos ao mesmo tempo:

1. **Documenta** o projeto sprint a sprint, sem ninguém escrever do zero.
2. **Acompanha a saúde do projeto** — prazo contra escopo, ritmo de entrega, gargalos.
3. **Acompanha a contribuição de cada pessoa** — para reconhecimento periódico.

A consequência prática de tudo sair da mesma fonte: **quanto mais fiel o Kanban, melhor
a documentação, mais confiável a saúde do projeto e mais justo o acompanhamento das
pessoas**. Não existe um passo separado de "documentar" — existe manter o trabalho
registrado.

---

## 2. Quem usa e o que cada um enxerga

O sistema tem quatro cargos, em ordem de alcance:

**Owner** — enxerga tudo, e é o único que consegue promover ou rebaixar o cargo de
outras pessoas.

**Líder** — enxerga tudo em todos os projetos, incluindo a área de Performance com o
ranking de contribuição. É o único que consegue reabrir um fechamento de sprint que já
foi confirmado.

**Gerente** — enxerga todos os projetos e opera todas as abas, mas não acessa o ranking
de performance.

**Operacional** — enxerga apenas os projetos em que foi cadastrado, e dentro deles
apenas quatro abas: Sprints, Tasks, Tecnologias e Documentos. Não vê Painel, Métricas,
Planejamento nem Configurações.

### Como alguém entra no sistema

Há dois caminhos de cadastro:

- **Reivindicar um convite** — quando um gerente já cadastrou a pessoa como operacional
  de um projeto, ela aparece numa lista de "contas pendentes" e pode reivindicar a sua
  criando senha. O sistema casa pelo e-mail.
- **Cadastro novo** — a pessoa se cadastra do zero e depois é adicionada aos projetos.

Nos dois casos o sistema pede o **usuário do GitHub** e o **e-mail do GitHub**. O e-mail
do GitHub é pedido separado do e-mail de login porque o que casa um commit com uma
pessoa é o e-mail que o Git usa na máquina dela, que nem sempre é o e-mail do CITi. Sem
isso, os commits da pessoa não são reconhecidos como dela.

---

## 3. O ciclo de vida de um projeto

Antes de detalhar cada funcionalidade, vale ver como elas se encaixam:

1. O gerente **cria o projeto** e preenche cliente, datas de contrato e configurações.
2. Cadastra as **pessoas** que vão trabalhar nele.
3. Sobe o **PDF da proposta** e a IA extrai as funcionalidades contratadas.
4. Distribui os **100 pontos do projeto** entre as sprints previstas.
5. A cada semana, **inicia uma sprint**, registra o **Planning**, e o time trabalha
   movendo **tasks no Kanban**.
6. Ao longo da semana registra **dailys**; ao final registra a **Review**.
7. Responde a **Avaliação Semanal** das pessoas e **confirma o fechamento** — o que
   trava a pontuação daquela sprint.
8. Gera os **documentos** que precisar, a qualquer momento.
9. Ao fim do projeto, gera a **Documentação Final** como entregável.

---

## 4. Criar e configurar um projeto

A tela inicial lista os projetos que a pessoa alcança, em cards com nome e cliente.
Daí se cria um projeto novo informando nome, cliente e descrição.

Dentro do projeto, a aba **Configurações** reúne tudo o que muda o comportamento do
sistema para aquele projeto:

**Datas de contrato** — data de início e data de fim contratada. É delas que sai o
cálculo de "quanto do prazo já foi consumido" no Painel. Sem elas, o Painel não tem o
que mostrar no bloco principal.

**Tolerância de desvio** — quantos pontos percentuais de diferença entre prazo
consumido e escopo entregue são aceitáveis antes de o sistema acusar atraso. O padrão
é 20.

**Período de garantia** — quantos dias de garantia após a entrega.

**Limites de trabalho simultâneo (WIP)** — dois números independentes: quantas tasks o
projeto inteiro pode ter em andamento ao mesmo tempo, e quantas cada pessoa pode ter.
É o freio contra começar dez coisas e terminar duas. Quem tenta mover uma task para "Em
andamento" acima do limite é barrado com a mensagem de qual limite estourou.

**Arquétipo do projeto** — duas opções: *padrão* (projeto com código) ou
*consultoria/discovery*. A escolha muda o peso das dimensões no acompanhamento de
contribuição, porque num projeto sem código não existe sinal de commit e a leitura do
gerente precisa pesar mais.

**E-mail do gerente** — para onde vão os avisos automáticos do projeto.

**Chave de IA própria** — o projeto pode usar uma chave de IA própria em vez da chave
geral do sistema.

**Integração com GitHub** — repositório e token, para o sistema receber commits.

**Marcar como entregue** e **excluir projeto**.

### Cadastro de pessoas no projeto

O gerente adiciona operacionais ao projeto informando nome, e-mail, papel e usuário do
GitHub. Se a pessoa já tem conta no sistema, os dados de GitHub são preenchidos
sozinhos a partir do cadastro dela.

Uma pessoa tem um cadastro de operacional **por projeto**. O sistema reconhece que são
a mesma pessoa através do e-mail — por isso um cadastro sem e-mail preenchido aparece
como uma pessoa separada no acompanhamento de contribuição.

Também dá para **remover alguém do projeto** sem apagar o histórico dela.

---

## 5. Planejamento — o escopo contratado

A aba **Planejamento** é onde vive o que foi vendido ao cliente.

### Funcionalidades

Funcionalidades são as entregas de alto nível para o cliente — "Tela de Login",
"Relatório mensal", "Pipeline de ingestão". São diferentes das tasks, que são o
trabalho técnico por trás de cada uma.

Cada funcionalidade tem:

- **Título e descrição**
- **Critérios de aceite** — a lista do que precisa estar verdadeiro para ela ser
  considerada pronta
- **Prioridade MoSCoW** — *Must* é obrigatório para a entrega, *Should* é importante
  mas não bloqueia, *Could* é desejável se sobrar tempo, *Won't* está fora desta versão.
  Serve para alinhar expectativa com o cliente antes de faltar tempo.
- **Status** — Não iniciada, Em andamento, Concluída. É o que alimenta o "escopo
  concluído" no Painel.
- **Responsável** e **sprint alvo**

Toda mudança de status fica registrada com data e hora, e é desse histórico que saem os
números de tempo por fase e eficiência de fluxo no Painel.

### Importar do contrato

Em vez de cadastrar funcionalidade por funcionalidade, o gerente sobe o **PDF da
proposta comercial** e a IA lê o documento e propõe a lista de funcionalidades com
título, descrição e critérios de aceite. O gerente revisa a lista proposta, ajusta o
que quiser, e só então confirma — nada entra no sistema sem passar pela revisão dele.

### Os 100 pontos do projeto

Todo projeto vale **100 pontos, fixo**, independente de tamanho. O que muda é como
esses 100 pontos se distribuem entre as sprints.

O gerente abre o distribuidor e diz quanto cada sprint recebe. Duas regras protegem a
conta:

- A soma de todas as sprints não pode passar de 100.
- Uma sprint não pode receber menos pontos do que as tasks já criadas nela somam.

Sprint sem orçamento definido não trava nada — ela simplesmente não aparece nos
indicadores que dependem de orçamento (como o SPI).

### Valor do projeto

Se o gerente informar o valor do contrato em reais, cada ponto passa a valer um
centésimo desse valor, e o faturamento previsto de cada sprint é calculado sozinho a
partir do orçamento de pontos dela. O valor congela assim que a primeira sprint recebe
orçamento, para não reescrever retroativamente o faturamento já registrado.

### Sprints planejadas

Também é daqui que se criam sprints **com antecedência**, só para reservar orçamento de
pontos. Uma sprint criada assim fica "planejada": ela existe, tem orçamento, pode
receber tasks, mas **não aparece na aba Sprints** com Planning, Daily, Review e
Avaliação até alguém efetivamente iniciá-la. Isso evita que a aba de execução fique
poluída com semanas que ainda não começaram.

---

## 6. Tasks e Kanban

É o coração do sistema. Quase tudo que o DocuData produz sai daqui.

### As três colunas

**Planejado → Em andamento → Concluída.** Move-se arrastando o card ou editando a task.

### Criar uma task

Obrigatório: **título** e **pontos**. Opcionais: sprint, pessoa responsável,
funcionalidade a que pertence, descrição e checklist.

Os pontos são a unidade de esforço do sistema inteiro — é o que o orçamento da sprint
distribui, o que o SPI mede e o que a dimensão Entrega usa.

### Checklist como critério de pronto

A task pode ter uma lista de itens que precisam estar prontos para ela poder ser
concluída. O card mostra o progresso ("3/5"), e **a task com checklist não vai para
Concluída enquanto todos os itens não estiverem marcados**. Task sem checklist não
trava nada.

### Sprint obrigatória para iniciar

Uma task só entra em "Em andamento" se estiver ligada a uma sprint. Sem isso não haveria
como saber a que semana aquele trabalho pertence, e o cálculo de entrega ficaria sem
denominador.

### Limites de trabalho simultâneo

Os dois limites configurados no projeto (por pessoa e pela coluna inteira) são checados
no momento de mover para "Em andamento". Se o limite já foi atingido, o sistema barra e
diz qual foi.

### Bloqueio

Quando alguém trava, marca a caixa **"Bloqueada"** na própria task e escreve o motivo.
O card ganha borda vermelha e fica visível no quadro para todo mundo.

Ao destravar, o sistema pergunta **quem resolveu**: a própria pessoa ou o gerente. Essa
resposta não é burocracia — é o que alimenta a dimensão Autonomia do acompanhamento de
contribuição. Quem se destrava sozinho pontua ali.

### Travamento automático por tempo

Todo dia o sistema varre as tasks ativas e marca com etiqueta amarela **"Travada"**
aquelas paradas há mais tempo do que o esperado para o tamanho delas. A régua é
**1,5 dia por ponto** — uma task de 2 pontos trava com 3 dias parada, uma de 4 pontos
com 6 dias.

Dois detalhes importantes:

- O relógio conta desde **Planejado**, não só desde "Em andamento". A razão é prática:
  alguém pode estar trabalhando na task sem nunca ter arrastado o card.
- O relógio só começa a contar quando a **sprint é iniciada**. Task planejada para uma
  sprint futura não acumula tempo parado antes da hora.

O travamento não é só um aviso visual: ele **desconta pontos da entrega da pessoa** no
fechamento da sprint. Por isso o gerente pode **dispensar o alerta** quando o atraso não
é responsabilidade de quem está na task — travamento dispensado não penaliza ninguém.

### Reabertura

Mover uma task de volta de "Concluída" registra uma reabertura. O contador fica na task
e alimenta a dimensão Qualidade — reabertura é o sinal de retrabalho do sistema.

### Pedir mais trabalho

Quando alguém termina tudo o que tinha, aparece no Kanban dela o botão **"Quero mais uma
task"**. A pessoa pode escrever junto uma sugestão do que acha que seria útil fazer.
O gerente recebe por e-mail e decide.

A task concedida assim é marcada como **extra** e tem um tratamento próprio:

- **Não consome o orçamento de pontos da sprint** — ela é trabalho além do planejado.
- **Não entra na conta de Entrega** da pessoa. Se entrasse, pedir mais trabalho e não
  conseguir terminar tudo seria punido, e ninguém pediria.
- Vira um **bônus limitado** no score, para que o ranking não vire uma corrida de quem
  pede mais task.

### Sugestões vindas do Review

Quando um Review é registrado, a IA detecta as tasks mencionadas ali como concluídas e
sugere movê-las no quadro. Aparece como sugestão para o gerente aceitar ou ignorar —
nada se move sozinho.

### Outras operações

- **Reordenar** cards dentro da coluna.
- **Redistribuir pontos** entre as tasks de uma sprint de uma vez só.
- **Histórico da task** — toda movimentação fica registrada com data, hora e quem estava
  responsável naquele momento.

---

## 7. Sprints

A aba **Sprints** é o ciclo de trabalho. Cada sprint dura uma semana e a numeração é
automática.

### Iniciar uma sprint

Iniciar é o ato que coloca a sprint em execução: ela passa a aparecer com Planning,
Daily, Review e Avaliação Semanal, e o relógio de travamento das tasks que já estavam
nela começa a correr a partir daquele momento — nunca retroativamente.

### Planning

A tela de Planning **já abre mostrando as tasks daquela sprint que estão no Kanban**,
porque é dali que sai o backlog do documento. O gerente escreve o contexto da sprint em
texto livre e completa os campos estruturados: período, horas previstas, riscos,
dependências e carry-over da sprint anterior. A IA monta o documento a partir disso.

Se as tasks ainda estiverem fora do sistema, um link no topo leva para a importação por
print ou texto. E quem preferir pode escrever o documento inteiro à mão, sem IA.

### Daily

Registro do andamento ao longo da sprint — o que foi feito, o que será feito e os
impedimentos. Cada registro vira histórico. Não há mínimo obrigatório, mas quanto mais
dailys, mais rico fica o repasse semanal e a retrospectiva no fim.

Aceita um anexo opcional, como a transcrição da reunião.

### Review

No fim da sprint, o gerente preenche a percepção do cliente, o sinal de satisfação e os
pedidos que apareceram fora do escopo.

A tabela **planejado vs. entregue é montada automaticamente a partir do Kanban real**:
uma linha por task da sprint, marcada como entregue ou não conforme a coluna em que ela
terminou. O que o sistema deixa em branco de propósito são as colunas de *motivo* e
*causa raiz* — isso é julgamento humano e o gerente completa.

### Retrospectiva

Gerada a partir de tudo o que a sprint acumulou — planning, dailys e review. Traz o que
foi feito, o que funcionou, o que não funcionou e os aprendizados.

### Avaliação Semanal

Sete perguntas sobre cada pessoa que teve task na sprint, respondidas de 0 a 5 pelo
gerente:

1. Entregou o que se comprometeu dentro do combinado nesta sprint?
2. A qualidade da entrega precisou de pouca ou nenhuma correção?
3. A pessoa destravou sozinha antes de te escalar?
4. A comunicação da entrega foi clara a ponto de você não precisar perguntar?
5. Ajudou, desbloqueou ou ensinou outro membro nesta sprint?
6. Evoluiu em relação a onde estava no começo do ciclo?
7. Trouxe algo além do que foi pedido?

**Confirmar a avaliação fecha a semana.** É esse ato que consolida e trava a pontuação
de todo mundo naquela sprint. Depois de confirmado, só o Líder consegue reabrir.

Se a pessoa já foi avaliada recentemente em outro projeto, o sistema oferece
reaproveitar aquela avaliação em vez de responder tudo de novo.

### Pendências

Sprint sem planning ou sem review fica marcada com "pend." no badge da aba, para o
gerente ver de relance o que ficou para trás.

---

## 8. Os documentos que o sistema gera

A aba **Documentos** tem duas visões: **por sprint** e **do projeto inteiro**.

São nove tipos:

**Repasse Semanal** *(por sprint)* — status executivo da semana: o que foi concluído, o
que está em andamento, o que está bloqueado. Serve para comunicar progresso ao líder
estratégico e ao cliente. Sai do planning, das dailys e dos uploads da sprint.

**Retrospectiva** *(por sprint)* — o registro formal do que foi alinhado na retro, para
que decisões não se percam entre sprints. Sai de tudo o que a sprint acumulou.

**Review** *(por sprint)* — compara o planejado com o entregue e explicita o delta.
Gerado pelo formulário do fim da sprint.

**Planning** *(por sprint)* — formaliza o que a sprint pretende entregar e em que
condições. Gerado pelo formulário do início da sprint.

**Daily** *(por sprint)* — o registro estruturado de uma daily, com formato consistente
entre elas.

**Ata de Reunião** *(avulso)* — sobe a transcrição ou a pauta de uma reunião e recebe a
ata formatada com tópicos, decisões e próximos passos. É o caminho para documentar
kickoffs e alinhamentos com cliente.

**Log de Decisões** *(projeto inteiro)* — lista cronológica de todas as decisões
técnicas e de escopo tomadas ao longo do projeto, com o motivo de cada uma. É o
documento de rastreabilidade — útil em handoff e em revisão pós-projeto.

**Onboarding** *(projeto inteiro)* — guia para quem está assumindo o projeto agora: o
que é, contexto do cliente, stack atual, decisões importantes, estado atual e próximos
passos. Reduz o tempo de ramp-up de um gerente ou analista novo.

**Documentação Final** *(projeto inteiro)* — o entregável de fechamento, no template do
CITi: visão geral, timeline de sprints, decisões arquiteturais, desafios, estado final e
glossário.

### O que todo documento permite

- **Copiar como markdown** para colar em qualquer ferramenta.
- **Exportar para o Google Docs**, já formatado.
- **Mover para outra sprint** se foi gerado na sprint errada — sem precisar regerar.
- **Observações adicionais**: um campo livre onde o gerente orienta a IA antes de gerar,
  se quiser puxar o documento para alguma direção.

### Documento manual

Quem já tem o texto pronto pode colar direto, ou subir um PDF, e o conteúdo entra no
acervo do projeto sem passar pela IA.

### O sistema se recusa a inventar

Antes de gerar, o sistema checa se existe matéria-prima suficiente e **se recusa a gerar
quando não existe**, em vez de produzir um documento plausível e vazio:

- Nenhum documento é gerado se não houver nenhum arquivo ou registro no escopo pedido.
- O **Log de Decisões** não é gerado se nenhuma das ingestões contiver decisão alguma —
  a mensagem pede que se suba material que tenha decisões.
- A **Documentação Final** exige dados de pelo menos **duas sprints** para ter
  substância.

---

## 9. Como a IA lê os arquivos

Todo arquivo que entra no sistema passa pelo mesmo caminho.

**Formatos aceitos:** Word (.docx), PDF, texto (.txt) e imagens (.png, .jpg, .jpeg,
.webp).

**Leitura por tipo:**

- Word e texto são lidos diretamente.
- PDF tem o texto extraído. Se o PDF for escaneado e não tiver texto nenhum, o sistema
  converte a página em imagem e lê com visão.
- Imagens — prints de kanban, quadro branco, backlog — são lidas com visão.

**Conferência de tipo antes de processar.** Antes de extrair qualquer coisa, a IA
classifica o documento — planning, daily, review, retrospectiva, ata, commit, upload
livre ou material não relacionado — e compara com o que a tela pediu. Se você estiver na
tela de Review e subir uma aula da faculdade, o sistema avisa. Mas a regra é
deliberadamente conservadora: **na dúvida, ele deixa passar**. Só bloqueia quando tem
alta confiança de que o conteúdo não tem nada a ver.

Se o gerente discordar do bloqueio, ele força o envio e o sistema processa.

**O que a IA extrai de cada arquivo** — sempre os mesmos oito campos, independente do
formato:

- Resumo do que foi trabalhado
- Tarefas identificadas
- Decisões técnicas tomadas
- Problemas e bloqueios
- Contexto do cliente e requisitos de negócio
- Próximos passos
- Tecnologias mencionadas
- Tecnologias removidas

A instrução central do prompt é **extrair apenas o que está explicitamente no conteúdo,
nunca inferir nem inventar**. Em prints de kanban, a IA extrai cada tarefa com
responsável, prazo e critério de pronto, quando visíveis — e omite a parte que não
estiver.

Esse conhecimento se acumula por projeto e por sprint. Quando alguém pede um documento,
a IA usa tudo o que foi acumulado até ali, **mais o estado atual do Kanban**.

### Enriquecimento antes de salvar

Existe ainda um passo opcional de *enriquecimento*: o gerente cola um texto bruto ou
sobe um arquivo, e a IA devolve os campos estruturados **para ele revisar antes** de
qualquer coisa ser salva. É uma prévia, não uma gravação.

---

## 10. Painel — a saúde do projeto

A aba **Painel** responde a uma pergunta: este projeto está indo bem?

### Tempo × Escopo

O bloco principal compara o **percentual do prazo já consumido** com o **percentual do
escopo concluído**. Se o prazo anda mais rápido que o escopo, há atraso.

O **desvio** é a diferença entre os dois: prazo consumido menos escopo concluído. A
**tolerância** configurada no projeto define quantos pontos percentuais de diferença são
aceitáveis — acima disso o Painel acusa desvio.

O alarme mede entrega real. O escopo concluído vem do status das funcionalidades, que o
gerente edita na aba Planejamento, então um projeto que entregou mais do que o
calendário pediu aparece com desvio negativo e nenhum alarme. Só acusa desvio quem está
de fato consumindo prazo mais rápido do que conclui escopo.

### Itens em atenção

Reúne as funcionalidades **travadas** — em andamento há mais de 7 dias — e, junto
delas, os achados críticos do revisor diário de código, quando a integração com o
GitHub está instalada.

### Fluxo de funcionalidades

- **WIP** — quantas funcionalidades estão em andamento agora.
- **Throughput** — quantas foram concluídas por semana.
- **Cycle-time** — quanto tempo cada uma leva do início ao fim.
- **Eficiência de fluxo** — o percentual do tempo em que as funcionalidades estiveram de
  fato sendo trabalhadas, e não paradas entre etapas. É o indicador que separa "demorou
  porque é grande" de "demorou porque ficou parado na fila".

### Tempo por fase

Mostra quanto tempo as funcionalidades passam em cada fase. É onde o gargalo aparece.

### Kanban de Sprint

Organiza as funcionalidades planejadas por sprint, para ver a distribuição do escopo ao
longo do tempo.

---

## 11. Métricas — os números de fluxo

A aba **Métricas** olha as tasks, não as funcionalidades.

**SPI** — mede se a sprint entregou o que planejou: pontos concluídos sobre pontos
previstos. Acima de 0,9 é saudável, entre 0,7 e 0,9 pede atenção, abaixo de 0,7 é
crítico. Só aparece em sprint que tenha orçamento de pontos definido.

O SPI também **atualiza sozinho o semáforo de saúde da sprint** — verde, amarelo ou
vermelho — sempre que o orçamento é definido ou uma task é concluída.

**Throughput** — quantas tasks foram concluídas por sprint.

**Cycle-time** — quanto tempo cada task ficou em "Em andamento", com a distribuição
(mediana e percentis). Task acima de três dias costuma indicar bloqueio, escopo grande
demais ou dependência externa.

**CFD** — a foto do estado das tasks por sprint. Se "Em andamento" cresce sem
"Concluída" crescer junto, há gargalo.

**SPI por pessoa (estimado)** — uma leitura **ao vivo** sobre as tasks atuais de cada
um, para ver quem está sobrecarregado agora. É diferente do número consolidado que
alimenta o ranking: este é um retrato do momento, aquele é o histórico travado.

**Entrega e evolução por pessoa** — o dado consolidado dos fechamentos de sprint. É o
que sustenta a conversa de feedback do gerente com cada pessoa.

---

## 12. Tecnologias

A aba **Tecnologias** monta uma linha do tempo do stack do projeto: em qual sprint cada
tecnologia foi introduzida e em qual foi abandonada.

A informação vem das tecnologias que a IA identifica em cada arquivo e, principalmente,
dos commits.

Uma regra deliberada: **uma tecnologia só é marcada como abandonada quando algum commit
a removeu explicitamente** — pacote deletado do arquivo de dependências, diretório
excluído, imports apagados. Simplesmente não ser mencionada nas últimas sprints não
conta como abandono, porque isso produziria falsos abandonos toda vez que uma parte do
sistema ficasse um tempo sem receber alterações.

---

## 13. Acompanhamento de contribuição

O sistema acompanha a contribuição individual ao longo das sprints, para reconhecimento
periódico. O ranking em si é visível apenas para o Líder.

### Quando o dado é fechado

Nada é contado ao longo da semana. **No momento em que o gerente confirma a Avaliação
Semanal**, o sistema olha o estado final de tudo — tasks, movimentações, bloqueios,
reaberturas, travamentos, notas de commit e as respostas do gerente — e grava uma linha
travada por pessoa.

Duas consequências disso:

- Reatribuir uma task no meio da semana não bagunça nada, porque o cálculo lê o estado
  final e o histórico, não um contador acumulado.
- O crédito por uma task concluída vai para **quem estava com ela no momento em que foi
  concluída**, mesmo que ela tenha sido reatribuída depois.

Se uma reabertura ou um bloqueio acontece numa task cuja sprint já foi fechada, o evento
não é perdido nem recontado: ele é redirecionado para a sprint ativa.

### As cinco dimensões

Cada pessoa é lida em cinco dimensões, todas numa escala de 0 a 100:

**Entrega** — pontos concluídos sobre pontos que estavam com ela, descontando os pontos
penalizados por travamento não dispensado.

**Avaliação do gerente** — a média das respostas do gerente às perguntas 1, 2, 3, 4, 5
e 7.

**Evolução** — vem exclusivamente da pergunta 6 ("evoluiu em relação a onde estava no
começo do ciclo?"). Ela fica fora da média do gerente de propósito: se entrasse nos dois
lugares, uma única pergunta teria peso triplo.

**Autonomia** — combina dois sinais: a proporção de bloqueios que a pessoa resolveu
sozinha, e a pergunta 3 do gerente. A pergunta entrou como segunda fonte porque bloqueio
marcado é raro na prática — sem ela, Autonomia dava 100 para todo mundo e virava peso
morto. Quando não houve bloqueio nenhum, a pergunta 3 sustenta a dimensão sozinha.

**Qualidade** — combina a nota de qualidade técnica dos commits com o retrabalho
(reaberturas sobre tasks concluídas).

### Regras que tornam o número justo

- **Dimensão sem dado não vira zero — vira indisponível**, e os pesos são
  redistribuídos entre as que existem. Zerar alguém por falta de sinal seria punir a
  ausência de informação.
- **Quem não entregou nada não ganha 100 em Qualidade.** Sem task concluída e sem nota
  de commit, a dimensão fica indisponível — dar nota cheia premiaria a ausência de
  entrega.
- **Task extra não entra em Entrega**, nem no numerador nem no denominador. Ela vira um
  bônus com teto, para que o ranking não vire uma corrida de quem pediu mais trabalho.
- **Travamento dispensado pelo gerente não penaliza ninguém.**
- Quem atua em mais de um projeto tem a nota calculada **dentro de cada projeto
  primeiro**, e depois a média entre eles — para que um projeto com muito mais tasks não
  domine a leitura da pessoa.

### Pesos por tipo de projeto

Em **projeto padrão**, com código: avaliação do gerente 35%, entrega 20%, qualidade 20%,
autonomia 15%, evolução 10%.

Em **consultoria/discovery**, sem código: avaliação do gerente 50%, entrega 20%,
autonomia 12%, qualidade 10%, evolução 8%. A leitura do gerente pesa mais porque não
existe sinal de commit para observar.

### As janelas do ranking

O ranking é lido em três janelas, contadas **por número de sprints, nunca por
calendário**: a última sprint, as duas últimas (quinzenal) e as quatro últimas (mensal).
Janela com menos sprints do que o esperado é marcada como parcial, para não passar como
leitura completa.

### Transparência

A metodologia é documentada dentro do próprio sistema, em três documentos com audiências
diferentes:

- **Guia do DocuData** — como o sistema funciona, tela por tela. Aberto a todos.
- **Como sua contribuição é acompanhada** — para operacionais: o que conta, o que não
  conta e como funciona o reconhecimento. Aberto a todos.
- **Sistema de Acompanhamento de Performance** — a metodologia completa, com pesos,
  fórmulas e manual do gerente. Restrito a Gerente para cima, e nem aparece na listagem
  para quem não pode abrir.

---

## 14. Integração com GitHub

Projetos com código podem instalar duas integrações no repositório. Todas são
propositalmente tolerantes a falha: se alguma quebrar, ela nunca derruba o build do time.

### Ingestão de commits

A cada commit, o sistema recebe a mensagem e o conteúdo da mudança, e faz três coisas:

1. **Extrai conhecimento técnico** do diff — o que foi feito, decisões, problemas
   corrigidos, tecnologias introduzidas e removidas. Isso alimenta a documentação e a
   linha do tempo de tecnologias.
2. **Avalia a qualidade técnica do commit de 0 a 10**, olhando a complexidade da tarefa
   resolvida, a clareza da documentação e da mensagem, e a aderência a boas práticas.
   Essa nota alimenta a dimensão Qualidade da pessoa. A avaliação devolve a nota e uma
   frase curta explicando o porquê — nunca uma lista de pendências a corrigir.
3. **Associa o commit à pessoa**, pelo usuário ou e-mail do GitHub cadastrado.

O commit pode ainda ser vinculado a uma task específica através de uma marcação na
mensagem.

### Revisor diário

Uma vez por dia, o sistema recebe tudo o que mudou no repositório nas últimas 24h e
devolve os achados — com severidade, nível de confiança e a referência exata de arquivo
e linha. O relatório sai em duas versões: uma técnica e uma escrita para o gerente.

---

## 15. Avisos automáticos

O sistema manda e-mail sozinho em algumas situações.

**Lembretes de sprint**, enquanto o documento continuar faltando:

- Planning — a partir de 24h depois de a sprint ser criada
- Review — a partir de 5 dias
- Retrospectiva — a partir de 7 dias

No máximo um e-mail de cada tipo, por sprint, por dia.

**Avisos de task:**

- A pessoa é avisada quando uma task é atribuída a ela.
- O gerente é avisado quando uma task é concluída.
- O gerente é avisado quando alguém pede uma task extra, com a sugestão que a pessoa
  escreveu.

---

## 16. Outras telas

**Pessoas** — lista de todo mundo cadastrado no sistema, com o cargo de cada um.
Apenas o Owner altera cargos.

**Performance** — a área de ranking, restrita ao Líder.

**Metodologia** — onde ficam os três documentos internos descritos acima.

**Busca de stack** — pesquisa por tecnologia entre todos os projetos, para responder
"quem já usou isso aqui dentro?".

---

## 17. Acompanhamento do cliente — removido

Existiu no back-end uma trilha de aprovação do cliente — um status da funcionalidade com
o cliente, um boletim de aceite gerado por IA e uma suíte de verificação de aceite
alimentada pelo CI — que nunca ganhou interface e nunca entrou na rotina dos gerentes.

Essa trilha foi **removida do código em setembro de 2026**. As colunas e tabelas
correspondentes continuam no banco, vazias e sem nada lendo ou escrevendo nelas, para
não destruir dado.

Na prática, o DocuData acompanha **execução interna** — tasks, sprints, pontos, pessoas,
documentação. Ele não acompanha o ciclo de validação com o cliente.

---

## 18. Outras limitações conhecidas

**"Ver fontes" de um documento é incompleto.** Hoje não dá para navegar de um documento
gerado até o arquivo específico que originou cada trecho.

**Não há isolamento por projeto acima do operacional.** Gerente e Líder enxergam todos
os projetos do sistema — foi uma decisão consciente para simplificar, não um descuido.

**A identidade de uma pessoa entre projetos depende do e-mail.** Cadastro de operacional
sem e-mail preenchido aparece como uma pessoa separada no acompanhamento de contribuição.

**Duas telas de Planning coexistem** — uma na aba Sprints e outra no fluxo guiado por
etapas. Elas fazem a mesma coisa por caminhos diferentes.

**O rastreamento de custo de IA foi removido** em setembro de 2026. O guia do sistema
ainda tem uma seção falando em teto de gasto por projeto e custo por documento, que não
corresponde mais ao comportamento atual.
