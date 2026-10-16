"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "../components/AuthGuard";
import { Card, Chip, ErrorNotice, PageHeader } from "../components/ds";
import { ds, labelStyle } from "../lib/ds";
import {
  listMetodologia,
  getMetodologia,
  type MetodologiaItem,
  type MetodologiaResponse,
} from "../lib/api";

/* O reset global zera a tipografia de markdown; estes documentos são longos e cheios de
   tabelas, então precisam da folha abaixo (tipografia do protótipo 09). Escopada em .doc. */
const DOC_CSS = `
.doc { color: #c3cbc6; font-size: 15.5px; line-height: 1.7; display: flex; flex-direction: column; gap: 18px; }
.doc > * { margin: 0; }
.doc h1 { font-size: 40px; font-weight: 700; letter-spacing: -0.03em; color: #fff; line-height: 1.1; }
.doc h2 { font-size: 22px; font-weight: 700; color: #fff; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.08); scroll-margin-top: 24px; }
.doc h1 + p { font-family: 'Geist Mono', ui-monospace, monospace; font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: #8a948e; }
.doc hr + h2 { border-top: none; padding-top: 0; }
.doc h3 { font-size: 17px; font-weight: 700; color: #fff; }
.doc ul, .doc ol { padding-left: 22px; }
.doc li { margin-bottom: 6px; }
.doc li > ul, .doc li > ol { margin: 6px 0 0; }
.doc a { color: #3ee06f; }
.doc a:hover { text-decoration: underline; }
.doc strong { color: #fff; font-weight: 700; }
.doc hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); }
.doc code { background: rgba(62,224,111,0.055); border-radius: 4px; padding: 1px 5px; font-size: 13px; font-family: 'Geist Mono', ui-monospace, monospace; color: #f2f5f3; }
.doc pre { background: rgba(62,224,111,0.055); border: 1px solid rgba(62,224,111,0.17); border-radius: 12px; padding: 16px 18px; overflow-x: auto; line-height: 1.6; }
.doc pre code { background: none; padding: 0; font-size: 12.5px; }
.doc blockquote { border-left: 3px solid #3ee06f; background: rgba(62,224,111,0.08); border-radius: 0 10px 10px 0; padding: 12px 18px; color: #c3cbc6; }
.doc blockquote p { margin: 0; }
.doc table { border-collapse: collapse; width: 100%; font-size: 13.5px; display: block; overflow-x: auto; }
.doc th, .doc td { border-bottom: 1px solid rgba(255,255,255,0.08); padding: 10px 12px; text-align: left; vertical-align: top; }
.doc th { font-family: 'Geist Mono', ui-monospace, monospace; font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: #8a948e; font-weight: 500; white-space: nowrap; }
@media (max-width: 900px) { .doc-layout { grid-template-columns: 1fr !important; padding: 28px 22px !important; gap: 24px !important; } .doc-toc { display: none !important; } }
`;

