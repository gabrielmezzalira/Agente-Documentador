import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agente Documentador",
  description: "Documentação automática de projetos de dados",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
