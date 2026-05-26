"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { listProjects, searchStack, type Project, type StackSearchResult } from "./lib/api";

const STALE_DAYS = 7;

function isStale(project: Project): boolean {
  if (project.is_delivered) return false;
  if (!project.last_ingestion_at) return true;
  const diff = Date.now() - new Date(project.last_ingestion_at).getTime();
  return diff > STALE_DAYS * 24 * 60 * 60 * 1000;
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<StackSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError("Não foi possível carregar os projetos."))
      .finally(() => setLoading(false));
  }, []);

  function handleSearchChange(value: string) {
    setSearchQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!value.trim()) { setSearchResults(null); return; }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await searchStack(value.trim());
        setSearchResults(res.results);
      } catch { setSearchResults([]); }
      finally { setSearching(false); }
    }, 400);
  }

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px" }}>
      <div style={{ marginBottom: 52 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "#16a34a" }}>
            citi · subárea de dados
          </span>
          <Link href="/projects/new">
            <button style={btnPrimary}>+ Novo projeto</button>
          </Link>
        </div>
        <h1 style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.03em", color: "#111116", lineHeight: 1.05 }}>
          Agente Documentador
        </h1>
        <p style={{ color: "#9696a0", marginTop: 10, fontSize: 15 }}>
          Documentação automática de projetos de dados
        </p>
      </div>

      {/* BUSCA CROSS-PROJETO */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ position: "relative" }}>
          <input
            type="text"
            placeholder="Buscar stack em todos os projetos... (ex: Python, Spark, K-means)"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            style={searchInputStyle}
          />
          {searching && (
            <span style={{ position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)", fontSize: 12, color: "#9696a0" }}>
              buscando...
            </span>
          )}
        </div>

        {searchQuery.trim() && searchResults !== null && (
          <div style={{ marginTop: 12, background: "#fff", border: "1px solid #e8e8ed", borderRadius: 12, overflow: "hidden" }}>
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
                  <Link key={r.project_id} href={`/projects/${r.project_id}`}>
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
        {projects.map((p) => {
          const stale = isStale(p);
          return (
            <Link key={p.id} href={`/projects/${p.id}`}>
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
                      <p style={{ color: "#9696a0", marginTop: 6, fontSize: 13, lineHeight: 1.5 }}>{p.description}</p>
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
        })}
      </div>
    </main>
  );
}

const btnPrimary: React.CSSProperties = {
  background: "#4ade80",
  color: "#0a0a0a",
  border: "none",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
  letterSpacing: "0.01em",
};

const cardStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 12,
  padding: "18px 22px",
  cursor: "pointer",
};

const searchInputStyle: React.CSSProperties = {
  width: "100%",
  padding: "11px 14px",
  background: "#ffffff",
  border: "1px solid #e4e4ea",
  borderRadius: 10,
  fontSize: 14,
  outline: "none",
  color: "#111116",
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
