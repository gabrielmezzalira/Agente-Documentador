# Spec 11 — Terceira subárea: `produto` (e o encaminhamento para `dados`/`dev`)

**Prioridade:** alta · **Depende de:** 03, 04, 05, 06 (já implementadas) · **Bloqueia:** nada (a Spec 12 funciona em qualquer subárea)
**Origem:** integração do Agente Diagnóstico (Discovery Enterprise é da subárea de Produto). Decisão do usuário em 2026-10-12.
**Atenção:** mexe no núcleo de autorização por subárea e convive com a Spec 10 (segurança estrutural). Por isso é uma spec **isolada**, em commits separados da Spec 12.

## Problema

O sistema tem exatamente duas subáreas (`dados`, `dev`), e o `AGENTS.md` §3.2 as trata como invariantes. O Discovery pertence a uma terceira, `produto`,
que **funciona como as outras duas** (mesmo isolamento: projetos, recursos derivados, pasta do Google Drive e template próprios).

A única diferença é o fim do ciclo: quando o Discovery termina, o projeto **sai de Produto e continua em `dados` ou `dev`** — uma **bifurcação** —, e **todo o contexto
do cliente vai junto** (reuniões, transcrições, requisitos, evidências, funcionalidades, documentos). Decisão do usuário em 2026-10-12.

## Escopo

### 1. Migration v8 (SQL entregue ao usuário, **nunca aplicada por agente**)
Bloco **comentado** no `supabase_schema.sql`, padrão do arquivo, idempotente, com preflight somente-leitura:

```sql
-- Preflight (somente leitura): distribuição atual
-- SELECT subarea, count(*) FROM projects GROUP BY subarea ORDER BY 1;
-- SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'projects_subarea_check';

-- Migration v8: subárea produto
-- ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_subarea_check;
-- ALTER TABLE projects ADD CONSTRAINT projects_subarea_check
--   CHECK (subarea IN ('dados','dev','produto'));

-- Migration v8 (parte 2): registro dos encaminhamentos Produto -> Dados/Dev (ver §6)
-- CREATE TABLE IF NOT EXISTS projeto_encaminhamentos (
--   id                       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
--   project_id               uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
--   origem                   text        NOT NULL,
--   destino                  text        NOT NULL,
--   motivo                   text,
--   autor                    text        NOT NULL,
--   requisitos_promovidos    int         NOT NULL DEFAULT 0,
--   created_at               timestamptz NOT NULL DEFAULT now()
-- );
-- CREATE INDEX IF NOT EXISTS idx_encaminhamentos_project ON projeto_encaminhamentos (project_id, created_at DESC);

-- Rollback (só se NENHUM projeto tiver subarea = 'produto'):
-- ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_subarea_check;
-- ALTER TABLE projects ADD CONSTRAINT projects_subarea_check CHECK (subarea IN ('dados','dev'));
-- (a tabela projeto_encaminhamentos é aditiva e pode ficar; remover é decisão sua)
```
Não há dado a migrar: a mudança só **alarga** o conjunto permitido (projetos existentes continuam válidos).

### 2. Backend — um único tipo de subárea
Hoje `Literal["dados", "dev"]` está repetido em `models/schemas.py` (3 vezes), `routers/projects.py` e `routers/search.py`.
Definir **uma vez** `Subarea = Literal["dados", "dev", "produto"]` em `models/schemas.py` e usar nesses cinco pontos
(mudança mínima e necessária; não é refator livre). `ProjectCreate.subarea` continua obrigatório; `produto` passa a ser aceito.

### 3. Backend — GitHub App
`services/github_app.py`: incluir `produto` em `_SUBAREAS_SUPORTADAS` para a seleção de repositórios não falhar em projeto de Produto.
Sem outra mudança.

