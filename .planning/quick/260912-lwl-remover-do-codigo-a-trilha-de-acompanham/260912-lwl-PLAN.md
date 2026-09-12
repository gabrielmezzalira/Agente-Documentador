---
phase: remover-trilha-acompanhamento-cliente
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docudata-backend/routers/painel.py
  - docudata-backend/routers/boletins.py
  - docudata-backend/routers/funcionalidades.py
  - docudata-backend/models/schemas.py
  - docudata-backend/main.py
  - docudata-backend/supabase_schema.sql
  - docudata-backend/tests/test_painel_desvio_escopo.py
  - docudata-backend/routers/aceite_ingest.py
  - docudata-backend/hooks/aceite_agent.py
  - docudata-backend/hooks/aceite.yml
  - docudata-frontend/app/lib/api.ts
  - RELATORIO-DOCUDATA.md
autonomous: true
requirements: []  # N/A — quick task de remoção de código morto + correção de bug observável; não é um requisito de roadmap

estimate:
  tokens: 85000
  raw_tokens: 55000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "O alarme de desvio do Painel passa a comparar prazo consumido com escopo CONCLUÍDO: para um projeto com 50% do prazo corrido e 100% das funcionalidades concluídas, `bloco_a.desvio_pontos` é negativo e `bloco_a.desvio_detectado` é False mesmo com tolerância 0 — antes desta mudança o mesmo projeto acusava desvio de +50 pontos porque comparava contra um campo que nenhuma tela preenchia"
    - "`tolerancia_desvio_pontos` do projeto continua sendo o corte de `desvio_detectado`, e `desvio_pontos` continua no retorno do Bloco A com uma casa decimal"
    - "`POST /boletins/resumo_semanal` continua respondendo 200 e continua salvando em `generated_docs` com `doc_type='resumo_semanal'` — é a única rota do router `/boletins` que sobra, e é chamada pela UI em `docudata-frontend/app/projects/[id]/page.tsx` via `gerarResumoSemanal`"
    - "O markdown do resumo semanal não tem mais as seções de cliente nem a linha de escopo aprovado; sobram Funcionalidades Travadas, Achados Críticos e Leitura Tempo × Escopo com duas linhas (prazo consumido e escopo concluído)"
    - "`from main import app` (ou `import main`) funciona sem ImportError após o router de aceite ser desregistrado e o arquivo deletado"
    - "A suíte do backend termina com exatamente as 4 falhas pré-existentes de `tests/test_schemas_and_client.py` e nenhuma outra — baseline medido antes da mudança: 4 failed, 256 passed"
    - "`criterios_aceite`, a tabela `transicoes_status`, as transições do campo `status`, `hooks/docudata_agent.py` e `hooks/revisor_agent.py` continuam intactos e funcionando"
    - "Nenhuma instrução executável foi adicionada a `docudata-backend/supabase_schema.sql` — só comentário SQL; o diff do arquivo não contém nenhuma linha adicionada com DROP/ALTER/DELETE"
  artifacts:
    - "docudata-backend/tests/test_painel_desvio_escopo.py — arquivo novo, testa `calcular_bloco_a` como função pura (sem Supabase) para a nova fórmula de desvio"
    - "docudata-backend/routers/aceite_ingest.py — DELETADO"
    - "docudata-backend/hooks/aceite_agent.py — DELETADO"
    - "docudata-backend/hooks/aceite.yml — DELETADO"
    - "docudata-backend/routers/boletins.py — mantido, com o prefixo `/boletins` e apenas `gerar_resumo_semanal` dentro"
    - "RELATORIO-DOCUDATA.md — seções 5, 10, 14 e 17 reescritas para descrever o estado pós-remoção"
  key_links:
    - "`routers/boletins.py:gerar_resumo_semanal` → `routers/painel.calcular_bloco_a` / `calcular_bloco_b`: a assinatura de `calcular_bloco_b` perde um parâmetro e o retorno perde chaves; o call-site do resumo semanal TEM que mudar no mesmo commit, senão o resumo semanal quebra em produção"
    - "`main.py` linha 12 (import) e linha 70 (include_router) → `routers/aceite_ingest.py`: o arquivo só pode ser deletado no mesmo commit em que essas duas referências saem, senão `import main` levanta ModuleNotFoundError e o app não sobe"
    - "`models/schemas.py` → `routers/boletins.py` e `routers/aceite_ingest.py`: as classes `Boletim*` e `ExecucaoAceite*` só podem ser removidas depois (Task 2) que seus consumidores sumiram (Task 1 + deleção); daí a ordem das tasks"
    - "`models/schemas.py:FuncionalidadeResponse` → `docudata-frontend/app/lib/api.ts:FuncionalidadeResponse`: são o mesmo contrato dos dois lados; campo removido de um tem que sair do outro"
