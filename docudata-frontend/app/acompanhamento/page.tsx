"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { useAuth } from "../components/AuthGuard";
import ProjetoDetalhePainel from "../components/acompanhamento/ProjetoDetalhePainel";
import {
  COR_STATUS, ORDEM_STATUS, PENDENCIAS, STATUS_INFO, TOM_STATUS, corDoSpi, num, pendencia, pts,
} from "../components/acompanhamento/visual";
import { Card, Chip, EmptyState, ErrorNotice, PageHeader, ProgressBar, SegmentedControl, Select, StatusDot } from "../components/ds";
import { ds, labelStyle, toneColors } from "../lib/ds";
import { nomeCurto } from "../lib/nome";
import {
  getAcompanhamento, type AcompanhamentoResponse, type AcompGerente, type AcompProjetoStatus, type AcompStatus, type Subarea,
} from "../lib/api";

const SUBAREAS: { value: Subarea; label: string }[] = [
  { value: "dados", label: "Dados" },
  { value: "dev", label: "Dev" },
  { value: "pta", label: "PTA" },
];

const STATUS_ORDEM: AcompStatus[] = ["critico", "atencao", "sem_dados", "saudavel"];

const mono: CSSProperties = { fontFamily: ds.fontMono };
const apagado: CSSProperties = { fontSize: 12.5, color: ds.muted };

function plural(n: number, um: string, varios: string): string {
  return `${n} ${n === 1 ? um : varios}`;
}

// ── resumo da carteira ──

function FiltroStatus({ status, qtd, ativo, onClick }: { status: AcompStatus; qtd: number; ativo: boolean; onClick: () => void }) {
  const tom = toneColors[TOM_STATUS[status]];
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      title={STATUS_INFO[status].regra}
      style={{
        display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-start", textAlign: "left",
        padding: "14px 16px", borderRadius: 12, cursor: "pointer", fontFamily: "inherit",
        background: ativo ? tom.bg : "rgba(255, 255, 255, 0.02)",
        border: `1px solid ${ativo ? tom.line : ds.border}`,
        opacity: qtd === 0 && !ativo ? 0.55 : 1,
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 600, color: ativo ? tom.fg : ds.text2 }}>
        <StatusDot tone={TOM_STATUS[status]} />
        {STATUS_INFO[status].nome}
      </span>
      <span style={{ ...mono, fontSize: 28, fontWeight: 700, lineHeight: 1, color: qtd > 0 ? COR_STATUS[status] : ds.dim }}>{qtd}</span>
    </button>
  );
}

// ── linha do projeto ──

function BarraSprint({ p }: { p: AcompProjetoStatus }) {
  const pr = p.progresso;
  if (!p.sprint_atual) return <span style={apagado}>Nenhuma sprint iniciada</span>;
  if (!pr || pr.tasks_total === 0) return <span style={apagado}>Sprint {p.sprint_atual.numero} sem tasks</span>;
  const pct = pr.pct ?? 0;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
        <span style={{ fontSize: 12.5, color: ds.text2 }}>
          Sprint {p.sprint_atual.numero}
          {p.sprint_atual.fechada && <span style={{ color: ds.muted }}> · fechada</span>}
        </span>
        <span style={{ ...mono, fontSize: 13, fontWeight: 700, color: ds.white }}>{pr.pct != null ? `${Math.round(pct)}%` : "—"}</span>
      </div>
      <ProgressBar pct={pct} label={`Progresso da sprint ${p.sprint_atual.numero} de ${p.nome ?? "projeto"}`} />
      <span style={apagado}>
        {pts(pr.pts_concluidos)} de {pts(pr.pts_previstos)} pts · {pr.tasks_concluidas}/{pr.tasks_total} tasks
        {pr.tasks_aguardando > 0 && <> · {pr.tasks_aguardando} aguardando aprovação</>}
      </span>
    </div>
  );
}

