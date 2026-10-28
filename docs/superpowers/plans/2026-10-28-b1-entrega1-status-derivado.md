# B1 · Entrega 1 — Status da funcionalidade derivado das tasks — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O status da funcionalidade passa a ser calculado pelas tasks dela. Assim o Painel (WIP, Throughput, eficiência de fluxo e itens em atenção) volta a refletir o andamento real.

**Architecture:** Um serviço novo (`services/status_funcionalidade.py`) concentra três coisas: a regra pura `status_derivado`, o registro da transição em `transicoes_status` (que hoje mora dentro do PATCH de funcionalidade) e `sincronizar_status`. Todas as rotas que mexem em task chamam `sincronizar_status` no fim, best-effort. O PATCH manual de status responde 409 quando a funcionalidade tem tasks. Um script faz o backfill. Não há migração.

**Tech Stack:** FastAPI + supabase-py (Python 3), pytest com `tests/fake_supabase.py`; Next.js 15 / React 19 com estilos inline e `app/components/ds`.

**Spec:** `docs/superpowers/specs/2026-10-28-acompanhamento-projetos-design.md` (seção 2 e item 1 da seção 7)

## Global Constraints

- Status da funcionalidade: `nao_iniciada`, `em_andamento`, `em_ajuste` e `concluida`. Não existe status novo.
- Regra, ignorando tasks com `extra = true`:
  - sem tasks → `None` (o status não muda);
  - todas em `planejado` → `nao_iniciada`;
  - todas em `concluida` → `concluida`;
  - qualquer outro caso → `em_andamento`.
- `em_ajuste` continua manual. Se o status atual é `em_ajuste` e o derivado é `em_andamento`, o status fica `em_ajuste`; os outros casos (`nao_iniciada` e `concluida`) sobrescrevem.
- Toda mudança de status grava uma linha em `transicoes_status` com `campo='status'`, `de`, `para`, `autor`, `timestamp` e `duracao_fase_anterior_segundos` (desde a última transição de status, ou desde `created_at`).
- Se o status sai de `concluida`, chama `revogar_se_aprovada(client, funcionalidade_id, "revogada: status derivado das tasks")`.
- `sincronizar_status` nunca derruba a rota que o chamou: exceções viram `logger.exception` e a rota responde normalmente.
- PATCH manual de `status` numa funcionalidade com pelo menos uma task não extra → HTTP 409, `detail="O status vem das tasks desta funcionalidade."`.
- Backend: `cd docudata-backend && python3 -m pytest -q`. `tests/test_security.py::test_dependencias_separam_browser_automacoes_e_webhooks_publicos` já falha em Python 3.13 e não é regressão.
- Frontend: `cd docudata-frontend && npx tsc --noEmit && npm test`. A worktree não tem `node_modules`: criar um symlink para `../Documentador/docudata-frontend/node_modules`, removê-lo antes do commit e restaurar `tsconfig.tsbuildinfo` e `next-env.d.ts`.
- Nunca commitar `docudata-backend/supabase_schema.sql` (mudança local do usuário) nem `.planning/`. Stage por caminho explícito.
- Commits em português no estilo `feat(escopo): ...`, com o trailer `Co-Authored-By` do modelo que escreveu.

---

### Task 1: Serviço de status derivado

**Files:**
- Create: `docudata-backend/services/status_funcionalidade.py`
- Modify: `docudata-backend/routers/funcionalidades.py` (PATCH, ~linhas 290–345: trocar o bloco que grava `transicoes_status` pela função nova)
- Test: `docudata-backend/tests/test_status_funcionalidade.py`

**Interfaces:**
- Produces:
  - `status_derivado(tasks: list[dict]) -> str | None` (puro);
  - `registrar_transicao_status(client, func: dict, novo: str, autor: str | None, motivo: str | None, agora: datetime) -> None`;
  - `sincronizar_status(client, funcionalidade_id: str | None, autor: str | None = "sistema") -> str | None`, que devolve o status novo se mudou, ou `None`. É best-effort e não levanta exceção.
  - `funcionalidade_tem_tasks(client, funcionalidade_id: str) -> bool`.

