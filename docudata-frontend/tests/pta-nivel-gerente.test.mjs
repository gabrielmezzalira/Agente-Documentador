import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("subárea PTA: tipo, card, menu, layout, cadastro e acompanhamento", () => {
  assert.ok(ler("app/lib/api.ts").includes('export type Subarea = "dados" | "dev" | "pta";'));
  const home = ler("app/page.tsx");
  assert.ok(home.includes('slug: "pta", title: "PTA", description: "Projetos do processo seletivo do CITi."'));
  assert.ok(ler("app/components/shell/navItems.ts").includes('{ slug: "pta", label: "PTA" }'));
  assert.ok(ler("app/[subarea]/layout.tsx").includes('new Set(["dados", "dev", "pta"])'));
  assert.ok(ler("app/[subarea]/projects/new/page.tsx").includes('pta: "PTA"'));
  assert.ok(ler("app/acompanhamento/page.tsx").includes('{ value: "pta", label: "PTA" }'));
  assert.ok(ler("app/[subarea]/projects/[id]/page.tsx").includes('sub === "pta" ? "PTA"'));
});
