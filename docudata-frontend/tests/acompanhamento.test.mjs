import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("dashboard de acompanhamento tem os 4 blocos e filtros", () => {
  const p = ler("app/acompanhamento/page.tsx");
  for (const s of ["Acompanhamento dos projetos", "Precisa de você", "Evolução por sprint", "Risco de prazo", "Por gerente",
                   "Features entregues", "SPI médio", "Metas batidas", "Tasks travadas", "Todos os gerentes",
                   "Nenhum projeto precisa de atenção agora.", "sem comparação"]) assert.ok(p.includes(s), s);
});

test("mapa de calor e dispersão", () => {
  assert.ok(existsSync(new URL("../app/components/acompanhamento/MapaCalor.tsx", import.meta.url)));
  const m = ler("app/components/acompanhamento/MapaCalor.tsx");
  for (const s of ["sem dado", "≥ 0,9", "0,7–0,9", "< 0,7", "aria-label"]) assert.ok(m.includes(s), s);
  const d = ler("app/components/acompanhamento/DispersaoPrazo.tsx");
  for (const s of ["% do prazo consumido", "% das funcionalidades aprovadas", "sem datas do contrato", "<title>"]) assert.ok(d.includes(s), s);
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
  for (const s of ["!projeto.sprint_atual.fechada", "!s.fechada", "Nenhuma sprint aberta para definir meta.", "metaDe === sprintId", "funcs === null"]) assert.ok(m.includes(s), s);
});

test("tela ignora resposta antiga ao alternar a subárea e chips do Escopo quebram linha", () => {
  assert.ok(ler("app/acompanhamento/page.tsx").includes("pedido.current"));
  assert.ok(ler("app/components/EscopoTab.tsx").includes('display: "flex", flexWrap: "wrap", gap: 4 }}><Chip tone={statusTone'));
});
