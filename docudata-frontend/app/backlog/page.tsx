"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { Button, Card, Chip, ErrorNotice, Input, PageHeader, Select, Textarea } from "../components/ds";
import { ds } from "../lib/ds";
import type { Tone } from "../lib/ds";
import {
  createBacklogItem, deleteBacklogItem, listBacklog, updateBacklogItem,
  type BacklogItem, type BacklogPrioridade, type BacklogStatus,
} from "../lib/api";

const PRIORIDADES: { valor: BacklogPrioridade; label: string; tom: Tone; peso: number }[] = [
  { valor: "alta", label: "Alta", tom: "red", peso: 0 },
  { valor: "media", label: "Média", tom: "amber", peso: 1 },
  { valor: "baixa", label: "Baixa", tom: "neutral", peso: 2 },
];
const prioridadeDe = (v: BacklogPrioridade) => PRIORIDADES.find((p) => p.valor === v)!;

// Mesmas colunas e cores do Kanban das tasks, sem "Pendente de aprovação" (aqui não há aprovação).
const COLUNAS: { id: BacklogStatus; label: string; color: string }[] = [
  { id: "planejado", label: "Planejado", color: "#8a948e" },
  { id: "andamento", label: "Em andamento", color: "#f2c14e" },
  { id: "concluido", label: "Concluído", color: "#3ee06f" },
];

