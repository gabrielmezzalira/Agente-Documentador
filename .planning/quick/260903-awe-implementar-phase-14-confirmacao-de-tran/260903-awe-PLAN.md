---
phase: 14-confirmacao-de-transicao-reabertura-bloqueio-manual
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docudata-backend/routers/tasks.py
  - docudata-backend/models/schemas.py
  - docudata-backend/supabase_schema.sql
  - docudata-backend/tests/test_task_confirmacao_sugestao.py
  - docudata-backend/tests/test_task_reabertura.py
  - docudata-backend/tests/test_bloqueio_manual.py
  - docudata-frontend/app/lib/api.ts
  - docudata-frontend/app/components/TasksKanbanTab.tsx
autonomous: true
requirements:
  - "TRANS-01"
  - "TRANS-02"
  - "TRANS-03"
  - "TRANS-04"
  - "TRANS-05"

estimate:
  tokens: 75000
  raw_tokens: 75000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Nenhuma mudança de coluna de uma task (drag-and-drop no kanban, aceite do banner de sugestão da IA) grava em coluna_kanban ou task_transicoes sem o gerente confirmar explicitamente em um modal; cancelar fecha o modal sem chamar nenhuma API e sem alterar nenhum estado — TRANS-01"
    - "O aceite da sugestão da IA (PATCH /tasks/sugestoes/{id} com aceita=true, acao=mover_para_concluida) passa a executar pelo mesmo caminho gated (DoR/DoD/WIP + registro em task_transicoes) que já é usado por PATCH /tasks/{id} e POST /tasks/{id}/mover — não grava mais coluna_kanban direto sem transição — TRANS-02"
    - "Toda confirmação de transição com status_anterior=concluida e status_novo=em_andamento grava uma linha em task_reaberturas (task_id, transicao_id, operacional_id, motivo opcional, timestamp) e incrementa tasks.contador_reaberturas em 1; nenhuma outra saída de concluida (ex.: concluida->planejado) grava em task_reaberturas — TRANS-03"
    - "Task ganha os campos bloqueado_manual, bloqueado_em, bloqueado_por, bloqueado_resolvido_por (operacional|gerente), bloqueado_resolvido_em; tentar desmarcar bloqueado_manual sem informar bloqueado_resolvido_por retorna 422 antes de qualquer escrita no banco — TRANS-04, TRANS-05"
  artifacts:
    - "docudata-backend/supabase_schema.sql — bloco de migration Phase 14: tabela task_reaberturas, tasks.contador_reaberturas, tasks.bloqueado_manual/_em/_por/_resolvido_por/_resolvido_em"
    - "docudata-backend/routers/tasks.py — resolve_task_sugestao delegando a patch_task; _registrar_reabertura; gate 422 de bloqueado_manual"
    - "docudata-frontend/app/components/TasksKanbanTab.tsx — ConfirmTransicaoModal component, usado por handleDrop e pelo botão Aceitar do banner de sugestão"
    - "docudata-backend/tests/test_task_confirmacao_sugestao.py, test_task_reabertura.py, test_bloqueio_manual.py — cobertura automatizada dos três comportamentos acima"
  key_links:
    - "TasksKanbanTab.tsx handleDrop -> setPendingMove -> ConfirmTransicaoModal (onConfirm) -> moverTaskKanban -> POST /tasks/{id}/mover -> patch_task -> _registrar_task_transicao -> task_transicoes"
    - "TasksKanbanTab.tsx botão Aceitar da sugestão -> setPendingSugestao -> ConfirmTransicaoModal (onConfirm) -> resolveTaskSugestao -> PATCH /tasks/sugestoes/{id} -> patch_task (mesmo caminho gated) -> task_transicoes"
    - "patch_task: campo coluna_kanban, de=concluida, para=em_andamento -> _registrar_reabertura -> task_reaberturas insert + tasks.contador_reaberturas incremento, na mesma escrita"
    - "TaskModal checkbox 'Bloqueada' -> bloqueado_manual/bloqueado_por (ao marcar) ou bloqueado_resolvido_por (ao desmarcar) -> PATCH /tasks/{id} -> patch_task gate 422 se faltar bloqueado_resolvido_por"
---

<objective>
Implementa a Phase 14 completa (TRANS-01..05): (1) nenhuma mudança de status de task acontece sem confirmação explícita do usuário em um modal, por qualquer caminho de UI — drag-and-drop no kanban e aceite do banner de sugestão da IA — e o aceite da sugestão para de gravar `coluna_kanban` direto, passando a usar o mesmo caminho gated (`patch_task`) que já grava em `task_transicoes`; (2) nova tabela `task_reaberturas` registra toda transição confirmada `concluida -> em_andamento`, com `task.contador_reaberturas` incrementado junto e `motivo` opcional; (3) task ganha os campos `bloqueado_manual`/`bloqueado_em`/`bloqueado_por`/`bloqueado_resolvido_por`/`bloqueado_resolvido_em`, com o backend exigindo `bloqueado_resolvido_por` (operacional|gerente) antes de aceitar desmarcar `bloqueado_manual`.

