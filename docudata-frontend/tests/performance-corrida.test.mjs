import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("../app/performance/page.tsx", import.meta.url), "utf8");

test("performance: resposta antiga do escopo anterior é descartada no cleanup do efeito", () => {
  const efeito = src.slice(src.indexOf("getPerformance(escopo)") - 300, src.indexOf("[auth, escopo]") + 20);
  assert.match(efeito, /let ignore = false/);
  assert.match(efeito, /if \(!ignore\) setDados/);
  assert.match(efeito, /if \(!ignore\) setErro/);
  assert.match(efeito, /return \(\) => \{\s*ignore = true;\s*\}/);
});