function PrazoEscopo({ p }: { p: AcompProjetoStatus }) {
  if (p.pct_prazo == null || p.pct_escopo == null) {
    return <span style={apagado}>{p.sinais.some((s) => s.codigo === "sem_funcionalidades") ? "Escopo vazio" : "Sem datas do contrato"}</span>;
  }
  const prazo = Math.max(0, Math.min(100, p.pct_prazo));
  const escopo = Math.max(0, Math.min(100, p.pct_escopo));
  const atrasado = prazo > escopo;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
        <span style={{ fontSize: 12.5, color: ds.text2 }}>Projeto</span>
        <span style={{ ...mono, fontSize: 13, fontWeight: 700, color: ds.white }}>{Math.round(escopo)}%</span>
      </div>
      <div
        role="img"
        aria-label={`${Math.round(escopo)}% do escopo aprovado com ${Math.round(prazo)}% do prazo consumido`}
        style={{ position: "relative", height: 6, borderRadius: 3, background: "rgba(255, 255, 255, 0.08)" }}
      >
        <div style={{ width: `${escopo}%`, height: "100%", borderRadius: 3, background: ds.violet }} />
        <span title={`${Math.round(prazo)}% do prazo`} style={{ position: "absolute", top: -3, left: `calc(${prazo}% - 1px)`, width: 2, height: 12, borderRadius: 1, background: atrasado ? ds.amber : ds.text2 }} />
      </div>
      <span style={apagado}>{Math.round(escopo)}% do escopo · {Math.round(prazo)}% do prazo</span>
    </div>
  );
}

function Tendencia({ p }: { p: AcompProjetoStatus }) {
  const anteriores = p.tendencia.filter((t) => !t.parcial);
  if (anteriores.length === 0) return <span style={apagado}>sem sprint fechada</span>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ fontSize: 12.5, color: ds.text2 }}>Ritmo</span>
      <div style={{ display: "flex", gap: 3 }}>
        {anteriores.slice(-5).map((t) => (
          <span
            key={t.numero}
            title={`Sprint ${t.numero} · SPI ${t.spi != null ? num(t.spi) : "sem dado"}${t.meta_batida ? " · meta batida" : ""}`}
            style={{ width: 14, height: 14, borderRadius: 3, background: corDoSpi(t.spi), opacity: t.spi == null ? 0.5 : 1 }}
          />
        ))}
      </div>
      <span style={apagado}>SPI das fechadas</span>
    </div>
  );
}

function ProjetoLinha({ p, onAbrir }: { p: AcompProjetoStatus; onAbrir: () => void }) {
  return (
    <li style={{ listStyle: "none" }}>
      <button type="button" onClick={onAbrir} className="acomp-linha" aria-label={`Abrir ${p.nome ?? "projeto"}: ${STATUS_INFO[p.status].nome}`}>
        <span style={{ display: "flex", gap: 10, alignItems: "flex-start", minWidth: 0 }}>
          <span style={{ paddingTop: 6 }}><StatusDot tone={TOM_STATUS[p.status]} /></span>
          <span style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: ds.white, overflowWrap: "anywhere" }}>{p.nome ?? "Projeto"}</span>
            <span style={apagado}>
              {p.gerente && p.gerente !== "Sem gerente" ? nomeCurto(p.gerente) : "sem gerente"}
              {p.cliente ? ` · ${p.cliente}` : ""}
            </span>
          </span>
        </span>
        <BarraSprint p={p} />
        <PrazoEscopo p={p} />
        <Tendencia p={p} />
        <span aria-hidden="true" className="acomp-seta">›</span>
        {p.sinais.length > 0 && (
          <span className="acomp-pendencias">
            {p.sinais.map((s) => {
              const pe = pendencia(s);
              return <span key={s.codigo} title={`${pe.explicacao}${pe.quem ? ` Quem resolve: ${pe.quem}.` : ""}`}><Chip tone={pe.tom}>{pe.titulo}</Chip></span>;
            })}
          </span>
        )}
      </button>
    </li>
  );
}

// ── por gerente ──

