"use client";

import Link from "next/link";
import { useState } from "react";
import { logout, type MeResponse } from "../../lib/api";
import { cardStyle, ds } from "../../lib/ds";
import { Chip } from "../ds";
import { CARGO_LABEL, navItemsFor } from "./navItems";

/** Cabeçalho da escolha de subárea: logo, acessos globais e identificação do usuário. */
export default function ChooserHeader({ pessoa }: { pessoa: MeResponse }) {
  const [loggingOut, setLoggingOut] = useState(false);
  const items = navItemsFor(pessoa.cargo, "dados", false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      window.location.href = "/login";
    }
  }

  return (
    <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/citi-logo.png" alt="CITi" style={{ height: 28, width: "auto" }} />
        <span aria-hidden="true" style={{ width: 1, height: 20, background: ds.borderStrong }} />
        <span style={{ fontFamily: ds.fontMono, fontSize: 11, letterSpacing: "0.18em", color: ds.muted }}>AGENTE DOCUMENTADOR</span>
      </div>

      <nav aria-label="Acessos globais" style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        {items.map((item) => (
          <Link key={item.href} href={item.href} className="ds-row-link" style={{ padding: "8px 12px", borderRadius: 10, fontSize: 13.5, color: ds.text2, fontWeight: 500 }}>
            {item.label}
          </Link>
        ))}
      </nav>

      <div style={{ ...cardStyle, boxShadow: "none", borderRadius: 999, display: "flex", alignItems: "center", gap: 10, padding: "6px 6px 6px 14px" }}>
        <span style={{ fontSize: 13.5, color: ds.text, fontWeight: 600 }}>{pessoa.nome}</span>
        <Chip tone="green">{CARGO_LABEL[pessoa.cargo] ?? pessoa.cargo}</Chip>
        <button
          type="button"
          onClick={handleLogout}
          disabled={loggingOut}
          title="Sair e trocar de conta"
          style={{ background: "none", border: "none", fontSize: 13, color: ds.muted, padding: "0 8px", cursor: "pointer", fontFamily: "inherit" }}
        >
          {loggingOut ? "Saindo…" : "Sair"}
        </button>
      </div>
    </header>
  );
}
