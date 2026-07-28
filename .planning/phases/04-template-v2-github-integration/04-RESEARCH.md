# Phase 4 Research: Template v2 + GitHub Integration

**Phase:** 4 — Template v2 + GitHub Integration
**Date:** 2026-07-27
**Status:** Complete

---

## Executive Summary

Phase 4 tem três frentes distintas: (a) completar o preenchimento dos placeholders dos templates Google Docs com dados estruturados reais, (b) adicionar novos campos nos modais de Planning e Review do frontend, e (c) criar integração com GitHub via commit hook. O codebase já tem a infraestrutura base para tudo — as adições são incrementais.

---

## Gap Analysis: O que já existe vs o que falta

### Template Export (google_docs.py)

**Já implementado:**
- `_clone_template()` — clona template DOCX e converte para Google Doc nativo
- `_replace_placeholders()` — substitui `{{CAMPO}}` via Docs API
- `_SECTION_PLACEHOLDERS` — mapeia headers markdown → placeholders (planning: BACKLOG, RISCOS; review: PLANEJADO, REALIZADO, DELTA, DECISOES, IMPEDIMENTOS, APRENDIZADOS, ITENS_PROXIMA_SPRINT; retrospectiva: O_QUE_FUNCIONOU, O_QUE_NAO_FUNCIONOU, CAUSA_RAIZ, ACOES_MELHORIA, PEDIDO_FORA_ESCOPO)
- `_TEMPLATE_ENV_BY_DOC_TYPE` — IDs de template por tipo
- SQUAD e PERIODO já chamados no `_replace_placeholders()` mas hardcoded como `"[A definir]"`

**Faltando:**
| Placeholder | Tipo doc | Status atual | Fix |
|---|---|---|---|
| `{{SQUAD}}` | planning | `"[A definir]"` | Ler `campos_planning.squad` do JSONB |
| `{{PERIODO}}` | planning | `"[A definir]"` | Ler `campos_planning.periodo_inicio` + `periodo_fim` |
| `{{HORAS_ESTIMADAS}}` | planning | Não mapeado | Ler `campos_planning.horas_estimadas` |
| `{{HORAS_REAIS}}` | planning | Não mapeado | Ler `campos_planning.horas_reais` ou blank |
| `{{DEPENDENCIAS_CLIENTE}}` | planning | Não mapeado | Ler `campos_planning.dependencias_cliente` |
| `{{CARRY_OVER}}` | planning | Não mapeado | A decidir (ver open questions) |
| `{{PLANEJADO_ENTREGUE}}` | review | Nome diverge de `PLANEJADO` atual | Renomear mapping |
| `{{PERCEPCAO_CLIENTE}}` | review | Não mapeado | Ler `campos_review.percepcao_cliente` |
| `{{SINAL_SATISFACAO}}` | review | Não mapeado | Ler `campos_review.sinal_satisfacao` |
| `{{PEDIDOS_FORA_ESCOPO}}` | review | Não mapeado | Ler `campos_review.pedidos_fora_escopo` |
| `{{CAUSA_RAIZ_IMPACTO}}` | retrospectiva | Mapeado como `CAUSA_RAIZ` | Renomear |
| `{{PEDIDO_FORA_ESCOPO_STATUS}}` | retrospectiva | Mapeado como `PEDIDO_FORA_ESCOPO` | Renomear |

### Banco de Dados

**Já existe:**
- `ingestions.extracted_content` JSONB — suporta sub-dicts (padrão já usado em `sprint_docs.py` com `campos_daily`, `campos_planning`, `campos_review`)
- `ingestions.tipo_documentacao` — CHECK constraint: `('planning','daily','review','outro')`

**Faltando:**
- Adicionar `'commit'` ao CHECK constraint do `tipo_documentacao`
- Nenhuma nova coluna necessária — todos os campos novos entram no JSONB existente

### Frontend (SprintDocModal)

**Já existe:**
- `SprintDocModal` — modal de criação de Sprint Docs com campos básicos (backlog, riscos)
- Campos de Planning: `backlog_items` (lista), `riscos`
- Campos de Review: `o_que_foi_planejado`, `o_que_foi_realizado`, `delta`, `decisoes`, `impedimentos`, `aprendizados`, `itens_proxima_sprint`
- Campos de Retrospectiva: `o_que_funcionou`, `o_que_nao_funcionou`, `causa_raiz`, `acoes_melhoria`, `pedido_fora_escopo`

**Faltando no modal de Planning:**
- Squad (text input)
- Período: início + fim (date inputs)
- Horas disponíveis / estimadas (number inputs)
- Dependências do cliente (textarea)
- Carry-over (ver open questions)

**Faltando no modal de Review:**
- Percepção do cliente (textarea)
- Sinal de satisfação (select dropdown — 6 opções a confirmar)
- Pedidos fora do escopo (textarea)

### Backend — Routers

**Já existe:**
- `POST /sprint-docs` em `sprint_docs.py` — cria sprint doc com `campos_planning`, `campos_daily`, `campos_review`
- `POST /docs/{doc_id}/export-gdocs` — exporta para Google Docs

**Faltando:**
- `POST /ingest/commit` — novo endpoint para receber payload do git hook

---

## Estratégia de Implementação

### Novos campos estruturados (FORM-01, FORM-02)

Os novos campos seguem exatamente o padrão `campos_*` já estabelecido em `sprint_docs.py`. O modal coleta, o frontend envia JSON, o backend armazena no `extracted_content` JSONB sob as chaves `campos_planning` e `campos_review`.