- [ ] **Step 1: Testes que falham**

```python
# docudata-backend/tests/test_status_funcionalidade.py
import pytest
from services.status_funcionalidade import status_derivado, sincronizar_status

def t(coluna, extra=False):
    return {"coluna_kanban": coluna, "extra": extra}

@pytest.mark.parametrize("tasks,esperado", [
    ([], None),
    ([t("concluida", extra=True)], None),
    ([t("planejado"), t("planejado")], "nao_iniciada"),
    ([t("planejado"), t("em_andamento")], "em_andamento"),
    ([t("planejado"), t("concluida")], "em_andamento"),
    ([t("pendente_aprovacao")], "em_andamento"),
    ([t("concluida"), t("concluida")], "concluida"),
    ([t("concluida"), t("planejado", extra=True)], "concluida"),
])
def test_status_derivado(tasks, esperado):
    assert status_derivado(tasks) == esperado
```

Testes de `sincronizar_status` com `tests/fake_supabase.py`. Ler o fake antes e seguir o padrão de montagem dos outros testes de serviço:
- funcionalidade `nao_iniciada` com uma task `em_andamento`: o status vira `em_andamento` e grava 1 linha em `transicoes_status` com `de="nao_iniciada"`, `para="em_andamento"` e `campo="status"`;
- status já igual ao derivado: nenhuma escrita, devolve `None`;
- `em_ajuste` com derivado `em_andamento`: fica `em_ajuste`, nenhuma escrita;
- `concluida` aprovada (`aprovada_em` preenchido) e uma task volta para `em_andamento`: o status vira `em_andamento` e `aprovada_em` vira `None`;
- funcionalidade sem tasks: devolve `None` e não escreve;
- `funcionalidade_id=None`: devolve `None`;
- o client levanta exceção: `sincronizar_status` devolve `None` sem propagar.

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && python3 -m pytest tests/test_status_funcionalidade.py -q`
Expected: FAIL (`ModuleNotFoundError: services.status_funcionalidade`).

- [ ] **Step 3: Implementar**

```python
# docudata-backend/services/status_funcionalidade.py
"""Status da funcionalidade derivado das tasks (Rodada B1, entrega 1).

Regra (extras ignoradas): sem tasks → não mexe; todas em planejado →
nao_iniciada; todas concluídas → concluida; senão → em_andamento.
`em_ajuste` é manual e só cede para nao_iniciada/concluida."""
import logging
from datetime import datetime, timezone

from services.aprovacao_funcionalidade import revogar_se_aprovada

logger = logging.getLogger(__name__)


def status_derivado(tasks: list[dict]) -> str | None:
    colunas = [t.get("coluna_kanban") for t in tasks if not t.get("extra")]
    if not colunas:
        return None
    if all(c == "planejado" for c in colunas):
        return "nao_iniciada"
    if all(c == "concluida" for c in colunas):
        return "concluida"
    return "em_andamento"


