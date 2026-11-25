"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Button, Chip, ErrorNotice, Modal, ProgressBar, StatusDot } from "../ds";
import DefinirMetaModal from "../DefinirMetaModal";
import { COLUNAS_KANBAN, COR_STATUS, STATUS_INFO, TOM_STATUS, corDoSpi, num, pendencia, pts } from "./visual";
import { ds, labelStyle } from "../../lib/ds";
import { nomeCurto } from "../../lib/nome";
import { getDetalheProjeto, getEventosMeta, type AcompDetalheResponse, type AcompTaskSprint, type MetaEvento } from "../../lib/api";

const mono: CSSProperties = { fontFamily: ds.fontMono };
const apagado: CSSProperties = { fontSize: 13, color: ds.muted };

function Numero({ label, valor, cor, dica }: { label: string; valor: string; cor?: string; dica?: string }) {
  const semDado = valor === "sem dado" || valor === "sem datas" || valor === "sem funcionalidades";
  return (
    <div title={dica} style={{ display: "flex", flexDirection: "column", gap: 4, padding: 12, border: `1px solid ${ds.border}`, borderRadius: 10 }}>
      <span style={labelStyle}>{label}</span>
      <span style={{ ...mono, fontSize: semDado ? 14 : 20, fontWeight: 700, color: semDado ? ds.muted : cor ?? ds.white }}>{valor}</span>
    </div>
  );
}

function Secao({ titulo, extra, children }: { titulo: string; extra?: ReactNode; children: ReactNode }) {
  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 12, paddingTop: 20, borderTop: `1px solid ${ds.border}` }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: ds.white }}>{titulo}</h3>
        {extra}
      </div>
      {children}
    </section>
  );
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
      <button type="button" aria-expanded={aberto} onClick={() => setAberto((a) => !a)} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13, color: ds.text2, textDecoration: "underline", textUnderlineOffset: 2 }}>
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
      <p style={{ margin: "6px 0 0", fontSize: 12, color: ds.muted }}>barra cinza: previsto · barra colorida: realizado (cor pelo SPI) · ● meta batida</p>
    </div>
  );
}

/** Progresso da sprint atual: o número grande, a barra e as tasks por coluna do kanban. */
function ProgressoSprint({ d }: { d: AcompDetalheResponse }) {
  const pr = d.progresso;
  const atual = d.sprint_atual;
  if (!atual) return <p style={{ margin: 0, ...apagado }}>Nenhuma sprint iniciada.</p>;
  if (!pr || pr.tasks_total === 0) return <p style={{ margin: 0, ...apagado }}>A Sprint {atual.numero} ainda não tem tasks: falta a Planning.</p>;
  const contagem: Record<string, number> = {
    planejado: pr.tasks_planejadas, em_andamento: pr.tasks_em_andamento,
    pendente_aprovacao: pr.tasks_aguardando, concluida: pr.tasks_concluidas,
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap" }}>
        <span style={{ ...mono, fontSize: 40, fontWeight: 700, lineHeight: 1, color: ds.white }}>{pr.pct != null ? `${Math.round(pr.pct)}%` : "—"}</span>
        <span style={{ fontSize: 14, lineHeight: 1.5, color: ds.text2, paddingBottom: 2 }}>
          do planejado concluído · {pts(pr.pts_concluidos)} de {pts(pr.pts_previstos)} pontos
          {atual.fechada ? " · sprint fechada" : " · sprint em andamento"}
        </span>
      </div>
      <ProgressBar pct={pr.pct ?? 0} height={8} label={`Progresso da Sprint ${atual.numero}`} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 8 }}>
        {COLUNAS_KANBAN.map((c) => (
          <div key={c.chave} style={{ display: "flex", flexDirection: "column", gap: 4, padding: "10px 12px", border: `1px solid ${ds.border}`, borderRadius: 10 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: ds.muted }}>
              <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: c.cor }} />{c.nome}
            </span>
            <span style={{ ...mono, fontSize: 20, fontWeight: 700, color: contagem[c.chave] > 0 ? ds.white : ds.dim }}>{contagem[c.chave]}</span>
          </div>
        ))}
      </div>
      {(pr.travadas > 0 || pr.extras > 0) && (
        <p style={{ margin: 0, ...apagado }}>
          {pr.travadas > 0 && <span style={{ color: ds.amber }}>{pr.travadas} {pr.travadas === 1 ? "task travada" : "tasks travadas"}</span>}
          {pr.travadas > 0 && pr.extras > 0 && " · "}
          {pr.extras > 0 && <>{pr.extras} {pr.extras === 1 ? "task extra" : "tasks extras"} (fora dos pontos previstos)</>}
        </p>
      )}
    </div>
  );
}

