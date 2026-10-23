# Rodada A2 — Classificador do nível da task

Data: 2026-10-23 · Branch: `feat/classificador-nivel` (a partir de `origin/main` e787d78, com a A1 em produção)

## Contexto

A A1 criou a régua única de dificuldade (1, 2, 3 e 5). Hoje quem escolhe o nível é o gerente, no seletor do modal "Nova task" do Kanban, que é o único lugar onde uma task nasce (`TasksKanbanTab.tsx` → `POST /tasks`).

A proposta institucional pede um classificador. Ele lê o título, a descrição e o checklist da task, compara com as tasks concluídas parecidas do histórico de todos os projetos e usa o tempo real delas para ajustar o nível. A base cresce a cada task concluída.

Esta rodada entrega esse classificador, o aprendizado contínuo e uma tela de acompanhamento para líder e owner.

## Decisões

| Tema | Decisão |
|---|---|
| Quem define o nível | **O agente.** O gerente não escolhe nem altera. Isso diverge do texto da proposta ("a decisão continua sendo do gerente") e é decisão do usuário. |
| Opinião do gerente | Campo opcional ao criar a task. Não define o nível. É uma leitura a mais, com peso pequeno, merecido e com teto. |
| Opinião do operacional | Pergunta opcional ao concluir. Não muda o nível daquela task, que já está travado. Entra só no aprendizado, com no máximo um degrau e peso merecido. |
| Quando ajusta | **Na hora**, a cada task concluída: média por nível, ritmo por pessoa, viés por gerente, pesos dos sinais e peso das opiniões. |
| Tasks parecidas | Embeddings no `pgvector` do Supabase. |
| Tempo real | Do primeiro Em Andamento até a última conclusão, descontando o bloqueio de **cliente** e o tempo em `pendente_aprovacao`. O bloqueio interno conta. A task reaberta soma os trechos e fica marcada. |
| Tempo típico | **Média** do tempo normalizado por nível, sem as tasks excluídas. A tela mostra também a média com todas. |
| Casos que puxam demais | Tasks acima de 3× a média do nível viram alerta. Líder ou owner decidem tirar ou manter na contagem, e a decisão é reversível. |
| Fator de projeto | Não existe. É uma regra geral para todos. |
| Modo sombra | Não existe. O classificador vale desde o primeiro dia. |
| Gerente vê o nível | Sim, depois de salvar, com a frase geral da justificativa e sem as notas por sinal. |
| Classificador fora do ar | Cria com nível provisório (opinião do gerente ou 2) e reclassifica automaticamente depois. |
| Evolução para modelo treinado | Fica fora desta rodada, mas os dados de treino são guardados desde o primeiro dia (§9). |

## 1. Régua e critérios (versão `v1`)

Os níveis e rótulos continuam os da A1: `1 · simples`, `2 · moderada`, `3 · complexa` e `5 · muito complexa`.

**Critério de cada nível** (texto dado ao modelo):

| Nível | Critério |
|---|---|
| 1 | Mudança pontual em uma parte do sistema, caminho já conhecido e sem incerteza. |
| 2 | Mexe em mais de uma parte seguindo um padrão que já existe, com pouca incerteza. |
| 3 | Várias partes integradas ou regra de negócio não trivial, com alguma incerteza técnica. |
| 5 | Incerteza alta: exige investigação, decisão de arquitetura ou tecnologia nova para o time. |

**Sinais extraídos do texto.** Cada sinal recebe nota 0, 1 ou 2 e precisa citar o trecho do texto que a justifica.

| Sinal | 0 | 1 | 2 |
|---|---|---|---|
| `partes` — partes do sistema | uma | duas | três ou mais |
| `novidade` | repete um padrão do projeto | adapta um padrão existente | o projeto nunca fez |
| `incerteza` | o que fazer está claro | há pontos a decidir | precisa investigar antes |
| `dependencia` — dependência externa | nenhuma | outra parte interna | terceiro ou cliente |
| `tamanho` — itens de checklist ou entregáveis | 1–2 | 3–5 | 6 ou mais |
| `risco` | nada sensível | regra de negócio importante | dados de produção, migração, segurança, pagamento |

Os critérios e os sinais ficam em `services/classificador_regua.py`, com a constante `VERSAO_REGUA = "v1"`. A revisão do rito mensal vira uma alteração versionada desse arquivo. Cada classificação guarda a versão que usou.

