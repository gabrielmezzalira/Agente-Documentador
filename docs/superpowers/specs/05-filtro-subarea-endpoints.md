# Spec 05 — Filtrar projetos e busca por subárea

**Prioridade:** alta · **Depende de:** 03 · **Bloqueia:** 06

## Problema

`GET /projects` e `GET /search` hoje devolvem/consideram projetos das duas subáreas
misturados. Com `subarea` já existindo no schema (spec 03), falta o filtro de fato.

## Escopo

### 1. `GET /projects`

Em `routers/projects.py`, endpoint `list_projects`:
- Novo query param **obrigatório**: `subarea: Literal["dados", "dev"]`.
- Sem o param → `422` (não devolva tudo por padrão; force o cliente a ser explícito,
  evita o bug de "esqueci o filtro e vazou projeto da outra subárea na tela errada").
- Aplique `.eq("subarea", subarea)` na query do Supabase.
- A lógica de `last_ingestion_at` (que hoje busca ingestions de todos os projetos e
  depois cruza) deve continuar funcionando igual, só que agora sobre o conjunto já
  filtrado.

### 2. `GET /search`

Em `routers/search.py`, endpoint `search_stack`:
- Novo query param **obrigatório**: `subarea: Literal["dados", "dev"]`.
- A query que hoje busca ingestions "de todos os projetos" (`.select(...)` sem filtro)
  precisa passar a considerar só projetos da subárea pedida. Como `ingestions` não
  tem `subarea` direto (só `projects` tem), a forma mais simples é: primeiro buscar
  os `id`s de `projects` daquela subárea, depois filtrar as ingestions com
  `.in_("project_id", ids)` — siga o mesmo padrão que `search.py` já usa pra
  `.in_("id", list(project_sprints.keys()))` no fim da função, só que invertendo a
  ordem das buscas.

### 3. Endpoints que NÃO mudam nesta spec

Todo endpoint que já opera a partir de um `project_id` conhecido (ingestions,
generate, sprints, docs, cost, usage, technologies) **não precisa de filtro de
subárea** — o `project_id` já ancora a subárea implicitamente. Não adicione
`subarea` como parâmetro nesses endpoints; seria redundante e é uma superfície a
mais pra manter sincronizada à toa.

## Critérios de aceite

- [ ] `GET /projects` sem `?subarea=` retorna `422`.
- [ ] `GET /projects?subarea=dev` só retorna projetos com `subarea='dev'`.
- [ ] `GET /projects?subarea=dados` só retorna projetos com `subarea='dados'`.
- [ ] `GET /projects?subarea=lixo` retorna `422` (fora do enum).
- [ ] `GET /search?q=python&subarea=dev` só considera ingestions de projetos `dev`
      no resultado, mesmo que exista uma ingestion idêntica em um projeto `dados`.
- [ ] `pytest` passa, com teste novo cobrindo o filtro de `/projects` (mock de dois
      projetos, subáreas diferentes, confirma que o filtro separa certo).

## Como testar manualmente

```bash
curl -s "http://localhost:8000/projects?subarea=dev" -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" | python3 -m json.tool
curl -s "http://localhost:8000/projects?subarea=dados" -H "X-Docudata-Key: $DOCUDATA_APP_SECRET" | python3 -m json.tool
curl -i "http://localhost:8000/projects" -H "X-Docudata-Key: $DOCUDATA_APP_SECRET"
# esperado: 422 (sem subarea)
```
