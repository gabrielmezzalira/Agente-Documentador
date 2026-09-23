import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const KANBAN = readFileSync(new URL("../app/components/TasksKanbanTab.tsx", import.meta.url), "utf-8");
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf-8");
const METRICAS = readFileSync(new URL("../app/components/MetricasTab.tsx", import.meta.url), "utf-8");

test("Kanban tem a coluna pendente_aprovacao e o checkbox requer_aprovacao", () => {
  assert.match(KANBAN, /pendente_aprovacao/);
  assert.match(KANBAN, /Requer aprovação do gerente/);
  assert.match(KANBAN, /handleAprovar/);
  assert.match(KANBAN, /handleRejeitar/);
});

test("api.ts expõe aprovarTask e rejeitarTask", () => {
  assert.match(API, /export async function aprovarTask/);
  assert.match(API, /export async function rejeitarTask/);
  assert.match(API, /pendente_aprovacao/);
});

test("MetricasTab CFD inclui pendente_aprovacao", () => {
  assert.match(METRICAS, /pendente_aprovacao/);
});

test("moverTaskKanban propaga a mensagem do backend em qualquer status, não só 409", () => {
  const fn = API.slice(API.indexOf("export async function moverTaskKanban"));
  const corpo = fn.slice(0, fn.indexOf("export async function overrideTravamentoTask"));
  // o bloco !res.ok tem que ler o detail do backend (os gates novos de
  // pendente_aprovacao respondem 422, não 409)
  assert.match(corpo, /if \(!res\.ok\) \{[\s\S]*detail[\s\S]*\}/);
  assert.doesNotMatch(corpo, /if \(!res\.ok\) throw new Error\("Erro ao mover task"\);/);
  // e o 409 continua carregando .status pra quem ramifica nele
  assert.match(corpo, /status: 409/);
});

test("Devolver à fila não aparece em task de Pendente de aprovação", () => {
  const trecho = KANBAN.slice(
    KANBAN.indexOf('modoTrabalho === "PULL" && task.coluna_kanban'),
    KANBAN.indexOf("Devolver à fila")
  );
  assert.match(trecho, /task\.coluna_kanban !== "pendente_aprovacao"/);
});
