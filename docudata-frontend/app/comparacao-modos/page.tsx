"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { Button, EmptyState, ErrorNotice, PageHeader } from "../components/ds";
import { BarGroups, ChartLegend } from "../components/metricas/Charts";
import { PanelCard } from "../components/painel/PanelCard";
import { ds } from "../lib/ds";
import {
  listProjects,
  getComparacaoModosEntreProjetos,
  type Project,
  type ComparacaoModoPonto,
} from "../lib/api";

export default function ComparacaoModosPage() {
  const auth = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selecionados, setSelecionados] = useState<string[]>([]);
  const [resultado, setResultado] = useState<ComparacaoModoPonto[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [buscou, setBuscou] = useState(false);

  useEffect(() => {
    if (!auth || (auth.cargo !== "lider" && auth.cargo !== "owner")) return;
    Promise.all([listProjects("dados"), listProjects("dev")])
      .then(([dados, dev]) => setProjects([...dados, ...dev]))
      .catch(() => setProjects([]));
  }, [auth]);

  function toggleProjeto(id: string) {
    setSelecionados((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));
    setBuscou(false);
    setResultado([]);
  }

  function buscar() {
    if (selecionados.length < 2) {
      setErro("Selecione ao menos 2 projetos.");
      return;
    }
    setLoading(true);
    setErro(null);
    getComparacaoModosEntreProjetos(selecionados)
      .then((r) => {
        setResultado(r);
        setBuscou(true);
      })
      .catch((err) => setErro(err instanceof Error ? err.message : "Erro ao comparar"))
      .finally(() => setLoading(false));
  }

  if (auth && auth.cargo !== "lider" && auth.cargo !== "owner") {
    return <ErrorNotice>Acesso restrito a Líder e Owner.</ErrorNotice>;
  }

  return (
    <>
      <PageHeader
        eyebrow="Leitura restrita a líderes"
        title="Comparação de modos"
        subtitle="Compare sprints fechadas de dois ou mais projetos, agrupadas pelo modo de trabalho e de avaliação vigente em cada fechamento."
      />

      <PanelCard label="Escolha 2 ou mais projetos" action={<span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{selecionados.length} selecionados</span>}>
        {projects.length === 0 ? (
          <EmptyState>Nenhum projeto de Dados ou Dev encontrado.</EmptyState>
        ) : (
          <div role="group" aria-label="Projetos para comparar" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {projects.map((p) => {
              const ativo = selecionados.includes(p.id);
              return (
                <button
                  key={p.id}
                  type="button"
                  aria-pressed={ativo}
                  onClick={() => toggleProjeto(p.id)}
                  style={{
                    display: "inline-flex", alignItems: "center", gap: 8, padding: "7px 12px", borderRadius: 999,
                    fontFamily: "inherit", fontSize: 13, fontWeight: 600, cursor: "pointer",
                    background: ativo ? ds.greenSoft : "rgba(255,255,255,0.04)",
                    color: ativo ? ds.green : ds.text2,
                    border: `1px solid ${ativo ? ds.greenLine : ds.border}`,
                  }}
                >
                  <span aria-hidden="true" style={{ width: 14, height: 14, borderRadius: 4, border: `1.5px solid ${ativo ? ds.green : ds.dim}`, background: ativo ? ds.green : "transparent", color: "#04120a", fontSize: 10, fontWeight: 800, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                    {ativo ? "✓" : ""}
                  </span>
                  {p.name}
                </button>
              );
            })}
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Button variant="primary" onClick={buscar} disabled={loading || selecionados.length < 2}>
            {loading ? "Comparando..." : "Comparar"}
          </Button>
          {erro && <span role="alert" style={{ fontSize: 13, color: ds.red }}>{erro}</span>}
        </div>
      </PanelCard>

      {buscou && resultado.length === 0 && !erro && (
        <EmptyState>Nenhuma sprint fechada encontrada para os projetos selecionados.</EmptyState>
      )}

      {resultado.length > 0 && (
        <PanelCard label="Resultado · SPI médio e entrega média por modo" action={<ChartLegend items={[{ label: "SPI médio", color: ds.chartGrey }, { label: "Entrega média", color: ds.green }]} />}>
          <BarGroups
            label="SPI médio e entrega média por modo"
            categories={resultado.map((r) => `${r.modo_trabalho}/${r.modo_avaliacao}`)}
            series={[
              { key: "spi", label: "SPI médio", color: ds.chartGrey, values: resultado.map((r) => r.spi_medio ?? 0) },
              { key: "ent", label: "Entrega média", color: ds.green, values: resultado.map((r) => r.entrega_media ?? 0) },
            ]}
          />
        </PanelCard>
      )}
    </>
  );
}
