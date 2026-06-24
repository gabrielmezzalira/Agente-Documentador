const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export interface Ingestion {
  id: string;
  project_id: string;
  sprint_number: number;
  file_name?: string;
  file_type?: string;
  tipo_documentacao?: "planning" | "daily" | "review" | "outro" | null;
  extracted_content?: {
    resumo?: string;
    tarefas?: string[];
    decisoes?: string[];
    problemas?: string[];
    contexto_cliente?: string;
    proximos_passos?: string[];
    tecnologias?: string[];
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
  file: File
): Promise<{ status: string; sprint: number; tentativas: number }> {
  const form = new FormData();
  form.append("arquivo", file);
  form.append("sprint_numero", String(sprintNumber));
  form.append("projeto_id", projectId);

  const res = await fetch(`${API}/ingest`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao processar arquivo");
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
    throw new Error(err.detail ?? "Erro ao registrar documento de sprint");
  }
  return res.json();
}

export async function submitPlanning(input: {
  projetoId: string;
  sprintNumero: number;
  descricao: string;
  itensBacklog: string[];
  anexo?: File | null;
}): Promise<SprintDocResponse> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("sprint_numero", String(input.sprintNumero));
  form.append("descricao", input.descricao);
  form.append("itens_backlog", JSON.stringify(input.itensBacklog));
  if (input.anexo) form.append("anexo", input.anexo);
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
}): Promise<SprintDocResponse> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("sprint_numero", String(input.sprintNumero));
  form.append("data", input.data);
  form.append("feito", input.feito);
  form.append("proximo", input.proximo);
  if (input.impedimentos) form.append("impedimentos", input.impedimentos);
  if (input.anexo) form.append("anexo", input.anexo);
  return _postSprintDoc("daily", form);
}

export async function submitReview(input: {
  projetoId: string;
  sprintNumero: number;
  observacoes?: string;
  anexo?: File | null;
}): Promise<SprintDocResponse> {
  const form = new FormData();
  form.append("projeto_id", input.projetoId);
  form.append("sprint_numero", String(input.sprintNumero));
  if (input.observacoes) form.append("observacoes", input.observacoes);
  if (input.anexo) form.append("anexo", input.anexo);
  return _postSprintDoc("review", form);
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