RBAC/papéis (Parte 6) e travamento automático por tempo (Parte 4, SprintCard baseline) são explicitamente fora de escopo desta phase (Phases 15/16) — nenhuma checagem de papel/permissão é adicionada aqui.

Purpose: fechar o gap real hoje existente — `resolve_task_sugestao` grava `coluna_kanban` direto sem confirmação nem `task_transicoes` — e adicionar as duas camadas de dado novas (reabertura, bloqueio manual) que alimentam as dimensões de score Qualidade Técnica e Autonomia em phases futuras (18/19), sem implementar score nenhum aqui.
Output: modal de confirmação reutilizável no kanban de tasks; `resolve_task_sugestao` corrigido; tabela `task_reaberturas` + contador; campos de bloqueio manual com gate de 422; testes automatizados para os três comportamentos.
</objective>

<execution_context>
@/Users/gabrielmezzalira/.claude/gsd-core/workflows/execute-plan.md
@/Users/gabrielmezzalira/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/STATE.md
@/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/.planning/intel/constraints.md
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Confirmação obrigatória, ponta a ponta — drag-and-drop e banner de sugestão pelo mesmo caminho gated (TRANS-01, TRANS-02)</name>
  <files>
    docudata-backend/routers/tasks.py,
    docudata-backend/models/schemas.py,
    docudata-backend/tests/test_task_confirmacao_sugestao.py,
    docudata-frontend/app/lib/api.ts,
    docudata-frontend/app/components/TasksKanbanTab.tsx
  </files>
  <read_first>
    - docudata-backend/routers/tasks.py lines 150-218 — `list_task_sugestoes` (select hoje é `"*, tasks(titulo, project_id)"`, sem `coluna_kanban`) e `resolve_task_sugestao` (o bug real: quando `data.aceita and row["acao"] == "mover_para_concluida"`, hoje faz `client.table("tasks").update({"coluna_kanban": "concluida", ...})` direto — sem gates, sem `task_transicoes`)
    - docudata-backend/routers/tasks.py lines 243-348 — `patch_task` (gates DoR/DoD/WIP, loop de `_registrar_task_transicao`, `updates` dict, `on_task_transition`) e `mover_task` (linha ~343-348, já delega para `patch_task` — é o padrão exato a replicar em `resolve_task_sugestao`)
    - docudata-backend/models/schemas.py lines 486-499 — `TaskSugestaoResponse`/`TaskSugestaoResolve` (adicionar `task_coluna_atual: Optional[str] = None` a `TaskSugestaoResponse`)
    - docudata-backend/tests/test_tasks_dod_gate.py — arquivo inteiro (174 linhas): é o padrão exato de mock do Supabase (`_make_mock_client`/`_patch_and_client`, monkeypatch de `get_client` em `routers.tasks`, `TestClient(app)` a partir de `main`) a reusar/adaptar para `task_sugestoes`
    - docudata-frontend/app/components/TasksKanbanTab.tsx lines 37-89 — constantes de estilo já existentes (`card`, `chip`, `inputSt`, `btnPrimary`, `btnGhost`) a reusar no novo modal, mesmo shell visual do `TaskModal` (lines 198-209: overlay fixed + card branco arredondado)
    - docudata-frontend/app/components/TasksKanbanTab.tsx lines 475-550 — `TasksKanbanTab` (estado `tasks`/`dragId`/`wipError`), `handleDrop` (chama `moverTaskKanban` direto hoje, sem confirmação)
    - docudata-frontend/app/components/TasksKanbanTab.tsx lines 495-531, 632-669 — estado `sugestoes`, `handleResolveSugestao` (chama `resolveTaskSugestao` direto hoje), e o banner JSX com os botões "Aceitar"/"Ignorar"
    - docudata-frontend/app/lib/api.ts lines 1205-1288 — `patchTaskKanban`, `moverTaskKanban`, `TaskSugestaoResponse`, `listTaskSugestoes`, `resolveTaskSugestao` — estilo exato de fetch function a espelhar
  </read_first>
  <action>
Backend — corrigir o gap real: em `docudata-backend/routers/tasks.py`, dentro de `resolve_task_sugestao`, troque o bloco `if data.aceita and row["acao"] == "mover_para_concluida": client.table("tasks").update({"coluna_kanban": "concluida", ...}).eq("id", task_id).execute()` por uma chamada `await patch_task(task_id, TaskUpdate(coluna_kanban="concluida", autor="sugestao_ia"))` — exatamente o mesmo padrão que `mover_task` já usa para delegar a `patch_task`. Isso faz o aceite da sugestão passar pelos mesmos gates de DoR/DoD/WIP e pela mesma gravação em `task_transicoes` que `PATCH /tasks/{id}` e `POST /tasks/{id}/mover` já usam — se `patch_task` levantar `HTTPException` (ex.: DoD com checklist incompleto), a exceção propaga e a sugestão continua não resolvida (`aceita` permanece `null`), o que é o comportamento correto: a sugestão só é marcada como aceita se a transição realmente for gravada. Adicione `coluna_kanban` ao select de `list_task_sugestoes` (`"*, tasks(titulo, project_id, coluna_kanban)"`) e ao de `resolve_task_sugestao` (já inclui `coluna_kanban` no select inicial, linha 185 — reuse) e ao schema `TaskSugestaoResponse` em `models/schemas.py` um novo campo opcional `task_coluna_atual: Optional[str] = None`, populado a partir de `task_info.get("coluna_kanban")` nas duas construções de `TaskSugestaoResponse` (`list_task_sugestoes` e ambos os retornos de `resolve_task_sugestao`). Isso dá ao frontend a coluna atual da task sem depender do estado local `tasks` (que pode estar filtrado).

