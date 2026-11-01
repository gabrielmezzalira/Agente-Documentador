# Guia do DocuData

Subárea de Dados · CITi

---

> Esta é a versão curta. Para o detalhe de cada regra, tela e cálculo, gerentes
> e líderes têm a **Bíblia do DocuData**, aqui mesmo na aba Documentos.

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
   gargalos de fluxo e metas da sprint.
3. **Acompanha a contribuição** de cada pessoa, para reconhecimento.

---

## Quem vê o quê

O sistema tem quatro cargos.

| Cargo | O que alcança |
|---|---|
| **Owner** | Tudo, mais a gestão dos cargos das outras pessoas |
| **Líder** | Tudo em todos os projetos, incluindo Acompanhamento, Classificador e Performance |
| **Gerente** | Todos os projetos, sem o ranking de performance |
| **Operacional** | Sprints, Tasks, Tecnologias e Documentos dos projetos em que está |

---

## As telas fora do projeto

- **Projetos**: a lista de projetos da subárea (Dados ou Dev), com quantos estão
  ativos, entregues e pedindo atenção. A busca encontra em quais projetos uma
  tecnologia já foi usada.
- **Acompanhamento** (Líder): os projetos agrupados por gerente, com a meta da
  sprint, o que foi planejado, prazo contra escopo e saúde. É aqui que o líder
  define a meta de cada sprint.
- **Avaliações**: as notas da avaliação semanal, com correção e histórico.
- **Classificador** (Líder): mostra o quanto o nível sugerido para as tasks
  bateu com o tempo real que elas levaram.
- **Performance** (Líder): a contribuição de cada pessoa por projeto, em
  janelas de sprint, quinzena ou mês.
- **Pessoas** (Líder e Owner): quem tem acesso ao sistema e em quais projetos.
- **Documentos**: este guia e os demais documentos do sistema.
- **Configurações**: a chave da IA, única para o sistema todo.

---

## As abas de um projeto

### Sprints

O ciclo de trabalho e os documentos que saem dele. É a aba que abre primeiro.

- **Criar sprint**: o número é atribuído sozinho. Uma sprint dura uma semana.
- **Planning**: a tela abre mostrando as tasks daquela sprint que estão no
  Kanban, porque é dali que sai o backlog do documento. Você escreve o contexto
  da sprint em texto livre, completa os campos (squad, período, horas, riscos,
  dependências, carry-over), e a IA monta o documento. Se as tasks estiverem
  fora do sistema, um link leva para a importação por print ou texto. Também dá
  para escrever tudo à mão, sem IA.
- **Foto do previsto**: quando a sprint começa, o sistema guarda as tasks que
  estavam nela. É contra essa foto que o entregue é comparado.
- **Daily**: registre as dailys ao longo da sprint. Não há mínimo obrigatório,
  mas quanto mais dailys, mais rico o repasse semanal.
- **Review**: no fim da sprint, preencha os campos (percepção do cliente, sinal
  de satisfação, pedidos fora do escopo). O planejado contra o entregue e o
  estado do Kanban entram sozinhos.
- **Retrospectiva**: gerada a partir de planning, dailys e review. Traz o que foi
  feito, o que funcionou, o que não funcionou e os aprendizados.
- **Repasse Semanal**: resumo da semana a partir das dailys e dos arquivos
  enviados.
- **Avaliação Semanal**: seis perguntas sobre cada operacional do projeto, com
  notas de 0 a 5. Com todas respondidas, você fecha a sprint, e os números da
  semana ficam congelados. Só o Líder reabre um fechamento.

### Planejamento

Onde vive o escopo contratado.

- **Funcionalidades** são as entregas de alto nível para o cliente, como "Tela
  de Login" ou "Relatório mensal". Diferentes das tasks, que são o trabalho
  técnico por trás.
- **Importar do contrato**: suba o PDF da proposta e a IA extrai as
  funcionalidades. Você revisa antes de confirmar.
- **Prioridades MoSCoW**: Must é obrigatório para a entrega, Should é importante
  mas não bloqueia, Could é desejável se sobrar tempo, Won't está fora desta
  versão.
