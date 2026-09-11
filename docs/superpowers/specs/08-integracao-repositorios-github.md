# Spec 08 — Repositórios GitHub vinculados ao projeto + ingestão confiável de commits

**Prioridade:** alta · **Depende de:** 01, 03, 04, 06, 07 · **Bloqueia:** rollout do commit tracker para as squads

## Contexto

A Spec 07 autenticou o script legado `hooks/docudata_agent.py`, mas a ligação entre
um repositório e um projeto ainda é apenas uma convenção manual: cada repositório
recebe um GitHub Secret `DOCUDATA_PROJECT_ID`, e o backend confia no valor enviado.

Hoje o Agente Documentador não sabe quais repositórios pertencem a um projeto. Não
há cadastro dessa relação no banco, não há tela com os repositórios conectados e o
endpoint `POST /ingest/commit` não valida a origem. Por isso, executar o hook em um
repositório qualquer com o UUID de outro projeto atribui o commit ao projeto errado.

O fluxo atual também perde rastreabilidade importante:

- o nome e o ID imutável do repositório não são salvos;
- a branch normalmente não é enviada;
- somente o hash curto aparece em `file_name`;
- não existe idempotência por repositório + SHA;
- um push com vários commits processa somente o `HEAD`;
- o diff é usado pelo Gemini, mas não existe uma origem verificável associada à
  extração;
- parte dos metadados extraídos não é serializada no contexto dos documentos.

## Objetivo

Permitir que um gerente conecte um ou mais repositórios GitHub a um projeto por uma
interface simples, sem copiar scripts, informar UUIDs ou cadastrar secrets em cada
repositório. Somente commits vindos de repositórios explicitamente associados podem
alimentar o projeto.

Esta spec implementa o recurso inicialmente **somente para projetos da subárea
`dev`**. Projetos de `dados` e todos os fluxos já disponíveis na versão implantada
devem continuar funcionando exatamente como antes. A expansão para Dados só pode
acontecer depois do piloto em Dev, mediante habilitação explícita e uma nova rodada
de validação.

O resultado esperado para o usuário é:

```text
Criar ou abrir projeto
        ↓
Configurações → Repositórios → Conectar GitHub
        ↓
Autorizar o GitHub App e selecionar um ou mais repositórios
        ↓
Repositórios aparecem como “Conectados” no projeto
        ↓
Cada push passa a alimentar automaticamente a sprint correta
```

## Decisões de arquitetura

### 1. GitHub App é o mecanismo principal

A integração deve usar um **GitHub App**, não exigir a instalação manual de
`docudata_agent.py` e `docudata.yml` em cada repositório.

O GitHub App centraliza:

- autorização e seleção de repositórios;
- assinatura verificável dos webhooks;
- leitura dos metadados e diffs dos commits;
- escrita opcional do Commit Status;
- revogação de acesso pelo próprio GitHub.

As credenciais do GitHub App ficam somente no backend. Nenhum segredo do App pode
ser retornado ou incorporado ao bundle do frontend.

### 2. Um projeto pode ter vários repositórios

Um projeto pode associar zero, um ou vários repositórios. Todos os repositórios
associados alimentam o mesmo histórico de sprints e documentos.

Um mesmo repositório GitHub não pode ficar ativo em dois projetos diferentes ao
mesmo tempo. Essa regra evita que o mesmo commit seja atribuído silenciosamente a
dois contextos. Para transferir um repositório, o usuário precisa desconectá-lo do
projeto anterior e conectá-lo ao novo.

### 3. A identidade é o `repository.id` do GitHub

O vínculo deve usar o ID numérico imutável retornado pelo GitHub. `owner/repo` é
armazenado e exibido, mas não é a chave de identidade porque pode mudar quando o
repositório é renomeado ou transferido.

### 4. A subárea continua implícita no projeto, com piloto restrito a Dev

Não existe `modo dev` no webhook. O repositório aponta para um `project_id`, e o
projeto já contém `subarea: "dados" | "dev"`. Nenhum endpoint de commit deve aceitar
uma subárea escolhida livremente pelo cliente.

