const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  return globalThis.fetch(input, { ...init, credentials: "include" });
}

export interface MeResponse {
  nome: string;
  email: string;
  cargo: "lider" | "gerente" | "operacional";
}

export interface LoginResponse {
  nome: string;
  cargo: "lider" | "gerente" | "operacional";
}

export interface OperacionalSemConta {
  operacional_id: string;
  nome: string;
  project_id: string;
  project_name: string;
}

export async function login(email: string, senha: string): Promise<LoginResponse> {
  const res = await apiFetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha }),
  });
  if (res.status === 401) throw new Error("Email ou senha inválidos");
  if (!res.ok) throw new Error("Erro ao fazer login");
  return res.json();
}

export async function logout(): Promise<void> {
  await apiFetch(`${API}/auth/logout`, { method: "POST" });
}

export async function getMe(): Promise<MeResponse> {
  const res = await apiFetch(`${API}/auth/me`);
  if (!res.ok) throw new Error("Não autenticado");
  return res.json();
}

export async function listOperacionaisSemConta(): Promise<OperacionalSemConta[]> {
  const res = await apiFetch(`${API}/auth/operacionais-sem-conta`);
  if (!res.ok) throw new Error("Erro ao buscar operacionais");
  return res.json();
}

export async function signupClaim(operacional_id: string, email: string, senha: string): Promise<LoginResponse> {
  const res = await apiFetch(`${API}/auth/signup/claim`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operacional_id, email, senha }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao criar conta");
  }
  return res.json();
}