---

<objective>
Remover do código a trilha inteira de "acompanhamento do cliente" do DocuData — campos de status com o cliente nas funcionalidades, boletim de aceite e suíte de verificação de aceite — e, junto disso, consertar o alarme de desvio do Painel, que hoje é calculado contra um campo que nenhuma tela nunca preencheu.

A trilha é funcional no back-end e nunca ganhou interface: nenhuma tela lê ou escreve esses campos. O efeito colateral é um bug observável: `pct_aprovado_cliente` é permanentemente 0, então **todo projeto acusa desvio assim que passa da tolerância do calendário**, independentemente de quanto o time entregou. A correção é trocar o termo da subtração para o escopo concluído, que vem do campo `status` das funcionalidades — esse sim editável na UI.

Purpose: eliminar código morto que induz o leitor a erro sobre o que o sistema faz, e fazer o indicador mais visível do Painel voltar a medir algo real.
Output: back-end sem a trilha de cliente e com o desvio medindo entrega; tipos do frontend limpos; `RELATORIO-DOCUDATA.md` descrevendo o sistema como ele passa a ser.

**Nota sobre tracer-first:** não se aplica aqui. Este plano não entrega capacidade nova que possa ser fatiada verticalmente — é uma remoção com uma mudança de fórmula acoplada. A ordem das tasks é ditada por dependência de import (ver `key_links`), e a Task 1 leva um teste automatizado novo para a única mudança de comportamento do plano.
</objective>

<execution_context>
@/Users/gabrielmezzalira/.claude/gsd-core/workflows/execute-plan.md
@/Users/gabrielmezzalira/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/CLAUDE.md
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend/routers/painel.py
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend/routers/boletins.py
</context>

<baseline>
Medido nesta máquina imediatamente antes de planejar — use como referência, não como falha introduzida:

- `cd docudata-backend && .venv/bin/python -m pytest -q` → **4 failed, 256 passed**. As 4 falhas são todas de `tests/test_schemas_and_client.py` e são **pré-existentes**, sem relação nenhuma com esta remoção.
- `cd docudata-backend && .venv/bin/python -c "import main"` → OK.
- `cd docudata-frontend && npx --no-install tsc --noEmit` → sem saída (limpo).
- `grep -rl` por `status_cliente`, boletim, execuções de aceite e testes e2e em `docudata-backend/tests/` e `docudata-backend/evals/` → **nenhum arquivo**. A suíte não cobre nada do que está sendo removido.
- `docudata-backend/supabase_schema.sql` já contém 7 ocorrências da palavra DROP em outras migrações; o gate do schema é sobre o **diff**, não sobre a contagem absoluta.
</baseline>

<do_not_touch>
Confirmado por leitura de código. Se o executor sentir vontade de "aproveitar e limpar", pare:

- **`POST /boletins/resumo_semanal`** — em uso pela UI (`docudata-frontend/app/projects/[id]/page.tsx:558` → `gerarResumoSemanal` em `app/lib/api.ts:1164`). O arquivo `routers/boletins.py`, o nome do router e o prefixo `/boletins` ficam como estão. Renomear quebraria o caminho que o frontend chama.
- **`criterios_aceite`** nas funcionalidades — é critério de aceite da ENTREGA, editado na `EscopoTab.tsx`. Nada a ver com cliente. Um grep por "aceite" casa com isso; não se deixe enganar.
- **Tabela `transicoes_status`** e o registro de transição do campo `status` — só a transição do campo de status com o cliente sai.
- **`calcular_bloco_c`** em `painel.py` — conta WIP com `status in ("em_andamento", "em_ajuste")`. Fora de escopo, não mexer, mesmo parecendo relacionado.
- **`hooks/docudata_agent.py`**, **`hooks/docudata.yml`**, **`hooks/revisor_agent.py`**, **`hooks/revisor.yml`** — as outras duas integrações de GitHub, em uso.
- **O banco.** Decisão explícita do usuário: nenhum `DROP COLUMN`, nenhum `DROP TABLE`, nem comentados. As colunas e tabelas ficam órfãs de propósito — nada de dado é destruído e a mudança é reversível revertendo o commit. As migrações deste repo são manuais (coladas no SQL Editor do Supabase); não há CI/CD de schema.
</do_not_touch>

