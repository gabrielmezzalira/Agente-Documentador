"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import ReactMarkdown from "react-markdown";
import {
  enrichPlanningComCorrelacoes,
  submitPlanning,
  createSprintFuncionalidades,
  getRascunho,
  confirmarPlanning,
  type FuncionalidadeResponse,
  type TaskCorrelacao,
  type SprintDocResponse,
  type EnrichResult,
} from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  projetoId: string;
  sprintNumero: number;
  sprintId: string;
  funcionalidades: FuncionalidadeResponse[];
  onSubmitted?: (response: SprintDocResponse) => void;
}

type Step = "input" | "correlacoes" | "form" | "gerando" | "manual_text" | "doc";
type InputTab = "texto" | "arquivo";

// ---------- styles ----------

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: 16,
};

const modal: CSSProperties = {
  background: "#fff",
  borderRadius: 16,
  width: "100%",
  maxWidth: 640,
  maxHeight: "92vh",
  overflowY: "auto",
  padding: 28,
  boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)",
};

const heading: CSSProperties = {
  fontSize: 20,
  fontWeight: 800,
  color: "#0f172a",
  margin: "0 0 4px",
  letterSpacing: "-0.02em",
};

const sub: CSSProperties = {
  fontSize: 13,
  color: "#64748b",
  margin: "0 0 20px",
};

const lbl: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  fontSize: 13,
  fontWeight: 600,
  color: "#334155",
  marginBottom: 6,
  marginTop: 14,
};

const aiBadge: CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  background: "#ede9fe",
  color: "#7c3aed",
  borderRadius: 4,
  padding: "1px 5px",
  letterSpacing: "0.04em",
};

const inp: CSSProperties = {
  width: "100%",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: "8px 10px",
  fontSize: 13,
  outline: "none",
  background: "#fff",
  boxSizing: "border-box",
};

const ta: CSSProperties = {
  ...inp,
  resize: "vertical",
  minHeight: 72,
  fontFamily: "inherit",
};

const tabBtnStyle = (active: boolean): CSSProperties => ({
  padding: "8px 16px",
  fontSize: 13,
  fontWeight: 600,
  borderRadius: 8,
  border: "1px solid",
  cursor: "pointer",
  background: active ? "#0f172a" : "#f8fafc",
  color: active ? "#fff" : "#475569",
  borderColor: active ? "#0f172a" : "#e2e8f0",
});

const btnPrimary: CSSProperties = {
  background: "#0f172a",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  padding: "11px 22px",
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
  transition: "opacity 0.1s",
};

const btnSecondary: CSSProperties = {
  background: "#f1f5f9",
  color: "#1e293b",
  border: "1px solid #e2e8f0",
  borderRadius: 10,
  padding: "11px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const banner = (color: "yellow" | "green"): CSSProperties => ({
  background: color === "yellow" ? "#fefce8" : "#f0fdf4",
  border: `1px solid ${color === "yellow" ? "#fde68a" : "#bbf7d0"}`,
  borderRadius: 10,
  padding: "12px 16px",
  marginBottom: 16,
  fontSize: 13,
  color: color === "yellow" ? "#92400e" : "#166534",
});

const tableHeader: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr 36px",
  gap: 8,
  padding: "8px 0",
  borderBottom: "1px solid #e2e8f0",
  fontWeight: 700,
  fontSize: 12,
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const tableRow: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr 36px",
  gap: 8,
  alignItems: "center",
  padding: "8px 0",
  borderBottom: "1px solid #f0f0f6",
};

const cellText: CSSProperties = {
  fontSize: 13,
  color: "#1e293b",
  lineHeight: 1.4,
};

const sel: CSSProperties = {
  width: "100%",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: "7px 10px",
  fontSize: 13,
  background: "#fff",
  outline: "none",
};

const tinyBtn: CSSProperties = {
  background: "transparent",
  border: "none",
  color: "#94a3b8",
  fontSize: 16,
  cursor: "pointer",
  lineHeight: 1,
  padding: 4,
};