## 2. Dados

Tudo entra num bloco idempotente "Rodada A2" no fim de `supabase_schema.sql`, aplicado manualmente.

- `CREATE EXTENSION IF NOT EXISTS vector;`
- **`task_embeddings`**
  - `task_id uuid PK REFERENCES tasks ON DELETE CASCADE`, `embedding vector(<dim>)`, `modelo text`, `hash_texto text`, `atualizado_em timestamptz`.
  - Índice HNSW com `vector_cosine_ops`.
  - A dimensão (768 desejado) é confirmada no teste rápido (§8).
- **`task_classificacoes`**
  - Identificação e tipo: `id`, `task_id` (FK cascade), `tipo` (`criacao` | `reclassificacao`), `criado_por uuid`, `criado_em`, `versao_regua`, `modelo`.
  - Leitura dos sinais: `sinais jsonb` (`{sinal: {nota, evidencia}}`) e `nivel_sinais`.
  - Leitura das parecidas: `parecidas jsonb` (`[{task_id, similaridade, nivel_real, tempo_normalizado_s}]`) e `nivel_parecidas`.
  - Avaliação geral: `nivel_geral` e `justificativa_geral`.
  - Combinação: `opiniao_gerente`, `nivel_combinado`, `ajuste_tempo` (−1, 0 ou 1) e `nivel_final`.
  - Situação: `status` (`aplicada` | `em_revisao` | `provisoria`), `motivo_revisao` e `parametros jsonb` (a foto dos parâmetros usados).
  - A classificação mais recente de cada task é a que vale.
- **`task_aprendizado`** — um exemplo por task concluída, regravado se a task for reconcluída.
  - Contexto: `task_id PK`, `classificacao_id`, `nivel_sugerido`, `operacional_id` e `gerente_id`.
  - Tempos: `tempo_bruto_s`, `tempo_limpo_s`, `ritmo_usado` e `tempo_normalizado_s`.
  - Rótulos: `reaberta`, `nivel_pelo_tempo`, `opiniao_operacional` e `nivel_real`.
  - Alerta e exclusão: `alerta`, `excluida`, `excluida_por`, `excluida_em` e `motivo_exclusao`.
  - Datas: `concluida_em` e `atualizado_em`.
- **`classificador_parametros`**
  - `tipo`, `chave`, `valor numeric`, `n_amostras int` e `atualizado_em`, com PK (`tipo`, `chave`).
  - Os tipos são `media_nivel`, `ritmo_pessoa`, `vies_gerente`, `peso_sinal`, `peso_opiniao_gerente` e `peso_opiniao_operacional`.
- **`classificador_parametros_hist`** — uma linha por mudança de parâmetro, para gráficos e auditoria.
- `tasks.nivel_travado_em timestamptz`.
- `task_transicoes.bloqueio_tipo text CHECK (bloqueio_tipo IN ('interno','cliente'))`.
  - É gravado a partir da A2 em cada transição de `bloqueado`.
  - Trechos antigos sem tipo contam como internos, ou seja, não são descontados.

## 3. Grafo de classificação

O grafo fica em `graphs/classificacao_graph.py`, compilado uma vez no carregamento do módulo. O estado leva título, descrição, checklist, `project_id`, `gerente_id` e a opinião do gerente, e acumula os resultados de cada nó.

1. **`verificar_suficiencia`** (sem modelo)
   - Exige título e, além dele, descrição não vazia ou checklist com pelo menos 2 itens.
   - Se faltar, o grafo termina com `faltando`.
2. **`extrair_sinais`** (Gemini)
   - Devolve um JSON validado com os 6 sinais, nota e evidência citada.
   - Nota sem evidência que apareça literalmente no texto vira 0.
   - Sinal que não dá para avaliar vira `faltando`, com a pergunta a fazer ao gerente.
   - JSON inválido tem até 2 novas tentativas. Depois disso, a classificação vira provisória.
3. **`buscar_parecidas`**
   - Gera o embedding do texto (título, descrição e checklist).
   - Busca as 8 tasks concluídas mais próximas em `task_embeddings`, considerando só as que têm `task_aprendizado` não excluído.
   - `nivel_parecidas` é a média do `nivel_real` delas, ponderada pela similaridade e arredondada para a régua.