<!-- planner-discipline-allow: status_cliente -->
<!-- planner-discipline-allow: data_aprovacao_cliente -->
<!-- planner-discipline-allow: testes_e2e -->
<!-- planner-discipline-allow: pct_aprovado_cliente -->
<!-- planner-discipline-allow: aguardando_cliente -->
<!-- planner-discipline-allow: execucoes_aceite -->
<!-- planner-discipline-allow: cobertura_aceite -->
<!-- planner-discipline-allow: boletins_aceite -->
<!-- planner-discipline-allow: funcionalidades_com_aceite_falhando -->
<!-- planner-discipline-allow: dispatch_aceite -->
<!-- planner-discipline-allow: aceite_ingest -->
<!-- planner-discipline-allow: BoletimCreate -->
<!-- planner-discipline-allow: BoletimPatch -->
<!-- planner-discipline-allow: BoletimResponse -->
<!-- planner-discipline-allow: ExecucaoAceite -->

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Painel mede entrega real — nova fórmula de desvio e limpeza de painel.py + boletins.py</name>
  <files>docudata-backend/tests/test_painel_desvio_escopo.py, docudata-backend/routers/painel.py, docudata-backend/routers/boletins.py</files>
  <read_first>
    - `docudata-backend/routers/painel.py` na íntegra (405 linhas). Os pontos de interesse: `calcular_bloco_a` (34-66), `calcular_bloco_b` (69-164), `_calcular_cobertura_aceite` (167-177) e o handler `get_painel` (326-405). `calcular_bloco_c` e `calcular_bloco_d` ficam intocados.
    - `docudata-backend/routers/boletins.py` na íntegra (544 linhas). Interessa saber que só `gerar_resumo_semanal` (279-441) sobrevive, e que ela consome o Bloco A e o Bloco B.
    - `docudata-backend/tests/test_valor_projeto.py` (30 primeiras linhas) — convenção de teste do repo: import direto de `routers.*` / `models.*`, sem conftest, pytest rodando com `rootdir=docudata-backend`.
  </read_first>
  <behavior>
    Testes a escrever ANTES da implementação, em `docudata-backend/tests/test_painel_desvio_escopo.py`, todos contra `calcular_bloco_a` importada de `routers.painel` (função pura — não toca Supabase, não precisa de mock). Monte as datas relativas a `date.today()` para o teste ser determinístico.

    - Test 1 — projeto em dia: `data_inicio = hoje - 50 dias`, `data_fim_contratada = hoje + 50 dias` (100 dias no total, 50% consumido), 10 funcionalidades das quais 5 com `status="concluida"`, `tolerancia_desvio_pontos=20`. Espera `pct_prazo_consumido == 50.0`, `pct_escopo_concluido == 50.0`, `desvio_pontos == 0.0`, `desvio_detectado is False`.
    - Test 2 — projeto atrasado de verdade: 80% do prazo consumido (`inicio = hoje - 80`, `fim = hoje + 20`), 10 funcionalidades com 1 concluída, tolerância 20. Espera `desvio_pontos == 70.0` e `desvio_detectado is True`.
    - Test 3 — o bug que está sendo consertado: 50% do prazo consumido, **todas** as 10 funcionalidades concluídas, `tolerancia_desvio_pontos=0`. Espera `desvio_pontos == -50.0` e `desvio_detectado is False`. Este teste falha na implementação atual (que daria +50.0 e True) e é a prova do conserto.
    - Test 4 — o retorno do Bloco A não expõe mais a métrica de aprovação do cliente: `assert "pct_aprovado_cliente" not in calcular_bloco_a(proj, funcs)`.
    - Test 5 — sem datas de contrato o comportamento não muda: `calcular_bloco_a({}, [])` retorna `{"sem_dados": True}`.
  </behavior>
  <action>
Escreva primeiro o arquivo de teste do bloco `<behavior>` e rode-o para ver Test 3 e Test 4 falharem (RED). Só então implemente.

**Em `docudata-backend/routers/painel.py`:**

