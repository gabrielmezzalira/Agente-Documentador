# Sistema de Acompanhamento de Performance

**Metodologia, regras de cálculo e manual do gerente**
Subárea de Dados · CITi · Gestão 26.2

> **Classificação: restrito a Líder e Gerente.**
> Este documento contém a camada oculta do sistema — pesos, fórmulas, fontes de
> dado e mecânica de fechamento. Não é acessível a operacionais dentro do
> DocuData (`GET /metodologia/performance` roda atrás de `require_not_operacional`)
> e não deve ser repassado fora da liderança. O que pode ser comunicado ao time
> está na **seção 13.3**.

---

## Índice

1. [Objetivo](#1-objetivo)
2. [Princípio central: direção pública, cálculo oculto](#2-princípio-central-direção-pública-cálculo-oculto)
3. [Fundamentação](#3-fundamentação)
4. [Arquitetura do sistema em quatro camadas](#4-arquitetura-do-sistema-em-quatro-camadas)
5. [As cinco dimensões](#5-as-cinco-dimensões)
6. [Pesos e arquétipos](#6-pesos-e-arquétipos)
7. [O questionário de sete perguntas](#7-o-questionário-de-sete-perguntas)
8. [Como o dado é produzido no dia a dia](#8-como-o-dado-é-produzido-no-dia-a-dia)
9. [O fechamento da sprint](#9-o-fechamento-da-sprint)
10. [Janelas, sequência pessoal e ranking](#10-janelas-sequência-pessoal-e-ranking)
11. [A fórmula completa, passo a passo](#11-a-fórmula-completa-passo-a-passo)
12. [Guard-rails e anti-gaming](#12-guard-rails-e-anti-gaming)
13. [Acesso, sigilo e auditoria](#13-acesso-sigilo-e-auditoria)
14. [Manual do gerente](#14-manual-do-gerente)
15. [Casos de borda e regras finas](#15-casos-de-borda-e-regras-finas)
16. [Erros que o sistema devolve e o que fazer](#16-erros-que-o-sistema-devolve-e-o-que-fazer)
17. [Riscos residuais assumidos](#17-riscos-residuais-assumidos)
18. [Piloto e evolução](#18-piloto-e-evolução)
19. [Decisões abertas](#19-decisões-abertas)
20. [Anexo A — referência técnica](#anexo-a--referência-técnica)
21. [Anexo B — divergências entre a metodologia de referência e o implementado](#anexo-b--divergências-entre-a-metodologia-de-referência-e-o-implementado)

---

## 1. Objetivo

O sistema mede a performance individual dos operacionais da subárea de Dados com
finalidade de **ranking**, para incentivar o trabalho e desenvolver as pessoas.
Ele opera em duas camadas: uma **camada pública**, que gera o incentivo, e uma
**camada oculta**, que impede o gaming e mantém a justiça.

Três coisas o sistema **não** é, e é importante que a liderança segure isso:

- **Não é métrica de saúde do squad.** Saúde de projeto é medida em nível de
  time (SPI da sprint, cycle time, semáforo). Ver seção 17.3.
- **Não é instrumento de desligamento.** É instrumento de reconhecimento e
  desenvolvimento. Nada no sistema foi calibrado para suportar decisão punitiva.
- **Não é auditoria de código.** Nenhuma contagem de commit, linha ou task
  entra como moeda. Ver seção 12.

---

## 2. Princípio central: direção pública, cálculo oculto

A **camada pública** é a direção. Os operacionais sabem quais comportamentos
contam — entregar com qualidade, ajudar o time, ser autônomo, evoluir,
documentar — e sabem que existe reconhecimento por ciclo para quem mais
contribui.

A **camada oculta** é o cálculo: pesos, fórmula, normalização, notas cruas dos
gerentes e scores individuais nunca são divulgados. Só a liderança enxerga.

A direção pública gera o incentivo, porque ninguém muda comportamento por uma
recompensa que não sabe que existe. O cálculo oculto impede o gaming dos pesos.
Esse é o ponto de equilíbrio entre incentivar e resistir a manipulação, e é o
único desenho em que "oculto" e "incentiva" coexistem.

**Esse princípio está implementado no código, não só no acordo social:**

| Camada | Quem enxerga | Como é garantido |
|---|---|---|
| Ranking, score final, sub-scores | Só Líder | `GET /performance` → `require_role("lider")` |
| SPI individual, baseline de evolução | Só Líder | `require_role("lider")` em `routers/pontuacao.py` |
| Notas cruas do questionário, métricas de projeto | Líder e Gerente | `require_not_operacional` em `main.py` |
| Esta metodologia | Líder e Gerente | `require_not_operacional` em `GET /metodologia/performance` |
| Kanban, tasks, sprints do próprio projeto | Todos os vinculados | `require_project_access` |

Todo acesso a `/performance` grava uma linha em `audit_log` (seção 13.2).

---

## 3. Fundamentação

O desenho segue o consenso de mercado sobre medição de performance em tecnologia.

**SPACE** (Forsgren et al., ACM Queue, 2021) estabelece que produtividade é
multidimensional e não é capturada por uma métrica única. Métricas de output de
código — commits, linhas, PRs — medem volume, não valor, e viraram ativamente
enganosas quando a IA gera parte relevante do código. Por isso este sistema mede
em cinco dimensões e nunca usa contagem de código como moeda.

**DX Core 4** (Noda e Tacho, 2024) organiza a medição em dimensões oposicionais,
onde cada uma segura o exagero da outra. Esse é o princípio anti-gaming central:
uma métrica de volume só entra quando outra dimensão a pune ao ser gameada.

**Google** amarra peso alto no gerente à calibração — que Laszlo Bock chama de
"a alma da avaliação" — porque força cada gerente a justificar a nota pros
outros e alinha padrões diferentes. Por isso os 35% no gerente aqui são
inseparáveis da rotina de calibração da seção 14.5.

**Microsoft**, ao sair do stack ranking, passou a avaliar a pessoa também pela
contribuição ao sucesso dos outros. Por isso colaboração vive dentro da
avaliação do gerente (pergunta 5).

**Adobe** substituiu a avaliação anual por conversa frequente. Por isso o
feedback aqui é **semanal**, preso ao fechamento da sprint, e não anual.

---

## 4. Arquitetura do sistema em quatro camadas

O sistema não é um contador que roda o tempo todo. Ele é uma sequência de quatro
camadas, e entender essa separação é o que evita 90% da confusão operacional.

```
CAMADA 1 — COLETA (contínua, durante a sprint)
  Escopo:  100 pontos do projeto → orçamento por sprint
  Kanban:  tasks com pontos, transições, bloqueios, reaberturas
  Git:     commits ingeridos → nota de qualidade por IA
        ↓  nada aqui é "score" ainda. É só dado bruto vivo.

CAMADA 2 — FECHAMENTO (uma vez por sprint, disparado pelo gerente)
  Gerente responde as 7 perguntas de cada operacional
  Gerente clica "Confirmar Avaliação Semanal"
        ↓  o sistema fotografa o estado e TRAVA uma linha por operacional
           em pontuacao_operacional_sprint. Irreversível.

CAMADA 3 — AGREGAÇÃO (em tempo de leitura, quando o Líder abre a tela)
  Sequência pessoal = linhas travadas da pessoa, mais recentes primeiro
  Janela = 1, 2 ou 4 linhas dessa sequência
  Por dimensão: calcula por projeto → média entre projetos
        ↓

CAMADA 4 — RANKING (em tempo de leitura)
  Score final = soma ponderada das 5 dimensões, pesos do arquétipo
  Ordenação decrescente, por janela
```

Consequências práticas dessa arquitetura:

- **O score nunca é "atualizado ao vivo".** Ele só existe depois que o gerente
  confirma a Avaliação Semanal. Sprint aberta não gera pontuação nenhuma.
- **O fechamento é uma fotografia, não um contador incremental.** O cálculo lê o
  estado final de tasks, transições, reaberturas e avaliações no momento em que
  roda. Por isso reatribuição de task no meio da sprint não precisa de tratamento
  especial — o cálculo simplesmente lê como as coisas ficaram.
- **A agregação é recalculada a cada leitura.** Mudar um peso em
  `pesos_arquetipo` muda o ranking imediatamente, sem reprocessar nada — porque
  o que está travado é o dado bruto, não o score.
- **Nada é apagado retroativamente.** Uma vez travada, a linha da sprint não é
  recalculada. Ver seção 15.

---

## 5. As cinco dimensões

Cada dimensão vira um número de **0 a 100** antes de ser multiplicada pelo peso.
As fórmulas são determinísticas e absolutas — nenhuma depende de comparação com
outros operacionais. Isso foi decisão explícita contra normalização por percentil:
com percentil, o placar de uma pessoa muda porque outra entrou ou saiu do grupo,
o que destrói a leitura de evolução individual.

Todas as fórmulas abaixo rodam **por projeto primeiro**; se a janela cobre mais
de um projeto, o valor final da dimensão é a **média simples** dos valores por
projeto (seção 10.4).

### 5.1 Entrega e Confiabilidade — peso 20%

**O que mede:** cumpriu o que se comprometeu, dentro do que foi alocado.

```
Entrega = min( Σ entrega_pontos_concluidos ÷ Σ entrega_pontos_alocados , 1 ) × 100
```

- Somatórios sobre todas as linhas da janela pertencentes ao mesmo projeto.
- **Teto de 100** — entregar além do alocado não pontua acima do máximo. Isso
  existe para que puxar task extra no fim da sprint não vire alavanca de score.
- Se `alocados = 0`, a dimensão fica **indisponível** para aquele projeto (não
  vira 0). Ver seção 11.3 sobre o que acontece com dimensão indisponível.

**Por que é razão e não soma bruta:** volume absoluto de pontos mede quem recebeu
as tasks maiores — ou seja, mede a decisão de alocação do gerente, não a
performance da pessoa. Entrega relativa à capacidade faz com que quem cumpriu
tudo que pegou pontue alto mesmo tendo pego menos.

### 5.2 Avaliação do Gerente — peso 35%

**O que mede:** a leitura estruturada do gerente sobre o operacional, incluindo
o sinal de colaboração.

```
gerente_media (por sprint) = média das 7 respostas (0–5)
Gerente = min( média(gerente_media das linhas do projeto) × 20 , 100 )
```

- `× 20` converte a escala 0–5 em 0–100.
- Se nenhuma linha da janela tem avaliação, a dimensão fica **indisponível**.

**Por que 35% e não mais:** acima disso o ranking vira ranking de opinião de
gerente vestido de dado. Mesmo com 35%, metade do peso total continua em
dimensões objetivas — as difíceis de gamear. E os 35% só são justos se a
calibração da seção 14.5 acontecer.

### 5.3 Qualidade Técnica — peso 20%

**O que mede:** o trabalho precisou de pouca correção e seguiu o padrão.

A dimensão combina **dois sinais**: retrabalho (dado de sistema) e nota de
qualidade de commit (avaliada por IA).

```
retrabalho = max( 1 − Σ qualidade_reaberturas ÷ Σ qualidade_tasks_concluidas , 0 ) × 100
             (se tasks_concluidas = 0 → retrabalho = 100)

commit_score = min( média(qualidade_commit_media) × 10 , 100 )

COM nota de commit no período:
  Qualidade = peso_commit × commit_score + (1 − peso_commit) × retrabalho

SEM nota de commit no período:
  Qualidade = retrabalho
```

- `peso_commit` é a coluna `pesos_arquetipo.peso_commit_qualidade`, **default 0.5**.
  É configurável por arquétipo, hoje só via SQL (não há UI). O valor final é
  decisão do Líder depois do piloto.
- A nota de commit só existe para projetos de arquétipo `padrao` (seção 8.5).
  Em `consultoria_discovery`, Qualidade é sempre retrabalho puro.
- `tasks_concluidas = 0` resulta em 100, não em indisponível. Isso é uma
  assimetria consciente: quem não concluiu nada não sofre penalidade de
  qualidade — a penalidade dele já está em Entrega.

**Reabertura** tem definição estrita: é a transição `concluida → em_andamento`, e
só ela. Sair de `concluida` para `planejado` não conta como reabertura.

### 5.4 Autonomia — peso 15%

**O que mede:** quanto a pessoa destrava sozinha antes de escalar.

```
Autonomia = Σ autonomia_bloqueios_resolvidos_proprio ÷ Σ autonomia_bloqueios_totais × 100
            (se bloqueios_totais = 0 → Autonomia = 100)
```

- A contagem vem exclusivamente de **bloqueio manual** registrado no Kanban, e o
  numerador só cresce quando o bloqueio é resolvido com
  `bloqueado_resolvido_por = "operacional"`.
- **Zero bloqueio = autonomia máxima (100).** É a escolha correta em termos de
  incentivo — não penaliza quem simplesmente não travou — mas cria um efeito
  colateral que o gerente precisa conhecer: registrar bloqueios *reduz* o teto
  de Autonomia de quem registrou, a não ser que ele mesmo resolva. Ver seção
  12.3 e a decisão aberta 19.4.

**O travamento automático por tempo nunca entra aqui.** É alerta, não pontuação.
Ver seção 8.6.

### 5.5 Evolução — peso 10%

**O que mede:** quanto a pessoa cresceu em relação a onde estava.

```
Evolução = min( média(gerente_pergunta6 das linhas do projeto) × 20 , 100 )
```

É a **pergunta 6 isolada** ("Evoluiu em relação a onde estava no começo do
ciclo?"). Essa pergunta entra duas vezes por design: uma dentro da média das 7
(Gerente) e outra sozinha aqui. **Não é bug nem duplicação a remover** — é
sobreposição proposital, o mesmo padrão da pergunta 3 (autonomia percebida) com
a dimensão Autonomia medida por dado de sistema.

Efeito prático do peso duplo: a pergunta 6 responde por `0.10` direto mais
`0.35 ÷ 7 = 0.05` dentro da média — **15% do score final**. É a pergunta mais
pesada do questionário. O gerente precisa saber disso ao responder.

---

## 6. Pesos e arquétipos

### 6.1 Os cinco pesos

| Dimensão | Coluna | Peso |
|---|---|---|
| Avaliação do Gerente | `peso_gerente` | **35%** |
| Entrega e Confiabilidade | `peso_entrega` | **20%** |
| Qualidade Técnica | `peso_qualidade` | **20%** |
| Autonomia | `peso_autonomia` | **15%** |
| Evolução | `peso_evolucao` | **10%** |

Somam 1.00. Vivem na tabela `pesos_arquetipo`, uma linha por arquétipo. Alterar
um peso é um `UPDATE` no Supabase e o ranking muda na próxima leitura, sem
reprocessar nada.

### 6.2 Os dois arquétipos

`projects.arquetipo` aceita dois valores:

- **`padrao`** — projeto com código. Pipeline de qualidade de commit ativo.
- **`consultoria_discovery`** — projeto sem entrega de código. Pipeline de
  qualidade de commit desligado.

### 6.3 Os pesos são iguais entre arquétipos — e isso é decisão fechada

Os cinco pesos principais são **idênticos** em `padrao` e `consultoria_discovery`
(decisão do Líder registrada em `.planning/intel/decisions.md` #3, fechada
permanentemente). Nenhum dado objetivo diferenciava os arquétipos o suficiente
para justificar pesos distintos, e pesos diferentes tornariam o ranking
cross-projeto incomparável.

**O que muda por arquétipo não é o peso, é a *presença do sinal* dentro de
Qualidade:** em `consultoria_discovery` não há nota de commit, então Qualidade
cai para retrabalho puro. Mesma régua, uma fonte a menos.

> A metodologia de referência propunha migrar 10 pontos de peso de Qualidade para
> Entrega em projetos de consultoria, com CSAT morando em Entrega. **Isso não foi
> implementado** e o CSAT não é coletado em lugar nenhum do sistema. Ver Anexo B.

### 6.4 Qual arquétipo a janela usa

Uma janela pode misturar projetos. O arquétipo aplicado é o do **projeto com mais
linhas na janela**; em empate, vence o projeto cuja linha é mais recente
(`sprint_fim`). Como hoje os pesos são iguais entre arquétipos, essa escolha só
afeta `peso_commit_qualidade`.

---

## 7. O questionário de sete perguntas

O gerente responde **por operacional, por sprint**, numa escala de **0 a 5**.
Todas as sete são obrigatórias — não há "não sei".

| # | Pergunta | Âncora 0 | Âncora 5 | Alimenta |
|---|---|---|---|---|
| 1 | Entregou o que se comprometeu dentro do combinado nesta sprint? | quase nada do previsto | tudo no prazo | Gerente (1/7) |
| 2 | A qualidade da entrega precisou de pouca ou nenhuma correção? | refiz quase tudo | entrou limpo | Gerente (1/7) |
| 3 | A pessoa destravou sozinha antes de te escalar? | dependeu de mim o tempo todo | resolveu sozinha | Gerente (1/7) |
| 4 | A comunicação da entrega foi clara a ponto de você não precisar perguntar? | tive que decifrar | entendi de primeira | Gerente (1/7) |
| 5 | Ajudou, desbloqueou ou ensinou outro membro nesta sprint? | não interagiu | foi peça de apoio do squad | Gerente (1/7) |
| 6 | Evoluiu em relação a onde estava no começo do ciclo? | estagnou | salto claro | Gerente (1/7) **+ Evolução (peso cheio)** |
| 7 | Trouxe algo além do que foi pedido? | fez o mínimo | antecipou problema ou propôs melhoria | Gerente (1/7) |

### 7.1 Peso real de cada pergunta no score final

| Pergunta | Peso no score final |
|---|---|
| 6 (evolução) | **15,0%** |
| 1, 2, 3, 4, 5, 7 (cada uma) | **5,0%** |

Ou seja: a pergunta 5 (colaboração) vale 5% do score final. É um sinal real, mas
não é uma dimensão própria — ela vive diluída dentro da avaliação do gerente.
Se o piloto mostrar queda de colaboração, o caminho de correção é subir o peso
de `peso_gerente` ou promover a pergunta 5 a dimensão própria (seção 18).

### 7.2 Como responder bem

- **Ancore na sprint, não na pessoa.** A pergunta é sobre o que aconteceu nestas
  duas semanas, não sobre quem a pessoa é.
- **Use a escala inteira.** Um gerente que só dá 4 e 5 destrói a comparação para
  todos os operacionais dele. A calibração (14.5) existe justamente para isso.
- **3 é "fez o combinado".** 5 é excepcional, não é "não tenho reclamação".
- **Pergunta 6 pesa o triplo.** Não responda no automático.
- **Não tente compensar o cálculo.** Se você acha que a pessoa merece mais porque
  as tasks dela eram difíceis, não infle a nota — registre isso na conversa de
  feedback. Inflar nota é exatamente o que a calibração vai pegar.

### 7.3 Janela de edição de 48 horas

Uma avaliação salva pode ser **editada por 48 horas** a partir da criação
(`avaliacoes_gerente.editavel_ate`). Depois disso, tentar alterar retorna
`409 — Janela de edição de 48h já encerrada para esta avaliação`.

Isso protege a integridade do dado sem impedir correção de erro honesto. Note que
a janela conta da **criação**, não da última edição.

### 7.4 Reaproveitamento cross-projeto

Se o mesmo operacional (casado por **e-mail**) já foi avaliado recentemente em
outro projeto, o modal oferece "usar essas respostas" e preenche as 7 notas a
partir da última avaliação encontrada. A origem fica registrada em
`avaliacoes_gerente.reaproveitada_de`.

**Use com cuidado.** É um atalho para quem gerencia a mesma pessoa em dois
projetos e teve a mesma leitura. Não é um botão de "repetir a nota anterior" — a
avaliação reaproveitada entra no cálculo com peso idêntico a uma avaliação
pensada.

---

## 8. Como o dado é produzido no dia a dia

Nada nesta seção é "preencher planilha de performance". É o trabalho normal de
gestão de sprint. O ponto é que **o sistema só enxerga o que passou pelo Kanban**.

### 8.1 Os 100 pontos do projeto

Todo projeto vale **100 pontos, fixo**. Não é um número que o gerente escolhe.

- Se o gerente informar `valor_projeto` (R$), o sistema calcula
  `valor_por_ponto = valor_projeto ÷ 100` e passa a derivar faturamento previsto
  por sprint automaticamente.
- **Trava:** `valor_projeto` só pode ser alterado enquanto **nenhuma sprint tiver
  orçamento de pontos definido**. Depois do primeiro orçamento, o valor congela —
  mudar depois desalinharia silenciosamente todo o faturamento já calculado.

### 8.2 Orçamento de pontos por sprint

No planejamento (aba **Escopo**), o gerente distribui os 100 pontos entre as
sprints (`sprints.pontos_orcamento`).

Regras:

- A soma dos orçamentos de todas as sprints **não pode passar de 100**.
- Um orçamento **não pode encolher abaixo do que as tasks daquela sprint já
  somam** — não dá para prometer menos do que já foi gasto.
- Sprint sem orçamento definido (`NULL`) não entra na soma e **não trava nada**.
  Planejamento incompleto não impede trabalhar.
- Marcar o projeto como entregue com soma diferente de 100 gera um aviso
  **não-bloqueante** ("62/100 pontos alocados — marcar como entregue mesmo
  assim?"). Forçar 100 exato incentivaria inflar pontos só para fechar a conta.

### 8.3 Tasks e pontos

Cada task carrega uma fatia dos pontos da sprint. `pontos > 0`, sempre.

- Se a sprint de destino **tem** orçamento: a soma dos pontos das tasks daquela
  sprint não pode ultrapassá-lo.
- Se **não tem** orçamento: sem validação, comportamento livre.
- Mover uma task entre sprints revalida contra o orçamento da sprint de
  **destino**.
- Dados anteriores à reforma de pontuação nunca são revalidados retroativamente.

**Por que isso importa para o score:** `pontos` é o denominador de Entrega. Task
sem pontos realistas produz Entrega sem significado. Fatiar task para inflar
contagem não ajuda — o denominador cresce junto (seção 12).

### 8.4 Transições, DoR, DoD e WIP

O Kanban tem três colunas: `planejado → em_andamento → concluida`.

| Gate | Regra | Efeito |
|---|---|---|
| **DoR** | Task sem sprint não pode entrar em `em_andamento` | Garante que todo trabalho em curso tem sprint — sem isso não há a quem atribuir a pontuação |
| **DoD** | Checklist com item pendente bloqueia `concluida` | Evita "concluída" nominal que vira reabertura depois |
| **WIP por coluna** | Limite configurável de tasks simultâneas em `em_andamento` no projeto | Segura multitarefa de squad |
| **WIP por pessoa** | Limite configurável por operacional | Segura multitarefa individual |

Toda mudança de `coluna_kanban`, `operacional_id` e `sprint_id` grava uma linha
em `task_transicoes`, **com snapshot de quem estava com a task naquele momento**.
Esse snapshot é o que permite saber quem de fato completou uma task que foi
reatribuída depois.

### 8.5 Bloqueio manual — a fonte de Autonomia

Quando uma task trava por dependência externa, dúvida ou impedimento, o gerente
(ou o operacional) marca **bloqueio manual** na task.

Ao desmarcar, o sistema **exige** informar quem resolveu:

- `operacional` → conta no numerador **e** no denominador de Autonomia
- `gerente` → conta **só** no denominador

Sem essa informação, a operação é recusada com `422`. É o único campo do sistema
que o gerente é obrigado a preencher fora do questionário, e é ele que carrega
15% do score.

### 8.6 Travamento automático por tempo — alerta, nunca pontuação

Um job diário marca `travado_automatico = true` em qualquer task parada em
`em_andamento` por mais dias do que `pontos × 2`.

**Esse sinal jamais entra em nenhuma fórmula de score.** É um alerta visível de
gestão, para o gerente ir olhar. O gerente pode dar override
(`travado_override`), e o relógio reseta a cada entrada ou saída de
`em_andamento`. Não confundir com bloqueio manual — só o bloqueio manual alimenta
Autonomia.

### 8.7 Qualidade de commit por IA

Quando um commit é ingerido (`POST /ingest/commit`, via a GitHub Action instalada
no repositório do cliente), e **somente se o projeto for de arquétipo `padrao`**,
o sistema faz uma segunda chamada ao Gemini pedindo uma nota **0–10** e uma frase
curta de evidência, avaliando:

- complexidade da tarefa resolvida no contexto do commit
- qualidade da documentação e das mensagens de commit
- aderência a boas práticas (nomes claros, tratamento de erro, testes quando cabível)

O prompt é explícito em **nunca listar pendências para corrigir** — devolve só a
nota e o porquê, no espírito de um placar.

**Como o commit encontra a pessoa** (ordem de prioridade):

1. `operacionais.github_login` igual ao autor do commit no GitHub
2. `operacionais.email` igual ao e-mail do autor
3. Sem match → a nota é gravada com `operacional_id = null` e **não entra no
   score de ninguém**

> **Ação obrigatória do gerente:** preencher o **GitHub username** no cadastro de
> cada operacional. Sem isso, os commits da pessoa não pontuam em Qualidade e ela
> cai para retrabalho puro — silenciosamente, sem erro em lugar nenhum.

A chamada é *best-effort*: se a avaliação de qualidade falhar, a ingestão de
conhecimento do commit continua funcionando normalmente.

O commit pode ainda referenciar uma task com a tag `[task:<uuid>]` na mensagem —
isso serve só para rastreabilidade; nenhuma agregação de score depende disso.

---

## 9. O fechamento da sprint

É o momento em que o dado bruto vira pontuação travada. É o único momento em que
isso acontece.

### 9.1 Pré-condição: zero pendências

`POST /avaliacoes/{sprint_id}/confirmar` só roda se **todo operacional com pelo
menos uma task na sprint** já tiver avaliação registrada. Caso contrário, o
sistema recusa com `409` listando os nomes que faltam.

Isso é deliberado: um fechamento parcial produziria linhas sem
`gerente_media`, e as pessoas não avaliadas teriam seu score renormalizado só
sobre as dimensões objetivas (seção 11.3) — comparação injusta e invisível.

### 9.2 O que o fechamento calcula e grava

Para cada operacional com dado na sprint, grava **uma linha** em
`pontuacao_operacional_sprint`:

| Campo | Como é preenchido |
|---|---|
| `gerente_media` | Média das **7** respostas |
| `gerente_pergunta6` | Resposta 6 isolada |
| `entrega_pontos_concluidos` | Σ pontos das tasks `concluida` atribuídas a quem completou |
| `entrega_pontos_alocados` | Σ pontos de todas as tasks da pessoa (concluídas + não concluídas) |
| `qualidade_reaberturas` | Reaberturas no período |
| `qualidade_tasks_concluidas` | Nº de tasks concluídas pela pessoa |
| `autonomia_bloqueios_totais` | Bloqueios resolvidos no período |
| `autonomia_bloqueios_resolvidos_proprio` | Subconjunto resolvido pelo próprio operacional |
| `qualidade_commit_media` | Média das notas de commit do período (ou `null`) |
| `finalizado_em` / `sprint_fim` | Timestamp do fechamento |

Entram na lista de operacionais todos que tiverem **qualquer** um destes:
pontos alocados, pontos concluídos, reaberturas, bloqueios, ou avaliação.

### 9.3 Quem recebe os pontos de uma task concluída

Os pontos vão para **quem estava com a task no momento da transição para
`concluida`**, lida do snapshot em `task_transicoes` (a transição mais recente,
se houve reabertura e reconclusão). Se não houver snapshot, cai para o
`operacional_id` atual da task.

Tasks **não** concluídas contam como alocadas para o responsável atual.

### 9.4 O cutoff — por que nada é contado duas vezes

Reabertura, bloqueio e nota de commit são eventos com timestamp, não campos por
sprint. Para não contá-los de novo a cada fechamento, o cálculo usa um **cutoff**:
o `finalizado_em` mais recente entre os fechamentos anteriores **daquele
projeto**. Só eventos posteriores ao cutoff entram.

No primeiro fechamento do projeto não há cutoff, e todo o histórico entra.

### 9.5 Idempotência

Se `pontuacao_operacional_sprint` já tiver qualquer linha para a sprint, o
fechamento **retorna as linhas existentes sem recalcular**. Clicar duas vezes não
duplica nem sobrescreve.

O corolário incômodo: **não existe "refazer o fechamento"**. Se o fechamento
rodou com dado errado, a correção não é pela UI. Ver seção 15.6.

### 9.6 Eventos tardios

Se uma reabertura ou resolução de bloqueio acontece numa task cuja sprint **já
fechou**, o evento não é descartado nem reescreve a linha travada. Ele é
redirecionado para a **sprint ativa do projeto** através de um ledger separado
(`eventos_pontuacao_tardios`) e entra no fechamento seguinte.

Se a sprint ativa também já estiver travada, o evento fica só no histórico e não
afeta pontuação nenhuma.

---

## 10. Janelas, sequência pessoal e ranking

### 10.1 Quem é uma "pessoa"

`operacionais` é uma entidade **por projeto** — a mesma pessoa em dois projetos
tem duas linhas. O ranking agrupa essas linhas pelo **e-mail**.

- Só operacionais com `ativo = true` entram no ranking.
- **Operacional sem e-mail cadastrado vira uma pessoa separada por projeto** —
  não há como casar identidade cross-projeto sem identificador comum. Isso
  fragmenta o histórico da pessoa e é um erro de cadastro silencioso.

> **Ação obrigatória do gerente:** cadastrar e-mail em todo operacional, e o
> **mesmo** e-mail em todos os projetos da pessoa.

### 10.2 Sequência pessoal

As linhas travadas da pessoa, **filtradas por `entrega_pontos_alocados > 0`** e
ordenadas por `sprint_fim` decrescente. Sprints em que a pessoa não teve nenhum
ponto alocado simplesmente não existem na sequência.

### 10.3 As três janelas

| Janela | Tamanho | Rótulo na tela |
|---|---|---|
| `sprint` | 1 linha | Última sprint |
| `quinzenal` | 2 linhas | Últimas 2 sprints |
| `mensal` | 4 linhas | Últimas 4 sprints |

**As janelas são por contagem de sprints, nunca por calendário.** Uma pessoa que
ficou dois meses fora tem a mesma janela "mensal" de quatro sprints — só que
mais antigas. Isso é intencional: compara volume de trabalho equivalente, não
período de tempo equivalente.

Se a pessoa tem menos linhas do que o tamanho da janela, o score é calculado com
o que existe e a linha é marcada **`janela_parcial`** — aparece na tela como
"Janela parcial — dado insuficiente ainda". Um score parcial não é comparável a
um score cheio; trate como indicativo.

### 10.4 Agregação em duas camadas

Dentro de uma janela que cobre mais de um projeto:

1. **Camada 1 — por projeto.** Agrupa as linhas por `projeto_id` e aplica a
   fórmula da dimensão sobre os somatórios daquele projeto.
2. **Camada 2 — entre projetos.** Média **simples** dos valores por projeto,
   ignorando projetos onde a dimensão ficou indisponível.

Média simples, não ponderada por volume: um projeto pequeno pesa igual a um
grande. Isso protege quem foi alocado parcialmente em algo pequeno de ter esse
projeto diluído a zero — mas também significa que uma sprint ruim num projeto
pequeno machuca tanto quanto num grande.

---

## 11. A fórmula completa, passo a passo

### 11.1 O algoritmo

```
Para cada pessoa ativa (agrupada por e-mail):
  sequencia ← linhas travadas com alocados > 0, ordenadas por sprint_fim DESC

  Para cada janela em {sprint:1, quinzenal:2, mensal:4}:
    linhas ← as N primeiras da sequencia
    Se não há linhas → pessoa não aparece nesta janela

    arquetipo ← arquétipo do projeto com mais linhas (empate: mais recente)
    pesos     ← pesos_arquetipo[arquetipo]

    Para cada dimensão D em {entrega, gerente, qualidade, autonomia, evolucao}:
      valores ← [ fórmula_D(linhas do projeto P) para cada projeto P ]
      valores ← valores sem os indisponíveis
      subscore[D] ← média simples de valores   (ou indisponível, se lista vazia)

    disponiveis     ← dimensões com subscore não-indisponível
    peso_disponivel ← Σ peso[D] para D em disponiveis
    score_final     ← Σ ( peso[D] × subscore[D] ) ÷ peso_disponivel

Ordena por score_final decrescente, por janela.
```

Todo resultado intermediário é arredondado para **2 casas decimais**.

### 11.2 Exemplo numérico completo

Maria, janela **quinzenal** (2 sprints), ambas no mesmo projeto de arquétipo
`padrao`, `peso_commit_qualidade = 0.5`.

| Dado | Sprint 12 | Sprint 13 |
|---|---|---|
| `entrega_pontos_alocados` | 14 | 10 |
| `entrega_pontos_concluidos` | 12 | 10 |
| `gerente_media` | 4.14 | 4.43 |
| `gerente_pergunta6` | 4 | 5 |
| `qualidade_reaberturas` | 1 | 0 |
| `qualidade_tasks_concluidas` | 6 | 4 |
| `autonomia_bloqueios_totais` | 3 | 1 |
| `autonomia_bloqueios_resolvidos_proprio` | 2 | 1 |
| `qualidade_commit_media` | 7.5 | 8.5 |

**Sub-scores:**

```
Entrega    = (12 + 10) ÷ (14 + 10) × 100 = 22/24 × 100          = 91.67
Gerente    = média(4.14, 4.43) × 20 = 4.285 × 20                = 85.70
Evolução   = média(4, 5) × 20 = 4.5 × 20                        = 90.00
Autonomia  = (2 + 1) ÷ (3 + 1) × 100 = 3/4 × 100                = 75.00

retrabalho = (1 − (1 + 0) ÷ (6 + 4)) × 100 = 0.9 × 100          = 90.00
commit     = média(7.5, 8.5) × 10 = 8.0 × 10                    = 80.00
Qualidade  = 0.5 × 80.00 + 0.5 × 90.00                          = 85.00
```

**Score final:**

```
0.35 × 85.70  = 29.995
0.20 × 91.67  = 18.334
0.20 × 85.00  = 17.000
0.15 × 75.00  = 11.250
0.10 × 90.00  =  9.000
                ───────
                85.579  ÷ 1.00  →  85.58
```

### 11.3 Renormalização quando falta dimensão

Se uma dimensão fica indisponível, ela **não vira zero** — ela sai da conta, e o
score é dividido pela soma dos pesos que restaram.

Mesma Maria, mas **sem avaliação do gerente** em nenhuma das duas sprints
(Gerente e Evolução indisponíveis):

```
peso disponível = 0.20 + 0.20 + 0.15 = 0.55
soma ponderada  = 18.334 + 17.000 + 11.250 = 46.584
score final     = 46.584 ÷ 0.55 = 84.70
```

Isso é matematicamente correto e comportamentalmente perigoso: uma pessoa sem
avaliação de gerente é rankeada só pelas dimensões objetivas, na mesma tabela de
quem tem as cinco. **A defesa contra isso é o gate da seção 9.1**, que impede o
fechamento com avaliação faltando. Enquanto esse gate for respeitado, o caso
acima não acontece na prática — mas linhas antigas ou dado importado podem
produzi-lo. Se você vir alguém com `Gerente = —` na tela, o score dele não é
comparável.

Se **todas** as dimensões estiverem indisponíveis, a pessoa não aparece no
ranking daquela janela.

---

## 12. Guard-rails e anti-gaming

O princípio: **uma métrica de volume só é admitida quando outra dimensão a pune
ao ser gameada.**

### 12.1 A regra dura

> Contagem de task, de commit e de linha é **guard-rail, nunca moeda.**

Sob IA, commit e linha são quase de graça. Servem para cruzar com qualidade,
jamais para pontuar sozinhos. Nenhuma dessas contagens aparece em nenhuma das
cinco fórmulas.

### 12.2 Como cada tentativa de gaming se anula

| Tentativa | O que a segura |
|---|---|
| Fatiar task para inflar contagem | Entrega é razão concluído/alocado — o denominador cresce junto. E `qualidade_tasks_concluidas` cresce sem melhorar retrabalho |
| Pegar poucas tasks para garantir 100% de Entrega | Entrega tem teto 100, então não há upside; e a leitura do gerente (35%) enxerga volume baixo |
| Pegar muitas tasks e entregar pela metade | Alocado cresce, concluído não — Entrega despenca |
| Commit trivial em volume | A nota é 0–10 por commit e entra como **média**, não soma. Commit trivial puxa a média para baixo |
| Inflar linha de código com IA | Não existe contagem de linha em lugar nenhum. E a nota de commit avalia complexidade e aderência, não tamanho |
| Marcar task como concluída sem estar | DoD bloqueia com checklist pendente; e a reabertura posterior pune Qualidade |
| Nunca registrar bloqueio para manter Autonomia em 100 | Segurada só parcialmente — ver 12.3 |
| Gerente inflar as notas do próprio squad | Calibração entre gerentes (14.5). É a única defesa, e é social, não técnica |

### 12.3 O buraco conhecido: sub-registro de bloqueio

Autonomia é 100 quando `bloqueios_totais = 0`. Não registrar bloqueio nenhum
garante nota máxima em 15% do score.

Nada no código impede isso. As defesas hoje são indiretas:

- A pergunta 3 do gerente ("destravou sozinha antes de te escalar?") captura a
  percepção real, e vale 5% — o gerente que vê a pessoa travada sem registro
  responde baixo.
- Bloqueio não registrado costuma virar task parada, que o travamento automático
  por tempo sinaliza como alerta (8.6).

Ainda assim, é o vetor de gaming mais aberto do sistema, e é onde a decisão 19.4
mira.

### 12.4 O que nunca entra no score

- `travado_automatico` — alerta de gestão, por design fora de toda fórmula
- número de commits, linhas, PRs, arquivos
- número de tasks (só pontos, e só como razão)
- cycle time e SPI de cronograma da sprint — são métricas de **saúde do squad**
- horas, presença, tempo de resposta

---

## 13. Acesso, sigilo e auditoria

### 13.1 Quem vê o quê

| Recurso | Líder | Gerente | Operacional |
|---|---|---|---|
| Ranking e score final (`/performance`) | ✅ | ❌ | ❌ |
| SPI individual, baseline de evolução | ✅ | ❌ | ❌ |
| Esta metodologia (`/metodologia`) | ✅ | ✅ | ❌ |
| Preencher e ler o questionário | ✅ | ✅ | ❌ |
| Métricas e painel do projeto | ✅ | ✅ | ❌ |
| Kanban, tasks, sprints | ✅ | ✅ | ✅ (só projetos vinculados) |

O gerente **não** enxerga score nem ranking. Ele produz o insumo (as 7 notas) e
consome as métricas do projeto — mas o resultado do cálculo é do Líder.

Qualquer conta com `cargo = gerente` acessa dados de gestão de **qualquer**
projeto, não só dos que gerencia. A única restrição por projeto é a do
operacional. Isso foi decisão explícita para não precisar manter um vínculo
squad↔gerente.

### 13.2 Auditoria

Todo acesso a `GET /performance` grava uma linha em `audit_log` com pessoa, rota
e timestamp. É exigência vinculante do desenho de RBAC: toda leitura de score,
peso ou avaliação de gerente deixa rastro.

### 13.3 O que divulgar e o que não divulgar

**Pode e deve ser dito ao time:**

- Que a contribuição é acompanhada em entrega, qualidade, autonomia, ajuda ao
  time e evolução.
- Que existe reconhecimento por ciclo para quem mais contribui no conjunto.
- Que **ajudar os outros conta a favor**, não contra.
- Que nenhuma métrica isolada define o rank.
- Que o objetivo é reconhecer e desenvolver.

**Nunca deve ser dito:**

- Os pesos e a fórmula.
- Os scores individuais e o ranking completo.
- As notas cruas do questionário.
- Qual coisa contável pesa mais.
- Que os critérios nunca mudam — os pesos serão calibrados após o piloto.

**Na divulgação:** anuncie apenas o **top performer por ciclo**; o resto do
ranking fica na liderança. Escolha um vencedor cuja contribuição inclua
visivelmente ter ajudado o time — o vencedor visível vira o modelo do que é
premiado. Se quem ganha é quem puxou os outros, o time lê que ajudar ganha.

> O botão de "anúncio do top performer" foi descopado do sistema. O anúncio é
> feito manualmente pela liderança, fora do DocuData.

---

## 14. Manual do gerente

### 14.1 Setup, uma vez por projeto

Antes da primeira sprint:

1. **Cadastre o contrato** (aba Painel → Contrato): arquétipo (`padrao` ou
   `consultoria_discovery`), datas, tolerância e, se houver, `valor_projeto` em
   R$. Lembre que o valor congela assim que a primeira sprint receber orçamento.
2. **Cadastre os operacionais** com **e-mail** e **GitHub username**. Os dois são
   obrigatórios na prática, mesmo que o formulário aceite vazio:
   - sem e-mail → a pessoa não é reconhecida entre projetos (10.1)
   - sem GitHub username → os commits dela não pontuam em Qualidade (8.7)
   - use o **mesmo e-mail** em todos os projetos da pessoa
3. **Distribua os 100 pontos** entre as sprints na aba Escopo. Pode ser
   incremental — sprint sem orçamento não trava nada.
4. **Configure os limites de WIP** se o squad tende a multitarefar.

### 14.2 Durante a sprint

O trabalho é o Kanban normal. As três coisas que exigem disciplina:

1. **Pontos de task realistas.** Eles são o denominador de Entrega. Task de 8
   pontos que era de 2 distorce o score de todo mundo naquela sprint.
2. **Registrar bloqueio quando houver bloqueio.** E, ao resolver, informar
   honestamente **quem resolveu**. Esse único campo carrega 15% do score.
3. **Manter a atribuição da task correta.** Quem está com a task quando ela é
   concluída é quem recebe os pontos. Reatribuiu? Reatribua no sistema também.

Não precisa fazer nada "de performance" durante a sprint. Se o Kanban reflete a
realidade, o dado está sendo coletado.

### 14.3 O fechamento — a rotina de fim de sprint

No card da sprint, botão **"Avaliação Semanal"**:

1. O modal lista todos os operacionais **pendentes** — todo mundo com pelo menos
   uma task na sprint.
2. Clique num nome → responda as **7 perguntas** (0 a 5). Todas obrigatórias.
   - Se a pessoa já foi avaliada recentemente em outro projeto, aparece a opção
     de reaproveitar aquelas respostas. Use só se a leitura for de fato a mesma.
3. **Salvar avaliação.** A pessoa some da lista de pendentes.
4. Repita até a lista zerar. Aparece "✓ Todas as avaliações desta sprint estão
   completas."
5. Clique em **"Confirmar Avaliação Semanal"**.

**O passo 5 é irreversível.** Ele fotografa o estado da sprint e trava a
pontuação. Depois dele:

- Tasks daquela sprint **não podem mais ser excluídas**.
- Rodar de novo não recalcula nada.
- Correções de dado bruto não têm caminho pela UI (15.6).

Antes de clicar, confira: todas as tasks estão na coluna certa? Os bloqueios
resolvidos foram desmarcados com o responsável correto? As atribuições estão como
de fato foram?

Depois de confirmado, o botão vira **"✓ Avaliação Semanal"**.

### 14.4 Prazo de correção

Você tem **48 horas a partir da criação** de cada avaliação para corrigir as
notas. Depois disso o sistema recusa a edição. Se você percebeu um erro de
leitura no dia seguinte, ainda dá tempo — na semana seguinte, não.

### 14.5 Calibração entre gerentes — não negociável

Porque o gerente pesa 35%.

**Antes de cada ciclo**, os gerentes se reúnem, olham casos reais de operacionais
e combinam o que é um 3 e o que é um 5. Cada gerente justifica a nota para os
outros. Repete uma vez por ciclo.

Sem calibração, peso alto no gerente faz o ranking medir **de qual gerente a
pessoa é**, não como ela performou. A calibração tira a pressão para inflar nota,
alinha padrões diferentes e reduz viés. É a peça que torna os 35% justos em vez
de ruído.

O sistema **não** força nem monitora a calibração. É rotina humana, e é a única
defesa contra o vetor de gaming da linha final da tabela 12.2.

### 14.6 O que o gerente não faz

- Não vê score, sub-score nem ranking — isso é do Líder.
- Não ajusta pesos — isso é `UPDATE` no banco, decisão do Líder.
- Não reabre fechamento.
- Não comunica posição de ranking a operacional. A comunicação de reconhecimento
  segue a seção 13.3 e é feita pela liderança.

---

## 15. Casos de borda e regras finas

### 15.1 Reatribuição de task no meio da sprint

Não exige nada do gerente além de reatribuir no sistema. O fechamento lê o estado
final e o histórico de transições: os pontos de uma task concluída vão para quem
estava com ela **no momento da conclusão**; tasks não concluídas contam como
alocadas para o responsável **atual**.

### 15.2 Pessoa em dois ou mais projetos

Cada projeto gera sua própria linha travada por sprint. A janela junta as linhas
mais recentes independentemente do projeto, e a agregação faz média simples entre
projetos (10.4). O arquétipo aplicado é o do projeto dominante na janela (6.4).

### 15.3 Pessoa sem e-mail cadastrado

Vira uma "pessoa" separada por linha de `operacionais` — o histórico não se junta
entre projetos. É um erro de cadastro que não gera nenhum aviso.

### 15.4 Operacional desativado

`ativo = false` remove a pessoa do ranking imediatamente. As linhas travadas dela
continuam no banco, mas não são lidas.

### 15.5 Sprint sem nenhuma task

Se não há tasks na sprint, o fechamento não cria linha nenhuma — mas ainda marca
`avaliacao_completa_em` na sprint. Ninguém entra na sequência pessoal por aquela
sprint.

### 15.6 Fechamento feito com dado errado

**Não há caminho pela UI.** A pontuação é idempotente por sprint: rodar de novo
retorna as linhas existentes. As opções, todas manuais e todas do Líder:

1. Aceitar e deixar a distorção diluir nas janelas seguintes (2 e 4 sprints).
2. Deletar as linhas de `pontuacao_operacional_sprint` daquela sprint direto no
   Supabase, corrigir o dado bruto e reconfirmar. Cuidado: isso desloca o
   **cutoff** (9.4) e pode fazer eventos serem recontados.

A prevenção é o checklist de 14.3.

### 15.7 Exclusão de task após o fechamento

Bloqueada com `409`. A pontuação da sprint já foi travada e a task faz parte da
base de cálculo.

### 15.8 Projeto de consultoria

Sem nota de commit, Qualidade = retrabalho puro. Como retrabalho é 100 quando não
há tasks concluídas, projetos de consultoria com pouca movimentação de Kanban
tendem a ter Qualidade artificialmente alta. Leia esses scores com desconto.

### 15.9 Pesos que não somam 1.00

O código **não valida** isso. Se alguém editar `pesos_arquetipo` e a soma der
diferente de 1.00, a renormalização por peso disponível (11.3) faz o score sair
numa escala diferente de 0–100 — silenciosamente. Ao mexer nos pesos, confira a
soma.

---

## 16. Erros que o sistema devolve e o que fazer

| Erro | Quando aparece | O que fazer |
|---|---|---|
| `409 Ainda há avaliações pendentes: <nomes>` | Confirmar Avaliação Semanal com gente sem avaliar | Avaliar os nomes listados e confirmar de novo |
| `409 Janela de edição de 48h já encerrada` | Editar avaliação antiga | Não há correção. Registre o desvio para a leitura do Líder |
| `409 Orçamento da sprint excedido: restam N pontos` | Task com pontos além do orçamento | Reduzir os pontos, mover a task para outra sprint, ou aumentar o orçamento da sprint (se houver saldo nos 100) |
| `409 restam só N pontos pra distribuir entre as sprints` | Orçamento de sprint estourando os 100 do projeto | Reduzir o orçamento de outra sprint primeiro |
| `409 DoR: associe a task a uma sprint...` | Mover task sem sprint para Em Andamento | Atribuir a sprint antes de mover |
| `409 DoD: N item(ns) do checklist...` | Concluir task com checklist pendente | Marcar os itens ou removê-los do checklist |
| `409 Limite WIP ... atingido` | Mover para Em Andamento acima do limite | Concluir ou devolver outra task antes |
| `422 Informe quem resolveu o bloqueio...` | Desmarcar bloqueio sem informar responsável | Escolher `operacional` ou `gerente` — e escolher com honestidade, isso é Autonomia |
| `409 A pontuação desta sprint já foi travada` | Excluir task de sprint fechada | Não é possível. A task faz parte da base travada |
| `403 Acesso restrito a lider` | Gerente tentando abrir `/performance` | Comportamento correto. Score é do Líder |
| `500 pesos_arquetipo não configurado` | Tabela de pesos vazia | Rodar o `INSERT` de `pesos_arquetipo` no Supabase |

---

## 17. Riscos residuais assumidos

### 17.1 Ranking individual diverge do consenso da literatura

Os autores de SPACE e DORA alertam explicitamente contra usar métrica individual
para rankear pessoa. A escolha aqui de fazer ranking individual **diverge disso,
é consciente, e fica registrada**. O ranking carrega risco de competição interna,
de evasão em time forte, e de energia gasta adivinhando o critério.

As mitigações embutidas cobrem os três riscos: calibração entre gerentes (régua
compartilhada, padrão Google), dimensões objetivas oposicionais (guard-rails do
DX Core 4), peso alto em colaboração dentro da avaliação do gerente (mecanismo
anti-toxicidade da Microsoft) e divulgação só do top performer (versão suave do
reconhecimento).

### 17.2 O peso do gerente depende inteiramente de rotina humana

35% do score sai de uma leitura subjetiva cuja única defesa contra inflação é uma
reunião. Se a calibração não acontecer, o sistema mede gerente, não operacional —
e nada no código vai avisar.

### 17.3 Separação entre saúde do squad e reconhecimento da pessoa

A metodologia de nível de time — DORA, DX Core 4, SPACE mais retrospectiva — mede
a **saúde do projeto**. Este sistema mede a **pessoa**, só para reconhecer e
desenvolver. As duas ficam separadas.

O erro a evitar é deixar o ranking individual virar a métrica de saúde do squad.
Saúde do projeto é do time. Reconhecimento é da pessoa. Separadas, as duas
funcionam. Fundidas, nenhuma funciona.

### 17.4 Sub-registro de bloqueio

Ver 12.3. É o vetor de gaming mais aberto hoje.

---

## 18. Piloto e evolução

Rode o sistema em **um squad e um arquétipo por um ciclo**, com os pesos desta
metodologia. Observe:

- O que as pessoas otimizam.
- Se alguém deixa de ajudar.
- Se a distribuição de notas do questionário está espremida no topo (sinal de
  calibração falha).
- Se `qualidade_commit_media` está sendo populada — ou se está tudo `null` por
  falta de `github_login`.
- Quantas pessoas aparecem com `janela_parcial`.

Se o comportamento sair como projetado, replique. Se aparecer competição tóxica ou
queda de colaboração, suba o peso da colaboração dentro da avaliação do gerente.
Calibre os pesos após o piloto, com dado real em mãos.

Os pesos são um `UPDATE` em `pesos_arquetipo` e valem na leitura seguinte, sem
reprocessamento — o que torna a recalibração barata de propósito.

---

## 19. Decisões abertas

1. **Linha de par no fechamento de sprint.** Se entra um passo onde cada
   operacional aponta quem o ajudou, cobrindo o ponto cego do gerente sobre a
   ajuda entre pares no privado. Hoje colaboração depende só da percepção do
   gerente (pergunta 5, 5% do score).
2. **Janela de divulgação do top performer:** mensal ou por ciclo fechado.
3. **Peso de Evolução no primeiro ciclo.** Se a dimensão entra com peso maior no
   primeiro ciclo, quando não há histórico, ou com peso pleno só do segundo em
   diante, quando existe baseline de verdade. Relacionado: `baseline_evolucao`
   existe na base mas **não é lida por nenhuma fórmula** — Evolução hoje é
   exclusivamente a pergunta 6.
4. **Fechar o buraco de sub-registro de bloqueio** (12.3). Opções em aberto:
   penalizar task com travamento automático não justificado, ou trazer o sinal da
   pergunta 3 para dentro de Autonomia como blend.
5. **Valor final de `peso_commit_qualidade`** (hoje 0.5), a decidir com dado do
   piloto.
6. **CSAT do projeto.** Não é coletado hoje. Se entrar, o desenho de referência o
   colocava dentro de Entrega para o arquétipo de consultoria.

---

## Anexo A — referência técnica

### A.1 Tabelas

| Tabela | Papel |
|---|---|
| `operacionais` | Pessoa **por projeto**. `email` casa identidade cross-projeto; `github_login` casa commits; `ativo` filtra o ranking |
| `tasks` | Unidade de trabalho pontuada. `pontos`, `coluna_kanban`, `bloqueado_manual`, `bloqueado_resolvido_por`, `contador_reaberturas`, `travado_automatico` |
| `task_transicoes` | Histórico de mudanças, **com snapshot de `operacional_id`** — resolve "quem completou" |
| `task_reaberturas` | Uma linha por `concluida → em_andamento` |
| `sprints` | `pontos_orcamento` (fatia dos 100), `avaliacao_completa_em` (marca de fechamento) |
| `projects` | `arquetipo`, `valor_projeto`, `valor_por_ponto`, `wip_config` |
| `avaliacoes_gerente` | 7 respostas 0–5, `UNIQUE (operacional_id, sprint_id)`, `editavel_ate`, `reaproveitada_de` |
| `commit_qualidade` | Nota 0–10 por commit + evidência, ligada a operacional e projeto |
| `pontuacao_operacional_sprint` | **A linha travada.** Uma por (operacional, sprint). Fonte única do ranking |
| `eventos_pontuacao_tardios` | Ledger de eventos ocorridos após o fechamento da sprint de origem |
| `pesos_arquetipo` | Os 5 pesos + `peso_commit_qualidade`, por arquétipo |
| `baseline_evolucao` | Snapshot de SPI no início do ciclo. **Não lido por nenhuma fórmula hoje** |
| `audit_log` | Rastro de acesso a score |

### A.2 Endpoints

| Rota | Gate | Papel |
|---|---|---|
| `GET /performance` | `lider` + auditoria | Ranking das 3 janelas com sub-scores |
| `GET /operacionais/{id}/spi` | `lider` | SPI individual em duas camadas |
| `POST /baseline-evolucao` | `lider` | Snapshot de baseline por ciclo |
| `GET /metodologia/performance` | não-operacional | Este documento |
| `GET /avaliacoes/{sprint_id}/pendencias` | não-operacional | Quem falta avaliar |
| `POST /avaliacoes` | não-operacional | Cria/edita avaliação (48h) |
| `POST /avaliacoes/{sprint_id}/confirmar` | não-operacional | **Fecha e trava a pontuação** |
| `PATCH /sprints/{id}/orcamento` | não-operacional | Define fatia dos 100 pontos |
| `POST /ingest/commit` | público (Action) | Ingestão + nota de qualidade (só `padrao`) |

### A.3 Arquivos de código

| Arquivo | Responsabilidade |
|---|---|
| `services/pontuacao.py` | Fechamento, cutoff, eventos tardios, SPI |
| `services/performance.py` | Janelas, agregação em duas camadas, score final |
| `routers/avaliacoes.py` | Questionário, pendências, confirmação |
| `routers/performance.py` | Ranking, RBAC, auditoria |
| `routers/tasks.py` | DoR, DoD, WIP, bloqueio, reabertura, orçamento de task |
| `routers/commit_ingest.py` | Pipeline de qualidade de commit |
| `services/travamento_checker.py` | Alerta por tempo — nunca pontuação |
| `docudata-frontend/app/components/AvaliacaoSemanalModal.tsx` | UI do questionário |
| `docudata-frontend/app/performance/page.tsx` | Tela do ranking (Líder) |

---

## Anexo B — divergências entre a metodologia de referência e o implementado

Registrado para que ninguém tome o texto de referência como especificação do
sistema.

| Ponto | Metodologia de referência | Implementado hoje |
|---|---|---|
| Pesos por arquétipo | Consultoria: Entrega 30%, Qualidade 20% | **Pesos idênticos** nos dois arquétipos. Muda só a presença do sinal de commit dentro de Qualidade (decisão fechada, `.planning/intel/decisions.md` #3) |
| CSAT do projeto | Entra em Entrega para consultoria | **Não coletado** em lugar nenhum |
| SPI de cronograma, previsibilidade, aderência a escopo | Fontes de Entrega | Entrega usa **só** pontos concluídos ÷ alocados |
| Cycle time | Fonte de dimensão objetiva | Existe como métrica de projeto, **fora do score** |
| Colaboração | "Peso de verdade no cálculo" | Pergunta 5, diluída na média das 7 → **5% do score final** |
| Autonomia | Proporção de task sem retrabalho + nível de intervenção do gerente | **Só** bloqueios manuais resolvidos pelo próprio operacional |
| Evolução | Contra a baseline do início do ciclo | **Só** a pergunta 6 do gerente. `baseline_evolucao` existe mas não é lida |
| Nota de review por rubrica | Fonte de Qualidade | Substituída pela **nota de commit avaliada por IA** (0–10) |
| Anúncio do top performer | Parte do sistema | **Descopado** — anúncio é manual, fora do DocuData |
| Score com dimensão faltando | Não previsto | **Renormaliza** pelo peso disponível (11.3) |
| Calibração entre gerentes | Rotina obrigatória | Não instrumentada — **rotina humana**, sem suporte no sistema |

---

*Documento mantido em `docudata-backend/docs/metodologia-performance.md`.
Alterações de regra devem alterar o código e este documento no mesmo commit.*