function Planejamento({ d }: { d: AcompDetalheResponse }) {
  if (d.planejamento.length === 0) {
    return <p style={{ margin: 0, ...apagado }}>Nenhuma funcionalidade ligada a esta sprint. As tasks abaixo são o planejado.</p>;
  }
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
      {d.planejamento.map((f) => {
        const pct = f.tasks_total > 0 ? (f.tasks_concluidas / f.tasks_total) * 100 : null;
        return (
          <li key={f.id} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 120px 72px", gap: 12, alignItems: "center", padding: "10px 0", borderTop: `1px solid ${ds.border}` }}>
            <span style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
              <span style={{ fontSize: 14, color: ds.text }}>
                <span style={{ ...mono, fontSize: 12, color: ds.muted, marginRight: 8 }}>{f.id_funcional ?? ""}</span>
                {f.titulo ?? "(sem título)"}
              </span>
              <span style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {f.na_meta && <Chip tone="violet">na meta</Chip>}
                {f.aprovada ? <Chip tone="green">aprovada</Chip> : f.status === "concluida" ? <Chip tone="amber">concluída, falta aprovar</Chip> : null}
                {f.tasks_total === 0 && <Chip>sem tasks nesta sprint</Chip>}
              </span>
            </span>
            <span>{pct != null && <ProgressBar pct={pct} label={`Tasks de ${f.titulo ?? "funcionalidade"}`} />}</span>
            <span style={{ ...mono, fontSize: 12, color: ds.muted, textAlign: "right" }}>{f.tasks_total > 0 ? `${f.tasks_concluidas}/${f.tasks_total} tasks` : "—"}</span>
          </li>
        );
      })}
    </ul>
  );
}

function TasksDaSprint({ tasks }: { tasks: AcompTaskSprint[] }) {
  const [verConcluidas, setVerConcluidas] = useState(false);
  if (tasks.length === 0) return <p style={{ margin: 0, ...apagado }}>Nenhuma task nesta sprint.</p>;
  const abertas = tasks.filter((t) => t.coluna !== "concluida");
  const concluidas = tasks.filter((t) => t.coluna === "concluida");
  const nomeColuna = (c: string) => COLUNAS_KANBAN.find((x) => x.chave === c) ?? COLUNAS_KANBAN[0];
  const linha = (t: AcompTaskSprint) => {
    const col = nomeColuna(t.coluna);
    return (
      <li key={t.id} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 12, alignItems: "center", padding: "9px 0", borderTop: `1px solid ${ds.border}` }}>
        <span style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
          <span style={{ fontSize: 13.5, color: t.coluna === "concluida" ? ds.muted : ds.text, overflowWrap: "anywhere" }}>{t.titulo ?? "(sem título)"}</span>
          <span style={{ fontSize: 12, color: ds.muted }}>
            {t.responsavel ? nomeCurto(t.responsavel) : <span style={{ color: ds.amber }}>sem responsável</span>}
            {t.funcionalidade ? ` · ${t.funcionalidade}` : ""} · {pts(t.pontos)} pt{t.pontos === 1 ? "" : "s"}{t.extra ? " · extra" : ""}
          </span>
        </span>
        <span style={{ display: "flex", gap: 6, alignItems: "center", justifyContent: "flex-end", flexWrap: "wrap" }}>
          {t.travada && <Chip tone="red">travada</Chip>}
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, color: ds.text2, whiteSpace: "nowrap" }}>
            <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: col.cor }} />{col.nome}
          </span>
        </span>
      </li>
    );
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {abertas.length === 0
        ? <p style={{ margin: 0, fontSize: 13, color: ds.green }}>Todas as tasks da sprint foram concluídas.</p>
        : <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>{abertas.map(linha)}</ul>}
      {concluidas.length > 0 && (
        <>
          <button type="button" aria-expanded={verConcluidas} onClick={() => setVerConcluidas((v) => !v)} style={{ alignSelf: "flex-start", background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13, color: ds.text2, textDecoration: "underline", textUnderlineOffset: 2 }}>
            {verConcluidas ? "Esconder" : "Ver"} {concluidas.length} {concluidas.length === 1 ? "concluída" : "concluídas"}
          </button>
          {verConcluidas && <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>{concluidas.map(linha)}</ul>}
        </>
      )}
    </div>
  );
}

