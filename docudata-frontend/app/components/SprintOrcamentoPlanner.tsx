"use client";

import { useState } from "react";
import { SprintWithStatus, updateSprintOrcamento } from "../lib/api";

interface Props {
  sprints: SprintWithStatus[];
  onSprintUpdated: (updated: SprintWithStatus) => void;
}

export default function SprintOrcamentoPlanner({ sprints, onSprintUpdated }: Props) {
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [errBySprint, setErrBySprint] = useState<Record<string, string>>({});

  const totalAlocado = sprints.reduce((acc, s) => acc + (s.pontos_orcamento ?? 0), 0);

  async function handleSalvar(sprint: SprintWithStatus) {
    const raw = inputs[sprint.id] ?? String(sprint.pontos_orcamento ?? "");
    const valor = parseInt(raw, 10);
    if (isNaN(valor) || valor < 0) {
      setErrBySprint((e) => ({ ...e, [sprint.id]: "Informe um número válido." }));
      return;
    }
    setSavingId(sprint.id);
    setErrBySprint((e) => ({ ...e, [sprint.id]: "" }));
    try {
      const updated = await updateSprintOrcamento(sprint.id, valor);
      onSprintUpdated(updated);
    } catch (err) {
      setErrBySprint((e) => ({
        ...e,
        [sprint.id]: err instanceof Error ? err.message : "Erro ao salvar orçamento.",
      }));
    } finally {
      setSavingId(null);
    }
  }

  if (sprints.length === 0) {
    return (
      <div style={{ background: "#fff", border: "1px solid #e8e8ed", borderRadius: 14, padding: "20px 24px", marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", margin: "0 0 8px" }}>Orçamento de pontos por sprint</h3>
        <p style={{ fontSize: 13, color: "#9696a0", margin: 0 }}>
          Nenhuma sprint criada ainda. Crie sprints na aba Sprints antes de distribuir os pontos.
        </p>
      </div>
    );
  }

  return (
    <div style={{ background: "#fff", border: "1px solid #e8e8ed", borderRadius: 14, padding: "20px 24px", marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", margin: 0 }}>Orçamento de pontos por sprint</h3>
        <span style={{ fontSize: 13, fontWeight: 700, color: totalAlocado > 100 ? "#dc2626" : "#4338ca" }}>
          {totalAlocado}/100 pontos alocados
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {sprints.map((s) => (
          <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#111116", width: 90 }}>Sprint {s.numero}</span>
            <input
              type="number"
              min={0}
              value={inputs[s.id] ?? (s.pontos_orcamento != null ? String(s.pontos_orcamento) : "")}
              onChange={(e) => setInputs((i) => ({ ...i, [s.id]: e.target.value }))}
              placeholder="0"
              style={{ width: 80, padding: "6px 10px", border: "1px solid #e4e4ea", borderRadius: 7, fontSize: 13 }}
            />
            <button
              onClick={() => handleSalvar(s)}
              disabled={savingId === s.id}
              style={{
                background: "#0f172a", color: "#fff", border: "none", borderRadius: 8,
                padding: "6px 14px", fontSize: 12, fontWeight: 700, cursor: "pointer",
                opacity: savingId === s.id ? 0.6 : 1,
              }}
            >
              {savingId === s.id ? "…" : "Salvar"}
            </button>
            <span style={{ fontSize: 12, color: "#9696a0" }}>{s.pontos_usados} pts já usados em tasks</span>
            {errBySprint[s.id] && <span style={{ fontSize: 12, color: "#dc2626" }}>{errBySprint[s.id]}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