- **Status**: Não iniciada, Em andamento, Em ajuste ou Concluída. Se a
  funcionalidade tem tasks, o status é calculado sozinho a partir delas. Sem
  tasks, você define à mão.
- **Aprovação**: uma funcionalidade concluída precisa da sua aprovação para
  contar como entregue. A aprovação cai se uma task dela for reaberta ou entrar
  uma task nova.
- **Meta da sprint**: a funcionalidade que está na meta definida pelo líder
  ganha o selo "meta da sprint".

### Painel

A visão de saúde do projeto.

- **Tempo × Escopo** compara o percentual do prazo já consumido com o percentual
  do escopo concluído. Se o prazo anda mais rápido que o escopo além da
  tolerância (20 pontos por padrão), aparece o alerta de desvio.
- **Itens em atenção** lista as funcionalidades em andamento sem nenhum
  movimento há mais de 7 dias.
- **WIP, throughput e cycle-time de funcionalidades**: quantas estão em
  andamento agora, quantas são concluídas por semana e quanto tempo cada uma
  leva do início ao fim.
- **Eficiência de fluxo** e **tempo por fase** mostram onde o trabalho fica
  parado.
- **Kanban de Sprint** organiza as funcionalidades planejadas por sprint.

### Tasks e Kanban

O coração do sistema. É daqui que sai quase tudo.

- **Colunas**: Planejado, Em andamento, Pendente de aprovação e Concluída. A
  coluna Pendente de aprovação só recebe tasks marcadas como "requer
  aprovação", que passam pelo gerente antes de concluir.
- **Criar uma task**: título e descrição bem escritos são o que importa. Você
  não digita os pontos.
- **Nível de dificuldade**: os pontos são só dificuldade, numa régua única: 1
  (simples), 2 (moderada), 3 (complexa) e 5 (muito complexa). Quem define o
  nível é o **classificador**, um agente de IA que lê a task, compara com tasks
  parecidas do passado e aprende com o tempo real que elas levaram. Você pode
  dar sua opinião, que entra com peso pequeno.
- **Checklist**: a lista de itens que precisam estar prontos para a task poder
  ir para Concluída. O card mostra o progresso, tipo "3/5". Task sem checklist
  não trava nada.
- **Sprint obrigatória para iniciar**: uma task só entra em Em andamento se
  estiver ligada a uma sprint.
- **Limite de tasks simultâneas**: quantas tasks o projeto e cada pessoa podem
  ter em andamento ao mesmo tempo. É o freio contra começar dez e terminar duas.
- **Bloqueio**: quem está travado marca a task como bloqueada, escolhe o tipo
  (por exemplo, dependência do cliente) e escreve o motivo. O card ganha borda
  vermelha.
- **Task travada por tempo**: se uma task fica parada em Em andamento por mais
  de um dia e meio por ponto, ela ganha a etiqueta "Travada". O gerente pode
  suprimir o alerta quando o atraso não é responsabilidade de quem está nela.
- **Pedir mais trabalho**: quando alguém termina tudo que tinha, aparece no
  Kanban o botão "Quero mais uma task", que avisa o gerente por e-mail.
- **Task extra** é a concedida além do planejado. Ela não entra no previsto da
  sprint.
- **Sugestões do review**: quando um review é registrado, o sistema detecta as
  tasks mencionadas como concluídas e sugere movê-las.

### Modos de trabalho: Atribuição e Pull

Cada projeto escolhe, na aba Configurações, como as tasks chegam às pessoas.

- **Atribuição** (padrão): o gerente define o responsável de cada task.
- **Pull**: as tasks ficam numa fila, sem responsável, e cada pessoa **puxa** a
  próxima quando termina a anterior. Cada pessoa tem uma task em andamento por
  vez, e pode devolver à fila uma task que não consegue tocar.

Trocar de modo reorganiza as tasks existentes, e o sistema mostra uma prévia
antes de confirmar.

### Métricas

Os números de fluxo do projeto.

- **SPI** mede se a sprint entregou o que previu: pontos concluídos sobre os
  pontos da foto do previsto. A partir de 0,9 é saudável, entre 0,7 e 0,9 pede
  atenção, abaixo de 0,7 é crítico.
