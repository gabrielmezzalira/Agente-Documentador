"use client";

import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import {
  listBoletins,
  createBoletim,
  patchBoletim,
  gerarResumoSemanal,
  listFuncionalidades,
  type BoletimResponse,
  type FuncionalidadeResponse,
} from "../lib/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AceiteTabProps {
  projectId: string;
  funcionalidades: FuncionalidadeResponse[];
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
  fontSize: 20,
  fontWeight: 700,
  color: "#111116",
  marginBottom: 12,
  marginTop: 0,
};

const subHeadingStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: "#111116",
  marginBottom: 8,
  marginTop: 0,
};

const btnPrimary: React.CSSProperties = {
  background: "#16a34a",
  color: "#ffffff",
  border: "none",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const btnSecondary: React.CSSProperties = {
  background: "#f1f5f9",
  color: "#374151",
  border: "1px solid #e8e8ed",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const btnDanger: React.CSSProperties = {
  background: "#fef2f2",
  color: "#dc2626",
  border: "1px solid #fca5a5",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

const btnDisabled: React.CSSProperties = {
  background: "#e8e8ed",
  color: "#b8b8c0",
  border: "none",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "not-allowed",
};

const badgeSuccess: React.CSSProperties = {
  background: "#dcfce7",
  color: "#16a34a",
  border: "1px solid #4ade80",
  borderRadius: 10,
  padding: "14px 20px",
  fontSize: 15,
  fontWeight: 700,
  marginBottom: 20,
  display: "block",
  textAlign: "center",
};

const badgeRascunho: React.CSSProperties = {
  background: "#f1f5f9",
  color: "#64748b",
  borderRadius: 6,
  padding: "2px 8px",
  fontSize: 12,
  fontWeight: 700,
  display: "inline-block",
};

const badgeEnviado: React.CSSProperties = {
  background: "#dbeafe",
  color: "#1d4ed8",
  borderRadius: 6,
  padding: "2px 8px",
  fontSize: 12,
  fontWeight: 700,
  display: "inline-block",
};

const badgeAprovado: React.CSSProperties = {
  background: "#dcfce7",
  color: "#16a34a",
  borderRadius: 6,
  padding: "2px 8px",
  fontSize: 12,
  fontWeight: 700,
  display: "inline-block",
};

const badgeAjuste: React.CSSProperties = {
  background: "#fef2f2",
  color: "#dc2626",
  borderRadius: 6,
  padding: "2px 8px",
  fontSize: 12,
  fontWeight: 700,
  display: "inline-block",
};

const badgeMudancaEscopo: React.CSSProperties = {
  background: "#fff7ed",
  color: "#c2410c",
  borderRadius: 6,
  padding: "2px 8px",
  fontSize: 12,
  fontWeight: 600,
  display: "inline-block",
  marginLeft: 6,
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

const checkboxRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  gap: 8,
  marginBottom: 6,
};

const errorTextStyle: React.CSSProperties = {
  color: "#dc2626",
  fontSize: 12,
  margin: "4px 0 8px",
};

const selectStyle: React.CSSProperties = {
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  padding: "7px 10px",
  fontSize: 13,
  color: "#111116",
  background: "#ffffff",
  width: "100%",
  marginBottom: 8,
};

const dividerStyle: React.CSSProperties = {
  border: "none",
  borderTop: "1px solid #e8e8ed",
  margin: "24px 0",
};

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export default function AceiteTab({ projectId, funcionalidades }: AceiteTabProps) {
  // Estado de dados
  const [boletins, setBoletins] = useState<BoletimResponse[]>([]);
  const [funcs, setFuncs] = useState<FuncionalidadeResponse[]>(funcionalidades);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Estado do fluxo "Novo Boletim"
  const [novoBoletimAberto, setNovoBoletimAberto] = useState(false);
  const [selectedFuncIds, setSelectedFuncIds] = useState<string[]>([]);
  const [boletimPreview, setBoletimPreview] = useState<BoletimResponse | null>(null);
  const [gerando, setGerando] = useState(false);

  // Estado de retorno do cliente
  const [retornandoBoletimId, setRetornandoBoletimId] = useState<string | null>(null);
  const [retornoTipo, setRetornoTipo] = useState<"bug" | "mudanca_escopo" | "">("");

  // Estado do resumo semanal
  const [resumoSemanal, setResumoSemanal] = useState<string | null>(null);
  const [gerandoResumo, setGerandoResumo] = useState(false);

  // Carregamento inicial
  useEffect(() => {
    setLoading(true);
    Promise.all([
      listBoletins(projectId),
      listFuncionalidades(projectId),
    ])
      .then(([bols, fs]) => {
        setBoletins(bols);
        setFuncs(fs);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [projectId]);

  // Badge de encerramento (D-04, D-13)
  const todasAprovadas =
    funcs.length > 0 && funcs.every((f) => f.status_cliente === "aprovado");

  // Funcionalidades com status "concluida" para seleção de novo boletim
  const funcsConcluidas = funcs.filter((f) => f.status === "concluida");

  // ---------------------------------------------------------------------------
  // Handlers — Boletins
  // ---------------------------------------------------------------------------

  function toggleFuncId(id: string) {
    setSelectedFuncIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function handleGerarBoletim() {
    if (selectedFuncIds.length === 0) return;
    setGerando(true);
    setError(null);
    try {
      const boletim = await createBoletim({
        project_id: projectId,
        funcionalidade_ids: selectedFuncIds,
      });
      setBoletimPreview(boletim);
    } catch (err) {
      setError(String(err));
    } finally {
      setGerando(false);
    }
  }

  async function handleMarcarEnviado(boletimId: string) {
    setError(null);
    try {
      await patchBoletim(boletimId, { status: "enviado" });
      const updated = await listBoletins(projectId);
      setBoletins(updated);
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleMarcarEnviadoPreview() {
    if (!boletimPreview) return;
    setError(null);
    try {
      await patchBoletim(boletimPreview.id, { status: "enviado" });
      const updated = await listBoletins(projectId);
      setBoletins(updated);
      setNovoBoletimAberto(false);
      setBoletimPreview(null);
      setSelectedFuncIds([]);
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleAprovado(boletimId: string) {
    setError(null);
    try {
      await patchBoletim(boletimId, { status: "aprovado" });
      const [bols, fs] = await Promise.all([listBoletins(projectId), listFuncionalidades(projectId)]);
      setBoletins(bols);
      setFuncs(fs);
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleConfirmarAjuste(boletimId: string) {
    if (!retornoTipo) return;
    setError(null);
    try {
      await patchBoletim(boletimId, { status: "ajuste", retorno_tipo: retornoTipo });
      const [bols, fs] = await Promise.all([listBoletins(projectId), listFuncionalidades(projectId)]);
      setBoletins(bols);
      setFuncs(fs);
      setRetornandoBoletimId(null);
      setRetornoTipo("");
    } catch (err) {
      setError(String(err));
    }
  }

  // ---------------------------------------------------------------------------
  // Handlers — Resumo Semanal
  // ---------------------------------------------------------------------------

  async function handleGerarResumo() {
    setGerandoResumo(true);
    setError(null);
    try {
      const result = await gerarResumoSemanal(projectId);
      setResumoSemanal(result.content);
    } catch (err) {
      setError(String(err));
    } finally {
      setGerandoResumo(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Badge de status
  // ---------------------------------------------------------------------------

  function statusBadge(status: BoletimResponse["status"]) {
    switch (status) {
      case "rascunho":
        return <span style={badgeRascunho}>Rascunho</span>;
      case "enviado":
        return <span style={badgeEnviado}>Enviado</span>;
      case "aprovado":
        return <span style={badgeAprovado}>Aprovado</span>;
      case "ajuste":
        return <span style={badgeAjuste}>Ajuste Pedido</span>;
      default:
        return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div style={pageWrapStyle}>
        <p style={{ color: "#6a6a7a", fontSize: 13, padding: 24 }}>Carregando...</p>
      </div>
    );
  }

  return (
    <div style={pageWrapStyle}>
      {/* Badge de encerramento (D-04, D-13) */}
      {todasAprovadas && (
        <div style={badgeSuccess}>
          Projeto encerrado — todas as funcionalidades aprovadas
        </div>
      )}

      {error && <p style={errorTextStyle}>{error}</p>}

      {/* ================================================================
          SEÇÃO 1: BOLETINS
          ================================================================ */}
      <h2 style={headingStyle}>Boletins</h2>

      {/* Lista de boletins existentes */}
      {boletins.length === 0 && !novoBoletimAberto && (
        <p style={{ color: "#6a6a7a", fontSize: 13, marginBottom: 16 }}>
          Nenhum boletim gerado ainda. Clique em &quot;Novo Boletim&quot; para criar o primeiro.
        </p>
      )}

      {boletins.map((bol) => (
        <div key={bol.id} style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 14, color: "#111116" }}>
              Boletim de {bol.criado_em.slice(0, 10)}
            </span>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              {statusBadge(bol.status)}
              {bol.retorno_tipo === "mudanca_escopo" && (
                <span style={badgeMudancaEscopo}>Mudança de Escopo Solicitada</span>
              )}
            </div>
          </div>

          {/* Ações por status */}
          {bol.status === "rascunho" && (
            <button
              style={btnPrimary}
              onClick={() => handleMarcarEnviado(bol.id)}
            >
              Marcar como Enviado
            </button>
          )}

          {bol.status === "enviado" && retornandoBoletimId !== bol.id && (
            <div style={{ display: "flex", gap: 8 }}>
              <button
                style={btnPrimary}
                onClick={() => handleAprovado(bol.id)}
              >
                Aprovado pelo Cliente
              </button>
              <button
                style={btnDanger}
                onClick={() => {
                  setRetornandoBoletimId(bol.id);
                  setRetornoTipo("");
                }}
              >
                Ajuste Pedido
              </button>
            </div>
          )}

          {/* Formulário de retorno: ajuste pedido */}
          {bol.status === "enviado" && retornandoBoletimId === bol.id && (
            <div style={{ marginTop: 8 }}>
              <label style={{ fontSize: 13, color: "#374151", fontWeight: 600, display: "block", marginBottom: 4 }}>
                Tipo de retorno (obrigatório)
              </label>
              <select
                value={retornoTipo}
                onChange={(e) => setRetornoTipo(e.target.value as "bug" | "mudanca_escopo" | "")}
                style={selectStyle}
              >
                <option value="">Selecione o tipo...</option>
                <option value="bug">Bug (dentro do escopo)</option>
                <option value="mudanca_escopo">Mudança de Escopo</option>
              </select>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  style={retornoTipo ? btnDanger : btnDisabled}
                  disabled={!retornoTipo}
                  onClick={() => handleConfirmarAjuste(bol.id)}
                >
                  Confirmar Ajuste
                </button>
                <button
                  style={btnSecondary}
                  onClick={() => {
                    setRetornandoBoletimId(null);
                    setRetornoTipo("");
                  }}
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Botão para abrir fluxo de novo boletim */}
      {!novoBoletimAberto && (
        <button
          style={btnPrimary}
          onClick={() => {
            setNovoBoletimAberto(true);
            setBoletimPreview(null);
            setSelectedFuncIds([]);
          }}
        >
          Novo Boletim
        </button>
      )}

      {/* Fluxo de criação de novo boletim */}
      {novoBoletimAberto && boletimPreview === null && (
        <div style={cardStyle}>
          <h3 style={subHeadingStyle}>Selecione as funcionalidades concluídas</h3>

          {funcsConcluidas.length === 0 && (
            <p style={{ color: "#6a6a7a", fontSize: 13, marginBottom: 12 }}>
              Nenhuma funcionalidade com status &quot;concluída&quot; disponível.
            </p>
          )}

          {funcsConcluidas.map((f) => (
            <div key={f.id} style={checkboxRowStyle}>
              <input
                type="checkbox"
                id={`func-${f.id}`}
                checked={selectedFuncIds.includes(f.id)}
                onChange={() => toggleFuncId(f.id)}
                style={{ marginTop: 2, cursor: "pointer" }}
              />
              <label
                htmlFor={`func-${f.id}`}
                style={{ fontSize: 13, color: "#111116", cursor: "pointer" }}
              >
                {f.id_funcional} — {f.titulo}
              </label>
            </div>
          ))}

          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              style={selectedFuncIds.length > 0 && !gerando ? btnPrimary : btnDisabled}
              disabled={selectedFuncIds.length === 0 || gerando}
              onClick={handleGerarBoletim}
            >
              {gerando ? "Gerando..." : "Gerar Boletim"}
            </button>
            <button
              style={btnSecondary}
              onClick={() => {
                setNovoBoletimAberto(false);
                setSelectedFuncIds([]);
              }}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Preview do boletim gerado */}
      {novoBoletimAberto && boletimPreview !== null && (
        <div style={cardStyle}>
          <h3 style={subHeadingStyle}>Preview do Boletim</h3>
          <div style={markdownWrapStyle}>
            <ReactMarkdown>{boletimPreview.conteudo}</ReactMarkdown>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={btnPrimary} onClick={handleMarcarEnviadoPreview}>
              Marcar como Enviado
            </button>
            <button
              style={btnSecondary}
              onClick={() => setBoletimPreview(null)}
            >
              Descartar Rascunho
            </button>
          </div>
        </div>
      )}

      {/* ================================================================
          SEÇÃO 2: RESUMO SEMANAL
          ================================================================ */}
      <hr style={dividerStyle} />

      <h2 style={headingStyle}>Resumo Semanal</h2>

      <button
        style={gerandoResumo ? btnDisabled : btnSecondary}
        disabled={gerandoResumo}
        onClick={handleGerarResumo}
      >
        {gerandoResumo ? "Gerando..." : "Gerar Resumo desta Semana"}
      </button>

      {resumoSemanal !== null && (
        <div style={{ ...markdownWrapStyle, marginTop: 16 }}>
          <ReactMarkdown>{resumoSemanal}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
