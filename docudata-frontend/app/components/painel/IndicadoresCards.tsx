"use client";

import { useState } from "react";
import { updateContrato, type BlocoD, type PainelData, type Project, type SprintWithStatus } from "../../lib/api";
import { ds } from "../../lib/ds";
import { Button, ErrorNotice, Field, Input, ProgressBar, Select } from "../ds";
import { BigNumber, CardTextAction, Metric, Muted, PanelCard, fmtNum } from "./PanelCard";

/** Bloco A — Tempo × Escopo, com o formulário de datas do contrato. */
export function TempoEscopoCard({
  bloco, project, sprints, onSaved,
}: {
  bloco: PainelData["bloco_a"];
  project: Project;
  sprints: SprintWithStatus[];
  onSaved?: (updated: Project) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [dataInicio, setDataInicio] = useState(project.data_inicio ?? "");
  const [dataFim, setDataFim] = useState(project.data_fim_contratada ?? "");
  const [tolerancia, setTolerancia] = useState(project.tolerancia_desvio_pontos != null ? String(project.tolerancia_desvio_pontos) : "");
  const [arquetipo, setArquetipo] = useState<"padrao" | "consultoria_discovery">(project.arquetipo ?? "padrao");
  const [valorProjeto, setValorProjeto] = useState(project.valor_projeto != null ? String(project.valor_projeto) : "");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const valorTravado = sprints.some((s) => s.pontos_orcamento != null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!dataInicio || !dataFim) { setErr("Preencha as duas datas."); return; }
    setSaving(true);
    setErr("");
    try {
      const updated = await updateContrato(project.id, {
        data_inicio: dataInicio,
        data_fim_contratada: dataFim,
        tolerancia_desvio_pontos: tolerancia !== "" ? Number(tolerancia) : null,
        arquetipo,
        valor_projeto: !valorTravado && valorProjeto !== "" ? Number(valorProjeto) : undefined,
      });
      onSaved?.(updated);
      setEditing(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  const action = (editing || !bloco.sem_dados)
    ? <CardTextAction expanded={editing} onClick={() => { setEditing((v) => !v); setErr(""); }}>{editing ? "Cancelar" : "Editar"}</CardTextAction>
    : undefined;

  return (
    <PanelCard label="Tempo × Escopo" action={action}>
      {editing ? (
        <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Início do projeto" htmlFor="contrato-inicio" required>
              <Input id="contrato-inicio" type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} required />
            </Field>
            <Field label="Fim contratado" htmlFor="contrato-fim" required>
              <Input id="contrato-fim" type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} required />
            </Field>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Field label="Tolerância (pontos)" htmlFor="contrato-tolerancia" hint="Opcional">
              <Input id="contrato-tolerancia" type="number" min={0} value={tolerancia} onChange={(e) => setTolerancia(e.target.value)} placeholder="ex: 5" />
            </Field>
            <Field label="Arquétipo" htmlFor="contrato-arquetipo">
              <Select id="contrato-arquetipo" value={arquetipo} onChange={(e) => setArquetipo(e.target.value as "padrao" | "consultoria_discovery")}>
                <option value="padrao">Padrão</option>
                <option value="consultoria_discovery">Consultoria / Discovery</option>
              </Select>
            </Field>
          </div>
          <Field
            label="Valor do projeto (R$)"
            htmlFor="contrato-valor"
            hint={valorTravado ? "Travado: já existe orçamento de pontos definido em pelo menos uma sprint." : "Opcional"}
          >
            <Input id="contrato-valor" type="number" min={0} step="0.01" value={valorProjeto} onChange={(e) => setValorProjeto(e.target.value)} placeholder="ex: 35000" disabled={valorTravado} />
          </Field>
          {err && <ErrorNotice>{err}</ErrorNotice>}
          <div>
            <Button type="submit" variant="primary" disabled={saving}>{saving ? "Salvando..." : "Salvar datas"}</Button>
          </div>
        </form>
      ) : bloco.sem_dados ? (
        <>
          <Muted>Defina as datas do contrato para comparar o prazo consumido com o escopo aprovado pelo cliente.</Muted>
          <div>
            <Button variant="secondary" onClick={() => setEditing(true)}>Configurar datas</Button>
          </div>
        </>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <Metric caption="Prazo consumido" value={`${fmtNum(bloco.pct_prazo_consumido ?? 0)}%`} />
            <Metric caption="Escopo concluído" value={`${fmtNum(bloco.pct_escopo_concluido ?? 0)}%`} color={ds.green} />
          </div>
          {bloco.desvio_detectado ? (
            <p role="status" style={{ margin: 0, display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: ds.amber }}>
              <span aria-hidden="true" style={{ width: 6, height: 6, borderRadius: "50%", background: ds.amber }} />
              Desvio de {bloco.desvio_pontos} pts acima da tolerância
            </p>
          ) : (
            <Muted small>Prazo e escopo dentro da tolerância.</Muted>
          )}
        </>
      )}
    </PanelCard>
  );
}

/** Bloco B — Itens em atenção (funcionalidades travadas). */
export function ItensAtencaoCard({ bloco }: { bloco: PainelData["bloco_b"] }) {
  const n = bloco.travadas.length;
  return (
    <PanelCard label="Itens em atenção">
      <BigNumber value={n} unit={n === 1 ? "travada" : "travadas"} color={n === 0 ? ds.green : ds.red} />
      {n === 0 ? (
        <Muted>Nenhuma funcionalidade travada.</Muted>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {bloco.travadas.map((f, i) => (
            <div key={f.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "10px 0", borderTop: i > 0 ? `1px solid ${ds.border}` : "none" }}>
              <span style={{ fontSize: 14, fontWeight: 500, color: ds.white }}>{f.titulo}</span>
              <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.red, flexShrink: 0 }}>{f.dias} dias</span>
            </div>
          ))}
        </div>
      )}
    </PanelCard>
  );
}

