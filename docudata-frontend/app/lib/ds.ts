import type { CSSProperties } from "react";

/**
 * Tokens do design system CITi (tema escuro) — espelham o DESIGN.md.
 * Use estes valores em estilos inline; os mesmos existem como variáveis CSS em globals.css.
 */
export const ds = {
  bg: "#030504",
  sidebar: "#070b09",
  cardTop: "#0e1913",
  cardBottom: "#0a120d",
  inner: "rgba(62, 224, 111, 0.055)",
  innerBorder: "rgba(62, 224, 111, 0.17)",
  border: "rgba(255, 255, 255, 0.08)",
  borderStrong: "rgba(255, 255, 255, 0.14)",
  text: "#f2f5f3",
  white: "#ffffff",
  text2: "#c3cbc6",
  muted: "#8a948e",
  dim: "#5d6661",
  green: "#3ee06f",
  greenHover: "#7cf0a0",
  greenSoft: "rgba(62, 224, 111, 0.12)",
  greenLine: "rgba(62, 224, 111, 0.35)",
  red: "#ff6b6b",
  redSoft: "rgba(255, 107, 107, 0.10)",
  redLine: "rgba(255, 107, 107, 0.30)",
  amber: "#f2c14e",
  amberSoft: "rgba(242, 193, 78, 0.10)",
  amberLine: "rgba(242, 193, 78, 0.30)",
  violet: "#b197fc",
  violetSoft: "rgba(177, 151, 252, 0.10)",
  violetLine: "rgba(177, 151, 252, 0.30)",
  chartGrey: "#4a5550",
  fontSans: "'Geist', system-ui, -apple-system, 'Segoe UI', sans-serif",
  fontMono: "'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace",
} as const;

export type Tone = "neutral" | "green" | "red" | "amber" | "violet";

export const toneColors: Record<Tone, { fg: string; bg: string; line: string }> = {
  neutral: { fg: ds.text2, bg: "rgba(255, 255, 255, 0.05)", line: ds.border },
  green: { fg: ds.green, bg: ds.greenSoft, line: ds.greenLine },
  red: { fg: ds.red, bg: ds.redSoft, line: ds.redLine },
  amber: { fg: ds.amber, bg: ds.amberSoft, line: ds.amberLine },
  violet: { fg: ds.violet, bg: ds.violetSoft, line: ds.violetLine },
};

/** Cartão padrão: gradiente verde escuro, contorno verde, brilho interno e sombra. */
export const cardStyle: CSSProperties = {
  background: `linear-gradient(180deg, ${ds.cardTop} 0%, ${ds.cardBottom} 100%)`,
  border: "1px solid rgba(62, 224, 111, 0.2)",
  borderRadius: 16,
  boxShadow: "inset 0 1px 0 rgba(62, 224, 111, 0.12), 0 12px 32px rgba(0, 0, 0, 0.45)",
};

/** Item/entrada dentro de um cartão. */
export const innerStyle: CSSProperties = {
  background: ds.inner,
  border: `1px solid ${ds.innerBorder}`,
  borderRadius: 12,
};

/** Rótulo de seção: mono 11px, caixa alta, tracking 0.16em. */
export const labelStyle: CSSProperties = {
  fontFamily: ds.fontMono,
  fontSize: 11,
  letterSpacing: "0.16em",
  textTransform: "uppercase",
  color: ds.muted,
  fontWeight: 500,
};
