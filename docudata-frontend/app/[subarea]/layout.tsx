import { notFound } from "next/navigation";

const SUBAREAS = new Set(["dados", "dev", "produto"]);

/** Valida a subárea da URL. O cabeçalho agora vive na casca global (components/shell). */
export default async function SubareaLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ subarea: string }>;
}>) {
  const { subarea } = await params;
  if (!SUBAREAS.has(subarea)) {
    notFound();
  }
  return <>{children}</>;
}
