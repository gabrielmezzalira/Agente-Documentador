"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  sprintNumero: number;
  onSubmit: (observacoes: string, file: File | null) => Promise<void>;
}

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

const textareaStyle: React.CSSProperties = {
  width: "100%",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: "8px 10px",
  fontSize: 14,
  outline: "none",
  background: "#fff",
  boxSizing: "border-box",
  resize: "vertical",
  minHeight: 120,
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

export default function RetroModal({ open, onClose, sprintNumero, onSubmit }: Props) {
  const [observacoes, setObservacoes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [anexoName, setAnexoName] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) {
      setObservacoes("");
      setSubmitting(false);
      setError(null);
      setAnexoName(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }, [open]);

  if (!open) return null;

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    const file = fileRef.current?.files?.[0] ?? null;
    try {
      await onSubmit(observacoes, file);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao gerar retrospectiva");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>
          Gerar Retrospectiva — Sprint {sprintNumero}
        </h2>

        <label style={labelStyle}>
          Observações do gerente{" "}
          <span style={{ fontWeight: 400, color: "#9696a0" }}>(opcional)</span>
        </label>
        <textarea
          style={textareaStyle}
          value={observacoes}
          onChange={(e) => setObservacoes(e.target.value)}
          placeholder="Tópicos discutidos na reunião de retro, o que o time sentiu que travou, feedbacks internos, decisões de processo..."
        />

        <label style={labelStyle}>
          Anexo{" "}
          <span style={{ fontWeight: 400, color: "#9696a0" }}>
            (opcional) — ex: Tactiq da reunião, ata externa, transcrição
          </span>
        </label>
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp"
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
            {submitting ? "Gerando…" : "Gerar Retrospectiva"}
          </button>
        </div>
      </div>
    </div>
  );
}
