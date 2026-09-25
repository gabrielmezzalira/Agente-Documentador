export type ModoTrabalho = "ATRIBUICAO" | "PULL";

// Ordem das perguntas do questionário. resposta_6 (Evolução) saiu em
// 2026-09-23 — por isso a 6ª pergunta grava em resposta_7.
export const CAMPOS_RESPOSTA = [
  "resposta_1",
  "resposta_2",
  "resposta_3",
  "resposta_4",
  "resposta_5",
  "resposta_7",
] as const;

export type CampoResposta = (typeof CAMPOS_RESPOSTA)[number];

export function perguntas(modoTrabalho: ModoTrabalho): string[] {
  return [
    modoTrabalho === "PULL"
      ? "Puxou e entregou num ritmo consistente?"
      : "Entregou o que se comprometeu dentro do combinado nesta sprint?",
    "A qualidade da entrega precisou de pouca ou nenhuma correção?",
    "A pessoa destravou sozinha antes de te escalar?",
    "A comunicação da entrega foi clara a ponto de você não precisar perguntar?",
    "Ajudou, desbloqueou ou ensinou outro membro nesta sprint?",
    "Trouxe algo além do que foi pedido?",
  ];
}

// Mesma escala da dimensão Gerente no ranking: média 0-5 (2 casas) × 20.
export function mediaGerente100(r: Record<CampoResposta, number>): number {
  const soma = CAMPOS_RESPOSTA.reduce((acc, c) => acc + r[c], 0);
  const media = Math.round((soma / CAMPOS_RESPOSTA.length) * 100) / 100;
  return Math.round(media * 20 * 100) / 100;
}
