"use client";

import { useEffect, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import TutorialBanner from "./TutorialBanner";
import { Button as DsButton, Select as DsSelect, ErrorNotice, Chip } from "./ds";
import { useAuth } from "./AuthGuard";
import { NIVEIS, rotuloNivel } from "../lib/regua";
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
  criarSolicitacaoTask,
  listSolicitacoesTask,
  resolverSolicitacaoTask,
  puxarTask,
  devolverTask,
  aprovarTask,
  rejeitarTask,
  reclassificarTask,
  opinarNivelTask,
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
  modoTrabalho: "ATRIBUICAO" | "PULL";
}

type Coluna = "planejado" | "em_andamento" | "pendente_aprovacao" | "concluida";

const COLUNAS: { id: Coluna; label: string; color: string; bg: string }[] = [
  { id: "planejado", label: "Planejado", color: "#8a948e", bg: "rgba(255,255,255,0.06)" },
  { id: "em_andamento", label: "Em andamento", color: "#f2c14e", bg: "rgba(242,193,78,0.10)" },
  { id: "pendente_aprovacao", label: "Pendente de aprovação", color: "#b197fc", bg: "rgba(177,151,252,0.10)" },
  { id: "concluida", label: "Concluída", color: "#3ee06f", bg: "rgba(62,224,111,0.12)" },
];

/** Quantas tasks concluídas aparecem antes do "+ N tasks concluídas" (protótipo 06). */
const CONCLUIDAS_VISIVEIS = 4;

const card: React.CSSProperties = {
  background: "rgba(62,224,111,0.055)",
  border: "1px solid rgba(62,224,111,0.17)",
  borderRadius: 12,
  padding: 16,
  cursor: "pointer",
  display: "flex",
  flexDirection: "column",
  gap: 12,
  textAlign: "left",
  width: "100%",
  fontFamily: "inherit",
};

const chip: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "4px 10px",
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 600,
  whiteSpace: "nowrap",
  border: "1px solid rgba(255,255,255,0.08)",
};

const inputSt: React.CSSProperties = {
  padding: "10px 14px",
  border: "1px solid rgba(62,224,111,0.17)",
  borderRadius: 10,
  fontSize: 14,
  color: "#f2f5f3",
  background: "rgba(62,224,111,0.055)",
  width: "100%",
  boxSizing: "border-box",
  fontFamily: "inherit",
};

const btnPrimary: React.CSSProperties = {
  background: "#3ee06f",
  color: "#04120a",
  border: "1px solid #3ee06f",
  borderRadius: 10,
  height: 38,
  padding: "0 16px",
  fontSize: 13.5,
  fontWeight: 600,
  cursor: "pointer",
  boxShadow: "0 0 24px rgba(62,224,111,0.25)",
  fontFamily: "inherit",
  whiteSpace: "nowrap",
};

const btnGhost: React.CSSProperties = {
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.14)",
  borderRadius: 10,
  padding: "0 14px",
  height: 32,
  fontSize: 12.5,
  fontWeight: 600,
  color: "#f2f5f3",
  cursor: "pointer",
  fontFamily: "inherit",
  whiteSpace: "nowrap",
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
  modoTrabalho: "ATRIBUICAO" | "PULL";
  onClose: () => void;
  onSaved: (t: TaskKanbanResponse, criada?: boolean) => void;
  onReclassified?: () => void;
  onDeleted?: (id: string) => void;
}

