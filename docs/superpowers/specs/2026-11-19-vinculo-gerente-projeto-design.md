# Vínculo gerente ↔ projeto e acesso por projeto

Data: 2026-11-19 · Pedido do usuário: "eu quero ter uma forma de vincular os gerentes ao projeto, e eles só têm acesso aos projetos que têm vínculo; a pessoa que cria um projeto vira automaticamente vinculada a ele, como gerente" e "o gerente só pode ver coisas relacionadas ao seu projeto, incluindo histórico de avaliações dos seus operacionais".

## Decisões do usuário

| Tema | Decisão |
|---|---|
| Owner e Líder | Veem e editam todos os projetos (sem mudança). |
| Gerente | Só acessa projetos em que está vinculado — inclusive telas gerais (lista de projetos, busca, histórico de avaliações). |
| Operacional | Continua restrito aos projetos em que está em `operacionais` (por e-mail). A varredura fecha as rotas que hoje não conferem projeto. |
| Projetos existentes | Vincula pelo `projects.gerente_email` ("Lembretes por email") quando esse e-mail é de uma pessoa com cargo `gerente`. Sem e-mail, o projeto fica sem gerente até um líder vincular. |
| Quem vincula | Líder/Owner em qualquer projeto; gerente vinculado no próprio projeto. |
| Criar projeto | Quem cria vira vinculado na hora. |

## Decisões tomadas por mim (rulings)

- **Sem acesso = 403** com o detalhe atual "Você não tem acesso a este projeto" (mesmo comportamento que o operacional já tem e que os testes atuais esperam). Rotas que já respondem 404 para esconder existência (discovery) mantêm 404.
- **Chave do Gemini** (`/settings/gemini*`) passa a ser só Líder/Owner — não é dado de projeto.
- **Antes da migração v16**: se a tabela `projeto_gerentes` não existir, o gerente é tratado como hoje (vê tudo) e o backend registra um aviso no log. O deploy não tranca ninguém antes do usuário rodar o SQL.
- Não dá para remover o **último** gerente de um projeto (409).
- Só pessoas com cargo `gerente`, `lider` ou `owner` podem ser vinculadas.

## Dados

Tabela nova (migração v16):

```sql
CREATE TABLE IF NOT EXISTS projeto_gerentes (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    pessoa_id   uuid NOT NULL REFERENCES pessoa(id) ON DELETE CASCADE,
    criado_por  uuid REFERENCES pessoa(id) ON DELETE SET NULL,
    criado_em   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, pessoa_id)
);
-- backfill pelo e-mail de lembrete
INSERT INTO projeto_gerentes (project_id, pessoa_id)
SELECT p.id, pe.id FROM projects p JOIN pessoa pe ON lower(pe.email) = lower(p.gerente_email)
WHERE pe.cargo = 'gerente'
ON CONFLICT (project_id, pessoa_id) DO NOTHING;
```

## Arquitetura

`services/acesso.py` (novo) concentra a regra:

- `projetos_visiveis(client, pessoa) -> set[str] | None` — `None` = todos (owner/líder, ou gerente com a tabela ausente); gerente = ids em `projeto_gerentes`; operacional = ids em `operacionais` com o e-mail dele.
- `tem_acesso(client, pessoa, project_id) -> bool`.
- `exigir_acesso(client, pessoa, project_id) -> None` — levanta 403 "Você não tem acesso a este projeto".
- Resolvedores `project_id_de_<entidade>(client, id) -> str` que levantam 404 quando o objeto não existe: task, sprint, funcionalidade, sprint_funcionalidade, generated_doc, ingestion, avaliacao, proposta, solicitacao, sugestao, operacional.
- `exigir_acesso_por(client, pessoa, entidade, id) -> str` = resolver + exigir, devolve o project_id.

`services/auth.require_project_access` passa a delegar para `exigir_acesso` (mesma assinatura; continua usável como dependência e inline).

## Rotas

Toda rota que lê ou escreve dado de um projeto confere acesso — pela dependência `require_project_access` quando o `project_id` vem no path/query, ou inline com `exigir_acesso`/`exigir_acesso_por` quando vem no body, Form ou é resolvido por outro id. O inventário completo está no plano. Rotas só de líder (acompanhamento, classificador, performance, pessoas, metas) e de máquina (commit/revisão/discovery ingest, webhook, callback GitHub) não mudam.

Listas que cruzam projetos filtram por `projetos_visiveis`:
- `GET /projects` (gerente e operacional).
- `GET /search`.
- `GET /avaliacoes/historico` (sem filtro, devolve só avaliações de sprints dos projetos visíveis; com `project_id`/`sprint_id` de fora, 403).
- `PATCH /tasks/reordenar/batch` (cada task precisa ser de projeto visível).

Vínculos (novo, em `routers/projects.py`):
- `GET /projects/{id}/gerentes` — lista vinculados (nome, e-mail, criado_em). Quem acessa o projeto.
- `GET /projects/{id}/gerentes/candidatos` — pessoas com cargo gerente/lider/owner ainda não vinculadas. Quem pode gerenciar.
- `POST /projects/{id}/gerentes` `{pessoa_id}` — vincula. Líder/Owner ou gerente vinculado.
- `DELETE /projects/{id}/gerentes/{pessoa_id}` — desvincula; 409 se for o último.
- `POST /projects` grava o criador em `projeto_gerentes` (best-effort se a tabela não existir).

## Frontend

- Configurações do projeto: seção "Gerentes do projeto" (lista, adicionar a partir dos candidatos, remover; botão de remover some quando só há um).
- Página do projeto: 403 mostra "Você não tem acesso a este projeto" em vez de erro genérico.
- Lista e busca já vêm filtradas do backend.

## Testes

Para cada grupo de rotas: gerente vinculado passa, gerente não vinculado 403, operacional de fora 403, líder passa. Serviço `acesso`: tabela ausente libera gerente; backfill não duplica; não remove último gerente; criar projeto vincula criador.

## Fora do escopo

RLS no Supabase; mudanças nas telas só de líder; e-mails de lembrete (seguem usando `gerente_email`).
