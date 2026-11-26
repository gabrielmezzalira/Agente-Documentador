"use client";

import { useEffect, useMemo, useRef, useState, type ClipboardEvent } from "react";
import { Button } from "./ds";
import TaskMarkdown, { anexosCitados, referenciaAnexo, semReferencia } from "./TaskMarkdown";
import { ds, labelStyle } from "../lib/ds";
import {
  TASK_ANEXO_MAX_BYTES, TASK_ANEXO_TIPOS, deleteTaskAnexo, listTaskAnexos, taskAnexoSrc, uploadTaskAnexo, type TaskAnexo,
} from "../lib/api";

const MAX_IMAGENS = 12;
const MAX_TEXTO = 20000;
const TIPOS = new Set(TASK_ANEXO_TIPOS.split(","));

function erroDoArquivo(f: File): string | null {
  if (!TIPOS.has(f.type)) return `"${f.name}" não é PNG, JPG, WEBP ou GIF.`;
  if (f.size > TASK_ANEXO_MAX_BYTES) return `"${f.name}" passa de ${TASK_ANEXO_MAX_BYTES / (1024 * 1024)} MB.`;
  return null;
}

const miniatura: React.CSSProperties = {
  width: 88, height: 88, objectFit: "cover", borderRadius: 10, border: `1px solid ${ds.border}`, display: "block", background: "rgba(255,255,255,0.04)",
};

/** Imagem na leitura da task: ocupa toda a largura disponível, na proporção original. */
const imagemCheia: React.CSSProperties = {
  display: "block", width: "100%", height: "auto", borderRadius: 10, border: `1px solid ${ds.border}`, background: "rgba(255,255,255,0.04)",
};

const campo: React.CSSProperties = {
  width: "100%", padding: "10px 14px", border: "1px solid rgba(62,224,111,0.17)", borderRadius: 10, fontSize: 13.5, lineHeight: 1.6,
  color: ds.text, background: "rgba(62,224,111,0.055)", boxSizing: "border-box", fontFamily: "inherit", resize: "vertical",
};

function PreviewLocal({ arquivo }: { arquivo: File }) {
  const url = useMemo(() => URL.createObjectURL(arquivo), [arquivo]);
  useEffect(() => () => URL.revokeObjectURL(url), [url]);
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={arquivo.name} style={miniatura} />;
}

/**
 * Editor do material de apoio da task (só gerente/líder/owner): texto em Markdown e imagens que o operacional vê.
 * Com a task já criada (`taskId`), a imagem sobe e some na hora; sem ela, as imagens ficam na fila (`pendentes`)
 * e o formulário as envia depois de criar a task.
 */
