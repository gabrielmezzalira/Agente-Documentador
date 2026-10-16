"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "../components/AuthGuard";
import {
  listMetodologia,
  getMetodologia,
  type MetodologiaItem,
  type MetodologiaResponse,
} from "../lib/api";

/* O reset global (`* { margin: 0; padding: 0 }`) zera tipografia de markdown —
   estes documentos são longos e cheios de tabelas, então precisam da folha
   abaixo para serem legíveis. Escopada em .doc para não vazar pro resto do app. */
const DOC_CSS = `
.doc { color: #c3cbc6; font-size: 15px; line-height: 1.75; }
.doc h1 { font-size: 30px; font-weight: 800; letter-spacing: -0.02em; color: #f2f5f3; line-height: 1.2; margin: 0 0 20px; }
.doc h2 { font-size: 21px; font-weight: 700; color: #f2f5f3; margin: 44px 0 14px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.08); }
.doc h3 { font-size: 16px; font-weight: 700; color: #f2f5f3; margin: 28px 0 10px; }
.doc p { margin: 0 0 14px; }
.doc ul, .doc ol { margin: 0 0 16px; padding-left: 22px; }
.doc li { margin-bottom: 6px; }
.doc li > ul, .doc li > ol { margin: 6px 0 0; }
.doc a { color: #3ee06f; }
.doc a:hover { text-decoration: underline; }
.doc strong { color: #f2f5f3; font-weight: 700; }
.doc hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 36px 0; }
.doc code { background: rgba(62,224,111,0.055); border-radius: 4px; padding: 1px 5px; font-size: 13px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #f2f5f3; }
.doc pre { background: rgba(62,224,111,0.055); border: 1px solid rgba(62,224,111,0.2); border-radius: 10px; padding: 16px 18px; overflow-x: auto; margin: 0 0 18px; line-height: 1.6; }
.doc pre code { background: none; padding: 0; font-size: 12.5px; }
.doc blockquote { border-left: 3px solid #3ee06f; background: rgba(62,224,111,0.12); border-radius: 0 8px 8px 0; padding: 12px 18px; margin: 0 0 18px; color: #7cf0a0; }
.doc blockquote p:last-child { margin-bottom: 0; }
.doc table { border-collapse: collapse; width: 100%; margin: 0 0 20px; font-size: 13.5px; display: block; overflow-x: auto; }
.doc th, .doc td { border: 1px solid rgba(62,224,111,0.2); padding: 8px 12px; text-align: left; vertical-align: top; }
.doc th { background: rgba(62,224,111,0.055); font-weight: 700; color: #f2f5f3; white-space: nowrap; }
`;

export default function DocumentosPage() {
  const auth = useAuth();
  const [itens, setItens] = useState<MetodologiaItem[]>([]);
  const [slug, setSlug] = useState<string | null>(null);
  const [doc, setDoc] = useState<MetodologiaResponse | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (!auth) return;
    listMetodologia()
      .then((lista) => {
        setItens(lista);
        if (lista.length > 0) setSlug((atual) => atual ?? lista[0].slug);
      })
      .catch((e: Error) => setErro(e.message));
  }, [auth]);

  useEffect(() => {
    if (!slug) return;
    setDoc(null);
    setErro("");
    getMetodologia(slug)
      .then(setDoc)
      .catch((e: Error) => setErro(e.message));
  }, [slug]);

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "48px 24px 96px" }}>
      <style>{DOC_CSS}</style>

      <Link href="/" style={{ fontSize: 13, color: "#8a948e" }}>← Projetos</Link>

      <h1 style={{ fontSize: 32, fontWeight: 800, color: "#f2f5f3", margin: "20px 0 20px" }}>
        Documentos
      </h1>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 24 }}>
        {itens.map((item) => (
          <button
            key={item.slug}
            onClick={() => setSlug(item.slug)}
            style={{
              textAlign: "left",
              flex: "1 1 240px",
              padding: "12px 16px",
              borderRadius: 10,
              border: item.slug === slug ? "2px solid #3ee06f" : "1px solid rgba(62,224,111,0.2)",
              background: item.slug === slug ? "rgba(62,224,111,0.12)" : "#0d1711",
              cursor: "pointer",
            }}
          >
            <span style={{ display: "block", fontSize: 14, fontWeight: 700, color: "#f2f5f3" }}>
              {item.titulo}
            </span>
            <span style={{ display: "block", fontSize: 12, color: "#8a948e", marginTop: 3 }}>
              {item.resumo}
            </span>
          </button>
        ))}
      </div>

      {doc?.restrito && (
        <div style={{
          background: "rgba(242,193,78,0.10)", border: "1px solid rgba(242,193,78,0.30)", borderRadius: 10,
          padding: "12px 16px", marginBottom: 24, fontSize: 13, color: "#f2c14e",
        }}>
          Documento interno, restrito a Gerente para cima. Pesos, fórmulas e notas
          cruas não são divulgados a operacionais.
        </div>
      )}

      {erro && <p style={{ color: "#ff6b6b" }}>{erro}</p>}
      {!doc && !erro && <p style={{ color: "#8a948e" }}>Carregando...</p>}

      {doc && (
        <div
          className="doc"
          style={{ background: "#0d1711", border: "1px solid rgba(62,224,111,0.2)", borderRadius: 12, padding: "36px 40px" }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc.conteudo}</ReactMarkdown>
        </div>
      )}
    </main>
  );
}
