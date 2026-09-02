"use client";

import { useEffect, useState, useCallback } from "react";
import TutorialBanner from "./TutorialBanner";
import {
  listTasksKanban,
  createTaskKanban,
  patchTaskKanban,
  moverTaskKanban,
  deleteTaskKanban,
  listTaskTransicoesKanban,
  listTaskSugestoes,
  resolveTaskSugestao,
  type TaskKanbanResponse,
  type TaskTransicaoKanban,
  type TaskSugestaoResponse,
  type OperacionalResponse,
  type FuncionalidadeResponse,
  type SprintWithStatus,
} from "../lib/api";

interface Props {
  projectId: string;
  sprints: SprintWithStatus[];
  operacionais: OperacionalResponse[];
  funcionalidades: FuncionalidadeResponse[];
}

type Coluna = "planejado" | "em_andamento" | "concluida";

const COLUNAS: { id: Coluna; label: string; color: string; bg: string }[] = [
  { id: "planejado", label: "Planejado", color: "#374151", bg: "#f1f5f9" },
  { id: "em_andamento", label: "Em andamento", color: "#a16207", bg: "#fef9c3" },
  { id: "concluida", label: "Concluída", color: "#166534", bg: "#dcfce7" },
];

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 10,
  padding: "12px 14px",
  marginBottom: 8,
  cursor: "pointer",
  display: "flex",
  flexDirection: "column",
  gap: 6,
};

const chip: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "3px 9px",
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 600,
};

const inputSt: React.CSSProperties = {
  padding: "7px 10px",
  border: "1px solid #e4e4ea",
  borderRadius: 7,
  fontSize: 13,
  color: "#111116",
  background: "#fff",
  width: "100%",
  boxSizing: "border-box",
};

const btnPrimary: React.CSSProperties = {
  background: "#0f172a",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  padding: "8px 18px",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
};

const btnGhost: React.CSSProperties = {
  background: "none",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  padding: "7px 14px",
  fontSize: 12,
  fontWeight: 600,
  color: "#374151",
  cursor: "pointer",
};

// ---------------------------------------------------------------------------
// Modal Nova/Editar Task

interface TaskModalProps {
  mode: "create" | "edit";
  task?: TaskKanbanResponse;
  projectId: string;
  sprints: SprintWithStatus[];
  operacionais: OperacionalResponse[];
  funcionalidades: FuncionalidadeResponse[];
  defaultSprintId?: string;
  onClose: () => void;
  onSaved: (t: TaskKanbanResponse) => void;
  onDeleted?: (id: string) => void;
}

