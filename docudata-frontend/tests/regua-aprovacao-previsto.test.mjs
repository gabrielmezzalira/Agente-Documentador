import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("régua do frontend espelha a do backend", () => {
  const regua = ler("app/lib/regua.ts");
  assert.match(regua, /NIVEIS = \[1, 2, 3, 5\]/);
  for (const r of ["simples", "moderada", "complexa", "muito complexa"]) assert.ok(regua.includes(r));
});

test("Kanban usa seletor de nível e não tem mais redistribuição", () => {
  const kanban = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(kanban.includes("rotuloNivel"));
  assert.ok(!kanban.includes('type="number" min={1} value={pontos}'));
  assert.ok(!kanban.includes("redistribuirPontos"));
});

test("orçamento, valor do projeto e comparação de modos saíram", () => {
  assert.ok(!existsSync(new URL("../app/components/SprintOrcamentoPlanner.tsx", import.meta.url)));
  assert.ok(!existsSync(new URL("../app/comparacao-modos/page.tsx", import.meta.url)));
  const api = ler("app/lib/api.ts");
  for (const s of ["updateSprintOrcamento", "redistribuirPontos", "getComparacaoModos", "faturamento_previsto", "valor_por_ponto"]) {
    assert.ok(!api.includes(s), s);
  }
  assert.ok(!ler("app/components/painel/IndicadoresCards.tsx").includes("valor_projeto"));
});

test("SprintCard mostra o previsto", () => {
  const card = ler("app/components/SprintCard.tsx");
  assert.ok(card.includes("sprint.previsto"));
  assert.ok(card.includes("surgiram na sprint"));
  assert.ok(!card.includes("pontos_orcamento"));
});

test("Escopo tem aprovação de funcionalidade", () => {
  const escopo = ler("app/components/EscopoTab.tsx");
  assert.ok(escopo.includes("aprovarFuncionalidade"));
  assert.ok(escopo.includes("Aguardando aprovação"));
  assert.ok(escopo.includes("Desfazer aprovação"));
});
