"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "../components/AuthGuard";
import { getMetodologia, type MetodologiaResponse } from "../lib/api";

/* O reset global (`* { margin: 0; padding: 0 }`) zera tipografia de markdown —
   este documento é longo e cheio de tabelas, então precisa da folha abaixo pra
   ser legível. Escopada em .doc pra não vazar pro resto do app. */
const DOC_CSS = `
.doc { color: #33333d; font-size: 15px; line-height: 1.75; }
.doc h1 { font-size: 30px; font-weight: 800; letter-spacing: -0.02em; color: #111116; line-height: 1.2; margin: 0 0 20px; }
.doc h2 { font-size: 21px; font-weight: 700; color: #111116; margin: 44px 0 14px; padding-top: 20px; border-top: 1px solid #ececf1; }
.doc h3 { font-size: 16px; font-weight: 700; color: #111116; margin: 28px 0 10px; }
.doc p { margin: 0 0 14px; }
.doc ul, .doc ol { margin: 0 0 16px; padding-left: 22px; }
.doc li { margin-bottom: 6px; }
.doc li > ul, .doc li > ol { margin: 6px 0 0; }
.doc a { color: #16a34a; }
.doc a:hover { text-decoration: underline; }
.doc strong { color: #111116; font-weight: 700; }
.doc hr { border: none; border-top: 1px solid #ececf1; margin: 36px 0; }
.doc code { background: #f2f2f6; border-radius: 4px; padding: 1px 5px; font-size: 13px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #111116; }
.doc pre { background: #f7f7fa; border: 1px solid #e8e8ed; border-radius: 10px; padding: 16px 18px; overflow-x: auto; margin: 0 0 18px; line-height: 1.6; }
.doc pre code { background: none; padding: 0; font-size: 12.5px; }
.doc blockquote { border-left: 3px solid #16a34a; background: #f0fdf4; border-radius: 0 8px 8px 0; padding: 12px 18px; margin: 0 0 18px; color: #3f6f52; }
.doc blockquote p:last-child { margin-bottom: 0; }
.doc table { border-collapse: collapse; width: 100%; margin: 0 0 20px; font-size: 13.5px; display: block; overflow-x: auto; }
.doc th, .doc td { border: 1px solid #e8e8ed; padding: 8px 12px; text-align: left; vertical-align: top; }
.doc th { background: #f7f7fa; font-weight: 700; color: #111116; white-space: nowrap; }
`;

export default function MetodologiaPage() {
  const auth = useAuth();
  const [doc, setDoc] = useState<MetodologiaResponse | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!auth || auth.cargo === "operacional") return;
    getMetodologia("performance")
      .then(setDoc)
      .catch((e: Error) => setErro(e.message));
  }, [auth]);

  if (auth && auth.cargo === "operacional") {
    return (
      <main style={{ maxWidth: 820, margin: "0 auto", padding: "52px 24px" }}>
        <p style={{ color: "#dc2626" }}>Acesso restrito a Líder e Gerente.</p>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 880, margin: "0 auto", padding: "48px 24px 96px" }}>
      <style>{DOC_CSS}</style>

      <Link href="/" style={{ fontSize: 13, color: "#9696a0" }}>← Projetos</Link>

      <div
        style={{
          marginTop: 20,
          marginBottom: 28,
          background: "#fffbeb",
          border: "1px solid #fde68a",
          borderRadius: 10,
          padding: "12px 16px",
          fontSize: 13,
          color: "#92400e",
        }}
      >
        Documento interno — Líder e Gerente. Pesos, fórmulas e notas cruas não são
        divulgados a operacionais.
      </div>

      {erro && <p style={{ color: "#dc2626" }}>{erro}</p>}
      {!doc && !erro && <p style={{ color: "#9696a0" }}>Carregando...</p>}

      {doc && (
        <div
          className="doc"
          style={{ background: "#fff", border: "1px solid #e8e8ed", borderRadius: 12, padding: "36px 40px" }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc.conteudo}</ReactMarkdown>
        </div>
      )}
    </main>
  );
}
