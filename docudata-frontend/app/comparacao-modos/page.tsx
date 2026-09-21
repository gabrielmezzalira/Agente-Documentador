"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { useAuth } from "../components/AuthGuard";
import {
  listProjects,
  getComparacaoModosEntreProjetos,
  type Project,
  type ComparacaoModoPonto,
} from "../lib/api";

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 12,
  padding: "20px 24px",
  marginBottom: 20,
};

const linkProjetosStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#9696a0",
};

export default function ComparacaoModosPage() {
  const auth = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selecionados, setSelecionados] = useState<string[]>([]);
  const [resultado, setResultado] = useState<ComparacaoModoPonto[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!auth || (auth.cargo !== "lider" && auth.cargo !== "owner")) return;
    Promise.all([listProjects("dados"), listProjects("dev")])
      .then(([dados, dev]) => setProjects([...dados, ...dev]))
      .catch(() => setProjects([]));
  }, [auth]);

  function toggleProjeto(id: string) {
    setSelecionados((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  }

  function buscar() {
    if (selecionados.length < 2) {
      setErro("Selecione ao menos 2 projetos.");
      return;
    }
    setLoading(true);
    setErro(null);
    getComparacaoModosEntreProjetos(selecionados)
      .then(setResultado)
      .catch((err) => setErro(err instanceof Error ? err.message : "Erro ao comparar"))
      .finally(() => setLoading(false));
  }

  if (auth && auth.cargo !== "lider" && auth.cargo !== "owner") {
    return (
      <main style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px" }}>
        <Link href="/" style={linkProjetosStyle}>← Projetos</Link>
        <p style={{ color: "#dc2626", marginTop: 20 }}>Acesso restrito a Líder e Owner.</p>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "52px 24px" }}>
      <Link href="/" style={linkProjetosStyle}>← Projetos</Link>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#111116", margin: "20px 0 24px" }}>
        Comparação de modos entre projetos
      </h1>

      <div style={card}>
        <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Escolha 2 ou mais projetos</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
          {projects.map((p) => (
            <label key={p.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
              <input
                type="checkbox"
                checked={selecionados.includes(p.id)}
                onChange={() => toggleProjeto(p.id)}
              />
              {p.name}
            </label>
          ))}
        </div>
        <button
          type="button"
          onClick={buscar}
          disabled={loading || selecionados.length < 2}
          style={{
            background: "#22c55e",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "8px 16px",
            fontSize: 13,
            cursor: loading || selecionados.length < 2 ? "not-allowed" : "pointer",
            opacity: loading || selecionados.length < 2 ? 0.5 : 1,
          }}
        >
          {loading ? "Comparando..." : "Comparar"}
        </button>
        {erro && <p style={{ fontSize: 12, color: "#dc2626", marginTop: 8 }}>{erro}</p>}
      </div>

      {resultado.length > 0 && (
        <div style={card}>
          <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Resultado</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={resultado.map((r) => ({
                modo: `${r.modo_trabalho}/${r.modo_avaliacao}`,
                spi_medio: r.spi_medio,
                entrega_media: r.entrega_media,
              }))}
              margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="modo" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend formatter={(v) => (v === "spi_medio" ? "SPI médio" : "Entrega média")} />
              <Bar dataKey="spi_medio" fill="#64748b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="entrega_media" fill="#166534" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </main>
  );
}
