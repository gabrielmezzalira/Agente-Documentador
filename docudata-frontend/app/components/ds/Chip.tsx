import type { ReactNode } from "react";
import { ds, toneColors, type Tone } from "../../lib/ds";

/** Ponto de status de 7px com brilho. */
export function StatusDot({ tone = "green" }: { tone?: Tone }) {
  const color = tone === "neutral" ? ds.dim : toneColors[tone].fg;
  return (
    <span
      aria-hidden="true"
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        borderRadius: "50%",
        background: color,
        boxShadow: tone === "neutral" ? "none" : `0 0 8px ${color}`,
        flexShrink: 0,
      }}
    />
  );
}

/** Pílula de 12px/600 com cor suave do estado. */
export default function Chip({ tone = "neutral", dot = false, children }: { tone?: Tone; dot?: boolean; children: ReactNode }) {
  const c = toneColors[tone];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 10px",
        borderRadius: 999,
        background: c.bg,
        color: c.fg,
        border: `1px solid ${c.line}`,
        fontSize: 12,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      {dot && <StatusDot tone={tone} />}
      {children}
    </span>
  );
}
