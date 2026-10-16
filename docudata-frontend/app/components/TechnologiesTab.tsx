"use client";

import { useEffect, useState } from "react";
import { getTechnologies, type TechTimeline } from "../lib/api";
import { ds, labelStyle } from "../lib/ds";
import { Card, Chip, EmptyState, ErrorNotice, TabSectionHead } from "./ds";
import { PanelCard } from "./painel/PanelCard";

interface Props {
  projectId: string;
}

export default function TechnologiesTab({ projectId }: Props) {
  const [data, setData] = useState<TechTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getTechnologies(projectId)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [projectId]);

  const head = (
    <TabSectionHead
      title="Tecnologias"
      count={data ? `${data.em_uso_atual.length} em uso` : undefined}
      description="Tecnologias detectadas nas ingestões e commits do projeto, sprint a sprint: o que está em uso agora e quando cada uma entrou ou saiu."
    />
  );

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        {head}
        <Card><p role="status" style={{ margin: 0, padding: "24px 26px", color: ds.muted, fontSize: 14 }}>Carregando tecnologias…</p></Card>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        {head}
        <ErrorNotice>{error}</ErrorNotice>
      </div>
    );
  }

  if (!data || data.timeline.length === 0) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        {head}
        <EmptyState>
          Nenhuma tecnologia identificada ainda. O DocuData extrai as tecnologias das ingestões: assim que o gerente subir conteúdo que mencione stack, ferramentas ou bibliotecas, elas aparecem aqui.
        </EmptyState>
      </div>
    );
  }

  const activeKeys = new Set(data.em_uso_atual.map((t) => t.toLowerCase()));
  const colunas = "minmax(0,1.4fr) 1fr 1fr 140px";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ marginBottom: 12 }}>{head}</div>
      <PanelCard label={`Em uso atualmente · ${data.em_uso_atual.length}`}>
        {data.em_uso_atual.length === 0 ? (
          <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Nenhuma tecnologia ativa na sprint mais recente.</p>
        ) : (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {data.em_uso_atual.map((t) => <Chip key={t} tone="green">{t}</Chip>)}
          </div>
        )}
      </PanelCard>

      <PanelCard label="Histórico · quando cada tecnologia entrou e saiu">
        <div role="table" style={{ display: "flex", flexDirection: "column", overflowX: "auto" }}>
          <div role="row" style={{ display: "grid", gridTemplateColumns: colunas, gap: 12, padding: "10px 16px", borderBottom: `1px solid ${ds.border}`, minWidth: 520 }}>
            {["Tecnologia", "Introduzida em", "Abandonada em", "Status"].map((c) => <span key={c} role="columnheader" style={labelStyle}>{c}</span>)}
          </div>
          {data.timeline.map((entry, i) => {
            const ativa = activeKeys.has(entry.tecnologia.toLowerCase());
            return (
              <div key={`${entry.tecnologia}-${i}`} role="row" style={{ display: "grid", gridTemplateColumns: colunas, gap: 12, alignItems: "center", padding: "14px 16px", borderTop: i > 0 ? `1px solid ${ds.border}` : "none", fontSize: 14, color: ds.text2, minWidth: 520 }}>
                <span role="cell" style={{ fontWeight: 600, color: ds.white }}>{entry.tecnologia}</span>
                <span role="cell" style={{ fontFamily: ds.fontMono, fontSize: 13 }}>Sprint {entry.introduzida_em}</span>
                <span role="cell" style={{ fontFamily: ds.fontMono, fontSize: 13, color: entry.abandonada_em == null ? ds.dim : ds.amber }}>
                  {entry.abandonada_em == null ? "—" : `Sprint ${entry.abandonada_em}`}
                </span>
                <span role="cell">{ativa ? <Chip tone="green" dot>Em uso</Chip> : <Chip>Abandonada</Chip>}</span>
              </div>
            );
          })}
        </div>
      </PanelCard>
    </div>
  );
}
