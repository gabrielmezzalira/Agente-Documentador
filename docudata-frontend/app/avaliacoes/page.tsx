"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "../components/AuthGuard";
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

  if (bloqueado) {
    return (
      <main style={pageStyle}>
        <Link href="/" style={linkVoltarStyle}>← Projetos</Link>
        <p style={{ color: "#dc2626", marginTop: 20 }}>Acesso restrito a Gerente, Líder e Owner.</p>
      </main>
    );
  }

  return (
    <main style={pageStyle}>
      <Link href="/" style={linkVoltarStyle}>← Projetos</Link>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#111116", margin: "20px 0 8px" }}>Avaliações do gerente</h1>
      <p style={{ color: "#737380", fontSize: 14, marginBottom: 24 }}>
        Notas da avaliação semanal por operacional e sprint. Corrigir uma nota atualiza o ranking.
      </p>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 24 }}>
        <label style={filtroLabelStyle}>
          Projeto
          <select
            value={projetoId}
            onChange={(e) => { setProjetoId(e.target.value); setSprintId(""); }}
            style={selectStyle}
          >
            <option value="">Todos</option>
            {projetos.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
          </select>
        </label>
        <label style={filtroLabelStyle}>
          Sprint
          <select
            value={sprintId}
            onChange={(e) => setSprintId(e.target.value)}
            disabled={!projetoId}
            style={selectStyle}
          >
            <option value="">Todas</option>
            {sprintsDoProjeto.map(([id, numero]) => <option key={id} value={id}>Sprint {numero ?? "—"}</option>)}
          </select>
        </label>
      </div>

      {erro && <p role="alert" style={{ color: "#dc2626" }}>{erro}</p>}
      {!itens && !erro && <p style={{ color: "#6b6b76" }}>Carregando...</p>}
      {itens && filtrados.length === 0 && (
        <p style={{ color: "#6b6b76" }}>Nenhuma avaliação registrada{projetoId ? " para este filtro" : " ainda"}.</p>
      )}

      {grupos.map((g) => (
        <section key={g.chave} style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 16, fontWeight: 800, color: "#111116", margin: "0 0 10px" }}>
            {g.projeto} <span style={{ color: "#6b6b76", fontWeight: 600 }}>· Sprint {g.sprint ?? "—"}</span>
          </h2>
          <div style={{ overflowX: "auto", background: "#fff", border: "1px solid #e8e8ed", borderRadius: 12 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={thStyle}>Operacional</th>
                  <th style={thStyle}>Avaliador</th>
                  {perguntas(g.linhas[0].modo_trabalho).map((texto, idx) => (
                    <th key={idx} style={{ ...thStyle, textAlign: "center" }} title={texto}>P{idx + 1}</th>
                  ))}
                  <th style={{ ...thStyle, textAlign: "center" }}>Média</th>
                  <th style={thStyle}><span style={srOnly}>Ações</span></th>
                </tr>
              </thead>
              <tbody>
                {g.linhas.map((a) => (
                  <tr key={a.id} style={{ borderTop: "1px solid #f1f1f4" }}>
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 650, color: "#111116" }}>{a.operacional_nome}</span>
                      {a.total_edicoes > 0 && a.ultima_edicao_em && (
                        <span style={badgeEditadaStyle}>
                          editada por {a.ultima_edicao_por} em {formatData(a.ultima_edicao_em)}
                        </span>
                      )}
                    </td>
                    <td style={{ ...tdStyle, color: "#737380" }}>{a.avaliador_nome}</td>
                    {CAMPOS_RESPOSTA.map((c) => (
                      <td key={c} style={{ ...tdStyle, textAlign: "center", fontVariantNumeric: "tabular-nums" }}>{a[c]}</td>
                    ))}
                    <td style={{ ...tdStyle, textAlign: "center", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
                      {mediaGerente100(notasDe(a))}
                    </td>
                    <td style={{ ...tdStyle, whiteSpace: "nowrap", textAlign: "right" }}>
                      <button type="button" onClick={() => setEditando(a)} style={btnLinkStyle}>Editar</button>
                      {a.total_edicoes > 0 && (
                        <button type="button" onClick={() => setVendoHistorico(a)} style={btnLinkStyle}>
                          Histórico ({a.total_edicoes})
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      {editando && <EditarModal avaliacao={editando} onClose={() => setEditando(null)} onSalvo={onSalvo} />}
      {vendoHistorico && <HistoricoModal avaliacao={vendoHistorico} onClose={() => setVendoHistorico(null)} />}
    </main>
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
    <Overlay onClose={onClose} titulo={`Corrigir nota · ${avaliacao.operacional_nome}`}>
      <p style={{ fontSize: 13, color: "#737380", margin: "0 0 16px" }}>
        {avaliacao.projeto_nome} · Sprint {avaliacao.sprint_numero ?? "—"} · avaliado por {avaliacao.avaliador_nome}
      </p>
      {perguntas(avaliacao.modo_trabalho).map((texto, idx) => {
        const campo = CAMPOS_RESPOSTA[idx];
        return (
          <fieldset key={campo} style={{ border: "none", padding: 0, margin: "0 0 14px" }}>
            <legend style={{ fontSize: 13, color: "#111116", fontWeight: 600, marginBottom: 6 }}>
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
                    onClick={() => setNotas((prev) => ({ ...prev, [campo]: n }))}
                    style={{
                      width: 36, height: 36, borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: "pointer",
                      border: ativo ? "2px solid #16a34a" : "1px solid #e8e8ed",
                      background: ativo ? "#f0fdf4" : "#fff",
                      color: "#111116",
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
      <label htmlFor="motivo-correcao" style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#374151", margin: "8px 0 4px" }}>
        Motivo da correção
      </label>
      <textarea
        id="motivo-correcao"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
        rows={3}
        placeholder="Ex.: nota lançada errada, conversei com o gerente"
        style={{ width: "100%", boxSizing: "border-box", border: "1px solid #e8e8ed", borderRadius: 8, padding: 10, fontSize: 13, resize: "vertical" }}
      />
      {erro && <p role="alert" style={{ color: "#dc2626", fontSize: 13, marginTop: 8 }}>{erro}</p>}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
        <button type="button" onClick={onClose} style={btnGhostStyle}>Cancelar</button>
        <button type="button" onClick={salvar} disabled={!podeSalvar} style={{ ...btnPrimaryStyle, opacity: podeSalvar ? 1 : 0.5 }}>
          {salvando ? "Salvando…" : "Salvar correção"}
        </button>
      </div>
    </Overlay>
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
    <Overlay onClose={onClose} titulo={`Histórico · ${avaliacao.operacional_nome}`}>
      {erro && <p role="alert" style={{ color: "#dc2626" }}>{erro}</p>}
      {!edicoes && !erro && <p style={{ color: "#6b6b76" }}>Carregando...</p>}
      {edicoes?.map((e) => (
        <div key={e.id} style={{ borderTop: "1px solid #f1f1f4", padding: "12px 0" }}>
          <p style={{ fontSize: 12, color: "#737380", margin: "0 0 6px" }}>
            {e.editor_nome} · {formatData(e.criado_em)}
          </p>
          <ul style={{ margin: "0 0 6px", paddingLeft: 18, fontSize: 13, color: "#111116" }}>
            {CAMPOS_RESPOSTA.map((c, idx) =>
              e.antes[c] !== e.depois[c] ? (
                <li key={c} title={textos[idx]}>P{idx + 1}: {e.antes[c] ?? "—"} → {e.depois[c] ?? "—"}</li>
              ) : null
            )}
          </ul>
          <p style={{ fontSize: 13, color: "#374151", margin: 0 }}>“{e.motivo}”</p>
        </div>
      ))}
    </Overlay>
  );
}

function Overlay({ titulo, onClose, children }: { titulo: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}
    >
      <div role="dialog" aria-modal="true" aria-label={titulo} style={{ background: "#fff", borderRadius: 16, padding: "24px 28px", width: "100%", maxWidth: 520, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.18)" }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: "#0f172a", margin: "0 0 12px" }}>{titulo}</h3>
        {children}
      </div>
    </div>
  );
}

const pageStyle: React.CSSProperties = { maxWidth: 1000, margin: "0 auto", padding: "52px 24px" };
const linkVoltarStyle: React.CSSProperties = { fontSize: 13, color: "#6b6b76" };
const filtroLabelStyle: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 4, fontSize: 11, fontWeight: 700, color: "#737380", textTransform: "uppercase", letterSpacing: "0.06em" };
const selectStyle: React.CSSProperties = { minWidth: 200, padding: "8px 10px", border: "1px solid #e8e8ed", borderRadius: 8, fontSize: 13, background: "#fff", color: "#111116", textTransform: "none", letterSpacing: 0, fontWeight: 500 };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "10px 12px", fontSize: 11, fontWeight: 700, color: "#737380", textTransform: "uppercase", letterSpacing: "0.06em", cursor: "default" };
const tdStyle: React.CSSProperties = { padding: "10px 12px", verticalAlign: "top" };
const badgeEditadaStyle: React.CSSProperties = { display: "block", marginTop: 4, fontSize: 11, color: "#b45309" };
const btnLinkStyle: React.CSSProperties = { background: "none", border: "none", color: "#16a34a", fontSize: 13, fontWeight: 650, cursor: "pointer", padding: "4px 6px" };
const btnGhostStyle: React.CSSProperties = { background: "#fff", border: "1px solid #e8e8ed", borderRadius: 8, padding: "8px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer", color: "#374151" };
const btnPrimaryStyle: React.CSSProperties = { background: "#111116", border: "none", borderRadius: 8, padding: "8px 14px", fontSize: 13, fontWeight: 700, cursor: "pointer", color: "#fff" };
const srOnly: React.CSSProperties = { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" };
