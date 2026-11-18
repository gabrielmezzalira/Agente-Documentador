import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("api: propostas de melhoria", () => {
  const api = ler("app/lib/api.ts");
  assert.ok(api.includes('export type StatusProposta = "pendente" | "aprovada" | "recusada" | "adiada";'));
  assert.ok(api.includes("export interface PropostaMelhoria"));
  assert.ok(api.includes("`${API}/projects/${projectId}/propostas`"));
  assert.ok(api.includes("`${API}/propostas/${id}/decisao`"));
  assert.ok(api.includes("export async function criarProposta"));
  assert.ok(api.includes("export async function listarPropostas"));
  assert.ok(api.includes("export async function decidirProposta"));
  assert.ok(api.includes("inovacao?: boolean;"));
});

test("propostas: botão, modal, painel do PM e chip só no PTA", () => {
  const c = ler("app/components/PropostasMelhoria.tsx");
  for (const t of ["Propor melhoria", "Valor para o cliente", "Enviar proposta", "Cancelar", "Minhas propostas",
    "Propostas de melhoria", "Aprovar", "Recusar", "Deixar para depois", "Motivo da recusa", "rotuloNivel"]) {
    assert.ok(c.includes(t), t);
  }
  assert.ok(c.includes('subarea === "pta"'));
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(k.includes("<PropostasMelhoria"));
  assert.ok(k.includes("task.inovacao"));
  assert.ok(k.includes("inovação"));
  assert.ok(ler("app/[subarea]/projects/[id]/page.tsx").includes("subarea={project?.subarea}"));
});
