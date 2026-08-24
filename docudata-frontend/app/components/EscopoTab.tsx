"use client";

import { useState } from "react";
import {
  FuncionalidadeResponse,
  FuncionalidadeProposta,
  importarFuncionalidades,
  confirmarImportacao,
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

type Step = "idle" | "input" | "loading" | "review" | "saving";

interface Props {
  projectId: string;
  funcionalidades: FuncionalidadeResponse[];
  onImported: (novas: FuncionalidadeResponse[]) => void;
}

export default function EscopoTab({ projectId, funcionalidades, onImported }: Props) {
  const [step, setStep] = useState<Step>("idle");
  const [texto, setTexto] = useState("");
  const [propostas, setPropostas] = useState<FuncionalidadeProposta[]>([]);
  const [selecionadas, setSelecionadas] = useState<Set<number>>(new Set());
  const [erro, setErro] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  async function handleAnalisar() {
    if (texto.trim().length < 20) {
      setErro("Cole o texto do contrato antes de continuar.");
      return;
    }
    setErro("");
    setStep("loading");
    try {
      const resultado = await importarFuncionalidades(projectId, texto);
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
          <button
            onClick={() => setStep("input")}
            style={{
              background: "#0f172a", color: "#fff", border: "none", borderRadius: 8,
              padding: "10px 18px", fontSize: 14, fontWeight: 600, cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            + Importar do contrato
          </button>
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
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", margin: "0 0 8px" }}>
            Colar texto do contrato
          </h3>
          <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 16px", lineHeight: 1.5 }}>
            Cole o texto completo do contrato ou proposta comercial. A IA vai extrair cada funcionalidade com título, descrição e critérios de aceite.
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
          {erro && <p style={{ color: "#dc2626", fontSize: 13, marginTop: 8 }}>{erro}</p>}
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

      {/* Lista existente */}
      {funcionalidades.length === 0 && step === "idle" ? (
        <div style={{
          background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: 12,
          padding: 48, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 15, margin: "0 0 8px", fontWeight: 500 }}>
            Nenhuma funcionalidade cadastrada
          </p>
          <p style={{ color: "#94a3b8", fontSize: 13, margin: 0 }}>
            Clique em <strong>+ Importar do contrato</strong> para extrair as funcionalidades automaticamente.
          </p>
        </div>
      ) : (
        step !== "review" && step !== "loading" && step !== "saving" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {funcionalidades.map((f) => (
              <div
                key={f.id}
                style={{
                  background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10,
                  padding: "14px 16px", cursor: "pointer",
                }}
                onClick={() => setExpanded(expanded === f.id ? null : f.id)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 11, color: "#94a3b8", fontFamily: "monospace" }}>{f.id_funcional}</span>
                  <span style={{
                    fontSize: 11, fontWeight: 700,
                    color: PRIORIDADE_COLOR[f.prioridade] ?? "#64748b",
                    background: `${PRIORIDADE_COLOR[f.prioridade] ?? "#64748b"}18`,
                    padding: "1px 7px", borderRadius: 4, textTransform: "uppercase",
                  }}>
                    {PRIORIDADE_LABEL[f.prioridade] ?? f.prioridade}
                  </span>
                  <span style={{
                    fontSize: 11, fontWeight: 600,
                    color: STATUS_COLOR[f.status] ?? "#94a3b8",
                    background: `${STATUS_COLOR[f.status] ?? "#94a3b8"}15`,
                    padding: "1px 7px", borderRadius: 4,
                  }}>
                    {STATUS_LABEL[f.status] ?? f.status}
                  </span>
                  <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: "#0f172a" }}>
                    {f.titulo}
                  </span>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{expanded === f.id ? "▲" : "▼"}</span>
                </div>

                {expanded === f.id && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #f1f5f9" }}>
                    {f.descricao && (
                      <p style={{ fontSize: 13, color: "#475569", margin: "0 0 10px", lineHeight: 1.5 }}>
                        {f.descricao}
                      </p>
                    )}
                    {f.criterios_aceite.length > 0 && (
                      <div>
                        <p style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", margin: "0 0 6px" }}>
                          Critérios de aceite
                        </p>
                        <ul style={{ margin: 0, paddingLeft: 16 }}>
                          {f.criterios_aceite.map((c, i) => (
                            <li key={i} style={{ fontSize: 13, color: "#475569", marginBottom: 4 }}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {f.responsavel && (
                      <p style={{ fontSize: 12, color: "#64748b", margin: "10px 0 0" }}>
                        Responsável: <strong>{f.responsavel}</strong>
                      </p>
                    )}
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