Em `calcular_bloco_a`: apague a contagem de funcionalidades aprovadas pelo cliente e a porcentagem derivada dela. O desvio passa a ser `pct_prazo - pct_escopo`, mantendo `tolerancia = proj.get("tolerancia_desvio_pontos") or 0` e `desvio_detectado = desvio > tolerancia` exatamente como estão. O dict de retorno perde a chave da porcentagem aprovada e mantém `sem_dados`, `pct_prazo_consumido`, `pct_escopo_concluido`, `desvio_detectado` e `desvio_pontos` (este continua `round(desvio, 1)`).

Em `calcular_bloco_b`: remova o quarto parâmetro (a lista de execuções da suíte de CI) da assinatura, que fica `(funcs, transicoes, revisao_recente=None)`. No laço de parsing das transições, apague o ramo que captura a transição do campo de status com o cliente e o dicionário auxiliar que ele alimentava. No laço sobre `funcs`, apague a leitura do campo de status com o cliente, o ramo que monta a lista de itens esperando retorno do cliente e o ramo que monta a lista de itens em ajuste — junto com as três listas vazias inicializadas no topo, exceto `travadas`. Apague também todo o bloco que cruza funcionalidades concluídas com execuções de CI falhando. O dict de retorno fica com `travadas`, `achados_criticos`, `relatorio_gerente`, `relatorio_tecnico` e `data_revisao`. O cálculo de `travadas` (em andamento há mais de 7 dias) e todo o bloco de `revisao_recente` ficam idênticos.

Apague a função auxiliar `_calcular_cobertura_aceite` inteira.

No handler `get_painel`: apague o passo que consulta a tabela de execuções de CI (a atribuição de `step`, a query, a deduplicação por funcionalidade), o quarto argumento na chamada de `calcular_bloco_b`, o cálculo da cobertura e a chave correspondente no dict de resposta. A resposta fica com `bloco_a`, `bloco_b`, `bloco_c`, `bloco_d`. O `try/except` com `step` e o traceback ficam como estão.

**Em `docudata-backend/routers/boletins.py`:**

Apague as três rotas da trilha de cliente — `criar_boletim` (POST ""), `listar_boletins` (GET "/{project_id}") e `atualizar_status_boletim` (PATCH "/{id}") — mais a função auxiliar `_registrar_transicao_status_cliente`, a constante `_BOLETIM_SYSTEM_PROMPT` e o dicionário `TRANSICOES_VALIDAS` (que só era lido pela rota PATCH). Fica no arquivo apenas `gerar_resumo_semanal`, com o mesmo decorator `@router.post("/resumo_semanal")`, o mesmo `router = APIRouter(prefix="/boletins", tags=["boletins"])` e o mesmo nome de módulo.

Ajuste os imports do topo: `from models.schemas import ResumoSemanalRequest` (as três classes de boletim saem); remova `from typing import Optional` e as duas linhas de import do LangChain/Gemini, que só serviam à geração do boletim. `APIRouter`, `HTTPException` e `date, datetime, timedelta, timezone` continuam em uso pelo resumo semanal.

Dentro de `gerar_resumo_semanal`: apague o bloco que consulta a tabela de execuções de CI e a variável que ele produzia, e passe a chamar `calcular_bloco_b(funcs, transicoes, revisao_recente)` com três argumentos. Na montagem do markdown, apague a leitura das duas listas que sumiram do Bloco B, ajuste `tem_anomalia` para considerar só travadas e achados críticos, apague a seção "Aguardando Cliente" e a seção "Concluídas com Suíte Falhando", e na seção "Leitura Tempo × Escopo" apague a terceira linha (a de escopo aprovado), deixando só prazo consumido e escopo concluído. A seção "Funcionalidades Travadas", a de achados críticos, o cálculo do período dom–sáb e o insert em `generated_docs` ficam idênticos.

