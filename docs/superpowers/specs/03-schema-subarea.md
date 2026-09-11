# Spec 03 — Coluna `subarea` em `projects`

**Prioridade:** alta · **Depende de:** nada · **Bloqueia:** 04, 05, 06

## Problema

Hoje `projects` não distingue Dados de Dev. Esta spec só adiciona o campo e o fio
elétrico básico (schema + validação) — a filtragem de fato é a spec 05, e o frontend
é a spec 06. Objetivo aqui é só ter o dado existindo e sendo aceito/validado de ponta
a ponta sem quebrar nada que já existe.

## Escopo

### 1. Migration SQL

Adicione ao final de `docudata-backend/supabase_schema.sql` um bloco novo seguindo o
padrão que já existe no arquivo (blocos de migration comentados, numerados):

```sql
-- Migration v3: subárea do projeto (dados | dev)
-- ALTER TABLE projects ADD COLUMN IF NOT EXISTS subarea text NOT NULL DEFAULT 'dados';
-- ALTER TABLE projects ADD CONSTRAINT projects_subarea_check
--   CHECK (subarea IN ('dados','dev'));
```

Essa migration **não roda sozinha** — é SQL que uma pessoa cola manualmente no
SQL Editor do Supabase (é assim que o resto do arquivo já funciona, mantenha o
padrão). Não tente rodar isso via código Python/`supabase-py` — sem client de
migration configurado no projeto, isso teria que ser feito manualmente de qualquer
forma.

### 2. Backend — schemas

Em `models/schemas.py`:
- `ProjectCreate` ganha `subarea: Literal["dados", "dev"]` (obrigatório — o único
  cliente é nosso próprio frontend, que a partir da spec 06 sempre vai mandar isso).
- `ProjectResponse` ganha `subarea: str`.

### 3. Backend — router

Em `routers/projects.py`:
- `create_project` passa `subarea` no `payload` do insert.
- `_sanitize` não precisa mudar (subarea não é segredo, continua no retorno normal).

### 4. Não filtrar ainda

**Não implemente filtro de listagem por subárea nesta spec** — isso é a spec 05, de
propósito separada pra manter o diff pequeno e revisável. Nesta spec, `GET /projects`
continua devolvendo tudo, só que agora cada item tem o campo `subarea` no JSON.

## Critérios de aceite

- [ ] SQL do migration está no `supabase_schema.sql`, comentado, seguindo o padrão
      dos blocos anteriores do arquivo.
- [ ] `POST /projects` sem `subarea` no body retorna `422` (campo obrigatório).
- [ ] `POST /projects` com `subarea: "dev"` ou `"dados"` cria normalmente e o
      registro retornado tem o campo.
- [ ] `POST /projects` com `subarea: "outraCoisa"` retorna `422` (fora do enum).
- [ ] `GET /projects` e `GET /projects/{id}` incluem `subarea` na resposta.
- [ ] Projetos criados **antes** desta migration (que não tinham a coluna) aparecem
      com `subarea: "dados"` depois do `ALTER ... DEFAULT 'dados'` — confirme isso
      rodando a migration em um ambiente com dados de teste antes de aplicar em
      produção.
- [ ] `pytest` passa, incluindo um teste novo cobrindo os três casos de validação
      acima (adicione em `tests/`, seguindo o padrão de mock já usado em
      `test_project_usage.py`).

## Como testar manualmente

```bash
# roda a migration manualmente no SQL Editor do Supabase antes de testar

curl -s -X POST http://localhost:8000/projects \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" -H "Content-Type: application/json" \
  -d '{"name":"Projeto Dev Teste","client":"CITi","subarea":"dev"}' | python3 -m json.tool
# esperado: 201, corpo tem "subarea": "dev"

curl -s -X POST http://localhost:8000/projects \
  -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" -H "Content-Type: application/json" \
  -d '{"name":"Projeto Sem Subarea","client":"CITi"}' -w "\n%{http_code}\n"
# esperado: 422
```

## ⚠️ Nota operacional (leia antes de rodar em produção)

Como não temos ferramenta de migration automatizada, quem for aplicar isso em
produção precisa: (1) rodar o SQL manualmente no Supabase da subárea de Dados
existente, (2) confirmar que os projetos atuais ficaram com `subarea='dados'`,
(3) só então fazer deploy do backend com essa spec. Se o deploy do backend subir
**antes** da coluna existir no banco, todo `INSERT`/`SELECT` que toque `subarea`
vai falhar. Ordem importa aqui: banco primeiro, código depois.
