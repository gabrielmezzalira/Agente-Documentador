import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("modal de task não tem mais seletor de pontos e tem opinião do gerente", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(!k.includes('id="task-pontos"'));
  assert.ok(k.includes('id="task-opiniao"'));
  assert.ok(k.includes("Não define o nível. É usada pelo classificador como mais uma referência."));
  assert.ok(k.includes("Classificando…"));
  assert.ok(k.includes("O classificador precisa de mais detalhes"));
  assert.ok(k.includes("Na sua visão, qual era o nível dessa task?"));
  assert.ok(k.includes("Editar o texto não muda o nível."));
});

test("api: criação sem pontos e funções do classificador", () => {
  const api = ler("app/lib/api.ts");
  for (const s of ["opiniao_nivel", "reclassificarTask", "resolverRevisaoNivel", "opinarNivelTask", "getClassificadorResumo", "definirExclusaoAprendizado"]) {
    assert.ok(api.includes(s), s);
  }
});

test("tela /classificador existe com os blocos e só para líder/owner no menu", () => {
  assert.ok(existsSync(new URL("../app/classificador/page.tsx", import.meta.url)));
  const p = ler("app/classificador/page.tsx");
  for (const s of ["Tempo típico por nível", "Tasks em alerta", "Acurácia contra o tempo real", "Por que o classificador decide assim", "Fila de revisão", "Ajuste interno, não é nota de desempenho."]) {
    assert.ok(p.includes(s), s);
  }
  const nav = ler("app/components/shell/navItems.ts");
  assert.match(nav, /isOwnerOrLider\(cargo\)[\s\S]{0,200}\/classificador/);
});
