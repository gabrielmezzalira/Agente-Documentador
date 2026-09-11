# Spec 09 — Relatório de execução

**Branch:** `feat/dev-subarea-expansion` · **Data:** 10/09/2026

## Resumo

| Verificação | Antes | Depois |
|---|---|---|
| `pytest` | 300 passando | **334 passando** |
| `npm run build` | ok (Next 15.3.9) | **ok (Next 15.5.25)** |
| `npm test` (novo) | — | **8 passando** |
| `npm audit --omit=dev` | 1 crítica + 3 altas | **0 vulnerabilidades** |
| `pip-audit -r requirements.txt` | advisories no Pillow 12.2.0 | **0 vulnerabilidades** |
| First Load JS `/{subarea}/projects/[id]` | 326 kB | **167 kB (−48,8%)** |
| Tamanho da rota | 180 kB | **21,3 kB** |
| First Load compartilhado | 103 kB | 103 kB (+0,28 kB em "other shared chunks") |

Meta da spec era −20% no First Load da página de projeto; foram −48,8%.

---

## 1. Dependências

**Frontend** — `next` 15.3.9 → **15.5.25** (mesma major), lockfile regenerado com npm 10.8.2.

A atualização sozinha zerou a cadeia crítica do Next, mas deixou `postcss`, `nanoid`
e `sharp` altos por transitividade. `npm audit fix --force` era proibido (levava a
Next 16). Em vez disso, dois `overrides` cirúrgicos em `package.json`:

| Pacote | Resolvia para | Agora | Justificativa |
|---|---|---|---|
| `sharp` | 0.34.5 | 0.35.4 | O próprio Next 15.5.25 declara `^0.34.3 \|\| ^0.35.4` — só o resolvedor escolhia o ramo antigo. |
| `postcss` | 8.4.31 (pin do Next) | 8.5.28 | Minor compatível; arrasta `nanoid` 3.3.12 → 3.3.19, que fecha os dois advisories de nanoid. |

Build e testes validados com a árvore resultante.

**Backend** — apenas `Pillow==12.2.0` → **`Pillow==12.3.0`**. Nenhuma outra dependência
tocada; nenhum ajuste de compatibilidade foi necessário.

## 2. Respostas de erro sanitizadas + request id

- Novo `core/observability.py`: geração/validação de `X-Request-ID`, log de exceção e
  helpers para falhas internas/externas. O stack é sanitizado para manter apenas
  arquivo, linha e função: nem o log recebe `str(exc)`.
- Novo middleware `correlacionar_requisicao` (o mais externo da pilha de usuário):
  carimba `X-Request-ID` em toda resposta. Reaproveita o header recebido só quando
  ele bate `[A-Za-z0-9._:-]{8,64}` — bloqueia header injection e poluição de log.
- `CORSMiddleware` ganhou `expose_headers=["X-Request-ID"]` para o navegador conseguir ler.
- Handler global de `Exception` devolve `{"detail": "Erro interno no servidor. Tente
  novamente em instantes.", "request_id": "..."}` — nunca mais `str(exc)`.
- **Dois vazamentos de traceback completo** que a busca original da spec não pegava:
  `painel.py` e `composer.py` mandavam `type(e).__name__ + str(e)[:500] + traceback[:800]`
  direto para o navegador. Removidos (o `import traceback` local foi junto).
- Erros externos padronizados: `"Não foi possível consultar o GitHub…"`,
  `"Não foi possível exportar o documento…"`, `"Não foi possível analisar o conteúdo
  com a IA…"`, etc.
- Mensagens internas do grafo (`Structured output parsing failed: …`,
  `Supabase insert failed: …`) trocadas por texto estável antes de chegarem ao router.
- **13 `print()` → `logging`**, sem conteúdo de cliente: o log de extração não registra
  mais o preview do documento, e as falhas externas registram só escopo + tipo da
  exceção (a mensagem dessas exceções costuma embutir a credencial rejeitada).
- Cada resposta também gera uma linha curta com `request_id`, método, path e status,
  tornando o identificador pesquisável inclusive para respostas de sucesso e erros
  tratados. Logs do scheduler de e-mail deixaram de registrar destinatário e de usar
  tracebacks não sanitizados.
- Ganho de brinde: o grafo de extração agora tem edge condicional após
  `preprocessar_arquivo`. Arquivo reprovado na guarda encerra ali, **sem gastar chamada
  do Gemini** — antes ia para a IA com conteúdo vazio e a mensagem específica era
  sobrescrita pela falha genérica.

Busca da spec (`detail=f...{exc}` / `detail=str(`) não encontra mais nada. Três
mensagens legítimas de orçamento davam falso positivo porque “excedido” começa por
`exc`; a string passou para uma variável antes do `HTTPException`, sem mudar o texto.

## 3. Headers de segurança

`security-headers.mjs` (módulo separado para poder ser testado sem subir o Next),
consumido por `next.config.ts` em `/:path*`:

