"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import HealthBadge from "./HealthBadge";
import type {
  GeneratedDoc,
  Ingestion,
  SprintDocType,
  SprintWithStatus,
} from "../lib/api";
import { DOC_TYPES, docTypeLabel } from "../lib/doc_types";

const EXPECTED_DAILYS = 5;

type SprintGenType = "repasse_semanal";

interface Props {
  sprint: SprintWithStatus;
  ingestions: Ingestion[];
  docs: GeneratedDoc[];
  generating: boolean;
  onOpenSprintDoc: (tipo: SprintDocType, sprintNumero: number) => void;
  onUploadLivre: (sprintNumero: number) => void;
  onGenerateSprintDoc: (tipoDoc: SprintGenType, sprintNumero: number) => void;
  onOpenRetroModal: (sprintNumero: number) => void;
  onAddManualDoc: (sprintNumero: number) => void;
  onDeleteDoc: (docId: string) => void;
  onHealthChanged: () => void;
}

// ---------- styles ----------

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e4e4ea",
  borderRadius: 16,
  padding: "26px 28px",
  marginBottom: 16,
  boxShadow: "0 1px 3px rgba(15, 23, 42, 0.04)",
};

const headerRow: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  marginBottom: 4,
};

const titleStyle: React.CSSProperties = {
  fontSize: 24,
  fontWeight: 800,
  color: "#0f172a",
  letterSpacing: "-0.02em",
  margin: 0,
};

const statusRow: React.CSSProperties = {
  display: "flex",
  gap: 10,
  alignItems: "center",
  flexWrap: "wrap",
  marginTop: 18,
  marginBottom: 18,
};

const statusChip = (done: boolean): React.CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "9px 16px",
  borderRadius: 10,
  fontSize: 14,
  fontWeight: 700,
  background: done ? "#dcfce7" : "#fef3c7",
  color: done ? "#16a34a" : "#b45309",
  border: done ? "1px solid #86efac" : "1px solid #fde68a",
  cursor: "pointer",
  transition: "transform 0.06s",
});

const dailyChip = (count: number): React.CSSProperties => ({
  ...statusChip(count > 0),
  background: count >= EXPECTED_DAILYS ? "#dcfce7" : count > 0 ? "#fef3c7" : "#f7f7fa",
  color: count >= EXPECTED_DAILYS ? "#16a34a" : count > 0 ? "#b45309" : "#475569",
  border: count >= EXPECTED_DAILYS
    ? "1px solid #86efac"
    : count > 0
    ? "1px solid #fde68a"
    : "1px solid #e4e4ea",
});

const muted: React.CSSProperties = {
  color: "#9696a0",
  fontSize: 13,
  marginLeft: 4,
};

const actionRow: React.CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
};

const btnAction: React.CSSProperties = {
  background: "#f1f5f9",
  color: "#1e293b",
  border: "1px solid #e2e8f0",
  borderRadius: 10,
  padding: "11px 18px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
  transition: "background 0.1s",
};

const btnActionActive: React.CSSProperties = {
  ...btnAction,
  background: "#dcfce7",
  borderColor: "#86efac",
  color: "#15803d",
};

const btnSubtle: React.CSSProperties = {
  background: "transparent",
  color: "#64748b",
  border: "none",
  fontSize: 13,
  cursor: "pointer",
  padding: "8px 12px",
  fontWeight: 500,
};

const confirmPanel: React.CSSProperties = {
  marginTop: 14,
  padding: "16px 18px",
  background: "#f8fafc",
  borderRadius: 12,
  border: "1px solid #e2e8f0",
};

const confirmField: React.CSSProperties = {
  display: "flex",
  gap: 8,
  fontSize: 13,
  color: "#475569",
  marginBottom: 8,
  lineHeight: 1.5,
};

const confirmFieldLabel: React.CSSProperties = {
  flexShrink: 0,
  fontWeight: 700,
  color: "#1e293b",
  minWidth: 72,
};

const confirmActions: React.CSSProperties = {
  display: "flex",
  gap: 8,
  justifyContent: "flex-end",
  marginTop: 14,
};

