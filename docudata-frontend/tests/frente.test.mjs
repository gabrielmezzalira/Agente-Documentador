import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("api: frente da task e FRENTES com valores e rótulos exatos", () => {
  const api = ler("app/lib/api.ts");
  assert.ok(api.includes('frente?: "software" | "mobile" | "dados" | "ia" | null;'));
  assert.ok(api.includes('frente_definida_por?: "ia" | "gerente" | null;'));
  assert.ok(api.includes('frente?: "software" | "mobile" | "dados" | "ia";'));
  const m = api.match(/export const FRENTES = (\[[\s\S]*?\]) as const;/);
  assert.ok(m, "FRENTES exportado");
  const FRENTES = eval(m[1]);
  assert.deepEqual(FRENTES, [
    { value: "software", label: "Software" },
    { value: "mobile", label: "Mobile" },
    { value: "dados", label: "Dados" },
    { value: "ia", label: "IA" },
  ]);
});

test("kanban: chip da frente no card e select Frente para o gerente", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(k.includes("rotuloFrente(task.frente)"));
  assert.ok(k.includes('id="task-frente"'));
  assert.ok(k.includes("Identificando…"));
  assert.ok(k.includes("definida pela IA"));
  assert.ok(k.includes("definida pelo gerente"));
  assert.ok(k.includes("patchTaskKanban(task.id, { frente:"));
});

test("kanban: frente e mudar nível não fecham o modal", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(k.includes("onTaskUpdated?.(atualizada);"));
  assert.ok(k.includes("onTaskUpdated={(t) => { upsertTask(t); setEditModal(t); }}"));
  assert.ok(k.includes("aria-busy={salvandoFrente}"));
});
