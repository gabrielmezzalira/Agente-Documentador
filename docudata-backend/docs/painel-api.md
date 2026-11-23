# API de leitura para o Painel do Projeto CITi

Rotas **somente leitura** que o Painel do Projeto CITi usa para puxar dados do DocuData.
Prefixo: `/integracoes/painel/v1`. Código: `routers/painel_leitura.py` e `services/painel_leitura.py`.

## Autenticação

Header `X-Painel-Key` com o valor de `DOCUDATA_PAINEL_KEY`.

- Chave **dedicada**, no padrão da `X-Discovery-Key`: não reusa `DOCUDATA_APP_SECRET`; cada uma gira separada.
- Variável ausente: **503** (falha fechada). Chave ausente ou errada: **401**.
- Só `GET`. Nenhuma rota escreve no banco.

## Rotas

`{id}` é o `projects.id` (uuid) do DocuData. Id que não é uuid ou projeto inexistente: **404**.
Datas em ISO 8601. Campo sem valor é omitido, exceto onde indicado `null`.

| Rota | Resposta |
|---|---|
| `GET /projetos/{id}/kanban?sprint=N` | `[{ id, titulo, coluna, colunaTipo, progresso?, bloqueadoPorCliente, bloqueadaDesde?, concluidaEm?, responsavel? }]` |
| `GET /projetos/{id}/indicadores?sprint=N` | `{ sprintNumero, sprintTotal, inicio, fim, prazoConsumidoPct, escopoConcluidoPct, spi \| null, desvioPontos, toleranciaPct, saude \| null }` |
| `GET /projetos/{id}/escopo` | `[{ id, codigo, nome, prioridade, data \| null, criterios: [{ texto, atendido }] }]` |
| `GET /projetos/{id}/atas` | `[{ id, data, titulo, markdown }]` |
| `GET /projetos/{id}/documentos` | `[{ id, nome, ext, data, tamanhoBytes }]` (sem atas, sem link) |
| `GET /projetos/{id}/pessoas` | `[{ id, nome, papel }]` (sem e-mail) |
| `GET /projetos/{id}/commits?desde=&ate=` | `{ count }` |

Sem `sprint`, vale a sprint iniciada de maior número.

## Como cada campo é calculado

- **colunaTipo**: `planejado` → `A_FAZER`; `em_andamento` e `pendente_aprovacao` → `OUTRA`; `concluida` → `CONCLUIDO`.
- **bloqueadoPorCliente**: `bloqueado_manual` e `bloqueio_tipo = 'cliente'` (a mesma regra do travamento).
- **progresso**: itens `done` do checklist ÷ total (omitido sem checklist).
- **concluidaEm**: transição mais recente para `concluida` em `task_transicoes`.
- **spi**: pontos concluídos (sem extras) ÷ previsto da sprint (`previsto_da_sprint`); `null` sem previsto.
- **desvioPontos**: pontos concluídos − previstos.
- **saude**: `sprints.status_saude` se definida; senão derivada do SPI (≥ 0,9 verde, ≥ 0,7 amarelo, abaixo vermelho); `null` sem previsto.
- **escopoConcluidoPct**: pontos concluídos ÷ pontos de todas as tasks do projeto (sem extras).
- **prazoConsumidoPct**: (hoje − início do contrato) ÷ (fim contratado − início), de 0 a 100, em America/Recife.
- **sprintTotal**: semanas entre o início e o fim do contrato (mínimo: o número da sprint).
- **inicio/fim**: da sprint; sem datas, derivadas do início do contrato (cada sprint tem uma semana).
- **escopo.prioridade**: `must`/`should`/`could`; `wont` vira `COULD`.
- **escopo.data**: fim da sprint em `sprint_alvo`; `null` se não houver. O DocuData não guarda data por funcionalidade.
- **escopo.criterios.atendido**: o DocuData só sabe se a funcionalidade inteira está `concluida`; todos os critérios herdam isso.
- **atas**: `generated_docs` com `doc_type = 'ata_reuniao'`; o título é a primeira linha do markdown.
- **commits**: linhas de `commit_qualidade` (commits analisados) com `criado_em` na janela.

## Limites conhecidos

- Documentos e atas são os **gerados** pelo DocuData; não há arquivo para baixar.
- `commits` conta commits analisados, não todos os commits do GitHub.
- Sem paginação: projetos têm centenas de tasks, não milhares.

## Configuração

1. Gere uma string longa e aleatória.
2. No Railway do DocuData: `DOCUDATA_PAINEL_KEY=<valor>`.
3. No Railway do Painel: `DOCUDATA_TOKEN=<o mesmo valor>` (o painel envia como `X-Painel-Key`).
