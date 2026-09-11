"use client";

import { useEffect, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import TutorialBanner from "./TutorialBanner";
import { useAuth } from "./AuthGuard";
import {
  listTasksKanban,
  createTaskKanban,
  patchTaskKanban,
  moverTaskKanban,
  deleteTaskKanban,
  listTaskTransicoesKanban,
  listTaskSugestoes,
  resolveTaskSugestao,
  overrideTravamentoTask,
  redistribuirPontos,
  criarSolicitacaoTask,
  listSolicitacoesTask,
  resolverSolicitacaoTask,
  type SolicitacaoTask,
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
  const [bloqueadoPor, setBloqueadoPor] = useState(task?.bloqueado_por ?? "");
  const [bloqueadoResolvidoPor, setBloqueadoResolvidoPor] = useState("");
  const jaEstavaBloqueadoManual = task?.bloqueado_manual ?? false;
  const [extra, setExtra] = useState(task?.extra ?? false);
  const [orcamentoEstourado, setOrcamentoEstourado] = useState(false);
  const [redistribuindo, setRedistribuindo] = useState(false);
  const [travadoOverridePor, setTravadoOverridePor] = useState("");
  const [overridingTravamento, setOverridingTravamento] = useState(false);
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
    if (jaEstavaBloqueadoManual && !bloqueado && !bloqueadoResolvidoPor) {
      setErr("Informe quem resolveu o bloqueio.");
      return;
    }
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
          extra,
          checklist,
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
          bloqueado_manual: bloqueado,
          bloqueado_por: (bloqueado && !jaEstavaBloqueadoManual) ? (bloqueadoPor.trim() || undefined) : undefined,
          bloqueado_resolvido_por: (!bloqueado && jaEstavaBloqueadoManual) ? bloqueadoResolvidoPor : undefined,
          extra,
        });
      }
      onSaved(saved);
      onClose();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro";
      setErr(msg);
      setOrcamentoEstourado(msg.includes("Orçamento da sprint excedido"));
    } finally {
      setSaving(false);
    }
  }

  async function handleRedistribuir() {
    if (!sprintId) return;
    setRedistribuindo(true);
    try {
      const { ajustes } = await redistribuirPontos(sprintId, pontos);
      const resumo = ajustes
        .filter((a) => a.de !== a.para)
        .map((a) => `${a.titulo}: ${a.de} → ${a.para}`)
        .join("\n");
      alert(resumo ? `Pontos redistribuídos:\n\n${resumo}` : "Nada precisou mudar.");
      setOrcamentoEstourado(false);
      setErr("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao redistribuir");
    } finally {
      setRedistribuindo(false);
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

  async function handleOverrideTravamento() {
    if (!task) return;
    setOverridingTravamento(true);
    setErr("");
    try {
      const updated = await overrideTravamentoTask(task.id, travadoOverridePor.trim() || undefined);
      onSaved(updated);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao suprimir alerta");
    } finally {
      setOverridingTravamento(false);
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

          <div style={{ background: extra ? "#f0fdf4" : "#f8fafc", border: `1px solid ${extra ? "#bbf7d0" : "#e8e8ed"}`, borderRadius: 8, padding: "10px 12px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
              <input type="checkbox" checked={extra} onChange={(e) => setExtra(e.target.checked)} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>Task extra</span>
            </label>
            <p style={{ fontSize: 11, color: "#64748b", margin: "6px 0 0" }}>
              Trabalho concedido além do que a pessoa já tinha. Não consome o orçamento
              de pontos da sprint e, se concluída antes do fechamento, vira bônus.
            </p>
          </div>

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
                <div style={{ display: "grid", gridTemplateColumns: jaEstavaBloqueadoManual ? "1fr" : "1fr 1fr", gap: 10 }}>
                  <div>
                    <label style={labelSt}>Motivo do bloqueio</label>
                    <input
                      value={motivoBloqueio}
                      onChange={(e) => setMotivoBloqueio(e.target.value)}
                      placeholder="Descreva o bloqueio..."
                      style={inputSt}
                    />
                  </div>
                  {!jaEstavaBloqueadoManual && (
                    <div>
                      <label style={labelSt}>Quem bloqueou?</label>
                      <input
                        value={bloqueadoPor}
                        onChange={(e) => setBloqueadoPor(e.target.value)}
                        placeholder="Nome de quem bloqueou..."
                        style={inputSt}
                      />
                    </div>
                  )}
                </div>
              )}
              {jaEstavaBloqueadoManual && !bloqueado && (
                <div>
                  <label style={labelSt}>Quem resolveu? *</label>
                  <select
                    value={bloqueadoResolvidoPor}
                    onChange={(e) => setBloqueadoResolvidoPor(e.target.value)}
                    style={inputSt}
                    required
                  >
                    <option value="">Selecione...</option>
                    <option value="operacional">Operacional</option>
                    <option value="gerente">Gerente</option>
                  </select>
                </div>
              )}

              {/* Travamento automático — ALERT-03: alerta, nunca pontuação */}
              {task?.travado_automatico && !task?.travado_override && (
                <div style={{ background: "#fef3c7", border: "1px solid #fde68a", borderRadius: 8, padding: 10 }}>
                  <p style={{ fontSize: 12, color: "#92400e", margin: "0 0 8px", fontWeight: 600 }}>
                    ⏱ Task parada além do limiar esperado para {task.pontos} ponto(s)
                    (~{Math.round(task.pontos * 1.5)} dias).
                  </p>
                  <div style={{ display: "flex", gap: 8 }}>
                    <input
                      value={travadoOverridePor}
                      onChange={(e) => setTravadoOverridePor(e.target.value)}
                      placeholder="Seu nome (gerente)..."
                      style={{ ...inputSt, flex: 1 }}
                    />
                    <button
                      type="button"
                      onClick={handleOverrideTravamento}
                      disabled={overridingTravamento}
                      style={{ ...btnGhost, opacity: overridingTravamento ? 0.6 : 1 }}
                    >
                      {overridingTravamento ? "Suprimindo..." : "Suprimir alerta"}
                    </button>
                  </div>
                </div>
              )}

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
          {orcamentoEstourado && sprintId && (
            <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: "10px 12px" }}>
              <p style={{ fontSize: 12, color: "#92400e", margin: "0 0 8px" }}>
                Dá para encolher as tasks que já estão nesta sprint, proporcionalmente,
                para abrir os {pontos} pontos que faltam.
              </p>
              <button
                type="button"
                onClick={handleRedistribuir}
                disabled={redistribuindo}
                style={{ background: "#92400e", color: "#fff", border: "none", borderRadius: 7, padding: "6px 12px", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
              >
                {redistribuindo ? "Redistribuindo..." : "Redistribuir pontos"}
              </button>
            </div>
          )}

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

// ---------------------------------------------------------------------------
// Modal de visualização — usado por operacionais: só leitura, exceto o
// checklist (cada marcação salva na hora, sem botão de Salvar separado).

function TaskViewModal({
  task, sprints, funcionalidades, onClose, onSaved,
}: {
  task: TaskKanbanResponse;
  sprints: SprintWithStatus[];
  funcionalidades: FuncionalidadeResponse[];
  onClose: () => void;
  onSaved: (t: TaskKanbanResponse) => void;
}) {
  const [checklist, setChecklist] = useState(task.checklist);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const sprint = sprints.find((s) => s.id === task.sprint_id);
  const funcionalidade = funcionalidades.find((f) => f.id === task.funcionalidade_id);
  const done = checklist.filter((i) => i.done).length;

  async function toggleItem(i: number) {
    const anterior = checklist;
    const atualizado = checklist.map((item, j) => (j === i ? { ...item, done: !item.done } : item));
    setChecklist(atualizado);
    setSaving(true);
    setErr("");
    try {
      const saved = await patchTaskKanban(task.id, { checklist: atualizado });
      onSaved(saved);
    } catch (e) {
      setChecklist(anterior);
      setErr(e instanceof Error ? e.message : "Erro ao salvar checklist");
    } finally {
      setSaving(false);
    }
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
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
          <span style={{ ...chip, background: "#f1f5f9", color: "#475569" }}>{task.pontos}pt</span>
          {sprint && <span style={{ ...chip, background: "#ede9fe", color: "#7c3aed" }}>Sprint {sprint.numero}</span>}
          {task.extra && <span style={{ ...chip, background: "#dcfce7", color: "#166534" }}>+ extra</span>}
          {task.bloqueado && (
            <span style={{ ...chip, background: "#fee2e2", color: "#dc2626" }}>
              Bloqueada{task.motivo_bloqueio ? `: ${task.motivo_bloqueio}` : ""}
            </span>
          )}
        </div>

        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#0f172a", margin: "0 0 6px" }}>{task.titulo}</h3>
        {funcionalidade && (
          <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 16px" }}>
            {funcionalidade.id_funcional} — {funcionalidade.titulo}
          </p>
        )}

        {task.descricao && (
          <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.6, marginBottom: 20 }}>
            <ReactMarkdown>{task.descricao}</ReactMarkdown>
          </div>
        )}

        <div>
          <label style={labelSt}>Checklist{checklist.length > 0 ? ` (${done}/${checklist.length})` : ""}</label>
          {checklist.length === 0 ? (
            <p style={{ fontSize: 13, color: "#9696a0", margin: 0 }}>Sem itens de checklist nesta task.</p>
          ) : (
            checklist.map((item, i) => (
              <label key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, cursor: "pointer" }}>
                <input type="checkbox" checked={item.done} disabled={saving} onChange={() => toggleItem(i)} />
                <span style={{ flex: 1, fontSize: 13, color: item.done ? "#9696a0" : "#111116", textDecoration: item.done ? "line-through" : "none" }}>
                  {item.texto}
                </span>
              </label>
            ))
          )}
        </div>

        {err && <p style={{ fontSize: 12, color: "#dc2626", marginTop: 10 }}>{err}</p>}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
          <button type="button" onClick={onClose} style={btnPrimary}>Fechar</button>
        </div>
      </div>
    </div>
  );
}

