"use client";

import { useState } from "react";
import HealthBadge from "./HealthBadge";
import type {
  GeneratedDoc,
  Ingestion,
  SprintDocType,
  SprintWithStatus,
} from "../lib/api";
import { docTypeLabel } from "../lib/doc_types";

interface Props {
  sprint: SprintWithStatus;
  ingestions: Ingestion[];      // já filtradas pra esta sprint
  docs: GeneratedDoc[];         // já filtradas pra esta sprint
  onOpenSprintDoc: (tipo: SprintDocType, sprintNumero: number) => void;
  onUploadLivre: (sprintNumero: number) => void;
  onGenerateSprintDoc: (tipoDoc: "sprint_status" | "sprint_retro", sprintNumero: number) => void;
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
  gap: 12,
  alignItems: "center",
  flexWrap: "wrap",
  marginTop: 12,
  marginBottom: 14,
  fontSize: 13,
  color: "#6a6a7a",
};

const statusChip = (ok: boolean, neutral = false): React.CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  padding: "3px 9px",
  borderRadius: 6,
  fontSize: 12,
  fontWeight: 600,
  background: neutral ? "#f7f7fa" : ok ? "#dcfce7" : "#fef3c7",
  color: neutral ? "#6a6a7a" : ok ? "#16a34a" : "#b45309",
});

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
  padding: "6px 12px",
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

export default function SprintCard({
  sprint,
  ingestions,
  docs,
  onOpenSprintDoc,
  onUploadLivre,
  onGenerateSprintDoc,
  onHealthChanged,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [showGenMenu, setShowGenMenu] = useState(false);

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
            {expanded ? "Recolher ▴" : "Detalhes ▾"}
          </button>
        </div>
      </div>

      <div style={statusRow}>
        <span style={statusChip(sprint.tem_planning)}>
          {sprint.tem_planning ? "✓" : "✗"} Planning
        </span>
        <span style={statusChip(sprint.tem_review)}>
          {sprint.tem_review ? "✓" : "✗"} Review
        </span>
        <span style={statusChip(sprint.dailys_count > 0, sprint.dailys_count === 0)}>
          Dailys {sprint.dailys_count}
        </span>
        <span style={{ ...statusChip(true, true), background: "transparent" }}>
          · {sprint.ingestions_count} ingestões · {sprint.docs_gerados_count} docs
        </span>
        {sprint.plano_correcao && (
          <span style={{ ...statusChip(true, true), background: "#fef3c7", color: "#b45309" }}>
            Plano de correção definido
          </span>
        )}
      </div>

      <div style={actionRow}>
        <button style={btnGhost} onClick={() => onOpenSprintDoc("planning", sprint.numero)}>
          + Planning
        </button>
        <button style={btnGhost} onClick={() => onOpenSprintDoc("daily", sprint.numero)}>
          + Daily
        </button>
        <button style={btnGhost} onClick={() => onOpenSprintDoc("review", sprint.numero)}>
          + Review
        </button>
        <button style={btnGhost} onClick={() => onUploadLivre(sprint.numero)}>
          Upload livre
        </button>
        <div style={{ position: "relative" }}>
          <button style={btnGhost} onClick={() => setShowGenMenu((v) => !v)}>
            Gerar docs ▾
          </button>
          {showGenMenu && (
            <div
              style={{
                position: "absolute",
                top: "100%",
                left: 0,
                marginTop: 4,
                background: "#fff",
                border: "1px solid #e4e4ea",
                borderRadius: 8,
                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.12)",
                zIndex: 20,
                minWidth: 180,
              }}
            >
              {[
                { key: "sprint_status", label: "Repasse Semanal" },
                { key: "sprint_retro", label: "Retrospectiva" },
              ].map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => {
                    setShowGenMenu(false);
                    onGenerateSprintDoc(opt.key as "sprint_status" | "sprint_retro", sprint.numero);
                  }}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    padding: "8px 12px",
                    border: "none",
                    background: "transparent",
                    fontSize: 13,
                    color: "#111116",
                    cursor: "pointer",
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {expanded && (
        <div style={detailBox}>
          <p style={subTitleStyle}>Ingestões ({ingestions.length})</p>
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

          <p style={{ ...subTitleStyle, marginTop: 14 }}>Documentos gerados ({docs.length})</p>
          {docs.length === 0 ? (
            <p style={{ color: "#9696a0", fontSize: 13, margin: 0 }}>
              Nenhum documento gerado para esta sprint ainda.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {docs.map((d) => (
                <div
                  key={d.id}
                  style={{
                    background: "#fff",
                    border: "1px solid #e8e8ed",
                    borderRadius: 8,
                    padding: "8px 12px",
                    fontSize: 13,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span>{docTypeLabel(d.doc_type)}</span>
                  <span style={{ color: "#b8b8c0", fontSize: 12 }}>
                    {new Date(d.created_at).toLocaleDateString("pt-BR")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