export function MaterialApoioEditor({ taskId, texto, onTexto, pendentes, onPendentes }: {
  taskId: string | null;
  texto: string;
  onTexto: (v: string) => void;
  pendentes: File[];
  onPendentes: (f: File[]) => void;
}) {
  const [aba, setAba] = useState<"escrever" | "visualizar">("escrever");
  const [anexos, setAnexos] = useState<TaskAnexo[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const areaRef = useRef<HTMLTextAreaElement>(null);
  const arquivoRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!taskId) return;
    let vivo = true;
    listTaskAnexos(taskId).then((l) => { if (vivo) setAnexos(l); }).catch((e) => { if (vivo) setErro(e instanceof Error ? e.message : "Erro ao carregar as imagens"); });
    return () => { vivo = false; };
  }, [taskId]);

  const total = taskId ? anexos.length : pendentes.length;

  async function adicionar(arquivos: File[]) {
    setErro("");
    const novos = arquivos.slice(0, Math.max(0, MAX_IMAGENS - total));
    if (arquivos.length > novos.length) setErro(`Cada task aceita até ${MAX_IMAGENS} imagens.`);
    const invalido = novos.map(erroDoArquivo).find(Boolean);
    if (invalido) { setErro(invalido); return; }
    if (!taskId) { onPendentes([...pendentes, ...novos]); return; }
    setEnviando(true);
    try {
      for (const f of novos) {
        const salvo = await uploadTaskAnexo(taskId, f);
        setAnexos((a) => [...a, salvo]);
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível enviar a imagem");
    } finally {
      setEnviando(false);
    }
  }

  function colar(e: ClipboardEvent<HTMLTextAreaElement>) {
    const imagens = Array.from(e.clipboardData.files).filter((f) => f.type.startsWith("image/"));
    if (imagens.length === 0) return;
    e.preventDefault();
    void adicionar(imagens);
  }

  function inserir(nome: string) {
    const el = areaRef.current;
    const pos = el?.selectionStart ?? texto.length;
    const antes = texto.slice(0, pos);
    const depois = texto.slice(pos);
    const novo = `${antes}${antes && !antes.endsWith("\n\n") ? (antes.endsWith("\n") ? "\n" : "\n\n") : ""}${referenciaAnexo(nome)}\n\n${depois}`;
    onTexto(novo.slice(0, MAX_TEXTO));
    setAba("escrever");
    el?.focus();
  }

  async function remover(nome: string) {
    if (!taskId || !confirm("Remover esta imagem? Ela some da task agora, mesmo que você não salve o formulário.")) return;
    setErro("");
    try {
      await deleteTaskAnexo(taskId, nome);
      setAnexos((a) => a.filter((x) => x.nome !== nome));
      onTexto(semReferencia(texto, nome));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível remover a imagem");
    }
  }

  const abaBtn = (id: "escrever" | "visualizar", rotulo: string) => (
    <button
      key={id} type="button" role="tab" aria-selected={aba === id} onClick={() => setAba(id)}
      style={{
        background: aba === id ? ds.greenSoft : "transparent", color: aba === id ? ds.green : ds.muted, border: "none", cursor: "pointer",
        fontFamily: "inherit", fontSize: 12.5, fontWeight: 600, padding: "5px 12px", borderRadius: 8,
      }}
    >
      {rotulo}
    </button>
  );

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 6 }}>
        <label htmlFor="task-material" style={{ ...labelStyle, margin: 0 }}>Material de apoio</label>
        <div role="tablist" aria-label="Modo do editor" style={{ display: "flex", gap: 2 }}>{abaBtn("escrever", "Escrever")}{abaBtn("visualizar", "Visualizar")}</div>
      </div>

      {aba === "escrever" ? (
        <textarea
          id="task-material" ref={areaRef} value={texto} rows={6} maxLength={MAX_TEXTO} aria-describedby="task-material-ajuda"
          onChange={(e) => onTexto(e.target.value)} onPaste={colar} style={campo}
          placeholder={"## Como fazer\n1. Passo a passo\n2. Link da referência\n\nCole um print aqui ou use Adicionar imagem."}
        />
      ) : (
        <div style={{ ...campo, minHeight: 138, resize: "none" }}>
          {texto.trim() ? <TaskMarkdown taskId={taskId ?? ""} texto={texto} /> : <span style={{ color: ds.dim }}>Nada para mostrar ainda.</span>}
        </div>
      )}
      <p id="task-material-ajuda" style={{ fontSize: 12, color: ds.muted, margin: "6px 0 10px", lineHeight: 1.5 }}>
        O operacional vê este texto na task. Aceita Markdown (títulos, listas, links, código, tabelas). Fica separado da descrição e não muda o nível da task.
      </p>

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <Button size="sm" variant="secondary" disabled={enviando || total >= MAX_IMAGENS} onClick={() => arquivoRef.current?.click()}>
          {enviando ? "Enviando…" : "Adicionar imagem"}
        </Button>
        <input
          ref={arquivoRef} type="file" accept={TASK_ANEXO_TIPOS} multiple hidden aria-label="Escolher imagens"
          onChange={(e) => { const f = Array.from(e.target.files ?? []); e.target.value = ""; void adicionar(f); }}
        />
        <span style={{ fontSize: 12, color: ds.muted }}>
          PNG, JPG, WEBP ou GIF, até {TASK_ANEXO_MAX_BYTES / (1024 * 1024)} MB · {total}/{MAX_IMAGENS}
          {taskId ? " · enviadas e removidas na hora" : " · enviadas quando a task for criada"}
        </span>
      </div>

      {erro && <p role="alert" style={{ color: ds.red, fontSize: 12.5, margin: "8px 0 0" }}>{erro}</p>}

      {(taskId ? anexos.length > 0 : pendentes.length > 0) && (
        <ul style={{ listStyle: "none", margin: "12px 0 0", padding: 0, display: "flex", gap: 12, flexWrap: "wrap" }}>
          {taskId
            ? anexos.map((a) => (
                <li key={a.nome} style={{ display: "flex", flexDirection: "column", gap: 6, width: 88 }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={taskAnexoSrc(taskId, a.nome)} alt={a.nome} style={miniatura} loading="lazy" />
                  <button type="button" onClick={() => inserir(a.nome)} style={linkBtn}>Inserir no texto</button>
                  <button type="button" onClick={() => void remover(a.nome)} style={{ ...linkBtn, color: ds.red }}>Remover</button>
                </li>
              ))
            : pendentes.map((f, i) => (
                <li key={`${f.name}-${i}`} style={{ display: "flex", flexDirection: "column", gap: 6, width: 88 }}>
                  <PreviewLocal arquivo={f} />
                  <button type="button" onClick={() => onPendentes(pendentes.filter((_, j) => j !== i))} style={{ ...linkBtn, color: ds.red }}>Tirar</button>
                </li>
              ))}
        </ul>
      )}
    </div>
  );
}

const linkBtn: React.CSSProperties = {
  background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 12, textAlign: "left", color: ds.text2,
  textDecoration: "underline", textUnderlineOffset: 2,
};

/** O que o operacional (e qualquer pessoa com acesso) vê na task: o texto e as imagens que o texto não mostra. */
export function MaterialApoioLeitura({ taskId, texto }: { taskId: string; texto: string | null | undefined }) {
  const [anexos, setAnexos] = useState<TaskAnexo[]>([]);

  useEffect(() => {
    let vivo = true;
    listTaskAnexos(taskId).then((l) => { if (vivo) setAnexos(l); }).catch(() => { if (vivo) setAnexos([]); });
    return () => { vivo = false; };
  }, [taskId]);

  const citados = anexosCitados(texto);
  const soltas = anexos.filter((a) => !citados.has(a.nome));
  if (!(texto ?? "").trim() && soltas.length === 0) return null;

  return (
    <section aria-label="Material de apoio" style={{ marginBottom: 20 }}>
      <span style={{ ...labelStyle, display: "block", marginBottom: 8 }}>Material de apoio</span>
      {(texto ?? "").trim() && <TaskMarkdown taskId={taskId} texto={texto!} />}
      {soltas.length > 0 && (
        <ul style={{ listStyle: "none", margin: (texto ?? "").trim() ? "12px 0 0" : 0, padding: 0, display: "flex", flexDirection: "column", gap: 12 }}>
          {soltas.map((a) => (
            <li key={a.nome}>
              <a href={taskAnexoSrc(taskId, a.nome)} target="_blank" rel="noreferrer noopener" title="Abrir em tamanho original" style={{ display: "block" }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={taskAnexoSrc(taskId, a.nome)} alt={a.nome.replace(/^[a-z0-9]{12}-/, "").replace(/\.[a-z]+$/, "").replace(/-/g, " ")} style={imagemCheia} loading="lazy" />
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
