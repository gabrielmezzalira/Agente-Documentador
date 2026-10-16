import type { ReactNode } from "react";
import { ds } from "../../lib/ds";

export interface BarSeries {
  key: string;
  label: string;
  color: string;
  values: number[];
}

/** Topo "redondo" do eixo Y: 4 divisões inteiras que cobrem o maior valor (ex.: 29 → 32, 17 → 20). */
function eixo(max: number): number[] {
  const passo = Math.max(1, Math.ceil(max / 4));
  return [4, 3, 2, 1, 0].map((i) => i * passo);
}

/**
 * Gráfico de barras agrupadas no estilo do protótipo 07: barras com topo arredondado,
 * valor em mono acima de cada barra, eixo Y apagado à esquerda e rótulos curtos embaixo.
 */
export function BarGroups({ categories, series, height = 190, label }: { categories: string[]; series: BarSeries[]; height?: number; label: string }) {
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const ticks = eixo(max);
  const topo = ticks[0];
  return (
    <figure role="img" aria-label={label} style={{ margin: 0, display: "flex", gap: 10 }}>
      <div aria-hidden="true" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", height, fontFamily: ds.fontMono, fontSize: 10.5, color: ds.dim, textAlign: "right", width: 24 }}>
        {ticks.map((t) => <span key={t}>{t}</span>)}
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
        <div style={{ height, display: "flex", alignItems: "flex-end", gap: 20, borderBottom: `1px solid ${ds.borderStrong}`, padding: "0 12px" }}>
          {categories.map((cat, ci) => (
            <div key={cat} style={{ flex: 1, display: "flex", alignItems: "flex-end", justifyContent: "center", gap: 6, height: "100%", minWidth: 0 }}>
              {series.map((s) => {
                const v = s.values[ci] ?? 0;
                return (
                  <div
                    key={s.key}
                    title={`${s.label}: ${v}`}
                    style={{ flex: 1, maxWidth: 76, height: `${(v / topo) * 100}%`, background: s.color, borderRadius: "6px 6px 0 0", position: "relative" }}
                  >
                    <span style={{ position: "absolute", top: -19, left: 0, right: 0, textAlign: "center", fontFamily: ds.fontMono, fontSize: 11, color: ds.text2 }}>
                      {Number.isInteger(v) ? v : v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div aria-hidden="true" style={{ display: "flex", gap: 20, padding: "0 12px" }}>
          {categories.map((cat) => (
            <span key={cat} style={{ flex: 1, textAlign: "center", fontFamily: ds.fontMono, fontSize: 11.5, color: ds.muted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{cat}</span>
          ))}
        </div>
      </div>
    </figure>
  );
}

/** Legenda com quadradinhos de cor, como no protótipo. */
export function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12.5, color: ds.text2 }}>
      {items.map((i) => (
        <span key={i.label} style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 3, background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}

export function ChartEmpty({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, padding: "30px 0", textAlign: "center" }}>
      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: ds.muted }}>{children}</p>
      {action}
    </div>
  );
}
