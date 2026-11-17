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

test("api: nível escolhido pelo gerente", () => {
  const api = ler("app/lib/api.ts");
  assert.ok(api.includes('"aplicada" | "em_revisao" | "provisoria" | "resolvida" | "manual"'));
  assert.ok(api.includes("nivel_gerente?: number;"));
  assert.ok(api.includes("export async function definirNivelGerente(id: string, nivel: number): Promise<TaskKanbanResponse>"));
  assert.ok(api.includes("`${API}/tasks/${id}/nivel-gerente`"));
});

test("criação: gerente define o nível e a opinião some", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(k.includes("Definir o nível eu mesmo"));
  assert.ok(k.includes('id="task-nivel-proprio"'));
  assert.ok(k.includes('id="task-nivel-gerente"'));
  assert.ok(k.includes("nivel_gerente: Number(nivelGerente)"));
  assert.ok(k.includes("Escolha o nível da task."));
  assert.match(k, /\{mode === "create" && !nivelProprio && \(/);
  assert.ok(k.includes('const ehGerente = !!auth && auth.cargo !== "operacional";'));
});

test("task aberta: Mudar nível e selos do gerente", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(k.includes("definirNivelGerente"));
  assert.ok(k.includes("Mudar nível"));
  assert.ok(k.includes('id="task-mudar-nivel"'));
  assert.ok(k.includes("function origemNivel("));
  assert.ok(k.includes('"definido pelo gerente"'));
  assert.ok(k.includes("nível do gerente"));
  assert.ok(k.includes('task.classificacao_status === "manual"'));
  assert.ok(!k.includes("· definido pelo classificador`"), "os títulos dos chips usam origemNivel");
});
