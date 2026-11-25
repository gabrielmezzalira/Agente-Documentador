"use client";

import type { CSSProperties, ReactNode } from "react";
import { cardStyle, ds } from "../../lib/ds";
import { nomeCurto } from "../../lib/nome";
import type { AcompanhamentoResponse, AcompMapaSprint, AcompProjetoStatus } from "../../lib/api";
import { num } from "./visual";

const mono: CSSProperties = { fontFamily: ds.fontMono, fontVariantNumeric: "tabular-nums" };
const legenda: CSSProperties = { fontSize: 12.5, lineHeight: 1.45, color: ds.muted };
const painel: CSSProperties = { ...cardStyle, boxShadow: "none", borderRadius: 14 };
const rotulo: CSSProperties = { fontFamily: ds.fontMono, fontSize: 11, letterSpacing: "0.14em", textTransform: "uppercase", color: ds.dim };

/** Variação contra a sprint anterior: subir é bom nos dois números em que aparece. */
function Variacao({ v, casas = 0 }: { v: number | null; casas?: number }) {
  if (v == null) return <>sem sprint anterior para comparar</>;
  if (Math.abs(v) < 0.5 * 10 ** -casas) return <>igual à sprint anterior</>;
  return (
    <span style={{ color: v > 0 ? ds.green : ds.red }}>
      {v > 0 ? "+" : "−"}{num(Math.abs(v), casas)} contra a sprint anterior
    </span>
  );
}

function Numero({ titulo, valor, children }: { titulo: string; valor: string | null; children: ReactNode }) {
  return (
    <div className="ind-numero">
      <span style={rotulo}>{titulo}</span>
      <span style={{ ...mono, fontSize: valor == null ? 15 : 30, fontWeight: 700, lineHeight: 1.1, color: valor == null ? ds.dim : ds.white }}>
        {valor ?? "sem dado ainda"}
      </span>
      <span style={legenda}>{children}</span>
    </div>
  );
}

function Icone({ feito }: { feito: boolean }) {
  return feito ? (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-label="entregue" role="img" style={{ flexShrink: 0 }}>
      <circle cx="7" cy="7" r="6.25" fill={ds.greenSoft} stroke={ds.green} strokeWidth="1.2" />
      <path d="M4.3 7.2 6.2 9l3.5-3.8" fill="none" stroke={ds.green} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ) : (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-label="em aberto" role="img" style={{ flexShrink: 0 }}>
      <circle cx="7" cy="7" r="6.25" fill="none" stroke={ds.dim} strokeWidth="1.2" strokeDasharray="2.4 2" />
    </svg>
  );
}

