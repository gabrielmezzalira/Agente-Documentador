# Spec 10 — Fechamento estrutural de segurança, privacidade e escala

**Status:** pronta para implementação

**Prioridade:** crítica

**Impacto:** alto, com rollout controlado

**Dependência de outras specs:** nenhuma

**Fonte de verdade:** `AGENTS.md`, o código atual e este documento

**Estratégia:** mudanças aditivas, reversíveis e ativadas em etapas

## 1. Como usar esta spec

Esta spec complementa o contexto permanente de `AGENTS.md` com o trabalho estrutural
específico desta entrega. Quem a implementar deve ler primeiro `AGENTS.md`, depois
esta spec por completo e então inspecionar o código atual relacionado. **Não é
necessário consultar as Specs 01–09** para entender riscos, escopo, rollout ou
critérios de aceite da Spec 10.

`AGENTS.md` define invariantes do produto e regras de trabalho; esta spec define a
arquitetura-alvo, etapas e evidências do fechamento de segurança/performance. A spec
continua autocontida em relação às demais specs e repete deliberadamente os pontos
de contexto que são necessários para implementar seu escopo com segurança.

Em caso de conflito entre um comentário legado e esta spec, seguir esta spec. Em
caso de conflito com uma regra de negócio comprovadamente usada pelo código atual,
preservar o fluxo atual, documentar a divergência e escolher a alternativa mais
restritiva que não cause perda de dados.

Esta é uma entrega grande. Ela pode ser dividida em commits técnicos e deploys
intermediários, mas todos os itens marcados como obrigatórios pertencem à Spec 10.
Não declarar a spec concluída apenas porque a primeira fase foi implantada.

## 2. Resposta obrigatória antes de começar a implementação

Antes de editar qualquer arquivo, a IA ou pessoa responsável deve inspecionar o
projeto e responder ao solicitante com um **preflight operacional** contendo:

1. o que pode ser implementado apenas no código, sem ação externa;
2. quais ações humanas serão necessárias no Supabase, Railway, Vercel e GitHub;
3. em qual etapa cada ação humana será necessária;
4. quais variáveis de ambiente serão adicionadas, alteradas ou removidas;
5. quais ações são apenas recomendadas e quais bloqueiam o enforcement;
6. como será feito o rollback sem apagar dados;
7. quais suposições sobre schema e infraestrutura ainda precisam ser confirmadas.

Usar obrigatoriamente esta classificação:

| Momento | Ação externa | Obrigatória? | Quem executa |
|---|---|---:|---|
| Antes do código | Nenhuma alteração externa é necessária para escrever código, migration comentada e testes mockados. | não | — |
| Antes de testar o schema novo em staging/preview | Criar backup ou confirmar PITR e aplicar manualmente a Migration v7. | sim | pessoa com acesso ao Supabase |
| Antes de habilitar autorização nova | Executar dry-run do backfill, resolver ambiguidades e observar o modo `audit`. | sim | pessoa autorizada + implementador |
| Antes de habilitar CSRF | Publicar backend e frontend compatíveis e configurar segredo/origens. | sim | pessoa com acesso ao Railway/Vercel |
| Antes de usar fila durável | Publicar um worker separado no Railway e aplicar a parte de jobs da migration. | sim | pessoa com acesso ao Railway/Supabase |
| Antes de migrar o aceite legado | Aprovar no GitHub App a permissão mínima de Actions necessária ao novo dispatch. | sim, somente para esse fluxo | owner do GitHub App/organização |
| Após validação | Rotacionar/revogar PATs e credenciais globais legadas ainda configuradas em squads. | sim | responsáveis pelos repositórios/deploy |

A IA **não deve** executar SQL em banco real, alterar Railway/Vercel, mudar o GitHub
App, rotacionar segredo, disparar webhook real ou fazer chamada paga ao Gemini sem
autorização explícita. Ela deve escrever os artefatos e apresentar comandos/SQL
copiáveis, parar no gate externo correspondente e aguardar a confirmação humana.

Testes automatizados devem usar mocks. Testes manuais que possam gerar custo ou
modificar GitHub, Drive, Resend, Gemini ou Supabase real precisam ser identificados
antes da execução.

## 3. Contexto completo do produto

### 3.1 Arquitetura atual

- `docudata-backend/`: FastAPI, Supabase e LangGraph/Gemini; deploy no Railway.
- `docudata-frontend/`: Next.js App Router; deploy na Vercel.
- Um único backend, um único frontend e um único banco atendem as subáreas `dados`
  e `dev`.
- `projects.subarea` é a fonte de verdade da subárea de um projeto.
- O browser chama apenas o backend. O browser não recebe a service role do Supabase.
- O backend usa `SUPABASE_SERVICE_KEY`, portanto ignora RLS e precisa autorizar cada
  operação antes de consultar ou alterar dados.
- A autenticação atual usa JWT HS256 em cookie `HttpOnly` chamado
  `docudata_session`.
- Os cargos atuais são `owner`, `lider`, `gerente` e `operacional`.
- A chave Gemini é única e global, criptografada em `app_settings`; o valor nunca
  pode ser enviado ao frontend.
- O custo de IA continua pertencendo ao projeto/subárea que originou a chamada,
  embora a credencial do Gemini seja global.
- O Google Drive possui identidade/pasta por subárea. Templates de Dev podem usar os
  de Dados como fallback, conforme a configuração atual.
- O GitHub App está disponível para projetos de **Dados e Dev**. A instalação pode
  autorizar todos os repositórios da organização, mas só repositórios vinculados
  explicitamente a um projeto podem gerar ingestões para esse projeto.
- A seleção atual de repositórios mostra os 30 com push mais recente e pesquisa os
  demais sob demanda. Essa otimização deve ser preservada.
- O hook antigo com `DOCUDATA_APP_SECRET` e o PAT em `projects.github_token` existem
  apenas como compatibilidade legada; não são a arquitetura desejada.

### 3.2 Regras de isolamento que não podem ser quebradas

1. Dados e Dev não podem ver projetos uma da outra por acidente.
2. Todo recurso derivado herda a subárea e o acesso do projeto: sprint, task,
   funcionalidade, ingestão, documento, avaliação, score, solicitação, boletim,
   repositório e job.
3. O cliente nunca é a fonte de verdade para cargo, subárea ou vínculo.
4. Um endpoint que agrega vários projetos deve filtrar os projetos autorizados no
   servidor antes da agregação.
5. `owner` possui acesso global; os demais cargos têm acesso somente aos escopos
   explicitamente atribuídos.
6. Mover um projeto entre subáreas preserva seus dados e vínculos de projeto. A
   operação exige `owner` ou líder autorizado tanto na origem quanto no destino.
7. A autorização do GitHub App não equivale a vínculo com projeto. Um repositório
   autorizado na instalação, mas não vinculado, deve ser ignorado pelo webhook.
8. Nenhuma mudança desta spec pode apagar, reprocessar ou recalcular automaticamente
   o histórico existente.

### 3.3 Estado de risco confirmado no código atual

O implementador deve reconfirmar estes pontos no código, pois eles definem o motivo
do trabalho:

- `services/auth.py` aceita cargo/e-mail do JWT como autoridade até o token expirar;
- gerente e líder passam genericamente por `require_project_access`;
- vários handlers que recebem IDs de recursos filhos não resolvem o `project_id`
  antes de ler ou alterar o recurso;
- `/auth/operacionais-sem-conta`, `/auth/signup/claim` e `/auth/signup/novo` são
  públicos e permitem enumeração/cadastro sem convite verificável;
- o cookie cross-site usa `SameSite=None`, mas as mutações não têm token CSRF;
- `main.py` limita request apenas quando `Content-Length` é válido; streams sem esse
  header seguem sem limite;
- diversos uploads são lidos inteiros em memória; PDF/DOCX/texto ainda precisam de
  limites estruturais completos;
- o rate limit é em memória e o primeiro `X-Forwarded-For` é aceito sem validar o
  proxy;
- o cliente Supabase é recriado por chamada e há I/O síncrono dentro de alguns
  handlers assíncronos;
- há construções diretas de `ChatGoogleGenerativeAI` espalhadas por routers, graphs
  e services, com telemetria de custo parcial;
- documentos, texto e diffs podem conter segredos ou instruções hostis antes de
  chegarem ao modelo;
- autoria de commit pode ser inferida por e-mail Git não verificado e influenciar
  score;
- webhook GitHub faz trabalho de GitHub/Gemini antes de responder e uma delivery
  pode ficar indefinidamente em `processing`;
- `AsyncIOScheduler` inicia em todo processo FastAPI e tarefas importantes usam
  `BackgroundTasks`, podendo duplicar ou se perder em restart;
- exportação Google Docs é síncrona, pode criar cópia duplicada após falha parcial e
  ainda constrói clients com discovery cache legado;
