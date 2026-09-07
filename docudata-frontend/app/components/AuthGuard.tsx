"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getMe, logout, type MeResponse } from "../lib/api";

const PUBLIC_PATHS = new Set(["/login", "/cadastro"]);

const AuthContext = createContext<MeResponse | null>(null);

export function useAuth(): MeResponse | null {
  return useContext(AuthContext);
}

const CARGO_LABEL: Record<string, string> = {
  owner: "Owner",
  lider: "Líder",
  gerente: "Gerente",
  operacional: "Operacional",
};

function UserBadge({ pessoa }: { pessoa: MeResponse }) {
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      // Recarrega em vez de só navegar — zera qualquer estado em memória de
      // outras telas (ex: dados carregados como a conta anterior) antes de
      // trocar de conta para testar outro nível de acesso.
      window.location.href = "/login";
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        top: 14,
        right: 16,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        gap: 8,
        background: "#fff",
        border: "1px solid #e8e8ed",
        borderRadius: 999,
        padding: "6px 8px 6px 14px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
        fontSize: 12,
      }}
    >
      <span style={{ color: "#374151", fontWeight: 600 }}>{pessoa.nome}</span>
      <span
        style={{
          background: "#f1f5f9",
          color: "#475569",
          borderRadius: 999,
          padding: "2px 9px",
          fontWeight: 700,
          fontSize: 11,
        }}
      >
        {CARGO_LABEL[pessoa.cargo] ?? pessoa.cargo}
      </span>
      <button
        onClick={handleLogout}
        disabled={loggingOut}
        style={{
          background: "none",
          border: "none",
          color: "#9696a0",
          fontSize: 12,
          fontWeight: 600,
          cursor: "pointer",
          padding: "4px 8px",
        }}
        title="Sair e trocar de conta"
      >
        {loggingOut ? "Saindo..." : "Sair"}
      </button>
    </div>
  );
}

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [pessoa, setPessoa] = useState<MeResponse | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (PUBLIC_PATHS.has(pathname)) {
      setChecked(true);
      return;
    }
    getMe()
      .then((me) => {
        setPessoa(me);
        setChecked(true);
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [pathname, router]);

  if (PUBLIC_PATHS.has(pathname)) {
    return <>{children}</>;
  }

  if (!checked) {
    return null;
  }

  return (
    <AuthContext.Provider value={pessoa}>
      {pessoa && <UserBadge pessoa={pessoa} />}
      {children}
    </AuthContext.Provider>
  );
}