Frontend — modal de confirmação reutilizável: em `docudata-frontend/app/components/TasksKanbanTab.tsx`, crie um novo componente `ConfirmTransicaoModal({ taskTitulo, de, para, onConfirm, onCancel, confirming }: {...})` no mesmo arquivo, logo após `TaskModal` (antes de `labelSt`). Reuse o mesmo shell visual de `TaskModal` (overlay `position: fixed, inset: 0, background: rgba(0,0,0,0.35)`, card branco `borderRadius: 16`, clique no overlay fecha via `onCancel` se `e.target === e.currentTarget`). Título "Confirmar mudança de status"; corpo: `Mover **{taskTitulo}** de **{label(de)}** para **{label(para)}**?` onde `label()` busca o `label` de exibição no array `COLUNAS` já existente no arquivo (fallback para o próprio valor se não encontrado); dois botões com os estilos `btnGhost` ("Cancelar", chama `onCancel`) e `btnPrimary` ("Confirmar"/"Movendo…" conforme `confirming`, chama `onConfirm`), ambos `disabled={confirming}`.

No componente `TasksKanbanTab`, adicione `const [pendingMove, setPendingMove] = useState<{ taskId: string; taskTitulo: string; de: Coluna; para: Coluna } | null>(null);`, `const [pendingSugestao, setPendingSugestao] = useState<TaskSugestaoResponse | null>(null);` e `const [confirming, setConfirming] = useState(false);`. Reescreva `handleDrop(coluna)`: em vez de chamar `moverTaskKanban` direto, se a task existir e `task.coluna_kanban !== coluna`, apenas `setPendingMove({ taskId: dragId, taskTitulo: task.titulo, de: task.coluna_kanban, para: coluna })` e `setDragId(null)` (nenhuma chamada de API ainda — cancelar depois não deixa rastro nenhum). Adicione `confirmPendingMove()`: se `!pendingMove`, retorna; seta `confirming=true`, chama `moverTaskKanban(pendingMove.taskId, pendingMove.para)`, em sucesso atualiza `tasks` (mesmo padrão de `upsertTask`) e limpa `pendingMove`; em erro 409 seta `wipError` (mesmo padrão já existente em `handleDrop`), senão `alert(msg)`; sempre limpa `confirming=false` no `finally`. Adicione `cancelPendingMove()`: apenas `setPendingMove(null)` (nenhuma chamada de API).

No botão "Aceitar" da sugestão (dentro do bloco `sugestoes.map`), troque `onClick={() => handleResolveSugestao(s.id, true)}` por `onClick={() => setPendingSugestao(s)}` — não chama a API ainda. O botão "Ignorar" continua chamando `handleResolveSugestao(s.id, false)` direto, sem modal (recusar uma sugestão não move nenhuma task, não precisa de confirmação). Adicione `confirmPendingSugestao()`: se `!pendingSugestao`, retorna; seta `confirming=true`, chama `handleResolveSugestao(pendingSugestao.id, true)` (já existente, que já chama `resolveTaskSugestao` e `load()` em caso de aceite), limpa `pendingSugestao` e `confirming=false` no `finally`. Adicione `cancelPendingSugestao()`: apenas `setPendingSugestao(null)`.

Renderize, no fim do JSX de `TasksKanbanTab` (junto aos outros modais condicionais `createModal`/`editModal`): `{pendingMove !== null && <ConfirmTransicaoModal taskTitulo={pendingMove.taskTitulo} de={pendingMove.de} para={pendingMove.para} onConfirm={confirmPendingMove} onCancel={cancelPendingMove} confirming={confirming} />}` e `{pendingSugestao !== null && <ConfirmTransicaoModal taskTitulo={pendingSugestao.task_titulo} de={pendingSugestao.task_coluna_atual ?? "atual"} para="concluida" onConfirm={confirmPendingSugestao} onCancel={cancelPendingSugestao} confirming={confirming} />}`. Adicione `task_coluna_atual?: string | null;` à interface `TaskSugestaoResponse` em `docudata-frontend/app/lib/api.ts` (mesmo arquivo, mesma interface já existente nas linhas ~1260-1269).

