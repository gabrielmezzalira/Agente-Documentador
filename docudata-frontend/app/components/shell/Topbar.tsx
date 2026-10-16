"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, type FormEvent } from "react";
import { buttonClass, buttonStyle } from "../ds/Button";
import { ds, cardStyle } from "../../lib/ds";
import { SUBAREAS, type SubareaSlug } from "./navItems";
import styles from "./shell.module.css";

/** Barra superior de 72px: busca (⌘K), seletor de subárea e ação primária. */
export default function Topbar({ subarea }: { subarea: SubareaSlug }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function submit(e: FormEvent) {
    e.preventDefault();
    const q = inputRef.current?.value.trim() ?? "";
    router.push(q ? `/${subarea}?q=${encodeURIComponent(q)}` : `/${subarea}`);
  }

  return (
    <header className={styles.topbar}>
      <Link href="/" className={styles.mobileLogo} aria-label="Agente Documentador — início">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/citi-logo.png" alt="CITi" style={{ height: 22, width: "auto" }} />
      </Link>

      <form onSubmit={submit} role="search" style={{ flex: 1, maxWidth: 520 }}>
        <label className={styles.searchWrap} style={{ ...cardStyle, borderRadius: 12, boxShadow: "none", height: 42, display: "flex", alignItems: "center", gap: 10, padding: "0 16px", fontSize: 13.5, color: ds.muted }}>
          <span aria-hidden="true" style={{ width: 11, height: 11, border: `1.5px solid ${ds.muted}`, borderRadius: "50%", flexShrink: 0 }} />
          <span style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>Buscar projetos e tecnologias</span>
          <input
            ref={inputRef}
            type="search"
            placeholder="Buscar projetos ou tecnologias"
            style={{ flex: 1, minWidth: 0, background: "transparent", border: "none", outline: "none", color: ds.text, fontSize: 13.5, fontFamily: "inherit" }}
          />
          <kbd style={{ fontFamily: ds.fontMono, fontSize: 11, padding: "2px 7px", border: `1px solid ${ds.borderStrong}`, borderRadius: 6, color: ds.muted }}>⌘K</kbd>
        </label>
      </form>

      {/* Seletor de subárea logo depois da busca, como no protótipo */}
      <div role="group" aria-label="Subárea" style={{ ...cardStyle, boxShadow: "none", borderRadius: 12, display: "flex", padding: 4, flexShrink: 0 }}>
        {SUBAREAS.map((s) => {
          const active = s.slug === subarea;
          return (
            <Link
              key={s.slug}
              href={`/${s.slug}`}
              aria-current={active ? "true" : undefined}
              style={{
                height: 32,
                padding: "0 14px",
                borderRadius: 9,
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                fontSize: 13,
                fontWeight: 600,
                background: active ? ds.greenSoft : "transparent",
                color: active ? ds.green : ds.muted,
              }}
            >
              {active && (
                <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: ds.green, boxShadow: `0 0 8px ${ds.green}`, flexShrink: 0 }} />
              )}
              {s.label}
            </Link>
          );
        })}
      </div>

      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
        <Link href={`/${subarea}/projects/new`} className={buttonClass("primary")} style={buttonStyle("primary")}>
          + Novo projeto
        </Link>
      </div>
    </header>
  );
}
