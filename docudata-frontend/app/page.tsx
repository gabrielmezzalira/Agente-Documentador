"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listProjects, type Project } from "./lib/api";

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError("Não foi possível carregar os projetos."))
      .finally(() => setLoading(false));
  }, []);

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

      {loading && <p style={{ color: "#9696a0" }}>Carregando...</p>}
      {error && <p style={{ color: "#dc2626" }}>{error}</p>}

      {!loading && projects.length === 0 && (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <p style={{ fontSize: 16, color: "#9696a0" }}>Nenhum projeto ainda.</p>
          <p style={{ marginTop: 8, color: "#b8b8c0", fontSize: 14 }}>Crie o primeiro projeto para começar.</p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {projects.map((p) => (
          <Link key={p.id} href={`/projects/${p.id}`}>
            <div style={cardStyle}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                <div>
                  <h2 style={{ fontSize: 15, fontWeight: 600, color: "#111116" }}>{p.name}</h2>
                  <p style={{ marginTop: 4, fontSize: 13, color: "#22c55e", fontWeight: 500 }}>{p.client}</p>
                  {p.description && (
                    <p style={{ color: "#9696a0", marginTop: 6, fontSize: 13, lineHeight: 1.5 }}>{p.description}</p>
                  )}
                </div>
                <span style={{ color: "#b8b8c0", fontSize: 12, whiteSpace: "nowrap", marginLeft: 20, marginTop: 2 }}>
                  {new Date(p.created_at).toLocaleDateString("pt-BR")}
                </span>
              </div>
            </div>
          </Link>
        ))}
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