const btnConfirm: React.CSSProperties = {
  background: "#4ade80",
  color: "#052e16",
  border: "none",
  padding: "9px 18px",
  borderRadius: 8,
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
};

const btnCancel: React.CSSProperties = {
  background: "#fff",
  color: "#64748b",
  border: "1px solid #e2e8f0",
  padding: "9px 16px",
  borderRadius: 8,
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};

const detailBox: React.CSSProperties = {
  marginTop: 20,
  padding: 18,
  background: "#f8fafc",
  borderRadius: 12,
  border: "1px solid #e2e8f0",
};

const subTitleStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#64748b",
  margin: 0,
  marginBottom: 10,
};

const tagStyle: React.CSSProperties = {
  background: "#e0e7ff",
  color: "#4338ca",
  borderRadius: 5,
  padding: "2px 9px",
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
};

const docRow: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 10,
  padding: "12px 14px",
  fontSize: 13,
};

const docHeader: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 8,
};

const markdownContainer: React.CSSProperties = {
  marginTop: 12,
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: "16px 20px",
  lineHeight: 1.7,
  color: "#374151",
  fontSize: 13,
};

const tinyBtn: React.CSSProperties = {
  background: "#fff",
  color: "#374151",
  border: "1px solid #e2e8f0",
  borderRadius: 7,
  padding: "5px 11px",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
};

const tinyBtnDanger: React.CSSProperties = {
  ...tinyBtn,
  background: "#fef2f2",
  color: "#dc2626",
  border: "1px solid #fecaca",
};

// ---------- component ----------

