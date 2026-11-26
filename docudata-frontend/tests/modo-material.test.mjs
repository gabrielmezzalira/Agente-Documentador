import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const ler = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");

test("em Atribuição o responsável é obrigatório ao criar a task, com aviso ao gerente", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  for (const s of ['Escolha o responsável da task.', "Responsável *", "toda task precisa de um responsável",
                   "Escolha quem vai fazer a task", 'modoTrabalho !== "PULL" && !operacionalId']) assert.ok(k.includes(s), s);
  assert.ok(!k.includes("Sem operacional</option>"), "a opção de criar sem responsável saiu do formulário");
});

test("aviso do modo de trabalho diz qual é o modo e que existe o outro", () => {
  const a = ler("app/components/ModoTrabalhoAviso.tsx");
  for (const s of ["Modo {m.nome}", "Existe também o modo", "Pull", "Atribuição", "Configurações do projeto"]) assert.ok(a.includes(s), s);
  assert.ok(ler("app/components/TasksKanbanTab.tsx").includes("<ModoTrabalhoAviso modo={modoTrabalho} />"));
});

test("material de apoio: gerente edita (texto e imagens), operacional só lê", () => {
  const k = ler("app/components/TasksKanbanTab.tsx");
  assert.ok(/ehGerente && \(\s*<MaterialApoioEditor/.test(k), "editor só para gerente/líder/owner");
  for (const s of ["<MaterialApoioLeitura", "materialMudou", "uploadTaskAnexo(saved.id", "A task foi criada, mas"]) assert.ok(k.includes(s), s);
  const m = ler("app/components/MaterialApoio.tsx");
  for (const s of ["Adicionar imagem", "Inserir no texto", "Visualizar", "onPaste", "TASK_ANEXO_MAX_BYTES", "MAX_IMAGENS"]) assert.ok(m.includes(s), s);
  const api = ler("app/lib/api.ts");
  for (const s of ["listTaskAnexos", "uploadTaskAnexo", "deleteTaskAnexo", "taskAnexoSrc", "material_apoio"]) assert.ok(api.includes(s), s);
});

test("markdown da task só abre imagens anexadas do próprio backend e não interpreta HTML solto", () => {
  const t = ler("app/components/TaskMarkdown.tsx");
  for (const s of ["anexo:", "NOME_ANEXO", "defaultUrlTransform", 'rel="noreferrer noopener"', 'referrerPolicy="no-referrer"']) assert.ok(t.includes(s), s);
  assert.ok(!t.includes("rehypeRaw") && !t.includes("dangerouslySetInnerHTML"), "sem HTML cru");
});

test("imagens do material de apoio ocupam toda a largura na leitura", () => {
  const m = ler("app/components/MaterialApoio.tsx");
  assert.ok(/imagemCheia[\s\S]{0,160}width: "100%"/.test(m), "galeria em largura total");
  assert.ok(!m.includes("width: 120, height: 120"), "sem miniatura fixa na leitura");
  assert.ok(ler("app/components/TaskMarkdown.tsx").includes(".task-md img{display:block;width:100%"), "imagem no texto em largura total");
});
