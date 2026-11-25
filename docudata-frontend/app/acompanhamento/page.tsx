"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { useAuth } from "../components/AuthGuard";
import Indicadores from "../components/acompanhamento/Indicadores";
import ProjetoDetalhePainel from "../components/acompanhamento/ProjetoDetalhePainel";
import {
  ORDEM_STATUS, PENDENCIAS, STATUS_INFO, TOM_STATUS, corDoSpi, num, pendencia, pts,
} from "../components/acompanhamento/visual";
import { EmptyState, ErrorNotice, PageHeader, SegmentedControl, Select, StatusDot } from "../components/ds";
import { cardStyle, ds, labelStyle, toneColors, type Tone } from "../lib/ds";
import { nomeCurto } from "../lib/nome";
import {
  getAcompanhamento, type AcompanhamentoResponse, type AcompGerente, type AcompProjetoStatus, type AcompSinal, type AcompStatus, type Subarea,
} from "../lib/api";

const SUBAREAS: { value: Subarea; label: string }[] = [
  { value: "dados", label: "Dados" },
  { value: "dev", label: "Dev" },
  { value: "pta", label: "PTA" },
];

const STATUS_ORDEM: AcompStatus[] = ["critico", "atencao", "sem_dados", "saudavel"];

const mono: CSSProperties = { fontFamily: ds.fontMono, fontVariantNumeric: "tabular-nums" };
const legenda: CSSProperties = { fontSize: 12.5, lineHeight: 1.4, color: ds.muted };
const vazio: CSSProperties = { fontSize: 13, color: ds.dim };

function plural(n: number, um: string, varios: string): string {
  return `${n} ${n === 1 ? um : varios}`;
}

function corDoTom(t: Tone): string {
  return t === "neutral" ? ds.dim : toneColors[t].fg;
}

// ── filtro por status (abas com contagem) ──

function Abas({ contagem, total, ativo, onMudar }: {
  contagem: Record<AcompStatus, number>; total: number; ativo: AcompStatus | null; onMudar: (s: AcompStatus | null) => void;
}) {
  const aba = (chave: AcompStatus | null, rotulo: string, qtd: number, tom?: Tone) => {
    const sel = ativo === chave;
    return (
      <button
        key={chave ?? "todos"}
        type="button"
        role="tab"
        aria-selected={sel}
        onClick={() => onMudar(chave)}
        title={chave ? STATUS_INFO[chave].regra : undefined}
        className="acomp-aba"
        style={{ color: sel ? ds.white : qtd === 0 ? ds.dim : ds.text2, borderBottomColor: sel ? ds.green : "transparent" }}
      >
        {tom && <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: qtd === 0 ? ds.dim : corDoTom(tom) }} />}
        {rotulo}
        <span style={{ ...mono, fontSize: 12.5, color: sel ? ds.text2 : ds.muted }}>{qtd}</span>
      </button>
    );
  };
  return (
    <div role="tablist" aria-label="Filtrar por status" className="acomp-abas">
      {aba(null, "Todos", total)}
      {STATUS_ORDEM.map((s) => aba(s, STATUS_INFO[s].nome, contagem[s], TOM_STATUS[s]))}
    </div>
  );
}

// ── células da linha ──

function Barra({ pct, cor, marca, rotulo }: { pct: number; cor: string; marca?: { pct: number; cor: string; titulo: string }; rotulo: string }) {
  const v = Math.max(0, Math.min(100, pct));
  return (
    <div role="img" aria-label={rotulo} style={{ position: "relative", height: 4, borderRadius: 2, background: "rgba(255, 255, 255, 0.08)" }}>
      <div style={{ width: `${v}%`, height: "100%", borderRadius: 2, background: cor }} />
      {marca && (
        <span title={marca.titulo} style={{ position: "absolute", top: -4, left: `calc(${Math.max(0, Math.min(100, marca.pct))}% - 1px)`, width: 2, height: 12, borderRadius: 1, background: marca.cor }} />
      )}
    </div>
  );
}

