"use client";

import { useState } from "react";
import { ds } from "../../lib/ds";

/** Ícone "i" com a explicação da métrica ao passar o mouse ou focar pelo teclado.
 *  `align` diz para que lado o balão abre: "right" ancora na borda direita do ícone
 *  (cabeçalho de cartão), "left" na esquerda (legenda de métrica no início da linha). */
export default function InfoTip({ text, align = "right" }: { text: string; align?: "left" | "right" }) {
  const [show, setShow] = useState(false);
  return (
    <span style={{ position: "relative", display: "inline-flex", verticalAlign: "middle" }}>
      <button
        type="button"
        aria-label="O que significa"
        aria-expanded={show}
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onFocus={() => setShow(true)}
        onBlur={() => setShow(false)}
        style={{ cursor: "help", fontSize: 10, color: ds.muted, fontWeight: 700, background: "none", border: `1px solid ${ds.borderStrong}`, borderRadius: "50%", width: 16, height: 16, display: "inline-flex", alignItems: "center", justifyContent: "center", padding: 0, fontFamily: "inherit" }}
      >
        i
      </button>
      {show && (
        <span role="tooltip" style={{
          position: "absolute", [align]: 0, top: 22, zIndex: 100,
          background: ds.cardTop, color: ds.text2, border: `1px solid ${ds.greenLine}`, fontSize: 12, lineHeight: 1.55,
          borderRadius: 10, padding: "10px 12px", width: 280, maxWidth: "calc(100vw - 32px)", whiteSpace: "normal", textTransform: "none", letterSpacing: 0, fontWeight: 400, fontFamily: ds.fontSans,
          boxShadow: "0 12px 32px rgba(0,0,0,0.45)",
        }}>
          {text}
        </span>
      )}
    </span>
  );
}
