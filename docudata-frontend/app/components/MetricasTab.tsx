"use client";

import { useEffect, useState } from "react";
import TutorialBanner from "./TutorialBanner";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import {
  getMetricasSpi,
  getMetricasThroughput,
  getMetricasCycleTime,
  getMetricasCfd,
  getMetricasPerformanceOperacional,
  getMetricasCycleTimeStats,
  type SpiPoint,
  type ThroughputPoint,
  type CycleTimePoint,
  type CfdPoint,
  type PerformanceOperacionalPoint,
  type CycleTimeStats,
} from "../lib/api";

interface Props {
  projectId: string;
}

const section: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 12,
  padding: "20px 24px",
  marginBottom: 20,
};

const title: React.CSSProperties = {
  fontSize: 15,
  fontWeight: 700,
  color: "#0f172a",
  marginBottom: 4,
};

const subtitle: React.CSSProperties = {
  fontSize: 12,
  color: "#78716c",
  marginBottom: 16,
};

const empty: React.CSSProperties = {
  textAlign: "center",
  padding: "32px 0",
  color: "#9696a0",
  fontSize: 13,
};

const TOOLTIPS: Record<string, string> = {
  spi: "SPI = pontos concluídos ÷ pontos previstos na sprint. 1.0 = entregou exatamente o planejado. ≥0.9 = saudável (verde) · 0.7–0.9 = atenção (amarelo) · <0.7 = crítico (vermelho). Requer baseline (pontos previstos) definido na sprint.",
  throughput: "Quantas tasks foram finalizadas por sprint. Mede o ritmo de entrega da equipe. Requer tasks cadastradas e associadas a sprints.",
  cycletime: "Tempo que uma task ficou em 'Em andamento' antes de ir para 'Concluída'. Detecta gargalos — tasks que demoram muito indicam bloqueios ou escopo grande demais. Requer tasks concluídas com histórico de transições.",
  cfd: "Foto do estado das tasks em cada sprint: quantas estão em Planejado, Em andamento e Concluída. Mostra se o trabalho está fluindo ou acumulando em uma coluna.",
  perfop: "SPI estimado por operacional — soma de todos os pontos já atribuídos ao operacional (qualquer coluna) dividida pelos pontos realizados. É um proxy interino, recomputado ao vivo, não um baseline travado por operacional.",
};

function InfoTooltip({ id }: { id: string }) {
  const [show, setShow] = useState(false);
  return (
    <span style={{ position: "relative", display: "inline-block", marginLeft: 6 }}>
      <span
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        style={{ cursor: "default", fontSize: 12, color: "#94a3b8", fontWeight: 700, border: "1px solid #e2e8f0", borderRadius: "50%", width: 16, height: 16, display: "inline-flex", alignItems: "center", justifyContent: "center" }}
      >
        i
      </span>
      {show && (
        <span style={{
          position: "absolute", left: 22, top: -4, zIndex: 100,
          background: "#1e293b", color: "#f1f5f9", fontSize: 12, lineHeight: 1.5,
          borderRadius: 8, padding: "8px 12px", width: 280, whiteSpace: "normal",
          boxShadow: "0 4px 16px rgba(0,0,0,0.18)",
        }}>
          {TOOLTIPS[id]}
        </span>
      )}
    </span>
  );
}

function spiColor(spi: number | null): string {
  if (spi === null) return "#94a3b8";
  if (spi >= 0.9) return "#166534";
  if (spi >= 0.7) return "#92400e";
  return "#dc2626";
}

