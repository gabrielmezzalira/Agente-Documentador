"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { Button, Card, Chip, ErrorNotice, Input, PageHeader, Textarea } from "../components/ds";
import { ds } from "../lib/ds";
import {
  createBacklogItem, deleteBacklogItem, listBacklog, reordenarBacklog, updateBacklogItem,
  type BacklogItem, type BacklogStatus,
} from "../lib/api";

// Mesmas colunas e cores do Kanban das tasks, sem "Pendente de aprovação" (aqui não há aprovação).
const COLUNAS: { id: BacklogStatus; label: string; color: string }[] = [
  { id: "planejado", label: "Planejado", color: "#8a948e" },
  { id: "andamento", label: "Em andamento", color: "#f2c14e" },
  { id: "concluido", label: "Concluído", color: "#3ee06f" },
];

function LinhaDeEncaixe({ cor }: { cor: string }) {
  return <div aria-hidden="true" style={{ height: 3, borderRadius: 2, background: cor, boxShadow: `0 0 8px ${cor}`, margin: "-4px 0" }} />;
}

export default function BacklogPage() {
  const auth = useAuth();
  const liberado = !!auth && auth.cargo !== "operacional";
  const [itens, setItens] = useState<BacklogItem[] | null>(null);
  const [erro, setErro] = useState("");
  const [titulo, setTitulo] = useState("");
  const [notas, setNotas] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [arrastando, setArrastando] = useState<string | null>(null);
  // Onde o card arrastado cairia: coluna e posição (a linha colorida marca o ponto).
  const [alvo, setAlvo] = useState<{ col: BacklogStatus; indice: number } | null>(null);
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
      mapa[col.id].sort((x, y) =>
        (x.ordem ?? 0) - (y.ordem ?? 0) || (col.id === "concluido"
          ? (y.concluido_em ?? "").localeCompare(x.concluido_em ?? "")
          : y.criado_em.localeCompare(x.criado_em)));
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
      const novo = await createBacklogItem({ titulo: titulo.trim(), notas: notas.trim() || undefined, prioridade: "media" });
      setItens((atual) => [novo, ...(atual ?? [])]);
      setTitulo(""); setNotas("");
    });
    setSalvando(false);
  }

  /** Põe o card na posição do ponto marcado: já na tela, e desfaz se o servidor recusar. */
  function soltar() {
    const destino = alvo;
    const item = (itens ?? []).find((i) => i.id === arrastando);
    setArrastando(null); setAlvo(null);
    if (!item || !destino) return;
    const coluna = porColuna[destino.col];
    const demais = coluna.filter((i) => i.id !== item.id);
    // O ponto foi medido com o próprio card ainda na lista: ajusta se ele estava antes dele.
    const antes = coluna.findIndex((i) => i.id === item.id);
    const posicao = Math.min(demais.length, antes !== -1 && antes < destino.indice ? destino.indice - 1 : destino.indice);
    const ids = [...demais.slice(0, posicao).map((i) => i.id), item.id, ...demais.slice(posicao).map((i) => i.id)];
    if (item.status === destino.col && ids.every((id, n) => id === coluna[n]?.id)) return;

    const snapshot = itens;
    const ordemNova = new Map(ids.map((id, n) => [id, n]));
    setItens((atual) => (atual ?? []).map((i) => ordemNova.has(i.id)
      ? { ...i, ordem: ordemNova.get(i.id), status: destino.col, feito: destino.col === "concluido" }
      : i));
    void executar(async () => {
      try {
        const salvos = await reordenarBacklog(destino.col, ids);
        setItens((atual) => (atual ?? []).map((i) => salvos.find((x) => x.id === i.id) ?? i));
      } catch (e) { setItens(snapshot); throw e; }
    });
  }

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
                onDragOver={(e) => { e.preventDefault(); if (arrastando && alvo?.col !== col.id) setAlvo({ col: col.id, indice: doStatus.length }); }}
                onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setAlvo(null); }}
                onDrop={(e) => { e.preventDefault(); soltar(); }}
                style={{
                  display: "flex", flexDirection: "column", gap: 10, minWidth: 0, minHeight: 140, padding: 16, borderRadius: 14,
                  background: "rgba(62,224,111,0.04)", transition: "border-color 0.15s",
                  border: `1px solid ${alvo?.col === col.id && arrastando ? col.color : "rgba(62,224,111,0.16)"}`,
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

                {doStatus.map((i, n) => (
                  <Fragment key={i.id}>
                  {arrastando && alvo?.col === col.id && alvo.indice === n && <LinhaDeEncaixe cor={col.color} />}
                  <article
                    draggable={aberto !== i.id}
                    onDragStart={() => setArrastando(i.id)}
                    onDragEnd={() => { setArrastando(null); setAlvo(null); }}
                    onDragOver={(e) => {
                      if (!arrastando) return;
                      e.preventDefault(); e.stopPropagation();
                      const r = e.currentTarget.getBoundingClientRect();
                      const indice = doStatus.indexOf(i) + (e.clientY > r.top + r.height / 2 ? 1 : 0);
                      if (alvo?.col !== col.id || alvo.indice !== indice) setAlvo({ col: col.id, indice });
                    }}
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
                        {i.status === "concluido" && <div><Chip tone="green">Feito</Chip></div>}
                      </>
                    )}
                  </article>
                  </Fragment>
                ))}
                {arrastando && alvo?.col === col.id && alvo.indice >= doStatus.length && doStatus.length > 0 && <LinhaDeEncaixe cor={col.color} />}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
