import type { CSSProperties, ReactNode } from "react";
import { ds, labelStyle } from "../../lib/ds";

export function SectionLabel({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return <span style={{ ...labelStyle, ...style }}>{children}</span>;
}

/** Eyebrow verde com traço de 18×2px antes do texto. */
export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span aria-hidden="true" style={{ width: 18, height: 2, background: ds.green }} />
      <span style={{ ...labelStyle, color: ds.green }}>{children}</span>
    </div>
  );
}

interface TabSectionHeadProps {
  title: string;
  /** Contagem em mono ao lado do título (ex.: "2 sprints"). */
  count?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

/** Cabeçalho de seção dentro de uma aba do projeto: título 28px, contagem mono, descrição e ações. */
export function TabSectionHead({ title, count, description, actions }: TabSectionHeadProps) {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 760, minWidth: 0, flex: "1 1 320px" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color: ds.white }}>{title}</h2>
          {count != null && <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{count}</span>}
        </div>
        {description && <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: ds.muted, textWrap: "pretty" }}>{description}</p>}
      </div>
      {actions && <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>{actions}</div>}
    </div>
  );
}

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /** H1 menor (38px) para páginas de projeto. */
  compact?: boolean;
}

export function PageHeader({ eyebrow, title, subtitle, actions, compact = false }: PageHeaderProps) {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, minWidth: 0, flex: "1 1 360px" }}>
        {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
        <h1 style={{ fontSize: compact ? 38 : 44, lineHeight: 1.05, fontWeight: 700, letterSpacing: "-0.035em", color: ds.white }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 15.5, lineHeight: 1.55, color: ds.muted, textWrap: "pretty" }}>{subtitle}</p>}
      </div>
      {actions && <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>{actions}</div>}
    </div>
  );
}
