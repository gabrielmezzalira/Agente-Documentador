import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf-8");
const API = ler("app/lib/api.ts");

test("api.ts expõe as funções de foto de perfil", () => {
  for (const f of ["chaveFoto", "fotoSrc", "listFotos", "uploadFoto", "deleteFoto"]) {
    assert.match(API, new RegExp(`export (async )?function ${f}\\b`));
  }
});

test("a chave da foto normaliza como o backend (sem acento, minúscula, hífens)", () => {
  const corpo = API.match(/export function chaveFoto[\s\S]*?\n}\n/)[0].replace(/export function chaveFoto\(nome: string \| null \| undefined\): string/, "function chaveFoto(nome)");
  const chaveFoto = new Function(`${corpo}; return chaveFoto;`)();
  assert.equal(chaveFoto("  Ana  Luíza D'Ávila "), "ana-luiza-d-avila");
  assert.equal(chaveFoto(null), "");
});

test("o provider de fotos envolve o app autenticado", () => {
  assert.match(ler("app/components/AuthGuard.tsx"), /<FotosProvider>/);
});

test("squads, pessoas e menu lateral permitem trocar a foto; avaliação e performance mostram", () => {
  for (const p of ["app/[subarea]/projects/[id]/page.tsx", "app/pessoas/page.tsx", "app/components/shell/Sidebar.tsx"]) {
    assert.match(ler(p), /<AvatarEditavel/, p);
  }
  for (const p of ["app/avaliacoes/page.tsx", "app/performance/page.tsx", "app/components/MetricasTab.tsx", "app/components/AvaliacaoSemanalModal.tsx"]) {
    assert.match(ler(p), /<PessoaComFoto/, p);
  }
});
