"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { chaveFoto, deleteFoto, fotoCompletaSrc, fotoSrc, listFotos, uploadFoto, TASK_ANEXO_TIPOS } from "../lib/api";
import { ds } from "../lib/ds";
import { initialsOf } from "./shell/navItems";

interface FotosCtx { versoes: Record<string, string>; recarregar: () => Promise<void> }

const FotosContext = createContext<FotosCtx>({ versoes: {}, recarregar: async () => {} });

/** Carrega uma vez quais pessoas têm foto; cada Avatar da tela consulta aqui, sem uma requisição por pessoa. */
export function FotosProvider({ children }: { children: React.ReactNode }) {
  const [versoes, setVersoes] = useState<Record<string, string>>({});
  const recarregar = useCallback(async () => {
    try { setVersoes(await listFotos()); } catch { /* sem foto, o avatar mostra as iniciais */ }
  }, []);
  useEffect(() => { void recarregar(); }, [recarregar]);
  const valor = useMemo(() => ({ versoes, recarregar }), [versoes, recarregar]);
  return <FotosContext.Provider value={valor}>{children}</FotosContext.Provider>;
}

const CORES = [
  { bg: "rgba(62,224,111,0.14)", fg: "#3ee06f", line: "rgba(62,224,111,0.35)" },
  { bg: "rgba(177,151,252,0.14)", fg: "#b197fc", line: "rgba(177,151,252,0.35)" },
  { bg: "rgba(242,193,78,0.14)", fg: "#f2c14e", line: "rgba(242,193,78,0.35)" },
  { bg: "rgba(110,190,255,0.14)", fg: "#6ebeff", line: "rgba(110,190,255,0.35)" },
  { bg: "rgba(255,138,138,0.14)", fg: "#ff8a8a", line: "rgba(255,138,138,0.35)" },
];

