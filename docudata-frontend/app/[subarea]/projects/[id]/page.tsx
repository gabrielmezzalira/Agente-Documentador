"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  getProject,
  updateGerenteEmail,
  listIngestions,
  listDocs,
  listSprints,
  createSprint,
  iniciarSprint,
  deleteSprint,
  generateDoc,
  ingestFile,
  exportToGdocs,
  submitAtaUpload,
  deleteProject,
  deleteDoc,
  deleteIngestion,
  moveIngestion,
  moveDoc,
  toggleDelivered,
  getGitHubCapabilities,
  startGitHubConnection,
  listAvailableGitHubRepositories,
  connectProjectRepositories,
  listProjectRepositories,
  disconnectProjectRepository,
  listFuncionalidades,
  gerarResumoSemanal,
  listOperacionais,
  listOperacionaisDisponiveis,
  removerOperacionalDoProjeto,
  createOperacional,
  type OperacionalDisponivel,
  updateOperacional,
  deleteOperacional,
  type Project,
  type Ingestion,
  type GeneratedDoc,
  type SprintWithStatus,
  type SprintDocType,
  type FuncionalidadeResponse,
  type OperacionalResponse,
  type GitHubRepositoryCandidate,
  type ProjectRepository,
} from "../../../lib/api";
import Tabs from "../../../components/Tabs";
import { useAuth } from "../../../components/AuthGuard";
import SprintCard from "../../../components/SprintCard";
import SprintDocModal from "../../../components/SprintDocModal";
import TechnologiesTab from "../../../components/TechnologiesTab";
import PainelTab from "../../../components/PainelTab";
import PlanningModal from "../../../components/PlanningModal";
import FuncionalidadesStatusModal from "../../../components/FuncionalidadesStatusModal";
import EscopoTab from "../../../components/EscopoTab";
import TasksKanbanTab from "../../../components/TasksKanbanTab";
import MetricasTab from "../../../components/MetricasTab";
import DocTypeCard from "../../../components/DocTypeCard";
import TutorialBanner from "../../../components/TutorialBanner";
import ManualDocModal from "../../../components/ManualDocModal";
import UploadLivreModal from "../../../components/UploadLivreModal";
import RetroModal from "../../../components/RetroModal";
import AvaliacaoSemanalModal from "../../../components/AvaliacaoSemanalModal";
import { DOC_TYPES, docTypeLabel, type DocTypeKey } from "../../../lib/doc_types";

type TabId = "sprints" | "escopo" | "painel" | "tasks" | "metricas" | "tecnologias" | "documentos" | "config";