Durante o rollout desta spec, os endpoints de conexão devem consultar o projeto e
permitir novos vínculos somente quando `project.subarea == "dev"`. O frontend só
exibe a seção **Repositórios GitHub** em projetos Dev enquanto a flag de rollout
estiver restrita a essa subárea.

Não adicionar `subarea` em `project_repositories`: ela continua derivada do projeto.
Isso evita inconsistência e permite expandir futuramente para Dados apenas mudando a
configuração de rollout, sem migration adicional.

### 5. O webhook não usa `X-Docudata-Key`

`POST /webhooks/github` é chamado pelo GitHub e, por isso, fica fora da dependência
global `require_app_key`. Em seu lugar, ele deve validar obrigatoriamente
`X-Hub-Signature-256` com HMAC-SHA256 e `GITHUB_WEBHOOK_SECRET` antes de interpretar
ou persistir o payload.

Todos os endpoints usados pelo frontend para listar, conectar ou desconectar
repositórios continuam protegidos por `X-Docudata-Key`, seguindo a Spec 01.

### 6. Diff bruto é efêmero

O backend pode buscar o diff completo pela API do GitHub e limitar o trecho enviado
ao Gemini, mantendo o limite atual de 8.000 caracteres. O diff bruto não deve ser
persistido no Supabase por padrão, pois pode conter código sensível ou segredos
acidentalmente commitados.

Devem ser persistidos os metadados de origem, o link para o commit, o `diff_stat` e
o conhecimento estruturado extraído. Uma reextração futura pode buscar novamente o
commit enquanto a instalação do GitHub App estiver ativa.

### 7. Commits são insumo; documentos não são atualizados retroativamente

Cada commit aceito gera uma ingestão `tipo_documentacao="commit"`. Essa ingestão
participa de novas gerações conforme o escopo do documento. Documentos já gerados
não são reescritos automaticamente quando um novo commit chega.

### 8. Compatibilidade e rollout sem regressão são requisitos de arquitetura

A integração deve ser **aditiva e opt-in**. Implantar o código da Spec 08 não pode:

- modificar projetos existentes automaticamente;
- criar vínculos de repositório por inferência;
- alterar ou reprocessar ingestões e documentos já salvos;
- mudar o comportamento de Planning, Daily, Review, Retrospectiva, geração,
  exportação para Google Docs ou custos;
- exigir variáveis do GitHub para o backend iniciar quando a funcionalidade estiver
  desabilitada;
- causar erro em páginas de projetos de Dados;
- interromper temporariamente o backend durante o deploy por depender de uma
  migration ainda não aplicada.

Compatibilidade entre versões também é obrigatória:

- frontend atual + backend novo continua funcionando;
- frontend novo + integração desligada mantém todas as telas atuais;
- se o endpoint de capabilities não estiver disponível durante um deploy, o
  frontend oculta apenas a seção GitHub e renderiza o restante do projeto;
- contratos existentes da API não perdem nem tornam obrigatórios campos novos;
- metadados de origem adicionados às respostas são opcionais para registros antigos;
- nenhum endpoint atual muda de URL, método ou semântica por causa da integração.

O código novo deve ficar protegido por feature flag, desligada por padrão. O deploy
seguro acontece em etapas independentes:

```text
1. Deploy do código com GitHub App desabilitado
2. Verificação dos fluxos atuais em produção
3. Aplicação manual da migration aditiva
4. Configuração das credenciais do GitHub App no Railway
5. Habilitação somente para subarea=dev
6. Piloto com projetos Dev selecionados
7. Validação funcional, de custo e estabilidade
8. Expansão futura para Dados, somente após aprovação explícita
```

Desabilitar a feature flag deve ser um rollback suficiente: o restante da aplicação
continua operando e as tabelas/colunas adicionais podem permanecer no banco sem
serem acessadas. O rollback não deve exigir apagar schema ou dados.

### 9. A expansão para Dados depende da aprovação do piloto Dev

Alterar `GITHUB_INTEGRATION_SUBAREAS` de `dev` para `dev,dados` não faz parte do
rollout inicial. Essa expansão só pode ser feita quando todos os gates abaixo forem
atendidos:

- suíte backend e build frontend passando com a integração ligada e desligada;
- smoke test dos fluxos atuais concluído após a migration;
- pelo menos dois repositórios Dev do mesmo projeto processando commits corretamente;
- todos os autores, committers e pushers identificados conforme os metadados do
  GitHub;
- push com múltiplos commits sem perda e sem duplicação após redelivery;
- ausência de regressão em Planning, Daily, Review, Retrospectiva, geração, custos e
  Google Docs;
- custos do Gemini por commit medidos e considerados aceitáveis;
- contexto de Review e documento project-wide validado por uma pessoa da subárea
  Dev;
- rollback por feature flag testado sem alteração ou exclusão de dados;
- aprovação explícita para iniciar a expansão.

Mesmo após aprovação, habilitar Dados deve começar como um segundo rollout
controlado. Não conectar automaticamente repositórios de projetos de Dados já
existentes.

## Escopo

### 1. Configuração do GitHub App

Documentar a criação de um GitHub App com, no mínimo:

- **Repository permissions**:
  - Metadata: read-only;
  - Contents: read-only;
  - Commit statuses: read and write;
- **Subscribe to events**:
  - Push;
  - Installation;
  - Installation repositories;
- webhook apontando para `POST /webhooks/github`;
- callback/setup URL apontando para o backend.

Adicionar apenas ao backend:

```env
GITHUB_INTEGRATION_ENABLED=false
GITHUB_INTEGRATION_SUBAREAS=dev
GITHUB_APP_ID=
GITHUB_APP_SLUG=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=
GITHUB_CONNECTION_STATE_SECRET=
```

Os valores devem ser documentados em `.env.example` e no mapa de variáveis do
projeto. `GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET` e
`GITHUB_CONNECTION_STATE_SECRET` nunca podem usar prefixo `NEXT_PUBLIC_`.

Regras das flags:

- `GITHUB_INTEGRATION_ENABLED` usa `false` como default seguro;
- `GITHUB_INTEGRATION_SUBAREAS` aceita lista separada por vírgula e começa como
  `dev`;
- credenciais do GitHub só são validadas quando a integração estiver habilitada;
- com a integração desligada, o backend inicia normalmente mesmo sem nenhuma env do
  GitHub;
- a configuração efetiva, sem segredos, pode ser exposta por um endpoint protegido
  de capabilities para o frontend decidir se mostra a seção;
- o frontend não deve manter uma flag independente que possa divergir do backend.

Centralizar criação de JWT, installation token e chamadas à API do GitHub em um
serviço de backend; routers e componentes não devem duplicar essa lógica.

### 2. Modelo de dados

Adicionar, por migration SQL comentada em `supabase_schema.sql`, sem executar
automaticamente:

A migration deve ser exclusivamente aditiva:

- `CREATE TABLE IF NOT EXISTS` para tabelas novas;
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para colunas novas;
- colunas novas em `ingestions` começam nullable e sem backfill obrigatório;
- `CREATE INDEX IF NOT EXISTS` para índices;
- nenhum `DROP`, rename, mudança de tipo ou alteração destrutiva de constraint
  existente;
- nenhuma atualização em massa de projetos, ingestões ou documentos atuais.

O SQL deve ser revisado e aplicado manualmente no Supabase. O código implantado com
a feature desligada não pode consultar as tabelas novas, permitindo publicar o
backend antes da migration sem quebrar o deploy atual.

Antes de aplicar o SQL em produção, registrar um backup ou ponto de restauração e
testar a mesma migration em um ambiente de validação. Índices potencialmente caros
devem ser criados de forma compatível com o volume atual e em janela segura. A
migration não deve ficar acoplada ao startup do FastAPI, ao build do frontend ou ao
deploy do Railway/Vercel.