Nota de escopo: "chamada de API" (Parte 1) é coberta pelo fato de `PATCH /tasks/{id}`, `POST /tasks/{id}/mover` e agora `PATCH /tasks/sugestoes/{id}` compartilharem o mesmo caminho gated de `patch_task` — não há confirmação de UI possível numa chamada de API direta (curl/script) num sistema sem tela própria para isso e sem auth (v1); a garantia aqui é que qualquer caminho que originar de uma ação de UI (drag-and-drop, aceite de sugestão) passa pelo modal antes de qualquer chamada, e que todos os caminhos gravam a mesma transição auditável em `task_transicoes`.
  </action>
  <verify>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && python3 -c "import ast; ast.parse(open('routers/tasks.py').read()); ast.parse(open('models/schemas.py').read()); print('syntax OK')"</automated>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && .venv/bin/pytest tests/test_task_confirmacao_sugestao.py -q</automated>
    <automated>grep -c "ConfirmTransicaoModal" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-frontend/app/components/TasksKanbanTab.tsx"</automated>
    <automated>grep -c "await patch_task(task_id, TaskUpdate(coluna_kanban=\"concluida\"" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend/routers/tasks.py"</automated>
  </verify>
  <done>
    `resolve_task_sugestao` não faz mais update direto de `coluna_kanban` — delega a `patch_task` (mesmos gates DoR/DoD/WIP, mesma gravação em `task_transicoes`); `ConfirmTransicaoModal` existe e é usado tanto por `handleDrop` (drag-and-drop) quanto pelo botão "Aceitar" do banner de sugestão; cancelar em qualquer um dos dois fecha o modal sem chamar `moverTaskKanban`/`resolveTaskSugestao`; testes novos em `test_task_confirmacao_sugestao.py` cobrem o caminho feliz (sugestão aceita grava transição) e o caminho de gate (sugestão aceita numa task com checklist incompleto retorna 409 e não marca a sugestão como aceita).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Reabertura de task — task_reaberturas + contador_reaberturas + motivo opcional (TRANS-03)</name>
  <files>
    docudata-backend/supabase_schema.sql,
    docudata-backend/models/schemas.py,
    docudata-backend/routers/tasks.py,
    docudata-backend/tests/test_task_reabertura.py,
    docudata-frontend/app/lib/api.ts,
    docudata-frontend/app/components/TasksKanbanTab.tsx
  </files>
  <read_first>
    - docudata-backend/supabase_schema.sql lines 255-288 — definição atual de `tasks` e `task_transicoes` (estilo exato de `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` já usado neste arquivo, um bloco de migration por phase — ver comentários `-- Phase N: ...` ao longo do arquivo, ex. linha 62 `-- Phase 7: ...`, linha 114 `-- Phase 9: ...`)
    - docudata-backend/routers/tasks.py lines 25-59 (`_registrar_task_transicao`, já modificada na Task 1 apenas se necessário — nesta task, mude o `return` para devolver o `id` da linha inserida em `task_transicoes`, hoje a função não retorna nada) e lines 302-341 (`patch_task`: loop de transições linhas 305-309, bloco `bloqueado` linhas 311-312, montagem de `updates` linha 314 em diante)
    - docudata-backend/models/schemas.py lines 431-446 (`TaskResponse`) e lines 408-428 (`TaskUpdate`, já tem `motivo: Optional[str] = None` genérico — reusar para o motivo da reabertura, não criar campo novo)
    - docudata-frontend/app/components/TasksKanbanTab.tsx — `ConfirmTransicaoModal` e `confirmPendingMove`/`moverTaskKanban` criados na Task 1 (ler o resultado da Task 1 antes de editar)
    - docudata-frontend/app/lib/api.ts lines 1235-1245 (`moverTaskKanban`, hoje só aceita `autor`)
  </read_first>
  <behavior>
    - Teste: `PATCH /tasks/{id}` movendo uma task de `coluna_kanban="concluida"` para `"em_andamento"` -> grava uma linha em `task_reaberturas` com `task_id`, `transicao_id` (o id da transição recém-criada em `task_transicoes`), `operacional_id` (o `operacional_id` atual da task), `motivo` (o que veio em `data.motivo`, pode ser `None`) e `timestamp`; `tasks.contador_reaberturas` no payload de update passa a ser `(contador atual ou 0) + 1`.
    - Teste: mesma chamada mas task já tem `contador_reaberturas=2` -> novo valor gravado é `3`.
    - Teste: `PATCH /tasks/{id}` movendo de `"em_andamento"` para `"concluida"` (não é reabertura) -> nenhuma linha inserida em `task_reaberturas`, `contador_reaberturas` não aparece no dict de `updates`.
    - Teste: `PATCH /tasks/{id}` movendo de `"concluida"` para `"planejado"` (saída de concluida que não é para em_andamento) -> nenhuma linha inserida em `task_reaberturas` (regra explícita: só `concluida -> em_andamento` conta como reabertura).
    - Teste: `motivo` é opcional — reabertura sem `data.motivo` grava `motivo=None` em `task_reaberturas` sem erro.
  </behavior>
  <action>
