import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("MetricasTab explica SPI nulo com sprints avaliadas em vez de deixar travessão sem contexto", () => {
  const src = readFileSync(
    new URL("../app/components/MetricasTab.tsx", import.meta.url),
    "utf-8"
  );
  assert.match(src, /sprints_avaliadas > 0/);
  assert.match(src, /Sem task alocada nesta sprint/);
});

test("pergunta 1 da Avaliação Semanal muda de texto conforme o modo de trabalho", () => {
  const src = readFileSync(
    new URL("../app/components/AvaliacaoSemanalModal.tsx", import.meta.url),
    "utf-8"
  );
  assert.match(src, /modoTrabalho/);
  assert.match(src, /Puxou e entregou num ritmo consistente\?/);
});

test("api.ts expõe puxarTask e devolverTask", () => {
  const src = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");
  assert.match(src, /export async function puxarTask/);
  assert.match(src, /export async function devolverTask/);
});

test("Kanban mostra ações de puxar/devolver conforme o modo", () => {
  const src = readFileSync(
    new URL("../app/components/TasksKanbanTab.tsx", import.meta.url),
    "utf-8"
  );
  assert.match(src, /puxarTask/);
  assert.match(src, /devolverTask/);
});