Não deixe comentários residuais nomeando o que foi removido — o histórico do git já registra isso, e comentários assim fazem os gates de grep deste plano falharem por texto de comentário em vez de por código.
  </action>
  <verify>
    <automated>cd docudata-backend && .venv/bin/python -m pytest -q tests/test_painel_desvio_escopo.py</automated>
    <automated>cd docudata-backend && ! grep -nE 'status_cliente|pct_aprovado_cliente|aguardando_cliente|execucoes_aceite|cobertura_aceite|boletins_aceite|funcionalidades_com_aceite_falhando' routers/painel.py routers/boletins.py</automated>
    <automated>cd docudata-backend && test "$(grep -c -F 'def gerar_resumo_semanal' routers/boletins.py)" -eq 1 && test "$(grep -c -F 'APIRouter(prefix="/boletins"' routers/boletins.py)" -eq 1</automated>
    <automated>cd docudata-backend && test "$(grep -cE '^@router\.' routers/boletins.py)" -eq 1</automated>
    <automated>cd docudata-backend && .venv/bin/python -c "import ast,sys; [ast.parse(open(f).read()) for f in ('routers/painel.py','routers/boletins.py')]"</automated>
  </verify>
  <done>Os 5 testes de `tests/test_painel_desvio_escopo.py` passam, incluindo o Test 3 que reprova a fórmula antiga. `routers/painel.py` não menciona mais nada da trilha de cliente nem da suíte de CI, `calcular_bloco_b` tem 3 parâmetros, e `routers/boletins.py` tem exatamente uma rota — o resumo semanal — ainda sob o prefixo `/boletins`.</done>
</task>

<task type="auto">
  <name>Task 2: Apagar a suíte de aceite e os campos de cliente do resto do back-end</name>
  <files>docudata-backend/routers/funcionalidades.py, docudata-backend/models/schemas.py, docudata-backend/main.py, docudata-backend/supabase_schema.sql, docudata-backend/routers/aceite_ingest.py, docudata-backend/hooks/aceite_agent.py, docudata-backend/hooks/aceite.yml</files>
  <read_first>
    - `docudata-backend/routers/funcionalidades.py` linhas 1-120 (imports + a função de disparo do CI que sai inteira) e 370-460 (o handler PATCH, onde ficam os laços de transição, o agendamento em background e o auto-preenchimento da data de aprovação).
    - `docudata-backend/models/schemas.py` linhas 190-330 — `FuncionalidadeUpdate`, `FuncionalidadeResponse`, e o bloco de classes `ExecucaoAceite*` / `Boletim*` / `ResumoSemanalRequest`.
    - `docudata-backend/main.py` linhas 12 e 55-82 — a linha de import dos routers e a lista de `include_router`.
    - `docudata-backend/supabase_schema.sql` linhas 60-82 (colunas de funcionalidades) e 175-223 (as duas migrações que criaram as tabelas que ficam órfãs).
  </read_first>
  <precondition>A Task 1 já removeu de `routers/boletins.py` todo uso das classes de boletim — verificável com `grep -c 'Boletim' docudata-backend/routers/boletins.py` retornando 0. Sem isso, apagar as classes de `schemas.py` quebra o import do módulo.</precondition>
  <action>
**Delete três arquivos inteiros:** `docudata-backend/routers/aceite_ingest.py`, `docudata-backend/hooks/aceite_agent.py` e `docudata-backend/hooks/aceite.yml`. Use `git rm`. Os outros quatro arquivos de `hooks/` (os dois agentes e os dois YAMLs das integrações de ingestão de commits e do revisor diário) ficam.

**Em `docudata-backend/main.py`:** tire o nome do router deletado da lista de imports da linha 12 e apague a linha de `include_router` correspondente (linha 70). Todas as outras 25 registrações, incluindo a do router de boletins logo abaixo, ficam exatamente como estão, com as mesmas dependências de auth.

**Em `docudata-backend/routers/funcionalidades.py`:** apague a função `dispatch_aceite_background` inteira (linhas 24-116, tudo entre os imports e a definição do `router`) e o bloco dentro do handler PATCH que a agendava quando o status virava `concluida`. Com isso, o parâmetro `background_tasks: BackgroundTasks` do `patch_funcionalidade` fica sem uso — remova-o da assinatura e remova `BackgroundTasks` da linha de import do `fastapi` (os outros nomes importados de lá seguem em uso). Ficam também sem uso e devem sair: `import subprocess`, `import urllib.error`, `import urllib.request` e o nome `date` do import de `datetime` — `import json` e `import os` ficam, pois são usados em outros pontos do arquivo.

Ainda no `patch_funcionalidade`: os dois laços `for campo in ("status", "status_cliente")` passam a iterar só sobre `("status",)`; apague o bloco que copiava `testes_e2e` para o payload de update; apague o bloco `if/elif` que auto-preenchia a data de aprovação do cliente. O restante do handler — busca da linha atual, 404, registro de transição do campo `status`, montagem do `updates` a partir dos campos editáveis e o update final — fica idêntico.