- o aceite de funcionalidades ainda lê `projects.github_token`/`github_repo` e usa
  PAT armazenado em texto;
- busca de tecnologias baixa JSON de muitas ingestões para filtrar em Python;
- ranking de performance faz queries por pessoa e pode misturar escopos;
- listas e contexto de geração podem crescer sem limite.

### 3.4 Modelo de ameaça e fronteiras de confiança

Proteger prioritariamente:

- isolamento entre Dados, Dev, projetos e pessoas;
- documentos, diffs, e-mails, score e dados de contrato;
- chaves Supabase/Gemini/Google/GitHub/Resend e cookies de sessão;
- integridade de autoria, avaliação, pontuação e histórico;
- orçamento Gemini e disponibilidade do backend/worker.

Considerar como não confiáveis: browser, parâmetros/UUIDs, arquivos enviados,
Markdown, texto de documento, mensagem/diff de commit, headers encaminhados, payload
de webhook antes do HMAC e resposta de qualquer serviço externo. O backend e o banco
com service role também podem conter bugs; por isso autorização central, constraints,
RLS e idempotência são camadas complementares.

Abusos mínimos a testar: usuário autenticado tentando IDOR, cookie roubado/CSRF,
signup automatizado, webhook forjado/repetido, arquivo comprimido malicioso, prompt
injection, segredo em diff, falsificação de autor, retry que duplica custo/documento,
mais de uma réplica executando o mesmo job e cliente forjando `X-Forwarded-For`.

## 4. Objetivos e definição de pronto

Ao final:

1. toda leitura/mutação é autorizada por pessoa, ação e escopo real;
2. recursos filhos não permitem IDOR por UUID;
3. signup público é substituído por convite de uso único;
4. mudança de cargo, vínculo, senha ou status invalida a sessão em até 30 segundos;
5. toda mutação originada do browser possui defesa CSRF compatível com
   Vercel ↔ Railway;
6. request/upload não consegue contornar limites omitindo `Content-Length`;
7. toda chamada Gemini passa por um único gateway, recebe conteúdo redigido e gera
   telemetria segura de custo/latência;
8. autoria não verificada de commit não é tratada como identidade confirmada;
9. webhook persiste trabalho idempotente e responde rapidamente; worker executa o
   trabalho com lease/retry/dead-letter;
10. scheduler, notificações e jobs são seguros com mais de uma réplica;
11. consultas críticas possuem quantidade de queries e volume de resposta limitados;
12. o fluxo funcional atual de Dados e Dev permanece íntegro.

## 5. Restrições de compatibilidade

- Não executar migration automaticamente no startup, testes ou deploy.
- Não usar `DROP`, truncar dados, renomear coluna em uso ou remover constraint
  legada nesta spec.
- Não apagar `projects.gemini_api_key`, `projects.github_token` ou
  `projects.github_repo`; apenas parar de usá-las depois do rollout.
- Toda coluna nova começa nullable ou com default compatível.
- Backend antigo + schema novo e backend novo em modo legado + frontend atual devem
  continuar operando durante o rollout.
- Defaults das flags devem preservar o comportamento atual até o gate de ativação.
- Não reintroduzir `GITHUB_INTEGRATION_ENABLED` nem
  `GITHUB_INTEGRATION_SUBAREAS`; GitHub permanece disponível em Dados e Dev.
- Não alterar identidade visual, rotas por subárea ou UX do seletor de repositórios
  fora do necessário para paginação/estado de jobs.
- Não realizar chamadas pagas duplicadas em modo shadow/audit.
- Não registrar request body, cookie, token, chave, prompt, resposta integral, diff
  bruto, documento completo ou e-mail em claro em logs técnicos.
- Reutilizar dependências existentes e stdlib sempre que suficiente. Qualquer
  dependência nova deve resolver requisito concreto, ser auditada e não provocar
  atualização ampla do `requirements.txt`/lockfile.

## 6. Preflight técnico e gate do schema-base

Antes do código, inventariar handlers, tabelas, flags e usos diretos de Gemini,
GitHub, Supabase, uploads, scheduler e `BackgroundTasks`. Salvar o inventário em
documentação ou testes; não criar um relatório com segredos.

A implementação não depende de migrations anteriores como documentos, mas depende
do **schema funcional que o próprio código atual usa**. Confirmar por leitura que o
banco do ambiente-alvo contém, no mínimo:

- `projects.subarea`;
- `app_settings`;
- `project_repositories`, `github_webhook_deliveries` e
  `github_connection_sessions`;
- colunas `ingestions.source_repository_id`, `source_commit_sha`, `source_branch` e
  `source_url`;
- tabelas funcionais presentes no `supabase_schema.sql`, incluindo `pessoa`,
  `operacionais`, `projects`, `sprints`, `tasks`, `ingestions`, `generated_docs`,
  `funcionalidades`, `pontuacao_operacional_sprint` e `commit_qualidade`.

Fornecer ao usuário uma query de diagnóstico somente-leitura, semelhante a:

```sql
select
  to_regclass('public.projects')                    as projects,
  to_regclass('public.app_settings')                as app_settings,
  to_regclass('public.project_repositories')        as project_repositories,
  to_regclass('public.github_webhook_deliveries')   as github_webhook_deliveries;

select table_name, column_name
from information_schema.columns
where table_schema = 'public'
  and (
    (table_name = 'projects' and column_name = 'subarea') or
    (table_name = 'ingestions' and column_name in (
      'source_repository_id', 'source_commit_sha', 'source_branch', 'source_url'
    ))
  )
order by table_name, column_name;
```

Se um objeto funcional obrigatório estiver ausente, parar o gate de banco e informar
exatamente o que falta. Não “compensar” criando migration automática. A parte do
código que não depende do banco real ainda pode ser preparada e testada com mocks.
Os índices de performance já documentados no schema são recomendados, mas a ausência
deles não bloqueia a Migration v7.

## 7. Decisões de arquitetura obrigatórias

### 7.1 Autorização centralizada

Criar `services/authorization.py` (e helpers estritamente necessários) com uma API
pequena para:

- autorizar ação global;
- autorizar subárea;
- autorizar projeto;
- resolver recurso filho para `project_id` e autorizar;
- filtrar o conjunto de projetos visíveis antes de listar/agregar;
- diferenciar `read`, `create`, `update`, `delete`, `manage_people`,
  `manage_integrations`, `manage_settings` e `trigger_job`.

Não permitir que request informe nome de tabela ou expressão de autorização.
Retornar `404` quando confirmar a existência do recurso vazaria informação e `403`
quando o recurso já é conhecido, mas a ação é proibida.

### 7.2 Identidade e escopo normalizados

- `pessoa.cargo` continua sendo o cargo global.
- `pessoa_subareas` representa liderança por subárea.
- `pessoa_projetos` representa vínculos de gerente/operacional com projetos.
- `operacionais.pessoa_id` liga a entidade de execução do projeto à identidade de
  login sem destruir o histórico de operacionais.
- E-mail é útil no backfill, nunca a autorização definitiva após enforcement.

### 7.3 Fila Postgres, sem Redis obrigatório

Usar Postgres/Supabase para fila durável porque já faz parte da arquitetura. O
worker roda como serviço separado; a API apenas persiste trabalho. Não introduzir
Redis, Kafka ou um novo provedor sem evidência e aprovação fora desta spec.

### 7.4 Gateway único de Gemini

Todo `ChatGoogleGenerativeAI` funcional deve nascer no mesmo gateway/factory. O
gateway usa exclusivamente `services/gemini_key.py`, aplica política por operação e
retorna tanto o resultado validado quanto metadados de uso. Não duplicar lógica de
chave, retry, preço ou telemetria.

### 7.5 RLS como defesa adicional

Como o browser não consulta Supabase, habilitar RLS e negar `anon`/
`authenticated` nas tabelas de negócio é defesa em profundidade. Isso não substitui
autorização no FastAPI; service role continuará acessando as tabelas.

## 8. Escopo de implementação

### 8.1 Migration v7 — aditiva, comentada e não executada pelo agente

Adicionar ao final de `docudata-backend/supabase_schema.sql` uma seção claramente
identificada como **Migration v7 — Spec 10**. Todo SQL novo deve permanecer
comentado e ser idempotente. Separar em blocos aplicáveis/rollback lógico, explicando
ordem, locks e validação.

O `supabase_schema.sql` é o ledger humano e a referência reproduzível do schema; ele
não é um mecanismo automático de migration. Os comentários deixam explícito o que
deve ser copiado/aplicado manualmente e impedem que uma leitura casual do arquivo
seja confundida com autorização para alterar o banco.

#### 8.1.1 Sessão e vínculos

- em `pessoa`: `ativo boolean NOT NULL DEFAULT true` e
  `session_version integer NOT NULL DEFAULT 1` com check positivo;
- `pessoa_subareas`: UUID, `pessoa_id` FK, `subarea` com check `dados|dev`,
  `created_at`, `created_by`, unique `(pessoa_id, subarea)` e índices de consulta;
