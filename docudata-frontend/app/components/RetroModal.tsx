"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { enrichContent, type EnrichResult } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  projetoId: string;
  sprintNumero: number;
  onSubmit: (observacoes: string, pedidoForaEscopoStatus: string, file: File | null) => Promise<void>;
}

const overlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: 16,
};

const modalStyle: CSSProperties = {
  background: "#fff",
  borderRadius: 12,
  width: "100%",
  maxWidth: 560,
  maxHeight: "90vh",
  overflowY: "auto",
  padding: 24,
  boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)",
};

const labelStyle: CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 600,
  color: "#334155",
  marginBottom: 6,
  marginTop: 14,
};

const textareaStyle: CSSProperties = {
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

const primaryBtn: CSSProperties = {
  background: "#4ade80",
  color: "#052e16",
  border: "none",
  padding: "10px 18px",
  borderRadius: 8,
  fontWeight: 700,
  fontSize: 14,
  cursor: "pointer",
};

const ghostBtn: CSSProperties = {
  background: "#f7f7fa",
  color: "#475569",
  border: "1px solid #e2e8f0",
  padding: "10px 18px",
  borderRadius: 8,
  fontWeight: 600,
  fontSize: 14,
  cursor: "pointer",
};

const aiBadgeStyle: CSSProperties = {
  fontSize: 11,
  background: "#eff6ff",
  color: "#2563eb",
  border: "1px solid #bfdbfe",
  borderRadius: 4,
  padding: "1px 6px",
  marginLeft: 6,
  fontWeight: 500,
};

export default function RetroModal({ open, onClose, projetoId, sprintNumero, onSubmit }: Props) {
  const [step, setStep] = useState<"input" | "form">("input");
  const [enrichText, setEnrichText] = useState("");
  const enrichFileRef = useRef<HTMLInputElement | null>(null);
  const [enrichFileName, setEnrichFileName] = useState<string | null>(null);
  const [enriching, setEnriching] = useState(false);
  const [aiFields, setAiFields] = useState<Set<string>>(new Set());

  const [observacoes, setObservacoes] = useState("");
  const [pedidoForaEscopoStatus, setPedidoForaEscopoStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [anexoName, setAnexoName] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) {
      setStep("input");
      setEnrichText("");
      setEnrichFileName(null);
      setEnriching(false);
      setAiFields(new Set());
      setObservacoes("");
      setPedidoForaEscopoStatus("");
      setSubmitting(false);
      setError(null);
      setAnexoName(null);
      if (fileRef.current) fileRef.current.value = "";
      if (enrichFileRef.current) enrichFileRef.current.value = "";
    }
  }, [open]);

  if (!open) return null;

  const AiBadge = ({ field }: { field: string }) =>
    aiFields.has(field) ? <span style={aiBadgeStyle}>IA</span> : null;

  const handleEnrich = async () => {
    setEnriching(true);
    setError(null);
    const arquivo = enrichFileRef.current?.files?.[0] ?? null;
    try {
      const result: EnrichResult = await enrichContent({
        projetoId,
        docType: "retrospectiva",
        texto: enrichText.trim() || undefined,
        arquivo: arquivo || undefined,
      });
      const fields = new Set<string>();
      if (result.observacoes) { setObservacoes(result.observacoes); fields.add("observacoes"); }
      if (result.pedido_fora_escopo_status) { setPedidoForaEscopoStatus(result.pedido_fora_escopo_status); fields.add("pedidoStatus"); }
      setAiFields(fields);
      setStep("form");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao analisar conteúdo");
    } finally {
      setEnriching(false);
    }
  };

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    const file = fileRef.current?.files?.[0] ?? null;
    try {
      await onSubmit(observacoes, pedidoForaEscopoStatus, file);
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
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>
            Gerar Retrospectiva — Sprint {sprintNumero}
          </h2>
          {step === "form" && (
            <span style={{ fontSize: 12, color: "#64748b" }}>Etapa 2 de 2 — Revise e confirme</span>
          )}
        </div>

        {/* ── ETAPA 1 ─────────────────────────────────────────────────── */}
        {step === "input" && (
          <>
            <p style={{ fontSize: 13, color: "#64748b", marginTop: 12, marginBottom: 0 }}>
              Cole a matéria-prima da retro ou faça upload de um arquivo. A IA vai preencher
              os campos para você revisar antes de gerar.
            </p>

            <label style={labelStyle}>Texto (cole aqui)</label>
            <textarea
              style={{ ...textareaStyle, minHeight: 160 }}
              value={enrichText}
              onChange={(e) => setEnrichText(e.target.value)}
              placeholder="Ex: anotações da reunião de retro, transcrição, relato pós-sprint..."
            />

            <label style={labelStyle}>Ou faça upload de arquivo</label>
            <input
              ref={enrichFileRef}
              type="file"
              accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp"
              onChange={(e) => setEnrichFileName(e.target.files?.[0]?.name ?? null)}
            />
            {enrichFileName && (
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Arquivo: {enrichFileName}</div>
            )}

            {error && (
              <div style={{ marginTop: 14, padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, fontSize: 13 }}>
                {error}
              </div>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
              <button type="button" style={ghostBtn} onClick={onClose} disabled={enriching}>Cancelar</button>
              <button type="button" style={ghostBtn} onClick={() => { setError(null); setStep("form"); }} disabled={enriching}>
                Pular — preencher manualmente
              </button>
              <button
                type="button"
                style={{ ...primaryBtn, opacity: enriching || (!enrichText.trim() && !enrichFileName) ? 0.6 : 1 }}
                onClick={handleEnrich}
                disabled={enriching || (!enrichText.trim() && !enrichFileName)}
              >
                {enriching ? "Analisando..." : "Analisar com IA"}
              </button>
            </div>
          </>
        )}

        {/* ── ETAPA 2 ─────────────────────────────────────────────────── */}
        {step === "form" && (
          <>
            {aiFields.size > 0 && (
              <div style={{ marginTop: 12, padding: "8px 12px", background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 8, fontSize: 13, color: "#1e40af" }}>
                Campos marcados com <strong>IA</strong> foram preenchidos automaticamente — revise antes de confirmar.
              </div>
            )}

            <label style={labelStyle}>
              Observações do gerente <span style={{ fontWeight: 400, color: "#9696a0" }}>(opcional)</span>
              <AiBadge field="observacoes" />
            </label>
            <textarea
              style={textareaStyle}
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              placeholder="Tópicos discutidos na reunião de retro, o que o time sentiu que travou, feedbacks internos..."
            />

            <label style={labelStyle}>
              Pedido fora de escopo — status
              <AiBadge field="pedidoStatus" />
            </label>
            <textarea
              style={textareaStyle}
              value={pedidoForaEscopoStatus}
              onChange={(e) => setPedidoForaEscopoStatus(e.target.value)}
              placeholder="Ex: Solicitação de relatório PDF — aceita para Sprint 4"
            />

            <label style={labelStyle}>
              Anexo <span style={{ fontWeight: 400, color: "#9696a0" }}>(opcional) — ex: Tactiq da reunião, ata externa</span>
            </label>
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp"
              onChange={(e) => setAnexoName(e.target.files?.[0]?.name ?? null)}
            />
            {anexoName && (
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Anexo: {anexoName}</div>
            )}

            {error && (
              <div style={{ marginTop: 14, padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, fontSize: 13 }}>
                {error}
              </div>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
              <button type="button" style={ghostBtn} onClick={() => { setError(null); setStep("input"); }} disabled={submitting}>Voltar</button>
              <button type="button" style={ghostBtn} onClick={onClose} disabled={submitting}>Cancelar</button>
              <button
                type="button"
                style={{ ...primaryBtn, opacity: submitting ? 0.6 : 1 }}
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? "Gerando…" : "Gerar Retrospectiva"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
