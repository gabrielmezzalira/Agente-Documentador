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
const REPOSITORY_PICKER = readFileSync(
  new URL("../app/components/GitHubRepositoryPicker.tsx", import.meta.url),
  "utf8",
);
const API = readFileSync(new URL("../app/lib/api.ts", import.meta.url), "utf8");

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

test("instalação existente abre seletor interno sem marcar repositórios automaticamente", () => {
  const inicioHandler = PROJECT_PAGE.indexOf("async function handleStartGitHubConnection()");
  const abreModal = PROJECT_PAGE.indexOf("setGithubPickerOpen(true)", inicioHandler);
  const criaSessao = PROJECT_PAGE.indexOf("await startGitHubConnection(id)", inicioHandler);
  assert.ok(PROJECT_PAGE.includes("if (session.connection_token)"));
  assert.ok(abreModal >= 0 && abreModal < criaSessao, "o modal deve abrir antes da consulta externa");
  assert.ok(PROJECT_PAGE.includes("setGithubSelected([])"));
  assert.ok(PROJECT_PAGE.includes("if (session.install_url)"));
  assert.ok(REPOSITORY_PICKER.includes("Escolha os repositórios deste projeto"));
  assert.ok(REPOSITORY_PICKER.includes('type="search"'));
  assert.ok(REPOSITORY_PICKER.includes('useState<"available" | "selected" | "results">("available")'));
  assert.ok(REPOSITORY_PICKER.includes("Disponíveis ("));
  assert.ok(REPOSITORY_PICKER.includes("Selecionados ("));
  assert.ok(REPOSITORY_PICKER.includes("Resultados ("));
  assert.ok(REPOSITORY_PICKER.includes("Exibindo os 30 repositórios com atividade mais recente"));
  assert.ok(REPOSITORY_PICKER.includes("onSearch(normalizedSearch)"));
  assert.ok(REPOSITORY_PICKER.includes("normalizedSearch.length === 1"));
  assert.ok(REPOSITORY_PICKER.includes("Digite mais um caractere para buscar em toda a organização"));
  assert.ok(REPOSITORY_PICKER.includes("Preparando uma conexão segura"));
  assert.ok(API.includes('params.set("search", search.trim())'));
  assert.ok(REPOSITORY_PICKER.includes('repo.connection_status === "available"'));
  assert.ok(REPOSITORY_PICKER.includes("Em outro projeto"));
  assert.ok(REPOSITORY_PICKER.includes("Liberar mais repositórios no GitHub"));
  assert.ok(REPOSITORY_PICKER.includes('repositoryScope === "all"'));
  assert.ok(REPOSITORY_PICKER.includes("Acesso organizacional completo"));
});

test("reconexão manual confirma e reativa somente o repositório escolhido", () => {
  const handler = PROJECT_PAGE.indexOf("async function handleReconnectRepository(repository: ProjectRepository)");
  const fimHandler = PROJECT_PAGE.indexOf("async function handleExportGdocs", handler);
  const fluxo = PROJECT_PAGE.slice(handler, fimHandler);

  assert.ok(handler >= 0, "faltou o fluxo dedicado de reconexão");
  assert.ok(fluxo.includes("Reconectar ${repository.full_name} a este projeto?"));
  assert.ok(fluxo.includes("[repository.github_repository_id]"));
  assert.ok(fluxo.includes("await connectProjectRepositories("));
  assert.ok(!fluxo.includes("setGithubPickerOpen(true)"));
  assert.ok(PROJECT_PAGE.includes('repo.permission_status === "disconnected"'));
  assert.ok(PROJECT_PAGE.includes("onClick={() => handleReconnectRepository(repo)}"));
  assert.ok(PROJECT_PAGE.includes("Reautorizar"));
});