export async function signupNovo(nome: string, email: string, senha: string): Promise<LoginResponse> {
  const res = await apiFetch(`${API}/auth/signup/novo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, email, senha }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao criar conta");
  }
  return res.json();
}

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
  data_inicio?: string | null;
  data_fim_contratada?: string | null;
  tolerancia_desvio_pontos?: number | null;
  periodo_garantia_dias?: number | null;
  gerente_email?: string | null;
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

export interface Sprint {
  id: string;
  project_id: string;
  numero: number;
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
  pontos_previstos: number | null;
  baseline_locked_at: string | null;
  avaliacao_completa_em?: string | null;
}

export interface AvaliacaoAnterior {
  avaliacao_id: string;
  project_name: string;
  criado_em: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number;
  resposta_7: number;
}

export interface PendenciaAvaliacao {
  operacional_id: string;
  nome: string;
  ultima_avaliacao_outro_projeto: AvaliacaoAnterior | null;
}

export interface AvaliacaoGerente {
  id: string;
  operacional_id: string;
  gerente_id: string;
  sprint_id: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number;
  resposta_7: number;
  reaproveitada_de: string | null;
  criado_em: string;
  editavel_ate: string;
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
  const res = await apiFetch(`${API}/projects`);
  if (!res.ok) throw new Error("Erro ao buscar projetos");
  return res.json();
}

export async function getProject(id: string): Promise<Project> {
  const res = await apiFetch(`${API}/projects/${id}`);
  if (!res.ok) throw new Error("Projeto não encontrado");
  return res.json();
}

export async function getProjectCost(projectId: string): Promise<ProjectCost> {
  const res = await apiFetch(`${API}/projects/${projectId}/cost`);
  if (!res.ok) throw new Error("Erro ao buscar custo do projeto");
  return res.json();
}

export async function getProjectUsage(projectId: string, month?: string): Promise<ProjectUsage> {
  const url = `${API}/projects/${projectId}/usage${month ? `?month=${month}` : ""}`;
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Erro ao buscar uso mensal do projeto");
  return res.json();
}

export async function updateContrato(
  projectId: string,
  data: {
    data_inicio?: string | null;
    data_fim_contratada?: string | null;
    tolerancia_desvio_pontos?: number | null;
    periodo_garantia_dias?: number | null;
  }
): Promise<Project> {
  const res = await apiFetch(`${API}/projects/${projectId}/contrato`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Erro ao atualizar dados de contrato");
  return res.json();
}

export async function updateApiKey(projectId: string, key: string | null): Promise<Project> {
  const res = await apiFetch(`${API}/projects/${projectId}/api-key`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gemini_api_key: key }),
  });
  if (!res.ok) throw new Error("Erro ao atualizar chave de API");
  return res.json();
}

export async function updateGerenteEmail(projectId: string, email: string | null): Promise<Project> {
  const res = await apiFetch(`${API}/projects/${projectId}/gerente-email`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gerente_email: email || null }),
  });
  if (!res.ok) throw new Error("Erro ao atualizar email do gerente");
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
  const res = await apiFetch(`${API}/projects`, {
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

  const res = await apiFetch(`${API}/ingest`, { method: "POST", body: form });
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
  const res = await apiFetch(`${API}/ingestions/${projectId}`);
  if (!res.ok) throw new Error("Erro ao buscar ingestões");
  return res.json();
}

export async function deleteProject(id: string): Promise<void> {
  const res = await apiFetch(`${API}/projects/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Erro ao excluir projeto");
}

export async function listDocs(projectId: string): Promise<GeneratedDoc[]> {
  const res = await apiFetch(`${API}/docs/${projectId}`);
  if (!res.ok) throw new Error("Erro ao buscar documentos");
  return res.json();
}

export async function deleteDoc(docId: string): Promise<void> {
  const res = await apiFetch(`${API}/docs/${docId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Erro ao excluir documento");
}

export async function toggleDelivered(projectId: string): Promise<Project> {
  const res = await apiFetch(`${API}/projects/${projectId}/delivered`, { method: "PATCH" });
  if (!res.ok) throw new Error("Erro ao atualizar status do projeto");
  return res.json();
}

export async function searchStack(query: string): Promise<StackSearchResponse> {
  const res = await apiFetch(`${API}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error("Erro ao buscar stack");
  return res.json();
}

export async function listSprints(projectId: string): Promise<SprintWithStatus[]> {
  const res = await apiFetch(`${API}/projects/${projectId}/sprints`);
  if (!res.ok) throw new Error("Erro ao buscar sprints");
  return res.json();
}

export async function updateSprintBaseline(
  sprintId: string,
  pontosPrevistos: number
): Promise<SprintWithStatus> {
  const res = await apiFetch(`${API}/sprints/${sprintId}/baseline`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pontos_previstos: pontosPrevistos }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao definir baseline");
  }
  return res.json();
}

export async function listPendenciasAvaliacao(sprintId: string): Promise<PendenciaAvaliacao[]> {
  const res = await apiFetch(`${API}/avaliacoes/${sprintId}/pendencias`);
  if (!res.ok) throw new Error("Erro ao buscar pendências de avaliação");
  return res.json();
}

export async function submitAvaliacao(data: {
  operacional_id: string;
  sprint_id: string;
  resposta_1: number;
  resposta_2: number;
  resposta_3: number;
  resposta_4: number;
  resposta_5: number;
  resposta_6: number;
  resposta_7: number;
  reaproveitada_de?: string;
}): Promise<AvaliacaoGerente> {
  const res = await apiFetch(`${API}/avaliacoes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao salvar avaliação");
  }
  return res.json();
}

export async function confirmarAvaliacaoSemanal(sprintId: string): Promise<{ sprint_id: string; avaliacao_completa_em: string }> {
  const res = await apiFetch(`${API}/avaliacoes/${sprintId}/confirmar`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Ainda há avaliações pendentes");
  }
  return res.json();
}

export async function deleteSprint(sprintId: string): Promise<void> {
  const res = await apiFetch(`${API}/sprints/${sprintId}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao excluir sprint");
  }
}

export async function createSprint(projectId: string, numero?: number): Promise<Sprint> {
  const res = await apiFetch(`${API}/projects/${projectId}/sprints`, {
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
  const res = await apiFetch(`${API}/projects/${projectId}/technologies`);
  if (!res.ok) throw new Error("Erro ao buscar tecnologias do projeto");
  return res.json();
}


async function _postSprintDoc(path: string, form: FormData): Promise<SprintDocResponse> {
  const res = await apiFetch(`${API}/sprint-docs/${path}`, { method: "POST", body: form });
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
  const res = await apiFetch(`${API}/docs/manual`, {
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
  const res = await apiFetch(`${API}/docs/manual/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao subir PDF do documento manual");
  }
  return res.json();
}

export async function exportToGdocs(docId: string): Promise<{ url: string }> {
  const res = await apiFetch(`${API}/docs/${docId}/export-gdocs`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao exportar para Google Docs");
  }
  return res.json();
}

export async function listIngestionsBySprint(projetoId: string, sprint: number): Promise<Ingestion[]> {
  const res = await apiFetch(`${API}/ingestions/${projetoId}/${sprint}`);
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
  const res = await apiFetch(`${API}/enrich`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao analisar conteúdo");
  }
  return res.json();
}

export async function deleteIngestion(ingestionId: string): Promise<void> {
  const res = await apiFetch(`${API}/ingestions/${ingestionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Erro ao excluir ingestão");
}

export async function moveIngestion(ingestionId: string, sprintNumber: number): Promise<Ingestion> {
  const res = await apiFetch(`${API}/ingestions/${ingestionId}`, {
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
  const res = await apiFetch(`${API}/docs/${docId}`, {
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
  const res = await apiFetch(`${API}/generate`, {
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
  status: "nao_iniciada" | "em_andamento" | "concluida";
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

export interface BlocoB {
  travadas: Array<{ id: string; titulo: string; dias: number }>;
  aguardando_cliente: Array<{ id: string; titulo: string; dias_uteis: number }>;
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
  const res = await apiFetch(`${API}/projects/${projectId}/painel`);
  if (!res.ok) throw new Error("Erro ao buscar painel");
  return res.json();
}

export async function listFuncionalidades(projectId: string): Promise<FuncionalidadeResponse[]> {
  const res = await apiFetch(`${API}/funcionalidades?project_id=${projectId}`);
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
  const res = await apiFetch(`${API}/funcionalidades/importar`, {
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
  const res = await apiFetch(`${API}/funcionalidades/importar/arquivo`, { method: "POST", body: form });
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
    status?: string;
    sprint_alvo?: string;
  },
): Promise<FuncionalidadeResponse> {
  const res = await apiFetch(`${API}/funcionalidades/${id}`, {
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
  const res = await apiFetch(`${API}/funcionalidades`, {
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
  const res = await apiFetch(`${API}/funcionalidades/importar/confirmar`, {
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
  const res = await apiFetch(`${API}/composer/rascunho/${projectId}/${sprintNumero}`);
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
  const res = await apiFetch(`${API}/composer/rascunho/${projectId}/${sprintNumero}`, {
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
  const res = await apiFetch(`${API}/composer/gerar`, {
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
  const res = await apiFetch(`${API}/composer/confirmar`, {
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
export async function gerarResumoSemanal(projectId: string): Promise<{ content: string }> {
  const res = await apiFetch(`${API}/boletins/resumo_semanal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ---------------------------------------------------------------------------
// Sprint Funcionalidades — planning redesign

export interface TaskItem {
  texto: string;
  responsavel?: string;
}

export interface Correlacao {
  funcionalidade_id: string | null;
  tasks: TaskItem[];
}

export interface SprintFuncionalidade {
  id: string;
  sprint_id: string;
  funcionalidade_id: string;
  status: "em_andamento" | "concluida";
  tasks: TaskItem[];
  created_at: string;
  funcionalidades?: {
    id: string;
    id_funcional: string;
    titulo: string;
    status: string;
    prioridade: string;
  };
}

export interface TaskCorrelacao {
  task: string;
  funcionalidade_id: string | null;
  funcionalidade_titulo: string | null;
}

export interface PlanningComCorrelacoes {
  enriquecimento: EnrichResult;
  correlacoes: TaskCorrelacao[];
  sem_funcionalidades: boolean;
}

export async function enrichPlanningComCorrelacoes(
  projetoId: string,
  { texto, arquivo }: { texto?: string; arquivo?: File }
): Promise<PlanningComCorrelacoes> {
  const fd = new FormData();
  fd.append("projeto_id", projetoId);
  if (texto) fd.append("texto", texto);
  if (arquivo) fd.append("arquivo", arquivo);

  const res = await apiFetch(`${API}/enrich/planning-correlacoes`, { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao analisar conteúdo");
  }
  return res.json();
}

export async function createSprintFuncionalidades(
  sprintId: string,
  correlacoes: Correlacao[]
): Promise<{ created: number; sprint_funcionalidades: SprintFuncionalidade[] }> {
  const res = await apiFetch(`${API}/sprint-funcionalidades`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sprint_id: sprintId, correlacoes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao salvar funcionalidades");
  }
  return res.json();
}

export async function getSprintFuncionalidades(sprintId: string): Promise<SprintFuncionalidade[]> {
  const res = await apiFetch(`${API}/sprint-funcionalidades/sprint/${sprintId}`);
  if (!res.ok) throw new Error("Erro ao buscar funcionalidades da sprint");
  return res.json();
}

export async function updateSprintFuncionalidade(
  sfId: string,
  data: { status?: "em_andamento" | "concluida"; tasks?: TaskItem[] }
): Promise<SprintFuncionalidade> {
  const res = await apiFetch(`${API}/sprint-funcionalidades/${sfId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao atualizar");
  }
  return res.json();
}

export async function getFuncionalidadesRecomendadas(
  projectId: string
): Promise<Pick<FuncionalidadeResponse, "id" | "id_funcional" | "titulo" | "status" | "sprint_alvo">[]> {
  const res = await apiFetch(`${API}/sprint-funcionalidades/recomendadas/${projectId}`);
  if (!res.ok) throw new Error("Erro ao buscar recomendações");
  return res.json();
}

// ---------------------------------------------------------------------------
// Operacionais

export interface OperacionalResponse {
  id: string;
  project_id: string;
  nome: string;
  email?: string | null;
  papel?: string | null;
  ativo: boolean;
  created_at: string;
}

export async function listOperacionais(projectId: string): Promise<OperacionalResponse[]> {
  const res = await apiFetch(`${API}/operacionais?project_id=${projectId}`);
  if (!res.ok) throw new Error("Erro ao buscar operacionais");
  return res.json();
}

export async function createOperacional(data: {
  project_id: string;
  nome: string;
  email?: string;
  papel?: string;
}): Promise<OperacionalResponse> {
  const res = await apiFetch(`${API}/operacionais`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Erro ao criar operacional");
  return res.json();
}

export async function updateOperacional(
  id: string,
  data: { nome?: string; email?: string; papel?: string; ativo?: boolean }
): Promise<OperacionalResponse> {
  const res = await apiFetch(`${API}/operacionais/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Erro ao atualizar operacional");
  return res.json();
}

export async function deleteOperacional(id: string): Promise<void> {
  const res = await apiFetch(`${API}/operacionais/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Erro ao excluir operacional");
  }
}

// ---------------------------------------------------------------------------
// Tasks (kanban de tasks — distinto de TaskItem do planning)

export interface TaskKanbanResponse {
  id: string;
  project_id: string;
  funcionalidade_id?: string | null;
  sprint_id?: string | null;
  operacional_id?: string | null;
  titulo: string;
  descricao?: string | null;
  pontos: number;
  coluna_kanban: "planejado" | "em_andamento" | "concluida";
  bloqueado: boolean;
  motivo_bloqueio?: string | null;
  checklist: { texto: string; done: boolean }[];
  ordem: number;
  contador_reaberturas: number;
  bloqueado_manual: boolean;
  bloqueado_em?: string | null;
  bloqueado_por?: string | null;
  bloqueado_resolvido_por?: string | null;
  bloqueado_resolvido_em?: string | null;
  entrou_em_andamento_em?: string | null;
  travado_automatico: boolean;
  travado_override: boolean;
  travado_override_por?: string | null;
  travado_override_em?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskTransicaoKanban {
  id: string;
  task_id: string;
  campo: string;
  de?: string | null;
  para?: string | null;
  autor?: string | null;
  timestamp: string;
  motivo?: string | null;
  duracao_fase_anterior_segundos?: number | null;
}

export async function listTasksKanban(params: {
  project_id: string;
  sprint_id?: string;
  operacional_id?: string;
  funcionalidade_id?: string;
  coluna?: string;
}): Promise<TaskKanbanResponse[]> {
  const q = new URLSearchParams({ project_id: params.project_id });
  if (params.sprint_id) q.set("sprint_id", params.sprint_id);
  if (params.operacional_id) q.set("operacional_id", params.operacional_id);
  if (params.funcionalidade_id) q.set("funcionalidade_id", params.funcionalidade_id);
  if (params.coluna) q.set("coluna", params.coluna);
  const res = await apiFetch(`${API}/tasks?${q}`);
  if (!res.ok) throw new Error("Erro ao buscar tasks");
  return res.json();
}

export async function createTaskKanban(data: {
  project_id: string;
  titulo: string;
  pontos: number;
  sprint_id?: string;
  operacional_id?: string;
  funcionalidade_id?: string;
  descricao?: string;
  coluna_kanban?: string;
}): Promise<TaskKanbanResponse> {
  const res = await apiFetch(`${API}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Erro ao criar task");
  return res.json();
}

export async function patchTaskKanban(
  id: string,
  data: {
    titulo?: string;
    descricao?: string;
    pontos?: number;
    coluna_kanban?: string;
    operacional_id?: string;
    sprint_id?: string;
    funcionalidade_id?: string;
    bloqueado?: boolean;
    motivo_bloqueio?: string;
    checklist?: { texto: string; done: boolean }[];
    autor?: string;
    motivo?: string;
    bloqueado_manual?: boolean;
    bloqueado_por?: string;
    bloqueado_resolvido_por?: string;
  }
): Promise<TaskKanbanResponse> {
  const res = await apiFetch(`${API}/tasks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (res.status === 409) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error((err as { detail?: string }).detail ?? "WIP atingido"), { status: 409 });
  }
  if (!res.ok) throw new Error("Erro ao atualizar task");
  return res.json();
}

export async function moverTaskKanban(
  id: string,
  coluna_destino: string,
  autor?: string,
  motivo?: string
): Promise<TaskKanbanResponse> {
  const q = new URLSearchParams({ coluna_destino });
  if (autor) q.set("autor", autor);
  if (motivo) q.set("motivo", motivo);
  const res = await apiFetch(`${API}/tasks/${id}/mover?${q}`, { method: "POST" });
  if (res.status === 409) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error((err as { detail?: string }).detail ?? "WIP atingido"), { status: 409 });
  }
  if (!res.ok) throw new Error("Erro ao mover task");
  return res.json();
}

export async function overrideTravamentoTask(id: string, autor?: string): Promise<TaskKanbanResponse> {
  const q = new URLSearchParams();
  if (autor) q.set("autor", autor);
  const res = await apiFetch(`${API}/tasks/${id}/travado/override?${q}`, { method: "POST" });
  if (res.status === 409) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error((err as { detail?: string }).detail ?? "Task não está em Em Andamento"), { status: 409 });
  }
  if (!res.ok) throw new Error("Erro ao suprimir alerta de travamento");
  return res.json();
}

export async function deleteTaskKanban(id: string): Promise<void> {
  const res = await apiFetch(`${API}/tasks/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Erro ao excluir task");
}

export async function listTaskTransicoesKanban(taskId: string): Promise<TaskTransicaoKanban[]> {
  const res = await apiFetch(`${API}/tasks/${taskId}/transicoes`);
  if (!res.ok) throw new Error("Erro ao buscar histórico da task");
  return res.json();
}

// ── Task sugestões ────────────────────────────────────────────────────────────

export interface TaskSugestaoResponse {
  id: string;
  task_id: string;
  task_titulo: string;
  acao: string;
  motivo: string | null;
  origem_ingestion_id: string | null;
  aceita: boolean | null;
  criado_em: string;
  task_coluna_atual?: string | null;
}

export async function listTaskSugestoes(projectId: string): Promise<TaskSugestaoResponse[]> {
  const res = await apiFetch(`${API}/tasks/sugestoes?project_id=${encodeURIComponent(projectId)}`);
  if (!res.ok) throw new Error("Erro ao buscar sugestões");
  return res.json();
}

export async function resolveTaskSugestao(
  sugestaoId: string,
  aceita: boolean
): Promise<TaskSugestaoResponse> {
  const res = await apiFetch(`${API}/tasks/sugestoes/${sugestaoId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aceita }),
  });
  if (!res.ok) throw new Error("Erro ao resolver sugestão");
  return res.json();
}

// ── Métricas ──────────────────────────────────────────────────────────────────

export interface SpiPoint {
  sprint_numero: number;
  pontos_previstos: number | null;
  pontos_realizados: number;
  spi: number | null;
}

export interface ThroughputPoint {
  sprint_numero: number;
  tasks_total: number;
  tasks_concluidas: number;
  pontos_concluidos: number;
}

export interface CycleTimePoint {
  task_titulo: string;
  sprint_numero: number | null;
  cycle_time_horas: number;
  operacional_nome: string | null;
}

export interface CfdPoint {
  sprint_numero: number;
  planejado: number;
  em_andamento: number;
  concluida: number;
}

export async function getMetricasSpi(projectId: string): Promise<SpiPoint[]> {
  const res = await apiFetch(`${API}/metricas/${projectId}/spi`);
  if (!res.ok) throw new Error("Erro ao buscar SPI");
  return res.json();
}

export async function getMetricasThroughput(projectId: string): Promise<ThroughputPoint[]> {
  const res = await apiFetch(`${API}/metricas/${projectId}/throughput`);
  if (!res.ok) throw new Error("Erro ao buscar throughput");
  return res.json();
}

export async function getMetricasCycleTime(projectId: string): Promise<CycleTimePoint[]> {
  const res = await apiFetch(`${API}/metricas/${projectId}/cycle-time`);
  if (!res.ok) throw new Error("Erro ao buscar cycle-time");
  return res.json();
}

export async function getMetricasCfd(projectId: string): Promise<CfdPoint[]> {
  const res = await apiFetch(`${API}/metricas/${projectId}/cfd`);
  if (!res.ok) throw new Error("Erro ao buscar CFD");
  return res.json();
}

export interface PerformanceOperacionalPoint {
  operacional_id: string;
  operacional_nome: string;
  pontos_atribuidos: number;
  pontos_realizados: number;
  tasks_concluidas: number;
  spi: number | null;
}

export interface CycleTimeStats {
  p50_horas: number | null;
  p85_horas: number | null;
}

export async function getMetricasPerformanceOperacional(projectId: string): Promise<PerformanceOperacionalPoint[]> {
  const res = await apiFetch(`${API}/metricas/${projectId}/performance-operacional`);
  if (!res.ok) throw new Error("Erro ao buscar performance por operacional");
  return res.json();
}

export async function getMetricasCycleTimeStats(projectId: string): Promise<CycleTimeStats> {
  const res = await apiFetch(`${API}/metricas/${projectId}/cycle-time/stats`);
  if (!res.ok) throw new Error("Erro ao buscar estatísticas de cycle-time");
  return res.json();
}
