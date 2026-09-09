"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { listProjects, searchStack, type Project, type StackSearchResult, type Subarea } from "../lib/api";
import styles from "./subarea.module.css";

const STALE_DAYS = 7;

function isStale(project: Project): boolean {
  if (project.is_delivered) return false;
  if (!project.last_ingestion_at) return true;
  const diff = Date.now() - new Date(project.last_ingestion_at).getTime();
  return diff > STALE_DAYS * 24 * 60 * 60 * 1000;
}

function ProjectCard({ p, subarea }: { p: Project; subarea: Subarea }) {
  const [expanded, setExpanded] = useState(false);
  const stale = isStale(p);

  return (
    <Link href={`/${subarea}/projects/${p.id}`}>
      <div style={{ ...cardStyle, borderColor: stale ? "#fecaca" : "#e8e8ed" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {stale && (
                <span style={staleDotStyle} title="Sem ingestão nos últimos 7 dias" />
              )}
              <h2 style={{ fontSize: 15, fontWeight: 600, color: "#111116" }}>{p.name}</h2>
              {p.is_delivered && (
                <span style={{ fontSize: 11, fontWeight: 700, color: "#9696a0", background: "#f0f0f4",
                  borderRadius: 4, padding: "2px 7px", letterSpacing: "0.04em" }}>
                  ENTREGUE
                </span>
              )}
            </div>
            <p style={{ marginTop: 4, fontSize: 13, color: "#22c55e", fontWeight: 500 }}>{p.client}</p>
            {p.description && (
              <>
                {expanded && (
                  <p style={{ color: "#9696a0", marginTop: 6, fontSize: 13, lineHeight: 1.5 }}>{p.description}</p>
                )}
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); setExpanded((v) => !v); }}
                  style={{ marginTop: 6, fontSize: 12, color: "#9696a0", background: "none", border: "none",
                    cursor: "pointer", padding: 0, fontWeight: 500 }}
                >
                  {expanded ? "▲ ocultar" : "▼ ver detalhes"}
                </button>
              </>
            )}
            {stale && (
              <p style={{ marginTop: 6, fontSize: 12, color: "#dc2626", fontWeight: 500 }}>
                Sem insumo nos últimos 7 dias
              </p>
            )}
          </div>
          <span style={{ color: "#b8b8c0", fontSize: 12, whiteSpace: "nowrap", marginLeft: 20, marginTop: 2 }}>
            {new Date(p.created_at).toLocaleDateString("pt-BR")}
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function Home() {
  const { subarea } = useParams<{ subarea: Subarea }>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<StackSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    listProjects(subarea)
      .then(setProjects)
      .catch(() => setError("Não foi possível carregar os projetos."))
      .finally(() => setLoading(false));
  }, [subarea]);

  function handleSearchChange(value: string) {
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
    }, 400);
  }

  function clearSearch() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setSearchQuery("");
    setSearchResults(null);
    setSearching(false);
  }

  const subareaLabel = subarea === "dev" ? "Dev" : "Dados";
  const activeProjects = projects.filter((project) => !project.is_delivered).length;
  const deliveredProjects = projects.filter((project) => project.is_delivered).length;
  const attentionProjects = projects.filter(isStale).length;
  const statValue = (value: number) => loading ? "—" : String(value);

  return (
    <main className={styles.page}>
      <section className={styles.hero} aria-labelledby="subarea-title">
        <span className={styles.eyebrow}>Visão geral · {subareaLabel}</span>
        <h1 id="subarea-title">Projetos de {subareaLabel}</h1>
        <p className={styles.heroDescription}>
          {subarea === "dev"
            ? "Centralize o contexto técnico, as decisões e a documentação dos projetos de desenvolvimento."
            : "Acompanhe sprints, decisões e documentação dos projetos de dados em um só lugar."}
        </p>

        <div className={styles.stats} aria-label="Resumo dos projetos" aria-live="polite">
          <div className={styles.stat}>
            <span className={styles.statIcon} aria-hidden="true" />
            <span className={styles.statCopy}>
              <strong className={styles.statValue}>{statValue(activeProjects)}</strong>
              <span className={styles.statLabel}>Projetos ativos</span>
            </span>
          </div>
          <div className={`${styles.stat} ${styles.statDelivered}`}>
            <span className={styles.statIcon} aria-hidden="true" />
            <span className={styles.statCopy}>
              <strong className={styles.statValue}>{statValue(deliveredProjects)}</strong>
              <span className={styles.statLabel}>Entregues</span>
            </span>
          </div>
          <div className={`${styles.stat} ${styles.statAttention}`}>
            <span className={styles.statIcon} aria-hidden="true" />
            <span className={styles.statCopy}>
              <strong className={styles.statValue}>{statValue(attentionProjects)}</strong>
              <span className={styles.statLabel}>Pedem atenção</span>
            </span>
          </div>
        </div>
      </section>

      {/* BUSCA CROSS-PROJETO */}
      <section className={styles.searchSection} aria-labelledby="search-title">
        <div className={styles.searchHeading}>
          <strong id="search-title">Busca entre projetos</strong>
          <span>Encontre tecnologias utilizadas nesta subárea</span>
        </div>
        <div className={styles.searchBox}>
          <svg className={styles.searchIcon} viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="m20 20-4.3-4.3m2.3-5.2a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <label htmlFor="project-search" className={styles.srOnly}>Buscar tecnologia nos projetos</label>
          <input
            id="project-search"
            type="text"
            placeholder="Busque por Python, Spark, React..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className={styles.searchInput}
          />
          <div className={styles.searchActions}>
            {searching && <span className={styles.searching}>Buscando…</span>}
            {searchQuery && (
              <button type="button" className={styles.clearSearch} onClick={clearSearch} aria-label="Limpar busca">
                ×
              </button>
            )}
          </div>
        </div>

        {searchQuery.trim() && searchResults !== null && (
          <div className={styles.searchResults}>
            {searchResults.length === 0 ? (
              <p style={{ padding: "16px 20px", color: "#9696a0", fontSize: 14 }}>
                Nenhum projeto encontrou "{searchQuery}" na stack.
              </p>
            ) : (
              <>
                <p style={{ padding: "12px 20px 8px", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                  textTransform: "uppercase", color: "#9696a0", borderBottom: "1px solid #f0f0f4" }}>
                  {searchResults.length} projeto{searchResults.length !== 1 ? "s" : ""} com "{searchQuery}"
                </p>
                {searchResults.map((r) => (
                  <Link key={r.project_id} href={`/${subarea}/projects/${r.project_id}`}>
                    <div style={searchResultCard}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                        <div>
                          <span style={{ fontWeight: 600, fontSize: 14, color: "#111116" }}>{r.project_name}</span>
                          <span style={{ marginLeft: 8, fontSize: 13, color: "#22c55e", fontWeight: 500 }}>{r.client}</span>
                        </div>
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
                          {r.sprints.map((s) => (
                            <span key={s} style={tagStyle}>Sprint {s}</span>
                          ))}
                        </div>
                      </div>
                      {r.sample_context && (
                        <p style={{ marginTop: 6, fontSize: 13, color: "#6a6a7a", lineHeight: 1.5,
                          display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                          {r.sample_context}
                        </p>
                      )}
                    </div>
                  </Link>
                ))}
              </>
            )}
          </div>
        )}
      </section>

      <div className={styles.sectionHeader}>
        <h2>Todos os projetos</h2>
        {!loading && <span>{projects.length} projeto{projects.length !== 1 ? "s" : ""}</span>}
      </div>

      {loading && <p style={{ color: "#9696a0" }}>Carregando...</p>}
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}

      {!loading && projects.length === 0 && (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <p style={{ fontSize: 16, color: "#9696a0" }}>Nenhum projeto ainda.</p>
          <p style={{ marginTop: 8, color: "#b8b8c0", fontSize: 14 }}>Crie o primeiro projeto para começar.</p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {projects.map((p) => <ProjectCard key={p.id} p={p} subarea={subarea} />)}
      </div>
    </main>
  );
}

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 12,
  padding: "18px 22px",
  cursor: "pointer",
};

const searchResultCard: React.CSSProperties = {
  padding: "14px 20px",
  cursor: "pointer",
  borderBottom: "1px solid #f0f0f4",
};

const tagStyle: React.CSSProperties = {
  background: "#dcfce7",
  color: "#16a34a",
  borderRadius: 4,
  padding: "2px 8px",
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: "0.02em",
};

const staleDotStyle: React.CSSProperties = {
  display: "inline-block",
  width: 8,
  height: 8,
  borderRadius: "50%",
  background: "#dc2626",
  flexShrink: 0,
};