**Em `docudata-backend/models/schemas.py`:** de `FuncionalidadeUpdate`, remova os três campos da trilha de cliente (o status paralelo, a data de aprovação e a lista de testes e2e). De `FuncionalidadeResponse`, remova os mesmos três campos. Apague as classes `ExecucaoAceitePayload`, `ExecucaoAceiteResponse`, `BoletimCreate`, `BoletimPatch` e `BoletimResponse`. `ResumoSemanalRequest` fica — é o corpo do resumo semanal. `FuncionalidadeCreate`, os `field_validator` de critérios e prioridade, `TransicaoStatusResponse` e `ContratoUpdate` ficam intocados.

**Em `docudata-backend/supabase_schema.sql`:** acrescente **apenas comentários SQL** (`--`), nada executável. Um comentário curto junto às colunas órfãs da tabela de funcionalidades e outro junto às duas migrações (Phase 11 e Phase 12) que criaram as tabelas órfãs, dizendo que o código que as usava foi removido em setembro de 2026 e que elas ficam no banco de propósito, sem código lendo ou escrevendo. Escreva os comentários de forma a não repetir verbatim os nomes de identificadores Python removidos — nomeie as colunas e tabelas do próprio SQL, que continuam existindo e já aparecem no arquivo. **Nenhum DROP, nenhum ALTER, nenhum DELETE**, nem comentados.
  </action>
  <verify>
    <automated>test ! -e docudata-backend/routers/aceite_ingest.py && test ! -e docudata-backend/hooks/aceite_agent.py && test ! -e docudata-backend/hooks/aceite.yml</automated>
    <automated>test -e docudata-backend/hooks/docudata_agent.py && test -e docudata-backend/hooks/revisor_agent.py && test -e docudata-backend/hooks/revisor.yml && test -e docudata-backend/hooks/docudata.yml</automated>
    <automated>cd docudata-backend && ! grep -rnE 'status_cliente|data_aprovacao_cliente|testes_e2e|execucoes_aceite|boletins_aceite|dispatch_aceite|aceite_ingest|BoletimCreate|BoletimPatch|BoletimResponse|ExecucaoAceite' --include='*.py' --include='*.yml' --exclude-dir=__pycache__ --exclude-dir=.venv .</automated>
    <automated>cd docudata-backend && .venv/bin/python -c "import main; print('IMPORT OK')"</automated>
    <automated>cd docudata-backend && { ! .venv/bin/python -m pytest -q 2>&1 | grep '^FAILED' | grep -qv 'test_schemas_and_client.py'; }</automated>
    <automated>! git diff -- docudata-backend/supabase_schema.sql | grep -E '^\+' | grep -qiE '(drop|alter table|delete from)'</automated>
    <automated>test "$(grep -c -F 'criterios_aceite' docudata-backend/models/schemas.py)" -ge 1 && test "$(grep -c -F 'ResumoSemanalRequest' docudata-backend/models/schemas.py)" -eq 1</automated>
  </verify>
  <done>Os três arquivos da suíte de aceite não existem mais, `import main` funciona, a suíte do backend termina com exatamente as 4 falhas pré-existentes de `test_schemas_and_client.py` e nenhuma outra, um grep por qualquer identificador da trilha de cliente no código Python/YAML do backend não retorna nada, e o diff do schema SQL só adiciona comentários.</done>
</task>

<task type="auto">
  <name>Task 3: Limpar os tipos do frontend e reescrever o relatório funcional</name>
  <files>docudata-frontend/app/lib/api.ts, RELATORIO-DOCUDATA.md</files>
  <read_first>
    - `docudata-frontend/app/lib/api.ts` linhas 856-922 — as interfaces `FuncionalidadeResponse`, `BlocoA`, `BlocoB` e `PainelData`. Já confirmado por grep: nenhum componente `.tsx` lê nenhum dos campos que saem; são declarações órfãs.
    - `RELATORIO-DOCUDATA.md` — seção 5 (linhas 137-167, o aviso em blockquote logo depois da lista de atributos da funcionalidade), seção 10 (488-523, os dois avisos em blockquote), seção 14 (678-710, as integrações de GitHub) e seção 17 inteira (748-793).
  </read_first>
  <action>
