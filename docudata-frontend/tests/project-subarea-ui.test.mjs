import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const NEW_PROJECT = readFileSync(
  new URL("../app/[subarea]/projects/new/page.tsx", import.meta.url),
  "utf8",
);
const PROJECT_PAGE = readFileSync(
  new URL("../app/[subarea]/projects/[id]/page.tsx", import.meta.url),
  "utf8",
);
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf8");
const LAYOUT = readFileSync(
  new URL("../app/[subarea]/layout.tsx", import.meta.url),
  "utf8",
);
const STYLES = readFileSync(
  new URL("../app/[subarea]/subarea.module.css", import.meta.url),
  "utf8",
);
const TABS = readFileSync(
  new URL("../app/components/Tabs.tsx", import.meta.url),
  "utf8",
);

test("cadastro deriva e envia a subárea presente na rota", () => {
  assert.ok(NEW_PROJECT.includes("useParams<{ subarea: Subarea }>()"));
  assert.ok(NEW_PROJECT.includes("createProject({ name, client, subarea,"));
  assert.ok(NEW_PROJECT.includes("Novo projeto de {subareaLabel}"));
  assert.ok(NEW_PROJECT.includes("será cadastrado automaticamente em {subareaLabel}"));
});

test("configurações permitem mover o projeto preservando seu id", () => {
  assert.ok(API.includes("export async function updateProjectSubarea("));
  assert.ok(API.includes("`${API}/projects/${projectId}/subarea`"));
  assert.ok(PROJECT_PAGE.includes('id="project-subarea"'));
  assert.ok(PROJECT_PAGE.includes("updateProjectSubarea(id, subareaDestino)"));
  assert.ok(PROJECT_PAGE.includes("router.replace(`/${updated.subarea}/projects/${id}?tab=config`)"));
  assert.ok(PROJECT_PAGE.includes("Sprints, ingestões, commits, documentos e repositórios conectados serão preservados"));
  assert.ok(PROJECT_PAGE.includes("if (p.subarea !== subarea)"));
  assert.ok(PROJECT_PAGE.includes("router.replace(`/${p.subarea}/projects/${p.id}`)"));
  assert.ok(PROJECT_PAGE.indexOf("<OperacionaisSection") < PROJECT_PAGE.indexOf('htmlFor="project-subarea"'));
  assert.ok(PROJECT_PAGE.indexOf('htmlFor="project-subarea"') < PROJECT_PAGE.indexOf("Zona perigosa"));
});

test("barra superior reorganiza ações antes que haja sobreposição", () => {
  assert.ok(LAYOUT.includes("styles.headerIdentity"));
  assert.ok(STYLES.includes("@media (max-width: 680px)"));
  assert.ok(STYLES.includes("grid-template-columns: repeat(3, minmax(0, 1fr))"));
  assert.ok(STYLES.includes("@media (max-width: 430px)"));
  assert.ok(STYLES.includes("grid-column: 1 / -1"));
  assert.ok(TABS.includes('overflowX: "auto"'));
  assert.ok(TABS.includes('flex: "0 0 auto"'));
  assert.ok(TABS.includes('role="tablist"'));
  assert.ok(TABS.includes('scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" })'));
});