function corDoNome(nome: string) {
  let h = 0;
  for (const c of chaveFoto(nome)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return CORES[h % CORES.length];
}

/** Foto inteira em tela cheia: clique, Esc ou fora fecham. Vai para o body para não herdar o recorte/clique de quem a abriu. */
function FotoAmpliada({ nome, chave, versao, onClose }: { nome: string; chave: string; versao: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return createPortal(
    <div
      role="dialog" aria-modal="true" aria-label={`Foto de ${nome}`}
      onClick={(e) => { e.stopPropagation(); e.preventDefault(); onClose(); }}
      style={{ position: "fixed", inset: 0, zIndex: 400, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14, padding: 24, background: "rgba(0,0,0,0.85)", backdropFilter: "blur(6px)", cursor: "zoom-out" }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={fotoCompletaSrc(chave, versao)} alt={`Foto de ${nome}`} style={{ maxWidth: "min(92vw, 900px)", maxHeight: "80vh", objectFit: "contain", borderRadius: 16, border: `1px solid ${ds.borderStrong}`, boxShadow: "0 20px 60px rgba(0,0,0,0.6)" }} />
      <span style={{ color: ds.white, fontSize: 16, fontWeight: 600 }}>{nome}</span>
    </div>,
    document.body,
  );
}

/** Foto redonda da pessoa; sem foto, as iniciais numa cor que depende do nome. Com foto, clicar amplia. */
export default function Avatar({ nome, size = 28 }: { nome: string; size?: number }) {
  const { versoes } = useContext(FotosContext);
  const chave = chaveFoto(nome);
  const versao = versoes[chave];
  const [quebrou, setQuebrou] = useState(false);
  const [ampliada, setAmpliada] = useState(false);
  useEffect(() => setQuebrou(false), [versao]);
  const fechar = useCallback(() => setAmpliada(false), []);
  const cor = corDoNome(nome);
  const base: React.CSSProperties = { width: size, height: size, flexShrink: 0, borderRadius: "50%", display: "inline-block", verticalAlign: "middle" };

  if (versao && !quebrou) {
    return (
      <>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={fotoSrc(chave, versao)} alt="" aria-hidden="true" title={`Ampliar a foto de ${nome}`} onError={() => setQuebrou(true)}
          onClick={(e) => { e.stopPropagation(); e.preventDefault(); setAmpliada(true); }}
          style={{ ...base, objectFit: "cover", border: `1px solid ${ds.borderStrong}`, cursor: "zoom-in" }}
        />
        {ampliada && <FotoAmpliada nome={nome} chave={chave} versao={versao} onClose={fechar} />}
      </>
    );
  }
  return (
    <span
      aria-hidden="true"
      style={{ ...base, background: cor.bg, border: `1px solid ${cor.line}`, color: cor.fg, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: Math.max(10, Math.round(size * 0.38)), fontWeight: 700 }}
    >
      {initialsOf(nome)}
    </span>
  );
}

/** Foto grande demais para o proxy (4 MB): reduz no navegador antes de enviar. */
async function reduzir(arquivo: File): Promise<Blob> {
  if (arquivo.size <= 1_500_000 || arquivo.type === "image/gif") return arquivo;
  try {
    const bmp = await createImageBitmap(arquivo);
    const escala = Math.min(1, 1024 / Math.max(bmp.width, bmp.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bmp.width * escala);
    canvas.height = Math.round(bmp.height * escala);
    canvas.getContext("2d")!.drawImage(bmp, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, "image/jpeg", 0.9));
    return blob ?? arquivo;
  } catch {
    return arquivo;
  }
}

const mini: React.CSSProperties = {
  position: "absolute", width: 16, height: 16, borderRadius: "50%", border: `1px solid ${ds.borderStrong}`, background: "#0d1711",
  color: ds.text2, fontSize: 9, lineHeight: 1, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", padding: 0,
};

/** Avatar que gerente/líder (ou a própria pessoa) troca clicando: lápis para trocar, × para remover. */
export function AvatarEditavel({ nome, size = 36, onErro }: { nome: string; size?: number; onErro?: (msg: string) => void }) {
  const { versoes, recarregar } = useContext(FotosContext);
  const chave = chaveFoto(nome);
  const temFoto = Boolean(versoes[chave]);
  const [ocupado, setOcupado] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function trocar(arquivo: File | undefined) {
    if (!arquivo) return;
    setOcupado(true);
    try {
      await uploadFoto(nome, await reduzir(arquivo));
      await recarregar();
    } catch (e) {
      onErro?.(e instanceof Error ? e.message : "Não foi possível enviar a foto");
    } finally {
      setOcupado(false);
    }
  }

  async function remover() {
    if (!confirm(`Remover a foto de ${nome}?`)) return;
    setOcupado(true);
    try {
      await deleteFoto(chave);
      await recarregar();
    } catch (e) {
      onErro?.(e instanceof Error ? e.message : "Não foi possível remover a foto");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <span style={{ position: "relative", display: "inline-block", width: size, height: size, flexShrink: 0, opacity: ocupado ? 0.5 : 1 }}>
      <Avatar nome={nome} size={size} />
      <button type="button" disabled={ocupado} onClick={() => inputRef.current?.click()} aria-label={`Trocar a foto de ${nome}`} title="Trocar foto" style={{ ...mini, right: -4, bottom: -4 }}>✎</button>
      {temFoto && <button type="button" disabled={ocupado} onClick={() => void remover()} aria-label={`Remover a foto de ${nome}`} title="Remover foto" style={{ ...mini, right: -4, top: -4 }}>×</button>}
      <input
        ref={inputRef} type="file" accept={TASK_ANEXO_TIPOS} hidden aria-label={`Escolher a foto de ${nome}`}
        onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; void trocar(f); }}
      />
    </span>
  );
}

/** Foto + nome lado a lado, para listas e tabelas. */
export function PessoaComFoto({ nome, size = 24, children }: { nome: string; size?: number; children?: React.ReactNode }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8, minWidth: 0 }}>
      <Avatar nome={nome} size={size} />
      {children ?? <span>{nome}</span>}
    </span>
  );
}