Migration: em `docudata-backend/supabase_schema.sql`, adicione ao final do arquivo um novo bloco comentado `-- Phase 14: Confirmação de Transição + Reabertura + Bloqueio Manual`, seguindo o estilo exato dos blocos anteriores (`CREATE TABLE IF NOT EXISTS` com colunas `id uuid PRIMARY KEY DEFAULT gen_random_uuid()`, `timestamptz DEFAULT now()`, `CREATE INDEX IF NOT EXISTS`). Crie `task_reaberturas` com colunas `id` (uuid PK), `task_id` (uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE), `transicao_id` (uuid REFERENCES task_transicoes(id) ON DELETE SET NULL), `operacional_id` (uuid REFERENCES operacionais(id) ON DELETE SET NULL), `motivo` (text, nullable — TRANS-03 exige opcional), `timestamp` (timestamptz DEFAULT now()); mais um índice em `task_reaberturas(task_id)`. Na mesma migration, `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS contador_reaberturas int NOT NULL DEFAULT 0;` e, já antecipando a Task 3 (para não editar este arquivo de novo depois), as cinco colunas de bloqueio manual: `bloqueado_manual boolean NOT NULL DEFAULT false`, `bloqueado_em timestamptz`, `bloqueado_por text`, `bloqueado_resolvido_por text` com `CHECK (bloqueado_resolvido_por IS NULL OR bloqueado_resolvido_por IN ('operacional','gerente'))`, `bloqueado_resolvido_em timestamptz` — todas via `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS`. A Task 3 não deve tocar `supabase_schema.sql` de novo — as colunas já existirão a partir desta migration.

Backend: em `_registrar_task_transicao` (`docudata-backend/routers/tasks.py`), capture a resposta do insert (`resp = client.table("task_transicoes").insert({...}).execute()`) e mude o `return` da função (hoje `-> None`) para `return resp.data[0]["id"] if resp.data else None`, tipado `-> Optional[str]`. Adicione um novo helper `_registrar_reabertura(client, task_id, transicao_id, operacional_id, motivo, agora)` que faz `client.table("task_reaberturas").insert({"task_id": task_id, "transicao_id": transicao_id, "operacional_id": operacional_id, "motivo": motivo, "timestamp": agora.isoformat()}).execute()`. Dentro de `patch_task`, no loop `for campo in ("coluna_kanban", "operacional_id", "sprint_id"): ...`, capture o retorno de `_registrar_task_transicao` numa variável (ex.: `transicao_id = _registrar_task_transicao(...)`) e, logo em seguida, quando `campo == "coluna_kanban"` e o valor anterior da task (`task.get("coluna_kanban")`) era `"concluida"` e `novo_valor == "em_andamento"`, chame `_registrar_reabertura(client, task_id, transicao_id, task.get("operacional_id"), data.motivo, agora)` e marque uma flag local (ex.: `houve_reabertura = True`) para uso logo abaixo. Depois que o dict `updates` é inicializado (`updates: dict = {"updated_at": agora.isoformat()}`, linha ~314), se `houve_reabertura`, adicione `updates["contador_reaberturas"] = (task.get("contador_reaberturas") or 0) + 1`. Adicione `contador_reaberturas: int = 0` a `TaskResponse` em `models/schemas.py` (não adicione a `TaskUpdate` — é sempre server-computed, nunca vindo do cliente).

Frontend — motivo opcional no modal de reabertura: em `ConfirmTransicaoModal` (criado na Task 1), quando `de === "concluida" && para === "em_andamento"`, renderize um campo extra abaixo do texto de confirmação: label "Motivo da reabertura (opcional)" com um `<textarea>` (reuse `inputSt` com `resize: "vertical"`, mesmo padrão do campo "Descrição" em `TaskModal`) controlado por um novo estado `motivo`/`setMotivo` no componente pai (`pendingMove`), passado como prop opcional `motivo`/`onMotivoChange` ao modal. Em `confirmPendingMove`, passe esse motivo para `moverTaskKanban(pendingMove.taskId, pendingMove.para, undefined, motivo || undefined)`. Estenda a assinatura de `moverTaskKanban` em `docudata-frontend/app/lib/api.ts` para `(id: string, coluna_destino: string, autor?: string, motivo?: string)`, adicionando `motivo` ao `URLSearchParams` (`if (motivo) q.set("motivo", motivo);`) só se presente. No backend, estenda `mover_task` (`docudata-backend/routers/tasks.py`) para aceitar `motivo: Optional[str] = None` como query param e repassar em `TaskUpdate(coluna_kanban=coluna_destino, autor=autor, motivo=motivo)`.

