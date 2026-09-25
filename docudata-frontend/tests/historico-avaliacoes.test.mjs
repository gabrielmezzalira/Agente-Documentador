import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf-8");

test("perguntas da avaliação vivem num módulo compartilhado", () => {
  const lib = read("../app/lib/perguntasAvaliacao.ts");
  assert.match(lib, /export function perguntas/);
  assert.match(lib, /Puxou e entregou num ritmo consistente\?/);
  assert.match(lib, /export const CAMPOS_RESPOSTA/);
  assert.match(lib, /export function mediaGerente100/);
  const modal = read("../app/components/AvaliacaoSemanalModal.tsx");
  assert.match(modal, /from "\.\.\/lib\/perguntasAvaliacao"/);
  assert.doesNotMatch(modal, /function perguntas\(/);
});

test("api.ts expõe histórico, edição e log de avaliações", () => {
  const api = read("../app/lib/api.ts");
  assert.match(api, /export async function getHistoricoAvaliacoes/);
  assert.match(api, /export async function editarAvaliacao/);
  assert.match(api, /export async function getEdicoesAvaliacao/);
  assert.match(api, /\/avaliacoes\/historico/);
  assert.match(api, /method: "PATCH"/);
});

test("página /avaliacoes: guarda de cargo, filtros, edição com motivo e histórico", () => {
  assert.ok(existsSync(new URL("../app/avaliacoes/page.tsx", import.meta.url)));
  const page = read("../app/avaliacoes/page.tsx");
  assert.match(page, /cargo === "operacional"/);
  assert.match(page, /getHistoricoAvaliacoes/);
  assert.match(page, /editarAvaliacao/);
  assert.match(page, /getEdicoesAvaliacao/);
  assert.match(page, /Motivo da correção/);
  assert.match(page, /mediaGerente100/);
  assert.match(page, /Nenhuma avaliação/);
});

test("nav global linka /avaliacoes para gerente/líder/owner", () => {
  const home = read("../app/page.tsx");
  assert.match(home, /podeConfigurar && <Link href="\/avaliacoes"/);
});
