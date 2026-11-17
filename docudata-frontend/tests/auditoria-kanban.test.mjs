import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const KANBAN = readFileSync(new URL("../app/components/TasksKanbanTab.tsx", import.meta.url), "utf-8");

test("edição só envia operacional_id quando mudou, e nunca em Pull", () => {
  assert.match(KANBAN, /const operacionalMudou = modoTrabalho !== "PULL" && operacionalId !== \(task\?\.operacional_id \?\? ""\);/);
  assert.match(KANBAN, /\.\.\.\(operacionalMudou \? \{ operacional_id: operacionalId \|\| null \} : \{\}\)/);
});

test("criação continua mandando operacional_id só quando escolhido", () => {
  assert.match(KANBAN, /operacional_id: operacionalId \|\| undefined,\n\s+funcionalidade_id: funcId \|\| undefined,\n\s+extra,/);
});

test("card de outra pessoa não é arrastável para operacional", () => {
  assert.match(KANBAN, /draggable=\{arrastavel\}/);
  assert.match(KANBAN, /function podeArrastar\(t: TaskKanbanResponse\)/);
  assert.match(KANBAN, /arrastavel=\{podeArrastar\(t\)\}/);
});

test("handleDrop também recusa mover task de colega", () => {
  assert.match(KANBAN, /if \(!podeArrastar\(task\)\) return;/);
});
