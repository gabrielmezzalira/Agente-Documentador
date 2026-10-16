"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { logout, type MeResponse } from "../../lib/api";
import { cardStyle, ds } from "../../lib/ds";
import { StatusDot } from "../ds";
import { CARGO_LABEL, initialsOf, navItemsFor, subareaFromPath, type SubareaSlug } from "./navItems";
import styles from "./shell.module.css";

/** Menu lateral de 248px: logo, produto, navegação por cargo e cartão do usuário no rodapé. */
export default function Sidebar({ pessoa, subarea, includeProjects }: { pessoa: MeResponse; subarea: SubareaSlug; includeProjects: boolean }) {
  const pathname = usePathname();
  const [loggingOut, setLoggingOut] = useState(false);
  const items = navItemsFor(pessoa.cargo, subarea, includeProjects);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      // Recarrega em vez de só navegar — zera o estado em memória antes de trocar de conta.
      window.location.href = "/login";
    }
  }

  return (
    <aside className={styles.sidebar} aria-label="Menu lateral">
      <Link href="/" style={{ display: "flex", flexDirection: "column", gap: 8, padding: "0 10px", width: "fit-content" }} aria-label="Agente Documentador — início">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/citi-logo.png" alt="CITi" style={{ height: 26, width: "auto", alignSelf: "flex-start" }} />
        <span style={{ fontFamily: ds.fontMono, fontSize: 10.5, letterSpacing: "0.18em", color: ds.muted }}>AGENTE DOCUMENTADOR</span>
      </Link>

      <nav aria-label="Principal" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {items.map((item) => {
          const active = item.active(pathname);
          return (
            <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={`${styles.navLink} ${active ? styles.navLinkActive : ""}`}>
              {active ? <StatusDot tone="green" /> : <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: 2, border: `1px solid ${ds.dim}`, flexShrink: 0 }} />}
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div style={{ ...cardStyle, marginTop: "auto", borderRadius: 12, boxShadow: "none", display: "flex", alignItems: "center", gap: 10, padding: 12 }}>
        <span
          aria-hidden="true"
          style={{ width: 36, height: 36, flexShrink: 0, borderRadius: "50%", background: ds.greenSoft, border: `1px solid ${ds.greenLine}`, color: ds.green, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700 }}
        >
          {initialsOf(pessoa.nome)}
        </span>
        <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
          <span style={{ fontSize: 13.5, fontWeight: 600, color: ds.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{pessoa.nome}</span>
          <span style={{ fontSize: 11.5, color: ds.muted }}>
            {CARGO_LABEL[pessoa.cargo] ?? pessoa.cargo} ·{" "}
            <button
              type="button"
              onClick={handleLogout}
              disabled={loggingOut}
              title="Sair e trocar de conta"
              style={{ background: "none", border: "none", color: ds.muted, fontSize: 11.5, cursor: "pointer", padding: 0, textDecoration: "underline", textUnderlineOffset: 2 }}
            >
              {loggingOut ? "Saindo…" : "Sair"}
            </button>
          </span>
        </div>
      </div>
    </aside>
  );
}

export { subareaFromPath };