export default function SprintCard({
  sprint,
  ingestions,
  docs,
  generating,
  onOpenSprintDoc,
  onUploadLivre,
  onGenerateSprintDoc,
  onOpenRetroModal,
  onAddManualDoc,
  onDeleteDoc,
  onHealthChanged,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const [expandedIngId, setExpandedIngId] = useState<string | null>(null);
  const [pendingGen, setPendingGen] = useState<SprintGenType | null>(null);

  function confirmGenerate() {
    if (pendingGen) {
      onGenerateSprintDoc(pendingGen, sprint.numero);
      setPendingGen(null);
    }
  }

  const pendingMeta = pendingGen ? DOC_TYPES[pendingGen] : null;

  type ExtractedContent = NonNullable<Ingestion["extracted_content"]>;

  function renderIngestionChips(content: ExtractedContent | undefined | null) {
    if (!content) return null;
    const tarefas = content.tarefas?.length ?? 0;
    const decisoes = content.decisoes?.length ?? 0;
    const problemas = content.problemas?.length ?? 0;
    const tecnologias = content.tecnologias ?? [];
    const parts: string[] = [];
    if (tarefas > 0) parts.push(`📋 ${tarefas}`);
    if (decisoes > 0) parts.push(`🧭 ${decisoes}`);
    if (problemas > 0) parts.push(`⚠️ ${problemas}`);
    if (tecnologias.length > 0) {
      const techStr = tecnologias.slice(0, 3).join(", ") + (tecnologias.length > 3 ? "…" : "");
      parts.push(`🔧 ${techStr}`);
    }
    if (parts.length === 0) return null;
    return (
      <p style={{ color: "#8892a4", fontSize: 11, margin: "4px 0 0", lineHeight: 1.4 }}>
        {parts.join("  ·  ")}
      </p>
    );
  }

  function renderIngestionDetail(content: ExtractedContent | undefined | null) {
    if (!content) return null;
    const sections = [
      { label: "Tarefas", items: content.tarefas ?? [] },
      { label: "Decisões", items: content.decisoes ?? [] },
      { label: "Problemas", items: content.problemas ?? [] },
      { label: "Próximos passos", items: content.proximos_passos ?? [] },
      { label: "Tecnologias", items: content.tecnologias ?? [] },
    ].filter((s) => s.items.length > 0);
    if (sections.length === 0) return null;
    return (
      <div style={{ marginTop: 8, borderTop: "1px solid #f0f0f6", paddingTop: 8 }}>
        {sections.map(({ label, items }) => (
          <div key={label} style={{ marginBottom: 6 }}>
            <span style={{ fontWeight: 700, fontSize: 11, color: "#64748b" }}>{label}:</span>
            <ul style={{ margin: "2px 0 0 16px", padding: 0 }}>
              {items.map((item, i) => (
                <li key={i} style={{ fontSize: 11, color: "#52525b", lineHeight: 1.5 }}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <div style={headerRow}>
        <h3 style={titleStyle}>Sprint {sprint.numero}</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <HealthBadge
            sprintId={sprint.id}
            value={sprint.status_saude}
            planoCorrecao={sprint.plano_correcao}
            onChanged={onHealthChanged}
          />
          <button style={btnSubtle} onClick={() => setExpanded((v) => !v)}>
            {expanded ? "Recolher" : "Detalhes"}
          </button>
        </div>
      </div>

      {/* Chips clicáveis — clicar adiciona o doc correspondente */}
      <div style={statusRow}>
        <button
          type="button"
          style={statusChip(sprint.tem_planning)}
          onClick={() => onOpenSprintDoc("planning", sprint.numero)}
          title="Adicionar Planning"
        >
          {sprint.tem_planning ? "1/1" : "0/1"} Planning
          <span style={{ marginLeft: 4, fontWeight: 800 }}>+</span>
        </button>
        <button
          type="button"
          style={statusChip(sprint.tem_review)}
          onClick={() => onOpenSprintDoc("review", sprint.numero)}
          title="Adicionar Review"
        >
          {sprint.tem_review ? "1/1" : "0/1"} Review
          <span style={{ marginLeft: 4, fontWeight: 800 }}>+</span>
        </button>
        <button
          type="button"
          style={dailyChip(sprint.dailys_count)}
          onClick={() => onOpenSprintDoc("daily", sprint.numero)}
          title="Adicionar Daily"
        >
          {sprint.dailys_count}/{EXPECTED_DAILYS} Dailys
          <span style={{ marginLeft: 4, fontWeight: 800 }}>+</span>
        </button>
        <span style={muted}>
          · {sprint.ingestions_count} ingestões · {sprint.docs_gerados_count} docs
        </span>
        {sprint.plano_correcao && (
          <span style={{ ...muted, color: "#b45309" }}>
            · plano de correção definido
          </span>
        )}
      </div>

      <div style={actionRow}>
        <button
          style={pendingGen === "repasse_semanal" ? btnActionActive : btnAction}
          onClick={() => setPendingGen(pendingGen === "repasse_semanal" ? null : "repasse_semanal")}
        >
          Gerar Repasse Semanal
        </button>
        <button
          style={btnAction}
          onClick={() => onOpenRetroModal(sprint.numero)}
        >
          Gerar Retrospectiva
        </button>
        <button style={btnAction} onClick={() => onUploadLivre(sprint.numero)}>
          Upload livre
        </button>
        <button style={btnAction} onClick={() => onAddManualDoc(sprint.numero)}>
          + Documento manual
        </button>
      </div>

      {/* Painel de confirmação com explicação */}
      {pendingMeta && (
        <div style={confirmPanel}>
          <h4 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", margin: "0 0 12px" }}>
            {pendingMeta.label} — Sprint {sprint.numero}
          </h4>
          <div style={confirmField}>
            <span style={confirmFieldLabel}>O quê</span>
            <span>{pendingMeta.o_que}</span>
          </div>
          <div style={confirmField}>
            <span style={confirmFieldLabel}>Pra quê</span>
            <span>{pendingMeta.pra_que}</span>
          </div>
          <div style={confirmField}>
            <span style={confirmFieldLabel}>Quando</span>
            <span>{pendingMeta.quando}</span>
          </div>
          <div style={confirmField}>
            <span style={confirmFieldLabel}>Fontes</span>
            <span>{pendingMeta.fontes}</span>
          </div>
          <div style={confirmActions}>
            <button style={btnCancel} onClick={() => setPendingGen(null)}>
              Cancelar
            </button>
            <button
              style={{ ...btnConfirm, opacity: generating ? 0.6 : 1 }}
              onClick={confirmGenerate}
              disabled={generating}
            >
              {generating ? "Gerando…" : "Confirmar e gerar"}
            </button>
          </div>
        </div>
      )}

      {expanded && (
        <div style={detailBox}>
          {/* DOCS GERADOS DA SPRINT — destaque */}
          <p style={subTitleStyle}>Documentos desta sprint ({docs.length})</p>
          {docs.length === 0 ? (
            <p style={{ color: "#9696a0", fontSize: 13, margin: "0 0 14px" }}>
              Nenhum documento gerado para esta sprint ainda.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 18 }}>
              {docs.map((d) => (
                <div key={d.id} style={docRow}>
                  <div style={docHeader}>
                    <span style={{ fontWeight: 600, color: "#0f172a" }}>
                      {docTypeLabel(d.doc_type)}
                      <span style={{ color: "#94a3b8", fontWeight: 400, marginLeft: 8 }}>
                        {new Date(d.created_at).toLocaleDateString("pt-BR")}
                      </span>
                    </span>
                    <div style={{ display: "flex", gap: 5 }}>
                      <button
                        style={tinyBtn}
                        onClick={() => setExpandedDocId(expandedDocId === d.id ? null : d.id)}
                      >
                        {expandedDocId === d.id ? "Fechar" : "Ver"}
                      </button>
                      <button
                        style={tinyBtn}
                        onClick={() => navigator.clipboard.writeText(d.content)}
                      >
                        Copiar
                      </button>
                      <button
                        style={tinyBtnDanger}
                        onClick={() => {
                          if (confirm("Excluir este documento?")) onDeleteDoc(d.id);
                        }}
                      >
                        Excluir
                      </button>
                    </div>
                  </div>
                  {expandedDocId === d.id && (
                    <div style={markdownContainer}>
                      <ReactMarkdown>{d.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* INGESTÕES — material bruto, secundário */}
          <p style={subTitleStyle}>
            Ingestões da sprint ({ingestions.length})
            <span style={{
              ...muted,
              fontWeight: 400,
              marginLeft: 6,
              textTransform: "none",
              letterSpacing: 0,
            }}>
              — material bruto que alimenta as docs
            </span>
          </p>
          {ingestions.length === 0 ? (
            <p style={{ color: "#9696a0", fontSize: 13, margin: 0 }}>
              Nenhuma ingestão nesta sprint.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {ingestions.map((ing) => {
                const isIngExpanded = expandedIngId === ing.id;
                const content = ing.extracted_content;
                const hasDetails = content && (
                  (content.tarefas?.length ?? 0) > 0 ||
                  (content.decisoes?.length ?? 0) > 0 ||
                  (content.problemas?.length ?? 0) > 0 ||
                  (content.proximos_passos?.length ?? 0) > 0 ||
                  (content.tecnologias?.length ?? 0) > 0
                );
                return (
                  <div
                    key={ing.id}
                    style={{
                      background: "#fff",
                      border: "1px solid #e2e8f0",
                      borderRadius: 8,
                      padding: "10px 12px",
                      fontSize: 13,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <span style={{ fontWeight: 600 }}>{ing.file_name}</span>
                      {ing.tipo_documentacao && (
                        <span style={tagStyle}>{ing.tipo_documentacao}</span>
                      )}
                    </div>
                    {content?.resumo && (
                      <p style={{ color: "#6a6a7a", margin: "4px 0 0", fontSize: 12, lineHeight: 1.5 }}>
                        {content.resumo}
                      </p>
                    )}
                    {renderIngestionChips(content)}
                    {hasDetails && (
                      <button
                        onClick={() => setExpandedIngId(isIngExpanded ? null : ing.id)}
                        style={{
                          background: "none",
                          border: "none",
                          padding: "3px 0 0",
                          fontSize: 11,
                          color: "#6366f1",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                      >
                        {isIngExpanded ? "ocultar detalhes ▲" : "ver detalhes ▼"}
                      </button>
                    )}
                    {isIngExpanded && renderIngestionDetail(content)}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