function OperacionaisSection({
  projectId,
  operacionais,
  onUpdated,
}: {
  projectId: string;
  operacionais: OperacionalResponse[];
  onUpdated: (ops: OperacionalResponse[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [papel, setPapel] = useState("");
  const [githubLogin, setGithubLogin] = useState("");
  const [githubEmail, setGithubEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const [disponiveis, setDisponiveis] = useState<OperacionalDisponivel[]>([]);

  // Pessoas já cadastradas em outros projetos. Redigitar cria a mesma pessoa com
  // e-mail divergente e a parte em duas no ranking, que casa identidade por e-mail.
  useEffect(() => {
    if (!adding) return;
    listOperacionaisDisponiveis(projectId).then(setDisponiveis).catch(() => setDisponiveis([]));
  }, [adding, projectId]);

  function preencherCom(pessoa: OperacionalDisponivel) {
    setNome(pessoa.nome);
    setEmail(pessoa.email ?? "");
    setPapel(pessoa.papel ?? "");
    setGithubLogin(pessoa.github_login ?? "");
    setGithubEmail(pessoa.github_email ?? "");
  }

  function limparForm() {
    setNome(""); setEmail(""); setPapel(""); setGithubLogin(""); setGithubEmail("");
  }

  const inputSm: React.CSSProperties = {
    padding: "6px 10px",
    border: "1px solid #e4e4ea",
    borderRadius: 7,
    fontSize: 13,
    color: "#111116",
    background: "#fff",
  };

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!nome.trim()) return;
    setSaving(true);
    setErr("");
    try {
      const novo = await createOperacional({
        project_id: projectId,
        nome: nome.trim(),
        email: email.trim() || undefined,
        papel: papel.trim() || undefined,
        github_login: githubLogin.trim() || undefined,
        github_email: githubEmail.trim() || undefined,
      });
      onUpdated([...operacionais, novo]);
      limparForm();
      setAdding(false);
    } catch {
      setErr("Erro ao adicionar.");
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleAtivo(op: OperacionalResponse) {
    try {
      const updated = await updateOperacional(op.id, { ativo: !op.ativo });
      onUpdated(operacionais.map((o) => (o.id === updated.id ? updated : o)));
    } catch {
      alert("Erro ao atualizar operacional.");
    }
  }

  async function handleRemover(op: OperacionalResponse) {
    if (!confirm(
      `Remover "${op.nome}" deste projeto?\n\n` +
      `O histórico de pontuação dele é preservado e continua contando no acompanhamento. ` +
      `As tasks ainda não concluídas ficam sem responsável para você redistribuir.\n\n` +
      `Use isso quando a pessoa sai do projeto no meio da execução.`
    )) return;
    try {
      const atualizado = await removerOperacionalDoProjeto(op.id);
      onUpdated(operacionais.map((o) => (o.id === atualizado.id ? atualizado : o)));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao remover do projeto.");
    }
  }

  async function handleDelete(op: OperacionalResponse) {
    if (!confirm(`Excluir "${op.nome}" permanentemente? Toda a pontuação e o histórico de ranking dele serão APAGADOS e não há como recuperar.\n\nSe a pessoa só saiu do projeto, use "Remover do projeto" para preservar os pontos.`)) return;
    try {
      await deleteOperacional(op.id);
      onUpdated(operacionais.filter((o) => o.id !== op.id));
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao excluir");
    }
  }

  return (
    <section style={{ background: "#fff", border: "1px solid #e8e8ed", borderRadius: 14, padding: "20px 24px", marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <h2 style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", margin: 0 }}>Operacionais</h2>
        {!adding && (
          <button
            onClick={() => setAdding(true)}
            style={{ background: "none", border: "none", fontSize: 12, color: "#9696a0", cursor: "pointer", textDecoration: "underline", padding: 0 }}
          >
            + Adicionar
          </button>
        )}
      </div>

      {operacionais.length === 0 && !adding && (
        <p style={{ fontSize: 13, color: "#9696a0", margin: 0 }}>Nenhum operacional cadastrado.</p>
      )}

      {operacionais.map((op) => (
        <div key={op.id} style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "8px 0", borderBottom: "1px solid #f0f0f4",
          opacity: op.ativo ? 1 : 0.5,
        }}>
          <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: "#111116" }}>
            {op.nome}
            {op.papel && <span style={{ fontWeight: 400, color: "#9696a0", marginLeft: 8 }}>{op.papel}</span>}
            {op.email
              ? <span style={{ fontWeight: 400, color: "#9696a0", marginLeft: 8 }}>{op.email}</span>
              : <span style={{ fontWeight: 400, color: "#d97706", marginLeft: 8 }} title="Sem e-mail, esta pessoa não é reconhecida entre projetos">sem e-mail</span>}
          </span>
          <button
            onClick={() => handleToggleAtivo(op)}
            style={{ background: "none", border: "none", fontSize: 11, color: "#9696a0", cursor: "pointer", textDecoration: "underline", padding: 0 }}
          >
            {op.ativo ? "Desativar" : "Ativar"}
          </button>
          {op.ativo && (
            <button
              onClick={() => handleRemover(op)}
              title="Sai do projeto, mas mantém a pontuação dele no acompanhamento"
              style={{ background: "none", border: "none", fontSize: 11, color: "#9696a0", cursor: "pointer", textDecoration: "underline", padding: 0 }}
            >
              Remover do projeto
            </button>
          )}
          <button
            onClick={() => handleDelete(op)}
            title="Apaga a pessoa e toda a pontuação dela. Irreversível."
            style={{ background: "none", border: "none", fontSize: 11, color: "#dc2626", cursor: "pointer", padding: 0 }}
          >
            ×
          </button>
        </div>
      ))}

      {adding && (
        <div style={{ marginTop: 12 }}>
          {disponiveis.length > 0 && (
            <div style={{ background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: 8, padding: "10px 12px", marginBottom: 12 }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: "#0369a1", margin: "0 0 6px" }}>
                Já trabalha em outro projeto?
              </p>
              <p style={{ fontSize: 11, color: "#0c4a6e", margin: "0 0 8px" }}>
                Selecione a pessoa para reaproveitar o cadastro. Redigitar com e-mail
                diferente faz ela contar como duas pessoas no acompanhamento.
              </p>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {disponiveis.map((pessoa) => (
                  <button
                    key={pessoa.email || pessoa.nome}
                    type="button"
                    onClick={() => preencherCom(pessoa)}
                    style={{ background: "#fff", border: "1px solid #bae6fd", borderRadius: 999, padding: "5px 12px", fontSize: 12, cursor: "pointer", color: "#0369a1", fontWeight: 600 }}
                    title={pessoa.projetos.join(", ")}
                  >
                    {pessoa.nome}
                  </button>
                ))}
              </div>
            </div>
          )}

          <form onSubmit={handleAdd} style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 3 }}>Nome *</label>
              <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex: João Silva" style={{ ...inputSm, width: 180 }} required />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 3 }}>E-mail</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="joao@citi.com" style={{ ...inputSm, width: 190 }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 3 }}>Papel</label>
              <input value={papel} onChange={(e) => setPapel(e.target.value)} placeholder="Front, Back, DS…" style={{ ...inputSm, width: 140 }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 3 }}>GitHub username</label>
              <input value={githubLogin} onChange={(e) => setGithubLogin(e.target.value)} placeholder="ex: joaosilva" style={{ ...inputSm, width: 140 }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#9696a0", marginBottom: 3 }}>Email do GitHub</label>
              <input type="email" value={githubEmail} onChange={(e) => setGithubEmail(e.target.value)} placeholder="se for diferente do e-mail" style={{ ...inputSm, width: 170 }} />
            </div>
            <button type="submit" disabled={saving} style={{ background: "#0f172a", color: "#fff", border: "none", borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
              {saving ? "…" : "Salvar"}
            </button>
            <button type="button" onClick={() => { setAdding(false); limparForm(); setErr(""); }} style={{ background: "none", border: "1px solid #e4e4ea", borderRadius: 8, padding: "7px 14px", fontSize: 12, cursor: "pointer", color: "#374151" }}>
              Cancelar
            </button>
            {err && <span style={{ fontSize: 12, color: "#dc2626" }}>{err}</span>}
          </form>

          <p style={{ fontSize: 11, color: "#9696a0", marginTop: 8 }}>
            E-mail e GitHub username não são obrigatórios, mas sem eles a pessoa não é
            reconhecida entre projetos e os commits dela não contam na nota de qualidade.
            O email do commit é o que o Git usa localmente — se for diferente do e-mail
            de login, preencha o campo "Email do GitHub" para o commit ser reconhecido.
          </p>
        </div>
      )}
    </section>
  );
}

export default function ProjectDashboard() {
  const { id, subarea } = useParams<{ id: string; subarea: string }>();
  const router = useRouter();

  // ---------- data ----------
  const [project, setProject] = useState<Project | null>(null);
  const [ingestions, setIngestions] = useState<Ingestion[]>([]);
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [sprints, setSprints] = useState<SprintWithStatus[]>([]);
  const [planejadasAbertas, setPlanejadasAbertas] = useState(false);
  const [funcionalidades, setFuncionalidades] = useState<FuncionalidadeResponse[]>([]);
  const [operacionais, setOperacionais] = useState<OperacionalResponse[]>([]);
  const [loading, setLoading] = useState(true);

  // ---------- ui ----------
  const [activeTab, setActiveTab] = useState<TabId>("sprints");
  const auth = useAuth();
  const cargo = auth?.cargo ?? "lider";
  const OPERACIONAL_TABS = new Set(["sprints", "tasks", "tecnologias", "documentos"]);
  const [descOpen, setDescOpen] = useState(false);
  const [docSubTab, setDocSubTab] = useState<"cross_sprint" | "por_sprint">("cross_sprint");

  // ---------- modal sprint-docs ----------
  const [modal, setModal] = useState<{ tipo: SprintDocType; sprintNumero: number; sprintId?: string } | null>(null);

  // ---------- modal status funcionalidades (pós-review) ----------
  const [statusModal, setStatusModal] = useState<{ sprintId: string; sprintNumero: number } | null>(null);

  // ---------- modal doc manual ----------
  const [manualModal, setManualModal] = useState<{ sprintNumero: number | null } | null>(null);

  // ---------- modal upload livre ----------
  const [uploadModal, setUploadModal] = useState<{ sprintNumero: number } | null>(null);

  // ---------- modal retrospectiva ----------
  const [retroModal, setRetroModal] = useState<{ sprintNumero: number } | null>(null);

  // ---------- carry-over prefill ----------
  const [carryOverPrefill, setCarryOverPrefill] = useState("");

  // ---------- modal planning (novo fluxo) ----------
  const [planningModal, setPlanningModal] = useState<{ sprint: SprintWithStatus } | null>(null);
  const [avaliacaoModal, setAvaliacaoModal] = useState<{ sprintId: string; sprintNumero: number } | null>(null);

  // ---------- resumo semanal ----------
  const [resumoSemanal, setResumoSemanal] = useState<string | null>(null);
  const [gerandoResumo, setGerandoResumo] = useState(false);

  // ---------- geração ----------
  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDoc | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const [exportingDocId, setExportingDocId] = useState<string | null>(null);
  const [exportError, setExportError] = useState<Record<string, string>>({});

  // ---------- repositórios GitHub (piloto Dev) ----------
  const [githubVisible, setGithubVisible] = useState(false);
  const [githubRepositories, setGithubRepositories] = useState<ProjectRepository[]>([]);
  const [githubCandidates, setGithubCandidates] = useState<GitHubRepositoryCandidate[]>([]);
  const [githubSelected, setGithubSelected] = useState<number[]>([]);
  const [githubConnectionToken, setGithubConnectionToken] = useState("");
  const [githubLoading, setGithubLoading] = useState(false);
  const [githubError, setGithubError] = useState("");

  const [emailInput, setEmailInput] = useState("");
  const [emailMsg, setEmailMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [savingEmail, setSavingEmail] = useState(false);

  // ---------- bootstrap ----------
  useEffect(() => {
    Promise.all([
      getProject(id),
      listIngestions(id),
      listDocs(id),
      listSprints(id),
      listFuncionalidades(id),
      listOperacionais(id).catch(() => [] as OperacionalResponse[]),
    ])
      .then(([p, ings, d, s, fs, ops]) => {
        setProject(p);
        setIngestions(ings);
        setDocs(d);
        setSprints(s);
        setFuncionalidades(fs);
        setOperacionais(ops);
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    // Dados não consulta a integração durante o piloto; o rollout é isolado em Dev.
    if (project?.subarea !== "dev") return;
    let active = true;
    getGitHubCapabilities()
      .then(async (capabilities) => {
        if (!active || !capabilities.enabled || !capabilities.configured || !capabilities.subareas.includes("dev")) return;
        setGithubVisible(true);
        const params = new URLSearchParams(window.location.search);
        const erroCallback = params.get("github_error");
        const token = params.get("github_connection");
        if (params.get("tab") === "config") setActiveTab("config");
        if (erroCallback === "cancelled") {
          setActiveTab("config");
          setGithubError("A conexão com o GitHub foi cancelada.");
        }
        const vinculados = await listProjectRepositories(id);
        if (active) setGithubRepositories(vinculados);
        if (token && active) {
          setActiveTab("config");
          setGithubConnectionToken(token);
          window.history.replaceState({}, "", window.location.pathname + "?tab=config");
          setGithubLoading(true);
          try {
            const candidatos = await listAvailableGitHubRepositories(token);
            if (!active) return;
            setGithubCandidates(candidatos);
            setGithubSelected(candidatos.map((repo) => repo.github_repository_id));
            if (candidatos.length === 0) setGithubError("Selecione pelo menos um repositório no GitHub.");
          } catch (err) {
            if (active) setGithubError(err instanceof Error ? err.message : "A conexão com o GitHub expirou.");
          } finally {
            if (active) setGithubLoading(false);
          }
        }
      })
      // Backend antigo ou flag desligada mantém o restante do projeto funcional.
      .catch(() => {});
    return () => { active = false; };
  }, [id, project?.subarea]);


  function refreshSprints() {
    listSprints(id).then(setSprints).catch(() => {});
  }
  async function refreshAll() {
    const [ings, d, s] = await Promise.all([
      listIngestions(id),
      listDocs(id),
      listSprints(id),
    ]);
    setIngestions(ings);
    setDocs(d);
    setSprints(s);
  }

  // ---------- handlers ----------
  async function handleSaveEmail(e: React.FormEvent) {
    e.preventDefault();
    setSavingEmail(true);
    setEmailMsg(null);
    try {
      const updated = await updateGerenteEmail(id, emailInput.trim() || null);
      setProject(updated);
      setEmailMsg({ ok: true, text: emailInput.trim() ? "Email salvo. Lembretes ativados." : "Email removido. Lembretes desativados." });
    } catch {
      setEmailMsg({ ok: false, text: "Erro ao salvar email." });
    } finally {
      setSavingEmail(false);
    }
  }

  async function handleCreateSprint() {
    try {
      // Prioriza destravar a sprint planejada mais antiga (criada em
      // Planejamento) em vez de sempre criar uma nova — só cria do zero
      // quando não sobra nenhuma planejada esperando.
      const planejadas = sprints.filter((s) => !s.iniciada).sort((a, b) => a.numero - b.numero);
      if (planejadas.length > 0) {
        await iniciarSprint(planejadas[0].id);
      } else {
        await createSprint(id);
      }
      refreshSprints();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao iniciar sprint");
    }
  }

  async function handleDeleteSprint(sprintId: string) {
    try {
      await deleteSprint(sprintId);
      refreshSprints();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao excluir sprint");
    }
  }

  async function handleGenerate(
    tipoDoc: string,
    sprintNum?: number,
    ingestionId?: string
  ) {
    setGenerating(true);
    setGeneratedDoc(null);
    setGenerateError("");
    try {
      const doc = await generateDoc(id, tipoDoc, sprintNum, ingestionId, observacoes);
      setGeneratedDoc(doc);
      await refreshAll();
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Erro ao gerar documento");
    } finally {
      setGenerating(false);
    }
  }

  async function handleDeleteProject() {
    if (!confirm(`Excluir o projeto "${project?.name}"? Todas as ingestões e documentos serão removidos.`))
      return;
    try { await deleteProject(id); router.push(`/${subarea}`); }
    catch { alert("Erro ao excluir projeto."); }
  }

  async function handleToggleDelivered() {
    if (!project?.is_delivered) {
      const totalOrcamento = sprints.reduce((acc, s) => acc + (s.pontos_orcamento ?? 0), 0);
      if (totalOrcamento !== 100) {
        const ok = confirm(
          `${totalOrcamento}/100 pontos alocados entre as sprints. Marcar como entregue mesmo assim?`
        );
        if (!ok) return;
      }
    }
    try {
      const updated = await toggleDelivered(id);
      setProject(updated);
    } catch {
      alert("Erro ao atualizar status do projeto.");
    }
  }

  async function handleStartGitHubConnection() {
    setGithubLoading(true);
    setGithubError("");
    try {
      const session = await startGitHubConnection(id);
      window.location.assign(session.install_url);
    } catch (err) {
      setGithubError(err instanceof Error ? err.message : "Não foi possível iniciar a conexão com o GitHub.");
      setGithubLoading(false);
    }
  }

  async function handleConnectRepositories() {
    if (githubSelected.length === 0) {
      setGithubError("Selecione pelo menos um repositório no GitHub.");
      return;
    }
    setGithubLoading(true);
    setGithubError("");
    try {
      await connectProjectRepositories(id, githubConnectionToken, githubSelected);
      setGithubRepositories(await listProjectRepositories(id));
      setGithubCandidates([]);
      setGithubConnectionToken("");
      window.history.replaceState({}, "", window.location.pathname + "?tab=config");
    } catch (err) {
      setGithubError(err instanceof Error ? err.message : "Não foi possível conectar os repositórios.");
    } finally {
      setGithubLoading(false);
    }
  }

  async function handleDisconnectRepository(repository: ProjectRepository) {
    if (!confirm(`Desconectar ${repository.full_name}? O histórico de commits já ingerido será preservado.`)) return;
    setGithubLoading(true);
    setGithubError("");
    try {
      await disconnectProjectRepository(id, repository.id);
      setGithubRepositories(await listProjectRepositories(id));
    } catch (err) {
      setGithubError(err instanceof Error ? err.message : "Não foi possível desconectar o repositório.");
    } finally {
      setGithubLoading(false);
    }
  }

  async function handleExportGdocs(docId: string) {
    setExportingDocId(docId);
    setExportError((prev) => { const n = { ...prev }; delete n[docId]; return n; });
    try {
      const { url } = await exportToGdocs(docId);
      window.open(url, "_blank");
    } catch (e) {
      setExportError((prev) => ({ ...prev, [docId]: e instanceof Error ? e.message : "Erro ao exportar" }));
    } finally {
      setExportingDocId(null);
    }
  }

  async function handleDeleteDoc(docId: string) {
    if (!confirm("Excluir este documento?")) return;
    try {
      await deleteDoc(docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
      if (generatedDoc?.id === docId) setGeneratedDoc(null);
      if (expandedDocId === docId) setExpandedDocId(null);
    } catch {
      alert("Erro ao excluir documento.");
    }
  }

  async function handleMoveDoc(docId: string, sprintNumber: number | null) {
    try {
      const updated = await moveDoc(docId, sprintNumber);
      setDocs((prev) => prev.map((d) => d.id === docId ? updated : d));
    } catch {
      alert("Erro ao mover documento.");
    }
  }

  async function handleDeleteIngestion(ingestionId: string) {
    try {
      await deleteIngestion(ingestionId);
      setIngestions((prev) => prev.filter((i) => i.id !== ingestionId));
      refreshSprints();
    } catch {
      alert("Erro ao excluir ingestão.");
    }
  }

  async function handleMoveIngestion(ingestionId: string, sprintNumber: number) {
    try {
      const updated = await moveIngestion(ingestionId, sprintNumber);
      setIngestions((prev) => prev.map((i) => i.id === ingestionId ? updated : i));
      refreshSprints();
    } catch {
      alert("Erro ao mover ingestão.");
    }
  }

  async function handleGerarResumoSemanal() {
    setGerandoResumo(true);
    try {
      const result = await gerarResumoSemanal(id);
      setResumoSemanal(result.content);
    } catch {
      // silently ignore
    } finally {
      setGerandoResumo(false);
    }
  }

  function handleUploadLivre(sprintNumero: number) {
    setUploadModal({ sprintNumero });
  }

  function handleGenerateFromCard(tipoDoc: "repasse_semanal", sprintNumero: number) {
    handleGenerate(tipoDoc, sprintNumero);
  }


  async function handleAtaUpload(sprintNumero: number, file: File) {
    setGenerating(true);
    setGeneratedDoc(null);
    setGenerateError("");
    try {
      const res = await submitAtaUpload({ projetoId: id, sprintNumero, anexo: file });
      // Adapta o SprintDocResponse pro shape do GeneratedDoc
      setGeneratedDoc({
        id: res.doc_id,
        doc_type: res.doc_type,
        sprint_number: res.sprint_number,
        content: res.content,
        created_at: res.created_at,
      });
      await refreshAll();
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Erro ao gerar ata a partir do PDF");
    } finally {
      setGenerating(false);
    }
  }

  // ---------- derived ----------
  const ingestionsBySprint = useMemo(() => {
    const map: Record<number, Ingestion[]> = {};
    for (const ing of ingestions) {
      (map[ing.sprint_number] ??= []).push(ing);
    }
    return map;
  }, [ingestions]);

  const docsBySprint = useMemo(() => {
    const map: Record<number, GeneratedDoc[]> = {};
    for (const d of docs) {
      if (d.sprint_number != null) (map[d.sprint_number] ??= []).push(d);
    }
    return map;
  }, [docs]);

  const totalPendencias = sprints.reduce((acc, s) => acc + s.pendencias.length, 0);

  function renderDocRow(doc: GeneratedDoc) {
    return (
      <DocRow
        key={doc.id}
        doc={doc}
        expandedDocId={expandedDocId}
        exportingDocId={exportingDocId}
        exportError={exportError}
        onToggleExpand={(id: string) => setExpandedDocId(expandedDocId === id ? null : id)}
        onExport={handleExportGdocs}
        onDelete={handleDeleteDoc}
        onMove={handleMoveDoc}
        ingestionCard={ingestionCard}
        tagStyle={tagStyle}
        btnSecondary={btnSecondary}
        btnDanger={btnDanger}
        markdownContainer={markdownContainer}
      />
    );
  }

  if (loading) return <p style={{ padding: 48, color: "#9696a0" }}>Carregando...</p>;
  if (!project) return <p style={{ padding: 48, color: "#dc2626" }}>Projeto não encontrado.</p>;

  return (
    <main style={{ maxWidth: 920, margin: "0 auto", padding: "48px 24px" }}>
      <Link href={`/${subarea}`} style={{ fontSize: 13, color: "#9696a0" }}>← Projetos</Link>

      {/* HEADER */}
      <div style={{ marginTop: 24, marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "start", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.02em", color: "#111116", margin: 0 }}>
            {project.name}
          </h1>
          <p style={{ marginTop: 6, fontSize: 14, color: "#9696a0", margin: 0 }}>
            Cliente: <span style={{ color: "#22c55e", fontWeight: 600 }}>{project.client}</span>
          </p>
          {project.description && (
            <div style={{ marginTop: 8 }}>
              <button
                onClick={() => setDescOpen((v) => !v)}
                style={{ background: "none", border: "none", cursor: "pointer", padding: 0, fontSize: 12, color: "#9696a0", display: "flex", alignItems: "center", gap: 4 }}
              >
                <span style={{ fontSize: 10 }}>{descOpen ? "▲" : "▼"}</span>
                {descOpen ? "Ocultar descrição" : "Ver descrição"}
              </button>
              {descOpen && (
                <p style={{ color: "#9696a0", marginTop: 6, fontSize: 13, lineHeight: 1.5, maxWidth: 560 }}>
                  {project.description}
                </p>
              )}
            </div>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
          {project.is_delivered && (
            <span style={{ ...badgeChip, background: "#dcfce7", color: "#16a34a" }}>✓ Entregue</span>
          )}
        </div>
      </div>

      <Tabs
        tabs={[
          { id: "sprints", label: "Sprints", badge: totalPendencias > 0 ? `${totalPendencias} pend.` : undefined },
          { id: "escopo", label: "Planejamento", badge: funcionalidades.length || undefined },
          { id: "painel", label: "Painel" },
          { id: "tasks", label: "Tasks" },
          { id: "metricas", label: "Métricas" },
          { id: "tecnologias", label: "Tecnologias" },
          { id: "documentos", label: "Documentos", badge: docs.length || undefined },
          { id: "config", label: "Configurações" },
        ].filter((t) => cargo !== "operacional" || OPERACIONAL_TABS.has(t.id))}
        active={activeTab}
        onChange={(t) => setActiveTab(t as TabId)}
      />

      {githubVisible && githubRepositories.every((repo) => !repo.active) && activeTab !== "config" && (
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16,
          padding: "13px 16px", margin: "-8px 0 18px", border: "1px solid #bfdbfe",
          borderRadius: 12, background: "#eff6ff", color: "#1e3a8a", fontSize: 13,
        }}>
          <span>Conecte os repositórios deste projeto para incorporar automaticamente os commits ao contexto.</span>
          <button style={{ ...btnSecondary, color: "#1d4ed8", borderColor: "#93c5fd" }} onClick={() => setActiveTab("config")}>
            Configurar
          </button>
        </div>
      )}

      {/* ABA: SPRINTS */}
      {activeTab === "sprints" && (
        <>
          <TutorialBanner heading="Sprints e Documentação" steps={[
            { title: "Criar uma sprint", body: "Clique em '+ Nova sprint'. O número é atribuído automaticamente. Cada sprint representa um ciclo de trabalho (geralmente 1–2 semanas)." },
            { title: "Planning", body: "Clique no chip 'Planning' na sprint. A tela já abre mostrando as tasks que estão no Kanban desta sprint, porque é dali que sai o backlog do documento: coluna, pontos e bloqueios entram no contexto da IA automaticamente. Você não precisa listar nada à mão. Abaixo das tasks tem o campo 'Contexto da sprint', em texto livre e sem formatação, para contar o que o Kanban não diz: por que a sprint é curta, o que mudou com o cliente, o que te preocupa. Se as tasks estiverem fora do DocuData (Notion, planilha, print), use o link no topo da tela para importar. E se preferir escrever o documento inteiro na mão, sem IA, use 'Escrever sem IA'." },
            { title: "Daily", body: "Registre as dailys ao longo da sprint. Cada upload vira um registro no histórico da sprint. Não há mínimo obrigatório, mas quanto mais dailys, mais rica a documentação final e o repasse semanal gerado pela IA." },
            { title: "Review", body: "Ao final da sprint, registre o review preenchendo os campos do formulário (Percepção do cliente, Sinal de satisfação, Pedidos fora do escopo, etc.). O documento gerado captura automaticamente o estado do kanban da sprint no momento da geração — cada task com seu status atual (planejada, em andamento, concluída, bloqueada) é injetada no contexto da IA sem você precisar listar manualmente. Além disso, o DocuData detecta tasks mencionadas no texto e cria sugestões de mover para 'Concluída' na aba Tasks." },
            { title: "Retrospectiva", body: "Após o review, gere a retrospectiva clicando no botão dedicado na sprint. A IA usa todas as ingestões da sprint (planning, dailys, review) para gerar: O que foi feito, O que funcionou, O que não funcionou, Aprendizados." },
            { title: "Orçamento de pontos da sprint", body: "Todo projeto vale 100 pontos, fixo. Na aba Planejamento você distribui esses 100 entre as sprints, e o card da sprint mostra quanto ela recebeu e quanto já foi gasto em tasks. É esse número que faz a aba Métricas calcular o SPI e o faturamento previsto." },
            { title: "Avaliação Semanal", body: "No fim da sprint, o botão 'Avaliação Semanal' abre as sete perguntas sobre cada operacional que teve task na sprint. Só dá para confirmar quando não sobrar ninguém pendente. Confirmar fecha a semana e trava a pontuação: as tasks daquela sprint não podem mais ser excluídas. Antes de confirmar, confira se as tasks estão na coluna certa, se os bloqueios foram resolvidos com o responsável correto, e se as tasks concedidas fora do planejado estão marcadas como extra." },
            { title: "Reabrir um fechamento errado", body: "Se a semana foi fechada com o Kanban desatualizado, o Líder consegue desfazer pelo botão 'Reabrir fechamento' no card da sprint. Ele apaga a pontuação travada e devolve a sprint ao estado aberto, sem apagar as respostas do questionário. É conserto, não rotina." },
            { title: "Pendências", body: "Sprints sem planning ou review são marcadas com 'pend.' no badge da aba. O número total de pendências aparece no topo das abas como lembrete para o gerente." },
          ]} />
          {/* SPRINTS — header destacado */}
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
            marginTop: 4,
          }}>
            <div>
              <h2 style={{
                fontSize: 22,
                fontWeight: 800,
                color: "#0f172a",
                letterSpacing: "-0.02em",
                margin: 0,
              }}>
                Sprints
                <span style={{
                  fontSize: 14,
                  color: "#94a3b8",
                  fontWeight: 600,
                  marginLeft: 10,
                }}>
                  {sprints.length} {sprints.length === 1 ? "sprint" : "sprints"}
                  {totalPendencias > 0 && ` · ${totalPendencias} pendência${totalPendencias === 1 ? "" : "s"}`}
                </span>
              </h2>
              <p style={{ color: "#64748b", fontSize: 13, margin: "6px 0 0", lineHeight: 1.5, maxWidth: 620 }}>
                Cada sprint tem documentação mínima obrigatória (Planning, Review) e recomendada (Dailys). Clique nos chips coloridos pra registrar, ou use os botões pra gerar docs derivadas.
              </p>
            </div>
            <button onClick={handleCreateSprint} style={btnPrimary}>Iniciar próxima sprint</button>
          </div>

          {sprints.some((s) => !s.iniciada) && (
            <section style={{ ...sectionStyle, marginBottom: 16 }}>
              <button
                onClick={() => setPlanejadasAbertas((v) => !v)}
                style={{
                  display: "flex", alignItems: "center", gap: 6, width: "100%",
                  background: "none", border: "none", cursor: "pointer", padding: 0,
                  marginBottom: planejadasAbertas ? 10 : 0,
                }}
              >
                <span style={{ fontSize: 11, color: "#9696a0", transform: planejadasAbertas ? "rotate(90deg)" : "none", transition: "transform 0.15s" }}>▶</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#9696a0", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Planejadas, ainda não iniciadas
                </span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#4338ca", background: "#eef2ff", borderRadius: 999, padding: "1px 8px" }}>
                  {sprints.filter((s) => !s.iniciada).length}
                </span>
              </button>
              {planejadasAbertas && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {sprints.filter((s) => !s.iniciada).map((s) => (
                  <div key={s.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f0f0f4" }}>
                    <span style={{ fontSize: 13, color: "#374151" }}>
                      Sprint {s.numero}
                      {s.pontos_orcamento != null && (
                        <span style={{ color: "#9696a0", marginLeft: 8 }}>{s.pontos_orcamento} pts orçados</span>
                      )}
                    </span>
                    <button
                      onClick={async () => {
                        const atualizado = await iniciarSprint(s.id);
                        setSprints((prev) => prev.map((x) => (x.id === s.id ? { ...x, ...atualizado } : x)));
                      }}
                      style={{ background: "#0f172a", color: "#fff", border: "none", borderRadius: 8, padding: "6px 14px", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                    >
                      Iniciar sprint
                    </button>
                  </div>
                ))}
              </div>
              )}
            </section>
          )}

          {sprints.filter((s) => s.iniciada).length === 0 ? (
            <section style={sectionStyle}>
              <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>
                Nenhuma sprint iniciada. Clique em <strong>Iniciar próxima sprint</strong> pra começar, ou
                inicie uma das sprints planejadas acima.
              </p>
            </section>
          ) : (
            sprints.filter((s) => s.iniciada).map((s) => (
              <SprintCard
                key={s.id}
                sprint={s}
                ingestions={ingestionsBySprint[s.numero] ?? []}
                docs={docsBySprint[s.numero] ?? []}
                generating={generating}
                onOpenSprintDoc={(tipo, n) => {
                  const sp = sprints.find((x) => x.numero === n);
                  setModal({ tipo, sprintNumero: n, sprintId: sp?.id });
                }}
                onOpenPlanning={(sprint) => setPlanningModal({ sprint })}
                onUploadLivre={handleUploadLivre}
                onGenerateSprintDoc={handleGenerateFromCard}
                onOpenRetroModal={(n) => setRetroModal({ sprintNumero: n })}
                onAddManualDoc={(n) => setManualModal({ sprintNumero: n })}
                onExportGdocs={handleExportGdocs}
                exportingDocId={exportingDocId}
                onDeleteDoc={handleDeleteDoc}
                onMoveDoc={handleMoveDoc}
                onDeleteIngestion={handleDeleteIngestion}
                onMoveIngestion={handleMoveIngestion}
                onDeleteSprint={handleDeleteSprint}
                onSprintUpdated={(updated) => setSprints((prev) => prev.map((s) => s.id === updated.id ? { ...s, ...updated } : s))}
                onOpenAvaliacaoSemanal={(s2) => setAvaliacaoModal({ sprintId: s2.id, sprintNumero: s2.numero })}
              />
            ))
          )}
        </>
      )}

      {/* ABA: PAINEL */}
      {activeTab === "painel" && project && (
        <PainelTab
          projectId={id}
          sprints={sprints}
          project={project}
          onProjectUpdated={(updated) => setProject(updated)}
        />
      )}

      {/* ABA: TASKS */}
      {activeTab === "tasks" && (
        <TasksKanbanTab
          projectId={id}
          sprints={sprints}
          operacionais={operacionais}
          funcionalidades={funcionalidades}
        />
      )}

      {/* ABA: MÉTRICAS */}
      {activeTab === "metricas" && <MetricasTab projectId={id} />}

      {/* ABA: TECNOLOGIAS */}
      {activeTab === "tecnologias" && <TechnologiesTab projectId={id} />}

      {/* ABA: DOCUMENTOS */}
      {activeTab === "documentos" && (
        <>
          {/* Sub-tabs */}
          <div style={{ display: "flex", gap: 4, marginBottom: 20, background: "#f7f7fa", borderRadius: 10, padding: 4, width: "fit-content" }}>
            {(["cross_sprint", "por_sprint"] as const).map((sub) => (
              <button
                key={sub}
                onClick={() => setDocSubTab(sub)}
                style={{
                  background: docSubTab === sub ? "#fff" : "transparent",
                  color: docSubTab === sub ? "#0f172a" : "#6a6a7a",
                  border: docSubTab === sub ? "1px solid #e4e4ea" : "1px solid transparent",
                  borderRadius: 7,
                  padding: "6px 14px",
                  fontSize: 13,
                  fontWeight: docSubTab === sub ? 700 : 500,
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                {sub === "cross_sprint" ? "Cross-sprint" : "Por sprint"}
              </button>
            ))}
          </div>

          {/* Sub-aba: Cross-sprint */}
          {docSubTab === "cross_sprint" && (
            <section style={sectionStyle}>
              <TutorialBanner heading="Documentos Cross-sprint" steps={[
                { title: "O que é Cross-sprint", body: "Documentos que cobrem o projeto inteiro — não estão ligados a uma sprint específica. São os entregáveis de documentação final para o cliente ou para novos membros da equipe." },
                { title: "Ata de Reunião", body: "Faça upload de um PDF ou arquivo de ata de reunião (com o cliente, stakeholders, etc). O DocuData gera uma ata formatada com pauta, decisões e próximos passos. Útil para registrar reuniões fora do ciclo de sprint." },
                { title: "Log de Decisões", body: "Compila automaticamente todas as decisões técnicas e de negócio registradas em todas as ingestões do projeto (plannings, reviews, dailys). Ideal para onboarding de novos membros e auditoria." },
                { title: "Onboarding", body: "Documento de integração para novos membros entrarem no projeto rapidamente: contexto do cliente, stack técnica, decisões tomadas, estado atual. Gerado a partir de todo o histórico de ingestões." },
                { title: "Documentação Final", body: "Documento completo para entrega ao cliente ao final do projeto: visão geral, timeline de sprints, decisões arquiteturais, desafios superados e estado final. Preenche o vazio de documentação que existe em muitos projetos de dados." },
                { title: "Observações adicionais", body: "O campo de observações permite incluir contexto extra que a IA deve considerar na geração. Use para orientações específicas, tom desejado, ou informações que não estão nos uploads." },
                { title: "Doc manual", body: "Adicione qualquer documento sem custo de IA — cole o texto diretamente. Útil para atas já escritas, contratos, ou qualquer conteúdo que não precisa ser gerado." },
                { title: "Google Docs", body: "Exporte qualquer documento gerado para o Google Docs com um clique. Requer que o projeto tenha uma conta Google configurada. O link abre diretamente no navegador." },
              ]} />
              <p style={{ fontSize: 13, color: "#6a6a7a", margin: "0 0 14px", lineHeight: 1.5 }}>
                Documentos que olham o projeto como um todo.
              </p>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Observações adicionais <span style={{ fontWeight: 400, color: "#b8b8c0" }}>(opcional)</span></label>
                <textarea
                  value={observacoes}
                  onChange={(e) => setObservacoes(e.target.value)}
                  placeholder="Contexto extra que deve ser considerado na geração."
                  rows={2}
                  style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", lineHeight: 1.6 }}
                />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
                {(["ata_reuniao", "log_decisoes", "onboarding", "documentacao_final"] as DocTypeKey[]).map((key) => (
                  <DocTypeCard
                    key={key}
                    meta={DOC_TYPES[key]}
                    sprints={sprints}
                    ingestions={ingestions}
                    generating={generating}
                    onGenerate={handleGenerate}
                    onUploadAndGenerate={key === "ata_reuniao" ? handleAtaUpload : undefined}
                  />
                ))}
              </div>
              <div style={{ marginBottom: 10 }}>
                <button onClick={() => setManualModal({ sprintNumero: null })} style={btnSecondary}>
                  + Adicionar documento manual
                </button>
                <span style={{ marginLeft: 10, fontSize: 12, color: "#9696a0" }}>Sem custo de IA.</span>
              </div>
              {generating && <p style={{ color: "#9696a0", fontSize: 14 }}>Gerando documento com IA...</p>}
              {generateError && <p style={{ color: "#dc2626", fontSize: 14 }}>{generateError}</p>}
              {generatedDoc && (
                <div style={{ marginTop: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <span style={{ fontSize: 13, color: "#9696a0" }}>
                      {docTypeLabel(generatedDoc.doc_type)}
                      {generatedDoc.sprint_number ? <span style={{ ...tagStyle, marginLeft: 8 }}>Sprint {generatedDoc.sprint_number}</span> : null}
                    </span>
                    <button onClick={() => navigator.clipboard.writeText(generatedDoc.content)} style={{ ...btnSecondary, fontSize: 12, padding: "6px 12px" }}>Copiar markdown</button>
                  </div>
                  <div style={markdownContainer}><ReactMarkdown>{generatedDoc.content}</ReactMarkdown></div>
                </div>
              )}

              {/* Histórico cross-sprint */}
              {(() => {
                const crossSprintDocs = docs.filter((d) => d.sprint_number == null);
                if (crossSprintDocs.length === 0) return null;
                return (
                  <div style={{ marginTop: 20 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "#94a3b8" }}>Histórico</span>
                      <div style={{ flex: 1, height: 1, background: "#f1f5f9" }} />
                      <span style={{ fontSize: 12, color: "#94a3b8" }}>{crossSprintDocs.length} {crossSprintDocs.length === 1 ? "doc" : "docs"}</span>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {crossSprintDocs.map((doc) => renderDocRow(doc))}
                    </div>
                  </div>
                );
              })()}
            </section>
          )}

          {/* Sub-aba: Por sprint */}
          {docSubTab === "por_sprint" && (
            <>
              <TutorialBanner heading="Documentos Por sprint" steps={[
                { title: "Repasse Semanal", body: "Gerado a partir das dailys e ingestões da sprint. Resume o que foi feito na semana, pontos em andamento e próximos passos. Gere a partir do botão na sprint ou pela aba Sprints." },
                { title: "Retrospectiva", body: "Gerado ao final da sprint com base no planning, dailys e review. Inclui: O que foi feito, O que funcionou, O que não funcionou, Aprendizados. Gere pelo botão 'Retro' na sprint." },
                { title: "Mover documento de sprint", body: "Se um documento foi gerado na sprint errada, use 'Mover sprint' para corrigir sem precisar regerar." },
                { title: "Copiar e exportar", body: "Todo documento gerado pode ser copiado como markdown (para colar em qualquer ferramenta) ou exportado diretamente para o Google Docs." },
              ]} />
              {docs.filter((d) => d.sprint_number != null).length === 0 ? (
                <section style={sectionStyle}>
                  <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>
                    Nenhum documento por sprint ainda. Gere docs na aba <strong>Sprints</strong> (Repasse/Retrospectiva) ou aqui em <strong>Por sprint</strong>.
                  </p>
                </section>
              ) : (
                sprints.map((s) => {
                  const sprintDocs = docsBySprint[s.numero] ?? [];
                  if (sprintDocs.length === 0) return null;
                  return (
                    <section key={s.id} style={sectionStyle}>
                      <h3 style={{
                        fontSize: 13,
                        fontWeight: 700,
                        letterSpacing: "0.06em",
                        textTransform: "uppercase",
                        color: "#64748b",
                        margin: 0,
                        marginBottom: 12,
                      }}>
                        Sprint {s.numero}
                        <span style={{
                          fontSize: 11,
                          fontWeight: 700,
                          color: "#16a34a",
                          marginLeft: 8,
                          background: "#dcfce7",
                          borderRadius: 4,
                          padding: "2px 7px",
                        }}>
                          {sprintDocs.length}
                        </span>
                      </h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {sprintDocs.map((doc) => renderDocRow(doc))}
                      </div>
                    </section>
                  );
                })
              )}
            </>
          )}
        </>
      )}


      {/* ABA: CONFIG */}
      {activeTab === "config" && (
        <>
          {githubVisible && (
            <section style={{ ...sectionStyle, borderColor: "#c7d2fe" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 16 }}>
                <div>
                  <h2 style={{ ...sectionTitle, color: "#4338ca", marginBottom: 6 }}>Repositórios GitHub</h2>
                  <p style={{ fontSize: 13, color: "#64748b", margin: 0, lineHeight: 1.5 }}>
                    Os commits de todos os repositórios conectados alimentam automaticamente o contexto deste projeto.
                  </p>
                </div>
                <button onClick={handleStartGitHubConnection} disabled={githubLoading} style={{ ...btnPrimary, opacity: githubLoading ? 0.6 : 1 }}>
                  {githubRepositories.length > 0 ? "Conectar outro" : "Conectar GitHub"}
                </button>
              </div>

              {githubError && (
                <p role="alert" style={{ padding: "10px 12px", borderRadius: 8, background: "#fef2f2", color: "#b91c1c", fontSize: 13 }}>
                  {githubError}
                </p>
              )}

              {githubCandidates.length > 0 && (
                <div style={{ padding: 16, borderRadius: 10, border: "1px solid #c7d2fe", background: "#f5f3ff", marginBottom: 16 }}>
                  <strong style={{ display: "block", color: "#312e81", fontSize: 14, marginBottom: 4 }}>Selecione os repositórios</strong>
                  <p style={{ color: "#64748b", fontSize: 12, margin: "0 0 12px" }}>Todos os selecionados serão associados ao projeto {project.name}.</p>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {githubCandidates.map((repo) => (
                      <label key={repo.github_repository_id} style={{ display: "flex", alignItems: "center", gap: 9, padding: "8px 10px", borderRadius: 8, background: "#fff", cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={githubSelected.includes(repo.github_repository_id)}
                          onChange={(event) => setGithubSelected((current) => event.target.checked
                            ? [...current, repo.github_repository_id]
                            : current.filter((repositoryId) => repositoryId !== repo.github_repository_id))}
                        />
                        <span style={{ fontWeight: 650, color: "#1e293b", fontSize: 13 }}>{repo.full_name}</span>
                        {repo.private && <span style={{ ...badgeChip, background: "#f1f5f9", color: "#64748b" }}>Privado</span>}
                      </label>
                    ))}
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
                    <button style={btnSecondary} onClick={() => { setGithubCandidates([]); setGithubConnectionToken(""); }}>Cancelar</button>
                    <button style={{ ...btnPrimary, opacity: githubLoading ? 0.6 : 1 }} disabled={githubLoading} onClick={handleConnectRepositories}>
                      Conectar selecionados
                    </button>
                  </div>
                </div>
              )}

              {githubRepositories.length === 0 ? (
                <div style={{ padding: "18px 0 4px", textAlign: "center" }}>
                  <strong style={{ display: "block", color: "#334155", fontSize: 14 }}>Nenhum repositório conectado</strong>
                  <span style={{ color: "#94a3b8", fontSize: 12 }}>A conexão é recomendada, mas não bloqueia o uso do projeto.</span>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {githubRepositories.map((repo) => (
                    <div key={repo.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "11px 12px", border: "1px solid #e2e8f0", borderRadius: 9 }}>
                      <div style={{ minWidth: 0 }}>
                        <a href={repo.html_url} target="_blank" rel="noreferrer" style={{ color: "#3730a3", fontWeight: 700, fontSize: 13, textDecoration: "none" }}>{repo.full_name}</a>
                        <span style={{ marginLeft: 9, color: "#94a3b8", fontSize: 12 }}>{repo.default_branch ?? "branch padrão não informada"}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                        <span style={{ ...badgeChip, background: repo.active ? "#dcfce7" : "#fef2f2", color: repo.active ? "#15803d" : "#b91c1c" }}>
                          {repo.active ? "✓ Ativo" : repo.permission_status === "disconnected" ? "Desconectado" : "Permissão revogada"}
                        </span>
                        {repo.active ? (
                          <button style={{ ...btnDanger, padding: "5px 9px", fontSize: 11 }} onClick={() => handleDisconnectRepository(repo)}>Desconectar</button>
                        ) : (
                          <button style={{ ...btnSecondary, padding: "5px 9px", fontSize: 11 }} onClick={handleStartGitHubConnection}>Reconectar</button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}


          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Lembretes por email</h2>
            <p style={{ fontSize: 13, color: "#6a6a7a", marginTop: 0, marginBottom: 14, lineHeight: 1.5 }}>
              O DocuData envia lembretes automáticos quando a sprint não tem planning (após 24h), review (após 5 dias) ou retrospectiva (após 7 dias).
            </p>
            {project.gerente_email ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 13, color: "#16a34a", fontWeight: 600 }}>✓ {project.gerente_email}</span>
                  <button
                    onClick={() => { setEmailInput(""); handleSaveEmail({ preventDefault: () => {} } as React.FormEvent); }}
                    style={{ background: "none", border: "none", fontSize: 12, color: "#9696a0", cursor: "pointer", textDecoration: "underline", padding: 0 }}
                  >
                    Remover
                  </button>
                </div>
                <form onSubmit={handleSaveEmail} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    type="email"
                    placeholder="Trocar email..."
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    style={{ ...inputStyle, width: 240 }}
                  />
                  <button type="submit" disabled={savingEmail || !emailInput.trim()} style={btnSecondary}>
                    {savingEmail ? "..." : "Trocar"}
                  </button>
                </form>
              </div>
            ) : (
              <form onSubmit={handleSaveEmail} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input
                  type="email"
                  placeholder="email@exemplo.com"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  style={{ ...inputStyle, flex: 1 }}
                  required
                />
                <button type="submit" disabled={savingEmail} style={btnPrimary}>
                  {savingEmail ? "Salvando..." : "Ativar lembretes"}
                </button>
              </form>
            )}
            {emailMsg && <p style={{ marginTop: 10, fontSize: 13, color: emailMsg.ok ? "#16a34a" : "#dc2626" }}>{emailMsg.text}</p>}
          </section>

          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Status do projeto</h2>
            <button onClick={handleToggleDelivered} style={project.is_delivered ? btnDeliveredActive : btnDelivered}>
              {project.is_delivered ? "✓ Marcado como entregue (desfazer)" : "Marcar como entregue"}
            </button>
          </section>

          <OperacionaisSection
            projectId={id}
            operacionais={operacionais}
            onUpdated={setOperacionais}
          />

          <section style={{ ...sectionStyle, borderColor: "#fecaca" }}>
            <h2 style={{ ...sectionTitle, color: "#dc2626" }}>Zona perigosa</h2>
            <p style={{ fontSize: 13, color: "#6a6a7a", marginBottom: 14 }}>
              Excluir o projeto remove todas as ingestões, sprints e documentos. Esta ação é irreversível.
            </p>
            <button onClick={handleDeleteProject} style={btnDanger}>Excluir projeto</button>
          </section>
        </>
      )}

      {/* ABA: ESCOPO */}
      {activeTab === "escopo" && (
        <EscopoTab
          projectId={id}
          funcionalidades={funcionalidades}
          onImported={(novas) => setFuncionalidades((prev) => [...prev, ...novas])}
          onDeleted={(deletedId) => setFuncionalidades((prev) => prev.filter((f) => f.id !== deletedId))}
          sprints={sprints}
          onSprintUpdated={(updated) =>
            setSprints((prev) => prev.map((s) => (s.id === updated.id ? updated : s)))
          }
          onSprintCreated={(created) =>
            setSprints((prev) => [...prev, created].sort((a, b) => a.numero - b.numero))
          }
        />
      )}

      {/* MODAL Planning/Daily/Review */}
      <SprintDocModal
        open={modal !== null}
        onClose={() => setModal(null)}
        tipo={modal?.tipo ?? "daily"}
        projetoId={id}
        sprintNumero={modal?.sprintNumero ?? 1}
        initialCarryOver={carryOverPrefill}
        onSubmitted={async () => {
          await refreshAll();
          if (modal?.tipo === "review" && modal.sprintId) {
            setStatusModal({ sprintId: modal.sprintId, sprintNumero: modal.sprintNumero });
          }
        }}
      />

      {/* MODAL Planning — novo fluxo com correlação de funcionalidades */}
      {planningModal && (
        <PlanningModal
          open={planningModal !== null}
          onClose={() => setPlanningModal(null)}
          projetoId={id}
          sprintNumero={planningModal.sprint.numero}
          sprintId={planningModal.sprint.id}
          funcionalidades={funcionalidades}
          onSubmitted={async () => {
            setPlanningModal(null);
            await refreshAll();
          }}
        />
      )}

      {/* MODAL Avaliação Semanal */}
      {avaliacaoModal && (
        <AvaliacaoSemanalModal
          sprintId={avaliacaoModal.sprintId}
          sprintNumero={avaliacaoModal.sprintNumero}
          onClose={() => setAvaliacaoModal(null)}
          onCompleted={() => {
            setSprints((prev) =>
              prev.map((s) =>
                s.id === avaliacaoModal.sprintId ? { ...s, avaliacao_completa_em: new Date().toISOString() } : s
              )
            );
          }}
        />
      )}

      {/* MODAL Doc Manual */}
      <ManualDocModal
        open={manualModal !== null}
        onClose={() => setManualModal(null)}
        projetoId={id}
        defaultSprintNumero={manualModal?.sprintNumero ?? null}
        onCreated={async () => {
          await refreshAll();
        }}
      />

      {/* MODAL Status Funcionalidades — abre após review */}
      <FuncionalidadesStatusModal
        open={statusModal !== null}
        onClose={() => setStatusModal(null)}
        sprintId={statusModal?.sprintId ?? ""}
        sprintNumero={statusModal?.sprintNumero ?? 1}
        onUpdated={() => { setStatusModal(null); listFuncionalidades(id).then(setFuncionalidades).catch(() => {}); }}
      />

      {/* MODAL Upload Livre */}
      <UploadLivreModal
        open={uploadModal !== null}
        onClose={() => setUploadModal(null)}
        projetoId={id}
        sprintNumero={uploadModal?.sprintNumero ?? 1}
        onCompleted={async () => {
          await refreshAll();
        }}
      />

      {/* MODAL Retrospectiva */}
      <RetroModal
        open={retroModal !== null}
        onClose={() => setRetroModal(null)}
        projetoId={id}
        sprintNumero={retroModal?.sprintNumero ?? 1}
        onSubmitted={(doc) => {
          setDocs((prev) => [doc as unknown as GeneratedDoc, ...prev]);
          setRetroModal(null);
        }}
      />
    </main>
  );
}

// ---------- styles ----------

const sectionStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "20px 22px",
  marginBottom: 14,
};
const sectionTitle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  marginBottom: 16,
  color: "#9696a0",
};
const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 700,
  marginBottom: 6,
  color: "#6a6a7a",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
};
const inputStyle: React.CSSProperties = {
  padding: "9px 12px",
  background: "#ffffff",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  fontSize: 14,
  width: "100%",
  outline: "none",
  color: "#111116",
  boxSizing: "border-box",
};
const btnPrimary: React.CSSProperties = {
  background: "#4ade80",
  color: "#0a0a0a",
  border: "none",
  borderRadius: 8,
  padding: "9px 18px",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
  whiteSpace: "nowrap",
};
function DocRow({
  doc,
  expandedDocId,
  exportingDocId,
  exportError,
  onToggleExpand,
  onExport,
  onDelete,
  onMove,
  ingestionCard,
  tagStyle,
  btnSecondary: btnSec,
  btnDanger: btnDng,
  markdownContainer: mdContainer,
}: {
  doc: GeneratedDoc;
  expandedDocId: string | null;
  exportingDocId: string | null;
  exportError: Record<string, string>;
  onToggleExpand: (id: string) => void;
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
  onMove: (id: string, sprint: number | null) => void;
  ingestionCard: React.CSSProperties;
  tagStyle: React.CSSProperties;
  btnSecondary: React.CSSProperties;
  btnDanger: React.CSSProperties;
  markdownContainer: React.CSSProperties;
}) {
  const [movingDoc, setMovingDoc] = useState(false);
  const [moveToSprint, setMoveToSprint] = useState("");
  return (
    <div style={ingestionCard}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, fontSize: 14, color: "#0f172a" }}>{docTypeLabel(doc.doc_type)}</span>
          {doc.sprint_number && <span style={tagStyle}>Sprint {doc.sprint_number}</span>}
          <span style={{ color: "#94a3b8", fontSize: 12 }}>{new Date(doc.created_at).toLocaleDateString("pt-BR")}</span>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button onClick={() => onToggleExpand(doc.id)} style={{ ...btnSec, fontSize: 12, padding: "6px 12px" }}>
            {expandedDocId === doc.id ? "Fechar" : "Ver"}
          </button>
          <button onClick={() => navigator.clipboard.writeText(doc.content)} style={{ ...btnSec, fontSize: 12, padding: "6px 12px" }}>
            Copiar
          </button>
          <button
            onClick={() => onExport(doc.id)}
            disabled={exportingDocId === doc.id}
            style={{ ...btnSec, fontSize: 12, padding: "6px 12px", opacity: exportingDocId === doc.id ? 0.6 : 1 }}
          >
            {exportingDocId === doc.id ? "Exportando…" : "Google Docs"}
          </button>
          <button onClick={() => { setMovingDoc(true); setMoveToSprint(""); }} style={{ ...btnSec, fontSize: 12, padding: "6px 12px" }}>
            Mover sprint
          </button>
          <button onClick={() => { if (confirm("Excluir este documento?")) onDelete(doc.id); }} style={{ ...btnDng, fontSize: 12, padding: "6px 12px" }}>
            Excluir
          </button>
          {exportError[doc.id] && <span style={{ fontSize: 11, color: "#dc2626" }}>{exportError[doc.id]}</span>}
        </div>
      </div>
      {movingDoc && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 10 }}>
          <span style={{ fontSize: 13, color: "#64748b" }}>Mover para sprint:</span>
          <input
            type="number"
            min={1}
            value={moveToSprint}
            onChange={(e) => setMoveToSprint(e.target.value)}
            style={{ width: 70, padding: "5px 10px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 13 }}
            autoFocus
          />
          <button
            style={{ ...btnSec, fontSize: 12, padding: "6px 14px", background: "#dcfce7", color: "#15803d", borderColor: "#86efac" }}
            onClick={() => { const n = parseInt(moveToSprint); if (!isNaN(n) && n > 0) { onMove(doc.id, n); setMovingDoc(false); } }}
          >
            Confirmar
          </button>
          <button style={{ ...btnSec, fontSize: 12, padding: "6px 12px" }} onClick={() => setMovingDoc(false)}>Cancelar</button>
        </div>
      )}
      {expandedDocId === doc.id && (
        <div style={{ ...mdContainer, marginTop: 14 }}>
          <ReactMarkdown>{doc.content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

const btnSecondary: React.CSSProperties = {
  background: "#f7f7fa",
  color: "#374151",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  padding: "8px 14px",
  fontSize: 13,
  fontWeight: 500,
  cursor: "pointer",
};
const btnDanger: React.CSSProperties = {
  background: "#fef2f2",
  color: "#dc2626",
  border: "1px solid #fecaca",
  borderRadius: 8,
  padding: "8px 14px",
  fontSize: 13,
  fontWeight: 500,
  cursor: "pointer",
};
const ingestionCard: React.CSSProperties = {
  background: "#f7f7fa",
  border: "1px solid #e8e8ed",
  borderRadius: 8,
  padding: "12px 16px",
};
const tagStyle: React.CSSProperties = {
  background: "#dcfce7",
  color: "#16a34a",
  borderRadius: 4,
  padding: "2px 8px",
  fontSize: 11,
  fontWeight: 600,
};
const markdownContainer: React.CSSProperties = {
  background: "#f7f7fa",
  border: "1px solid #e8e8ed",
  borderRadius: 10,
  padding: "20px 24px",
  lineHeight: 1.8,
  color: "#374151",
};
const btnDelivered: React.CSSProperties = {
  background: "#f7f7fa",
  color: "#6a6a7a",
  border: "1px solid #e4e4ea",
  borderRadius: 8,
  padding: "9px 16px",
  fontSize: 13,
  fontWeight: 500,
  cursor: "pointer",
};
const btnDeliveredActive: React.CSSProperties = {
  background: "#dcfce7",
  color: "#16a34a",
  border: "1px solid #86efac",
  borderRadius: 8,
  padding: "9px 16px",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
};
const alertBox: React.CSSProperties = {
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: 12,
  padding: "16px 20px",
  marginBottom: 18,
};
const badgeChip: React.CSSProperties = {
  display: "inline-block",
  padding: "3px 9px",
  borderRadius: 6,
  fontSize: 11,
  fontWeight: 700,
};
