import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("funcionalidade só nasce com sprint alvo (manual, importação e edição)", () => {
  const e = ler("app/components/EscopoTab.tsx");
  for (const s of ["sprintAlvoValida", "Informe a sprint alvo", "Sprint alvo para todas", "Aplicar a todas", 'htmlFor="nova-sprint_alvo" required',
                   "sprint_alvo: selecionadas.has(i)", "onUpdated?.(atualizada)"]) assert.ok(e.includes(s), s);
});

test("task só nasce ligada a uma funcionalidade", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  for (const s of ['Escolha a funcionalidade da task.', "Funcionalidade *", "Cadastre o escopo na aba Planejamento"]) assert.ok(k.includes(s), s);
});

test("aviso fixo de planejamento incompleto no projeto", () => {
  const a = ler("app/components/PendenciasPlanejamento.tsx");
  for (const s of ["sem sprint alvo", "Prazo total do projeto não definido", "Definir sprints", "Salvar prazo", "if (semSprint.length === 0 && !semPrazo) return null"]) assert.ok(a.includes(s), s);
  assert.ok(!/onClose|onDismiss|setOculto|localStorage/.test(a), "o aviso não pode ser dispensado");
  const p = ler("app/[subarea]/projects/[id]/page.tsx");
  for (const s of ["<PendenciasPlanejamento", 'cargo !== "operacional"', 'setEscopoFiltro("sem_sprint")']) assert.ok(p.includes(s), s);
});

test("kanban rola a tela sozinho enquanto um card é arrastado", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  for (const s of ["useAutoScrollDuranteArrasto", "ancestralRolavel", 'addEventListener("dragover"', "gradeRef"]) assert.ok(k.includes(s), s);
});
