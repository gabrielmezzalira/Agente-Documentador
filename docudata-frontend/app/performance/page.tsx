"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { Card, Chip, EmptyState, ErrorNotice, PageHeader, SegmentedControl } from "../components/ds";
import { ds, labelStyle } from "../lib/ds";
import { getPerformance, type PerformanceResponse, type PerformanceOperacional } from "../lib/api";

type Janela = "sprint" | "quinzenal" | "mensal";

const JANELAS: { value: Janela; label: string }[] = [
  { value: "sprint", label: "Última sprint" },
  { value: "quinzenal", label: "Últimas 2 sprints" },
  { value: "mensal", label: "Últimas 4 sprints" },
];

const DIMENSOES = [
  { key: "entrega", label: "Entrega" },
  { key: "gerente", label: "Gerente" },
  { key: "qualidade", label: "Qualidade" },
  { key: "autonomia", label: "Autonomia" },
] as const;

function fmt(n: number): string {
  return n.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

/** Dimensão: rótulo mono, valor e barra. Sem dado fica "—" apagado (não vira zero). */
function Dimensao({ label, valor }: { label: string; valor: number | null | undefined }) {
  const tem = valor != null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
      <span style={labelStyle}>{label}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontFamily: ds.fontMono, fontSize: 15, fontWeight: 600, color: tem ? ds.white : ds.dim, width: 44 }}>{tem ? fmt(valor) : "—"}</span>
        <div aria-hidden="true" style={{ flex: 1, height: 5, borderRadius: 3, background: "rgba(255,255,255,0.07)", overflow: "hidden" }}>
          {tem && <div style={{ width: `${Math.max(0, Math.min(100, valor))}%`, height: "100%", background: ds.green }} />}
        </div>
      </div>
    </div>
  );
}

function PessoaCard({ op, posicao }: { op: PerformanceOperacional; posicao: number }) {
  const primeiro = posicao === 1;
  return (
    <Card style={primeiro ? { borderColor: ds.greenLine, boxShadow: "0 0 40px rgba(62,224,111,0.08)" } : undefined}>
      <div className="ds-perf-row" style={{ display: "grid", gridTemplateColumns: "52px 250px minmax(0,1fr) 120px", gap: 24, alignItems: "center", padding: "22px 28px" }}>
        <span style={{ fontFamily: ds.fontMono, fontSize: 22, fontWeight: 600, color: primeiro ? ds.green : ds.dim }}>{String(posicao).padStart(2, "0")}</span>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 8, minWidth: 0 }}>
          <span style={{ fontSize: 17, fontWeight: 600, color: ds.white }}>{op.nome}</span>
          {primeiro && <Chip tone="green" dot>Maior contribuição</Chip>}
          {op.janela_parcial && <Chip tone="amber">Janela parcial</Chip>}
        </div>
        <div className="ds-perf-dims" style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 20 }}>
          {DIMENSOES.map((d) => <Dimensao key={d.key} label={d.label} valor={op[d.key]} />)}
        </div>
        <span
          aria-label={`Nota final ${fmt(op.score_final)}`}
          style={{
            textAlign: "right", fontSize: 36, fontWeight: 700, letterSpacing: "-0.03em",
            color: primeiro ? ds.green : ds.white, textShadow: primeiro ? "0 0 24px rgba(62,224,111,0.45)" : "none",
          }}
        >
          {fmt(op.score_final)}
        </span>
      </div>
    </Card>
  );
}

export default function PerformancePage() {
  const auth = useAuth();
  const [janela, setJanela] = useState<Janela>("sprint");
  const [dados, setDados] = useState<PerformanceResponse | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!auth || (auth.cargo !== "lider" && auth.cargo !== "owner")) return;
    getPerformance()
      .then(setDados)
      .catch((e: Error) => setErro(e.message));
  }, [auth]);

  if (auth && auth.cargo !== "lider" && auth.cargo !== "owner") {
    return <ErrorNotice>Acesso restrito a Líder e Owner.</ErrorNotice>;
  }

  const projetos = dados?.projetos ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Leitura restrita a líderes e gerentes"
        title="Performance"
        subtitle="Contribuição no conjunto das dimensões, por projeto. Dimensão sem dado fica indisponível e não vira zero."
        actions={<SegmentedControl label="Janela de tempo" options={JANELAS} value={janela} onChange={setJanela} />}
      />

      {erro && <ErrorNotice>{erro}</ErrorNotice>}
      {!dados && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
      {dados && projetos.length === 0 && <EmptyState>Nenhum projeto com dado suficiente nesta janela.</EmptyState>}

      {projetos.map((projeto) => {
        const lista: PerformanceOperacional[] = projeto[janela];
        return (
          <section key={projeto.projeto_id} aria-label={projeto.projeto_nome} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
              <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", color: ds.white }}>{projeto.projeto_nome}</h2>
              <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{lista.length} {lista.length === 1 ? "pessoa" : "pessoas"}</span>
            </div>
            {lista.length === 0
              ? <EmptyState>Nenhum operacional com dado suficiente nesta janela.</EmptyState>
              : lista.map((op, i) => <PessoaCard key={op.email} op={op} posicao={i + 1} />)}
          </section>
        );
      })}
    </>
  );
}
