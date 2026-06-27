"use client";

import { useEffect, useRef, useState } from "react";
import { uploadManualDocPdf, type GeneratedDoc } from "../lib/api";
import { DOC_TYPES, type DocTypeKey } from "../lib/doc_types";

interface Props {
  open: boolean;
  onClose: () => void;
  projetoId: string;
  /** Pré-selecionado se o modal for aberto de dentro de uma sprint. */
  defaultSprintNumero?: number | null;
  defaultDocType?: DocTypeKey;
  onCreated?: (doc: GeneratedDoc) => void;
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
  padding: 28,
  boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 600,
  color: "#334155",
  marginBottom: 6,
  marginTop: 16,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: "10px 12px",
  fontSize: 14,
  outline: "none",
  background: "#fff",
  boxSizing: "border-box",
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

const TIPOS_SELECIONAVEIS: DocTypeKey[] = [
  "repasse_semanal",
  "retrospectiva",
  "ata_reuniao",
  "log_decisoes",
  "onboarding",
  "documentacao_final",
  "planning",
  "daily",
  "review",
];

export default function ManualDocModal({
  open,
  onClose,
  projetoId,
  defaultSprintNumero = null,
  defaultDocType = "documentacao_final",
  onCreated,
}: Props) {
  const [docType, setDocType] = useState<DocTypeKey>(defaultDocType);
  const [sprintNumero, setSprintNumero] = useState<number | null>(defaultSprintNumero);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setDocType(defaultDocType);
      setSprintNumero(defaultSprintNumero);
      setFileName(null);
      setError(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }, [open, defaultDocType, defaultSprintNumero]);

  if (!open) return null;

  async function submit() {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Selecione um PDF.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const doc = await uploadManualDocPdf({
        projetoId,
        docType,
        sprintNumero: sprintNumero ?? null,
        arquivo: file,
      });
      onCreated?.(doc);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao subir documento");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: "#0f172a" }}>
          Adicionar documento manual
        </h2>
        <p style={{ fontSize: 13, color: "#6a6a7a", margin: "8px 0 0", lineHeight: 1.5 }}>
          Subir um PDF de doc final escrito fora do sistema. O texto é extraído e armazenado
          junto com os outros documentos do projeto. Não chama o LLM (sem custo).
        </p>

        <label style={labelStyle}>Tipo de documento</label>
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value as DocTypeKey)}
          style={inputStyle}
        >
          {TIPOS_SELECIONAVEIS.map((k) => (
            <option key={k} value={k}>
              {DOC_TYPES[k].label}
            </option>
          ))}
        </select>

        <label style={labelStyle}>
          Sprint (opcional)
          <span style={{ fontWeight: 400, color: "#9696a0", marginLeft: 6 }}>
            — vazio se for doc do projeto inteiro
          </span>
        </label>
        <input
          type="number"
          min={1}
          value={sprintNumero ?? ""}
          onChange={(e) =>
            setSprintNumero(e.target.value === "" ? null : Number(e.target.value))
          }
          style={{ ...inputStyle, width: 140 }}
          placeholder="—"
        />

        <label style={labelStyle}>PDF do documento</label>
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
          style={{ fontSize: 13 }}
        />
        {fileName && (
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 6 }}>
            Selecionado: {fileName}
          </div>
        )}
        <p style={{ fontSize: 12, color: "#9696a0", margin: "8px 0 0", lineHeight: 1.5 }}>
          PDFs escaneados sem camada de texto não são suportados aqui — use o upload livre da sprint nesse caso.
        </p>

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
            onClick={submit}
            disabled={submitting}
          >
            {submitting ? "Salvando…" : "Salvar documento"}
          </button>
        </div>
      </div>
    </div>
  );
}
