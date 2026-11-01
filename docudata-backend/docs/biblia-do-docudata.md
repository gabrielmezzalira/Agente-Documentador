# Bíblia do DocuData

Referência completa do sistema · CITi

---

> Este documento explica **tudo o que existe no DocuData e como funciona**:
> cada tela, cada regra, cada métrica e o papel da IA em cada etapa. Ele é a
> referência mais completa do sistema. O Guia do DocuData é a versão curta, e o
> documento de Acompanhamento de Performance aprofunda a metodologia de
> reconhecimento.
>
> Restrito a Gerente para cima, porque traz pesos e fórmulas da performance.
> Para operacionais, use "Como sua contribuição é acompanhada".

## Como ler este documento

- **Se você é gerente e está começando:** leia a Parte 1, que apresenta o
  sistema, os cargos e os projetos. Depois a Parte 3, sobre tasks e Kanban, e a
  Parte 4, que explica a sprint e a planning. Isso cobre o dia a dia.
- **Se você é líder:** acrescente a parte do classificador (Parte 3), a Parte 5
  inteira (métricas, pontuação e performance) e a tela de Acompanhamento
  (Parte 2).
- **Para consulta:** use o índice abaixo e o glossário no final.

## Índice

| Parte | O que cobre |
|---|---|
| **1. O sistema, os cargos e os projetos** | O que é o DocuData, quem vê o quê, as telas, como criar e configurar um projeto e as integrações com GitHub, Google Docs e e-mail |
| **2. Escopo, funcionalidades, metas e acompanhamento** | Funcionalidades e prioridades, enriquecimento por IA, status e aprovação, meta da sprint, tela de Acompanhamento, Painel e Tecnologias |
| **3. Tasks, Kanban e Classificador** | A task e seus pontos, o Kanban, os modos Atribuição e Pull, limites de trabalho em andamento, bloqueios, travamento, pedidos de mais trabalho, commits e o classificador de dificuldade |
| **4. Sprints, Planning e Documentação** | O ciclo da sprint, como gerar a planning passo a passo, Review, Daily, Retrospectiva e Repasse, envio de arquivos e todos os documentos que o sistema gera |
| **5. Métricas, pontuação e performance** | Cada métrica e como é calculada, a pontuação da semana, as quatro dimensões da performance, a avaliação do gerente, o fechamento da sprint e um exemplo completo |
| **Apêndice A. Os outros documentos** | O que cada documento da aba Documentos cobre |
| **Apêndice B. Glossário** | Os termos do sistema em uma linha cada |

## O DocuData em uma página

O gerente organiza o trabalho em **projetos**. Cada projeto tem um **escopo**,
feito de funcionalidades priorizadas, que vira **tasks** no **Kanban**. Toda
task recebe um **nível de dificuldade** (1, 2, 3 ou 5). Quem sugere o nível é o
**classificador**, um agente de IA que aprende com o tempo que as tasks
realmente levaram.

O trabalho acontece em **sprints** de uma semana. A sprint começa com a
**planning**, que a IA escreve a partir das tasks do Kanban e do contexto que o
gerente informa. No início da sprint o sistema tira uma **foto do previsto**,
que depois é comparada com o que foi entregue.

Durante a semana entram **dailys**, **commits** do GitHub e arquivos soltos,
como atas, prints e PDFs. A IA transforma tudo em conhecimento organizado, que
alimenta os documentos do projeto: review, retrospectiva, log de decisões,
repasse e documento completo.

Os mesmos dados alimentam duas leituras de saúde:

- **A do projeto**, nas abas Painel e Métricas e na tela de Acompanhamento.
  Ela mostra prazo contra escopo, ritmo, gargalos e se a meta da sprint vai ser
  cumprida.
- **A das pessoas**, na pontuação e na performance. Ela junta entrega,
  avaliação semanal do gerente, qualidade técnica e autonomia num ranking por
  projeto, que fica congelado quando a sprint é **fechada**.

---

## Parte 1 — O sistema, os cargos e os projetos

Esta parte explica o "chão" do DocuData: o que o sistema é, como alguém entra, quem pode fazer o quê, quais telas existem, como um projeto nasce e é configurado e com o que o sistema conversa (GitHub, Google Docs, e-mail). Os capítulos seguintes detalham cada frente de trabalho.

---

### 1.1 O que é o DocuData e o problema que resolve

Projetos de dados e de software do CITi acumulam conhecimento: decisões técnicas, contexto do cliente, bloqueios, escolhas de arquitetura. Esse conhecimento fica na cabeça das pessoas e se perde quando o projeto acaba ou a gestão troca. Documentar à mão custa caro, então quase ninguém faz, e quem faz usa formatos diferentes.

O DocuData resolve isso de trás para frente. Em vez de pedir que alguém escreva documentação, ele lê o que o time já produz no dia a dia (o Kanban de tasks, atas e documentos de planning, review e retrospectiva, prints, PDFs, commits do GitHub) e monta os documentos sozinho. Quem mantém o trabalho atualizado no sistema recebe a documentação como consequência.

A partir da mesma fonte de dados, o sistema faz três coisas ao mesmo tempo:

| Frente | O que entrega |
|---|---|
| **Documentar** | Leitura de arquivos e commits, extração de conhecimento por IA e geração de documentos (status de sprint, retrospectiva, decisões, documento completo e outros) |
| **Acompanhar a saúde do projeto** | Painel com prazo contra escopo, métricas de fluxo, sprints, planejado contra entregue e acompanhamento por gerente |
| **Acompanhar a contribuição das pessoas** | Pontuação por sprint, avaliação semanal do gerente e ranking de performance (restrito) |

O sistema usa IA (Gemini, do Google) para ler arquivos, entender o que aconteceu e escrever os documentos. Tudo o que é extraído e gerado fica guardado por projeto e por sprint, e vai se acumulando: quanto mais o time alimenta, mais rico e preciso fica o que o sistema consegue escrever.

Dentro do próprio sistema existe também um guia de uso, aberto a todos na tela **Documentos**. Este documento, a Bíblia, é a camada mais completa e fica restrita a Gerente para cima.

---

### 1.2 Cargos: quem vê e faz o quê

O sistema tem quatro cargos, em ordem crescente de alcance: Operacional, Gerente, Líder e Owner.

| Cargo | Papel |
|---|---|
| **Operacional** | Vê apenas os projetos em que está vinculado e só as abas Sprints, Tasks, Tecnologias e Documentos |
| **Gerente** | Vê todos os projetos e os configura (contrato, modos de trabalho, equipe, GitHub, subárea). Não vê o ranking de performance |
| **Líder** | Tudo o que o Gerente faz, mais as telas restritas à liderança: Performance, Acompanhamento, Classificador, Pessoas e a meta de funcionalidades por sprint |
| **Owner** | Tudo o que o Líder faz, mais a gestão dos cargos das outras pessoas. É o único que promove ou rebaixa |

Cada cargo alcança tudo o que o anterior alcança.

#### O que cada cargo pode fazer

| Capacidade | Operacional | Gerente | Líder | Owner |
|---|---|---|---|---|
| Ver a lista de projetos | só os que está vinculado | todos | todos | todos |
| Abrir um projeto | só se vinculado | sim | sim | sim |
| Abas do projeto | Sprints, Tasks, Tecnologias, Documentos | todas | todas | todas |
| Mover tasks | só as próprias (e puxar ou devolver em modo Pull) | sim | sim | sim |
| Criar, editar e excluir tasks | não | sim | sim | sim |
| Aprovar ou rejeitar task pendente; aprovar funcionalidade | não | sim | sim | sim |
| Iniciar e excluir sprint, ver saúde da sprint | não | sim | sim | sim |
| Painel, Métricas e avaliação semanal do gerente | não | sim | sim | sim |
| Pontuação das pessoas | não | sim | sim | sim |
| Reclassificar ou revisar o nível de uma task | não | não | sim | sim |
| Tela de Performance | não | não | sim | sim |
| Acompanhamento dos projetos e meta por sprint | não | não | sim | sim |
| Classificador | não | não | sim | sim |
| Desfazer a confirmação de uma avaliação | não | não | sim | sim |
| Ver a lista de Pessoas | não | não | sim | sim |
| Alterar o cargo de alguém | não | não | não | sim |
| Configurações (chave de IA) e integração com GitHub | não | sim | sim | sim |
| Encaminhar projeto de Produto para Dados ou Dev | não | sim | sim | sim |
| Discovery: promover requisito, analisar reunião, ver transcrição | não | sim | sim | sim |
| Documentos "Guia" e "Contribuição" | sim | sim | sim | sim |
| Documentos restritos ("Bíblia" e "Performance") | não | sim | sim | sim |

Uma regra importante sobre mudança de cargo: quando o Owner altera o cargo de alguém, a interface mostra o cargo novo na hora, mas as permissões só passam a valer de fato no próximo login da pessoa (a sessão dura 8 horas). Se a mudança precisa valer já, peça para a pessoa sair e entrar de novo.

---

### 1.3 Login, cadastro e recuperação de senha

Quem não está logado só enxerga quatro telas: login, cadastro, "esqueci minha senha" e "redefinir senha". Qualquer outra tela leva de volta ao login.

#### Login

A pessoa entra com e-mail e senha. Se errar o e-mail ou a senha, a mensagem é sempre a mesma ("Email ou senha inválidos"), de propósito: assim ninguém consegue descobrir quais e-mails têm conta. A sessão dura 8 horas; depois disso é preciso entrar de novo. Se a sessão expirar com a aba aberta, a próxima ação leva automaticamente ao login, em vez de a tela parecer logada e nada funcionar.

#### Cadastro

A tela de cadastro tem dois caminhos:

- **Já sou operacional em algum projeto.** A tela lista os operacionais que um gerente já cadastrou em algum projeto e que ainda não têm conta. A pessoa escolhe o próprio nome e assume aquele cadastro. Se o gerente já tinha registrado um e-mail para ela, o e-mail digitado precisa ser o mesmo; se não tinha, o e-mail digitado fica gravado no cadastro. A conta usa o nome do operacional.
- **Sou novo.** A pessoa informa nome, e-mail e senha e cria a conta do zero.

Nos dois caminhos são pedidos o **usuário do GitHub** e o **e-mail do GitHub**. Eles são obrigatórios porque é isso que liga um commit à pessoa que o escreveu. O e-mail do GitHub fica separado do e-mail de login porque o Git usa o e-mail configurado na máquina de cada um, que nem sempre é o mesmo do login. Depois do cadastro, a pessoa já entra logada. A senha tem no mínimo 6 caracteres.

Todo mundo entra como **Operacional**. Não existe cadastro que crie Gerente, Líder ou Owner: a promoção é feita por um Owner na tela **Pessoas**.

Para evitar abuso, há limites de tentativas: poucos logins por minuto, e poucos cadastros e pedidos de recuperação por hora, por endereço de rede.

#### Esqueci minha senha

A pessoa informa o e-mail e a tela mostra sempre a mesma confirmação ("Se o e-mail existir, você vai receber um link em instantes"), exista conta ou não. Se existir, chega um e-mail com um link de redefinição, que vale por 30 minutos. Ao abrir o link, a pessoa digita a nova senha e volta ao login. Um link inválido ou vencido mostra "Link inválido".

---

### 1.4 Subáreas e navegação

Cada projeto pertence a uma subárea, e as subáreas mantêm listas, buscas, pastas de documentos e modelos de documento separados.

| Subárea | Situação | Para que serve |
|---|---|---|
| **Dados** | ativa na interface | Projetos de dados. É a subárea padrão dos projetos mais antigos |
| **Dev** | ativa na interface | Projetos de software. Mesmos recursos, mas com lista, busca, pasta de documentos e modelos próprios |
| **Produto** | só nos bastidores | Subárea do fluxo de Discovery. Um projeto de Produto não é trabalhado ali: ele é encaminhado para Dados ou Dev, levando todo o contexto acumulado |

Um projeto de Dados ou Dev pode trocar de subárea na aba Configurações do projeto. A troca só reclassifica o projeto: tasks, sprints, documentos e histórico continuam todos ligados a ele. A troca direta não leva para Produto.

#### A tela inicial

Ao entrar, a pessoa vê uma saudação pelo primeiro nome e escolhe a subárea, Dados ou Dev. Nessa tela não há menu lateral. Nas demais telas aparece um menu lateral e uma barra superior.

#### Barra superior e menu lateral

- A barra superior tem um campo **Buscar projetos ou tecnologias**, um botão para alternar entre Dados e Dev e o botão **+ Novo projeto**.
- O menu lateral mostra a identificação do sistema, os itens liberados para o cargo da pessoa e, embaixo, o cartão do usuário com o cargo e o botão **Sair**.

| Item do menu | Quem vê |
|---|---|
| Projetos | todos |
| Performance | Owner e Líder |
| Acompanhamento | Owner e Líder |
| Classificador | Owner e Líder |
| Avaliações | Owner, Líder e Gerente |
| Pessoas | Owner e Líder |
| Documentos | todos |
| Configurações | Owner, Líder e Gerente |

---

### 1.5 As telas globais

Telas que não pertencem a um projeto específico.

#### Lista de projetos

É a tela principal de cada subárea. No topo, três números: projetos **ativos**, **entregues** e os que **pedem atenção**. Abaixo, um cartão por projeto. O operacional só vê os projetos em que está vinculado e que estão ativos; Gerente, Líder e Owner veem todos.

A busca entre projetos serve para descobrir onde uma tecnologia já foi usada. Ela procura o termo na lista de tecnologias que o sistema extraiu dos arquivos e commits de cada projeto da subárea e devolve o projeto, o cliente, as sprints em que a tecnologia apareceu e um trecho de contexto. Não é uma busca de texto livre: só tecnologias.

#### Novo projeto

Formulário de criação, detalhado na seção 1.6.

#### Dashboard do projeto

Reúne as abas de trabalho do projeto (seção 1.6).

#### Acompanhamento

Visão da liderança sobre os projetos agrupados por gerente: meta da sprint, planejado, prazo e saúde de cada um. O agrupamento usa o e-mail do gerente configurado em cada projeto; projetos sem gerente aparecem em um grupo "Sem gerente". Restrito a Líder e Owner. Aceita as subáreas Dados e Dev.

#### Avaliações

Mostra as notas da avaliação semanal do gerente, por operacional e por sprint. Permite corrigir uma nota e mantém o histórico das correções. Corrigir uma nota atualiza o ranking. Visível para Gerente, Líder e Owner.

#### Classificador

Mostra como o classificador de nível de task se comporta em comparação com o tempo real que as tasks concluídas levaram. Leitura restrita a Líder e Owner. O funcionamento do classificador tem capítulo próprio.

#### Performance

Mostra a contribuição de cada pessoa nas várias dimensões de avaliação, por projeto, em janelas de sprint, quinzena ou mês. Uma dimensão sem dado aparece como indisponível e nunca como zero. Restrita a Líder e Owner.

#### Pessoas

Painel de quem tem acesso ao sistema, visível para Owner e Líder. Lista nome, e-mail, cargo, data de criação e os projetos de cada pessoa. O vínculo com projetos considera tanto os operacionais cadastrados nos projetos quanto o e-mail de gerente configurado neles; sem juntar as duas fontes, todo gerente pareceria não ter projeto.

Só o Owner altera cargos, e cada alteração fica registrada em um histórico de auditoria. Há uma proteção: ninguém muda o próprio cargo. Um Owner que queira deixar de ser Owner precisa antes promover outra pessoa.

#### Documentos

Reúne os documentos internos do sistema, em texto formatado, e permite baixar em um arquivo compactado tudo o que a pessoa pode abrir.

| Documento | Quem abre |
|---|---|
| Guia do DocuData | todos |
| Como sua contribuição é acompanhada | todos |
| Bíblia do DocuData | Gerente, Líder e Owner |
| Sistema de Acompanhamento de Performance | Gerente, Líder e Owner |

O controle é por documento: a lista só mostra o que a pessoa pode abrir, e o arquivo baixado respeita o mesmo filtro. Assim, um operacional nunca recebe um documento restrito.

#### Configurações

Configurações compartilhadas por toda a aplicação. Hoje existe uma só: o cadastro da chave de acesso ao Gemini, a IA que o sistema usa. A chave é única para o sistema inteiro (não há chave por projeto nem por subárea). A tela mostra se a chave está configurada ou não e permite alterá-la; por segurança, o sistema nunca exibe a chave inteira, só os quatro últimos caracteres. Sem chave cadastrada, qualquer recurso de IA avisa que é preciso configurá-la antes. Visível para Gerente, Líder e Owner.

---

### 1.6 Projetos

#### Criar um projeto

O formulário de novo projeto pede:

| Campo | Obrigatório | Observação |
|---|---|---|
| **Nome do projeto** | sim | |
| **Cliente** | sim | |
| **Squad** | não | Texto livre com os nomes da equipe. Aparece nos documentos exportados (se vazio, mostra um traço) |
| **Descrição** | não | Escopo em texto livre |

A subárea vem da tela em que a pessoa está (Dados ou Dev). Depois de criar, o sistema abre o dashboard do projeto.

O projeto já nasce com configurações padrão: modo de trabalho Atribuição, tolerância de desvio de 20 pontos percentuais, garantia de 30 dias, tipo de projeto padrão e não entregue.

#### As abas do projeto

O dashboard tem oito abas. A aba que abre primeiro é **Sprints**.

| Aba | Operacional vê? |
|---|---|
| Sprints | sim |
| Planejamento (escopo e funcionalidades) | não |
| Painel | não |
| Tasks (Kanban) | sim |
| Métricas | não |
| Tecnologias | sim |
| Documentos | sim |
| Configurações | não |

Cada aba é detalhada em seu capítulo. Aqui o foco é a aba Configurações e o contrato do projeto.

#### Aba Configurações do projeto

Na ordem em que as seções aparecem:

| Seção | O que faz |
|---|---|
| **Repositórios GitHub** | Conectar, desconectar, reconectar e reautorizar os repositórios do projeto (seção 1.8). Enquanto nenhum repositório estiver ativo, um aviso roxo leva a esta aba |
| **Lembretes por email** | Define o e-mail do gerente do projeto. Esse e-mail recebe os lembretes de sprint e também define quem é o "gerente" do projeto na tela Pessoas e no Acompanhamento. Removê-lo para os lembretes |
| **Status do projeto** | Marca o projeto como **Entregue**. Projetos entregues entram na contagem de "entregues" da lista |
| **Modos de Trabalho e de Avaliação** | Escolha entre Atribuição e Pull e ajustes do Pull (seção 1.7) |
| **Operacionais** | Equipe do projeto: adicionar, ativar ou desativar, remover do projeto ou excluir |
| **Subárea** | Mover o projeto entre Dados e Dev |
| **Zona perigosa** | Excluir o projeto, o que apaga ingestões, sprints e documentos. Irreversível |

#### Gerenciar a equipe (Operacionais)

Cada operacional do projeto tem nome, e-mail, papel livre (por exemplo Front, Back, Design), usuário do GitHub e e-mail do GitHub. Não pode haver dois operacionais com o mesmo nome no mesmo projeto.

Para não digitar a mesma pessoa duas vezes, o formulário oferece um atalho com as pessoas já cadastradas em outros projetos (e as contas ainda sem projeto). Isso importa porque o ranking identifica a pessoa pelo e-mail: a mesma pessoa com e-mails diferentes em dois projetos seria dividida em duas no ranking.

Existem três formas de tirar alguém da equipe, e a diferença importa:

- **Desativar** deixa a pessoa inativa e registra a data de saída. Reativar limpa a data.
- **Remover do projeto** é o caminho correto para quem saiu do projeto: a pessoa fica inativa com data de saída, as tasks que ela ainda não tinha concluído ficam sem responsável, e a pontuação e o histórico dela são preservados.
- **Excluir** apaga a pessoa definitivamente e leva junto toda a pontuação já travada dela. É irreversível, e a tela avisa para usar "Remover do projeto" quando a pessoa apenas saiu.

A conta de login de um operacional é ligada aos projetos pelo e-mail: o que faz o projeto aparecer para ela é o e-mail da conta ser igual ao e-mail do cadastro de operacional.

#### O contrato do projeto

O contrato não fica na aba Configurações, e sim no card **Tempo x Escopo** da aba Painel, pelo botão **Configurar datas** (ou **Editar**).

| Campo | Padrão | Significado |
|---|---|---|
| **Início do projeto** | vazio | Obrigatório no formulário |
| **Fim contratado** | vazio | Obrigatório no formulário |
| **Tolerância de desvio** | 20 pontos | Quantos pontos percentuais o prazo consumido pode passar do escopo concluído antes de o painel acusar desvio. Opcional no formulário |
| **Garantia** | 30 dias | Período de garantia pós-entrega. O formulário atual não expõe este campo |
| **Tipo de projeto** | padrão | Padrão ou consultoria com discovery (seção 1.7) |

O painel compara o percentual do prazo já consumido com o percentual do escopo concluído. Se o prazo avançou mais do que o escopo além da tolerância, aparece o alerta "Desvio de N pts acima da tolerância".

---

### 1.7 Modos de trabalho e tipo de projeto

#### Atribuição e Pull

Todo projeto trabalha em um de dois modos. O modo de avaliação da dimensão de entrega não é escolhido à parte: ele é sempre derivado do modo de trabalho.

| | **Atribuição** (padrão) | **Pull** (puxada) |
|---|---|---|
| Como a task chega à pessoa | O gerente define o responsável | A task entra numa fila, sem responsável. A pessoa **puxa** a task sozinha e ela vai direto para Em andamento |
| Definir responsável à mão | permitido | bloqueado: o sistema avisa que em Pull é preciso usar a fila de puxar |
| Avaliação da dimensão Entrega | por pontos atribuídos | por pontos relativos ao squad |
| Parâmetros extras | nenhum | **piso** (padrão 1) e **teto** (padrão 1,5), que definem a faixa da avaliação relativa. O formulário recomenda recalibrar depois da primeira sprint real |
| Tasks em andamento por pessoa | configurável | fixo em 1, sempre |
| Devolver à fila | não se aplica | o dono da task ou um Gerente+ pode devolver a task à fila. Se a task já estava travada automaticamente, a devolução gera a mesma penalidade de um travamento |
| Rótulos das métricas e perguntas da avaliação semanal | "Atribuídos" | "Puxados" |

#### Trocar de modo

Ajustar piso e teto é livre, mas trocar o modo em si exige a ação de **migrar de modo**, que também reclassifica as tasks existentes. Antes de confirmar, o sistema mostra uma prévia sem gravar nada, contando quantas tasks entram na fila, quantas mantêm o responsável e quantas ficam sem alteração.

Efeitos da migração:

- **Para Pull:** tasks planejadas perdem o responsável e entram na fila. Tasks em andamento e bloqueadas mantêm o responsável. Tasks concluídas não mudam.
- **De volta para Atribuição:** as tasks planejadas saem da fila, mas o responsável anterior não é recriado.
- Toda troca fica registrada em um histórico que não pode ser alterado, com quem trocou e quando, e a sprint em andamento é marcada como híbrida (parte dela correu em cada modo).
- A migração é uma reclassificação estrutural, não um movimento de Kanban: não conta como transição nem como reabertura de task.
- Ao migrar para Pull, o sistema envia um e-mail avisando todos os operacionais ativos do projeto e todos os gerentes e líderes.

Existe ainda uma ação à parte, **desvincular planejado**, que tira o responsável das tasks planejadas da sprint atual para abrir a fila sem migrar o projeto inteiro.

#### Tipo de projeto

O tipo de projeto, também chamado de arquétipo, pode ser **padrão** ou **consultoria com discovery**. Ele define quais pesos as dimensões de performance recebem no cálculo das pessoas daquele projeto. Os pesos em si estão no capítulo de pontuação.

O tipo também decide se a qualidade dos commits é avaliada: essa avaliação só acontece em projetos do tipo padrão (seção 1.8).

#### Chave de IA e conta Google

- A chave de IA não é por projeto: é uma só para o sistema, cadastrada em Configurações.
- A conta Google usada na exportação de documentos não é por projeto, e sim por subárea: Dados, Dev e Produto têm cada uma a sua conta e a sua pasta raiz no Drive.

---

### 1.8 Integrações

#### GitHub: como os commits chegam ao sistema

O sistema recebe os commits do projeto por meio de um aplicativo do GitHub instalado nos repositórios. Cada commit enviado ao repositório é lido pelo sistema, que extrai o conhecimento dele e o guarda no projeto, contando para a documentação e para a linha do tempo de tecnologias.

**Conectar repositórios** (aba Configurações do projeto, para Gerente+):

1. O gerente clica em **Selecionar repositórios**.
2. Se o aplicativo ainda não estiver instalado na conta do GitHub, o sistema leva o gerente à página de instalação do GitHub; se já estiver, vai direto à seleção.
3. Concluída a instalação, o GitHub devolve o gerente à aba Configurações do projeto. Se ele cancelar no GitHub, volta com um aviso de cancelamento.
4. O sistema lista os repositórios autorizados e o gerente escolhe quais pertencem ao projeto.
5. Ao confirmar, os vínculos são gravados. O pedido é validado por inteiro antes de gravar: se um repositório já estiver ativo em outro projeto, nada é gravado e o sistema informa qual projeto o está usando. **Um repositório pertence a um projeto de cada vez.**

