"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { listProjects, searchStack, type Project, type StackSearchResult, type Subarea } from "../lib/api";
import { ds, innerStyle } from "../lib/ds";
import { Card, EmptyState, ErrorNotice, PageHeader, StatusDot } from "../components/ds";
import ProjectListCard, { isStale } from "../components/projects/ProjectListCard";

const SUBAREA_COPY: Record<Subarea, { label: string; description: string }> = {
  dados: { label: "Dados", description: "Acompanhe sprints, decisões e documentação dos projetos de dados em um só lugar." },
  dev: { label: "Dev", description: "Centralize o contexto técnico, as decisões e a documentação dos projetos de desenvolvimento." },
};

function SubareaHome() {
  const { subarea } = useParams<{ subarea: Subarea }>();
  const queryFromUrl = (useSearchParams().get("q") ?? "").trim();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchQuery, setSearchQuery] = useState(queryFromUrl);
  const [searchResults, setSearchResults] = useState<StackSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setLoading(true);
    listProjects(subarea)
      .then(setProjects)
      .catch(() => setError("Não foi possível carregar os projetos."))
      .finally(() => setLoading(false));
  }, [subarea]);

  function runSearch(value: string, delay: number) {
    setSearchQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!value.trim()) { setSearchResults(null); return; }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await searchStack(value.trim(), subarea);
        setSearchResults(res.results);
      } catch { setSearchResults([]); }
      finally { setSearching(false); }
    }, delay);
  }

  // A busca da barra superior leva até aqui com ?q=: dispara a mesma busca por tecnologia.
  useEffect(() => {
    if (queryFromUrl) runSearch(queryFromUrl, 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryFromUrl, subarea]);

  function clearSearch() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setSearchQuery("");
    setSearchResults(null);
    setSearching(false);
  }

  const copy = SUBAREA_COPY[subarea] ?? SUBAREA_COPY.dados;
  const activeProjects = projects.filter((p) => !p.is_delivered).length;
  const deliveredProjects = projects.filter((p) => p.is_delivered).length;
  const attentionProjects = projects.filter(isStale).length;
  const statValue = (value: number) => (loading ? "—" : String(value));

  const stats = [
    { value: activeProjects, label: "Projetos ativos", tone: "green" as const },
    { value: deliveredProjects, label: "Entregues", tone: "neutral" as const },
    { value: attentionProjects, label: "Pedem atenção", tone: "red" as const },
  ];

  return (
    <>
      <PageHeader eyebrow={`Visão geral · ${copy.label}`} title={`Projetos de ${copy.label}`} subtitle={copy.description} />

      <Card>
        <div role="group" aria-label="Resumo dos projetos" aria-live="polite" style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
          {stats.map((stat, i) => (
            <div key={stat.label} style={{ borderLeft: i > 0 ? `1px solid ${ds.border}` : "none", padding: "22px 24px", display: "flex", alignItems: "center", gap: 16 }}>
              <StatusDot tone={stat.tone} />
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <span style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.03em", color: ds.white, lineHeight: 1 }}>{statValue(stat.value)}</span>
                <span style={{ fontSize: 13, color: ds.muted }}>{stat.label}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* BUSCA CROSS-PROJETO */}
      <section aria-labelledby="search-title" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16, flexWrap: "wrap" }}>
          <strong id="search-title" style={{ fontSize: 15, fontWeight: 600, color: ds.white }}>Busca entre projetos</strong>
          <span style={{ fontSize: 13, color: ds.muted }}>Encontre tecnologias utilizadas nesta subárea</span>
        </div>
        <div style={{ ...innerStyle, borderRadius: 10, height: 52, display: "flex", alignItems: "center", gap: 10, padding: "0 14px" }}>
          <label htmlFor="project-search" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>Buscar tecnologia nos projetos</label>
          <input
            id="project-search"
            type="text"
            placeholder="Busque por Python, Spark, React…"
            value={searchQuery}
            onChange={(e) => runSearch(e.target.value, 400)}
            style={{ flex: 1, minWidth: 0, background: "transparent", border: "none", outline: "none", color: ds.text2, fontSize: 15, fontFamily: "inherit" }}
          />
          {searching && <span style={{ fontSize: 12, color: ds.muted }}>Buscando…</span>}
          {searchQuery && (
            <button type="button" onClick={clearSearch} aria-label="Limpar busca" style={{ background: "none", border: "none", color: ds.muted, fontSize: 20, cursor: "pointer", lineHeight: 1 }}>×</button>
          )}
        </div>

        {searchQuery.trim() && searchResults !== null && (
          <Card style={{ overflow: "hidden" }}>
            {searchResults.length === 0 ? (
              <p style={{ padding: "16px 20px", color: ds.muted, fontSize: 14 }}>Nenhum projeto encontrou &quot;{searchQuery}&quot; na stack.</p>
            ) : (
              <>
                <p style={{ padding: "12px 20px 8px", fontFamily: ds.fontMono, fontSize: 11, letterSpacing: "0.16em", textTransform: "uppercase", color: ds.muted, borderBottom: `1px solid ${ds.border}` }}>
                  {searchResults.length} projeto{searchResults.length !== 1 ? "s" : ""} com &quot;{searchQuery}&quot;
                </p>
                {searchResults.map((r) => (
                  <Link key={r.project_id} href={`/${subarea}/projects/${r.project_id}`} className="ds-row-link" style={{ display: "block", padding: "14px 20px", borderBottom: `1px solid ${ds.border}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
                      <div>
                        <span style={{ fontWeight: 600, fontSize: 14, color: ds.text }}>{r.project_name}</span>
                        <span style={{ marginLeft: 8, fontSize: 13, color: ds.green, fontWeight: 500 }}>{r.client}</span>
                      </div>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
                        {r.sprints.map((s) => (
                          <span key={s} style={{ background: ds.greenSoft, color: ds.green, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600 }}>Sprint {s}</span>
                        ))}
                      </div>
                    </div>
                    {r.sample_context && (
                      <p style={{ marginTop: 6, fontSize: 13, color: ds.muted, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                        {r.sample_context}
                      </p>
                    )}
                  </Link>
                ))}
              </>
            )}
          </Card>
        )}
      </section>

      <section style={{ display: "flex", flexDirection: "column", gap: 12 }} aria-label="Todos os projetos">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: ds.white }}>Todos os projetos</h2>
          {!loading && <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{projects.length} projeto{projects.length !== 1 ? "s" : ""}</span>}
        </div>

        {loading && <p style={{ color: ds.muted }}>Carregando…</p>}
        {error && <ErrorNotice>{error}</ErrorNotice>}
        {!loading && !error && projects.length === 0 && <EmptyState>Nenhum projeto ainda. Crie o primeiro projeto para começar.</EmptyState>}

        {projects.map((p) => <ProjectListCard key={p.id} project={p} subarea={subarea} />)}
      </section>
    </>
  );
}

export default function Home() {
  return (
    <Suspense fallback={null}>
      <SubareaHome />
    </Suspense>
  );
}