Backend tests: crie `docudata-backend/tests/test_task_reabertura.py` reusando o padrão `_make_mock_client`/`_patch_and_client` de `tests/test_tasks_dod_gate.py` (adaptar o mock de `task_transicoes.insert` para devolver um `id` fixo no payload de resposta, e adicionar um mock para a tabela `task_reaberturas.insert` que captura o payload recebido para asserção). Cubra os cinco casos do `<behavior>` acima.
  </action>
  <verify>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && python3 -c "import ast; ast.parse(open('routers/tasks.py').read()); ast.parse(open('models/schemas.py').read()); print('syntax OK')"</automated>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && .venv/bin/pytest tests/test_task_reabertura.py -q</automated>
    <automated>grep -c "task_reaberturas" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend/supabase_schema.sql"</automated>
    <automated>grep -c "contador_reaberturas" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend/models/schemas.py"</automated>
  </verify>
  <done>
    Confirmar uma transição `concluida -> em_andamento` (via drag-and-drop) grava uma linha em `task_reaberturas` ligada à `task_transicoes` recém-criada e incrementa `tasks.contador_reaberturas`; nenhuma outra transição grava em `task_reaberturas`; motivo é opcional em todo o caminho (schema, endpoint, UI); todos os testes de `test_task_reabertura.py` passam.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Bloqueio manual com captura de quem resolveu (TRANS-04, TRANS-05)</name>
  <files>
    docudata-backend/models/schemas.py,
    docudata-backend/routers/tasks.py,
    docudata-backend/tests/test_bloqueio_manual.py,
    docudata-frontend/app/lib/api.ts,
    docudata-frontend/app/components/TasksKanbanTab.tsx
  </files>
  <read_first>
    - docudata-backend/supabase_schema.sql — colunas `bloqueado_manual`/`bloqueado_em`/`bloqueado_por`/`bloqueado_resolvido_por`/`bloqueado_resolvido_em` já criadas pela Task 2 — esta task NÃO edita `supabase_schema.sql` de novo
    - docudata-backend/models/schemas.py lines 408-428 (`TaskUpdate`, já tem `bloqueado: Optional[bool]`/`motivo_bloqueio: Optional[str]` — campos legados, NÃO remover, mantidos como estão) e lines 431-446 (`TaskResponse`)
    - docudata-backend/routers/tasks.py lines 275-300 (bloco de validação DoR/DoD/WIP em `patch_task`, todo ANTES de `agora = datetime.now(timezone.utc)` — o novo gate 422 de bloqueio entra nesse mesmo bloco, antes de qualquer escrita) e lines 314-327 (montagem final de `updates` e o tratamento explícito de `bloqueado` na linha 324-325 — o mesmo padrão para os campos novos)
    - docudata-frontend/app/components/TasksKanbanTab.tsx lines 111-122 (estado do `TaskModal`: `bloqueado`, `motivoBloqueio`) e lines 270-294 (JSX do checkbox "Bloqueada" + input de motivo, dentro do bloco `mode === "edit"`)
    - docudata-frontend/app/lib/api.ts lines 1139-1155 (`TaskKanbanResponse`) e lines 1205-1233 (`patchTaskKanban`)
  </read_first>
  <behavior>
    - Teste: `PATCH /tasks/{id}` com `bloqueado_manual=true` numa task com `bloqueado_manual` atualmente `false` -> 200; `updates` gravados incluem `bloqueado_manual=true`, `bloqueado_em` (timestamp do request) e `bloqueado_por` (o que veio em `data.bloqueado_por`).
    - Teste: `PATCH /tasks/{id}` com `bloqueado_manual=false` numa task com `bloqueado_manual` atualmente `true`, SEM `bloqueado_resolvido_por` no payload -> 422, `detail` menciona "resolveu"; nenhuma escrita em `tasks.update` acontece (a exceção é levantada antes do `.update(...)`).
    - Teste: mesma chamada, mas com `bloqueado_resolvido_por="operacional"` -> 200; `updates` gravados incluem `bloqueado_manual=false`, `bloqueado_resolvido_por="operacional"` e `bloqueado_resolvido_em` (timestamp do request).
    - Teste: `bloqueado_resolvido_por` com valor fora de `{"operacional", "gerente"}` (ex.: `"cliente"`) -> 422 de validação do Pydantic (`TaskUpdate`), antes mesmo de chegar na lógica do endpoint.
    - Teste: `PATCH /tasks/{id}` sem tocar em `bloqueado_manual` (campo ausente do payload) -> 200, nenhum dos campos de bloqueio aparece em `updates`.
  </behavior>
  <action>
Backend schemas (`docudata-backend/models/schemas.py`): adicione a `TaskUpdate` os campos `bloqueado_manual: Optional[bool] = None`, `bloqueado_por: Optional[str] = None`, `bloqueado_resolvido_por: Optional[str] = None`, com um `@field_validator("bloqueado_resolvido_por")` que, se o valor não for `None`, exige que esteja em `{"operacional", "gerente"}` (mesmo padrão de `field_validator` já usado em `FuncionalidadeCreate.prioridade_valida`/`coluna_valida` neste arquivo — levantar `ValueError` com mensagem clara). Adicione a `TaskResponse` os campos `bloqueado_manual: bool = False`, `bloqueado_em: Optional[datetime] = None`, `bloqueado_por: Optional[str] = None`, `bloqueado_resolvido_por: Optional[str] = None`, `bloqueado_resolvido_em: Optional[datetime] = None`. NÃO remova nem renomeie os campos legados `bloqueado`/`motivo_bloqueio` — continuam existindo e funcionando exatamente como hoje (WIP check e renderização do `TaskCard` dependem deles).

