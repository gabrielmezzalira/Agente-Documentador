import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const KANBAN = readFileSync(new URL("../app/components/TasksKanbanTab.tsx", import.meta.url), "utf-8");
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");

test("api.ts expõe bloqueio_tipo na task e no PATCH", () => {
  assert.match(API, /bloqueio_tipo\?: "interno" \| "cliente" \| null;/);
  assert.match(API, /bloqueio_tipo\?: "interno" \| "cliente";/);
});

test("TaskModal oferece Dependência do cliente dentro do bloqueio", () => {
  assert.match(KANBAN, /Dependência do cliente/);
  assert.match(KANBAN, /bloqueio_tipo: bloqueado \? bloqueioTipo : undefined/);
});

test("destravar bloqueio de cliente não pergunta quem resolveu", () => {
  assert.match(KANBAN, /jaEstavaBloqueadoManual && !eraBloqueioCliente && !bloqueado/);
});

test("card mostra que a task espera o cliente", () => {
  assert.match(KANBAN, /Aguardando cliente/);
});