function PorGerente({ projetos, onFiltrar }: { projetos: AcompProjetoStatus[]; onFiltrar: (nome: string) => void }) {
  const grupos = useMemo(() => {
    const m = new Map<string, AcompProjetoStatus[]>();
    for (const p of projetos) {
      const g = p.gerente ?? "Sem gerente";
      m.set(g, [...(m.get(g) ?? []), p]);
    }
    return [...m.entries()]
      .map(([nome, ps]) => {
        const comProgresso = ps.filter((p) => p.progresso && p.progresso.pts_previstos > 0);
        const prev = comProgresso.reduce((a, p) => a + p.progresso!.pts_previstos, 0);
        const conc = comProgresso.reduce((a, p) => a + p.progresso!.pts_concluidos, 0);
        return {
          nome, projetos: ps,
          criticos: ps.filter((p) => p.status === "critico").length,
          atencao: ps.filter((p) => p.status === "atencao").length,
          pendencias: ps.reduce((a, p) => a + p.sinais.length, 0),
          travadas: ps.reduce((a, p) => a + p.travadas, 0),
          pct: prev > 0 ? (conc / prev) * 100 : null,
        };
      })
      .sort((a, b) => (a.nome === "Sem gerente" ? 1 : 0) - (b.nome === "Sem gerente" ? 1 : 0) || b.criticos - a.criticos || b.atencao - a.atencao || a.nome.localeCompare(b.nome));
  }, [projetos]);

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5 }}>
        <thead>
          <tr>
            {["Gerente", "Projetos", "Sprint atual", "Críticos", "Atenção", "Travadas", "Pendências"].map((h, i) => (
              <th key={h} scope="col" style={{ ...labelStyle, textAlign: i === 0 ? "left" : i === 2 ? "left" : "right", padding: "0 10px 10px", whiteSpace: "nowrap" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grupos.map((g) => (
            <tr key={g.nome} style={{ borderTop: `1px solid ${ds.border}` }}>
              <td style={{ padding: "10px" }}>
                <button type="button" onClick={() => onFiltrar(g.nome)} title="Ver só os projetos deste gerente" style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13.5, fontWeight: 600, color: ds.white, textAlign: "left" }}>
                  {g.nome === "Sem gerente" ? g.nome : nomeCurto(g.nome)}
                </button>
              </td>
              <td style={{ ...mono, padding: "10px", textAlign: "right", color: ds.text2 }}>{g.projetos.length}</td>
              <td style={{ padding: "10px", minWidth: 140 }}>
                {g.pct == null ? <span style={apagado}>sem tasks</span> : (
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ flex: 1 }}><ProgressBar pct={g.pct} label={`Progresso médio de ${g.nome}`} /></span>
                    <span style={{ ...mono, fontSize: 12, color: ds.text2 }}>{Math.round(g.pct)}%</span>
                  </span>
                )}
              </td>
              <td style={{ ...mono, padding: "10px", textAlign: "right", color: g.criticos > 0 ? ds.red : ds.dim }}>{g.criticos}</td>
              <td style={{ ...mono, padding: "10px", textAlign: "right", color: g.atencao > 0 ? ds.amber : ds.dim }}>{g.atencao}</td>
              <td style={{ ...mono, padding: "10px", textAlign: "right", color: g.travadas > 0 ? ds.amber : ds.dim }}>{g.travadas}</td>
              <td style={{ ...mono, padding: "10px", textAlign: "right", color: g.pendencias > 0 ? ds.text2 : ds.dim }}>{g.pendencias}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── legenda ──

function Legenda() {
  return (
    <details className="acomp-legenda">
      <summary style={{ cursor: "pointer", fontSize: 13.5, fontWeight: 600, color: ds.text2 }}>O que significa cada status e pendência</summary>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 20, marginTop: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <span style={labelStyle}>Status</span>
          {STATUS_ORDEM.map((s) => (
            <div key={s} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13.5, fontWeight: 600, color: ds.white }}><StatusDot tone={TOM_STATUS[s]} />{STATUS_INFO[s].nome}</span>
              <span style={{ fontSize: 13, lineHeight: 1.5, color: ds.muted }}>{STATUS_INFO[s].regra}</span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <span style={labelStyle}>Pendências</span>
          {Object.entries(PENDENCIAS).map(([codigo, p]) => (
            <div key={codigo} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600, color: ds.white }}>{p.titulo(codigo === "travadas" ? "1 travada" : codigo === "spi_critico" ? "SPI 0,6" : "")}</span>
              <span style={{ fontSize: 13, lineHeight: 1.5, color: ds.muted }}>{p.explicacao} <span style={{ color: ds.text2 }}>Quem resolve: {p.quem}.</span></span>
            </div>
          ))}
        </div>
      </div>
    </details>
  );
}

function Bloco({ titulo, extra, children }: { titulo: string; extra?: ReactNode; children: ReactNode }) {
  return (
    <Card>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600, color: ds.white }}>{titulo}</h2>
          {extra}
        </div>
        {children}
      </div>
    </Card>
  );
}

