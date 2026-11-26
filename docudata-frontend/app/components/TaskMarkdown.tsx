"use client";

import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { taskAnexoSrc } from "../lib/api";
import { ds } from "../lib/ds";

const PREFIXO = "anexo:";
const NOME_ANEXO = /^[a-z0-9][a-z0-9-]{0,90}\.(png|jpg|webp|gif)$/;

/** Markdown que aponta para uma imagem anexada à task: `![legenda](anexo:nome.png)`. */
export function referenciaAnexo(nome: string): string {
  const legenda = nome.replace(/^[a-z0-9]{12}-/, "").replace(/\.[a-z]+$/, "").replace(/-/g, " ");
  return `![${legenda}](${PREFIXO}${nome})`;
}

/** Nomes das imagens anexadas que o texto já mostra (a galeria não repete essas). */
export function anexosCitados(markdown: string | null | undefined): Set<string> {
  const achados = new Set<string>();
  for (const m of (markdown ?? "").matchAll(/\(anexo:([a-z0-9][a-z0-9-]*\.(?:png|jpg|webp|gif))\)/g)) achados.add(m[1]);
  return achados;
}

/** Tira do texto as referências a uma imagem que acabou de ser removida. */
export function semReferencia(markdown: string, nome: string): string {
  const escapado = nome.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return markdown.replace(new RegExp(`!\\[[^\\]]*\\]\\(${PREFIXO}${escapado}\\)\\n*`, "g"), "");
}

const CSS = `
.task-md{font-size:13.5px;line-height:1.65;color:${ds.text2};overflow-wrap:anywhere}
.task-md > :first-child{margin-top:0}.task-md > :last-child{margin-bottom:0}
.task-md p,.task-md ul,.task-md ol,.task-md pre,.task-md blockquote,.task-md table{margin:0 0 12px}
.task-md h1,.task-md h2,.task-md h3,.task-md h4{color:${ds.white};line-height:1.3;margin:18px 0 8px;font-weight:700}
.task-md h1{font-size:18px}.task-md h2{font-size:16px}.task-md h3,.task-md h4{font-size:14px}
.task-md ul,.task-md ol{padding-left:22px}.task-md li{margin:3px 0}
.task-md a{color:${ds.green};text-decoration:underline;text-underline-offset:2px}
.task-md code{font-family:${ds.fontMono};font-size:12.5px;background:rgba(255,255,255,0.07);padding:1px 5px;border-radius:5px}
.task-md pre{background:rgba(0,0,0,0.35);border:1px solid ${ds.border};border-radius:10px;padding:12px 14px;overflow-x:auto}
.task-md pre code{background:none;padding:0}
.task-md blockquote{background:rgba(255,255,255,0.04);border-radius:8px;padding:8px 14px;color:${ds.muted}}
.task-md table{border-collapse:collapse;display:block;overflow-x:auto}
.task-md th,.task-md td{border:1px solid ${ds.border};padding:6px 10px;text-align:left}
.task-md th{color:${ds.white};background:rgba(255,255,255,0.04)}
.task-md hr{border:none;border-top:1px solid ${ds.border};margin:16px 0}
.task-md img{display:block;max-width:100%;height:auto;border-radius:10px;border:1px solid ${ds.border}}
`;

/** Markdown da task. As imagens `anexo:` vêm do backend (com o acesso do projeto); HTML solto no texto não é interpretado. */
export default function TaskMarkdown({ taskId, texto }: { taskId: string; texto: string }) {
  return (
    <div className="task-md">
      <style>{CSS}</style>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={(url) => (url.startsWith(PREFIXO) ? url : defaultUrlTransform(url))}
        components={{
          a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer noopener">{children}</a>,
          img: ({ src, alt }) => {
            if (typeof src !== "string") return null;
            if (src.startsWith(PREFIXO)) {
              const nome = src.slice(PREFIXO.length);
              if (!NOME_ANEXO.test(nome)) return <span style={{ color: ds.muted }}>[imagem indisponível]</span>;
              const url = taskAnexoSrc(taskId, nome);
              return (
                <a href={url} target="_blank" rel="noreferrer noopener" title="Abrir em tamanho original" style={{ display: "inline-block", maxWidth: "100%" }}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={url} alt={alt ?? ""} loading="lazy" />
                </a>
              );
            }
            // eslint-disable-next-line @next/next/no-img-element
            return <img src={src} alt={alt ?? ""} loading="lazy" referrerPolicy="no-referrer" />;
          },
        }}
      >
        {texto}
      </ReactMarkdown>
    </div>
  );
}
