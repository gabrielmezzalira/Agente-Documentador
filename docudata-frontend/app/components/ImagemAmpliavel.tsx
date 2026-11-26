"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { ds } from "../lib/ds";

function Ampliada({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  const fecharRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    fecharRef.current?.focus();
    // Captura o Esc antes de qualquer modal por baixo: fecha só a imagem.
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.stopPropagation();
      onClose();
    };
    window.addEventListener("keydown", aoTeclar, true);
    return () => window.removeEventListener("keydown", aoTeclar, true);
  }, [onClose]);

  return createPortal(
    <div
      role="dialog" aria-modal="true" aria-label={alt || "Imagem ampliada"}
      onClick={(e) => { e.stopPropagation(); onClose(); }}
      style={{
        position: "fixed", inset: 0, zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center",
        padding: "56px 24px 24px", background: "rgba(0, 0, 0, 0.88)", backdropFilter: "blur(4px)", cursor: "zoom-out", overscrollBehavior: "contain",
      }}
    >
      <div style={{ position: "absolute", top: 14, right: 16, display: "flex", gap: 8 }} onClick={(e) => e.stopPropagation()}>
        <a
          href={src} target="_blank" rel="noreferrer noopener"
          style={{ display: "inline-flex", alignItems: "center", height: 34, padding: "0 14px", borderRadius: 10, fontSize: 13, fontWeight: 600, color: ds.text, background: "rgba(255,255,255,0.08)", border: `1px solid ${ds.borderStrong}`, textDecoration: "none" }}
        >
          Abrir em nova aba
        </a>
        <button
          ref={fecharRef} type="button" onClick={onClose} aria-label="Fechar imagem"
          style={{ height: 34, padding: "0 14px", borderRadius: 10, fontFamily: "inherit", fontSize: 13, fontWeight: 600, color: ds.text, background: "rgba(255,255,255,0.08)", border: `1px solid ${ds.borderStrong}`, cursor: "pointer" }}
        >
          Fechar
        </button>
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src} alt={alt} onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "min(96vw, 1800px)", maxHeight: "calc(100vh - 80px)", width: "auto", height: "auto", objectFit: "contain", borderRadius: 10, cursor: "default", boxShadow: "0 24px 80px rgba(0,0,0,0.6)" }}
      />
    </div>,
    document.body,
  );
}

/** Imagem que, ao clicar, abre ampliada sobre a tela (Esc, clique fora ou botão fecham). */
export default function ImagemAmpliavel({ src, alt, style }: { src: string; alt: string; style?: CSSProperties }) {
  const [aberta, setAberta] = useState(false);
  const gatilho = useRef<HTMLButtonElement>(null);

  function fechar() {
    setAberta(false);
    gatilho.current?.focus();
  }

  return (
    <>
      <button
        ref={gatilho} type="button" onClick={(e) => { e.stopPropagation(); setAberta(true); }}
        aria-label={`Ampliar imagem${alt ? `: ${alt}` : ""}`} title="Clique para ampliar"
        style={{ display: "block", width: "100%", padding: 0, border: "none", background: "none", cursor: "zoom-in", font: "inherit" }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={alt} loading="lazy" referrerPolicy="no-referrer" style={style} />
      </button>
      {aberta && <Ampliada src={src} alt={alt} onClose={fechar} />}
    </>
  );
}
