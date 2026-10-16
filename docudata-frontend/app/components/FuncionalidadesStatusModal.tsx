"use client";

import { useEffect, useState, type CSSProperties } from "react";
import {
  getSprintFuncionalidades,
  updateSprintFuncionalidade,
  type SprintFuncionalidade,
} from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  sprintId: string;
  sprintNumero: number;
  onUpdated?: () => void;
}

// ---------- styles ----------

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1100,
  padding: 16,
};

const modal: CSSProperties = {
  background: "#0d1711",
  borderRadius: 14,
  width: "100%",
  maxWidth: 480,
  maxHeight: "80vh",
  overflowY: "auto",
  padding: 24,
  boxShadow: "0 20px 60px rgba(15, 23, 42, 0.25)",
};

const row: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "12px 0",
  borderBottom: "1px solid rgba(255,255,255,0.08)",
  gap: 12,
};

const funcTitle: CSSProperties = {
  fontSize: 13,
  color: "#f2f5f3",
  fontWeight: 600,
  lineHeight: 1.4,
};

const funcCode: CSSProperties = {
  fontSize: 11,
  color: "#8a948e",
  marginTop: 2,
};

const toggleBtn = (active: boolean, color: "green" | "amber"): CSSProperties => ({
  padding: "6px 14px",
  borderRadius: 8,
  fontSize: 12,
  fontWeight: 700,
  border: "1px solid",
  cursor: "pointer",
  background: active ? (color === "green" ? "rgba(62,224,111,0.12)" : "rgba(242,193,78,0.10)") : "rgba(62,224,111,0.055)",
  color: active ? (color === "green" ? "#3ee06f" : "#f2c14e") : "#8a948e",
  borderColor: active ? (color === "green" ? "rgba(62,224,111,0.35)" : "rgba(242,193,78,0.30)") : "rgba(62,224,111,0.2)",
  transition: "all 0.1s",
});

const btnPrimary: CSSProperties = {
  background: "#3ee06f",
  color: "#04120a",
  border: "none",
  borderRadius: 10,
  padding: "10px 20px",
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
};

const btnSecondary: CSSProperties = {
  background: "rgba(62,224,111,0.055)",
  color: "#f2f5f3",
  border: "1px solid rgba(62,224,111,0.2)",
  borderRadius: 10,
  padding: "10px 16px",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
};

// ---------- component ----------

export default function FuncionalidadesStatusModal({
  open,
  onClose,
  sprintId,
  sprintNumero,
  onUpdated,
}: Props) {
  const [items, setItems] = useState<SprintFuncionalidade[]>([]);
  const [statuses, setStatuses] = useState<Record<string, "em_andamento" | "concluida">>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !sprintId) return;
    setLoading(true);
    setError("");
    getSprintFuncionalidades(sprintId)
      .then((data) => {
        setItems(data);
        const init: Record<string, "em_andamento" | "concluida"> = {};
        data.forEach((sf) => { init[sf.id] = sf.status; });
        setStatuses(init);
      })
      .catch(() => setError("Não foi possível carregar as funcionalidades desta sprint."))
      .finally(() => setLoading(false));
  }, [open, sprintId]);

  useEffect(() => {
    if (!open) {
      setItems([]);
      setStatuses({});
      setError("");
    }
  }, [open]);

  if (!open) return null;

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      await Promise.all(
        items
          .filter((sf) => statuses[sf.id] !== sf.status)
          .map((sf) => updateSprintFuncionalidade(sf.id, { status: statuses[sf.id] }))
      );
      onUpdated?.();
      onClose();
    } catch {
      setError("Erro ao salvar status. Tente novamente.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={modal}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#f2f5f3", margin: "0 0 4px", letterSpacing: "-0.02em" }}>
              Status das Funcionalidades
            </h2>
            <p style={{ fontSize: 13, color: "#8a948e", margin: 0 }}>
              Sprint {sprintNumero} — marque o que foi concluído nesta sprint.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", fontSize: 20, color: "#8a948e", cursor: "pointer" }}
          >
            ×
          </button>
        </div>

        {loading && (
          <p style={{ fontSize: 13, color: "#8a948e", padding: "20px 0", textAlign: "center" }}>
            Carregando…
          </p>
        )}

        {!loading && items.length === 0 && !error && (
          <p style={{ fontSize: 13, color: "#8a948e", padding: "20px 0", textAlign: "center" }}>
            Nenhuma funcionalidade associada a esta sprint. Use o botão de Planning para vincular funcionalidades.
          </p>
        )}

        {!loading && items.map((sf) => {
          const func = sf.funcionalidades;
          return (
            <div key={sf.id} style={row}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={funcTitle}>{func?.titulo ?? "—"}</div>
                {func?.id_funcional && <div style={funcCode}>{func.id_funcional}</div>}
              </div>
              <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                <button
                  style={toggleBtn(statuses[sf.id] === "em_andamento", "amber")}
                  onClick={() => setStatuses((prev) => ({ ...prev, [sf.id]: "em_andamento" }))}
                >
                  Em andamento
                </button>
                <button
                  style={toggleBtn(statuses[sf.id] === "concluida", "green")}
                  onClick={() => setStatuses((prev) => ({ ...prev, [sf.id]: "concluida" }))}
                >
                  Concluída ✓
                </button>
              </div>
            </div>
          );
        })}

        {error && (
          <p style={{ color: "#ff6b6b", fontSize: 13, marginTop: 12 }}>{error}</p>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
          <button style={btnSecondary} onClick={onClose}>Pular</button>
          {items.length > 0 && (
            <button
              style={{ ...btnPrimary, opacity: saving ? 0.7 : 1 }}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Salvando…" : "Salvar status"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