#### `project_repositories`

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | uuid | PK, `gen_random_uuid()` |
| `project_id` | uuid | FK para `projects`, cascade delete |
| `github_repository_id` | bigint | NOT NULL, UNIQUE global |
| `installation_id` | bigint | NOT NULL |
| `full_name` | text | NOT NULL, `owner/repository` para exibição |
| `html_url` | text | NOT NULL |
| `default_branch` | text | nullable |
| `active` | boolean | NOT NULL, default true |
| `connected_at` | timestamptz | default `now()` |
| `updated_at` | timestamptz | default `now()` |

Desconectar deve marcar `active=false`, não apagar imediatamente a linha. Isso
preserva a rastreabilidade das ingestões históricas.

#### Metadados de origem em `ingestions`

Adicionar colunas nullable para não quebrar ingestões de arquivo já existentes:

| Coluna | Tipo | Uso |
|---|---|---|
| `source_repository_id` | uuid | FK para `project_repositories` |
| `source_repository_full_name` | text | snapshot de `owner/repo` no momento da ingestão |
| `source_commit_sha` | text | SHA completo |
| `source_branch` | text | branch do push |
| `source_url` | text | URL do commit no GitHub |
| `source_diff_stat` | text | estatística resumida do diff |

Criar índice único parcial em `(source_repository_id, source_commit_sha)` quando o
SHA não for nulo. Esse índice é a garantia final contra duplicação, inclusive após
retry ou redelivery do webhook.

#### Controle de deliveries

Adicionar uma tabela pequena `github_webhook_deliveries`:

| Coluna | Tipo | Uso |
|---|---|---|
| `delivery_id` | text | PK; valor de `X-GitHub-Delivery` |
| `event` | text | evento de `X-GitHub-Event` |
| `status` | text | `received`, `processing`, `succeeded`, `failed`, `ignored` |
| `attempts` | int | tentativas de processamento |
| `last_error` | text | erro sanitizado, sem tokens ou payload completo |
| `created_at` | timestamptz | auditoria |
| `updated_at` | timestamptz | auditoria |

Não armazenar o payload bruto indefinidamente nessa tabela.

### 3. Fluxo de conexão no backend

Implementar endpoints equivalentes a:

```text
POST   /projects/{project_id}/repositories/github/session
GET    /integrations/github/callback
GET    /integrations/github/repositories
POST   /projects/{project_id}/repositories
GET    /projects/{project_id}/repositories
DELETE /projects/{project_id}/repositories/{repository_id}
```

#### Início da conexão

`POST /projects/{project_id}/repositories/github/session`:

1. confirma que o projeto existe;
2. gera um `state` opaco, assinado, de uso único e curta duração;
3. associa internamente o state ao projeto;
4. retorna a URL oficial de instalação/configuração do GitHub App.

O `state` não pode confiar em um `project_id` não assinado vindo do callback.

#### Callback

`GET /integrations/github/callback`:

1. valida assinatura, expiração e uso único do `state`;
2. recebe o `installation_id` do GitHub;
3. cria um token opaco e temporário de conexão;
4. redireciona para a aba de configurações do projeto.

O frontend usa o token temporário apenas para listar os repositórios acessíveis
naquela instalação e confirmar quais serão associados. O installation token real
do GitHub nunca é retornado ao browser.

#### Associação

Ao confirmar os repositórios:

1. o backend consulta a API do GitHub com o installation token;
2. confirma ID, nome, URL e permissão de cada repositório selecionado;
3. impede associação a outro projeto ativo;
4. faz upsert em `project_repositories`;
5. invalida o token temporário da conexão.

### 4. Fluxo no frontend

Na aba **Configurações** do dashboard do projeto, adicionar a seção
**Repositórios GitHub**.

Durante o piloto, essa seção aparece somente se:

```text
GITHUB_INTEGRATION_ENABLED=true
e
project.subarea está em GITHUB_INTEGRATION_SUBAREAS
```

Portanto, projetos de Dados mantêm a tela e o fluxo atuais sem botão, requisição ou
mensagem nova relacionada ao GitHub.

Estado vazio:

```text
Nenhum repositório conectado
Conecte o GitHub para que commits alimentem automaticamente o contexto do projeto.

[ Conectar GitHub ]
```

Estado conectado:

