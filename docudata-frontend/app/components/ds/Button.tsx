import Link from "next/link";
import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";
import { ds } from "../../lib/ds";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "active";
export type ButtonSize = "md" | "sm" | "hero";

const VARIANTS: Record<ButtonVariant, CSSProperties> = {
  primary: { background: ds.green, color: "#04120a", border: `1px solid ${ds.green}`, boxShadow: "0 0 24px rgba(62, 224, 111, 0.25)" },
  secondary: { background: "rgba(255, 255, 255, 0.04)", color: ds.text, border: `1px solid ${ds.borderStrong}` },
  ghost: { background: "transparent", color: ds.text2, border: "1px solid transparent" },
  danger: { background: "transparent", color: ds.red, border: `1px solid ${ds.redLine}` },
  active: { background: ds.greenSoft, color: ds.green, border: `1px solid ${ds.greenLine}` },
};

const SIZES: Record<ButtonSize, CSSProperties> = {
  md: { height: 38, padding: "0 16px", borderRadius: 10, fontSize: 13.5 },
  sm: { height: 32, padding: "0 12px", borderRadius: 10, fontSize: 12.5 },
  hero: { height: 64, padding: "0 24px", borderRadius: 14, fontSize: 17, fontWeight: 700, width: "100%", boxShadow: "0 0 40px rgba(62, 224, 111, 0.3)" },
};

const BASE: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 8,
  fontFamily: "inherit",
  fontWeight: 600,
  whiteSpace: "nowrap",
};

export function buttonStyle(variant: ButtonVariant = "secondary", size: ButtonSize = "md", extra?: CSSProperties): CSSProperties {
  return { ...BASE, ...VARIANTS[variant], ...SIZES[size], ...extra };
}

export function buttonClass(variant: ButtonVariant = "secondary"): string {
  return `ds-btn ds-btn-${variant}`;
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  children?: ReactNode;
}

export default function Button({ variant = "secondary", size = "md", style, type = "button", className, ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      className={`${buttonClass(variant)} ${className ?? ""}`.trim()}
      style={buttonStyle(variant, size, style)}
      {...rest}
    />
  );
}

interface ButtonLinkProps {
  href: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  style?: CSSProperties;
  children?: ReactNode;
}

export function ButtonLink({ href, variant = "secondary", size = "md", style, children }: ButtonLinkProps) {
  return (
    <Link href={href} className={buttonClass(variant)} style={buttonStyle(variant, size, style)}>
      {children}
    </Link>
  );
}