function TaskModal({
  mode, task, projectId, sprints, operacionais, funcionalidades,
  defaultSprintId, onClose, onSaved, onDeleted,
}: TaskModalProps) {
  const [titulo, setTitulo] = useState(task?.titulo ?? "");
  const [descricao, setDescricao] = useState(task?.descricao ?? "");
  const [pontos, setPontos] = useState(task?.pontos ?? 1);
  const [sprintId, setSprintId] = useState(task?.sprint_id ?? defaultSprintId ?? "");
  const [operacionalId, setOperacionalId] = useState(task?.operacional_id ?? "");
  const [funcId, setFuncId] = useState(task?.funcionalidade_id ?? "");
  const [bloqueado, setBloqueado] = useState(task?.bloqueado ?? false);
  const [motivoBloqueio, setMotivoBloqueio] = useState(task?.motivo_bloqueio ?? "");
  const [checklist, setChecklist] = useState<{ texto: string; done: boolean }[]>(
    task?.checklist ?? []
  );
  const [novoItem, setNovoItem] = useState("");
  const [transicoes, setTransicoes] = useState<TaskTransicaoKanban[]>([]);
  const [loadingHist, setLoadingHist] = useState(false);
  const [showHist, setShowHist] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (mode === "edit" && task && showHist) {
      setLoadingHist(true);
      listTaskTransicoesKanban(task.id)
        .then(setTransicoes)
        .catch(() => setTransicoes([]))
        .finally(() => setLoadingHist(false));
    }
  }, [showHist, task?.id, mode]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!titulo.trim()) { setErr("Título obrigatório."); return; }
    if (pontos < 1) { setErr("Pontos deve ser ≥ 1."); return; }
    setSaving(true);
    setErr("");
    try {
      let saved: TaskKanbanResponse;
      if (mode === "create") {
        saved = await createTaskKanban({
          project_id: projectId,
          titulo: titulo.trim(),
          descricao: descricao.trim() || undefined,
          pontos,
          sprint_id: sprintId || undefined,
          operacional_id: operacionalId || undefined,
          funcionalidade_id: funcId || undefined,
        });
      } else {
        saved = await patchTaskKanban(task!.id, {
          titulo: titulo.trim(),
          descricao: descricao.trim() || undefined,
          pontos,
          sprint_id: sprintId || undefined,
          operacional_id: operacionalId || undefined,
          funcionalidade_id: funcId || undefined,
          bloqueado,
          motivo_bloqueio: bloqueado ? motivoBloqueio.trim() || undefined : undefined,
          checklist,
        });
      }
      onSaved(saved);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!task || !confirm(`Excluir "${task.titulo}"?`)) return;
    setSaving(true);
    try {
      await deleteTaskKanban(task.id);
      onDeleted?.(task.id);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao excluir");
      setSaving(false);
    }
  }

  function addChecklistItem() {
    if (!novoItem.trim()) return;
    setChecklist((prev) => [...prev, { texto: novoItem.trim(), done: false }]);
    setNovoItem("");
  }

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: "#fff", borderRadius: 16, padding: "28px 32px",
        width: "100%", maxWidth: 520, maxHeight: "90vh", overflowY: "auto",
        boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
      }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#0f172a", margin: "0 0 20px" }}>
          {mode === "create" ? "Nova task" : "Editar task"}
        </h3>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={labelSt}>Título *</label>
            <input value={titulo} onChange={(e) => setTitulo(e.target.value)} style={inputSt} required />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 80px", gap: 10 }}>
            <div>
              <label style={labelSt}>Sprint</label>
              <select value={sprintId} onChange={(e) => setSprintId(e.target.value)} style={inputSt}>
                <option value="">Sem sprint</option>
                {sprints.map((s) => (
                  <option key={s.id} value={s.id}>Sprint {s.numero}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelSt}>Pontos *</label>
              <input
                type="number" min={1} value={pontos}
                onChange={(e) => setPontos(Number(e.target.value))}
                style={inputSt} required
              />
            </div>
          </div>

          <div>
            <label style={labelSt}>Operacional</label>
            <select value={operacionalId} onChange={(e) => setOperacionalId(e.target.value)} style={inputSt}>
              <option value="">Sem operacional</option>
              {operacionais.filter((o) => o.ativo).map((o) => (
                <option key={o.id} value={o.id}>{o.nome}{o.papel ? ` — ${o.papel}` : ""}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={labelSt}>Funcionalidade</label>
            <select value={funcId} onChange={(e) => setFuncId(e.target.value)} style={inputSt}>
              <option value="">Sem funcionalidade</option>
              {funcionalidades.map((f) => (
                <option key={f.id} value={f.id}>{f.id_funcional} — {f.titulo}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={labelSt}>Descrição</label>
            <textarea
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              rows={2}
              style={{ ...inputSt, resize: "vertical" }}
            />
          </div>

          {mode === "edit" && (
            <>
              {/* Bloqueado */}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input
                  type="checkbox"
                  id="bloqueado"
                  checked={bloqueado}
                  onChange={(e) => setBloqueado(e.target.checked)}
                />
                <label htmlFor="bloqueado" style={{ fontSize: 13, fontWeight: 600, color: "#374151", cursor: "pointer" }}>
                  Bloqueada
                </label>
              </div>
              {bloqueado && (
                <div>
                  <label style={labelSt}>Motivo do bloqueio</label>
                  <input
                    value={motivoBloqueio}
                    onChange={(e) => setMotivoBloqueio(e.target.value)}
                    placeholder="Descreva o bloqueio..."
                    style={inputSt}
                  />
                </div>
              )}

              {/* Checklist */}
              <div>
                <label style={labelSt}>Checklist</label>
                {checklist.map((item, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <input
                      type="checkbox"
                      checked={item.done}
                      onChange={(e) => {
                        const copy = [...checklist];
                        copy[i] = { ...copy[i], done: e.target.checked };
                        setChecklist(copy);
                      }}
                    />
                    <span style={{ flex: 1, fontSize: 13, color: item.done ? "#9696a0" : "#111116", textDecoration: item.done ? "line-through" : "none" }}>
                      {item.texto}
                    </span>
                    <button
                      type="button"
                      onClick={() => setChecklist((prev) => prev.filter((_, j) => j !== i))}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#dc2626", fontSize: 14, padding: 0 }}
                    >
                      ×
                    </button>
                  </div>
                ))}
                <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                  <input
                    value={novoItem}
                    onChange={(e) => setNovoItem(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addChecklistItem(); } }}
                    placeholder="Novo item..."
                    style={{ ...inputSt, flex: 1 }}
                  />
                  <button type="button" onClick={addChecklistItem} style={{ ...btnGhost, padding: "7px 12px" }}>+</button>
                </div>
              </div>

              {/* Histórico */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowHist((v) => !v)}
                  style={{ background: "none", border: "none", fontSize: 12, color: "#9696a0", cursor: "pointer", textDecoration: "underline", padding: 0 }}
                >
                  {showHist ? "Ocultar histórico" : "Ver histórico de transições"}
                </button>
                {showHist && (
                  <div style={{ marginTop: 10 }}>
                    {loadingHist ? (
                      <p style={{ fontSize: 12, color: "#9696a0" }}>Carregando...</p>
                    ) : transicoes.length === 0 ? (
                      <p style={{ fontSize: 12, color: "#9696a0" }}>Sem transições registradas.</p>
                    ) : (
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                        <thead>
                          <tr style={{ color: "#9696a0" }}>
                            <th style={{ textAlign: "left", padding: "4px 6px" }}>Campo</th>
                            <th style={{ textAlign: "left", padding: "4px 6px" }}>De → Para</th>
                            <th style={{ textAlign: "left", padding: "4px 6px" }}>Tempo anterior</th>
                          </tr>
                        </thead>
                        <tbody>
                          {transicoes.map((t) => (
                            <tr key={t.id} style={{ borderTop: "1px solid #f0f0f4" }}>
                              <td style={{ padding: "4px 6px", color: "#374151" }}>{t.campo}</td>
                              <td style={{ padding: "4px 6px", color: "#111116" }}>{t.de ?? "—"} → {t.para ?? "—"}</td>
                              <td style={{ padding: "4px 6px", color: "#9696a0" }}>
                                {t.duracao_fase_anterior_segundos != null
                                  ? formatDuration(t.duracao_fase_anterior_segundos)
                                  : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          {err && <p style={{ fontSize: 12, color: "#dc2626", margin: 0 }}>{err}</p>}

          <div style={{ display: "flex", gap: 10, justifyContent: "space-between", marginTop: 4 }}>
            {mode === "edit" && (
              <button type="button" onClick={handleDelete} disabled={saving}
                style={{ background: "none", border: "none", fontSize: 12, color: "#dc2626", cursor: "pointer", padding: 0, textDecoration: "underline" }}>
                Excluir
              </button>
            )}
            <div style={{ display: "flex", gap: 10, marginLeft: "auto" }}>
              <button type="button" onClick={onClose} style={btnGhost}>Cancelar</button>
              <button type="submit" disabled={saving} style={{ ...btnPrimary, opacity: saving ? 0.6 : 1 }}>
                {saving ? "Salvando…" : mode === "create" ? "Criar" : "Salvar"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

const labelSt: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 700,
  color: "#9696a0",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  marginBottom: 4,
};

function formatDuration(sec: number): string {
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.round(sec / 60)}min`;
  const h = Math.floor(sec / 3600);
  const m = Math.round((sec % 3600) / 60);
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

// ---------------------------------------------------------------------------
// Task card

function TaskCard({
  task, operacionais, onDragStart, onDragEnd, onClick,
}: {
  task: TaskKanbanResponse;
  operacionais: OperacionalResponse[];
  onDragStart: () => void;
  onDragEnd: () => void;
  onClick: () => void;
}) {
  const op = operacionais.find((o) => o.id === task.operacional_id);
  const done = task.checklist.filter((i) => i.done).length;
  const total = task.checklist.length;

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onClick}
      style={{
        ...card,
        borderLeft: task.bloqueado ? "3px solid #ef4444" : card.border as string,
        borderColor: task.bloqueado ? undefined : "#e8e8ed",
      }}
    >
      <span style={{ fontSize: 13, fontWeight: 600, color: "#111116", lineHeight: 1.4 }}>
        {task.titulo}
      </span>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ ...chip, background: "#f1f5f9", color: "#475569" }}>{task.pontos}pt</span>

        {op && (
          <span style={{ ...chip, background: "#ede9fe", color: "#7c3aed" }}>{op.nome}</span>
        )}

        {task.bloqueado && (
          <span style={{ ...chip, background: "#fee2e2", color: "#dc2626" }}>Bloqueada</span>
        )}

        {total > 0 && (
          <span style={{ ...chip, background: done === total ? "#dcfce7" : "#f1f5f9", color: done === total ? "#166534" : "#64748b" }}>
            {done}/{total} ✓
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component

export default function TasksKanbanTab({ projectId, sprints, operacionais, funcionalidades }: Props) {
  const [tasks, setTasks] = useState<TaskKanbanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  // filters
  const sortedSprints = [...sprints].sort((a, b) => a.numero - b.numero);
  const lastSprint = sortedSprints[sortedSprints.length - 1];
  const [filterSprintId, setFilterSprintId] = useState<string>(lastSprint?.id ?? "");
  const [filterOpId, setFilterOpId] = useState("");
  const [filterFuncId, setFilterFuncId] = useState("");

  // drag
  const [dragId, setDragId] = useState<string | null>(null);
  const [wipError, setWipError] = useState("");

  // modals
  const [createModal, setCreateModal] = useState<{ defaultSprintId?: string } | null>(null);
  const [editModal, setEditModal] = useState<TaskKanbanResponse | null>(null);

  // sugestões
  const [sugestoes, setSugestoes] = useState<TaskSugestaoResponse[]>([]);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    listTasksKanban({
      project_id: projectId,
      sprint_id: filterSprintId || undefined,
      operacional_id: filterOpId || undefined,
      funcionalidade_id: filterFuncId || undefined,
    })
      .then((data) => { setTasks(data); setErr(""); })
      .catch((e) => setErr(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [projectId, filterSprintId, filterOpId, filterFuncId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    listTaskSugestoes(projectId)
      .then(setSugestoes)
      .catch(() => {});
  }, [projectId]);

  async function handleResolveSugestao(id: string, aceita: boolean) {
    setResolvingId(id);
    try {
      await resolveTaskSugestao(id, aceita);
      setSugestoes((prev) => prev.filter((s) => s.id !== id));
      if (aceita) load();
    } catch {
      // silently ignore
    } finally {
      setResolvingId(null);
    }
  }

  async function handleDrop(coluna: Coluna) {
    if (!dragId) return;
    const task = tasks.find((t) => t.id === dragId);
    if (!task || task.coluna_kanban === coluna) { setDragId(null); return; }
    setDragId(null);
    setWipError("");
    try {
      const updated = await moverTaskKanban(dragId, coluna);
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao mover";
      if ((e as { status?: number }).status === 409) {
        setWipError(msg);
      } else {
        alert(msg);
      }
    }
  }

  function upsertTask(t: TaskKanbanResponse) {
    setTasks((prev) => {
      const idx = prev.findIndex((x) => x.id === t.id);
      if (idx >= 0) { const copy = [...prev]; copy[idx] = t; return copy; }
      return [...prev, t];
    });
  }

  const byColuna = (col: Coluna) => tasks.filter((t) => t.coluna_kanban === col);

  const tasksSteps = [
    { title: "Tasks vs Funcionalidades", body: "Funcionalidades (aba Escopo) são entregas de alto nível para o cliente. Tasks são o trabalho técnico interno: 'Criar endpoint de login', 'Estilizar header', etc. Uma funcionalidade geralmente envolve várias tasks." },
    { title: "Criar uma task", body: "Clique em '+ Adicionar' em qualquer coluna do kanban. Informe o título, pontos e opcionalmente sprint, operacional e funcionalidade relacionada." },
    { title: "Pontos (1, 2 ou 3)", body: "Cada task recebe pontos conforme a complexidade: 1 = simples (< 4h), 2 = médio (meio dia), 3 = complexo (dia inteiro ou mais). Os pontos têm valor financeiro — o total do contrato dividido pelo total de pontos define o valor de cada ponto. Tasks concluídas geram faturamento." },
    { title: "Sprint obrigatória para iniciar (DoR)", body: "Para mover uma task para 'Em andamento', ela precisa estar vinculada a uma sprint. Isso é o 'Definition of Ready' — garante que a task foi planejada antes de ser iniciada. Vincule a sprint ao editar a task." },
    { title: "WIP — limite de tasks simultâneas", body: "Cada operacional tem um limite de tasks em 'Em andamento' ao mesmo tempo. Se o limite for atingido, o sistema bloqueia novos movimentos para aquele membro. Configure o WIP em Configurações > Operacionais." },
    { title: "Operacional", body: "Atribua a task a um membro da equipe (cadastrado em Configurações > Operacionais). O cycle-time e o WIP são calculados por operacional. Útil para ver quem está sobrecarregado." },
    { title: "Sugestões automáticas do Review", body: "Quando um review é registrado na aba Sprints, o DocuData analisa o texto e detecta quais tasks foram mencionadas como concluídas. Sugestões aparecem no banner amarelo acima do kanban — você aceita ou ignora cada uma." },
    { title: "Mover tasks entre colunas", body: "Arraste a task ou use o botão de edição para mudar a coluna. Planejado → Em andamento → Concluída. Cada transição é registrada no histórico e alimenta o cycle-time e o SPI." },
  ];

  return (
    <div>
      <TutorialBanner heading="Tasks e Kanban" steps={tasksSteps} />
      {/* Filters */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <select
          value={filterSprintId}
          onChange={(e) => setFilterSprintId(e.target.value)}
          style={{ ...inputSt, width: "auto", minWidth: 140 }}
        >
          <option value="">Todas as sprints</option>
          {sortedSprints.map((s) => (
            <option key={s.id} value={s.id}>Sprint {s.numero}</option>
          ))}
        </select>

        <select
          value={filterOpId}
          onChange={(e) => setFilterOpId(e.target.value)}
          style={{ ...inputSt, width: "auto", minWidth: 160 }}
        >
          <option value="">Todos os operacionais</option>
          {operacionais.filter((o) => o.ativo).map((o) => (
            <option key={o.id} value={o.id}>{o.nome}</option>
          ))}
        </select>

        <select
          value={filterFuncId}
          onChange={(e) => setFilterFuncId(e.target.value)}
          style={{ ...inputSt, width: "auto", minWidth: 200 }}
        >
          <option value="">Todas as funcionalidades</option>
          {funcionalidades.map((f) => (
            <option key={f.id} value={f.id}>{f.id_funcional} — {f.titulo}</option>
          ))}
        </select>

        <button
          onClick={() => setCreateModal({ defaultSprintId: filterSprintId || lastSprint?.id })}
          style={{ ...btnPrimary, marginLeft: "auto" }}
        >
          + Nova task
        </button>
      </div>

      {/* WIP error banner */}
      {wipError && (
        <div style={{
          background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 8,
          padding: "10px 14px", fontSize: 13, color: "#dc2626", marginBottom: 12,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span>{wipError}</span>
          <button onClick={() => setWipError("")} style={{ background: "none", border: "none", cursor: "pointer", color: "#dc2626", fontSize: 16, padding: 0 }}>×</button>
        </div>
      )}

      {/* Sugestões do review */}
      {sugestoes.length > 0 && (
        <div style={{
          background: "#fffbeb", border: "1px solid #fbbf24", borderRadius: 10,
          padding: "12px 16px", marginBottom: 14,
        }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "#92400e", margin: "0 0 8px" }}>
            📋 {sugestoes.length} sugestão{sugestoes.length > 1 ? "ões" : ""} do review — tasks mencionadas como concluídas
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sugestoes.map((s) => (
              <div key={s.id} style={{
                display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
                background: "#fff", border: "1px solid #fde68a", borderRadius: 7, padding: "8px 12px",
              }}>
                <span style={{ fontSize: 13, color: "#374151", flex: 1, minWidth: 0 }}>
                  <strong>{s.task_titulo}</strong>
                  {s.motivo && <span style={{ color: "#78716c", fontWeight: 400 }}> — {s.motivo}</span>}
                </span>
                <button
                  disabled={resolvingId === s.id}
                  onClick={() => handleResolveSugestao(s.id, true)}
                  style={{ ...btnPrimary, padding: "5px 14px", fontSize: 12, background: "#166534", opacity: resolvingId === s.id ? 0.5 : 1 }}
                >
                  Aceitar
                </button>
                <button
                  disabled={resolvingId === s.id}
                  onClick={() => handleResolveSugestao(s.id, false)}
                  style={{ ...btnGhost, padding: "4px 12px", fontSize: 12, opacity: resolvingId === s.id ? 0.5 : 1 }}
                >
                  Ignorar
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {err && <p style={{ color: "#dc2626", fontSize: 13 }}>{err}</p>}

      {loading ? (
        <p style={{ color: "#9696a0", fontSize: 13 }}>Carregando tasks...</p>
      ) : (
        <div style={{
          background: "#f7f7fa",
          borderRadius: 14,
          padding: 16,
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 12,
        }}>
          {COLUNAS.map((col) => {
            const colTasks = byColuna(col.id);
            return (
              <div
                key={col.id}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => handleDrop(col.id)}
                style={{ minHeight: 120 }}
              >
                {/* Column header */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <span style={{
                    fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                    textTransform: "uppercase", color: col.color,
                  }}>
                    {col.label}
                  </span>
                  <span style={{ ...chip, background: col.bg, color: col.color, fontSize: 11 }}>
                    {colTasks.length}
                  </span>
                  <button
                    onClick={() => setCreateModal({ defaultSprintId: filterSprintId || lastSprint?.id })}
                    title="Nova task nesta coluna"
                    style={{
                      background: "none", border: "none", cursor: "pointer",
                      color: "#b8b8c0", fontSize: 18, lineHeight: 1, padding: 0, marginLeft: "auto",
                    }}
                  >
                    +
                  </button>
                </div>

                {/* Cards */}
                {colTasks.length === 0 ? (
                  <div style={{ padding: "20px 0", textAlign: "center" }}>
                    <span style={{ color: "#b8b8c0", fontSize: 12 }}>Nenhuma task</span>
                  </div>
                ) : (
                  colTasks.map((t) => (
                    <TaskCard
                      key={t.id}
                      task={t}
                      operacionais={operacionais}
                      onDragStart={() => setDragId(t.id)}
                      onDragEnd={() => setDragId(null)}
                      onClick={() => setEditModal(t)}
                    />
                  ))
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modals */}
      {createModal !== null && (
        <TaskModal
          mode="create"
          projectId={projectId}
          sprints={sprints}
          operacionais={operacionais}
          funcionalidades={funcionalidades}
          defaultSprintId={createModal.defaultSprintId}
          onClose={() => setCreateModal(null)}
          onSaved={(t) => { upsertTask(t); setCreateModal(null); }}
        />
      )}

      {editModal !== null && (
        <TaskModal
          mode="edit"
          task={editModal}
          projectId={projectId}
          sprints={sprints}
          operacionais={operacionais}
          funcionalidades={funcionalidades}
          onClose={() => setEditModal(null)}
          onSaved={(t) => { upsertTask(t); setEditModal(null); }}
          onDeleted={(id) => { setTasks((prev) => prev.filter((t) => t.id !== id)); setEditModal(null); }}
        />
      )}
    </div>
  );
}