```json
// campos_planning (extensão do atual)
{
  "squad": "Backend",
  "periodo_inicio": "2026-07-14",
  "periodo_fim": "2026-07-28",
  "horas_disponiveis": 40,
  "horas_estimadas": 35,
  "dependencias_cliente": "Acesso ao banco de dados de produção"
}

// campos_review (extensão do atual)
{
  "percepcao_cliente": "Cliente satisfeito com a velocidade de entrega",
  "sinal_satisfacao": "Verde",
  "pedidos_fora_escopo": "Adicionar relatório PDF"
}
```

### Template filling (TMPL-01, TMPL-02, TMPL-03)

A função `export_to_gdocs()` recebe `doc_id` e faz query no Supabase para buscar a ingestion de planning/review da sprint. Os campos estruturados são lidos do JSONB e passados para `_replace_placeholders()`.

Fluxo:
1. `export_to_gdocs()` recebe `sprint_numero` e `project_id`
2. Query: `ingestions WHERE project_id=X AND sprint_number=N AND tipo_documentacao='planning'` (ou `review`)
3. Extrai `extracted_content.campos_planning` (ou `campos_review`)
4. Monta dict de replacements com os novos campos + os existentes
5. Chama `_replace_placeholders()` com o dict completo

### GitHub Integration (GH-01, GH-02)

**Script do hook** (instalado localmente pelo gerente, não no servidor):

```bash
#!/bin/bash
# .git/hooks/post-commit
# Envia mudanças com [docudata] para o DocuData
COMMIT_MSG=$(git log -1 --pretty=%B)
if echo "$COMMIT_MSG" | grep -q "\[docudata\]"; then
  PAYLOAD=$(git log -1 --pretty=format:'{"hash":"%H","message":"%s","author":"%an","date":"%ai"}')
  DIFF=$(git diff HEAD~1 HEAD --stat)
  curl -s -X POST "$DOCUDATA_API_URL/ingest/commit" \
    -H "Content-Type: application/json" \
    -d "{\"project_id\":\"$DOCUDATA_PROJECT_ID\",\"sprint_number\":$DOCUDATA_SPRINT,\"commit\":$PAYLOAD,\"diff_stat\":\"$DIFF\"}"
fi
```

**Endpoint `POST /ingest/commit`** no backend:
- Recebe: `project_id`, `sprint_number`, `commit` (hash, message, author, date), `diff_stat`
- Usa Gemini para extrair `extracted_content` do conteúdo do commit: mudança, decisão, tecnologias, impacto no backlog
- Salva ingestion com `tipo_documentacao='commit'`, `file_name=f"commit:{hash[:7]}"`, `file_type='commit'`
- Retorna `{"id": uuid}` — sem corpo de resposta longo

---

## Decisões de Implementação

| Decisão | Escolha | Razão |
|---|---|---|
| Armazenamento de novos campos | JSONB existente (`campos_planning`/`campos_review`) | Padrão já estabelecido em sprint_docs.py; zero migração |
| `tipo_documentacao='commit'` | CHECK constraint update | Mantém integridade sem nova coluna |
| Export busca campos estruturados | Query na ingestion da sprint | Dados já existem no DB; sem duplicação |
| Sinal de satisfação | Dropdown select no frontend | 6 opções fixas (a confirmar com gerente) |
| Script do hook | Bash script simples | Portátil, sem dependências, gerente instala localmente |

---

## Open Questions (RESOLVED)

1. **CARRY_OVER**: Qual a estratégia? **RESOLVED → (A)+(B) híbrido**: campo manual no modal + pré-preenchido automaticamente com `proximos_passos` da ingestion de review da sprint anterior. Plan 04-02 Task 5 implementa o `fetchCarryOver`.

2. **Sinal de Satisfação**: Quais são as opções exatas do padrão CITi? **RESOLVED → 3 opções**: 🟢 Verde / 🟡 Amarelo / 🔴 Vermelho (padrão semáforo de gestão de projetos). ROADMAP SC5 atualizado de "6 opções" para "3 opções". Plan 04-02 Task 3 implementa o select com essas 3 opções.

3. **HORAS_REAIS no export de Planning**: **RESOLVED → (A)**: `horas_disponiveis` (capacidade do squad na sprint) é mapeado para `{{HORAS_REAIS}}` no export. Semanticamente: no contexto de Planning, "horas reais disponíveis" = capacidade planejada, não horas trabalhadas. Plan 04-03 Task 3 implementa.

4. **PEDIDO_FORA_ESCOPO_STATUS na Retrospectiva**: **RESOLVED → campo novo no modal de Retro**: Plan 04-01 Task 4 cria o endpoint com `campos_retrospectiva.pedido_fora_escopo_status`. Plan 04-02 Task 4 adiciona o campo no RetroModal. O preenchimento no export vem do `_SECTION_PLACEHOLDERS` (mapping de seção no markdown gerado).

---

## Confidence Assessment

| Área | Nível | Razão |
|---|---|---|
| Gap analysis de templates | HIGH | Inspeção direta do código |
| Estratégia DB (JSONB sem migração) | HIGH | Padrão campos_* já confirmado |
| Frontend modal additions | HIGH | SprintDocModal lido; campos são incrementais |
| GitHub hook arquitetura | HIGH | Padrão bash + curl bem estabelecido |
| Endpoint /ingest/commit | HIGH | Segue padrão de ingest existente |
| Sinal de Satisfação opções | LOW | Não documentado no codebase ou projeto |
| Nomes exatos dos placeholders | MEDIUM | Depende do template real no Google Docs |
