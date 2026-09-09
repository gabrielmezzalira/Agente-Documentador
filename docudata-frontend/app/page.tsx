"use client";

import Link from "next/link";
import { useAuth } from "./components/AuthGuard";


const subareas = [
  {
    slug: "dados",
    title: "Dados",
    description: "Projetos de dados, analytics e inteligência artificial.",
  },
  {
    slug: "dev",
    title: "Dev",
    description: "Projetos de desenvolvimento de software e seus repositórios.",
  },
] as const;


export default function SubareaSelector() {
  const auth = useAuth();
  const podeGerenciar = auth?.cargo === "owner" || auth?.cargo === "lider";
  const podeConfigurar = podeGerenciar || auth?.cargo === "gerente";

  return (
    <main style={{ maxWidth: 800, margin: "0 auto", padding: "72px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "#16a34a" }}>
          citi · agente documentador
        </span>
        <nav style={{ display: "flex", gap: 8, flexWrap: "wrap" }} aria-label="Acessos globais">
          <Link href="/metodologia" style={navLinkStyle}>Documentos</Link>
          {podeGerenciar && <Link href="/pessoas" style={navLinkStyle}>Pessoas</Link>}
          {podeGerenciar && <Link href="/performance" style={navLinkStyle}>Performance</Link>}
          {podeConfigurar && <Link href="/settings" style={navLinkStyle}>Configurações</Link>}
        </nav>
      </div>

      <h1 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.03em", color: "#111116", marginTop: 28, marginBottom: 8 }}>
        Escolha uma subárea
      </h1>
      <p style={{ color: "#737380", fontSize: 15, marginBottom: 36 }}>
        Projetos, buscas e novos cadastros permanecem separados entre Dados e Dev.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
        {subareas.map((subarea) => (
          <Link key={subarea.slug} href={`/${subarea.slug}`} style={{ color: "inherit" }}>
            <section style={cardStyle}>
              <h2 style={{ fontSize: 22, fontWeight: 750, color: "#111116", margin: 0 }}>{subarea.title}</h2>
              <p style={{ color: "#6a6a7a", fontSize: 14, lineHeight: 1.5, marginTop: 8 }}>
                {subarea.description}
              </p>
              <span style={{ display: "inline-block", color: "#16a34a", fontSize: 13, fontWeight: 700, marginTop: 22 }}>
                Acessar projetos →
              </span>
            </section>
          </Link>
        ))}
      </div>
    </main>
  );
}


const navLinkStyle: React.CSSProperties = {
  color: "#374151",
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 8,
  padding: "8px 12px",
  fontSize: 12,
  fontWeight: 650,
};

const cardStyle: React.CSSProperties = {
  height: "100%",
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "26px 28px",
};
