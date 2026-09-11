# AGENTS.md — contexto permanente do projeto

Este arquivo orienta qualquer agente de IA que leia, revise ou altere este
repositório. Ele vale para `docudata-backend/`, `docudata-frontend/`, scripts,
documentação e schema.

Leia este arquivo **por completo antes de tocar em qualquer arquivo**. Em seguida,
leia por completo a spec solicitada pelo usuário, se houver, e inspecione o código
atual diretamente relacionado ao trabalho.

## 1. Hierarquia de contexto e escopo

Use esta ordem:

1. `AGENTS.md`: arquitetura, regras permanentes, segurança e forma de trabalhar;
2. pedido atual do usuário e spec correspondente: objetivo, escopo, não escopo e
   critérios de aceite da entrega;
3. código, testes e schema atuais: implementação real que precisa ser preservada;
4. `GUIDE.md`: configuração operacional e mapa de variáveis de ambiente.

Uma spec complementa este arquivo com decisões específicas da implementação. Ela
não autoriza mudanças fora do seu escopo. Se uma spec evoluir deliberadamente uma
regra permanente, faça a implementação pedida e atualize este arquivo somente se o
usuário também solicitar ou se a própria spec exigir.

Specs não aplicadas descrevem intenção, não o estado do deploy. Não pressuponha que
uma migration, variável ou configuração externa existe só porque aparece numa spec
ou em um bloco comentado. Confirme pelo código e, para ambiente real, peça uma
verificação somente-leitura ao usuário.

## 2. O que é este projeto

O sistema é o agente interno de documentação e acompanhamento de projetos do CITi.
Ele recebe material bruto — texto, formulário, PDF, DOCX, imagem e commits —, usa
LangGraph + Gemini para extrair conhecimento estruturado e gera artefatos como
planning, daily, review, retrospectiva, atas, decisões, boletins e insights por
projeto/sprint.

Além da documentação, o sistema mantém sprints, funcionalidades, kanban de tasks,
operacionais, avaliações, métricas, performance e integração com GitHub e Google
Drive.

É um monorepo com dois deploys:

- `docudata-backend/`: FastAPI, Supabase, LangGraph e integrações; Railway;
- `docudata-frontend/`: Next.js App Router; Vercel.

Backend e frontend são publicados separadamente, embora vivam no mesmo repositório.
Um push pode disparar os dois deploys conforme a configuração de root directory de
cada plataforma.

## 3. Estado funcional atual que deve ser preservado

### 3.1 Autenticação e papéis já existem

O projeto **possui autenticação de usuário**. Não restaure a regra antiga de “MVP
sem login”. O fluxo atual usa:

- tabela `pessoa` no Supabase;
- senha com hash bcrypt;
- JWT HS256;
- cookie `docudata_session` `HttpOnly`;
- chamadas do frontend com `credentials: "include"`;
- cargos `owner`, `lider`, `gerente` e `operacional`.

O RBAC atual ainda possui limitações estruturais conhecidas; a Spec 10 define seu
endurecimento. Fora de uma spec que peça isso, não substitua autenticação, não crie
login social/SSO, não exponha token ao JavaScript e não amplie permissões para
resolver um teste.

Intenção de negócio para acesso:

- `owner`: administração global;
- `lider`: escopo das subáreas atribuídas;
- `gerente`: projetos atribuídos;
- `operacional`: projetos atribuídos e ações operacionais permitidas.

Até os vínculos normalizados da Spec 10 estarem implantados, preserve compatibilidade
com o modelo atual e não finja que o enforcement novo já existe.

### 3.2 Duas subáreas no mesmo sistema

Existem exatamente duas subáreas:

```text
dados
dev
```

Elas compartilham frontend, backend e banco. A separação é feita por
`projects.subarea`, não por deploy ou banco diferente.

Invariantes:

1. Dados e Dev não podem ver dados uma da outra sem permissão administrativa
   explícita.
2. Todo recurso derivado herda o projeto: sprint, task, funcionalidade, ingestão,
   documento, custo, avaliação, score, boletim, solicitação, repositório e commit.
3. A subárea enviada pelo frontend ou presente na URL nunca é fonte suficiente de
   autorização.
4. Para operar por `project_id`, carregue o projeto no servidor e valide o acesso.
5. Para operar por ID de recurso filho, resolva primeiro seu `project_id`.
6. Toda listagem, busca, ranking ou agregado entre projetos deve filtrar os projetos
   e subáreas autorizados **antes** de agregar.
7. Criar um projeto pela rota `/dados/...` ou `/dev/...` deve persistir a subárea
   correspondente; o default de banco não substitui esse valor explícito.