4. **`avaliacao_geral`** (Gemini)
   - Lê a task, os critérios do nível e as parecidas (com nível real e tempo) e devolve nível e justificativa.
   - Não vê os pesos nem a opinião do gerente.
5. **`combinar`** (sem modelo)
   - Calcula uma escala contínua: `Σ peso_sinal × nota` (mapeada para a régua), `nivel_parecidas`, `nivel_geral` e `opiniao_gerente × peso_opiniao_gerente`, que é limitado a 0,15 do total e sozinho nunca move um degrau.
   - Soma o `vies_gerente` daquele gerente.
   - Arredonda para o nível da régua mais próximo.
   - Marca `em_revisao` em dois casos: as três leituras do agente se espalham por mais de um degrau da régua, ou o texto tem trechos com cara de instrução ao classificador.
6. **`ajuste_tempo`** (sem modelo)
   - Se a média do `tempo_normalizado_s` das parecidas estiver mais perto da média de outro nível do que da do nível combinado, move um degrau na direção dele.
   - Nunca move mais de um degrau.
7. **`salvar`**
   - Grava `task_classificacoes`, atualiza `tasks.pontos` com `nivel_final` e faz o upsert do embedding da task.

O texto da task vai aos prompts como **dado delimitado**, nunca como instrução. A saída é sempre validada por schema.

## 4. Aprendizado

Fica em `services/classificador_aprendizado.py`, só com cálculo, sem modelo. Roda depois que a task é gravada como `concluida`, em modo melhor esforço: uma falha é registrada e não bloqueia a conclusão. Os passos:

1. **Tempo limpo.** Vem de `task_transicoes`: do primeiro `em_andamento` até a última `concluida`, menos os intervalos em `pendente_aprovacao` e os intervalos com `bloqueado = true` e `bloqueio_tipo = 'cliente'`. Reabertura marca `reaberta = true`.
2. **Ritmo da pessoa.**
   - É a média de `tempo_limpo ÷ media_nivel[nivel_real]` nas tasks dela, encolhida para 1,0: `ritmo = (n × média + 10 × 1,0) ÷ (n + 10)`.
   - O tempo normalizado é `tempo_limpo ÷ ritmo`.
3. **Nível pelo tempo.** É o nível cuja `media_nivel` (o valor **anterior** a esta atualização) fica mais próxima do tempo normalizado.
4. **Nível real.**
   - É o nível pelo tempo, ajustado em no máximo um degrau pela `opiniao_operacional`.
   - O ajuste só acontece se a opinião tiver peso merecido maior que 0 e se o tempo normalizado estiver dentro de 25% da fronteira com o nível opinado.
5. **Atualizações**, todas gravadas também em `classificador_parametros_hist`:
   - `media_nivel`: média do tempo normalizado dos exemplos não excluídos de cada nível real.
   - `alerta`: tempo normalizado maior que 3 × `media_nivel` do seu nível real. A task continua contando até alguém decidir.
   - `vies_gerente`: média de `nivel_real − nivel_sugerido` (em degraus da régua) nas tasks do gerente, encolhida para 0 com o mesmo fator de 10.
   - `peso_sinal`: regressão linear com mínimos quadrados limitados (pesos ≥ 0) do nível real sobre as notas dos sinais, refeita com todos os exemplos.
   - `peso_opiniao_gerente` e `peso_opiniao_operacional`: taxa de acerto da opinião contra o nível real, encolhida, com teto.
6. O embedding da task concluída passa a servir de exemplo para as próximas buscas.

**Exclusão e reinclusão** de um exemplo (líder ou owner) disparam um recálculo completo, que passa por todos os exemplos em ordem de `concluida_em` usando a regra do "valor anterior".

**Ponto de partida.** Um script único, `scripts/classificador_ponto_de_partida.py`, roda depois da migração. Para cada task concluída:

- calcula o tempo limpo e o embedding;
- extrai os sinais com o Gemini (uma chamada por task);
- grava `task_aprendizado` com `nivel_sugerido` igual ao nível convertido da A1 (`converter_pontos_legado`).

Depois roda o recálculo completo. O script pode ser reexecutado sem duplicar nada.

## 5. Ciclo de vida do nível