```text
Repositórios conectados

✓ citi-org/projeto-frontend   main       Ativo
✓ citi-org/projeto-backend    develop    Ativo

[ Conectar outro repositório ]
```

Requisitos de UX:

- não pedir UUID, App Secret, webhook secret ou installation ID;
- permitir selecionar vários repositórios na mesma conexão;
- explicar que todos alimentarão o projeto atualmente aberto;
- mostrar erro amigável se um repositório já pertencer a outro projeto;
- desconexão exige confirmação e informa que o histórico não será apagado;
- após perda de permissão no GitHub, mostrar `Permissão revogada` e ação de
  reconectar;
- o projeto pode ser criado sem repositório; a conexão é um passo recomendado, não
  bloqueante;
- após criar um projeto Dev, mostrar um banner discreto com ação
  **Conectar repositórios** até que exista pelo menos um vínculo ativo.

Chamadas HTTP permanecem centralizadas e tipadas em `app/lib/api.ts`.

### 5. Recebimento e validação do webhook

Criar `POST /webhooks/github` com o seguinte comportamento, nesta ordem:

1. ler o corpo bruto da requisição;
2. validar `X-Hub-Signature-256` com comparação constante;
3. rejeitar assinatura ausente ou inválida antes de parsear/processar o evento;
4. registrar `X-GitHub-Delivery` para idempotência;
5. tratar apenas eventos previstos;
6. responder eventos irrelevantes com sucesso e status `ignored`, sem Gemini;
7. nunca logar private key, webhook secret, installation token ou diff completo.

Para `push`:

- ignorar tags e branches apagadas;
- identificar o repositório por `repository.id`;
- exigir vínculo ativo em `project_repositories`;
- derivar o projeto exclusivamente desse vínculo;
- nunca aceitar `project_id` do payload do GitHub;
- capturar a branch a partir de `ref`;
- processar **todos os commits do push**, não apenas `head_commit`;
- se o payload estiver truncado, usar a API Compare/Commits do GitHub para obter a
  lista completa;
- buscar os dados/diff de cada SHA usando o installation token correspondente;
- preservar o limite de conteúdo enviado ao Gemini;
- continuar aplicando `[sprint:N]` na mensagem como override explícito;
- sem override, usar a mesma regra atual de sprint vigente;
- não chamar o Gemini se `(repository, SHA)` já estiver persistido.

Um erro em um commit não deve descartar os demais commits do push. A delivery deve
registrar sucesso parcial/erro de forma observável, e um redelivery deve tentar
somente os SHAs ainda ausentes.

### 6. Extração e persistência

Reutilizar um único serviço de extração de commits entre o webhook novo e qualquer
compatibilidade temporária com o endpoint legado. Não duplicar prompt, cálculo de
tokens ou insert em routers diferentes.

O Gemini continua extraindo:

- resumo;
- tarefas;
- decisões;
- problemas/bugs;
- contexto do cliente explicitamente mencionado;
- próximos passos;
- tecnologias introduzidas/usadas;
- tecnologias explicitamente removidas.

Persistir na mesma ingestão:

- metadados verificáveis de origem;
- `_meta_autor`;
- `_meta_data_commit`;
- `_meta_commit_msg`;
- `_meta_repository`;
- `_meta_branch`;
- tokens e custo reais retornados pelo Gemini.

O Commit Status no GitHub deve indicar sucesso somente depois da persistência da
ingestão. Falha de uma chamada de status não apaga uma ingestão já salva.

### 7. Uso no contexto completo do projeto

Ingestões de commit devem continuar na tabela `ingestions`, pois o
`generation_graph` já consulta essa tabela para compor os documentos.

Escopo esperado:

| Documento | Uso de commits |
|---|---|
| Planning | não; usa somente a ingestão que originou o Planning |
| Daily | não; usa somente a ingestão que originou a Daily |
| Ata | não; usa somente a ingestão da reunião |
| Repasse semanal | commits da sprint selecionada |
| Review | commits da sprint selecionada |
| Retrospectiva | commits da sprint selecionada |
| Log de decisões | commits de todas as sprints |
| Onboarding | commits de todas as sprints |
| Documentação final | commits de todas as sprints |

