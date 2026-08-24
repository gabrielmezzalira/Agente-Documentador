const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ValidationError422 {
  tipo_detectado: string;
  tipo_esperado: string;
  mensagem: string;
  pode_forcar: boolean;
}

export class ValidationError extends Error {
  readonly detail: ValidationError422;
  constructor(detail: ValidationError422) {
    super(detail.mensagem);
    this.name = "ValidationError";
    this.detail = detail;
  }
}

export interface Project {
  id: string;
  name: string;
  client: string;
  description?: string;
  budget_usd?: number | null;
  has_api_key: boolean;
  is_delivered: boolean;
  created_at: string;
  last_ingestion_at?: string | null;
}

export interface StackSearchResult {
  project_id: string;
  project_name: string;
  client: string;
  sprints: number[];
  sample_context: string;
}

export interface StackSearchResponse {
  query: string;
  results: StackSearchResult[];
}

export interface ProjectCost {
  project_id: string;
  total_usd: number;
  budget_usd?: number | null;
  input_tokens: number;
  output_tokens: number;
}

export interface UsageBucket {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  count: number;
}

export interface UsageItem {
  source: "ingestion" | "generated_doc";
  id: string;
  label: string;
  created_at: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface ProjectUsage {
  project_id: string;
  month: string;          // formato YYYY-MM
  total_usd: number;
  input_tokens: number;
  output_tokens: number;
  breakdown: Record<string, UsageBucket>;
  items: UsageItem[];
  truncated: boolean;
}

export interface Ingestion {
  id: string;
  project_id: string;
  sprint_number: number;
  file_name?: string;
  file_type?: string;
  tipo_documentacao?: "planning" | "daily" | "review" | "outro" | "commit" | null;
  extracted_content?: {
    resumo?: string;
    tarefas?: string[];
    decisoes?: string[];
    problemas?: string[];
    contexto_cliente?: string;
    proximos_passos?: string[];
    tecnologias?: string[];
    _meta_autor?: string;
    _meta_data_commit?: string;
    _meta_commit_msg?: string;
    _meta_branch?: string;
  };
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  created_at: string;
}

export interface GeneratedDoc {
  id: string;
  doc_type: string;
  sprint_number?: number;
  content: string;
  created_at: string;
}

export type SprintHealth = "verde" | "amarelo" | "vermelho";

export interface Sprint {
  id: string;
  project_id: string;
  numero: number;
  status_saude?: SprintHealth | null;
  plano_correcao?: string | null;
  created_at: string;
  updated_at: string;
}

/** Retorno do GET /projects/{id}/sprints — Sprint + agregados de mínimo obrigatório. */
export interface SprintWithStatus extends Sprint {
  tem_planning: boolean;
  tem_review: boolean;
  dailys_count: number;
  ingestions_count: number;
  docs_gerados_count: number;
  pendencias: string[];          // subset de ['planning','review']
}

export interface TechTimelineEntry {
  tecnologia: string;
  introduzida_em: number;
  abandonada_em: number | null;   // null = ainda em uso
}

export interface TechTimeline {
  em_uso_atual: string[];
  timeline: TechTimelineEntry[];
}

export type SprintDocType = "planning" | "daily" | "review";

export interface SprintDocResponse {
  ingestion_id: string;
  doc_id: string;
  doc_type: SprintDocType;
  sprint_number: number;
  content: string;
  created_at: string;
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(`${API}/projects`);
  if (!res.ok) throw new Error("Erro ao buscar projetos");
  return res.json();
}

export async function getProject(id: string): Promise<Project> {
  const res = await fetch(`${API}/projects/${id}`);
  if (!res.ok) throw new Error("Projeto não encontrado");
  return res.json();
}

export async function getProjectCost(projectId: string): Promise<ProjectCost> {
  const res = await fetch(`${API}/projects/${projectId}/cost`);
  if (!res.ok) throw new Error("Erro ao buscar custo do projeto");
  return res.json();
}

export async function getProjectUsage(projectId: string, month?: string): Promise<ProjectUsage> {
  const url = `${API}/projects/${projectId}/usage${month ? `?month=${month}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Erro ao buscar uso mensal do projeto");
  return res.json();
}

export async function updateApiKey(projectId: string, key: string | null): Promise<Project> {
  const res = await fetch(`${API}/projects/${projectId}/api-key`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gemini_api_key: key }),
  });
  if (!res.ok) throw new Error("Erro ao atualizar chave de API");
  return res.json();
}

