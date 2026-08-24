"use client";

import { useEffect, useState } from "react";
import {
  getRascunho,
  patchRascunho,
  gerarPlanning,
  confirmarPlanning,
  listFuncionalidades,
  updateFuncionalidade,
  type DadosJson,
  type FuncionalidadeResponse,
  type GetRascunhoResponse,
  type SprintWithStatus,
} from "../lib/api";

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
  onGoToSprintDoc?: (payload: {
    sprintNumero: number;
    descricao: string;
    itens: { item: string; responsavel: string; prazo: string; criterio: string }[];
  }) => void;
}

// ---------------------------------------------------------------------------
// Constantes de estilo (zero className — todos os estilos como React.CSSProperties)
// ---------------------------------------------------------------------------

const pageWrapStyle: React.CSSProperties = {
  background: "#f7f7fa",
  minHeight: 400,
};

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "20px 22px",
  marginBottom: 16,
};

const headingStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: "#111116",
  marginBottom: 8,
  marginTop: 0,
};

const subHeadingStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: "#374151",
  marginBottom: 6,
  marginTop: 12,
};

const textSecondaryStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#9696a0",
  margin: 0,
};

const labelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#6a6a7a",
  marginBottom: 4,
};

const badgeTransbordadoStyle: React.CSSProperties = {
  background: "#ffedd5",
  color: "#c2410c",
  borderRadius: 6,
  padding: "2px 8px",
  fontSize: 12,
  fontWeight: 700,
  display: "inline-block",
  marginLeft: 8,
};

const stepBarContainerStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
  marginBottom: 24,
  alignItems: "center",
};

const stepLabelStyle = (active: boolean, done: boolean): React.CSSProperties => ({
  fontSize: 13,
  fontWeight: active ? 700 : 500,
  color: active ? "#16a34a" : done ? "#9696a0" : "#c8c8d0",
  padding: "6px 14px",
  borderRadius: 20,
  background: active ? "#dcfce7" : done ? "#f1f5f9" : "#e8e8ed",
  border: active ? "1px solid #4ade80" : "1px solid transparent",
  cursor: "default",
});

const btnPrimaryStyle: React.CSSProperties = {
  background: "#16a34a",
  color: "#ffffff",
  border: "none",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const btnSecondaryStyle: React.CSSProperties = {
  background: "#f1f5f9",
  color: "#374151",
  border: "1px solid #e8e8ed",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const btnConfirmStyle: React.CSSProperties = {
  background: "#dcfce7",
  color: "#16a34a",
  border: "1px solid #4ade80",
  borderRadius: 8,
  padding: "10px 22px",
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
};

const btnDisabledStyle: React.CSSProperties = {
  background: "#e8e8ed",
  color: "#b8b8c0",
  border: "none",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "not-allowed",
};

const errorTextStyle: React.CSSProperties = {
  color: "#dc2626",
  fontSize: 12,
  margin: "4px 0 0",
};

const checkboxRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  gap: 8,
  marginBottom: 6,
};

const funcCardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 10,
  padding: "12px 14px",
  marginBottom: 10,
};

const funcCardTransbordadoStyle: React.CSSProperties = {
  ...funcCardStyle,
  borderLeft: "3px solid #c2410c",
};

const throughputInfoStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#374151",
  background: "#f7f7fa",
  borderRadius: 8,
  padding: "8px 12px",
  marginBottom: 16,
};

const inputStyle: React.CSSProperties = {
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  padding: "7px 10px",
  fontSize: 13,
  color: "#111116",
  width: "100%",
  boxSizing: "border-box",
};

const markdownWrapStyle: React.CSSProperties = {
  background: "#f7f7fa",
  borderRadius: 10,
  padding: "16px 18px",
  fontSize: 14,
  color: "#111116",
  lineHeight: 1.6,
  marginBottom: 16,
  border: "1px solid #e8e8ed",
};