A etapa de conexão tem prazo curto: a sessão de conexão vale 10 minutos.

Cada repositório aparece na tela em um de três estados:

- **Ativo:** recebendo commits.
- **Desconectado:** o gerente o desconectou; dá para reconectar.
- **Permissão revogada:** o GitHub retirou o acesso; é preciso reautorizar.

O sistema também reage a mudanças feitas no GitHub: se o aplicativo for suspenso ou removido, ou se repositórios forem retirados ou adicionados à instalação, os vínculos são desativados ou reativados automaticamente, e a renomeação de um repositório é acompanhada.

**O que acontece quando alguém faz um push:**

- Só valem pushes em branches (não exclusões de branch). O repositório precisa estar conectado e ativo em um projeto de uma subárea habilitada.
- Cada commit novo é lido e entra na ingestão do projeto. Commits já ingeridos não são processados duas vezes.
- A IA gera um resumo estruturado do commit a partir da mensagem, do autor, da data e das alterações. Mensagens e diferenças muito longas são cortadas antes de serem lidas.
- Ao terminar, o sistema marca o commit no próprio GitHub com um selo informando que ele foi incorporado ao contexto do projeto.

**Em que sprint o commit cai:** se a mensagem do commit tiver a marcação da sprint (por exemplo, indicando o número da sprint entre colchetes), ela vale. Caso contrário, vale a sprint atual do projeto.

**Avaliação de qualidade do commit** (somente projetos do tipo padrão): o sistema descobre de qual operacional é o commit comparando o autor com o usuário do GitHub, o e-mail do GitHub e o e-mail do cadastro, nessa ordem. Em seguida, a IA dá uma nota de 0 a 10 com uma frase de evidência. Se a mensagem do commit citar a task, a nota fica ligada a ela. Se essa etapa falhar, só vira um aviso interno: o contexto do commit já salvo nunca se perde.

É por isso que o cadastro pede usuário e e-mail do GitHub: sem eles, o sistema não consegue ligar o commit à pessoa.

**Caminho antigo.** Projetos que ainda não migraram para o aplicativo do GitHub podem usar um script instalado no repositório que envia os commits ao sistema (e um segundo script que envia a revisão diária de código, com achados classificados por severidade e confiança). Esse caminho continua funcionando enquanto os projetos migram, mas o caminho atual é o aplicativo do GitHub.

#### Exportação para Google Docs

Qualquer pessoa logada pode exportar um documento gerado para o Google Docs. O sistema devolve o link do documento criado.

O que acontece na exportação:

1. O sistema escolhe o modelo de documento pela subárea e pelo tipo. Planning, review e retrospectiva têm modelo próprio; os demais tipos usam um modelo geral. Dev e Produto procuram primeiro seus modelos específicos.
2. Organiza a pasta no Drive, criando o que faltar: pasta da subárea, pasta do projeto e, dentro dela, uma pasta por sprint ("Sprint N"). Documentos sem sprint vão para uma pasta "Cross-Sprint". O título segue o formato "Tipo do documento — Projeto — Sprint N" (ou "Projeto completo").
3. Copia o modelo para a pasta e preenche os dados do projeto (nome, cliente, tipo do documento, sprint, data, squad e, conforme o tipo, período, horas reais e estimadas, percepção do cliente, sinal de satisfação, pedidos fora de escopo e observações da retrospectiva).
4. Preenche as tabelas do planning (backlog, dependências, riscos e carry-over) e converte o texto do documento gerado para o Google Docs.

Os campos estruturados de planning, review e retrospectiva vêm do arquivo mais recente daquele tipo e sprint que o time alimentou no sistema.

Se algo falhar, o usuário vê uma mensagem fixa ("Não foi possível exportar o documento para o Google Docs"); os detalhes técnicos ficam só no registro interno do sistema.

#### E-mails e lembretes

O único canal de notificação do sistema é o e-mail. Não há avisos dentro da tela. Todos os e-mails seguem o mesmo visual, com o selo "DocuData · Lembrete".

| E-mail | Quando é enviado | Quem recebe |
|---|---|---|
| **Sprint sem planning** | 24 horas depois de a sprint ser criada e, depois, uma vez por dia enquanto não houver planning | E-mail do gerente do projeto |
| **Sprint sem review** | 5 dias depois de a sprint ser criada e, depois, uma vez por dia | E-mail do gerente do projeto |
| **Sprint sem retrospectiva** | 7 dias depois de a sprint ser criada e, depois, uma vez por dia. Conta tanto a retrospectiva enviada quanto a gerada pelo sistema | E-mail do gerente do projeto |
| **Task atribuída** | Quando uma task é atribuída a um operacional que tenha e-mail cadastrado | O operacional |
| **Task concluída** | Quando uma task é concluída | Todas as contas de Gerente e Líder |
| **Task pendente de aprovação** | Quando uma task entra em Pendente de aprovação | Todas as contas de Gerente e Líder |
| **Task rejeitada** | Quando o gerente rejeita, com o motivo | O operacional dono da task, se tiver e-mail |
| **Pedido de task extra** | Quando um operacional pede uma task extra | Todas as contas de Gerente e Líder |
| **Modo Pull ativado** | Ao migrar um projeto para Pull | Operacionais ativos do projeto, gerentes e líderes |
| **Esqueci minha senha** | Ao pedir a redefinição | A própria pessoa |

Como funcionam os lembretes de sprint:

- O sistema verifica a cada hora e só considera projetos com e-mail de gerente preenchido.
- Os prazos contam a partir da criação da sprint.
- Há no máximo um e-mail de cada tipo, por sprint, por dia, para ninguém ser inundado.
- Para parar os lembretes de um projeto, basta remover o e-mail do gerente na aba Configurações, em **Lembretes por email**.
- Uma falha no envio nunca derruba o sistema nem impede a ação em andamento.

Os e-mails de task e de modo Pull são "melhor esforço": mover a task ou migrar o modo vale mesmo que o e-mail não saia. As contas de Owner não estão nas listas de gerentes e líderes que recebem os e-mails de task.

#### Rotinas automáticas

O sistema executa quatro rotinas por conta própria, sem que ninguém precise acioná-las:

| Rotina | Frequência | O que faz |
|---|---|---|
| Lembretes de sprint | a cada hora | Envia os e-mails de planning, review e retrospectiva atrasados |
| Travamento automático | a cada 24 horas | Marca como travadas as tasks paradas (regra no capítulo de tasks e pontuação) |
| Classificação provisória | a cada 10 minutos | Reclassifica as tasks que ainda têm nível provisório (capítulo do classificador) |
| Recálculo diário do classificador | a cada 24 horas | Recalcula os parâmetros do classificador (capítulo do classificador) |

Gerentes, líderes e o Owner podem também disparar manualmente a verificação de lembretes e a de travamento, o que serve para testes.

---

### 1.9 Segurança e privacidade, em resumo

Os pontos que o usuário precisa conhecer:

- **Sessão:** vale 8 horas e depois exige novo login.
- **Senhas:** guardadas de forma protegida; nunca ficam legíveis para ninguém, nem para o Owner.
- **Chave de IA:** guardada criptografada e nunca exibida por inteiro.
- **Limites de tentativa:** login, cadastro, recuperação de senha e recursos de IA têm limites por endereço de rede, para evitar abuso.
- **Tamanho de arquivo:** o envio de arquivos tem um teto de 20 MB por requisição.
- **Auditoria:** o sistema registra quem fez o quê em três situações: acesso à tela de Performance, mudança de cargo de uma pessoa e encaminhamento de projeto de Produto.
- **Erros:** quando algo dá errado de forma inesperada, a tela mostra uma mensagem genérica com um código de referência. Esse código permite que quem mantém o sistema localize o problema; se precisar de ajuda, informe o código.
- **Dados:** tudo o que o sistema extrai e gera fica guardado por projeto e sprint, e some junto com o projeto se ele for excluído.


---

## Parte 2 — Escopo, funcionalidades, metas e acompanhamento

Esta parte explica como o DocuData registra **o que o projeto promete entregar**, como esse escopo se liga às sprints e às tasks, e como gerentes e líderes medem o andamento: o Painel de cada projeto, as metas por sprint e a tela de Acompanhamento. Também cobre a aba que mostra as tecnologias usadas no projeto.

Duas palavras aparecem o tempo todo e vale fixá-las. **Funcionalidade** é a entrega de alto nível que o cliente enxerga (por exemplo, "Tela de Login" ou "Relatório mensal"). **Task** é a unidade de trabalho do Kanban, feita por uma pessoa. Uma task pode apontar para uma funcionalidade, e é dessa ligação que nasce quase tudo o que está abaixo.

No menu do projeto, a aba de escopo aparece com o nome **Planejamento**.

---

### 2.1 Visão geral: o que é escopo no DocuData

O escopo do projeto é formado por poucas peças que conversam entre si.

| Conceito | Papel |
|---|---|
| Funcionalidade | Item de escopo, com prioridade, critérios de aceite, status e aprovação |
| Histórico de status | Registro de cada mudança de status e de aprovação de uma funcionalidade; alimenta o Painel |
| Vínculo com a sprint | Indica que uma funcionalidade está planejada para determinada sprint, junto com as tasks citadas na planning |
| Meta da sprint | Conjunto de funcionalidades que o líder se compromete a ver entregues na sprint, com histórico de mudanças |
| Contrato | Datas de início e fim contratadas e a tolerância de desvio; base do cálculo de Tempo × Escopo |
| Requisito de Discovery | Pré-escopo extraído de reuniões com o cliente; pode virar funcionalidade |

#### Quem vê o quê

| Tela | Operacional | Gerente | Líder / Owner |
|---|---|---|---|
| Aba Planejamento | Não vê | Vê e edita | Vê e edita |
| Aba Painel | Não vê | Vê | Vê |
| Aba Tecnologias | Vê | Vê | Vê |
| Aprovar ou desfazer aprovação de funcionalidade | Não | Sim | Sim |
| Tela de Acompanhamento e definição de meta | Não | Não | Só líder e owner |

O operacional enxerga apenas as abas de Sprints, Tasks, Tecnologias e Documentos do projeto.

---

### 2.2 Aba Planejamento: o escopo do projeto

A aba abre com um pequeno tutorial, mostra a contagem de funcionalidades, oferece dois caminhos para criar funcionalidades e lista tudo o que já existe, com um filtro por sprint.

#### 2.2.1 O que tem numa funcionalidade

| Campo | O que é |
|---|---|
| **ID funcional** | Código curto (F01, F02...). Se o gerente deixar em branco ao criar manualmente, a tela sugere o próximo número |
| **Título** | Nome da funcionalidade (obrigatório) |
| **Descrição** | Texto livre, opcional |
| **Critérios de aceite** | Lista do que precisa ser verdade para a funcionalidade ser considerada pronta. **Ao menos um critério é obrigatório**; linhas em branco são descartadas |
| **Prioridade** | Must, Should, Could ou Won't. Se nada for escolhido, vale Should |
| **Status** | Não iniciada, Em andamento, Em ajuste ou Concluída. Nasce como Não iniciada |
| **Responsável** | Texto livre, opcional |
| **Sprint alvo** | Texto livre, opcional (por exemplo, "3"). Alimenta o filtro da aba |
| **Aprovação** | Data e pessoa que aprovou, preenchidas pelo gerente (ver 2.6) |

Por que exigir critério de aceite: sem ele ninguém sabe dizer quando a funcionalidade acabou, e a aprovação do gerente perderia o sentido.

#### 2.2.2 Prioridade (Must, Should, Could, Won't)

| Prioridade | Cor | Significado |
|---|---|---|
| Must | Vermelho | Obrigatório para a entrega |
| Should | Amarelo | Importante, mas não bloqueia |
| Could | Roxo | Desejável se houver tempo |
| Won't | Cinza | Fora do escopo desta versão |

A prioridade serve para alinhar expectativa com o cliente e com o time, e ajuda na hora de escolher funcionalidades para a meta. Ela **não pesa em nenhum cálculo**: no Painel, na meta e no Acompanhamento todas as funcionalidades valem igual.

#### 2.2.3 Criar funcionalidade manualmente

O botão **+ Adicionar manualmente** abre um formulário com ID funcional, título, descrição, critérios de aceite, prioridade e responsável. É preciso informar o título e ao menos um critério. A funcionalidade nasce como Não iniciada.

#### 2.2.4 Criar com ajuda da IA: importar do contrato

O botão **+ Importar do contrato** lê um contrato (ou qualquer documento de escopo) e propõe uma lista de funcionalidades. Há duas formas de entrada:

- **Enviar arquivo**: PDF (com ou sem texto selecionável, inclusive escaneado), DOCX ou TXT, arrastando ou escolhendo o arquivo.
- **Colar texto**: o mínimo é de 20 caracteres.

O fluxo tem três passos:

1. **Analisar com IA.** O sistema lê o material e monta as propostas. **Nada é salvo nesta etapa.**
2. **Revisão.** Aparecem as funcionalidades propostas, todas marcadas, com ID, prioridade, título, descrição e critérios. O gerente desmarca o que não quer, e pode usar **Selecionar todas** e **Desmarcar todas**.
3. **Salvar as selecionadas.** Só o que ficou marcado é criado.

A IA age como um especialista em levantamento de requisitos. Para cada funcionalidade, ela sugere um código curto, título, descrição e prioridade, e escreve os critérios de aceite no formato **"Quando [situação], o sistema deve [comportamento]"**, que deixa o critério verificável.

Limites e comportamentos a conhecer:

- Textos muito longos são aproveitados só até um limite (cerca de 50 mil caracteres).
- Em PDF escaneado, o sistema usa a primeira página como imagem.
- A IA tenta duas vezes antes de desistir; se não conseguir extrair nada aproveitável, o sistema avisa que não foi possível montar a lista.
- Propostas que não vêm completas são descartadas sem aviso, e só o que é válido chega à revisão.
- Há um limite de chamadas de IA por minuto para proteger o custo; ao estourar, é só esperar um pouco.

#### 2.2.5 Lista, edição, exclusão e filtro

- **Resumo de status**: contadores por status no topo (Não iniciada, Em andamento, Em ajuste, Concluída).
- **Filtro por sprint**: mostra todas, só as sem sprint, ou as de uma sprint específica.
- **Cada linha** mostra código, título, prioridade e status. Se a funcionalidade está na meta de alguma sprint ainda aberta, aparece o selo **meta da sprint N**. Se está concluída, aparece o estado de aprovação (ver 2.6).
- **Editar** permite mudar todos os campos. Quando a funcionalidade já tem tasks, o campo de status fica bloqueado com a dica "O status vem das tasks" (ver 2.5).
- **Excluir** pede confirmação e é irreversível. Apaga também o histórico de status, os vínculos com sprints e a presença nas metas. As tasks continuam existindo, só deixam de apontar para a funcionalidade; no histórico da meta, ela aparece como "(funcionalidade removida)".

---

### 2.3 Preenchimento automático dos documentos de sprint

Os modais de planning, daily, review e retrospectiva podem ser preenchidos por IA a partir de material bruto: o gerente cola um texto ou envia um arquivo, e o sistema devolve os campos já organizados para ele revisar. **Nada é gravado nessa etapa.** O gerente confere, corrige e só então gera o documento.

O material pode ser PDF, DOCX, TXT ou imagem (PNG, JPEG, WEBP), além de texto digitado. Cada documento tem seu próprio conjunto de campos, e a regra comum é: **a IA extrai somente o que está explícito** e deixa em branco o que não aparece, sem inventar.

| Documento | O que a IA preenche |
|---|---|
| **Planning** | Objetivo da sprint, itens do backlog (com responsável, prazo e critério), horas disponíveis e estimadas, período, dependências do cliente (com prazo, consequência e confiança), riscos e itens que sobraram da sprint anterior (com causa raiz) |
| **Daily** | Data, o que foi feito, o que vem a seguir e impedimentos |
| **Review** | Observações, percepção do cliente (literal ou parafraseada, sem interpretar), sinal de satisfação, pedidos fora de escopo, itens planejados e se foram entregues (com motivo e causa raiz), percentual de itens prontos e itens da próxima sprint |
| **Retrospectiva** | O que funcionou, o que não funcionou, causas raiz com impacto (Baixo, Médio, Alto), até 2 ações de melhoria (com responsável e prazo) e se houve pedido fora de escopo |

O **sinal de satisfação** da review é sempre uma de seis opções fixas: elogio espontâneo; neutro ou sem sinal; reclamação pontual resolvida na própria review; reclamação não resolvida ao final; reclamação recorrente sobre o mesmo tema; ou cliente solicitou reunião de escalonamento.

As **causas raiz** usadas na review e na retrospectiva seguem sete categorias fixas:

1. Especificação incompleta na planning.
2. Dependência do cliente atrasada.
3. Pedido de escopo novo.
4. Estimativa equivocada.
5. Bloqueio técnico.
6. Ausência ou rotatividade de membro.
7. Outro.

#### 2.3.1 Planning com ligação às funcionalidades

No modal de planning há um passo extra. Depois de extrair as tasks do material, o sistema compara cada uma com as funcionalidades já cadastradas e **sugere a qual funcionalidade ela pertence**. Uma funcionalidade pode ter várias tasks, e uma task sem encaixe claro fica sem sugestão.

O gerente confirma ou corrige essas ligações. Ao gerar a planning, o sistema agrupa as tasks por funcionalidade e cria o vínculo entre a sprint e cada funcionalidade (ver 2.7). Tasks sem funcionalidade não geram vínculo.

Nada disso trava o fluxo: se o projeto não tem funcionalidades, ou se a IA não consegue correlacionar, as tasks simplesmente seguem sem ligação.

---

### 2.4 Discovery e requisitos

O Discovery é a etapa em que a subárea de Produto conversa com o cliente para entender o problema antes de existir um escopo fechado. O DocuData tem uma estrutura para isso: reuniões de Discovery alimentam uma lista de **requisitos**, cada um com evidência, status e histórico, e os requisitos validados podem ser promovidos a funcionalidades. Hoje essa parte funciona nos bastidores, alimentada por um agente externo de diagnóstico, e **ainda não tem tela própria** no sistema. Ela está em preparação, e por isso não é detalhada aqui.

---

### 2.5 Status da funcionalidade

Uma funcionalidade pode estar Não iniciada, Em andamento, Em ajuste ou Concluída. Existem **dois modos** de definir esse status, e o que decide é haver ou não tasks ligadas a ela.

#### 2.5.1 Funcionalidade com tasks: o status vem das tasks

O status é calculado sozinho a partir das tasks da funcionalidade. Tasks extras (trabalho concedido além do planejado) não entram na conta.

| Situação das tasks | Status da funcionalidade |
|---|---|
| Todas em **Planejado** | Não iniciada |
| Todas em **Concluída** | Concluída |
| Qualquer outra combinação | Em andamento |

O que isso significa na prática:

- O cálculo sempre vence. Nesse modo, o gerente não consegue mudar o status à mão, e a tela deixa o campo bloqueado.
- O status **Em ajuste** só existe para funcionalidades **sem tasks**; o cálculo automático nunca o produz.
- O status é recalculado toda vez que uma task é criada, movida ou alterada, ou quando uma sprint é excluída.

Por que assim: o status da funcionalidade deixa de ser opinião e passa a refletir o que o time realmente fez no Kanban.

Cada mudança automática é registrada no histórico, com o motivo "derivado das tasks", quem moveu a task e quanto tempo a funcionalidade ficou na fase anterior. Esse tempo alimenta as métricas de fluxo do Painel (2.10).

#### 2.5.2 Funcionalidade sem tasks: status manual

O gerente muda o status à mão, informando quem está mudando e o motivo. A mudança também entra no histórico.

#### 2.5.3 Concluída não é o mesmo que entregue

Uma funcionalidade Concluída ainda não está "entregue". Para valer como entregue ela precisa também da **aprovação do gerente**, explicada a seguir.

---

### 2.6 Aprovação de funcionalidade

Depois que uma funcionalidade chega a Concluída, o gerente (ou alguém acima dele) a **aprova**. A aprovação não é um status novo: é um carimbo com data e pessoa, registrado também no histórico.

#### Para aprovar

O sistema só deixa aprovar quando:

1. A funcionalidade está Concluída.
2. Ela ainda não está aprovada.
3. **Todas** as tasks dela, inclusive as extras, estão na coluna Concluída.

#### Para desfazer

O gerente pode desfazer a aprovação a qualquer momento. O histórico registra "desfeita pelo gerente".

#### Quando a aprovação cai sozinha

A aprovação é revogada automaticamente, com o motivo registrado, sempre que a funcionalidade deixa de estar pronta:

| Acontecimento | Motivo registrado |
|---|---|
| Entra uma task nova na funcionalidade, ou uma task é movida para ela | Task nova |
| Uma task da funcionalidade é reaberta | Task reaberta |
| O status é mudado à mão para algo diferente de Concluída | Status alterado |
| O status calculado sai de Concluída | Status derivado das tasks |

#### Na tela

Em funcionalidades concluídas, a aba Planejamento mostra um selo verde "Aprovada em DD/MM/AAAA por Nome", com botão para desfazer, ou um selo âmbar "Aguardando aprovação", com o botão **Aprovar**.

#### Por que isso importa

**Só funcionalidade aprovada conta.** Ela é a única que entra no "Escopo concluído" do Painel, na ideia de "entregue" da meta e na porcentagem de aprovadas do Acompanhamento. É o freio contra declarar vitória antes da hora.

---

### 2.7 Sprint e funcionalidades

#### 2.7.1 O vínculo entre sprint e funcionalidade

Cada vínculo diz "esta funcionalidade está planejada nesta sprint", guarda se ela está **Em andamento** ou **Concluída** naquela sprint e guarda as tasks citadas na planning, com o responsável de cada uma.

Os vínculos nascem de dois lugares: do modal de planning (2.3.1) e do botão **+ Adicionar funcionalidade** do Kanban de Sprint. Ao vincular uma funcionalidade que ainda estava Não iniciada, o sistema a promove para Em andamento.

O sistema também sugere, na próxima planning, as funcionalidades que ainda estão Em andamento no projeto.

#### 2.7.2 Janela "Status das Funcionalidades"

Depois que uma **Review** de sprint é enviada, abre-se automaticamente uma janela que lista as funcionalidades vinculadas àquela sprint. Para cada uma, o gerente escolhe **Em andamento** ou **Concluída**, com a orientação "marque o que foi concluído nesta sprint".

- **Salvar status** grava só o que mudou.
- **Pular** fecha sem salvar.
- Se a sprint não tem funcionalidades vinculadas, a janela avisa e orienta a usar o botão de Planning.

Marcar Concluída aqui **não aprova** a funcionalidade. Ela continua aguardando aprovação e não conta como entregue até o gerente aprovar na aba Planejamento.

#### 2.7.3 Kanban de Sprint, no Painel

É um quadro com três colunas, **Planejado**, **Em andamento** e **Concluído**, para acompanhar as funcionalidades de uma sprint.

- Um seletor escolhe a sprint; por padrão aparece a mais recente.
- Cada cartão mostra o título, uma barra de progresso e "X/Y tasks" (ou "sem tasks").
- Os cartões podem ser arrastados entre colunas.
- **+ Adicionar funcionalidade** vincula à sprint uma funcionalidade que ainda não esteja lá.

Como as colunas são preenchidas:

- Se a sprint tem funcionalidades vinculadas (o caminho normal, via planning), a coluna Planejado fica sempre vazia, e Em andamento e Concluído seguem o status do vínculo. Arrastar para Em andamento ou Concluído atualiza o vínculo; arrastar para Planejado não faz nada.
- Se a sprint não tem vínculos, o quadro usa um modo antigo: mostra as funcionalidades cuja sprint alvo coincide com o número da sprint, separadas pelo status delas.

---

### 2.8 Meta de funcionalidades por sprint

A **meta** é o conjunto de funcionalidades que o líder espera ver **entregues** (concluídas e aprovadas) até o fechamento da sprint. Ela é diferente do **planejado**, que é o que foi vinculado à sprint na planning. A tela de Acompanhamento mostra as duas coisas lado a lado e destaca as divergências: é aí que o líder enxerga se o time está planejando o que prometeu entregar.

#### 2.8.1 Quem define e onde

Somente **líder e owner** definem a meta. O caminho é a tela de Acompanhamento: expandir o projeto e clicar em **Definir meta**. Dentro do projeto, a aba Planejamento só exibe o selo "meta da sprint N", sem permitir edição.

A janela de definição funciona assim:

- Um seletor oferece a sprint atual (se ainda não fechada) e as próximas. Sem sprint aberta, aparece "Nenhuma sprint aberta para definir meta."
- A lista mostra as funcionalidades **ainda não entregues**. As que já estão na meta continuam visíveis para poderem ser retiradas.
- Para a sprint atual, cada funcionalidade mostra a porcentagem de tasks concluídas e o selo "planejada nesta sprint".
- O botão **Salvar meta** só habilita depois que a meta daquela sprint termina de carregar, para não gravar por cima dos dados de outra sprint.

#### 2.8.2 Regras da meta

- **A meta substitui a anterior**: o líder envia o conjunto final desejado, e o sistema calcula o que entrou e o que saiu.
- **Sprint fechada não aceita mudança.** A mensagem é "A sprint já foi fechada; a meta não pode mais mudar."
- Só podem **entrar** na meta funcionalidades do mesmo projeto da sprint e que ainda não foram entregues.
- Uma meta vazia é permitida: nesse caso o projeto aparece como "sem meta".
- Se duas pessoas alterarem a meta ao mesmo tempo, o sistema pede para recarregar e tentar de novo.

#### 2.8.3 Histórico de mudanças

Toda inclusão ou retirada fica registrada, com quem fez e quando, e não pode ser editada. Na tela de Acompanhamento, cada projeto tem o link **Histórico de mudanças da meta**, que lista "ação, funcionalidade, pessoa e data" da sprint atual. Funcionalidade excluída aparece como "(funcionalidade removida)". Sem registros, aparece "Nenhuma mudança registrada."

Hoje o Acompanhamento mostra a meta atual da sprint. A comparação entre a meta original e a meta final no fechamento da sprint está prevista, mas ainda não é exibida.

#### 2.8.4 Selos e resultado

| Onde | O que aparece | Regra |
|---|---|---|
| Aba Planejamento | Selo violeta **meta da sprint N** | Um por sprint ainda aberta que tem a funcionalidade na meta |
| Acompanhamento, coluna Meta | **N de M**, com uma barra por funcionalidade | N é quantas da meta foram entregues; a barra é cheia se aprovada, senão mostra a porcentagem de tasks concluídas |
| Acompanhamento, coluna Meta | **sem meta** | Nenhuma funcionalidade na meta |
| Acompanhamento, projeto expandido | Selo verde **aprovada** | Funcionalidade da meta já aprovada |
| Acompanhamento, projeto expandido | Selo âmbar **fora do planejamento** | Está na meta, mas não foi vinculada à sprint atual |
| Acompanhamento, projeto expandido | **Planejadas fora da meta** | Funcionalidades vinculadas à sprint atual que não estão na meta |

A **meta é batida** somente quando **100%** das funcionalidades dela estão entregues. Abaixo disso, não é batida, por mais próxima que esteja. Em sprint já fechada, uma funcionalidade só conta como entregue se foi aprovada até o fechamento.

---

### 2.9 Tela de Acompanhamento

A tela de **Acompanhamento** dá ao líder uma visão de todos os projetos de uma subárea, agrupados por gerente. Aparece no menu como **Acompanhamento**, é visível só para **líder e owner**, e os demais cargos veem a mensagem "Acesso restrito a Líder e Owner."

#### 2.9.1 Como a tela é organizada

- **Seletor Dados / Dev** no topo, para alternar a subárea.
- **Três contadores**: Projetos, Em risco e Metas batidas ("X de Y").
- **Um cartão por gerente**, em ordem alfabética, com o grupo "Sem gerente" por último. O cabeçalho resume: "N projetos, K em risco, metas batidas X de Y, P% das funcionalidades aprovadas".
- **Uma linha por projeto**, em ordem alfabética, com as colunas **Meta**, **Planejado**, **Prazo × escopo** e **Saúde**, mais o selo **em risco** quando houver, com os motivos.
- Cada linha **expande** para mostrar as funcionalidades da meta, as planejadas fora da meta, o resumo da última sprint fechada, o botão **Definir meta** e o histórico de mudanças.

O gerente de cada projeto é identificado pelo e-mail cadastrado no projeto. Sem e-mail, ou sem pessoa correspondente, aparece o e-mail ou "Sem gerente".

#### 2.9.2 Quais sprints a tela considera

| Papel | Regra |
|---|---|
| **Sprint atual** | A de maior número entre as que já começaram. Pode já estar fechada |
| **Próximas** | As que ainda não começaram |
| **Última fechada** | A de maior número entre as que tiveram a avaliação concluída |

#### 2.9.3 Os indicadores

**Meta (sprint atual)**

Mostra quantas funcionalidades da meta já foram entregues, no formato "N de M", e a porcentagem de tasks concluídas de cada uma. Essa porcentagem considera só as tasks não extras. A funcionalidade sem tasks fica sem porcentagem.

**Planejado (sprint atual)**

- Quantas funcionalidades estão vinculadas à sprint e quantas dessas já foram entregues.
- **SPI da sprint**: pontos concluídos divididos pelo previsto da sprint. O previsto é a "foto" das tasks no início da sprint, mais as que surgiram depois; tasks extras ficam de fora. É a mesma regra explicada na parte de performance. Um SPI próximo de 1 indica que o que foi previsto foi entregue; abaixo disso, entregou-se menos do que o previsto.

**Prazo × escopo**

Reaproveita o cálculo do Painel (ver 2.10.1) e mostra algo como "X% do prazo, Y% entregue". Sem datas de contrato, mostra "sem datas do contrato".

**Saúde (do projeto inteiro, não da sprint)**

| Indicador | O que mostra |
|---|---|
| **Tasks travadas** | Quantas tasks estão travadas automaticamente por falta de movimento e ainda não foram concluídas |
| **WIP** | Quantas funcionalidades estão Em andamento agora |
| **85% em até (horas)** | Tempo em que 85% das tasks concluídas nos últimos 30 dias foram entregues. Mede o ritmo recente do time |

**Última sprint fechada**

O resumo mostra a meta (quantas foram entregues e se foi batida) e o SPI daquela sprint, no formato "Última sprint fechada (SN): meta X de Y, SPI Z".

**Projeto em risco**

O projeto ganha o selo **em risco** se **qualquer** uma destas três regras disparar. O selo mostra o texto de cada regra que disparou.

| Regra | Condição | Texto no selo |
|---|---|---|
| Prazo à frente do escopo | O desvio de Tempo × Escopo passou da tolerância (2.10.1) | "prazo à frente do escopo" |
| Meta fraca | A última sprint fechada tinha meta e menos de 50% dela foi entregue | "meta da última sprint abaixo de 50%" |
| SPI baixo | O SPI da última sprint fechada ficou abaixo de 0,7 | "SPI da última sprint abaixo de 0,7" |

Sem sprint fechada ainda, só a primeira regra pode disparar.

**Resumo do gerente**

| Campo | O que significa |
|---|---|
| Projetos | Quantidade de projetos do gerente |
| Em risco | Projetos com ao menos um motivo de risco |
| Metas batidas | Entre os projetos cuja última sprint fechada tinha meta, quantos a bateram |
| Funcionalidades aprovadas | Aprovadas divididas pelo total de funcionalidades de todos os projetos do gerente |

Os contadores do topo somam os dados de todos os gerentes.

O Acompanhamento olha apenas a **última sprint fechada**. Um histórico mais longo de metas e uma visão por pessoa estão previstos, mas ainda não existem nesta tela.

---

### 2.10 Aba Painel

O Painel é a visão de saúde do projeto para o gerente e o líder. Reúne quatro blocos de indicadores, o Kanban de Sprint (2.7.3) e dois cartões de pontuação, o Extrato de pontos e a Elegibilidade, que são explicados na parte de performance.

#### 2.10.1 Tempo × Escopo

Compara quanto do prazo do contrato já passou com quanto do escopo já foi entregue. Se o prazo anda mais rápido que o escopo, o projeto está atrasado.

Os dados do contrato são editados no próprio card, pelo botão **Editar**, com os campos **Início do projeto**, **Fim contratado**, **Tolerância (pontos)** e **Arquétipo**. As duas datas são obrigatórias; a tolerância é opcional e deve ser um número inteiro, zero ou maior. O arquétipo é o tipo do projeto: padrão ou consultoria e Discovery.

Como é calculado:

- **% do prazo consumido**: dias desde o início divididos pelo total de dias do contrato, até no máximo 100%.
- **% do escopo concluído**: funcionalidades **concluídas e aprovadas** divididas pelo total de funcionalidades. Todas pesam igual, e a prioridade não pondera.
- **Desvio**: % do prazo menos % do escopo, em pontos percentuais.

Quando o desvio passa da **tolerância**, o card mostra, em âmbar, "Desvio de X pts acima da tolerância". Caso contrário, mostra "Prazo e escopo dentro da tolerância." Sem a tolerância preenchida no projeto, vale zero. Quando o escopo está à frente do prazo, o desvio é negativo e nunca gera alerta. Sem as datas do contrato, o card mostra "Configurar datas".

#### 2.10.2 Itens em atenção

Lista as funcionalidades **paradas**: as que estão Em andamento e não tiveram nenhum movimento há **mais de 7 dias**. Conta como movimento qualquer mudança de uma task da funcionalidade; se não houver, vale a última mudança de status e, por fim, a data de criação.

O card mostra quantas funcionalidades estão paradas (verde se nenhuma, vermelho se houver) e a lista "título, N dias".

Não existe marcação manual de "travada" para funcionalidades. A palavra do card significa **sem movimento**, e não tem relação com o bloqueio de tasks do Kanban.

#### 2.10.3 Métricas de fluxo

Medem o ritmo de entrega das funcionalidades.

| Métrica | O que mostra |
|---|---|
| **WIP agora** | Quantas funcionalidades estão em andamento ou em ajuste neste momento |
| **Cycle time** | Quanto tempo uma funcionalidade levou, em dias, desde que **entrou em andamento pela primeira vez** até a **última vez em que foi concluída**. Só vale para funcionalidades concluídas |
| **Throughput por semana** | Funcionalidades concluídas divididas pelas semanas de vida do projeto (no mínimo 1 semana) |
| **Mediana** | O tempo típico: metade das funcionalidades leva menos que isso |
| **85% em até** | O tempo dentro do qual 85% das funcionalidades foram concluídas. Serve como previsão realista de prazo |

Sem nenhuma funcionalidade concluída, o card mostra "Nenhuma funcionalidade concluída, cycle time indisponível". Nestas métricas, "concluída" **não exige aprovação**, ao contrário do cálculo de Tempo × Escopo.

#### 2.10.4 Tempo por fase e eficiência de fluxo

**Tempo por fase** mostra onde as funcionalidades passam mais tempo. Para cada fase (Não iniciada, Em andamento, Em ajuste, Concluída), a tela exibe "média X dias, 85% em até Y dias". Clicando na fase, abre a lista "funcionalidade, N dias". Só entram fases de onde a funcionalidade **já saiu**: o tempo da fase em que ela está agora não é contado. É assim que se enxerga o gargalo, por exemplo uma fase de ajuste que nunca acaba.

**Eficiência de fluxo** é a porcentagem do tempo de vida da funcionalidade em que ela esteve de fato **em andamento**, e não parada entre etapas. O número do projeto é a média entre as funcionalidades, e a tela o mostra com uma barra de progresso. Uma funcionalidade que começou no dia em que foi criada e terminou sem nenhuma espera teria 100%. Funcionalidades que nunca saíram do início entram na média com 0%.

#### 2.10.5 Resumo dos limiares do Painel

| Item | Regra |
|---|---|
| Desvio de Tempo × Escopo | Alerta quando o prazo consumido passa o escopo aprovado em mais pontos que a tolerância |
| Funcionalidade parada | Em andamento e mais de 7 dias sem movimento |
| Throughput | Considera no mínimo 1 semana |
| Percentis | Mediana e 85%; com uma única amostra, o próprio valor |

---

### 2.11 Aba Tecnologias

Visível para todos os cargos, inclusive operacional. Mostra **quais tecnologias o projeto usa e como isso mudou ao longo das sprints**, sem que ninguém precise manter essa lista à mão.

#### 2.11.1 De onde vêm as tecnologias

O sistema colhe as tecnologias de tudo o que foi registrado no projeto: arquivos enviados e commits do repositório. Nos commits, a IA também identifica tecnologias que foram **removidas**, mas apenas quando a remoção completa fica explícita nas mudanças; na dúvida, não registra nada.

#### 2.11.2 Regras da linha do tempo

- A comparação ignora maiúsculas e minúsculas, e vale a grafia da primeira vez em que a tecnologia apareceu.
- **Em uso atualmente**: as tecnologias citadas na sprint mais recente, em ordem alfabética.
- **Introduzida em**: a primeira sprint em que a tecnologia apareceu.
- **Abandonada em**: a sprint em que houve remoção explícita.
- **Regra de abandono**: só se considera abandono com remoção explícita. Não ser mencionada em sprints recentes não significa que a tecnologia foi abandonada.
- A lista é ordenada pela sprint de introdução e, em empate, pelo nome.

#### 2.11.3 O que a pessoa vê

Sem dados, a tela mostra "Nenhuma tecnologia identificada ainda...". Com dados, aparecem dois cartões: **Em uso atualmente**, com as tecnologias em destaque verde, e **Histórico**, uma tabela com Tecnologia, Introduzida em, Abandonada em e Status.


---

## Parte 3 — Tasks, Kanban e Classificador

Esta parte conta o que acontece com uma task desde o momento em que o gerente a cria até o momento em que ela vira dado de aprendizado do classificador. Cobre a task em si, o Kanban, os modos de trabalho, bloqueios e travamento, o pedido de mais trabalho, a entrada de commits e, com mais profundidade, o classificador que define o nível de dificuldade de cada task.

Um lembrete de vocabulário: "operacional" é a pessoa que executa o trabalho, "gerente" é quem planeja e avalia, e "líder" é quem acompanha tudo (o owner tem os mesmos poderes do líder nesta parte).

---

### 3.1 A task: o que é, nível de dificuldade e ciclo de vida

#### 3.1.1 O que é uma task

Uma task é a unidade de trabalho de um projeto. Ela pertence a um projeto, normalmente a uma sprint e a uma funcionalidade do Escopo, e tem no máximo um responsável. Uma task sem responsável está "sem dono": fica na fila, no caso do modo Pull (seção 3.3).

O que a task guarda, em linguagem de produto:

- **Título** (obrigatório) e **descrição** (opcional, mas importante: é com ela que o classificador entende o tamanho do trabalho).
- **Nível de dificuldade**, na régua de 1, 2, 3 e 5.
- **Coluna do Kanban**: Planejado, Em andamento, Pendente de aprovação ou Concluída.
- **Responsável**, **sprint** e **funcionalidade**.
- **Checklist**, que funciona como o critério de pronto (Definition of Done).
- **Opção "requer aprovação"**: quando ligada, a task não vai direto a Concluída, passa antes pelo gerente.
- **Bloqueio**, com motivo, tipo e quem resolveu.
- **Marcas de previsto**: se a task já estava na sprint quando ela começou, se surgiu depois, ou se é uma task extra.
- **Contador de reaberturas**: quantas vezes a task saiu de Concluída para voltar ao trabalho.
- **Relógio de travamento**: o ponto de partida da contagem de tempo parado (seção 3.5).
- **Nível travado**: o momento em que o nível foi fixado (seção 3.8).

#### 3.1.2 O nível de dificuldade: a régua

Os pontos de uma task são só o **nível de dificuldade**. Não existe orçamento de pontos nem total de pontos do projeto. A régua é única para todos:

| Nível | Rótulo |
|---|---|
| 1 | simples |
| 2 | moderada |
| 3 | complexa |
| 5 | muito complexa |

Regras:

- Só esses quatro valores existem.
- **O gerente não digita o nível.** Quem define é o classificador, a partir do que está escrito na task. Na tela, o nível aparece como uma etiqueta com o número de pontos e a explicação "definido pelo classificador".
- Task antiga, de antes da régua, pode ter pontos fora dela. Quando é reaberta, o valor é convertido: 1 ou menos vira 1; 2 vira 2; 3 ou 4 viram 3; 5 ou mais vira 5. O valor original fica guardado.
- O nível é usado no fechamento da sprint (Entrega) e no previsto da sprint. O previsto é a soma dos níveis das tasks que estavam na sprint quando ela começou, mais as que surgiram depois. Tasks extras ficam de fora.

#### 3.1.3 Quem pode fazer o quê

| Ação | Quem |
|---|---|
| Criar task | Gerente e líder |
| Ver as tasks de um projeto | Quem tem acesso ao projeto |
| Mover a task de coluna e marcar itens do checklist | Qualquer pessoa logada, com as regras de cada coluna |
| Editar título, descrição, responsável, sprint, funcionalidade, bloqueio e aprovação | Gerente e líder |
| Excluir task | Gerente e líder |

O operacional só consegue mexer em quatro coisas: a coluna da task, o checklist, e o autor e o motivo do movimento. Qualquer outra alteração é recusada.

#### 3.1.4 Criação

Ao criar uma task, o sistema faz, em ordem:

1. Confere se o projeto existe. Em projeto de modo Pull, não é permitido definir responsável na criação, porque a pessoa se atribui puxando da fila.
2. Confere se responsável, funcionalidade e sprint realmente pertencem ao projeto.
3. Chama o classificador. Se faltar informação na task, a criação é recusada e a tela lista as perguntas que o gerente precisa responder. Se o classificador estiver fora do ar, a task é criada com um **nível provisório** (seção 3.8.7).
4. Se a sprint já começou, liga o relógio de travamento da task.
5. Aplica as marcas de previsto: se a sprint já começou e a task não é extra, ela entra como "surgiu na sprint". Se a sprint ainda não começou, ela entrará na foto do previsto quando a sprint iniciar.
6. Salva a task, o histórico da classificação e o material que permite ao classificador encontrar tasks parecidas no futuro.
7. Se a sprint já começou ou a task nasce em andamento, o nível é travado na hora.
8. Se a funcionalidade estava aprovada, a aprovação é revogada ("task nova") e o status da funcionalidade é recalculado.
9. Se há responsável, ele recebe um e-mail de atribuição.

#### 3.1.5 Edição

A edição e o movimento entre colunas seguem o mesmo caminho. O que vale a pena saber:

- Trocar a task de sprint refaz as marcas de previsto e reavalia o relógio de travamento.
- Trocar o responsável fica registrado no histórico e avisa o novo responsável por e-mail. Em modo Pull isso é proibido.
- Editar título, descrição ou o texto dos itens do checklist de uma task cujo nível ainda não foi travado manda a classificação de volta para revisão do líder, com o motivo "texto editado após a classificação". Marcar um item como feito não conta como edição.
- Mover a task para uma coluna de trabalho ou concluí-la trava o nível.
- Mudar a funcionalidade da task revoga a aprovação anterior e recalcula o status das funcionalidades envolvidas.

#### 3.1.6 Exclusão

Gerente e líder podem apagar uma task, o que também apaga o histórico dela. A exclusão é bloqueada se a Avaliação Semanal daquela sprint já foi confirmada, porque a pontuação já foi travada. Depois de apagar, o status da funcionalidade é recalculado.

#### 3.1.7 Responsáveis

Cada task tem um responsável. "Operacional" é um cadastro por projeto, com nome, e-mail, login do GitHub e datas de entrada e saída. A pessoa que faz login é ligada ao operacional pelo e-mail. A atribuição dispara um e-mail para o operacional.

#### 3.1.8 Checklist como critério de pronto

O checklist é uma lista de itens que o operacional vai marcando, e funciona como o Definition of Done:

- **Bloqueia a conclusão.** Mover para Concluída ou para Pendente de aprovação com algum item desmarcado é recusado, com a mensagem de quantos itens faltam.
- Checklist vazio não bloqueia nada.
- Para o classificador, o checklist faz parte do texto da task e conta para a suficiência: basta descrição preenchida ou ao menos dois itens de checklist.
- O card mostra o progresso (por exemplo, 3 de 5) e o operacional marca os itens direto na tela de visualização da task.

#### 3.1.9 Pronto para começar

Existe também uma regra de entrada: uma task sem sprint não pode ir para Em andamento. O sistema pede que você associe a task a uma sprint antes, porque sem sprint não há a quem creditar o trabalho no fechamento da semana.

---

### 3.2 O Kanban

A aba **Tasks** do projeto mostra o quadro Kanban.

#### 3.2.1 Colunas

| Coluna | Observação |
|---|---|
| **Planejado** | Também é a "fila" quando o projeto está em modo Pull e a task não tem dono |
| **Em andamento** | Sujeita ao limite de trabalho em andamento (WIP) |
| **Pendente de aprovação** | Task esperando o gerente aprovar ou rejeitar |
| **Concluída** | Mostra as 4 mais recentes e um botão **+ N tasks concluídas** para ver o resto |

O quadro pode ser filtrado por sprint (a última por padrão), por operacional e por funcionalidade. O botão **+ Nova task** só aparece para quem não é operacional.

#### 3.2.2 O que é permitido

Não existe uma lista fechada de caminhos: qualquer coluna pode ir para qualquer outra, desde que as regras abaixo sejam respeitadas.

| Regra | Efeito |
|---|---|
| Saída de Pendente de aprovação | Só pelo gerente ou líder, aprovando (vai a Concluída) ou rejeitando (volta a Planejado) |
| Task que requer aprovação | Não pode ir direto a Concluída: precisa passar por Pendente de aprovação |
| Pronto para começar | Sem sprint, a task não vai para Em andamento |
| Critério de pronto | Checklist incompleto bloqueia Concluída e Pendente de aprovação |
| Limite de WIP | Se o limite foi atingido, a task não entra em Em andamento |
| Reabertura | Só a saída de Concluída de volta para Em andamento conta como reabertura |

Na tela, arrastar um card abre uma janela de confirmação antes de qualquer mudança. Cancelar não deixa rastro. O operacional não consegue arrastar uma task que está em Pendente de aprovação ("só o gerente ou líder pode aprová-la ou rejeitá-la"). Quando um operacional conclui uma task, o sistema abre um diálogo pedindo a opinião dele sobre o nível (seção 3.8.6).

#### 3.2.3 Fluxo típico

- Planejado vai para Em andamento (arrastando ou puxando da fila).
- De Em andamento, a task vai a Concluída quando o checklist está completo.
- Se a task requer aprovação, vai a Pendente de aprovação. O gerente então aprova (Concluída) ou rejeita (volta a Planejado, sem dono).
- Uma task Concluída pode ser reaberta, com motivo opcional, e volta a Em andamento. Isso conta como reabertura.

#### 3.2.4 O que acontece ao mover

Toda mudança de coluna, responsável ou sprint fica registrada no histórico da task, com a duração da fase anterior. Além disso:

- **Ao concluir:** o sistema registra a task como exemplo de aprendizado do classificador, atualiza a saúde da sprint e, se quem concluiu foi um operacional, avisa gerentes e líderes por e-mail.
- **Ao ir para Pendente de aprovação:** gerentes e líderes recebem e-mail.
- **Ao entrar em andamento, em aprovação ou em concluída:** o nível da task é travado.
- **Ao sair de Concluída (reabertura):** o contador de reaberturas sobe, o evento alimenta a dimensão Qualidade, pontos antigos fora da régua são convertidos e a aprovação da funcionalidade é revogada ("task reaberta"). Se a sprint de origem já fechou, o evento de Qualidade é contado na sprint ativa.
- **Sempre:** o status das funcionalidades afetadas é recalculado, e o movimento entra no histórico da sprint como uma ingestão (seção 3.5.5).

#### 3.2.5 Aprovação

- **Quem entra:** a task marcada como "requer aprovação", quando o operacional declara o trabalho pronto. O checklist é conferido nessa entrada.
- **Aprovar** (gerente ou líder): a task vai a Concluída, e o aprendizado do classificador e a saúde da sprint são atualizados. O checklist não é conferido de novo.
- **Rejeitar** (gerente ou líder, com motivo obrigatório): a task volta a Planejado, **perde o responsável** e vai para o fim da fila. O relógio de travamento é zerado, e a rejeição não gera penalidade de travamento, porque o relógio já estava parado desde a entrada em Pendente de aprovação. O operacional recebe um e-mail com o motivo.
- O relógio de travamento fica desligado enquanto a task está em Pendente de aprovação ou Concluída.

#### 3.2.6 Sugestões da IA para concluir

Quando um review de sprint é ingerido, o sistema compara as tarefas citadas nele com as tasks ainda não concluídas da sprint, por semelhança de texto. Quando encontra uma correspondência forte, cria uma sugestão de mover aquela task para Concluída (no máximo uma pendente por task).

A tela mostra um banner com as sugestões. Aceitar uma sugestão passa pelas mesmas regras de qualquer movimento: critério de pronto, limite de WIP e demais travas valem. Se o movimento falhar, a sugestão continua pendente.

#### 3.2.7 Outros elementos do card

Etiquetas que podem aparecer no card:

- o nível de dificuldade;
- **+ extra**, para task extra;
- **Bloqueada** ou **Aguardando cliente**;
- **Travada**, em amarelo, quando o alerta de travamento está ativo e não foi suprimido pelo gerente.

A tela de edição tem a seção de bloqueio, o botão de suprimir o alerta de travamento, aprovação e rejeição, e o histórico de movimentos com a duração em cada fase.

