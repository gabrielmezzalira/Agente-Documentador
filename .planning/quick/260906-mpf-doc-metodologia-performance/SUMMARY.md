---
status: complete
date: 2026-09-06
slug: doc-metodologia-performance
---

## O que foi entregue

Documento de metodologia do Sistema de Acompanhamento de Performance, servido
dentro do DocuData com acesso restrito a Líder e Gerente.

### Arquivos

| Arquivo | Mudança |
|---|---|
| `docudata-backend/docs/metodologia-performance.md` | **novo** — o documento (21 seções + 2 anexos) |
| `docudata-backend/routers/metodologia.py` | **novo** — `GET /metodologia/{slug}` servindo o markdown |
| `docudata-backend/models/schemas.py` | `MetodologiaResponse` |
| `docudata-backend/main.py` | router registrado com `require_not_operacional` |
| `docudata-backend/tests/test_metodologia_rbac.py` | **novo** — 5 testes de gate e conteúdo |
| `docudata-frontend/app/metodologia/page.tsx` | **novo** — página com markdown estilizado |
| `docudata-frontend/app/lib/api.ts` | `getMetodologia(slug)` |
| `docudata-frontend/app/page.tsx` | link "Metodologia" no header para não-operacional |
| `docudata-frontend/package.json` | `remark-gfm@^4` — react-markdown v9 não renderiza tabelas GFM sem ele, e o documento é majoritariamente tabelas |

### Conteúdo do documento

Descreve o sistema **como implementado**, não como idealizado: fórmulas exatas
das 5 dimensões, renormalização por peso disponível, arquitetura em 4 camadas,
mecânica de fechamento (cutoff, idempotência, eventos tardios), janelas por
contagem de sprint, guard-rails anti-gaming, manual do gerente passo a passo,
tabela de erros do sistema, casos de borda e referência técnica.

O **Anexo B** registra 11 divergências entre a metodologia de referência escrita
pelo Líder e o que o código faz hoje (pesos iguais entre arquétipos, CSAT não
coletado, colaboração valendo 5%, Evolução sem uso da baseline, etc.) — para que
o texto de referência não seja lido como especificação do sistema.

### Verificação

- `pytest tests/test_metodologia_rbac.py` — 5 passed
- `pytest` (suíte completa) — 194 passed, 4 failed
  - as 4 falhas são **pré-existentes** (`test_schemas_and_client.py` afirma que
    `ConteudoEstruturado` tem 6 campos; o schema tem 8 desde a Phase de
    tecnologias). Confirmado com `git stash` das mudanças desta task.
- `npm run build` — compilado, rota `/metodologia` gerada

### Fora de escopo (não feito)

- Nenhuma fórmula, peso ou regra do motor de score foi alterada.
- Nenhuma migração de banco — esta task não toca schema do Supabase.
