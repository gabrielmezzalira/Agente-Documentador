# Guia do DocuData

Subárea de Dados · CITi

---

## O que o DocuData faz

Documentar projeto de dados custa caro e quase ninguém faz. O conhecimento fica
na cabeça das pessoas e some quando o projeto acaba ou a gestão troca.

O DocuData resolve isso de trás para frente: em vez de pedir que alguém escreva
documentação, ele lê o que o time já produz naturalmente (o Kanban, as atas, os
prints, os commits) e monta os documentos sozinho. Você mantém o trabalho
atualizado no sistema e a documentação sai como consequência.

Ele faz três coisas ao mesmo tempo, a partir da mesma fonte:

1. **Documenta** o projeto sprint a sprint, sem ninguém escrever do zero.
2. **Acompanha a saúde** do projeto: prazo contra escopo, ritmo de entrega,
   gargalos de fluxo.
3. **Acompanha a contribuição** de cada pessoa, para reconhecimento.

---

## Quem vê o quê

O sistema tem quatro cargos.

| Cargo | O que alcança |
|---|---|
| **Owner** | Tudo, mais a gestão dos cargos das outras pessoas |
| **Líder** | Tudo em todos os projetos, incluindo o acompanhamento de performance |
| **Gerente** | Todos os projetos, sem o ranking de performance |
| **Operacional** | Kanban, tasks e sprints dos projetos em que está |

---

## As abas de um projeto

### Painel

A visão de saúde do projeto.

- **Tempo × Escopo** compara o percentual do prazo já consumido com o percentual
  do escopo concluído. Se o prazo anda mais rápido que o escopo, há atraso. As
  datas e a tolerância se configuram no card "Editar".
- **Desvio e tolerância**: o desvio é o prazo consumido menos o escopo concluído.
  A tolerância define quantos pontos percentuais são aceitáveis; acima disso
  aparece alerta.
- **Itens em atenção** reúne as funcionalidades travadas, que dependem de
  cliente, de dependência externa ou de decisão pendente.
- **WIP, throughput e cycle-time de funcionalidades**: quantas estão em
  andamento agora, quantas foram concluídas por semana, e quanto tempo cada uma
  leva do início ao fim.
- **Eficiência de fluxo** é o percentual do tempo em que as funcionalidades
  estiveram de fato em andamento, e não paradas entre etapas.
- **Tempo por fase** mostra onde está o gargalo.
- **Kanban de Sprint** organiza as funcionalidades planejadas por sprint.

### Escopo

Onde vive o escopo contratado.

- **Funcionalidades** são as entregas de alto nível para o cliente, como "Tela de
  Login" ou "Relatório mensal". Diferentes das tasks, que são o trabalho técnico
  por trás.
- **Importar do contrato**: suba o PDF da proposta e a IA extrai as
  funcionalidades. Você revisa antes de confirmar.
- **Prioridades MoSCoW**: Must é obrigatório para a entrega, Should é importante
  mas não bloqueia, Could é desejável se sobrar tempo, Won't está fora desta
  versão. Serve para alinhar expectativa com o cliente.
- **Status**: Não iniciada, Em andamento, Concluída. É o que alimenta o "escopo
  concluído" do Painel.
- **Distribuir os 100 pontos**: todo projeto vale 100 pontos, fixo. Aqui você diz
  quanto cada sprint recebe desses 100. A soma não pode passar de 100, e uma
  sprint não pode receber menos do que as tasks dela já somam. Sprint sem
  orçamento não trava nada.
- **Valor do projeto**: se você informar o valor do contrato em reais, cada ponto
  passa a valer um centésimo desse valor e o faturamento previsto de cada sprint
  sai sozinho. O valor congela quando a primeira sprint recebe orçamento.

### Tasks e Kanban

O coração do sistema. É daqui que sai quase tudo.

- **Três colunas**: Planejado, Em andamento, Concluída. Arraste ou edite a task
  para mover.
- **Criar uma task**: título e pontos são obrigatórios; sprint, operacional,
  funcionalidade e checklist são opcionais.
- **Checklist**: a lista de itens que precisam estar prontos para a task poder ir
  para Concluída. O card mostra o progresso, tipo "3/5". Task sem checklist não
  trava nada.
- **Sprint obrigatória para iniciar**: uma task só entra em Em andamento se
  estiver ligada a uma sprint.
- **Limite de tasks simultâneas**: você configura quantas tasks o projeto e cada
  pessoa podem ter em andamento ao mesmo tempo. É o freio contra começar dez e
  terminar duas.
- **Bloqueio**: quem está travado marca a caixa "Bloqueada" na task e escreve o
  motivo. O card ganha borda vermelha e fica visível no quadro. Ao destravar,
  alguém informa quem resolveu.
- **Task travada por tempo**: se uma task fica parada em Em andamento por mais de
  um dia e meio por ponto, ela ganha a etiqueta amarela "Travada". O gerente pode
  suprimir o alerta quando o atraso não é responsabilidade de quem está nela.
- **Pedir mais trabalho**: quando alguém termina tudo que tinha, aparece no
  Kanban dela o botão "Quero mais uma task", que avisa o gerente por e-mail.
- **Task extra** é a concedida além do planejado. Ela não consome o orçamento de
  pontos da sprint.