E-mails disparados pelo Kanban: atribuição, conclusão por operacional, pendente de aprovação, rejeição e pedido de task extra. O envio é feito na melhor das hipóteses: a ação vale mesmo que o e-mail falhe. Os destinatários "gerentes e líderes" são todas as pessoas com esses cargos, sem filtro por projeto.

---

### 3.3 Modos de trabalho: Atribuição e Pull, e limite de WIP

#### 3.3.1 Os dois modos

Cada projeto trabalha em um de dois modos.

| | **Atribuição** | **Pull** |
|---|---|---|
| Quem escolhe o responsável | O gerente atribui | A pessoa puxa a task da fila |
| Atribuir responsável a uma task | Permitido (gerente e líder) | Proibido |
| Fila | Não existe | Tasks em Planejado sem dono, em ordem de fila |
| Limite de WIP por pessoa | Configurável (sem limite por padrão) | Sempre 1 |
| Avaliação de Entrega | Pontos atribuídos | Pontos relativos ao time, com piso de 1 e teto de 1,5 |

Atribuição é o modo padrão. Trocar de modo não é uma simples edição do projeto: é um fluxo próprio de migração, que reclassifica as tasks existentes.

#### 3.3.2 Puxar e devolver

Em modo Pull, a pessoa se atribui a uma task da fila com o botão **Puxar esta task**. As regras:

1. A task precisa estar na fila: sem responsável e em Planejado.
2. O projeto precisa estar em modo Pull.
3. A pessoa precisa estar vinculada ao projeto como operacional.
4. O limite de WIP precisa permitir.
5. Se duas pessoas tentam puxar a mesma task ao mesmo tempo, só a primeira consegue. A outra recebe a informação de que a task já foi puxada.

Ao puxar, a pessoa vira a responsável, a task vai para Em andamento, o relógio de travamento começa e o nível é travado.

O botão **Devolver à fila** permite ao dono da task (ou ao gerente e líder) colocá-la de volta na fila, sem responsável, no fim da fila. Não vale para task em Pendente de aprovação: nesse caso, o caminho é aprovar ou rejeitar. Se a task já tinha sido marcada como travada, a devolução gera uma penalidade igual aos pontos da task, que aparece no extrato da pessoa. Quem devolve antes de travar não é punido.

Duas decisões de produto: puxar e devolver são movimentos da fila, e por isso não entram no histórico de movimentos nem no histórico da sprint. E, para medir tempo de trabalho, o início de uma task puxada é o momento do puxar, não o da criação, para que a espera na fila não conte como trabalho.

#### 3.3.3 Limite de WIP

O WIP é o limite de tasks em andamento ao mesmo tempo. Há dois limites possíveis, ambos **sem limite por padrão**:

| Limite | Significado |
|---|---|
| **Por coluna Em andamento** | Máximo de tasks em andamento no projeto inteiro |
| **Por pessoa** | Máximo de tasks em andamento por operacional |

A checagem só age quando a task vai entrar em Em andamento, e a contagem é por projeto, não por sprint. Quando o limite estoura, o movimento é recusado com a mensagem do limite atingido. Gerente e líder configuram os limites. Em modo Pull, o limite por pessoa é sempre 1, independentemente do que for configurado.

---

### 3.4 Bloqueios, dependência do cliente e "entrega sem dado"

#### 3.4.1 Duas marcas de bloqueio

- **Bloqueio visual:** o card fica vermelho e mostra **Bloqueada** ou **Aguardando cliente**, com o motivo. A mudança fica no histórico da task.
- **Bloqueio que conta para Autonomia:** só gerente e líder marcam. Registra quando foi marcado, por quem, o tipo e, ao final, quem resolveu. O operacional não pode mexer nesses campos.

#### 3.4.2 Bloqueio interno

- Ao marcar, o sistema registra quando e por quem. O tipo padrão é interno.
- Ao desmarcar, é obrigatório informar quem resolveu: o operacional ou o gerente. Sem isso, a mudança é recusada.
- Cada resolução alimenta a dimensão Autonomia: o total de bloqueios e quantos foram resolvidos pelo próprio operacional. Se a sprint de origem já fechou, o evento vai para a sprint ativa.

#### 3.4.3 Dependência do cliente

Task parada esperando o cliente é o único caso em que o atraso externo não pode ser culpa do operacional. Marcar a task como **Aguardando cliente** tem estes efeitos:

- **Pausa o relógio de travamento.** O verificador diário ignora a task enquanto ela estiver nesse estado.
- **Limpa o alerta atual** e dispensa os travamentos ainda não dispensados da task, que deixam de penalizar a Entrega.
- **Ao desbloquear**, não é preciso dizer quem resolveu, e o desbloqueio não conta para Autonomia. O prazo recomeça do zero.
- **Trocar o tipo do bloqueio** com a task já bloqueada fecha o trecho antigo e abre outro na mesma hora, para que o tempo limpo desconte só o trecho de cliente.
- **No fechamento da sprint**, a task esperando o cliente sai dos pontos alocados, para não zerar a Entrega de ninguém.
- **No classificador**, o tempo parado por causa do cliente é descontado do tempo que a task levou de verdade.

#### 3.4.4 "Entrega sem dado"

No fechamento de sprints em modo Pull:

- Se não há nenhuma task regular que poderia ter sido puxada (só tasks extras, só tasks esperando o cliente, ou sprint vazia), a Entrega fica **sem dado para todos**, e não zero.
- Quem só tinha task esperando o cliente e não concluiu nada fica isento e sai da média do time.
- Nos demais casos, a Entrega usa como referência a média de pontos concluídos pelos vinculados ao projeto, com o piso de 1 ponto.

Sprints Pull já fechadas que, sem nenhuma task regular, tinham gravado Entrega zero foram corrigidas para "sem dado". A conta completa de Entrega pertence à parte de Performance.

---

### 3.5 Travamento automático e histórico da task

#### 3.5.1 O relógio

A contagem de tempo parado começa quando a task está ativa (Planejado ou Em andamento) **e** a sprint dela já foi iniciada. Task de sprint futura não conta tempo.

Quando a sprint é iniciada, pelo botão **Iniciar próxima sprint** ou pela confirmação da Avaliação Semanal, todas as tasks não concluídas dela ganham o relógio naquele instante (a contagem não é retroativa) e a foto do previsto é tirada. O relógio é desligado quando a task entra em Pendente de aprovação ou Concluída, ou quando deixa de ter sprint iniciada.

#### 3.5.2 Quando a task trava

A task trava quando o tempo parado alcança o nível dela multiplicado por **1,5 dia**, contados em dias corridos.

| Nível | Trava depois de |
|---|---|
| 1 | 1,5 dia |
| 2 | 3 dias |
| 3 | 4,5 dias |
| 5 | 7,5 dias |

- A verificação roda automaticamente a cada 24 horas e só avalia tasks em Planejado ou Em andamento. Ignora as que já estão travadas, as que aguardam o cliente e as sem relógio.
- O fator já foi 2 e baixou para 1,5 em setembro de 2026: com sprint de uma semana, o fator 2 fazia uma task de 4 pontos só travar depois do fim da sprint.
- Ao travar, o card ganha a etiqueta amarela **Travada** e o evento é registrado. No fechamento da sprint, os pontos da task travada são descontados dos pontos concluídos do operacional. Isso penaliza a Entrega, nunca a Autonomia.
- O texto de ajuda na tela resume a regra: passando de um dia e meio por ponto, a task ganha a etiqueta "Travada" e, se for concluída depois disso, os pontos dela são descontados da entrega.

#### 3.5.3 Suprimir o alerta (decisão do gerente)

É a válvula para travamento que não é culpa do operacional. Ao suprimir o alerta:

- a etiqueta Travada some;
- o relógio **recomeça do zero**. Não é imunidade permanente: se a task continuar parada além do novo prazo, trava de novo;
- os travamentos já registrados da task são dispensados, e o fechamento deixa de penalizar.

Não vale para task concluída ou sem relógio rodando.

#### 3.5.4 Histórico guardado de cada task

| O que é guardado | Para que serve |
|---|---|
| Cada mudança de coluna, responsável, sprint ou bloqueio, com autor, motivo e duração da fase anterior | Histórico na tela da task, medição de tempo de ciclo e tempo limpo do classificador |
| Cada reabertura de task concluída | Dimensão Qualidade (retrabalho) |
| Cada travamento automático | Desconto de Entrega no fechamento |
| Sugestões da IA vindas de reviews | Banner no Kanban |
| Extrato de pontos da pessoa (por exemplo, penalidade de devolução) | Extrato da pessoa |

#### 3.5.5 Movimentos do Kanban viram histórico da sprint

Cada mudança de coluna de uma task também é registrada como uma ingestão da sprint, com um resumo legível, por exemplo "Task 'X' movida de Planejado para Em andamento". Assim o movimento do Kanban aparece no histórico da sprint e entra no contexto de geração de documentos, como qualquer outro arquivo ingerido. Puxar e devolver não geram esse registro.

Quando uma task é concluída, o sistema também confere se todas as tasks da funcionalidade estão concluídas, e o status da funcionalidade é recalculado.

---

### 3.6 Pedir mais trabalho, encaminhamento e elegibilidade

#### 3.6.1 Solicitação de task extra

Isso nasceu de um feedback real: o operacional termina o que tinha e não tem um jeito social de pedir mais, então fica parado. O botão troca a conversa por um clique.

O fluxo:

1. O operacional zera suas tasks abertas.
2. No Kanban aparece o cartão **Você concluiu tudo que estava com você**, com o botão **Quero mais uma task**. O pedido aceita uma sugestão opcional em texto livre.
3. Gerente e líder recebem um e-mail e veem no Kanban o aviso de pedidos de nova task.
4. O gerente escolhe **Criar task extra** (marca o pedido como atendido e abre a criação de task) ou **Recusar**.

Regras:

- **Só vale com zero tasks em aberto.** Qualquer task do operacional fora de Concluída, de qualquer sprint, impede o pedido.
- Se já existe um pedido pendente do mesmo operacional, o sistema reaproveita o existente.
- O pedido é associado à sprint atual do projeto: a da planning mais recente, ou, se não há planning, a de maior número.
- Marcar o pedido como atendido não cria a task sozinho: o gerente a cria como task extra.

Como funciona a task extra:

- Não entra no previsto da sprint nem na Entrega.
- Concluída antes do fechamento, vira **bônus no score**: 1 ponto de score por ponto da task, com teto de 5. O teto existe para o ranking não virar "quem pediu mais task". O score final continua limitado a 100.
- Se uma extra for convertida em task normal numa sprint já iniciada, passa a contar como "surgiu na sprint".

#### 3.6.2 Encaminhamento

O encaminhamento permite que um projeto da subárea de Produto seja passado para Dados ou Dev, mantendo todo o contexto. O gerente (ou acima) escolhe o destino, pode informar um motivo de até 500 caracteres e decide se quer promover os requisitos já validados no Discovery.

- Só projetos de Produto podem ser encaminhados.
- Se a promoção estiver marcada, os requisitos validados do Discovery são promovidos antes do encaminhamento. A promoção não duplica o que já foi promovido.
- A troca de subárea e o registro do encaminhamento (origem, destino, motivo, autor, requisitos promovidos) acontecem juntos, ou não acontecem.
- O encaminhamento não mexe nas tasks: o que acompanha o projeto é todo o contexto, incluindo ingestões, Discovery e tasks.
- Esse recurso depende de uma atualização manual do banco, que precisa ter sido aplicada.

#### 3.6.3 Elegibilidade: quem é avaliado

Para a Avaliação Semanal e o fechamento de pontuação, são avaliados os operacionais **vinculados ao projeto naquele momento**: quem já tinha entrado e ainda não tinha saído.

Isso substitui a antiga definição "elegível = tem task na sprint". Na prática, quem entrou antes e ainda não saiu é avaliado e entra na média do time mesmo sem task na sprint. Quem já saiu, não.

---

### 3.7 Commits: como chegam, o que se extrai e a nota de qualidade

#### 3.7.1 Dois caminhos de entrada

- **GitHub App (caminho principal).** O repositório é conectado ao projeto, e cada envio de código (push) chega ao sistema automaticamente. Funciona em projetos das subáreas Dados, Dev e Produto.
- **Hook legado.** Mantido enquanto projetos Dev migram para o App. Tem um limite de uso por minuto (20 por padrão).

No caminho principal, o sistema:

1. Confirma que o aviso vem mesmo do GitHub, e ignora entregas repetidas.
2. Só processa envios em branches, não exclusões.
3. Descobre o projeto pelo repositório conectado.
4. Quando o envio traz mais commits do que a lista inicial mostra, busca a lista completa.
5. Para cada commit novo, lê a mensagem, o resumo das mudanças e o diff e extrai o conhecimento. Commits já ingeridos são pulados.
6. Ao concluir, marca o commit no GitHub com o status "Commit incorporado ao contexto do projeto". Se essa marcação falhar, a ingestão não é desfeita.

O hook legado não evita repetição por repositório, então a deduplicação só vale no caminho do GitHub App.

#### 3.7.2 Qual sprint o commit recebe

Em ordem de prioridade:

1. A etiqueta **[sprint:N]** na mensagem do commit.
2. O número da sprint informado pelo hook legado.
3. A sprint atual do projeto.

#### 3.7.3 O que é extraído

A IA lê o commit e extrai os mesmos campos de uma ingestão comum: resumo, tarefas implementadas, decisões técnicas, problemas ou bugs corrigidos, contexto do cliente, próximos passos e tecnologias usadas ou removidas. A regra é não inferir nada ausente: o contexto do cliente só entra se estiver explícito, e uma tecnologia só é registrada como removida quando a remoção é completa e demonstrada pelo diff.

Para controlar o tamanho, o sistema lê no máximo as primeiras 8.000 letras do diff. Se a IA falhar, o commit não é ingerido e o erro é informado.

O registro guarda também quem fez o commit, a data, o repositório, a branch e o endereço do commit no GitHub. Se dois avisos do mesmo commit chegarem ao mesmo tempo, o segundo é tratado como duplicado e não gera nova ingestão.

#### 3.7.4 Como o commit se liga a tasks

O vínculo é fraco e opcional: a etiqueta **[task:código-da-task]** na mensagem do commit. Quando presente, a task fica associada à nota de qualidade do commit. Sem a etiqueta, o commit é ingerido normalmente e fica ligado ao projeto, à sprint e à pessoa, mas não a uma task. Esse vínculo não move tasks nem alimenta o classificador.

#### 3.7.5 Nota de qualidade do commit

Logo depois de salvar o commit, a IA dá uma nota de **0 a 10** com uma frase curta de justificativa. Isso só acontece em **projetos do tipo Padrão** (projetos sem tipo definido contam como Padrão).

- **Quem fez:** o sistema tenta ligar o commit a um operacional do projeto pelo login do GitHub, depois pelo e-mail do GitHub, depois pelo e-mail cadastrado. Se nenhum bate, a nota é salva sem dono e não conta para ninguém.
- **Critérios:** complexidade do que foi resolvido, qualidade da documentação e da mensagem, e aderência a boas práticas (nomes, tratamento de erro, testes quando cabe). A justificativa é uma frase curta, nunca uma lista de pendências.
- Se a nota falhar por qualquer motivo, só o erro é registrado: o commit já ingerido nunca se perde.

**Uso na pontuação.** No fechamento, a média das notas da pessoa no projeto (só as posteriores ao último fechamento) vira a nota de commit. A dimensão Qualidade combina essa média (transformada em escala de 0 a 100) com o retrabalho, com peso padrão de 50% para cada um. Se só existir um dos dois, vale ele sozinho. Se nenhum existir, a dimensão fica indisponível, não vira 100.

**Atenção operacional:** se o login do GitHub do operacional não estiver preenchido (e o e-mail não bater), os commits da pessoa não pontuam, e não há nenhum aviso na tela.

---

### 3.8 O Classificador de nível

#### 3.8.1 O que ele faz e por quê

O classificador define o **nível de dificuldade** de cada task na régua de 1, 2, 3 e 5. O gerente deixou de digitar pontos: o agente lê título, descrição e checklist e devolve o nível. Esse nível entra no previsto da sprint, na Entrega e no ranking, então precisa ser **consistente entre gerentes** e **comparável ao tempo real gasto**.

Além de classificar, ele **aprende com a realidade**. Toda task concluída vira um exemplo: o nível que foi sugerido contra o tempo que a task levou de verdade. Desses exemplos saem as médias de tempo por nível, o ritmo de cada pessoa, o viés de cada gerente e a importância de cada sinal.

Os critérios e os sinais, em si, não mudam sozinhos. A régua só muda por uma revisão versionada, feita em rito mensal, e cada classificação guarda qual versão da régua usou.

#### 3.8.2 O que cada nível significa

Estes são os critérios que o classificador usa:

| Nível | Critério |
|---|---|
| **1** | Mudança pontual em uma parte do sistema, caminho já conhecido, sem incerteza |
| **2** | Mexe em mais de uma parte seguindo um padrão que já existe, com pouca incerteza |
| **3** | Várias partes integradas ou regra de negócio não trivial, com alguma incerteza técnica |
| **5** | Incerteza alta: exige investigação, decisão de arquitetura ou tecnologia nova para o time |

Na conta interna, a distância entre dois níveis vizinhos é sempre a mesma: a diferença entre 3 e 5 pesa igual à diferença entre 1 e 2.

#### 3.8.3 Os seis sinais

Para entender o tamanho de uma task, o classificador observa seis sinais. Cada um recebe uma nota de 0 a 2:

| Sinal | O que observa | 0 | 1 | 2 |
|---|---|---|---|---|
| **Partes** | Quantas partes do sistema a task toca | uma parte | duas partes | três ou mais |
| **Novidade** | Se o projeto já fez algo parecido | repete um padrão que o projeto já tem | adapta um padrão existente | o projeto nunca fez |
| **Incerteza** | Se está claro o que fazer | está claro | há pontos a decidir | precisa investigar antes |
| **Dependência** | De quem a task depende | nenhuma | de outra parte interna | de terceiro ou do cliente |
| **Tamanho** | Quantos itens ou entregáveis | 1 a 2 | 3 a 5 | 6 ou mais |
| **Risco** | Quão sensível é o que se mexe | nada sensível | regra de negócio importante | dados de produção, migração, segurança ou pagamento |

Duas travas garantem que a IA não "chute":

- **Cada nota precisa de prova.** Para cada sinal, a IA cita um trecho exato da própria task. O sistema confere se o trecho realmente aparece no texto, se tem tamanho mínimo e se não é a task inteira copiada (citar tudo não prova nada). Sem prova válida, a nota daquele sinal vale zero.
- **Palavras de efeito são ignoradas.** "Urgente", "complexo" e "difícil" não contam. O que vale é o que a task descreve.

Se o texto não permite avaliar um sinal, a IA deixa o sinal em branco e devolve a pergunta que o gerente precisa responder.

#### 3.8.4 Quando o classificador roda

| Momento | O que acontece |
|---|---|
| **Criação da task** | O classificador roda, com limite de 20 segundos. Se faltar informação, a task não é criada e a tela lista o que falta. Se o agente falhar, a task nasce com nível provisório |
| **Reclassificação manual** | O líder pode pedir para reclassificar, usando o texto atual. Não vale se o nível já está travado ou se a task está concluída. Se o classificador estiver fora do ar, o pedido é recusado |
| **A cada 10 minutos** | Um processo automático tenta de novo as tasks que ficaram com nível provisório |
| **Uma vez por dia** | Cria o exemplo de aprendizado das tasks concluídas que ficaram sem ele e recalcula todo o aprendizado |
| **Conclusão da task** | Não reclassifica: registra o exemplo de aprendizado e recalcula |

O classificador em si apenas decide. Quem grava a classificação, o material de busca de tasks parecidas e o nível na task é o ciclo de vida da task.

#### 3.8.5 Como o classificador chega ao nível

O caminho tem quatro etapas, em sequência.

**Etapa 1: a task tem informação suficiente?** O texto da task (título, descrição e checklist) é suficiente se há descrição preenchida **ou** pelo menos dois itens de checklist. Se não, o classificador para e pede: "Descreva a task ou adicione ao menos 2 itens no checklist para classificar o nível."

**Etapa 2: leitura dos seis sinais.** A IA dá a nota de cada sinal, com a prova do trecho citado. O texto da task é tratado só como dado, nunca como instrução. Se a IA não responder de forma válida, a chamada é repetida até três vezes; se esgotar, é falha do agente (nível provisório). Se há perguntas sem resposta, o classificador para e devolve as perguntas ao gerente ("O classificador precisa de mais detalhes").

A leitura dos sinais vira uma primeira estimativa de nível: as notas são somadas, cada uma multiplicada pela importância daquele sinal. No começo, todos os sinais têm a mesma importância. Com o tempo, o sistema aprende quais sinais de fato preveem o nível que o tempo confirmou (seção 3.8.8).

**Etapa 3: tasks parecidas do passado.** O sistema procura as **8 tasks mais parecidas** já concluídas, olhando o sentido do texto, não só as palavras. Só entram tasks que:

- já foram concluídas e têm nível real conhecido (o nível que o tempo confirmou);
- não foram excluídas do aprendizado pelo líder;
- vêm de qualquer projeto, não só do projeto da task.

A segunda estimativa de nível é a média do nível real dessas tasks, dando mais peso às mais parecidas. Se não há nenhuma parecida, essa leitura simplesmente sai da conta.

**Etapa 4: avaliação geral.** A IA dá uma segunda opinião sobre o nível, com uma justificativa curta. Se houver tasks parecidas, ela as recebe como referência, com o nível real e o tempo de cada uma. Essa justificativa é a que aparece na tela da task.

#### 3.8.6 Como as três leituras e a opinião do gerente se combinam

O classificador chega a até três leituras do mesmo nível: a dos **sinais**, a das **tasks parecidas** e a da **avaliação geral**. A conta é:

1. As leituras que existem são **somadas e divididas pelo número de leituras** (média simples).
2. Se o gerente deu a **opinião dele** sobre o nível na criação, ela entra com um peso pequeno. Esse peso **parte de zero** e só sobe se as opiniões passadas do gerente concordaram com o que o tempo mostrou. **O peso máximo é 15%.**
3. O resultado é corrigido pelo **viés do gerente**: se o histórico dele mostra que ele tende a subestimar ou superestimar, o sistema compensa.
4. O número final é arredondado para o nível mais próximo da régua.

O gerente, portanto, é uma voz de peso pequeno e **conquistado**, não dado.

**Quando vai para revisão.** A classificação não é aplicada direto e vai para o líder decidir se:

- as leituras **divergem demais** entre si (mais de um nível de distância entre a menor e a maior): motivo "leituras divergentes";
- o texto da task **parece conter uma instrução para o classificador**, como "ignore as instruções" ou "o nível desta task é 5": motivo "texto com instrução ao classificador". É a defesa contra tentativa de manipular o resultado.

**Ajuste pelo tempo.** Por último, o sistema corrige o nível usando o histórico de tempo das tasks parecidas. Ele olha quanto tempo, em média, essas tasks levaram e vê de qual nível aquele tempo mais se aproxima. Se esse nível está acima ou abaixo do combinado, move o resultado **um nível** nessa direção. O ajuste só roda quando as parecidas têm tempo registrado e já existem médias de tempo para pelo menos dois níveis, e **nunca move mais que um nível**, para limitar o estrago de uma média ruim.

O resultado é o nível final, que vai para a task junto com o histórico completo de como foi decidido.

#### 3.8.7 Quando o classificador falha: estados da classificação

Cada classificação tem um estado:

| Estado | Significado | O nível trava? |
|---|---|---|
| **Aplicada** | O agente classificou sem divergência | Sim, quando o trabalho começa |
| **Em revisão** | Aguarda decisão do líder | Não, até alguém resolver |
| **Provisória** | O agente falhou; vale um nível provisório | Não, até o sistema reclassificar ou o líder resolver |
| **Resolvida** | O líder definiu o nível | Sim |

Motivos que levam uma task à revisão: leituras divergentes, texto com instrução ao classificador, texto editado após a classificação, texto insuficiente para classificar e classificador indisponível.

**Nível provisório.** Se o agente falhar por qualquer motivo (chave, modelo, busca de parecidas, tempo esgotado), a task é criada mesmo assim, com um nível provisório: a opinião do gerente, se ele deu uma, ou o nível 2. A task fica marcada como "provisório" na tela.

A cada 10 minutos, o sistema tenta reclassificar as provisórias. Se a falha for por texto insuficiente, a classificação vai para revisão. Depois de **6 tentativas sem sucesso**, a task também vai para revisão, com o motivo "classificador indisponível". Se, enquanto a IA respondia, o nível da task foi travado ou outra classificação foi gravada, o resultado novo é descartado para não sobrescrever uma decisão mais recente.

#### 3.8.8 Como o classificador aprende com o tempo real

Quando uma task é concluída (diretamente ou por aprovação), o sistema registra um **exemplo de aprendizado** com:

- o nível que o classificador deu;
- as notas dos seis sinais;
- quem executou e qual gerente criou a task;
- quanto tempo a task levou.

Depois, todo o aprendizado é recalculado a partir de todos os exemplos, na ordem em que foram concluídos, de modo que cada exemplo é julgado só com o que se sabia antes dele.

**Tempo limpo.** O que importa é o esforço real, então o sistema mede o tempo da primeira vez que a task entrou em andamento até a última conclusão e **desconta as pausas**:

- o tempo em Pendente de aprovação;
- o tempo de volta na fila (Planejado);
- o tempo parado em Concluída antes de uma reabertura;
- os trechos de **bloqueio por cliente**. Bloqueio interno não é descontado.

Se a task não tem como determinar o início ou o fim, ela fica sem tempo e não alimenta nenhum cálculo.

**Ritmo de cada pessoa.** O sistema mede quão rápida a pessoa é em relação à média de cada nível. Quem leva o dobro da média tem ritmo 2; quem leva metade, 0,5. Para que quem tem uma ou duas tasks não receba um ritmo extremo, o cálculo "puxa" para o ritmo neutro (1,0) até que a pessoa acumule histórico. O **tempo normalizado** de uma task é o tempo limpo dividido pelo ritmo da pessoa, o que torna comparáveis tasks feitas por pessoas de ritmos diferentes.

**Médias por nível.** Para cada nível, o sistema guarda o tempo normalizado médio das tasks que a realidade confirmou naquele nível, sem contar as excluídas. É a base do ajuste pelo tempo (seção 3.8.6).

**Nível real.** É o nível que o tempo confirmou: o nível cuja média de tempo está mais perto do tempo normalizado da task. Se o nível sugerido ainda não tem média (poucos dados), confia-se na sugestão. A **opinião do operacional** depois da conclusão pode empurrar o nível real para o nível vizinho, mas só se todas estas condições valerem:

- ele opinou diferente do que o tempo indicou;
- ele tem histórico de acertos (peso maior que zero);
- existe média do nível vizinho;
- o tempo da task está perto do ponto médio entre os dois níveis (a menos de 25% da distância entre as médias).

**Alerta.** Uma task concluída entra em alerta se o tempo normalizado passa de **3 vezes a média do nível real**. Aparece na tela como "Tasks em alerta".

**Viés do gerente.** Mede o quanto o nível que o gerente acabou com tende a ficar acima ou abaixo do que o tempo indicou. Positivo significa que o gerente subestima as tasks; negativo, que superestima. O cálculo também puxa para zero enquanto há pouco histórico.

**Peso da opinião do gerente.** É a taxa de acerto da opinião dele contra o tempo, com o teto de 15%. **Peso da opinião do operacional** segue a mesma ideia, sem teto.

**Importância de cada sinal.** Com menos de 12 exemplos que tenham as notas dos sinais, todos os sinais ficam com a mesma importância. Com 12 ou mais, o sistema descobre quais sinais de fato predizem o nível que o tempo confirmou, sem nunca atribuir importância negativa a um sinal. A importância de cada sinal ao longo do tempo aparece na tela do líder.

**Exclusões.** O líder pode **tirar uma task da contagem**. Ela continua recebendo um nível real, mas deixa de atualizar médias, ritmos, vieses, opiniões e importâncias dos sinais, e não aparece como task parecida. É reversível, e o recálculo roda na hora.

**Acurácia.** O sistema mede o quanto o nível sugerido bate com o nível real: a fração de acertos exatos, a fração dentro de um nível de diferença, o erro médio em níveis, a matriz de confusão (sugerido contra real) e, para cada nível, a precisão e a cobertura.

As correções humanas que alimentam o aprendizado são quatro, todas registradas:

| Fonte | Como entra | Efeito |
|---|---|---|
| **Opinião do gerente na criação** | Um nível opcional informado ao criar a task | Entra na combinação com peso de 0 a 15% e, depois da conclusão, é comparada ao nível pelo tempo para reajustar esse peso |
| **Revisão do líder** | Escolha do nível com um motivo de pelo menos 3 caracteres | A classificação vira Resolvida com o nível escolhido. Se a task já estava em trabalho, o nível trava. Se estava concluída, o exemplo de aprendizado é refeito. Só vale para classificações em revisão ou provisórias |
| **Opinião do operacional após concluir** | Diálogo que aparece quando o operacional conclui a task | Pode empurrar o nível real para o vizinho e define o peso da opinião do operacional |
| **Exclusão do líder** | Botão **Tirar da contagem**, com motivo | Remove o exemplo do aprendizado |

Em resumo: **o gerente corrige o nível pela revisão e pela opinião, e o tempo real é o juiz.** A cada conclusão, o sistema compara o nível sugerido com o que o tempo mostrou e ajusta médias, ritmos, vieses e importâncias. A cada nova classificação, tudo isso já entra na conta.

#### 3.8.9 A trava do nível

O nível é **travado** quando o trabalho começa: ao criar a task numa sprint já iniciada ou direto em andamento, ao puxá-la da fila e ao movê-la para Em andamento, Pendente de aprovação ou Concluída. O nível só trava se a classificação está Aplicada ou Resolvida (ou se a task é antiga, sem classificação). Uma task provisória ou em revisão fica destravada até ser resolvida.

Com o nível travado, não há reclassificação, e a tela mostra "nível travado desde" a data. Isso impede que o nível mude no meio do trabalho, o que bagunçaria o previsto da sprint, a Entrega e o aprendizado.

#### 3.8.10 Quando a régua muda

A régua (critérios de nível, sinais e regras de suficiência) só muda por uma **revisão versionada**, num rito mensal, nunca automaticamente. Cada classificação guarda a versão da régua que usou, o que permite comparar resultados antes e depois de uma revisão. O que muda sozinho, com o tempo, são os valores aprendidos: médias por nível, ritmos, vieses, opiniões e importâncias dos sinais.

#### 3.8.11 O que o líder vê e faz: a tela do classificador

A tela **Classificador** é exclusiva do líder e mostra como o classificador se comporta contra o tempo real das tasks concluídas.

| Bloco | Conteúdo | Ações |
|---|---|---|
| **Tempo típico por nível** | Tempo normalizado médio por nível real. A média "sem excluídas" é a que o classificador usa. Mostra também a evolução semanal | Leitura |
| **Tasks em alerta** | Concluídas com tempo muito distante da média do nível (mais de 3 vezes): task, projeto, operacional, tempo e média do nível. Há também a lista das excluídas | **Tirar da contagem** (pede motivo) e devolver à contagem |
| **Acurácia contra o tempo real** | Acurácia exata, dentro de um nível, erro médio em níveis, número de tasks, matriz de confusão, precisão e cobertura por nível, evolução mensal | Filtros de período (30 dias, 90 dias, tudo) e por gerente |
| **Por que o classificador decide assim** | Importância dos sinais e sua evolução, viés por gerente, ritmo por pessoa, opiniões de gerentes e operacionais (peso e acurácia) | Leitura |
| **Fila de revisão** | Tasks em revisão ou provisórias, com situação, nível e motivo | Abre a janela de revisão |

**Janela de revisão.** Mostra o motivo, as três leituras (sinais, parecidas e geral), a justificativa, a tabela de sinais com a nota e a prova citada (ou "sem evidência"), a tabela de tasks parecidas (semelhança, nível real e tempo), a opinião do gerente, o nível combinado, o ajuste de tempo e o nível final. Duas ações: **Reclassificar** (roda o agente de novo) e **Resolver** (escolher o nível e escrever um motivo de pelo menos 3 caracteres).

**No Kanban**, o gerente vê o nível da task, a situação ("provisório", "em revisão" ou "definido pelo classificador") na edição, a justificativa do nível e as perguntas do classificador quando a criação é recusada por falta de detalhe. O líder tem ainda o botão de reclassificar na task.

#### 3.8.12 O ponto de partida: aprender com o passado

Para o classificador não começar do zero, existe uma rotina de apoio que transforma as tasks **já concluídas antes dele** em exemplos de aprendizado. Para cada task concluída sem exemplo, ela:

1. Calcula o tempo limpo. Task sem tempo calculável é pulada.
2. Prepara o material para a busca de tasks parecidas.
3. Pede à IA as notas dos seis sinais, com a mesma exigência de prova.
4. Cria o exemplo de aprendizado, usando como nível sugerido o valor antigo convertido para a régua.
5. No fim, recalcula todo o aprendizado.

A rotina pode ser repetida sem duplicar nada, e refaz o material de busca de tasks parecidas quando o modelo de busca é trocado. Segundo o registro do projeto, esta etapa entrou em produção em outubro de 2026, ainda faltando validar a busca de parecidas com a primeira task real e rodar essa rotina de ponto de partida.

---

### 3.9 Busca de tasks

Não existe busca por texto de tasks. O que há é:

- **Filtros** na lista de tasks: por sprint, operacional, coluna e funcionalidade. O Kanban expõe os filtros de sprint, operacional e funcionalidade.
- **Busca por semelhança de sentido**, usada só internamente pelo classificador para achar tasks parecidas. O usuário não a usa como busca: o líder só vê as parecidas dentro da janela de revisão.
- Existe também uma busca à parte que procura **projetos** de uma subárea que usaram determinada tecnologia citada nas ingestões. Ela não procura tasks.

---

### 3.10 Resumo para consulta rápida

| Pergunta | Resposta |
|---|---|
| Quem define os pontos? | O classificador, na régua 1, 2, 3 e 5 |
| O que bloqueia mover para Concluída? | Checklist incompleto, ou task que requer aprovação (precisa passar por Pendente de aprovação) |
| Quando uma task trava? | Quando o tempo parado alcança o nível multiplicado por 1,5 dia. A verificação roda a cada 24 horas |
| O que acontece ao travar? | Etiqueta amarela e desconto de Entrega ao concluir, a menos que o gerente suprima o alerta |
| E o bloqueio por cliente? | Pausa o relógio, não conta em Autonomia, sai dos pontos alocados e é descontado do tempo que o classificador usa |
| WIP padrão? | Sem limite. Em Pull, 1 por pessoa |
| Quanto vale uma task extra? | Bônus de 1 ponto de score por ponto da task, com teto de 5 |
| Quantas tasks parecidas o classificador consulta? | 8, só concluídas, não excluídas e com nível real conhecido |
| Peso máximo da opinião do gerente? | 15% |
| Quando o nível trava? | Ao entrar em trabalho (andamento, aprovação, conclusão ou puxar), se a classificação está Aplicada ou Resolvida |
| O que é nível provisório? | O nível dado quando o agente falha: a opinião do gerente ou 2. O sistema tenta de novo a cada 10 minutos, até 6 vezes |
| Como o commit pontua? | Nota de 0 a 10 dada por IA, só em projetos Padrão, ligada à pessoa pelo login do GitHub ou e-mail |


---

## Parte 4 — Sprints, Planning e Documentação

Esta parte explica o que acontece entre criar uma sprint e ter um documento pronto: o ciclo de vida da sprint, a Planning passo a passo, a Daily, a Review, a Retrospectiva, o Repasse Semanal, o envio de arquivos soltos e todos os tipos de documento que o sistema gera. A ideia central é que o gerente alimenta o sistema com o que já produz no dia a dia e a documentação sai como consequência.

Dois pontos valem para todo o ciclo de sprint:

- **A IA nunca inventa.** Quando não há informação suficiente, o documento diz isso de forma explícita em vez de preencher com suposição.
- **Os envios à IA têm limites.** Há um limite de pedidos por minuto e um tamanho máximo por arquivo enviado (20 MB por padrão).

---

### 4.1 Sprints: o que são e como o sistema as enxerga

#### 4.1.1 O que é uma sprint no DocuData

Uma sprint é um número dentro de um projeto (Sprint 1, Sprint 2...) que agrupa tasks, documentos e arquivos enviados. Cada sprint carrega:

- um **semáforo de saúde** (verde, amarelo ou vermelho) e um **plano de correção** em texto livre;
- a informação de se já foi **iniciada** ou se está apenas planejada;
- a marca de que a **Avaliação Semanal** foi confirmada, que é o que a deixa "Fechada";
- os modos de avaliação usados na pontuação (assunto da parte de performance).

Não existe um estado "fechada" guardado à parte. O rótulo vem da combinação entre estar iniciada e ter a avaliação confirmada.

#### 4.1.2 Como uma sprint nasce

Há quatro caminhos:

| Caminho | Como funciona |
|---|---|
| Botão **Iniciar próxima sprint** (aba Sprints) | Se existir alguma sprint planejada e ainda não iniciada, o botão **inicia a mais antiga** em vez de criar outra. Só cria uma nova quando não há nenhuma planejada. O número nunca é digitado: é sempre o maior número existente mais um (ou 1, no primeiro caso). |
| Criação automática | Sempre que alguém envia um arquivo ou gera um documento de sprint para um número que ainda não existe, o sistema cria a sprint na hora. Por isso toda ingestão tem uma sprint correspondente, mesmo que ninguém tenha clicado em criar. |
| Confirmação da Avaliação Semanal | Ao confirmar a avaliação da sprint N, se a sprint N+1 existir e estiver apenas planejada, ela é iniciada automaticamente. |
| Criação com número explícito | Existe só como possibilidade do sistema, não como botão na tela. Dois números iguais no mesmo projeto não são aceitos. |

Só quem tem acesso ao projeto pode criar sprints, e o cargo operacional não inicia nem altera o ciclo da sprint.

#### 4.1.3 Estados da sprint na aba Sprints

| Estado | Condição | Como aparece |
|---|---|---|
| **Planejada, não iniciada** | Ainda não foi iniciada | Não vira card. Fica num bloco recolhível "Planejadas, ainda não iniciadas", com o previsto em pontos e o botão **Iniciar sprint**. |
| **Atual** | Iniciada e com o maior número entre as iniciadas | Card aberto, com selo verde "Atual". |
| **Em aberto** | Iniciada, não é a atual e a avaliação ainda não foi confirmada | Linha recolhida com rótulo âmbar "Em aberto". |
| **Fechada** | Iniciada, não é a atual e a avaliação foi confirmada | Linha recolhida com rótulo cinza "Fechada". |

Para o resto do sistema (commits, Motor de Score), a "sprint vigente" é a da Planning mais recente. Se o projeto ainda não tem nenhuma Planning, vale a de maior número. Essa definição pode diferir da visual da aba Sprints, que usa a maior sprint iniciada.

#### 4.1.4 O que acontece quando uma sprint é iniciada

Iniciar uma sprint é um passo sem volta. Ao iniciar, o sistema faz, nesta ordem:

1. Marca a sprint como iniciada.
2. Se for a primeira vez, **tira a foto do previsto** (4.1.5).
3. Começa a contar o relógio de travamento automático das tasks da sprint que ainda não estão concluídas e ainda não tinham essa contagem. A medida não é retroativa.
4. Trava o nível de dificuldade das tasks.

Outras ações sobre a sprint:

- **Reabrir fechamento:** no menu "···" do card, só para líder e owner, e só em sprint já fechada. Apaga a pontuação travada e devolve a sprint a "Em aberto". As respostas do questionário da avaliação são mantidas.
- **Semáforo e plano de correção:** podem ser editados à mão. O semáforo também é recalculado sozinho toda vez que uma task é concluída: divide-se os pontos concluídos (sem extras) pelo previsto, e o resultado dá **verde a partir de 0,9**, **amarelo a partir de 0,7** e **vermelho abaixo disso**. Se o previsto for zero, o semáforo manual é mantido.
- **Excluir sprint:** apaga tudo que pertence a ela, de forma irreversível: as tasks, os arquivos enviados, os documentos gerados, o rascunho de planning e a própria sprint. As funcionalidades afetadas têm o status reajustado. A tela pede confirmação antes.

#### 4.1.5 O previsto da sprint (a "foto")

O previsto é o total de pontos que a sprint se comprometeu a entregar, e alimenta o card e o SPI.

- Quando a sprint **é iniciada**, todas as tasks dela que não são extras são marcadas como **planejadas no início**. Essa é a foto do planejado. Iniciar de novo não tira outra foto.
- Uma task que entra na sprint **depois** de iniciada (criada nela ou movida para ela) e não é extra é marcada como **surgiu na sprint**.
- **Previsto = pontos das planejadas no início + pontos das que surgiram.** Task extra nunca entra, porque é trabalho concedido além do planejado.
- O card mostra "Previsto N pts" e, quando há tasks que surgiram, a divisão "X planejados + Y surgiram na sprint".

Detalhe importante: a foto **não é tirada pelo documento de Planning**. Ela é tirada no instante em que a sprint é iniciada. Gerar ou não o documento de Planning não muda o previsto; o que o muda é o conjunto de tasks do Kanban naquele momento. Também não existe mais uma tela de orçamento de pontos: o orçamento fixo de 100 pontos foi removido e os pontos de cada task são definidos no Kanban. Nenhum campo da Planning pede ou valida pontos.

#### 4.1.6 O card da sprint e o checklist de documentação

A **documentação mínima obrigatória** de uma sprint é **Planning e Review**. As **Dailys** são recomendadas. A Retrospectiva e a Avaliação aparecem no checklist visual, mas não entram na conta das pendências.

Cada card mostra os itens abaixo como chips clicáveis:

| Chip | Fica "feito" quando | O que abre |
|---|---|---|
| **Planning** | Existe uma Planning registrada na sprint | O formulário de Planning (4.2) |
| **Review** | Existe uma Review registrada | O formulário de Review (4.3.1) |
| **Retrospectiva** | Existe uma retrospectiva gerada | O formulário de Retrospectiva (4.3.3) |
| **Avaliação** (oculto para operacional) | A avaliação foi confirmada ou todos os elegíveis foram avaliados | A Avaliação Semanal |
| **Dailys** | Há ao menos uma Daily; senão aparece como "opcional" | O formulário de Daily (4.3.2) |

Os estados visuais são três: círculo verde com check (feito), círculo âmbar (pendente) e círculo tracejado (opcional). Na linha recolhida, uma mini-barra por item obrigatório e o texto "N de M documentos" resumem o andamento.

Outros elementos do card:

- **+ Documento:** adiciona um documento manual (4.5.6).
- **Gerar Repasse Semanal:** gera o repasse da sprint (4.3.4).
- **Menu "···":** **Upload livre**, **Reabrir fechamento** e **Excluir sprint**.
- Contador "N ingestões · M docs".
- Painel **Detalhes**, com os documentos da sprint (ver, copiar, editar, enviar ao Google Docs, mover de sprint, excluir), os arquivos enviados (com chips de tarefas, decisões, problemas e tecnologias extraídos, além de mover de sprint e excluir) e os commits, agrupáveis por repositório.

A listagem de sprints também informa, para cada uma, se tem Planning e Review, quantas Dailys, quantos arquivos enviados, quantos documentos gerados, o previsto e o progresso da Avaliação Semanal.

#### 4.1.7 Lembretes automáticos por e-mail

O sistema confere de hora em hora e envia no máximo um e-mail por tipo, por sprint, por dia:

| Lembrete | Dispara quando |
|---|---|
| Planning | A sprint foi criada há 24 horas ou mais e ainda não tem Planning |
| Review | Passaram 5 dias ou mais e ainda não há Review |
| Retrospectiva | Passaram 7 dias ou mais e ainda não há retrospectiva |

---

### 4.2 Como gerar a Planning, passo a passo

A Planning é o documento mais usado do ciclo. O princípio do fluxo atual é **não pedir ao gerente o que o Kanban já sabe**: responsável, prazo e critério de pronto saem das tasks e do período da sprint, não de digitação.

Para abrir, vá à aba Sprints e clique no chip **Planning** do card da sprint. O assistente tem quatro barras de progresso no topo e três caminhos possíveis:

- **Caminho normal:** as tasks já estão no Kanban. Tela inicial, depois formulário, depois documento.
- **Caminho de importação:** as tasks estão fora do DocuData (Notion, planilha, print). Importação, conferência das correlações, formulário, documento.
- **Caminho sem IA:** o gerente escreve o texto da planning à mão.

#### 4.2.1 Tela inicial

Ao abrir, a tela mostra, de cima para baixo:

- Um link roxo: **"As tasks desta sprint estão em outro lugar (Notion, planilha, print)?"**, que leva ao caminho de importação.
- Um **banner amarelo** (só a partir da Sprint 2) listando as funcionalidades que ainda estão **em andamento** vindas da sprint anterior, no formato código e título. É só um lembrete visual.
- A lista **Tasks desta sprint no Kanban**, com rolagem. Mostra as tasks das colunas **Planejado** e **Em Andamento**, ordenadas por coluna e posição, com título, selo "bloqueada" quando for o caso e pontos. Se não houver nenhuma, aparece um aviso amarelo sugerindo criar as tasks na aba Kanban ou usar o link de importação. Sem tasks, a planning não é aceita (ver 4.2.3).
- **Contexto da sprint (opcional):** uma caixa de texto livre. É o espaço para o gerente contar, do jeito dele, por que a sprint existe, o que mudou com o cliente e o que o preocupa. A IA usa esse texto como insumo.
- Os botões **Escrever sem IA**, **Cancelar** e **Continuar**.

Ao clicar em **Continuar**, se o gerente não passou pela importação, o sistema monta a lista de backlog automaticamente a partir das tasks do Kanban, já associando cada uma à funcionalidade a que pertence.

#### 4.2.2 Formulário da planning

Os campos aparecem nesta ordem:

| Campo | Obrigatório? | O que vem preenchido e observações |
|---|---|---|
| **Objetivo da sprint** | Não, quando já há tasks. Se não houver tasks e o objetivo estiver vazio, o sistema bloqueia pedindo "ao menos o objetivo da sprint" | Caixa de texto. Se estiver vazio e houver tasks, o documento usa "Planning da Sprint N". Vem preenchido, com selo **IA**, se o gerente passou pela importação. |
| **Squad (membros e papéis)** | Sim | Já vem preenchido com os operacionais **ativos** do projeto, no formato "Nome (papel)". Pode ser editado. |
| **Período da sprint** (início e fim) | Sim, as duas datas | Selo IA quando extraído da importação. A data de **fim** vira o prazo de todos os itens do backlog. |
| **Horas disponíveis** | Sim | Número inteiro: a capacidade real do squad na sprint. |
| **Horas estimadas** | Sim | Número inteiro: as horas que o trabalho planejado deve exigir. |
| **Dependências** | Sim: pelo menos um item **ou** marcar "sem dependências" | Cada item tem a dependência, o prazo, a consequência e a confiança. |
| **Riscos** | Sim: pelo menos um item **ou** marcar "sem riscos" | Cada item tem o risco e a consequência. |
| **Carry-over** | Sim: pelo menos um item **ou** marcar "sem carry-over" | Cada item tem o que não foi entregue e a causa raiz. |

A regra de "preencher ou confirmar que não há" existe para impedir lacuna silenciosa: um campo em branco por esquecimento não é aceito, só um vazio assumido de propósito. Quando algo falta, o assistente avisa com mensagens como "Squad é obrigatório" ou "Preencha ao menos uma dependência, ou confirme que não há nenhuma".

#### 4.2.3 O que o sistema monta ao gerar

Ao clicar em gerar, aparece "Gerando documentação da sprint…". Para cada task da lista, o sistema monta um item de backlog:

| Campo do item | De onde vem |
|---|---|
| **Item** | O título da task |
| **Responsável** | O operacional vinculado à task no Kanban, quando a task é encontrada pelo título idêntico. Senão, fica vazio. |
| **Prazo** | A data de fim do período da sprint, porque todo item do backlog é devido até o fim da sprint |
| **Critério de pronto** | O checklist da task no Kanban (os textos não vazios, unidos). Fica vazio se a task não tem checklist. |

O checklist da task é o mesmo que impede movê-la para Concluída, e por isso funciona como Definition of Done. Tasks que chegaram por importação e não têm título idêntico a uma task do Kanban saem sem responsável e sem critério de pronto, mas com o prazo do fim da sprint.

O sistema recusa a planning quando:

- o backlog está vazio ("O backlog da sprint é obrigatório — inclua ao menos 1 item");
- dependências, riscos ou carry-over estão vazios sem a confirmação correspondente.

Quando tudo está certo, acontece o seguinte:

1. A sprint é criada, se ainda não existir.
2. Os dados do formulário são registrados **sem passar pela IA**: eles já são estruturados, e chamar o modelo só traria custo e risco de distorção. O resumo é o objetivo, as tarefas são os itens do backlog com responsável, prazo e critério de pronto, e os riscos viram problemas com sua consequência.
3. Esse registro conta como a Planning da sprint e deixa o chip **Planning** verde.
4. A IA gera o documento de Planning a partir desse registro e do backlog do Kanban (4.5.3).
5. Em paralelo, as tasks são agrupadas por funcionalidade (4.2.6).

#### 4.2.4 Tela do documento

No fim aparece "Planning gerado e salvo com sucesso", com o documento renderizado e o botão **Copiar markdown**. Ao fechar o assistente, a aba recarrega e o documento já está disponível em Documentos.

