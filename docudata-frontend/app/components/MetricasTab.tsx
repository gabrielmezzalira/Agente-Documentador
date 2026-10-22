"use client";

import { useEffect, useState } from "react";
import TutorialBanner from "./TutorialBanner";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { ds, labelStyle } from "../lib/ds";
import { Chip, InfoTip } from "./ds";
import { BigNumber, PanelCard, fmtNum } from "./painel/PanelCard";
import { BarGroups, ChartEmpty, ChartLegend } from "./metricas/Charts";
import {
  getMetricasSpi,
  getMetricasThroughput,
  getMetricasCycleTime,
  getMetricasCfd,
  getMetricasPerformanceOperacional,
  getSpiDoProjeto,
  getMetricasCycleTimeStats,
  getComparacaoModos,
  type SpiPoint,
  type ThroughputPoint,
  type CycleTimePoint,
  type CfdPoint,
  type PerformanceOperacionalPoint,
  type SpiPorOperacionalDoProjeto,
  type CycleTimeStats,
  type ComparacaoModoPonto,
} from "../lib/api";

interface Props {
  projectId: string;
  modoTrabalho?: "ATRIBUICAO" | "PULL";
}

const TOOLTIPS: Record<string, string> = {
  spi: "SPI = pontos concluídos ÷ pontos previstos na sprint (as tasks que estavam nela quando começou + as que surgiram depois; extras ficam de fora). 1,0 = entregou o previsto. ≥0,9 saudável (verde) · 0,7–0,9 atenção (amarelo) · <0,7 crítico (vermelho).",
  throughput: "Quantas tasks foram finalizadas por sprint. Mede o ritmo de entrega da equipe. Requer tasks cadastradas e associadas a sprints.",
  cycletime: "Tempo que uma task ficou em 'Em andamento' antes de ir para 'Concluída'. Detecta gargalos — tasks que demoram muito indicam bloqueios ou escopo grande demais. Requer tasks concluídas com histórico de transições.",
  cfd: "Foto do estado das tasks em cada sprint: quantas estão em Planejado, Em andamento e Concluída. Mostra se o trabalho está fluindo ou acumulando em uma coluna.",
  spievol: "Só entra o que já foi travado pelo fechamento da Avaliação Semanal — é o mesmo dado que alimenta o acompanhamento de performance. SPI = pontos entregues sobre pontos que a pessoa pegou, já descontando o que foi penalizado por task parada tempo demais.",
  perfop: "SPI estimado por operacional — soma de todos os pontos já atribuídos ao operacional (qualquer coluna) dividida pelos pontos realizados. É um proxy interino, recomputado ao vivo, não um baseline travado por operacional.",
};

function InfoTooltip({ id }: { id: string }) {
  return <InfoTip text={TOOLTIPS[id]} />;
}

function spiColor(spi: number | null): string {
  if (spi === null) return ds.muted;
  if (spi >= 0.9) return ds.green;
  if (spi >= 0.7) return ds.amber;
  return ds.red;
}

function _cfdLabel(v: string): string {
  if (v === "concluida") return "Concluída";
  if (v === "pendente_aprovacao") return "Pendente de aprovação";
  if (v === "em_andamento") return "Em andamento";
  return "Planejado";
}

