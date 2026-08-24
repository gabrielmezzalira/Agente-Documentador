import Link from "next/link";
import { notFound } from "next/navigation";
import styles from "./subarea.module.css";


export default async function SubareaLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ subarea: string }>;
}>) {
  const { subarea } = await params;
  if (subarea !== "dados" && subarea !== "dev") {
    notFound();
  }

  const label = subarea === "dados" ? "Dados" : "Dev";

  return (
    <div className={`${styles.shell} ${styles[subarea]}`}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href={`/${subarea}`} className={styles.brand} aria-label={`Início da subárea de ${label}`}>
            <span className={styles.brandMark} aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M7 3.75h7l3 3V20.25H7V3.75Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
                <path d="M14 3.75v3h3M9.75 11h4.5M9.75 14.25h4.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span className={styles.brandCopy}>
              <strong>Agente Documentador</strong>
              <small>CITi</small>
            </span>
          </Link>

          <nav className={styles.navigation} aria-label="Navegação da subárea">
            <span className={styles.subareaBadge}>
              <span className={styles.statusDot} aria-hidden="true" />
              {label}
            </span>
            <Link href="/settings" className={styles.navLink}>
              Configurações
            </Link>
            <Link href="/" className={styles.navLink}>
              Trocar subárea
            </Link>
            <Link href={`/${subarea}/projects/new`} className={styles.primaryAction}>
              <span aria-hidden="true">+</span>
              Novo projeto
            </Link>
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