Atualizar `compilar_contexto` para serializar explicitamente, quando a ingestão for
um commit:

```text
Origem: owner/repository
Branch: nome-da-branch
Commit: SHA completo e URL
Autor e data
Mensagem do commit
Resumo
Tarefas
Decisões
Problemas
Tecnologias
Tecnologias removidas
Próximos passos
```

O diff bruto não entra diretamente no contexto dos documentos. O contexto usa a
extração estruturada para controlar tamanho, custo e exposição de código.

Busca por tecnologia e timeline devem continuar considerando `tecnologias` e
`tecnologias_removidas` vindas de commits.

### 8. Interface do histórico de commits

Na seção de commits da sprint, mostrar pelo menos:

- `owner/repository`;
- branch;
- hash curto com link para o commit;
- mensagem;
- autor;
- data;
- resumo extraído;
- estado de processamento, quando aplicável.

Em projetos com múltiplos repositórios, permitir filtrar o histórico por
repositório. O filtro é apenas de visualização e não altera o contexto persistido.

### 9. Instalação removida ou permissões alteradas

Tratar eventos `installation` e `installation_repositories`:

- repositório removido da instalação → `active=false`;
- instalação suspensa/revogada → todos os vínculos daquela instalação ficam
  inativos;
- instalação reativada → sincronizar novamente antes de marcar como ativa;
- renome do repositório → atualizar `full_name` e `html_url`, preservando o ID;
- histórico de commits permanece visível após desconexão.

### 10. Transição do hook legado

`hooks/docudata_agent.py` e `hooks/docudata.yml` não devem continuar como mecanismo
principal depois que o GitHub App estiver validado.

Durante o piloto Dev, o endpoint e o hook legados permanecem funcionando como hoje
para não quebrar qualquer instalação já existente. Não remover rota, env ou
comportamento legado no mesmo deploy que introduz o GitHub App.

O endurecimento ou desligamento do legado acontece somente após:

1. levantar quais repositórios realmente usam o workflow atual;
2. migrá-los para o GitHub App;
3. validar o piloto em Dev;
4. confirmar que não há chamadas legítimas ao endpoint antigo.

Na fase posterior, se o endpoint for mantido, ele não poderá aceitar apenas
`project_id` + segredo global: deverá enviar a identidade do repositório e usar uma
credencial específica do vínculo, validada contra `project_repositories`.

Somente após a conclusão aprovada do piloto Dev e a migração dos consumidores
legítimos do hook:

- desabilitar o modo legado por padrão;
- remover das instruções para novas squads a cópia manual de workflow;
- manter ingestões antigas legíveis;
- não atribuir automaticamente origem a registros antigos sem evidência;
- exibir registros antigos sem repositório como `Origem não registrada (legado)`.

## Segurança

- validar toda assinatura de webhook com o corpo bruto;
- usar comparação constante para HMAC;
- não confiar em `owner/repo` sem confirmar o `repository.id` pela API do GitHub;
- não aceitar `project_id`, `subarea` ou `installation_id` escolhidos pelo webhook;
- installation tokens ficam apenas em memória e expiram normalmente;
- private key e secrets nunca aparecem em respostas, logs ou frontend;
- tokens temporários de conexão são opacos, expiram e têm uso único;
- validar que o projeto existe antes de iniciar conexão;
- não permitir o mesmo repositório ativo em dois projetos;
- limitar tamanho de diffs e mensagens antes do prompt;
- sanitizar erros vindos do GitHub antes de retorná-los ao frontend;
- webhook inválido não pode consumir Gemini nem escrever no Supabase.

## Tratamento de erros

Mensagens de frontend devem ser orientadas à ação:

- instalação cancelada: `A conexão com o GitHub foi cancelada.`
- sem repositórios autorizados: `Selecione pelo menos um repositório no GitHub.`
- já associado: `Este repositório já está conectado ao projeto <nome>.`
- permissão removida: `O GitHub não permite mais acessar este repositório. Reconecte a integração.`
- falha temporária: `Não foi possível consultar o GitHub agora. Tente novamente.`

