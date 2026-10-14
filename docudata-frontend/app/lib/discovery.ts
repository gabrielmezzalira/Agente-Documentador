import { API, apiFetch } from "./api";

export type TipoReuniao = "contexto_empresa" | "entrevista_tecnica" | "validacao" | "outra";
export type TipoRequisito = "funcional" | "dados" | "integracao" | "nao_funcional" | "regra_negocio";
export type Lente = "produto" | "dados";
export type Prioridade = "must" | "should" | "could" | "wont";
export type StatusRequisito = "proposto" | "em_revisao" | "validado" | "rejeitado";
export type StatusAnalise = "pendente" | "ok" | "falhou";

export interface Reuniao {
  id: string;
  project_id: string;
  tipo: TipoReuniao;
  origem: string;
  fonte_session_id: string | null;
  ocorrida_em: string | null;
  analise_status: StatusAnalise;
  created_at: string;
}

export interface Requisito {
  id: string;
  project_id: string;
  codigo: string;
  titulo: string;
  descricao: string | null;
  tipo: TipoRequisito;
  lente: Lente | null;
  criterios_aceite: string[];
  prioridade_sugerida: Prioridade;
  justificativa: string | null;
  status: StatusRequisito;
  motivo_decisao: string | null;
  possivel_duplicata_de: string | null;
  conflito: boolean;
  revisado_por: string | null;
  validado_por: string | null;
  funcionalidade_id: string | null;
  n_evidencias: number;
}

export interface Evidencia {
  id: string;
  requisito_id: string;
  reuniao_id: string;
  trecho: string;
  speaker: string | null;
  confianca: number | null;
  created_at: string;
}

export interface TransicaoRequisito {
  id: string;
  requisito_id: string;
  campo: string;
  de: string;
  para: string;
  autor: string | null;
  motivo: string | null;
  timestamp: string;
}

export interface RequisitoDetalhe extends Requisito {
  evidencias: Evidencia[];
  transicoes: TransicaoRequisito[];
}

export interface RequisitoPatch {
  titulo?: string;
  descricao?: string;
  criterios_aceite?: string[];
  prioridade_sugerida?: Prioridade;
  status?: StatusRequisito;
  motivo?: string;
}

export interface Transcricao {
  conteudo: string;
  redigida: boolean;
}

export interface EncaminharBody {
  destino: "dados" | "dev";
  motivo?: string;
  promover_validados: boolean;
}

