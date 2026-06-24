"use client";

import { useEffect, useRef, useState } from "react";
import {
  submitPlanning,
  submitDaily,
  submitReview,
  type SprintDocResponse,
  type SprintDocType,
} from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmitted?: (response: SprintDocResponse) => void;
  tipo: SprintDocType;
  projetoId: string;
  sprintNumero: number;
}

const TITLES: Record<SprintDocType, string> = {
  planning: "Adicionar Planning",
  daily: "Adicionar Daily",
  review: "Adicionar Review",
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: 16,
};

const modalStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 12,
  width: "100%",
  maxWidth: 560,
  maxHeight: "90vh",
  overflowY: "auto",
  padding: 24,
  boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 600,
  color: "#334155",
  marginBottom: 6,
  marginTop: 14,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: "8px 10px",
  fontSize: 14,
  outline: "none",
  background: "#fff",
  boxSizing: "border-box",
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle,
  resize: "vertical",
  minHeight: 80,
  fontFamily: "inherit",
};

const primaryBtn: React.CSSProperties = {
  background: "#4ade80",
  color: "#052e16",
  border: "none",
  padding: "10px 18px",
  borderRadius: 8,
  fontWeight: 700,
  fontSize: 14,
  cursor: "pointer",
};

const ghostBtn: React.CSSProperties = {
  background: "#f7f7fa",
  color: "#475569",
  border: "1px solid #e2e8f0",
  padding: "10px 18px",
  borderRadius: 8,
  fontWeight: 600,
  fontSize: 14,
  cursor: "pointer",
};

export default function SprintDocModal({
  open,
  onClose,
  onSubmitted,
  tipo,
  projetoId,
  sprintNumero,
}: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Planning state
  const [descricao, setDescricao] = useState("");
  const [itens, setItens] = useState<string[]>([""]);

  // Daily state
  const today = new Date().toISOString().slice(0, 10);
  const [data, setData] = useState(today);
  const [feito, setFeito] = useState("");
  const [proximo, setProximo] = useState("");
  const [impedimentos, setImpedimentos] = useState("");

  // Review state
  const [observacoes, setObservacoes] = useState("");

  // Common
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [anexoName, setAnexoName] = useState<string | null>(null);

  // Reset on close
  useEffect(() => {
    if (!open) {
      setSubmitting(false);
      setError(null);
      setDescricao("");
      setItens([""]);
      setData(today);
      setFeito("");
      setProximo("");
      setImpedimentos("");
      setObservacoes("");
      setAnexoName(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }, [open, today]);

  if (!open) return null;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    const anexo = fileRef.current?.files?.[0] ?? null;
    try {
      let response: SprintDocResponse;
      if (tipo === "planning") {
        const cleanItens = itens.map((i) => i.trim()).filter(Boolean);
        if (!descricao.trim()) throw new Error("Descrição é obrigatória");
        response = await submitPlanning({
          projetoId,
          sprintNumero,
          descricao,
          itensBacklog: cleanItens,
          anexo,
        });
      } else if (tipo === "daily") {
        if (!feito.trim() || !proximo.trim())
          throw new Error("Preencha 'O que foi feito' e 'O que será feito'");
        response = await submitDaily({
          projetoId,
          sprintNumero,
          data,
          feito,
          proximo,
          impedimentos: impedimentos || undefined,
          anexo,
        });
      } else {
        response = await submitReview({
          projetoId,
          sprintNumero,
          observacoes: observacoes || undefined,
          anexo,
        });
      }
      onSubmitted?.(response);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao submeter");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>
          {TITLES[tipo]} — Sprint {sprintNumero}
        </h2>

        {tipo === "planning" && (
          <>
            <label style={labelStyle}>Descrição do planejamento</label>
            <textarea
              style={textareaStyle}
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Ex: Sprint focada em finalizar o ETL e iniciar a camada de visualização"
            />
            <label style={labelStyle}>Itens do backlog</label>
            {itens.map((item, idx) => (
              <div key={idx} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                <input
                  style={inputStyle}
                  value={item}
                  onChange={(e) => {
                    const next = [...itens];
                    next[idx] = e.target.value;
                    setItens(next);
                  }}
                  placeholder={`Item ${idx + 1}`}
                />
                {itens.length > 1 && (
                  <button
                    type="button"
                    style={ghostBtn}
                    onClick={() => setItens(itens.filter((_, i) => i !== idx))}
                  >
                    −
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              style={{ ...ghostBtn, marginTop: 4 }}
              onClick={() => setItens([...itens, ""])}
            >
              + Adicionar item
            </button>
          </>
        )}

        {tipo === "daily" && (
          <>
            <label style={labelStyle}>Data</label>
            <input
              type="date"
              style={inputStyle}
              value={data}
              onChange={(e) => setData(e.target.value)}
            />
            <label style={labelStyle}>O que foi feito desde a última Daily?</label>
            <textarea
              style={textareaStyle}
              value={feito}
              onChange={(e) => setFeito(e.target.value)}
            />
            <label style={labelStyle}>O que será feito até a próxima Daily?</label>
            <textarea
              style={textareaStyle}
              value={proximo}
              onChange={(e) => setProximo(e.target.value)}
            />
            <label style={labelStyle}>Existe algum impedimento ou risco?</label>
            <textarea
              style={textareaStyle}
              value={impedimentos}
              onChange={(e) => setImpedimentos(e.target.value)}
              placeholder="Opcional"
            />
          </>
        )}

        {tipo === "review" && (
          <>
            <label style={labelStyle}>Observações do gerente sobre a sprint</label>
            <textarea
              style={{ ...textareaStyle, minHeight: 120 }}
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Opcional — observações qualitativas. O delta planejado vs realizado será calculado automaticamente a partir do planning e das dailys da sprint."
            />
          </>
        )}

        <label style={labelStyle}>Anexo (PDF opcional)</label>
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          onChange={(e) => setAnexoName(e.target.files?.[0]?.name ?? null)}
        />
        {anexoName && (
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
            Anexo: {anexoName}
          </div>
        )}

        {error && (
          <div
            style={{
              marginTop: 14,
              padding: 10,
              background: "#fef2f2",
              color: "#b91c1c",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
          <button type="button" style={ghostBtn} onClick={onClose} disabled={submitting}>
            Cancelar
          </button>
          <button
            type="button"
            style={{ ...primaryBtn, opacity: submitting ? 0.6 : 1 }}
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? "Gerando…" : `Gerar ${tipo === "planning" ? "Planning" : tipo === "daily" ? "Daily" : "Review"}`}
          </button>
        </div>
      </div>
    </div>
  );
}