/** Bloco C — Métricas de fluxo (WIP, throughput e cycle time). */
export function MetricasFluxoCard({ bloco }: { bloco: PainelData["bloco_c"] }) {
  return (
    <PanelCard label="Métricas de fluxo">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <Metric caption="WIP agora" value={bloco.wip} unit="funcionalidades" />
        <Metric caption="Throughput" value={fmtNum(bloco.throughput_por_semana ?? 0)} unit="/ semana" />
      </div>
      <Muted small>
        {bloco.total_concluidas === 0
          ? "Nenhuma funcionalidade concluída · cycle time indisponível"
          : `Cycle time p50 ${fmtNum(bloco.cycle_time_p50_dias)} dias · p85 ${fmtNum(bloco.cycle_time_p85_dias)} dias`}
      </Muted>
    </PanelCard>
  );
}

/** Bloco D — Tempo por fase e eficiência de fluxo. */
export function TempoPorFaseCard({ bloco }: { bloco: BlocoD }) {
  const [expandedFase, setExpandedFase] = useState<string | null>(null);
  const fases = Object.entries(bloco.fases_resumo);
  const eficiencia = bloco.eficiencia_fluxo_pct;

  return (
    <PanelCard label="Tempo por fase">
      <Metric caption="Eficiência de fluxo" value={eficiencia != null ? `${fmtNum(eficiencia)}%` : "—"} color={ds.green} />
      {eficiencia != null && <ProgressBar pct={eficiencia} label="Eficiência de fluxo" />}
      {fases.length === 0 ? (
        <Muted small>Sem transições de status registradas ainda.</Muted>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {fases.map(([fase, resumo]) => {
            const aberta = expandedFase === fase;
            const detalhes = bloco.detalhe_por_funcionalidade.filter((d) => d.tempos_por_fase[fase] != null);
            return (
              <div key={fase} style={{ borderTop: `1px solid ${ds.border}` }}>
                <button
                  type="button"
                  className="ds-row-link"
                  aria-expanded={aberta}
                  onClick={() => setExpandedFase(aberta ? null : fase)}
                  style={{
                    width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12,
                    padding: "12px 0", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", fontSize: 13, textAlign: "left",
                  }}
                >
                  <span style={{ fontFamily: ds.fontMono, color: ds.white }}>{fase}</span>
                  <span style={{ color: ds.text2 }}>
                    {fmtNum(resumo.media_dias)} dias (média) · {fmtNum(resumo.p85_dias)} p85 <span aria-hidden="true" style={{ color: ds.muted }}>{aberta ? "▴" : "▾"}</span>
                  </span>
                </button>
                {aberta && (
                  <div style={{ padding: "0 0 12px", display: "flex", flexDirection: "column", gap: 6 }}>
                    {detalhes.length === 0 ? (
                      <Muted small>Sem dados de duração para esta fase.</Muted>
                    ) : detalhes.map((d) => (
                      <div key={d.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 12.5 }}>
                        <span style={{ color: ds.text2 }}>{d.titulo}</span>
                        <span style={{ fontFamily: ds.fontMono, color: ds.muted }}>{fmtNum(d.tempos_por_fase[fase])} dias</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </PanelCard>
  );
}
