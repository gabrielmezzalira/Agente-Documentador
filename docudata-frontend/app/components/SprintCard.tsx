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
import { docTypeLabel } from "../lib/doc_types";

const EXPECTED_DAILYS = 5;

interface Props {
  sprint: SprintWithStatus;
  ingestions: Ingestion[];      // já filtradas pra esta sprint
  docs: GeneratedDoc[];         // já filtradas pra esta sprint
  generating: boolean;          // estado global de geração
  onOpenSprintDoc: (tipo: SprintDocType, sprintNumero: number) => void;
  onUploadLivre: (sprintNumero: number) => void;
  onGenerateSprintDoc: (tipoDoc: "sprint_status" | "sprint_retro", sprintNumero: number) => void;
  onAddManualDoc: (sprintNumero: number) => void;
  onDeleteDoc: (docId: string) => void;
  onHealthChanged: () => void;
}

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "18px 22px",
  marginBottom: 12,
};

const headerRow: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
};

const titleStyle: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: "#111116",
  margin: 0,
};

const statusRow: React.CSSProperties = {
  display: "flex",
  gap: 8,
  alignItems: "center",
  flexWrap: "wrap",
  marginTop: 14,
  marginBottom: 14,
};

const statusChip = (done: boolean): React.CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "6px 12px",
  borderRadius: 8,
  fontSize: 13,
  fontWeight: 600,
  background: done ? "#dcfce7" : "#fef3c7",
  color: done ? "#16a34a" : "#b45309",
  border: done ? "1px solid #86efac" : "1px solid #fde68a",
  cursor: "pointer",
  transition: "transform 0.05s",
});

const dailyChip = (count: number): React.CSSProperties => ({
  ...statusChip(count > 0),
  background: count >= EXPECTED_DAILYS ? "#dcfce7" : count > 0 ? "#fef3c7" : "#f7f7fa",
  color: count >= EXPECTED_DAILYS ? "#16a34a" : count > 0 ? "#b45309" : "#6a6a7a",
  border: count >= EXPECTED_DAILYS
    ? "1px solid #86efac"
    : count > 0
    ? "1px solid #fde68a"
    : "1px solid #e4e4ea",
});

const muted: React.CSSProperties = {
  color: "#9696a0",
  fontSize: 12,
  marginLeft: 4,
};

const actionRow: React.CSSProperties = {
  display: "flex",
  gap: 6,
  flexWrap: "wrap",
};

const btnGhost: React.CSSProperties = {
  background: "#f7f7fa",
  color: "#374151",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  padding: "7px 12px",
  fontSize: 12,
  fontWeight: 500,
  cursor: "pointer",
};

const btnSubtle: React.CSSProperties = {
  background: "transparent",
  color: "#9696a0",
  border: "none",
  fontSize: 12,
  cursor: "pointer",
  padding: "6px 10px",
};

const detailBox: React.CSSProperties = {
  marginTop: 16,
  padding: 14,
  background: "#f7f7fa",
  borderRadius: 10,
  border: "1px solid #e8e8ed",
};

const subTitleStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#9696a0",
  margin: 0,
  marginBottom: 8,
};

const tagStyle: React.CSSProperties = {
  background: "#e0e7ff",
  color: "#4338ca",
  borderRadius: 4,
  padding: "1px 7px",
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
};

const docRow: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 8,
  padding: "10px 12px",
  fontSize: 13,
};

const docHeader: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 8,
};

const markdownContainer: React.CSSProperties = {
  marginTop: 10,
  background: "#f7f7fa",
  border: "1px solid #e8e8ed",
  borderRadius: 8,
  padding: "14px 18px",
  lineHeight: 1.7,
  color: "#374151",
  fontSize: 13,
};

const tinyBtn: React.CSSProperties = {
  background: "#fff",
  color: "#374151",
  border: "1px solid #e4e4ea",
  borderRadius: 6,
  padding: "4px 9px",
  fontSize: 11,
  fontWeight: 500,
  cursor: "pointer",
};

