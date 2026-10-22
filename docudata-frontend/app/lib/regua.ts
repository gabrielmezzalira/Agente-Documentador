/** Régua única de dificuldade (espelha docudata-backend/services/regua.py). */
export const NIVEIS = [1, 2, 3, 5] as const;
export type Nivel = (typeof NIVEIS)[number];

export const ROTULO_NIVEL: Record<Nivel, string> = {
  1: "simples",
  2: "moderada",
  3: "complexa",
  5: "muito complexa",
};

/** "3 · complexa"; valor fora da régua (task concluída antiga) mostra só o número. */
export function rotuloNivel(p: number): string {
  return (NIVEIS as readonly number[]).includes(p) ? `${p} · ${ROTULO_NIVEL[p as Nivel]}` : `${p}`;
}
