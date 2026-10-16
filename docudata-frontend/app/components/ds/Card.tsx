import type { CSSProperties, HTMLAttributes } from "react";
import { cardStyle, ds } from "../../lib/ds";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  highlight?: boolean;
  style?: CSSProperties;
}

/** Cartão padrão do design system. `highlight` deixa o fundo verde translúcido (avisos e destaques). */
export default function Card({ highlight = false, style, ...rest }: CardProps) {
  return (
    <div
      style={{
        ...cardStyle,
        ...(highlight ? { background: "rgba(62, 224, 111, 0.06)", borderColor: ds.greenLine } : null),
        ...style,
      }}
      {...rest}
    />
  );
}