### 4. Backend — Google Docs/Drive por subárea
`services/google_docs.py` (três funções que hoje ramificam em `dados`/`dev`): para `produto`, derivar **sempre** da subárea carregada no servidor:
- refresh token: `GOOGLE_REFRESH_TOKEN_PRODUTO`;
- pasta: `GDRIVE_FOLDER_ID_PRODUTO`;
- template: override opcional `GDOCS_TEMPLATE_ID_PRODUTO` (e variantes por tipo com sufixo `_PRODUTO`); ausente, reutiliza o equivalente de Dados, **mas o destino continua sendo a pasta de Produto**.
- **Falha segura:** sem `GOOGLE_REFRESH_TOKEN_PRODUTO` ou `GDRIVE_FOLDER_ID_PRODUTO`, o export devolve erro de negócio claro ("Google Drive de Produto não configurado") —
  **nunca** cai silenciosamente na pasta de Dados ou de Dev.
- `get_google_token.py`: aceitar `--produto` (grava o nome `GOOGLE_REFRESH_TOKEN_PRODUTO`), no padrão do `--dev`.
- Atualizar o mapa de variáveis no `GUIDE.md`.

### 5. Frontend
Aceitar `produto` onde hoje se aceita `dados`/`dev`: `app/[subarea]/layout.tsx` (validação do parâmetro), `app/[subarea]/page.tsx` (lista),
`app/[subarea]/projects/new/page.tsx` (criação persiste `subarea=produto`), `app/[subarea]/projects/[id]/page.tsx`, `app/page.tsx` (seletor de subáreas, rótulo "Produto") e
tipos/chamadas em `app/lib/api.ts`. Estilo inline atual; sem biblioteca visual nova. Revisar `SprintDocModal.tsx`, `RetroModal.tsx` e `comparacao-modos/page.tsx` só se dependerem da lista fechada.

### 6. Encaminhamento (bifurcação): Produto → Dados | Dev
O **mesmo** `project_id` muda de subárea; tudo que herda do projeto vai junto (sprints, tasks, funcionalidades, ingestões, documentos, avaliações, repositórios e os dados de Discovery da Spec 12).
Isso é a regra §3.2.8 (mover preserva recursos e histórico) aplicada ao caso de uso real.

- **Rota:** `POST /projects/{id}/encaminhar` com `{destino: "dados"|"dev", motivo?, promover_validados?: bool}`.
- **Regras:** só projeto em `produto` pode ser encaminhado; destino só `dados` ou `dev`. O projeto é **carregado no servidor** e a subárea de origem vem do banco, nunca do corpo.
- **Permissão:** `gerente`+ com acesso ao projeto na origem **e** no destino (§3.2.8). Hoje os cargos não têm escopo por subárea, então o destino é validado pelo cargo; quando a Spec 10 trouxer o escopo por subárea, a mesma checagem passa a valer sem mudar a rota.
- **Atomicidade:** trocar `projects.subarea` e gravar `projeto_encaminhamentos` na mesma operação (RPC/transação, §6.1 do `AGENTS.md`), nunca em sequência vulnerável a falha parcial. Encaminhar para a subárea em que o projeto já está é recusado (409).
- **`promover_validados`:** promove antes de mover os requisitos `validado` ainda sem funcionalidade (reaproveita o serviço de promoção da Spec 12, idempotente) e grava a quantidade em `requisitos_promovidos`.
- **Contexto vai junto:** as tabelas de Discovery são **por projeto, não por subárea**; no destino, `GET /discovery/projetos/{id}/contexto` e a lista de requisitos continuam funcionando com os cargos do destino. A transcrição inteira continua só para `gerente`+.
- **Google Drive/GitHub:** documentos já exportados continuam na pasta de Produto; **novos** exports usam a pasta da subárea de destino (sempre derivada do banco). Vínculos de repositório do GitHub App continuam.
- **Auditoria:** registrar o evento no `audit_log` existente, além da linha em `projeto_encaminhamentos`.
- **Sentido único na v1:** não há retorno ao Produto nem movimento entre `dados` e `dev` por esta rota.
- **Frontend:** botão "Encaminhar para Dados/Dev" na página do projeto de Produto (só `gerente`+), com modal de confirmação (destino, motivo, "promover requisitos validados"); ao concluir, redireciona para `/{destino}/projects/{id}`. A lista de Produto deixa de mostrar o projeto (invariante §3.2.1: cada subárea só vê os seus).