const successBoxStyle: React.CSSProperties = {
  background: "#dcfce7",
  border: "1px solid #4ade80",
  borderRadius: 12,
  padding: "24px",
  textAlign: "center",
};

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export default function PlanningTab({ projectId, sprints, onGoToSprintDoc }: Props) {
  const sprintAlvo =
    sprints.length > 0 ? Math.max(...sprints.map((s) => s.numero)) + 1 : 1;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [funcionalidades, setFuncionalidades] = useState<FuncionalidadeResponse[]>([]);
  const [rascunhoData, setRascunhoData] = useState<GetRascunhoResponse | null>(null);

  // Wizard state
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3 | 4>(1);
  const [selecionadas, setSelecionadas] = useState<string[]>([]);
  const [recortes, setRecortes] = useState<Record<string, number[]>>({});
  const [alocacoes, setAlocacoes] = useState<Record<string, string>>({});
  const [transbordos, setTransbordos] = useState<string[]>([]);

  // Step 4 state
  const [markdownGerado, setMarkdownGerado] = useState<string>("");
  const [gerandoMarkdown, setGerandoMarkdown] = useState(false);
  const [gerarErro, setGerarErro] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [confirmado, setConfirmado] = useState(false);
  const [novoCriterio, setNovoCriterio] = useState<Record<string, string>>({});
  const [salvandoCriterio, setSalvandoCriterio] = useState<string | null>(null);
  const [detalhes, setDetalhes] = useState<Record<string, string>>({});
  const [objetivoSprint, setObjetivoSprint] = useState<string>("");

  async function adicionarCriterio(funcId: string) {
    const texto = (novoCriterio[funcId] ?? "").trim();
    if (!texto) return;
    const func = funcionalidades.find((f) => f.id === funcId);
    if (!func) return;
    setSalvandoCriterio(funcId);
    try {
      const novosCriterios = [...(func.criterios_aceite ?? []), texto];
      const atualizada = await updateFuncionalidade(funcId, {
        criterios_aceite: novosCriterios,
      });
      setFuncionalidades((prev) =>
        prev.map((f) => (f.id === funcId ? atualizada : f))
      );
      const newIdx = novosCriterios.length - 1;
      setRecortes((prev) => ({
        ...prev,
        [funcId]: [...(prev[funcId] ?? []), newIdx],
      }));
      setNovoCriterio((prev) => ({ ...prev, [funcId]: "" }));
    } catch {
      // silent — usuário tenta de novo
    } finally {
      setSalvandoCriterio(null);
    }
  }

  // Load funcionalidades on mount
  useEffect(() => {
    listFuncionalidades(projectId).then(setFuncionalidades).catch(() => {});
  }, [projectId]);

  // Step 4 agora é composição por cards — sem auto-geração de markdown.

  async function handleIniciar() {
    setLoading(true);
    setError(null);
    try {
      const data = await getRascunho(projectId, sprintAlvo);
      setRascunhoData(data);
      const dj = data.rascunho.dados_json;
      setSelecionadas(dj.funcionalidades_selecionadas ?? []);
      setRecortes(dj.recortes ?? {});
      setAlocacoes(dj.alocacoes ?? {});
      setTransbordos(dj.transbordos ?? []);
      setDetalhes(dj.detalhes ?? {});
      setObjetivoSprint(dj.objetivo_sprint ?? "");
      const savedStep = data.rascunho.step_atual;
      setWizardStep(savedStep >= 1 && savedStep <= 4 ? (savedStep as 1 | 2 | 3 | 4) : 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao iniciar planning");
    } finally {
      setLoading(false);
    }
  }

  async function patchAndAdvance(nextStep: 1 | 2 | 3 | 4) {
    const dadosJson: DadosJson = {
      funcionalidades_selecionadas: selecionadas,
      recortes,
      alocacoes,
      transbordos,
      detalhes,
      objetivo_sprint: objetivoSprint,
    };
    try {
      await patchRascunho(projectId, sprintAlvo, {
        step_atual: nextStep,
        dados_json: dadosJson,
      });
    } catch {
      // non-blocking — continue navigation
    }
    setWizardStep(nextStep);
  }

  async function handleGerar() {
    setGerandoMarkdown(true);
    setGerarErro(null);
    try {
      const resp = await gerarPlanning(projectId, sprintAlvo);
      setMarkdownGerado(resp.markdown);
    } catch (e) {
      setGerarErro(e instanceof Error ? e.message : "Erro ao gerar planning");
    } finally {
      setGerandoMarkdown(false);
    }
  }

  async function handleConfirmar() {
    setConfirmando(true);
    try {
      await confirmarPlanning(projectId, sprintAlvo, markdownGerado);
      setConfirmado(true);
      setRascunhoData(null);
    } catch (e) {
      setGerarErro(e instanceof Error ? e.message : "Erro ao confirmar planning");
    } finally {
      setConfirmando(false);
    }
  }

  // Step 2 validation: every selected func must have at least 1 index
  const passo2Valido = selecionadas.every((id) => (recortes[id] ?? []).length > 0);

  // Map transbordos ids for quick lookup
  const transbordosSet = new Set(
    rascunhoData?.transbordos.map((t) => t.id) ?? []
  );

  // Sort funcs: transbordados first
  const funcsOrdenadas = [...funcionalidades].sort((a, b) => {
    const aT = transbordosSet.has(a.id) ? 0 : 1;
    const bT = transbordosSet.has(b.id) ? 0 : 1;
    return aT - bT;
  });

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------
  if (loading) {
    return (
      <section style={{ ...cardStyle, marginBottom: 14 }}>
        <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>Carregando planning…</p>
      </section>
    );
  }

  // ---------------------------------------------------------------------------
  // Error state
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <section style={{ ...cardStyle, marginBottom: 14 }}>
        <p style={{ color: "#dc2626", fontSize: 14, margin: 0 }}>{error}</p>
      </section>
    );
  }

  // ---------------------------------------------------------------------------
  // Success (confirmado)
  // ---------------------------------------------------------------------------
  if (confirmado) {
    return (
      <div style={pageWrapStyle}>
        <div style={successBoxStyle}>
          <p style={{ fontSize: 18, fontWeight: 700, color: "#16a34a", margin: "0 0 8px" }}>
            Planning da Sprint {sprintAlvo} salvo com sucesso!
          </p>
          <p style={{ fontSize: 13, color: "#374151", margin: "0 0 16px" }}>
            O documento foi registrado e o rascunho foi descartado.
          </p>
          <button
            style={btnPrimaryStyle}
            onClick={() => {
              setConfirmado(false);
              setMarkdownGerado("");
              setWizardStep(1);
              setSelecionadas([]);
              setRecortes({});
              setAlocacoes({});
              setTransbordos([]);
            }}
          >
            Iniciar novo planning
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Tela de boas-vindas (sem rascunho ativo) — D-10
  // ---------------------------------------------------------------------------
  if (!rascunhoData) {
    return (
      <div style={pageWrapStyle}>
        <div style={cardStyle}>
          <h2 style={headingStyle}>Planning da Sprint {sprintAlvo}</h2>
          <p style={textSecondaryStyle}>
            Componha o planning da próxima sprint em 4 passos: seleção de funcionalidades,
            recorte de critérios, alocação de responsáveis e geração do documento via IA.
          </p>

          <div style={{ ...throughputInfoStyle, marginTop: 16 }}>
            {/* Throughput — ainda não temos dados antes de iniciar */}
            <span style={{ fontWeight: 600 }}>Throughput de referência: </span>
            será calculado ao iniciar o planning (últimas 3 sprints)
          </div>

          <button style={btnPrimaryStyle} onClick={handleIniciar}>
            Iniciar Planning da Sprint {sprintAlvo}
          </button>
        </div>
      </div>
    );
  }

  // Throughput info (disponível após iniciar)
  const throughputText =
    rascunhoData.throughput_ref !== null && rascunhoData.throughput_ref !== undefined
      ? `Throughput médio das últimas 3 sprints: ${rascunhoData.throughput_ref} funcionalidades/sprint`
      : "Sem dados de throughput das sprints anteriores";

  // ---------------------------------------------------------------------------
  // Wizard
  // ---------------------------------------------------------------------------
  const STEP_LABELS = ["1. Seleção", "2. Recorte", "3. Alocação", "4. Composição"];

  return (
    <div style={pageWrapStyle}>
      {/* Barra de progresso horizontal — D-09 */}
      <div style={stepBarContainerStyle}>
        {STEP_LABELS.map((label, idx) => {
          const stepNum = idx + 1;
          const active = wizardStep === stepNum;
          const done = wizardStep > stepNum;
          return (
            <span key={label} style={stepLabelStyle(active, done)}>
              {label}
            </span>
          );
        })}
      </div>

      {/* Throughput info */}
      <div style={throughputInfoStyle}>{throughputText}</div>

      {/* ------------------------------------------------------------------ */}
      {/* STEP 1 — Seleção */}
      {/* ------------------------------------------------------------------ */}
      {wizardStep === 1 && (
        <div style={cardStyle}>
          <h3 style={headingStyle}>Selecione as funcionalidades para a Sprint {sprintAlvo}</h3>
          <p style={{ ...textSecondaryStyle, marginBottom: 12 }}>
            Throughput de referência: {rascunhoData.throughput_ref ?? "—"} func/sprint — selecionar
            além desse número pode comprometer a sprint.
          </p>

          {funcionalidades.length === 0 && (
            <p style={textSecondaryStyle}>Nenhuma funcionalidade cadastrada neste projeto.</p>
          )}

          {funcsOrdenadas.map((f) => {
            const isTransbordado = transbordosSet.has(f.id);
            const checked = selecionadas.includes(f.id);
            return (
              <div key={f.id} style={isTransbordado ? funcCardTransbordadoStyle : funcCardStyle}>
                <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelecionadas((prev) => [...prev, f.id]);
                        // auto-include transbordado id
                        if (isTransbordado && !transbordos.includes(f.id)) {
                          setTransbordos((prev) => [...prev, f.id]);
                        }
                      } else {
                        setSelecionadas((prev) => prev.filter((id) => id !== f.id));
                        setTransbordos((prev) => prev.filter((id) => id !== f.id));
                      }
                    }}
                    style={{ width: 16, height: 16, cursor: "pointer" }}
                  />
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#111116" }}>
                    {f.titulo}
                    {isTransbordado && (
                      <span style={badgeTransbordadoStyle}>Transbordado</span>
                    )}
                  </span>
                </label>
              </div>
            );
          })}

          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button
              style={selecionadas.length > 0 ? btnPrimaryStyle : btnDisabledStyle}
              disabled={selecionadas.length === 0}
              onClick={() => patchAndAdvance(2)}
            >
              Próximo
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* STEP 2 — Recorte (D-03/D-04) */}
      {/* ------------------------------------------------------------------ */}
      {wizardStep === 2 && (
        <div style={cardStyle}>
          <h3 style={headingStyle}>Recorte de critérios de aceite</h3>
          <p style={{ ...textSecondaryStyle, marginBottom: 16 }}>
            Selecione quais critérios de aceite entram nesta sprint para cada funcionalidade.
          </p>

          {selecionadas.map((funcId) => {
            const func = funcionalidades.find((f) => f.id === funcId);
            if (!func) return null;
            const criterios: string[] = func.criterios_aceite ?? [];
            const selectedIdxs = recortes[funcId] ?? [];
            const hasSelection = selectedIdxs.length > 0;

            return (
              <div key={funcId} style={{ ...funcCardStyle, marginBottom: 12 }}>
                <p style={subHeadingStyle}>{func.titulo}</p>
                {criterios.length === 0 ? (
                  <p style={textSecondaryStyle}>Sem critérios de aceite cadastrados.</p>
                ) : (
                  criterios.map((criterio, idx) => (
                    <div key={idx} style={checkboxRowStyle}>
                      <input
                        type="checkbox"
                        checked={selectedIdxs.includes(idx)}
                        onChange={(e) => {
                          setRecortes((prev) => {
                            const current = prev[funcId] ?? [];
                            if (e.target.checked) {
                              return { ...prev, [funcId]: [...current, idx] };
                            } else {
                              return { ...prev, [funcId]: current.filter((i) => i !== idx) };
                            }
                          });
                        }}
                        style={{ width: 15, height: 15, marginTop: 2, cursor: "pointer" }}
                      />
                      <span style={{ fontSize: 13, color: "#374151", lineHeight: 1.4 }}>
                        {criterio}
                      </span>
                    </div>
                  ))
                )}
                {!hasSelection && criterios.length > 0 && (
                  <p style={errorTextStyle}>Selecione ao menos um critério de aceite</p>
                )}

                <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
                  <input
                    type="text"
                    placeholder="+ Adicionar novo critério (formato EARS: Quando X, o sistema deve Y)"
                    value={novoCriterio[funcId] ?? ""}
                    onChange={(e) =>
                      setNovoCriterio((prev) => ({ ...prev, [funcId]: e.target.value }))
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        adicionarCriterio(funcId);
                      }
                    }}
                    style={{
                      flex: 1,
                      border: "1px solid #d1d5db",
                      borderRadius: 6,
                      padding: "6px 10px",
                      fontSize: 12,
                      color: "#111827",
                      outline: "none",
                    }}
                  />
                  <button
                    onClick={() => adicionarCriterio(funcId)}
                    disabled={salvandoCriterio === funcId || !(novoCriterio[funcId] ?? "").trim()}
                    style={{
                      background: (novoCriterio[funcId] ?? "").trim() ? "#0f172a" : "#e5e7eb",
                      color: (novoCriterio[funcId] ?? "").trim() ? "#fff" : "#9ca3af",
                      border: "none",
                      borderRadius: 6,
                      padding: "6px 12px",
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: (novoCriterio[funcId] ?? "").trim() ? "pointer" : "not-allowed",
                    }}
                  >
                    {salvandoCriterio === funcId ? "…" : "Add"}
                  </button>
                </div>
              </div>
            );
          })}

          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button style={btnSecondaryStyle} onClick={() => patchAndAdvance(1)}>
              Anterior
            </button>
            <button
              style={passo2Valido ? btnPrimaryStyle : btnDisabledStyle}
              disabled={!passo2Valido}
              onClick={() => patchAndAdvance(3)}
            >
              Próximo
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* STEP 3 — Alocação */}
      {/* ------------------------------------------------------------------ */}
      {wizardStep === 3 && (
        <div style={cardStyle}>
          <h3 style={headingStyle}>Alocação de responsáveis</h3>
          <p style={{ ...textSecondaryStyle, marginBottom: 16 }}>
            Defina o responsável por cada funcionalidade (opcional).
          </p>

          {selecionadas.map((funcId) => {
            const func = funcionalidades.find((f) => f.id === funcId);
            if (!func) return null;
            return (
              <div key={funcId} style={{ ...funcCardStyle, marginBottom: 10 }}>
                <p style={{ ...labelStyle, fontWeight: 600, color: "#374151" }}>{func.titulo}</p>
                <input
                  type="text"
                  placeholder="Nome do responsável (opcional)"
                  value={alocacoes[funcId] ?? ""}
                  onChange={(e) =>
                    setAlocacoes((prev) => ({ ...prev, [funcId]: e.target.value }))
                  }
                  style={inputStyle}
                />
              </div>
            );
          })}

          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button style={btnSecondaryStyle} onClick={() => patchAndAdvance(2)}>
              Anterior
            </button>
            <button style={btnPrimaryStyle} onClick={() => patchAndAdvance(4)}>
              Próximo
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* STEP 4 — Composição (cards editáveis) */}
      {/* ------------------------------------------------------------------ */}
      {wizardStep === 4 && (
        <div style={cardStyle}>
          <h3 style={headingStyle}>Composição do Planning</h3>
          <p style={{ ...textSecondaryStyle, marginBottom: 16 }}>
            Revise cada funcionalidade e adicione detalhes. Depois vá pra Documentação da Sprint pra completar e gerar o markdown.
          </p>

          <div style={{ marginBottom: 18 }}>
            <label style={{ ...subHeadingStyle, display: "block", marginBottom: 6 }}>
              Objetivo da sprint
            </label>
            <textarea
              value={objetivoSprint}
              onChange={(e) => setObjetivoSprint(e.target.value)}
              placeholder="Ex: Entregar o pipeline de ingestão inicial validado com o cliente"
              rows={2}
              style={{
                ...inputStyle,
                width: "100%",
                boxSizing: "border-box",
                resize: "vertical",
                fontFamily: "inherit",
                minHeight: 60,
              }}
            />
          </div>

          {selecionadas.length === 0 && (
            <p style={textSecondaryStyle}>Nenhuma funcionalidade selecionada. Volte para a etapa 1.</p>
          )}

          {selecionadas.map((funcId) => {
            const func = funcionalidades.find((f) => f.id === funcId);
            if (!func) return null;
            const criteriosSelecionados = (recortes[funcId] ?? [])
              .map((idx) => func.criterios_aceite[idx])
              .filter(Boolean);
            const responsavel = alocacoes[funcId] ?? "";
            const detalheAtual = detalhes[funcId] ?? "";

            return (
              <div key={funcId} style={{ ...funcCardStyle, marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div>
                    <p style={{ ...subHeadingStyle, marginBottom: 2 }}>{func.titulo}</p>
                    <p style={{ fontSize: 11, color: "#9696a0", margin: 0 }}>
                      {func.id_funcional} · Prioridade: {func.prioridade}
                    </p>
                  </div>
                  {responsavel && (
                    <span style={{
                      fontSize: 11,
                      background: "#eff6ff",
                      color: "#2563eb",
                      border: "1px solid #bfdbfe",
                      borderRadius: 4,
                      padding: "2px 8px",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                    }}>
                      {responsavel}
                    </span>
                  )}
                </div>

                {criteriosSelecionados.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    <p style={{ fontSize: 11, color: "#6b7280", fontWeight: 600, textTransform: "uppercase", margin: "0 0 4px", letterSpacing: 0.4 }}>
                      Critérios de aceite desta sprint
                    </p>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#374151", lineHeight: 1.5 }}>
                      {criteriosSelecionados.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <label style={{ fontSize: 11, color: "#6b7280", fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.4, display: "block", marginBottom: 4 }}>
                  Detalhes adicionais
                </label>
                <textarea
                  value={detalheAtual}
                  onChange={(e) =>
                    setDetalhes((prev) => ({ ...prev, [funcId]: e.target.value }))
                  }
                  placeholder="Ex: dependência de acesso ao S3, entregar em duas etapas, alinhar com o cliente antes do dev..."
                  rows={2}
                  style={{
                    ...inputStyle,
                    width: "100%",
                    boxSizing: "border-box",
                    resize: "vertical",
                    fontFamily: "inherit",
                    minHeight: 52,
                  }}
                />
              </div>
            );
          })}

          <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
            <button style={btnSecondaryStyle} onClick={() => patchAndAdvance(3)}>
              Anterior
            </button>
            <button
              style={btnPrimaryStyle}
              onClick={async () => {
                await patchAndAdvance(4);
                if (onGoToSprintDoc) {
                  const itens = selecionadas.map((funcId) => {
                    const func = funcionalidades.find((f) => f.id === funcId);
                    const criterios = (recortes[funcId] ?? [])
                      .map((idx) => func?.criterios_aceite[idx])
                      .filter(Boolean) as string[];
                    const detalhe = (detalhes[funcId] ?? "").trim();
                    return {
                      item: detalhe
                        ? `${func?.titulo ?? ""} — ${detalhe}`
                        : func?.titulo ?? "",
                      responsavel: alocacoes[funcId] ?? "",
                      prazo: "",
                      criterio: criterios.join(" · "),
                    };
                  });
                  onGoToSprintDoc({
                    sprintNumero: sprintAlvo,
                    descricao: objetivoSprint,
                    itens,
                  });
                }
              }}
              disabled={!onGoToSprintDoc || selecionadas.length === 0}
            >
              Ir para Documentação da Sprint →
            </button>
            {markdownGerado && !gerandoMarkdown && (
              <button
                style={confirmando ? btnDisabledStyle : btnConfirmStyle}
                disabled={confirmando}
                onClick={handleConfirmar}
                title="Salvar markdown gerado anteriormente"
              >
                {confirmando ? "Salvando…" : "Confirmar Planning (markdown antigo)"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