`X-Content-Type-Options: nosniff` · `Referrer-Policy: strict-origin-when-cross-origin` ·
`X-Frame-Options: DENY` · `Permissions-Policy: camera=(), microphone=(), geolocation=()` ·
`Content-Security-Policy-Report-Only` (com `frame-ancestors 'none'`, `object-src 'none'`,
`connect-src` só self + backend configurado) · `poweredByHeader: false`.
`unsafe-eval` só é liberado no servidor de desenvolvimento, para os source maps do
bundler; a política de produção não inclui essa permissão.

Verificado contra um `next start` real: todos presentes, `X-Powered-By` sumiu.

## 4. `API_DOCS_ENABLED`

Padrão `true`. Com `false`, `/docs`, `/redoc` e `/openapi.json` devolvem 404 e `/health`
segue idêntico. Verificado com uvicorn real nos dois estados.

## 5. Rate limit de autenticação

`AUTH_LOGIN_RATE_LIMIT_PER_MINUTE` (5) e `AUTH_SIGNUP_RATE_LIMIT_PER_HOUR` (3), por IP,
mesmo mecanismo e mesma leitura de `X-Forwarded-For` da Spec 02. O 429 é idêntico para
e-mail existente e inexistente (teste compara os dois corpos). Endpoints de leitura e
`/health` continuam sem limite.

`tests/conftest.py` ganhou reset autouse do limiter — sem isso um teste consumiria a
cota do seguinte. O limiter **não** é desligado nos testes.

## 6. Guardas de imagem e PDF

Em `services/file_parser.py`:

- `MAX_IMAGE_PIXELS` (padrão 40 MP) aplicado antes de qualquer conversão.
- `DecompressionBombWarning` promovido a erro dentro de `warnings.catch_warnings()`
  (não altera o filtro global do processo).
- `img.verify()` antes do processamento, com reabertura para converter.
- Allowlist de formato: PNG, JPEG/JPG, MPO (fotos de celular), WEBP.
- `PDF_POPPLER_TIMEOUT_SECONDS` (padrão 30) passado ao `convert_from_bytes`.
- Três exceções tipadas → **413** (acima do teto) e **422** (inválido / timeout),
  propagadas pelo novo campo `erro_status` do estado do grafo.

Tamanho máximo de upload e estrutura de payload não mudaram.

## 7. Consultas

- `list_projects`: `last_ingestion_at` agora usa `.in_("project_id", ids da página)`.
  Antes varria a tabela inteira de ingestões — as duas subáreas, inclusive projetos que
  o operacional não pode ver. Ordenação, campos e valores idênticos (com teste).
- Projeções explícitas onde o response model é conhecido: `list_projects`/`get_project`
  (deixa de trazer `gemini_api_key` do banco) e `login` (traz `senha_hash` só para
  verificar, em vez de `select("*")`).
- **Migration v6** documentada, comentada e idempotente no fim de `supabase_schema.sql`,
  com a query que justifica cada um dos 7 índices. **Nada foi executado.**

## 8. Bundle

`next/dynamic` em 5 abas não-iniciais e 7 modais, com montagem condicional para os
modais (o chunk só baixa quando abre). Aba Sprints (`Tabs`, `SprintCard`, `DocTypeCard`,
`TutorialBanner`) continua no bundle inicial. Estado, labels, ordem das abas, formulários
e handlers inalterados. Nenhuma biblioteca nova.

## 9. CI

`.github/workflows/ci.yml`, três jobs, nenhum segredo real: `pytest` + `pip-audit`;
`npm ci` + `npm test` + `npm run build` + `npm audit --omit=dev --audit-level=high`;
`git diff --check` + varredura de segredos (PEM, `ghp_`/`gh[opsu]_`/`github_pat_`,
`AIza…`, `sk-…`, `re_…`, JWT). Cache só de índice de dependências. Sem autofix.
O workflow legado `docudata-sync.yml` não foi tocado.

---

## Testes automatizados obrigatórios

| # | Exigência | Onde | Status |
|---|---|---|---|
| 1 | Exceção não tratada → mensagem genérica + `request_id` | `test_hardening_spec09.py` | ✅ |
| 2 | Supabase/Gemini/GitHub/traceback fora do response | idem (+ guarda anti-regressão por regex) | ✅ |
| 3 | Erros de negócio mantêm status e mensagem | idem (404, 409, 401) | ✅ |
| 4 | Headers de segurança nas páginas | `docudata-frontend/tests/security-headers.test.mjs` + `next start` real | ✅ |
| 5 | Docs on/off | subprocesso com a flag nos dois estados (+ uvicorn real) | ✅ |
| 6 | Login limitado sem revelar e-mail; ambos os cadastros limitados | idem (compara os dois corpos de 429 e testa `novo`/`claim`) | ✅ |
| 7 | Leitura e `/health` sem rate limit | `test_limits.py` + novo teste de `/health` | ✅ |
| 8 | Imagem válida continua processada | idem (inclui redimensionamento) | ✅ |
| 9 | Imagem acima do teto / corrompida recusadas sem crash | idem (+ formato fora da allowlist) | ✅ |
| 10 | Timeout do Poppler → erro amigável | idem (unidade + nó do grafo) | ✅ |
| 11 | Listagem não consulta ingestões fora dos IDs | idem (registra o `in_` chamado) | ✅ |
| 12 | `last_ingestion_at` mantém o resultado | idem | ✅ |
| 13 | Campos sensíveis fora da resposta | idem | ✅ |
| 14 | Lazy loading não quebra renderização nem tipos | `next build` (type check) + `tests/lazy-loading.test.mjs` | ✅ automatizável / ⚠️ renderização no browser é manual |

