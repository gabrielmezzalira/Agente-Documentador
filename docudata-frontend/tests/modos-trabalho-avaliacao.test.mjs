import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf8");

test("api.ts expõe os endpoints de modos, wip-config e extrato de pontos", () => {
  assert.ok(API.includes("export async function updateProjectModos("));
  assert.ok(API.includes("`${API}/projects/${projectId}/modos`"));
  assert.ok(API.includes("export async function getModosHistorico("));
  assert.ok(API.includes("`${API}/projects/${projectId}/modos-historico`"));
  assert.ok(API.includes("export async function updateWipConfig("));
  assert.ok(API.includes("`${API}/projects/${projectId}/wip-config`"));
  assert.ok(API.includes("export async function getExtratoPontos("));
  assert.ok(API.includes("`${API}/operacionais/${operacionalId}/extrato${qs}`"));
});

test("Project e SprintWithStatus ganham os campos novos", () => {
  assert.ok(API.includes('modo_trabalho: "ATRIBUICAO" | "PULL";'));
  assert.ok(API.includes('modo_avaliacao: "PONTOS_ATRIBUIDOS" | "PONTOS_RELATIVO";'));
  assert.ok(API.includes("avaliados_count: number;"));
  assert.ok(API.includes("elegiveis_avaliacao_count: number;"));
});

const SPRINT_CARD = readFileSync(new URL("../app/components/SprintCard.tsx", import.meta.url), "utf8");

test("SprintCard mostra o contador N/M de avaliação semanal", () => {
  assert.ok(SPRINT_CARD.includes("const avaliacaoPendente ="));
  assert.ok(SPRINT_CARD.includes("sprint.elegiveis_avaliacao_count > 0"));
  assert.ok(SPRINT_CARD.includes("{sprint.avaliados_count}/{sprint.elegiveis_avaliacao_count} Avaliação"));
});

const PROJECT_PAGE = readFileSync(new URL("../app/[subarea]/projects/[id]/page.tsx", import.meta.url), "utf8");

test("Configurações mostram os selects de modo com campos condicionais e WIP forçado", () => {
  assert.ok(PROJECT_PAGE.includes("function ModosTrabalhoSection("));
  assert.ok(PROJECT_PAGE.includes('id="project-modo-trabalho"'));
  assert.ok(PROJECT_PAGE.includes('id="project-modo-avaliacao"'));
  assert.ok(PROJECT_PAGE.includes("updateProjectModos(projectId,"));
  assert.ok(PROJECT_PAGE.includes('modoTrabalho === "PULL"'));
  assert.ok(PROJECT_PAGE.includes('modoAvaliacao === "PONTOS_RELATIVO"'));
  assert.ok(PROJECT_PAGE.includes("updateWipConfig(projectId,"));
  assert.ok(PROJECT_PAGE.includes("getModosHistorico(projectId)"));
  assert.ok(PROJECT_PAGE.includes("<ModosTrabalhoSection"));
});