- **Throughput**: quantas tasks foram concluídas por sprint.
- **Cycle-time**: quanto tempo cada task ficou em Em andamento. Task com mais de
  três dias costuma indicar bloqueio, escopo grande demais ou dependência
  externa.
- **CFD**: a foto do estado das tasks por sprint. Se "Em andamento" cresce sem
  "Concluída" crescer junto, há gargalo.
- **SPI por operacional (estimado)**: leitura ao vivo das tasks de cada pessoa.
  Serve para ver quem está sobrecarregado agora.
- **Entrega por pessoa**: o dado consolidado dos fechamentos de sprint. É o que
  sustenta a conversa de feedback.

### Tecnologias

A linha do tempo das tecnologias do projeto, montada sozinha a partir dos
arquivos e commits: quando cada uma entrou e em quais sprints apareceu.

### Documentos

Onde ficam os documentos gerados, em duas visões.

**Por sprint** reúne planning, daily, review, retrospectiva e repasse semanal
de cada sprint. Documento gerado na sprint errada pode ser movido sem regerar.

**Cross-sprint** são os documentos que olham o projeto inteiro:

- **Ata de Reunião**: suba o arquivo da reunião e receba a ata com pauta,
  decisões e próximos passos.
- **Log de Decisões**: compila todas as decisões técnicas e de negócio
  registradas no projeto.
- **Onboarding**: documento para quem entra agora, com contexto do cliente,
  stack, decisões e estado atual.
- **Documentação Final**: o entregável de fim de projeto, com visão geral,
  timeline, decisões arquiteturais, desafios e estado final. Precisa de dados
  de pelo menos duas sprints.
- **Observações adicionais**: campo livre para orientar a IA na geração.
- **Documento manual**: suba um PDF pronto. O texto é guardado como está, sem
  passar pela IA.

Todo documento gerado pode ser editado, copiado como markdown ou exportado para
o Google Docs.

### Configurações

Repositórios do GitHub, e-mail do gerente para os lembretes, status de
entregue, modo de trabalho, equipe de operacionais, datas do contrato e
tolerância de desvio.

---

## Como os documentos são gerados

Todo documento sai do mesmo lugar: o que já está no sistema.

1. Você alimenta o projeto no dia a dia, movendo tasks e subindo os arquivos que
   já existem (atas, prints, PDFs, documentos de texto).
2. Cada arquivo que entra é lido por IA e vira conhecimento estruturado: resumo,
   tarefas, decisões, problemas, contexto de cliente e próximos passos.
3. Esse conhecimento se acumula por projeto e por sprint.
4. Quando você pede um documento, a IA usa tudo o que foi acumulado até ali, mais
   o estado atual do Kanban. O que não estiver nos registros aparece marcado
   como insumo insuficiente, em vez de inventado.

A consequência prática: **quanto mais fiel o Kanban, melhor a documentação**. Não
existe um passo separado de "documentar", existe manter o trabalho registrado.

---

## Integração com o GitHub

Projetos com código podem conectar o repositório na aba Configurações. A cada
commit, o sistema recebe a mensagem e a mudança, extrai o conhecimento técnico
e alimenta a documentação e a linha do tempo de tecnologias do projeto.

Para que os commits sejam reconhecidos como seus, o **usuário do GitHub** precisa
estar cadastrado no seu perfil de operacional no projeto.

---

## Lembretes por e-mail

O sistema avisa por e-mail o gerente do projeto quando falta planning, review
ou retrospectiva numa sprint, e avisa as pessoas sobre tasks atribuídas,
concluídas, pendentes de aprovação ou rejeitadas. Para parar os lembretes de
sprint de um projeto, basta remover o e-mail do gerente nas Configurações.

---

## Acompanhamento de contribuição

O sistema também acompanha a contribuição individual ao longo das sprints, para
reconhecimento a cada duas semanas.

O que conta, o que não conta e como funciona o reconhecimento está no documento
**"Como sua contribuição é acompanhada"**, acessível a todo mundo nesta mesma
aba.

---

## Baixar os documentos

Cada documento desta aba tem o botão **Baixar PDF**, e o botão **Baixar todos em
PDF (.zip)** baixa de uma vez todos os que você pode abrir.
