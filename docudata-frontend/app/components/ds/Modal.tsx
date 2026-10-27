"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { cardStyle, ds } from "../../lib/ds";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}

/** Diálogo modal no tema escuro. Esc e clique fora fecham; o foco vai para o botão de fechar ao abrir. */
export default function Modal({ title, onClose, children, footer, width = 720 }: ModalProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  // Guarda o onClose mais recente sem refazer o efeito: um pai que passa função inline não rouba o foco a cada render.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onCloseRef.current(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0, 0, 0, 0.7)", backdropFilter: "blur(4px)", padding: 16 }}
    >
      <div role="dialog" aria-modal="true" aria-label={title} style={{ ...cardStyle, width: "100%", maxWidth: width, maxHeight: "90vh", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", borderBottom: `1px solid ${ds.border}` }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: ds.white }}>{title}</span>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Fechar" style={{ background: "none", border: "none", color: ds.muted, fontSize: 20, cursor: "pointer", lineHeight: 1, padding: 4 }}>×</button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>{children}</div>
        {footer && <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, padding: "16px 24px", borderTop: `1px solid ${ds.border}` }}>{footer}</div>}
      </div>
    </div>
  );
}