export default function MetricasTab({ projectId, modoTrabalho = "ATRIBUICAO" }: Props) {
  const labelPontosVinculados = modoTrabalho === "PULL" ? "Puxados" : "Atribuídos";
  const [spi, setSpi] = useState<SpiPoint[]>([]);
  const [throughput, setThroughput] = useState<ThroughputPoint[]>([]);
  const [cycleTime, setCycleTime] = useState<CycleTimePoint[]>([]);
  const [cfd, setCfd] = useState<CfdPoint[]>([]);
  const [perfOp, setPerfOp] = useState<PerformanceOperacionalPoint[]>([]);
  const [spiPorPessoa, setSpiPorPessoa] = useState<SpiPorOperacionalDoProjeto[]>([]);
  const [ctStats, setCtStats] = useState<CycleTimeStats | null>(null);
  const [comparacaoModos, setComparacaoModos] = useState<ComparacaoModoPonto[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getMetricasSpi(projectId),
      getMetricasThroughput(projectId),
      getMetricasCycleTime(projectId),
      getMetricasCfd(projectId),
      getMetricasPerformanceOperacional(projectId),
      getMetricasCycleTimeStats(projectId),
      getSpiDoProjeto(projectId).catch(() => [] as SpiPorOperacionalDoProjeto[]),
    ])
      .then(([s, t, ct, c, po, cts, se]) => {
        setSpi(s);
        setThroughput(t);
        setCycleTime(ct);
        setCfd(c);
        setPerfOp(po);
        setCtStats(cts);
        setSpiPorPessoa(se);
        setErr("");
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "Erro ao carregar métricas"))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    getComparacaoModos(projectId).then(setComparacaoModos).catch(() => setComparacaoModos([]));
  }, [projectId]);

  if (loading) return <p role="status" style={{ color: ds.muted, fontSize: 13, margin: 0 }}>Carregando métricas...</p>;
  if (err) return <p role="alert" style={{ color: ds.red, fontSize: 13, margin: 0 }}>{err}</p>;

  const tutorialSteps = [
    { title: "Pontos por task", body: "Cada task vale 1, 2, 3 ou 5 pontos, conforme o tamanho. O previsto de cada sprint é a soma dos pontos das tasks que estavam nela quando começou, mais as que surgiram depois." },
    { title: "SPI — Schedule Performance Index", body: "Mede se você está entregando o que planejou por sprint. SPI = pontos concluídos ÷ pontos previstos (planejadas + surgiram na sprint). ≥ 0,9 = saudável (verde) · 0,7–0,89 = atenção (amarelo) · < 0,7 = crítico (vermelho)." },
    { title: "Throughput", body: "Quantas tasks foram concluídas por sprint. Mede o ritmo de entrega da equipe. Se o throughput cai de uma sprint pra outra, pode ser sinal de tasks muito grandes ou bloqueios." },
    { title: "Cycle-time", body: "Tempo que cada task ficou em 'Em andamento' antes de ser concluída. Tasks com mais de 3 dias merecem atenção — geralmente indicam bloqueio, escopo grande demais ou dependência externa. Requer tasks que passaram por 'Em andamento' antes de 'Concluída'." },
    { title: "CFD — Cumulative Flow Diagram", body: "Foto do estado das tasks por sprint: quantas estão em Planejado, Em andamento e Concluída. Se a coluna 'Em andamento' cresce sprint a sprint sem que 'Concluída' cresça junto, há gargalo de fluxo." },
    { title: "SPI por operacional (estimado)", body: "Proxy calculado ao vivo sobre todas as tasks vinculadas a cada pessoa (atribuídas ou puxadas), em qualquer coluna. Serve para ver quem está sobrecarregado agora; não é o número que alimenta o acompanhamento de performance." },
    { title: "Entrega por pessoa", body: "Este é o dado consolidado: só entra o que já foi travado pelo fechamento da Avaliação Semanal, e é o mesmo que alimenta o acompanhamento de performance. Mostra a entrega de cada pessoa (já descontando o que foi penalizado por task travada), quantas sprints já foram avaliadas, e quantos pontos ela perdeu por atraso. Use na conversa de feedback." },
  ];

  // Cycle-time — distribuição por faixas de horas
  const ctBuckets: { faixa: string; tasks: number }[] = [
    { faixa: "< 8h", tasks: cycleTime.filter((c) => c.cycle_time_horas < 8).length },
    { faixa: "8–24h", tasks: cycleTime.filter((c) => c.cycle_time_horas >= 8 && c.cycle_time_horas < 24).length },
    { faixa: "1–3d", tasks: cycleTime.filter((c) => c.cycle_time_horas >= 24 && c.cycle_time_horas < 72).length },
    { faixa: "3–7d", tasks: cycleTime.filter((c) => c.cycle_time_horas >= 72 && c.cycle_time_horas < 168).length },
    { faixa: "> 7d", tasks: cycleTime.filter((c) => c.cycle_time_horas >= 168).length },
  ].filter((b) => b.tasks > 0);

  const avgCT = cycleTime.length
    ? Math.round(cycleTime.reduce((s, c) => s + c.cycle_time_horas, 0) / cycleTime.length)
    : null;

  const chartGrey = ds.chartGrey;
  const fmtHoras = (h: number) => (h < 24 ? `${fmtNum(h)}h` : `${Math.round(h / 24)}d`);
  const spiComBaseline = spi.filter((s) => s.pontos_previstos !== null);
  const ultimoSpi = [...spiComBaseline].reverse().find((s) => s.spi !== null)?.spi ?? null;
  const lentas = [...cycleTime].sort((a, b) => b.cycle_time_horas - a.cycle_time_horas).slice(0, 5);
  const corLenta = (h: number) => (h >= 120 ? ds.red : h >= 72 ? ds.amber : ds.text2);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <TutorialBanner heading="Métricas" steps={tutorialSteps} />

      <div className="ds-painel-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 16 }}>
        <PanelCard label="SPI · Schedule Performance Index" action={<InfoTooltip id="spi" />}>
          {spiComBaseline.length === 0 ? (
            <ChartEmpty>
              O SPI aparece quando a sprint começa com tasks dentro dela.
            </ChartEmpty>
          ) : (
            <>
              {ultimoSpi !== null && <BigNumber value={fmtNum(ultimoSpi)} unit="SPI da última sprint" color={spiColor(ultimoSpi)} />}
              <BarGroups
                label="Pontos previstos e realizados por sprint"
                categories={spiComBaseline.map((s) => `S${s.sprint_numero}`)}
                series={[
                  { key: "prev", label: "Previstos", color: chartGrey, values: spiComBaseline.map((s) => s.pontos_previstos ?? 0) },
                  { key: "real", label: "Realizados", color: ds.green, values: spiComBaseline.map((s) => s.pontos_realizados ?? 0) },
                ]}
              />
            </>
          )}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Chip tone="green">≥ 0,9 saudável</Chip>
            <Chip tone="amber">0,7 a 0,9 atenção</Chip>
            <Chip tone="red">&lt; 0,7 crítico</Chip>
          </div>
        </PanelCard>

        <PanelCard
          label="Throughput · tasks concluídas por sprint"
          action={<ChartLegend items={[{ label: "Concluídas", color: ds.green }, { label: "Total", color: chartGrey }]} />}
        >
          {throughput.filter((t) => t.tasks_total > 0).length === 0 ? (
            <ChartEmpty>Nenhuma task registrada ainda.</ChartEmpty>
          ) : (
            <BarGroups
              label="Tasks totais e concluídas por sprint"
              categories={throughput.map((t) => `S${t.sprint_numero}`)}
              series={[
                { key: "total", label: "Total", color: chartGrey, values: throughput.map((t) => t.tasks_total) },
                { key: "conc", label: "Concluídas", color: ds.green, values: throughput.map((t) => t.tasks_concluidas) },
              ]}
            />
          )}
        </PanelCard>
      </div>

      <PanelCard label="Cycle time · distribuição" action={<InfoTooltip id="cycletime" />}>
        {cycleTime.length === 0 ? (
          <ChartEmpty>Nenhuma task concluída com histórico de transições ainda.</ChartEmpty>
        ) : (
          <>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {avgCT !== null && <Chip>Média {fmtHoras(avgCT)}</Chip>}
              {ctStats?.p50_horas != null && <Chip>mediana {fmtNum(ctStats.p50_horas)}h</Chip>}
              {ctStats?.p85_horas != null && <Chip>85% em até {fmtNum(ctStats.p85_horas)}h</Chip>}
              <Chip>{cycleTime.length} task{cycleTime.length !== 1 ? "s" : ""} com histórico</Chip>
            </div>
            <div className="ds-painel-grid" style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 36, alignItems: "start", paddingTop: 10 }}>
              <BarGroups
                label="Quantidade de tasks por faixa de cycle time"
                categories={ctBuckets.map((b) => b.faixa)}
                series={[{ key: "tasks", label: "Tasks", color: ds.green, values: ctBuckets.map((b) => b.tasks) }]}
              />
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: ds.white, paddingBottom: 8 }}>Tasks mais lentas</span>
                {lentas.map((ct, i) => (
                  <div key={i} style={{ display: "grid", gridTemplateColumns: "28px minmax(0,1fr) auto 36px", gap: 10, alignItems: "center", padding: "9px 0", borderTop: `1px solid ${ds.border}`, fontSize: 13 }}>
                    <span style={{ fontFamily: ds.fontMono, color: ds.dim }}>#{i + 1}</span>
                    <span style={{ color: ds.text2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{ct.task_titulo}</span>
                    <span style={{ color: ds.violet, fontSize: 12 }}>{ct.operacional_nome ?? ""}</span>
                    <span style={{ fontFamily: ds.fontMono, fontWeight: 600, color: corLenta(ct.cycle_time_horas), textAlign: "right" }}>{fmtHoras(ct.cycle_time_horas)}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </PanelCard>

      <div className="ds-painel-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <PanelCard label="CFD · tasks por coluna e sprint" action={<InfoTooltip id="cfd" />}>
          {cfd.length === 0 ? (
            <ChartEmpty>Nenhuma sprint com tasks ainda.</ChartEmpty>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={190}>
                <AreaChart data={cfd} margin={{ top: 8, right: 4, left: -24, bottom: 0 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="sprint_numero" tickFormatter={(v) => `S${v}`} tick={{ fontSize: 11.5, fill: ds.muted, fontFamily: ds.fontMono }} axisLine={{ stroke: ds.borderStrong }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10.5, fill: ds.dim, fontFamily: ds.fontMono }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: ds.cardTop, border: `1px solid ${ds.greenLine}`, borderRadius: 10, color: ds.text, fontSize: 12.5 }}
                    labelStyle={{ color: ds.text2 }}
                    labelFormatter={(l) => `Sprint ${l}`}
                    formatter={(v, n) => [v, _cfdLabel(String(n))]}
                  />
                  <Area type="monotone" dataKey="concluida" stackId="1" stroke={ds.green} fill="rgba(62,224,111,0.20)" />
                  <Area type="monotone" dataKey="pendente_aprovacao" stackId="1" stroke={ds.violet} fill="rgba(177,151,252,0.16)" />
                  <Area type="monotone" dataKey="em_andamento" stackId="1" stroke={ds.amber} fill="rgba(242,193,78,0.16)" />
                  <Area type="monotone" dataKey="planejado" stackId="1" stroke={chartGrey} fill="rgba(74,85,80,0.25)" />
                </AreaChart>
              </ResponsiveContainer>
              <ChartLegend items={[
                { label: "Concluída", color: ds.green },
                { label: "Em andamento", color: ds.amber },
                { label: "Pendente de aprovação", color: ds.violet },
                { label: "Planejado", color: chartGrey },
              ]} />
            </>
          )}
        </PanelCard>

        <PanelCard label="SPI por operacional · estimado" action={<InfoTooltip id="perfop" />}>
          {perfOp.length === 0 ? (
            <ChartEmpty>Nenhum operacional com tasks {modoTrabalho === "PULL" ? "puxadas" : "atribuídas"} ainda.</ChartEmpty>
          ) : (
            <>
              <BarGroups
                label={`Pontos ${labelPontosVinculados.toLowerCase()} e realizados por operacional`}
                categories={perfOp.map((p) => p.operacional_nome)}
                series={[
                  { key: "vinc", label: labelPontosVinculados, color: chartGrey, values: perfOp.map((p) => p.pontos_atribuidos) },
                  { key: "real", label: "Realizados", color: ds.green, values: perfOp.map((p) => p.pontos_realizados) },
                ]}
              />
              <ChartLegend items={[{ label: labelPontosVinculados, color: chartGrey }, { label: "Realizados", color: ds.green }]} />
            </>
          )}
        </PanelCard>
      </div>

      <PanelCard label="Entrega por pessoa" action={<Chip tone="amber">Leitura restrita a líderes e gerentes</Chip>}>
        <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55, color: ds.muted }}>
          Dado consolidado nos fechamentos de sprint. Use na conversa de feedback. <InfoTooltip id="spievol" />
        </p>
        {spiPorPessoa.length === 0 ? (
          <ChartEmpty>Nenhum operacional cadastrado neste projeto.</ChartEmpty>
        ) : (
          <div role="table" style={{ display: "flex", flexDirection: "column" }}>
            <div role="row" style={{ display: "grid", gridTemplateColumns: "1.3fr 1.4fr 1fr 1.2fr", gap: 12, padding: "10px 16px", borderBottom: `1px solid ${ds.border}` }}>
              {["Pessoa", "Entrega", "Sprints avaliadas", "Pontos perdidos por atraso"].map((c) => <span key={c} role="columnheader" style={labelStyle}>{c}</span>)}
            </div>
            {spiPorPessoa.map((op, i) => {
              const cor = op.spi === null ? ds.muted : spiColor(op.spi / 100);
              return (
                <div key={op.operacional_id} role="row" style={{ display: "grid", gridTemplateColumns: "1.3fr 1.4fr 1fr 1.2fr", gap: 12, alignItems: "center", padding: "14px 16px", borderTop: i > 0 ? `1px solid ${ds.border}` : "none", fontSize: 14, color: ds.text2 }}>
                  <span role="cell">{op.nome}</span>
                  <span role="cell" style={{ display: "flex", alignItems: "center", gap: 10 }} title={op.spi === null && op.sprints_avaliadas > 0 ? "Sem task alocada nesta sprint: score calculado com o restante das dimensões (avaliação do gerente, autonomia)" : undefined}>
                    <span style={{ fontFamily: ds.fontMono, fontWeight: 600, color: cor, width: 52 }}>{op.spi === null ? "—" : fmtNum(op.spi)}</span>
                    {op.spi !== null && (
                      <span aria-hidden="true" style={{ flex: 1, maxWidth: 140, height: 5, borderRadius: 3, background: "rgba(255,255,255,0.07)", overflow: "hidden", display: "block" }}>
                        <span style={{ display: "block", width: `${Math.min(100, op.spi)}%`, height: "100%", background: cor }} />
                      </span>
                    )}
                  </span>
                  <span role="cell">{op.sprints_avaliadas}</span>
                  <span role="cell" style={{ color: op.pontos_penalizados > 0 ? ds.red : ds.muted }}>{op.pontos_penalizados || "—"}</span>
                </div>
              );
            })}
          </div>
        )}
      </PanelCard>

      {/* Comparação de modos (Entrega 2) */}
      {comparacaoModos.length >= 2 && (
        <PanelCard label="Comparação de modos">
          <p style={{ margin: 0, fontSize: 13, color: ds.muted }}>Sprints fechadas agrupadas pelo modo vigente no momento do fechamento de cada uma.</p>
          <BarGroups
            label="SPI médio e entrega média por modo"
            categories={comparacaoModos.map((c) => `${c.modo_trabalho}/${c.modo_avaliacao}`)}
            series={[
              { key: "spi", label: "SPI médio", color: chartGrey, values: comparacaoModos.map((c) => c.spi_medio ?? 0) },
              { key: "ent", label: "Entrega média", color: ds.green, values: comparacaoModos.map((c) => c.entrega_media ?? 0) },
            ]}
          />
          <ChartLegend items={[{ label: "SPI médio", color: chartGrey }, { label: "Entrega média", color: ds.green }]} />
        </PanelCard>
      )}
    </div>
  );
}
