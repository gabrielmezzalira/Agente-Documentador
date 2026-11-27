import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const ler = (p) => readFileSync(join(raiz, p), "utf8");

test("backlog é um quadro de 3 colunas, sem aprovação, aberto a quem não é operacional", () => {
  const pagina = ler("app/backlog/page.tsx");
  assert.match(pagina, /id: "planejado"[\s\S]*id: "andamento"[\s\S]*id: "concluido"/);
  assert.doesNotMatch(pagina, /pendente_aprovacao/);
  assert.match(pagina, /draggable/);
  assert.match(pagina, /cargo !== "operacional"/);
  assert.match(ler("app/components/shell/navItems.ts"), /cargo !== "operacional"\) items\.push\(\{ href: "\/backlog"/);
});

test("clicar na foto abre a versão inteira em tela cheia", () => {
  const avatar = ler("app/components/Avatar.tsx");
  assert.match(avatar, /FotoAmpliada/);
  assert.match(avatar, /createPortal/);
  assert.match(ler("app/lib/api.ts"), /tam=completa/);
});

test("cards se reordenam arrastando, sem seletores de prioridade/mover", () => {
  const pagina = ler("app/backlog/page.tsx");
  assert.match(pagina, /reordenarBacklog/);
  assert.match(pagina, /LinhaDeEncaixe/);
  assert.doesNotMatch(pagina, /<Select/);
});