- **Sugestões do review**: quando um review é registrado, o sistema detecta as
  tasks mencionadas como concluídas e sugere movê-las. Você aceita ou ignora.

### Sprints e Documentação

O ciclo de trabalho e os documentos que saem dele.

- **Criar sprint**: o número é atribuído sozinho. Uma sprint dura uma semana.
- **Planning**: a tela abre mostrando as tasks daquela sprint que estão no
  Kanban, porque é dali que sai o backlog do documento. Você escreve o contexto
  da sprint em texto livre, completa os campos (período, horas, riscos,
  dependências, carry-over), e a IA monta o documento. Se as tasks estiverem fora
  do sistema, o link no topo leva para a importação por print ou texto. Também dá
  para escrever tudo à mão, sem IA.
- **Daily**: registre as dailys ao longo da sprint. Cada upload vira histórico.
  Não há mínimo obrigatório, mas quanto mais dailys, mais rico o repasse semanal.
- **Review**: no fim da sprint, preencha os campos (percepção do cliente, sinal
  de satisfação, pedidos fora do escopo). O estado do Kanban entra automaticamente
  no contexto.
- **Retrospectiva**: gerada a partir de planning, dailys e review. Traz o que foi
  feito, o que funcionou, o que não funcionou e os aprendizados.
- **Repasse Semanal**: resumo da semana a partir das dailys e ingestões.
- **Avaliação Semanal**: as sete perguntas sobre cada pessoa que teve task na
  sprint. Fecha a semana e consolida o acompanhamento. Só o Líder consegue
  reabrir um fechamento.
- **Pendências**: sprints sem planning ou review ficam marcadas com "pend." no
  badge da aba.

### Documentos

Onde ficam os documentos gerados, em duas visões.

**Por sprint** reúne repasse semanal e retrospectiva de cada sprint. Documento
gerado na sprint errada pode ser movido sem regerar. Tudo pode ser copiado como
markdown ou exportado para o Google Docs.

**Cross-sprint** são os documentos que olham o projeto inteiro:

- **Ata de Reunião**: suba o arquivo da reunião e receba a ata formatada com
  pauta, decisões e próximos passos.
- **Log de Decisões**: compila todas as decisões técnicas e de negócio
  registradas em todas as ingestões do projeto.
- **Onboarding**: documento de integração para quem entra agora, com contexto do
  cliente, stack, decisões e estado atual.
- **Documentação Final**: o entregável de fim de projeto, com visão geral,
  timeline, decisões arquiteturais, desafios e estado final.
- **Observações adicionais**: campo livre para orientar a IA na geração.
- **Doc manual**: cole qualquer texto pronto, sem custo de IA.

### Métricas

Os números de fluxo do projeto.

- **SPI** mede se a sprint entregou o que planejou: pontos concluídos sobre
  pontos previstos. Acima de 0,9 é saudável, entre 0,7 e 0,9 pede atenção, abaixo
  de 0,7 é crítico. Só aparece se a sprint tiver orçamento de pontos.
- **Throughput**: quantas tasks foram concluídas por sprint.
- **Cycle-time**: quanto tempo cada task ficou em Em andamento. Task com mais de
  três dias costuma indicar bloqueio, escopo grande demais ou dependência externa.
- **CFD**: a foto do estado das tasks por sprint. Se "Em andamento" cresce sem
  "Concluída" crescer junto, há gargalo.
- **SPI por operacional (estimado)**: proxy ao vivo sobre todas as tasks de cada
  pessoa. Serve para ver quem está sobrecarregado agora.
- **Entrega e evolução por pessoa**: o dado consolidado dos fechamentos de sprint.
  É o que sustenta a conversa de feedback.

---

## Como os documentos são gerados

Todo documento sai do mesmo lugar: o que já está no sistema.

1. Você alimenta o projeto no dia a dia, movendo tasks e subindo os arquivos que
   já existem (atas, prints, PDFs).
2. Cada arquivo que entra é lido por IA e vira conhecimento estruturado: resumo,
   tarefas, decisões, problemas, contexto de cliente e próximos passos.
3. Esse conhecimento se acumula por projeto e por sprint.
4. Quando você pede um documento, a IA usa tudo o que foi acumulado até ali, mais
   o estado atual do Kanban.

A consequência prática: **quanto mais fiel o Kanban, melhor a documentação**. Não
existe um passo separado de "documentar", existe manter o trabalho registrado.

---

## Integração com o GitHub

Projetos com código podem instalar uma integração no repositório. A cada commit,
o sistema recebe a mensagem e o conteúdo da mudança, extrai o conhecimento
técnico e alimenta a documentação e a linha do tempo de tecnologias do projeto.

Para que os commits sejam reconhecidos como seus, o **usuário do GitHub** precisa
estar cadastrado no seu perfil de operacional no projeto.

---

## Acompanhamento de contribuição

O sistema também acompanha a contribuição individual ao longo das sprints, para
reconhecimento a cada duas semanas.

O que conta, o que não conta e como funciona o reconhecimento está no documento
**"Como sua contribuição é acompanhada"**, acessível a todo mundo no mesmo lugar
onde você está lendo este guia.

---

## Custos

Cada geração de documento e cada arquivo processado consomem tokens de IA, e o
custo aparece no projeto. Dá para definir um teto de gasto por projeto e usar uma
chave própria de IA. Documento manual não tem custo de IA nenhum.