8. Mover projeto de subárea preserva recursos e histórico. A permissão para a troca
   deve ser validada na origem e no destino.

Não adicione `subarea` arbitrariamente a endpoints que operam sobre um único projeto
se isso permitir conflito entre o parâmetro e o projeto real. Derive do banco.

### 3.3 Chave Gemini global

A credencial Gemini é **única e global para toda a aplicação**:

- é configurada pelo fluxo global de Configurações;
- é armazenada em `app_settings`, criptografada com `DOCUDATA_SECRETS_KEY`;
- é acessada exclusivamente por `services/gemini_key.py` ou pelo gateway central
  definido numa spec;
- nunca é retornada pelo backend nem exposta em hint reversível;
- nunca usa prefixo `NEXT_PUBLIC_`;
- sua substituição deve afetar todos os projetos sem edição individual.

Custos e tokens continuam atribuídos ao projeto/subárea que originou cada operação.
Credencial global não significa custo global sem rastreabilidade.

A coluna legada `projects.gemini_api_key` pode existir no banco, mas não deve ser
lida, escrita, exibida ou removida por migration destrutiva sem pedido específico.

### 3.4 Google Docs e Drive por subárea

O OAuth client Google é compartilhado, mas a identidade/pasta é separada:

- Dados: `GOOGLE_REFRESH_TOKEN` e `GDRIVE_FOLDER_ID`;
- Dev: `GOOGLE_REFRESH_TOKEN_DEV` e `GDRIVE_FOLDER_ID_DEV`.

Templates com sufixo `_DEV` são overrides opcionais. Quando ausentes, Dev pode
reutilizar o template equivalente de Dados, mas o destino continua sendo a pasta de
Dev.

Sempre derive refresh token, pasta e template a partir de `projects.subarea`
carregada no backend. Não aceite IDs de pasta/template ou subárea arbitrários do
browser. Nunca registre tokens Google.

### 3.5 GitHub App para Dados e Dev

O GitHub App está disponível permanentemente para projetos das duas subáreas. Não
reintroduza `GITHUB_INTEGRATION_ENABLED` ou `GITHUB_INTEGRATION_SUBAREAS`.

Modelo atual:

- o App pode estar autorizado para todos os repositórios da organização;
- cada projeto escolhe explicitamente seus repositórios em
  `project_repositories`;
- somente vínculo ativo faz um push gerar ingestão para aquele projeto;
- repositório autorizado no App, mas não vinculado, deve ser ignorado;
- installation token e private key permanecem somente no backend;
- o seletor mostra inicialmente os 30 repositórios com push mais recente;
- pesquisa remota encontra repositórios antigos sem carregar toda a organização;
- desconectar e reconectar dentro do projeto não deve obrigar reinstalar o App.

Os commits ingeridos são `ingestions` do projeto e devem poder compor o contexto de
documentos/insights junto com ingestões manuais. Preserve repositório, branch, SHA,
URL e autoria disponíveis. Não faça chamada Gemini apenas para listar ou pesquisar
repositórios.

O hook com `DOCUDATA_PROJECT_ID`/`DOCUDATA_APP_SECRET` e o PAT em
`projects.github_token` são legados temporários. Código novo deve preferir GitHub App
e não ampliar o uso dessas credenciais.

## 4. Banco, schema e migrations

Supabase é o banco compartilhado. O backend acessa dados somente por
`services/supabase_client.get_client()`; não instancie outro client dentro de
routers.

O backend usa `SUPABASE_SERVICE_KEY`, que pode contornar RLS. Portanto:

- autorização no FastAPI é obrigatória;
- RLS é defesa adicional, não substituta;
- browser nunca recebe service role;
- queries devem selecionar apenas campos necessários, especialmente em tabelas com
  segredos ou conteúdo grande.

`docudata-backend/supabase_schema.sql` é a referência/ledger manual do schema. Ele
**não roda sozinho** no startup, CI, Railway ou Vercel. Blocos de migration
incremental ficam comentados para revisão e execução humana no SQL Editor.

Regras para qualquer migration:

- escrever SQL idempotente e comentado seguindo o padrão do arquivo;
- nunca executar contra banco real sem autorização explícita;
- nunca criar mecanismo automático de migration se o projeto não o possui;
- preferir alteração aditiva, coluna nullable/default compatível e índice
  justificado por query real;
- não usar `DROP`, truncar, renomear coluna em uso ou alterar tipo de forma destrutiva
  sem spec e plano de migração explícitos;
