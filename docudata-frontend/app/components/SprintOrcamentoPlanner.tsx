"use client";

import { useState } from "react";
import { SprintWithStatus, createSprint, updateSprintOrcamento } from "../lib/api";
import { ds, labelStyle } from "../lib/ds";
import { Button, Card, Input, ProgressBar } from "./ds";

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
        avaliados_count: 0,
        elegiveis_avaliacao_count: 0,
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

  // Mais recente primeiro, como no protótipo 04.
  const ordenadas = [...sprints].sort((a, b) => b.numero - a.numero);
  const excedeu = totalAlocado > 100;

  return (
    <Card>
      <div className="ds-orcamento-grid" style={{ padding: "26px 28px", display: "grid", gridTemplateColumns: "minmax(0,1fr) 280px", gap: 40 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
          <span style={labelStyle}>Orçamento de pontos por sprint</span>
          {ordenadas.length === 0 && (
            <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: ds.muted }}>
              Planeje aqui o projeto inteiro: crie as sprints que você já sabe que vai ter e distribua os 100 pontos entre elas, sem precisar esperar a semana chegar.
            </p>
          )}
          {ordenadas.map((s) => (
            <div key={s.id} style={{ display: "grid", gridTemplateColumns: "110px 140px auto 1fr", gap: 14, alignItems: "center" }}>
              <label htmlFor={`orc-${s.id}`} style={{ fontSize: 14.5, fontWeight: 600, color: ds.white }}>Sprint {s.numero}</label>
              <Input
                id={`orc-${s.id}`}
                type="number"
                min={0}
                inputMode="numeric"
                value={inputs[s.id] ?? (s.pontos_orcamento != null ? String(s.pontos_orcamento) : "")}
                onChange={(e) => setInputs((i) => ({ ...i, [s.id]: e.target.value }))}
                placeholder="0"
                style={{ width: 140, height: 40, fontSize: 13.5 }}
              />
              <Button variant="secondary" onClick={() => handleSalvar(s)} disabled={savingId === s.id}>
                {savingId === s.id ? "Salvando…" : "Salvar"}
              </Button>
              <span style={{ fontSize: 13, color: errBySprint[s.id] ? ds.red : ds.muted }}>
                {errBySprint[s.id] || `${s.pontos_usados} pts já usados em tasks`}
              </span>
            </div>
          ))}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Button variant="secondary" onClick={handleCriarSprint} disabled={creating}>
              {creating ? "Criando…" : "+ Nova sprint"}
            </Button>
            {createErr && <span style={{ fontSize: 12.5, color: ds.red }}>{createErr}</span>}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, paddingLeft: 32, borderLeft: `1px solid ${ds.border}` }}>
          <span style={labelStyle}>Pontos alocados</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.03em", color: excedeu ? ds.red : ds.white, lineHeight: 1 }}>{totalAlocado}</span>
            <span style={{ fontFamily: ds.fontMono, fontSize: 14, color: ds.muted }}>/ 100</span>
          </div>
          <ProgressBar pct={totalAlocado} tone={excedeu ? "red" : "green"} label="Pontos alocados de 100" />
          <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.55, color: excedeu ? ds.red : ds.muted, textWrap: "pretty" }}>
            {excedeu
              ? "A soma passou de 100 pontos. Reduza o orçamento de alguma sprint."
              : "Todo projeto vale 100 pontos. Distribua entre as sprints para liberar o SPI."}
          </p>
        </div>
      </div>
    </Card>
  );
}
