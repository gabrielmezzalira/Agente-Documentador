"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Button, Chip, ErrorNotice, Modal, ProgressBar } from "../ds";
import DefinirMetaModal from "../DefinirMetaModal";
import { corDoSpi } from "./MapaCalor";
import { ds, labelStyle, type Tone } from "../../lib/ds";
import { getDetalheProjeto, getEventosMeta, type AcompDetalheResponse, type AcompStatus, type MetaEvento } from "../../lib/api";

const TOM: Record<AcompStatus, Tone> = { critico: "red", atencao: "amber", sem_dados: "neutral", saudavel: "green" };
const COR_STATUS: Record<AcompStatus, string> = { critico: ds.red, atencao: ds.amber, sem_dados: ds.chartGrey, saudavel: ds.green };
const STATUS_PALAVRA: Record<AcompStatus, string> = { critico: "Crítico", atencao: "Atenção", sem_dados: "Faltam dados", saudavel: "Saudável" };

const mono: CSSProperties = { fontFamily: ds.fontMono };

function num(x: number, casas = 2): string {
  return x.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function pct(x: number | null): string {
  return x == null ? "sem dado" : `${Math.round(x)}%`;
}

function Numero({ label, valor, cor }: { label: string; valor: string; cor?: string }) {
  const semDado = valor === "sem dado" || valor === "sem datas";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, padding: 12, border: `1px solid ${ds.border}`, borderRadius: 8 }}>
      <span style={labelStyle}>{label}</span>
      <span style={{ ...mono, fontSize: semDado ? 14 : 20, fontWeight: 700, color: semDado ? ds.muted : cor ?? ds.white }}>{valor}</span>
    </div>
  );
}

function Secao({ children }: { children: ReactNode }) {
  return <section style={{ display: "flex", flexDirection: "column", gap: 10, paddingTop: 16, borderTop: `1px solid ${ds.border}` }}>{children}</section>;
}

function dataCurta(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString("pt-BR");
}