/** Detalhe de um projeto do acompanhamento: o que está pendente, quanto da sprint foi feito, o planejado, meta, histórico e time. */
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
      if (meu === pedido.current) { setD(null); setErro(e instanceof Error ? e.message : "Erro ao buscar o detalhe do projeto"); }
    }
  }, [projetoId]);

  useEffect(() => {
    setD(null);
    void carregar();
    return () => { pedido.current++; };
  }, [carregar]);

  const titulo = d ? `${d.projeto.nome ?? "Projeto"} · ${d.projeto.gerente ? nomeCurto(d.projeto.gerente) : "sem gerente"}` : "Detalhe do projeto";
  const atual = d?.sprint_atual ?? null;
  const metaTexto = d && d.meta.total > 0 && atual ? `Meta da Sprint ${atual.numero}: ${d.meta.entregues} de ${d.meta.total} entregue${d.meta.total === 1 ? "" : "s"}` : null;

  return (
    <>
      <Modal title={titulo} width={880} onClose={() => { if (!definindo) onClose(); }}>
        {erro && <ErrorNotice>{erro}</ErrorNotice>}
        {!d && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
        {d && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ border: `1px solid ${COR_STATUS[d.status]}`, borderRadius: 12, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <Chip tone={TOM_STATUS[d.status]} dot>{STATUS_INFO[d.status].nome}</Chip>
                <span style={{ fontSize: 13, color: ds.muted }}>{STATUS_INFO[d.status].regra}</span>
              </span>
              {d.sinais.length === 0 ? (
                <p style={{ margin: 0, fontSize: 14, color: ds.text2 }}>Nada pendente.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <span style={labelStyle}>O que está pendente</span>
                  <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
                    {d.sinais.map((s) => {
                      const pe = pendencia(s);
                      return (
                        <li key={s.codigo} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                          <span style={{ paddingTop: 6 }}><StatusDot tone={pe.tom} /></span>
                          <span style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                            <span style={{ fontSize: 14, fontWeight: 600, color: ds.white }}>{pe.titulo}</span>
                            <span style={{ fontSize: 13, lineHeight: 1.5, color: ds.muted }}>
                              {pe.explicacao}{pe.quem && <span style={{ color: ds.text2 }}> Quem resolve: {pe.quem}.</span>}
                            </span>
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>

            <Secao titulo={atual ? `Sprint ${atual.numero}` : "Sprint atual"}>
              <ProgressoSprint d={d} />
            </Secao>

            {atual && (
              <Secao titulo="O que foi planejado">
                <Planejamento d={d} />
              </Secao>
            )}

            {atual && (
              <Secao titulo="Tasks da sprint" extra={<span style={{ fontSize: 12.5, color: ds.muted }}>travadas e em andamento primeiro</span>}>
                <TasksDaSprint tasks={d.tasks} />
              </Secao>
            )}

            <Secao
              titulo={metaTexto ?? "Meta da sprint"}
              extra={<Button variant="primary" size="sm" onClick={() => setDefinindo(true)}>Definir meta</Button>}
            >
              {!metaTexto || d.meta.funcionalidades.length === 0 ? (
                <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Sem meta nesta sprint.</p>
              ) : (
                <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
                  {d.meta.funcionalidades.map((f) => (
                    <li key={f.id} style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", padding: "8px 0", borderTop: `1px solid ${ds.border}`, fontSize: 14, color: ds.text2 }}>
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

            <Secao titulo="Projeto">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8 }}>
                <Numero
                  label="Escopo × prazo"
                  dica="Quanto das funcionalidades foi aprovado, contra quanto do prazo do contrato já passou."
                  valor={d.numeros.sem_funcionalidades ? "sem funcionalidades" : d.numeros.prazo_sem_dados || d.numeros.pct_prazo == null || d.numeros.pct_escopo == null ? "sem datas" : `${Math.round(d.numeros.pct_escopo)}% · ${Math.round(d.numeros.pct_prazo)}%`}
                />
                <Numero label={d.sprint_atual && !d.sprint_atual.fechada ? "SPI da sprint atual (parcial)" : "SPI da sprint atual"} dica="Pontos concluídos ÷ pontos previstos." valor={d.numeros.spi_atual != null ? num(d.numeros.spi_atual) : "sem dado"} cor={d.numeros.spi_atual != null && d.sprint_atual?.fechada ? corDoSpi(d.numeros.spi_atual) : undefined} />
                <Numero label="SPI da última sprint fechada" valor={d.numeros.spi_ultima_fechada != null ? num(d.numeros.spi_ultima_fechada) : "sem dado"} cor={d.numeros.spi_ultima_fechada != null ? corDoSpi(d.numeros.spi_ultima_fechada) : undefined} />
                <Numero label="p85 tempo limpo" dica="85% das tasks dos últimos 30 dias levaram até este tempo de trabalho." valor={d.numeros.p85_horas != null ? `${Math.round(d.numeros.p85_horas)}h` : "sem dado"} />
              </div>
            </Secao>

            <Secao titulo="Sprint a sprint">
              {d.sprints.length === 0 ? <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>sem dado</p> : <SprintASprint sprints={d.sprints} />}
            </Secao>

            <Secao titulo={d.time.sprint_numero != null ? `Time · Sprint ${d.time.sprint_numero}` : "Time"}>
              {d.time.pessoas.length === 0 ? (
                <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Ninguém com task nesta sprint.</p>
              ) : (
                <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
                  {d.time.pessoas.map((p) => (
                    <li key={p.operacional_id} style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", padding: "8px 0", borderTop: `1px solid ${ds.border}`, fontSize: 14, color: ds.text2 }}>
                      <span style={{ fontWeight: 600, color: ds.white }} title={p.nome ?? undefined}>{p.nome ? nomeCurto(p.nome) : "Sem nome"}</span>
                      <span style={{ ...mono, marginLeft: "auto", color: ds.muted }}>{num(p.realizado, 1)} pts</span>
                      {p.piso == null
                        ? <span style={{ fontSize: 12.5, color: ds.muted }}>sem histórico para o piso</span>
                        : p.abaixo == null
                        ? <span style={{ fontSize: 12.5, color: ds.muted }}>piso {num(p.piso, 1)} · sprint em andamento</span>
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
