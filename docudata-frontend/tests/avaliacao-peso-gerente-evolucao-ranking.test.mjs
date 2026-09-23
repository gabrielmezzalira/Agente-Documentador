import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const MODAL = readFileSync(new URL("../app/components/AvaliacaoSemanalModal.tsx", import.meta.url), "utf-8");
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");
const METRICAS = readFileSync(new URL("../app/components/MetricasTab.tsx", import.meta.url), "utf-8");
const PERFORMANCE_PAGE = readFileSync(new URL("../app/performance/page.tsx", import.meta.url), "utf-8");

test("questionário semanal não pergunta mais sobre evolução", () => {
  assert.doesNotMatch(MODAL, /Evoluiu em relação a onde estava/);
  assert.match(MODAL, /Respostas = \[number, number, number, number, number, number\]/);
});

test("api.ts não expõe mais evolucao nem spi-evolucao", () => {
  assert.doesNotMatch(API, /(?<!d)evolucao/i);
  assert.doesNotMatch(API, /spi-evolucao/);
  assert.match(API, /export async function getSpiDoProjeto/);
  assert.match(API, /projetos: PerformanceProjeto\[\]/);
});

test("MetricasTab não mostra mais a coluna Evolução", () => {
  assert.doesNotMatch(METRICAS, />Evolução</);
  assert.match(METRICAS, /Entrega por pessoa/);
});

test("performance/page.tsx renderiza uma seção por projeto", () => {
  assert.match(PERFORMANCE_PAGE, /projeto\.projeto_nome/);
  assert.match(PERFORMANCE_PAGE, /projetos\.map/);
  assert.doesNotMatch(PERFORMANCE_PAGE, /(?<!d)evolucao/i);
});