O webhook deve responder de forma compatível com redelivery e registrar falhas sem
expor payloads sensíveis.

## Testes automatizados obrigatórios

Backend, com GitHub e Gemini mockados e sem rede real:

- com a feature flag desligada, o backend inicia sem envs do GitHub;
- com a feature desligada, nenhum fluxo existente consulta tabelas da integração;
- projeto `dados` não pode iniciar conexão durante o piloto;
- projeto `dev` pode iniciar conexão quando a feature está habilitada;
- todos os testes existentes continuam passando sem alteração de comportamento;
- migrations são compatíveis com linhas antigas que têm campos de origem nulos;
- assinatura válida aceita;
- assinatura ausente ou inválida rejeita antes de qualquer query/Gemini;
- repositório ativo resolve o projeto correto;
- repositório não associado não cria ingestão;
- repositório inativo não cria ingestão;
- um push com vários commits cria uma ingestão por SHA;
- redelivery não duplica commits;
- dois repositórios associados alimentam o mesmo projeto;
- um repositório não pode ser associado a dois projetos ativos;
- `[sprint:N]` continua sobrescrevendo a sprint detectada;
- sem override, a sprint vigente é usada;
- metadados de repositório, branch, SHA completo e URL são persistidos;
- falha no Commit Status não desfaz a ingestão;
- commit aparece no contexto de documentos sprint-scoped e project-wide;
- commit não invade documentos ingestion-only;
- contexto serializa tecnologias e metadados de origem;
- nenhum secret é retornado pelos endpoints de integração.

Frontend:

- projetos de Dados não exibem nem consultam a integração durante o piloto;
- projetos Dev exibem a integração somente quando habilitada pelo backend;
- páginas e fluxos existentes continuam funcionando com a integração desligada;
- estado vazio e botão de conexão;
- listagem de um ou vários repositórios;
- seleção múltipla;
- tratamento de callback cancelado/expirado;
- confirmação de desconexão;
- estado de permissão revogada;
- tipos compilam sem `any` desnecessário.

## Como testar manualmente

1. Fazer deploy com `GITHUB_INTEGRATION_ENABLED=false` e confirmar que backend,
   frontend e todos os projetos atuais continuam funcionando.
2. Antes da migration, testar health, listagem, abertura de projeto, Planning,
   geração e exportação Google Docs; nenhum fluxo pode consultar tabela nova.
3. Aplicar manualmente a migration aditiva e repetir o smoke test dos fluxos atuais.
4. Habilitar `GITHUB_INTEGRATION_ENABLED=true` com
   `GITHUB_INTEGRATION_SUBAREAS=dev`.
5. Abrir um projeto de Dados e confirmar ausência total da seção GitHub.
6. Criar ou abrir um projeto em `/dev`.
7. Abrir Configurações → Repositórios GitHub.
8. Clicar em **Conectar GitHub**.
9. Autorizar dois repositórios de teste no GitHub App.
10. Confirmar que ambos aparecem no mesmo projeto, sem informar UUID ou secret.
11. Fazer um push com dois commits no primeiro repositório.
12. Confirmar que os dois aparecem uma única vez, com repositório e branch corretos.
13. Fazer um push no segundo repositório e confirmar que aparece no mesmo projeto.
14. Redeliver o primeiro webhook no GitHub e confirmar ausência de duplicação.
15. Tentar enviar webhook assinado de um repositório não associado e confirmar que
    nenhuma ingestão é criada e nenhum custo Gemini é registrado.
16. Gerar uma Review da sprint e confirmar que as informações dos commits aparecem
    no contexto/documento.
17. Gerar Onboarding ou Documentação Final e confirmar que commits dos dois
    repositórios participam do contexto completo.
18. Desconectar um repositório, fazer novo push e confirmar que não há nova ingestão.
19. Confirmar que o histórico anterior do repositório desconectado continua visível.
20. Desligar novamente a feature flag e confirmar que o fluxo atual permanece
    disponível e que não é necessário reverter a migration.

## Critérios de aceite

