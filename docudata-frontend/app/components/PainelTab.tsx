"use client";

import { useEffect, useState } from "react";
import {
  getPainel,
  listFuncionalidades,
  getSprintFuncionalidades,
  createSprintFuncionalidades,
  updateSprintFuncionalidade,
  updateContrato,
  type BlocoD,
  type FuncionalidadeResponse,
  type PainelData,
  type Project,
  type SprintFuncionalidade,
  type SprintWithStatus,
} from "../lib/api";

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
  project: Project;
  onProjectUpdated?: (updated: Project) => void;
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

const inputSmStyle: React.CSSProperties = {
  padding: "6px 10px",
  border: "1px solid #e4e4ea",
  borderRadius: 7,
  fontSize: 13,
  color: "#111116",
  background: "#ffffff",
  width: "100%",
  boxSizing: "border-box",
};

const labelSmStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 700,
  color: "#9696a0",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  marginBottom: 4,
};

function BlocoACard({
  bloco,
  project,
  onSaved,
}: {
  bloco: PainelData["bloco_a"];
  project: Project;
  onSaved?: (updated: Project) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [dataInicio, setDataInicio] = useState(project.data_inicio ?? "");
  const [dataFim, setDataFim] = useState(project.data_fim_contratada ?? "");
  const [tolerancia, setTolerancia] = useState(
    project.tolerancia_desvio_pontos != null ? String(project.tolerancia_desvio_pontos) : ""
  );
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

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
      });
      onSaved?.(updated);
      setEditing(false);
    } catch {
      setErr("Erro ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={cardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <span style={{ ...cardTitleStyle, marginBottom: 0 }}>Tempo × Escopo</span>
        <button
          onClick={() => { setEditing((v) => !v); setErr(""); }}
          style={{
            background: "none",
            border: "none",
            fontSize: 12,
            color: "#9696a0",
            cursor: "pointer",
            padding: 0,
            textDecoration: "underline",
          }}
        >
          {editing ? "Cancelar" : (bloco.sem_dados ? "Configurar" : "Editar")}
        </button>
      </div>

      {editing ? (
        <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div>
            <label style={labelSmStyle}>Data início do projeto</label>
            <input type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} style={inputSmStyle} required />
          </div>
          <div>
            <label style={labelSmStyle}>Data fim contratada</label>
            <input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} style={inputSmStyle} required />
          </div>
          <div>
            <label style={labelSmStyle}>Tolerância de desvio (pontos) <span style={{ fontWeight: 400 }}>— opcional</span></label>
            <input
              type="number"
              min={0}
              value={tolerancia}
              onChange={(e) => setTolerancia(e.target.value)}
              placeholder="ex: 5"
              style={inputSmStyle}
            />
          </div>
          {err && <p style={{ fontSize: 12, color: "#dc2626", margin: 0 }}>{err}</p>}
          <button
            type="submit"
            disabled={saving}
            style={{
              background: "#4ade80",
              color: "#0a0a0a",
              border: "none",
              borderRadius: 7,
              padding: "8px 16px",
              fontSize: 13,
              fontWeight: 700,
              cursor: saving ? "not-allowed" : "pointer",
              opacity: saving ? 0.6 : 1,
              alignSelf: "flex-start",
            }}
          >
            {saving ? "Salvando..." : "Salvar"}
          </button>
        </form>
      ) : bloco.sem_dados ? (
        <p style={{ fontSize: 13, color: "#9696a0", margin: 0 }}>
          Clique em <strong>Configurar</strong> para definir as datas do contrato.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            { label: "Prazo consumido", value: bloco.pct_prazo_consumido },
            { label: "Escopo concluído", value: bloco.pct_escopo_concluido },
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
  const sep = (
    <hr style={{ border: "none", borderTop: "1px solid #f0f0f4", margin: "10px 0" }} />
  );
  return (
    <div style={cardStyle}>
      <span style={cardTitleStyle}>
        Itens em Atenção
        <InfoTooltip text="Travadas: funcionalidades paradas há muitos dias sem avanço — precisam de atenção ou desbloqueio." />
      </span>

      <p style={subSectionTitleStyle}>
        Travadas{" "}
        <span style={{ ...chipBaseStyle, background: "#fee2e2", color: "#dc2626", fontSize: 11 }}>
          {bloco.travadas.length}
        </span>
      </p>
      {bloco.travadas.length === 0 ? (
        <p style={{ fontSize: 12, color: "#9696a0", margin: 0 }}>Nenhuma funcionalidade travada</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {bloco.travadas.map((f) => (
            <div key={f.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600, fontSize: 13, color: "#111116" }}>{f.titulo}</span>
              <span style={{ background: "#fee2e2", color: "#dc2626", borderRadius: 4, padding: "2px 6px", fontSize: 11 }}>
                {f.dias} dias
              </span>
            </div>
          ))}
        </div>
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
            funcionalidades em andamento
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
      <span style={cardTitleStyle}>
        Tempo por Fase
        <InfoTooltip text="Quanto tempo cada funcionalidade ficou em cada estado (planejada, em andamento, concluída). Eficiência de fluxo = % do tempo efetivamente trabalhado vs. tempo total." />
      </span>
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

function InfoTooltip({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span
      style={{ position: "relative", display: "inline-flex", marginLeft: 5, verticalAlign: "middle" }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <span style={{
        cursor: "help",
        fontSize: 10,
        fontWeight: 700,
        color: "#9696a0",
        border: "1px solid #d1d5db",
        borderRadius: "50%",
        width: 15,
        height: 15,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}>
        i
      </span>
      {show && (
        <div style={{
          position: "absolute",
          top: 20,
          left: "50%",
          transform: "translateX(-50%)",
          background: "#1e293b",
          color: "#f1f5f9",
          borderRadius: 8,
          padding: "8px 12px",
          fontSize: 11,
          width: 230,
          zIndex: 200,
          lineHeight: 1.6,
          boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
          pointerEvents: "none",
        }}>
          {text}
        </div>
      )}
    </span>
  );
}

function KanbanCard({ f, allSprints }: { f: FuncionalidadeResponse; allSprints: string[] }) {
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
      {sprintsToShow.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          {sprintsToShow.map((s) => (
            <span key={s} style={{ ...chipBaseStyle, background: "#ede9fe", color: "#7c3aed" }}>
              Sprint {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PainelTab({ projectId, sprints, project, onProjectUpdated }: Props) {
  const [data, setData] = useState<PainelData | null>(null);
  const [funcionalidades, setFuncionalidades] = useState<FuncionalidadeResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sprintSelecionada, setSprintSelecionada] = useState<number>(
    sprints.length > 0 ? Math.max(...sprints.map((s) => s.numero)) : 1
  );
  const [sprintFuncs, setSprintFuncs] = useState<SprintFuncionalidade[]>([]);
  const [expandedFase, setExpandedFase] = useState<string | null>(null);
  const [dragFuncId, setDragFuncId] = useState<string | null>(null);
  const [addingFunc, setAddingFunc] = useState(false);
  const [addFuncId, setAddFuncId] = useState("");
  const [kanbanSaving, setKanbanSaving] = useState(false);

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

  const selectedSprintObj = sprints.find((s) => s.numero === sprintSelecionada);

  useEffect(() => {
    if (!selectedSprintObj) { setSprintFuncs([]); return; }
    getSprintFuncionalidades(selectedSprintObj.id)
      .then(setSprintFuncs)
      .catch(() => setSprintFuncs([]));
  }, [selectedSprintObj?.id]);

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

  const sfByFuncId = new Map(sprintFuncs.map((sf) => [sf.funcionalidade_id, sf]));
  const funcsNotInSprint = funcionalidades.filter((f) => !sfByFuncId.has(f.id));

  async function handleDrop(targetStatus: "em_andamento" | "concluida") {
    if (!dragFuncId || !selectedSprintObj) { setDragFuncId(null); return; }
    const sf = sfByFuncId.get(dragFuncId);
    if (!sf || sf.status === targetStatus) { setDragFuncId(null); return; }
    setKanbanSaving(true);
    try {
      await updateSprintFuncionalidade(sf.id, { status: targetStatus });
      setSprintFuncs(await getSprintFuncionalidades(selectedSprintObj.id));
    } finally {
      setKanbanSaving(false);
      setDragFuncId(null);
    }
  }

  async function handleAddToSprint() {
    if (!addFuncId || !selectedSprintObj) return;
    setKanbanSaving(true);
    try {
      await createSprintFuncionalidades(selectedSprintObj.id, [{ funcionalidade_id: addFuncId, tasks: [] }]);
      setSprintFuncs(await getSprintFuncionalidades(selectedSprintObj.id));
      setAddFuncId("");
      setAddingFunc(false);
    } finally {
      setKanbanSaving(false);
    }
  }

  const sortedSprints = [...sprints].sort((a, b) => b.numero - a.numero);

  // Resolve sprint_funcionalidade → FuncionalidadeResponse using the funcionalidades list
  function sfToFunc(sf: SprintFuncionalidade): FuncionalidadeResponse | null {
    return funcionalidades.find((f) => f.id === sf.funcionalidade_id) ?? null;
  }

  let planejado: FuncionalidadeResponse[];
  let emAndamento: FuncionalidadeResponse[];
  let concluido: FuncionalidadeResponse[];

  if (sprintFuncs.length > 0) {
    // New planning flow: use sprint_funcionalidades as source of truth
    planejado = [];
    emAndamento = sprintFuncs
      .filter((sf) => sf.status === "em_andamento")
      .map(sfToFunc)
      .filter((f): f is FuncionalidadeResponse => f !== null);
    concluido = sprintFuncs
      .filter((sf) => sf.status === "concluida")
      .map(sfToFunc)
      .filter((f): f is FuncionalidadeResponse => f !== null);
  } else {
    // Fallback: old sprint_alvo-based filtering
    const funcsDaSprint = funcionalidades.filter(
      (f) => f.sprint_alvo !== null && f.sprint_alvo !== undefined && f.sprint_alvo === String(sprintSelecionada)
    );
    planejado = funcsDaSprint.filter((f) => f.status === "nao_iniciada");
    emAndamento = funcsDaSprint.filter((f) => f.status === "em_andamento");
    concluido = funcsDaSprint.filter((f) => f.status === "concluida");
  }

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
        <BlocoACard
          bloco={data.bloco_a}
          project={project}
          onSaved={(updated) => {
            onProjectUpdated?.(updated);
            getPainel(projectId).then(setData).catch(() => {});
          }}
        />
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
                <span style={{ ...chipBaseStyle, background: "#f1f5f9", color: "#64748b", fontSize: 11 }}>
                  {planejado.length}
                </span>
              </div>
              {planejado.length === 0 ? (
                <div style={{ padding: "20px 0", textAlign: "center" }}>
                  <span style={{ color: "#b8b8c0", fontSize: 12 }}>Nenhuma funcionalidade</span>
                </div>
              ) : (
                planejado.map((f) => (
                  <KanbanCard key={f.id} f={f} allSprints={allSprintsByFuncional[f.id_funcional] ?? []} />
                ))
              )}
            </div>

            {/* Em andamento — drop target */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop("em_andamento")}
              style={{ opacity: kanbanSaving ? 0.6 : 1, transition: "opacity 0.1s" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={colHeaderStyle("#a16207")}>Em andamento</span>
                <span style={{ ...chipBaseStyle, background: "#fef9c3", color: "#a16207", fontSize: 11 }}>
                  {emAndamento.length}
                </span>
              </div>
              {emAndamento.length === 0 ? (
                <div style={{ padding: "20px 0", textAlign: "center" }}>
                  <span style={{ color: "#b8b8c0", fontSize: 12 }}>Nenhuma funcionalidade</span>
                </div>
              ) : (
                emAndamento.map((f) => (
                  <div
                    key={f.id}
                    draggable
                    onDragStart={() => setDragFuncId(f.id)}
                    onDragEnd={() => setDragFuncId(null)}
                    style={{ cursor: "grab" }}
                  >
                    <KanbanCard f={f} allSprints={allSprintsByFuncional[f.id_funcional] ?? []} />
                  </div>
                ))
              )}
              {/* Adicionar manualmente */}
              {!addingFunc ? (
                <button
                  onClick={() => setAddingFunc(true)}
                  style={{ marginTop: 8, width: "100%", background: "transparent", border: "1px dashed #cbd5e1", borderRadius: 8, padding: "7px 0", fontSize: 12, color: "#64748b", cursor: "pointer" }}
                >
                  + Adicionar funcionalidade
                </button>
              ) : (
                <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
                  <select
                    value={addFuncId}
                    onChange={(e) => setAddFuncId(e.target.value)}
                    style={{ width: "100%", border: "1px solid #e2e8f0", borderRadius: 8, padding: "7px 10px", fontSize: 13, background: "#fff" }}
                  >
                    <option value="">Selecione…</option>
                    {funcsNotInSprint.map((f) => (
                      <option key={f.id} value={f.id}>{f.id_funcional} — {f.titulo}</option>
                    ))}
                  </select>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      onClick={handleAddToSprint}
                      disabled={!addFuncId || kanbanSaving}
                      style={{ flex: 1, background: "#0f172a", color: "#fff", border: "none", borderRadius: 8, padding: "7px 0", fontSize: 12, fontWeight: 700, cursor: "pointer", opacity: (!addFuncId || kanbanSaving) ? 0.5 : 1 }}
                    >
                      {kanbanSaving ? "Adicionando…" : "Confirmar"}
                    </button>
                    <button
                      onClick={() => { setAddingFunc(false); setAddFuncId(""); }}
                      style={{ background: "#f1f5f9", color: "#64748b", border: "1px solid #e2e8f0", borderRadius: 8, padding: "7px 12px", fontSize: 12, cursor: "pointer" }}
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Concluído — drop target */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop("concluida")}
              style={{ opacity: kanbanSaving ? 0.6 : 1, transition: "opacity 0.1s" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <span style={colHeaderStyle("#16a34a")}>Concluído</span>
                <span style={{ ...chipBaseStyle, background: "#dcfce7", color: "#16a34a", fontSize: 11 }}>
                  {concluido.length}
                </span>
              </div>
              {concluido.length === 0 ? (
                <div style={{ padding: "20px 0", textAlign: "center" }}>
                  <span style={{ color: "#b8b8c0", fontSize: 12 }}>Nenhuma funcionalidade</span>
                </div>
              ) : (
                concluido.map((f) => (
                  <div
                    key={f.id}
                    draggable
                    onDragStart={() => setDragFuncId(f.id)}
                    onDragEnd={() => setDragFuncId(null)}
                    style={{ cursor: "grab" }}
                  >
                    <KanbanCard f={f} allSprints={allSprintsByFuncional[f.id_funcional] ?? []} />
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
