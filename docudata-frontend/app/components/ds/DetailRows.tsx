import type { ReactNode } from "react";
import { ds } from "../../lib/ds";
import Card from "./Card";

export interface DetailRow {
  label: string;
  value: ReactNode;
}

/** Lista "rótulo à esquerda, valor à direita" dentro de um cartão, com linhas separadas por borda. */
export default function DetailRows({ rows }: { rows: DetailRow[] }) {
  return (
    <Card>
      {rows.map((row, i) => (
        <div
          key={row.label}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 20,
            padding: "18px 24px",
            borderTop: i > 0 ? `1px solid ${ds.border}` : "none",
          }}
        >
          <span style={{ fontSize: 14, color: ds.muted, flexShrink: 0 }}>{row.label}</span>
          <span style={{ fontSize: 14.5, color: ds.white, fontWeight: 500, textAlign: "right", minWidth: 0, overflowWrap: "anywhere" }}>{row.value}</span>
        </div>
      ))}
    </Card>
  );
}