function MetaAtual({ projetos, onAbrir }: { projetos: AcompProjetoStatus[]; onAbrir: (id: string) => void }) {
  const comSprint = projetos.filter((p) => p.sprint_atual);
  const ordenados = [...comSprint].sort((a, b) => (a.meta_total > 0 ? 1 : 0) - (b.meta_total > 0 ? 1 : 0) || (a.nome ?? "").localeCompare(b.nome ?? ""));
  if (ordenados.length === 0) return <p style={{ margin: 0, padding: "20px 24px", ...legenda }}>Nenhum projeto com sprint iniciada.</p>;
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
      {ordenados.map((p) => {
        const pct = p.meta_total > 0 ? (p.meta_entregues / p.meta_total) * 100 : 0;
        return (
          <li key={p.id}>
            <button type="button" className="ind-linha" onClick={() => onAbrir(p.id)} aria-label={`Abrir ${p.nome ?? "projeto"}`}>
              <span style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
                <span style={{ fontSize: 14.5, fontWeight: 600, color: ds.white, overflowWrap: "anywhere" }}>{p.nome ?? "Projeto"}</span>
                <span style={legenda}>
                  Sprint {p.sprint_atual!.numero}{p.gerente && p.gerente !== "Sem gerente" ? ` · ${nomeCurto(p.gerente)}` : ""}
                </span>
              </span>
              {p.meta_total === 0 ? (
                <span style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  <span style={{ fontSize: 13.5, color: ds.amber }}>Meta não definida</span>
                  <span style={legenda}>Abra o projeto e use Definir meta</span>
                </span>
              ) : (
                <span style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                  <span style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ ...mono, fontSize: 14, fontWeight: 600, color: ds.white }}>{p.meta_entregues} de {p.meta_total}</span>
                    <span style={legenda}>entregues</span>
                  </span>
                  <span role="img" aria-label={`${p.meta_entregues} de ${p.meta_total} funcionalidades da meta entregues`} style={{ display: "flex", gap: 3 }}>
                    {Array.from({ length: p.meta_total }, (_, i) => (
                      <span key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: i < p.meta_entregues ? ds.green : "rgba(255, 255, 255, 0.08)" }} />
                    ))}
                  </span>
                  <span style={legenda}>{Math.round(pct)}% da meta</span>
                </span>
              )}
              <span className="ind-funcs">
                {p.meta_funcionalidades.map((f) => (
                  <span key={f.id} style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                    <Icone feito={f.aprovada} />
                    <span style={{ fontSize: 13, color: f.aprovada ? ds.muted : ds.text2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {f.id_funcional && <span style={{ ...mono, fontSize: 12, color: ds.dim, marginRight: 6 }}>{f.id_funcional}</span>}
                      {f.titulo ?? "(sem título)"}
                    </span>
                    {!f.aprovada && f.pct_tasks != null && <span style={{ ...mono, fontSize: 11.5, color: ds.dim, marginLeft: "auto", flexShrink: 0 }}>{Math.round(f.pct_tasks)}%</span>}
                  </span>
                ))}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

const COLUNAS = [-5, -4, -3, -2, -1, 0];

function Celula({ s }: { s: AcompMapaSprint | undefined }) {
  if (!s || s.numero == null) return <span className="ind-cel" style={{ color: ds.dim }}>·</span>;
  const titulo = `Sprint ${s.numero}${s.parcial ? " (em andamento)" : ""} · ${s.meta_total > 0 ? `meta ${s.meta_entregues}/${s.meta_total}` : "sem meta"} · SPI ${s.spi != null ? num(s.spi) : "sem dado"}`;
  if (s.meta_total === 0) {
    return <span className="ind-cel" title={titulo} style={{ color: ds.dim }}><small>S{s.numero}</small>sem meta</span>;
  }
  const estilo: CSSProperties = s.parcial
    ? { border: `1px dashed ${ds.borderStrong}`, color: ds.text2 }
    : s.meta_batida
      ? { background: ds.greenSoft, color: ds.green }
      : { background: ds.redSoft, color: ds.red };
  return (
    <span className="ind-cel" title={titulo} style={estilo}>
      <small style={{ color: s.parcial ? ds.muted : undefined, opacity: s.parcial ? 1 : 0.75 }}>S{s.numero}</small>
      <span style={{ ...mono, fontWeight: 600 }}>{s.meta_entregues}/{s.meta_total}</span>
    </span>
  );
}

function Historico({ mapa, onAbrir }: { mapa: AcompanhamentoResponse["mapa"]; onAbrir: (id: string) => void }) {
  const linhas = mapa.filter((m) => m.sprints.some((s) => s.numero != null));
  if (linhas.length === 0) return <p style={{ margin: 0, ...legenda }}>Nenhum projeto com sprint iniciada.</p>;
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="ind-tabela">
        <thead>
          <tr>
            <th scope="col" style={{ textAlign: "left" }}>Projeto</th>
            {COLUNAS.map((c) => <th key={c} scope="col">{c === 0 ? "Atual" : `Há ${Math.abs(c)}`}</th>)}
            <th scope="col">Batidas</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((m) => {
            const porRel = new Map(m.sprints.map((s) => [s.rel, s]));
            const fechadasComMeta = m.sprints.filter((s) => s.numero != null && !s.parcial && s.meta_total > 0);
            const batidas = fechadasComMeta.filter((s) => s.meta_batida).length;
            return (
              <tr key={m.projeto_id}>
                <td style={{ textAlign: "left" }}>
                  <button type="button" className="ind-link" onClick={() => onAbrir(m.projeto_id)}>{m.nome ?? "Projeto"}</button>
                </td>
                {COLUNAS.map((c) => <td key={c}><Celula s={porRel.get(c)} /></td>)}
                <td>
                  {fechadasComMeta.length === 0
                    ? <span style={{ ...mono, color: ds.dim }}>—</span>
                    : <span style={{ ...mono, color: ds.text2 }}>{batidas} de {fechadasComMeta.length}</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p style={{ margin: "14px 0 0", ...legenda, display: "flex", gap: 18, flexWrap: "wrap" }}>
        <span className="ind-chave"><i style={{ background: ds.greenSoft, borderColor: ds.greenLine }} />meta batida</span>
        <span className="ind-chave"><i style={{ background: ds.redSoft, borderColor: ds.redLine }} />meta não batida</span>
        <span className="ind-chave"><i style={{ borderStyle: "dashed", borderColor: ds.borderStrong }} />sprint em andamento</span>
        <span>Cada célula: funcionalidades da meta entregues / total. Passe o mouse para ver o SPI.</span>
      </p>
    </div>
  );
}

const CSS = `
.ind-numeros{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}
.ind-numero{display:flex;flex-direction:column;gap:8px;padding:22px 24px}
.ind-numero + .ind-numero{border-left:1px solid ${ds.border}}
.ind-linha{display:grid;grid-template-columns:minmax(200px,1.1fr) minmax(150px,.8fr) minmax(220px,1.6fr);gap:12px 32px;align-items:center;width:100%;
  text-align:left;background:none;border:none;border-top:1px solid ${ds.border};padding:16px 24px;cursor:pointer;font-family:inherit;color:${ds.text};transition:background .15s}
.ind-linha:hover{background:rgba(255,255,255,0.025)}
.ind-linha:focus-visible{outline:2px solid ${ds.green};outline-offset:-2px}
.ind-funcs{display:flex;flex-direction:column;gap:6px;min-width:0}
.ind-tabela{width:100%;border-collapse:collapse;font-size:13.5px}
.ind-tabela th{font-family:${ds.fontMono};font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:${ds.dim};font-weight:500;padding:0 6px 10px;white-space:nowrap}
.ind-tabela td{padding:6px;border-top:1px solid ${ds.border};text-align:center}
.ind-tabela th:first-child,.ind-tabela td:first-child{padding-left:0}
.ind-cel{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;min-width:64px;height:44px;border-radius:8px;font-size:13px}
.ind-cel small{font-family:${ds.fontMono};font-size:10.5px}
.ind-chave{display:inline-flex;align-items:center;gap:7px}
.ind-chave i{display:inline-block;width:12px;height:12px;border-radius:3px;border:1px solid transparent}
.ind-link{background:none;border:none;padding:0;cursor:pointer;font-family:inherit;font-size:13.5px;font-weight:600;color:${ds.white};text-align:left;white-space:nowrap}
.ind-link:hover{color:${ds.green}}
@media (max-width: 900px){
  .ind-numeros{grid-template-columns:repeat(2,minmax(0,1fr))}
  .ind-numero:nth-child(3){border-left:none}
  .ind-numero:nth-child(n+3){border-top:1px solid ${ds.border}}
  .ind-linha{grid-template-columns:1fr;padding:16px 20px}
}
`;

/** Aba Indicadores do acompanhamento: números da carteira, meta da sprint atual por projeto e histórico de metas. */
export default function Indicadores({ dados, projetos, onAbrir }: { dados: AcompanhamentoResponse; projetos: AcompProjetoStatus[]; onAbrir: (id: string) => void }) {
  const k = dados.kpis;
  return (
    <>
      <style>{CSS}</style>
      <section aria-label="Números da carteira" className="ind-numeros" style={painel}>
        <Numero titulo="Metas batidas" valor={k.metas_fechadas > 0 ? `${k.metas_batidas} de ${k.metas_fechadas}` : null}>
          {k.metas_fechadas > 0 ? "na última sprint fechada de cada projeto" : "nenhuma sprint fechada com meta"}
          {k.projetos_sem_meta > 0 && <><br /><span style={{ color: ds.amber }}>{k.projetos_sem_meta} {k.projetos_sem_meta === 1 ? "projeto" : "projetos"} sem meta na sprint atual</span></>}
        </Numero>
        <Numero titulo="SPI médio" valor={k.spi_medio != null ? num(k.spi_medio) : null}>
          {k.spi_medio != null ? <>das sprints fechadas · <Variacao v={k.spi_medio_var} casas={2} /></> : "nenhuma sprint fechada ainda"}
        </Numero>
        <Numero titulo="Funcionalidades entregues" valor={k.features_entregues != null ? String(k.features_entregues) : null}>
          {k.features_entregues != null ? <>aprovadas na sprint atual · <Variacao v={k.features_entregues_var} /></> : "sprints sem data de início"}
        </Numero>
        <Numero titulo="Tasks travadas" valor={String(k.tasks_travadas)}>
          {k.tasks_travadas > 0 ? <span style={{ color: ds.amber }}>paradas tempo demais no kanban</span> : "nenhuma agora"}
        </Numero>
      </section>

      <section aria-labelledby="ind-meta-atual" style={painel}>
        <div style={{ padding: "20px 24px 14px", display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <h2 id="ind-meta-atual" style={{ margin: 0, fontSize: 16, fontWeight: 600, color: ds.white }}>Meta da sprint atual</h2>
          <span style={legenda}>Sem meta primeiro · clique para abrir o projeto e definir</span>
        </div>
        <MetaAtual projetos={projetos} onAbrir={onAbrir} />
      </section>

      <section aria-labelledby="ind-historico" style={{ ...painel, padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <h2 id="ind-historico" style={{ margin: 0, fontSize: 16, fontWeight: 600, color: ds.white }}>Histórico de metas</h2>
          <span style={legenda}>Últimas 6 sprints de cada projeto</span>
        </div>
        <Historico mapa={dados.mapa} onAbrir={onAbrir} />
      </section>
    </>
  );
}

