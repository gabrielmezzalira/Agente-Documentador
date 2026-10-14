"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ds } from "../../lib/ds";
import {
  PRIORIDADE_LABEL, STATUS_LABEL, TIPO_LABEL, listRequisitos, nivelDoCargo, reconsolidarProjeto,
  type Requisito, type StatusRequisito,
} from "../../lib/discovery";
import { Button, Card, Chip, EmptyState, ErrorNotice, SectionLabel } from "../ds";
import RequisitoDetalhe from "./RequisitoDetalhe";
import { PRIORIDADE_TONE, STATUS_TONE } from "./requisitoTones";

const FILTROS: Array<{ id: StatusRequisito | "todos"; label: string }> = [
  { id: "todos", label: "Todos" },
  { id: "proposto", label: "Propostos" },
  { id: "em_revisao", label: "Em revisão" },
  { id: "validado", label: "Validados" },
  { id: "rejeitado", label: "Rejeitados" },
];

/** Aba "Requisitos": lista por status e detalhe expansível; reconsolidar é de gerente ou acima. */
export default function RequisitosTab({ projectId, cargo }: { projectId: string; cargo: string | undefined }) {
  const [reqs, setReqs] = useState<Requisito[] | null>(null);
  const [error, setError] = useState("");
  const [filtro, setFiltro] = useState<StatusRequisito | "todos">("todos");
  const [aberto, setAberto] = useState<string | null>(null);
  const [reconsolidando, setReconsolidando] = useState(false);
  const [aviso, setAviso] = useState("");

  const carregar = useCallback(() => {
    listRequisitos(projectId).then(setReqs).catch((e: Error) => setError(e.message));
  }, [projectId]);

  useEffect(() => { carregar(); }, [carregar]);

  const contagem = useMemo(() => {
    const c: Record<string, number> = { todos: reqs?.length ?? 0 };
    for (const r of reqs ?? []) c[r.status] = (c[r.status] ?? 0) + 1;
    return c;
  }, [reqs]);

  const visiveis = (reqs ?? []).filter((r) => filtro === "todos" || r.status === filtro);

  async function reconsolidar() {
    setReconsolidando(true);
    setAviso("");
    try {
      await reconsolidarProjeto(projectId);
      setAviso("Reconsolidação agendada. Atualize a lista em alguns instantes.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao reconsolidar");
    } finally {
      setReconsolidando(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 760 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
            <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color: ds.white }}>Requisitos</h2>
            <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{contagem.todos} requisitos</span>
          </div>
          <p style={{ fontSize: 14, lineHeight: 1.55, color: ds.muted, textWrap: "pretty" }}>
            Saem das reuniões do Agente Diagnóstico, cada um com o trecho que o sustenta. Nada é validado sozinho: a equipe revisa, valida e depois promove a funcionalidade.
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <Button onClick={carregar}>Atualizar</Button>
          {nivelDoCargo(cargo) >= 1 && <Button variant="primary" onClick={reconsolidar} disabled={reconsolidando}>{reconsolidando ? "Agendando…" : "Reconsolidar"}</Button>}
        </div>
      </div>

      {error && <ErrorNotice>{error}</ErrorNotice>}
      {aviso && <p role="status" style={{ fontSize: 13.5, color: ds.green }}>{aviso}</p>}

      <div role="tablist" aria-label="Filtrar por status" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {FILTROS.map((f) => (
          <Button key={f.id} role="tab" aria-selected={filtro === f.id} size="sm" variant={filtro === f.id ? "active" : "secondary"} onClick={() => setFiltro(f.id)}>
            {f.label} <span style={{ fontFamily: ds.fontMono, fontSize: 11 }}>{contagem[f.id] ?? 0}</span>
          </Button>
        ))}
      </div>

      {!reqs && !error && <p style={{ color: ds.muted }}>Carregando…</p>}
      {reqs && visiveis.length === 0 && (
        <EmptyState>{reqs.length === 0 ? "Nenhum requisito ainda. Eles aparecem depois que uma reunião de discovery é encerrada e analisada." : "Nenhum requisito neste status."}</EmptyState>
      )}

      {visiveis.map((r) => {
        const open = aberto === r.id;
        return (
          <Card key={r.id}>
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setAberto(open ? null : r.id)}
              className="ds-row-link"
              style={{ width: "100%", background: "none", border: "none", textAlign: "left", cursor: "pointer", color: "inherit", fontFamily: "inherit", display: "grid", gridTemplateColumns: "auto minmax(0, 1fr) auto auto", gap: 18, alignItems: "center", padding: "20px 28px", borderRadius: 16 }}
            >
              <span style={{ fontFamily: ds.fontMono, fontSize: 12.5, color: ds.green, fontWeight: 600 }}>{r.codigo}</span>
              <span style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
                <span style={{ fontSize: 16, fontWeight: 600, color: ds.white }}>{r.titulo}</span>
                <span style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Chip tone={STATUS_TONE[r.status]} dot>{STATUS_LABEL[r.status]}</Chip>
                  <Chip tone={PRIORIDADE_TONE[r.prioridade_sugerida]}>{PRIORIDADE_LABEL[r.prioridade_sugerida]}</Chip>
                  <Chip>{TIPO_LABEL[r.tipo]}</Chip>
                  {r.lente && <Chip tone="violet">{r.lente === "produto" ? "Produto" : "Dados"}</Chip>}
                  {r.conflito && <Chip tone="red">Conflito</Chip>}
                  {r.possivel_duplicata_de && <Chip tone="amber">Possível duplicata</Chip>}
                </span>
              </span>
              <SectionLabel>{r.n_evidencias} {r.n_evidencias === 1 ? "evidência" : "evidências"}</SectionLabel>
              <span aria-hidden="true" style={{ color: ds.muted }}>{open ? "▴" : "▾"}</span>
            </button>
            {open && <RequisitoDetalhe requisitoId={r.id} cargo={cargo} onChanged={carregar} />}
          </Card>
        );
      })}
    </div>
  );
}