const mdContainer: CSSProperties = {
  marginTop: 16,
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
  borderRadius: 10,
  padding: "16px 20px",
  lineHeight: 1.7,
  color: "#374151",
  fontSize: 13,
  maxHeight: 400,
  overflowY: "auto",
};

const dropZone = (dragging: boolean): CSSProperties => ({
  border: `2px dashed ${dragging ? "#4ade80" : "#cbd5e1"}`,
  borderRadius: 10,
  padding: "28px 16px",
  textAlign: "center",
  cursor: "pointer",
  background: dragging ? "#f0fdf4" : "#fafafa",
  transition: "all 0.15s",
  marginTop: 8,
});

const listRow: CSSProperties = {
  display: "flex",
  gap: 8,
  alignItems: "center",
  marginBottom: 6,
};

const addBtn: CSSProperties = {
  background: "transparent",
  border: "1px dashed #cbd5e1",
  borderRadius: 8,
  padding: "6px 12px",
  fontSize: 12,
  color: "#64748b",
  cursor: "pointer",
  marginTop: 6,
};

const sectionDivider: CSSProperties = {
  borderTop: "1px solid #f0f0f6",
  marginTop: 20,
  paddingTop: 4,
};

// ---------- helpers ----------

type DepsItem = { item: string; prazo: string; consequencia: string; confianca: string };
type RiscoItem = { risco: string; consequencia: string };
type CarryItem = { item: string; causa_raiz: string };

function initFromEnrich(e: EnrichResult) {
  return {
    descricao: e.descricao ?? "",
    periodoInicio: e.periodo_inicio ?? "",
    periodoFim: e.periodo_fim ?? "",
    horasDisponiveis: e.horas_disponiveis != null ? String(e.horas_disponiveis) : "",
    horasEstimadas: e.horas_estimadas != null ? String(e.horas_estimadas) : "",
    dependencias: (e.dependencias_items ?? []).map((d) => ({
      item: d.item,
      prazo: d.prazo,
      consequencia: d.consequencia,
      confianca: d.confianca,
    })),
    riscos: (e.riscos_items ?? []).map((r) => ({ risco: r.risco, consequencia: r.consequencia })),
    carryOver: (e.carry_over_items ?? []).map((c) => ({ item: c.item, causa_raiz: c.causa_raiz })),
  };
}

// ---------- component ----------

