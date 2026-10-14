"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getMe, type MeResponse } from "../lib/api";
import AppShell from "./shell/AppShell";

// Rotas que quem está deslogado precisa abrir — inclui o fluxo de senha,
// senão o guard manda de volta pro /login e o link parece não fazer nada.
const PUBLIC_PATHS = new Set(["/login", "/cadastro", "/esqueci-senha", "/redefinir-senha"]);

const AuthContext = createContext<MeResponse | null>(null);

export function useAuth(): MeResponse | null {
  return useContext(AuthContext);
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
      {pessoa ? <AppShell pessoa={pessoa}>{children}</AppShell> : children}
    </AuthContext.Provider>
  );
}
