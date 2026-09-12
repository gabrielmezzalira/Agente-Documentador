---
phase: remover-trilha-acompanhamento-cliente
plan: quick-260912-lwl
subsystem: painel-e-acompanhamento
tags: [remocao-codigo-morto, bugfix, painel, boletins, documentacao]
status: complete

requires:
  - "docudata-backend/routers/painel.py — calcular_bloco_a / calcular_bloco_b"
  - "docudata-backend/models/schemas.py — FuncionalidadeUpdate / FuncionalidadeResponse"
provides:
  - "Alarme de desvio do Painel medindo entrega real (prazo consumido − escopo concluído)"
  - "Back-end sem a trilha de acompanhamento do cliente"
  - "tests/test_painel_desvio_escopo.py — cobertura automatizada da fórmula de desvio"
affects:
  - "GET /projects/{id}/painel — resposta perde a chave cobertura_aceite; bloco_a perde pct_aprovado_cliente; bloco_b perde aguardando_cliente, em_ajuste e funcionalidades_com_aceite_falhando"
  - "PATCH /funcionalidades/{id} — não aceita mais status_cliente, data_aprovacao_cliente nem testes_e2e"
  - "POST /boletins (removido), GET /boletins/{project_id} (removido), PATCH /boletins/{id} (removido)"
  - "POST /aceite/* — router inteiro removido"

tech-stack:
  added: []
  patterns:
    - "Colunas e tabelas órfãs mantidas no banco com comentário SQL em vez de migração destrutiva"

key-files:
  created:
    - docudata-backend/tests/test_painel_desvio_escopo.py
  modified:
    - docudata-backend/routers/painel.py
    - docudata-backend/routers/boletins.py
    - docudata-backend/routers/funcionalidades.py
    - docudata-backend/models/schemas.py
    - docudata-backend/main.py
    - docudata-backend/supabase_schema.sql
    - docudata-frontend/app/lib/api.ts
    - RELATORIO-DOCUDATA.md
  deleted:
    - docudata-backend/routers/aceite_ingest.py
    - docudata-backend/hooks/aceite_agent.py
    - docudata-backend/hooks/aceite.yml

decisions:
  - "Desvio do Painel = pct_prazo_consumido − pct_escopo_concluido; tolerancia_desvio_pontos segue sendo o corte de desvio_detectado"
  - "Banco intocado: nenhuma migração destrutiva; colunas e tabelas ficam órfãs com comentário SQL marcando o estado"
  - "Prefixo de rota /boletins e o nome do arquivo boletins.py preservados porque o frontend chama esse caminho"

metrics:
  duration: "~35min"
  completed: 2026-09-12

actuals:
  tokens: 31000
  tasks: 3
  commits: 3
---

# Quick Task 260912-lwl: Remover a trilha de acompanhamento do cliente — Summary

Removida do código a trilha inteira de acompanhamento do cliente (status paralelo com o cliente, data de aprovação, testes e2e, boletim de aceite e suíte de verificação de aceite via CI) e corrigido o alarme de desvio do Painel, que passa a comparar prazo consumido com escopo **concluído** em vez de um campo que nenhuma tela nunca preencheu.

## O que mudou

### Task 1 — Painel mede entrega real (`12f2ec6`)

`calcular_bloco_a` calculava `desvio = pct_prazo_consumido − pct_aprovado_cliente`. Como `pct_aprovado_cliente` derivava de `funcionalidades.status_cliente`, campo sem nenhuma interface que o escrevesse, ele era permanentemente 0 — logo **todo projeto acusava desvio assim que passava da tolerância do calendário**, independentemente de quanto o time tinha entregue. A fórmula passa a ser `pct_prazo_consumido − pct_escopo_concluido`, e `pct_escopo_concluido` vem de `funcionalidades.status`, esse sim editável na aba Planejamento.

`calcular_bloco_b` perdeu o quarto parâmetro (execuções da suíte de CI); a assinatura ficou `(funcs, transicoes, revisao_recente=None)`. Saíram do retorno `aguardando_cliente`, `em_ajuste` e `funcionalidades_com_aceite_falhando`. `_calcular_cobertura_aceite` foi apagada inteira e a chave `cobertura_aceite` saiu da resposta de `GET /projects/{id}/painel`.

`routers/boletins.py` ficou com uma única rota — `POST /boletins/resumo_semanal` — sob o mesmo prefixo e no mesmo arquivo, porque o frontend chama esse caminho. O markdown gerado perdeu as seções "Aguardando Cliente" e "Concluídas com Suíte Falhando" e a linha de escopo aprovado na "Leitura Tempo × Escopo".

5 testes novos em `tests/test_painel_desvio_escopo.py` exercitam `calcular_bloco_a` como função pura, sem Supabase nem mock. O terceiro deles (50% do prazo, 100% do escopo, tolerância 0 → desvio −50.0 e `desvio_detectado is False`) falhava na implementação antiga com +50.0 e `True` — é a prova do conserto.

### Task 2 — Suíte de aceite e campos de cliente fora do back-end (`208d9c4`)

Deletados `routers/aceite_ingest.py`, `hooks/aceite_agent.py` e `hooks/aceite.yml`. As outras duas integrações de GitHub (`docudata_agent.py`/`docudata.yml` e `revisor_agent.py`/`revisor.yml`) ficaram intactas.

`main.py` desregistrou o router de aceite; as outras 25 registrações continuam com as mesmas dependências de auth.

