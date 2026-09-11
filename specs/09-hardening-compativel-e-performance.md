# Spec 09 — Hardening compatível, dependências e ganhos de performance sem regressão

**Prioridade:** crítica · **Impacto estrutural:** baixo · **Depende de:** 01–08 · **Bloqueia:** Spec 10

## Contexto

Uma auditoria estática do backend, frontend, schema e dependências encontrou um
conjunto de correções urgentes que podem ser aplicadas sem mudar a arquitetura de
autorização, o modelo de dados funcional ou os contratos públicos da aplicação.

Na data da auditoria:

- `pytest` executou 300 testes com sucesso;
- `npm run build` passou;
- a rota `/{subarea}/projects/{id}` tinha 325 kB de First Load JS;
- `npm audit --omit=dev` apontou uma cadeia crítica no Next.js 15.3.9 e
  vulnerabilidades altas em `sharp`, `postcss` e `nanoid`;
- `pip-audit -r requirements.txt` apontou advisories no Pillow 12.2.0, todos com
  correção indicada no Pillow 12.3.0;
- respostas de erro de algumas rotas ainda incluíam a exceção original ou trecho de
  stack trace;
- o frontend não configurava headers de segurança;
- login e cadastro não tinham proteção contra tentativas automatizadas;
- a listagem de projetos consultava ingestões de todos os projetos para calcular
  `last_ingestion_at`;
- vários logs eram feitos com `print`, sem estrutura ou correlação.

As mudanças desta spec devem reduzir a exposição imediatamente, mas **não podem
alterar o comportamento funcional observado pelos usuários em requisições válidas**.
Mudanças que exigem novos vínculos de acesso, troca do fluxo de cadastro, CSRF,
RLS, fila durável ou reformulação do processamento de uploads ficam na Spec 10.

## Objetivo

Aplicar correções de segurança e performance de baixo risco, preservando integralmente:

- URLs, métodos HTTP e payloads de sucesso atuais;
- navegação, permissões e fluxos atualmente disponíveis;
- projetos e registros existentes;
- separação e rotas de `dados` e `dev`;
- geração com Gemini e configuração da chave global;
- exportação para as pastas corretas do Google Drive;
- integração GitHub App restrita ao piloto Dev;
- Planning, Daily, Review, Retrospectiva, documentos manuais, tarefas, sprints,
  funcionalidades, métricas, performance e painel de pessoas;
- execução local sem depender de serviços externos durante os testes automatizados.

Uma entrada que era válida antes desta spec deve continuar válida e produzir o
mesmo resultado funcional depois dela. A única exceção são requisições abusivas,
malformadas, excessivas ou dependentes de detalhes internos de erro.

## Regras de compatibilidade obrigatórias

1. Não remover, renomear ou tornar obrigatório nenhum campo existente da API.
2. Não mudar status code ou corpo de respostas de sucesso.
3. Erros de negócio documentados (`401`, `403`, `404`, `409`, `422`, `429`) devem
   manter sua mensagem amigável quando ela não contém detalhes internos.
4. Não criar autenticação nova, tabela de vínculo, sessão stateful ou mecanismo de
   autorização por projeto nesta spec.
5. Não executar SQL contra o Supabase. Qualquer índice novo deve ser apenas
   documentado, comentado e idempotente em `supabase_schema.sql`.
6. Não usar `npm audit fix --force`, não trocar major de framework e não atualizar
   dependências não relacionadas em lote.
7. Testes não podem chamar Gemini, GitHub, Google Drive, Resend ou Supabase reais.
8. Não usar a chave Gemini real para validar esta spec.
9. Backend novo deve funcionar com o frontend atual, e frontend novo deve funcionar
   com o backend atual durante o deploy gradual.
10. Não remover o hook legado nem as colunas legadas de GitHub ou Gemini.

## Escopo

### 1. Corrigir dependências vulneráveis

Frontend:

- atualizar `next` de `15.3.9` para `15.5.25`, mantendo a linha major 15;
- regenerar `package-lock.json` com a mesma versão de npm usada no projeto;
- confirmar que a árvore resultante corrige os advisories transitivos de `sharp`,
  `postcss` e `nanoid` apontados pelo audit;
- não habilitar AVIF, middleware, Server Actions ou qualquer feature nova apenas por
  causa da atualização;
- verificar todas as rotas do App Router após a atualização.

Backend:

