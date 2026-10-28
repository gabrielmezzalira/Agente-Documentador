import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("../app/components/EscopoTab.tsx", import.meta.url), "utf8");

test("seletor de status da funcionalidade avisa que o status vem das tasks", () => {
  assert.ok(src.includes("O status vem das tasks."));
  assert.match(src, /id=\{`edit-\$\{f\.id\}-status`\}[^>]*disabled=\{f\.tem_tasks\}/);
  assert.match(src, /hint=\{f\.tem_tasks \? "O status vem das tasks\." : undefined\}/);
});

test("api expõe tem_tasks na funcionalidade", () => {
  const api = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf8");
  assert.match(api, /tem_tasks\?: boolean/);
});
