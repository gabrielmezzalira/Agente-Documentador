"use client";

import { useState } from "react";
import type { DocTypeMeta } from "../lib/doc_types";
import type { Ingestion, SprintWithStatus } from "../lib/api";

interface Props {
  meta: DocTypeMeta;
  sprints: SprintWithStatus[];
  ingestions: Ingestion[];
  generating: boolean;
  /** Disparado quando o usuário clica em "Gerar documento" dentro do card. */
  onGenerate: (key: string, sprintNumero?: number, ingestionId?: string) => void;
}

const cardStyle = (expanded: boolean): React.CSSProperties => ({
  background: "#ffffff",
  border: `1px solid ${expanded ? "#86efac" : "#e8e8ed"}`,
  borderRadius: 12,
  padding: expanded ? "16px 18px" : "12px 16px",
  cursor: "pointer",
  transition: "border-color 0.15s, padding 0.15s",
});

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
};

const titleStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  fontSize: 14,
  fontWeight: 700,
  color: "#111116",
};

const explanationStyle: React.CSSProperties = {
  marginTop: 14,
  display: "flex",
  flexDirection: "column",
  gap: 8,
  fontSize: 13,
  color: "#374151",
  lineHeight: 1.5,
};

const lineStyle: React.CSSProperties = {
  display: "flex",
  gap: 6,
};

const labelChip: React.CSSProperties = {
  flexShrink: 0,
  fontWeight: 700,
  color: "#6a6a7a",
  width: 78,
};

const formZone: React.CSSProperties = {
  marginTop: 16,
  paddingTop: 16,
  borderTop: "1px solid #f0f0f4",
  display: "flex",
  flexWrap: "wrap",
  alignItems: "center",
  gap: 10,
};

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  background: "#fff",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  fontSize: 13,
  color: "#111116",
  outline: "none",
};

const btnPrimary: React.CSSProperties = {
  background: "#4ade80",
  color: "#052e16",
  border: "none",
  borderRadius: 8,
  padding: "8px 16px",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
};

const fieldLabel: React.CSSProperties = {
  fontSize: 12,
  color: "#6a6a7a",
  fontWeight: 600,
};

export default function DocTypeCard({
  meta,
  sprints,
  ingestions,
  generating,
  onGenerate,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [sprintNumero, setSprintNumero] = useState<number>(
    sprints[0]?.numero ?? 1
  );
  const [ingestionId, setIngestionId] = useState<string>(
    ingestions[0]?.id ?? ""
  );

  function handleGenerate(e: React.MouseEvent) {
    e.stopPropagation();
    if (meta.scope === "sprint") onGenerate(meta.key, sprintNumero);
    else if (meta.scope === "ingestion") onGenerate(meta.key, undefined, ingestionId);
    else onGenerate(meta.key);
  }

  return (
    <div style={cardStyle(expanded)} onClick={() => setExpanded((v) => !v)}>
      <div style={headerStyle}>
        <span style={titleStyle}>
          <span style={{ fontSize: 18 }}>{meta.icone}</span>
          {meta.label}
        </span>
        <span style={{ color: "#9696a0", fontSize: 13 }}>
          {expanded ? "▴" : "▾"}
        </span>
      </div>

      {expanded && (
        <>
          <div style={explanationStyle}>
            <div style={lineStyle}>
              <span style={labelChip}>O quê</span>
              <span>{meta.o_que}</span>
            </div>
            <div style={lineStyle}>
              <span style={labelChip}>Pra quê</span>
              <span>{meta.pra_que}</span>
            </div>
            <div style={lineStyle}>
              <span style={labelChip}>Quando</span>
              <span>{meta.quando}</span>
            </div>
            <div style={lineStyle}>
              <span style={labelChip}>Fontes</span>
              <span>{meta.fontes}</span>
            </div>
          </div>

          <div style={formZone} onClick={(e) => e.stopPropagation()}>
            {meta.scope === "sprint" && (
              <>
                <span style={fieldLabel}>Sprint:</span>
                {sprints.length === 0 ? (
                  <input
                    type="number"
                    min={1}
                    value={sprintNumero}
                    onChange={(e) => setSprintNumero(Number(e.target.value))}
                    style={{ ...inputStyle, width: 70 }}
                  />
                ) : (
                  <select
                    value={sprintNumero}
                    onChange={(e) => setSprintNumero(Number(e.target.value))}
                    style={inputStyle}
                  >
                    {sprints.map((s) => (
                      <option key={s.id} value={s.numero}>
                        Sprint {s.numero}
                      </option>
                    ))}
                  </select>
                )}
              </>
            )}

            {meta.scope === "ingestion" && (
              <>
                <span style={fieldLabel}>Ingestão:</span>
                {ingestions.length === 0 ? (
                  <span style={{ color: "#9696a0", fontSize: 13 }}>
                    Nenhuma ingestão disponível ainda.
                  </span>
                ) : (
                  <select
                    value={ingestionId}
                    onChange={(e) => setIngestionId(e.target.value)}
                    style={{ ...inputStyle, maxWidth: 360 }}
                  >
                    {ingestions.map((ing) => (
                      <option key={ing.id} value={ing.id}>
                        Sprint {ing.sprint_number} · {ing.file_name}
                      </option>
                    ))}
                  </select>
                )}
              </>
            )}

            <button
              type="button"
              onClick={handleGenerate}
              disabled={
                generating ||
                (meta.scope === "ingestion" && !ingestionId)
              }
              style={{
                ...btnPrimary,
                opacity: generating ? 0.6 : 1,
                marginLeft: "auto",
              }}
            >
              {generating ? "Gerando…" : "Gerar documento"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