export default function PlanningModal({
  open,
  onClose,
  projetoId,
  sprintNumero,
  sprintId,
  funcionalidades,
  onSubmitted,
}: Props) {
  const [step, setStep] = useState<Step>("input");
  const [inputTab, setInputTab] = useState<InputTab>("arquivo");
  const [texto, setTexto] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // correlações
  const [correlacoes, setCorrelacoes] = useState<TaskCorrelacao[]>([]);
  const [semFuncionalidades, setSemFuncionalidades] = useState(false);
  const [newTask, setNewTask] = useState("");

  // formulário de planning
  const [descricao, setDescricao] = useState("");
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFim, setPeriodoFim] = useState("");
  const [horasDisponiveis, setHorasDisponiveis] = useState("");
  const [horasEstimadas, setHorasEstimadas] = useState("");
  const [dependencias, setDependencias] = useState<DepsItem[]>([]);
  const [riscos, setRiscos] = useState<RiscoItem[]>([]);
  const [carryOver, setCarryOver] = useState<CarryItem[]>([]);
  const [aiFilledFields, setAiFilledFields] = useState<Set<string>>(new Set());

  // manual path
  const [manualMarkdown, setManualMarkdown] = useState("");
  const [manualSaving, setManualSaving] = useState(false);

  // doc gerado
  const [docContent, setDocContent] = useState("");
  const [copied, setCopied] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const recomendadas = funcionalidades.filter((f) => f.status === "em_andamento");

  useEffect(() => {
    if (!open) {
      setStep("input");
      setTexto("");
      setArquivo(null);
      setError("");
      setCorrelacoes([]);
      setNewTask("");
      setDescricao("");
      setPeriodoInicio("");
      setPeriodoFim("");
      setHorasDisponiveis("");
      setHorasEstimadas("");
      setDependencias([]);
      setRiscos([]);
      setCarryOver([]);
      setAiFilledFields(new Set());
      setManualMarkdown("");
      setManualSaving(false);
      setDocContent("");
      setCopied(false);
    }
  }, [open]);

  if (!open) return null;

  // ── helpers ──────────────────────────────────────────────────────────────

  function handleFile(file: File) {
    setArquivo(file);
    setError("");
  }

  async function handleAnalisar() {
    if (inputTab === "arquivo" && !arquivo) {
      setError("Selecione um arquivo antes de analisar.");
      return;
    }
    if (inputTab === "texto" && !texto.trim()) {
      setError("Cole o texto das tasks antes de analisar.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const result = await enrichPlanningComCorrelacoes(projetoId, {
        texto: inputTab === "texto" ? texto : undefined,
        arquivo: inputTab === "arquivo" ? (arquivo ?? undefined) : undefined,
      });
      setCorrelacoes(result.correlacoes);
      setSemFuncionalidades(result.sem_funcionalidades);

      // Pré-preenche formulário com o que a IA extraiu
      const f = initFromEnrich(result.enriquecimento);
      setDescricao(f.descricao);
      setPeriodoInicio(f.periodoInicio);
      setPeriodoFim(f.periodoFim);
      setHorasDisponiveis(f.horasDisponiveis);
      setHorasEstimadas(f.horasEstimadas);
      setDependencias(f.dependencias);
      setRiscos(f.riscos);
      setCarryOver(f.carryOver);

      // Marca quais campos a IA realmente preencheu
      const filled = new Set<string>();
      if (f.descricao) filled.add("descricao");
      if (f.periodoInicio || f.periodoFim) filled.add("periodo");
      if (f.horasDisponiveis || f.horasEstimadas) filled.add("horas");
      if (f.dependencias.length > 0) filled.add("dependencias");
      if (f.riscos.length > 0) filled.add("riscos");
      if (f.carryOver.length > 0) filled.add("carryOver");
      setAiFilledFields(filled);

      setStep("correlacoes");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao analisar conteúdo.");
    } finally {
      setLoading(false);
    }
  }

  function updateCorrelacaoFunc(idx: number, funcId: string | null) {
    const func = funcionalidades.find((f) => f.id === funcId);
    setCorrelacoes((prev) =>
      prev.map((c, i) =>
        i === idx
          ? { ...c, funcionalidade_id: funcId, funcionalidade_titulo: func?.titulo ?? null }
          : c
      )
    );
  }

  function removeCorrelacao(idx: number) {
    setCorrelacoes((prev) => prev.filter((_, i) => i !== idx));
  }

  function addManualTask() {
    if (!newTask.trim()) return;
    setCorrelacoes((prev) => [
      ...prev,
      { task: newTask.trim(), funcionalidade_id: null, funcionalidade_titulo: null },
    ]);
    setNewTask("");
  }

  async function handleGerar() {
    if (correlacoes.length === 0 && !descricao.trim()) {
      setError("Preencha ao menos o objetivo da sprint.");
      return;
    }
    setError("");
    setStep("gerando");

    try {
      const itensBacklog = correlacoes.map((c) => ({
        item: c.task,
        responsavel: "",
        prazo: "",
        criterio: "",
      }));

      const [docResponse] = await Promise.all([
        submitPlanning({
          projetoId,
          sprintNumero,
          descricao: descricao || `Planning da Sprint ${sprintNumero}`,
          itensBacklog,
          periodoInicio: periodoInicio || undefined,
          periodoFim: periodoFim || undefined,
          horasDisponiveis: horasDisponiveis ? Number(horasDisponiveis) : undefined,
          horasEstimadas: horasEstimadas ? Number(horasEstimadas) : undefined,
          dependenciasItems: dependencias.filter((d) => d.item.trim()).map((d) => ({
            item: d.item, prazo: d.prazo, consequencia: d.consequencia, confianca: d.confianca,
          })),
          riscosItems: riscos.filter((r) => r.risco.trim()).map((r) => ({
            risco: r.risco, consequencia: r.consequencia,
          })),
          carryOverItems: carryOver.filter((c) => c.item.trim()).map((c) => ({
            item: c.item, causa_raiz: c.causa_raiz,
          })),
        }),
        (() => {
          const byFunc = new Map<string | null, string[]>();
          correlacoes.forEach((c) => {
            const key = c.funcionalidade_id ?? null;
            if (!byFunc.has(key)) byFunc.set(key, []);
            byFunc.get(key)!.push(c.task);
          });
          const payload = Array.from(byFunc.entries())
            .filter(([funcId]) => funcId !== null)
            .map(([funcId, tasks]) => ({
              funcionalidade_id: funcId,
              tasks: tasks.map((t) => ({ texto: t })),
            }));
          if (payload.length === 0) return Promise.resolve(null);
          return createSprintFuncionalidades(sprintId, payload);
        })(),
      ]);

      setDocContent(docResponse.content);
      setStep("doc");
      onSubmitted?.(docResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao gerar planning.");
      setStep("form");
    }
  }

  async function handleEnterManual() {
    setError("");
    setLoading(true);
    try {
      await getRascunho(projetoId, sprintNumero);
      setStep("manual_text");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao inicializar planning.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveManual() {
    if (!manualMarkdown.trim()) {
      setError("Digite o conteúdo do planning antes de salvar.");
      return;
    }
    setError("");
    setManualSaving(true);
    try {
      await confirmarPlanning(projetoId, sprintNumero, manualMarkdown);
      setDocContent(manualMarkdown);
      setStep("doc");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar planning.");
    } finally {
      setManualSaving(false);
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(docContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // ── step indicator helpers ─────────────────────────────────────────────────

  const STEPS: Step[] = ["input", "correlacoes", "form", "doc"];
  const stepIndex =
    step === "gerando" ? 3
    : step === "manual_text" ? 1
    : STEPS.indexOf(step);

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div style={overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={modal}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
          <div>
            <h2 style={heading}>Planning — Sprint {sprintNumero}</h2>
            <p style={sub}>
              {step === "input" && "Suba o kanban ou cole as tasks da sprint para a IA extrair e correlacionar."}
              {step === "correlacoes" && "Revise a correlação de cada task com a funcionalidade — corrija onde a IA errou."}
              {step === "form" && "Revise e complemente os campos da planning antes de gerar."}
              {step === "gerando" && "Gerando documentação da sprint…"}
              {step === "manual_text" && "Escreva o planning manualmente em markdown."}
              {step === "doc" && "Planning gerado com sucesso."}
            </p>
          </div>
          <button onClick={onClose} style={{ ...tinyBtn, fontSize: 20, color: "#94a3b8" }}>×</button>
        </div>

        {/* Step indicator */}
        <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{
              height: 4,
              flex: 1,
              borderRadius: 4,
              background: i <= stepIndex ? "#0f172a" : "#e2e8f0",
              transition: "background 0.2s",
            }} />
          ))}
        </div>

        {/* ── STEP: INPUT ── */}
        {step === "input" && (
          <>
            {recomendadas.length > 0 && (
              <div style={banner("yellow")}>
                <strong>
                  {recomendadas.length}{" "}
                  {recomendadas.length === 1 ? "funcionalidade em andamento" : "funcionalidades em andamento"} da sprint anterior:
                </strong>
                <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
                  {recomendadas.map((f) => (
                    <li key={f.id} style={{ lineHeight: 1.5 }}>{f.id_funcional} — {f.titulo}</li>
                  ))}
                </ul>
              </div>
            )}

            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
              <button style={tabBtnStyle(inputTab === "arquivo")} onClick={() => setInputTab("arquivo")}>
                Arquivo / Kanban
              </button>
              <button style={tabBtnStyle(inputTab === "texto")} onClick={() => setInputTab("texto")}>
                Texto
              </button>
            </div>

            {inputTab === "arquivo" && (
              <>
                <div
                  style={dropZone(dragging)}
                  onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragging(false);
                    const f = e.dataTransfer.files[0];
                    if (f) handleFile(f);
                  }}
                  onClick={() => fileRef.current?.click()}
                >
                  {arquivo ? (
                    <p style={{ margin: 0, fontSize: 13, color: "#16a34a", fontWeight: 600 }}>
                      ✓ {arquivo.name}
                    </p>
                  ) : (
                    <>
                      <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>
                        Arraste o print do kanban aqui, ou clique para selecionar
                      </p>
                      <p style={{ margin: "4px 0 0", fontSize: 11, color: "#94a3b8" }}>
                        PNG, JPG, PDF, DOCX, TXT
                      </p>
                    </>
                  )}
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.pdf,.docx,.txt"
                  style={{ display: "none" }}
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                />
              </>
            )}

            {inputTab === "texto" && (
              <>
                <span style={lbl}>Cole aqui as tasks da sprint</span>
                <textarea
                  style={ta}
                  rows={6}
                  placeholder={"Ex:\n- Criar modelo de ML para previsão de churn — Responsável: Ana\n- Dashboard de métricas semanais — Responsável: Bruno"}
                  value={texto}
                  onChange={(e) => setTexto(e.target.value)}
                />
              </>
            )}

            {error && <p style={{ color: "#dc2626", fontSize: 13, marginTop: 10 }}>{error}</p>}

            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginTop: 20 }}>
              <button
                style={{ ...btnSecondary, fontSize: 12, color: "#64748b" }}
                onClick={handleEnterManual}
                disabled={loading}
              >
                Escrever sem IA
              </button>
              <div style={{ display: "flex", gap: 10 }}>
                <button style={btnSecondary} onClick={onClose}>Cancelar</button>
                <button
                  style={{ ...btnPrimary, opacity: loading ? 0.7 : 1 }}
                  onClick={handleAnalisar}
                  disabled={loading}
                >
                  {loading ? "Analisando…" : "Analisar com IA →"}
                </button>
              </div>
            </div>
          </>
        )}

        {/* ── STEP: CORRELAÇÕES ── */}
        {step === "correlacoes" && (
          <>
            {semFuncionalidades && (
              <div style={{ ...banner("yellow"), marginBottom: 16 }}>
                <strong>Projeto sem funcionalidades cadastradas.</strong> Vá à aba <strong>Escopo</strong> para
                importar do contrato ou adicionar manualmente.
                As tasks ficarão sem funcionalidade associada.
              </div>
            )}

            <div style={tableHeader}>
              <span>Task</span>
              <span>Funcionalidade</span>
              <span />
            </div>

            {correlacoes.map((c, idx) => (
              <div key={idx} style={tableRow}>
                <span style={cellText}>{c.task}</span>
                <select
                  style={sel}
                  value={c.funcionalidade_id ?? ""}
                  onChange={(e) => updateCorrelacaoFunc(idx, e.target.value || null)}
                >
                  <option value="">Sem funcionalidade</option>
                  {funcionalidades.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.id_funcional} — {f.titulo}
                    </option>
                  ))}
                </select>
                <button style={tinyBtn} onClick={() => removeCorrelacao(idx)} title="Remover task">✕</button>
              </div>
            ))}

            {correlacoes.length === 0 && (
              <p style={{ fontSize: 13, color: "#94a3b8", padding: "12px 0", textAlign: "center" }}>
                Nenhuma task extraída. Adicione manualmente abaixo.
              </p>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 14, alignItems: "center" }}>
              <input
                style={{ ...sel, flex: 1 }}
                placeholder="Adicionar task manualmente…"
                value={newTask}
                onChange={(e) => setNewTask(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addManualTask()}
              />
              <button style={btnSecondary} onClick={addManualTask}>+ Add</button>
            </div>

            {error && <p style={{ color: "#dc2626", fontSize: 13, marginTop: 10 }}>{error}</p>}

            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginTop: 20 }}>
              <button style={btnSecondary} onClick={() => setStep("input")}>← Voltar</button>
              <button style={btnPrimary} onClick={() => setStep("form")}>
                Próximo: preencher campos →
              </button>
            </div>
          </>
        )}

        {/* ── STEP: FORMULÁRIO ── */}
        {step === "form" && (
          <>
            {/* Objetivo */}
            <span style={lbl}>
              Objetivo da sprint {aiFilledFields.has("descricao") && <span style={aiBadge}>IA</span>}
            </span>
            <textarea
              style={ta}
              rows={3}
              placeholder="Descreva o objetivo principal da sprint…"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
            />

            {/* Período */}
            <div style={sectionDivider} />
            <span style={{ ...lbl, marginTop: 16 }}>Período da sprint {aiFilledFields.has("periodo") && <span style={aiBadge}>IA</span>}</span>
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 4 }}>Início</div>
                <input type="date" style={inp} value={periodoInicio} onChange={(e) => setPeriodoInicio(e.target.value)} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 4 }}>Fim</div>
                <input type="date" style={inp} value={periodoFim} onChange={(e) => setPeriodoFim(e.target.value)} />
              </div>
            </div>

            {/* Horas */}
            <div style={sectionDivider} />
            <span style={{ ...lbl, marginTop: 16 }}>Capacidade da sprint {aiFilledFields.has("horas") && <span style={aiBadge}>IA</span>}</span>
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 4 }}>Horas disponíveis</div>
                <input
                  type="number" style={inp} min={0}
                  placeholder="Ex: 80"
                  value={horasDisponiveis}
                  onChange={(e) => setHorasDisponiveis(e.target.value)}
                />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 4 }}>Horas estimadas</div>
                <input
                  type="number" style={inp} min={0}
                  placeholder="Ex: 72"
                  value={horasEstimadas}
                  onChange={(e) => setHorasEstimadas(e.target.value)}
                />
              </div>
            </div>

            {/* Dependências */}
            <div style={sectionDivider} />
            <span style={{ ...lbl, marginTop: 16 }}>Dependências externas {aiFilledFields.has("dependencias") && <span style={aiBadge}>IA</span>}</span>
            {dependencias.map((d, i) => (
              <div key={i} style={listRow}>
                <input
                  style={{ ...inp, flex: 2 }}
                  placeholder="Dependência"
                  value={d.item}
                  onChange={(e) => setDependencias((prev) => prev.map((x, j) => j === i ? { ...x, item: e.target.value } : x))}
                />
                <input
                  style={{ ...inp, flex: 1 }}
                  placeholder="Prazo"
                  value={d.prazo}
                  onChange={(e) => setDependencias((prev) => prev.map((x, j) => j === i ? { ...x, prazo: e.target.value } : x))}
                />
                <button style={tinyBtn} onClick={() => setDependencias((prev) => prev.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}
            <button style={addBtn} onClick={() => setDependencias((prev) => [...prev, { item: "", prazo: "", consequencia: "", confianca: "" }])}>
              + Adicionar dependência
            </button>

            {/* Riscos */}
            <div style={sectionDivider} />
            <span style={{ ...lbl, marginTop: 16 }}>Riscos identificados {aiFilledFields.has("riscos") && <span style={aiBadge}>IA</span>}</span>
            {riscos.map((r, i) => (
              <div key={i} style={listRow}>
                <input
                  style={{ ...inp, flex: 2 }}
                  placeholder="Risco"
                  value={r.risco}
                  onChange={(e) => setRiscos((prev) => prev.map((x, j) => j === i ? { ...x, risco: e.target.value } : x))}
                />
                <input
                  style={{ ...inp, flex: 1 }}
                  placeholder="Consequência"
                  value={r.consequencia}
                  onChange={(e) => setRiscos((prev) => prev.map((x, j) => j === i ? { ...x, consequencia: e.target.value } : x))}
                />
                <button style={tinyBtn} onClick={() => setRiscos((prev) => prev.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}
            <button style={addBtn} onClick={() => setRiscos((prev) => [...prev, { risco: "", consequencia: "" }])}>
              + Adicionar risco
            </button>

            {/* Carry-over */}
            <div style={sectionDivider} />
            <span style={{ ...lbl, marginTop: 16 }}>Itens carry-over (sprint anterior) {aiFilledFields.has("carryOver") && <span style={aiBadge}>IA</span>}</span>
            {carryOver.map((c, i) => (
              <div key={i} style={listRow}>
                <input
                  style={{ ...inp, flex: 2 }}
                  placeholder="Item não entregue"
                  value={c.item}
                  onChange={(e) => setCarryOver((prev) => prev.map((x, j) => j === i ? { ...x, item: e.target.value } : x))}
                />
                <input
                  style={{ ...inp, flex: 1 }}
                  placeholder="Causa raiz"
                  value={c.causa_raiz}
                  onChange={(e) => setCarryOver((prev) => prev.map((x, j) => j === i ? { ...x, causa_raiz: e.target.value } : x))}
                />
                <button style={tinyBtn} onClick={() => setCarryOver((prev) => prev.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}
            <button style={addBtn} onClick={() => setCarryOver((prev) => [...prev, { item: "", causa_raiz: "" }])}>
              + Adicionar carry-over
            </button>

            {error && <p style={{ color: "#dc2626", fontSize: 13, marginTop: 12 }}>{error}</p>}

            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginTop: 24 }}>
              <button style={btnSecondary} onClick={() => setStep("correlacoes")}>← Voltar</button>
              <button style={btnPrimary} onClick={handleGerar}>
                Gerar planning →
              </button>
            </div>
          </>
        )}

        {/* ── STEP: GERANDO ── */}
        {step === "gerando" && (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <p style={{ color: "#64748b", fontSize: 14 }}>Gerando documentação da sprint…</p>
          </div>
        )}

        {/* ── STEP: MANUAL TEXT ── */}
        {step === "manual_text" && (
          <>
            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: "10px 14px", marginBottom: 16, fontSize: 12, color: "#64748b" }}>
              Escreva o planning em markdown. Use <code style={{ background: "#e2e8f0", padding: "1px 4px", borderRadius: 3 }}># Título</code>, <code style={{ background: "#e2e8f0", padding: "1px 4px", borderRadius: 3 }}>## Seção</code> e <code style={{ background: "#e2e8f0", padding: "1px 4px", borderRadius: 3 }}>- item</code> para estruturar o documento.
            </div>
            <textarea
              style={{ ...ta, minHeight: 320, fontFamily: "monospace", fontSize: 12 }}
              placeholder={`# Planning — Sprint ${sprintNumero}\n**Projeto:** ...\n**Data:** ...\n\n## Objetivo da sprint\n\n...\n\n## Backlog da sprint\n\n- Item 1\n- Item 2`}
              value={manualMarkdown}
              onChange={(e) => setManualMarkdown(e.target.value)}
            />
            {error && <p style={{ color: "#dc2626", fontSize: 13, marginTop: 8 }}>{error}</p>}
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginTop: 20 }}>
              <button style={btnSecondary} onClick={() => setStep("input")}>← Voltar</button>
              <button
                style={{ ...btnPrimary, opacity: manualSaving ? 0.7 : 1 }}
                onClick={handleSaveManual}
                disabled={manualSaving}
              >
                {manualSaving ? "Salvando…" : "Salvar planning →"}
              </button>
            </div>
          </>
        )}

        {/* ── STEP: DOC ── */}
        {step === "doc" && (
          <>
            <div style={{ ...banner("green"), display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>✓ Planning gerado e salvo com sucesso.</span>
              <button
                style={{ ...btnSecondary, fontSize: 12, padding: "6px 12px" }}
                onClick={handleCopy}
              >
                {copied ? "Copiado!" : "Copiar markdown"}
              </button>
            </div>
            <div style={mdContainer}>
              <ReactMarkdown>{docContent}</ReactMarkdown>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
              <button style={btnPrimary} onClick={onClose}>Fechar</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
