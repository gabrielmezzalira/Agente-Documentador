import { ds } from "../../lib/ds";

/** Marca das telas de conta (login, cadastro, senha): logo CITi + "Agente Documentador", como na sidebar. */
export default function AuthBrand({ title }: { title: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 18, marginBottom: 28, textAlign: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/citi-logo.png" alt="CITi" style={{ height: 30, width: "auto" }} />
        <span style={{ fontFamily: ds.fontMono, fontSize: 10.5, letterSpacing: "0.18em", color: ds.muted }}>AGENTE DOCUMENTADOR</span>
      </div>
      <h1 style={{ margin: 0, fontSize: 30, fontWeight: 700, letterSpacing: "-0.03em", color: ds.white }}>{title}</h1>
    </div>
  );
}