---

## Matriz de regressão manual — **pendente em ambiente integrado**

Precisa de navegador conectado, Supabase de teste e sessão logada. Nesta revisão, o
navegador interativo não estava disponível e nenhuma operação real foi feita para não
alterar dados nem consumir Gemini. O servidor local foi consultado por HTTP: a página
de login respondeu 200 com todos os headers esperados e sem `X-Powered-By`.

| Item | Status |
|---|---|
| Login e logout | ⬜ pendente |
| Cadastro/claim em cadência normal | ⬜ pendente |
| Home de Dados e de Dev | ⬜ pendente |
| Criar e abrir projeto nas duas subáreas | ⬜ pendente |
| Listar, editar e excluir projeto de teste | ⬜ pendente |
| Criar sprint, mover task, abrir todas as abas | ⬜ pendente (**maior risco: lazy loading**) |
| Upload TXT, DOCX, PDF textual, PDF escaneado, PNG, JPEG | ⬜ pendente (**maior risco: guardas de imagem/PDF**) |
| Planning, Daily, Review, Retrospectiva | ⬜ pendente |
| Documento manual sem IA | ⬜ pendente |
| Listagem e expansão de documentos | ⬜ pendente |
| Exportação Google Docs | ⬜ pendente |
| Configurações e status da chave Gemini | ⬜ pendente |
| Conexão/listagem de repositório GitHub em Dev | ⬜ pendente |
| Performance, pessoas e metodologia | ⬜ pendente |
| Navegação direta e refresh em todas as rotas | ⬜ pendente |
| Console do navegador sem erro de CSP ou hidratação | ⬜ pendente (CSP é Report-Only: violação aparece no console, não bloqueia) |

Sugestão de ordem: abas do projeto → uploads → CSP no console. São os três pontos
onde esta spec realmente mexeu no caminho do usuário.

---

## Pontos que exigem decisão ou ação sua

1. **`API_DOCS_ENABLED=false` no Railway** antes ou junto do deploy. Sem isso o
   comportamento em produção continua o de hoje (docs abertas).
2. **Migration v6 não foi aplicada** — de propósito. São 7 índices aditivos, nenhum
   é requisito funcional. Aplicar manualmente, um por vez, preferindo
   `CREATE INDEX CONCURRENTLY` nas tabelas já grandes.
3. **Reversão consciente do commit `264fa1a`** ("mostra o erro real em vez de
   'Erro ao salvar.' genérico"). Salvar contrato voltou a devolver mensagem estável;
   a causa real agora vive só no log, achável pelo `request_id` do header. Se o time
   preferir manter o diagnóstico na tela, o caminho compatível é exibir o `request_id`
   no toast de erro do frontend — não voltar a interpolar a exceção.
4. **`overrides` de `postcss`/`sharp`**: o build local passou, mas confirme o primeiro
   build da Vercel. `sharp` está dentro do range que o Next declara; `postcss` está um
   minor acima do pin exato dele.
5. **`X-Forwarded-For`**: os limites por IP só valem enquanto o Railway controlar esse
   header e o backend não for alcançável por um caminho que contorne o proxy. Vale
   confirmar a configuração de rede do Railway. Limiter distribuído fica na Spec 10.
6. **CSP Report-Only sem coletor**: as violações aparecem só no console do navegador —
   não há `report-uri`/`report-to` configurado, porque não existe endpoint para receber.
   Coleta e política bloqueante ficam na Spec 10.
7. **`docudata-frontend/tsconfig.tsbuildinfo` está versionado** e muda a cada build,
   sujando todo diff. Não mexi (fora do escopo), mas vale um `.gitignore`.

## Rollout

1. ✅ Dependências atualizadas e validadas em branch isolada.
2. ✅ Testes e build locais.
3. ⬜ Preview/staging.
4. ⬜ Matriz de regressão nas duas subáreas.
5. ⬜ `API_DOCS_ENABLED=false` na produção.
6. ⬜ Deploy **sem** a Migration v6.
7. ⬜ Medir erros e latência.
8. ⬜ Aplicar índices manualmente, um por vez.

Rollback de código é suficiente. Índices, se criados, podem ficar — são aditivos.
