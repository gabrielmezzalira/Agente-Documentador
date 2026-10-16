"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { Button, Card, EmptyState, ErrorNotice, Field, Modal, PageHeader, Select, Textarea } from "../components/ds";
import { ds, labelStyle } from "../lib/ds";
import {
  editarAvaliacao,
  getEdicoesAvaliacao,
  getHistoricoAvaliacoes,
  type AvaliacaoEdicaoItem,
  type AvaliacaoHistoricoItem,
} from "../lib/api";
import { CAMPOS_RESPOSTA, mediaGerente100, perguntas, type CampoResposta } from "../lib/perguntasAvaliacao";

type Notas = Record<CampoResposta, number>;

function notasDe(a: AvaliacaoHistoricoItem): Notas {
  return {
    resposta_1: a.resposta_1,
    resposta_2: a.resposta_2,
    resposta_3: a.resposta_3,
    resposta_4: a.resposta_4,
    resposta_5: a.resposta_5,
    resposta_7: a.resposta_7,
  };
}

function formatData(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function AvaliacoesPage() {
  const auth = useAuth();
  const [itens, setItens] = useState<AvaliacaoHistoricoItem[] | null>(null);
  const [erro, setErro] = useState("");
  const [projetoId, setProjetoId] = useState("");
  const [sprintId, setSprintId] = useState("");
  const [editando, setEditando] = useState<AvaliacaoHistoricoItem | null>(null);
  const [vendoHistorico, setVendoHistorico] = useState<AvaliacaoHistoricoItem | null>(null);

  const bloqueado = auth?.cargo === "operacional";

  useEffect(() => {
    if (!auth || bloqueado) return;
    getHistoricoAvaliacoes()
      .then(setItens)
      .catch((e: Error) => setErro(e.message));
  }, [auth, bloqueado]);

  const projetos = useMemo(() => {
    const m = new Map<string, string>();
    (itens ?? []).forEach((i) => i.projeto_id && m.set(i.projeto_id, i.projeto_nome));
    return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [itens]);

  const sprintsDoProjeto = useMemo(() => {
    const m = new Map<string, number | null>();
    (itens ?? []).filter((i) => i.projeto_id === projetoId).forEach((i) => m.set(i.sprint_id, i.sprint_numero));
    return [...m.entries()].sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0));
  }, [itens, projetoId]);

  const filtrados = (itens ?? []).filter(
    (i) => (!projetoId || i.projeto_id === projetoId) && (!sprintId || i.sprint_id === sprintId)
  );

  // Agrupa projeto → sprint mantendo a ordem do backend (projeto, sprint desc, operacional).
  const grupos: { chave: string; projeto: string; sprint: number | null; linhas: AvaliacaoHistoricoItem[] }[] = [];
  filtrados.forEach((i) => {
    const chave = `${i.projeto_id}:${i.sprint_id}`;
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.chave === chave) ultimo.linhas.push(i);
    else grupos.push({ chave, projeto: i.projeto_nome, sprint: i.sprint_numero, linhas: [i] });
  });

  function onSalvo(atualizada: AvaliacaoHistoricoItem) {
    setItens((prev) => (prev ?? []).map((i) => (i.id === atualizada.id ? atualizada : i)));
    setEditando(null);
  }

  if (bloqueado) return <ErrorNotice>Acesso restrito a Gerente, Líder e Owner.</ErrorNotice>;

  return (
    <>
      <PageHeader title="Avaliações do gerente" subtitle="Notas da avaliação semanal por operacional e sprint. Corrigir uma nota atualiza o ranking." />

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
        <Field label="Projeto" htmlFor="filtro-projeto">
          <Select id="filtro-projeto" value={projetoId} onChange={(e) => { setProjetoId(e.target.value); setSprintId(""); }} style={{ width: 320, height: 40, fontSize: 13.5 }}>
            <option value="">Todos</option>
            {projetos.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
          </Select>
        </Field>
        <Field label="Sprint" htmlFor="filtro-sprint">
          <Select id="filtro-sprint" value={sprintId} onChange={(e) => setSprintId(e.target.value)} disabled={!projetoId} style={{ width: 220, height: 40, fontSize: 13.5 }}>
            <option value="">Todas</option>
            {sprintsDoProjeto.map(([id, numero]) => <option key={id} value={id}>Sprint {numero ?? "—"}</option>)}
          </Select>
        </Field>
      </div>

      {erro && <ErrorNotice>{erro}</ErrorNotice>}
      {!itens && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
      {itens && filtrados.length === 0 && (
        <EmptyState>Nenhuma avaliação registrada{projetoId ? " para este filtro" : " ainda"}.</EmptyState>
      )}

      {grupos.map((g) => {
        const textos = perguntas(g.linhas[0].modo_trabalho);
        const colunas = `minmax(0,1.6fr) minmax(0,1.3fr) repeat(${textos.length}, 48px) 80px 150px`;
        return (
          <section key={g.chave} aria-label={`${g.projeto} · Sprint ${g.sprint ?? "—"}`} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <h2 style={{ margin: 0, fontSize: 19, fontWeight: 700, letterSpacing: "-0.02em", color: ds.white }}>{g.projeto}</h2>
              <span style={{ fontSize: 15, color: ds.muted }}>· Sprint {g.sprint ?? "—"}</span>
            </div>
            <Card style={{ overflowX: "auto" }}>
              <div role="table" style={{ display: "flex", flexDirection: "column", minWidth: 760 }}>
                <div role="row" style={{ display: "grid", gridTemplateColumns: colunas, gap: 12, padding: "10px 16px", borderBottom: `1px solid ${ds.border}` }}>
                  <span role="columnheader" style={labelStyle}>Operacional</span>
                  <span role="columnheader" style={labelStyle}>Avaliador</span>
                  {textos.map((texto, idx) => <span key={idx} role="columnheader" title={texto} style={{ ...labelStyle, cursor: "help" }}>P{idx + 1}</span>)}
                  <span role="columnheader" style={labelStyle}>Média</span>
                  <span role="columnheader" style={srOnly}>Ações</span>
                </div>
                {g.linhas.map((a, i) => (
                  <div key={a.id} role="row" style={{ display: "grid", gridTemplateColumns: colunas, gap: 12, alignItems: "center", padding: "14px 16px", borderTop: i > 0 ? `1px solid ${ds.border}` : "none", fontSize: 14, color: ds.text2 }}>
                    <span role="cell" style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
                      <span style={{ color: ds.white, fontWeight: 600 }}>{a.operacional_nome}</span>
                      {a.total_edicoes > 0 && a.ultima_edicao_em && (
                        <span style={{ fontSize: 11.5, color: ds.amber }}>editada por {a.ultima_edicao_por} em {formatData(a.ultima_edicao_em)}</span>
                      )}
                    </span>
                    <span role="cell">{a.avaliador_nome}</span>
                    {CAMPOS_RESPOSTA.map((c, idx) => <span key={c} role="cell"><NotaCelula valor={a[c]} pergunta={textos[idx]} /></span>)}
                    <span role="cell" style={{ fontFamily: ds.fontMono, fontSize: 15, fontWeight: 700, color: ds.white }}>{mediaGerente100(notasDe(a))}</span>
                    <span role="cell" style={{ display: "flex", gap: 10, justifyContent: "flex-end", whiteSpace: "nowrap" }}>
                      <button type="button" onClick={() => setEditando(a)} style={btnLinkStyle}>Editar</button>
                      {a.total_edicoes > 0 && (
                        <button type="button" onClick={() => setVendoHistorico(a)} style={{ ...btnLinkStyle, color: ds.text2 }}>Histórico ({a.total_edicoes})</button>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          </section>
        );
      })}

      {editando && <EditarModal avaliacao={editando} onClose={() => setEditando(null)} onSalvo={onSalvo} />}
      {vendoHistorico && <HistoricoModal avaliacao={vendoHistorico} onClose={() => setVendoHistorico(null)} />}
    </>
  );
}

/** Nota 0–5 numa célula de calor: quanto maior, mais verde (protótipo 11). Zero fica apagado. */
function NotaCelula({ valor, pergunta }: { valor: number | null | undefined; pergunta?: string }) {
  const v = valor ?? 0;
  return (
    <span
      title={pergunta ? `${pergunta}: ${valor ?? "—"}` : undefined}
      style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center", width: 30, height: 30, borderRadius: 8,
        fontFamily: ds.fontMono, fontSize: 13, fontWeight: 600,
        background: v > 0 ? `rgba(62,224,111,${(0.055 * v).toFixed(3)})` : "rgba(255,255,255,0.03)",
        color: v > 0 ? ds.white : ds.dim,
      }}
    >
      {valor ?? "—"}
    </span>
  );
}

function EditarModal({
  avaliacao, onClose, onSalvo,
}: {
  avaliacao: AvaliacaoHistoricoItem;
  onClose: () => void;
  onSalvo: (a: AvaliacaoHistoricoItem) => void;
}) {
  const originais = notasDe(avaliacao);
  const [notas, setNotas] = useState<Notas>(originais);
  const [motivo, setMotivo] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  const mudou = CAMPOS_RESPOSTA.some((c) => notas[c] !== originais[c]);
  const podeSalvar = mudou && motivo.trim().length > 0 && !salvando;

  async function salvar() {
    setSalvando(true);
    setErro("");
    try {
      onSalvo(await editarAvaliacao(avaliacao.id, { ...notas, motivo: motivo.trim() }));
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal
      title={`Corrigir nota · ${avaliacao.operacional_nome}`}
      onClose={onClose}
      width={560}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={salvar} disabled={!podeSalvar}>{salvando ? "Salvando…" : "Salvar correção"}</Button>
        </>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <p style={{ margin: 0, fontSize: 13, color: ds.muted }}>
          {avaliacao.projeto_nome} · Sprint {avaliacao.sprint_numero ?? "—"} · avaliado por {avaliacao.avaliador_nome}
        </p>
        {perguntas(avaliacao.modo_trabalho).map((texto, idx) => {
          const campo = CAMPOS_RESPOSTA[idx];
          return (
            <fieldset key={campo} style={{ border: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              <legend style={{ fontSize: 13.5, color: ds.text, fontWeight: 600, marginBottom: 8, padding: 0 }}>
                {idx + 1}. {texto}
              </legend>
              <div style={{ display: "flex", gap: 6 }}>
                {[0, 1, 2, 3, 4, 5].map((n) => {
                  const ativo = notas[campo] === n;
                  return (
                    <button
                      key={n}
                      type="button"
                      aria-pressed={ativo}
                      aria-label={`Nota ${n}`}
                      onClick={() => setNotas((prev) => ({ ...prev, [campo]: n }))}
                      style={{
                        width: 36, height: 36, borderRadius: 8, fontFamily: ds.fontMono, fontSize: 14, fontWeight: 600, cursor: "pointer",
                        border: `1px solid ${ativo ? ds.green : ds.innerBorder}`,
                        background: ativo ? ds.greenSoft : ds.inner,
                        color: ativo ? ds.green : ds.text2,
                      }}
                    >
                      {n}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          );
        })}
        <Field label="Motivo da correção" htmlFor="motivo-correcao" required error={erro || null}>
          <Textarea
            id="motivo-correcao"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            rows={3}
            placeholder="Ex.: nota lançada errada, conversei com o gerente"
          />
        </Field>
      </div>
    </Modal>
  );
}

function HistoricoModal({ avaliacao, onClose }: { avaliacao: AvaliacaoHistoricoItem; onClose: () => void }) {
  const [edicoes, setEdicoes] = useState<AvaliacaoEdicaoItem[] | null>(null);
  const [erro, setErro] = useState("");
  const textos = perguntas(avaliacao.modo_trabalho);

  useEffect(() => {
    getEdicoesAvaliacao(avaliacao.id).then(setEdicoes).catch((e: Error) => setErro(e.message));
  }, [avaliacao.id]);

  return (
    <Modal title={`Histórico · ${avaliacao.operacional_nome}`} onClose={onClose} width={560}>
      {erro && <ErrorNotice>{erro}</ErrorNotice>}
      {!edicoes && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
      {edicoes?.map((e, i) => (
        <div key={e.id} style={{ borderTop: i > 0 ? `1px solid ${ds.border}` : "none", padding: "12px 0" }}>
          <p style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted, margin: "0 0 6px" }}>
            {e.editor_nome} · {formatData(e.criado_em)}
          </p>
          <ul style={{ margin: "0 0 6px", paddingLeft: 18, fontSize: 13, color: ds.text }}>
            {CAMPOS_RESPOSTA.map((c, idx) =>
              e.antes[c] !== e.depois[c] ? (
                <li key={c} title={textos[idx]}>P{idx + 1}: {e.antes[c] ?? "—"} → {e.depois[c] ?? "—"}</li>
              ) : null
            )}
          </ul>
          <p style={{ fontSize: 13, color: ds.text2, margin: 0 }}>“{e.motivo}”</p>
        </div>
      ))}
    </Modal>
  );
}

const btnLinkStyle: React.CSSProperties = { background: "none", border: "none", color: "#3ee06f", fontSize: 13.5, fontWeight: 600, cursor: "pointer", padding: 0, fontFamily: "inherit" };
const srOnly: React.CSSProperties = { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" };
