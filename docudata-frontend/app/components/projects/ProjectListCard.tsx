"use client";

import Link from "next/link";
import { useState } from "react";
import type { Project, Subarea } from "../../lib/api";
import { cardStyle, ds } from "../../lib/ds";
import { Chip, StatusDot } from "../ds";

const STALE_DAYS = 7;

export function isStale(project: Project): boolean {
  if (project.is_delivered) return false;
  if (!project.last_ingestion_at) return true;
  const diff = Date.now() - new Date(project.last_ingestion_at).getTime();
  return diff > STALE_DAYS * 24 * 60 * 60 * 1000;
}

/** Cartão de projeto da lista da subárea: status (em dia / parado / entregue), cliente, data e detalhes. */
export default function ProjectListCard({ project, subarea }: { project: Project; subarea: Subarea }) {
  const [expanded, setExpanded] = useState(false);
  const stale = isStale(project);

  return (
    <Link href={`/${subarea}/projects/${project.id}`} style={{ display: "block" }}>
      <div className="ds-row-link" style={{ ...cardStyle, ...(stale ? { borderColor: "rgba(255, 107, 107, 0.22)" } : null) }}>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 20, alignItems: "center", padding: "22px 26px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <StatusDot tone={project.is_delivered ? "neutral" : stale ? "red" : "green"} />
              <span style={{ fontSize: 17, fontWeight: 600, color: ds.white }}>{project.name}</span>
            </div>
            <span style={{ fontSize: 13.5, color: ds.green, fontWeight: 500, paddingLeft: 17 }}>{project.client}</span>
            {expanded && project.description && (
              <p style={{ color: ds.muted, fontSize: 13.5, lineHeight: 1.6, paddingLeft: 17 }}>{project.description}</p>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap", justifyContent: "flex-end" }}>
            {project.is_delivered ? <Chip>Entregue</Chip> : stale ? <Chip tone="red">Sem insumo nos últimos 7 dias</Chip> : <Chip tone="green">Em dia</Chip>}
            <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{new Date(project.created_at).toLocaleDateString("pt-BR")}</span>
            {project.description && (
              <button
                type="button"
                aria-expanded={expanded}
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setExpanded((v) => !v); }}
                style={{ background: "none", border: "none", color: ds.muted, fontSize: 13, cursor: "pointer", fontFamily: "inherit" }}
              >
                {expanded ? "ocultar ▴" : "ver detalhes ▾"}
              </button>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