function TaskModal({
  mode, task, projectId, sprints, operacionais, funcionalidades,
  defaultSprintId, modoTrabalho, onClose, onSaved, onReclassified, onDeleted,
}: TaskModalProps) {
  const [titulo, setTitulo] = useState(task?.titulo ?? "");
  const [descricao, setDescricao] = useState(task?.descricao ?? "");
  const auth = useAuth();
  const ehLider = auth?.cargo === "lider" || auth?.cargo === "owner";
  const [opiniao, setOpiniao] = useState("");
  const [faltando, setFaltando] = useState<string[]>([]);
  const [reclassificando, setReclassificando] = useState(false);
  const [sprintId, setSprintId] = useState(task?.sprint_id ?? defaultSprintId ?? "");
  const [operacionalId, setOperacionalId] = useState(task?.operacional_id ?? "");
  const [funcId, setFuncId] = useState(task?.funcionalidade_id ?? "");
  const [bloqueado, setBloqueado] = useState(task?.bloqueado ?? false);
  const [motivoBloqueio, setMotivoBloqueio] = useState(task?.motivo_bloqueio ?? "");
  const [bloqueadoPor, setBloqueadoPor] = useState(task?.bloqueado_por ?? "");
  const [bloqueadoResolvidoPor, setBloqueadoResolvidoPor] = useState("");
  const jaEstavaBloqueadoManual = task?.bloqueado_manual ?? false;
  const eraBloqueioCliente = jaEstavaBloqueadoManual && task?.bloqueio_tipo === "cliente";
  const [bloqueioTipo, setBloqueioTipo] = useState<"interno" | "cliente">(
    task?.bloqueio_tipo === "cliente" ? "cliente" : "interno"
  );
  const [extra, setExtra] = useState(task?.extra ?? false);
  const [requerAprovacao, setRequerAprovacao] = useState(task?.requer_aprovacao ?? false);
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

  const tituloMudou = mode === "edit" && titulo !== (task?.titulo ?? "");
  const descricaoMudou = mode === "edit" && descricao !== (task?.descricao ?? "");
  const checklistMudou = mode === "edit" && JSON.stringify(checklist.map((i) => [i.texto, i.done])) !== JSON.stringify((task?.checklist ?? []).map((i) => [i.texto, i.done]));
  const textoMudou = tituloMudou || descricaoMudou
    || (mode === "edit" && JSON.stringify(checklist.map((i) => i.texto)) !== JSON.stringify((task?.checklist ?? []).map((i) => i.texto)));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!titulo.trim()) { setErr("Título obrigatório."); return; }
    if (jaEstavaBloqueadoManual && !eraBloqueioCliente && !bloqueado && !bloqueadoResolvidoPor) {
      setErr("Informe quem resolveu o bloqueio.");
      return;
    }
    setSaving(true);
    setErr("");
    setFaltando([]);
    try {
      let saved: TaskKanbanResponse;
      if (mode === "create") {
        saved = await createTaskKanban({
          project_id: projectId,
          titulo: titulo.trim(),
          descricao: descricao.trim() || undefined,
          sprint_id: sprintId || undefined,
          operacional_id: operacionalId || undefined,
          funcionalidade_id: funcId || undefined,
          extra,
          requer_aprovacao: requerAprovacao,
          checklist,
          ...(opiniao ? { opiniao_nivel: Number(opiniao) } : {}),
        });
      } else {
        // O backend trata qualquer diferença de texto como mudança de escopo
        // (null != ""), então titulo/descricao/checklist só vão no payload se
        // realmente mudaram em relação à task carregada.
        saved = await patchTaskKanban(task!.id, {
          ...(tituloMudou ? { titulo: titulo.trim() } : {}),
          ...(descricaoMudou ? { descricao: descricao.trim() } : {}),
          ...(checklistMudou ? { checklist } : {}),
          sprint_id: sprintId || undefined,
          operacional_id: operacionalId || undefined,
          funcionalidade_id: funcId || undefined,
          bloqueado,
          motivo_bloqueio: bloqueado ? motivoBloqueio.trim() || undefined : undefined,
          bloqueado_manual: bloqueado,
          bloqueio_tipo: bloqueado ? bloqueioTipo : undefined,
          bloqueado_por: (bloqueado && !jaEstavaBloqueadoManual) ? (bloqueadoPor.trim() || undefined) : undefined,
          bloqueado_resolvido_por: (!bloqueado && jaEstavaBloqueadoManual && !eraBloqueioCliente) ? bloqueadoResolvidoPor : undefined,
          extra,
          requer_aprovacao: requerAprovacao,
        });
      }
      onSaved(saved, mode === "create");
      onClose();
    } catch (e) {
      const f = (e as { status?: number; faltando?: string[] }).faltando;
      if (mode === "create" && (e as { status?: number }).status === 422 && Array.isArray(f)) {
        setFaltando(f);
        return;
      }
      const msg = e instanceof Error ? e.message : "Erro";
      setErr(msg);
    } finally {
      setSaving(false);
    }
  }

  async function handleReclassificar() {
    if (!task) return;
    setReclassificando(true);
    setErr("");
    try {
      await reclassificarTask(task.id);
      onReclassified?.();
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao reclassificar");
    } finally {
      setReclassificando(false);
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

  const [rejeitando, setRejeitando] = useState(false);
  const [motivoRejeicao, setMotivoRejeicao] = useState("");
  const [aprovando, setAprovando] = useState(false);

  async function handleAprovar() {
    if (!task) return;
    setAprovando(true);
    setErr("");
    try {
      const updated = await aprovarTask(task.id);
      onSaved(updated);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao aprovar");
    } finally {
      setAprovando(false);
    }
  }

  async function handleRejeitar() {
    if (!task || !motivoRejeicao.trim()) { setErr("Informe o motivo da rejeição."); return; }
    setAprovando(true);
    setErr("");
    try {
      const updated = await rejeitarTask(task.id, motivoRejeicao.trim());
      onSaved(updated);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao rejeitar");
    } finally {
      setAprovando(false);
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
        background: "#0d1711", borderRadius: 16, padding: "28px 32px",
        width: "100%", maxWidth: 520, maxHeight: "90vh", overflowY: "auto",
        boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
      }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#f2f5f3", margin: "0 0 20px" }}>
          {mode === "create" ? "Nova task" : "Editar task"}
        </h3>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {faltando.length > 0 && (
            <ErrorNotice>
              <strong>O classificador precisa de mais detalhes</strong>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {faltando.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </ErrorNotice>
          )}
          <div>
            <label style={labelSt}>Título *</label>
            <input value={titulo} onChange={(e) => setTitulo(e.target.value)} style={inputSt} required />
          </div>

          {mode === "edit" && task && (
            <p style={{ fontSize: 12.5, color: "#c3cbc6", margin: 0 }}>
              nível {task.pontos} · {task.classificacao_status === "provisoria" ? "provisório" : task.classificacao_status === "em_revisao" ? "em revisão" : "definido pelo classificador"}
            </p>
          )}

          <div>
            <label htmlFor="task-descricao" style={labelSt}>Descrição</label>
            <textarea
              id="task-descricao"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              rows={4}
              aria-describedby="task-descricao-ajuda"
              style={{ ...inputSt, resize: "vertical" }}
            />
            <p id="task-descricao-ajuda" style={{ fontSize: 12, color: "#8a948e", margin: "6px 0 0" }}>
              Descreva o que precisa ser feito, quais partes do sistema mexe e o que ainda não está claro. O nível é definido a partir disso.
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
                <span style={{ flex: 1, fontSize: 13, color: item.done ? "#8a948e" : "#f2f5f3", textDecoration: item.done ? "line-through" : "none" }}>
                  {item.texto}
                </span>
                <button
                  type="button"
                  onClick={() => setChecklist((prev) => prev.filter((_, j) => j !== i))}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "#ff6b6b", fontSize: 14, padding: 0 }}
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

          {mode === "edit" && textoMudou && (
            <p role="status" style={{ fontSize: 12, color: "#f2c14e", margin: 0 }}>
              Editar o texto não muda o nível. Se a task mudou de escopo, peça reclassificação a um líder.
            </p>
          )}

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
            <label style={labelSt}>Sprint</label>
            <select value={sprintId} onChange={(e) => setSprintId(e.target.value)} style={inputSt}>
              <option value="">Sem sprint</option>
              {sprints.map((s) => (
                <option key={s.id} value={s.id}>Sprint {s.numero}</option>
              ))}
            </select>
          </div>

          {modoTrabalho === "PULL" ? (
            <div>
              <label style={labelSt}>Operacional</label>
              <p style={{ fontSize: 12, color: "#8a948e", margin: "4px 0 0", padding: "8px 10px", background: "rgba(62,224,111,0.055)", borderRadius: 8 }}>
                {mode === "create" || !task?.operacional_id
                  ? "Atribuição via fila de puxar — não é definida manualmente em modo Pull."
                  : `Responsável atual: ${operacionais.find((o) => o.id === task.operacional_id)?.nome ?? "—"} (somente leitura em modo Pull).`}
              </p>
            </div>
          ) : (
            <div>
              <label style={labelSt}>Operacional</label>
              <select value={operacionalId} onChange={(e) => setOperacionalId(e.target.value)} style={inputSt}>
                <option value="">Sem operacional</option>
                {operacionais.filter((o) => o.ativo).map((o) => (
                  <option key={o.id} value={o.id}>{o.nome}{o.papel ? ` — ${o.papel}` : ""}</option>
                ))}
              </select>
            </div>
          )}

          <div style={{ background: extra ? "rgba(62,224,111,0.12)" : "rgba(62,224,111,0.055)", border: `1px solid ${extra ? "rgba(62,224,111,0.35)" : "rgba(62,224,111,0.2)"}`, borderRadius: 8, padding: "10px 12px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
              <input type="checkbox" checked={extra} onChange={(e) => setExtra(e.target.checked)} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#c3cbc6" }}>Task extra</span>
            </label>
            <p style={{ fontSize: 11, color: "#8a948e", margin: "6px 0 0" }}>
              Trabalho concedido além do que a pessoa já tinha. Não entra no previsto
              da sprint e, se concluída antes do fechamento, vira bônus.
            </p>
          </div>

          <div style={{ background: requerAprovacao ? "rgba(177,151,252,0.10)" : "rgba(62,224,111,0.055)", border: `1px solid ${requerAprovacao ? "rgba(177,151,252,0.30)" : "rgba(62,224,111,0.2)"}`, borderRadius: 8, padding: "10px 12px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
              <input type="checkbox" checked={requerAprovacao} onChange={(e) => setRequerAprovacao(e.target.checked)} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#c3cbc6" }}>Requer aprovação do gerente</span>
            </label>
            <p style={{ fontSize: 11, color: "#8a948e", margin: "6px 0 0" }}>
              A task não pode ir direto de Em andamento pra Concluída — precisa passar por
              Pendente de aprovação primeiro.
            </p>
          </div>

          {mode === "create" && (
            <div>
              <label htmlFor="task-opiniao" style={labelSt}>Sua opinião sobre o nível (opcional)</label>
              <DsSelect id="task-opiniao" value={opiniao} onChange={(e) => setOpiniao(e.target.value)}>
                <option value="">sem opinião</option>
                {NIVEIS.map((n) => (
                  <option key={n} value={n}>{rotuloNivel(n)}</option>
                ))}
              </DsSelect>
              <p style={{ fontSize: 12, color: "#8a948e", margin: "6px 0 0" }}>
                Não define o nível. É usada pelo classificador como mais uma referência.
              </p>
            </div>
          )}

          {mode === "edit" && task && ehLider && (
            task.nivel_travado_em ? (
              <p style={{ fontSize: 12, color: "#8a948e", margin: 0 }}>
                nível travado desde {new Date(task.nivel_travado_em).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}
              </p>
            ) : (
              <div>
                <button type="button" onClick={handleReclassificar} disabled={reclassificando || saving} style={btnGhost}>
                  {reclassificando ? "Reclassificando…" : "Reclassificar"}
                </button>
              </div>
            )
          )}

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
                <label htmlFor="bloqueado" style={{ fontSize: 13, fontWeight: 600, color: "#c3cbc6", cursor: "pointer" }}>
                  Bloqueada
                </label>
              </div>
              {bloqueado && (
                <>
                <div>
                  <label htmlFor="bloqueio-tipo" style={labelSt}>Tipo do bloqueio</label>
                  <select
                    id="bloqueio-tipo"
                    value={bloqueioTipo}
                    onChange={(e) => setBloqueioTipo(e.target.value as "interno" | "cliente")}
                    style={inputSt}
                  >
                    <option value="interno">Interno (equipe, acesso, outra task)</option>
                    <option value="cliente">Dependência do cliente</option>
                  </select>
                  {bloqueioTipo === "cliente" && (
                    <p style={{ fontSize: 12, color: "#8a948e", margin: "6px 0 0" }}>
                      Se a sprint fechar com a task ainda esperando o cliente, ela não conta na Entrega de ninguém e o relógio de atraso fica pausado.
                    </p>
                  )}
                </div>
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
                </>
              )}
              {jaEstavaBloqueadoManual && !eraBloqueioCliente && !bloqueado && (
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
                <div style={{ background: "rgba(242,193,78,0.10)", border: "1px solid rgba(242,193,78,0.30)", borderRadius: 8, padding: 10 }}>
                  <p style={{ fontSize: 12, color: "#f2c14e", margin: "0 0 8px", fontWeight: 600 }}>
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

              {task?.coluna_kanban === "pendente_aprovacao" && (
                <div style={{ background: "rgba(177,151,252,0.10)", border: "1px solid rgba(177,151,252,0.30)", borderRadius: 8, padding: 12 }}>
                  <p style={{ fontSize: 12, color: "#b197fc", margin: "0 0 10px", fontWeight: 600 }}>
                    Esta task está esperando aprovação.
                  </p>
                  {!rejeitando ? (
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        type="button"
                        onClick={handleAprovar}
                        disabled={aprovando}
                        style={{ ...btnPrimary, opacity: aprovando ? 0.6 : 1 }}
                      >
                        {aprovando ? "Aprovando..." : "Aprovar"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setRejeitando(true)}
                        disabled={aprovando}
                        style={btnGhost}
                      >
                        Rejeitar
                      </button>
                    </div>
                  ) : (
                    <div>
                      <label style={labelSt}>Motivo da rejeição *</label>
                      <textarea
                        value={motivoRejeicao}
                        onChange={(e) => setMotivoRejeicao(e.target.value)}
                        rows={2}
                        placeholder="Por que esta task está voltando pra fila?"
                        style={{ ...inputSt, resize: "vertical", marginBottom: 8 }}
                      />
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          type="button"
                          onClick={handleRejeitar}
                          disabled={aprovando}
                          style={{ ...btnPrimary, background: "#ff6b6b", opacity: aprovando ? 0.6 : 1 }}
                        >
                          {aprovando ? "Rejeitando..." : "Confirmar rejeição"}
                        </button>
                        <button type="button" onClick={() => setRejeitando(false)} disabled={aprovando} style={btnGhost}>
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Histórico */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowHist((v) => !v)}
                  style={{ background: "none", border: "none", fontSize: 12, color: "#8a948e", cursor: "pointer", textDecoration: "underline", padding: 0 }}
                >
                  {showHist ? "Ocultar histórico" : "Ver histórico de transições"}
                </button>
                {showHist && (
                  <div style={{ marginTop: 10 }}>
                    {loadingHist ? (
                      <p style={{ fontSize: 12, color: "#8a948e" }}>Carregando...</p>
                    ) : transicoes.length === 0 ? (
                      <p style={{ fontSize: 12, color: "#8a948e" }}>Sem transições registradas.</p>
                    ) : (
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                        <thead>
                          <tr style={{ color: "#8a948e" }}>
                            <th style={{ textAlign: "left", padding: "4px 6px" }}>Campo</th>
                            <th style={{ textAlign: "left", padding: "4px 6px" }}>De → Para</th>
                            <th style={{ textAlign: "left", padding: "4px 6px" }}>Quem</th>
                            <th style={{ textAlign: "left", padding: "4px 6px" }}>Quando</th>
                            <th style={{ textAlign: "left", padding: "4px 6px" }}>Tempo anterior</th>
                          </tr>
                        </thead>
                        <tbody>
                          {transicoes.map((t) => {
                            const resolverValor = (v: string | null | undefined) => {
                              if (t.campo !== "operacional_id") return v ?? "—";
                              if (!v) return "—";
                              return operacionais.find((o) => o.id === v)?.nome ?? v;
                            };
                            return (
                            <tr key={t.id} style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                              <td style={{ padding: "4px 6px", color: "#c3cbc6" }}>{t.campo}</td>
                              <td style={{ padding: "4px 6px", color: "#f2f5f3" }}>{resolverValor(t.de)} → {resolverValor(t.para)}</td>
                              <td style={{ padding: "4px 6px", color: "#c3cbc6" }}>{t.autor ?? "—"}</td>
                              <td style={{ padding: "4px 6px", color: "#8a948e" }}>
                                {t.timestamp ? new Date(t.timestamp).toLocaleString("pt-BR") : "—"}
                              </td>
                              <td style={{ padding: "4px 6px", color: "#8a948e" }}>
                                {t.duracao_fase_anterior_segundos != null
                                  ? formatDuration(t.duracao_fase_anterior_segundos)
                                  : "—"}
                              </td>
                            </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          {err && <p style={{ fontSize: 12, color: "#ff6b6b", margin: 0 }}>{err}</p>}

          <div style={{ display: "flex", gap: 10, justifyContent: "space-between", marginTop: 4 }}>
            {mode === "edit" && (
              <button type="button" onClick={handleDelete} disabled={saving}
                style={{ background: "none", border: "none", fontSize: 12, color: "#ff6b6b", cursor: "pointer", padding: 0, textDecoration: "underline" }}>
                Excluir
              </button>
            )}
            <div style={{ display: "flex", gap: 10, marginLeft: "auto" }}>
              <button type="button" onClick={onClose} style={btnGhost}>Cancelar</button>
              <button type="submit" disabled={saving} style={{ ...btnPrimary, opacity: saving ? 0.6 : 1 }}>
                {saving ? (mode === "create" ? "Classificando…" : "Salvando…") : mode === "create" ? "Criar" : "Salvar"}
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
  task, sprints, funcionalidades, onClose, onSaved, modoTrabalho, meuOperacionalId,
}: {
  task: TaskKanbanResponse;
  sprints: SprintWithStatus[];
  funcionalidades: FuncionalidadeResponse[];
  onClose: () => void;
  onSaved: (t: TaskKanbanResponse) => void;
  modoTrabalho: "ATRIBUICAO" | "PULL";
  meuOperacionalId: string | null;
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
        background: "#0d1711", borderRadius: 16, padding: "28px 32px",
        width: "100%", maxWidth: 520, maxHeight: "90vh", overflowY: "auto",
        boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
      }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
          <span style={{ ...chip, background: "rgba(62,224,111,0.055)", color: "#c3cbc6" }} title={`${rotuloNivel(task.pontos)} · definido pelo classificador`}>{task.pontos}pt</span>
          {sprint && <span style={{ ...chip, background: "rgba(177,151,252,0.10)", color: "#b197fc" }}>Sprint {sprint.numero}</span>}
          {task.extra && <span style={{ ...chip, background: "rgba(62,224,111,0.12)", color: "#3ee06f" }}>+ extra</span>}
          {task.bloqueado && (
            <span style={{ ...chip, background: "rgba(255,107,107,0.10)", color: "#ff6b6b" }}>
              {task.bloqueio_tipo === "cliente" ? "Aguardando cliente" : "Bloqueada"}{task.motivo_bloqueio ? `: ${task.motivo_bloqueio}` : ""}
            </span>
          )}
        </div>

        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#f2f5f3", margin: "0 0 6px" }}>{task.titulo}</h3>
        {funcionalidade && (
          <p style={{ fontSize: 12, color: "#8a948e", margin: "0 0 16px" }}>
            {funcionalidade.id_funcional} — {funcionalidade.titulo}
          </p>
        )}

        {task.descricao && (
          <div style={{ fontSize: 13, color: "#c3cbc6", lineHeight: 1.6, marginBottom: 20 }}>
            <ReactMarkdown>{task.descricao}</ReactMarkdown>
          </div>
        )}

        <div>
          <label style={labelSt}>Checklist{checklist.length > 0 ? ` (${done}/${checklist.length})` : ""}</label>
          {checklist.length === 0 ? (
            <p style={{ fontSize: 13, color: "#8a948e", margin: 0 }}>Sem itens de checklist nesta task.</p>
          ) : (
            checklist.map((item, i) => (
              <label key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, cursor: "pointer" }}>
                <input type="checkbox" checked={item.done} disabled={saving} onChange={() => toggleItem(i)} />
                <span style={{ flex: 1, fontSize: 13, color: item.done ? "#8a948e" : "#f2f5f3", textDecoration: item.done ? "line-through" : "none" }}>
                  {item.texto}
                </span>
              </label>
            ))
          )}
        </div>

        {err && <p style={{ fontSize: 12, color: "#ff6b6b", marginTop: 10 }}>{err}</p>}

        {modoTrabalho === "PULL" && !task.operacional_id && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
            <button
              type="button"
              onClick={async () => {
                const atualizada = await puxarTask(task.id);
                onSaved(atualizada);
              }}
              style={btnPrimary}
            >
              Puxar esta task
            </button>
          </div>
        )}
        {/* Task em Pendente de aprovação só sai via Aprovar/Rejeitar (o backend
            devolve 409 em /devolver) — esconder o botão evita oferecer uma ação
            que só pode dar erro. */}
        {modoTrabalho === "PULL" && task.coluna_kanban !== "pendente_aprovacao" && task.operacional_id && (meuOperacionalId === task.operacional_id) && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
            <button
              type="button"
              onClick={async () => {
                const atualizada = await devolverTask(task.id);
                onSaved(atualizada);
              }}
              style={{ ...btnPrimary, background: "#0d1711", color: "#ff6b6b", border: "1px solid rgba(255,107,107,0.30)" }}
            >
              Devolver à fila
            </button>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
          <button type="button" onClick={onClose} style={btnPrimary}>Fechar</button>
        </div>
      </div>
    </div>
  );
}

function modoPendingMove(m: { de: string; para: string }): "mover" | "aprovar" | "rejeitar" {
  if (m.de !== "pendente_aprovacao") return "mover";
  return m.para === "concluida" ? "aprovar" : "rejeitar";
}

function labelForColuna(c: string): string {
  return COLUNAS.find((col) => col.id === c)?.label ?? c;
}

// ---------------------------------------------------------------------------
// Modal de confirmação de transição — usado pelo drag-and-drop e pelo aceite
// do banner de sugestão da IA. Cancelar não chama nenhuma API.

function ConfirmTransicaoModal({
  taskTitulo, de, para, onConfirm, onCancel, confirming, motivo, onMotivoChange, modo = "mover",
}: {
  taskTitulo: string;
  de: string;
  para: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirming: boolean;
  motivo?: string;
  onMotivoChange?: (v: string) => void;
  // Saída de pendente_aprovacao não é um "mover": vira aprovação (-> concluida)
  // ou rejeição (volta pra planejado, motivo obrigatório).
  modo?: "mover" | "aprovar" | "rejeitar";
}) {
  // Reabertura (TRANS-03): concluida -> em_andamento aceita um motivo opcional.
  const isReabertura = modo === "mover" && de === "concluida" && para === "em_andamento";
  const isRejeicao = modo === "rejeitar";
  const semMotivo = isRejeicao && !(motivo ?? "").trim();

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div style={{
        background: "#0d1711", borderRadius: 16, padding: "28px 32px",
        width: "100%", maxWidth: 420,
        boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
      }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#f2f5f3", margin: "0 0 14px" }}>
          {modo === "aprovar" ? "Aprovar task" : isRejeicao ? "Rejeitar task" : "Confirmar mudança de status"}
        </h3>
        <p style={{ fontSize: 14, color: "#c3cbc6", margin: "0 0 20px", lineHeight: 1.5 }}>
          {modo === "aprovar" ? (
            <>Aprovar <strong>{taskTitulo}</strong> e mover para <strong>{labelForColuna("concluida")}</strong>?</>
          ) : isRejeicao ? (
            <>Rejeitar <strong>{taskTitulo}</strong>? Ela volta para <strong>{labelForColuna("planejado")}</strong> sem responsável, e o operacional recebe o motivo.</>
          ) : (
            <>Mover <strong>{taskTitulo}</strong> de <strong>{labelForColuna(de)}</strong> para{" "}
            <strong>{labelForColuna(para)}</strong>?</>
          )}
        </p>
        {isRejeicao && onMotivoChange && (
          <div style={{ marginBottom: 20 }}>
            <label style={labelSt}>Motivo da rejeição</label>
            <textarea
              value={motivo ?? ""}
              onChange={(e) => onMotivoChange(e.target.value)}
              rows={3}
              placeholder="O que precisa ser ajustado?"
              style={{ ...inputSt, resize: "vertical" }}
              autoFocus
            />
          </div>
        )}
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
            disabled={confirming || semMotivo}
            style={{ ...btnPrimary, opacity: confirming || semMotivo ? 0.6 : 1 }}
          >
            {modo === "aprovar"
              ? (confirming ? "Aprovando…" : "Aprovar")
              : isRejeicao
                ? (confirming ? "Rejeitando…" : "Rejeitar")
                : (confirming ? "Movendo…" : "Confirmar")}
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
  color: "#8a948e",
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
    <button
      type="button"
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className="ds-task-card"
      style={{
        ...card,
        ...(task.bloqueado ? { borderColor: "rgba(255,107,107,0.30)", background: "rgba(255,107,107,0.06)" } : null),
      }}
    >
      <span style={{ fontSize: 14, fontWeight: 600, color: "#ffffff", lineHeight: 1.35 }}>
        {task.titulo}
      </span>

      <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ ...chip, background: "rgba(255,255,255,0.05)", color: "#c3cbc6" }} title={`${rotuloNivel(task.pontos)} · definido pelo classificador`}>{task.pontos}pt</span>

        {(task.classificacao_status === "provisoria" || task.classificacao_status === "em_revisao") && (
          <Chip tone="amber">{task.classificacao_status === "provisoria" ? "provisório" : "em revisão"}</Chip>
        )}

        {op && (
          <span style={{ ...chip, background: "rgba(177,151,252,0.14)", color: "#b197fc", borderColor: "rgba(177,151,252,0.3)" }}>{op.nome}</span>
        )}

        {task.extra && (
          <span style={{ ...chip, background: "rgba(62,224,111,0.12)", color: "#3ee06f", borderColor: "rgba(62,224,111,0.35)" }}>+ extra</span>
        )}

        {task.bloqueado && (
          <span style={{ ...chip, background: "rgba(255,107,107,0.10)", color: "#ff6b6b", borderColor: "rgba(255,107,107,0.30)" }}>{task.bloqueio_tipo === "cliente" ? "Aguardando cliente" : "Bloqueada"}</span>
        )}

        {task.travado_automatico && !task.travado_override && (
          <span style={{ ...chip, background: "rgba(242,193,78,0.10)", color: "#f2c14e", borderColor: "rgba(242,193,78,0.30)" }}>Travada</span>
        )}

        {total > 0 && (
          <span style={{
            ...chip,
            background: done === total ? "rgba(62,224,111,0.12)" : "rgba(255,255,255,0.05)",
            color: done === total ? "#3ee06f" : "#8a948e",
            borderColor: done === total ? "rgba(62,224,111,0.35)" : "rgba(255,255,255,0.08)",
          }}>
            {done}/{total} ✓
          </span>
        )}
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main component

export default function TasksKanbanTab({ projectId, sprints, operacionais, funcionalidades, modoTrabalho }: Props) {
  const [concluidasAbertas, setConcluidasAbertas] = useState(false);
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

  // aviso pós-criação (classificador) e opinião do operacional na conclusão
  const [avisoCriacao, setAvisoCriacao] = useState<{ nivel: number; justificativa: string | null } | null>(null);
  const [mostrarPorque, setMostrarPorque] = useState(false);
  const [opiniaoTaskId, setOpiniaoTaskId] = useState<string | null>(null);

  async function escolherOpiniao(nivel: number | null) {
    const id = opiniaoTaskId;
    setOpiniaoTaskId(null);
    if (id && nivel !== null) {
      try { await opinarNivelTask(id, nivel); } catch { /* opinião é opcional */ }
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
    // Saída de Pendente de aprovação só por aprovar/rejeitar, que são
    // gerente/líder-only no backend — operacional nem abre o modal.
    if (task.coluna_kanban === "pendente_aprovacao" && ehOperacional) {
      alert("Esta task está esperando aprovação. Só o gerente ou líder pode aprová-la ou rejeitá-la.");
      return;
    }
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
      const modo = modoPendingMove(pendingMove);
      const updated =
        modo === "aprovar"
          ? await aprovarTask(pendingMove.taskId, auth?.nome)
          : modo === "rejeitar"
            ? await rejeitarTask(pendingMove.taskId, motivoReabertura.trim(), auth?.nome)
            : await moverTaskKanban(
                pendingMove.taskId,
                pendingMove.para,
                auth?.nome,
                motivoReabertura.trim() || undefined
              );
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      if (ehOperacional && updated.coluna_kanban === "concluida") setOpiniaoTaskId(updated.id);
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
    { title: "Criar uma task", body: "Clique em '+ Nova task'. Informe título e descrição (o classificador define o nível a partir deles), e opcionalmente sprint, operacional, funcionalidade e checklist. O checklist já aparece na criação: são os itens que precisam estar prontos para a task poder ir para Concluída." },
    { title: "Pontos da task", body: "Os pontos são o nível de dificuldade da task, numa régua única para todos os projetos: 1 (simples), 2 (moderada), 3 (complexa) e 5 (muito complexa). Não existe total de pontos do projeto; os pontos só são somados dentro de uma sprint, para comparar o que foi entregue com o que estava previsto." },
    { title: "Checklist e Definition of Done", body: "Dentro da task você monta uma lista de itens e vai marcando conforme fica pronto. O card mostra o progresso no formato '3/5'. Se sobrar item aberto, o sistema recusa mover a task para Concluída. Task sem checklist não trava nada: a regra só vale se você criou a lista." },
    { title: "Sprint obrigatória para iniciar (DoR)", body: "Para mover uma task para 'Em andamento', ela precisa estar vinculada a uma sprint. Sem sprint não existe a quem creditar aquele trabalho quando a semana fechar." },
    { title: "WIP — limite de tasks simultâneas", body: "Cada operacional tem um limite de tasks em 'Em andamento' ao mesmo tempo, e o projeto também. Se o limite for atingido, o sistema bloqueia novos movimentos. Configure em Configurações." },
    { title: "Bloqueio: quem marca é quem trava", body: "Quando o trabalho para por algo que não depende de você (esperando cliente, acesso, outra task, uma decisão), marque a caixa 'Bloqueada' na task e escreva o motivo. O card ganha borda vermelha e o gerente vê no quadro. Ao destravar, alguém informa quem resolveu: Operacional ou Gerente. Essa resposta é o que alimenta a leitura de autonomia. Se o motivo for o cliente, o gerente escolhe 'Dependência do cliente': se a sprint fechar com a task ainda esperando, ela sai da conta de Entrega de todo mundo, não conta na Autonomia e o relógio de atraso fica pausado." },
    { title: "Task travada por tempo", body: "O relógio conta desde que a task está ativa — Planejado ou Em andamento, tanto faz — e a sprint dela já começou. Se passar de um dia e meio por ponto (uma de 2 pontos, 3 dias; uma de 4 pontos, 6 dias), ela ganha a etiqueta amarela 'Travada'. Se for concluída depois disso, os pontos dela são descontados da entrega. Mover a task pra uma sprint futura pausa o relógio; o gerente também pode suprimir o alerta dentro da task quando o atraso não é culpa de quem estava nela, e aí não há desconto." },
    { title: "Task extra", body: "Quando alguém termina tudo que tinha, aparece no Kanban dela o botão 'Quero mais uma task' e você recebe um e-mail. Ao criar a task para essa pessoa, marque a caixa 'Task extra': ela não entra no previsto da sprint e, se concluída antes do fechamento, vira bônus. Recusar o pedido é uma resposta válida; deixar sem resposta é a única errada." },
    { title: "Kanban alimenta Planning e Review", body: "Ao gerar um Planning ou Review pela aba Sprints, a IA captura o estado atual do kanban dessa sprint — cada task com coluna, pontos e se está bloqueada entra automaticamente no contexto. O que você vê aqui é exatamente o que a IA usa para escrever os documentos." },
    { title: "Sugestões automáticas do Review", body: "Quando um review é registrado na aba Sprints, o DocuData analisa o texto e detecta quais tasks foram mencionadas como concluídas. Sugestões aparecem no banner amarelo acima do kanban — você aceita ou ignora cada uma." },
    { title: "Mover tasks entre colunas", body: "Arraste a task ou use o botão de edição para mudar a coluna. Planejado → Em andamento → Concluída. Cada transição é registrada com quem estava na task naquele momento, e é isso que define quem recebe os pontos da entrega." },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <TutorialBanner heading="Tasks e Kanban" steps={tasksSteps} />
      {/* Filters */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <DsSelect aria-label="Filtrar por sprint" value={filterSprintId} onChange={(e) => setFilterSprintId(e.target.value)} style={{ width: 200, height: 40, fontSize: 13.5 }}>
          <option value="">Todas as sprints</option>
          {sortedSprints.map((s) => (
            <option key={s.id} value={s.id}>Sprint {s.numero}</option>
          ))}
        </DsSelect>

        <DsSelect aria-label="Filtrar por operacional" value={filterOpId} onChange={(e) => setFilterOpId(e.target.value)} style={{ width: 240, height: 40, fontSize: 13.5 }}>
          <option value="">Todos os operacionais</option>
          {operacionais.filter((o) => o.ativo).map((o) => (
            <option key={o.id} value={o.id}>{o.nome}</option>
          ))}
        </DsSelect>

        <DsSelect aria-label="Filtrar por funcionalidade" value={filterFuncId} onChange={(e) => setFilterFuncId(e.target.value)} style={{ flex: "1 1 220px", width: "auto", height: 40, fontSize: 13.5 }}>
          <option value="">Todas as funcionalidades</option>
          {funcionalidades.map((f) => (
            <option key={f.id} value={f.id}>{f.id_funcional} · {f.titulo}</option>
          ))}
        </DsSelect>

        {!ehOperacional && (
          <DsButton variant="primary" onClick={() => setCreateModal({ defaultSprintId: filterSprintId || lastSprint?.id })}>
            + Nova task
          </DsButton>
        )}
      </div>

      {/* Pedir nova task — só aparece pro operacional que zerou a fila */}
      {ehOperacional && meuOperacional && minhasTasksAbertas === 0 && (
        <div style={{
          background: "rgba(62,224,111,0.12)", border: "1px solid rgba(62,224,111,0.35)", borderRadius: 10,
          padding: "12px 16px", marginBottom: 14,
        }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "#3ee06f", margin: "0 0 4px" }}>
            Você concluiu tudo que estava com você.
          </p>
          <p style={{ fontSize: 12, color: "#7cf0a0", margin: "0 0 10px" }}>
            Peça mais trabalho sem precisar puxar conversa. O gerente recebe um e-mail
            e, se tiver algo disponível, te passa uma task extra.
          </p>
          {jaPediu ? (
            <p style={{ fontSize: 12, color: "#7cf0a0", margin: 0, fontWeight: 600 }}>
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
                style={{ ...btnPrimary, background: "rgba(62,224,111,0.12)" }}
              >
                {pedindoTask ? "Enviando..." : "Quero mais uma task"}
              </button>
            </>
          )}
          {avisoPedido && <p style={{ fontSize: 12, color: "#7cf0a0", marginTop: 8 }}>{avisoPedido}</p>}
        </div>
      )}

      {/* Pedidos pendentes — visão do gerente */}
      {!ehOperacional && solicitacoes.length > 0 && (
        <div style={{
          background: "rgba(62,224,111,0.12)", border: "1px solid rgba(62,224,111,0.35)", borderRadius: 10,
          padding: "12px 16px", marginBottom: 14,
        }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "#3ee06f", margin: "0 0 8px" }}>
            {solicitacoes.length} pedido{solicitacoes.length > 1 ? "s" : ""} de nova task
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {solicitacoes.map((s) => (
              <div key={s.id} style={{
                display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
                background: "#0d1711", border: "1px solid rgba(62,224,111,0.35)", borderRadius: 7, padding: "8px 12px",
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 13, color: "#c3cbc6" }}>
                    <strong>{s.operacional_nome}</strong> está sem task em aberto e pediu mais trabalho.
                  </span>
                  {s.sugestao && (
                    <p style={{ fontSize: 12, color: "#7cf0a0", background: "rgba(62,224,111,0.12)", borderRadius: 6, padding: "6px 10px", margin: "6px 0 0" }}>
                      <strong>Sugestão:</strong> {s.sugestao}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => { handleResolverPedido(s.id, "atendida"); setCreateModal({ defaultSprintId: filterSprintId || lastSprint?.id }); }}
                  style={{ ...btnPrimary, padding: "5px 14px", fontSize: 12, background: "rgba(62,224,111,0.12)" }}
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
          background: "rgba(255,107,107,0.10)", border: "1px solid rgba(255,107,107,0.30)", borderRadius: 8,
          padding: "10px 14px", fontSize: 13, color: "#ff6b6b", marginBottom: 12,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span>{wipError}</span>
          <button onClick={() => setWipError("")} style={{ background: "none", border: "none", cursor: "pointer", color: "#ff6b6b", fontSize: 16, padding: 0 }}>×</button>
        </div>
      )}

      {/* Sugestões do review */}
      {sugestoes.length > 0 && (
        <div style={{
          background: "rgba(242,193,78,0.10)", border: "1px solid rgba(242,193,78,0.30)", borderRadius: 10,
          padding: "12px 16px", marginBottom: 14,
        }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "#f2c14e", margin: "0 0 8px" }}>
            📋 {sugestoes.length} sugestão{sugestoes.length > 1 ? "ões" : ""} do review — tasks mencionadas como concluídas
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sugestoes.map((s) => (
              <div key={s.id} style={{
                display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
                background: "#0d1711", border: "1px solid rgba(242,193,78,0.30)", borderRadius: 7, padding: "8px 12px",
              }}>
                <span style={{ fontSize: 13, color: "#c3cbc6", flex: 1, minWidth: 0 }}>
                  <strong>{s.task_titulo}</strong>
                  {s.motivo && <span style={{ color: "#8a948e", fontWeight: 400 }}> — {s.motivo}</span>}
                </span>
                <button
                  disabled={resolvingId === s.id}
                  onClick={() => setPendingSugestao(s)}
                  style={{ ...btnPrimary, padding: "5px 14px", fontSize: 12, background: "rgba(62,224,111,0.12)", opacity: resolvingId === s.id ? 0.5 : 1 }}
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

      {err && <p style={{ color: "#ff6b6b", fontSize: 13 }}>{err}</p>}

      {loading ? (
        <p role="status" style={{ color: "#8a948e", fontSize: 13, margin: 0 }}>Carregando tasks...</p>
      ) : (
        <div className="ds-tasks-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 14, alignItems: "start" }}>
          {COLUNAS.map((col) => {
            const colTasks = byColuna(col.id);
            const recolher = col.id === "concluida" && !concluidasAbertas && colTasks.length > CONCLUIDAS_VISIVEIS;
            const visiveis = recolher ? colTasks.slice(0, CONCLUIDAS_VISIVEIS) : colTasks;
            return (
              <div
                key={col.id}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => handleDrop(col.id)}
                style={{
                  display: "flex", flexDirection: "column", gap: 10, minWidth: 0, minHeight: 120,
                  padding: 16, borderRadius: 14, background: "rgba(62,224,111,0.04)", border: "1px solid rgba(62,224,111,0.16)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 2px 6px" }}>
                  <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: col.color, boxShadow: `0 0 8px ${col.color}`, flexShrink: 0 }} />
                  <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, letterSpacing: "0.14em", textTransform: "uppercase", color: col.color, fontWeight: 600 }}>
                    {col.label}
                  </span>
                  <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, padding: "1px 8px", borderRadius: 999, background: "rgba(255,255,255,0.06)", color: "#c3cbc6" }}>
                    {colTasks.length}
                  </span>
                  {!ehOperacional && (
                    <button
                      type="button"
                      className="ds-text-btn"
                      onClick={() => setCreateModal({ defaultSprintId: filterSprintId || lastSprint?.id })}
                      aria-label={`Nova task em ${col.label}`}
                      title="Nova task"
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#8a948e", fontSize: 16, lineHeight: 1, padding: 0, marginLeft: "auto" }}
                    >
                      +
                    </button>
                  )}
                </div>

                {colTasks.length === 0 ? (
                  <div style={{ padding: "28px 12px", border: "1px dashed rgba(255,255,255,0.14)", borderRadius: 12, textAlign: "center", fontSize: 13, color: "#5d6661" }}>
                    Nenhuma task
                  </div>
                ) : (
                  visiveis.map((t) => (
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
                {col.id === "concluida" && colTasks.length > CONCLUIDAS_VISIVEIS && (
                  <button
                    type="button"
                    className="ds-text-btn"
                    aria-expanded={concluidasAbertas}
                    onClick={() => setConcluidasAbertas((v) => !v)}
                    style={{ background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", textAlign: "center", fontSize: 12.5, color: "#8a948e", padding: 6 }}
                  >
                    {concluidasAbertas ? "Mostrar menos" : `+ ${colTasks.length - CONCLUIDAS_VISIVEIS} tasks concluídas`}
                  </button>
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
          modoTrabalho={modoTrabalho}
          onClose={() => setCreateModal(null)}
          onSaved={(t, criada) => {
            upsertTask(t);
            setCreateModal(null);
            if (criada) { setAvisoCriacao({ nivel: t.pontos, justificativa: t.justificativa_nivel ?? null }); setMostrarPorque(false); }
          }}
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
            modoTrabalho={modoTrabalho}
            meuOperacionalId={meuOperacional?.id ?? null}
          />
        ) : (
          <TaskModal
            mode="edit"
            task={editModal}
            projectId={projectId}
            sprints={sprints}
            operacionais={operacionais}
            funcionalidades={funcionalidades}
            modoTrabalho={modoTrabalho}
            onClose={() => setEditModal(null)}
            onSaved={(t) => { upsertTask(t); setEditModal(null); }}
            onReclassified={() => { load(); setEditModal(null); }}
            onDeleted={(id) => { setTasks((prev) => prev.filter((t) => t.id !== id)); setEditModal(null); }}
          />
        )
      )}

      {avisoCriacao && (
        <div role="status" style={{ position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)", zIndex: 1100, maxWidth: 480, width: "calc(100% - 32px)", background: "#0d1711", border: "1px solid rgba(62,224,111,0.35)", borderRadius: 12, padding: "12px 16px", boxShadow: "0 12px 40px rgba(0,0,0,0.4)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: 13.5, color: "#f2f5f3", fontWeight: 600 }}>
              Task criada · nível {avisoCriacao.nivel} · {rotuloNivel(avisoCriacao.nivel)}
            </span>
            {avisoCriacao.justificativa && (
              <button type="button" onClick={() => setMostrarPorque((v) => !v)} aria-expanded={mostrarPorque} style={btnGhost}>
                por quê?
              </button>
            )}
            <button type="button" onClick={() => setAvisoCriacao(null)} aria-label="Fechar aviso" style={{ marginLeft: "auto", background: "none", border: "none", color: "#8a948e", cursor: "pointer", fontSize: 16 }}>×</button>
          </div>
          {mostrarPorque && avisoCriacao.justificativa && (
            <p style={{ fontSize: 12.5, color: "#c3cbc6", margin: "8px 0 0", lineHeight: 1.5 }}>{avisoCriacao.justificativa}</p>
          )}
        </div>
      )}

      {opiniaoTaskId !== null && (
        <div role="dialog" aria-modal="true" aria-labelledby="opiniao-titulo" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1200 }}>
          <div style={{ background: "#0d1711", borderRadius: 16, padding: "24px 28px", width: "100%", maxWidth: 420, boxShadow: "0 20px 60px rgba(0,0,0,0.18)" }}>
            <h3 id="opiniao-titulo" style={{ fontSize: 16, fontWeight: 800, color: "#f2f5f3", margin: "0 0 16px" }}>
              Na sua visão, qual era o nível dessa task?
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <button type="button" style={btnGhost} onClick={() => escolherOpiniao(1)}>1 · simples</button>
              <button type="button" style={btnGhost} onClick={() => escolherOpiniao(2)}>2 · moderada</button>
              <button type="button" style={btnGhost} onClick={() => escolherOpiniao(3)}>3 · complexa</button>
              <button type="button" style={btnGhost} onClick={() => escolherOpiniao(5)}>5 · muito complexa</button>
              <button type="button" style={{ ...btnGhost, border: "none", background: "none", color: "#8a948e" }} onClick={() => escolherOpiniao(null)}>Pular</button>
            </div>
          </div>
        </div>
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
          modo={modoPendingMove(pendingMove)}
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