`funcionalidades.py` perdeu `dispatch_aceite_background` inteira, o agendamento em background no PATCH, o parâmetro `BackgroundTasks` e os imports que ficaram sem uso (`subprocess`, `urllib.error`, `urllib.request`, `date`). Os dois laços `for campo in ("status", "status_cliente")` passaram a iterar só sobre `("status",)`; saíram o bloco de `testes_e2e` e o auto-preenchimento de `data_aprovacao_cliente`.

`schemas.py` perdeu os três campos de cliente de `FuncionalidadeUpdate` e `FuncionalidadeResponse` e as classes `ExecucaoAceitePayload`, `ExecucaoAceiteResponse`, `BoletimCreate`, `BoletimPatch` e `BoletimResponse`.

### Task 3 — Tipos do frontend e relatório funcional (`eb6ce98`)

`app/lib/api.ts` perdeu 5 declarações órfãs (nenhum `.tsx` as lia): `status_cliente` e `data_aprovacao_cliente` de `FuncionalidadeResponse`, `pct_aprovado_cliente` de `BlocoA`, `aguardando_cliente` de `BlocoB`, `cobertura_aceite` de `PainelData`.

`RELATORIO-DOCUDATA.md` teve as seções 5, 10, 14 e 17 reescritas. A seção 17 deixou de ser "a maior lacuna do sistema" e virou registro histórico curto da remoção; a seção 14 passou de três para duas integrações de GitHub; a seção 10 descreve o alarme de desvio como funcional.

## O que ficou intocado (por decisão explícita)

- **Banco de dados.** Zero `DROP`, `ALTER` ou `DELETE` — nem comentados. `supabase_schema.sql` recebeu apenas 13 linhas de comentário SQL marcando que `status_cliente`, `data_aprovacao_cliente`, `testes_e2e`, `execucoes_aceite` e `boletins_aceite` ficaram órfãos de propósito. Reverter os commits restaura o código sem nenhuma perda de dado.
- **`POST /boletins/resumo_semanal`**, o arquivo `boletins.py` e o prefixo `/boletins` — em uso pela UI.
- **`criterios_aceite`** — critério de aceite da entrega, editado na `EscopoTab.tsx`.
- **`em_ajuste` no Bloco C** — `calcular_bloco_c` continua contando WIP com `status in ("em_andamento", "em_ajuste")`.
- **Tabela `transicoes_status`** e as transições do campo `status`.

## Deviations from Plan

### 1. [Rule 3 - Blocking] `RELATORIO-DOCUDATA.md` não estava versionado

- **Encontrado durante:** Task 3, ao commitar.
- **Situação:** o arquivo existia no disco mas era **untracked** (não ignorado — `git check-ignore` retorna 1). O plano o listava em `files_modified` assumindo que fosse um arquivo versionado.
- **Efeito:** o commit `eb6ce98` o registra como arquivo novo (754 inserções, 0 deleções) em vez de mostrar o diff das quatro seções editadas. O conteúdo commitado é o correto — pós-remoção, com as seções 5, 10, 14 e 17 já reescritas — mas o histórico do git não preserva a versão anterior do documento para comparação.
- **Ação:** commitado assim mesmo, porque o plano exigia o arquivo no commit da Task 3 e deixá-lo untracked contradiria o próprio `files_modified`. Registrado aqui porque, se alguém quiser ver o que exatamente mudou no relatório, a referência é este SUMMARY, não `git diff`.

Nenhuma outra deviation. Rules 1, 2 e 4 não foram acionadas.

## Authentication Gates

Nenhum.

## Known Stubs

Nenhum. A remoção não deixou nenhum caminho de código parcialmente ligado.

## Threat Flags

Nenhuma superfície nova. A remoção **elimina** uma superfície de confiança: a suíte de aceite recebia POST do CI do GitHub em `/aceite/*`, e esse router não existe mais.

Verificações do threat model do plano:
- **T-LWL-01** (Elevation of Privilege em `main.py`): apenas uma linha de `include_router` saiu; `import main` OK com 33 rotas registradas e a suíte completa passando.
- **T-LWL-02** (DoS no resumo semanal): o call-site foi ajustado no mesmo commit da mudança de assinatura; gates de AST e de contagem de rotas confirmam que `POST /boletins/resumo_semanal` sobreviveu intacta.
- **T-LWL-03** (Tampering no schema): gate sobre o diff confirma zero linha adicionada com DROP/ALTER TABLE/DELETE FROM.
- **T-LWL-04** (Information Disclosure em `hooks/`): gate positivo confirma os 4 arquivos das outras duas integrações presentes.

## Verificação

| Gate | Resultado |
|------|-----------|
| `cd docudata-backend && .venv/bin/python -m pytest -q` | **4 failed, 261 passed** — as 4 falhas são as pré-existentes de `tests/test_schemas_and_client.py`; baseline era 4 failed, 256 passed. Nenhuma falha nova, +5 passados (os testes novos do Painel). |
| `cd docudata-backend && .venv/bin/python -c "import main"` | OK — 33 rotas |
| `cd docudata-frontend && npx --no-install tsc --noEmit` | Limpo, sem saída |
| `git diff --stat HEAD~3 HEAD` | 12 arquivos — exatamente os de `files_modified` |
| Grep por identificadores da trilha de cliente em `*.py`/`*.yml` do backend | Zero ocorrências |
| Diff de `supabase_schema.sql` | 13 linhas adicionadas, todas comentário `--` |

Conferência manual pendente (não bloqueante): abrir o Painel de um projeto com datas de contrato e ver o desvio refletindo escopo concluído; gerar um resumo semanal pela UI e confirmar o markdown sem as seções de cliente.

## Self-Check: PASSED

Arquivos criados conferidos no disco, arquivos deletados conferidos ausentes, e os 3 commits conferidos em `git log`.
