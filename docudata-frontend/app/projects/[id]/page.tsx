"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  getProject,
  getProjectCost,
  updateApiKey,
  listIngestions,
  listDocs,
  listSprints,
  createSprint,
  ingestFile,
  generateDoc,
  submitAtaUpload,
  deleteProject,
  deleteDoc,
  toggleDelivered,
  type Project,
  type Ingestion,
  type GeneratedDoc,
  type ProjectCost,
  type SprintWithStatus,
  type SprintDocType,
} from "../../lib/api";
import Tabs from "../../components/Tabs";
import SprintCard from "../../components/SprintCard";
import SprintDocModal from "../../components/SprintDocModal";
import TechnologiesTab from "../../components/TechnologiesTab";
import DocTypeCard from "../../components/DocTypeCard";
import ManualDocModal from "../../components/ManualDocModal";
import { DOC_TYPES, docTypeLabel, type DocTypeKey } from "../../lib/doc_types";

type TabId = "sprints" | "tecnologias" | "docs" | "config";

export default function ProjectDashboard() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  // ---------- data ----------
  const [project, setProject] = useState<Project | null>(null);
  const [ingestions, setIngestions] = useState<Ingestion[]>([]);
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [sprints, setSprints] = useState<SprintWithStatus[]>([]);
  const [cost, setCost] = useState<ProjectCost | null>(null);
  const [loading, setLoading] = useState(true);

  // ---------- ui ----------
  const [activeTab, setActiveTab] = useState<TabId>("sprints");

  // ---------- modal sprint-docs ----------
  const [modal, setModal] = useState<{ tipo: SprintDocType; sprintNumero: number } | null>(null);

  // ---------- modal doc manual ----------
  const [manualModal, setManualModal] = useState<{ sprintNumero: number | null } | null>(null);

  // ---------- upload livre ----------
  const [uploadMode, setUploadMode] = useState<"file" | "folder">("file");
  const [file, setFile] = useState<File | null>(null);
  const [sprint, setSprint] = useState<number>(1);
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [folderFiles, setFolderFiles] = useState<File[]>([]);
  const [folderIngesting, setFolderIngesting] = useState(false);
  const [folderProgress, setFolderProgress] = useState<
    { done: number; total: number; errors: string[]; cancelled?: boolean } | null
  >(null);
  const cancelRef = useRef(false);
  const uploadSectionRef = useRef<HTMLDivElement | null>(null);

  // ---------- geração ----------
  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDoc | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);

  // ---------- api key ----------
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [apiKeyMsg, setApiKeyMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [savingKey, setSavingKey] = useState(false);

  // ---------- bootstrap ----------
  useEffect(() => {
    Promise.all([
      getProject(id),
      listIngestions(id),
      listDocs(id),
      getProjectCost(id),
      listSprints(id),
    ])
      .then(([p, ings, d, c, s]) => {
        setProject(p);
        setIngestions(ings);
        setDocs(d);
        setCost(c);
        setSprints(s);
      })
      .finally(() => setLoading(false));
  }, [id]);

  function refreshCost() {
    getProjectCost(id).then(setCost).catch(() => {});
  }
  function refreshSprints() {
    listSprints(id).then(setSprints).catch(() => {});
  }
  async function refreshAll() {
    const [ings, d, c, s] = await Promise.all([
      listIngestions(id),
      listDocs(id),
      getProjectCost(id),
      listSprints(id),
    ]);
    setIngestions(ings);
    setDocs(d);
    setCost(c);
    setSprints(s);
  }

  // ---------- handlers ----------
  async function handleSaveApiKey(e: React.FormEvent) {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;
    setSavingKey(true);
    setApiKeyMsg(null);
    try {
      const updated = await updateApiKey(id, apiKeyInput.trim());
      setProject(updated);
      setApiKeyInput("");
      setApiKeyMsg({ ok: true, text: "Chave salva com sucesso." });
    } catch {
      setApiKeyMsg({ ok: false, text: "Erro ao salvar chave." });
    } finally {
      setSavingKey(false);
    }
  }

  async function handleCreateSprint() {
    try {
      await createSprint(id);
      refreshSprints();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao criar sprint");
    }
  }

  const ACCEPTED_EXTS = new Set([
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".sql",
    ".yaml", ".yml", ".json", ".csv", ".html", ".css", ".java",
    ".go", ".rs", ".rb", ".sh", ".toml", ".xml", ".env",
    ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".webp",
  ]);
  const SKIP_DIRS = new Set([
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".cache", ".idea", ".vscode",
  ]);

  async function resizeImageIfNeeded(f: File, maxDim = 1024): Promise<File> {
    if (!f.type.startsWith("image/")) return f;
    return new Promise((resolve) => {
      const img = new Image();
      const url = URL.createObjectURL(f);
      img.onload = () => {
        URL.revokeObjectURL(url);
        const { naturalWidth: w, naturalHeight: h } = img;
        if (w <= maxDim && h <= maxDim) { resolve(f); return; }
        const scale = maxDim / Math.max(w, h);
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(w * scale);
        canvas.height = Math.round(h * scale);
        canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(
          (blob) => resolve(blob ? new File([blob], f.name, { type: "image/jpeg" }) : f),
          "image/jpeg",
          0.85
        );
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(f); };
      img.src = url;
    });
  }

  function isAcceptedFile(f: File): boolean {
    if (f.size < 100) return false;
    const path = (f as File & { webkitRelativePath: string }).webkitRelativePath || f.name;
    const segments = path.split("/");
    if (segments.slice(0, -1).some((s) => SKIP_DIRS.has(s))) return false;
    const ext = "." + (f.name.split(".").pop() ?? "").toLowerCase();
    return ACCEPTED_EXTS.has(ext);
  }

  function handleFolderChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFolderFiles(Array.from(e.target.files ?? []).filter(isAcceptedFile));
    setFolderProgress(null);
  }

  async function handleFolderIngest(e: React.FormEvent) {
    e.preventDefault();
    if (folderFiles.length === 0) return;
    cancelRef.current = false;
    setFolderIngesting(true);
    setFolderProgress({ done: 0, total: folderFiles.length, errors: [] });
    const CONCURRENCY = 5;
    const errors: string[] = [];
    let done = 0;
    let idx = 0;
    async function worker() {
      while (true) {
        if (cancelRef.current) break;
        const myIdx = idx++;
        if (myIdx >= folderFiles.length) break;
        const f = folderFiles[myIdx];
        const relativePath =
          (f as File & { webkitRelativePath: string }).webkitRelativePath || f.name;
        try {
          const fileToSend = await resizeImageIfNeeded(
            new File([f], relativePath, { type: f.type })
          );
          await ingestFile(id, sprint, fileToSend);
        } catch {
          errors.push(relativePath);
        }
        done++;
        setFolderProgress({ done, total: folderFiles.length, errors: [...errors] });
      }
    }
    await Promise.all(Array.from({ length: CONCURRENCY }, worker));
    setFolderIngesting(false);
    if (!cancelRef.current) {
      await refreshAll();
    } else {
      setFolderProgress((p) => (p ? { ...p, cancelled: true } : null));
    }
  }

  async function handleIngest(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setIngesting(true);
    setIngestMsg(null);
    try {
      await ingestFile(id, sprint, await resizeImageIfNeeded(file));
      setIngestMsg({ ok: true, text: `"${file.name}" processado com sucesso.` });
      setFile(null);
      await refreshAll();
    } catch (err) {
      setIngestMsg({
        ok: false,
        text: err instanceof Error ? err.message : "Erro desconhecido",
      });
    } finally {
      setIngesting(false);
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
    try { await deleteProject(id); router.push("/"); }
    catch { alert("Erro ao excluir projeto."); }
  }

  async function handleToggleDelivered() {
    try {
      const updated = await toggleDelivered(id);
      setProject(updated);
    } catch {
      alert("Erro ao atualizar status do projeto.");
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

  function handleUploadLivre(sprintNumero: number) {
    setSprint(sprintNumero);
    setActiveTab("sprints");
    setTimeout(() => uploadSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  function handleGenerateFromCard(tipoDoc: "sprint_status" | "sprint_retro", sprintNumero: number) {
    // Gera direto e mantém o gerente na aba Sprints — o doc aparece dentro do próprio card
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

  if (loading) return <p style={{ padding: 48, color: "#9696a0" }}>Carregando...</p>;
  if (!project) return <p style={{ padding: 48, color: "#dc2626" }}>Projeto não encontrado.</p>;

  return (
    <main style={{ maxWidth: 920, margin: "0 auto", padding: "48px 24px" }}>
      <Link href="/" style={{ fontSize: 13, color: "#9696a0" }}>← Projetos</Link>

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
            <p style={{ color: "#9696a0", marginTop: 8, fontSize: 13, lineHeight: 1.5, maxWidth: 560 }}>
              {project.description}
            </p>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
          {cost && (
            <div style={{ fontSize: 12, color: "#6a6a7a", display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontWeight: 700, color: "#111116" }}>
                ${cost.total_usd < 0.001 && cost.total_usd > 0 ? cost.total_usd.toFixed(6) : cost.total_usd.toFixed(4)}
              </span>
              {cost.budget_usd != null && (
                <span style={{ color: "#b8b8c0" }}>/ ${cost.budget_usd.toFixed(2)}</span>
              )}
            </div>
          )}
          {project.is_delivered && (
            <span style={{ ...badgeChip, background: "#dcfce7", color: "#16a34a" }}>✓ Entregue</span>
          )}
        </div>
      </div>

      {/* API KEY ALERT — sempre visível se faltando */}
      {!project.has_api_key && (
        <section style={{ ...alertBox }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#dc2626", margin: 0, marginBottom: 12 }}>
            Chave de API do Gemini não configurada — uploads e geração de documentos não funcionarão.
          </p>
          <form onSubmit={handleSaveApiKey} style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input
              type="password"
              placeholder="AIza..."
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              style={{ ...inputStyle, flex: 1 }}
              required
            />
            <button type="submit" disabled={savingKey} style={btnPrimary}>
              {savingKey ? "Salvando..." : "Salvar chave"}
            </button>
          </form>
          {apiKeyMsg && (
            <p style={{ marginTop: 10, fontSize: 13, color: apiKeyMsg.ok ? "#16a34a" : "#dc2626" }}>
              {apiKeyMsg.text}
            </p>
          )}
        </section>
      )}

      <Tabs
        tabs={[
          { id: "sprints", label: "Sprints", badge: totalPendencias > 0 ? `${totalPendencias} pend.` : undefined },
          { id: "tecnologias", label: "Tecnologias" },
          { id: "docs", label: "Docs Gerais", badge: docs.length || undefined },
          { id: "config", label: "Configurações" },
        ]}
        active={activeTab}
        onChange={(t) => setActiveTab(t as TabId)}
      />

      {/* ABA: SPRINTS */}
      {activeTab === "sprints" && (
        <>
          {/* UPLOAD LIVRE */}
          <section ref={uploadSectionRef} style={sectionStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h2 style={sectionTitle}>Upload livre · Sprint {sprint}</h2>
              <div style={{ display: "flex", border: "1px solid #e4e4ea", borderRadius: 8, overflow: "hidden" }}>
                <button onClick={() => setUploadMode("file")} style={uploadMode === "file" ? modeTabActive : modeTab}>Arquivo</button>
                <button onClick={() => setUploadMode("folder")} style={uploadMode === "folder" ? modeTabActive : modeTab}>Pasta</button>
              </div>
            </div>
            <p style={{ fontSize: 13, color: "#6a6a7a", margin: "0 0 18px", lineHeight: 1.5 }}>
              Material avulso pra dar contexto ao projeto — print de conversa, código fonte, PDFs do cliente, ata externa, qualquer coisa que ajude o agente a entender o que está acontecendo. Esses uploads alimentam as documentações gerais (ADRs, Onboarding, Documentação Final). Pro mínimo obrigatório de cada sprint (Planning, Daily, Review) use os botões coloridos no card da sprint.
            </p>

            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Sprint</label>
              <input
                type="number"
                min={1}
                value={sprint}
                onChange={(e) => setSprint(Number(e.target.value))}
                style={{ ...inputStyle, width: 90 }}
              />
            </div>

            {uploadMode === "file" ? (
              <form onSubmit={handleIngest} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", gap: 12, alignItems: "end" }}>
                  <div style={{ flex: 1 }}>
                    <label style={labelStyle}>Arquivo (.txt, .docx, .pdf, imagens, código)</label>
                    <input
                      type="file"
                      accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp,.py,.js,.ts,.tsx,.jsx,.sql,.md,.yaml,.yml,.json,.csv,.html,.css,.java,.go,.rs,.rb,.sh,.toml,.env,.xml"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                      style={{ ...inputStyle, padding: "8px 12px" }}
                    />
                  </div>
                  <button type="submit" disabled={ingesting || !file} style={btnPrimary}>
                    {ingesting ? "Processando..." : "Enviar"}
                  </button>
                </div>
                {ingestMsg && (
                  <p style={{ fontSize: 13, color: ingestMsg.ok ? "#16a34a" : "#dc2626" }}>
                    {ingestMsg.text}
                  </p>
                )}
              </form>
            ) : (
              <form onSubmit={handleFolderIngest} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", gap: 12, alignItems: "end" }}>
                  <div style={{ flex: 1 }}>
                    <label style={labelStyle}>Selecionar pasta</label>
                    <input
                      type="file"
                      /* @ts-expect-error webkitdirectory não é atributo padrão do TS */
                      webkitdirectory=""
                      multiple
                      onChange={handleFolderChange}
                      style={{ ...inputStyle, padding: "8px 12px" }}
                    />
                    {folderFiles.length > 0 && (
                      <p style={{ fontSize: 13, color: "#9696a0", marginTop: 6 }}>
                        {folderFiles.length} arquivo{folderFiles.length !== 1 ? "s" : ""} aceitos · node_modules, .git e binários ignorados
                      </p>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" disabled={folderIngesting || folderFiles.length === 0} style={btnPrimary}>
                      {folderIngesting ? `${folderProgress?.done ?? 0} / ${folderProgress?.total ?? 0}` : "Enviar pasta"}
                    </button>
                    {folderIngesting && (
                      <button type="button" onClick={() => { cancelRef.current = true; }} style={btnDanger}>Cancelar</button>
                    )}
                  </div>
                </div>
                {folderProgress && (
                  <div style={{ fontSize: 13 }}>
                    <div style={{ background: "#f0f0f4", borderRadius: 4, height: 4, marginBottom: 8 }}>
                      <div style={{
                        background: folderProgress.cancelled ? "#b8b8c0" : folderProgress.errors.length > 0 ? "#d97706" : "#22c55e",
                        borderRadius: 4,
                        height: 4,
                        width: `${(folderProgress.done / folderProgress.total) * 100}%`,
                        transition: "width 0.2s",
                      }} />
                    </div>
                    {folderIngesting ? (
                      <p style={{ color: "#9696a0" }}>Processando {folderProgress.done} de {folderProgress.total} · 5 em paralelo</p>
                    ) : folderProgress.cancelled ? (
                      <p style={{ color: "#9696a0" }}>Cancelado · {folderProgress.done - folderProgress.errors.length} processados</p>
                    ) : (
                      <p style={{ color: folderProgress.errors.length === 0 ? "#16a34a" : "#d97706" }}>
                        ✓ {folderProgress.done - folderProgress.errors.length} processados
                        {folderProgress.errors.length > 0 && ` · ${folderProgress.errors.length} com erro: ${folderProgress.errors.slice(0, 3).join(", ")}`}
                      </p>
                    )}
                  </div>
                )}
              </form>
            )}
          </section>

          {/* SPRINTS LIST */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, marginTop: 24 }}>
            <h2 style={{ ...sectionTitle, margin: 0 }}>
              Sprints ({sprints.length})
            </h2>
            <button onClick={handleCreateSprint} style={btnPrimary}>+ Nova sprint</button>
          </div>

          {sprints.length === 0 ? (
            <section style={sectionStyle}>
              <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>
                Nenhuma sprint criada. Clique em <strong>+ Nova sprint</strong> ou faça um upload acima.
              </p>
            </section>
          ) : (
            sprints.map((s) => (
              <SprintCard
                key={s.id}
                sprint={s}
                ingestions={ingestionsBySprint[s.numero] ?? []}
                docs={docsBySprint[s.numero] ?? []}
                generating={generating}
                onOpenSprintDoc={(tipo, n) => setModal({ tipo, sprintNumero: n })}
                onUploadLivre={handleUploadLivre}
                onGenerateSprintDoc={handleGenerateFromCard}
                onAddManualDoc={(n) => setManualModal({ sprintNumero: n })}
                onDeleteDoc={handleDeleteDoc}
                onHealthChanged={refreshSprints}
              />
            ))
          )}
        </>
      )}

      {/* ABA: TECNOLOGIAS */}
      {activeTab === "tecnologias" && <TechnologiesTab projectId={id} />}

      {/* ABA: DOCS GERAIS */}
      {activeTab === "docs" && (
        <>
          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Documentos cross-sprint</h2>
            <p style={{ fontSize: 13, color: "#6a6a7a", marginTop: 0, marginBottom: 16, lineHeight: 1.5 }}>
              Documentos que olham o projeto como um todo. <strong>Repasse Semanal e Retrospectiva</strong> agora ficam dentro do card da sprint correspondente (aba Sprints), já que são sprint-específicos. Clique em cada tipo abaixo pra ver o que é antes de gerar.
            </p>
            <div style={{ marginBottom: 18 }}>
              <label style={labelStyle}>Observações adicionais <span style={{ fontWeight: 400, color: "#b8b8c0" }}>(opcional)</span></label>
              <textarea
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                placeholder="Contexto extra que deve ser considerado na geração — aplicado a qualquer tipo escolhido abaixo."
                rows={3}
                style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", lineHeight: 1.6 }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 18 }}>
              {(
                [
                  "ata_reuniao",
                  "decisoes",
                  "adr",
                  "onboarding",
                  "completo",
                ] as DocTypeKey[]
              ).map((key) => (
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

            <div style={{ marginBottom: 18 }}>
              <button
                onClick={() => setManualModal({ sprintNumero: null })}
                style={btnSecondary}
              >
                + Adicionar documento manual
              </button>
              <span style={{ marginLeft: 10, fontSize: 12, color: "#9696a0" }}>
                Pra registrar um doc que você escreveu fora do sistema (sem custo de IA).
              </span>
            </div>

            {generating && <p style={{ color: "#9696a0", fontSize: 14 }}>Gerando documento com IA...</p>}
            {generateError && <p style={{ color: "#dc2626", fontSize: 14 }}>{generateError}</p>}

            {generatedDoc && (
              <div style={{ marginTop: 18 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <span style={{ fontSize: 13, color: "#9696a0" }}>
                    {docTypeLabel(generatedDoc.doc_type)}
                    {generatedDoc.sprint_number ? <span style={{ ...tagStyle, marginLeft: 8 }}>Sprint {generatedDoc.sprint_number}</span> : null}
                  </span>
                  <button onClick={() => navigator.clipboard.writeText(generatedDoc.content)} style={{ ...btnSecondary, fontSize: 12, padding: "6px 12px" }}>
                    Copiar markdown
                  </button>
                </div>
                <div style={markdownContainer}>
                  <ReactMarkdown>{generatedDoc.content}</ReactMarkdown>
                </div>
              </div>
            )}
          </section>

          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Documentos gerados ({docs.length})</h2>
            {docs.length === 0 ? (
              <p style={{ color: "#9696a0", fontSize: 14 }}>Nenhum documento gerado ainda.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {docs.map((doc) => (
                  <div key={doc.id} style={ingestionCard}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                        <span style={{ fontWeight: 600, fontSize: 13, color: "#111116" }}>{docTypeLabel(doc.doc_type)}</span>
                        {doc.sprint_number && <span style={tagStyle}>Sprint {doc.sprint_number}</span>}
                        <span style={{ color: "#b8b8c0", fontSize: 12 }}>{new Date(doc.created_at).toLocaleDateString("pt-BR")}</span>
                      </div>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button onClick={() => setExpandedDocId(expandedDocId === doc.id ? null : doc.id)} style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}>
                          {expandedDocId === doc.id ? "Fechar" : "Ver"}
                        </button>
                        <button onClick={() => navigator.clipboard.writeText(doc.content)} style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}>
                          Copiar
                        </button>
                        <button onClick={() => handleDeleteDoc(doc.id)} style={{ ...btnDanger, fontSize: 12, padding: "5px 10px" }}>
                          Excluir
                        </button>
                      </div>
                    </div>
                    {expandedDocId === doc.id && (
                      <div style={{ ...markdownContainer, marginTop: 14 }}>
                        <ReactMarkdown>{doc.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {/* ABA: CONFIG */}
      {activeTab === "config" && (
        <>
          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Chave da API do Gemini</h2>
            {project.has_api_key ? (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <span style={{ fontSize: 13, color: "#16a34a", fontWeight: 600 }}>Chave configurada</span>
                <form onSubmit={handleSaveApiKey} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input type="password" placeholder="Nova chave..." value={apiKeyInput} onChange={(e) => setApiKeyInput(e.target.value)} style={{ ...inputStyle, width: 240 }} />
                  <button type="submit" disabled={savingKey || !apiKeyInput.trim()} style={btnSecondary}>
                    {savingKey ? "..." : "Trocar"}
                  </button>
                </form>
              </div>
            ) : (
              <form onSubmit={handleSaveApiKey} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input type="password" placeholder="AIza..." value={apiKeyInput} onChange={(e) => setApiKeyInput(e.target.value)} style={{ ...inputStyle, flex: 1 }} required />
                <button type="submit" disabled={savingKey} style={btnPrimary}>{savingKey ? "Salvando..." : "Salvar"}</button>
              </form>
            )}
            {apiKeyMsg && <p style={{ marginTop: 10, fontSize: 13, color: apiKeyMsg.ok ? "#16a34a" : "#dc2626" }}>{apiKeyMsg.text}</p>}
          </section>

          {cost !== null && (
            <section style={sectionStyle}>
              <h2 style={sectionTitle}>Custo de IA</h2>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: cost.budget_usd ? 12 : 0 }}>
                <span style={{ fontSize: 16, fontWeight: 700, color: "#111116" }}>
                  ${cost.total_usd < 0.001 && cost.total_usd > 0 ? cost.total_usd.toFixed(6) : cost.total_usd.toFixed(4)}
                  {cost.budget_usd != null && <span style={{ color: "#b8b8c0", fontWeight: 400, marginLeft: 8 }}>de ${cost.budget_usd.toFixed(2)}</span>}
                </span>
                <span style={{ color: "#9696a0", fontSize: 12 }}>
                  {cost.input_tokens.toLocaleString("pt-BR")} in · {cost.output_tokens.toLocaleString("pt-BR")} out tokens
                </span>
              </div>
              {cost.budget_usd != null && cost.budget_usd > 0 && (() => {
                const pct = Math.min((cost.total_usd / cost.budget_usd) * 100, 100);
                const color = pct >= 90 ? "#dc2626" : pct >= 70 ? "#d97706" : "#22c55e";
                return (
                  <div>
                    <div style={{ background: "#f0f0f4", borderRadius: 4, height: 6 }}>
                      <div style={{ background: color, borderRadius: 4, height: 6, width: `${pct}%`, transition: "width 0.3s" }} />
                    </div>
                    {pct >= 90 && <p style={{ marginTop: 8, fontSize: 12, color: "#dc2626", fontWeight: 500 }}>{pct.toFixed(0)}% do budget consumido.</p>}
                  </div>
                );
              })()}
            </section>
          )}

          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Status do projeto</h2>
            <button onClick={handleToggleDelivered} style={project.is_delivered ? btnDeliveredActive : btnDelivered}>
              {project.is_delivered ? "✓ Marcado como entregue (desfazer)" : "Marcar como entregue"}
            </button>
          </section>

          <section style={{ ...sectionStyle, borderColor: "#fecaca" }}>
            <h2 style={{ ...sectionTitle, color: "#dc2626" }}>Zona perigosa</h2>
            <p style={{ fontSize: 13, color: "#6a6a7a", marginBottom: 14 }}>
              Excluir o projeto remove todas as ingestões, sprints e documentos. Esta ação é irreversível.
            </p>
            <button onClick={handleDeleteProject} style={btnDanger}>Excluir projeto</button>
          </section>
        </>
      )}

      {/* MODAL Planning/Daily/Review */}
      <SprintDocModal
        open={modal !== null}
        onClose={() => setModal(null)}
        tipo={modal?.tipo ?? "planning"}
        projetoId={id}
        sprintNumero={modal?.sprintNumero ?? 1}
        onSubmitted={async () => {
          await refreshAll();
        }}
      />

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
const modeTab: React.CSSProperties = {
  background: "transparent",
  color: "#9696a0",
  border: "none",
  padding: "6px 14px",
  fontSize: 13,
  fontWeight: 500,
  cursor: "pointer",
};
const modeTabActive: React.CSSProperties = {
  ...modeTab,
  background: "#4ade80",
  color: "#0a0a0a",
  fontWeight: 700,
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