export default function BacklogPage() {
  const auth = useAuth();
  const liberado = !!auth && auth.cargo !== "operacional";
  const [itens, setItens] = useState<BacklogItem[] | null>(null);
  const [erro, setErro] = useState("");
  const [titulo, setTitulo] = useState("");
  const [notas, setNotas] = useState("");
  const [prioridade, setPrioridade] = useState<BacklogPrioridade>("media");
  const [salvando, setSalvando] = useState(false);
  const [arrastando, setArrastando] = useState<string | null>(null);
  const [sobre, setSobre] = useState<BacklogStatus | null>(null);
  const [aberto, setAberto] = useState<string | null>(null);
  const [rascunho, setRascunho] = useState({ titulo: "", notas: "" });

  useEffect(() => {
    if (!liberado) return;
    listBacklog().then(setItens).catch((e: Error) => setErro(e.message));
  }, [liberado]);

  const porColuna = useMemo(() => {
    const mapa: Record<BacklogStatus, BacklogItem[]> = { planejado: [], andamento: [], concluido: [] };
    for (const i of itens ?? []) mapa[i.status].push(i);
    for (const col of COLUNAS) {
      mapa[col.id].sort((a, b) => col.id === "concluido"
        ? (b.concluido_em ?? "").localeCompare(a.concluido_em ?? "")
        : prioridadeDe(a.prioridade).peso - prioridadeDe(b.prioridade).peso || b.criado_em.localeCompare(a.criado_em));
    }
    return mapa;
  }, [itens]);

  function trocar(novo: BacklogItem) {
    setItens((atual) => (atual ?? []).map((i) => (i.id === novo.id ? novo : i)));
  }

  async function executar(acao: () => Promise<void>) {
    setErro("");
    try { await acao(); } catch (e) { setErro(e instanceof Error ? e.message : "Algo deu errado"); }
  }

  async function adicionar(e: React.FormEvent) {
    e.preventDefault();
    if (!titulo.trim()) return;
    setSalvando(true);
    await executar(async () => {
      const novo = await createBacklogItem({ titulo: titulo.trim(), notas: notas.trim() || undefined, prioridade });
      setItens((atual) => [novo, ...(atual ?? [])]);
      setTitulo(""); setNotas("");
    });
    setSalvando(false);
  }

  /** Move o card já na tela e desfaz se o servidor recusar. */
  function mover(item: BacklogItem, status: BacklogStatus) {
    if (item.status === status) return Promise.resolve();
    const antes = item;
    trocar({ ...item, status, feito: status === "concluido" });
    return executar(async () => {
      try { trocar(await updateBacklogItem(item.id, { status })); } catch (e) { trocar(antes); throw e; }
    });
  }

  function soltar(status: BacklogStatus) {
    const item = (itens ?? []).find((i) => i.id === arrastando);
    setArrastando(null); setSobre(null);
    if (item) void mover(item, status);
  }

  const mudarPrioridade = (i: BacklogItem, p: BacklogPrioridade) => executar(async () => trocar(await updateBacklogItem(i.id, { prioridade: p })));
  const apagar = (i: BacklogItem) => {
    if (!confirm(`Apagar "${i.titulo}"?`)) return Promise.resolve();
    return executar(async () => {
      await deleteBacklogItem(i.id);
      setItens((atual) => (atual ?? []).filter((x) => x.id !== i.id));
      setAberto(null);
    });
  };

  function abrir(i: BacklogItem) {
    setAberto(i.id);
    setRascunho({ titulo: i.titulo, notas: i.notas ?? "" });
  }

  async function salvarEdicao(i: BacklogItem) {
    const novoTitulo = rascunho.titulo.trim();
    if (!novoTitulo) return;
    if (novoTitulo === i.titulo && rascunho.notas.trim() === (i.notas ?? "")) { setAberto(null); return; }
    await executar(async () => {
      trocar(await updateBacklogItem(i.id, { titulo: novoTitulo, notas: rascunho.notas }));
      setAberto(null);
    });
  }

  if (auth && !liberado) return <ErrorNotice>Esta página é só de Gerente, Líder e Owner.</ErrorNotice>;

  return (
    <>
      <PageHeader title="Backlog" subtitle="Suas coisas a fazer. Só você vê esta página." />

      {erro && <ErrorNotice>{erro}</ErrorNotice>}

      <Card>
        <form onSubmit={adicionar} style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Input aria-label="Novo item" placeholder="O que precisa ser feito?" value={titulo} maxLength={200} onChange={(e) => setTitulo(e.target.value)} style={{ flex: "1 1 320px", width: "auto" }} />
            <Select aria-label="Prioridade" value={prioridade} onChange={(e) => setPrioridade(e.target.value as BacklogPrioridade)} style={{ width: 130 }}>
              {PRIORIDADES.map((p) => <option key={p.valor} value={p.valor}>{p.label}</option>)}
            </Select>
            <Button type="submit" variant="primary" disabled={salvando || !titulo.trim()}>Adicionar</Button>
          </div>
          <Textarea aria-label="Notas" placeholder="Notas (opcional)" rows={2} value={notas} maxLength={5000} onChange={(e) => setNotas(e.target.value)} />
        </form>
      </Card>

      {!itens && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}

      {itens && (
        <div className="ds-backlog-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 14, alignItems: "start" }}>
          {COLUNAS.map((col) => {
            const doStatus = porColuna[col.id];
            return (
              <div
                key={col.id}
                onDragOver={(e) => { e.preventDefault(); if (sobre !== col.id) setSobre(col.id); }}
                onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setSobre(null); }}
                onDrop={() => soltar(col.id)}
                style={{
                  display: "flex", flexDirection: "column", gap: 10, minWidth: 0, minHeight: 140, padding: 16, borderRadius: 14,
                  background: "rgba(62,224,111,0.04)", transition: "border-color 0.15s",
                  border: `1px solid ${sobre === col.id && arrastando ? col.color : "rgba(62,224,111,0.16)"}`,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 2px 6px" }}>
                  <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: col.color, boxShadow: `0 0 8px ${col.color}`, flexShrink: 0 }} />
                  <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, letterSpacing: "0.14em", textTransform: "uppercase", color: col.color, fontWeight: 600 }}>{col.label}</span>
                  <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, padding: "1px 8px", borderRadius: 999, background: "rgba(255,255,255,0.06)", color: "#c3cbc6" }}>{doStatus.length}</span>
                </div>

                {doStatus.length === 0 && (
                  <div style={{ padding: "28px 12px", border: "1px dashed rgba(255,255,255,0.14)", borderRadius: 12, textAlign: "center", fontSize: 13, color: "#5d6661" }}>
                    {arrastando ? "Solte aqui" : "Nada por aqui"}
                  </div>
                )}

                {doStatus.map((i) => (
                  <article
                    key={i.id}
                    draggable={aberto !== i.id}
                    onDragStart={() => setArrastando(i.id)}
                    onDragEnd={() => { setArrastando(null); setSobre(null); }}
                    className="ds-task-card"
                    style={{
                      display: "flex", flexDirection: "column", gap: 10, padding: 16, borderRadius: 12, textAlign: "left", width: "100%",
                      background: "rgba(62,224,111,0.055)", border: "1px solid rgba(62,224,111,0.17)", fontFamily: "inherit",
                      opacity: arrastando === i.id ? 0.4 : 1, cursor: aberto === i.id ? "default" : "grab",
                    }}
                  >
                    {aberto === i.id ? (
                      <>
                        <Input autoFocus aria-label="Título" value={rascunho.titulo} maxLength={200} onChange={(e) => setRascunho({ ...rascunho, titulo: e.target.value })} />
                        <Textarea aria-label="Notas" rows={3} placeholder="Notas (opcional)" value={rascunho.notas} maxLength={5000} onChange={(e) => setRascunho({ ...rascunho, notas: e.target.value })} />
                        <div style={{ display: "flex", gap: 8, justifyContent: "space-between" }}>
                          <Button type="button" variant="secondary" onClick={() => void apagar(i)} style={{ color: ds.red }}>Apagar</Button>
                          <span style={{ display: "flex", gap: 8 }}>
                            <Button type="button" variant="secondary" onClick={() => setAberto(null)}>Cancelar</Button>
                            <Button type="button" variant="primary" disabled={!rascunho.titulo.trim()} onClick={() => void salvarEdicao(i)}>Salvar</Button>
                          </span>
                        </div>
                      </>
                    ) : (
                      <>
                        <button
                          type="button" onClick={() => abrir(i)} title="Clique para editar"
                          style={{ background: "none", border: "none", padding: 0, textAlign: "left", cursor: "pointer", fontFamily: "inherit", fontSize: 14, fontWeight: 600, lineHeight: 1.35, color: i.status === "concluido" ? ds.muted : ds.white, textDecoration: i.status === "concluido" ? "line-through" : "none", overflowWrap: "anywhere" }}
                        >
                          {i.titulo}
                        </button>
                        {i.notas && <span style={{ fontSize: 13, lineHeight: 1.5, color: ds.muted, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{i.notas}</span>}
                        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                          {i.status === "concluido"
                            ? <Chip tone="green">Feito</Chip>
                            : (
                              <Select aria-label={`Prioridade de ${i.titulo}`} value={i.prioridade} onChange={(e) => void mudarPrioridade(i, e.target.value as BacklogPrioridade)} style={{ width: 100, height: 28, fontSize: 12 }}>
                                {PRIORIDADES.map((p) => <option key={p.valor} value={p.valor}>{p.label}</option>)}
                              </Select>
                            )}
                          {/* Alternativa ao arrastar (celular/teclado). */}
                          <Select aria-label={`Mover "${i.titulo}" para`} value={i.status} onChange={(e) => void mover(i, e.target.value as BacklogStatus)} style={{ width: 130, height: 28, fontSize: 12, marginLeft: "auto" }}>
                            {COLUNAS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                          </Select>
                        </div>
                      </>
                    )}
                  </article>
                ))}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
