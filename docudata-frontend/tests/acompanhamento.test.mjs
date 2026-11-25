import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("dashboard de acompanhamento: filtro por status, lista de projetos com progresso, por gerente e legenda", () => {
  const p = ler("app/acompanhamento/page.tsx");
  for (const s of ["Acompanhamento dos projetos", "Projetos", "Por gerente", "Todos os gerentes", "O que significa cada status e pendência",
                   "dos pontos planejados já foram concluídos", "aria-selected", "Nenhum projeto com este status.", "Escopo vazio",
                   "Sem datas do contrato", "Escopo × prazo", "Nenhuma sprint iniciada"]) assert.ok(p.includes(s), s);
});

test("pendências e status têm explicação e quem resolve", () => {
  const v = ler("app/components/acompanhamento/visual.ts");
  for (const c of ["spi_critico", "prazo", "meta_ruim", "travadas", "spi_caindo", "sem_meta", "sem_sprint", "sem_planejamento",
                   "sem_datas", "sem_funcionalidades", "sem_gerente"]) assert.ok(v.includes(`${c}: {`), c);
  for (const s of ["Meta da sprint não definida", "quem:", "Crítico", "Faltam dados", "Pendente de aprovação"]) assert.ok(v.includes(s), s);
  assert.ok(ler("app/components/acompanhamento/ProjetoDetalhePainel.tsx").includes("Quem resolve"));
});

test("api e menu", () => {
  const api = ler("app/lib/api.ts");
  for (const s of ["getAcompanhamento", "getDetalheProjeto", "definirMetaSprint", "getEventosMeta"]) assert.ok(api.includes(s), s);
  assert.match(ler("app/components/shell/navItems.ts"), /isOwnerOrLider\(cargo\)[\s\S]{0,200}\/acompanhamento/);
});

test("aba Escopo mostra o selo da meta da sprint", () => {
  assert.ok(ler("app/components/EscopoTab.tsx").includes("meta da sprint"));
  assert.ok(ler("app/lib/api.ts").includes("meta_sprints?: number[]"));
});

test("modal de meta ignora sprint fechada e amarra a meta carregada à sprint", () => {
  assert.ok(ler("app/lib/api.ts").includes("fechada: boolean"));
  const m = ler("app/components/DefinirMetaModal.tsx");
  for (const s of ["!detalhe.sprint_atual.fechada", "!s.fechada", "Nenhuma sprint aberta para definir meta.", "metaDe === sprintId", "funcs === null"]) assert.ok(m.includes(s), s);
});

test("tela ignora resposta antiga ao alternar a subárea e chips do Escopo quebram linha", () => {
  assert.ok(ler("app/acompanhamento/page.tsx").includes("pedido.current"));
  assert.ok(ler("app/components/EscopoTab.tsx").includes('display: "flex", flexWrap: "wrap", gap: 4 }}><Chip tone={statusTone'));
});

test("painel de detalhe do projeto", () => {
  const p = ler("app/components/acompanhamento/ProjetoDetalhePainel.tsx");
  for (const s of ["Definir meta", "Sprint a sprint", "abaixo do piso", "sem histórico para o piso", "Planejadas fora da meta:",
                   "Histórico de mudanças da meta", "Sem meta nesta sprint.", "meta batida", "O que está pendente", "O que foi planejado",
                   "Tasks da sprint", "do planejado concluído", "sem responsável", "falta a Planning"]) assert.ok(p.includes(s), s);
  assert.ok(ler("app/acompanhamento/page.tsx").includes("ProjetoDetalhePainel"));
});

test("SPI parcial da sprint aberta, projeto sem funcionalidades e estados sem dado", () => {
  const p = ler("app/acompanhamento/page.tsx");
  for (const s of ["SPI de S", "Atualizando...", "!t.parcial"]) assert.ok(p.includes(s), s);
  assert.ok(/metas_fechadas > 0 \?/.test(p), "metas sem fechadas não aparecem");
  assert.ok(!/const carregar[\s\S]{0,200}setDados\(null\)/.test(p), "recarregar não esvazia o dashboard");
  const d = ler("app/components/acompanhamento/ProjetoDetalhePainel.tsx");
  for (const s of ["SPI da sprint atual (parcial)", "SPI da última sprint fechada", "sem funcionalidades", "setEventos(null)"]) assert.ok(d.includes(s), s);
  assert.ok(d.includes("f.pct_tasks != null && <ProgressBar"), "barra omitida sem pct_tasks");
});

test("aba Indicadores e metas: números, meta da sprint atual e histórico", () => {
  const p = ler("app/acompanhamento/page.tsx");
  for (const s of ["Indicadores e metas", "<Indicadores"]) assert.ok(p.includes(s), s);
  const i = ler("app/components/acompanhamento/Indicadores.tsx");
  for (const s of ["Metas batidas", "SPI médio", "Funcionalidades entregues", "Tasks travadas", "Meta da sprint atual",
                   "Meta não definida", "Histórico de metas", "meta batida", "sprint em andamento", "meta_funcionalidades"]) assert.ok(i.includes(s), s);
});