const tinyBtnDanger: React.CSSProperties = {
  ...tinyBtn,
  background: "#fef2f2",
  color: "#dc2626",
  border: "1px solid #fecaca",
};

export default function SprintCard({
  sprint,
  ingestions,
  docs,
  generating,
  onOpenSprintDoc,
  onUploadLivre,
  onGenerateSprintDoc,
  onAddManualDoc,
  onDeleteDoc,
  onHealthChanged,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);

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
          <span style={{ marginLeft: 4, fontWeight: 700 }}>+</span>
        </button>
        <button
          type="button"
          style={statusChip(sprint.tem_review)}
          onClick={() => onOpenSprintDoc("review", sprint.numero)}
          title="Adicionar Review"
        >
          {sprint.tem_review ? "1/1" : "0/1"} Review
          <span style={{ marginLeft: 4, fontWeight: 700 }}>+</span>
        </button>
        <button
          type="button"
          style={dailyChip(sprint.dailys_count)}
          onClick={() => onOpenSprintDoc("daily", sprint.numero)}
          title="Adicionar Daily"
        >
          {sprint.dailys_count}/{EXPECTED_DAILYS} Dailys
          <span style={{ marginLeft: 4, fontWeight: 700 }}>+</span>
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
          style={btnGhost}
          onClick={() => onGenerateSprintDoc("sprint_status", sprint.numero)}
          disabled={generating}
        >
          {generating ? "Gerando…" : "Gerar Repasse Semanal"}
        </button>
        <button
          style={btnGhost}
          onClick={() => onGenerateSprintDoc("sprint_retro", sprint.numero)}
          disabled={generating}
        >
          {generating ? "Gerando…" : "Gerar Retrospectiva"}
        </button>
        <button style={btnGhost} onClick={() => onUploadLivre(sprint.numero)}>
          Upload livre
        </button>
        <button style={btnGhost} onClick={() => onAddManualDoc(sprint.numero)}>
          + Documento manual
        </button>
      </div>

      {expanded && (
        <div style={detailBox}>
          {/* DOCS GERADOS DA SPRINT — mais destaque, primeiro */}
          <p style={subTitleStyle}>Documentos desta sprint ({docs.length})</p>
          {docs.length === 0 ? (
            <p style={{ color: "#9696a0", fontSize: 13, margin: "0 0 14px" }}>
              Nenhum documento gerado para esta sprint ainda.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 16 }}>
              {docs.map((d) => (
                <div key={d.id} style={docRow}>
                  <div style={docHeader}>
                    <span style={{ fontWeight: 600, color: "#111116" }}>
                      {docTypeLabel(d.doc_type)}
                      <span style={{ color: "#b8b8c0", fontWeight: 400, marginLeft: 8 }}>
                        {new Date(d.created_at).toLocaleDateString("pt-BR")}
                      </span>
                    </span>
                    <div style={{ display: "flex", gap: 4 }}>
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

          {/* INGESTÕES — contexto bruto, secundário */}
          <p style={subTitleStyle}>
            Ingestões da sprint ({ingestions.length})
            <span style={{ ...muted, fontWeight: 400, marginLeft: 6, textTransform: "none", letterSpacing: 0 }}>
              — material bruto que alimenta as docs
            </span>
          </p>
          {ingestions.length === 0 ? (
            <p style={{ color: "#9696a0", fontSize: 13, margin: 0 }}>
              Nenhuma ingestão nesta sprint.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {ingestions.map((ing) => (
                <div
                  key={ing.id}
                  style={{
                    background: "#fff",
                    border: "1px solid #e8e8ed",
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
                  {ing.extracted_content?.resumo && (
                    <p style={{ color: "#6a6a7a", margin: "4px 0 0", fontSize: 12, lineHeight: 1.5 }}>
                      {ing.extracted_content.resumo}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