#### 4.2.5 Caminho de importação (tasks fora do DocuData)

Aberto pelo link roxo da tela inicial.

1. **Entrada.** Duas abas: **Arquivo / Kanban** (arraste ou escolha um arquivo; aceita imagens PNG, JPG, JPEG e WEBP, além de PDF, DOCX e TXT) ou **Texto** (cole a lista, por exemplo "Criar modelo de ML — Responsável: Ana").
2. **Analisar com IA.** A IA faz duas leituras em sequência. Primeiro extrai o planejamento: descrição, itens de backlog, horas, período, dependências, riscos e carry-over. Imagens e PDFs escaneados são lidos por visão; textos longos são cortados em cerca de 30 mil caracteres. Depois **correlaciona** cada task extraída com a funcionalidade mais provável do escopo do projeto, ou deixa sem funcionalidade quando não couber. Se o projeto não tem funcionalidades cadastradas, as tasks ficam sem funcionalidade.
3. **Nada é salvo nessa etapa.** Serve apenas para pré-popular a tela seguinte.
4. **Conferência das correlações.** Uma tabela *Task × Funcionalidade*, com uma lista de seleção por linha (incluindo "Sem funcionalidade"), botão de remover e um campo para adicionar task manualmente. Se o projeto não tem funcionalidades, aparece um aviso amarelo orientando a ir à aba de Planejamento/Escopo. O botão seguinte é **Próximo: preencher campos**.
5. **Formulário.** Abre com os campos extraídos e o selo **IA** em tudo que a IA realmente preencheu (objetivo, período, horas, dependências, riscos, carry-over). Tudo continua editável e obrigatório como no caminho normal.

#### 4.2.6 Caminho "Escrever sem IA"

Uma caixa de texto grande, sem formato obrigatório. Ao clicar em **Salvar planning**, o texto é guardado **exatamente como foi escrito**, como documento de Planning da sprint. Esse caminho não passa pela IA e não vincula funcionalidades à sprint.

#### 4.2.7 O que a Planning altera além do documento

- Para cada funcionalidade correlacionada, registra que ela entrou na sprint, com suas tasks, e marca o andamento como "em andamento".
- Funcionalidades que ainda estavam como "não iniciada" são promovidas para "em andamento".
- **Não cria tasks no Kanban.** As tasks vêm do Kanban (ou do texto) e a Planning apenas as documenta e correlaciona. Tasks sem funcionalidade ficam fora desse vínculo.
- **Não define pontos** e **não tira a foto do previsto** (4.1.5).

---

### 4.3 Review, Daily, Retrospectiva, Repasse e Resumo semanal

Daily, Review e Retrospectiva seguem o mesmo molde de duas etapas:

1. **Matéria-prima (opcional).** O gerente cola um texto bruto (transcrição, conversa, anotações) ou sobe um arquivo e clica em **Analisar com IA**, ou então escolhe **Preencher manualmente**. A IA extrai apenas o que está explícito e deixa em branco o que não estiver, para o gerente revisar. Nada é salvo nesse momento.
2. **Formulário.** O gerente confere e completa os campos. Ao enviar, o sistema registra os dados e gera o documento.

Cada envio vira um registro da sprint no formato padrão do sistema, com os campos do formulário guardados junto. Os documentos de Review e Retrospectiva são gerados a partir de **todos** os registros da sprint; Planning e Daily usam só o registro recém-criado.

#### 4.3.1 Review

Formulário no padrão do Template 2 do CITi:

| Campo | Obrigatório | Observações |
|---|---|---|
| Observações do gerente | Sim | Vira o resumo do registro. |
| Percepção do cliente | Sim | Frase literal ou paráfrase objetiva. A IA é instruída a **não interpretar**. |
| Sinal de satisfação | Sim | Seis categorias fixas, listadas abaixo. |
| Squad | Sim | Texto. |
| Período (início e fim) | Sim | Datas. |
| Subárea | Sim | Dados, desenvolvimento ou produto. |
| **Planejado vs Entregue** | Sim, ao menos uma linha | Preenchido automaticamente a partir do Kanban (abaixo). |
| % de itens com "Pronto" cumprido | Sim | Texto digitado, por exemplo "8 de 10 = 80%". A tela não calcula. |
| Pedidos fora do escopo | Ao menos uma linha **ou** marcar "sem pedidos" | Cada linha tem data, descrição e status (Insistência ou Sugestão pontual). |
| Itens para a próxima sprint | Ao menos uma linha **ou** marcar "sem itens" | Cada linha tem o item e o número da causa raiz. |
| Anexo (PDF ou imagem) | Opcional | Passa pela leitura da IA e é somado aos dados do formulário. |

As seis categorias do sinal de satisfação:

1. Elogio espontâneo.
2. Neutro / sem sinal.
3. Reclamação pontual, resolvida na própria Review.
4. Reclamação não resolvida ao final da Review.
5. Reclamação recorrente sobre o mesmo tema (2ª vez).
6. Cliente solicitou reunião de escalonamento.

**Preenchimento automático do Planejado vs Entregue.** Ao chegar no formulário, a tabela já vem montada com **uma linha por task da sprint**. O item é o título da task. A coluna "entregue" é **S** quando a task está em Concluída e **N** nas demais. Motivo e causa raiz vêm vazios, porque dependem de julgamento humano e o gerente os completa. A tabela é recalculada do zero a cada abertura, e o conteúdo lido de anexo ou pela IA **não** a alimenta, de propósito. Se a sprint não tem tasks, a tabela fica vazia e o envio é recusado, com a mensagem de que nenhuma task foi encontrada para a sprint.

Se um anexo falhar por motivo técnico, a Review segue sem ele. Se o anexo for de um tipo de documento diferente do esperado, o erro volta ao usuário (4.4.4).

Depois de enviar uma Review, o sistema abre a tela para **atualizar o status das funcionalidades** da sprint.

**Efeito extra de arquivos de Review.** Quando um arquivo enviado pelo Upload livre é reconhecido como Review, o sistema compara as tarefas citadas com as tasks ativas da sprint e cria **sugestões** de mover tasks para Concluída, que aparecem na aba Tasks. Isso nunca bloqueia o envio.

#### 4.3.2 Daily

| Campo | Obrigatório | Observações |
|---|---|---|
| Data | Sim | Vem preenchida com hoje. |
| O que foi feito | Sim | |
| O que será feito | Sim | |
| Impedimentos | Não | Se ficar vazio, o documento diz "Nenhum impedimento reportado nesta daily". |
| Anexo (PDF ou imagem) | Não | Por exemplo, a transcrição da daily. |

Cada Daily vira um registro e um documento próprios. Não há quantidade mínima, porque as Dailys são recomendadas, não obrigatórias.

#### 4.3.3 Retrospectiva

Abre pelo chip **Retrospectiva**. **Nenhum campo é obrigatório.** Sem observações, o resumo vira "Retrospectiva da Sprint N".

| Seção | Campos |
|---|---|
| Cabeçalho | Squad, período (início e fim) e subárea |
| **O que Funcionou** | Lista de textos, que começa com duas linhas e aceita mais ou menos |
| **O que Não Funcionou** | Lista de textos |
| **Causa Raiz × Impacto** | Linhas com o número da causa raiz (ex.: "4: Estimativa equivocada") e o impacto: Baixo, Médio ou Alto |
| **Ações de Melhoria** | **No máximo duas**, cada uma com ação, responsável e prazo |
| Pedido fora de escopo | Sim ou não, e o status do registro (lista informal ou pedido de mudança formalizado) |
| Anexo | PDF ou imagem, opcional |

As **sete categorias de causa raiz**, usadas na Review, na Retrospectiva e nos prompts:

1. Especificação incompleta no Planning.
2. Dependência do cliente atrasada ou não entregue.
3. Pedido de escopo novo (potencial pedido de mudança).
4. Estimativa de horas equivocada.
5. Bloqueio técnico ou de infraestrutura.
6. Ausência ou rotatividade de membro.
7. Outro.

A retrospectiva gerada considera todos os registros da sprint e segue o Template 3 do CITi.

#### 4.3.4 Repasse Semanal

O botão **Gerar Repasse Semanal** fica no card da sprint. Ele abre um painel de confirmação que explica o que o documento é, para que serve, quando gerar e de quais fontes vem, com o botão **Confirmar e gerar**. Não há formulário: o repasse usa os registros da sprint e o Kanban.

O texto é executivo, pensado para líder ou cliente. Traz data e tópico, resumo da semana, principais pontos com status, decisões tomadas e próximos passos. O quadro de **Entregue vs Pendente da sprint**, calculado do Kanban na hora, entra como **fonte de verdade do status**. Por isso o repasse **não precisa de uma Review pronta** para ser gerado.

#### 4.3.5 Boletim de aceite e Resumo semanal

- **Boletim de aceite:** foi removido do produto. Não há tela nem função para ele.
- **Resumo semanal:** é gerado **sem IA**, com regras fixas, o que significa custo zero e nenhum risco de invenção. Cobre a semana corrente, de **domingo a sábado**, e traz:
  - as funcionalidades **travadas** (em andamento há mais de 7 dias);
  - os **achados críticos** da revisão diária de código mais recente;
  - a leitura **Tempo × Escopo** (percentual do prazo consumido contra percentual do escopo concluído), ou um aviso de que as datas do contrato não estão configuradas.

  Sem nenhuma anomalia, o resumo diz "Nenhuma anomalia identificada nesta semana". O documento é guardado sem número de sprint.

---

### 4.4 Ingestão de arquivos

Ingestão é o caminho "arquivo solto vira conhecimento estruturado". Ela tem três portas de entrada: o **Upload livre**, os **anexos** dos formulários de Planning, Daily, Review e Retrospectiva, e a **transcrição da Ata**. Os commits de código também viram registros da sprint, por um fluxo próprio descrito em outra parte deste guia.

#### 4.4.1 Upload livre

Abre pelo menu "···" do card da sprint. A tela explica que o material enviado é avulso e alimenta o contexto do projeto e os documentos gerais, como Onboarding e Documentação Final. Serve para prints, código, atas externas e PDFs do cliente.

- **Aba Arquivo:** um arquivo por vez. Aceita documentos (TXT, DOCX, PDF), imagens (PNG, JPG, JPEG, WEBP) e arquivos de código ou configuração de várias linguagens e formatos, como Python, JavaScript, TypeScript, SQL, Markdown, YAML, JSON, CSV, HTML, CSS, Java, Go, Rust, Ruby, shell, TOML e XML.
- **Aba Pasta / Projeto:** envia uma pasta inteira. O sistema filtra pelos tipos aceitos, ignora arquivos muito pequenos (menos de 100 bytes) e pula pastas que não interessam, como as de dependências, de controle de versão, de cache, de compilação e de configuração de editor. Processa vários arquivos ao mesmo tempo, mostra o progresso, lista os arquivos que deram erro e permite cancelar. O nome registrado é o caminho relativo do arquivo na pasta.
- **Imagens** são reduzidas no próprio navegador, para no máximo 1024 pixels no maior lado, antes do envio.
- Tipos de arquivo fora dessa lista são recusados.

Se o arquivo for reconhecido como Review, o sistema também gera as sugestões de tasks descritas em 4.3.1.

#### 4.4.2 O que a IA faz com o arquivo

O processamento tem cinco etapas:

1. **Conferir o tipo do documento.** A IA lê os primeiros 3 mil caracteres do arquivo, usando o nome, o cliente e a descrição do projeto como contexto, e o classifica em uma de **oito categorias**: Planning, Daily, Review, Retrospectiva, ata de reunião, commit, upload livre ou não relacionado.
2. **Identificar o formato** do arquivo: texto, PDF ou imagem.
3. **Preparar o conteúdo.** Textos são limpos (espaços e linhas em branco em excesso são removidos) e cortados em 50 mil caracteres. PDFs têm o texto lido diretamente; se não houver nenhum texto (PDF escaneado), a primeira página é transformada em imagem e lida por visão. Imagens são validadas e reduzidas.
4. **Extrair o conteúdo estruturado.** A IA lê o texto ou a imagem e devolve os campos descritos em 4.4.3. Se não houver conteúdo aproveitável, a extração é rejeitada com o aviso "A IA não encontrou conteúdo aproveitável neste arquivo".
5. **Salvar** o resultado como registro da sprint.

**Nova tentativa automática.** Se a resposta da IA vier mal formada, o sistema tenta de novo com a instrução reforçada de devolver apenas o formato esperado. Há no máximo duas execuções. Erros do próprio arquivo (corrompido, formato não suportado) encerram sem gastar IA.

**Limites e mensagens.** Imagens acima de cerca de 40 milhões de pixels são recusadas por serem grandes demais. Arquivo corrompido, formato de imagem fora de PNG, JPEG e WEBP, PDF inválido ou PDF que demora demais para ser convertido (mais de 30 segundos) são recusados com uma explicação. Se a IA falhar, a mensagem mostrada é genérica, sem expor dados internos.

#### 4.4.3 O que é extraído

Cada arquivo vira um conjunto de oito campos:

| Campo | Conteúdo |
|---|---|
| **Resumo** | O que foi trabalhado. |
| **Tarefas** | Lista de tarefas. Em print de Kanban, uma por linha, com responsável, prazo e critério de pronto quando estiverem visíveis. |
| **Decisões** | Decisões técnicas tomadas. |
| **Problemas** | Problemas e bloqueios. Riscos visíveis em Kanban entram com a consequência. |
| **Contexto do cliente** | Informações do cliente e requisitos. |
| **Próximos passos** | O que vem a seguir. |
| **Tecnologias** | A stack mencionada, como linguagens, técnicas e ferramentas. |
| **Tecnologias removidas** | Só quando a remoção é explícita e completa (por exemplo, um pacote deletado). Nunca é inferida. |

Para código-fonte, o resumo diz o que o código faz, as tarefas são as funcionalidades implementadas, as decisões são padrões e escolhas de arquitetura, e os problemas são os pontos pendentes registrados nos comentários. A IA é instruída a extrair somente o que está explícito no arquivo.

#### 4.4.4 Quando o tipo não bate: "Enviar assim mesmo"

A conferência de tipo é **conservadora**: na dúvida, ela libera. Ela só bloqueia com alta confiança.

- No Upload livre, só é bloqueado o que a IA considera **claramente não relacionado** ao projeto.
- Nos botões específicos (Planning, Daily, Review, Retrospectiva), é bloqueado o arquivo que parece ser de outro tipo de documento. A mensagem diz algo como "Esse arquivo parece ser uma X, não um(a) Y. Para ingerir como X, use o botão X da sprint."

Quando há bloqueio, a tela mostra a explicação e oferece o botão **Enviar assim mesmo**, que reenvia pulando a conferência. Isso vale para o Upload livre e para os anexos dos formulários. Na aba Pasta / Projeto esse botão não existe: arquivos reprovados contam como erro.

#### 4.4.5 Anexos dos formulários

Os anexos de Planning, Daily, Review e Retrospectiva aceitam **somente PDF ou imagem** (PNG, JPG, WEBP). O sistema lê o anexo com a mesma IA do Upload livre e soma o resultado aos dados do formulário, de modo que no fim exista **um único registro consolidado** da sprint, com o tipo correto.

A **Ata de reunião** é diferente: exige um **PDF** e o registro criado a partir dele é **mantido** como material avulso da sprint, sem contar como Planning, Daily nem Review.

#### 4.4.6 Revisão diária de código

Não é um envio de arquivo. É uma rotina que recebe o conjunto de alterações de código das últimas 24 horas de um repositório e pede à IA que aponte **achados**: problemas de bug, segurança, dívida técnica, testes removidos e credenciais expostas.

- Cada achado tem **severidade** (crítica, alta, média ou baixa), confiança, a referência exata do arquivo e da linha, uma descrição técnica e uma **descrição para o gerente**, em linguagem de negócio.
- **Sem referência confirmada no código, não há achado.** O máximo é 20 achados, ordenados por severidade. Sem alterações, o resultado é vazio.
- O resultado vira um relatório para o gerente e outro técnico, e os achados críticos alimentam o Resumo semanal (4.3.5).

---

### 4.5 Geração de documentos

#### 4.5.1 Catálogo dos tipos

O sistema gera **nove tipos de documento**, mais o Resumo semanal, que é produzido por regras fixas (4.3.5).

| Documento | Escopo | De onde vem a informação |
|---|---|---|
| **Repasse Semanal** | Sprint | Todos os registros da sprint, o Kanban e o quadro Entregue vs Pendente |
| **Retrospectiva** | Sprint | Todos os registros da sprint, incluindo os campos do formulário de retrospectiva, e o Kanban |
| **Review** | Sprint | Todos os registros da sprint, incluindo os campos do formulário de review, e o Kanban |
| **Planning** | Sprint | Só o registro da Planning recém-criada e o Kanban da sprint |
| **Daily** | Sprint | Só o registro da Daily recém-criada |
| **Ata de Reunião** | Arquivo | Só o registro da transcrição ou pauta escolhida |
| **Log de Decisões** | Projeto | Todos os registros do projeto, em ordem crescente de sprint |
| **Onboarding** | Projeto | Todos os registros do projeto; a sprint mais recente define o estado atual |
| **Documentação Final** | Projeto | Todos os registros do projeto |

Na interface, Planning, Daily, Review e Retrospectiva são gerados pelos próprios formulários da sprint (4.2 e 4.3). Os demais saem do botão do card da sprint (Repasse) ou da sub-aba Cross-sprint da aba Documentos (4.5.4).

#### 4.5.2 Como a IA monta o documento

O processo tem quatro passos:

1. **Buscar o que vale.** Dependendo do tipo, o sistema reúne só o registro escolhido, ou os registros da sprint, ou os do projeto inteiro.
2. **Compilar o contexto.** Cada registro vira um bloco legível com resumo, tarefas, decisões, problemas, contexto do cliente, tecnologias, tecnologias removidas e próximos passos. Registros de commit acrescentam repositório, branch, autor, data, mensagem e resumo das alterações. Os campos dos formulários de Planning, Daily, Review e Retrospectiva entram em blocos de **dados estruturados**, sem os campos vazios. Documentos de sprint (e a Planning) recebem também o **backlog do Kanban** da sprint, com coluna, título, pontos e selo de bloqueada. O Repasse recebe ainda o quadro de **Entregue vs Pendente**. Quando há duas ou mais sprints, entra um bloco de **mudanças detectadas entre sprints**, com as tecnologias adicionadas e removidas.
3. **Gerar com o modelo.** O modelo recebe o modelo de documento do tipo escolhido, a **regra anti-invenção** e as **Observações adicionais** do gerente (se houver). A regra anti-invenção manda escrever "[Insumo insuficiente — sem dados nas ingestões do projeto]" sempre que o contexto não tiver informação suficiente, em vez de preencher com suposição. Todos os modelos mandam seguir exatamente a estrutura pedida e dar prioridade aos dados estruturados do gerente.
4. **Salvar** o documento junto com o projeto, o tipo e a sprint.

**Quando o sistema recusa a geração por falta de material:**

- Planning, Daily e Ata: nunca são recusadas, porque o registro acabou de ser criado.
- Qualquer outro tipo, sem nenhum registro no escopo: pede que se envie ao menos um arquivo.
- **Log de Decisões:** exige que pelo menos um registro tenha decisões extraídas.
- **Documentação Final:** exige dados de **pelo menos duas sprints** diferentes.

Documentos muito longos, como a Documentação Final, podem sair truncados pelo limite de tamanho da resposta da IA.

#### 4.5.3 O que cada documento contém

| Documento | Estrutura gerada |
|---|---|
| **Repasse Semanal** | Data e tópico; **Resumo da Semana** (parágrafo narrativo que cliente ou diretor entendem); **Principais Pontos** com status (Concluído, Em andamento, Em validação, Bloqueado, Cancelado); **Decisões Tomadas**; **Próximos Passos**; assinatura "Gerente de Dados — CITi". |
| **Retrospectiva** (Template 3 CITi) | Cabeçalho (projeto, cliente, data, squad, período e subárea, quando existem); **O que Funcionou**; **O que Não Funcionou**; **Causa Raiz × Impacto** (tabela); **Ações de Melhoria** (máximo duas, em tabela com responsável e prazo, com "A definir" se faltar); **Houve Pedido Fora de Escopo?** (sim ou não e status). Os dados estruturados do gerente têm prioridade e não são reinterpretados. |
| **Review** (Template 2 CITi) | Cabeçalho; **Planejado vs Entregue** (tabela com S/N e causa raiz); **% de itens com "Pronto" cumprido**; **Pedidos do Cliente Fora do Escopo**; **Percepção do Cliente Registrada** (transcrita, sem interpretar); **Sinal de Satisfação** (uma das seis categorias); **Itens que Passam para a Próxima Sprint**. |
| **Planning** | Título "Planning — Sprint N", projeto, cliente, data, squad e período; **Objetivo da sprint**; **Backlog da sprint** (um item por linha, com responsável, prazo e critério de pronto **somente** quando essa informação existe para o item); **Responsabilidades** (tabela só com atribuições explícitas a itens; a simples lista de squad não conta como atribuição); **Riscos previstos** ("Nenhum risco reportado pelo gerente neste momento" quando não há). |
| **Daily** | Data; **O que foi feito desde a última Daily**; **O que será feito até a próxima**; **Impedimentos / Riscos** ("Nenhum impedimento reportado nesta daily"); **Observações adicionais**, só se o anexo trouxe algo novo. |
| **Ata de Reunião** | Data, tópico e andamento; **Participantes e cargos** (sem nomes, usa Gerente de Dados CITi, Analista de Dados CITi e Representante do Cliente); **Tópicos discutidos** (numerados); **Decisões tomadas** (com verbo no infinitivo, incluindo validações do cliente); **Outcomes**; **Outputs**; **Conclusão executiva**. |
| **Log de Decisões** | Título do log técnico do projeto e itens "Sprint X — Decisão" com o **Motivo**, em ordem cronológica. Inclui decisões técnicas, de escopo, de arquitetura e alinhamentos com o cliente. |
| **Onboarding** | Pensado para um novo gerente ou analista: **O que é este projeto**; **Contexto do cliente**; **O que já foi feito** (tabela por sprint) e estado atual; **Stack atual** (só as tecnologias da sprint mais recente); **Decisões importantes**; **Problemas que apareceram**; **Próximos passos imediatos**; **Quem contatar**. A sprint mais recente é o estado atual, e as mudanças detectadas indicam o que foi removido. |
| **Documentação Final** | Template oficial do CITi com nove capítulos: 1 Overview (definição, escopo, dores e objetivos, cronograma, responsáveis); 2 Arquitetura da Solução (requisitos, tecnologias, metodologia, rituais, decisões estratégicas); 3 Projeto de Dados (banco, linhagem dos dados, automações); 4 Qualidade de Dados (dicionário, pipeline de ETL, regras, credenciais); 5 Design de Interfaces; 6 Documentação de Modelo; 7 Interface do Usuário (fluxos, telas, user stories); 8 Deploy; 9 Glossário. |

#### 4.5.4 A aba Documentos do projeto

A aba tem duas sub-abas.

**Por sprint.** Mostra os documentos que pertencem a uma sprint, agrupados em um painel por sprint, com a mais recente primeiro ("Sprint N · M documentos"). Não gera nada aqui: a geração acontece nos chips e botões do card da sprint. Quando está vazia, a tela orienta a gerar Planning, Review, Repasse ou Retrospectiva na aba Sprints.

**Cross-sprint.** Mostra os documentos que olham o projeto como um todo. Tem quatro cards: **Ata de Reunião**, **Log de Decisões**, **Onboarding** e **Documentação Final**, cada um indicando "Não gerado" ou "Gerado em" com a data do último. Abaixo ficam:

- o campo **Observações adicionais (opcional)**;
- o botão **+ Adicionar documento manual** ("Sem custo de IA");
- a pré-visualização do último documento gerado;
- o **Histórico** dos documentos cross-sprint.

Clicar num card abre um painel que explica o quê, para quê, quando e de quais fontes é o documento, com o botão **Gerar documento**. Para documentos de escopo sprint, o painel pede a sprint. Para a Ata, pede que se escolha um arquivo já enviado ("Sprint N · arquivo") ou a opção **ou subir transcrição (PDF)**, com a sprint correspondente. Para os de projeto, só há o botão. O botão fica desabilitado enquanto gera ou se faltar arquivo ou PDF.

Duas coisas fáceis de errar:

- O campo **Observações adicionais** é único na página e vai junto em **toda** geração. Serve para orientar tom, foco ou contexto extra.
- Uma **Ata gerada por PDF** é guardada com a sprint escolhida e aparece em "Por sprint". Uma Ata gerada a partir de um arquivo já enviado fica como **cross-sprint**.

#### 4.5.5 Ver, copiar, editar, mover, excluir e exportar

Cada documento aparece numa linha, na aba Documentos ou no painel Detalhes do card da sprint, com estas ações:

