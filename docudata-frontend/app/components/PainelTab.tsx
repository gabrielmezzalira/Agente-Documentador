"use client";

import { useEffect, useState } from "react";
import {
  getPainel,
  listFuncionalidades,
  type AchadoCritico,
  type BlocoD,
  type FuncionalidadeResponse,
  type PainelData,
  type SprintWithStatus,
} from "../lib/api";

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
  onNavigateToConfig?: () => void;
}

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "20px 22px",
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "#9696a0",
  marginBottom: 14,
  display: "block",
};

const metricLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#6a6a7a",
  marginBottom: 2,
};

const metricValueStyle: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 800,
  color: "#111116",
  letterSpacing: "-0.02em",
};

const chipBaseStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "4px 10px",
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 600,
};

const subSectionTitleStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  color: "#374151",
  marginBottom: 8,
  marginTop: 12,
};

function BlocoACard({
  bloco,
  onNavigateToConfig,
}: {
  bloco: PainelData["bloco_a"];
  onNavigateToConfig?: () => void;
}) {
  return (
    <div style={cardStyle}>
      <span style={cardTitleStyle}>Tempo × Escopo</span>
      {bloco.sem_dados ? (
        <div>
          <p style={{ fontSize: 13, color: "#9696a0", margin: "0 0 8px" }}>
            Sem dados de contrato
          </p>
          <button
            style={{
              background: "none",
              border: "none",
              color: "#4ade80",
              fontSize: 13,
              cursor: "pointer",
              padding: 0,
              textDecoration: "underline",
            }}
            onClick={() => onNavigateToConfig?.()}
          >
            Ir para Configurações
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            { label: "Prazo consumido", value: bloco.pct_prazo_consumido },
            { label: "Escopo concluído", value: bloco.pct_escopo_concluido },
            { label: "Aprovado pelo cliente", value: bloco.pct_aprovado_cliente },
          ].map(({ label, value }) => (
            <div key={label}>
              <p style={metricLabelStyle}>{label}</p>
              <p style={{ ...metricValueStyle, margin: 0 }}>{value ?? 0}%</p>
            </div>
          ))}
          {bloco.desvio_detectado && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginTop: 10,
                padding: "8px 12px",
                background: "#fff7ed",
                borderRadius: 8,
                border: "1px solid #fed7aa",
              }}
            >
              <span style={{ color: "#c2410c", fontSize: 14 }}>⚠</span>
              <span style={{ fontSize: 12, color: "#c2410c" }}>
                Desvio de {bloco.desvio_pontos} pts acima da tolerância
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BlocoBCard({ bloco }: { bloco: PainelData["bloco_b"] }) {
  const [visaoRelatorio, setVisaoRelatorio] = useState<"gerente" | "tecnico">("gerente");
  const sep = (
    <hr style={{ border: "none", borderTop: "1px solid #f0f0f4", margin: "10px 0" }} />
  );
  return (
    <div style={cardStyle}>
      <span style={cardTitleStyle}>Itens Travados</span>

      <p style={subSectionTitleStyle}>
        Travadas{" "}
        <span
          style={{
            ...chipBaseStyle,
            background: "#fee2e2",
            color: "#dc2626",
            fontSize: 11,
          }}
        >
          {bloco.travadas.length}
        </span>
      </p>
      {bloco.travadas.length === 0 ? (
        <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>
          Nenhuma funcionalidade travada
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {bloco.travadas.map((f) => (
            <div key={f.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600, fontSize: 13, color: "#111116" }}>{f.titulo}</span>
              <span
                style={{
                  background: "#fee2e2",
                  color: "#dc2626",
                  borderRadius: 4,
                  padding: "2px 6px",
                  fontSize: 11,
                }}
              >
                {f.dias} dias
              </span>
            </div>
          ))}
        </div>
      )}

      {sep}

      <p style={subSectionTitleStyle}>
        Aguardando cliente{" "}
        <span
          style={{ ...chipBaseStyle, background: "#fef9c3", color: "#a16207", fontSize: 11 }}
        >
          {bloco.aguardando_cliente.length}
        </span>
      </p>
      {bloco.aguardando_cliente.length === 0 ? (
        <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>Nenhuma aguardando</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {bloco.aguardando_cliente.map((f) => (
            <div key={f.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600, fontSize: 13, color: "#111116" }}>{f.titulo}</span>
              <span
                style={{
                  background: "#fef9c3",
                  color: "#a16207",
                  borderRadius: 4,
                  padding: "2px 6px",
                  fontSize: 11,
                }}
              >
                {f.dias_uteis} d.u.
              </span>
            </div>
          ))}
        </div>
      )}

      {sep}

      <p style={subSectionTitleStyle}>
        Em ajuste{" "}
        <span
          style={{ ...chipBaseStyle, background: "#ffedd5", color: "#c2410c", fontSize: 11 }}
        >
          {bloco.em_ajuste.length}
        </span>
      </p>
      {bloco.em_ajuste.length === 0 ? (
        <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>Nenhuma em ajuste</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {bloco.em_ajuste.map((f) => (
            <span key={f.id} style={{ fontSize: 13, color: "#111116", fontWeight: 600 }}>
              {f.titulo}
            </span>
          ))}
        </div>
      )}

      {bloco.achados_criticos !== undefined && (
        <>
          {sep}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <p style={{ ...subSectionTitleStyle, marginTop: 12 }}>
              Achados do Revisor{" "}
              <span
                style={{
                  ...chipBaseStyle,
                  background: "#fee2e2",
                  color: "#dc2626",
                  fontSize: 11,
                }}
              >
                {bloco.achados_criticos.length}
              </span>
            </p>
            <div style={{ display: "flex", gap: 4 }}>
              {(["gerente", "tecnico"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setVisaoRelatorio(v)}
                  style={{
                    background: visaoRelatorio === v ? "#111116" : "#f1f5f9",
                    color: visaoRelatorio === v ? "#ffffff" : "#374151",
                    border: "none",
                    borderRadius: 6,
                    padding: "3px 10px",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {v === "gerente" ? "Gerente" : "Técnico"}
                </button>
              ))}
            </div>
          </div>

          {bloco.data_revisao && (
            <p style={{ fontSize: 11, color: "#9696a0", margin: "0 0 8px" }}>
              Revisão de {bloco.data_revisao}
            </p>
          )}

          {bloco.achados_criticos.length === 0 ? (
            <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>
              Nenhum achado crítico/alta com alta confiança
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {bloco.achados_criticos.map((a: AchadoCritico, i: number) => (
                <div key={i} style={{ borderLeft: "3px solid #dc2626", paddingLeft: 8 }}>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 2 }}>
                    <span
                      style={{
                        ...chipBaseStyle,
                        background: a.severidade === "CRITICA" ? "#fee2e2" : "#ffedd5",
                        color: a.severidade === "CRITICA" ? "#dc2626" : "#c2410c",
                        fontSize: 10,
                      }}
                    >
                      {a.severidade}
                    </span>
                    {visaoRelatorio === "tecnico" && (
                      <span style={{ fontSize: 11, color: "#9696a0", fontFamily: "monospace" }}>
                        {a.referencia}
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: 12, color: "#374151", margin: 0, lineHeight: 1.4 }}>
                    {visaoRelatorio === "gerente" ? a.descricao_gerente : a.descricao_tecnica}
                  </p>
                </div>
              ))}
            </div>
          )}

          {(bloco.relatorio_gerente || bloco.relatorio_tecnico) && (
            <div
              style={{
                marginTop: 10,
                background: "#f7f7fa",
                borderRadius: 8,
                padding: "10px 12px",
              }}
            >
              <p
                style={{
                  fontSize: 12,
                  color: "#374151",
                  margin: 0,
                  lineHeight: 1.5,
                  whiteSpace: "pre-wrap",
                }}
              >
                {visaoRelatorio === "gerente" ? bloco.relatorio_gerente : bloco.relatorio_tecnico}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function BlocoCCard({ bloco }: { bloco: PainelData["bloco_c"] }) {
  return (
    <div style={cardStyle}>
      <span style={cardTitleStyle}>Métricas de Fluxo</span>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div>
          <p style={metricLabelStyle}>WIP agora</p>
          <p style={{ ...metricValueStyle, margin: 0 }}>{bloco.wip}</p>
          <p style={{ fontSize: 11, color: "#9696a0", margin: "2px 0 0" }}>
            funcionalidades em andamento ou em ajuste
          </p>
        </div>
        <div>
          <p style={metricLabelStyle}>Throughput</p>
          <p style={{ ...metricValueStyle, margin: 0, fontSize: 18 }}>
            {bloco.throughput_por_semana ?? "—"}
            <span style={{ fontSize: 12, color: "#6a6a7a", fontWeight: 400 }}> / semana</span>
          </p>
        </div>
        {bloco.total_concluidas === 0 ? (
          <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>
            Nenhuma funcionalidade concluída — cycle time indisponível
          </p>
        ) : (
          <>
            <div>
              <p style={metricLabelStyle}>Cycle time (p50)</p>
              <p style={{ ...metricValueStyle, margin: 0, fontSize: 18 }}>
                {bloco.cycle_time_p50_dias ?? "—"}
                <span style={{ fontSize: 12, color: "#6a6a7a", fontWeight: 400 }}> dias</span>
              </p>
            </div>
            <div>
              <p style={metricLabelStyle}>Cycle time (p85)</p>
              <p style={{ ...metricValueStyle, margin: 0, fontSize: 18 }}>
                {bloco.cycle_time_p85_dias ?? "—"}
                <span style={{ fontSize: 12, color: "#6a6a7a", fontWeight: 400 }}> dias</span>
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function BlocoDCard({
  bloco,
  expandedFase,
  setExpandedFase,
}: {
  bloco: BlocoD;
  expandedFase: string | null;
  setExpandedFase: (f: string | null) => void;
}) {
  const fases = Object.entries(bloco.fases_resumo);
  return (
    <div style={cardStyle}>
      <span style={cardTitleStyle}>Tempo por Fase</span>
      <div style={{ marginBottom: 12 }}>
        <p style={metricLabelStyle}>Eficiência de fluxo</p>
        <p style={{ ...metricValueStyle, margin: 0 }}>
          {bloco.eficiencia_fluxo_pct ?? "—"}
          {bloco.eficiencia_fluxo_pct != null && "%"}
        </p>
      </div>
      {fases.length === 0 ? (
        <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>
          Sem transições de status registradas ainda
        </p>
      ) : (
        fases.map(([fase, resumo]) => (
          <div key={fase}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                cursor: "pointer",
                padding: "8px 0",
                borderBottom: "1px solid #f0f0f4",
              }}
            >
              <span style={{ fontWeight: 600, fontSize: 13, color: "#111116" }}>{fase}</span>
              <span style={{ fontSize: 12, color: "#6a6a7a" }}>
                {resumo.media_dias} dias (média) · {resumo.p85_dias ?? "—"} p85
              </span>
              <button
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: 12, color: "#9696a0" }}
                onClick={() => setExpandedFase(expandedFase === fase ? null : fase)}
              >
                {expandedFase === fase ? "▲ fechar" : "▼ ver detalhe"}
              </button>
            </div>
            {expandedFase === fase && (
              <div
                style={{
                  background: "#f7f7fa",
                  borderRadius: 8,
                  padding: "10px 12px",
                  marginTop: 4,
                  marginBottom: 4,
                }}
              >
                {bloco.detalhe_por_funcionalidade.filter(
                  (d) => d.tempos_por_fase[fase] != null
                ).length === 0 ? (
                  <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>
                    Sem dados de duração para esta fase
                  </p>
                ) : (
                  bloco.detalhe_por_funcionalidade
                    .filter((d) => d.tempos_por_fase[fase] != null)
                    .map((d) => (
                      <div key={d.id} style={{ display: "flex", gap: 8, marginBottom: 4 }}>
                        <span style={{ fontSize: 12, color: "#374151" }}>{d.titulo}</span>
                        <span style={{ fontSize: 12, color: "#6a6a7a" }}>
                          {d.tempos_por_fase[fase]} dias
                        </span>
                      </div>
                    ))
                )}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function KanbanCard({ f, allSprints }: { f: FuncionalidadeResponse; allSprints: string[] }) {
  const prioColor: Record<string, { bg: string; color: string }> = {
    alta: { bg: "#fee2e2", color: "#dc2626" },
    media: { bg: "#fef9c3", color: "#a16207" },
    baixa: { bg: "#f1f5f9", color: "#64748b" },
  };
  const prio = prioColor[f.prioridade] ?? prioColor.baixa;
  const sprintsToShow = allSprints.length > 0 ? allSprints : f.sprint_alvo ? [f.sprint_alvo] : [];

  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #e8e8ed",
        borderRadius: 10,
        padding: "12px 14px",
        marginBottom: 8,
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <span style={{ fontSize: 13, fontWeight: 600, color: "#111116", lineHeight: 1.4 }}>
        {f.titulo}
      </span>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ ...chipBaseStyle, background: prio.bg, color: prio.color }}>
          {f.prioridade}
        </span>
        {sprintsToShow.map((s) => (
          <span key={s} style={{ ...chipBaseStyle, background: "#ede9fe", color: "#7c3aed" }}>
            Sprint {s}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function PainelTab({ projectId, sprints, onNavigateToConfig }: Props) {
  const [data, setData] = useState<PainelData | null>(null);
  const [funcionalidades, setFuncionalidades] = useState<FuncionalidadeResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sprintSelecionada, setSprintSelecionada] = useState<number>(
    sprints.length > 0 ? Math.max(...sprints.map((s) => s.numero)) : 1
  );
  const [expandedFase, setExpandedFase] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([getPainel(projectId), listFuncionalidades(projectId)])
      .then(([d, funcs]) => {
        setData(d);
        setFuncionalidades(funcs);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <section style={{ ...cardStyle, marginBottom: 14 }}>
        <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>Carregando painel…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section style={{ ...cardStyle, marginBottom: 14 }}>
        <p style={{ color: "#dc2626", fontSize: 14, margin: 0 }}>{error}</p>
      </section>
    );
  }

  if (!data) return null;

  const sortedSprints = [...sprints].sort((a, b) => b.numero - a.numero);

  const funcsDaSprint = funcionalidades.filter(
    (f) => f.sprint_alvo !== null && f.sprint_alvo !== undefined && f.sprint_alvo === String(sprintSelecionada)
  );

  const planejado = funcsDaSprint.filter((f) => f.status === "nao_iniciada");
  const emAndamento = funcsDaSprint.filter(
    (f) => f.status === "em_andamento" || f.status === "em_ajuste"
  );
  const concluido = funcsDaSprint.filter((f) => f.status === "concluida");

  const allSprintsByFuncional: Record<string, string[]> = {};
  for (const f of funcionalidades) {
    if (!f.sprint_alvo) continue;
    if (!allSprintsByFuncional[f.id_funcional]) allSprintsByFuncional[f.id_funcional] = [];
    if (!allSprintsByFuncional[f.id_funcional].includes(f.sprint_alvo)) {
      allSprintsByFuncional[f.id_funcional].push(f.sprint_alvo);
    }
  }
  for (const key of Object.keys(allSprintsByFuncional)) {
    allSprintsByFuncional[key].sort();
  }

  const colHeaderStyle = (color: string): React.CSSProperties => ({
    fontSize: 13,
    fontWeight: 700,
    color,
  });

  return (
    <div>
      <h2 style={{ fontSize: 16, fontWeight: 700, color: "#111116", marginBottom: 16 }}>
        Painel do Projeto
      </h2>

      {/* 4-block grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 14,
          marginBottom: 24,
        }}
      >
        <BlocoACard bloco={data.bloco_a} onNavigateToConfig={onNavigateToConfig} />
        <BlocoBCard bloco={data.bloco_b} />
        <BlocoCCard bloco={data.bloco_c} />
        <BlocoDCard
          bloco={data.bloco_d}
          expandedFase={expandedFase}
          setExpandedFase={setExpandedFase}
        />
      </div>

      {/* Kanban */}
      <div style={{ ...cardStyle, background: "#f7f7fa" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "#111116", margin: 0 }}>
            Kanban de Sprint
          </h3>
          <select
            value={String(sprintSelecionada)}
            onChange={(e) => setSprintSelecionada(Number(e.target.value))}
            style={{
              border: "1px solid #e4e4ea",
              borderRadius: 8,
              padding: "6px 12px",
              fontSize: 13,
              background: "#ffffff",
              color: "#111116",
            }}
          >
            {sortedSprints.length === 0 ? (
              <option disabled>Sem sprints</option>
            ) : (
              sortedSprints.map((s) => (
                <option key={s.id} value={String(s.numero)}>
                  Sprint {s.numero}
                </option>
              ))
            )}
          </select>
        </div>

        {sortedSprints.length === 0 ? (
          <p style={{ color: "#9696a0", fontSize: 13 }}>Nenhuma sprint cadastrada.</p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 16 }}>
            {/* Planejado */}
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <span style={colHeaderStyle("#374151")}>Planejado</span>
                <span
                  style={{ ...chipBaseStyle, background: "#f1f5f9", color: "#64748b", fontSize: 11 }}
                >
                  {planejado.length}
                </span>
              </div>
              {planejado.length === 0 ? (
                <div style={{ padding: "20px 0", textAlign: "center" }}>
                  <span style={{ color: "#b8b8c0", fontSize: 12 }}>Nenhuma funcionalidade</span>
                </div>
              ) : (
                planejado.map((f) => (
                  <KanbanCard
                    key={f.id}
                    f={f}
                    allSprints={allSprintsByFuncional[f.id_funcional] ?? []}
                  />
                ))
              )}
            </div>

            {/* Em andamento */}
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={colHeaderStyle("#a16207")}>Em andamento</span>
                <span
                  style={{ ...chipBaseStyle, background: "#fef9c3", color: "#a16207", fontSize: 11 }}
                >
                  {emAndamento.length}
                </span>
              </div>
              <p style={{ fontSize: 11, color: "#9696a0", margin: "0 0 8px" }}>inclui em ajuste</p>
              {emAndamento.length === 0 ? (
                <div style={{ padding: "20px 0", textAlign: "center" }}>
                  <span style={{ color: "#b8b8c0", fontSize: 12 }}>Nenhuma funcionalidade</span>
                </div>
              ) : (
                emAndamento.map((f) => (
                  <KanbanCard
                    key={f.id}
                    f={f}
                    allSprints={allSprintsByFuncional[f.id_funcional] ?? []}
                  />
                ))
              )}
            </div>

            {/* Concluído */}
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <span style={colHeaderStyle("#16a34a")}>Concluído</span>
                <span
                  style={{ ...chipBaseStyle, background: "#dcfce7", color: "#16a34a", fontSize: 11 }}
                >
                  {concluido.length}
                </span>
              </div>
              {concluido.length === 0 ? (
                <div style={{ padding: "20px 0", textAlign: "center" }}>
                  <span style={{ color: "#b8b8c0", fontSize: 12 }}>Nenhuma funcionalidade</span>
                </div>
              ) : (
                concluido.map((f) => (
                  <KanbanCard
                    key={f.id}
                    f={f}
                    allSprints={allSprintsByFuncional[f.id_funcional] ?? []}
                  />
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