- não pressupor que blocos comentados já foram aplicados;
- fornecer query somente-leitura de preflight e SQL copiável ao usuário;
- em produção, considerar lock/volume e usar janela adequada; índices grandes podem
  exigir `CREATE INDEX CONCURRENTLY` fora de transação;
- nunca colar/rodar o arquivo inteiro por conveniência sem conferir o estado do
  banco e o bloco realmente necessário.

As migrations v3–v6 documentam, respectivamente, subárea, configuração global,
GitHub App e índices de leitura. A Spec 10 define a v7. Esses números são histórico
do schema, não prova de aplicação no ambiente.

## 5. Fronteiras de segurança permanentes

### 5.1 Segredos e configuração

- Tudo é lido de `os.environ`; `.env` é apenas local.
- Nunca hardcode, logue, devolva ou commite segredo.
- Nunca coloque credencial em variável `NEXT_PUBLIC_*`.
- `NEXT_PUBLIC_API_URL` é configuração pública, não segredo.
- Consulte e atualize o mapa de envs no `GUIDE.md` ao adicionar variável.
- Arquivos `.env`, `.pem`, tokens e chaves reais não entram em fixtures ou output de
  ferramenta.
- `DOCUDATA_APP_SECRET` é exclusivo de automações/hook legado, não autenticação do
  browser.

### 5.2 HTTP, erros e logs

- CORS usa allowlist exata de origens; nunca use origem `*` com cookies.
- Mutações do browser precisam respeitar a proteção CSRF vigente.
- Erros de negócio usam `HTTPException` e mensagem amigável.
- Erro interno/externo não expõe exception, URL privada, payload ou segredo.
- Preserve `X-Request-ID` nas respostas e logs sanitizados.
- Não registre request body, cookie, Authorization, documento, diff, prompt ou
  resposta integral do modelo.
- `/health` deve ser barato e não chamar Supabase/Gemini/Google/GitHub.
- `API_DOCS_ENABLED=false` é o valor esperado em produção.

### 5.3 Arquivos e conteúdo não confiável

- Não confie em `Content-Length`, extensão, MIME, filename, Markdown, PDF/DOCX,
  imagem, texto, mensagem/diff de commit ou output de modelo.
- Aplique limites antes de carregar conteúdo integral sempre que possível.
- Não use filename do usuário como caminho local.
- Parsing bloqueante/CPU-bound não deve bloquear o event loop.
- Não habilite renderização de HTML bruto em Markdown sem sanitização e spec
  explícita.
- Conteúdo enviado ao Gemini deve ser delimitado, limitado e redigido de segredos.

### 5.4 Integrações e efeitos externos

- Webhook GitHub só é confiável depois de validar HMAC do corpo bruto.
- Operações externas não idempotentes precisam de estado/chave de idempotência.
- Retries não podem duplicar ingestão, documento, e-mail ou cobrança Gemini.
- Não execute chamadas reais pagas ou mutações externas durante testes sem avisar e
  receber autorização.
- Installation/access/refresh tokens nunca são enviados ao browser.

## 6. Convenções de código

### 6.1 Backend

- FastAPI com `APIRouter` por domínio em `routers/`.
- Lógica de negócio e integrações em `services/`.
- Schemas Pydantic em `models/schemas.py` ou módulo coerente se ele crescer demais.
- Grafos LangGraph em `graphs/`.
- Router novo deve ser registrado em `main.py`.
- Nomes de campos, variáveis, funções e docstrings em português quando o módulo já
  segue esse padrão.
- Comentários em português, curtos e explicando o porquê.
- Erros de negócio usam `HTTPException(status_code=..., detail=...)`.
- Não aceite nome de tabela, filtro bruto ou expressão SQL vindo do request.
- Evite I/O síncrono longo em handler `async`; use rota sync/threadpool ou adaptador
  explícito conforme o padrão escolhido.
- Evite `select("*")` em fluxo com conteúdo/segredo; use projeção mínima.
- Operações multi-tabela que precisam ser atômicas devem usar RPC/transação, não uma
  sequência vulnerável a falha parcial.

### 6.2 Frontend

- Next.js App Router com componentes client onde necessário.
- Manter o estilo inline/CSS-in-JS atual; não introduzir framework visual para uma
  mudança localizada.
- Chamadas HTTP ficam em `app/lib/api.ts`; componentes não fazem `fetch` direto.
- Tipar request/response e tratar estados de loading, vazio, erro e cancelamento.
- Rotas de projeto permanecem sob `app/[subarea]/projects/...`.
- A URL melhora a navegação, mas não autoriza acesso.
- Preserve identidade visual, responsividade, barra superior e fluxos atuais.
- Não considerar botão oculto como controle de segurança.

