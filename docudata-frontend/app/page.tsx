import Link from "next/link";


const subareas = [
  {
    slug: "dados",
    title: "Dados",
    description: "Projetos de dados, analytics e inteligência artificial.",
  },
  {
    slug: "dev",
    title: "Dev",
    description: "Projetos de desenvolvimento de software.",
  },
] as const;


export default function SubareaSelector() {
  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "72px 24px" }}>
      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "#16a34a" }}>
        citi · agente documentador
      </span>
      <h1 style={{ fontSize: 40, fontWeight: 800, letterSpacing: "-0.03em", color: "#111116", marginTop: 18, marginBottom: 8 }}>
        Escolha uma subárea
      </h1>
      <p style={{ color: "#9696a0", fontSize: 15, marginBottom: 36 }}>
        Os projetos e buscas ficam separados entre Dados e Dev.
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


const cardStyle: React.CSSProperties = {
  height: "100%",
  background: "#fff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "26px 28px",
};
