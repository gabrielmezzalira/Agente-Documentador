"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { Button, Card, Chip, EmptyState, ErrorNotice, Input, PageHeader, SegmentedControl, Select, Textarea } from "../components/ds";
import { ds } from "../lib/ds";
import type { Tone } from "../lib/ds";
import {
  createBacklogItem, deleteBacklogItem, listBacklog, updateBacklogItem,
  type BacklogItem, type BacklogPrioridade,
} from "../lib/api";

const PRIORIDADES: { valor: BacklogPrioridade; label: string; tom: Tone; peso: number }[] = [
  { valor: "alta", label: "Alta", tom: "red", peso: 0 },
  { valor: "media", label: "Média", tom: "amber", peso: 1 },
  { valor: "baixa", label: "Baixa", tom: "neutral", peso: 2 },
];
const prioridadeDe = (v: BacklogPrioridade) => PRIORIDADES.find((p) => p.valor === v)!;

type Filtro = "pendentes" | "feitos" | "todos";

export default function BacklogPage() {
  const auth = useAuth();
  const ehOwner = auth?.cargo === "owner";
  const [itens, setItens] = useState<BacklogItem[] | null>(null);
  const [erro, setErro] = useState("");
  const [filtro, setFiltro] = useState<Filtro>("pendentes");
  const [titulo, setTitulo] = useState("");
  const [notas, setNotas] = useState("");
  const [prioridade, setPrioridade] = useState<BacklogPrioridade>("media");
  const [salvando, setSalvando] = useState(false);
  const [editando, setEditando] = useState<string | null>(null);
  const [rascunho, setRascunho] = useState("");

  useEffect(() => {
    if (!ehOwner) return;
    listBacklog().then(setItens).catch((e: Error) => setErro(e.message));
  }, [ehOwner]);

  const visiveis = useMemo(() => {
    const base = (itens ?? []).filter((i) => (filtro === "todos" ? true : filtro === "feitos" ? i.feito : !i.feito));
    return [...base].sort((a, b) =>
      Number(a.feito) - Number(b.feito) ||
      prioridadeDe(a.prioridade).peso - prioridadeDe(b.prioridade).peso ||
      b.criado_em.localeCompare(a.criado_em));
  }, [itens, filtro]);

  const pendentes = (itens ?? []).filter((i) => !i.feito).length;

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

  const alternar = (i: BacklogItem) => executar(async () => trocar(await updateBacklogItem(i.id, { feito: !i.feito })));
  const mudarPrioridade = (i: BacklogItem, p: BacklogPrioridade) => executar(async () => trocar(await updateBacklogItem(i.id, { prioridade: p })));
  const apagar = (i: BacklogItem) => {
    if (!confirm(`Apagar "${i.titulo}"?`)) return Promise.resolve();
    return executar(async () => {
      await deleteBacklogItem(i.id);
      setItens((atual) => (atual ?? []).filter((x) => x.id !== i.id));
    });
  };
  async function salvarTitulo(i: BacklogItem) {
    const novo = rascunho.trim();
    setEditando(null);
    if (!novo || novo === i.titulo) return;
    await executar(async () => trocar(await updateBacklogItem(i.id, { titulo: novo })));
  }

  if (auth && !ehOwner) return <ErrorNotice>Esta página é só do Owner.</ErrorNotice>;

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

      <SegmentedControl
        label="Filtro"
        value={filtro}
        onChange={setFiltro}
        options={[{ value: "pendentes", label: `Pendentes${itens ? ` (${pendentes})` : ""}` }, { value: "feitos", label: "Feitos" }, { value: "todos", label: "Todos" }]}
      />

      {!itens && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
      {itens && visiveis.length === 0 && <EmptyState>{filtro === "pendentes" ? "Nada pendente. Adicione algo acima." : "Nada por aqui."}</EmptyState>}

      {visiveis.length > 0 && (
        <Card>
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {visiveis.map((i, idx) => (
              <li key={i.id} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "14px 18px", borderTop: idx > 0 ? `1px solid ${ds.border}` : "none" }}>
                <input type="checkbox" checked={i.feito} onChange={() => void alternar(i)} aria-label={`Marcar "${i.titulo}" como ${i.feito ? "pendente" : "feito"}`} style={{ marginTop: 4, width: 18, height: 18, accentColor: ds.green, cursor: "pointer" }} />
                <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 4 }}>
                  {editando === i.id ? (
                    <Input
                      autoFocus value={rascunho} maxLength={200} aria-label="Editar título"
                      onChange={(e) => setRascunho(e.target.value)} onBlur={() => void salvarTitulo(i)}
                      onKeyDown={(e) => { if (e.key === "Enter") void salvarTitulo(i); if (e.key === "Escape") setEditando(null); }}
                    />
                  ) : (
                    <button
                      type="button" onClick={() => { setEditando(i.id); setRascunho(i.titulo); }} title="Clique para editar"
                      style={{ background: "none", border: "none", padding: 0, textAlign: "left", cursor: "text", fontFamily: "inherit", fontSize: 15, fontWeight: 600, color: i.feito ? ds.muted : ds.white, textDecoration: i.feito ? "line-through" : "none", overflowWrap: "anywhere" }}
                    >
                      {i.titulo}
                    </button>
                  )}
                  {i.notas && <span style={{ fontSize: 13, lineHeight: 1.5, color: ds.muted, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{i.notas}</span>}
                </div>
                {i.feito
                  ? <Chip tone="green">Feito</Chip>
                  : (
                    <Select aria-label={`Prioridade de ${i.titulo}`} value={i.prioridade} onChange={(e) => void mudarPrioridade(i, e.target.value as BacklogPrioridade)} style={{ width: 110, height: 32, fontSize: 12.5 }}>
                      {PRIORIDADES.map((p) => <option key={p.valor} value={p.valor}>{p.label}</option>)}
                    </Select>
                  )}
                <button type="button" onClick={() => void apagar(i)} aria-label={`Apagar "${i.titulo}"`} title="Apagar" style={{ background: "none", border: "none", cursor: "pointer", color: ds.red, fontSize: 18, lineHeight: 1, padding: "2px 4px" }}>×</button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
