"use client";

import { useEffect, useState } from "react";
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
  type SpiPoint,
  type ThroughputPoint,
  type CycleTimePoint,
  type CfdPoint,
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
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getMetricasSpi(projectId),
      getMetricasThroughput(projectId),
      getMetricasCycleTime(projectId),
      getMetricasCfd(projectId),
    ])
      .then(([s, t, ct, c]) => {
        setSpi(s);
        setThroughput(t);
        setCycleTime(ct);
        setCfd(c);
        setErr("");
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "Erro ao carregar métricas"))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <p style={{ color: "#9696a0", fontSize: 13 }}>Carregando métricas...</p>;
  if (err) return <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>;

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
      {/* SPI por sprint */}
      <div style={section}>
        <p style={title}>SPI — Schedule Performance Index</p>
        <p style={subtitle}>Pontos realizados / previstos por sprint. ≥ 0.9 saudável · 0.7–0.9 atenção · &lt; 0.7 crítico</p>
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
        <p style={title}>Throughput — Tasks concluídas por sprint</p>
        <p style={subtitle}>Quantas tasks foram finalizadas em cada sprint.</p>
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
        <p style={title}>Cycle-time — Distribuição</p>
        <p style={subtitle}>
          Tempo em em_andamento antes de concluir.
          {avgCT !== null && ` Média: ${avgCT < 24 ? `${avgCT}h` : `${Math.round(avgCT / 24)}d`} · ${cycleTime.length} task${cycleTime.length !== 1 ? "s" : ""} com histórico`}
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
        <p style={title}>CFD — Distribuição de tasks por coluna e sprint</p>
        <p style={subtitle}>Snapshot do estado das tasks em cada sprint.</p>
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
    </div>
  );
}
