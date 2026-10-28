"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { useAuth } from "../components/AuthGuard";
import DefinirMetaModal from "../components/DefinirMetaModal";
import { Button, Card, Chip, EmptyState, ErrorNotice, PageHeader, ProgressBar, SegmentedControl } from "../components/ds";
import { ds, labelStyle } from "../lib/ds";
import {
  getAcompanhamento,
  getEventosMeta,
  type AcompanhamentoResponse,
  type AcompProjeto,
  type MetaEvento,
  type Subarea,
} from "../lib/api";

const SUBAREAS: { value: Subarea; label: string }[] = [
  { value: "dados", label: "Dados" },
  { value: "dev", label: "Dev" },
];

const mono: CSSProperties = { fontFamily: ds.fontMono };

function num(x: number, casas = 2): string {
  return x.toLocaleString("pt-BR", { maximumFractionDigits: casas });
}

function pluralProjetos(n: number): string {
  return `${n} ${n === 1 ? "projeto" : "projetos"}`;
}

function Contador({ label, valor }: { label: string; valor: string }) {
  return (
    <Card>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <span style={labelStyle}>{label}</span>
        <span style={{ ...mono, fontSize: 28, fontWeight: 700, color: ds.white }}>{valor}</span>
      </div>
    </Card>
  );
}

function Celula({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 150, flex: "1 1 150px" }}>
      <span style={labelStyle}>{titulo}</span>
      <div style={{ fontSize: 13.5, color: ds.text2, display: "flex", flexDirection: "column", gap: 4 }}>{children}</div>
    </div>
  );
}

function Historico({ sprintId }: { sprintId: string }) {
  const [eventos, setEventos] = useState<MetaEvento[] | null>(null);
  const [erro, setErro] = useState("");
  useEffect(() => {
    let vivo = true;
    getEventosMeta(sprintId)
      .then((e) => { if (vivo) setEventos(e); })
      .catch((e) => { if (vivo) setErro(e instanceof Error ? e.message : "Erro ao buscar o histórico da meta"); });
    return () => { vivo = false; };
  }, [sprintId]);
  if (erro) return <ErrorNotice>{erro}</ErrorNotice>;
  if (!eventos) return <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>;
  if (eventos.length === 0) return <p style={{ margin: 0, fontSize: 13, color: ds.muted }}>Nenhuma mudança registrada.</p>;
  return (
    <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: ds.text2 }}>
      {eventos.map((e, i) => (
        <li key={`${e.funcionalidade_id}-${e.criado_em}-${i}`}>
          {e.acao} · {e.titulo ?? "(funcionalidade removida)"} · {e.pessoa_nome ?? "—"} · {new Date(e.criado_em).toLocaleDateString("pt-BR")}
        </li>
      ))}
    </ul>
  );
}

function ProjetoLinha({ p, onMeta, versao }: { p: AcompProjeto; onMeta: (p: AcompProjeto) => void; versao: number }) {
  const [aberto, setAberto] = useState(false);
  const [historico, setHistorico] = useState(false);
  const meta = p.meta;
  const semMeta = meta.total === 0;
  const pe = p.prazo_escopo;

  return (
    <div style={{ borderTop: `1px solid ${ds.border}`, padding: "14px 0", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 180, flex: "1 1 180px" }}>
          <button
            type="button"
            aria-expanded={aberto}
            onClick={() => setAberto((a) => !a)}
            style={{ background: "none", border: "none", padding: 0, cursor: "pointer", textAlign: "left", fontFamily: "inherit", fontSize: 15, fontWeight: 600, color: ds.white }}
          >
            {aberto ? "▾" : "▸"} {p.nome ?? "Projeto"}
          </button>
          <span style={{ fontSize: 12.5, color: ds.muted }}>{p.cliente ?? "—"}</span>
          {p.riscos.length > 0 && (
            <>
              <span title={p.riscos.join("\n")} style={{ alignSelf: "flex-start" }}><Chip tone="red">em risco</Chip></span>
              <span style={{ fontSize: 12, color: ds.red }}>{p.riscos.join(" · ")}</span>
            </>
          )}
        </div>
        <Celula titulo="Meta">
          {semMeta ? <span style={{ color: ds.muted }}>sem meta</span> : (
            <>
              <span>{meta.entregues} de {meta.total}</span>
              <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                {meta.funcionalidades.map((f) => (
                  <ProgressBar key={f.id} pct={f.aprovada ? 100 : (f.pct_tasks ?? 0)} tone="green" height={4} label={f.id_funcional ?? f.titulo ?? "Funcionalidade"} />
                ))}
              </div>
            </>
          )}
        </Celula>
        <Celula titulo="Planejado">
          <span>{p.planejado.funcs_planejadas_entregues} de {p.planejado.funcs_planejadas} planejadas{p.planejado.spi != null ? ` · SPI ${num(p.planejado.spi)}` : ""}</span>
        </Celula>
        <Celula titulo="Prazo × escopo">
          {pe.sem_dados ? <span style={{ color: ds.muted }}>sem datas do contrato</span> : (
            <span>{Math.round(pe.pct_prazo_consumido ?? 0)}% do prazo · {Math.round(pe.pct_escopo_concluido ?? 0)}% entregue</span>
          )}
        </Celula>
        <Celula titulo="Saúde">
          <span>
            {p.saude.tasks_travadas} {p.saude.tasks_travadas === 1 ? "travada" : "travadas"} · WIP {p.saude.wip}
            {p.saude.p85_horas != null ? ` · p85 ${num(p.saude.p85_horas, 0)}h` : ""}
          </span>
        </Celula>
      </div>

      {aberto && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, paddingLeft: 12 }}>
          {!semMeta && (
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {meta.funcionalidades.map((f) => (
                <li key={f.id} style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", fontSize: 13.5, color: ds.text2 }}>
                  <span style={{ ...mono, color: ds.muted }}>{f.id_funcional ?? "—"}</span>
                  <span style={{ flex: "1 1 160px" }}>{f.titulo ?? "—"}</span>
                  <span style={{ color: ds.muted }}>{f.status ?? "—"}</span>
                  <span style={mono}>{f.pct_tasks != null ? `${Math.round(f.pct_tasks)}% tasks` : "— tasks"}</span>
                  {f.aprovada && <Chip tone="green">aprovada</Chip>}
                  {!f.planejada_na_sprint && <Chip tone="amber">fora do planejamento</Chip>}
                </li>
              ))}
            </ul>
          )}
          {p.planejadas_fora_da_meta.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", fontSize: 13, color: ds.muted }}>
              <span>Planejadas fora da meta:</span>
              {p.planejadas_fora_da_meta.map((f) => <Chip key={f.id}>{f.id_funcional ?? f.titulo ?? f.id}</Chip>)}
            </div>
          )}
          {p.ultima_fechada && (
            <span style={{ fontSize: 13, color: ds.muted }}>
              Última sprint fechada (S{p.ultima_fechada.numero}): meta {p.ultima_fechada.meta_entregues} de {p.ultima_fechada.meta_total}
              {p.ultima_fechada.spi != null ? ` · SPI ${num(p.ultima_fechada.spi)}` : ""}
            </span>
          )}
          <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
            <Button variant="secondary" onClick={() => onMeta(p)}>Definir meta</Button>
            {p.sprint_atual && (
              <button
                type="button"
                aria-expanded={historico}
                onClick={() => setHistorico((h) => !h)}
                style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", fontSize: 13, color: ds.green, textDecoration: "underline" }}
              >
                Histórico de mudanças da meta
              </button>
            )}
          </div>
          {historico && p.sprint_atual && <Historico key={versao} sprintId={p.sprint_atual.id} />}
        </div>
      )}
    </div>
  );
}