- `pessoa_projetos`: UUID, `pessoa_id` FK, `project_id` FK, `papel` com check
  `gerente|operacional`, `ativo`, auditoria, unique
  `(pessoa_id, project_id, papel)` e índices por pessoa/projeto ativo;
- `operacionais.pessoa_id` nullable, FK `ON DELETE SET NULL`, com índice;
- não criar unique parcial em `operacionais(project_id,pessoa_id)` antes do relatório
  confirmar ausência de duplicidades. Documentar o índice unique como segunda etapa
  manual após saneamento.

#### 8.1.2 Convites normalizados

- `convites_acesso`: UUID, `token_hash` SHA-256 unique, `email_normalizado`, cargo,
  `expires_at`, `consumed_at`, `revoked_at`, `created_by`, `created_at`;
- `convite_subareas`: FK do convite, subárea validada, unique do par;
- `convite_projetos`: FK do convite, FK do projeto, papel validado, unique do trio;
- índices para token, expiração e convites pendentes;
- token puro jamais é persistido.

#### 8.1.3 Auditoria de decisão

Criar `authorization_decision_audit` ou equivalente com request ID, pessoa ID,
ação, tipo/ID do recurso, decisão legada, decisão nova, motivo enumerado e timestamp.
Não armazenar conteúdo do recurso, e-mail, token ou detalhe sensível. Definir retenção
e job de limpeza.

#### 8.1.4 Uso de IA

Criar `ai_usage` com:

- `project_id` nullable para operações realmente globais;
- `subarea` derivada do projeto, nunca aceita livremente do cliente;
- `pessoa_id` quando aplicável;
- operação catalogada, modelo, tokens de entrada/saída/cache, custo estimado,
  duração, sucesso, código de erro sanitizado, quantidade de redactions e timestamp;
- índices por projeto/período, subárea/período e operação/período;
- nenhum prompt, output integral, chave ou conteúdo de documento/diff.

#### 8.1.5 Identidade de commit

- `pessoa.github_user_id bigint` nullable, com unique parcial para IDs não nulos;
- em `ingestions`, campos normalizados para GitHub user ID do autor, committer,
  pusher e merger quando existirem, além de flags de identidade/assinatura
  verificadas;
- em `commit_qualidade`, flag explícita de identidade verificada;
- o vínculo confiável passa por `ingestions.github_user_id` →
  `pessoa.github_user_id` → `operacionais.pessoa_id`; login/e-mail legados continuam
  apenas como pista de backfill;
- preservar campos atuais por compatibilidade e não recalcular histórico.

#### 8.1.6 Jobs e idempotência

Criar `background_jobs` com:

- UUID, tipo enumerado, payload JSON mínimo, `project_id` nullable e chave de
  idempotência unique;
- status `pending|processing|retry|succeeded|dead_letter|cancelled`;
- `attempts`, `max_attempts`, `available_at`, `locked_at`, `locked_by`,
  `lease_expires_at`, erro sanitizado, timestamps e metadados mínimos do resultado;
- índice parcial de claim por status/disponibilidade e índices de observabilidade;
- sem diff bruto, chave, token, documento completo ou prompt no payload;
- política de retenção para jobs finalizados.

Criar funções/RPCs transacionais para claim, renovação de lease, sucesso e falha. As
funções `SECURITY DEFINER` devem ter `search_path` fixo, validação de entradas,
execução revogada de `public`/`anon`/`authenticated` e grant apenas à service role.

Adicionar idempotência por constraint às notificações e execuções recorrentes. Se a
tabela atualmente usada por `notification_checker` não estiver descrita no schema,
documentá-la primeiro em vez de assumir sua forma.

#### 8.1.7 Rate limit distribuído

Criar `rate_limit_buckets` com identificador HMAC, tipo de bucket, início/fim da
janela, contador e timestamp de expiração, unique por identificador/tipo/janela.
Criar RPC atômica de incremento e limpeza paginada. IP/e-mail em claro não devem ser
persistidos; o identificador é HMAC com segredo exclusivo do backend.

#### 8.1.8 Credenciais legadas de serviço

Criar `service_credentials` para transição do hook antigo:

- segredo armazenado apenas por hash;
- escopo obrigatório por projeto e, para commit, por repositório;
- label, status, expiração, último uso e timestamps;
- unique de hash e índices de lookup;
- credencial pura retornada uma única vez.

Não migrar o valor global atual para essa tabela e não expor hashes ao frontend.
Os scripts instalados dentro de repositórios de squads continuam usando apenas
stdlib/`urllib`; não adicionar dependência Python externa a esses hooks.

#### 8.1.9 Busca e contexto escalável

- `ingestion_technologies`: tecnologia normalizada/display, ingestion, projeto,
  sprint, estado de remoção e índices; popular nas escritas novas;
- índice adequado para busca normalizada. Se `pg_trgm` for usado, documentar criação
  da extensão, impacto e alternativa sem extensão;
- `project_context_summaries`: projeto, escopo/tipo, watermark da última fonte,
  resumo seguro, IDs/fontes cobertos, versão e timestamps;
- não gerar backfill de resumos automaticamente ao aplicar SQL.

#### 8.1.10 RLS deny-by-default

Escrever bloco separado para:

- habilitar RLS nas tabelas centrais e novas;
- revogar acesso direto de `anon` e `authenticated`;
- preservar service role;
- listar query de verificação das tabelas sem RLS;
- testar em staging antes de aplicar em produção.

Não clicar automaticamente em “Run and enable RLS” no editor. A pessoa deve revisar
e executar o SQL explícito da spec. Se o produto passar a consultar Supabase direto
do browser no futuro, novas policies exigirão outra decisão de arquitetura.

#### 8.1.11 Estado idempotente de exportação Google Docs

Adicionar em `generated_docs` campos nullable para `gdocs_document_id`, `gdocs_url`,
`gdocs_export_status`, `gdocs_exported_at` e código de último erro sanitizado, além
de índice/unique adequado para impedir duas exportações lógicas do mesmo documento.
Nunca persistir refresh/access token. O estado intermediário deve permitir retomar
uma cópia já criada no Drive depois de falha parcial, sem criar documentos órfãos a
cada retry.

### 8.2 Backfill manual e auditável

Criar script em `docudata-backend/scripts/` com modo dry-run padrão e `--apply`
explícito. O script deve:

1. normalizar e-mail com `lower(trim())` apenas para comparação;
2. ligar pessoa ↔ operacional somente quando houver correspondência inequívoca;
3. criar vínculos de gerente a partir de `projects.gerente_email` apenas quando
   inequívocos;
4. exigir escolha humana para subáreas de líderes;
5. não criar vínculos artificiais para owner;
6. detectar pessoas/e-mails duplicados, órfãos, cargos incompatíveis e projetos sem
   responsável;
7. ser idempotente por upsert/unique;
8. emitir contagens e IDs, mascarando e-mails no output compartilhável;
9. não alterar cargo, senha, score ou histórico;
10. nunca ser executado automaticamente pelo agente em banco real.

Depois do backfill, oferecer queries somente-leitura para confirmar contagens por
subárea/cargo e localizar ambiguidades restantes.

### 8.3 Matriz de autorização

Implementar a seguinte regra mínima:

| Ação | Owner | Líder atribuído à subárea | Gerente atribuído ao projeto | Operacional atribuído ao projeto |
|---|---:|---:|---:|---:|
| Listar/ler projetos e recursos | todos | somente sua subárea | somente seus projetos | somente seus projetos |
| Criar projeto | sim | em sua subárea | não | não |
| Editar dados gerais/contrato | sim | sua subárea | seu projeto, conforme fluxo atual | não |
| Excluir projeto | sim | sua subárea | não | não |
| Trocar subárea | sim | apenas se lidera origem e destino | não | não |
| Gerenciar sprint/escopo | sim | sua subárea | seu projeto | apenas ações hoje permitidas |
| Gerenciar pessoas/vínculos | sim | dentro de sua subárea | somente equipe do próprio projeto quando já permitido | não |
| Configurar chave Gemini global | sim | não | não | não |
| Conectar/desconectar GitHub | sim | sua subárea | seu projeto | não |
| Ver custos globais | sim | somente sua subárea | somente seus projetos | não, salvo custo próprio já previsto |
| Ver performance | global | somente sua subárea | somente seus projetos/equipe | própria, se o produto já exibir |
| Disparar job administrativo | sim | limitado à própria subárea | não | não |

Preservar as ações operacionais atuais de task/solicitação. Ocultar botão no frontend
é apenas UX; o backend continua sendo a autoridade.

Inventariar e testar todos os routers atuais, incluindo:

