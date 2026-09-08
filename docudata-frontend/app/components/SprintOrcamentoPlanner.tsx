"use client";

import { useState } from "react";
import { SprintWithStatus, createSprint, updateSprintOrcamento } from "../lib/api";

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
  onSprintUpdated: (updated: SprintWithStatus) => void;
  onSprintCreated: (created: SprintWithStatus) => void;
}

export default function SprintOrcamentoPlanner({ projectId, sprints, onSprintUpdated, onSprintCreated }: Props) {
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [errBySprint, setErrBySprint] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [createErr, setCreateErr] = useState("");

  async function handleCriarSprint() {
    setCreating(true);
    setCreateErr("");
    try {
      const nova = await createSprint(projectId, undefined, false);
      onSprintCreated({
        ...nova,
        tem_planning: false,
        tem_review: false,
        dailys_count: 0,
        ingestions_count: 0,
        docs_gerados_count: 0,
        pendencias: [],
        pontos_orcamento: null,
        pontos_usados: 0,
        faturamento_previsto: null,
        avaliacao_completa_em: null,
      });
    } catch (err) {
      setCreateErr(err instanceof Error ? err.message : "Erro ao criar sprint.");
    } finally {
      setCreating(false);
    }
  }

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
        <p style={{ fontSize: 13, color: "#9696a0", margin: "0 0 14px" }}>
          Planeje aqui o projeto inteiro: crie as sprints que você já sabe que vai ter e
          distribua os 100 pontos entre elas, sem precisar esperar a semana chegar.
        </p>
        <button
          onClick={handleCriarSprint}
          disabled={creating}
          style={{
            background: "#0f172a", color: "#fff", border: "none", borderRadius: 8,
            padding: "8px 16px", fontSize: 13, fontWeight: 700, cursor: "pointer",
            opacity: creating ? 0.6 : 1,
          }}
        >
          {creating ? "Criando…" : "+ Nova sprint"}
        </button>
        {createErr && <p style={{ fontSize: 12, color: "#dc2626", marginTop: 8 }}>{createErr}</p>}
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
      <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid #f0f0f4" }}>
        <button
          onClick={handleCriarSprint}
          disabled={creating}
          style={{
            background: "none", border: "1px solid #e4e4ea", borderRadius: 8,
            padding: "6px 14px", fontSize: 12, fontWeight: 700, color: "#374151", cursor: "pointer",
            opacity: creating ? 0.6 : 1,
          }}
        >
          {creating ? "Criando…" : "+ Nova sprint"}
        </button>
        {createErr && <span style={{ fontSize: 12, color: "#dc2626", marginLeft: 10 }}>{createErr}</span>}
      </div>
    </div>
  );
}