/** Id estável para um título (âncora do índice "Nesta página"). */
function slugify(texto: string): string {
  return texto.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function textoDe(children: ReactNode): string {
  if (typeof children === "string" || typeof children === "number") return String(children);
  if (Array.isArray(children)) return children.map(textoDe).join("");
  if (children && typeof children === "object" && "props" in children) return textoDe((children as { props: { children?: ReactNode } }).props.children);
  return "";
}

export default function DocumentosPage() {
  const auth = useAuth();
  const [itens, setItens] = useState<MetodologiaItem[]>([]);
  const [slug, setSlug] = useState<string | null>(null);
  const [docs, setDocs] = useState<Record<string, MetodologiaResponse>>({});
  const [erro, setErro] = useState("");
  const [secaoAtiva, setSecaoAtiva] = useState<string | null>(null);

  useEffect(() => {
    if (!auth) return;
    listMetodologia()
      .then((lista) => {
        setItens(lista);
        if (lista.length > 0) setSlug((atual) => atual ?? lista[0].slug);
        // Poucos documentos: carrega todos para saber quais são restritos e trocar sem espera.
        lista.forEach((item) => {
          getMetodologia(item.slug)
            .then((d) => setDocs((prev) => ({ ...prev, [item.slug]: d })))
            .catch((e: Error) => { if (item.slug === lista[0].slug) setErro(e.message); });
        });
      })
      .catch((e: Error) => setErro(e.message));
  }, [auth]);

  const doc = slug ? docs[slug] : undefined;
  const secoes = useMemo(
    () => (doc?.conteudo ?? "").split("\n").filter((l) => /^##\s+/.test(l)).map((l) => l.replace(/^##\s+/, "").trim()),
    [doc],
  );

  return (
    <>
      <style>{DOC_CSS}</style>
      <PageHeader title="Documentos" subtitle="A metodologia do DocuData, documentada dentro do próprio sistema." />

      <div className="ds-painel-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 14 }}>
        {itens.map((item) => {
          const ativo = item.slug === slug;
          const restrito = docs[item.slug]?.restrito ?? false;
          return (
            <button
              key={item.slug}
              type="button"
              aria-pressed={ativo}
              className="ds-task-card"
              onClick={() => { setSlug(item.slug); setSecaoAtiva(null); }}
              style={{
                textAlign: "left", fontFamily: "inherit", cursor: "pointer",
                padding: "20px 22px", borderRadius: 14, display: "flex", flexDirection: "column", gap: 8,
                ...(ativo
                  ? { border: `1px solid ${ds.greenLine}`, background: "rgba(62,224,111,0.07)" }
                  : { border: "1px solid rgba(62,224,111,0.2)", background: `linear-gradient(180deg, ${ds.cardTop} 0%, ${ds.cardBottom} 100%)` }),
              }}
            >
              <span style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
                <span style={{ ...labelStyle, color: ativo ? ds.green : ds.muted }}>{restrito ? "Líderes e gerentes" : "Aberto a todos"}</span>
                {restrito && <Chip tone="amber">Restrito</Chip>}
              </span>
              <span style={{ fontSize: 16, fontWeight: 600, color: ds.white, lineHeight: 1.3 }}>{item.titulo}</span>
              <span style={{ fontSize: 13, lineHeight: 1.45, color: ds.muted }}>{item.resumo}</span>
            </button>
          );
        })}
      </div>

      {erro && <ErrorNotice>{erro}</ErrorNotice>}
      {!doc && !erro && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}

      {doc && (
        <Card>
          <div className="doc-layout" style={{ display: "grid", gridTemplateColumns: "220px minmax(0,1fr)", gap: 56, padding: "44px 52px" }}>
            <nav className="doc-toc" aria-label="Nesta página" style={{ display: "flex", flexDirection: "column", gap: 10, paddingTop: 6, position: "sticky", top: 24, alignSelf: "start" }}>
              <span style={labelStyle}>Nesta página</span>
              {secoes.map((s, i) => {
                const ativa = (secaoAtiva ?? secoes[0]) === s;
                return (
                  <a
                    key={`${s}-${i}`}
                    href={`#${slugify(s)}`}
                    onClick={() => setSecaoAtiva(s)}
                    style={{ fontSize: 13.5, lineHeight: 1.4, color: ativa ? ds.green : ds.text2, fontWeight: ativa ? 600 : 400 }}
                  >
                    {s}
                  </a>
                );
              })}
            </nav>
            <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 720, minWidth: 0 }}>
              {doc.restrito && (
                <div role="note" style={{ fontSize: 13, color: ds.amber, background: ds.amberSoft, border: `1px solid ${ds.amberLine}`, borderRadius: 12, padding: "12px 16px" }}>
                  Documento interno, restrito a Gerente para cima. Pesos, fórmulas e notas cruas não são divulgados a operacionais.
                </div>
              )}
              <div className="doc">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h2: ({ children }) => <h2 id={slugify(textoDe(children))}>{children}</h2>,
                  }}
                >
                  {doc.conteudo}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </Card>
      )}
    </>
  );
}