function Celula({ valor, barra, legenda: texto }: { valor: ReactNode; barra?: ReactNode; legenda: ReactNode }) {
  return (
    <div className="acomp-celula">
      <span style={{ ...mono, fontSize: 14, fontWeight: 600, color: ds.white }}>{valor}</span>
      {barra}
      <span style={legenda}>{texto}</span>
    </div>
  );
}

function CelulaSprint({ p }: { p: AcompProjetoStatus }) {
  const pr = p.progresso;
  if (!p.sprint_atual) return <span className="acomp-celula" style={vazio} data-rotulo="Sprint atual">Nenhuma sprint iniciada</span>;
  if (!pr || pr.tasks_total === 0) return <span className="acomp-celula" style={vazio} data-rotulo="Sprint atual">Sprint {p.sprint_atual.numero} sem tasks</span>;
  return (
    <Celula
      valor={pr.pct != null ? `${Math.round(pr.pct)}%` : "—"}
      barra={<Barra pct={pr.pct ?? 0} cor={ds.green} rotulo={`${Math.round(pr.pct ?? 0)}% dos pontos da sprint ${p.sprint_atual.numero} concluídos`} />}
      legenda={<>S{p.sprint_atual.numero}{p.sprint_atual.fechada ? " fechada" : ""} · {pts(pr.pts_concluidos)}/{pts(pr.pts_previstos)} pts · {pr.tasks_concluidas}/{pr.tasks_total} tasks</>}
    />
  );
}

function CelulaEscopo({ p }: { p: AcompProjetoStatus }) {
  if (p.pct_prazo == null || p.pct_escopo == null) {
    const semEscopo = p.sinais.some((s) => s.codigo === "sem_funcionalidades");
    return <span className="acomp-celula" style={vazio}>{semEscopo ? "Escopo vazio" : "Sem datas do contrato"}</span>;
  }
  const atrasado = p.pct_prazo > p.pct_escopo;
  return (
    <Celula
      valor={`${Math.round(p.pct_escopo)}%`}
      barra={
        <Barra
          pct={p.pct_escopo} cor={ds.violet}
          marca={{ pct: p.pct_prazo, cor: atrasado ? ds.amber : ds.text2, titulo: `${Math.round(p.pct_prazo)}% do prazo` }}
          rotulo={`${Math.round(p.pct_escopo)}% do escopo aprovado, ${Math.round(p.pct_prazo)}% do prazo consumido`}
        />
      }
      legenda={<span style={{ color: atrasado ? ds.amber : undefined }}>{Math.round(p.pct_prazo)}% do prazo passou</span>}
    />
  );
}

function CelulaRitmo({ p }: { p: AcompProjetoStatus }) {
  const fechadas = p.tendencia.filter((t) => !t.parcial).slice(-5);
  if (fechadas.length === 0) return <span className="acomp-celula" style={vazio}>—</span>;
  const ultima = fechadas[fechadas.length - 1];
  return (
    <div className="acomp-celula">
      <span style={{ ...mono, fontSize: 14, fontWeight: 600, color: ultima.spi != null ? corDoSpi(ultima.spi) : ds.dim }}>
        {ultima.spi != null ? num(ultima.spi) : "—"}
      </span>
      <span style={{ display: "flex", gap: 3, alignItems: "flex-end", height: 12 }} aria-hidden="true">
        {fechadas.map((t) => (
          <span
            key={t.numero}
            title={`Sprint ${t.numero} · SPI ${t.spi != null ? num(t.spi) : "sem dado"}`}
            style={{ width: 8, height: t.spi == null ? 3 : Math.max(3, Math.min(12, t.spi * 12)), borderRadius: 1, background: corDoSpi(t.spi) }}
          />
        ))}
      </span>
      <span style={legenda}>SPI de S{ultima.numero}</span>
    </div>
  );
}