- **Criação.** O `POST /tasks` roda o grafo antes de inserir a task.
  - `pontos` deixa de ser obrigatório no payload e é ignorado se vier.
  - Entra o campo novo `opiniao_nivel` (opcional, na régua).
  - Respostas:
    - `faltando` → 422 com a lista do que falta, e nada é criado;
    - classificação aplicada → 201 com o nível e a justificativa geral;
    - `em_revisao` → 201 com o nível combinado e a marca de revisão;
    - classificador indisponível ou tempo esgotado (20 s) → 201 com nível provisório (opinião do gerente ou 2) e `status = provisoria`.
- **Provisória.**
  - Uma rotina a cada 10 minutos reclassifica as tasks provisórias.
  - O nível provisório não trava. Se a task já estiver em andamento, o nível trava quando a reclassificação terminar.
- **Trava.**
  - `nivel_travado_em` é preenchido quando a task entra em `em_andamento` ou quando a sprint dela começa, o que vier primeiro.
  - Isso só acontece se a classificação for `aplicada` ou se a revisão já tiver sido resolvida.
- **Edição.** Mudar título, descrição ou checklist não reclassifica. A edição fica registrada.
- **Reclassificação.** `POST /tasks/{id}/reclassificar` é só para líder e owner, com 409 se o nível estiver travado.
- **Revisão.** `POST /tasks/{id}/revisao-nivel` é só para líder e owner, com nível e motivo, e marca a classificação como resolvida.
- **Pontuação.** `tasks.pontos` continua sendo o campo que SPI, previsto e fechamento usam, sem outra mudança.

## 6. Interface

**Modal "Nova task"** (`TasksKanbanTab.tsx`)

- Nova ordem dos campos:
  1. Título
  2. Descrição, com o texto de ajuda: "Descreva o que precisa ser feito, quais partes do sistema mexe e o que ainda não está claro. O nível é definido a partir disso."
  3. Checklist
  4. Funcionalidade, Sprint e Operacional
  5. Task extra e Requer aprovação
  6. "Sua opinião sobre o nível (opcional)": seletor 1/2/3/5 com "sem opinião", e abaixo a nota "Não define o nível. É usada pelo classificador como mais uma referência."
- O seletor de pontos sai do modal.
- Ao criar:
  - o botão vira "Classificando…" e fica desabilitado;
  - um 422 mostra o pedido do agente no topo do modal e destaca o campo relacionado;
  - o sucesso fecha o modal e mostra um aviso "Task criada · nível N · rótulo", com "por quê?" exibindo a justificativa geral.
- Na edição, o nível aparece só como informação ("nível N · definido pelo classificador"). Se o texto mudar, aparece a nota "Editar o texto não muda o nível. Se a task mudou de escopo, peça reclassificação a um líder."
- Líder e owner veem "Reclassificar" enquanto o nível não está travado. Depois de travado, aparece "nível travado desde DD/MM".
- O card mostra os selos "provisório" e "em revisão" quando for o caso. O `title` do chip vira "N · rótulo · definido pelo classificador".

**Conclusão pelo operacional**

- No passo de conclusão aparece a pergunta opcional "Na sua visão, qual era o nível dessa task?" (1/2/3/5 ou pular).
- O nível do classificador só é mostrado depois da resposta.

**Tela `/classificador`** (só líder e owner, com item de menu condicional)

1. **Tempo típico por nível:** média total e média sem excluídas, número de tasks e gráfico semanal de evolução.
2. **Alertas:** lista das tasks acima de 3× a média, com "Tirar da contagem" (motivo obrigatório) e "Manter". A aba "Excluídas" tem "Devolver à contagem".
3. **Acurácia contra o tempo real:** exata, ±1, erro médio em degraus, matriz de confusão 4×4, precisão e cobertura por nível e evolução mensal. Filtros de período (30 dias, 90 dias, tudo) e de **gerente**.
4. **Por que decide assim:** pesos dos sinais e sua evolução, viés por gerente, peso e acurácia das opiniões de gerentes e operacionais, e ritmo por operacional com o aviso "ajuste interno, não é nota de desempenho".
5. **Fila de revisão:** tasks `em_revisao` e `provisoria`. O detalhe de cada uma mostra as três leituras, as notas e evidências, as parecidas, a opinião, o combinado e o ajuste pelo tempo. Daí dá para resolver com nível e motivo, ou reclassificar.

## 7. API

