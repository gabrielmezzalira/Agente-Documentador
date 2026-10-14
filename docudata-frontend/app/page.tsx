"use client";

import Link from "next/link";
import { useAuth } from "./components/AuthGuard";
import { Chip } from "./components/ds";
import { ds, cardStyle, labelStyle } from "./lib/ds";

const subareas = [
  { slug: "dados", title: "Dados", description: "Projetos de dados, analytics e inteligência artificial." },
  { slug: "dev", title: "Dev", description: "Projetos de desenvolvimento de software e seus repositórios." },
  { slug: "produto", title: "Produto", description: "Discovery de produto: requisitos que saem das reuniões e seguem para Dados ou Dev." },
] as const;

export default function SubareaSelector() {
  const auth = useAuth();
  const firstName = auth?.nome.trim().split(/\s+/)[0] ?? "";

  return (
    <>
      <section style={{ marginTop: 110, display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 20, maxWidth: 780 }}>
        {firstName && <Chip tone="green" dot>Bem-vindo de volta, {firstName}.</Chip>}
        <h1 style={{ fontSize: 76, lineHeight: 1, fontWeight: 700, letterSpacing: "-0.04em", color: ds.white }}>
          Escolha uma <span style={{ color: ds.green, textShadow: "0 0 40px rgba(62, 224, 111, 0.35)" }}>subárea.</span>
        </h1>
        <p style={{ fontSize: 18, lineHeight: 1.55, color: ds.muted, textWrap: "pretty" }}>
          Projetos, buscas e novos cadastros permanecem separados entre Dados, Dev e Produto.
        </p>
      </section>

      <div style={{ marginTop: 56, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
        {subareas.map((subarea, i) => {
          const primary = i === 0;
          return (
            <Link key={subarea.slug} href={`/${subarea.slug}`} style={{ display: "block", color: "inherit" }}>
              <section
                style={{
                  ...cardStyle,
                  padding: 36,
                  borderRadius: 20,
                  display: "flex",
                  flexDirection: "column",
                  gap: 14,
                  minHeight: 260,
                  height: "100%",
                  ...(primary ? { background: "rgba(62, 224, 111, 0.06)", borderColor: ds.greenLine, boxShadow: "0 0 60px rgba(62, 224, 111, 0.10)" } : null),
                }}
              >
                <span style={{ ...labelStyle, color: primary ? ds.green : ds.muted }}>{String(i + 1).padStart(2, "0")}</span>
                <h2 style={{ fontSize: 34, fontWeight: 700, letterSpacing: "-0.03em", color: ds.white }}>{subarea.title}</h2>
                <p style={{ fontSize: 16, lineHeight: 1.55, color: ds.muted, maxWidth: 420, textWrap: "pretty" }}>{subarea.description}</p>
                <span style={{ marginTop: "auto", color: ds.green, fontSize: 15, fontWeight: 600 }}>Acessar projetos →</span>
              </section>
            </Link>
          );
        })}
      </div>
    </>
  );
}
