"use client";

import type { FuncionalidadeResponse, SprintWithStatus } from "../../lib/api";
import { ds, innerStyle } from "../../lib/ds";
import { Button, Card, Select } from "../ds";

export type KanbanStatus = "nao_iniciada" | "em_andamento" | "concluida";

interface TaskCount { total: number; concluidas: number }

const COLUNAS: { status: KanbanStatus; label: string; color: string }[] = [
  { status: "nao_iniciada", label: "Planejado", color: ds.muted },
  { status: "em_andamento", label: "Em andamento", color: ds.amber },
  { status: "concluida", label: "Concluído", color: ds.green },
];

interface Props {
  sprints: SprintWithStatus[];
  sprintSelecionada: number;
  onSelectSprint: (numero: number) => void;
  colunas: Record<KanbanStatus, FuncionalidadeResponse[]>;
  taskCounts: Map<string, TaskCount>;
  saving: boolean;
  onDragStart: (funcId: string) => void;
  onDragEnd: () => void;
  onDrop: (status: KanbanStatus) => void;
  /** Adicionar funcionalidade à sprint (fica na coluna Em andamento, como no protótipo). */
  adding: boolean;
  addFuncId: string;
  funcsDisponiveis: FuncionalidadeResponse[];
  onStartAdding: () => void;
  onChangeAddFunc: (id: string) => void;
  onConfirmAdd: () => void;
  onCancelAdd: () => void;
}

function KanbanItem({ f, count, color }: { f: FuncionalidadeResponse; count?: TaskCount; color: string }) {
  const temTasks = count && count.total > 0;
  const completa = temTasks && count.concluidas === count.total;
  const pct = temTasks ? (count.concluidas / count.total) * 100 : 0;
  return (
    <div style={{ ...innerStyle, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
      <span style={{ fontSize: 14, fontWeight: 600, color: ds.white, lineHeight: 1.35 }}>{f.titulo}</span>
      {temTasks ? (
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div aria-hidden="true" style={{ flex: 1, height: 5, borderRadius: 3, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
            <div style={{ width: `${pct}%`, height: "100%", background: completa ? ds.green : color }} />
          </div>
          <span style={{ fontFamily: ds.fontMono, fontSize: 11.5, color: completa ? ds.green : ds.text2 }}>
            {count.concluidas}/{count.total} tasks
          </span>
        </div>
      ) : (
        <span style={{ fontFamily: ds.fontMono, fontSize: 11.5, color: ds.dim }}>sem tasks</span>
      )}
    </div>
  );
}

const dashedBox: React.CSSProperties = {
  padding: "28px 12px", border: `1px dashed ${ds.borderStrong}`, borderRadius: 12,
  textAlign: "center", fontSize: 13, color: ds.dim,
};

export default function SprintKanbanBoard(p: Props) {
  const ordenadas = [...p.sprints].sort((a, b) => b.numero - a.numero);
  return (
    <Card>
      <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em", color: ds.white }}>Kanban de Sprint</h3>
          {ordenadas.length > 0 && (
            <Select
              aria-label="Sprint do kanban"
              value={String(p.sprintSelecionada)}
              onChange={(e) => p.onSelectSprint(Number(e.target.value))}
              style={{ width: 160, height: 40, fontSize: 13.5 }}
            >
              {ordenadas.map((s) => <option key={s.id} value={String(s.numero)}>Sprint {s.numero}</option>)}
            </Select>
          )}
        </div>

        {ordenadas.length === 0 ? (
          <div style={dashedBox}>Nenhuma sprint cadastrada.</div>
        ) : (
          <div className="ds-kanban-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 16, opacity: p.saving ? 0.6 : 1, transition: "opacity 0.15s" }}>
            {COLUNAS.map((col) => {
              const itens = p.colunas[col.status];
              return (
                <div
                  key={col.status}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => p.onDrop(col.status)}
                  style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 4px 6px" }}>
                    <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: col.color, boxShadow: `0 0 8px ${col.color}`, flexShrink: 0 }} />
                    <span style={{ fontFamily: ds.fontMono, fontSize: 11.5, letterSpacing: "0.14em", textTransform: "uppercase", color: col.color, fontWeight: 600 }}>{col.label}</span>
                    <span style={{ fontFamily: ds.fontMono, fontSize: 11, padding: "1px 8px", borderRadius: 999, background: "rgba(255,255,255,0.06)", color: ds.text2 }}>{itens.length}</span>
                  </div>
                  {itens.length === 0 && col.status !== "em_andamento" && <div style={dashedBox}>Nenhum item</div>}
                  {itens.map((f) => (
                    <div key={f.id} draggable onDragStart={() => p.onDragStart(f.id)} onDragEnd={p.onDragEnd} style={{ cursor: "grab" }}>
                      <KanbanItem f={f} count={p.taskCounts.get(f.id)} color={col.color} />
                    </div>
                  ))}
                  {col.status === "em_andamento" && (
                    p.adding ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        <Select aria-label="Funcionalidade para adicionar à sprint" value={p.addFuncId} onChange={(e) => p.onChangeAddFunc(e.target.value)} style={{ height: 40, fontSize: 13 }}>
                          <option value="">Selecione…</option>
                          {p.funcsDisponiveis.map((f) => <option key={f.id} value={f.id}>{f.id_funcional} · {f.titulo}</option>)}
                        </Select>
                        <div style={{ display: "flex", gap: 8 }}>
                          <Button variant="primary" size="sm" onClick={p.onConfirmAdd} disabled={!p.addFuncId || p.saving}>{p.saving ? "Adicionando…" : "Confirmar"}</Button>
                          <Button variant="ghost" size="sm" onClick={p.onCancelAdd}>Cancelar</Button>
                        </div>
                      </div>
                    ) : (
                      <button type="button" className="ds-row-link" onClick={p.onStartAdding} style={{ ...dashedBox, background: "none", cursor: "pointer", fontFamily: "inherit", width: "100%" }}>
                        + Adicionar funcionalidade
                      </button>
                    )
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}
