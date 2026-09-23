import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const KANBAN = readFileSync(new URL("../app/components/TasksKanbanTab.tsx", import.meta.url), "utf-8");
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");
const METRICAS = readFileSync(new URL("../app/components/MetricasTab.tsx", import.meta.url), "utf-8");

test("Kanban tem a coluna pendente_aprovacao e o checkbox requer_aprovacao", () => {
  assert.match(KANBAN, /pendente_aprovacao/);
  assert.match(KANBAN, /Requer aprovação do gerente/);
  assert.match(KANBAN, /handleAprovar/);
  assert.match(KANBAN, /handleRejeitar/);
});

test("api.ts expõe aprovarTask e rejeitarTask", () => {
  assert.match(API, /export async function aprovarTask/);
  assert.match(API, /export async function rejeitarTask/);
  assert.match(API, /pendente_aprovacao/);
});

test("MetricasTab CFD inclui pendente_aprovacao", () => {
  assert.match(METRICAS, /pendente_aprovacao/);
});
