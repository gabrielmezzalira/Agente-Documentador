"use client";

import { useEffect, useState } from "react";
import { createManualDoc, type GeneratedDoc } from "../lib/api";
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
  maxWidth: 640,
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
  minHeight: 240,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
  fontSize: 13,
  lineHeight: 1.6,
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
  "sprint_status",
  "sprint_retro",
  "ata_reuniao",
  "decisoes",
  "adr",
  "onboarding",
  "completo",
  "planning",
  "daily",
  "review",
];

export default function ManualDocModal({
  open,
  onClose,
  projetoId,
  defaultSprintNumero = null,
  defaultDocType = "completo",
  onCreated,
}: Props) {
  const [docType, setDocType] = useState<DocTypeKey>(defaultDocType);
  const [sprintNumero, setSprintNumero] = useState<number | null>(defaultSprintNumero);
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setDocType(defaultDocType);
      setSprintNumero(defaultSprintNumero);
      setContent("");
      setError(null);
    }
  }, [open, defaultDocType, defaultSprintNumero]);

  if (!open) return null;

  async function submit() {
    if (!content.trim()) {
      setError("O conteúdo do documento não pode estar vazio.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const doc = await createManualDoc({
        projetoId,
        docType,
        sprintNumero: sprintNumero ?? null,
        content,
      });
      onCreated?.(doc);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar documento");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>
          Adicionar documento manual
        </h2>
        <p style={{ fontSize: 13, color: "#6a6a7a", margin: "8px 0 0", lineHeight: 1.5 }}>
          Use pra registrar um doc que você já escreveu fora do sistema. Não chama o LLM
          (sem custo). Aparece junto com os documentos gerados.
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
          style={{ ...inputStyle, width: 120 }}
          placeholder="—"
        />

        <label style={labelStyle}>Conteúdo (markdown)</label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={"# Título\n\n## Seção\n\nTexto..."}
          style={textareaStyle}
        />

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