/** Pendências como texto: marcador pequeno pela gravidade, sem pílula. */
function Pendencias({ sinais }: { sinais: AcompSinal[] }) {
  return (
    <ul className="acomp-pendencias" aria-label="Pendências">
      {sinais.map((s) => {
        const pe = pendencia(s);
        return (
          <li key={s.codigo} title={`${pe.explicacao}${pe.quem ? ` Quem resolve: ${pe.quem}.` : ""}`}>
            <span aria-hidden="true" style={{ width: 6, height: 6, borderRadius: 1.5, flexShrink: 0, background: corDoTom(pe.tom) }} />
            <span style={{ color: pe.tom === "red" ? ds.text : ds.text2 }}>{pe.titulo}</span>
          </li>
        );
      })}
    </ul>
  );
}

function ProjetoLinha({ p, onAbrir }: { p: AcompProjetoStatus; onAbrir: () => void }) {
  return (
    <li>
      <button type="button" onClick={onAbrir} className="acomp-cols acomp-linha" aria-label={`Abrir ${p.nome ?? "projeto"}: ${STATUS_INFO[p.status].nome}`}>
        <span className="acomp-nome">
          <span style={{ paddingTop: 7 }}><StatusDot tone={TOM_STATUS[p.status]} /></span>
          <span style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: ds.white, overflowWrap: "anywhere" }}>{p.nome ?? "Projeto"}</span>
            <span style={legenda}>
              {p.gerente && p.gerente !== "Sem gerente" ? nomeCurto(p.gerente) : "sem gerente"}
              {p.cliente ? ` · ${p.cliente}` : ""}
            </span>
          </span>
        </span>
        <CelulaSprint p={p} />
        <CelulaEscopo p={p} />
        <CelulaRitmo p={p} />
        <span aria-hidden="true" className="acomp-seta">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 3.5 10.5 8 6 12.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </span>
        {p.sinais.length > 0 && <Pendencias sinais={p.sinais} />}
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

  const num0 = (v: number, cor: string) => <span style={{ ...mono, color: v > 0 ? cor : ds.dim }}>{v}</span>;
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="acomp-tabela">
        <thead>
          <tr>
            <th scope="col" style={{ textAlign: "left" }}>Gerente</th>
            <th scope="col">Projetos</th>
            <th scope="col" style={{ textAlign: "left", minWidth: 180 }}>Sprint atual</th>
            <th scope="col">Críticos</th>
            <th scope="col">Atenção</th>
            <th scope="col">Travadas</th>
            <th scope="col">Pendências</th>
          </tr>
        </thead>
        <tbody>
          {grupos.map((g) => (
            <tr key={g.nome}>
              <td style={{ textAlign: "left" }}>
                <button type="button" onClick={() => onFiltrar(g.nome)} title="Ver só os projetos deste gerente" className="acomp-link">
                  {g.nome === "Sem gerente" ? g.nome : nomeCurto(g.nome)}
                </button>
              </td>
              <td><span style={{ ...mono, color: ds.text2 }}>{g.projetos.length}</span></td>
              <td style={{ textAlign: "left" }}>
                {g.pct == null ? <span style={vazio}>sem tasks</span> : (
                  <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ flex: 1 }}><Barra pct={g.pct} cor={ds.green} rotulo={`${Math.round(g.pct)}% dos pontos concluídos`} /></span>
                    <span style={{ ...mono, fontSize: 12.5, color: ds.text2, width: 36, textAlign: "right" }}>{Math.round(g.pct)}%</span>
                  </span>
                )}
              </td>
              <td>{num0(g.criticos, ds.red)}</td>
              <td>{num0(g.atencao, ds.amber)}</td>
              <td>{num0(g.travadas, ds.amber)}</td>
              <td>{num0(g.pendencias, ds.text2)}</td>
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
      <summary>O que significa cada status e pendência</summary>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: "24px 40px", marginTop: 20 }}>
        <dl style={{ margin: 0, display: "flex", flexDirection: "column", gap: 14 }}>
          {STATUS_ORDEM.map((s) => (
            <div key={s}>
              <dt style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13.5, fontWeight: 600, color: ds.white }}>
                <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: corDoTom(TOM_STATUS[s]) }} />{STATUS_INFO[s].nome}
              </dt>
              <dd style={{ margin: "4px 0 0 15px", fontSize: 13, lineHeight: 1.5, color: ds.muted }}>{STATUS_INFO[s].regra}</dd>
            </div>
          ))}
        </dl>
        <dl style={{ margin: 0, display: "flex", flexDirection: "column", gap: 14 }}>
          {Object.entries(PENDENCIAS).map(([codigo, p]) => (
            <div key={codigo}>
              <dt style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13.5, fontWeight: 600, color: ds.white }}>
                <span aria-hidden="true" style={{ width: 6, height: 6, borderRadius: 1.5, background: corDoTom(p.tom) }} />
                {p.titulo(codigo === "travadas" ? "2 travadas" : codigo === "spi_critico" ? "SPI 0,6" : "")}
              </dt>
              <dd style={{ margin: "4px 0 0 14px", fontSize: 13, lineHeight: 1.5, color: ds.muted }}>
                {p.explicacao} <span style={{ color: ds.text2 }}>Quem resolve: {p.quem}.</span>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </details>
  );
}

