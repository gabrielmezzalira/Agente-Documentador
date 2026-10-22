import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf8");

test("api.ts tem os tipos e funções de elegibilidade", () => {
  assert.ok(API.includes("export interface ElegivelPonto"));
  assert.ok(API.includes("export async function getElegiveis("));
});

// O Painel foi dividido em componentes (app/components/painel/*); os cartões de pontos ficam em PontosCards.
const PAINEL =
  readFileSync(new URL("../app/components/PainelTab.tsx", import.meta.url), "utf8") +
  readFileSync(new URL("../app/components/painel/PontosCards.tsx", import.meta.url), "utf8");

test("PainelTab mostra a seção de elegibilidade da sprint", () => {
  assert.ok(PAINEL.includes("function ElegibilidadeCard("));
  assert.ok(PAINEL.includes("getElegiveis("));
  assert.ok(PAINEL.includes("<ElegibilidadeCard"));
});
