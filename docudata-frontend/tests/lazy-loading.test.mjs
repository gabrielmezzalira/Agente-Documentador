import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const PAGINA = readFileSync(
  new URL("../app/[subarea]/projects/[id]/page.tsx", import.meta.url),
  "utf8",
);

// Componentes fora da aba inicial. Se algum voltar a ser importado
// estaticamente, os ~160 kB de First Load JS voltam junto.
const SOB_DEMANDA = [
  "TechnologiesTab",
  "PainelTab",
  "EscopoTab",
  "TasksKanbanTab",
  "MetricasTab",
  "SprintDocModal",
  "PlanningModal",
  "FuncionalidadesStatusModal",
  "ManualDocModal",
  "UploadLivreModal",
  "RetroModal",
  "AvaliacaoSemanalModal",
];

// Aba Sprints é a que abre por padrão: estes precisam continuar no bundle
// inicial para não trocar um custo por um flash de carregamento.
const NO_BUNDLE_INICIAL = ["Tabs", "SprintCard", "DocTypeCard", "TutorialBanner"];

test("componentes fora da aba inicial são carregados sob demanda", () => {
  for (const nome of SOB_DEMANDA) {
    assert.ok(
      PAGINA.includes(`const ${nome} = dynamic(`),
      `${nome} deveria usar next/dynamic`,
    );
    assert.ok(
      !PAGINA.includes(`import ${nome} from`),
      `${nome} não pode ter import estático`,
    );
  }
});

test("a aba inicial continua no bundle inicial", () => {
  for (const nome of NO_BUNDLE_INICIAL) {
    assert.ok(
      PAGINA.includes(`import ${nome} from`),
      `${nome} deveria continuar com import estático`,
    );
  }
});

test("modais só são montados quando abertos", () => {
  const guardas = [
    "{modal !== null && (",
    "{planningModal && (",
    "{avaliacaoModal && (",
    "{manualModal !== null && (",
    "{statusModal !== null && (",
    "{uploadModal !== null && (",
    "{retroModal !== null && (",
  ];

  for (const guarda of guardas) {
    assert.ok(PAGINA.includes(guarda), `faltou a guarda de montagem: ${guarda}`);
  }
});
