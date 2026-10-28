"use client";

import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { useAuth } from "../components/AuthGuard";
import DispersaoPrazo from "../components/acompanhamento/DispersaoPrazo";
import MapaCalor from "../components/acompanhamento/MapaCalor";
import { Button, Card, Chip, EmptyState, ErrorNotice, PageHeader, SegmentedControl, Select, StatusDot } from "../components/ds";
import { ds, labelStyle, type Tone } from "../lib/ds";
import { getAcompanhamento, type AcompanhamentoResponse, type AcompGerente, type AcompStatus, type Subarea } from "../lib/api";

const SUBAREAS: { value: Subarea; label: string }[] = [
  { value: "dados", label: "Dados" },
  { value: "dev", label: "Dev" },
];

const TOM: Record<AcompStatus, Tone> = { critico: "red", atencao: "amber", sem_dados: "neutral", saudavel: "green" };

const STATUS_PALAVRA: Record<AcompStatus, string> = { critico: "crítico", atencao: "atenção", sem_dados: "faltam dados", saudavel: "saudável" };

const mono: CSSProperties = { fontFamily: ds.fontMono };

function num(x: number, casas = 2): string {
  return x.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function plural(n: number, um: string, varios: string): string {
  return `${n} ${n === 1 ? um : varios}`;
}

/** Variação em relação à sprint anterior: verde quando melhora, vermelho quando piora. `null` = sem base de comparação. */
function Variacao({ v, casas = 0 }: { v: number | null; casas?: number }) {
  if (v == null) return <span style={{ fontSize: 12.5, color: ds.muted }}>sem comparação</span>;
  if (Math.abs(v) < 0.5 * 10 ** -casas) return <span style={{ fontSize: 12.5, color: ds.muted }}>sem variação</span>;
  return (
    <span style={{ fontSize: 12.5, fontWeight: 600, color: v > 0 ? ds.green : ds.red }}>
      {v > 0 ? "▲" : "▼"} {num(Math.abs(v), casas)}
    </span>
  );
}

function Kpi({ label, valor, children }: { label: string; valor: string; children: ReactNode }) {
  return (
    <Card style={{ padding: 16 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <span style={labelStyle}>{label}</span>
        <span style={{ ...mono, fontSize: valor === "sem dado" ? 16 : 26, fontWeight: 700, color: valor === "sem dado" ? ds.muted : ds.white, lineHeight: 1.3 }}>{valor}</span>
        <span style={{ fontSize: 12.5, color: ds.muted }}>{children}</span>
      </div>
    </Card>
  );
}

function Bloco({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <Card>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: ds.white }}>{titulo}</h2>
        {children}
      </div>
    </Card>
  );
}

const linhaBotao: CSSProperties = {
  position: "relative", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", width: "100%", textAlign: "left",
  background: "none", border: "none", borderTop: `1px solid ${ds.border}`, padding: "10px 0", cursor: "pointer",
  fontFamily: "inherit", fontSize: 14, color: ds.text,
};

export default function AcompanhamentoPage() {
  const auth = useAuth();
  const permitido = !auth || auth.cargo === "lider" || auth.cargo === "owner";
  const [subarea, setSubarea] = useState<Subarea>("dados");
  const [gerente, setGerente] = useState(""); // "" = todos; "sem" = sem gerente; senão, e-mail
  const [dados, setDados] = useState<AcompanhamentoResponse | null>(null);
  const [gerentes, setGerentes] = useState<AcompGerente[]>([]); // sobrevive ao recarregar, para o select não esvaziar
  const [erro, setErro] = useState("");
  const [projetoAberto, setProjetoAberto] = useState<string | null>(null);

  const pedido = useRef(0); // só a resposta do pedido mais recente vale (ao mudar subárea ou gerente)

  const carregar = useCallback(async () => {
    const meu = ++pedido.current;
    setErro("");
    setDados(null);
    try {
      const r = await getAcompanhamento(subarea, gerente || undefined);
      if (meu === pedido.current) { setDados(r); setGerentes(r.gerentes); }
    } catch (e) {
      if (meu === pedido.current) setErro(e instanceof Error ? e.message : "Erro ao buscar o acompanhamento");
    }
  }, [subarea, gerente]);

  useEffect(() => {
    if (!permitido) return;
    void carregar();
  }, [permitido, carregar]);

  if (!permitido) return <ErrorNotice>Acesso restrito a Líder e Owner.</ErrorNotice>;

  const mudarSubarea = (s: Subarea) => { setSubarea(s); setGerente(""); setGerentes([]); setProjetoAberto(null); };
  const k = dados?.kpis;
  const aberto = projetoAberto ? dados?.projetos.find((p) => p.id === projetoAberto) : undefined;

  return (
    <>
      <PageHeader
        eyebrow="Leitura restrita a líderes"
        title="Acompanhamento dos projetos"
        subtitle="Saúde da carteira por sprint, e quem precisa de você."
        actions={
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <SegmentedControl label="Subárea" options={SUBAREAS} value={subarea} onChange={mudarSubarea} />
            <Select aria-label="Gerente" value={gerente} onChange={(e) => { setGerente(e.target.value); setProjetoAberto(null); }} style={{ width: "auto", minWidth: 190 }}>
              <option value="">Todos os gerentes</option>
              {gerentes.filter((g) => g.email).map((g) => <option key={g.email} value={g.email!}>{g.nome}</option>)}
              <option value="sem">Sem gerente</option>
            </Select>
          </div>
        }
      />

      {erro && <ErrorNotice>{erro}</ErrorNotice>}
      {!dados && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}

      {dados && k && (
        k.projetos === 0 ? <EmptyState>{gerente ? "Nenhum projeto com este filtro." : "Nenhum projeto nesta subárea."}</EmptyState> : (
          <>
            <div className="acomp-kpis" style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 12 }}>
              <style>{"@media (max-width: 900px){.acomp-kpis{grid-template-columns:repeat(2,minmax(0,1fr)) !important}}"}</style>
              <Kpi label="Projetos" valor={String(k.projetos)}>{k.criticos} {k.criticos === 1 ? "crítico" : "críticos"} · {k.atencao} atenção</Kpi>
              <Kpi label="Features entregues" valor={k.features_entregues != null ? String(k.features_entregues) : "sem dado"}>
                <Variacao v={k.features_entregues_var} />
              </Kpi>
              <Kpi label="SPI médio" valor={k.spi_medio != null ? num(k.spi_medio) : "sem dado"}>
                <Variacao v={k.spi_medio_var} casas={2} />
              </Kpi>
              <Kpi label="Metas batidas" valor={`${k.metas_batidas} de ${k.metas_fechadas}`}>
                {plural(k.projetos_sem_meta, "projeto sem meta", "projetos sem meta")}
              </Kpi>
              <Kpi label="Tasks travadas" valor={String(k.tasks_travadas)}>no momento</Kpi>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))", gap: 16, alignItems: "start" }}>
              <Bloco titulo="Precisa de você">
                {dados.fila.length === 0 ? (
                  <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Nenhum projeto precisa de atenção agora.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    {dados.fila.map((f) => (
                      <button key={f.projeto_id} type="button" onClick={() => setProjetoAberto(f.projeto_id)} style={linhaBotao}>
                        <StatusDot tone={TOM[f.status]} />
                        <span style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" }}>{STATUS_PALAVRA[f.status]}: </span>
                        <span style={{ fontWeight: 600, color: ds.white }}>{f.nome ?? "Projeto"}</span>
                        <span style={{ fontSize: 12.5, color: ds.muted }}>{f.gerente}</span>
                        <span style={{ display: "flex", gap: 6, flexWrap: "wrap", marginLeft: "auto" }}>
                          {f.motivos.map((m) => <Chip key={m} tone={TOM[f.status]}>{m}</Chip>)}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </Bloco>

              <Bloco titulo="Evolução por sprint">
                <MapaCalor mapa={dados.mapa} onAbrir={setProjetoAberto} />
              </Bloco>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))", gap: 16, alignItems: "start" }}>
              <Bloco titulo="Risco de prazo">
                <DispersaoPrazo dispersao={dados.dispersao} onAbrir={setProjetoAberto} />
              </Bloco>

              <Bloco titulo="Por gerente">
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {dados.por_gerente.map((g) => (
                    <button key={g.email ?? g.nome} type="button" onClick={() => { setGerente(g.email ?? "sem"); setProjetoAberto(null); }} style={{ ...linhaBotao, justifyContent: "space-between" }}>
                      <span style={{ fontWeight: 600, color: ds.white }}>{g.nome}</span>
                      <span style={{ fontSize: 12.5, color: ds.text2 }}>
                        {g.projetos} proj · <span style={{ color: g.criticos > 0 ? ds.red : undefined }}>{g.criticos} {g.criticos === 1 ? "crítico" : "críticos"}</span>
                        {" · "}<span style={{ color: g.atencao > 0 ? ds.amber : undefined }}>{g.atencao} atenção</span> · metas {g.metas_batidas}/{g.metas_fechadas}
                      </span>
                    </button>
                  ))}
                </div>
              </Bloco>
            </div>
          </>
        )
      )}

      {aberto && (
        <Card role="region" aria-label={`Detalhe de ${aberto.nome ?? "projeto"}`}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: ds.white }}>{aberto.nome ?? "Projeto"}</h2>
            <p style={{ margin: 0, fontSize: 14, color: ds.text2 }}>{aberto.diagnostico}</p>
            <div><Button variant="secondary" onClick={() => setProjetoAberto(null)}>Fechar</Button></div>
          </div>
        </Card>
      )}
    </>
  );
}
