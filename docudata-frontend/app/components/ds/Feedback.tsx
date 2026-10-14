import type { ReactNode } from "react";
import { ds } from "../../lib/ds";

/** Estado vazio: borda tracejada e texto apagado. */
export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div style={{ padding: "28px 12px", border: `1px dashed ${ds.borderStrong}`, borderRadius: 12, textAlign: "center", fontSize: 13, color: ds.dim }}>
      {children}
    </div>
  );
}

/** Aviso de erro em cartão vermelho suave. */
export function ErrorNotice({ children }: { children: ReactNode }) {
  return (
    <div role="alert" style={{ fontSize: 13.5, color: ds.red, background: ds.redSoft, border: `1px solid ${ds.redLine}`, borderRadius: 12, padding: "12px 16px" }}>
      {children}
    </div>
  );
}

export function ProgressBar({ pct, tone = "green", height = 6, label }: { pct: number; tone?: "green" | "amber" | "red"; height?: number; label?: string }) {
  const value = Math.max(0, Math.min(100, pct));
  const color = tone === "green" ? ds.green : tone === "amber" ? ds.amber : ds.red;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={100}
      style={{ height, borderRadius: 3, background: "rgba(255, 255, 255, 0.08)", overflow: "hidden" }}
    >
      <div style={{ width: `${value}%`, height: "100%", background: color, transition: "width 0.5s" }} />
    </div>
  );
}
