import type { ReactNode } from "react";
import { ds, labelStyle } from "../../lib/ds";
import { Card } from "../ds";

/** Cartão do Painel: rótulo mono no topo, ação opcional à direita (protótipo 05). */
export function PanelCard({ label, action, children }: { label: string; action?: ReactNode; children: ReactNode }) {
  return (
    <Card>
      <div style={{ padding: "24px 26px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <span style={labelStyle}>{label}</span>
          {action}
        </div>
        {children}
      </div>
    </Card>
  );
}

/** Número grande (44px) com unidade ao lado, como nos indicadores do protótipo. */
export function BigNumber({ value, unit, color = ds.white }: { value: ReactNode; unit?: ReactNode; color?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
      <span style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.03em", color, lineHeight: 1 }}>{value}</span>
      {unit && <span style={{ fontSize: 13, color: ds.muted }}>{unit}</span>}
    </div>
  );
}

/** Indicador com legenda curta acima do número grande. */
export function Metric({ caption, value, unit, color }: { caption: string; value: ReactNode; unit?: ReactNode; color?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ fontSize: 13, color: ds.text2 }}>{caption}</span>
      <BigNumber value={value} unit={unit} color={color} />
    </div>
  );
}

export function Muted({ children, small = false }: { children: ReactNode; small?: boolean }) {
  return <p style={{ margin: 0, fontSize: small ? 12.5 : 14, lineHeight: 1.55, color: ds.muted, textWrap: "pretty" }}>{children}</p>;
}

/** Botão de texto discreto usado como ação do cabeçalho do cartão. */
export function CardTextAction({ onClick, children, expanded }: { onClick: () => void; children: ReactNode; expanded?: boolean }) {
  return (
    <button
      type="button"
      className="ds-text-btn"
      aria-expanded={expanded}
      onClick={onClick}
      style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13, fontWeight: 600, color: ds.text2 }}
    >
      {children}
    </button>
  );
}

/** Formata número no padrão brasileiro (vírgula decimal), com até 1 casa. */
export function fmtNum(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}