**Em `docudata-frontend/app/lib/api.ts`:** de `FuncionalidadeResponse`, remova as duas linhas do status paralelo com o cliente e da data de aprovação. De `BlocoA`, remova a linha da porcentagem aprovada pelo cliente. De `BlocoB`, remova a linha da lista de itens esperando retorno do cliente — a interface fica só com `travadas`. De `PainelData`, remova a linha da cobertura de aceite. Nada mais no arquivo muda; `gerarResumoSemanal` e o caminho `/boletins/resumo_semanal` ficam exatamente como estão.

**Em `RELATORIO-DOCUDATA.md`** — quatro edições, todas de prosa voltada ao usuário final, em português, no mesmo tom do resto do documento:

*Seção 5 (Planejamento):* apague o blockquote de aviso sobre o status paralelo com o cliente. O campo não existe mais, então não há mais lacuna a avisar. A lista de atributos da funcionalidade acima dele e o parágrafo sobre histórico de mudança de status ficam.

*Seção 10 (Painel):* no bloco "Tempo × Escopo", reescreva o texto para dizer que o Painel compara prazo consumido com escopo concluído e que o **desvio** é a diferença entre os dois, com a tolerância do projeto definindo quantos pontos percentuais são aceitáveis. Apague o blockquote de aviso inteiro — o alarme passa a funcionar, e o texto novo deve deixar claro que ele mede entrega real. No bloco "Itens em atenção", reescreva para dizer que ele reúne as funcionalidades travadas (em andamento há mais de 7 dias) e os achados críticos do revisor diário de código quando a integração com o GitHub está instalada; apague a menção às duas listas de cliente e o blockquote de aviso que vinha depois.

*Seção 14 (GitHub):* o parágrafo de abertura hoje diz que existem 3 integrações instaláveis no repositório — corrija a contagem para 2, escrita por extenso como já está no texto. Apague a subseção da suíte de verificação de aceite (a última das três, que fala em gates de teste do CI e remete à seção 17). Sobram ingestão de commits e revisor diário.

*Seção 17:* deixa de ser a maior lacuna do sistema e vira registro histórico curto — algo como duas a quatro frases sob um título que deixe claro que isso foi **removido** do código (por exemplo, "Acompanhamento do cliente — removido"). O conteúdo: existiu no back-end uma trilha de aprovação do cliente (status da funcionalidade com o cliente, boletim de aceite gerado por IA e suíte de verificação de aceite via CI) que nunca ganhou interface; foi removida do código em setembro de 2026; as colunas e tabelas correspondentes continuam no banco, vazias e sem nada lendo, para não destruir dado; e o DocuData acompanha execução interna — tasks, sprints, pontos, pessoas, documentação — não o ciclo de validação com o cliente. Apague as subseções "O que existe e está inacessível", "O que isso quebra hoje" e "Como ler isso": os três itens que ela listava como quebrados ou deixaram de existir ou foram consertados nas tasks anteriores.

Não mexa nas seções 1-4, 6-9, 11-13, 15, 16 e 18, nem no índice/cabeçalho do documento se houver. Se alguma seção fora dessas quatro referenciar a seção 17 por número, ajuste só a frase de referência.
  </action>
  <verify>
    <automated>cd docudata-frontend && ! grep -nE 'status_cliente|data_aprovacao_cliente|pct_aprovado_cliente|aguardando_cliente|cobertura_aceite' app/lib/api.ts</automated>
    <automated>cd docudata-frontend && test "$(grep -c -F 'gerarResumoSemanal' app/lib/api.ts)" -ge 1 && test "$(grep -c -F '/boletins/resumo_semanal' app/lib/api.ts)" -eq 1</automated>
    <automated>cd docudata-frontend && npx --no-install tsc --noEmit</automated>
    <automated>test "$(grep -c -F 'não está implementado' RELATORIO-DOCUDATA.md)" -eq 0</automated>
    <automated>test "$(grep -c -F 'Suíte de verificação de aceite' RELATORIO-DOCUDATA.md)" -eq 0 && test "$(grep -c -F 'três integrações' RELATORIO-DOCUDATA.md)" -eq 0</automated>
    <automated>test "$(grep -c -F 'O alarme de desvio não funciona hoje' RELATORIO-DOCUDATA.md)" -eq 0</automated>
    <automated>test "$(grep -cE '^## 1[0-8]\.' RELATORIO-DOCUDATA.md)" -eq 9</automated>
  </verify>
  <done>`npx tsc --noEmit` continua limpo no frontend e `app/lib/api.ts` não declara mais nenhum campo da trilha de cliente, mantendo `gerarResumoSemanal` intacto. `RELATORIO-DOCUDATA.md` descreve o alarme de desvio como funcional e medido contra escopo concluído, lista duas integrações de GitHub, e a seção 17 é um registro histórico curto de remoção — a numeração das 18 seções permanece intacta.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| frontend → API FastAPI | Sessão autenticada via `get_current_pessoa`; nenhuma rota pode perder seu gate de auth durante a remoção |