const CSS = `
.acomp-linha{display:grid;grid-template-columns:minmax(200px,1.4fr) minmax(170px,1fr) minmax(150px,1fr) 96px 16px;gap:8px 24px;align-items:center;
  width:100%;text-align:left;background:none;border:none;border-top:1px solid ${ds.border};padding:16px 4px;cursor:pointer;font-family:inherit;color:${ds.text};border-radius:0}
.acomp-linha:hover{background:rgba(255,255,255,0.025)}
.acomp-linha:focus-visible{outline:2px solid ${ds.green};outline-offset:2px;border-radius:8px}
.acomp-seta{color:${ds.dim};font-size:20px;line-height:1;justify-self:end}
.acomp-linha:hover .acomp-seta{color:${ds.text2}}
.acomp-pendencias{grid-column:1 / -1;display:flex;gap:6px;flex-wrap:wrap;padding-left:17px}
.acomp-resumo{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.acomp-legenda summary::marker{color:${ds.dim}}
@media (max-width: 900px){
  .acomp-linha{grid-template-columns:1fr 1fr;gap:12px 16px}
  .acomp-linha > :first-child{grid-column:1 / -1}
  .acomp-seta{display:none}
  .acomp-resumo{grid-template-columns:repeat(2,minmax(0,1fr))}
}
`;