export default function AcompanhamentoPage() {
  const auth = useAuth();
  const permitido = !auth || auth.cargo === "lider" || auth.cargo === "owner";
  const [subarea, setSubarea] = useState<Subarea>("dados");
  const [dados, setDados] = useState<AcompanhamentoResponse | null>(null);
  const [erro, setErro] = useState("");
  const [modal, setModal] = useState<AcompProjeto | null>(null);
  const [versao, setVersao] = useState(0);

  const pedido = useRef(0); // só a resposta do pedido mais recente vale (ao alternar Dados/Dev)

  const carregar = useCallback(async () => {
    const meu = ++pedido.current;
    setErro("");
    try {
      const r = await getAcompanhamento(subarea);
      if (meu === pedido.current) setDados(r);
    } catch (e) {
      if (meu === pedido.current) setErro(e instanceof Error ? e.message : "Erro ao buscar o acompanhamento");
    }
  }, [subarea]);

  useEffect(() => {
    if (!permitido) return;
    setDados(null);
    void carregar();
  }, [permitido, carregar]);

  if (!permitido) return <ErrorNotice>Acesso restrito a Líder e Owner.</ErrorNotice>;

  const t = dados?.totais;

  return (
    <>
      <PageHeader
        eyebrow="Leitura restrita a líderes"
        title="Acompanhamento dos projetos"
        subtitle="Projetos agrupados por gerente: meta da sprint, planejado, prazo e saúde."
        actions={<SegmentedControl label="Subárea" options={SUBAREAS} value={subarea} onChange={setSubarea} />}
      />

      {erro && <ErrorNotice>{erro}</ErrorNotice>}
      {!dados && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}

      {dados && t && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            <Contador label="Projetos" valor={String(t.projetos)} />
            <Contador label="Em risco" valor={String(t.em_risco)} />
            <Contador label="Metas batidas" valor={`${t.metas_batidas} de ${t.metas_fechadas}`} />
          </div>

          {dados.grupos.length === 0 && <EmptyState>Nenhum projeto nesta subárea.</EmptyState>}

          {dados.grupos.map((g) => (
            <Card key={g.gerente.email ?? g.gerente.nome}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, paddingBottom: 12 }}>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: ds.white }}>{g.gerente.nome}</h2>
                <span style={{ fontSize: 13, color: ds.muted }}>
                  {pluralProjetos(g.resumo.projetos)} · {g.resumo.em_risco} em risco · metas batidas {g.resumo.metas_batidas} de {g.resumo.metas_fechadas} · {Math.round(g.resumo.pct_funcs_aprovadas)}% das funcionalidades aprovadas
                </span>
              </div>
              {g.projetos.map((p) => <ProjetoLinha key={p.id} p={p} onMeta={setModal} versao={versao} />)}
            </Card>
          ))}
        </>
      )}

      {modal && <DefinirMetaModal projeto={modal} onClose={() => setModal(null)} onSalvo={() => { setVersao((v) => v + 1); void carregar(); }} />}
    </>
  );
}