const painel: CSSProperties = { ...cardStyle, boxShadow: "none", borderRadius: 14 };

const CSS = `
.acomp-abas{display:flex;gap:4px;overflow-x:auto;padding:0 20px;border-bottom:1px solid ${ds.border}}
.acomp-aba{display:inline-flex;align-items:center;gap:8px;height:48px;padding:0 12px;background:none;border:none;border-bottom:2px solid transparent;
  margin-bottom:-1px;font-family:inherit;font-size:13.5px;font-weight:600;cursor:pointer;white-space:nowrap}
.acomp-aba:hover{color:${ds.white} !important}
.acomp-aba:focus-visible{outline:2px solid ${ds.green};outline-offset:-4px;border-radius:6px}
.acomp-cols{display:grid;grid-template-columns:minmax(220px,1.5fr) minmax(170px,1fr) minmax(170px,1fr) 110px 16px;column-gap:32px}
.acomp-cabecalho{padding:14px 24px 10px}
.acomp-cabecalho span{font-family:${ds.fontMono};font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:${ds.dim}}
.acomp-lista{list-style:none;margin:0;padding:0}
.acomp-linha{row-gap:12px;align-items:center;width:100%;text-align:left;
  background:none;border:none;border-top:1px solid ${ds.border};padding:18px 24px;cursor:pointer;font-family:inherit;color:${ds.text};transition:background .15s}
.acomp-linha:hover{background:rgba(255,255,255,0.025)}
.acomp-linha:focus-visible{outline:2px solid ${ds.green};outline-offset:-2px}
.acomp-nome{display:flex;gap:12px;align-items:flex-start;min-width:0}
.acomp-celula{display:flex;flex-direction:column;gap:7px;min-width:0}
.acomp-seta{color:${ds.dim};display:flex;justify-content:flex-end}
.acomp-linha:hover .acomp-seta{color:${ds.text2}}
.acomp-pendencias{grid-column:1 / -1;list-style:none;margin:0;padding:0 0 0 19px;display:flex;flex-wrap:wrap;gap:6px 20px}
.acomp-pendencias li{display:inline-flex;align-items:center;gap:8px;font-size:13px}
.acomp-tabela{width:100%;border-collapse:collapse;font-size:13.5px}
.acomp-tabela th{font-family:${ds.fontMono};font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:${ds.dim};font-weight:500;
  text-align:right;padding:0 12px 10px;white-space:nowrap}
.acomp-tabela td{text-align:right;padding:12px;border-top:1px solid ${ds.border}}
.acomp-tabela th:first-child,.acomp-tabela td:first-child{padding-left:0}
.acomp-tabela th:last-child,.acomp-tabela td:last-child{padding-right:0}
.acomp-link{background:none;border:none;padding:0;cursor:pointer;font-family:inherit;font-size:13.5px;font-weight:600;color:${ds.white};text-align:left}
.acomp-link:hover{color:${ds.green}}
.acomp-legenda summary{cursor:pointer;font-size:13.5px;font-weight:600;color:${ds.text2};list-style:none;display:flex;align-items:center;gap:8px}
.acomp-legenda summary::-webkit-details-marker{display:none}
.acomp-legenda summary::before{content:"";width:6px;height:6px;border-right:1.5px solid ${ds.muted};border-bottom:1.5px solid ${ds.muted};transform:rotate(-45deg);transition:transform .15s}
.acomp-legenda[open] summary::before{transform:rotate(45deg)}
@media (max-width: 900px){
  .acomp-cabecalho{display:none !important}
  .acomp-linha{grid-template-columns:1fr 1fr;row-gap:14px;column-gap:20px;padding:16px 20px}
  .acomp-linha > .acomp-nome,.acomp-pendencias{grid-column:1 / -1}
  .acomp-seta{display:none}
}
`;

