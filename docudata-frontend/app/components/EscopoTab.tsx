"use client";

import { useState, useEffect } from "react";
import {
  FuncionalidadeResponse,
  FuncionalidadeProposta,
  importarFuncionalidades,
  importarFuncionalidadesArquivo,
  confirmarImportacao,
  createFuncionalidade,
  updateFuncionalidade,
} from "../lib/api";

const PRIORIDADE_LABEL: Record<string, string> = {
  must: "Must",
  should: "Should",
  could: "Could",
  wont: "Won't",
};

const PRIORIDADE_COLOR: Record<string, string> = {
  must: "#dc2626",
  should: "#d97706",
  could: "#2563eb",
  wont: "#9ca3af",
};

const STATUS_LABEL: Record<string, string> = {
  nao_iniciada: "Não iniciada",
  em_andamento: "Em andamento",
  em_ajuste: "Em ajuste",
  concluida: "Concluída",
};

const STATUS_COLOR: Record<string, string> = {
  nao_iniciada: "#94a3b8",
  em_andamento: "#2563eb",
  em_ajuste: "#d97706",
  concluida: "#16a34a",
};

type Step = "idle" | "input" | "loading" | "review" | "saving" | "manual";
type InputMode = "texto" | "arquivo";

interface Props {
  projectId: string;
  funcionalidades: FuncionalidadeResponse[];
  onImported: (novas: FuncionalidadeResponse[]) => void;
}