### 6.3 Dependências e refactors

- Prefira stdlib e dependências já existentes quando suficientes.
- Não fixe/atualize todo `requirements.txt` ou lockfile por causa de uma dependência
  isolada.
- Nova dependência exige motivo, audit e teste.
- Scripts copiados para repositórios de squads em `hooks/` usam stdlib/`urllib`; não
  adicione biblioteca Python externa a eles.
- Evite abstração genérica ou refactor não relacionado à spec.
- Preserve compatibilidade de contratos ou versione/migre frontend e backend em
  ordem segura.

## 7. Como trabalhar no repositório

Antes de alterar:

1. leia este arquivo e a spec completa;
2. rode busca global pelos símbolos/fluxos citados;
3. confira `git status` e preserve alterações do usuário;
4. identifique efeitos em backend, frontend, schema, envs, testes e deploy;
5. informe previamente ações humanas externas necessárias;
6. para mudança estrutural, descreva rollout e rollback antes de executar.

Durante:

- implemente apenas o escopo pedido;
- não “corrija junto” algo fora do escopo sem autorização;
- centralize regra de segurança/integração em vez de copiá-la entre routers;
- atualize testes existentes que codificam o comportamento alterado;
- use mocks para Supabase, Gemini, GitHub, Google e Resend;
- não gaste chave Gemini real deliberadamente;
- não aplique SQL, deploy, rotação de segredo ou mudança em GitHub App por conta
  própria.

Ao finalizar:

- execute validações proporcionais ao que mudou;
- confira busca global por referências legadas;
- execute `git diff --check`;
- liste critérios de aceite um por um com evidência;
- se existir gate externo pendente, marque como pendente e não diga que tudo está
  funcionando em produção;
- não faça commit/push salvo pedido explícito do usuário;
- quando o usuário pedir commit de implementação, não inclua `AGENTS.md` ou
  `specs/` sem autorização expressa para versionar esses documentos.

## 8. Como rodar localmente

### Backend

Na primeira vez:

```bash
cd docudata-backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Depois de preencher `.env` conforme `GUIDE.md`:

```bash
cd docudata-backend
source .venv/bin/activate
python -m uvicorn main:app --reload
```

Testes:

```bash
cd docudata-backend
source .venv/bin/activate
python -m pytest
```

Os testes devem usar mocks e não depender de banco ou chave paga real.

### Frontend

Na primeira vez:

```bash
cd docudata-frontend
npm install
cp .env.local.example .env.local
```

Desenvolvimento e build:

```bash
npm run dev
npm run build
```

O frontend usa somente `NEXT_PUBLIC_API_URL` para apontar ao backend.

### GitHub App local

Quando o webhook for testado localmente, o túnel/Smee precisa estar rodando de novo
após reiniciar os terminais. A URL pública encaminha para
`http://localhost:8000/webhooks/github`. Nunca cole private key ou webhook secret no
chat/output.

## 9. Validação mínima por tipo de mudança

- Backend: `python -m pytest` em `docudata-backend/`.
- Frontend/rotas/tipos: `npm run build` em `docudata-frontend/`.
- Ambos: executar os dois.
- Schema: validar sintaxe/ordem em ambiente isolado; não aplicar no banco real.
- Segurança/dependências: usar os audits já definidos no workflow de CI.
- Performance: medir antes/depois com volume representativo, sem carga agressiva em
  produção.
- Fluxo externo: teste mockado primeiro; teste real mínimo somente com autorização.

Teste passando é necessário, mas não suficiente. Também verifique isolamento de
subárea, autorização por ID, ausência de segredos, idempotência e compatibilidade do
fluxo atual.

## 10. Specs

As specs vivem em `specs/NN-slug.md`. Cada uma deve declarar contexto específico,
escopo, não escopo, riscos, ações humanas, testes e critérios de aceite.

- Implemente uma spec por vez.
- Leia a spec inteira antes de escrever código.
- “Não faz parte” é limite explícito.
- Migration documentada não significa migration aplicada.
- Critério bloqueado por Supabase/Railway/Vercel/GitHub deve ser reportado, não
  presumido.
- Specs antigas não prevalecem sobre o código atual já integrado nem sobre este
  contexto atualizado.

A Spec 10 é o complemento focado no fechamento estrutural de autorização, sessão,
CSRF, uploads, Gemini, GitHub/jobs, Google Docs, banco e escalabilidade. Ela não deve
ser tratada como autorização para redesenhar o produto ou trocar sua infraestrutura.
