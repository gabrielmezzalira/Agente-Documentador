import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const SPRINT_CARD = readFileSync(
  new URL("../app/components/SprintCard.tsx", import.meta.url),
  "utf8",
);
const PROJECT_PAGE = readFileSync(
  new URL("../app/[subarea]/projects/[id]/page.tsx", import.meta.url),
  "utf8",
);

test("histórico de commits inicia recolhido e só monta a lista ao expandir", () => {
  assert.ok(SPRINT_CARD.includes("const [commitsExpanded, setCommitsExpanded] = useState(false)"));
  assert.ok(SPRINT_CARD.includes("aria-expanded={commitsExpanded}"));
  assert.ok(SPRINT_CARD.includes('{commitsExpanded ? "Recolher ▲" : "Expandir ▼"}'));

  const guarda = SPRINT_CARD.indexOf("{commitsExpanded && (");
  const lista = SPRINT_CARD.indexOf("{filteredCommits.map((ing) =>", guarda);
  assert.ok(guarda >= 0 && lista > guarda, "a lista deve permanecer dentro da guarda de expansão");
});

test("detalhes expandidos identificam origem, autoria e alterações do commit", () => {
  for (const trecho of [
    "source_repository_full_name",
    "_meta_autor_login",
    "_meta_data_commit ?? ing.created_at",
    "Committer:",
    "Push por:",
    "source_diff_stat",
    "renderIngestionChips(meta)",
  ]) {
    assert.ok(SPRINT_CARD.includes(trecho), `faltou exibir o detalhe ${trecho}`);
  }
});

test("configuração do GitHub segue a capacidade da subárea atual sem hardcode de Dev", () => {
  assert.ok(PROJECT_PAGE.includes("capabilities.subareas.includes(subareaProjeto)"));
  assert.ok(!PROJECT_PAGE.includes('project?.subarea !== "dev"'));
  assert.ok(!PROJECT_PAGE.includes('capabilities.subareas.includes("dev")'));
});