Backend gate (`docudata-backend/routers/tasks.py`, dentro de `patch_task`): logo após o bloco existente de DoD (linhas ~286-296) e antes de `op_efetivo = ...`/`check_wip(...)` (dentro do mesmo `if coluna_nova is not None and coluna_nova != coluna_atual:` NÃO — este gate roda independentemente de mudança de coluna, então coloque-o fora desse `if`, ainda antes de `agora = datetime.now(timezone.utc)`): se `data.bloqueado_manual is not None and data.bloqueado_manual != task.get("bloqueado_manual", False) and data.bloqueado_manual is False`, então exija `data.bloqueado_resolvido_por in ("operacional", "gerente")` — se não, `raise HTTPException(status_code=422, detail="Informe quem resolveu o bloqueio (operacional ou gerente) antes de desmarcar.")`. Isso garante que a exceção é levantada antes de qualquer `.update(...)` na função (mesma garantia de "fail fast" que os gates de DoR/DoD/WIP já têm). Depois que o dict `updates` é montado (após a linha `if data.bloqueado is not None: updates["bloqueado"] = data.bloqueado`), adicione: se `data.bloqueado_manual is not None and data.bloqueado_manual != task.get("bloqueado_manual", False)`: `updates["bloqueado_manual"] = data.bloqueado_manual`; se `data.bloqueado_manual is True`, também `updates["bloqueado_em"] = agora.isoformat()` e `updates["bloqueado_por"] = data.bloqueado_por`; senão (`False`, já validado acima), `updates["bloqueado_resolvido_por"] = data.bloqueado_resolvido_por` e `updates["bloqueado_resolvido_em"] = agora.isoformat()`.

Frontend (`docudata-frontend/app/components/TasksKanbanTab.tsx`, dentro de `TaskModal`): adicione estado `const [bloqueadoPor, setBloqueadoPor] = useState(task?.bloqueado_por ?? "");`, `const [bloqueadoResolvidoPor, setBloqueadoResolvidoPor] = useState("");` e `const jaEstavaBloqueadoManual = task?.bloqueado_manual ?? false;`. No JSX existente do checkbox "Bloqueada" (linhas ~272-294, dentro de `mode === "edit"`): quando `bloqueado === true && !jaEstavaBloqueadoManual` (acabou de marcar), mostre um input extra "Quem bloqueou?" controlado por `bloqueadoPor`/`setBloqueadoPor`, ao lado do já existente "Motivo do bloqueio". Quando `jaEstavaBloqueadoManual && !bloqueado` (acabou de desmarcar uma task que já estava bloqueada), mostre um `<select>` obrigatório "Quem resolveu? *" com opções `""` (placeholder "Selecione..."), `"operacional"`, `"gerente"`, controlado por `bloqueadoResolvidoPor`/`setBloqueadoResolvidoPor`, reusando `inputSt`. Em `handleSubmit`, antes do `try`, adicione a validação: `if (jaEstavaBloqueadoManual && !bloqueado && !bloqueadoResolvidoPor) { setErr("Informe quem resolveu o bloqueio."); return; }`. No payload de `patchTaskKanban` (branch `mode === "edit"`), adicione: `bloqueado_manual: bloqueado`, `bloqueado_por: (bloqueado && !jaEstavaBloqueadoManual) ? (bloqueadoPor.trim() || undefined) : undefined`, `bloqueado_resolvido_por: (!bloqueado && jaEstavaBloqueadoManual) ? bloqueadoResolvidoPor : undefined`. Estenda o tipo do parâmetro `data` de `patchTaskKanban` em `docudata-frontend/app/lib/api.ts` com `bloqueado_manual?: boolean; bloqueado_por?: string; bloqueado_resolvido_por?: string;`, e a interface `TaskKanbanResponse` com `bloqueado_manual: boolean; bloqueado_em?: string | null; bloqueado_por?: string | null; bloqueado_resolvido_por?: string | null; bloqueado_resolvido_em?: string | null; contador_reaberturas: number;` (este último cobre também a Task 2).

Backend tests: crie `docudata-backend/tests/test_bloqueio_manual.py` reusando o padrão `_make_mock_client`/`_patch_and_client` de `tests/test_tasks_dod_gate.py` (a fixture de task base precisa incluir `bloqueado_manual: False` e demais campos novos). Cubra os cinco casos do `<behavior>` acima.
  </action>
  <verify>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && python3 -c "import ast; ast.parse(open('routers/tasks.py').read()); ast.parse(open('models/schemas.py').read()); print('syntax OK')"</automated>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && .venv/bin/pytest tests/test_bloqueio_manual.py -q</automated>
    <automated>cd "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-backend" && .venv/bin/pytest tests/test_tasks_dod_gate.py tests/test_task_reabertura.py tests/test_task_confirmacao_sugestao.py -q</automated>
    <automated>grep -c "bloqueado_resolvido_por" "/Users/gabrielmezzalira/Documents/Faculdade/CIti/Liderança Dados/Agentes/Documentador/docudata-frontend/app/components/TasksKanbanTab.tsx"</automated>
  </verify>
  <done>
    `PATCH /tasks/{id}` com `bloqueado_manual=false` numa task previamente bloqueada e sem `bloqueado_resolvido_por` retorna 422 antes de qualquer escrita; com `bloqueado_resolvido_por` válido grava `bloqueado_resolvido_por`/`bloqueado_resolvido_em`; marcar `bloqueado_manual=true` grava `bloqueado_em`/`bloqueado_por`; o checkbox "Bloqueada" do `TaskModal` aciona `bloqueado_manual` e pede quem bloqueou/resolveu na hora certa; toda a suíte de testes de `tasks.py` (DoD, reabertura, confirmação de sugestão, bloqueio) passa junto.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client -> PATCH /tasks/{id}, POST /tasks/{id}/mover, PATCH /tasks/sugestoes/{id} | todo o payload (coluna_kanban, motivo, bloqueado_por, bloqueado_resolvido_por) é fornecido pelo cliente sem autenticação (v1 sem auth, por decisão de projeto) |
