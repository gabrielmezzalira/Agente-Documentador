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
