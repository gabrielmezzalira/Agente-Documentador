"use client";

import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { useAuth } from "../components/AuthGuard";
import { Button, Card, Chip, EmptyState, ErrorNotice, Field, Modal, PageHeader, Select, SegmentedControl, TabSectionHead, Textarea } from "../components/ds";
import { ds, labelStyle } from "../lib/ds";
import { NIVEIS, rotuloNivel } from "../lib/regua";
import {
  definirExclusaoAprendizado,
  getClassificadorResumo,
  getClassificadorRevisao,
  getClassificadorTask,
  reclassificarTask,
  resolverRevisaoNivel,
  type ClassificadorOpiniao,
  type ClassificadorResumo,
  type ClassificadorRevisaoItem,
  type ClassificadorTaskDetalhe,
} from "../lib/api";

type Periodo = "30" | "90" | "tudo";

const PERIODOS: { value: Periodo; label: string }[] = [
  { value: "30", label: "30 dias" },
  { value: "90", label: "90 dias" },
  { value: "tudo", label: "Tudo" },
];

const th: CSSProperties = { ...labelStyle, textAlign: "left", padding: "8px 12px", borderBottom: `1px solid ${ds.border}`, fontWeight: 600 };
const td: CSSProperties = { padding: "10px 12px", borderBottom: `1px solid ${ds.border}`, fontSize: 13.5, color: ds.text2, verticalAlign: "top" };
const mono: CSSProperties = { fontFamily: ds.fontMono };

function pct(x: number | null | undefined): string {
  return x == null ? "—" : `${Math.round(x * 100)}%`;
}

function num(x: number | null | undefined, casas = 2): string {
  return x == null ? "—" : x.toLocaleString("pt-BR", { maximumFractionDigits: casas });
}

/** Segundos em "2d 4h", "3h 20min" ou "15min". Zero ou ausente vira "—". */
function duracao(s: number | null | undefined): string {
  if (!s || s <= 0) return "—";
  const min = Math.round(s / 60);
  if (min < 60) return `${Math.max(min, 1)}min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ${String(min % 60).padStart(2, "0")}min`;
  return `${Math.floor(h / 24)}d ${h % 24}h`;
}

function dataCurta(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleDateString("pt-BR") : "—";
}

function Tabela({ children, minWidth = 0 }: { children: ReactNode; minWidth?: number }) {
  return <div style={{ overflowX: "auto" }}><table style={{ width: "100%", minWidth, borderCollapse: "collapse" }}>{children}</table></div>;
}

function Bloco({ titulo, descricao, children, actions }: { titulo: string; descricao?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section aria-label={titulo} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <TabSectionHead title={titulo} description={descricao} actions={actions} />
      {children}
    </section>
  );
}

function Subtitulo({ children }: { children: ReactNode }) {
  return <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: ds.white }}>{children}</h3>;
}

function Numero({ label, valor }: { label: string; valor: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={labelStyle}>{label}</span>
      <span style={{ ...mono, fontSize: 28, fontWeight: 700, color: ds.white }}>{valor}</span>
    </div>
  );
}

/** Diálogo de motivo obrigatório para tirar uma task da contagem. */
function ExclusaoModal({ titulo, onClose, onConfirm }: { titulo: string; onClose: () => void; onConfirm: (motivo: string) => Promise<void> }) {
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  async function confirmar() {
    setEnviando(true);
    setErro("");
    try {
      await onConfirm(motivo.trim());
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao tirar da contagem");
      setEnviando(false);
    }
  }
  return (
    <Modal
      title="Tirar da contagem"
      width={520}
      onClose={onClose}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancelar</Button>
        <Button variant="danger" disabled={!motivo.trim() || enviando} onClick={confirmar}>{enviando ? "Salvando..." : "Tirar da contagem"}</Button>
      </>}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <p style={{ margin: 0, fontSize: 14, color: ds.text2 }}>{titulo}</p>
        <Field label="Motivo" htmlFor="motivo-exclusao" required hint="A task deixa de entrar nas médias e no aprendizado. Dá para devolver depois.">
          <Textarea id="motivo-exclusao" rows={3} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        </Field>
        {erro && <ErrorNotice>{erro}</ErrorNotice>}
      </div>
    </Modal>
  );
}

