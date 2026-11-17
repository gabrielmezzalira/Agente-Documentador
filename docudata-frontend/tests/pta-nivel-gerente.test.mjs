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

test("performance: escopo CITi/PTA vai da tela até a API", () => {
  const api = ler("app/lib/api.ts");
  assert.ok(api.includes('export type EscopoPerformance = "citi" | "pta";'));
  assert.ok(api.includes("getPerformance(escopo: EscopoPerformance = \"citi\")"));
  assert.ok(api.includes("`${API}/performance?escopo=${escopo}`"));
  const pagina = ler("app/performance/page.tsx");
  assert.ok(pagina.includes('label="Escopo do ranking"'));
  assert.ok(pagina.includes('{ value: "citi", label: "CITi" }'));
  assert.ok(pagina.includes('{ value: "pta", label: "PTA" }'));
  assert.ok(pagina.includes("getPerformance(escopo)"));
});