- projects, sprints e sprint_funcionalidades;
- tasks, transições, reaberturas, travamento e solicitações;
- ingest, ingestions, generate, generated_docs, enrich e composer;
- funcionalidades, aceite, boletins e exportação Google Docs;
- painel, métricas, pontuação, avaliações e performance;
- operacionais, pessoas, convite e settings;
- GitHub App, webhook e hooks legados;
- search, metodologia e qualquer agregado entre projetos;
- endpoints manuais de notificação/travamento.

Para todo recurso recebido por ID, consultar primeiro somente o necessário para obter
o `project_id`, autorizar e então ler/mutar. Cobrir IDs encadeados inconsistentes,
como task de um projeto com sprint/funcionalidade de outro.

### 8.4 Rollout da autorização em três modos

Usar uma única variável:

```env
AUTHORIZATION_MODE=legacy
# Valores: legacy | audit | enforce
```

- `legacy`: comportamento atual, mas código novo e logs seguros já ativos;
- `audit`: calcula decisão nova, mantém a antiga e persiste apenas divergência
  sanitizada, sem negar acesso;
- `enforce`: usa apenas a decisão nova.

O modo audit não pode duplicar query cara sem limite e nunca pode duplicar chamada
externa/Gemini. Antes de `enforce`, observar uma janela representativa em staging e
produção, resolver todas as divergências legítimas e guardar contagem por rota/ação.

### 8.5 Cadastro por convite

Adicionar:

- `POST /admin/invites`: owner, ou líder estritamente limitado à própria subárea;
- `POST /auth/invites/status`: recebe token no corpo e devolve resposta mínima e
  não enumerável;
- `POST /auth/invites/accept`: recebe token no corpo, valida token/e-mail/senha e
  consome em
  transação única com criação de pessoa e vínculos.

Regras:

- token com pelo menos 256 bits, armazenado apenas como SHA-256;
- validade curta configurável e uso único atômico;
- convite pode ser revogado;
- e-mail enviado por Resend ou link entregue uma vez ao administrador;
- link do frontend deve preferir fragmento (`#token=...`) para o token não aparecer
  em access log/referer; o frontend remove o fragmento depois de carregá-lo;
- mensagens públicas não distinguem e-mail já cadastrado/inexistente;
- senha aceita passphrase longa e possui mínimo consistente no frontend/backend;
- rate limit compartilhado entre réplicas para login e aceite de convite;
- os endpoints antigos ficam disponíveis apenas enquanto
  `INVITE_ONLY_SIGNUP=false`; depois retornam `404` ou `410` de forma uniforme;
- a tela `/cadastro` migra para token de convite e deixa de baixar pessoas sem conta.

```env
INVITE_ONLY_SIGNUP=false
INVITE_TTL_HOURS=24
```

### 8.6 Sessão revogável

O JWT novo deve conter `iss`, `aud`, `jti`, `sub`, `sv`, `iat`, `nbf` e `exp`.
Cargo/e-mail do token podem existir para exibição compatível, mas nunca substituem a
leitura da pessoa ativa e dos vínculos.

- validar força e presença de `JWT_SECRET` no startup;
- exigir no mínimo 32 bytes de entropia para novos `JWT_SECRET`/`CSRF_SECRET`; não
  imprimir o valor ao reportar configuração inválida;
- aceitar temporariamente cookie legado durante o rollout e emitir cookie novo no
  próximo login;
- carregar pessoa/status/session_version do banco com cache máximo de 30 segundos;
- invalidar cache local no mesmo processo após alteração administrativa;
- incrementar `session_version` ao trocar senha/cargo/status e nas mudanças de
  escopo que precisem revogar a sessão;
- usuário inativo ou versão divergente recebe `401`;
- cookie `HttpOnly`, `Secure` em produção, `Path=/` e tempo explícito;
- manter compatibilidade local sem `Secure` apenas em ambiente de desenvolvimento;
- usar prefixo `__Host-` somente depois de comprovar compatibilidade dos domínios e
  sem quebrar sessões existentes.

```env
SESSION_CACHE_TTL_SECONDS=30
SESSION_ISSUER=docudata-backend
SESSION_AUDIENCE=docudata-frontend
```

### 8.7 Proteção CSRF compatível com Vercel e Railway

Como cookie `SameSite=None` viaja cross-site, CORS não basta. Implementar:

1. `GET /auth/csrf` autenticado devolve token assinado e vinculado ao `jti` da
   sessão, sem expor `JWT_SECRET`;
2. `apiFetch` guarda o token apenas em memória e envia `X-CSRF-Token` em
   POST/PUT/PATCH/DELETE do browser;
3. backend valida token, sessão, método e `Origin` permitido;
4. `Sec-Fetch-Site` pode reforçar a decisão, mas não deve bloquear legitimamente a
   relação cross-site Vercel ↔ Railway;
5. login e aceite de convite não exigem sessão/CSRF, mas validam origem e rate limit;
6. webhook GitHub continua protegido por HMAC e fica isento;
7. hooks servidor-a-servidor ficam isentos somente com credencial escopada válida;
8. token gira com a sessão e nunca é persistido em localStorage.

Rollout:

```env
CSRF_ENFORCEMENT=false
CSRF_SECRET=
```

Gerar `CSRF_SECRET` com `openssl rand -hex 32`. Publicar primeiro backend capaz de
aceitar/emitir token, depois frontend enviando header, observar falhas e só então
trocar para `true`.

### 8.8 Rate limit distribuído e proxy confiável

- substituir o armazenamento em memória por contador atômico compartilhado no
  Postgres/Supabase, com janela e expiração; não criar uma linha por request para
  sempre;
- derivar a chave do bucket com HMAC e `RATE_LIMIT_HASH_SECRET`, sem armazenar IP ou
  e-mail em claro;
- limites de autenticação, convite, geração/Gemini, uploads e ações administrativas
  devem ter buckets separados;
- endpoints somente-leitura comuns continuam sem rate limit pago/agressivo, salvo
  proteção de abuso claramente documentada;
- retornar `429` com `Retry-After`;
- não confiar cegamente no primeiro `X-Forwarded-For`;
- só interpretar forwarded headers quando `request.client.host` pertence a proxy
  explicitamente confiável;
- percorrer a cadeia da direita para a esquerda, removendo hops confiáveis;
- não inventar CIDRs do Railway. O operador deve obter a topologia/ranges oficiais
  do ambiente. Se isso não puder ser comprovado, usar o IP de conexão e aceitar um
  limite mais conservador/coarse em vez de confiar em header forjável;
- documentar como Uvicorn/Railway já tratam proxy headers para evitar dupla
  interpretação.

```env
TRUSTED_PROXY_CIDRS=
RATE_LIMIT_HASH_SECRET=
```

### 8.9 Limite real de request e upload seguro

Implementar contagem no fluxo ASGI para todo corpo de request, não apenas no header:

- `Content-Length` ausente, inválido, negativo ou incompatível não contorna o teto;
- corpo acima do limite recebe `413` assim que o teto é ultrapassado;
- multipart é processado em streaming/spooling sem duplicar o arquivo inteiro;
- filename do usuário nunca vira caminho local;
- tipos permitidos continuam PDF, DOCX, PNG/JPEG e TXT usados pela aplicação;
- extensão, MIME declarado e assinatura/magic bytes devem ser compatíveis;
- PDF: limite de páginas, texto extraído, pixels e timeout do Poppler;
- DOCX: ZIP válido, estrutura esperada, número/tamanho de entradas e soma
  descomprimida limitados; bloquear zip bomb e path traversal;
- imagem: manter `MAX_IMAGE_PIXELS`, validar com Pillow e normalizar formato;
- TXT: tamanho e encoding controlados;
- parsing bloqueante/CPU-bound roda em threadpool/processo com capacity limiter e
  timeout; não bloquear event loop;
- liberar temporários em sucesso, erro e cancelamento.

```env
MAX_UPLOAD_MB=20
MAX_PDF_PAGES=200
MAX_EXTRACTED_TEXT_CHARS=1000000
MAX_DOCX_UNCOMPRESSED_MB=50
FILE_PARSE_CONCURRENCY=2
PDF_POPPLER_TIMEOUT_SECONDS=30
MAX_IMAGE_PIXELS=40000000
```

Os valores são defaults conservadores e devem ser medidos em staging antes de
alterados. Antivírus/ClamAV pode ser avaliado, mas não é requisito desta spec.

### 8.10 Gateway Gemini, privacidade e custo

Buscar novamente por `ChatGoogleGenerativeAI` ao início e ao final. Migrar todo uso
funcional em `graphs/`, `routers/` e `services/` para o gateway. Imports apenas em
testes/factory são aceitáveis.

O gateway deve:

- ler somente a chave global por `services/gemini_key.py`;
- refletir substituição da chave sem restart ou invalidar cache explicitamente;
- possuir catálogo de operações com modelo, timeout, retries seguros, limite de
  saída e schema esperado;
- aplicar semáforo de concorrência por processo e limite compartilhado por
  projeto/subárea para evitar explosões de custo;