function Historico({ sprintId, versao }: { sprintId: string; versao: number }) {
  const [aberto, setAberto] = useState(false);
  const [eventos, setEventos] = useState<MetaEvento[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!aberto) return;
    let vivo = true;
    setErro("");
    setEventos(null);
    getEventosMeta(sprintId)
      .then((e) => { if (vivo) setEventos(e); })
      .catch((e) => { if (vivo) { setEventos(null); setErro(e instanceof Error ? e.message : "Erro ao buscar o histórico da meta"); } });
    return () => { vivo = false; };
  }, [aberto, sprintId, versao]);

  return (
    <div>
      <button type="button" aria-expanded={aberto} onClick={() => setAberto((a) => !a)} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13, color: ds.text2, textDecoration: "underline" }}>
        Histórico de mudanças da meta
      </button>
      {aberto && (
        <div style={{ marginTop: 8 }}>
          {erro && <ErrorNotice>{erro}</ErrorNotice>}
          {!erro && eventos === null && <p role="status" style={{ margin: 0, fontSize: 13, color: ds.muted }}>Carregando...</p>}
          {eventos !== null && eventos.length === 0 && <p style={{ margin: 0, fontSize: 13, color: ds.muted }}>Nenhuma mudança registrada.</p>}
          {eventos !== null && eventos.length > 0 && (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 4 }}>
              {eventos.map((ev, i) => (
                <li key={i} style={{ fontSize: 13, color: ds.text2 }}>
                  {ev.acao} · {ev.titulo ?? "(funcionalidade removida)"} · {ev.pessoa_nome ?? "sem pessoa"} · {dataCurta(ev.criado_em)}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function SprintASprint({ sprints }: { sprints: AcompDetalheResponse["sprints"] }) {
  const lista = [...sprints].sort((a, b) => a.numero - b.numero);
  const max = Math.max(1, ...lista.flatMap((s) => [s.previsto, s.realizado]));
  const L = 56, H = 90, gap = 14;
  const largura = lista.length * L + (lista.length - 1) * gap;
  const alt = (v: number) => (v / max) * H;
  return (
    <div style={{ overflowX: "auto" }}>
      <svg role="img" aria-label="Pontos previstos e realizados por sprint" width={largura} height={H + 28} viewBox={`0 0 ${largura} ${H + 28}`} style={{ display: "block" }}>
        {lista.map((s, i) => {
          const x = i * (L + gap);
          const w = (L - 4) / 2;
          return (
            <g key={s.numero}>
              <title>{`Sprint ${s.numero} · previsto ${num(s.previsto, 1)} · realizado ${num(s.realizado, 1)} · SPI ${s.spi != null ? num(s.spi) : "sem dado"}${s.meta_batida ? " · meta batida" : ""}`}</title>
              <rect x={x} y={H - alt(s.previsto)} width={w} height={alt(s.previsto)} rx={2} fill={ds.chartGrey} />
              <rect x={x + w + 4} y={H - alt(s.realizado)} width={w} height={alt(s.realizado)} rx={2} fill={corDoSpi(s.spi)} />
              <text x={x + L / 2} y={H + 14} textAnchor="middle" fontSize={11} fill={ds.muted} fontFamily={ds.fontMono}>{`S${s.numero}`}{s.meta_batida ? " ●" : ""}</text>
            </g>
          );
        })}
      </svg>
      <p style={{ margin: "6px 0 0", fontSize: 12, color: ds.muted }}>previsto · realizado · ● meta batida</p>
    </div>
  );
}

/** Painel de detalhe de um projeto do acompanhamento: diagnóstico, meta da sprint, sprint a sprint e time. */
export default function ProjetoDetalhePainel({ projetoId, onClose, onMetaSalva }: { projetoId: string; onClose: () => void; onMetaSalva: () => void }) {
  const [d, setD] = useState<AcompDetalheResponse | null>(null);
  const [erro, setErro] = useState("");
  const [definindo, setDefinindo] = useState(false);
  const [versao, setVersao] = useState(0);
  const pedido = useRef(0);

  const carregar = useCallback(async () => {
    const meu = ++pedido.current;
    try {
      const r = await getDetalheProjeto(projetoId);
      if (meu === pedido.current) { setD(r); setErro(""); }
    } catch (e) {
      if (meu === pedido.current) setErro(e instanceof Error ? e.message : "Erro ao buscar o detalhe do projeto");
    }
  }, [projetoId]);

  useEffect(() => {
    setD(null);
    void carregar();
    return () => { pedido.current++; };
  }, [carregar]);

  const titulo = d ? `${d.projeto.nome ?? "Projeto"} · ${d.projeto.gerente ?? "sem gerente"}` : "Detalhe do projeto";
  const tom = d ? TOM[d.status] : "neutral";
  const atual = d?.sprint_atual ?? null;
  const metaTexto = d && d.meta.total > 0 && atual ? `Sprint ${atual.numero} (atual) · meta ${d.meta.entregues} de ${d.meta.total} entregue` : null;

  return (
    <>
      <Modal title={titulo} width={760} onClose={() => { if (!definindo) onClose(); }}>
        {erro && <ErrorNotice>{erro}</ErrorNotice>}
        {!d && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
        {d && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ border: `1px solid ${COR_STATUS[d.status]}`, borderRadius: 8, padding: 12, display: "flex", flexDirection: "column", gap: 6 }}>
              <span style={labelStyle}>Diagnóstico</span>
              <span><Chip tone={tom} dot>{STATUS_PALAVRA[d.status]}</Chip></span>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: ds.text2 }}>{d.diagnostico}</p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 8 }}>
              <Numero label={d.sprint_atual && !d.sprint_atual.fechada ? "SPI da sprint atual (parcial)" : "SPI da sprint atual"} valor={d.numeros.spi_atual != null ? num(d.numeros.spi_atual) : "sem dado"} cor={d.numeros.spi_atual != null ? corDoSpi(d.numeros.spi_atual) : undefined} />
              <Numero label="SPI da última sprint fechada" valor={d.numeros.spi_ultima_fechada != null ? num(d.numeros.spi_ultima_fechada) : "sem dado"} cor={d.numeros.spi_ultima_fechada != null ? corDoSpi(d.numeros.spi_ultima_fechada) : undefined} />
              <Numero label="Prazo × escopo" valor={d.numeros.sem_funcionalidades ? "sem funcionalidades" : d.numeros.prazo_sem_dados || d.numeros.pct_prazo == null || d.numeros.pct_escopo == null ? "sem datas" : `${Math.round(d.numeros.pct_prazo)}% · ${Math.round(d.numeros.pct_escopo)}%`} />
              <Numero label="Tasks travadas" valor={String(d.numeros.travadas)} />
              <Numero label="p85 tempo limpo" valor={d.numeros.p85_horas != null ? `${Math.round(d.numeros.p85_horas)}h` : "sem dado"} />
            </div>

            <Secao>
              <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <span style={labelStyle}>{metaTexto ?? (atual ? `Sprint ${atual.numero} (atual)` : "Sprint atual")}</span>
                <span style={{ marginLeft: "auto" }}>
                  <Button variant="primary" size="sm" onClick={() => setDefinindo(true)}>Definir meta</Button>
                </span>
              </div>
              {!metaTexto || d.meta.funcionalidades.length === 0 ? (
                <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Sem meta nesta sprint.</p>
              ) : (
                <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
                  {d.meta.funcionalidades.map((f) => (
                    <li key={f.id} style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", padding: "8px 0", borderBottom: `1px solid ${ds.border}`, fontSize: 14, color: ds.text2 }}>
                      <span style={{ ...mono, color: ds.muted }}>{f.id_funcional ?? ""}</span>
                      <span style={{ flex: "1 1 160px" }}>{f.titulo ?? "(sem título)"}</span>
                      {f.aprovada && <Chip tone="green">aprovada</Chip>}
                      {!f.planejada_na_sprint && <Chip tone="amber">fora do planejamento</Chip>}
                      <span style={{ flex: "0 0 110px" }}>{f.pct_tasks != null && <ProgressBar pct={f.pct_tasks} label={`Tasks de ${f.titulo ?? "funcionalidade"}`} />}</span>
                      <span style={{ ...mono, fontSize: 12, color: ds.muted, minWidth: 64, textAlign: "right" }}>{f.pct_tasks != null ? `${Math.round(f.pct_tasks)}%` : "sem dado"}</span>
                    </li>
                  ))}
                </ul>
              )}
              {d.planejadas_fora_da_meta.length > 0 && (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", fontSize: 13, color: ds.muted }}>
                  Planejadas fora da meta:
                  {d.planejadas_fora_da_meta.map((f) => <Chip key={f.id} tone="violet">{f.id_funcional ?? f.titulo ?? "?"}</Chip>)}
                </div>
              )}
              {atual && <Historico sprintId={atual.id} versao={versao} />}
            </Secao>

            <Secao>
              <span style={labelStyle}>Sprint a sprint</span>
              {d.sprints.length === 0 ? <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>sem dado</p> : <SprintASprint sprints={d.sprints} />}
            </Secao>

            <Secao>
              <span style={labelStyle}>{d.time.sprint_numero != null ? `Time · sprint ${d.time.sprint_numero}` : "Time"}</span>
              {d.time.pessoas.length === 0 ? (
                <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Ninguém com task nesta sprint.</p>
              ) : (
                <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
                  {d.time.pessoas.map((p) => (
                    <li key={p.operacional_id} style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", padding: "8px 0", borderBottom: `1px solid ${ds.border}`, fontSize: 14, color: ds.text2 }}>
                      <span style={{ fontWeight: 600, color: ds.white }}>{p.nome ?? "Sem nome"}</span>
                      <span style={{ ...mono, marginLeft: "auto", color: ds.muted }}>{num(p.realizado, 1)} pts</span>
                      {p.piso == null || p.abaixo == null
                        ? <span style={{ fontSize: 12.5, color: ds.muted }}>sem histórico para o piso</span>
                        : p.abaixo ? <Chip tone="red">abaixo do piso ({num(p.piso, 1)})</Chip> : <Chip tone="green">acima</Chip>}
                    </li>
                  ))}
                </ul>
              )}
            </Secao>
          </div>
        )}
      </Modal>
      {definindo && d && (
        <DefinirMetaModal
          detalhe={d}
          onClose={() => setDefinindo(false)}
          onSalvo={() => { setVersao((v) => v + 1); void carregar(); onMetaSalva(); }}
        />
      )}
    </>
  );
}