export default function EscopoTab({ projectId, funcionalidades, onImported }: Props) {
  const [step, setStep] = useState<Step>("idle");
  const [inputMode, setInputMode] = useState<InputMode>("arquivo");
  const [texto, setTexto] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [propostas, setPropostas] = useState<FuncionalidadeProposta[]>([]);
  const [selecionadas, setSelecionadas] = useState<Set<number>>(new Set());
  const [erro, setErro] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{ id_funcional: string; titulo: string; descricao: string; criterios_aceite: string[]; prioridade: string; responsavel: string }>({ id_funcional: "", titulo: "", descricao: "", criterios_aceite: [""], prioridade: "should", responsavel: "" });
  const [savingEdit, setSavingEdit] = useState(false);
  const [erroEdit, setErroEdit] = useState("");
  const [funcList, setFuncList] = useState<FuncionalidadeResponse[]>(funcionalidades);
  useEffect(() => { setFuncList(funcionalidades); }, [funcionalidades]);

  function startEdit(f: FuncionalidadeResponse) {
    setEditingId(f.id);
    setEditForm({ id_funcional: f.id_funcional, titulo: f.titulo, descricao: f.descricao ?? "", criterios_aceite: f.criterios_aceite.length ? f.criterios_aceite : [""], prioridade: f.prioridade, responsavel: f.responsavel ?? "" });
    setErroEdit("");
  }

  async function handleSalvarEdit() {
    if (!editForm.titulo.trim()) { setErroEdit("Título é obrigatório."); return; }
    const criterios = editForm.criterios_aceite.filter(c => c.trim());
    if (!criterios.length) { setErroEdit("Adicione ao menos um critério de aceite."); return; }
    setSavingEdit(true);
    setErroEdit("");
    try {
      const atualizada = await updateFuncionalidade(editingId!, {
        id_funcional: editForm.id_funcional.trim() || undefined,
        titulo: editForm.titulo.trim(),
        descricao: editForm.descricao.trim() || undefined,
        criterios_aceite: criterios,
        prioridade: editForm.prioridade,
        responsavel: editForm.responsavel.trim() || undefined,
      });
      setFuncList(prev => prev.map(f => f.id === atualizada.id ? atualizada : f));
      setEditingId(null);
    } catch (e: unknown) {
      setErroEdit((e as Error).message);
    } finally {
      setSavingEdit(false);
    }
  }

  // formulário manual
  const emptyForm = { id_funcional: "", titulo: "", descricao: "", criterios_aceite: [""], prioridade: "should", responsavel: "" };
  const [form, setForm] = useState(emptyForm);
  const [savingManual, setSavingManual] = useState(false);

  async function handleSalvarManual() {
    if (!form.titulo.trim()) { setErro("Título é obrigatório."); return; }
    const criterios = form.criterios_aceite.filter(c => c.trim());
    if (!criterios.length) { setErro("Adicione ao menos um critério de aceite."); return; }
    setSavingManual(true);
    setErro("");
    try {
      const nova = await createFuncionalidade({
        project_id: projectId,
        id_funcional: form.id_funcional.trim() || `F${String(funcList.length + 1).padStart(2, "0")}`,
        titulo: form.titulo.trim(),
        descricao: form.descricao.trim() || undefined,
        criterios_aceite: criterios,
        prioridade: form.prioridade,
        responsavel: form.responsavel.trim() || undefined,
      });
      setFuncList(prev => [...prev, nova]);
      onImported([nova]);
      setForm(emptyForm);
      setStep("idle");
    } catch (e: unknown) {
      setErro((e as Error).message);
    } finally {
      setSavingManual(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const ok = file.name.endsWith(".pdf") || file.name.endsWith(".docx") || file.name.endsWith(".txt");
    if (!ok) { setErro("Formato não suportado. Use PDF, DOCX ou TXT."); return; }
    setErro("");
    setArquivo(file);
  }

  async function handleAnalisar() {
    setErro("");
    setStep("loading");
    try {
      let resultado: FuncionalidadeProposta[];
      if (inputMode === "arquivo") {
        if (!arquivo) { setErro("Selecione um arquivo antes de continuar."); setStep("input"); return; }
        resultado = await importarFuncionalidadesArquivo(projectId, arquivo);
      } else {
        if (texto.trim().length < 20) { setErro("Cole o texto do contrato antes de continuar."); setStep("input"); return; }
        resultado = await importarFuncionalidades(projectId, texto);
      }
      setPropostas(resultado);
      setSelecionadas(new Set(resultado.map((_, i) => i)));
      setStep("review");
    } catch (e: unknown) {
      setErro((e as Error).message);
      setStep("input");
    }
  }

  async function handleConfirmar() {
    setStep("saving");
    setErro("");
    try {
      const itens = propostas.map((p, i) => ({ proposta: p, confirmed: selecionadas.has(i) }));
      const criadas = await confirmarImportacao(projectId, itens);
      onImported(criadas);
      setStep("idle");
      setTexto("");
      setPropostas([]);
      setSelecionadas(new Set());
    } catch (e: unknown) {
      setErro((e as Error).message);
      setStep("review");
    }
  }

  function toggleSelecionada(i: number) {
    setSelecionadas((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  function handleCancelar() {
    setStep("idle");
    setTexto("");
    setArquivo(null);
    setPropostas([]);
    setSelecionadas(new Set());
    setErro("");
  }

  const totalPorStatus = funcionalidades.reduce<Record<string, number>>((acc, f) => {
    acc[f.status] = (acc[f.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20, marginTop: 4 }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 800, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
            Escopo
            <span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 600, marginLeft: 10 }}>
              {funcionalidades.length} {funcionalidades.length === 1 ? "funcionalidade" : "funcionalidades"}
            </span>
          </h2>
          <p style={{ color: "#64748b", fontSize: 13, margin: "6px 0 0", lineHeight: 1.5, maxWidth: 620 }}>
            Lista de funcionalidades do projeto. Importe direto do texto do contrato ou da proposta — a IA extrai e propõe cada item para você confirmar.
          </p>
        </div>
        {step === "idle" && (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => { setStep("manual"); setErro(""); setForm(emptyForm); }}
              style={{
                background: "#fff", color: "#0f172a", border: "1px solid #cbd5e1", borderRadius: 8,
                padding: "10px 16px", fontSize: 14, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap",
              }}
            >
              + Adicionar manualmente
            </button>
            <button
              onClick={() => setStep("input")}
              style={{
                background: "#0f172a", color: "#fff", border: "none", borderRadius: 8,
                padding: "10px 18px", fontSize: 14, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap",
              }}
            >
              + Importar do contrato
            </button>
          </div>
        )}
      </div>

      {/* Resumo de status */}
      {funcionalidades.length > 0 && (
        <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
          {Object.entries(totalPorStatus).map(([status, count]) => (
            <div key={status} style={{
              background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8,
              padding: "8px 14px", display: "flex", alignItems: "center", gap: 8,
            }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: STATUS_COLOR[status] ?? "#94a3b8" }} />
              <span style={{ fontSize: 13, color: "#475569", fontWeight: 500 }}>
                {STATUS_LABEL[status] ?? status}
              </span>
              <span style={{ fontSize: 13, color: "#0f172a", fontWeight: 700 }}>{count}</span>
            </div>
          ))}
        </div>
      )}

      {/* Fluxo de importação */}
      {step === "input" && (
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", margin: "0 0 16px" }}>
            Importar do contrato
          </h3>

          {/* Toggle modo */}
          <div style={{ display: "flex", gap: 0, marginBottom: 20, border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden", width: "fit-content" }}>
            {(["arquivo", "texto"] as InputMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setInputMode(mode)}
                style={{
                  padding: "8px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer", border: "none",
                  background: inputMode === mode ? "#0f172a" : "#f8fafc",
                  color: inputMode === mode ? "#fff" : "#64748b",
                  transition: "all 0.15s",
                }}
              >
                {mode === "arquivo" ? "Upload de arquivo" : "Colar texto"}
              </button>
            ))}
          </div>

          {inputMode === "arquivo" ? (
            <div>
              <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 14px", lineHeight: 1.5 }}>
                Faça upload do contrato ou proposta. Aceita PDF (com ou sem texto), DOCX e TXT.
              </p>
              <label
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                style={{
                  display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                  border: `2px dashed ${dragging ? "#2563eb" : arquivo ? "#86efac" : "#cbd5e1"}`,
                  borderRadius: 10, padding: "40px 24px", cursor: "pointer",
                  background: dragging ? "#eff6ff" : arquivo ? "#f0fdf4" : "#f8fafc",
                  transition: "all 0.15s",
                }}
              >
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  style={{ display: "none" }}
                  onChange={(e) => { setErro(""); setArquivo(e.target.files?.[0] ?? null); }}
                />
                {dragging ? (
                  <>
                    <span style={{ fontSize: 36, marginBottom: 10 }}>📂</span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "#2563eb" }}>Solte aqui</span>
                  </>
                ) : arquivo ? (
                  <>
                    <span style={{ fontSize: 32, marginBottom: 8 }}>✓</span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "#16a34a" }}>{arquivo.name}</span>
                    <span style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                      {(arquivo.size / 1024).toFixed(0)} KB · clique ou arraste para trocar
                    </span>
                  </>
                ) : (
                  <>
                    <span style={{ fontSize: 36, marginBottom: 10 }}>📄</span>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "#475569" }}>Arraste o arquivo aqui</span>
                    <span style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>ou clique para selecionar · PDF, DOCX ou TXT</span>
                  </>
                )}
              </label>
            </div>
          ) : (
            <div>
              <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 12px", lineHeight: 1.5 }}>
                Cole o texto completo do contrato ou proposta. A IA extrai cada funcionalidade com título, descrição e critérios de aceite.
              </p>
              <textarea
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                placeholder="Cole aqui o texto do contrato..."
                rows={12}
                style={{
                  width: "100%", boxSizing: "border-box", border: "1px solid #cbd5e1",
                  borderRadius: 8, padding: "12px 14px", fontSize: 13, lineHeight: 1.6,
                  fontFamily: "inherit", resize: "vertical", outline: "none", color: "#0f172a",
                }}
              />
            </div>
          )}

          {erro && <p style={{ color: "#dc2626", fontSize: 13, marginTop: 10 }}>{erro}</p>}
          <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
            <button
              onClick={handleAnalisar}
              style={{
                background: "#0f172a", color: "#fff", border: "none", borderRadius: 8,
                padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer",
              }}
            >
              Analisar com IA
            </button>
            <button
              onClick={handleCancelar}
              style={{
                background: "transparent", color: "#64748b", border: "1px solid #cbd5e1",
                borderRadius: 8, padding: "10px 20px", fontSize: 14, cursor: "pointer",
              }}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {step === "loading" && (
        <div style={{
          background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12,
          padding: 40, textAlign: "center", marginBottom: 24,
        }}>
          <p style={{ color: "#475569", fontSize: 14, margin: 0 }}>
            Analisando o contrato e extraindo funcionalidades...
          </p>
          <p style={{ color: "#94a3b8", fontSize: 12, margin: "8px 0 0" }}>
            Isso pode levar alguns segundos
          </p>
        </div>
      )}

      {step === "review" && (
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", margin: 0 }}>
                {propostas.length} funcionalidades encontradas
              </h3>
              <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0" }}>
                Desmarque as que não quer salvar, depois confirme.
              </p>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={handleCancelar}
                style={{
                  background: "transparent", color: "#64748b", border: "1px solid #cbd5e1",
                  borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer",
                }}
              >
                Cancelar
              </button>
              <button
                onClick={handleConfirmar}
                disabled={selecionadas.size === 0}
                style={{
                  background: selecionadas.size === 0 ? "#e2e8f0" : "#16a34a",
                  color: selecionadas.size === 0 ? "#94a3b8" : "#fff",
                  border: "none", borderRadius: 8, padding: "8px 16px",
                  fontSize: 13, fontWeight: 600,
                  cursor: selecionadas.size === 0 ? "not-allowed" : "pointer",
                }}
              >
                Salvar {selecionadas.size} selecionadas
              </button>
            </div>
          </div>

          {erro && <p style={{ color: "#dc2626", fontSize: 13, marginBottom: 12 }}>{erro}</p>}

          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <button
              onClick={() => setSelecionadas(new Set(propostas.map((_, i) => i)))}
              style={{ fontSize: 12, color: "#2563eb", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              Selecionar todas
            </button>
            <span style={{ color: "#cbd5e1" }}>·</span>
            <button
              onClick={() => setSelecionadas(new Set())}
              style={{ fontSize: 12, color: "#64748b", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              Desmarcar todas
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {propostas.map((p, i) => (
              <div
                key={i}
                style={{
                  border: `1px solid ${selecionadas.has(i) ? "#bfdbfe" : "#e2e8f0"}`,
                  borderRadius: 10,
                  padding: "14px 16px",
                  background: selecionadas.has(i) ? "#f0f9ff" : "#fafafa",
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
                onClick={() => toggleSelecionada(i)}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <input
                    type="checkbox"
                    checked={selecionadas.has(i)}
                    onChange={() => toggleSelecionada(i)}
                    onClick={(e) => e.stopPropagation()}
                    style={{ marginTop: 2, cursor: "pointer", width: 16, height: 16, accentColor: "#2563eb" }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 11, color: "#94a3b8", fontFamily: "monospace" }}>{p.id_funcional}</span>
                      <span style={{
                        fontSize: 11, fontWeight: 700, color: PRIORIDADE_COLOR[p.prioridade] ?? "#64748b",
                        background: `${PRIORIDADE_COLOR[p.prioridade]}18`,
                        padding: "1px 7px", borderRadius: 4, textTransform: "uppercase",
                      }}>
                        {PRIORIDADE_LABEL[p.prioridade] ?? p.prioridade}
                      </span>
                    </div>
                    <p style={{ fontSize: 14, fontWeight: 600, color: "#0f172a", margin: "4px 0 0" }}>
                      {p.titulo}
                    </p>
                    {p.descricao && (
                      <p style={{ fontSize: 13, color: "#475569", margin: "4px 0 0", lineHeight: 1.5 }}>
                        {p.descricao}
                      </p>
                    )}
                    {p.criterios_aceite.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <p style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", margin: "0 0 4px" }}>
                          Critérios de aceite
                        </p>
                        <ul style={{ margin: 0, paddingLeft: 16 }}>
                          {p.criterios_aceite.map((c, j) => (
                            <li key={j} style={{ fontSize: 12, color: "#475569", marginBottom: 2 }}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {step === "saving" && (
        <div style={{
          background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12,
          padding: 40, textAlign: "center", marginBottom: 24,
        }}>
          <p style={{ color: "#475569", fontSize: 14, margin: 0 }}>Salvando funcionalidades...</p>
        </div>
      )}

      {step === "manual" && (
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", margin: "0 0 20px" }}>Nova funcionalidade</h3>

          {(
            [
              { label: "ID funcional", key: "id_funcional" as const, placeholder: "Ex: F01 (opcional — gerado automaticamente)" },
              { label: "Título *", key: "titulo" as const, placeholder: "Ex: Autenticação de usuários" },
              { label: "Descrição", key: "descricao" as const, placeholder: "Contexto adicional (opcional)" },
              { label: "Responsável", key: "responsavel" as const, placeholder: "Nome do responsável (opcional)" },
            ] as const
          ).map(({ label, key, placeholder }) => (
            <div key={key} style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>{label}</label>
              <input
                value={form[key]}
                onChange={(e) => setForm(f => ({ ...f, [key]: e.target.value }))}
                placeholder={placeholder}
                style={{
                  width: "100%", boxSizing: "border-box", border: "1px solid #cbd5e1", borderRadius: 8,
                  padding: "9px 12px", fontSize: 13, outline: "none", color: "#0f172a",
                }}
              />
            </div>
          ))}

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>Prioridade</label>
            <select
              value={form.prioridade}
              onChange={(e) => setForm(f => ({ ...f, prioridade: e.target.value }))}
              style={{ border: "1px solid #cbd5e1", borderRadius: 8, padding: "9px 12px", fontSize: 13, color: "#0f172a", background: "#fff" }}
            >
              {[["must", "Must"], ["should", "Should"], ["could", "Could"], ["wont", "Won't"]].map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>Critérios de aceite *</label>
            {form.criterios_aceite.map((c, i) => (
              <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <input
                  value={c}
                  onChange={(e) => {
                    const next = [...form.criterios_aceite];
                    next[i] = e.target.value;
                    setForm(f => ({ ...f, criterios_aceite: next }));
                  }}
                  placeholder={`Critério ${i + 1}`}
                  style={{
                    flex: 1, border: "1px solid #cbd5e1", borderRadius: 8,
                    padding: "9px 12px", fontSize: 13, outline: "none", color: "#0f172a",
                  }}
                />
                {form.criterios_aceite.length > 1 && (
                  <button
                    onClick={() => setForm(f => ({ ...f, criterios_aceite: f.criterios_aceite.filter((_, j) => j !== i) }))}
                    style={{ background: "none", border: "none", color: "#dc2626", fontSize: 18, cursor: "pointer", padding: "0 4px" }}
                  >×</button>
                )}
              </div>
            ))}
            <button
              onClick={() => setForm(f => ({ ...f, criterios_aceite: [...f.criterios_aceite, ""] }))}
              style={{ fontSize: 12, color: "#2563eb", background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              + Adicionar critério
            </button>
          </div>

          {erro && <p style={{ color: "#dc2626", fontSize: 13, marginBottom: 12 }}>{erro}</p>}

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleSalvarManual}
              disabled={savingManual}
              style={{
                background: savingManual ? "#e2e8f0" : "#0f172a", color: savingManual ? "#94a3b8" : "#fff",
                border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600,
                cursor: savingManual ? "not-allowed" : "pointer",
              }}
            >
              {savingManual ? "Salvando..." : "Salvar funcionalidade"}
            </button>
            <button
              onClick={() => { setStep("idle"); setErro(""); }}
              style={{ background: "transparent", color: "#64748b", border: "1px solid #cbd5e1", borderRadius: 8, padding: "10px 20px", fontSize: 14, cursor: "pointer" }}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Lista existente */}
      {funcList.length === 0 && step === "idle" ? (
        <div style={{ background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: 12, padding: 48, textAlign: "center" }}>
          <p style={{ color: "#94a3b8", fontSize: 15, margin: "0 0 8px", fontWeight: 500 }}>Nenhuma funcionalidade cadastrada</p>
          <p style={{ color: "#94a3b8", fontSize: 13, margin: 0 }}>Clique em <strong>+ Importar do contrato</strong> para extrair as funcionalidades automaticamente.</p>
        </div>
      ) : (
        step !== "review" && step !== "loading" && step !== "saving" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {funcList.map((f) => (
              <div key={f.id} style={{ background: "#fff", border: `1px solid ${editingId === f.id ? "#bfdbfe" : "#e2e8f0"}`, borderRadius: 10, padding: "14px 16px" }}>

                {/* Header do card — sempre visível */}
                <div
                  style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", cursor: editingId === f.id ? "default" : "pointer" }}
                  onClick={() => { if (editingId !== f.id) setExpanded(expanded === f.id ? null : f.id); }}
                >
                  <span style={{ fontSize: 11, color: "#94a3b8", fontFamily: "monospace" }}>{f.id_funcional}</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: PRIORIDADE_COLOR[f.prioridade] ?? "#64748b", background: `${PRIORIDADE_COLOR[f.prioridade] ?? "#64748b"}18`, padding: "1px 7px", borderRadius: 4, textTransform: "uppercase" }}>
                    {PRIORIDADE_LABEL[f.prioridade] ?? f.prioridade}
                  </span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: STATUS_COLOR[f.status] ?? "#94a3b8", background: `${STATUS_COLOR[f.status] ?? "#94a3b8"}15`, padding: "1px 7px", borderRadius: 4 }}>
                    {STATUS_LABEL[f.status] ?? f.status}
                  </span>
                  <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: "#0f172a" }}>{f.titulo}</span>
                  {editingId !== f.id && (
                    <>
                      <button
                        onClick={(e) => { e.stopPropagation(); startEdit(f); setExpanded(f.id); }}
                        style={{ fontSize: 12, color: "#2563eb", background: "none", border: "none", cursor: "pointer", padding: "2px 6px", borderRadius: 4 }}
                      >
                        Editar
                      </button>
                      <span style={{ fontSize: 12, color: "#94a3b8" }}>{expanded === f.id ? "▲" : "▼"}</span>
                    </>
                  )}
                </div>

                {/* Formulário de edição inline */}
                {editingId === f.id && (
                  <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid #e0f2fe" }}>
                    {([ { label: "ID funcional", key: "id_funcional" as const, placeholder: "F01" }, { label: "Título *", key: "titulo" as const, placeholder: "Título da funcionalidade" }, { label: "Descrição", key: "descricao" as const, placeholder: "Descrição opcional" }, { label: "Responsável", key: "responsavel" as const, placeholder: "Nome do responsável" } ] as const).map(({ label, key, placeholder }) => (
                      <div key={key} style={{ marginBottom: 12 }}>
                        <label style={{ fontSize: 11, fontWeight: 600, color: "#475569", display: "block", marginBottom: 3 }}>{label}</label>
                        <input value={editForm[key]} onChange={(e) => setEditForm(ef => ({ ...ef, [key]: e.target.value }))} placeholder={placeholder}
                          style={{ width: "100%", boxSizing: "border-box", border: "1px solid #cbd5e1", borderRadius: 7, padding: "8px 11px", fontSize: 13, outline: "none", color: "#0f172a" }} />
                      </div>
                    ))}

                    <div style={{ marginBottom: 12 }}>
                      <label style={{ fontSize: 11, fontWeight: 600, color: "#475569", display: "block", marginBottom: 3 }}>Prioridade</label>
                      <select value={editForm.prioridade} onChange={(e) => setEditForm(ef => ({ ...ef, prioridade: e.target.value }))}
                        style={{ border: "1px solid #cbd5e1", borderRadius: 7, padding: "8px 11px", fontSize: 13, color: "#0f172a", background: "#fff" }}>
                        {[["must","Must"],["should","Should"],["could","Could"],["wont","Won't"]].map(([v,l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </div>

                    <div style={{ marginBottom: 14 }}>
                      <label style={{ fontSize: 11, fontWeight: 600, color: "#475569", display: "block", marginBottom: 3 }}>Critérios de aceite *</label>
                      {editForm.criterios_aceite.map((c, i) => (
                        <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                          <input value={c} onChange={(e) => { const n = [...editForm.criterios_aceite]; n[i] = e.target.value; setEditForm(ef => ({ ...ef, criterios_aceite: n })); }}
                            placeholder={`Critério ${i + 1}`} style={{ flex: 1, border: "1px solid #cbd5e1", borderRadius: 7, padding: "8px 11px", fontSize: 13, outline: "none", color: "#0f172a" }} />
                          {editForm.criterios_aceite.length > 1 && (
                            <button onClick={() => setEditForm(ef => ({ ...ef, criterios_aceite: ef.criterios_aceite.filter((_, j) => j !== i) }))}
                              style={{ background: "none", border: "none", color: "#dc2626", fontSize: 18, cursor: "pointer", padding: "0 4px" }}>×</button>
                          )}
                        </div>
                      ))}
                      <button onClick={() => setEditForm(ef => ({ ...ef, criterios_aceite: [...ef.criterios_aceite, ""] }))}
                        style={{ fontSize: 12, color: "#2563eb", background: "none", border: "none", cursor: "pointer", padding: 0 }}>+ Adicionar critério</button>
                    </div>

                    {erroEdit && <p style={{ color: "#dc2626", fontSize: 12, marginBottom: 10 }}>{erroEdit}</p>}
                    <div style={{ display: "flex", gap: 8 }}>
                      <button onClick={handleSalvarEdit} disabled={savingEdit}
                        style={{ background: savingEdit ? "#e2e8f0" : "#0f172a", color: savingEdit ? "#94a3b8" : "#fff", border: "none", borderRadius: 7, padding: "8px 18px", fontSize: 13, fontWeight: 600, cursor: savingEdit ? "not-allowed" : "pointer" }}>
                        {savingEdit ? "Salvando..." : "Salvar"}
                      </button>
                      <button onClick={() => { setEditingId(null); setErroEdit(""); }}
                        style={{ background: "transparent", color: "#64748b", border: "1px solid #cbd5e1", borderRadius: 7, padding: "8px 16px", fontSize: 13, cursor: "pointer" }}>
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}

                {/* Detalhes expandidos (só quando não está editando) */}
                {expanded === f.id && editingId !== f.id && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #f1f5f9" }}>
                    {f.descricao && <p style={{ fontSize: 13, color: "#475569", margin: "0 0 10px", lineHeight: 1.5 }}>{f.descricao}</p>}
                    {f.criterios_aceite.length > 0 && (
                      <div>
                        <p style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", margin: "0 0 6px" }}>Critérios de aceite</p>
                        <ul style={{ margin: 0, paddingLeft: 16 }}>
                          {f.criterios_aceite.map((c, i) => <li key={i} style={{ fontSize: 13, color: "#475569", marginBottom: 4 }}>{c}</li>)}
                        </ul>
                      </div>
                    )}
                    {f.responsavel && <p style={{ fontSize: 12, color: "#64748b", margin: "10px 0 0" }}>Responsável: <strong>{f.responsavel}</strong></p>}
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