- retornar resultado validado + usage;
- registrar uma linha `ai_usage` para sucesso e falha;
- centralizar preço por modelo com versão/data e marcar estimativa quando o provedor
  não devolver usage;
- converter falha externa em erro consistente e amigável com request ID;
- permitir um único mock para todos os testes.

Antes de qualquer chamada:

- excluir por default `.env*`, PEM, certificados, chaves, arquivos binários/gerados
  e caminhos sensíveis de diffs;
- detectar/redigir tokens, senhas e chaves no texto/documento/diff;
- sempre redigir o valor detectado, inclusive em modo de observação; observar
  significa registrar **apenas a contagem**, nunca enviar/logar o segredo;
- delimitar conteúdo não confiável e instruir o modelo a não obedecer comandos
  encontrados dentro dele;
- limitar caracteres/tokens e validar output por schema/enums/tamanho.

Custos:

- toda chamada é atribuída ao projeto e à subárea derivados no servidor;
- operação sem projeto fica explicitamente global;
- oferecer leitura owner global, líder por subárea e gerente por seus projetos;
- orçamento nesta spec é **observe/alert**, sem hard cap que interrompa fluxo;
- não fazer chamada shadow duplicada, pois gera custo real.

```env
GEMINI_MAX_CONCURRENCY=2
GEMINI_BUDGET_MODE=observe
```

### 8.11 Integridade de commits

- priorizar o `github_user_id` imutável resolvido pela API/evento;
- distinguir autor, committer, pusher e merger;
- persistir status de assinatura verificada quando disponível;
- login/e-mail Git só auxiliam match; e-mail declarado no commit não comprova
  identidade;
- se houver apenas nome/e-mail, marcar `autor_nao_verificado` e não atribuir a nota
  como score pessoal verificado;
- permitir associação manual auditada por gerente/líder autorizado sem reescrever
  metadados originais;
- nota Gemini é sinal auxiliar e nunca decisão automática de RH;
- impedir prompt injection em mensagem/diff e testar spoofing;
- não recalcular commits históricos automaticamente.

### 8.12 Webhook GitHub e worker durável

O endpoint `/webhooks/github` deve:

1. limitar corpo por bytes antes de carregar tudo;
2. validar headers esperados e HMAC sobre bytes crus antes de parsear JSON/banco;
3. persistir delivery + job idempotente em operação transacional;
4. ignorar repositório autorizado no App, porém não vinculado/ativo em projeto;
5. derivar projeto/subárea exclusivamente de `project_repositories`;
6. responder `202` depois da persistência, sem chamar GitHub nem Gemini na request.

O worker deve:

- fazer claim atômico com `FOR UPDATE SKIP LOCKED` ou RPC equivalente;
- renovar e recuperar lease expirado;
- usar retry exponencial com jitter e limite;
- separar falha temporária, permanente e dead-letter;
- processar pushes grandes em lotes limitados;
- preservar unique `(source_repository_id, source_commit_sha)`;
- cachear installation token somente até pouco antes da expiração, nunca no browser;
- respeitar rate limit do GitHub e `Retry-After`;
- tornar publicação de status idempotente;
- registrar métricas de fila/duração/falha/custo sem payload sensível;
- permitir retry administrativo auditado.

```env
GITHUB_WEBHOOK_MAX_BYTES=2097152
DURABLE_JOBS_MODE=sync
# Valores: sync | queue
JOB_LEASE_SECONDS=120
JOB_MAX_ATTEMPTS=5
JOB_POLL_INTERVAL_SECONDS=2
```

`sync` preserva temporariamente o comportamento atual. `queue` só pode ser ativado
depois de Migration v7 aplicada e worker saudável. Não criar modo que processe o
mesmo commit sincronamente e em fila, pois isso dobra custo mesmo com deduplicação
posterior.

O Railway precisa de um segundo serviço/processo com comando explícito, por exemplo
`python -m workers.main`; o web continua usando o Procfile atual. Documentar health,
restart policy, escala inicial de um worker e como pausar sem perder jobs.

### 8.13 Jobs recorrentes e `BackgroundTasks`

- mover notificações e travamento automático para `background_jobs` disparados por
  Railway Cron ou scheduler com advisory lock/lease único;
- impedir execução lógica dupla entre cron, endpoint manual e réplicas;
- criar chave de idempotência por tipo/janela/projeto quando aplicável;
- registrar início, fim, duração e resultado;
- endpoints manuais apenas enfileiram e exigem owner/líder no próprio escopo;
- email, parsing/Gemini e aceite que não podem ser perdidos deixam de depender de
  `BackgroundTasks`;
- `AsyncIOScheduler` não inicia em toda réplica depois de `DURABLE_JOBS_MODE=queue`;
- adicionar `/ready` que valida Supabase e infraestrutura essencial sem chamar
  Gemini, Drive, Resend ou GitHub.

### 8.14 Migrar aceite legado para GitHub App

O fluxo de aceite em `routers/funcionalidades.py` deve parar de ler
`projects.github_token` e `projects.github_repo`.

- selecionar explicitamente um vínculo ativo em `project_repositories`;
- quando houver vários repositórios, exigir vínculo da funcionalidade ou escolha
  explícita; nunca escolher silenciosamente o primeiro;
- usar installation token do GitHub App;
- usar a branch/tag da entrega como `ref` do `workflow_dispatch` e enviar o SHA da
  entrega como input explícito; o workflow valida que o SHA pertence ao repositório
  esperado e faz checkout desse SHA. Nunca usar `git rev-parse HEAD` do backend;
- adotar `workflow_dispatch` (recomendado) com permissão **Actions: write**, mantendo
  Contents somente leitura, após confirmar o contrato do workflow alvo;
- a alteração de permissão do GitHub App e a aprovação da organização são ações
  humanas e precisam ocorrer antes de ativar o fluxo novo;
- manter fallback legado somente durante rollout e nunca mostrar PAT;
- depois da validação, revogar/rotacionar PATs e limpar os valores, sem remover as
  colunas nesta migration.

```env
LEGACY_ACCEPTANCE_GITHUB_ENABLED=true
LEGACY_HOOKS_ENABLED=true
```

O hook legado deve migrar de `DOCUDATA_APP_SECRET` global para credencial individual
de projeto/repositório. Depois que todos os consumidores conhecidos estiverem no
GitHub App ou na credencial escopada, desligar `LEGACY_HOOKS_ENABLED` e rotacionar o
segredo global. Vazamento de uma credencial de squad não pode autorizar ingestão em
outro projeto.

### 8.15 Banco, I/O e consistência

- reutilizar o cliente Supabase por processo com inicialização segura e sem estado
  mutável de request;
- escolher uma estratégia consistente para SDK bloqueante: rota sync em threadpool
  ou adaptador explícito; não bloquear event loop com Supabase/urllib/Google;
- usar projeções mínimas, limites máximos e timeouts;
- transformar operações multi-tabela críticas em RPC transacional: aceite de
  convite, reorder batch, orçamento/baseline, fechamento de avaliação, exclusão de
  sprint e persistência delivery+job;
- preferir unique/upsert/lock a `check-then-write` sujeito a corrida;
- filtrar subárea/projetos autorizados dentro da consulta sempre que possível;
- validar índices com `EXPLAIN (ANALYZE, BUFFERS)` apenas em staging/clone com volume
  representativo, nunca sob carga de produção sem janela.

### 8.16 Paginação, busca e ranking

- criar contratos paginados cursor-based para ingestões, documentos, tasks,
  commits, pessoas e demais listas que crescem;
- definir `limit` padrão e máximo no servidor;
- não quebrar respostas em array usadas pelo frontend: criar contrato v2 ou período
  de compatibilidade, migrar frontend e só então descontinuar o antigo;
- paginação deve ter ordenação determinística com desempate por ID;
- busca de tecnologia consulta `ingestion_technologies`, não baixa todo
  `extracted_content` para Python;
- novos registros alimentam o índice na mesma unidade lógica da ingestão;
- backfill de tecnologia é manual, paginado, idempotente e não chama Gemini;
- ranking/performance busca dados em lotes com quantidade de queries constante em
  relação ao número de pessoas;
- agrupar identidade final por `pessoa_id`, mantendo operacional histórico;
- performance sempre filtra subárea/projetos autorizados;
- preservar o popup rápido do GitHub: 30 recentes inicialmente, busca remota
  paginada para antigos, cache curto por instalação e cancelamento de busca anterior.

### 8.17 Contexto de geração limitado e rastreável

- definir orçamento de caracteres/tokens por operação/tipo de documento;
- priorizar ingestão âncora, sprint solicitada, informações recentes, documentos
  estruturados e commits relevantes;
- commits continuam sendo insumo junto com ingestões manuais e demais abas;
- não concatenar indefinidamente todas as ingestões do projeto;
- para documentos project-wide, resumir lotes antigos de forma incremental ou
  map-reduce, persistindo watermark e IDs das fontes;