- atualizar somente `Pillow==12.2.0` para `Pillow==12.3.0`;
- não alterar pdfplumber, pdf2image, LangChain, LangGraph, Supabase ou FastAPI nesta
  etapa, salvo se uma incompatibilidade comprovada impedir os testes;
- se houver ajuste de compatibilidade, documentar a causa e manter a menor mudança
  possível.

Validação obrigatória:

```bash
cd docudata-backend
.venv/bin/pytest
pipx run pip-audit -r requirements.txt

cd ../docudata-frontend
npm run build
npm audit --omit=dev
```

O audit não precisa ficar literalmente sem qualquer advisory futuro, mas não pode
restar vulnerabilidade alta ou crítica aplicável sem justificativa explícita,
documentada e acompanhada de mitigação.

### 2. Sanitizar respostas de erro sem perder diagnóstico interno

- o handler global de exceções deve retornar somente uma mensagem genérica e um
  `request_id`; nunca deve interpolar `str(exc)` no corpo;
- gerar ou aceitar um `X-Request-ID` com formato e tamanho validados e devolvê-lo no
  response;
- registrar internamente `request_id`, método, rota, status e tipo da exceção;
- não registrar corpo de request, cookies, headers de autorização, chave Gemini,
  chave de aplicação, private key, token GitHub, conteúdo extraído, diff ou documento;
- substituir respostas que hoje expõem exceção/traceback em `main.py`, `painel.py`,
  `composer.py`, `projects.py`, `operacionais.py`, `sprints.py`, `export.py`,
  `enrich.py`, `boletins.py`, `revisao_ingest.py` e demais ocorrências encontradas
  por busca global;
- preservar exceções de negócio conhecidas e converter falhas externas em mensagens
  estáveis como “Não foi possível consultar o GitHub” ou “Não foi possível exportar
  o documento”;
- trocar `print` por `logging`, mantendo logs curtos e sem dados sensíveis.

Ao terminar, a busca abaixo não deve encontrar interpolação de exceção em respostas:

```bash
rg 'detail=f.*(exc|traceback)|detail=str\(' docudata-backend
```

### 3. Headers de segurança sem quebrar o Next.js

Configurar em `next.config.ts`, para todas as páginas:

- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: strict-origin-when-cross-origin`;
- `Permissions-Policy` negando câmera, microfone e geolocalização;
- proteção contra framing com `X-Frame-Options: DENY` e/ou
  `frame-ancestors 'none'`;
- `poweredByHeader: false`.

Adicionar inicialmente `Content-Security-Policy-Report-Only`, compatível com:

- scripts e chunks do próprio Next.js;
- estilos inline já usados pelo projeto;
- chamadas `connect-src` apenas para o frontend e backend configurados;
- imagens `self`, `data:` e `blob:` quando realmente necessárias;
- navegação para GitHub e Google Docs sem liberar execução de scripts externos.

Não aplicar CSP bloqueante nesta spec se isso exigir nonce dinâmico ou alterar a
renderização estática. O objetivo desta etapa é obter visibilidade sem quebrar o
frontend; a política bloqueante fica condicionada aos testes e pode ser concluída
na Spec 10.

Adicionar testes para os headers. Validar pelo navegador que não há bloqueio de
hidratação, navegação, login, download ou abertura de links externos.

### 4. Reduzir exposição da documentação da API em produção

- adicionar `API_DOCS_ENABLED`, documentada no `.env.example` e no `GUIDE.md`;
- default local: `true`;
- produção: configurar `false` antes ou junto do deploy;
- quando desabilitada, `/docs`, `/redoc` e `/openapi.json` devem retornar `404`;
- `/health` permanece público e inalterado;
- não colocar autenticação improvisada nas páginas de documentação.

### 5. Rate limit específico para autenticação

Reutilizar o mecanismo e a interpretação de `X-Forwarded-For` da Spec 02:

- login: default `5/minute` por IP;
- cadastro/claim: default `3/hour` por IP;
- variáveis novas devem ter nomes específicos, validação de inteiro positivo e
  documentação no mapa de envs;
- resposta `429` não pode informar se o e-mail existe;
- uma autenticação bem-sucedida dentro do limite continua idêntica;
- endpoints somente leitura continuam sem rate limit, como decidido na Spec 02;
- `/health` nunca recebe rate limit;
- documentar que o primeiro item de `X-Forwarded-For` só é confiável enquanto o
  Railway sobrescrever/controlar esse header e o backend não estiver exposto por um
  caminho que contorne o proxy.

O armazenamento distribuído do limiter e a reformulação do cadastro pertencem à
Spec 10.

### 6. Guardas locais para processamento de imagem e PDF

Sem redesenhar o fluxo de upload:

- configurar um teto explícito de pixels antes de converter/redimensionar imagens;
- transformar `DecompressionBombWarning` em erro tratado;
- chamar `img.verify()` ou validação equivalente antes do processamento completo e
  reabrir a imagem para conversão;
- aceitar somente os formatos de imagem que a interface já declara suportar;
- adicionar timeout configurável ao Poppler usado na primeira página de PDF
  escaneado;
- retornar `422` amigável para arquivo inválido e `413` quando o limite conhecido for
  excedido;
- não alterar o tamanho máximo atual nem a estrutura do payload nesta spec.

Leitura em streaming, magic bytes completos, isolamento de parser e limites de
páginas ficam na Spec 10 porque exigem mudança estrutural.

### 7. Otimizações de consulta sem mudar contratos

#### Listagem de projetos

- calcular `last_ingestion_at` consultando somente os IDs de projetos já filtrados
  por `subarea` e, para operacional, pelos vínculos permitidos;
- nunca consultar ingestões de projetos que não serão devolvidos;
- preferir uma view/RPC de agregação ou uma consulta limitada aos IDs retornados;
- manter ordenação, campos e valor de `last_ingestion_at` exatamente iguais;
- garantir que `gemini_api_key` e `github_token` continuam removidos da resposta.

#### Projeções seguras

- substituir `select("*")` apenas nos endpoints em que o response model e os campos
  necessários são conhecidos com segurança;
- não retirar campos atualmente retornados por contratos públicos;
- login não deve buscar `senha_hash` junto com campos que serão retornados, embora
  possa selecioná-lo internamente para verificação;
- não introduzir paginação nesta spec, pois isso mudaria contratos.

#### Índices aditivos

Documentar como Migration v6, comentada e sem execução automática:

```sql
CREATE INDEX IF NOT EXISTS idx_projects_subarea_created
    ON projects (subarea, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestions_project_created
    ON ingestions (project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestions_project_sprint_created
    ON ingestions (project_id, sprint_number, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_docs_project_sprint_created
    ON generated_docs (project_id, sprint_number, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_funcionalidades_project
    ON funcionalidades (project_id);
CREATE INDEX IF NOT EXISTS idx_operacionais_email_ativo
    ON operacionais (email, ativo);
CREATE INDEX IF NOT EXISTS idx_pontuacao_operacional_sprint_fim
    ON pontuacao_operacional_sprint (operacional_id, sprint_fim DESC);
```

Antes de consolidar a migration, conferir nomes existentes e justificar cada índice
com as queries atuais. Em produção, orientar aplicação manual e preferencialmente
concorrente quando o tamanho real da tabela justificar; não executar nesta tarefa.

### 8. Reduzir o bundle da página de projeto sem redesenhar a UI

- carregar dinamicamente abas pesadas que não estão ativas;
- carregar modais somente quando abertos;
- manter estado, labels, ordem das abas, formulários e handlers atuais;
- usar placeholders discretos sem alterar o layout final;
- não introduzir biblioteca de estado ou framework visual;
- não dividir a API nem reestruturar o domínio nesta spec além do necessário para o
  lazy loading;
- registrar o tamanho antes e depois usando a saída do `next build`.

Meta: reduzir em pelo menos 20% o First Load JS de
`/{subarea}/projects/{id}`, sem aumentar o First Load compartilhado de forma
equivalente. Se a meta não for tecnicamente alcançável sem refactor maior, entregar
as divisões seguras, medir o resultado e documentar o restante para a Spec 10.

### 9. Automação de auditoria e prevenção de regressão

Adicionar ao CI, sem acessar segredos reais:

- `pytest`;
- `npm run build`;
- `npm audit --omit=dev --audit-level=high`;
- `pip-audit -r requirements.txt`;
- busca/secret scanning que falhe para private keys, tokens e chaves conhecidas;
- `git diff --check`;
- cache de dependências sem cachear `.env`, PEM ou credenciais.

Se o repositório ainda não tiver pipeline central apropriado, criar workflow mínimo
e documentado. Não habilitar autofix ou commit automático de dependência.

## Não faz parte desta spec

- nova tabela de vínculo pessoa–projeto ou pessoa–subárea;
- correção completa de IDOR/BOLA;
- remoção dos endpoints públicos de cadastro;
- convite por e-mail ou SSO;
- revogação stateful de JWT;
- CSRF token e mudança do contrato de `apiFetch`;
- habilitação ampla de RLS;
- cliente Supabase assíncrono ou singleton compartilhado;
- paginação de endpoints;
- fila de webhooks ou worker separado;
- mudança do scheduler;
- migração do aceite legado para GitHub App;
- remoção de `projects.github_token` ou qualquer coluna legada;
- redaction/DLP de diff antes do Gemini;
- reformulação do score de commits;
- orçamento e telemetria central de IA;
- streaming completo de upload ou antivírus;
- CSP bloqueante que exija nonce ou renderização dinâmica.

## Testes automatizados obrigatórios

Adicionar ou ajustar testes para provar:

1. exceção não tratada devolve mensagem genérica e `request_id`;
2. detalhes de Supabase, Gemini, GitHub e traceback não aparecem no response;
3. erros de negócio continuam com status e mensagem existentes;
4. headers de segurança aparecem nas páginas do frontend;
5. docs ficam disponíveis com a flag ligada e retornam `404` com a flag desligada;
6. login respeita o limite e não revela existência do e-mail;
7. endpoints de leitura e `/health` não foram limitados;
8. imagem válida continua sendo processada;
9. imagem acima do teto de pixels e imagem corrompida são recusadas sem crash;
10. timeout do Poppler é traduzido para erro amigável;
11. listagem de projetos não consulta ingestões fora dos IDs permitidos;
12. `last_ingestion_at` mantém o resultado anterior;
13. campos sensíveis de projeto não aparecem nas respostas;
14. lazy loading não quebra renderização nem tipos.

## Matriz de regressão manual obrigatória

Testar localmente, sem gastar Gemini real sempre que houver mock disponível:

- login e logout;
- cadastro/claim em cadência normal;
- entrada nas home pages de Dados e Dev;
- criar e abrir projeto nas duas subáreas;
- listar, editar e excluir projeto de teste;
- criar sprint, mover task e abrir todas as abas;
- upload de TXT, DOCX, PDF textual, PDF escaneado, PNG e JPEG pequenos;
- Planning, Daily, Review e Retrospectiva com Gemini mockada;
- documento manual sem IA;
- listagem e expansão de documentos;
- exportação Google Docs com serviços mockados;
- tela de configurações e status da chave Gemini sem expor o segredo;
- conexão/listagem de repositório GitHub em Dev com API mockada;
- performance, pessoas e metodologia;
- navegação direta e refresh em todas as rotas;
- console do navegador sem erro de CSP ou hidratação.

## Critérios de aceite

- [ ] `pytest` passa integralmente.
- [ ] `npm run build` passa sem erro de tipo.
- [ ] Next.js está em 15.5.25 e Pillow em 12.3.0.
- [ ] Não resta advisory alto/crítico aplicável sem justificativa documentada.
- [ ] Nenhum response expõe exceção, traceback, segredo ou conteúdo privado.
- [ ] Toda resposta possui request ID correlacionável com o log.
- [ ] Headers de segurança foram verificados e não quebram o frontend.
- [ ] Docs da API podem ser desligadas em produção sem afetar `/health`.
- [ ] Login/cadastro abusivos recebem `429`; uso normal permanece igual.
- [ ] Endpoints somente leitura continuam sem rate limit.
- [ ] Arquivos válidos atualmente suportados continuam funcionando.
- [ ] Imagem malformada ou excessiva falha de forma controlada.
- [ ] Listagem de projetos não lê ingestões de outros projetos/subáreas.
- [ ] Contratos e payloads de sucesso não mudaram.
- [ ] First Load JS da página de projeto foi medido e reduzido sem regressão.
- [ ] CI executa testes, build e auditorias sem usar segredos reais.
- [ ] Nenhuma migration foi executada automaticamente ou pelo agente.
- [ ] A matriz de regressão foi registrada item por item no relatório final.

## Rollout e rollback

1. Atualizar e validar dependências em branch isolada.
2. Executar testes e build localmente.
3. Implantar primeiro em preview/staging.
4. Executar a matriz de regressão nas duas subáreas.
5. Configurar `API_DOCS_ENABLED=false` na produção antes do deploy final.
6. Fazer deploy sem aplicar a Migration v6; os índices não são requisito funcional.
7. Medir erros e latência.
8. Aplicar índices manualmente em janela adequada, um por vez.

Rollback de código deve ser suficiente. Os índices, se já criados, podem permanecer:
eles são aditivos e não alteram o contrato. Não apagar dados nem reverter schema de
forma destrutiva durante um rollback.