| Método e rota | Quem | Função |
|---|---|---|
| `POST /tasks` (alterado) | gerente, líder, owner | Classifica e cria (§5). |
| `POST /tasks/{id}/reclassificar` | líder, owner | Roda o grafo de novo; 409 se o nível estiver travado. |
| `POST /tasks/{id}/revisao-nivel` | líder, owner | Resolve a revisão com nível e motivo. |
| `PATCH /tasks/{id}` (alterado) | — | Ignora `pontos`. Grava `opiniao_operacional` quando a coluna vai para `concluida`. Dispara o aprendizado. |
| `GET /classificador/resumo?periodo=&gerente_id=` | líder, owner | Médias, alertas, acurácia e pesos. |
| `GET /classificador/revisao` | líder, owner | Fila de revisão. |
| `GET /classificador/tasks/{id}` | líder, owner | Detalhe completo da classificação. |
| `PATCH /classificador/aprendizado/{task_id}` | líder, owner | `{excluida, motivo}` e recálculo. |

## 8. Erros e riscos

| Situação | Resposta |
|---|---|
| Texto insuficiente | 422 com o que falta |
| Gemini ou embedding indisponível, ou tempo esgotado | 201 com nível provisório; reclassificação a cada 10 min |
| JSON inválido depois de 2 novas tentativas | Classificação provisória |
| Leituras divergentes ou texto com cara de instrução | `em_revisao` |
| Falha no aprendizado | A conclusão segue; erro registrado; recálculo diário |
| Reclassificar nível travado | 409 |
| Operacional ou gerente em rota de líder | 403 |

**Teste rápido obrigatório antes de tudo.** É preciso confirmar com a chave atual qual modelo de embedding do Gemini responde e com que dimensão. As chaves novas só aceitam modelos 3.5 ou superiores. Se nenhum responder, o trabalho para e volta ao usuário com alternativas.

## 9. Caminho para um modelo treinado (fora desta rodada)

Desde o primeiro dia ficam guardados o embedding, as notas, as três leituras, as opiniões, o nível final e o tempo real limpo e normalizado. Com volume suficiente (referência de 100 exemplos por nível), o caminho é:

1. um script mensal treina um modelo simples sobre esses dados;
2. o modelo entra no `combinar` como uma quarta leitura, registrada mas sem peso;
3. a tela ganha um bloco que compara a acurácia dele com a da abordagem atual;
4. o modelo passa a ter peso quando superar a abordagem atual na acurácia ±1 por meses seguidos.

O nó `combinar` trata as leituras como lista para que isso não exija refazer o grafo.

## 10. Testes

**Backend (pytest, com TDD, FakeClient e o modelo simulado)**

- `verificar_suficiencia`.
- Sinais: evidência ausente vira 0; JSON inválido gera novas tentativas e depois provisória.
- `nivel_parecidas` ponderado.
- `combinar`: teto da opinião e viés.
- Divergência e injeção levam a `em_revisao`.
- `ajuste_tempo`: no máximo ±1.
- Tempo limpo: descontos de cliente e de pendente de aprovação, e reabertura.
- Ritmo e viés com encolhimento.
- Nível real com a opinião do operacional.
- Média e alerta.
- Exclusão e reinclusão com recálculo.
- Regressão dos pesos com pesos ≥ 0.
- Provisória e rotina de reclassificação.
- Trava.
- 409 ao reclassificar nível travado.
- RBAC de todas as rotas novas.
- O `POST /tasks` ignora `pontos`.

**Frontend (`tsc --noEmit` e `npm test` estrutural)**

- Modal sem seletor de pontos, com campo de opinião e texto de ajuda.
- Estado "Classificando…".
- Pergunta ao concluir.
- Tela `/classificador` com os 5 blocos e os filtros.
- Item de menu só para líder e owner.

## 11. Entrega

1. Teste rápido do embedding (§8).
2. Migração "Rodada A2", aplicada manualmente. O usuário é avisado quando ela estiver pronta.
3. Backend e frontend no mesmo deploy. O frontend antigo continua mandando `pontos`, que passa a ser ignorado.
4. O script de ponto de partida roda logo depois do deploy.

## Fora de escopo

- O modelo treinado (§9).
- A edição dos critérios da régua por tela.
- O fator de projeto.
- A meta por sprint e o piso (rodada B).
- O relógio do cliente que pausa de verdade (rodada B).