- [ ] O código pode ser publicado com a integração desligada sem exigir envs ou
      migration do GitHub App para o backend iniciar.
- [ ] A migration é somente aditiva e não modifica, apaga ou faz backfill dos dados
      atuais.
- [ ] Projetos, ingestões, documentos, sprints, custos e exports existentes continuam
      legíveis e funcionais após código e migration.
- [ ] Durante o piloto, somente projetos `subarea="dev"` podem conectar repositórios.
- [ ] Projetos de Dados não exibem integração, não fazem chamadas novas e preservam
      integralmente o fluxo atual.
- [ ] Desabilitar a feature flag restaura o comportamento anterior sem rollback de
      banco.
- [ ] Nenhum projeto existente ganha repositório associado automaticamente.
- [ ] Um gerente conecta GitHub pela interface sem copiar arquivos, UUIDs ou secrets.
- [ ] Um projeto aceita múltiplos repositórios ativos.
- [ ] Um repositório não pode pertencer a dois projetos ativos.
- [ ] Somente webhooks com assinatura válida são processados.
- [ ] Somente repositórios ativos e cadastrados podem gerar ingestões.
- [ ] O projeto é resolvido pelo vínculo persistido, nunca por `project_id` enviado
      pelo evento.
- [ ] Todos os commits de um push são processados, não apenas o `HEAD`.
- [ ] Redelivery/retry não duplica `(repositório, SHA)`.
- [ ] Cada ingestão salva repositório, branch, SHA completo, URL, autor, data e
      mensagem.
- [ ] O conhecimento estruturado do commit entra em novas gerações sprint-scoped e
      project-wide conforme a tabela de escopo.
- [ ] Tecnologias e metadados de origem aparecem explicitamente no contexto compilado.
- [ ] O diff bruto não é persistido nem incluído diretamente em documentos.
- [ ] Desconectar impede novas ingestões sem apagar o histórico.
- [ ] O fluxo legado continua funcionando durante o piloto e só pode ser endurecido
      ou desabilitado após migração e validação explícitas.
- [ ] `pytest` passa integralmente.
- [ ] `npm run build` passa sem erro de tipo.
- [ ] O teste manual com dois repositórios e push de múltiplos commits passa.

## Não faz parte desta spec

- habilitar a integração para projetos de Dados durante o piloto;
- migrar ou vincular automaticamente projetos existentes;
- reprocessar ingestões ou regenerar documentos atuais;
- remover tabelas, colunas, constraints ou dados já implantados;
- desligar o hook legado antes da conclusão do piloto Dev;
- autenticação de usuários, login ou permissões por pessoa;
- integração com GitLab, Bitbucket ou Azure DevOps;
- ingestão de Issues, Pull Requests, comentários ou Releases;
- alteração automática de código nos repositórios;
- criação automática de commits/workflows nas squads;
- atualização retroativa de documentos já gerados;
- atribuição inventada de repositório a ingestões legadas;
- armazenamento permanente do diff bruto;
- execução automática da migration contra o Supabase.

## Ordem recomendada de implementação

1. Implementar feature flags com defaults seguros e testes de regressão.
2. Escrever migration comentada, exclusivamente aditiva, e modelos de dados.
3. Publicar o código com a integração desligada e validar os fluxos atuais.
4. Aplicar a migration manualmente e repetir os testes de regressão.
5. Implementar serviço central do GitHub App e testes de assinatura.
6. Implementar sessão/callback e endpoints restritos a projetos Dev.
7. Implementar UI de conexão apenas para o piloto Dev.
8. Implementar webhook, idempotência e processamento de todos os commits.
9. Centralizar a extração hoje existente em `commit_ingest.py` sem quebrar o legado.
10. Completar persistência e serialização no contexto.
11. Atualizar histórico de commits no frontend.
12. Habilitar somente `dev` e validar com dois repositórios de teste.
13. Observar estabilidade, custos e qualidade do contexto durante o piloto.
14. Planejar a expansão para Dados como etapa posterior e explicitamente aprovada.
15. Endurecer ou desabilitar o mecanismo legado somente após migração confirmada.