def _ts(valor: str) -> datetime:
    dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def registrar_transicao_status(client, func: dict, novo: str, autor: str | None, motivo: str | None, agora: datetime) -> None:
    anterior = (
        client.table("transicoes_status")
        .select("timestamp")
        .eq("funcionalidade_id", func["id"])
        .eq("campo", "status")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    base = anterior.data[0]["timestamp"] if anterior.data else func["created_at"]
    duracao = int((agora - _ts(base)).total_seconds())
    client.table("transicoes_status").insert({
        "funcionalidade_id": func["id"],
        "campo": "status",
        "de": func.get("status"),
        "para": novo,
        "autor": autor,
        "timestamp": agora.isoformat(),
        "motivo": motivo,
        "duracao_fase_anterior_segundos": duracao,
    }).execute()


def _tasks_da_funcionalidade(client, funcionalidade_id: str) -> list[dict]:
    return (
        client.table("tasks")
        .select("coluna_kanban, extra")
        .eq("funcionalidade_id", funcionalidade_id)
        .execute()
        .data or []
    )


def funcionalidade_tem_tasks(client, funcionalidade_id: str) -> bool:
    return status_derivado(_tasks_da_funcionalidade(client, funcionalidade_id)) is not None


def sincronizar_status(client, funcionalidade_id: str | None, autor: str | None = "sistema") -> str | None:
    if not funcionalidade_id:
        return None
    try:
        resp = client.table("funcionalidades").select("*").eq("id", funcionalidade_id).execute()
        if not resp.data:
            return None
        func = resp.data[0]
        novo = status_derivado(_tasks_da_funcionalidade(client, funcionalidade_id))
        atual = func.get("status")
        if novo is None or novo == atual:
            return None
        if atual == "em_ajuste" and novo == "em_andamento":
            return None
        agora = datetime.now(timezone.utc)
        registrar_transicao_status(client, func, novo, autor, "derivado das tasks", agora)
        client.table("funcionalidades").update({"status": novo}).eq("id", funcionalidade_id).execute()
        if atual == "concluida":
            revogar_se_aprovada(client, funcionalidade_id, "revogada: status derivado das tasks")
        return novo
    except Exception:
        logger.exception("falha ao sincronizar status da funcionalidade %s", funcionalidade_id)
        return None
```

No PATCH de `routers/funcionalidades.py`, troque o bloco "Record transitions for status fields that changed" (o laço `for campo in ("status",)` que consulta e insere em `transicoes_status`) por:

```python
    if data.status is not None and data.status != func.get("status"):
        registrar_transicao_status(client, func, data.status, data.autor, data.motivo, agora)
```

Importe `registrar_transicao_status` de `services.status_funcionalidade`. O resto do PATCH continua igual.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd docudata-backend && python3 -m pytest tests/test_status_funcionalidade.py tests/ -q -k "funcionalidade or painel"`
Expected: PASS. Os testes existentes do PATCH de funcionalidade seguem passando.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/services/status_funcionalidade.py docudata-backend/routers/funcionalidades.py docudata-backend/tests/test_status_funcionalidade.py
git commit -m "feat(funcionalidade): status derivado das tasks com registro de transição"
```

---

### Task 2: Sincronizar o status em toda escrita de task

**Files:**
- Modify: `docudata-backend/routers/tasks.py`, nas rotas `create_task` (~295), `resolve_task_sugestao` (~463, quando cria ou altera task), `puxar_task` (~522), `devolver_task` (~578), `aprovar_task` (~643), `rejeitar_task` (~680), `patch_task` (~789), `mover_task` (~1110) e `delete_task` (~1191).
- Modify: qualquer outro arquivo de `routers/` ou `services/` que faça `insert`, `update` (em `coluna_kanban`, `funcionalidade_id` ou `extra`) ou `delete` na tabela `tasks`. Encontre todos com `grep -rn 'table("tasks")' docudata-backend/routers docudata-backend/services | grep -v select` e liste no relatório os que foram ou não mexidos, com o motivo.
- Test: `docudata-backend/tests/test_status_funcionalidade_ganchos.py`

**Interfaces:**
- Consumes: `sincronizar_status(client, funcionalidade_id, autor)` da Task 1.

**Regras do gancho:**
- Chamar **depois** da escrita da task e depois das chamadas existentes a `revogar_se_aprovada`.
- No PATCH (e em qualquer rota que troque `funcionalidade_id`), sincronizar a funcionalidade **antiga e a nova**, quando forem diferentes.
- No DELETE, ler o `funcionalidade_id` antes de apagar e sincronizar depois.
- O autor é o e-mail ou o nome da pessoa autenticada, quando a rota tiver. Senão, `"sistema"`.
- Nunca deixar o gancho mudar a resposta da rota: `sincronizar_status` já é best-effort.

- [ ] **Step 1: Testes que falham**

Testes de rota com `TestClient` e o `fake_supabase`, seguindo os testes de rota existentes de `routers/tasks.py`. Procure um teste que já monta create e PATCH de task (`grep -ln "client.post(\"/tasks\"" tests/`) e reaproveite as fixtures:
- criar task `planejado` numa funcionalidade sem tasks → funcionalidade `nao_iniciada` (sem transição se já era `nao_iniciada`);
- mover essa task para `em_andamento` → funcionalidade `em_andamento`, com 1 transição;
- concluir a única task (PATCH/mover para `concluida`) → funcionalidade `concluida`;
- trocar a task de funcionalidade A para B → A volta a `nao_iniciada` (ou fica sem mudança se ficou sem tasks) e B é recalculada;
- excluir a última task não concluída de uma funcionalidade cujas outras tasks estão concluídas → funcionalidade `concluida`;
- `sincronizar_status` levantando exceção (monkeypatch para `raise`) → a rota responde 2xx do mesmo jeito.

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && python3 -m pytest tests/test_status_funcionalidade_ganchos.py -q`
Expected: FAIL (o status não muda).

- [ ] **Step 3: Implementar os ganchos** em cada rota listada. Exemplo para o DELETE:

```python
    check = client.table("tasks").select("id, sprint_id, funcionalidade_id").eq("id", task_id).execute()
    ...
    client.table("tasks").delete().eq("id", task_id).execute()
    sincronizar_status(client, check.data[0].get("funcionalidade_id"))
```

Exemplo para o PATCH, no fim, depois das revogações existentes:

```python
    func_antiga = task.get("funcionalidade_id")
    sincronizar_status(client, func_efetiva, pessoa.get("email"))
    if func_antiga and func_antiga != func_efetiva:
        sincronizar_status(client, func_antiga, pessoa.get("email"))
```

- [ ] **Step 4: Rodar a suíte inteira**

Run: `cd docudata-backend && python3 -m pytest -q`
Expected: só a falha pré-existente de `test_security`. Se algum teste antigo contar exatamente as escritas em `transicoes_status` ou em `funcionalidades` e quebrar por causa das linhas novas, ajuste a expectativa e cite no relatório.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/tasks.py docudata-backend/tests/test_status_funcionalidade_ganchos.py <outros arquivos mexidos>
git commit -m "feat(funcionalidade): toda escrita de task recalcula o status da funcionalidade"
```

---

### Task 3: Status manual bloqueado com tasks, UI e backfill

**Files:**
- Modify: `docudata-backend/routers/funcionalidades.py` (PATCH: 409 quando há tasks e `data.status` muda)
- Create: `docudata-backend/scripts/status_funcionalidade_backfill.py`
- Modify: o componente do frontend que edita o status da funcionalidade. Encontre com `grep -rln "nao_iniciada" docudata-frontend/app --include=*.tsx`; o mais provável é o que tem o seletor de status.
- Modify: `docudata-frontend/app/lib/api.ts` se for preciso expor `tem_tasks` ou o número de tasks. Antes, veja se a resposta de funcionalidade já traz `tasks`/contagem; se trouxer, use o que existe.
- Test: `docudata-backend/tests/test_status_funcionalidade.py` (acrescentar) e `docudata-frontend/tests/status-funcionalidade.test.mjs`

**Interfaces:**
- Consumes: `funcionalidade_tem_tasks`, `sincronizar_status` e `registrar_transicao_status` da Task 1.

- [ ] **Step 1: Testes que falham (backend)**
  - PATCH `{status: "concluida"}` numa funcionalidade com task não extra → 409 com `detail == "O status vem das tasks desta funcionalidade."`;
  - PATCH `{status: "em_ajuste"}` numa funcionalidade com tasks → também 409, porque toda edição manual de status com tasks é bloqueada. O `em_ajuste` existente é só preservado, não definido à mão;
  - PATCH `{status: ...}` sem tasks → 200 como hoje;
  - PATCH `{titulo: "x"}` com tasks → 200 (só `status` é bloqueado);
  - backfill: com 3 funcionalidades (uma sem tasks, uma com tasks em andamento e uma com todas concluídas), `main(dry_run=False)` ajusta as duas que divergem e devolve `{"ajustadas": 2, "total": 3}`. Rodar de novo devolve `ajustadas: 0`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd docudata-backend && python3 -m pytest tests/test_status_funcionalidade.py -q`

- [ ] **Step 3: Implementar**

No PATCH, logo depois de buscar `func`:

```python
    if data.status is not None and data.status != func.get("status") and funcionalidade_tem_tasks(client, funcionalidade_id):
        raise HTTPException(status_code=409, detail="O status vem das tasks desta funcionalidade.")
```

Script (siga o cabeçalho e o carregamento do `.env` de `scripts/classificador_ponto_de_partida.py`; não imprimir segredos nem mensagens de exceção):

```python
# docudata-backend/scripts/status_funcionalidade_backfill.py
"""Backfill (Rodada B1, entrega 1): recalcula o status de todas as
funcionalidades a partir das tasks. Idempotente. Uso:
    cd <pasta com o .env>/docudata-backend && python3 <caminho>/scripts/status_funcionalidade_backfill.py [--dry-run]"""
import argparse, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import find_dotenv, load_dotenv
load_dotenv(os.environ.get("ENV_FILE") or find_dotenv(usecwd=True) or None)

from services.status_funcionalidade import sincronizar_status, status_derivado  # noqa: E402
from services.supabase_client import get_client  # noqa: E402
from services.supabase_paginacao import ler_tudo  # noqa: E402


def main(dry_run: bool = False, client=None) -> dict:
    client = client or get_client()
    funcs = ler_tudo(lambda: client.table("funcionalidades").select("id, status").order("id"))
    ajustadas = 0
    for f in funcs:
        if dry_run:
            tasks = client.table("tasks").select("coluna_kanban, extra").eq("funcionalidade_id", f["id"]).execute().data or []
            novo = status_derivado(tasks)
            if novo and novo != f["status"] and not (f["status"] == "em_ajuste" and novo == "em_andamento"):
                ajustadas += 1
        elif sincronizar_status(client, f["id"], "backfill"):
            ajustadas += 1
    print(f"{'simulação: ' if dry_run else ''}{ajustadas} de {len(funcs)} funcionalidades ajustadas")
    return {"ajustadas": ajustadas, "total": len(funcs)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    main(dry_run=ap.parse_args().dry_run)
```

Confira a assinatura real de `ler_tudo` em `services/supabase_paginacao.py` e adapte a chamada.

**Frontend:** onde o status é editado, se a funcionalidade tem tasks, o seletor fica `disabled` com o texto de ajuda literal `O status vem das tasks.` logo abaixo. Se a UI já recebe as tasks ou uma contagem, use isso. Se não, acrescente na resposta de funcionalidade um campo `tem_tasks: bool`, calculado em lote no backend (uma consulta por lista, sem N+1), e espelhe no tipo em `api.ts`. Se o PATCH responder 409, mostre o `detail` no aviso de erro que o componente já usa.

Teste estrutural do frontend:

```js
// docudata-frontend/tests/status-funcionalidade.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { execSync } from "node:child_process";

test("seletor de status da funcionalidade avisa que o status vem das tasks", () => {
  const arquivos = execSync("grep -rl \"O status vem das tasks.\" app", { cwd: new URL("..", import.meta.url) }).toString().trim().split("\n").filter(Boolean);
  assert.ok(arquivos.length >= 1);
  const src = readFileSync(new URL(`../${arquivos[0]}`, import.meta.url), "utf8");
  assert.match(src, /disabled=\{[^}]*tem_tasks|disabled=\{[^}]*temTasks|disabled=\{[^}]*tasks/);
});
```

- [ ] **Step 4: Rodar tudo**

Run: `cd docudata-backend && python3 -m pytest -q` e `cd docudata-frontend && npx tsc --noEmit && npm test`
Expected: backend só com a falha pré-existente; frontend verde.

- [ ] **Step 5: Commit**

```bash
git add docudata-backend/routers/funcionalidades.py docudata-backend/scripts/status_funcionalidade_backfill.py docudata-backend/tests/test_status_funcionalidade.py docudata-frontend/app/<arquivos> docudata-frontend/tests/status-funcionalidade.test.mjs
git commit -m "feat(funcionalidade): status manual bloqueado quando há tasks, backfill e aviso na tela"
```

---

## Depois da entrega (controlador)

1. Push e PR (sem migração).
2. Merge e deploy.
3. Pedir ao usuário para rodar o backfill com `--dry-run` e depois sem ele (precisa das variáveis de produção, como o script do classificador).
4. Conferir no Painel se WIP, Throughput e eficiência de fluxo mudaram.