| Ação | O que faz |
|---|---|
| **Ver / Fechar** | Expande ou recolhe o documento renderizado. |
| **Copiar** | Copia o **markdown cru** para a área de transferência. Na pré-visualização do último gerado também existe **Copiar markdown**. |
| **Editar** | Abre uma caixa de texto com o markdown. **Salvar** grava a mudança. Documento vazio não é aceito ("O documento não pode ficar vazio"). A edição vale só para aquele documento: não regenera nada nem altera o arquivo de origem. |
| **Mover sprint** | Informa o número de outra sprint (inteiro maior que zero) e confirma. Também é possível desvincular o documento de qualquer sprint, o que o torna cross-sprint. |
| **Excluir** | Pede confirmação e remove. |
| **Google Docs** | Exporta o documento e abre o resultado numa nova aba. Se falhar, o erro aparece abaixo da linha do documento. |

**Exportação para o Google Docs.** O sistema usa as credenciais e a pasta do Drive configuradas para a subárea do projeto (dados, desenvolvimento ou produto). Os documentos são organizados no Drive assim: pasta da subárea, pasta com o nome do projeto e, dentro dela, uma pasta "Sprint N" (ou "Cross-Sprint"). O título segue o padrão "Tipo do documento — Projeto — Sprint N" (ou "Projeto completo").

O conteúdo vai para um **modelo de documento** do Google Docs, com variações por tipo e por subárea. O texto é convertido (títulos, listas e negrito) e inserido no corpo do modelo. Os campos de cabeçalho (projeto, cliente, squad, data, sprint) são preenchidos, e, para Planning, Review e Retrospectiva, os dados do formulário preenchem as tabelas do modelo. Se a configuração da exportação estiver incompleta, a tela mostra uma mensagem genérica de que a exportação não está disponível.

#### 4.5.6 Documentos manuais, sem IA

O botão **+ Documento** do card da sprint e o **+ Adicionar documento manual** do Cross-sprint abrem a mesma tela. Ela pede:

- **Tipo de documento:** um dos nove tipos ou "Outro (personalizado)", com nome livre, por exemplo "Contrato do Projeto". Tipos personalizados aparecem na interface com o nome digitado.
- **Sprint:** já vem escolhida quando aberto de dentro de uma sprint. Vazio significa cross-sprint.
- **Um arquivo PDF.**

O texto do PDF é extraído **sem IA** e guardado como está, sem formatação em markdown. PDF escaneado, ou sem texto extraível, é recusado com a orientação de usar o Upload livre, que tem leitura por visão.

---

### 4.6 O que cada instrução da IA faz

Em alto nível, estas são as instruções que orientam a IA no ciclo de sprint e o objetivo de cada uma:

| Instrução | Objetivo e regras principais |
|---|---|
| **Extração de arquivos** | Tirar de qualquer artefato do projeto (documento de sprint, ata, transcrição, print de Kanban, código) os oito campos de 4.4.3. Em prints de Kanban, uma tarefa por linha, com responsável, prazo e critério de pronto só se estiverem visíveis. **Não inferir nem inventar.** Na nova tentativa, reforça que a resposta deve ser apenas no formato esperado. |
| **Conferência de tipo** | Classificar o arquivo em uma das oito categorias. É conservadora: **nunca bloqueia sem alta confiança**. |
| **Pré-preenchimento de formulários** | Transformar matéria-prima bruta (pauta, WhatsApp, transcrição, anotações) nos campos de Planning, Daily, Review ou Retrospectiva, para o gerente **revisar**. Extrai só o que está explícito, deixa vazio o que não estiver, usa exatamente uma das seis opções de sinal de satisfação e as categorias de causa raiz de 1 a 7. Não salva nada. |
| **Correlação de tasks com funcionalidades** | Para cada task extraída, apontar a funcionalidade do projeto a que ela pertence, ou nenhuma quando não couber com clareza. Uma funcionalidade pode ter várias tasks. |
| **Geração dos documentos** | Um modelo por tipo de documento, todos no papel de assistente de documentação do CITi, seguindo exatamente a estrutura pedida, dando prioridade aos dados estruturados do gerente e aplicando a regra anti-invenção. Review, Retrospectiva e Documentação Final seguem os templates oficiais do CITi. |
| **Revisão diária de código** | Atuar como revisor técnico sênior: achados de bug, segurança, dívida, testes removidos e credenciais expostas, sempre com a referência exata, sem inventar, no máximo 20, com descrição de negócio e técnica. |


---

## Parte 5 — Métricas, pontuação e performance

Esta parte responde a uma pergunta só: o que o DocuData mede e como cada número é calculado. Ela separa duas famílias de números que costumam ser misturadas: os que dizem se o projeto está fluindo e os que reconhecem a contribuição de cada pessoa.

| Família | Para que serve | Onde aparece | Quem vê |
|---|---|---|---|
| **Saúde do squad e do projeto** (SPI da sprint, throughput, cycle time, CFD, WIP) | Dizer se o projeto está fluindo | Abas **Métricas** e **Painel** do projeto | Gerente, Líder e Owner |
| **Score individual** (Entrega, Gerente, Qualidade, Autonomia, mais o bônus de task extra) | Reconhecer a contribuição de cada operacional | Tela de **Performance** | Só Líder e Owner |

Regra de ouro do sistema: **as métricas de saúde do squad nunca entram no score individual.** SPI da sprint, cycle time e throughput não aparecem em nenhuma das quatro fórmulas da seção 5.4. O motivo é simples: o ritmo do projeto depende de muita coisa que a pessoa não controla, e misturar os dois mundos puniria alguém por um problema do squad.

---

### 5.1 Pontos, previsto e a régua de dificuldade

Tudo o que é "em pontos" no sistema parte de um único conceito: **pontos são o nível de dificuldade da task**, numa régua fixa de quatro degraus.

| Pontos | Rótulo |
|---|---|
| 1 | Simples |
| 2 | Moderada |
| 3 | Complexa |
| 5 | Muito complexa |

Qualquer outro valor é recusado, com a orientação de usar um nível da régua. Tasks antigas, criadas com pontuação fora da régua, são convertidas automaticamente quando reabertas: 1 ou menos vira 1, 2 continua 2, 3 e 4 viram 3, 5 ou mais vira 5. O valor original fica guardado como referência.

**Não existe orçamento de 100 pontos por projeto nem divisão de pontos por sprint.** Isso existiu em versões antigas e foi removido. Criar uma task não é limitado por nenhum orçamento. Os pontos só se somam dentro de uma sprint: não há total do projeto, preço por ponto ou faturamento em pontos.

#### O previsto da sprint

O previsto é o denominador do SPI e responde a "quanto a sprint prometeu entregar". Ele é a soma de duas parcelas:

- **Planejado no início:** pontos das tasks que já estavam na sprint quando ela começou.
- **Surgiu na sprint:** pontos das tasks que entraram depois que a sprint já estava em andamento.

Tasks extras nunca entram no previsto. Em resumo, o previsto é "o que prometemos no início mais o que aceitamos depois".

Como cada task recebe a sua marca:

| Evento | O que acontece |
|---|---|
| A sprint é iniciada (manualmente, ou automaticamente ao confirmar a avaliação da sprint anterior) | O sistema tira uma "foto do início": toda task não extra que está na sprint é marcada como prevista no início. Isso só acontece na primeira vez, então iniciar de novo não "promove" tasks que chegaram depois |
| Uma task entra numa sprint que já foi iniciada (criada nela ou movida para ela) e não é extra | É marcada como surgida na sprint |
| Uma task entra numa sprint que ainda não foi iniciada | Fica sem marca; será fotografada quando a sprint começar |
| Uma task é movida de uma sprint para outra | Perde a marca de prevista no início, porque a foto pertence à sprint de origem |
| Task extra | Nunca entra no previsto |

Uma task removida da sprint depois da foto deixa de contar, porque a conta olha as tasks que estão na sprint agora.

---

### 5.2 A aba Métricas do projeto

A aba Métricas é de gestão: **o operacional não a acessa**. Ela carrega tudo de uma vez, e os blocos aparecem nesta ordem, de cima para baixo:

1. **SPI** (esquerda) e **Throughput** (direita)
2. **Cycle time · distribuição** (histograma e as 5 tasks mais lentas)
3. **CFD** (esquerda) e **SPI por operacional · estimado** (direita)
4. **Entrega por pessoa** (tabela)

#### 5.2.1 SPI da sprint

O SPI diz quanto do previsto da sprint foi concluído.

- **Fórmula:** pontos realizados divididos pelo previsto, com 3 casas decimais.
- **Pontos realizados:** soma dos pontos das tasks da sprint que estão na coluna **Concluída**, sem contar as extras.
- **Sem previsto:** se o previsto é zero, não há SPI para mostrar.
- **Janela:** uma sprint por vez. Não existe SPI acumulado do projeto.
- **Atualização:** o número é calculado ao vivo a cada abertura da aba.
- **Na tela:** o card mostra só a última sprint com SPI, com o número grande e barras de "Previstos x Realizados". A comparação entre sprints fica no Throughput.

Como ler:

- **1,0 significa que o previsto foi entregue.** Abaixo de 1, sobrou task aberta. Pode passar de 1 em dado antigo, quando uma task concluída não tinha nenhuma das duas marcas e por isso conta no realizado, mas não no previsto.
- A foto vale para o previsto. O realizado muda enquanto a sprint está aberta e continua sendo recalculado ao vivo depois do fechamento. Para ver o número congelado no fechamento existe a tabela "Entrega por pessoa" (5.2.7).
- Task extra concluída não infla o SPI.

#### 5.2.2 Saúde do SPI (semáforo)

Cada sprint tem um semáforo de saúde, calculado com o mesmo SPI (realizado dividido pelo previsto, sem extras):

| SPI | Status |
|---|---|
| 0,9 ou mais | Verde |
| De 0,7 até menos de 0,9 | Amarelo |
| Menos de 0,7 | Vermelho |
| Sem previsto | Não muda; permanece o valor manual, se houver |

O semáforo é recalculado **depois que uma task vai para Concluída**, seja por aprovação do gerente, seja por mover direto. Ele não é recalculado na reabertura de uma task, então pode ficar defasado até a próxima conclusão. O gerente pode sobrescrever o status manualmente (verde, amarelo, vermelho ou nenhum) e registrar um plano de correção, mas a próxima conclusão de task recalcula e sobrescreve.

Na tela, as mesmas faixas aparecem como três legendas: "≥ 0,9 saudável", "0,7 a 0,9 atenção" e "< 0,7 crítico".

#### 5.2.3 Throughput

O throughput mostra, para cada sprint do projeto, quantas tasks existiam, quantas foram concluídas e quantos pontos foram concluídos.

- **Cálculo:** contagem simples das tasks da sprint; "concluídas" são as que estão na coluna **Concluída**.
- **Extras:** diferente do SPI, as tasks extras **entram** nesta contagem.
- **Na tela:** barras agrupadas "Total" e "Concluídas" por sprint. Os pontos concluídos são calculados, mas a aba não os desenha.
- **Sem tasks:** aparece "Nenhuma task registrada ainda."

Como ler: uma queda de throughput de uma sprint para outra sugere tasks grandes demais ou bloqueios.

#### 5.2.4 Cycle time

O cycle time mede quanto tempo uma task levou de fato em execução.

**Definição:** é o tempo entre a **última vez** que a task entrou em **Em Andamento** e a **última vez** que ela entrou em **Concluída**.

Por que a diferença entre os dois momentos, e não só o tempo da última fase: o tempo da fase imediatamente anterior a Concluída contaria só a espera pela aprovação do gerente numa task que passou por **Pendente de Aprovação**. A task com mais cerimônia pareceria a mais rápida. Medir do início da execução ao fim evita essa distorção.

Casos de borda:

| Situação | O que acontece |
|---|---|
| Task concluída sem registro de entrada em Em Andamento (por exemplo, puxada da fila no modo PULL, que não registra essa transição) | Usa o tempo da fase anterior à conclusão como alternativa |
| Intervalo negativo (fim antes do início) | Também usa essa alternativa |
| Duração zero ou desconhecida | A task fica de fora do histograma e das estatísticas |
| Task reaberta e ainda não reconcluída | Sai do cálculo, pois só entram tasks que estão em Concluída agora |
| Unidade | Horas, com 1 casa decimal |

**Papel do momento do "puxar":** no modo PULL, quando uma task é puxada da fila e ainda não tem nenhuma movimentação anterior, o tempo passa a contar a partir do momento em que ela foi puxada, e não de quando foi criada. Assim o tempo de espera na fila não vira "tempo de trabalho". Se a task é devolvida ou rejeitada, esse momento é zerado.

**Percentis:** o sistema mostra a **mediana** (50% das tasks levaram até esse tempo) e o **percentil 85** (85% das tasks levaram até esse tempo). Com uma única task, o mesmo valor aparece nos dois; sem tasks, nenhum valor. Na tela: "mediana Xh", "85% em até Xh", a "Média" (média simples das durações do histograma) e "N tasks com histórico".

O percentil 85 é o número para prometer prazo ("só 15% das tasks demoraram mais que isso"); a mediana descreve o caso típico.

**O histograma** agrupa as tasks em faixas: menos de 8h, 8 a 24h, 1 a 3 dias, 3 a 7 dias e mais de 7 dias (faixas vazias somem). A lista **Tasks mais lentas** mostra as 5 maiores durações, e a cor sinaliza o tamanho: cinza normal, **âmbar a partir de 72 horas** e **vermelho a partir de 120 horas**.

O histograma pode ser filtrado por sprint, mas a aba usa sempre o projeto inteiro.

#### 5.2.5 CFD

Apesar do nome, este gráfico **não é um diagrama de fluxo cumulativo**. É uma foto, sprint por sprint, de quantas tasks estão hoje em cada coluna: **Planejado**, **Em Andamento**, **Pendente de Aprovação** e **Concluída**. Sprints sem tasks são omitidas, e as quatro áreas são empilhadas.

Como ler: se a área de "Em andamento" cresce de sprint em sprint sem que a de "Concluída" cresça junto, há gargalo.

Como a foto é lida ao vivo, uma sprint antiga que teve uma task reaberta hoje mostra o estado de hoje, não o do último dia dela.

#### 5.2.6 SPI por operacional · estimado

Este bloco mostra, por operacional ativo do projeto, quantos pontos foram atribuídos a ele, quantos realizou e quantas tasks concluiu.

- **Fórmula do SPI estimado:** pontos realizados divididos pelos pontos atribuídos, com 3 casas.
- **Janela:** o projeto inteiro, todas as sprints, todas as colunas, **incluindo as tasks extras**.
- **Natureza:** é uma estimativa interina. **Não é o número que alimenta o ranking** (esse é o da tabela de Entrega por pessoa, a seguir).
- **Na tela:** barras "Atribuídos" (ou "Puxados", no modo PULL) contra "Realizados" por pessoa. O SPI em si não é desenhado.

#### 5.2.7 Entrega por pessoa (SPI travado)

Esta tabela mostra a Entrega de cada operacional a partir do que já foi **travado no fechamento das sprints**. O Gerente passou a vê-la em 2026-09-07, por decisão do Líder, para sustentar a conversa de feedback.

A conta soma, nas sprints fechadas da pessoa naquele projeto, os pontos concluídos, os pontos penalizados e os pontos alocados. A Entrega é:

- (pontos concluídos menos pontos penalizados, nunca abaixo de zero) dividido pelos pontos alocados, vezes 100, limitado a 100.

| Coluna na tela | O que mostra |
|---|---|
| **Entrega** | Valor de 0 a 100, colorido pelas mesmas faixas do semáforo (aplicadas à nota dividida por 100) |
| **Sprints avaliadas** | Quantas sprints fechadas a pessoa tem neste projeto |
| **Pontos perdidos por atraso** | Pontos penalizados (vermelho se maior que zero) |

Só entra o que já foi travado pelo fechamento. A lista traz só operacionais ativos do projeto, em ordem alfabética. Um traço ("—") significa que nada foi alocado à pessoa. Quando a pessoa participa de vários projetos, o valor consolidado é a média simples entre os projetos.

#### 5.2.8 Métricas de fluxo das funcionalidades (aba Painel) e limite de WIP

O card **Métricas de fluxo** da aba Painel olha para **funcionalidades**, não para tasks:

| Métrica | Como é calculada |
|---|---|
| **WIP agora** | Número de funcionalidades **Em Andamento** ou **Em Ajuste** neste momento |
| **Cycle time (dias)** | Para cada funcionalidade concluída, do primeiro momento em Em Andamento até a última conclusão (só vale se o fim for depois do início). Mostra mediana e percentil 85 |
| **Throughput por semana** | Funcionalidades concluídas (com cycle time calculável) divididas pelo número de semanas desde que a primeira funcionalidade foi criada, com mínimo de 1 semana |

Uma funcionalidade em andamento há mais de 7 dias sem movimentação de task nem de status passa a aparecer como "travada" no bloco de atenção do Painel.

**Limite de WIP:** a gestão pode configurar limites por projeto. Ao mover ou puxar uma task para **Em Andamento**, o sistema recusa a ação se o limite da coluna (total do projeto) ou o limite da pessoa já foi atingido. Os dois limites são opcionais; sem valor, não há limite. **Em projetos PULL, o limite por pessoa é sempre 1**, para que cada pessoa trabalhe numa task por vez.

**Acompanhamento de projetos:** a tela de Acompanhamento tem a sua própria visão de SPI, com a mesma regra de previsto da seção 5.1, e o selo "projeto em risco" (SPI da última sprint fechada abaixo de 0,7, entre outras regras). Ela é descrita em outra parte desta Bíblia.

---

### 5.3 Pontuação: do Kanban ao snapshot travado

A pontuação acontece **uma única vez, no fechamento da sprint**. Não é um contador que sobe e desce durante a semana: no fechamento, o sistema lê o estado final de tasks, movimentações, reaberturas, travamentos e avaliações do gerente e grava **uma linha congelada por operacional**, o chamado snapshot.

#### 5.3.1 Quem é elegível

É elegível **quem está vinculado ao projeto no momento do fechamento**: a data de entrada já passou e a data de saída não existe ou ainda está no futuro. Todo vinculado ganha uma linha, **mesmo sem nenhuma task** na sprint. Isso corrigiu um problema do modo PULL, em que quem não puxava nada simplesmente sumia.

#### 5.3.2 O que cada task vira

| Situação da task | Efeito |
|---|---|
| **Extra** e concluída | Não entra em Entrega. Soma bônus de task extra para quem concluiu e conta como task concluída em Qualidade. Aparece como "bônus extra" no extrato |
| **Extra** e não concluída | Ignorada: não é alocada nem gera bônus |
| Regular e concluída | Pontos concluídos **e** alocados para quem completou, mais uma task concluída em Qualidade. Aparece como "entrega concluída" no extrato |
| Regular, não concluída, **esperando o cliente** | Não conta como alocada de ninguém (seção 5.3.6) |
| Regular, não concluída, normal | Pontos alocados ao responsável atual: ele "pegou" e não entregou |

**Quem recebe os pontos de uma task concluída:** quem estava com ela **no momento em que foi concluída**, e não o dono atual. Por isso reatribuir uma task no meio da sprint não exige nenhum ajuste. Se não houver registro dessa movimentação, vale o responsável atual.

#### 5.3.3 Marco de corte: nada é contado duas vezes

Eventos com data (reaberturas, bloqueios resolvidos, travamentos, notas de commit) só entram se tiverem acontecido **depois do último fechamento do projeto**. Sem fechamento anterior, todo o histórico entra. Ao reabrir um fechamento (5.6), o marco volta sozinho ao estado anterior.

Eventos de uma sprint que **já foi fechada** (uma task reaberta, um bloqueio resolvido depois) são redirecionados para a **sprint ativa** e entram no fechamento seguinte. Se não houver sprint ativa, o evento fica só no histórico.

#### 5.3.4 Entrega no modo ATRIBUICAO

No modo ATRIBUICAO, cada linha guarda os pontos concluídos, os alocados e os penalizados. A nota de Entrega só é calculada na agregação (5.4):

- (pontos concluídos menos pontos penalizados, nunca abaixo de zero) dividido pelos pontos alocados, vezes 100, com teto de 100.

O teto existe porque entregar além do que pegou não pontua acima de 100. Sem pontos alocados na janela, a dimensão fica **indisponível**; não vira zero.

**Penalidade de travamento.** Todo dia o sistema verifica as tasks e marca como travada aquela que ficou em andamento por tempo demais, segundo esta regra:

- **Limite em dias = pontos da task vezes 1,5.**

| Pontos | Limite |
|---|---|
| 1 | 1,5 dia |
| 2 | 3 dias |
| 3 | 4,5 dias |
| 5 | 7,5 dias |

O relógio conta a partir do momento em que a task entrou em Em Andamento (ancorado quando a sprint da task já começou). Tasks em **Planejado** ou **Em Andamento** entram na varredura; tasks esperando o cliente são puladas (relógio pausado); uma task já marcada não é marcada de novo.

Regras da penalidade:

- Só pune a task que **foi concluída**. Uma task que travou e nunca foi entregue já não está entre as concluídas, e descontar de novo puniria as outras entregas da pessoa.
- O gerente pode **dispensar** o alerta na task, e a penalidade some. Marcar a task como espera do cliente também dispensa os alertas abertos.
- A penalidade desconta de **Entrega, nunca de Autonomia**.
- Cada travamento aparece como "penalidade de travamento" (pontos negativos) no extrato. Devolver uma task travada registra uma "penalidade de devolução" no extrato, apenas como histórico, porque a conta de Entrega só olha tasks concluídas.

#### 5.3.5 Entrega no modo PULL

No modo PULL a avaliação é sempre **relativa ao squad**: a nota de Entrega da sprint compara a pessoa com a média de pontos concluídos pelos vinculados, e é calculada e congelada no fechamento. (O modo ATRIBUICAO usa sempre a avaliação por pontos atribuídos, descrita acima.)

A conta, passo a passo:

1. **Base da média:** todos os vinculados, menos os isentos (quem só tinha task esperando o cliente e concluiu zero).
2. **Denominador bruto:** média de pontos concluídos dessa base.
3. **Denominador:** o maior entre o denominador bruto e o piso (padrão 1).
4. **Nota bruta:** pontos concluídos da pessoa divididos pelo denominador.
5. **Nota de Entrega:** a nota bruta, limitada ao teto (padrão 1,5), multiplicada por 100 e dividida pelo teto. O resultado fica entre 0 e 100.

| Parâmetro | Padrão | Observação |
|---|---|---|
| Piso de pontos | **1** | Editável por projeto; precisa ser maior que zero |
| Teto | **1,5** | Editável por projeto |

O piso é **técnico**: evita dividir por zero ou por uma média minúscula. Não é o "piso mínimo por pessoa" da proposta institucional. Um ponto é provavelmente baixo demais na prática, e a configuração existe justamente para ajustar isso.

Casos especiais:

- **Sem task regular disponível** (só extras, só tasks esperando cliente, ou sprint vazia), a Entrega fica sem dado para todos, e não zero.
- **Isento:** quem só tinha task esperando o cliente e não concluiu nada fica sem dado e **sai da média** do squad.
- Na janela, a Entrega no PULL é a média simples das notas das sprints (piso e teto já aplicados). Se a janela mistura sprints dos dois modos, porque o projeto trocou de modo, as duas fórmulas são combinadas por **média ponderada pelo número de sprints de cada regime**.

#### 5.3.6 Dependência do cliente e "Entrega sem dado"

Uma task marcada como bloqueada por dependência do **cliente** e **não concluída** no fechamento recebe este tratamento:

| Efeito | Detalhe |
|---|---|
| Não entra nos pontos alocados | O atraso do cliente não pode zerar a Entrega de ninguém |
| Não conta em Autonomia | Quem destrava é o cliente |
| Pausa o relógio de travamento | Ao destravar, o relógio recomeça |
| Dispensa os travamentos abertos | Os alertas já abertos da task deixam de valer |
| Só o gerente marca | O operacional não altera bloqueios |
| Se o cliente destravou e a task foi concluída | Conta normalmente |

Quando a pessoa fica sem nada alocado, a Entrega fica **sem dado** e o score é calculado com as outras dimensões. Na aba Métricas, o traço "—" tem uma explicação ao passar o mouse. A contagem de "Sprints avaliadas" **não muda**: a sprint continua contada.

#### 5.3.7 Bônus de task extra e o que mais é congelado

**Task extra** é a concedida depois que o operacional zerou a fila: ele usa o botão "Quero mais uma task" e o gerente cria uma task marcada como extra. Ela não entra no previsto nem em Entrega; se for concluída até o fechamento, vira bônus:

- **Bônus = soma dos pontos de task extra concluídos na janela, vezes 1,0, limitado a 5,0.**

O bônus é somado ao score final (5.4.3), com teto de 5 pontos de score por janela. O teto existe para que o ranking não vire "quem pediu mais task".

O que cada linha congelada de uma pessoa guarda no fechamento:

| Informação | Conteúdo |
|---|---|
| Média do gerente | Média das notas da avaliação semanal (as seis perguntas da seção 5.5), com 2 casas |
| Nota da pergunta 3 | Alimenta metade da Autonomia |
| Dados de Entrega | Pontos concluídos, alocados e penalizados; no PULL, também a nota relativa, os pontos da pessoa e o denominador |
| Pontos de task extra | Extras concluídas, para o bônus |
| Reaberturas e tasks concluídas | Reaberturas no período e total de tasks concluídas (inclui extras), para Qualidade |
| Bloqueios | Total de bloqueios resolvidos no período e quantos a própria pessoa resolveu, para Autonomia |
| Nota de commit | Média das notas de 0 a 10 dos commits do projeto no período |
| Modo da sprint | O modo de trabalho e de avaliação vigentes ficam gravados na própria sprint, para que períodos ATRIBUICAO e PULL continuem identificáveis mesmo que o projeto troque de modo depois |

**Extrato auditável:** cada ponto ganho ou descontado vira um evento no extrato da pessoa (entrega concluída, bônus extra, penalidade de travamento, reabertura com 0 pontos, penalidade de devolução). Gerente e Líder podem consultá-lo. A gravação do extrato é complementar e, se falhar, não desfaz o fechamento.

---

### 5.4 Performance: as quatro dimensões e o score final

A performance é calculada **quando o Líder abre a tela de Performance**, a partir dos snapshots congelados. Nada é recalculado a partir do Kanban nesse momento. Por isso, mudar um peso muda o ranking na leitura seguinte, sem reprocessar nenhuma sprint.

#### 5.4.1 Pesos por tipo de projeto

Cada projeto tem um tipo, **padrão** ou **consultoria/discovery**, e cada tipo tem seus pesos:

| Dimensão | Projeto padrão | Consultoria / discovery |
|---|---|---|
| Avaliação do Gerente | **0,50** | **0,50** |
| Entrega e Confiabilidade | **0,18** | **0,24** |
| Qualidade Técnica | **0,18** | **0,12** |
| Autonomia | **0,14** | **0,14** |

O **peso do gerente é 50% nos dois tipos**, por decisão confirmada. A dimensão **Evolução foi removida** em 2026-09-23, junto com a pergunta de evolução do questionário. Hoje ela tem peso zero e nenhuma conta a usa.

Existem ainda dois pesos internos às dimensões:

| Peso interno | Padrão | Uso |
|---|---|---|
| Nota de commit dentro de Qualidade | 0,50 | O resto é retrabalho |
| Pergunta 3 dentro de Autonomia | 0,50 | O resto é o sinal de bloqueio |

A liderança pode alterar todos esses pesos, mas hoje não há tela para isso: a alteração é feita diretamente na configuração. Sem pesos configurados, a tela de Performance não funciona.

#### 5.4.2 As quatro dimensões

Cada dimensão vai de 0 a 100 e é calculada **por projeto**, sobre os snapshots da janela. As fórmulas são absolutas: nenhuma compara a pessoa com as outras (a única exceção é a Entrega no modo PULL, que é relativa ao squad por definição).

**1. Entrega e Confiabilidade**

- **No ATRIBUICAO:** pontos concluídos menos pontos penalizados (nunca abaixo de zero), divididos pelos pontos alocados, vezes 100, com teto de 100. Sem pontos alocados, a dimensão fica indisponível.
- **No PULL:** média das notas relativas de Entrega das sprints da janela. Sem nenhuma nota, fica indisponível.
- **Janela mista:** média ponderada pelo número de sprints de cada regime.

**2. Avaliação do Gerente**

- A média das notas do gerente nas sprints avaliadas da janela (escala de 0 a 5), vezes 20, com teto de 100. Sem nenhuma avaliação, fica indisponível.

**3. Qualidade Técnica**

A Qualidade combina duas fontes:

- **Retrabalho:** 1 menos (reaberturas divididas pelas tasks concluídas), nunca abaixo de zero, vezes 100. Sem tasks concluídas, esta fonte fica indisponível.
- **Nota de commit:** média das notas de commit (0 a 10) vezes 10, com teto de 100. Sem notas, esta fonte fica indisponível.
- **Qualidade:** 0,5 vezes a nota de commit mais 0,5 vezes o retrabalho.

Se falta uma das fontes, usa-se a que sobrou. Se faltam as duas, a dimensão fica indisponível. **Quem não concluiu nada fica sem nota de Qualidade**; ela não vira 100, para não premiar quem não entregou. Em projetos de consultoria não há nota de commit, então a Qualidade é o retrabalho puro.

**Reabertura** é uma task que estava em Concluída e voltou para Em Andamento. Voltar para Planejado não conta.

**4. Autonomia**

Autonomia também combina duas fontes:

- **Sinal de bloqueio:** bloqueios resolvidos pela própria pessoa divididos pelo total de bloqueios, vezes 100. Sem bloqueios na janela, esta fonte fica indisponível.
- **Sinal do gerente:** média das notas da pergunta 3 vezes 20, com teto de 100. Sem avaliação, fica indisponível.
- **Autonomia:** 0,5 vezes o sinal do gerente mais 0,5 vezes o sinal de bloqueio.

Sem bloqueio na janela, a Autonomia é só a pergunta 3; sem avaliação, só o sinal de bloqueio; sem nenhum dos dois, fica indisponível. A pergunta 3 entrou porque bloqueio quase nunca é registrado (antes disso, a Autonomia era sempre 100). Task parada por tempo **não** entra aqui, e bloqueio de cliente também não.

#### 5.4.3 Como o score final é montado

O score final agrega as dimensões disponíveis:

- **Score base** = soma de (peso vezes nota) das dimensões disponíveis, dividida pela soma dos pesos dessas mesmas dimensões.
- **Score final** = score base mais o bônus de task extra, limitado a 100, com 2 casas decimais.

**Quando falta uma dimensão, ela não vira zero:** sai da conta, e o resultado é dividido pela soma dos pesos que sobraram. Se nenhuma dimensão está disponível, a pessoa **não aparece** no ranking daquela janela.

Uma consequência importante: uma pessoa medida por 3 dimensões fica na mesma tabela que outra medida por 4, e as duas não são totalmente comparáveis. É por isso que a trava de fechamento (5.6) existe: para que a nota do gerente nunca falte.

#### 5.4.4 Janelas e ranking

| Janela | Rótulo na tela | Sprints consideradas |
|---|---|---|
| Sprint | Última sprint | 1 |
| Quinzenal | Últimas 2 sprints | 2 |
| Mensal | Últimas 4 sprints | 4 |

- **Janelas contam sprints, nunca dias.** São os snapshots mais recentes da pessoa.
- Se a pessoa tem menos sprints que o tamanho da janela, o sistema calcula com o que existe e a tela mostra o aviso **"Janela parcial"**. Uma nota parcial é só indicativa.
- **O ranking é por projeto** (decisão de 2026-09-23). Quem está em dois projetos aparece separadamente em cada um; não há média entre projetos. Dentro de um projeto, cadastros duplicados da mesma pessoa são unidos pelo e-mail; sem e-mail, cada cadastro é uma pessoa. Operacional desativado sai na hora.
- Projetos aparecem por ordem de nome e as pessoas por score final decrescente em cada janela. Projeto sem ninguém com nota é omitido.
- **Top performer:** o primeiro colocado de cada projeto e janela recebe o destaque verde e o aviso **"Maior contribuição"**. Não há critério de empate nem nota mínima: é simplesmente a posição 1. O anúncio ao time, a cada duas semanas e só do destaque, é feito pela liderança fora do sistema.
- Sprints em que a pessoa **não alocou nenhum ponto entram** na sequência. A linha existe com Entrega sem dado, e o score usa as demais dimensões.

**A tela de Performance** só aparece para Líder e Owner; as demais pessoas veem "Acesso restrito a Líder e Owner". Cada pessoa é um cartão com a posição, o nome, quatro barras (Entrega, Gerente, Qualidade e Autonomia, com "—" quando indisponível) e a nota final em destaque.

---

### 5.5 Avaliação semanal do gerente

O gerente avalia **cada operacional vinculado, a cada sprint**, numa escala inteira de **0 a 5**. São **6 perguntas, todas obrigatórias** (não há "não sei"). A primeira muda de texto conforme o modo do projeto.

| # | Pergunta | Para onde vai |
|---|---|---|
| 1 | ATRIBUICAO: "Entregou o que se comprometeu dentro do combinado nesta sprint?" / PULL: "Puxou e entregou num ritmo consistente?" | Média do gerente |
| 2 | "A qualidade da entrega precisou de pouca ou nenhuma correção?" | Média do gerente |
| 3 | "A pessoa destravou sozinha antes de te escalar?" | Média do gerente **e** metade da Autonomia |
| 4 | "A comunicação da entrega foi clara a ponto de você não precisar perguntar?" | Média do gerente |
| 5 | "Ajudou, desbloqueou ou ensinou outro membro nesta sprint?" | Média do gerente |
| 6 | "Trouxe algo além do que foi pedido?" | Média do gerente |

A média do gerente é a média simples das seis notas, com 2 casas, congelada no fechamento. A dimensão Gerente é essa média vezes 20.

Peso aproximado de cada pergunta no score de um projeto padrão: 50% dividido por 6, ou cerca de 8,3% cada. A pergunta 3 pesa mais 7% (metade dos 14% de Autonomia) quando não houve bloqueio.

#### Fluxo na tela

1. No card da sprint, o item **Avaliação Semanal** abre a lista de pendências e, para cada pessoa, o questionário.
2. Se a mesma pessoa já foi avaliada em **outro projeto**, o sistema oferece "Reaproveitar avaliação de X em dd/mm?". O botão **Usar essas respostas** preenche as seis notas com a última avaliação encontrada (busca pelo e-mail). O reaproveitamento é registrado e entra na conta com o mesmo peso de uma avaliação nova.
3. Ao enviar, a avaliação da pessoa naquela sprint é criada ou atualizada. Se a sprint já está fechada, a nota nova é refletida no snapshot, para chegar ao ranking.
4. Sem pendências, o botão **Confirmar Avaliação Semanal** dispara o fechamento (5.6).

**Janela de correção de 48 horas:** ao criar a avaliação, o sistema dá 48 horas para reenviar o questionário. Depois disso, o reenvio é recusado com a mensagem de que a janela de edição de 48h já encerrou. O prazo conta da **criação**, não da última edição.

**Correção posterior e histórico de edições:** a tela de Avaliações (acesso de Gerente, Líder e Owner) lista todas as avaliações, com projeto, sprint, avaliador, as seis notas, a média vezes 20 e um resumo das edições. Há filtros por projeto e por sprint.

- A correção feita por essa tela **não tem prazo de 48h**: serve para corrigir uma nota dada errado a qualquer tempo.
- Exige um **motivo** preenchido, é recusada se nenhuma nota mudou e mantém o avaliador original.
- Cada correção grava um registro com as notas antes e depois, o motivo, quem editou e a data, e o snapshot é atualizado.
- Na tela aparece "editada por X em dd/mm" e o botão **Histórico (N)**, que mostra as edições da mais recente para a mais antiga.

**Contador "N/M" no card da sprint:** M é quantos operacionais estão vinculados ao projeto agora; N é quantos desses já têm avaliação (só conta quem ainda é elegível).

---

### 5.6 Fechamento de sprint

O fechamento **é** a confirmação da Avaliação Semanal. É o único momento em que o dado bruto vira pontuação travada.

**Pré-condição:** nenhuma avaliação pendente. Se houver, o sistema recusa e lista os nomes: "Ainda há avaliações pendentes". "Pendente" é quem está vinculado ao projeto naquele momento e não tem avaliação para a sprint.

**O que acontece, em ordem:**

1. **Pontuação é calculada e travada.** Se a sprint já tem linhas travadas, nada é recalculado (isso protege contra clique duplo). O sistema grava o modo vigente na sprint, aplica o marco de corte (5.3.3), define quem completou cada task, aloca pontos, calcula penalidades, bônus, reaberturas, bloqueios, nota de commit e eventos tardios, e grava **uma linha por operacional**, seguida do extrato.
2. **A sprint é marcada como fechada.** O card passa de "Em aberto" para **"Fechada"**.
3. **A próxima sprint é iniciada**, se existir e ainda não tiver começado: o sistema tira a foto do previsto, ancora o relógio de travamento das tasks que já estavam nela e trava o nível das tasks (classificador). Se essa etapa falhar, o fechamento continua valendo.

**O que fica congelado:** as linhas de cada operacional (5.3.7) e o modo da sprint. Depois do fechamento, nada é reescrito, **exceto** (a) os campos do gerente, quando alguém cria ou edita uma avaliação, e (b) os eventos tardios empurrados para a sprint ativa.

**Reabertura do fechamento:** só Líder ou Owner podem reabrir. No card da sprint, o menu "···" tem o item **Reabrir fechamento**, visível só para Líder e Owner e só quando a sprint está fechada.

| Situação | Resposta |
|---|---|
| Sprint inexistente | Recusado, não encontrada |
| Sprint não fechada | Recusado: "Esta sprint não está fechada." |

Ao reabrir, o sistema apaga as linhas travadas da sprint, devolve à fila os eventos tardios que tinham sido redirecionados para ela e tira o status de fechada. **As avaliações do questionário não são apagadas**: o gerente não responde tudo de novo e a janela de 48h segue valendo. O marco de corte se ajusta sozinho. O extrato de pontos daquela sprint não é apagado. Reabrir é conserto, não rotina.

---

### 5.7 Quem vê o quê e as proteções contra manipulação

#### Sigilo

| Recurso | Owner | Líder | Gerente | Operacional |
|---|---|---|---|---|
| Ranking e score final (Performance) | sim | sim | não | não |
| Reabrir fechamento | sim | sim | não | não |
| Aba Métricas e Painel do projeto | sim | sim | sim | não |
| Entrega por pessoa e extrato de pontos | sim | sim | sim | não |
| Questionário e tela de Avaliações | sim | sim | sim | não |
| Kanban, tasks, sprints | sim | sim | sim | só nos projetos em que está vinculado |

- O Gerente produz o insumo (as seis notas) e vê a entrega consolidada do projeto, mas **nunca vê o score final nem a posição de ninguém**.
- Cada abertura da tela de Performance é **registrada em auditoria**: quem abriu e quando.
- Pesos, fórmulas e notas individuais **não são divulgados ao time**. O documento público "Como sua contribuição é acompanhada" descreve só as direções, sem números. Os detalhes de política estão no documento de metodologia de performance.

#### Proteções contra manipulação

Princípio: **contagem de task, de commit e de linha é proteção, nunca moeda.** Uma métrica de volume só é admitida se outra dimensão punir a tentativa de manipulá-la. Nenhuma dessas contagens está nas quatro fórmulas; só pontos, e só como proporção.

| Tentativa | O que a segura |
|---|---|
| Pegar poucas tasks para ter 100% | Teto de 100 em Entrega; a leitura do gerente enxerga o volume baixo |
| Pegar muitas e entregar metade | A Entrega despenca, porque o que foi alocado cresce |
| Segurar task por semanas | Travamento: 1,5 dia por ponto, e a task concluída depois do alerta perde seus pontos de Entrega (a menos que o gerente dispense) |
| Pedir task extra sem parar | Bônus com teto de 5 pontos de score; quem concede é o gerente |
| Não concluir nada para escapar de Qualidade | Qualidade fica sem dado, mas a Entrega vai a zero e pesa mais |
| Marcar concluída sem estar | O checklist de critério de pronto bloqueia a conclusão; reabertura derruba a Qualidade |
| Nunca registrar bloqueio | A pergunta 3 sustenta metade da Autonomia (ou toda ela) |
| Commit trivial em volume | A nota é a média por commit, não a soma |
| Gerente inflar notas | Só a calibração entre gerentes (defesa social; o sistema não detecta) |
| Fechar a semana com nota faltando | Trava de fechamento: pendências bloqueiam a confirmação |

Outros mecanismos de integridade: tasks que exigem aprovação do gerente só saem de **Pendente de Aprovação** por aprovação ou rejeição dele; o operacional não altera pontos, responsável nem bloqueio; e os eventos com data mais o marco de corte evitam a dupla contagem.

---

### 5.8 Exemplo numérico do começo ao fim

O cenário é o da **Maria**, num projeto **padrão** no modo ATRIBUICAO, com a janela **"Últimas 2 sprints"** (sprints 12 e 13). Os números abaixo foram conferidos rodando as contas reais do sistema.

#### a) O que está congelado nas duas sprints

| Informação | Sprint 12 | Sprint 13 |
|---|---|---|
| Pontos alocados | 14 | 10 |
| Pontos concluídos | 12 | 10 |
| Pontos penalizados | 0 | 2 (uma task de 2 pontos concluída depois do alerta, sem dispensa) |
| Média do gerente | 4,17 | 4,50 |
| Nota da pergunta 3 | 4 | 5 |
| Tasks concluídas | 6 | 4 |
| Reaberturas | 1 | 0 |
| Bloqueios totais | 3 | 1 |
| Bloqueios resolvidos pela própria pessoa | 2 | 1 |
| Nota de commit (média) | 7,5 | 8,5 |
| Pontos de task extra | 0 | 0 |

#### b) As quatro dimensões

| Dimensão | Conta | Resultado |
|---|---|---|
| Entrega | (12 + 10 − 2) ÷ (14 + 10) × 100 = 20 ÷ 24 × 100 | **83,33** |
| Gerente | média de 4,17 e 4,50 = 4,335, vezes 20 | **86,70** |
| Qualidade | retrabalho = (1 − 1 ÷ 10) × 100 = 90; commit = média de 7,5 e 8,5 = 8,0, vezes 10 = 80; 0,5 × 80 + 0,5 × 90 | **85,00** |
| Autonomia | bloqueio = 3 ÷ 4 × 100 = 75; pergunta 3 = média de 4 e 5 = 4,5, vezes 20 = 90; 0,5 × 90 + 0,5 × 75 | **82,50** |

#### c) Score final (pesos de projeto padrão)

| Dimensão | Nota | Peso | Contribuição |
|---|---|---|---|
| Gerente | 86,70 | 0,50 | 43,35 |
| Entrega | 83,33 | 0,18 | 15,00 |
| Qualidade | 85,00 | 0,18 | 15,30 |
| Autonomia | 82,50 | 0,14 | 11,55 |
| **Total** (soma dos pesos = 1,00) | | | **85,20** |

#### d) Variações

| Variação | Resultado |
|---|---|
| Maria concluiu uma task **extra** de 3 pontos na sprint 13 (bônus = 3 × 1,0, limitado a 5,0 = 3,0) | 85,20 + 3,00 = **88,20** |
| Mesmo histórico num projeto de **consultoria** (pesos 0,50 / 0,24 / 0,12 / 0,14, mantendo Qualidade em 85) | **85,10** |
| Consultoria de verdade (sem nota de commit, Qualidade = retrabalho puro = 90) | 43,35 + 20,00 + 10,80 + 11,55 = **85,70** |
| **Sem avaliação do gerente** nas duas sprints: Gerente some e a Autonomia cai para 75,00 (só bloqueio). Sobram Entrega, Qualidade e Autonomia, com pesos 0,18 + 0,18 + 0,14 = 0,50: (15,00 + 15,30 + 10,50) ÷ 0,50 | **81,60** |
| Sem os 2 pontos de atraso (Entrega = 22 ÷ 24 = 91,67) | 43,35 + 16,50 + 15,30 + 11,55 = **86,70** (o atraso custou 1,50 ponto de score) |

#### e) Exemplo de SPI e semáforo (sprint 12)

Foto do início: três tasks de 5, 3 e 2 pontos, somando 10. No meio da sprint surge uma task de 2 pontos. Uma task **extra** de 3 pontos é concedida. No fim, as quatro tasks regulares são concluídas, e a extra também.

| Item | Conta | Resultado |
|---|---|---|
| Previsto | 10 + 2 (a extra não entra) | 12 |
| Realizado | 5 + 3 + 2 + 2 (a extra concluída não entra) | 12 |
| SPI | 12 ÷ 12 | 1,000, **verde** |

Se a task de 2 pontos que surgiu tivesse ficado aberta, o realizado seria 10 e o SPI seria 10 ÷ 12 = 0,833, com semáforo **amarelo** (de 0,7 até menos de 0,9).

#### f) Exemplo PULL (Entrega relativa ao squad)

Squad de 3 vinculados, projeto PULL com piso 1 e teto 1,5. Pontos concluídos na sprint: Ana 6, Bia 2, Caio 0.

O denominador bruto é (6 + 2 + 0) ÷ 3 = 2,667, e como é maior que o piso de 1, o denominador fica em 2,667.

| Pessoa | Conta | Nota de Entrega |
|---|---|---|
| Ana | 6 ÷ 2,667 = 2,25, limitado ao teto de 1,5; 1,5 × 100 ÷ 1,5 | **100,00** |
| Bia | 2 ÷ 2,667 = 0,75; 0,75 × 100 ÷ 1,5 | **50,00** |
| Caio | 0 concluído | **0,00** (entra na média e na lista, mesmo sem ter puxado nada) |

Essas notas ficam congeladas e, na janela, viram a média simples das sprints.

---

### 5.9 Referência rápida de valores configuráveis

| Item | Valor padrão |
|---|---|
| Régua de pontos | 1, 2, 3 e 5 |
| Limiares do semáforo de SPI | 0,9 (verde) e 0,7 (amarelo) |
| Fator de travamento | 1,5 dia por ponto |
| Piso do PULL | 1 |
| Teto do PULL | 1,5 |
| Pesos das 4 dimensões | Ver a seção 5.4.1 |
| Peso da nota de commit dentro de Qualidade | 0,50 |
| Peso da pergunta 3 dentro de Autonomia | 0,50 |
| Bônus por ponto de task extra e teto | 1,0 e 5,0 |
| Janelas de ranking | 1, 2 e 4 sprints |
| Janela de edição do questionário | 48 horas |
| Escala das perguntas | Inteiros de 0 a 5 |
| Nota de commit | 0 a 10 (a IA lê o commit e as alterações) |
| Cores do histograma de cycle time | Âmbar a partir de 72 horas, vermelho a partir de 120 horas |
| Limite de WIP | Sem limite; no PULL, o limite por pessoa é sempre 1 |


---


---

## Apêndice A — Os outros documentos

A aba **Documentos** reúne todos os documentos institucionais. O botão
**Baixar todos (.zip)** baixa uma cópia de cada documento que você pode abrir.

| Documento | Para quem | O que traz |
|---|---|---|
| **Bíblia do DocuData** (este) | Gerente, Líder, Owner | Tudo o que existe no sistema e como funciona |
| **Guia do DocuData** | Todos | Visão curta de cada tela, para quem está começando |
| **Como sua contribuição é acompanhada** | Todos, pensado para operacionais | O que conta, o que não conta e como funciona o reconhecimento, sem pesos nem fórmulas |
| **Sistema de Acompanhamento de Performance** | Gerente, Líder, Owner | Metodologia completa da performance: fundamentação, pesos, manual do gerente e casos de borda |

## Apêndice B — Glossário

| Termo | Significado |
|---|---|
| **Arquétipo** | Tipo do projeto (padrão ou consultoria/discovery), que define os pesos da performance |
| **Atribuição / Pull** | Modos de trabalho. Na Atribuição, o gerente define o responsável. No Pull, o operacional puxa a próxima task da fila |
| **Bloqueio** | Marca de task impedida, com tipo (por exemplo, dependência do cliente). Afeta travamento e pontuação |
| **Checklist** | Critério de pronto (DoD) da task. Precisa estar completo para mover a task para Concluída |
| **Classificador** | Agente de IA que sugere o nível da task e aprende com o tempo real |
| **Cycle time** | Tempo da task de Em andamento até Concluída |
| **Fechamento** | Ato do gerente no fim da sprint, que congela pontuação e avaliações em snapshot |
| **Foto do previsto** | Registro das tasks e pontos no início da sprint, base do SPI e do planejado × entregue |
| **Funcionalidade** | Item de escopo (MoSCoW). O status é derivado das tasks ligadas a ela |
| **Ingestão** | Arquivo ou texto processado pela IA e guardado como conhecimento estruturado da sprint |
| **Janela** | Período de sprints usado para agregar performance e montar o ranking |
| **Meta da sprint** | Conjunto de funcionalidades que o gerente se compromete a entregar na sprint, com histórico de mudanças |
| **Régua** | Níveis válidos de dificuldade: 1, 2, 3 e 5 |
| **SPI** | Pontos concluídos da sprint ÷ previsto da foto. 1,0 significa que entregou o previsto |
| **Snapshot** | Cópia congelada dos números no fechamento. O ranking lê dela, não do Kanban ao vivo |
| **Tempo limpo** | Tempo efetivo da task, descontado o tempo bloqueado por cliente, usado pelo classificador para aprender |
| **Travamento** | Task parada há mais tempo que os pontos dela multiplicados por 1,5, em dias. O sistema marca automaticamente uma vez por dia |
| **WIP** | Trabalho em andamento ao mesmo tempo, com limite configurável |