async function erroDaApi(res: Response, padrao: string): Promise<Error> {
  const detalhe = (await res.json().catch(() => ({}))).detail;
  return new Error(typeof detalhe === "string" ? detalhe : padrao);
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function listRequisitos(projectId: string, status?: StatusRequisito): Promise<Requisito[]> {
  const q = status ? `?status=${status}` : "";
  const res = await apiFetch(`${API}/discovery/projetos/${projectId}/requisitos${q}`);
  if (!res.ok) throw await erroDaApi(res, "Erro ao buscar requisitos");
  return res.json();
}

export async function listReunioes(projectId: string): Promise<Reuniao[]> {
  const res = await apiFetch(`${API}/discovery/projetos/${projectId}/reunioes`);
  if (!res.ok) throw await erroDaApi(res, "Erro ao buscar reuniões");
  return res.json();
}

export async function getRequisito(id: string): Promise<RequisitoDetalhe> {
  const res = await apiFetch(`${API}/discovery/requisitos/${id}`);
  if (!res.ok) throw await erroDaApi(res, "Erro ao buscar o requisito");
  return res.json();
}

export async function patchRequisito(id: string, body: RequisitoPatch): Promise<Requisito> {
  const res = await apiFetch(`${API}/discovery/requisitos/${id}`, { method: "PATCH", headers: JSON_HEADERS, body: JSON.stringify(body) });
  if (!res.ok) throw await erroDaApi(res, "Erro ao alterar o requisito");
  return res.json();
}

export async function promoverRequisito(id: string): Promise<unknown> {
  const res = await apiFetch(`${API}/discovery/requisitos/${id}/promover`, { method: "POST" });
  if (!res.ok) throw await erroDaApi(res, "Erro ao promover o requisito");
  return res.json();
}

export async function reconsolidarProjeto(projectId: string): Promise<void> {
  const res = await apiFetch(`${API}/discovery/projetos/${projectId}/reconsolidar`, { method: "POST" });
  if (!res.ok) throw await erroDaApi(res, "Erro ao reconsolidar os requisitos");
}

export async function reanalisarReuniao(reuniaoId: string): Promise<void> {
  const res = await apiFetch(`${API}/discovery/reunioes/${reuniaoId}/analisar`, { method: "POST" });
  if (!res.ok) throw await erroDaApi(res, "Erro ao reanalisar a reunião");
}

export async function getTranscricao(reuniaoId: string): Promise<Transcricao> {
  const res = await apiFetch(`${API}/discovery/reunioes/${reuniaoId}/transcricao`);
  if (!res.ok) throw await erroDaApi(res, "Erro ao buscar a transcrição");
  return res.json();
}

export async function encaminharProjeto(projectId: string, body: EncaminharBody): Promise<void> {
  const res = await apiFetch(`${API}/projects/${projectId}/encaminhar`, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
  if (!res.ok) throw await erroDaApi(res, "Erro ao encaminhar o projeto");
}

// ---- rótulos e regras de apresentação ----
export const STATUS_LABEL: Record<StatusRequisito, string> = {
  proposto: "Proposto",
  em_revisao: "Em revisão",
  validado: "Validado",
  rejeitado: "Rejeitado",
};

export const PRIORIDADE_LABEL: Record<Prioridade, string> = {
  must: "Must",
  should: "Should",
  could: "Could",
  wont: "Won't",
};

export const TIPO_LABEL: Record<TipoRequisito, string> = {
  funcional: "Funcional",
  dados: "Dados",
  integracao: "Integração",
  nao_funcional: "Não funcional",
  regra_negocio: "Regra de negócio",
};

export const TIPO_REUNIAO_LABEL: Record<TipoReuniao, string> = {
  contexto_empresa: "Contexto da empresa",
  entrevista_tecnica: "Entrevista técnica",
  validacao: "Validação",
  outra: "Reunião",
};

const NIVEL: Record<string, number> = { operacional: 0, gerente: 1, lider: 2, owner: 3 };

export function nivelDoCargo(cargo: string | undefined): number {
  return cargo ? (NIVEL[cargo] ?? -1) : -1;
}

/** Transições permitidas (espelham as regras do backend; o backend continua sendo a fonte de verdade). */
export interface AcaoStatus {
  para: StatusRequisito;
  rotulo: string;
  cargoMinimo: "operacional" | "gerente";
  exigeMotivo: boolean;
}

const ACOES: Record<StatusRequisito, AcaoStatus[]> = {
  proposto: [
    { para: "em_revisao", rotulo: "Marcar em revisão", cargoMinimo: "operacional", exigeMotivo: false },
    { para: "rejeitado", rotulo: "Rejeitar", cargoMinimo: "gerente", exigeMotivo: true },
  ],
  em_revisao: [
    { para: "validado", rotulo: "Validar", cargoMinimo: "gerente", exigeMotivo: false },
    { para: "rejeitado", rotulo: "Rejeitar", cargoMinimo: "gerente", exigeMotivo: true },
  ],
  validado: [{ para: "rejeitado", rotulo: "Rejeitar", cargoMinimo: "gerente", exigeMotivo: true }],
  rejeitado: [{ para: "proposto", rotulo: "Reabrir como proposto", cargoMinimo: "gerente", exigeMotivo: true }],
};

export function acoesDisponiveis(status: StatusRequisito, cargo: string | undefined): AcaoStatus[] {
  return ACOES[status].filter((a) => nivelDoCargo(cargo) >= nivelDoCargo(a.cargoMinimo));
}

/** Operacional edita só antes de validar; gerente ou acima edita sempre. */
export function podeEditar(status: StatusRequisito, cargo: string | undefined): boolean {
  return nivelDoCargo(cargo) >= NIVEL.gerente || status === "proposto" || status === "em_revisao";
}

export function podePromover(req: Pick<Requisito, "status" | "funcionalidade_id">, cargo: string | undefined): boolean {
  return nivelDoCargo(cargo) >= NIVEL.gerente && req.status === "validado" && !req.funcionalidade_id;
}
