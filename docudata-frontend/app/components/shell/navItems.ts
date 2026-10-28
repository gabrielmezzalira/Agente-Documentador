import type { Cargo } from "../../lib/api";

export const SUBAREAS = [
  { slug: "dados", label: "Dados" },
  { slug: "dev", label: "Dev" },
] as const;

export type SubareaSlug = (typeof SUBAREAS)[number]["slug"];

export function subareaFromPath(pathname: string): SubareaSlug | null {
  const first = pathname.split("/")[1];
  return SUBAREAS.find((s) => s.slug === first)?.slug ?? null;
}

export interface NavItem {
  href: string;
  label: string;
  /** Rotas que também deixam o item ativo. */
  active: (pathname: string) => boolean;
}

const isOwnerOrLider = (c?: Cargo) => c === "owner" || c === "lider";
const canConfigure = (c?: Cargo) => isOwnerOrLider(c) || c === "gerente";

/** Itens do menu lateral, na ordem do protótipo, respeitando o cargo (mesmas regras do seletor de subárea). */
export function navItemsFor(cargo: Cargo | undefined, subarea: SubareaSlug, includeProjects: boolean): NavItem[] {
  const items: NavItem[] = [];
  if (includeProjects) {
    items.push({ href: `/${subarea}`, label: "Projetos", active: (p) => SUBAREAS.some((s) => p === `/${s.slug}` || p.startsWith(`/${s.slug}/`)) });
  }
  if (isOwnerOrLider(cargo)) items.push({ href: "/performance", label: "Performance", active: (p) => p.startsWith("/performance") });
  if (isOwnerOrLider(cargo)) items.push({ href: "/acompanhamento", label: "Acompanhamento", active: (p) => p.startsWith("/acompanhamento") });
  if (isOwnerOrLider(cargo)) items.push({ href: "/classificador", label: "Classificador", active: (p) => p.startsWith("/classificador") });
  if (canConfigure(cargo)) items.push({ href: "/avaliacoes", label: "Avaliações", active: (p) => p.startsWith("/avaliacoes") });
  if (isOwnerOrLider(cargo)) items.push({ href: "/pessoas", label: "Pessoas", active: (p) => p.startsWith("/pessoas") });
  items.push({ href: "/metodologia", label: "Documentos", active: (p) => p.startsWith("/metodologia") });
  if (canConfigure(cargo)) items.push({ href: "/settings", label: "Configurações", active: (p) => p.startsWith("/settings") });
  return items;
}

export const CARGO_LABEL: Record<Cargo, string> = {
  owner: "Owner",
  lider: "Líder",
  gerente: "Gerente",
  operacional: "Operacional",
};

export function initialsOf(nome: string): string {
  const parts = nome.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}