- nunca resumir em background silenciosamente durante a migration;
- resposta/documento registra quais fontes foram usadas, sem expor conteúdo
  sensível;
- projetos pequenos devem manter qualidade comparável aos snapshots atuais;
- cancelamento/retry não pode gerar documento duplicado nem cobrança invisível;
- medir cobertura, tokens, custo e latência antes/depois.

### 8.18 Frontend

- `app/lib/api.ts` continua concentrando HTTP;
- `apiFetch` envia request ID e CSRF em mutações;
- tratar distintamente `401`, `403`, `404`, `409`, `413`, `422`, `429` e `503`;
- tela de cadastro usa convite e não enumera operacionais;
- botões/rotas são ocultados conforme capacidade retornada, sem confiar nisso como
  segurança;
- subárea da URL orienta navegação, mas o backend valida o escopo real;
- listas novas usam carga incremental, preservam scroll e cancelam requests ao
  trocar rota/filtro;
- mostrar estado `queued|processing|failed|done` em operações assíncronas sem
  bloquear navegação;
- preservar identidade visual, responsividade, barra superior, seletor de
  repositórios e aba de commits retraível;
- nunca criar variável `NEXT_PUBLIC_*` com segredo;
- CSP só muda de report-only para bloqueante após confirmar zero violação legítima.

### 8.19 Observabilidade e retenção

- manter `X-Request-ID` de ponta a ponta e associá-lo a job/delivery sem registrar
  payload;
- métricas mínimas: latência/status por rota, tamanho/recusa de upload, rate limit,
  autorização audit/enforce, fila por status/idade, GitHub rate limit, Gemini
  uso/custo/falha/redaction e scheduler;
- alertar para dead-letter, lease vencido recorrente, custo anormal, falha de auth e
  webhook inválido em volume;
- definir retenção e limpeza idempotente para audit, deliveries, jobs e usage;
- logs estruturados devem usar IDs e códigos enumerados, não PII/conteúdo;
- documentar backup, PITR e restauração; fazer teste de restore somente em ambiente
  isolado autorizado.

### 8.20 Fronteira HTTP, conteúdo renderizado e serviços externos

