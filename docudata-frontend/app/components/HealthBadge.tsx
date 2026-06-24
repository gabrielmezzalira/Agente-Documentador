"use client";

import { useEffect, useRef, useState } from "react";
import { updateSprintHealth, type SprintHealth } from "../lib/api";

interface Props {
  sprintId: string;
  value: SprintHealth | null | undefined;
  planoCorrecao?: string | null;
  onChanged: () => void;
}

const META: Record<SprintHealth | "null", { emoji: string; label: string; bg: string; color: string }> = {
  verde: { emoji: "🟢", label: "Verde", bg: "#dcfce7", color: "#16a34a" },
  amarelo: { emoji: "🟡", label: "Amarelo", bg: "#fef3c7", color: "#b45309" },
  vermelho: { emoji: "🔴", label: "Vermelho", bg: "#fee2e2", color: "#b91c1c" },
  null: { emoji: "⚪", label: "Sem status", bg: "#f7f7fa", color: "#6a6a7a" },
};

const badgeBase: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "4px 10px",
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 700,
  cursor: "pointer",
  border: "1px solid transparent",
};

const popoverStyle: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  right: 0,
  marginTop: 6,
  background: "#fff",
  border: "1px solid #e4e4ea",
  borderRadius: 10,
  padding: 14,
  width: 280,
  boxShadow: "0 12px 32px rgba(15, 23, 42, 0.12)",
  zIndex: 50,
};

export default function HealthBadge({ sprintId, value, planoCorrecao, onChanged }: Props) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<SprintHealth | null>(value ?? null);
  const [plano, setPlano] = useState(planoCorrecao ?? "");
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setDraft(value ?? null);
    setPlano(planoCorrecao ?? "");
  }, [value, planoCorrecao]);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const meta = META[value ?? "null"];

  async function save() {
    setSaving(true);
    try {
      await updateSprintHealth(sprintId, draft, plano || null);
      onChanged();
      setOpen(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{ ...badgeBase, background: meta.bg, color: meta.color }}
        title="Clique para editar o semáforo"
      >
        <span>{meta.emoji}</span>
        <span>{meta.label}</span>
      </button>

      {open && (
        <div style={popoverStyle} onClick={(e) => e.stopPropagation()}>
          <p style={{ fontSize: 11, fontWeight: 700, color: "#6a6a7a", textTransform: "uppercase", letterSpacing: "0.06em", margin: 0, marginBottom: 8 }}>
            Saúde da sprint
          </p>
          <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
            {(["verde", "amarelo", "vermelho"] as SprintHealth[]).map((opt) => {
              const m = META[opt];
              const selected = draft === opt;
              return (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setDraft(opt)}
                  style={{
                    flex: 1,
                    padding: "8px 6px",
                    background: selected ? m.bg : "#f7f7fa",
                    border: selected ? `1.5px solid ${m.color}` : "1px solid #e4e4ea",
                    borderRadius: 8,
                    cursor: "pointer",
                    fontSize: 12,
                    fontWeight: selected ? 700 : 500,
                    color: selected ? m.color : "#6a6a7a",
                  }}
                >
                  {m.emoji} {m.label}
                </button>
              );
            })}
          </div>
          {draft === "amarelo" || draft === "vermelho" ? (
            <>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#6a6a7a", marginBottom: 4 }}>
                Plano de correção
              </label>
              <textarea
                value={plano}
                onChange={(e) => setPlano(e.target.value)}
                placeholder="Como esse desvio será corrigido?"
                rows={3}
                style={{
                  width: "100%",
                  padding: 8,
                  border: "1px solid #e4e4ea",
                  borderRadius: 8,
                  fontSize: 13,
                  resize: "vertical",
                  fontFamily: "inherit",
                  boxSizing: "border-box",
                  outline: "none",
                }}
              />
            </>
          ) : null}
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginTop: 10 }}>
            <button
              type="button"
              onClick={() => { setDraft(null); setPlano(""); }}
              style={{ background: "transparent", border: "none", fontSize: 12, color: "#9696a0", cursor: "pointer" }}
            >
              Limpar
            </button>
            <button
              type="button"
              onClick={save}
              disabled={saving}
              style={{
                background: "#4ade80",
                color: "#052e16",
                border: "none",
                padding: "6px 14px",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
                opacity: saving ? 0.6 : 1,
              }}
            >
              {saving ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
