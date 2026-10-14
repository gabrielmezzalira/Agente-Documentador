"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
};

const card: React.CSSProperties = {
  background: "#0d1711",
  border: "1px solid rgba(62,224,111,0.2)",
  borderRadius: 12,
  padding: "20px 24px",
  marginBottom: 20,
};

const projetoHeading: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 800,
  color: "#f2f5f3",
  margin: "32px 0 12px",
};

export default function PerformancePage() {
  const auth = useAuth();
  const [janela, setJanela] = useState<"sprint" | "quinzenal" | "mensal">("sprint");
  const [dados, setDados] = useState<PerformanceResponse | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!auth || (auth.cargo !== "lider" && auth.cargo !== "owner")) return;
    getPerformance()
      .then(setDados)
      .catch((e: Error) => setErro(e.message));
  }, [auth]);

  if (auth && auth.cargo !== "lider" && auth.cargo !== "owner") {
    return (
      <main style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px" }}>
        <Link href="/" style={linkProjetosStyle}>← Projetos</Link>
        <p style={{ color: "#ff6b6b", marginTop: 20 }}>Acesso restrito a Líder e Owner.</p>
      </main>
    );
  }

  const projetos = dados?.projetos ?? [];

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "52px 24px" }}>
      <Link href="/" style={linkProjetosStyle}>← Projetos</Link>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#f2f5f3", margin: "20px 0 24px" }}>Performance</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {(["sprint", "quinzenal", "mensal"] as const).map((j) => (
          <button
            key={j}
            onClick={() => setJanela(j)}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: j === janela ? "2px solid #3ee06f" : "1px solid rgba(62,224,111,0.2)",
              background: j === janela ? "rgba(62,224,111,0.12)" : "#0d1711",
              color: "#f2f5f3",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {JANELA_LABEL[j]}
          </button>
        ))}
      </div>

      {erro && <p style={{ color: "#ff6b6b" }}>{erro}</p>}

      {!dados && !erro && <p style={{ color: "#8a948e" }}>Carregando...</p>}

      {dados && projetos.length === 0 && (
        <p style={{ color: "#8a948e" }}>Nenhum projeto com dado suficiente nesta janela.</p>
      )}

      {projetos.map((projeto) => {
        const lista: PerformanceOperacional[] = projeto[janela];
        return (
          <section key={projeto.projeto_id}>
            <h2 style={projetoHeading}>{projeto.projeto_nome}</h2>

            {lista.length === 0 && (
              <p style={{ color: "#8a948e" }}>Nenhum operacional com dado suficiente nesta janela.</p>
            )}

            {lista.map((op, i) => (
              <div key={op.email} style={card}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <span style={{ fontSize: 16, fontWeight: 700, color: "#f2f5f3" }}>
                    {i + 1}. {op.nome}
                  </span>
                  <span style={{ fontSize: 20, fontWeight: 800, color: "#3ee06f" }}>{op.score_final}</span>
                </div>
                {op.janela_parcial && (
                  <p style={{ fontSize: 12, color: "#f2c14e", marginBottom: 8 }}>Janela parcial — dado insuficiente ainda</p>
                )}
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                  {(["entrega", "gerente", "qualidade", "autonomia"] as const).map((dim) => (
                    <div key={dim}>
                      <p style={{ fontSize: 11, color: "#8a948e", textTransform: "uppercase", marginBottom: 2 }}>
                        {DIMENSAO_LABEL[dim]}
                      </p>
                      <p style={{ fontSize: 14, fontWeight: 600, color: "#f2f5f3" }}>{op[dim] ?? "—"}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </section>
        );
      })}
    </main>
  );
}

const linkProjetosStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#8a948e",
};