- manter CORS com origens exatas, sem wildcard, e reduzir métodos/headers aos
  realmente usados (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`,
  `Content-Type`, `X-CSRF-Token`, `X-Request-ID`);
- expor ao browser apenas headers operacionais necessários, como `X-Request-ID` e
  `Retry-After`;
- validar `FRONTEND_URL`/`ALLOWED_ORIGINS` no startup e rejeitar valor malformado;
- manter docs/OpenAPI desligados em produção e `/health` sem dependência externa;
- preservar headers de segurança existentes e promover CSP para bloqueante somente
  após relatório sem violações legítimas;
- continuar renderizando Markdown sem HTML bruto; não habilitar `rehypeRaw` ou
  equivalente. Links externos devem usar `rel="noopener noreferrer"`;
- qualquer endpoint de status/configuração devolve apenas presença, hint não
  sensível e timestamp, nunca segredo.

Para Google Drive/Docs e Resend:

- derivar refresh token, pasta e template da subárea do projeto carregada no
  servidor; não aceitar subárea/pasta/template arbitrários do cliente;
- mover exportações e e-mails que não podem ser perdidos para jobs duráveis;
- exportação é idempotente por `generated_doc`: sucesso repetido devolve o mesmo
  documento, e retry de falha parcial reutiliza `gdocs_document_id` já persistido;
- forçar nova cópia exige ação explícita e autorizada, nunca retry automático;
- configurar timeout e retry apenas para falhas transitórias; não repetir operação
  não idempotente sem chave/estado persistido;
- construir clients Google sem discovery cache legado e não bloquear o event loop;
- traduzir erro externo em código/mensagem amigável + request ID, mantendo detalhes
  sanitizados apenas nos logs;
- deduplicar e-mail por tipo/projeto/sprint/janela com constraint, não por
  `check-then-insert`;
- testar que projeto Dev nunca exporta para pasta de Dados e vice-versa.

### 8.21 Mapa mínimo de arquivos/componentes esperados

O nome final pode acompanhar as convenções do repositório, mas a responsabilidade
deve ficar clara:

| Área | Arquivo/componente esperado |
|---|---|
| Autorização | `services/authorization.py`, dependências FastAPI e matriz em testes |
| Sessão/convite/CSRF | `services/auth.py`, `routers/auth.py`, módulo CSRF e schemas |
| Limite/rate limit | `core/` para middleware/identidade do cliente e service/RPC de bucket |
| Gemini | gateway/factory único em `services/`, catálogo de operações e testes |
| Jobs | service/repositório de jobs, `workers/main.py` e handlers por tipo |
| GitHub | `routers/github_integration.py`, `services/github_app.py`, commit extraction e aceite |
| Upload | middleware ASGI, `services/file_parser.py` e endpoints de upload |
| Performance/contexto | services/graphs afetados, sem lógica SQL espalhada no frontend |
| Frontend | `app/lib/api.ts`, cadastro, providers de sessão/CSRF e telas paginadas |
| Banco/operação | `supabase_schema.sql`, `scripts/`, `.env.example`, `GUIDE.md` |
| Testes | matriz de autorização, segurança, jobs, Gemini, GitHub, upload, performance e UI |

Não é obrigatório criar um arquivo por linha se já houver local adequado. Não criar
“framework interno” genérico; preferir a menor estrutura que centralize de fato as
decisões de segurança e elimine duplicação funcional.

## 9. Variáveis de ambiente

Adicionar ao `GUIDE.md` e `.env.example`, com defaults seguros:

```env
# Autorização e cadastro
AUTHORIZATION_MODE=legacy
INVITE_ONLY_SIGNUP=false
INVITE_TTL_HOURS=24
SESSION_CACHE_TTL_SECONDS=30
SESSION_ISSUER=docudata-backend
SESSION_AUDIENCE=docudata-frontend

# CSRF
CSRF_ENFORCEMENT=false
CSRF_SECRET=

# Rede e rate limit
TRUSTED_PROXY_CIDRS=
RATE_LIMIT_HASH_SECRET=

# Upload/parsing
MAX_PDF_PAGES=200
MAX_EXTRACTED_TEXT_CHARS=1000000
MAX_DOCX_UNCOMPRESSED_MB=50
FILE_PARSE_CONCURRENCY=2

# IA
GEMINI_MAX_CONCURRENCY=2
GEMINI_BUDGET_MODE=observe

# Webhook/fila
GITHUB_WEBHOOK_MAX_BYTES=2097152
DURABLE_JOBS_MODE=sync
JOB_LEASE_SECONDS=120
JOB_MAX_ATTEMPTS=5
JOB_POLL_INTERVAL_SECONDS=2

# Compatibilidade temporária
LEGACY_ACCEPTANCE_GITHUB_ENABLED=true
LEGACY_HOOKS_ENABLED=true
```

Regras:

- `JWT_SECRET`, `CSRF_SECRET`, `DOCUDATA_APP_SECRET`, `DOCUDATA_SECRETS_KEY`, chaves
  Google/GitHub/Supabase/Resend e Gemini nunca usam `NEXT_PUBLIC_`;
- `NEXT_PUBLIC_API_URL` continua sendo a única variável pública necessária para esse
  fluxo;
- validar no startup flags/enums/números e força mínima dos segredos;
- não copiar valores reais para documentação, testes, fixtures, logs ou resposta
  final;
- `CSRF_SECRET` deve ser diferente de `JWT_SECRET` e `DOCUDATA_APP_SECRET`;
- `RATE_LIMIT_HASH_SECRET` também deve ser independente e possuir ao menos 32 bytes
  aleatórios;
- remover flags temporárias somente em spec futura de limpeza, depois de comprovar
  que não há consumidores legados.

## 10. O que a pessoa deverá fazer fora do código

### 10.1 Supabase — obrigatório antes de ativar recursos novos

1. Confirmar backup/PITR ou gerar backup adequado ao plano disponível.
2. Rodar as queries de preflight somente-leitura.
3. Revisar o bloco v7 escrito no `supabase_schema.sql`.
4. Aplicar v7 primeiro em staging/clone, por blocos e na ordem documentada.
5. Rodar queries de validação e dry-run do backfill.
6. Resolver ambiguidades de identidade/escopo.
7. Aplicar o unique parcial pós-backfill somente quando o relatório permitir.
8. Testar RLS deny-by-default com anon/authenticated e service role separadamente.
9. Repetir em produção em janela planejada; guardar output sem segredos.

Se não houver staging, não usar produção como bancada. Criar um projeto Supabase de
teste ou usar fixtures locais para validar SQL antes da janela real.

### 10.2 Railway — obrigatório para enforcement completo

1. Configurar as novas envs inicialmente em modo compatível (`legacy`, `false`,
   `sync`, legados `true`).
2. Publicar backend compatível e executar smoke tests.
3. Criar serviço de worker usando a mesma revisão do backend e as mesmas credenciais
   privadas necessárias, sem expô-las ao frontend.
4. Configurar health/restart e uma réplica inicial.
5. Somente com worker saudável trocar `DURABLE_JOBS_MODE=queue`.
6. Depois do frontend compatível, ativar `CSRF_ENFORCEMENT=true`.
7. Após auditoria, trocar `AUTHORIZATION_MODE=enforce` e
   `INVITE_ONLY_SIGNUP=true`.
8. Desligar jobs recorrentes no web quando cron/worker assumir.

No estado final validado, os modos esperados são `AUTHORIZATION_MODE=enforce`,
`INVITE_ONLY_SIGNUP=true`, `CSRF_ENFORCEMENT=true` e
`DURABLE_JOBS_MODE=queue`. As flags legadas ficam `false` somente depois da migração
dos respectivos consumidores; qualquer exceção deve ter owner, prazo e risco
documentados.

### 10.3 Vercel — obrigatório antes de CSRF enforce

1. Publicar frontend que obtém/envia CSRF.
2. Confirmar `NEXT_PUBLIC_API_URL` apontando para o backend correto.
3. Confirmar URL da Vercel em `FRONTEND_URL`/`ALLOWED_ORIGINS` no Railway.
4. Testar login, convite, mutações e logout no domínio real antes do enforcement.

### 10.4 GitHub App — obrigatório apenas para retirar o PAT do aceite

1. Revisar o workflow alvo e adotar `workflow_dispatch`.
2. Solicitar **Actions: read and write** ou a permissão mínima confirmada pela API
   escolhida, sem ampliar Contents se não for necessário.
3. Obter aprovação da organização para a permissão alterada.
4. Testar em repositório não crítico e validar repo/ref/SHA.
5. Só então desativar fallback PAT e revogar os PATs conhecidos.

O GitHub App continua instalado para Dados e Dev. Não é necessário restringi-lo de
novo a uma subárea nem voltar a escolher repositórios na tela global do GitHub; o
vínculo interno por projeto continua sendo o filtro de ingestão.

## 11. Testes automatizados obrigatórios

Todos usam Supabase/GitHub/Gemini/Google/Resend mockados.

### 11.1 Autorização

- matriz parametrizada cargo × subárea × vínculo × ação × método;
- IDOR por project, sprint, task, ingestion, doc, funcionalidade, avaliação,
  operacional, solicitação e repositório;
- IDs pais/filhos de projetos diferentes;
- listagens e agregados sem vazamento entre Dados/Dev;
- owner global apenas nas ações explicitadas;
- mudança de subárea exige origem e destino;
- modo audit preserva decisão antiga e registra só divergência sanitizada;
- modo enforce aplica decisão nova;
- credencial de hook não escolhe projeto/repositório fora do próprio escopo.

### 11.2 Convite, sessão e CSRF

- convite válido, expirado, revogado, consumido e adulterado;
- duas requisições concorrentes tentando consumir o mesmo convite;
- e-mail divergente e enumeração pública impossível;
- endpoints antigos habilitados/desabilitados pela flag;
- JWT legado durante transição e JWT novo com issuer/audience/version;
- usuário inativo, senha/cargo/vínculo alterado e cache expirando em até 30 s;
- CSRF ausente, inválido, de outra sessão, expirado e válido;
- Origin permitido/negado;
- webhook HMAC e credencial de serviço isentos sem abrir isenção genérica.

### 11.3 Request/upload

- excesso com/sem `Content-Length`, chunked e header inválido/negativo;
- limite interrompe leitura e não cresce memória proporcional ao corpo excedente;
- MIME/extensão/magic incompatíveis;
- ZIP não-DOCX, zip bomb, path traversal e excesso descomprimido;
- PDF com páginas/texto demais e timeout;
- imagem válida, inválida e acima de pixels;
- cada formato válido aceito atualmente continua aceito;
- temporários removidos em erro/cancelamento.

### 11.4 Gemini e privacidade

- busca global prova que nenhum fluxo funcional instancia LLM fora do gateway;
- chave global presente, ausente, substituída e nunca exposta;
- todos os tipos de operação registram usage/custo/duração;
- atribuição correta a projeto/subárea;
- segredo em diff/documento é redigido antes de chegar ao mock;
- arquivos sensíveis são ignorados;
- prompt injection não altera instrução/schema;
- timeout/retry/concurrency sem chamada duplicada não idempotente;
- budget observe alerta, mas não interrompe o fluxo atual.

### 11.5 GitHub, autoria e jobs

- assinatura HMAC inválida é recusada antes de JSON/banco;
- payload acima do teto é recusado;
- repo não vinculado não enfileira ingestão;
- webhook persiste e responde `202` sem chamar Gemini;
- delivery/job duplicado não duplica custo/ingestão;
- lease expirado é recuperado;
- falha temporária retenta e permanente vai a dead-letter;
- push com vários commits processa todos uma vez;
- Dados e Dev usam o mesmo mecanismo com isolamento;
- e-mail/nome falsificado não ganha identidade verificada;
- autor/committer/pusher/merger são distintos;
- aceite usa installation token, repo/ref e SHA-input escolhidos/validados;
- busca final prova que o fluxo novo não lê `projects.github_token`.

### 11.6 Performance e consistência

- número de queries do ranking não cresce com número de pessoas;
- listas respeitam cursor, ordenação estável e limite máximo;
- busca de tecnologia não carrega JSON global em Python;
- operações transacionais falham por inteiro em erro intermediário;
- duas instâncias de scheduler/worker produzem uma execução lógica;
- contexto respeita orçamento e mantém referências;
- projetos pequenos preservam snapshot/qualidade;
- cliente HTTP/Supabase reutilizado e I/O bloqueante não trava event loop.

### 11.7 Frontend

- adaptador CSRF e retry controlado;
- mensagens para 401/403/404/409/413/422/429/503;
- cadastro por convite;
- paginação/cancelamento de requests;
- capacidades escondem ações sem substituir autorização;
- rotas de Dados e Dev continuam funcionais;
- seletor GitHub recente/pesquisa antiga não regride;
- aba de commits continua retraída/expansível.

### 11.8 HTTP, Google e notificações

- CORS aceita apenas origem/método/header esperado e continua funcional na Vercel;
- docs/OpenAPI ficam inacessíveis em modo de produção;
- Markdown hostil não executa HTML/script;
- exportação repetida devolve o mesmo Google Doc;
- falha depois do clone é retomada sem criar outra cópia;
- pasta/template/refresh token são derivados da subárea real do projeto;
- cliente Google tem timeout, não usa discovery cache legado e não bloqueia event
  loop;
- duas execuções concorrentes enviam uma única notificação lógica.

## 12. Validação obrigatória

Executar, corrigir e registrar:

```bash
cd docudata-backend
pytest
```

```bash
cd docudata-frontend
npm run build
```

Além disso, executar os audits já previstos pelo repositório:

```bash
cd docudata-frontend
npm audit --omit=dev --audit-level=high
```

```bash
cd docudata-backend
pip-audit -r requirements.txt
```

```bash
git diff --check
```

Se `pip-audit` não estiver instalado localmente, usar o ambiente/CI já configurado e
registrar isso; não alterar dependências apenas para fazer o comando existir.

### 12.1 Regressão manual em staging/preview

Registrar individualmente para Dados e Dev:

- login/logout e sessão expirada;
- criar/listar/abrir/editar projeto dentro do escopo;
- tentativa de abrir UUID da outra subárea;
- mover projeto com autorização adequada;
- sprint, planning, daily, review e retrospectiva;
- task, kanban, avaliação, painel e performance;
- ingestão manual, PDF/DOCX/imagem/TXT válidos e arquivo recusado;
- geração com mock/sandbox de IA ou uma única chamada autorizada;
- exportação Google Docs para a pasta correta por subárea;
- conectar/pesquisar/desconectar/reconectar repositório;
- push GitHub, fila, ingestão de commits, autor e contexto;
- aceite pelo GitHub App em repositório de teste;
- convite e desativação de pessoa;
- paginação e estados de erro.

Não testar cross-subarea apenas pela ausência de botão; chamar diretamente os
endpoints com IDs reais de fixture.

## 13. Metas mensuráveis de staging

Medir antes/depois com volume representativo e excluir cold start separadamente:

- leitura comum p95 < 500 ms;
- mutação sem IA p95 < 1 s;
- webhook GitHub p95 < 500 ms depois de persistir o job;
- nenhuma request acima do limite mantém crescimento de memória proporcional ao
  corpo excedente;
- ranking usa quantidade constante e documentada de queries;
- página transfere no máximo o limite definido;
- nenhum job fica em `processing` além do lease sem recuperação;
- 100% das chamadas Gemini funcionais produzem `ai_usage`;
- nenhuma chamada Gemini recebe fixture marcada como segredo;
- taxa de erro nominal < 1% no cenário controlado.

Se a infraestrutura não atingir uma meta, registrar medição, causa provável e plano;
não mascarar a falha aumentando limite sem evidência.

## 14. Sequência obrigatória de implementação e rollout

### Fase A — código compatível e schema documentado

- [ ] Responder o preflight obrigatório.
- [ ] Inventariar endpoints e riscos atuais.
- [ ] Escrever Migration v7 comentada, scripts dry-run e testes mockados.
- [ ] Implementar novas estruturas atrás de defaults compatíveis.
- [ ] Atualizar `GUIDE.md` e exemplos de env.
- [ ] Rodar pytest/build/audits.
- [ ] Publicar backend com `legacy|false|sync` apenas se autorizado.

### Fase B — schema e vínculos

- [ ] Backup/PITR confirmado.
- [ ] Preflight do schema-base sem ausências.
- [ ] V7 validada em staging e aplicada manualmente.
- [ ] Backfill dry-run executado.
- [ ] Ambiguidades resolvidas.
- [ ] Backfill aplicado manualmente e revalidado.
- [ ] `AUTHORIZATION_MODE=audit` observado sem PII.

### Fase C — identidade, convite e CSRF

- [ ] Backend aceita sessão/CSRF novos sem exigir ainda.
- [ ] Frontend de convite/CSRF publicado.
- [ ] Sessões antigas têm caminho controlado de renovação/login.
- [ ] CSRF habilitado após smoke test nos domínios reais.
- [ ] Signup antigo desligado.
- [ ] Autorização `enforce` habilitada apenas após divergências legítimas zeradas.

### Fase D — upload, Gemini e jobs

- [ ] Streaming/format guards validados.
- [ ] Todo Gemini migrou para gateway sem duplicar chamadas.
- [ ] Redaction e ledger de custo validados.
- [ ] Worker Railway publicado e saudável.
- [ ] Webhook mudou de `sync` para `queue`.
- [ ] Scheduler web deixou de duplicar jobs.

### Fase E — legado GitHub e escala

- [ ] Workflow de aceite e permissão do GitHub App aprovados.
- [ ] Aceite usa installation token, ref real e SHA-input validado.
- [ ] PATs legados revogados após validação.
- [ ] Hooks legados migrados para credencial escopada ou desligados.
- [ ] Paginação, busca, ranking e contexto medidos.
- [ ] Regressão completa de Dados e Dev registrada.

## 15. Rollback

- `AUTHORIZATION_MODE` volta para `legacy` sem apagar vínculos;
- `CSRF_ENFORCEMENT=false` apenas durante rollback coordenado do frontend/backend;
- `INVITE_ONLY_SIGNUP=false` pode restaurar temporariamente o fluxo antigo enquanto
  ele ainda existir, com risco explicitado e prazo curto;
- `DURABLE_JOBS_MODE=sync` só volta se a versão web ainda suporta sync e isso não
  causar processamento duplo; pausar worker antes da troca;
- jobs persistidos permanecem no banco e podem ser retomados;
- legados GitHub permanecem `true` até validação, mas PAT revogado não deve ser
  restaurado como rollback;
- schema aditivo permanece; rollback de aplicação não faz `DROP`;
- não desabilitar RLS às pressas: validar acesso por service role e rollback de
  aplicação;
- rollback nunca apaga projeto, sprint, task, ingestão, documento, score, vínculo ou
  histórico.

Cada troca de flag deve ter owner, horário, métrica de sucesso, métrica de rollback e
tempo máximo de observação documentados.

## 16. Não faz parte desta spec

- separar banco/deploy por subárea;
- substituir Supabase, Railway, Vercel, Gemini, GitHub ou Google Drive;
- migrar para microserviços;
- reescrever frontend em outro framework ou biblioteca visual;
- implementar SSO/OIDC completo;
- criar login social;
- remover fisicamente colunas legadas;
- reprocessar histórico inteiro de commits/documentos;
- usar score de IA para decisão automática de RH;
- criar acesso público aos dados;
- adicionar hard cap financeiro que interrompa operações;
- adicionar antivírus como dependência obrigatória;
- mudar GitHub para somente Dev ou recriar flags de subárea;
- alterar seleção global de repositórios do GitHub App;
- executar migration/deploy/rotação automaticamente.

## 17. Critérios de aceite

### Segurança e identidade

- [ ] A spec foi implementada sem depender de outro documento de spec.
- [ ] Migration v7 está comentada e não foi executada pelo agente.
- [ ] Backfill é manual, dry-run por default, idempotente e reporta ambiguidades.
- [ ] Toda rota/recurso consta na matriz automatizada de autorização.
- [ ] Não existe acesso cruzado por UUID entre projeto/subárea sem autorização.
- [ ] Listagens, search, performance e custos filtram os projetos autorizados.
- [ ] Signup público/enumeração deixam de existir quando a flag é ativada.
- [ ] Convite é hash-only, expirável, revogável e consumido atomicamente.
- [ ] Cargo/status/vínculo alterado revoga acesso em até 30 segundos.
- [ ] Toda mutação do browser exige CSRF + sessão/origem válidas.
- [ ] Webhook e hooks têm isenções específicas, não genéricas.
- [ ] RLS deny-by-default foi validada antes da produção.
- [ ] Rate limit é compartilhado e não confia em XFF não confiável.

### Upload, IA e GitHub

- [ ] Corpo excessivo sem `Content-Length` recebe `413` sem carga integral.
- [ ] MIME falso, ZIP bomb, excesso de páginas/pixels/texto e timeout falham de
  forma controlada.
- [ ] Todo uso funcional de Gemini passa pelo gateway único.
- [ ] Chave/prompt/resposta/diff/documento nunca aparecem em log/response/usage.
- [ ] Segredo detectado é redigido antes de chegar ao Gemini.
- [ ] 100% das chamadas Gemini têm custo/tokens/duração e escopo registrados.
- [ ] Custos são consultáveis globalmente por owner, por subárea e por projeto.
- [ ] Autoria por e-mail não verificado não gera identidade/score verificado.
- [ ] Webhook autentica/enfileira e responde `202` dentro da meta.
- [ ] Jobs têm idempotência, lease, retry, backoff, dead-letter e retry auditado.
- [ ] Repositório não vinculado nunca gera ingestão, mesmo autorizado no GitHub App.
- [ ] GitHub continua funcional e isolado em Dados e Dev.
- [ ] Aceite novo não lê PAT nem usa SHA do backend.

### Performance, consistência e operação

- [ ] Scheduler/worker não duplica execução com duas instâncias.
- [ ] Ranking usa queries em lote e respeita subárea/vínculos.
- [ ] Busca não transfere todo JSON de ingestões ao backend.
- [ ] Listas crescentes são paginadas sem quebrar o frontend.
- [ ] Contexto tem orçamento, fontes e crescimento limitado.
- [ ] Operações multi-tabela críticas são atômicas.
- [ ] Exportação Google Docs é idempotente, retomável e respeita a pasta da subárea.
- [ ] CORS/CSP/Markdown foram validados sem ampliar a superfície do browser.
- [ ] Seletor GitHub mantém 30 recentes + pesquisa remota de antigos.
- [ ] `pytest` passa integralmente.
- [ ] `npm run build` passa sem erro de tipo.
- [ ] Audits de dependência, secret scan e `git diff --check` passam.
- [ ] Metas de staging foram medidas e documentadas.
- [ ] Regressão manual de Dados e Dev foi registrada item por item.
- [ ] Rollback de cada modo foi testado sem exclusão de dados/schema.
- [ ] Modos finais estão em `enforce|true|true|queue`; exceções legadas possuem
  responsável e prazo explícitos.

## 18. Entrega final obrigatória

A resposta final do implementador deve conter, nesta ordem:

1. resumo da arquitetura final;
2. principais arquivos alterados;
3. migration adicionada, deixando explícito que **não foi executada**;
4. ações humanas pendentes, separadas por Supabase/Railway/Vercel/GitHub;
5. variáveis novas e valores de modo usados, sem segredos;
6. resultado completo de `pytest`;
7. resultado de `npm run build`;
8. resultado dos audits;
9. métricas antes/depois;
10. cada critério de aceite, um por um, com evidência;
11. regressão de Dados e Dev, item por item;
12. riscos residuais, flags ainda em compatibilidade e próximo gate;
13. confirmação de que nenhum segredo real/chamada paga foi usado sem autorização;
14. confirmação de que não houve commit, salvo pedido explícito do usuário.

Não usar “está tudo funcionando” como substituto para evidência. Se uma ação humana
impedir um critério, marcar como **pendente de gate externo**, explicar exatamente o
que deve ser feito e não declarar a Spec 10 concluída.
