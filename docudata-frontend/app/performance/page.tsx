"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../components/AuthGuard";
import { getPerformance, type PerformanceResponse, type PerformanceOperacional } from "../lib/api";

const JANELA_LABEL: Record<string, string> = {
  sprint: "Última sprint",
  quinzenal: "Últimas 2 sprints",
  mensal: "Últimas 4 sprints",
};

const DIMENSAO_LABEL: Record<string, string> = {
  entrega: "Entrega",
  gerente: "Gerente",
  qualidade: "Qualidade",
  autonomia: "Autonomia",
  evolucao: "Evolução",
};

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 12,
  padding: "20px 24px",
  marginBottom: 20,
};

export default function PerformancePage() {
  const auth = useAuth();
  const [janela, setJanela] = useState<"sprint" | "quinzenal" | "mensal">("sprint");
  const [dados, setDados] = useState<PerformanceResponse | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!auth || auth.cargo !== "lider") return;
    getPerformance()
      .then(setDados)
      .catch((e: Error) => setErro(e.message));
  }, [auth]);

  if (auth && auth.cargo !== "lider") {
    return (
      <main style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px" }}>
        <p style={{ color: "#dc2626" }}>Acesso restrito a Líder.</p>
      </main>
    );
  }

  const lista: PerformanceOperacional[] = dados ? dados[janela] : [];

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "52px 24px" }}>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#111116", marginBottom: 24 }}>Performance</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {(["sprint", "quinzenal", "mensal"] as const).map((j) => (
          <button
            key={j}
            onClick={() => setJanela(j)}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: j === janela ? "2px solid #16a34a" : "1px solid #e8e8ed",
              background: j === janela ? "#f0fdf4" : "#fff",
              color: "#111116",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {JANELA_LABEL[j]}
          </button>
        ))}
      </div>

      {erro && <p style={{ color: "#dc2626" }}>{erro}</p>}

      {!dados && !erro && <p style={{ color: "#9696a0" }}>Carregando...</p>}

      {dados && lista.length === 0 && (
        <p style={{ color: "#9696a0" }}>Nenhum operacional com dado suficiente nesta janela.</p>
      )}

      {lista.map((op, i) => (
        <div key={op.email} style={card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: "#111116" }}>
              {i + 1}. {op.nome}
            </span>
            <span style={{ fontSize: 20, fontWeight: 800, color: "#16a34a" }}>{op.score_final}</span>
          </div>
          {op.janela_parcial && (
            <p style={{ fontSize: 12, color: "#d97706", marginBottom: 8 }}>Janela parcial — dado insuficiente ainda</p>
          )}
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {(["entrega", "gerente", "qualidade", "autonomia", "evolucao"] as const).map((dim) => (
              <div key={dim}>
                <p style={{ fontSize: 11, color: "#9696a0", textTransform: "uppercase", marginBottom: 2 }}>
                  {DIMENSAO_LABEL[dim]}
                </p>
                <p style={{ fontSize: 14, fontWeight: 600, color: "#111116" }}>{op[dim] ?? "—"}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </main>
  );
}