| client -> ConfirmTransicaoModal | o modal é só UX — nenhuma garantia de segurança, apenas de fluxo; a garantia real está no backend (gates em patch_task) |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-14-01 | Information Disclosure | Todos os endpoints de tasks (sem auth v1) | low | accept | Postura idêntica a todos os endpoints já existentes no projeto (CLAUDE.md "Sem auth v1") — não é um risco novo introduzido por esta phase |
| T-14-02 | Tampering | PATCH /tasks/sugestoes/{id} -> patch_task | medium | mitigate | Roteando `resolve_task_sugestao` pelo mesmo `patch_task` usado por PATCH/mover, os gates de DoR/DoD/WIP passam a valer também para o aceite da sugestão — elimina o bypass que existia hoje (update direto de `coluna_kanban` sem gate nenhum) |
| T-14-03 | Repudiation | task_reaberturas.operacional_id | low | accept | `operacional_id` vem de `task.get("operacional_id")` no servidor (não é client-supplied), reduzindo o risco de forjar de quem é a reabertura; sem auth, ainda é possível qualquer cliente mover a task de outro operacional — mesma postura de confiança do resto do sistema |
| T-14-04 | Tampering | PATCH /tasks/{id} — bloqueado_resolvido_por client-supplied | low | accept | Restrito por `field_validator` a `{"operacional","gerente"}` (não aceita texto livre), mas sem auth qualquer cliente pode alegar ser "gerente" — aceito como limitação conhecida do MVP sem RBAC (Phase 16), não deve ser resolvido aqui |

</threat_model>

<verification>
- `python3 -c "import ast; ast.parse(...)"` em `routers/tasks.py` e `models/schemas.py`: ambos parseiam sem SyntaxError
- `docudata-backend/.venv/bin/pytest tests/test_task_confirmacao_sugestao.py tests/test_task_reabertura.py tests/test_bloqueio_manual.py tests/test_tasks_dod_gate.py -q`: todos passam, incluindo os testes já existentes de DoD (garante que nada foi quebrado)
- `grep -c "ConfirmTransicaoModal"` em `TasksKanbanTab.tsx`: >= 1 (componente definido e usado)
- `grep -c "task_reaberturas"` em `supabase_schema.sql`: >= 1 (tabela criada)
- `grep -c "contador_reaberturas"` em `models/schemas.py`: >= 1
- `grep -c "bloqueado_resolvido_por"` em `TasksKanbanTab.tsx`: >= 1 (UI de "quem resolveu" existe)
- Manual spot-check (não automatizado): arrastar uma task de `concluida` para `em_andamento` no kanban mostra o modal com campo de motivo opcional; confirmar grava a transição e uma linha em `task_reaberturas`; cancelar não move o card
</verification>

<success_criteria>
- [ ] Drag-and-drop no kanban de tasks exige confirmação explícita antes de qualquer chamada de API — TRANS-01
- [ ] Aceite do banner de sugestão da IA exige confirmação explícita e passa a gravar em task_transicoes pelo mesmo caminho gated do drag-and-drop — TRANS-01, TRANS-02
- [ ] Cancelar em qualquer um dos dois modais não altera nenhum estado e não chama nenhuma API
- [ ] Toda transição confirmada concluida->em_andamento grava task_reaberturas + incrementa contador_reaberturas; nenhuma outra saída de concluida grava — TRANS-03
- [ ] motivo da reabertura é opcional em schema, endpoint e UI
- [ ] Task ganha bloqueado_manual/bloqueado_em/bloqueado_por/bloqueado_resolvido_por/bloqueado_resolvido_em — TRANS-04
- [ ] Desmarcar bloqueado_manual sem informar bloqueado_resolvido_por retorna 422 antes de qualquer escrita — TRANS-05
- [ ] Nenhuma checagem de papel/permissão (RBAC) foi adicionada — fora de escopo desta phase
- [ ] Campos legados bloqueado/motivo_bloqueio, WIP check e DoD gate permanecem funcionando sem alteração de comportamento
</success_criteria>

<output>
Create `.planning/quick/260903-awe-implementar-phase-14-confirmacao-de-tran/260903-awe-SUMMARY.md` when done
</output>