export async function createProject(data: {
  name: string;
  client: string;
  description?: string;
  squad?: string;
  budget_usd?: number | null;
  gemini_api_key?: string;
}): Promise<Project> {
  const res = await fetch(`${API}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Erro ao criar projeto");
  return res.json();
}

export async function ingestFile(
  projectId: string,
  sprintNumber: number,
  file: File,
  force?: boolean
): Promise<{ status: string; sprint: number; tentativas: number }> {
  const form = new FormData();
  form.append("arquivo", file);
  form.append("sprint_numero", String(sprintNumber));
  form.append("projeto_id", projectId);
  if (force) form.append("force", "true");

  const res = await fetch(`${API}/ingest`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    if (res.status === 422 && err.detail && typeof err.detail === "object" && err.detail.tipo_detectado) {
      throw new ValidationError(err.detail as ValidationError422);
    }
    throw new Error(typeof err.detail === "string" ? err.detail : "Erro ao processar arquivo");
  }
  return res.json();
}

export async function listIngestions(projectId: string): Promise<Ingestion[]> {
  const res = await fetch(`${API}/ingestions/${projectId}`);
  if (!res.ok) throw new Error("Erro ao buscar ingestões");
  return res.json();
}

export async function deleteProject(id: string): Promise<void> {
  const res = await fetch(`${API}/projects/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Erro ao excluir projeto");
}

export async function listDocs(projectId: string): Promise<GeneratedDoc[]> {
  const res = await fetch(`${API}/docs/${projectId}`);
  if (!res.ok) throw new Error("Erro ao buscar documentos");
  return res.json();
}

export async function deleteDoc(docId: string): Promise<void> {
  const res = await fetch(`${API}/docs/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Erro ao excluir documento");
}

export async function toggleDelivered(projectId: string): Promise<Project> {
  const res = await fetch(`${API}/projects/${projectId}/delivered`, { method: "PATCH" });
  if (!res.ok) throw new Error("Erro ao atualizar status do projeto");
  return res.json();
}

export async function searchStack(query: string): Promise<StackSearchResponse> {
  const res = await fetch(`${API}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error("Erro ao buscar stack");
  return res.json();
}

export async function listSprints(projectId: string): Promise<SprintWithStatus[]> {
  const res = await fetch(`${API}/projects/${projectId}/sprints`);
  if (!res.ok) throw new Error("Erro ao buscar sprints");
  return res.json();
}

export async function deleteSprint(sprintId: string): Promise<void> {
  const res = await fetch(`${API}/sprints/${sprintId}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao excluir sprint");
  }
}

export async function createSprint(projectId: string, numero?: number): Promise<Sprint> {
  const res = await fetch(`${API}/projects/${projectId}/sprints`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ numero: numero ?? null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao criar sprint");
  }
  return res.json();
}

export async function getTechnologies(projectId: string): Promise<TechTimeline> {
  const res = await fetch(`${API}/projects/${projectId}/technologies`);
  if (!res.ok) throw new Error("Erro ao buscar tecnologias do projeto");
  return res.json();
}

export async function updateSprintHealth(
  sprintId: string,
  statusSaude: SprintHealth | null,
  planoCorrecao?: string | null
): Promise<Sprint> {
  const res = await fetch(`${API}/sprints/${sprintId}/health`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status_saude: statusSaude,
      plano_correcao: planoCorrecao ?? null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao atualizar saúde da sprint");
  }
  return res.json();
}

async function _postSprintDoc(path: string, form: FormData): Promise<SprintDocResponse> {
  const res = await fetch(`${API}/sprint-docs/${path}`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    if (res.status === 422 && err.detail && typeof err.detail === "object" && err.detail.tipo_detectado) {
      throw new ValidationError(err.detail as ValidationError422);
    }
    throw new Error(typeof err.detail === "string" ? err.detail : "Erro ao registrar documento de sprint");
  }
  return res.json();
}

export async function submitPlanning(input: {
  projetoId: string;
  sprintNumero: number;
  descricao: string;
  itensBacklog: { item: string; responsavel?: string; prazo?: string; criterio?: string }[];
  dependenciasItems?: { item: string; prazo?: string; consequencia?: string; confianca?: string }[];
  riscosItems?: { risco: string; consequencia?: string }[];
  carryOverItems?: { item: string; causa_raiz?: string }[];
  periodoInicio?: string;
  periodoFim?: string;
  horasDisponiveis?: number;
  horasEstimadas?: number;
  dependenciasCliente?: string;
  carryOver?: string;
  anexo?: File | null;
  force?: boolean;
}): Promise<SprintDocResponse> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("sprint_numero", String(input.sprintNumero));
  form.append("descricao", input.descricao);
  form.append("itens_backlog", JSON.stringify(input.itensBacklog));
  if (input.periodoInicio) form.append("periodo_inicio", input.periodoInicio);
  if (input.periodoFim) form.append("periodo_fim", input.periodoFim);
  if (input.horasDisponiveis != null) form.append("horas_disponiveis", String(input.horasDisponiveis));
  if (input.horasEstimadas != null) form.append("horas_estimadas", String(input.horasEstimadas));
  if (input.dependenciasItems?.length) form.append("dependencias_items", JSON.stringify(input.dependenciasItems));
  if (input.riscosItems?.length) form.append("riscos_items", JSON.stringify(input.riscosItems));
  if (input.carryOverItems?.length) form.append("carry_over_items", JSON.stringify(input.carryOverItems));
  if (input.anexo) form.append("anexo", input.anexo);
  if (input.force) form.append("force", "true");
  return _postSprintDoc("planning", form);
}

export async function submitDaily(input: {
  projetoId: string;
  sprintNumero: number;
  data: string;            // YYYY-MM-DD
  feito: string;
  proximo: string;
  impedimentos?: string;
  anexo?: File | null;
  force?: boolean;
}): Promise<SprintDocResponse> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("sprint_numero", String(input.sprintNumero));
  form.append("data", input.data);
  form.append("feito", input.feito);
  form.append("proximo", input.proximo);
  if (input.impedimentos) form.append("impedimentos", input.impedimentos);
  if (input.anexo) form.append("anexo", input.anexo);
  if (input.force) form.append("force", "true");
  return _postSprintDoc("daily", form);
}

export async function submitReview(input: {
  projetoId: string;
  sprintNumero: number;
  observacoes?: string;
  percepcaoCliente?: string;
  sinalSatisfacao?: string;
  pedidosForaEscopo?: string;
  // Template 2 CITi
  squad?: string;
  periodoInicio?: string;
  periodoFim?: string;
  subarea?: string;
  itensPlanejadasEntregues?: { item: string; entregue: string; motivo_nao: string; causa_raiz_num: string }[];
  percentualItensProntos?: string;
  pedidosForaEscopoItens?: { data: string; descricao: string; status: string }[];
  itensProximaSprint?: { item: string; causa_raiz_num: string }[];
  anexo?: File | null;
  force?: boolean;
}): Promise<SprintDocResponse> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("sprint_numero", String(input.sprintNumero));
  if (input.observacoes) form.append("observacoes", input.observacoes);
  if (input.percepcaoCliente) form.append("percepcao_cliente", input.percepcaoCliente);
  if (input.sinalSatisfacao) form.append("sinal_satisfacao", input.sinalSatisfacao);
  if (input.pedidosForaEscopo) form.append("pedidos_fora_escopo", input.pedidosForaEscopo);
  if (input.squad) form.append("squad", input.squad);
  if (input.periodoInicio) form.append("periodo_inicio", input.periodoInicio);
  if (input.periodoFim) form.append("periodo_fim", input.periodoFim);
  if (input.subarea) form.append("subarea", input.subarea);
  if (input.itensPlanejadasEntregues?.length) form.append("itens_planejados_entregues", JSON.stringify(input.itensPlanejadasEntregues));
  if (input.percentualItensProntos) form.append("percentual_itens_prontos", input.percentualItensProntos);
  if (input.pedidosForaEscopoItens?.length) form.append("pedidos_fora_escopo_itens", JSON.stringify(input.pedidosForaEscopoItens));
  if (input.itensProximaSprint?.length) form.append("itens_proxima_sprint", JSON.stringify(input.itensProximaSprint));
  if (input.anexo) form.append("anexo", input.anexo);
  if (input.force) form.append("force", "true");
  return _postSprintDoc("review", form);
}

export async function submitRetrospectiva(input: {
  projetoId: string;
  sprintNumero: number;
  observacoes?: string;
  pedidoForaEscopoStatus?: string;
  // Template 3 CITi
  squad?: string;
  periodoInicio?: string;
  periodoFim?: string;
  subarea?: string;
  oQueFuncionou?: string[];
  oQueNaoFuncionou?: string[];
  causaRaizImpacto?: { causa_raiz_num: string; impacto: string }[];
  acoesMelhoria?: { acao: string; responsavel: string; prazo: string }[];
  houvePedidoForaEscopo?: string;
  statusPedidoForaEscopo?: string;
  anexo?: File | null;
  force?: boolean;
}): Promise<SprintDocResponse> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("sprint_numero", String(input.sprintNumero));
  if (input.observacoes) form.append("observacoes", input.observacoes);
  if (input.pedidoForaEscopoStatus) form.append("pedido_fora_escopo_status", input.pedidoForaEscopoStatus);
  if (input.squad) form.append("squad", input.squad);
  if (input.periodoInicio) form.append("periodo_inicio", input.periodoInicio);
  if (input.periodoFim) form.append("periodo_fim", input.periodoFim);
  if (input.subarea) form.append("subarea", input.subarea);
  if (input.oQueFuncionou?.length) form.append("o_que_funcionou", JSON.stringify(input.oQueFuncionou));
  if (input.oQueNaoFuncionou?.length) form.append("o_que_nao_funcionou", JSON.stringify(input.oQueNaoFuncionou));
  if (input.causaRaizImpacto?.length) form.append("causa_raiz_impacto", JSON.stringify(input.causaRaizImpacto));
  if (input.acoesMelhoria?.length) form.append("acoes_melhoria", JSON.stringify(input.acoesMelhoria));
  if (input.houvePedidoForaEscopo) form.append("houve_pedido_fora_escopo", input.houvePedidoForaEscopo);
  if (input.statusPedidoForaEscopo) form.append("status_pedido_fora_escopo", input.statusPedidoForaEscopo);
  if (input.anexo) form.append("anexo", input.anexo);
  if (input.force) form.append("force", "true");
  return _postSprintDoc("retrospectiva", form);
}

export async function submitAtaUpload(input: {
  projetoId: string;
  sprintNumero: number;
  anexo: File;       // obrigatório — PDF da transcrição
  force?: boolean;
}): Promise<SprintDocResponse> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("sprint_numero", String(input.sprintNumero));
  form.append("anexo", input.anexo);
  if (input.force) form.append("force", "true");
  return _postSprintDoc("ata", form);
}

export async function createManualDoc(input: {
  projetoId: string;
  docType: string;
  sprintNumero?: number | null;
  content: string;
}): Promise<GeneratedDoc> {
  const res = await fetch(`${API}/docs/manual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      projeto_id: input.projetoId,
      doc_type: input.docType,
      sprint_numero: input.sprintNumero ?? null,
      content: input.content,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao criar documento manual");
  }
  return res.json();
}

export async function uploadManualDocPdf(input: {
  projetoId: string;
  docType: string;
  sprintNumero?: number | null;
  arquivo: File;
}): Promise<GeneratedDoc> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("doc_type", input.docType);
  if (input.sprintNumero != null) form.append("sprint_numero", String(input.sprintNumero));
  form.append("arquivo", input.arquivo);
  const res = await fetch(`${API}/docs/manual/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao subir PDF do documento manual");
  }
  return res.json();
}

export async function exportToGdocs(docId: string): Promise<{ url: string }> {
  const res = await fetch(`${API}/docs/${docId}/export-gdocs`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao exportar para Google Docs");
  }
  return res.json();
}

export async function listIngestionsBySprint(projetoId: string, sprint: number): Promise<Ingestion[]> {
  const res = await fetch(`${API}/ingestions/${projetoId}/${sprint}`);
  if (!res.ok) throw new Error("Erro ao buscar ingestões da sprint");
  return res.json();
}

export interface EnrichResult {
  // planning
  descricao?: string;
  itens_backlog?: { item: string; responsavel: string; prazo: string; criterio: string }[];
  horas_disponiveis?: number | null;
  horas_estimadas?: number | null;
  periodo_inicio?: string | null;
  periodo_fim?: string | null;
  dependencias_items?: { item: string; prazo: string; consequencia: string; confianca: string }[];
  riscos_items?: { risco: string; consequencia: string }[];
  carry_over_items?: { item: string; causa_raiz: string }[];
  // daily
  data?: string | null;
  feito?: string;
  proximo?: string;
  impedimentos?: string | null;
  // review — campos base
  observacoes?: string | null;
  percepcao_cliente?: string | null;
  sinal_satisfacao?: string | null;
  pedidos_fora_escopo?: string | null;
  // review — Template 2 CITi
  squad?: string | null;
  subarea?: string | null;
  itens_planejados_entregues?: { item: string; entregue: string; motivo_nao: string; causa_raiz_num: string }[];
  percentual_itens_prontos?: string | null;
  pedidos_fora_escopo_itens?: { data: string; descricao: string; status: string }[];
  itens_proxima_sprint?: { item: string; causa_raiz_num: string }[];
  // retrospectiva — campos base
  pedido_fora_escopo_status?: string | null;
  // retrospectiva — Template 3 CITi
  o_que_funcionou?: string[];
  o_que_nao_funcionou?: string[];
  causa_raiz_impacto?: { causa_raiz_num: string; impacto: string }[];
  acoes_melhoria?: { acao: string; responsavel: string; prazo: string }[];
  houve_pedido_fora_escopo?: string | null;
  status_pedido_fora_escopo?: string | null;
}

export async function enrichContent(input: {
  projetoId: string;
  docType: string;
  texto?: string;
  arquivo?: File | null;
}): Promise<EnrichResult> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("doc_type", input.docType);
  if (input.texto) form.append("texto", input.texto);
  if (input.arquivo) form.append("arquivo", input.arquivo);
  const res = await fetch(`${API}/enrich`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao analisar conteúdo");
  }
  return res.json();
}

export async function deleteIngestion(ingestionId: string): Promise<void> {
  const res = await fetch(`${API}/ingestions/${ingestionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Erro ao excluir ingestão");
}

export async function moveIngestion(ingestionId: string, sprintNumber: number): Promise<Ingestion> {
  const res = await fetch(`${API}/ingestions/${ingestionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sprint_number: sprintNumber }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao mover ingestão");
  }
  return res.json();
}

export async function moveDoc(docId: string, sprintNumber: number | null): Promise<GeneratedDoc> {
  const res = await fetch(`${API}/docs/${docId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sprint_number: sprintNumber }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao mover documento");
  }
  return res.json();
}

export async function generateDoc(
  projectId: string,
  tipoDoc: string,
  sprintNumero?: number,
  ingestionId?: string,
  observacoes?: string
): Promise<GeneratedDoc> {
  const res = await fetch(`${API}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      projeto_id: projectId,
      tipo_doc: tipoDoc,
      sprint_numero: sprintNumero ?? null,
      ingestion_id: ingestionId ?? null,
      observacoes: observacoes || null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao gerar documento");
  }
  return res.json();
}

export interface FuncionalidadeResponse {
  id: string;
  project_id: string;
  id_funcional: string;
  titulo: string;
  descricao?: string;
  criterios_aceite: string[];
  prioridade: string;
  status: "nao_iniciada" | "em_andamento" | "em_ajuste" | "concluida";
  status_cliente: "nao_enviado" | "enviado" | "aprovado" | "rejeitado" | "ajuste_pedido";
  data_aprovacao_cliente?: string | null;
  responsavel?: string | null;
  sprint_alvo?: string | null;
  created_at: string;
}

export interface BlocoA {
  sem_dados: boolean;
  pct_prazo_consumido?: number;
  pct_escopo_concluido?: number;
  pct_aprovado_cliente?: number;
  desvio_detectado?: boolean;
  desvio_pontos?: number;
}

export interface AchadoCritico {
  severidade: "CRITICA" | "ALTA";
  confianca: "ALTA";
  referencia: string;
  descricao_tecnica: string;
  descricao_gerente: string;
}

export interface BlocoB {
  travadas: Array<{ id: string; titulo: string; dias: number }>;
  aguardando_cliente: Array<{ id: string; titulo: string; dias_uteis: number }>;
  em_ajuste: Array<{ id: string; titulo: string }>;
  achados_criticos?: AchadoCritico[];
  relatorio_gerente?: string | null;
  relatorio_tecnico?: string | null;
  data_revisao?: string | null;
  funcionalidades_com_aceite_falhando?: Array<{ id: string; titulo: string }>;
}

export interface BlocoC {
  throughput_por_semana: number | null;
  wip: number;
  cycle_time_p50_dias: number | null;
  cycle_time_p85_dias: number | null;
  total_concluidas: number;
}

export interface FaseResumo {
  media_dias: number;
  p85_dias: number | null;
  amostras: number;
}

export interface BlocoD {
  fases_resumo: Record<string, FaseResumo>;
  eficiencia_fluxo_pct: number | null;
  detalhe_por_funcionalidade: Array<{
    id: string;
    titulo: string;
    tempos_por_fase: Record<string, number>;
  }>;
}

export interface PainelData {
  bloco_a: BlocoA;
  bloco_b: BlocoB;
  bloco_c: BlocoC;
  bloco_d: BlocoD;
  cobertura_aceite?: number | null;
}

export async function getPainel(projectId: string): Promise<PainelData> {
  const res = await fetch(`${API}/projects/${projectId}/painel`);
  if (!res.ok) throw new Error("Erro ao buscar painel");
  return res.json();
}

export async function listFuncionalidades(projectId: string): Promise<FuncionalidadeResponse[]> {
  const res = await fetch(`${API}/funcionalidades?project_id=${projectId}`);
  if (!res.ok) throw new Error("Erro ao buscar funcionalidades");
  return res.json();
}

export interface FuncionalidadeProposta {
  id_funcional: string;
  titulo: string;
  descricao?: string;
  criterios_aceite: string[];
  prioridade: string;
}

export async function importarFuncionalidades(
  projectId: string,
  textoContrato: string,
): Promise<FuncionalidadeProposta[]> {
  const res = await fetch(`${API}/funcionalidades/importar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, texto_contrato: textoContrato }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao importar funcionalidades");
  }
  const data = await res.json();
  return data.propostas as FuncionalidadeProposta[];
}

export async function importarFuncionalidadesArquivo(
  projectId: string,
  arquivo: File,
): Promise<FuncionalidadeProposta[]> {
  const form = new FormData();
  form.append("project_id", projectId);
  form.append("arquivo", arquivo);
  const res = await fetch(`${API}/funcionalidades/importar/arquivo`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao importar arquivo");
  }
  const data = await res.json();
  return data.propostas as FuncionalidadeProposta[];
}

export async function updateFuncionalidade(
  id: string,
  data: {
    titulo?: string;
    descricao?: string;
    criterios_aceite?: string[];
    prioridade?: string;
    responsavel?: string;
    id_funcional?: string;
  },
): Promise<FuncionalidadeResponse> {
  const res = await fetch(`${API}/funcionalidades/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao atualizar funcionalidade");
  }
  return res.json();
}

export async function createFuncionalidade(data: {
  project_id: string;
  id_funcional: string;
  titulo: string;
  descricao?: string;
  criterios_aceite: string[];
  prioridade: string;
  responsavel?: string;
}): Promise<FuncionalidadeResponse> {
  const res = await fetch(`${API}/funcionalidades`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao criar funcionalidade");
  }
  return res.json();
}

export async function confirmarImportacao(
  projectId: string,
  itens: { proposta: FuncionalidadeProposta; confirmed: boolean }[],
): Promise<FuncionalidadeResponse[]> {
  const res = await fetch(`${API}/funcionalidades/importar/confirmar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, itens }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao confirmar importação");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Composer de Planning — interfaces e funções
// ---------------------------------------------------------------------------

export interface DadosJson {
  funcionalidades_selecionadas: string[];
  recortes: Record<string, number[]>;
  alocacoes: Record<string, string>;
  transbordos: string[];
  detalhes?: Record<string, string>;
  objetivo_sprint?: string;
}

export interface RascunhoData {
  id: string;
  project_id: string;
  sprint_numero: number;
  step_atual: number;
  dados_json: DadosJson;
  created_at: string;
  updated_at: string;
}

export interface TransbordoItem {
  id: string;
  titulo: string;
  sprint_alvo: string;
  status: string;
  criterios_aceite: string[];
}

export interface GetRascunhoResponse {
  rascunho: RascunhoData;
  throughput_ref: number | null;
  transbordos: TransbordoItem[];
}

export interface GerarResponse {
  markdown: string;
}

export interface ConfirmarResponse {
  doc_id: string;
  content: string;
  created_at: string;
}

export async function getRascunho(
  projectId: string,
  sprintNumero: number
): Promise<GetRascunhoResponse> {
  const res = await fetch(`${API}/composer/rascunho/${projectId}/${sprintNumero}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao buscar rascunho");
  }
  return res.json();
}

export async function patchRascunho(
  projectId: string,
  sprintNumero: number,
  payload: { step_atual: number; dados_json: DadosJson }
): Promise<RascunhoData> {
  const res = await fetch(`${API}/composer/rascunho/${projectId}/${sprintNumero}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao salvar rascunho");
  }
  return res.json();
}

export async function gerarPlanning(
  projectId: string,
  sprintNumero: number
): Promise<GerarResponse> {
  const res = await fetch(`${API}/composer/gerar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, sprint_numero: sprintNumero }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao gerar planning");
  }
  return res.json();
}

export async function confirmarPlanning(
  projectId: string,
  sprintNumero: number,
  markdown: string
): Promise<ConfirmarResponse> {
  const res = await fetch(`${API}/composer/confirmar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, sprint_numero: sprintNumero, markdown }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao confirmar planning");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Suíte de Aceite — interfaces e funções
// ---------------------------------------------------------------------------

export interface ExecucaoAceite {
  funcionalidade_id: string;
  commit_sha: string;
  gates: { nome: string; resultado: string }[];
  disparado_em: string;
  concluido_em: string | null;
}

export async function getExecucoesAceite(projectId: string): Promise<ExecucaoAceite[]> {
  const res = await fetch(`${API}/execucoes_aceite/${projectId}`);
  if (!res.ok) return []; // falha silenciosa — badge é informativo
  return res.json();
}

// ---------------------------------------------------------------------------
// Boletins de Aceite — interfaces e funções
// ---------------------------------------------------------------------------

export interface BoletimResponse {
  id: string;
  project_id: string;
  sprint_numero?: number | null;
  funcionalidade_ids: string[];
  status: "rascunho" | "enviado" | "aprovado" | "ajuste";
  retorno_tipo?: "bug" | "mudanca_escopo" | null;
  conteudo: string;
  criado_em: string;
  enviado_em?: string | null;
  retorno_em?: string | null;
}

export async function listBoletins(projectId: string): Promise<BoletimResponse[]> {
  const res = await fetch(`${API}/boletins/${projectId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createBoletim(body: {
  project_id: string;
  sprint_numero?: number | null;
  funcionalidade_ids: string[];
}): Promise<BoletimResponse> {
  const res = await fetch(`${API}/boletins`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function patchBoletim(
  id: string,
  body: { status: string; retorno_tipo?: string }
): Promise<BoletimResponse> {
  const res = await fetch(`${API}/boletins/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function gerarResumoSemanal(projectId: string): Promise<{ content: string }> {
  const res = await fetch(`${API}/boletins/resumo_semanal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