export default function AcompanhamentoPage() {
  const auth = useAuth();
  const permitido = !auth || auth.cargo === "lider" || auth.cargo === "owner";
  const [subarea, setSubarea] = useState<Subarea>("dados");
  const [gerente, setGerente] = useState(""); // "" = todos; "sem" = sem gerente; senão, e-mail
  const [statusFiltro, setStatusFiltro] = useState<AcompStatus | null>(null);
  const [dados, setDados] = useState<AcompanhamentoResponse | null>(null);
  const [gerentes, setGerentes] = useState<AcompGerente[]>([]); // sobrevive ao recarregar, para o select não esvaziar
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [projetoAberto, setProjetoAberto] = useState<string | null>(null);

  const pedido = useRef(0); // só a resposta do pedido mais recente vale (ao mudar subárea ou gerente)

  const carregar = useCallback(async () => {
    const meu = ++pedido.current;
    setErro("");
    setCarregando(true);
    try {
      const r = await getAcompanhamento(subarea, gerente || undefined);
      if (meu === pedido.current) { setDados(r); setGerentes(r.gerentes); }
    } catch (e) {
      // Some com o dado anterior: depois de salvar uma meta ele já não vale, e mostrá-lo junto do erro confunde.
      if (meu === pedido.current) { setDados(null); setErro(e instanceof Error ? e.message : "Erro ao buscar o acompanhamento"); }
    } finally {
      if (meu === pedido.current) setCarregando(false);
    }
  }, [subarea, gerente]);

  useEffect(() => {
    if (!permitido) return;
    void carregar();
  }, [permitido, carregar]);

  const projetos = useMemo(
    () => [...(dados?.projetos ?? [])].sort((a, b) =>
      ORDEM_STATUS[a.status] - ORDEM_STATUS[b.status] || b.sinais.length - a.sinais.length || (a.nome ?? "").localeCompare(b.nome ?? "")),
    [dados],
  );
  const visiveis = statusFiltro ? projetos.filter((p) => p.status === statusFiltro) : projetos;

  const carteira = useMemo(() => {
    const comSprint = projetos.filter((p) => p.progresso && p.progresso.pts_previstos > 0);
    const prev = comSprint.reduce((a, p) => a + p.progresso!.pts_previstos, 0);
    const conc = comSprint.reduce((a, p) => a + p.progresso!.pts_concluidos, 0);
    return {
      pct: prev > 0 ? (conc / prev) * 100 : null, conc, prev,
      travadas: projetos.reduce((a, p) => a + p.travadas, 0),
      semMeta: projetos.filter((p) => p.sinais.some((s) => s.codigo === "sem_meta")).length,
      aguardando: projetos.reduce((a, p) => a + (p.progresso?.tasks_aguardando ?? 0), 0),
    };
  }, [projetos]);

  if (!permitido) return <ErrorNotice>Acesso restrito a Líder e Owner.</ErrorNotice>;

  const mudarSubarea = (s: Subarea) => { setSubarea(s); setGerente(""); setStatusFiltro(null); setGerentes([]); setDados(null); setProjetoAberto(null); };
  const filtrarPorGerente = (nome: string) => {
    const g = gerentes.find((x) => x.nome === nome);
    setGerente(g?.email ?? "sem");
    setStatusFiltro(null);
    setProjetoAberto(null);
  };
  const k = dados?.kpis;
  const contagem: Record<AcompStatus, number> = { critico: k?.criticos ?? 0, atencao: k?.atencao ?? 0, sem_dados: k?.sem_dados ?? 0, saudavel: k?.saudaveis ?? 0 };

  return (
    <>
      <style>{CSS}</style>
      <PageHeader
        title="Acompanhamento dos projetos"
        subtitle="Quanto cada projeto já fez da sprint atual, como está o prazo e o que está pendente."
        actions={
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <SegmentedControl label="Subárea" options={SUBAREAS} value={subarea} onChange={mudarSubarea} />
            <Select aria-label="Gerente" value={gerente} onChange={(e) => { setGerente(e.target.value); setStatusFiltro(null); setDados(null); setProjetoAberto(null); }} style={{ width: "auto", minWidth: 190 }}>
              <option value="">Todos os gerentes</option>
              {gerentes.filter((g) => g.email).map((g) => <option key={g.email} value={g.email!}>{g.nome}</option>)}
              <option value="sem">Sem gerente</option>
            </Select>
          </div>
        }
      />

      {erro && <ErrorNotice>{erro}</ErrorNotice>}
      {!dados && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
      {dados && carregando && <p role="status" style={{ margin: 0, fontSize: 12.5, color: ds.muted }}>Atualizando...</p>}

      {dados && k && (
        k.projetos === 0 ? <EmptyState>{gerente ? "Nenhum projeto com este filtro." : "Nenhum projeto nesta subárea."}</EmptyState> : (
          <>
            <section aria-label="Resumo da carteira" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="acomp-resumo">
                {STATUS_ORDEM.map((s) => (
                  <FiltroStatus key={s} status={s} qtd={contagem[s]} ativo={statusFiltro === s} onClick={() => setStatusFiltro((f) => (f === s ? null : s))} />
                ))}
              </div>
              <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6, color: ds.text2 }}>
                {carteira.pct != null
                  ? <>Nas sprints atuais, <strong style={{ color: ds.white }}>{Math.round(carteira.pct)}%</strong> dos pontos planejados já foram concluídos ({pts(carteira.conc)} de {pts(carteira.prev)}).</>
                  : "Nenhuma sprint atual com tasks planejadas."}
                {" "}<span style={{ color: carteira.travadas > 0 ? ds.amber : ds.muted }}>{plural(carteira.travadas, "task travada", "tasks travadas")}</span>
                {carteira.aguardando > 0 && <> · <span style={{ color: ds.violet }}>{carteira.aguardando} aguardando aprovação</span></>}
                {" · "}<span style={{ color: carteira.semMeta > 0 ? ds.amber : ds.muted }}>{plural(carteira.semMeta, "projeto sem meta", "projetos sem meta")}</span>
                {k.metas_fechadas > 0 ? <> · metas batidas na última sprint fechada: {k.metas_batidas} de {k.metas_fechadas}</> : null}
              </p>
            </section>

            <Bloco
              titulo={statusFiltro ? `Projetos · ${STATUS_INFO[statusFiltro].nome}` : "Projetos"}
              extra={
                <span style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  {statusFiltro && (
                    <button type="button" onClick={() => setStatusFiltro(null)} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13, color: ds.green }}>
                      Ver todos
                    </button>
                  )}
                  <span style={apagado}>{plural(visiveis.length, "projeto", "projetos")} · clique para ver o detalhe</span>
                </span>
              }
            >
              {visiveis.length === 0 ? (
                <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Nenhum projeto com este status.</p>
              ) : (
                <ul style={{ margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
                  {visiveis.map((p) => <ProjetoLinha key={p.id} p={p} onAbrir={() => setProjetoAberto(p.id)} />)}
                </ul>
              )}
            </Bloco>

            <Bloco titulo="Por gerente" extra={<span style={apagado}>clique no nome para filtrar</span>}>
              <PorGerente projetos={projetos} onFiltrar={filtrarPorGerente} />
            </Bloco>

            <Card><Legenda /></Card>
          </>
        )
      )}

      {projetoAberto && <ProjetoDetalhePainel projetoId={projetoAberto} onClose={() => setProjetoAberto(null)} onMetaSalva={() => { void carregar(); }} />}
    </>
  );
}
