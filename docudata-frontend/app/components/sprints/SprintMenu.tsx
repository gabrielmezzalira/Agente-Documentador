"use client";

import { useEffect, useRef, useState } from "react";
import { ds, cardStyle } from "../../lib/ds";

export interface SprintMenuAction {
  label: string;
  onSelect: () => void;
  danger?: boolean;
  disabled?: boolean;
  title?: string;
}

/** Botão "···" do card de sprint com as ações secundárias (upload livre, reabrir, excluir). */
export default function SprintMenu({ actions, sprintNumero }: { actions: SprintMenuAction[]; sprintNumero: number }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        className="ds-text-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Mais ações da Sprint ${sprintNumero}`}
        onClick={() => setOpen((v) => !v)}
        style={{ background: "none", border: "none", cursor: "pointer", padding: "0 2px", fontSize: 18, lineHeight: 1, color: ds.muted, fontFamily: "inherit" }}
      >
        ···
      </button>
      {open && (
        <div
          role="menu"
          style={{ ...cardStyle, position: "absolute", right: 0, top: "calc(100% + 8px)", zIndex: 20, minWidth: 210, padding: 6, display: "flex", flexDirection: "column" }}
        >
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              role="menuitem"
              className="ds-row-link"
              disabled={a.disabled}
              title={a.title}
              onClick={() => { setOpen(false); a.onSelect(); }}
              style={{
                textAlign: "left", background: "none", border: "none", borderRadius: 8, padding: "9px 12px",
                fontSize: 13.5, fontWeight: 500, fontFamily: "inherit",
                color: a.danger ? ds.red : ds.text2, cursor: a.disabled ? "default" : "pointer", opacity: a.disabled ? 0.5 : 1,
              }}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