export default function AcompanhamentoPage() {
  const auth = useAuth();
  const permitido = !auth || auth.cargo === "lider" || auth.cargo === "owner";
  const [subarea, setSubarea] = useState<Subarea>("dados");
  const [gerente, setGerente] = useState(""); // "" = todos; "sem" = sem gerente; senão, e-mail
  const [statusFiltro, setStatusFiltro] = useState<AcompStatus | null>(null);
  const [visao, setVisao] = useState<"projetos" | "indicadores">("projetos");
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
  const forte = (t: ReactNode) => <strong style={{ ...mono, fontWeight: 600, color: ds.white }}>{t}</strong>;

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
            <SegmentedControl
              label="Visão"
              options={[{ value: "projetos", label: "Projetos" }, { value: "indicadores", label: "Indicadores e metas" }]}
              value={visao}
              onChange={setVisao}
            />
            {visao === "indicadores" ? <Indicadores dados={dados} projetos={projetos} onAbrir={setProjetoAberto} /> : <>
            <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.7, color: ds.muted, maxWidth: "75ch" }}>
              {carteira.pct != null
                ? <>Nas sprints atuais, {forte(`${Math.round(carteira.pct)}%`)} dos pontos planejados já foram concluídos ({pts(carteira.conc)} de {pts(carteira.prev)}).</>
                : "Nenhuma sprint atual com tasks planejadas."}{" "}
              {forte(carteira.travadas)} {carteira.travadas === 1 ? "task travada" : "tasks travadas"}, {forte(carteira.aguardando)} aguardando aprovação
              {" "}e {forte(carteira.semMeta)} {carteira.semMeta === 1 ? "projeto sem meta" : "projetos sem meta"}.
              {k.metas_fechadas > 0 ? <> Metas batidas na última sprint fechada: {forte(`${k.metas_batidas} de ${k.metas_fechadas}`)}.</> : null}
            </p>

            <section aria-label="Projetos" style={painel}>
              <Abas contagem={contagem} total={k.projetos} ativo={statusFiltro} onMudar={setStatusFiltro} />
              {visiveis.length === 0 ? (
                <p style={{ margin: 0, padding: "28px 24px", fontSize: 14, color: ds.muted }}>Nenhum projeto com este status.</p>
              ) : (
                <ul className="acomp-lista">
                  <li aria-hidden="true" className="acomp-cols acomp-cabecalho">
                    <span>Projeto</span><span>Sprint atual</span><span>Escopo × prazo</span><span>Ritmo</span><span />
                  </li>
                  {visiveis.map((p) => <ProjetoLinha key={p.id} p={p} onAbrir={() => setProjetoAberto(p.id)} />)}
                </ul>
              )}
            </section>

            <section aria-labelledby="acomp-por-gerente" style={{ ...painel, padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <h2 id="acomp-por-gerente" style={{ margin: 0, fontSize: 16, fontWeight: 600, color: ds.white }}>Por gerente</h2>
                <span style={legenda}>Clique no nome para ver só os projetos dele</span>
              </div>
              <PorGerente projetos={projetos} onFiltrar={filtrarPorGerente} />
            </section>

            </>}

            <section style={{ ...painel, padding: "18px 24px" }}><Legenda /></section>
          </>
        )
      )}

      {projetoAberto && <ProjetoDetalhePainel projetoId={projetoAberto} onClose={() => setProjetoAberto(null)} onMetaSalva={() => { void carregar(); }} />}
    </>
  );
}
