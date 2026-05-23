const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Project {
  id: string;
  name: string;
  client: string;
  description?: string;
  budget_usd?: number | null;
  has_api_key: boolean;
  created_at: string;
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

export async function generateDoc(
  projectId: string,
  tipoDoc: string,
  sprintNumero?: number,
  ingestionId?: string
): Promise<GeneratedDoc> {
  const res = await fetch(`${API}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      projeto_id: projectId,
      tipo_doc: tipoDoc,
      sprint_numero: sprintNumero ?? null,
      ingestion_id: ingestionId ?? null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Erro ao gerar documento");
  }
  return res.json();
}
