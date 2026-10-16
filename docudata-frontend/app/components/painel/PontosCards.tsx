"use client";

import { useEffect, useState } from "react";
import {
  getElegiveis, getExtratoPontos,
  type ElegivelPonto, type OperacionalResponse, type PontuacaoEvento, type SprintWithStatus,
} from "../../lib/api";
import { ds, labelStyle } from "../../lib/ds";
import { Chip, Select } from "../ds";
import { PanelCard } from "./PanelCard";

const dashedBox: React.CSSProperties = {
  padding: "28px 12px", border: `1px dashed ${ds.borderStrong}`, borderRadius: 12,
  textAlign: "center", fontSize: 13, color: ds.dim,
};

const ROTULO_TIPO: Record<PontuacaoEvento["tipo"], string> = {
  entrega_concluida: "Entrega concluída",
  travamento_penalidade: "Travamento (penalidade)",
  devolucao_penalidade: "Devolução após travamento (penalidade)",
  bonus_extra: "Bônus de task extra",
  reabertura: "Reabertura",
};

/** Tabela em grade (linhas com divisória), no lugar de <table> com bordas. */
function GridTable({ columns, template, rows }: { columns: string[]; template: string; rows: React.ReactNode[][] }) {
  return (
    <div role="table" style={{ display: "flex", flexDirection: "column" }}>
      <div role="row" style={{ display: "grid", gridTemplateColumns: template, gap: 12, padding: "10px 16px", borderBottom: `1px solid ${ds.border}` }}>
        {columns.map((c) => <span key={c} role="columnheader" style={labelStyle}>{c}</span>)}
      </div>
      {rows.map((cells, i) => (
        <div key={i} role="row" style={{ display: "grid", gridTemplateColumns: template, gap: 12, alignItems: "center", padding: "14px 16px", borderTop: i > 0 ? `1px solid ${ds.border}` : "none", fontSize: 14, color: ds.text2 }}>
          {cells.map((cell, j) => <span key={j} role="cell" style={{ minWidth: 0 }}>{cell}</span>)}
        </div>
      ))}
    </div>
  );
}

export function ExtratoPontosCard({ operacionais, sprints }: { operacionais: OperacionalResponse[]; sprints: SprintWithStatus[] }) {
  const [operacionalId, setOperacionalId] = useState("");
  const [sprintId, setSprintId] = useState("");
  const [eventos, setEventos] = useState<PontuacaoEvento[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!operacionalId) { setEventos([]); return; }
    setLoading(true);
    setErro(null);
    getExtratoPontos(operacionalId, sprintId || undefined)
      .then(setEventos)
      .catch((err) => setErro(err instanceof Error ? err.message : "Erro ao buscar extrato"))
      .finally(() => setLoading(false));
  }, [operacionalId, sprintId]);

  return (
    <PanelCard label="Extrato de pontos">
      <div style={{ display: "flex", gap: 10 }}>
        <Select aria-label="Operacional" value={operacionalId} onChange={(e) => setOperacionalId(e.target.value)} style={{ height: 40, fontSize: 13.5 }}>
          <option value="">Selecione um operacional</option>
          {operacionais.map((op) => <option key={op.id} value={op.id}>{op.nome}</option>)}
        </Select>
        <Select aria-label="Sprint do extrato" value={sprintId} onChange={(e) => setSprintId(e.target.value)} style={{ height: 40, fontSize: 13.5, width: 200, flexShrink: 0 }}>
          <option value="">Todas as sprints</option>
          {sprints.map((s) => <option key={s.id} value={s.id}>Sprint {s.numero}</option>)}
        </Select>
      </div>
      {!operacionalId ? (
        <div style={dashedBox}>Selecione um operacional para ver o extrato.</div>
      ) : loading ? (
        <p role="status" style={{ margin: 0, fontSize: 13, color: ds.muted }}>Carregando...</p>
      ) : erro ? (
        <p role="alert" style={{ margin: 0, fontSize: 13, color: ds.red }}>{erro}</p>
      ) : eventos.length === 0 ? (
        <div style={dashedBox}>Nenhum evento de pontuação registrado ainda.</div>
      ) : (
        <GridTable
          columns={["Data", "Tipo", "Pontos"]}
          template="90px minmax(0,1fr) 70px"
          rows={eventos.map((ev) => [
            <span key="d" style={{ fontFamily: ds.fontMono, fontSize: 12.5 }}>{new Date(ev.criado_em).toLocaleDateString("pt-BR")}</span>,
            <span key="t" style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span>{ROTULO_TIPO[ev.tipo]}</span>
              {ev.descricao && <span style={{ fontSize: 12.5, color: ds.muted }}>{ev.descricao}</span>}
            </span>,
            <span key="p" style={{ fontFamily: ds.fontMono, fontWeight: 600, color: ev.pontos > 0 ? ds.green : ev.pontos < 0 ? ds.red : ds.muted }}>
              {ev.pontos > 0 ? `+${ev.pontos}` : ev.pontos}
            </span>,
          ])}
        />
      )}
    </PanelCard>
  );
}

export function ElegibilidadeCard({ sprints }: { sprints: SprintWithStatus[] }) {
  const ordenadas = [...sprints].sort((a, b) => b.numero - a.numero);
  const [sprintId, setSprintId] = useState<string>(ordenadas[0]?.id ?? "");
  const [elegiveis, setElegiveis] = useState<ElegivelPonto[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!sprintId) return;
    setLoading(true);
    setErro(null);
    getElegiveis(sprintId)
      .then(setElegiveis)
      .catch((err) => setErro(err instanceof Error ? err.message : "Erro ao carregar"))
      .finally(() => setLoading(false));
  }, [sprintId]);

  const seletor = ordenadas.length > 0 ? (
    <Select aria-label="Sprint da elegibilidade" value={sprintId} onChange={(e) => setSprintId(e.target.value)} style={{ width: 140, height: 40, fontSize: 13.5 }}>
      {ordenadas.map((s) => <option key={s.id} value={s.id}>Sprint {s.numero}</option>)}
    </Select>
  ) : undefined;

  return (
    <PanelCard label="Elegibilidade da sprint" action={seletor}>
      {loading ? (
        <p role="status" style={{ margin: 0, fontSize: 13, color: ds.muted }}>Carregando...</p>
      ) : erro ? (
        <p role="alert" style={{ margin: 0, fontSize: 13, color: ds.red }}>{erro}</p>
      ) : elegiveis.length === 0 ? (
        <div style={dashedBox}>Ninguém vinculado a este projeto nesta consulta.</div>
      ) : (
        <GridTable
          columns={["Nome", "Tasks na sprint", "Avaliado"]}
          template="1.6fr 1fr 0.8fr"
          rows={elegiveis.map((e) => [
            e.nome,
            e.tasks_na_sprint,
            <Chip key="a" tone={e.avaliado ? "green" : "red"}>{e.avaliado ? "Sim" : "Não"}</Chip>,
          ])}
        />
      )}
    </PanelCard>
  );
}
