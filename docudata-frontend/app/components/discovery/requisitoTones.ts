import type { Tone } from "../../lib/ds";
import type { Prioridade, StatusAnalise, StatusRequisito } from "../../lib/discovery";

export const STATUS_TONE: Record<StatusRequisito, Tone> = {
  proposto: "neutral",
  em_revisao: "amber",
  validado: "green",
  rejeitado: "red",
};

export const PRIORIDADE_TONE: Record<Prioridade, Tone> = {
  must: "red",
  should: "amber",
  could: "neutral",
  wont: "neutral",
};

export const ANALISE_TONE: Record<StatusAnalise, Tone> = {
  pendente: "amber",
  ok: "green",
  falhou: "red",
};

export const ANALISE_LABEL: Record<StatusAnalise, string> = {
  pendente: "Analisando",
  ok: "Analisada",
  falhou: "Falhou",
};