export default function MetricasTab({ projectId }: Props) {
  const [spi, setSpi] = useState<SpiPoint[]>([]);
  const [throughput, setThroughput] = useState<ThroughputPoint[]>([]);
  const [cycleTime, setCycleTime] = useState<CycleTimePoint[]>([]);
  const [cfd, setCfd] = useState<CfdPoint[]>([]);
  const [perfOp, setPerfOp] = useState<PerformanceOperacionalPoint[]>([]);
  const [ctStats, setCtStats] = useState<CycleTimeStats | null>(null);
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
    ])
      .then(([s, t, ct, c, po, cts]) => {
        setSpi(s);
        setThroughput(t);
        setCycleTime(ct);
        setCfd(c);
        setPerfOp(po);
        setCtStats(cts);
        setErr("");
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "Erro ao carregar métricas"))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <p style={{ color: "#9696a0", fontSize: 13 }}>Carregando métricas...</p>;
  if (err) return <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>;

  const tutorialSteps = [
    { title: "Pontos por task", body: "Cada task tem 1, 2 ou 3 pontos conforme a complexidade: 1 = simples, 2 = médio, 3 = complexo. Os pontos têm valor financeiro — o total do projeto dividido pelo total de pontos define o 'preço' de cada ponto." },
    { title: "SPI — Schedule Performance Index", body: "Mede se você está entregando o que planejou por sprint. SPI = pontos concluídos ÷ pontos previstos (baseline). ≥ 0,9 = saudável (verde) · 0,7–0,89 = atenção (amarelo) · < 0,7 = crítico (vermelho). Um SPI baixo significa faturamento abaixo do esperado." },
    { title: "Como definir o baseline", body: "O SPI só aparece se a sprint tiver um 'baseline' (pontos previstos). Vá na aba Sprints, acesse a sprint e clique em 'Baseline'. Informe a soma dos pontos de todas as tasks planejadas para aquela sprint." },
    { title: "Throughput", body: "Quantas tasks foram concluídas por sprint. Mede o ritmo de entrega da equipe. Se o throughput cai de uma sprint pra outra, pode ser sinal de tasks muito grandes ou bloqueios." },
    { title: "Cycle-time", body: "Tempo que cada task ficou em 'Em andamento' antes de ser concluída. Tasks com mais de 3 dias merecem atenção — geralmente indicam bloqueio, escopo grande demais ou dependência externa. Requer tasks que passaram por 'Em andamento' antes de 'Concluída'." },
    { title: "CFD — Cumulative Flow Diagram", body: "Foto do estado das tasks por sprint: quantas estão em Planejado, Em andamento e Concluída. Se a coluna 'Em andamento' cresce sprint a sprint sem que 'Concluída' cresça junto, há gargalo de fluxo." },
    { title: "SPI por operacional (estimado)", body: "Soma de todos os pontos já atribuídos a cada operacional dividida pelos pontos realizados. É um proxy interino recomputado ao vivo — não um baseline travado por operacional (esse mecanismo formal é de uma fase futura)." },
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

  return (
    <div>
      <TutorialBanner heading="Métricas" steps={tutorialSteps} />
      {/* SPI por sprint */}
      <div style={section}>
        <p style={title}>SPI — Schedule Performance Index <InfoTooltip id="spi" /></p>
        {spi.filter((s) => s.pontos_previstos !== null).length === 0 ? (
          <p style={empty}>Nenhuma sprint com baseline definido ainda.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={spi} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="sprint_numero" tickFormatter={(v) => `S${v}`} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} domain={[0, "auto"]} />
              <Tooltip
                formatter={(v, name) => [
                  name === "spi" ? (typeof v === "number" ? v.toFixed(2) : v) : v,
                  name === "spi" ? "SPI" : name === "pontos_realizados" ? "Realizados" : "Previstos",
                ]}
                labelFormatter={(l) => `Sprint ${l}`}
              />
              <Legend formatter={(v) => v === "pontos_previstos" ? "Previstos" : v === "pontos_realizados" ? "Realizados" : "SPI"} />
              <ReferenceLine y={0.9} stroke="#166534" strokeDasharray="4 2" label={{ value: "0.9", position: "right", fontSize: 11, fill: "#166534" }} />
              <ReferenceLine y={0.7} stroke="#dc2626" strokeDasharray="4 2" label={{ value: "0.7", position: "right", fontSize: 11, fill: "#dc2626" }} />
              <Bar dataKey="pontos_previstos" fill="#e2e8f0" radius={[4, 4, 0, 0]} />
              <Bar dataKey="pontos_realizados" fill="#0f172a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Throughput */}
      <div style={section}>
        <p style={title}>Throughput — Tasks concluídas por sprint <InfoTooltip id="throughput" /></p>
        {throughput.filter((t) => t.tasks_total > 0).length === 0 ? (
          <p style={empty}>Nenhuma task registrada ainda.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={throughput} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="sprint_numero" tickFormatter={(v) => `S${v}`} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip labelFormatter={(l) => `Sprint ${l}`} formatter={(v, n) => [v, n === "tasks_concluidas" ? "Concluídas" : n === "tasks_total" ? "Total" : "Pontos"]} />
              <Legend formatter={(v) => v === "tasks_total" ? "Total" : v === "tasks_concluidas" ? "Concluídas" : "Pontos concluídos"} />
              <Bar dataKey="tasks_total" fill="#e2e8f0" radius={[4, 4, 0, 0]} />
              <Bar dataKey="tasks_concluidas" fill="#166534" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Cycle-time */}
      <div style={section}>
        <p style={title}>Cycle-time — Distribuição <InfoTooltip id="cycletime" /></p>
        <p style={subtitle}>
          Tempo em em_andamento antes de concluir.
          {avgCT !== null && ` Média: ${avgCT < 24 ? `${avgCT}h` : `${Math.round(avgCT / 24)}d`} · ${cycleTime.length} task${cycleTime.length !== 1 ? "s" : ""} com histórico`}
          {ctStats?.p50_horas != null && ` · p50: ${ctStats.p50_horas}h`}
          {ctStats?.p85_horas != null && ` · p85: ${ctStats.p85_horas}h`}
        </p>
        {ctBuckets.length === 0 ? (
          <p style={empty}>Nenhuma task concluída com histórico de transições ainda.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={ctBuckets} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="faixa" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
              <Tooltip formatter={(v) => [v, "Tasks"]} />
              <Bar dataKey="tasks" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}

        {cycleTime.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 8 }}>Top tasks mais lentas</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {[...cycleTime]
                .sort((a, b) => b.cycle_time_horas - a.cycle_time_horas)
                .slice(0, 5)
                .map((ct, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12 }}>
                    <span style={{ color: "#78716c", minWidth: 24 }}>#{i + 1}</span>
                    <span style={{ flex: 1, color: "#0f172a" }}>{ct.task_titulo}</span>
                    {ct.operacional_nome && <span style={{ color: "#6366f1", fontSize: 11 }}>{ct.operacional_nome}</span>}
                    <span style={{ fontWeight: 700, color: ct.cycle_time_horas > 72 ? "#dc2626" : "#374151", minWidth: 52, textAlign: "right" }}>
                      {ct.cycle_time_horas < 24 ? `${ct.cycle_time_horas}h` : `${Math.round(ct.cycle_time_horas / 24)}d`}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* CFD */}
      <div style={section}>
        <p style={title}>CFD — Distribuição de tasks por coluna e sprint <InfoTooltip id="cfd" /></p>
        {cfd.length === 0 ? (
          <p style={empty}>Nenhuma sprint com tasks ainda.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={cfd} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="sprint_numero" tickFormatter={(v) => `S${v}`} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip labelFormatter={(l) => `Sprint ${l}`} formatter={(v, n) => [v, n === "concluida" ? "Concluída" : n === "em_andamento" ? "Em andamento" : "Planejado"]} />
              <Legend formatter={(v) => v === "concluida" ? "Concluída" : v === "em_andamento" ? "Em andamento" : "Planejado"} />
              <Area type="monotone" dataKey="concluida" stackId="1" stroke="#166534" fill="#dcfce7" />
              <Area type="monotone" dataKey="em_andamento" stackId="1" stroke="#92400e" fill="#fef9c3" />
              <Area type="monotone" dataKey="planejado" stackId="1" stroke="#374151" fill="#f1f5f9" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Performance por operacional (SPI estimado) */}
      <div style={section}>
        <p style={title}>SPI por operacional (estimado) <InfoTooltip id="perfop" /></p>
        {perfOp.length === 0 ? (
          <p style={empty}>Nenhum operacional com tasks atribuídas ainda.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={perfOp} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="operacional_nome" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} domain={[0, "auto"]} />
              <Tooltip
                formatter={(v, name) => [
                  v,
                  name === "pontos_atribuidos" ? "Atribuídos" : name === "pontos_realizados" ? "Realizados" : name,
                ]}
              />
              <Legend formatter={(v) => v === "pontos_atribuidos" ? "Atribuídos" : "Realizados"} />
              <Bar dataKey="pontos_atribuidos" fill="#e2e8f0" radius={[4, 4, 0, 0]} />
              <Bar dataKey="pontos_realizados" fill="#0f172a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