/** Detalhe de uma task da fila de revisão: as três leituras, sinais, parecidas, combinado e ajuste. */
function RevisaoModal({ item, onClose, onFeito }: { item: ClassificadorRevisaoItem; onClose: () => void; onFeito: () => void }) {
  const [det, setDet] = useState<ClassificadorTaskDetalhe | null>(null);
  const [erro, setErro] = useState("");
  const [nivel, setNivel] = useState<number>(NIVEIS[0]);
  const [motivo, setMotivo] = useState("");
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    getClassificadorTask(item.task_id).then((d) => {
      setDet(d);
      if ((NIVEIS as readonly number[]).includes(d.classificacao.nivel_final)) setNivel(d.classificacao.nivel_final);
    }).catch((e: Error) => setErro(e.message));
  }, [item.task_id]);

  async function executar(fn: () => Promise<unknown>) {
    setOcupado(true);
    setErro("");
    try {
      await fn();
      onFeito();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao salvar");
      setOcupado(false);
    }
  }

  const c = det?.classificacao;
  const leituras: { label: string; valor: number | null | undefined }[] = c ? [
    { label: "Pelos sinais", valor: c.nivel_sinais },
    { label: "Pelas parecidas", valor: c.nivel_parecidas },
    { label: "Geral", valor: c.nivel_geral },
  ] : [];

  return (
    <Modal
      title={item.titulo ?? "Task sem título"}
      width={760}
      onClose={onClose}
      footer={<Button variant="secondary" disabled={ocupado} onClick={() => executar(() => reclassificarTask(item.task_id))}>Reclassificar</Button>}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {erro && <ErrorNotice>{erro}</ErrorNotice>}
        {!c && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
        {c && (
          <>
            {c.motivo_revisao && <p style={{ margin: 0, fontSize: 14, color: ds.amber }}>{c.motivo_revisao}</p>}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
              {leituras.map((l) => (
                <div key={l.label} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={labelStyle}>{l.label}</span>
                  <span style={{ fontSize: 15, color: ds.white }}>{l.valor != null ? rotuloNivel(l.valor) : "—"}</span>
                </div>
              ))}
            </div>
            {c.justificativa_geral && <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: ds.text2 }}>{c.justificativa_geral}</p>}

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Subtitulo>Sinais</Subtitulo>
              {c.sinais && Object.keys(c.sinais).length > 0 ? (
                <Tabela minWidth={480}>
                  <thead><tr><th style={th}>Sinal</th><th style={th}>Nota</th><th style={th}>Evidência citada</th></tr></thead>
                  <tbody>
                    {Object.entries(c.sinais).map(([s, v]) => (
                      <tr key={s}>
                        <td style={td}>{s}</td>
                        <td style={{ ...td, ...mono }}>{v.nota}</td>
                        <td style={{ ...td, fontStyle: v.evidencia ? "italic" : "normal", color: v.evidencia ? ds.text2 : ds.dim }}>{v.evidencia ? `“${v.evidencia}”` : "sem evidência"}</td>
                      </tr>
                    ))}
                  </tbody>
                </Tabela>
              ) : <span style={{ fontSize: 13, color: ds.muted }}>Sem sinais registrados.</span>}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Subtitulo>Tasks parecidas</Subtitulo>
              {c.parecidas && c.parecidas.length > 0 ? (
                <Tabela minWidth={480}>
                  <thead><tr><th style={th}>Task</th><th style={th}>Similaridade</th><th style={th}>Nível real</th><th style={th}>Tempo</th></tr></thead>
                  <tbody>
                    {c.parecidas.map((p) => (
                      <tr key={p.task_id}>
                        <td style={td}>{p.titulo ?? "—"}</td>
                        <td style={{ ...td, ...mono }}>{pct(p.similaridade)}</td>
                        <td style={td}>{rotuloNivel(p.nivel_real)}</td>
                        <td style={{ ...td, ...mono }}>{duracao(p.tempo_normalizado_s)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Tabela>
              ) : <span style={{ fontSize: 13, color: ds.muted }}>Nenhuma parecida encontrada.</span>}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={labelStyle}>Opinião do gerente</span>
                <span style={{ fontSize: 15, color: ds.white }}>{c.opiniao_gerente != null ? rotuloNivel(c.opiniao_gerente) : "sem opinião"}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={labelStyle}>Combinado</span>
                <span style={{ fontSize: 15, color: ds.white }}>{c.nivel_combinado != null ? rotuloNivel(c.nivel_combinado) : "—"}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={labelStyle}>Ajuste</span>
                <span style={{ ...mono, fontSize: 15, color: ds.white }}>{c.ajuste_tempo > 0 ? `+${c.ajuste_tempo}` : c.ajuste_tempo}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={labelStyle}>Nível final</span>
                <span style={{ fontSize: 15, color: ds.white }}>{rotuloNivel(c.nivel_final)}</span>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12, paddingTop: 16, borderTop: `1px solid ${ds.border}` }}>
              <Subtitulo>Resolver</Subtitulo>
              <Field label="Nível" htmlFor="resolver-nivel">
                <Select id="resolver-nivel" value={nivel} onChange={(e) => setNivel(Number(e.target.value))}>
                  {NIVEIS.map((n) => <option key={n} value={n}>{rotuloNivel(n)}</option>)}
                </Select>
              </Field>
              <Field label="Motivo" htmlFor="resolver-motivo" required hint="Mínimo de 3 caracteres.">
                <Textarea id="resolver-motivo" rows={2} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
              </Field>
              <div>
                <Button variant="primary" disabled={ocupado || motivo.trim().length < 3} onClick={() => executar(() => resolverRevisaoNivel(item.task_id, nivel, motivo.trim()))}>Resolver</Button>
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}

function TabelaOpinioes({ titulo, linhas }: { titulo: string; linhas: ClassificadorOpiniao[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <Subtitulo>{titulo}</Subtitulo>
      {linhas.length === 0 ? <span style={{ fontSize: 13, color: ds.muted }}>Sem opiniões suficientes ainda.</span> : (
        <Tabela minWidth={360}>
          <thead><tr><th style={th}>Pessoa</th><th style={th}>Peso</th><th style={th}>Acurácia</th><th style={th}>N</th></tr></thead>
          <tbody>
            {linhas.map((o) => (
              <tr key={o.pessoa_id}>
                <td style={td}>{o.nome ?? "—"}</td>
                <td style={{ ...td, ...mono }}>{num(o.peso)}</td>
                <td style={{ ...td, ...mono }}>{pct(o.acuracia)}</td>
                <td style={{ ...td, ...mono }}>{o.n}</td>
              </tr>
            ))}
          </tbody>
        </Tabela>
      )}
    </div>
  );
}

export default function ClassificadorPage() {
  const auth = useAuth();
  const permitido = !auth || auth.cargo === "lider" || auth.cargo === "owner";

  const [periodo, setPeriodo] = useState<Periodo>("tudo");
  const [gerenteId, setGerenteId] = useState("");
  const [resumo, setResumo] = useState<ClassificadorResumo | null>(null);
  const [fila, setFila] = useState<ClassificadorRevisaoItem[] | null>(null);
  const [erro, setErro] = useState("");
  const [aba, setAba] = useState<"alertas" | "excluidas">("alertas");
  const [mantidas, setMantidas] = useState<Set<string>>(new Set());
  const [excluindo, setExcluindo] = useState<{ id: string; titulo: string } | null>(null);
  const [aberta, setAberta] = useState<ClassificadorRevisaoItem | null>(null);
  const [erroAcao, setErroAcao] = useState("");

  const carregarResumo = useCallback(() => {
    getClassificadorResumo(periodo, gerenteId || undefined).then((r) => { setResumo(r); setErro(""); }).catch((e: Error) => setErro(e.message));
  }, [periodo, gerenteId]);
  const carregarFila = useCallback(() => {
    getClassificadorRevisao().then(setFila).catch((e: Error) => setErro(e.message));
  }, []);

  useEffect(() => {
    if (!auth || !permitido) return;
    carregarResumo();
  }, [auth, permitido, carregarResumo]);
  useEffect(() => {
    if (!auth || !permitido) return;
    carregarFila();
  }, [auth, permitido, carregarFila]);

  if (!permitido) return <ErrorNotice>Acesso restrito a Líder e Owner.</ErrorNotice>;

  async function devolver(taskId: string) {
    setErroAcao("");
    try {
      await definirExclusaoAprendizado(taskId, false);
      carregarResumo();
    } catch (e) {
      setErroAcao(e instanceof Error ? e.message : "Erro ao devolver à contagem");
    }
  }

  const alertas = (resumo?.alertas ?? []).filter((a) => !mantidas.has(a.task_id));
  const semanas = Array.from(new Set((resumo?.evolucao_medias ?? []).map((e) => e.semana))).sort();
  const datasPesos = Array.from(new Set((resumo?.evolucao_pesos ?? []).map((e) => e.data))).sort().slice(-12);
  const sinais = Array.from(new Set((resumo?.evolucao_pesos ?? []).map((e) => e.sinal))).sort();
  const ac = resumo?.acuracia;

  return (
    <>
      <PageHeader
        eyebrow="Leitura restrita a líderes"
        title="Classificador"
        subtitle="Como o classificador de nível se comporta contra o tempo real das tasks concluídas."
      />

      {erro && <ErrorNotice>{erro}</ErrorNotice>}
      {erroAcao && <ErrorNotice>{erroAcao}</ErrorNotice>}
      {!resumo && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}

      {resumo && (
        <>
          <Bloco titulo="Tempo típico por nível" descricao="Tempo normalizado das tasks concluídas, por nível real. A média sem excluídas é a usada pelo classificador.">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
              {resumo.medias.map((m) => (
                <Card key={m.nivel} style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                  <span style={{ fontSize: 15, fontWeight: 600, color: ds.white }}>{rotuloNivel(m.nivel)}</span>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={labelStyle}>Média</span><span style={mono}>{duracao(m.media_s)}</span></div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={labelStyle}>Média sem excluídas</span><span style={mono}>{duracao(m.media_sem_excluidas_s)}</span></div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span style={labelStyle}>N tasks</span><span style={mono}>{m.n}</span></div>
                </Card>
              ))}
            </div>
            <Card style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
              <Subtitulo>Evolução semanal da média</Subtitulo>
              {semanas.length === 0 ? <span style={{ fontSize: 13, color: ds.muted }}>Ainda sem histórico semanal.</span> : (
                <Tabela minWidth={420}>
                  <thead><tr><th style={th}>Semana</th>{NIVEIS.map((n) => <th key={n} style={th}>{rotuloNivel(n)}</th>)}</tr></thead>
                  <tbody>
                    {semanas.slice(-12).map((s) => (
                      <tr key={s}>
                        <td style={{ ...td, ...mono }}>{dataCurta(s)}</td>
                        {NIVEIS.map((n) => {
                          const e = resumo.evolucao_medias.find((x) => x.semana === s && x.nivel === n);
                          return <td key={n} style={{ ...td, ...mono }}>{e ? duracao(e.media_s) : "—"}</td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </Tabela>
              )}
            </Card>
          </Bloco>

          <Bloco
            titulo="Tasks em alerta"
            descricao="Tasks concluídas com tempo muito distante da média do nível. Tirar da contagem evita que distorçam as médias."
            actions={<SegmentedControl label="Lista" value={aba} onChange={setAba} options={[{ value: "alertas", label: `Em alerta (${alertas.length})` }, { value: "excluidas", label: `Excluídas (${resumo.excluidas.length})` }]} />}
          >
            {aba === "alertas" ? (
              alertas.length === 0 ? <EmptyState>Nenhuma task em alerta.</EmptyState> : (
                <Card style={{ padding: 8 }}>
                  <Tabela minWidth={760}>
                    <thead><tr><th style={th}>Task</th><th style={th}>Projeto</th><th style={th}>Operacional</th><th style={th}>Tempo</th><th style={th}>Média do nível</th><th style={th}>Ações</th></tr></thead>
                    <tbody>
                      {alertas.map((a) => (
                        <tr key={a.task_id}>
                          <td style={td}>{a.titulo ?? "—"}<div style={{ marginTop: 4 }}><Chip tone="neutral">{rotuloNivel(a.nivel_real)}</Chip></div></td>
                          <td style={td}>{a.projeto ?? "—"}</td>
                          <td style={td}>{a.operacional ?? "—"}</td>
                          <td style={{ ...td, ...mono }}>{duracao(a.tempo_normalizado_s)}</td>
                          <td style={{ ...td, ...mono }}>{duracao(a.media_nivel_s)}</td>
                          <td style={td}>
                            <div style={{ display: "flex", gap: 8 }}>
                              <Button size="sm" variant="danger" onClick={() => setExcluindo({ id: a.task_id, titulo: a.titulo ?? "Task sem título" })}>Tirar da contagem</Button>
                              <Button size="sm" variant="ghost" onClick={() => setMantidas((s) => new Set(s).add(a.task_id))}>Manter</Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Tabela>
                </Card>
              )
            ) : (
              resumo.excluidas.length === 0 ? <EmptyState>Nenhuma task excluída da contagem.</EmptyState> : (
                <Card style={{ padding: 8 }}>
                  <Tabela minWidth={620}>
                    <thead><tr><th style={th}>Task</th><th style={th}>Motivo</th><th style={th}>Excluída em</th><th style={th}>Ação</th></tr></thead>
                    <tbody>
                      {resumo.excluidas.map((e) => (
                        <tr key={e.task_id}>
                          <td style={td}>{e.titulo ?? "—"}</td>
                          <td style={td}>{e.motivo_exclusao ?? "—"}</td>
                          <td style={{ ...td, ...mono }}>{dataCurta(e.excluida_em)}</td>
                          <td style={td}><Button size="sm" variant="secondary" onClick={() => devolver(e.task_id)}>Devolver à contagem</Button></td>
                        </tr>
                      ))}
                    </tbody>
                  </Tabela>
                </Card>
              )
            )}
          </Bloco>

          <Bloco
            titulo="Acurácia contra o tempo real"
            descricao="Nível sugerido no momento da criação contra o nível que o tempo real indicou."
            actions={
              <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
                <SegmentedControl label="Período" options={PERIODOS} value={periodo} onChange={setPeriodo} />
                <Field label="Gerente" htmlFor="filtro-gerente">
                  <Select id="filtro-gerente" value={gerenteId} onChange={(e) => setGerenteId(e.target.value)} style={{ height: 40, minWidth: 180 }}>
                    <option value="">Todos</option>
                    {resumo.gerentes.map((g) => <option key={g.id} value={g.id}>{g.nome ?? g.id}</option>)}
                  </Select>
                </Field>
              </div>
            }
          >
            {!ac || ac.n === 0 ? <EmptyState>Nenhuma task concluída neste filtro.</EmptyState> : (
              <>
                <Card style={{ padding: 20, display: "flex", gap: 40, flexWrap: "wrap" }}>
                  <Numero label="Acurácia" valor={pct(ac.exata)} />
                  <Numero label="Acurácia ±1" valor={pct(ac.mais_menos_um)} />
                  <Numero label="Erro médio (degraus)" valor={num(ac.erro_medio_degraus)} />
                  <Numero label="Tasks" valor={String(ac.n)} />
                </Card>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 }}>
                  <Card style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                    <Subtitulo>Matriz de confusão</Subtitulo>
                    <Tabela minWidth={320}>
                      <thead><tr><th style={th}>Sugerido \ Real</th>{NIVEIS.map((n) => <th key={n} style={{ ...th, textAlign: "right" }}>{n}</th>)}</tr></thead>
                      <tbody>
                        {NIVEIS.map((s) => (
                          <tr key={s}>
                            <td style={{ ...td, ...mono }}>{s}</td>
                            {NIVEIS.map((r) => {
                              const v = ac.matriz[String(s)]?.[String(r)] ?? 0;
                              return <td key={r} style={{ ...td, ...mono, textAlign: "right", color: v === 0 ? ds.dim : s === r ? ds.green : ds.text, fontWeight: s === r && v > 0 ? 700 : 400 }}>{v}</td>;
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </Tabela>
                  </Card>
                  <Card style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                    <Subtitulo>Precisão e cobertura por nível</Subtitulo>
                    <Tabela minWidth={320}>
                      <thead><tr><th style={th}>Nível</th><th style={th}>Precisão</th><th style={th}>Cobertura</th></tr></thead>
                      <tbody>
                        {NIVEIS.map((n) => (
                          <tr key={n}>
                            <td style={td}>{rotuloNivel(n)}</td>
                            <td style={{ ...td, ...mono }}>{pct(ac.por_nivel[String(n)]?.precisao)}</td>
                            <td style={{ ...td, ...mono }}>{pct(ac.por_nivel[String(n)]?.cobertura)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </Tabela>
                  </Card>
                </div>
                <Card style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                  <Subtitulo>Evolução mensal (±1)</Subtitulo>
                  <Tabela minWidth={320}>
                    <thead><tr><th style={th}>Mês</th><th style={th}>Acurácia ±1</th><th style={th}>Tasks</th></tr></thead>
                    <tbody>
                      {resumo.evolucao_acuracia.map((e) => (
                        <tr key={e.mes}><td style={{ ...td, ...mono }}>{e.mes}</td><td style={{ ...td, ...mono }}>{pct(e.mais_menos_um)}</td><td style={{ ...td, ...mono }}>{e.n}</td></tr>
                      ))}
                    </tbody>
                  </Tabela>
                </Card>
              </>
            )}
          </Bloco>

          <Bloco titulo="Por que o classificador decide assim" descricao="Parâmetros que o classificador aprendeu com as tasks concluídas.">
            <p role="note" style={{ margin: 0, fontSize: 13.5, color: ds.amber }}>Ajuste interno, não é nota de desempenho.</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 }}>
              <Card style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                <Subtitulo>Pesos dos sinais</Subtitulo>
                {resumo.pesos_sinais.length === 0 ? <span style={{ fontSize: 13, color: ds.muted }}>Ainda sem pesos aprendidos.</span> : (
                  <Tabela minWidth={240}>
                    <thead><tr><th style={th}>Sinal</th><th style={th}>Peso</th></tr></thead>
                    <tbody>{resumo.pesos_sinais.map((p) => <tr key={p.sinal}><td style={td}>{p.sinal}</td><td style={{ ...td, ...mono }}>{num(p.peso)}</td></tr>)}</tbody>
                  </Tabela>
                )}
                {datasPesos.length > 0 && (
                  <>
                    <Subtitulo>Evolução dos pesos</Subtitulo>
                    <Tabela minWidth={420}>
                      <thead><tr><th style={th}>Data</th>{sinais.map((s) => <th key={s} style={th}>{s}</th>)}</tr></thead>
                      <tbody>
                        {datasPesos.map((d) => (
                          <tr key={d}>
                            <td style={{ ...td, ...mono }}>{dataCurta(d)}</td>
                            {sinais.map((s) => {
                              const e = resumo.evolucao_pesos.find((x) => x.data === d && x.sinal === s);
                              return <td key={s} style={{ ...td, ...mono }}>{e ? num(e.peso) : "—"}</td>;
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </Tabela>
                  </>
                )}
              </Card>
              <Card style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
                <Subtitulo>Viés por gerente</Subtitulo>
                {resumo.vies_gerentes.length === 0 ? <span style={{ fontSize: 13, color: ds.muted }}>Sem viés calculado ainda.</span> : (
                  <Tabela minWidth={280}>
                    <thead><tr><th style={th}>Gerente</th><th style={th}>Viés (degraus)</th><th style={th}>N</th></tr></thead>
                    <tbody>{resumo.vies_gerentes.map((v) => <tr key={v.gerente_id}><td style={td}>{v.nome ?? "—"}</td><td style={{ ...td, ...mono }}>{num(v.vies)}</td><td style={{ ...td, ...mono }}>{v.n}</td></tr>)}</tbody>
                  </Tabela>
                )}
                <Subtitulo>Ritmos</Subtitulo>
                {resumo.ritmos.length === 0 ? <span style={{ fontSize: 13, color: ds.muted }}>Sem ritmos calculados ainda.</span> : (
                  <Tabela minWidth={280}>
                    <thead><tr><th style={th}>Pessoa</th><th style={th}>Ritmo</th><th style={th}>N</th></tr></thead>
                    <tbody>{resumo.ritmos.map((r) => <tr key={r.pessoa_id}><td style={td}>{r.nome ?? "—"}</td><td style={{ ...td, ...mono }}>{num(r.ritmo)}</td><td style={{ ...td, ...mono }}>{r.n}</td></tr>)}</tbody>
                  </Tabela>
                )}
              </Card>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 }}>
              <Card style={{ padding: 20 }}><TabelaOpinioes titulo="Opiniões dos gerentes" linhas={resumo.opinioes.gerentes} /></Card>
              <Card style={{ padding: 20 }}><TabelaOpinioes titulo="Opiniões dos operacionais" linhas={resumo.opinioes.operacionais} /></Card>
            </div>
          </Bloco>
        </>
      )}

      <Bloco titulo="Fila de revisão" descricao="Tasks cuja classificação está em revisão ou ainda é provisória.">
        {!fila && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
        {fila && fila.length === 0 && <EmptyState>Nenhuma task aguardando revisão.</EmptyState>}
        {fila && fila.length > 0 && (
          <Card style={{ padding: 8 }}>
            <Tabela minWidth={620}>
              <thead><tr><th style={th}>Task</th><th style={th}>Projeto</th><th style={th}>Situação</th><th style={th}>Nível</th><th style={th}>Ação</th></tr></thead>
              <tbody>
                {fila.map((f) => (
                  <tr key={f.task_id}>
                    <td style={td}>{f.titulo ?? "—"}{f.motivo_revisao && <div style={{ marginTop: 4, fontSize: 12.5, color: ds.muted }}>{f.motivo_revisao}</div>}</td>
                    <td style={td}>{f.projeto ?? "—"}</td>
                    <td style={td}><Chip tone={f.status === "em_revisao" ? "amber" : "neutral"}>{f.status === "em_revisao" ? "Em revisão" : "Provisória"}</Chip></td>
                    <td style={td}>{f.nivel_final != null ? rotuloNivel(f.nivel_final) : "—"}</td>
                    <td style={td}><Button size="sm" variant="secondary" onClick={() => setAberta(f)}>Abrir</Button></td>
                  </tr>
                ))}
              </tbody>
            </Tabela>
          </Card>
        )}
      </Bloco>

      {excluindo && (
        <ExclusaoModal
          titulo={excluindo.titulo}
          onClose={() => setExcluindo(null)}
          onConfirm={async (motivo) => {
            await definirExclusaoAprendizado(excluindo.id, true, motivo);
            setExcluindo(null);
            carregarResumo();
          }}
        />
      )}
      {aberta && <RevisaoModal item={aberta} onClose={() => setAberta(null)} onFeito={() => { setAberta(null); carregarFila(); carregarResumo(); }} />}
    </>
  );
}
