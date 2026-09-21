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
