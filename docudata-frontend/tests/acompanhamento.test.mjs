import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("tela /acompanhamento existe com os blocos e o modal de meta", () => {
  assert.ok(existsSync(new URL("../app/acompanhamento/page.tsx", import.meta.url)));
  const p = ler("app/acompanhamento/page.tsx");
  for (const s of ["Acompanhamento dos projetos", "Em risco", "Metas batidas", "Definir meta", "Histórico de mudanças da meta", "Planejadas fora da meta:", "sem meta"]) {
    assert.ok(p.includes(s), s);
  }
  const m = ler("app/components/DefinirMetaModal.tsx");
  for (const s of ["Salvar meta", "planejada nesta sprint"]) assert.ok(m.includes(s), s);
});

test("api e menu do acompanhamento", () => {
  const api = ler("app/lib/api.ts");
  for (const s of ["getAcompanhamento", "definirMetaSprint", "getMetaSprint", "getEventosMeta"]) assert.ok(api.includes(s), s);
  assert.match(ler("app/components/shell/navItems.ts"), /isOwnerOrLider\(cargo\)[\s\S]{0,200}\/acompanhamento/);
});

test("aba Escopo mostra o selo da meta da sprint", () => {
  assert.ok(ler("app/components/EscopoTab.tsx").includes("meta da sprint"));
  assert.ok(ler("app/lib/api.ts").includes("meta_sprints?: number[]"));
});
