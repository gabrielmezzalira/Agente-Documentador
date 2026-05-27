"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  getProject,
  getProjectCost,
  updateApiKey,
  listIngestions,
  listDocs,
  ingestFile,
  generateDoc,
  deleteProject,
  deleteDoc,
  toggleDelivered,
  type Project,
  type Ingestion,
  type GeneratedDoc,
  type ProjectCost,
} from "../../lib/api";

type SprintMap = Record<number, Ingestion[]>;

export default function ProjectDashboard() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [ingestions, setIngestions] = useState<Ingestion[]>([]);
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [loading, setLoading] = useState(true);

  const [uploadMode, setUploadMode] = useState<"file" | "folder">("file");
  const [file, setFile] = useState<File | null>(null);
  const [sprint, setSprint] = useState<number>(1);
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const [folderFiles, setFolderFiles] = useState<File[]>([]);
  const [folderIngesting, setFolderIngesting] = useState(false);
  const [folderProgress, setFolderProgress] = useState<{ done: number; total: number; errors: string[]; cancelled?: boolean } | null>(null);
  const cancelRef = useRef(false);

  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDoc | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");
  const [sprintForDoc, setSprintForDoc] = useState<number>(1);
  const [pendingDocType, setPendingDocType] = useState<string | null>(null);

  const [pendingAta, setPendingAta] = useState(false);
  const [observacoes, setObservacoes] = useState("");
  const [selectedIngestionId, setSelectedIngestionId] = useState<string>("");

  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);

  const [showIngestions, setShowIngestions] = useState(false);
  const [showDocs, setShowDocs] = useState(false);

  const [cost, setCost] = useState<ProjectCost | null>(null);

  const [apiKeyInput, setApiKeyInput] = useState("");
  const [apiKeyMsg, setApiKeyMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [savingKey, setSavingKey] = useState(false);

  useEffect(() => {
    Promise.all([getProject(id), listIngestions(id), listDocs(id), getProjectCost(id)])
      .then(([p, ings, d, c]) => { setProject(p); setIngestions(ings); setDocs(d); setCost(c); })
      .finally(() => setLoading(false));
  }, [id]);

  function refreshCost() { getProjectCost(id).then(setCost).catch(() => {}); }

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
    } catch { setApiKeyMsg({ ok: false, text: "Erro ao salvar chave." }); }
    finally { setSavingKey(false); }
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

  async function resizeImageIfNeeded(file: File, maxDim = 1024): Promise<File> {
    if (!file.type.startsWith("image/")) return file;
    return new Promise((resolve) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        URL.revokeObjectURL(url);
        const { naturalWidth: w, naturalHeight: h } = img;
        if (w <= maxDim && h <= maxDim) { resolve(file); return; }
        const scale = maxDim / Math.max(w, h);
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(w * scale);
        canvas.height = Math.round(h * scale);
        canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(
          (blob) => resolve(blob ? new File([blob], file.name, { type: "image/jpeg" }) : file),
          "image/jpeg", 0.85
        );
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
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
    let done = 0; let idx = 0;
    async function worker() {
      while (true) {
        if (cancelRef.current) break;
        const myIdx = idx++;
        if (myIdx >= folderFiles.length) break;
        const f = folderFiles[myIdx];
        const relativePath = (f as File & { webkitRelativePath: string }).webkitRelativePath || f.name;
        try {
          const fileToSend = await resizeImageIfNeeded(new File([f], relativePath, { type: f.type }));
          await ingestFile(id, sprint, fileToSend);
        } catch { errors.push(relativePath); }
        done++;
        setFolderProgress({ done, total: folderFiles.length, errors: [...errors] });
      }
    }
    await Promise.all(Array.from({ length: CONCURRENCY }, worker));
    setFolderIngesting(false);
    if (!cancelRef.current) { setIngestions(await listIngestions(id)); refreshCost(); }
    else { setFolderProgress((p) => p ? { ...p, cancelled: true } : null); }
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
      setIngestions(await listIngestions(id));
      refreshCost();
    } catch (err) {
      setIngestMsg({ ok: false, text: err instanceof Error ? err.message : "Erro desconhecido" });
    } finally { setIngesting(false); }
  }

  async function handleGenerate(tipoDoc: string, sprintNum?: number, ingestionId?: string) {
    setGenerating(true);
    setGeneratedDoc(null);
    setGenerateError("");
    try {
      const doc = await generateDoc(id, tipoDoc, sprintNum, ingestionId, observacoes);
      setGeneratedDoc(doc);
      setDocs(await listDocs(id));
      refreshCost();
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Erro ao gerar documento");
    } finally { setGenerating(false); setPendingDocType(null); setPendingAta(false); }
  }

  async function handleDeleteProject() {
    if (!confirm(`Excluir o projeto "${project?.name}"? Todas as ingestões e documentos serão removidos.`)) return;
    try { await deleteProject(id); router.push("/"); }
    catch { alert("Erro ao excluir projeto."); }
  }

  async function handleToggleDelivered() {
    try {
      const updated = await toggleDelivered(id);
      setProject(updated);
    } catch { alert("Erro ao atualizar status do projeto."); }
  }

  async function handleDeleteDoc(docId: string) {
    if (!confirm("Excluir este documento?")) return;
    try {
      await deleteDoc(docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
      if (generatedDoc?.id === docId) setGeneratedDoc(null);
      if (expandedDocId === docId) setExpandedDocId(null);
    } catch { alert("Erro ao excluir documento."); }
  }

  const sprintMap: SprintMap = ingestions.reduce((acc, ing) => {
    const s = ing.sprint_number;
    if (!acc[s]) acc[s] = [];
    acc[s].push(ing);
    return acc;
  }, {} as SprintMap);

  if (loading) return <p style={{ padding: 48, color: "#9696a0" }}>Carregando...</p>;
  if (!project) return <p style={{ padding: 48, color: "#dc2626" }}>Projeto não encontrado.</p>;

  return (
    <main style={{ maxWidth: 880, margin: "0 auto", padding: "48px 24px" }}>
      <Link href="/" style={{ fontSize: 13, color: "#9696a0" }}>← Projetos</Link>

      {/* Header */}
      <div style={{ marginTop: 24, marginBottom: 36, display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <div>
          <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.02em", color: "#111116" }}>{project.name}</h1>
          <p style={{ marginTop: 6, fontSize: 14, color: "#9696a0" }}>
            Cliente: <span style={{ color: "#22c55e", fontWeight: 600 }}>{project.client}</span>
          </p>
          {project.description && (
            <p style={{ color: "#9696a0", marginTop: 6, fontSize: 13, lineHeight: 1.5 }}>{project.description}</p>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={handleToggleDelivered}
            style={project?.is_delivered ? btnDeliveredActive : btnDelivered}
          >
            {project?.is_delivered ? "✓ Entregue" : "Marcar como entregue"}
          </button>
          <button onClick={handleDeleteProject} style={btnDanger}>Excluir projeto</button>
        </div>
      </div>

      {/* API KEY — not configured */}
      {project && !project.has_api_key && (
        <section style={{ ...sectionStyle, borderColor: "#fecaca", background: "#fef2f2" }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#dc2626", marginBottom: 14 }}>
            Chave de API do Gemini não configurada — uploads e geração de documentos não funcionarão.
          </p>
          <form onSubmit={handleSaveApiKey} style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input type="password" placeholder="AIza..." value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)} style={{ ...inputStyle, flex: 1 }} required />
            <button type="submit" disabled={savingKey} style={btnPrimary}>
              {savingKey ? "Salvando..." : "Salvar chave"}
            </button>
          </form>
          {apiKeyMsg && <p style={{ marginTop: 10, fontSize: 13, color: apiKeyMsg.ok ? "#16a34a" : "#dc2626" }}>{apiKeyMsg.text}</p>}
        </section>
      )}

      {/* API KEY — configured */}
      {project?.has_api_key && (
        <section style={sectionStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 13, color: "#16a34a", fontWeight: 600 }}>Chave de API configurada</span>
            <form onSubmit={handleSaveApiKey} style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="password" placeholder="Nova chave..." value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                style={{ ...inputStyle, width: 200, padding: "7px 10px", fontSize: 13 }} />
              <button type="submit" disabled={savingKey || !apiKeyInput.trim()} style={{ ...btnSecondary, fontSize: 13 }}>
                {savingKey ? "..." : "Trocar"}
              </button>
            </form>
          </div>
          {apiKeyMsg && <p style={{ marginTop: 10, fontSize: 13, color: apiKeyMsg.ok ? "#16a34a" : "#dc2626" }}>{apiKeyMsg.text}</p>}
        </section>
      )}

      {/* CUSTO */}
      {cost !== null && (
        <section style={{ ...sectionStyle, marginBottom: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: cost.budget_usd ? 12 : 0 }}>
            <span style={sectionTitle}>Custo de IA</span>
            <span style={{ fontSize: 14, color: "#6a6a7a" }}>
              <span style={{ fontWeight: 700, color: "#111116" }}>
                ${cost.total_usd < 0.001 && cost.total_usd > 0 ? cost.total_usd.toFixed(6) : cost.total_usd.toFixed(4)}
              </span>
              {cost.budget_usd != null && <span style={{ color: "#b8b8c0" }}> / ${cost.budget_usd.toFixed(2)}</span>}
              <span style={{ color: "#b8b8c0", marginLeft: 14, fontSize: 12 }}>
                {cost.input_tokens.toLocaleString("pt-BR")} in · {cost.output_tokens.toLocaleString("pt-BR")} out tokens
              </span>
            </span>
          </div>
          {cost.budget_usd != null && cost.budget_usd > 0 && (() => {
            const pct = Math.min((cost.total_usd / cost.budget_usd) * 100, 100);
            const color = pct >= 90 ? "#dc2626" : pct >= 70 ? "#d97706" : "#22c55e";
            return (
              <div>
                <div style={{ background: "#f0f0f4", borderRadius: 4, height: 4 }}>
                  <div style={{ background: color, borderRadius: 4, height: 4, width: `${pct}%`, transition: "width 0.3s" }} />
                </div>
                {pct >= 90 && <p style={{ marginTop: 8, fontSize: 12, color: "#dc2626", fontWeight: 500 }}>Atenção: {pct.toFixed(0)}% do budget consumido.</p>}
              </div>
            );
          })()}
        </section>
      )}

      {/* UPLOAD */}
      <section style={sectionStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h2 style={sectionTitle}>Upload</h2>
          <div style={{ display: "flex", border: "1px solid #e4e4ea", borderRadius: 8, overflow: "hidden" }}>
            <button onClick={() => setUploadMode("file")} style={uploadMode === "file" ? modeTabActive : modeTab}>Arquivo</button>
            <button onClick={() => setUploadMode("folder")} style={uploadMode === "folder" ? modeTabActive : modeTab}>Pasta / Projeto</button>
          </div>
        </div>

        <div style={{ marginBottom: 18 }}>
          <label style={labelStyle}>Sprint</label>
          <input type="number" min={1} value={sprint} onChange={(e) => setSprint(Number(e.target.value))}
            style={{ ...inputStyle, width: 80 }} />
        </div>

        {uploadMode === "file" ? (
          <form onSubmit={handleIngest} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 12, alignItems: "end" }}>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Arquivo (.txt, .docx, .pdf, imagens, código)</label>
                <input type="file"
                  accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.webp,.py,.js,.ts,.tsx,.jsx,.sql,.md,.yaml,.yml,.json,.csv,.html,.css,.java,.go,.rs,.rb,.sh,.toml,.env,.xml"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)} style={{ ...inputStyle, padding: "8px 12px" }} />
              </div>
              <button type="submit" disabled={ingesting || !file} style={btnPrimary}>
                {ingesting ? "Processando..." : "Enviar"}
              </button>
            </div>
            {ingestMsg && <p style={{ fontSize: 13, color: ingestMsg.ok ? "#16a34a" : "#dc2626" }}>{ingestMsg.text}</p>}
          </form>
        ) : (
          <form onSubmit={handleFolderIngest} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 12, alignItems: "end" }}>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Selecionar pasta</label>
                <input type="file"
                  /* @ts-expect-error webkitdirectory não é atributo padrão do TS */
                  webkitdirectory="" multiple onChange={handleFolderChange} style={{ ...inputStyle, padding: "8px 12px" }} />
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
                    borderRadius: 4, height: 4, width: `${(folderProgress.done / folderProgress.total) * 100}%`, transition: "width 0.2s",
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

      {/* HISTÓRICO DE INGESTÕES */}
      <section style={sectionStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: showIngestions ? 20 : 0 }}>
          <h2 style={{ ...sectionTitle, marginBottom: 0 }}>
            Histórico de ingestões
            {ingestions.length > 0 && (
              <span style={{ fontSize: 11, fontWeight: 700, color: "#16a34a", marginLeft: 8,
                background: "#dcfce7", borderRadius: 4, padding: "2px 7px" }}>
                {ingestions.length}
              </span>
            )}
          </h2>
          <button onClick={() => setShowIngestions((v) => !v)} style={{ ...btnSecondary, fontSize: 12, padding: "5px 12px" }}>
            {showIngestions ? "Ocultar" : "Mostrar"}
          </button>
        </div>
        {showIngestions && ingestions.length === 0 ? (
          <p style={{ color: "#9696a0", fontSize: 14 }}>Nenhum arquivo enviado ainda.</p>
        ) : showIngestions ? (
          Object.keys(sprintMap).map(Number).sort((a, b) => b - a).map((s) => (
            <div key={s} style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
                color: "#9696a0", marginBottom: 10 }}>
                Sprint {s}
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {sprintMap[s].map((ing) => (
                  <div key={ing.id} style={ingestionCard}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: "#111116" }}>{ing.file_name}</span>
                      <span style={{ color: "#b8b8c0", fontSize: 12 }}>{new Date(ing.created_at).toLocaleDateString("pt-BR")}</span>
                    </div>
                    {ing.extracted_content?.resumo && (
                      <p style={{ color: "#6a6a7a", fontSize: 13, marginTop: 6, lineHeight: 1.5 }}>{ing.extracted_content.resumo}</p>
                    )}
                    {ing.extracted_content?.tecnologias && ing.extracted_content.tecnologias.length > 0 && (
                      <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {ing.extracted_content.tecnologias.map((t) => <span key={t} style={tagStyle}>{t}</span>)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))
        ) : null}
      </section>

      {/* GERAÇÃO */}
      <section style={sectionStyle}>
        <h2 style={sectionTitle}>Gerar documento</h2>
        <div style={{ marginBottom: 18 }}>
          <label style={labelStyle}>Observações adicionais <span style={{ fontWeight: 400, color: "#b8b8c0" }}>(opcional)</span></label>
          <textarea
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            placeholder="Adicione contexto extra que deve ser considerado na geração — ex: foco do documento, ressalvas, detalhes que não estão nos uploads..."
            rows={3}
            style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit", lineHeight: 1.6 }}
          />
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
          <button onClick={() => { setPendingDocType("sprint_status"); setPendingAta(false); }} style={btnSecondary}>Repasse Semanal</button>
          <button onClick={() => { setPendingAta(true); setPendingDocType(null); setSelectedIngestionId(ingestions[0]?.id ?? ""); }} style={btnSecondary}>Ata de Reunião</button>
          <button onClick={() => { setPendingDocType("decisoes"); setPendingAta(false); }} style={btnSecondary}>Log de Decisões</button>
          <button onClick={() => handleGenerate("adr")} style={btnSecondary}>ADRs</button>
          <button onClick={() => handleGenerate("onboarding")} style={btnSecondary}>Onboarding</button>
          <button onClick={() => handleGenerate("completo")} style={btnSecondary}>Documentação Final</button>
        </div>

        {pendingDocType && (
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 18,
            padding: "14px 16px", background: "#f7f7fa", border: "1px solid #e4e4ea", borderRadius: 8 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: "#6a6a7a", whiteSpace: "nowrap" }}>Sprint:</label>
            <input type="number" min={1} value={sprintForDoc} onChange={(e) => setSprintForDoc(Number(e.target.value))}
              style={{ ...inputStyle, width: 80 }} />
            <button onClick={() => handleGenerate(pendingDocType, sprintForDoc)} style={btnPrimary} disabled={generating}>
              {generating ? "Gerando..." : "Gerar"}
            </button>
            <button onClick={() => setPendingDocType(null)} style={{ ...btnSecondary, color: "#9696a0" }}>Cancelar</button>
          </div>
        )}

        {pendingAta && (
          <div style={{ marginBottom: 18, padding: "16px", background: "#f7f7fa",
            border: "1px solid #e4e4ea", borderRadius: 8 }}>
            <label style={{ ...labelStyle, marginBottom: 10 }}>Selecione a transcrição da reunião</label>
            {ingestions.length === 0 ? (
              <p style={{ fontSize: 13, color: "#9696a0" }}>Nenhuma ingestão disponível. Faça o upload de um arquivo primeiro.</p>
            ) : (
              <select value={selectedIngestionId} onChange={(e) => setSelectedIngestionId(e.target.value)}
                style={{ ...inputStyle, marginBottom: 12 }}>
                {ingestions.map((ing) => (
                  <option key={ing.id} value={ing.id}>
                    Sprint {ing.sprint_number} · {ing.file_name} · {new Date(ing.created_at).toLocaleDateString("pt-BR")}
                  </option>
                ))}
              </select>
            )}
            <div style={{ display: "flex", gap: 10 }}>
              <button onClick={() => handleGenerate("ata_reuniao", undefined, selectedIngestionId)}
                style={btnPrimary} disabled={generating || !selectedIngestionId}>
                {generating ? "Gerando..." : "Gerar Ata"}
              </button>
              <button onClick={() => setPendingAta(false)} style={{ ...btnSecondary, color: "#9696a0" }}>Cancelar</button>
            </div>
          </div>
        )}

        {generating && <p style={{ color: "#9696a0", fontSize: 14 }}>Gerando documento com IA...</p>}
        {generateError && <p style={{ color: "#dc2626", fontSize: 14 }}>{generateError}</p>}

        {generatedDoc && (
          <div style={{ marginTop: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <span style={{ fontSize: 13, color: "#9696a0" }}>
                {docTypeLabel(generatedDoc.doc_type)}
                {generatedDoc.sprint_number ? <span style={{ ...tagStyle, marginLeft: 8 }}>Sprint {generatedDoc.sprint_number}</span> : null}
              </span>
              <button onClick={() => navigator.clipboard.writeText(generatedDoc.content)}
                style={{ ...btnSecondary, fontSize: 12, padding: "6px 12px" }}>
                Copiar markdown
              </button>
            </div>
            <div style={markdownContainer}>
              <ReactMarkdown>{generatedDoc.content}</ReactMarkdown>
            </div>
          </div>
        )}
      </section>

      {/* DOCUMENTOS GERADOS */}
      <section style={sectionStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: showDocs ? 20 : 0 }}>
          <h2 style={{ ...sectionTitle, marginBottom: 0 }}>
            Documentos gerados
            {docs.length > 0 && (
              <span style={{ fontSize: 11, fontWeight: 700, color: "#16a34a", marginLeft: 8,
                background: "#dcfce7", borderRadius: 4, padding: "2px 7px" }}>
                {docs.length}
              </span>
            )}
          </h2>
          <button onClick={() => setShowDocs((v) => !v)} style={{ ...btnSecondary, fontSize: 12, padding: "5px 12px" }}>
            {showDocs ? "Ocultar" : "Mostrar"}
          </button>
        </div>
        {showDocs && docs.length === 0 ? (
          <p style={{ color: "#9696a0", fontSize: 14 }}>Nenhum documento gerado ainda.</p>
        ) : showDocs ? (
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
                    <button onClick={() => setExpandedDocId(expandedDocId === doc.id ? null : doc.id)}
                      style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}>
                      {expandedDocId === doc.id ? "Fechar" : "Ver"}
                    </button>
                    <button onClick={() => navigator.clipboard.writeText(doc.content)}
                      style={{ ...btnSecondary, fontSize: 12, padding: "5px 10px" }}>
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
        ) : null}
      </section>
    </main>
  );
}

function docTypeLabel(tipo: string) {
  const labels: Record<string, string> = {
    sprint_status: "Repasse Semanal",
    sprint_retro: "Retrospectiva",
    decisoes: "Log de Decisões",
    completo: "Documentação Final",
    ata_reuniao: "Ata de Reunião",
    onboarding: "Onboarding",
    adr: "ADRs",
  };
  return labels[tipo] ?? tipo;
}

const sectionStyle: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e8e8ed",
  borderRadius: 14,
  padding: "22px 24px",
  marginBottom: 14,
};
const sectionTitle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  marginBottom: 18,
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
  letterSpacing: "0.01em",
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
  letterSpacing: "0.02em",
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
  padding: "8px 14px",
  fontSize: 13,
  fontWeight: 500,
  cursor: "pointer",
};
const btnDeliveredActive: React.CSSProperties = {
  background: "#dcfce7",
  color: "#16a34a",
  border: "1px solid #86efac",
  borderRadius: 8,
  padding: "8px 14px",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
};
