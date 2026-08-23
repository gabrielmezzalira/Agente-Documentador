# Phase 9: Revisor Diário Generalizado - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-22
**Phase:** 9-Revisor Diário Generalizado
**Areas discussed:** Trigger do revisor, Janela de análise, Schema de RevisaoDiaria e Bloco B, Entrega dos relatórios

---

## Trigger do Revisor

| Option | Description | Selected |
|--------|-------------|----------|
| Cron diário | GitHub Actions schedule — um relatório por dia, previsível e auditável | ✓ |
| A cada push | Igual ao commit tracker; gera muitos registros por dia | |
| Cron + dispatch manual | Cron padrão + gerente pode disparar manualmente | |

**Horário:** 08:00 UTC (05:00 BRT) — relatório do dia anterior pronto quando o time chegar.

**Sem commits → para silenciosamente:** Nenhum registro criado se não houve commits nas últimas 24h.

---

## Janela de Análise

| Option | Description | Selected |
|--------|-------------|----------|
| Diff acumulado das últimas 24h | Mesma abordagem do commit tracker, agregada. Funciona com qualquer projeto | ✓ |
| Full file (arquivos modificados) | Mais contexto, custo maior | |
| Diff + arquivos de teste | Melhor para bugs, requer cobertura de testes | |

**User's choice:** Diff das 24h. Quando questionado sobre "qual melhor formato pra detectar bug?", Claude explicou os tradeoffs: diff+testes é mais preciso mas depende de cobertura; diff acumulado é mais confiável universalmente.

**Limite do diff:** 100k chars (vs 8k do commit tracker atual). Usuário identificou que o limite atual estava pequeno para o uso diário agregado.

---

## Schema de RevisaoDiaria e Bloco B

| Option | Description | Selected |
|--------|-------------|----------|
| Severidade + confiança + arquivo:linha + duas descrições | Schema estruturado; permite filtrar CRITICA+ALTA no Bloco B | ✓ |
| Apenas descrição livre | Mais simples, mas sem filtro de severidade | |

**Usuário pediu clarificação sobre "achado"** — explicado com exemplo concreto (IndexError potencial, com versão técnica e gerente lado a lado). Confirmou a estrutura.

**Bloco B:** Expandir endpoint `/painel` existente com `achados_criticos` — sem endpoint separado.

---

## Entrega dos Relatórios

| Option | Description | Selected |
|--------|-------------|----------|
| Só no DocuData | Simples, sem integração GitHub adicional | ✓ |
| DocuData + job summary | Relatório técnico no GitHub Actions tab | |
| DocuData + issue comment | Histórico no GitHub | |

**Usuário pediu clarificação sobre as duas versões** — explicado com exemplos de "versão gerente" (macro, sem arquivo:linha) vs "versão técnica" (com arquivo:linha). Confirmou manter as duas.

**Acesso no frontend:** toggle/abas no PainelTab.tsx para alternar entre versões. Padrão: versão gerente.

---

## Claude's Discretion

- Horário configurável no YML (padrão 08:00 UTC)
- Cap de 20 achados por RevisaoDiaria (prioridade CRITICA > ALTA > MEDIA > BAIXA)
- Endpoint: `POST /ingest/revisao`
- Agente Python sem dependências externas (só stdlib), mesma convenção do commit tracker

## Deferred Ideas

- Notificação por email/Slack além do Painel
- `.citi/revisao.yml` como arquivo de configuração separado
- Histórico paginado de todas as RevisaoDiaria no Painel
- Filtro de severidade configurável pelo gerente
