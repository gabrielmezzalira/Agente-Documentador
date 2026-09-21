import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf8");

test("api.ts tem os tipos e funções de elegibilidade e comparação de modos", () => {
  assert.ok(API.includes("export interface ElegivelPonto"));
  assert.ok(API.includes("export async function getElegiveis("));
  assert.ok(API.includes("export interface ComparacaoModoPonto"));
  assert.ok(API.includes("export async function getComparacaoModos("));
  assert.ok(API.includes("export async function getComparacaoModosEntreProjetos("));
});

const PAINEL = readFileSync(new URL("../app/components/PainelTab.tsx", import.meta.url), "utf8");

test("PainelTab mostra a seção de elegibilidade da sprint", () => {
  assert.ok(PAINEL.includes("function ElegibilidadeCard("));
  assert.ok(PAINEL.includes("getElegiveis("));
  assert.ok(PAINEL.includes("<ElegibilidadeCard"));
});

const METRICAS = readFileSync(new URL("../app/components/MetricasTab.tsx", import.meta.url), "utf8");

test("MetricasTab mostra a comparação de modos dentro do projeto", () => {
  assert.ok(METRICAS.includes("getComparacaoModos("));
  assert.ok(METRICAS.includes("Comparação de modos"));
});

const PAGE_ENTRE_PROJETOS = readFileSync(
  new URL("../app/comparacao-modos/page.tsx", import.meta.url),
  "utf8"
);

test("página de comparação entre projetos existe e usa a função certa", () => {
  assert.ok(PAGE_ENTRE_PROJETOS.includes("getComparacaoModosEntreProjetos("));
  assert.ok(PAGE_ENTRE_PROJETOS.includes("export default function"));
});

const HOME = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");

test("home tem link de navegação pra comparação entre projetos", () => {
  assert.ok(HOME.includes("/comparacao-modos"));
});