## Não faz parte

- Enforcement de escopo do `lider` por subárea (é a Spec 10; esta spec **não** amplia nem restringe permissões).
- Templates de documento específicos de Produto.
- Retorno de um projeto ao Produto e movimento direto entre `dados` e `dev` (a v1 só encaminha de Produto para fora).
- Decidir se o `arquetipo` muda no destino (hoje fica como está; **DECISÃO EM ABERTO** do time).
- Qualquer mudança de `enrich.py`/`sprint_docs.py`: lá `subarea` é texto livre extraído de documento ("desenvolvimento"/"dados"/"produto"), outro conceito.

## Riscos

- Quebrar a validação de subárea que protege o isolamento (invariante §3.2): teste negativo obrigatório.
- Export caindo na pasta errada (vazamento entre subáreas): falha segura + teste.
- Colidir com a Spec 10 (migration v7 / enforcement): conferir a numeração antes de fechar a v8.

## Ações humanas externas (o agente NÃO faz)

1. Rodar o preflight e depois a migration v8 (constraint e tabela `projeto_encaminhamentos`) no SQL Editor do Supabase.
2. Criar, no Google, a pasta de Produto e gerar o refresh token (`python get_google_token.py --produto`).
3. Definir no Railway: `GOOGLE_REFRESH_TOKEN_PRODUTO`, `GDRIVE_FOLDER_ID_PRODUTO` (e, se quiser, `GDOCS_TEMPLATE_ID_PRODUTO`).
4. Conferir, no deploy do front, que `NEXT_PUBLIC_API_URL` não mudou.

## Testes (mocks; sem banco nem Google reais)

- `POST /projects` com `subarea="produto"` cria; com `"outra"` retorna 422; sem subárea retorna 422.
- `GET /projects?subarea=produto` lista só projetos de Produto; `dados` e `dev` não os veem.
- Encaminhar `produto → dados` e `produto → dev`: o projeto muda de subárea, aparece só na lista do destino, mantém sprints/tasks/funcionalidades/ingestões/documentos e os dados de Discovery; grava `projeto_encaminhamentos` e `audit_log`.
- Encaminhar com `promover_validados`: cria as funcionalidades dos requisitos validados uma única vez; repetir não duplica.
- Recusas: projeto que não está em `produto` (409), destino igual à origem (409), destino `produto` (422), cargo abaixo de `gerente` (403), projeto sem acesso (403/404); falha no meio não deixa subárea trocada sem registro.
- Depois de encaminhar, o contexto de Discovery continua legível por um cargo do destino, e a transcrição só por `gerente`+.
- Export Google: Produto usa as envs `_PRODUTO`; sem elas retorna erro de negócio e **não** chama a pasta de Dados/Dev; Dados e Dev inalterados.
- GitHub App aceita `produto`. `npm run build` verde.

## Critérios de aceite

- [ ] SQL da v8 comentado, idempotente, com preflight e rollback, no `supabase_schema.sql`.
- [ ] Um único `Subarea` usado nos 5 pontos; nenhum `Literal["dados","dev"]` restante.
- [ ] Projeto de Produto criado, listado e acessado pelo front em `/produto/...`.
- [ ] `POST /projects/{id}/encaminhar` move o projeto de Produto para Dados ou Dev **com todo o contexto**, de forma atômica, auditada e só para `gerente`+.
- [ ] Depois do encaminhamento, requisitos, reuniões e contexto de Discovery continuam acessíveis no destino; a lista de Produto não mostra mais o projeto.
- [ ] Export de Produto isolado (envs próprias, falha segura, sem fallback para outra subárea).
- [ ] `python -m pytest` e `npm run build` verdes; `git diff --check` limpo.
- [ ] Gate externo (SQL e envs) reportado como **pendente** até o usuário confirmar; nada declarado "funcionando em produção".