function labelForColuna(c: string): string {
  return COLUNAS.find((col) => col.id === c)?.label ?? c;
}

// ---------------------------------------------------------------------------
// Modal de confirmação de transição — usado pelo drag-and-drop e pelo aceite
// do banner de sugestão da IA. Cancelar não chama nenhuma API.

function ConfirmTransicaoModal({
  taskTitulo, de, para, onConfirm, onCancel, confirming, motivo, onMotivoChange,
}: {
  taskTitulo: string;
  de: string;
  para: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirming: boolean;
  motivo?: string;
  onMotivoChange?: (v: string) => void;
}) {
  // Reabertura (TRANS-03): concluida -> em_andamento aceita um motivo opcional.
  const isReabertura = de === "concluida" && para === "em_andamento";

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div style={{
        background: "#fff", borderRadius: 16, padding: "28px 32px",
        width: "100%", maxWidth: 420,
        boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
      }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#0f172a", margin: "0 0 14px" }}>
          Confirmar mudança de status
        </h3>
        <p style={{ fontSize: 14, color: "#374151", margin: "0 0 20px", lineHeight: 1.5 }}>
          Mover <strong>{taskTitulo}</strong> de <strong>{labelForColuna(de)}</strong> para{" "}
          <strong>{labelForColuna(para)}</strong>?
        </p>
        {isReabertura && onMotivoChange && (
          <div style={{ marginBottom: 20 }}>
            <label style={labelSt}>Motivo da reabertura (opcional)</label>
            <textarea
              value={motivo ?? ""}
              onChange={(e) => onMotivoChange(e.target.value)}
              rows={2}
              placeholder="Por que essa task voltou para Em andamento?"
              style={{ ...inputSt, resize: "vertical" }}
            />
          </div>
        )}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button type="button" onClick={onCancel} disabled={confirming} style={btnGhost}>
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={confirming}
            style={{ ...btnPrimary, opacity: confirming ? 0.6 : 1 }}
          >
            {confirming ? "Movendo…" : "Confirmar"}
          </button>
        </div>
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

        {task.extra && (
          <span style={{ ...chip, background: "#dcfce7", color: "#166534" }}>+ extra</span>
        )}

        {task.bloqueado && (
          <span style={{ ...chip, background: "#fee2e2", color: "#dc2626" }}>Bloqueada</span>
        )}

        {task.travado_automatico && !task.travado_override && (
          <span style={{ ...chip, background: "#fef3c7", color: "#a16207" }}>⏱ Travada</span>
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

  // pedido de task extra
  const auth = useAuth();
  const [solicitacoes, setSolicitacoes] = useState<SolicitacaoTask[]>([]);
  const [pedindoTask, setPedindoTask] = useState(false);
  const [avisoPedido, setAvisoPedido] = useState("");
  const [sugestaoTask, setSugestaoTask] = useState("");

  const ehOperacional = auth?.cargo === "operacional";
  const meuOperacional = ehOperacional
    ? operacionais.find((o) => o.ativo && o.email && auth?.email && o.email.toLowerCase() === auth.email.toLowerCase())
    : undefined;
  const minhasTasksAbertas = meuOperacional
    ? tasks.filter((t) => t.operacional_id === meuOperacional.id && t.coluna_kanban !== "concluida").length
    : 0;
  const jaPediu = meuOperacional
    ? solicitacoes.some((s) => s.operacional_id === meuOperacional.id)
    : false;

  const carregarSolicitacoes = useCallback(() => {
    listSolicitacoesTask(projectId).then(setSolicitacoes).catch(() => setSolicitacoes([]));
  }, [projectId]);

  useEffect(() => { carregarSolicitacoes(); }, [carregarSolicitacoes]);

  async function handlePedirTask() {
    if (!meuOperacional) return;
    setPedindoTask(true);
    setAvisoPedido("");
    try {
      await criarSolicitacaoTask(meuOperacional.id, sugestaoTask);
      setAvisoPedido("Pedido enviado. O gerente foi avisado por e-mail.");
      setSugestaoTask("");
      carregarSolicitacoes();
    } catch (e) {
      setAvisoPedido(e instanceof Error ? e.message : "Erro ao pedir nova task");
    } finally {
      setPedindoTask(false);
    }
  }

  async function handleResolverPedido(id: string, status: "atendida" | "recusada") {
    try {
      await resolverSolicitacaoTask(id, status);
      setSolicitacoes((prev) => prev.filter((s) => s.id !== id));
    } catch {
      setWipError("Erro ao responder o pedido.");
    }
  }

  // modals
  const [createModal, setCreateModal] = useState<{ defaultSprintId?: string } | null>(null);
  const [editModal, setEditModal] = useState<TaskKanbanResponse | null>(null);

  // sugestões
  const [sugestoes, setSugestoes] = useState<TaskSugestaoResponse[]>([]);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  // confirmação de transição — drag-and-drop e aceite de sugestão passam por aqui
  // antes de qualquer chamada de API (TRANS-01/TRANS-02)
  const [pendingMove, setPendingMove] = useState<{ taskId: string; taskTitulo: string; de: Coluna; para: Coluna } | null>(null);
  const [pendingSugestao, setPendingSugestao] = useState<TaskSugestaoResponse | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [motivoReabertura, setMotivoReabertura] = useState("");

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

  function handleDrop(coluna: Coluna) {
    if (!dragId) return;
    const task = tasks.find((t) => t.id === dragId);
    setDragId(null);
    if (!task || task.coluna_kanban === coluna) return;
    // Nenhuma chamada de API ainda — apenas abre o modal de confirmação.
    // Cancelar depois não deixa rastro nenhum (TRANS-01).
    setMotivoReabertura("");
    setPendingMove({ taskId: task.id, taskTitulo: task.titulo, de: task.coluna_kanban, para: coluna });
  }

  async function confirmPendingMove() {
    if (!pendingMove) return;
    setConfirming(true);
    setWipError("");
    try {
      const updated = await moverTaskKanban(
        pendingMove.taskId,
        pendingMove.para,
        undefined,
        motivoReabertura.trim() || undefined
      );
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setPendingMove(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao mover";
      if ((e as { status?: number }).status === 409) {
        setWipError(msg);
      } else {
        alert(msg);
      }
      setPendingMove(null);
    } finally {
      setConfirming(false);
      setMotivoReabertura("");
    }
  }

  function cancelPendingMove() {
    // Nenhuma chamada de API — fecha o modal sem alterar nenhum estado.
    setPendingMove(null);
    setMotivoReabertura("");
  }

  async function confirmPendingSugestao() {
    if (!pendingSugestao) return;
    setConfirming(true);
    try {
      await handleResolveSugestao(pendingSugestao.id, true);
    } finally {
      setPendingSugestao(null);
      setConfirming(false);
    }
  }

  function cancelPendingSugestao() {
    // Nenhuma chamada de API — fecha o modal sem resolver a sugestão.
    setPendingSugestao(null);
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
    { title: "Tasks vs Funcionalidades", body: "Funcionalidades (aba Planejamento) são entregas de alto nível para o cliente. Tasks são o trabalho técnico interno: 'Criar endpoint de login', 'Estilizar header', etc. Uma funcionalidade geralmente envolve várias tasks." },
    { title: "Criar uma task", body: "Clique em '+ Nova task'. Informe título e pontos, e opcionalmente sprint, operacional, funcionalidade e checklist. O checklist já aparece na criação: são os itens que precisam estar prontos para a task poder ir para Concluída." },
    { title: "Pontos da task", body: "Todo projeto vale 100 pontos, fixo. Você distribui esses 100 entre as sprints na aba Planejamento, e os pontos de cada sprint entre as tasks dela. A soma das tasks não pode passar do que a sprint recebeu; se passar, aparece o botão 'Redistribuir pontos', que encolhe as tasks existentes proporcionalmente. Pontue com honestidade: os pontos são o denominador da entrega de cada pessoa." },
    { title: "Checklist e Definition of Done", body: "Dentro da task você monta uma lista de itens e vai marcando conforme fica pronto. O card mostra o progresso no formato '3/5'. Se sobrar item aberto, o sistema recusa mover a task para Concluída. Task sem checklist não trava nada: a regra só vale se você criou a lista." },
    { title: "Sprint obrigatória para iniciar (DoR)", body: "Para mover uma task para 'Em andamento', ela precisa estar vinculada a uma sprint. Sem sprint não existe a quem creditar aquele trabalho quando a semana fechar." },
    { title: "WIP — limite de tasks simultâneas", body: "Cada operacional tem um limite de tasks em 'Em andamento' ao mesmo tempo, e o projeto também. Se o limite for atingido, o sistema bloqueia novos movimentos. Configure em Configurações." },
    { title: "Bloqueio: quem marca é quem trava", body: "Quando o trabalho para por algo que não depende de você (esperando cliente, acesso, outra task, uma decisão), marque a caixa 'Bloqueada' na task e escreva o motivo. O card ganha borda vermelha e o gerente vê no quadro. Ao destravar, alguém informa quem resolveu: Operacional ou Gerente. Essa resposta é o que alimenta a leitura de autonomia." },
    { title: "Task travada por tempo", body: "O relógio conta desde que a task está ativa — Planejado ou Em andamento, tanto faz — e a sprint dela já começou. Se passar de um dia e meio por ponto (uma de 2 pontos, 3 dias; uma de 4 pontos, 6 dias), ela ganha a etiqueta amarela 'Travada'. Se for concluída depois disso, os pontos dela são descontados da entrega. Mover a task pra uma sprint futura pausa o relógio; o gerente também pode suprimir o alerta dentro da task quando o atraso não é culpa de quem estava nela, e aí não há desconto." },
    { title: "Task extra", body: "Quando alguém termina tudo que tinha, aparece no Kanban dela o botão 'Quero mais uma task' e você recebe um e-mail. Ao criar a task para essa pessoa, marque a caixa 'Task extra': ela não consome o orçamento de pontos da sprint e, se for concluída antes do fechamento, rende um bônus. Recusar o pedido é uma resposta válida; deixar sem resposta é a única errada." },
    { title: "Kanban alimenta Planning e Review", body: "Ao gerar um Planning ou Review pela aba Sprints, a IA captura o estado atual do kanban dessa sprint — cada task com coluna, pontos e se está bloqueada entra automaticamente no contexto. O que você vê aqui é exatamente o que a IA usa para escrever os documentos." },
    { title: "Sugestões automáticas do Review", body: "Quando um review é registrado na aba Sprints, o DocuData analisa o texto e detecta quais tasks foram mencionadas como concluídas. Sugestões aparecem no banner amarelo acima do kanban — você aceita ou ignora cada uma." },
    { title: "Mover tasks entre colunas", body: "Arraste a task ou use o botão de edição para mudar a coluna. Planejado → Em andamento → Concluída. Cada transição é registrada com quem estava na task naquele momento, e é isso que define quem recebe os pontos da entrega." },
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

        {!ehOperacional && (
          <button
            onClick={() => setCreateModal({ defaultSprintId: filterSprintId || lastSprint?.id })}
            style={{ ...btnPrimary, marginLeft: "auto" }}
          >
            + Nova task
          </button>
        )}
      </div>

      {/* Pedir nova task — só aparece pro operacional que zerou a fila */}
      {ehOperacional && meuOperacional && minhasTasksAbertas === 0 && (
        <div style={{
          background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10,
          padding: "12px 16px", marginBottom: 14,
        }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "#166534", margin: "0 0 4px" }}>
            Você concluiu tudo que estava com você.
          </p>
          <p style={{ fontSize: 12, color: "#3f6f52", margin: "0 0 10px" }}>
            Peça mais trabalho sem precisar puxar conversa. O gerente recebe um e-mail
            e, se tiver algo disponível, te passa uma task extra.
          </p>
          {jaPediu ? (
            <p style={{ fontSize: 12, color: "#3f6f52", margin: 0, fontWeight: 600 }}>
              Pedido enviado, aguardando o gerente.
            </p>
          ) : (
            <>
              <textarea
                value={sugestaoTask}
                onChange={(e) => setSugestaoTask(e.target.value)}
                placeholder="Alguma sugestão do que seria útil fazer? (opcional — vai junto no e-mail pro gerente)"
                rows={2}
                style={{ ...inputSt, resize: "vertical", marginBottom: 8 }}
              />
              <button
                onClick={handlePedirTask}
                disabled={pedindoTask}
                style={{ ...btnPrimary, background: "#166534" }}
              >
                {pedindoTask ? "Enviando..." : "Quero mais uma task"}
              </button>
            </>
          )}
          {avisoPedido && <p style={{ fontSize: 12, color: "#3f6f52", marginTop: 8 }}>{avisoPedido}</p>}
        </div>
      )}

      {/* Pedidos pendentes — visão do gerente */}
      {!ehOperacional && solicitacoes.length > 0 && (
        <div style={{
          background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10,
          padding: "12px 16px", marginBottom: 14,
        }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "#166534", margin: "0 0 8px" }}>
            {solicitacoes.length} pedido{solicitacoes.length > 1 ? "s" : ""} de nova task
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {solicitacoes.map((s) => (
              <div key={s.id} style={{
                display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
                background: "#fff", border: "1px solid #bbf7d0", borderRadius: 7, padding: "8px 12px",
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 13, color: "#374151" }}>
                    <strong>{s.operacional_nome}</strong> está sem task em aberto e pediu mais trabalho.
                  </span>
                  {s.sugestao && (
                    <p style={{ fontSize: 12, color: "#3f6f52", background: "#f0fdf4", borderRadius: 6, padding: "6px 10px", margin: "6px 0 0" }}>
                      <strong>Sugestão:</strong> {s.sugestao}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => { handleResolverPedido(s.id, "atendida"); setCreateModal({ defaultSprintId: filterSprintId || lastSprint?.id }); }}
                  style={{ ...btnPrimary, padding: "5px 14px", fontSize: 12, background: "#166534" }}
                >
                  Criar task extra
                </button>
                <button
                  onClick={() => handleResolverPedido(s.id, "recusada")}
                  style={{ ...btnGhost, padding: "4px 12px", fontSize: 12 }}
                >
                  Nada agora
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

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
                  onClick={() => setPendingSugestao(s)}
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
                  {!ehOperacional && (
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
                  )}
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
        ehOperacional ? (
          <TaskViewModal
            task={editModal}
            sprints={sprints}
            funcionalidades={funcionalidades}
            onClose={() => setEditModal(null)}
            onSaved={(t) => { upsertTask(t); setEditModal(t); }}
          />
        ) : (
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
        )
      )}

      {pendingMove !== null && (
        <ConfirmTransicaoModal
          taskTitulo={pendingMove.taskTitulo}
          de={pendingMove.de}
          para={pendingMove.para}
          onConfirm={confirmPendingMove}
          onCancel={cancelPendingMove}
          confirming={confirming}
          motivo={motivoReabertura}
          onMotivoChange={setMotivoReabertura}
        />
      )}

      {pendingSugestao !== null && (
        <ConfirmTransicaoModal
          taskTitulo={pendingSugestao.task_titulo}
          de={pendingSugestao.task_coluna_atual ?? "atual"}
          para="concluida"
          onConfirm={confirmPendingSugestao}
          onCancel={cancelPendingSugestao}
          confirming={confirming}
        />
      )}
    </div>
  );
}
