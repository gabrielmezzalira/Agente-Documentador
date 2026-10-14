"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import type { MeResponse } from "../../lib/api";
import ChooserHeader from "./ChooserHeader";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { subareaFromPath } from "./navItems";
import styles from "./shell.module.css";

/**
 * Casca das telas autenticadas: menu lateral + barra superior + conteúdo.
 * Na escolha de subárea ("/") a casca é outra: cabeçalho horizontal, sem menu lateral.
 */
export default function AppShell({ pessoa, children }: { pessoa: MeResponse; children: ReactNode }) {
  const pathname = usePathname();
  const subarea = subareaFromPath(pathname) ?? "dados";
  const isChooser = pathname === "/";

  if (isChooser) {
    return (
      <div className={styles.chooser}>
        <ChooserHeader pessoa={pessoa} />
        {children}
      </div>
    );
  }

  return (
    <div className={styles.root}>
      <Sidebar pessoa={pessoa} subarea={subarea} includeProjects />
      <div className={styles.main}>
        <Topbar subarea={subarea} />
        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
