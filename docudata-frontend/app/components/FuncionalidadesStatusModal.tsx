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
  background: "#fff",
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
  borderBottom: "1px solid #f0f0f6",
  gap: 12,
};

const funcTitle: CSSProperties = {
  fontSize: 13,
  color: "#1e293b",
  fontWeight: 600,
  lineHeight: 1.4,
};

const funcCode: CSSProperties = {
  fontSize: 11,
  color: "#94a3b8",
  marginTop: 2,
};

const toggleBtn = (active: boolean, color: "green" | "amber"): CSSProperties => ({
  padding: "6px 14px",
  borderRadius: 8,
  fontSize: 12,
  fontWeight: 700,
  border: "1px solid",
  cursor: "pointer",
  background: active ? (color === "green" ? "#dcfce7" : "#fef3c7") : "#f8fafc",
  color: active ? (color === "green" ? "#16a34a" : "#b45309") : "#94a3b8",
  borderColor: active ? (color === "green" ? "#86efac" : "#fde68a") : "#e2e8f0",
  transition: "all 0.1s",
});

const btnPrimary: CSSProperties = {
  background: "#0f172a",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  padding: "10px 20px",
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
};

const btnSecondary: CSSProperties = {
  background: "#f1f5f9",
  color: "#1e293b",
  border: "1px solid #e2e8f0",
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
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0f172a", margin: "0 0 4px", letterSpacing: "-0.02em" }}>
              Status das Funcionalidades
            </h2>
            <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
              Sprint {sprintNumero} — marque o que foi concluído nesta sprint.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", fontSize: 20, color: "#94a3b8", cursor: "pointer" }}
          >
            ×
          </button>
        </div>

        {loading && (
          <p style={{ fontSize: 13, color: "#64748b", padding: "20px 0", textAlign: "center" }}>
            Carregando…
          </p>
        )}

        {!loading && items.length === 0 && !error && (
          <p style={{ fontSize: 13, color: "#94a3b8", padding: "20px 0", textAlign: "center" }}>
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
          <p style={{ color: "#dc2626", fontSize: 13, marginTop: 12 }}>{error}</p>
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