| CI do GitHub → API | A suíte de aceite recebia POST anônimo/tokenizado do CI; essa superfície some inteira nesta remoção |
| API → Supabase | Chave `service_role` no backend; nenhuma migração destrutiva é executada por este plano |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-LWL-01 | Elevation of Privilege | `main.py` — lista de `include_router` | high | mitigate | A Task 2 remove **uma** linha de registro; o gate `import main` mais a suíte completa provam que nada mais mudou. Nenhuma registração restante perde seu kwarg `dependencies=[Depends(...)]` — verificado por leitura antes da edição. |
| T-LWL-02 | Denial of Service | `POST /boletins/resumo_semanal` | high | mitigate | Rota em uso pela UI e consumidora direta das funções de Painel cuja assinatura muda. Task 1 ajusta o call-site no mesmo commit; gate de AST + contagem de rotas do router garante que a rota sobreviveu. |
| T-LWL-03 | Tampering | `supabase_schema.sql` | critical | mitigate | Gate sobre o **diff** do arquivo rejeita qualquer linha adicionada com DROP/ALTER TABLE/DELETE FROM. Migrações aqui são manuais e irreversíveis uma vez coladas no SQL Editor. |
| T-LWL-04 | Information Disclosure | `hooks/` | medium | mitigate | Só os três arquivos da suíte de aceite são deletados; gate positivo confirma que os quatro arquivos das outras duas integrações de GitHub continuam presentes. |
| T-LWL-SC | Tampering | npm/pip/cargo installs | n/a | accept | Este plano não instala nenhum pacote — só remove código e edita documentação. Sem superfície de supply-chain. |
</threat_model>

<verification>
Depois das três tasks, rodar da raiz do repositório:

1. `cd docudata-backend && .venv/bin/python -m pytest -q` — esperado: as 4 falhas pré-existentes de `test_schemas_and_client.py` e mais nada; o total de passados sobe de 256 para 261 (os 5 testes novos do Painel).
2. `cd docudata-backend && .venv/bin/python -c "import main"` — o app precisa subir.
3. `cd docudata-frontend && npx --no-install tsc --noEmit` — sem saída.
4. `git diff --stat` — confere que os arquivos tocados são exatamente os 12 de `files_modified` e nenhum outro.
5. Conferência manual rápida (não bloqueante): abrir o Painel de um projeto com datas de contrato e ver o desvio refletindo o escopo concluído; clicar em gerar resumo semanal e ver o markdown sair sem as seções de cliente.
</verification>

<success_criteria>
- [ ] `calcular_bloco_a` calcula desvio como prazo consumido menos escopo concluído, com `tolerancia_desvio_pontos`, `desvio_pontos` e `desvio_detectado` preservados
- [ ] 5 testes novos em `docudata-backend/tests/test_painel_desvio_escopo.py`, todos passando
- [ ] `routers/aceite_ingest.py`, `hooks/aceite_agent.py` e `hooks/aceite.yml` deletados; as outras duas integrações de GitHub intactas
- [ ] `routers/boletins.py` com uma única rota — `POST /boletins/resumo_semanal` — ainda chamada pelo frontend sem mudança de caminho
- [ ] Grep por qualquer identificador da trilha de cliente no código Python/YAML do backend e nos tipos do frontend retorna zero
- [ ] `criterios_aceite`, `transicoes_status` e as transições do campo `status` intactos
- [ ] Suíte do backend com exatamente as 4 falhas pré-existentes; `import main` OK; `tsc --noEmit` limpo
- [ ] `supabase_schema.sql` alterado só por comentário — zero instrução executável adicionada
- [ ] `RELATORIO-DOCUDATA.md` com seções 5, 10, 14 e 17 refletindo o sistema pós-remoção
- [ ] Três commits atômicos, um por task
</success_criteria>

<output>
Criar `.planning/quick/260912-lwl-remover-do-codigo-a-trilha-de-acompanham/260912-lwl-SUMMARY.md` ao terminar.
</output>
