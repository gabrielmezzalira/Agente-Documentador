"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  getProject,
  getProjectCost,
  getProjectUsage,
  updateApiKey,
  listIngestions,
  listIngestionsBySprint,
  listDocs,
  listSprints,
  createSprint,
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
  type Project,
  type Ingestion,
  type GeneratedDoc,
  type ProjectCost,
  type ProjectUsage,
  type SprintWithStatus,
  type SprintDocType,
} from "../../lib/api";
import Tabs from "../../components/Tabs";
import SprintCard from "../../components/SprintCard";
import SprintDocModal from "../../components/SprintDocModal";
import TechnologiesTab from "../../components/TechnologiesTab";
import DocTypeCard from "../../components/DocTypeCard";
import ManualDocModal from "../../components/ManualDocModal";
import UploadLivreModal from "../../components/UploadLivreModal";
import RetroModal from "../../components/RetroModal";
import { DOC_TYPES, docTypeLabel, type DocTypeKey } from "../../lib/doc_types";

type TabId = "sprints" | "tecnologias" | "cross_sprint" | "documentos" | "custos" | "config";

function shiftMonth(yyyymm: string, delta: number): string {
  const year = parseInt(yyyymm.slice(0, 4), 10);
  const month = parseInt(yyyymm.slice(5, 7), 10) - 1; // 0-indexed
  const d = new Date(year, month + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function formatMonthLabel(yyyymm: string): string {
  const [y, m] = yyyymm.split("-").map(Number);
  return new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric" }).format(new Date(y, m - 1, 1));
}

function humanizeLabel(label: string): string {
  const map: Record<string, string> = {
    "ingestion:commit": "Ingestão: Commit",
    "ingestion:planning": "Ingestão: Planning",
    "ingestion:daily": "Ingestão: Daily",
    "ingestion:review": "Ingestão: Review",
    "ingestion:retrospectiva": "Ingestão: Retrospectiva",
    "ingestion:ata": "Ingestão: Ata",
    "ingestion:upload": "Ingestão: Upload livre",
    "generation:repasse_semanal": "Geração: Repasse Semanal",
    "generation:retrospectiva": "Geração: Retrospectiva",
    "generation:log_decisoes": "Geração: Log de Decisões",
    "generation:documentacao_final": "Geração: Documentação Final",
    "generation:onboarding": "Geração: Onboarding",
    "generation:ata_reuniao": "Geração: Ata de Reunião",
    "generation:planning": "Geração: Planning",
    "generation:daily": "Geração: Daily",
    "generation:review": "Geração: Review",
    "generation:manual": "Doc Manual",
  };
  return map[label] ?? label.split(":").map((s) => s.charAt(0).toUpperCase() + s.slice(1)).join(": ");
}

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

  // ---------- custos mensais ----------
  const [usage, setUsage] = useState<ProjectUsage | null>(null);
  const [usageLoading, setUsageLoading] = useState(false);
  const [usageError, setUsageError] = useState("");
  const todayMonth = (() => {
    const parts = new Intl.DateTimeFormat("pt-BR", {
      timeZone: "America/Sao_Paulo",
      year: "numeric",
      month: "2-digit",
    }).formatToParts(new Date());
    const year = parts.find((p) => p.type === "year")?.value ?? "";
    const month = parts.find((p) => p.type === "month")?.value ?? "";
    return `${year}-${month}`;
  })();
  const [currentMonth, setCurrentMonth] = useState<string>(todayMonth);

  // ---------- ui ----------
  const [activeTab, setActiveTab] = useState<TabId>("sprints");

  // ---------- modal sprint-docs ----------
  const [modal, setModal] = useState<{ tipo: SprintDocType; sprintNumero: number } | null>(null);

  // ---------- modal doc manual ----------
  const [manualModal, setManualModal] = useState<{ sprintNumero: number | null } | null>(null);

  // ---------- modal upload livre ----------
  const [uploadModal, setUploadModal] = useState<{ sprintNumero: number } | null>(null);

  // ---------- modal retrospectiva ----------
  const [retroModal, setRetroModal] = useState<{ sprintNumero: number } | null>(null);

  // ---------- carry-over prefill ----------
  const [carryOverPrefill, setCarryOverPrefill] = useState("");

  // ---------- geração ----------
  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDoc | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const [exportingDocId, setExportingDocId] = useState<string | null>(null);
  const [exportError, setExportError] = useState<Record<string, string>>({});

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

  // Carrega uso mensal ao entrar na aba Custos ou trocar de mês
  useEffect(() => {
    if (activeTab === "custos") {
      setUsageLoading(true);
      setUsageError("");
      getProjectUsage(id, currentMonth)
        .then(setUsage)
        .catch(() => setUsageError("Não foi possível carregar os dados."))
        .finally(() => setUsageLoading(false));
    }
  }, [activeTab, id, currentMonth]);

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

  function handleUploadLivre(sprintNumero: number) {
    setUploadModal({ sprintNumero });
  }

  function handleGenerateFromCard(tipoDoc: "repasse_semanal", sprintNumero: number) {
    handleGenerate(tipoDoc, sprintNumero);
  }

  async function fetchCarryOver(sprintNumero: number) {
    if (sprintNumero <= 1) { setCarryOverPrefill(""); return; }
    try {
      const ingestions = await listIngestionsBySprint(id, sprintNumero - 1);
      const review = ingestions.find((ing: Ingestion) => ing.tipo_documentacao === "review");
      const items: string[] = (review?.extracted_content as any)?.campos_review?.itens_proxima_sprint
        || review?.extracted_content?.proximos_passos
        || [];
      setCarryOverPrefill(Array.isArray(items) ? items.join("\n") : String(items));
    } catch {
      setCarryOverPrefill("");
    }
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
          { id: "cross_sprint", label: "Cross-sprint" },
          { id: "documentos", label: "Documentos", badge: docs.length || undefined },
          { id: "custos", label: "Custos" },
          { id: "config", label: "Configurações" },
        ]}
        active={activeTab}
        onChange={(t) => setActiveTab(t as TabId)}
      />

      {/* ABA: SPRINTS */}
      {activeTab === "sprints" && (
        <>
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
            <button onClick={handleCreateSprint} style={btnPrimary}>+ Nova sprint</button>
          </div>

          {sprints.length === 0 ? (
            <section style={sectionStyle}>
              <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>
                Nenhuma sprint criada. Clique em <strong>+ Nova sprint</strong> pra começar.
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
                onOpenSprintDoc={(tipo, n) => {
                  setModal({ tipo, sprintNumero: n });
                  if (tipo === "planning") fetchCarryOver(n);
                }}
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
                onHealthChanged={refreshSprints}
              />
            ))
          )}
        </>
      )}

      {/* ABA: TECNOLOGIAS */}
      {activeTab === "tecnologias" && <TechnologiesTab projectId={id} />}

      {/* ABA: CROSS-SPRINT (geradores que olham o projeto inteiro) */}
      {activeTab === "cross_sprint" && (
        <>
          <section style={sectionStyle}>
            <h2 style={sectionTitle}>Documentos cross-sprint</h2>
            <p style={{ fontSize: 13, color: "#6a6a7a", marginTop: 0, marginBottom: 16, lineHeight: 1.5 }}>
              Documentos que olham o projeto como um todo. Clique em cada tipo abaixo pra ver o que é antes de gerar.
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
                  "log_decisoes",
                  "onboarding",
                  "documentacao_final",
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

        </>
      )}

      {/* ABA: DOCUMENTOS — visualização de todos os docs do projeto, agrupados */}
      {activeTab === "documentos" && (
        <>
          <div style={{ marginBottom: 16, marginTop: 4 }}>
            <h2 style={{
              fontSize: 22,
              fontWeight: 800,
              color: "#0f172a",
              letterSpacing: "-0.02em",
              margin: 0,
            }}>
              Documentos do projeto
              <span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 600, marginLeft: 10 }}>
                {docs.length} {docs.length === 1 ? "documento" : "documentos"}
              </span>
            </h2>
            <p style={{ color: "#64748b", fontSize: 13, margin: "6px 0 0", lineHeight: 1.5, maxWidth: 620 }}>
              Tudo que foi gerado ou adicionado manualmente, organizado por sprint e separando os docs cross-sprint.
            </p>
          </div>

          {docs.length === 0 ? (
            <section style={sectionStyle}>
              <p style={{ color: "#9696a0", fontSize: 14, margin: 0 }}>
                Nenhum documento ainda. Gere docs na aba <strong>Sprints</strong> (Repasse/Retrospectiva por sprint) ou <strong>Cross-sprint</strong> (Ata, Decisões, Onboarding, Documentação Final).
              </p>
            </section>
          ) : (
            <>
              {/* Por sprint — ordem decrescente */}
              {sprints.map((s) => {
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
              })}

              {/* Cross-sprint — docs sem sprint_number */}
              {(() => {
                const crossSprintDocs = docs.filter((d) => d.sprint_number == null);
                if (crossSprintDocs.length === 0) return null;
                return (
                  <section style={sectionStyle}>
                    <h3 style={{
                      fontSize: 13,
                      fontWeight: 700,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      color: "#64748b",
                      margin: 0,
                      marginBottom: 12,
                    }}>
                      Cross-sprint
                      <span style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: "#4338ca",
                        marginLeft: 8,
                        background: "#e0e7ff",
                        borderRadius: 4,
                        padding: "2px 7px",
                      }}>
                        {crossSprintDocs.length}
                      </span>
                      <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 500, marginLeft: 8, letterSpacing: 0, textTransform: "none" }}>
                        — docs que cobrem o projeto inteiro (Decisões, Onboarding, Documentação Final, Ata)
                      </span>
                    </h3>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {crossSprintDocs.map((doc) => renderDocRow(doc))}
                    </div>
                  </section>
                );
              })()}
            </>
          )}
        </>
      )}

      {/* ABA: CUSTOS */}
      {activeTab === "custos" && (
        <>
          {/* Seletor de mês */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
            <button
              onClick={() => setCurrentMonth(shiftMonth(currentMonth, -1))}
              style={btnSecondary}
            >‹</button>
            <span style={{ fontWeight: 700, fontSize: 15, color: "#111116", minWidth: 100, textAlign: "center" }}>
              {formatMonthLabel(currentMonth)}
            </span>
            <button
              onClick={() => setCurrentMonth(shiftMonth(currentMonth, 1))}
              disabled={shiftMonth(currentMonth, 1) > todayMonth}
              style={{ ...btnSecondary, opacity: shiftMonth(currentMonth, 1) > todayMonth ? 0.4 : 1 }}
            >›</button>
          </div>

          {usageLoading && <p style={{ fontSize: 13, color: "#9696a0" }}>Carregando dados do mês...</p>}
          {usageError && <p style={{ fontSize: 13, color: "#dc2626" }}>{usageError}</p>}

          {!usageLoading && usage && (
            <>
              {/* SUMMARY */}
              <section style={sectionStyle}>
                <h2 style={sectionTitle}>Resumo — {formatMonthLabel(currentMonth)}</h2>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 24, fontWeight: 800, color: "#111116" }}>
                    ${usage.total_usd < 0.001 && usage.total_usd > 0 ? usage.total_usd.toFixed(6) : usage.total_usd.toFixed(4)}
                  </span>
                  <span style={{ color: "#9696a0", fontSize: 13 }}>
                    {usage.input_tokens.toLocaleString("pt-BR")} in · {usage.output_tokens.toLocaleString("pt-BR")} out tokens
                  </span>
                </div>
                {usage.total_usd === 0 && (
                  <p style={{ fontSize: 13, color: "#9696a0", marginTop: 8, marginBottom: 0 }}>Nenhum custo registrado neste mês.</p>
                )}
              </section>

              {/* BREAKDOWN */}
              {Object.keys(usage.breakdown).length > 0 && (
                <section style={sectionStyle}>
                  <h2 style={sectionTitle}>Por tipo de ação</h2>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {Object.entries(usage.breakdown)
                      .sort(([, a], [, b]) => b.cost_usd - a.cost_usd)
                      .map(([label, bucket]) => (
                        <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #f0f0f4" }}>
                          <div>
                            <span style={{ fontWeight: 600, fontSize: 13, color: "#0f172a" }}>{humanizeLabel(label)}</span>
                            <span style={{ marginLeft: 8, fontSize: 12, color: "#94a3b8" }}>{bucket.count} {bucket.count === 1 ? "ação" : "ações"}</span>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <span style={{ fontWeight: 700, fontSize: 13, color: "#111116" }}>
                              ${bucket.cost_usd < 0.001 && bucket.cost_usd > 0 ? bucket.cost_usd.toFixed(6) : bucket.cost_usd.toFixed(4)}
                            </span>
                            <span style={{ marginLeft: 8, fontSize: 11, color: "#94a3b8" }}>
                              {bucket.input_tokens.toLocaleString("pt-BR")} in / {bucket.output_tokens.toLocaleString("pt-BR")} out
                            </span>
                          </div>
                        </div>
                      ))}
                  </div>
                </section>
              )}

              {/* HISTÓRICO */}
              {usage.items.length > 0 && (
                <section style={sectionStyle}>
                  <h2 style={sectionTitle}>Histórico de ações</h2>
                  {usage.truncated && (
                    <p style={{ fontSize: 12, color: "#2563eb", marginBottom: 10 }}>
                      Mostrando as 100 ações mais recentes deste mês.
                    </p>
                  )}
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                    <thead>
                      <tr style={{ color: "#94a3b8", textAlign: "left" }}>
                        <th style={{ paddingBottom: 8, fontWeight: 600 }}>Data</th>
                        <th style={{ paddingBottom: 8, fontWeight: 600 }}>Tipo</th>
                        <th style={{ paddingBottom: 8, fontWeight: 600, textAlign: "right" }}>Tokens</th>
                        <th style={{ paddingBottom: 8, fontWeight: 600, textAlign: "right" }}>Custo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usage.items.map((item) => (
                        <tr key={item.id} style={{ borderTop: "1px solid #f0f0f4" }}>
                          <td style={{ padding: "6px 0", color: "#6a6a7a" }}>
                            {new Date(item.created_at).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                          </td>
                          <td style={{ padding: "6px 8px", color: "#0f172a" }}>{humanizeLabel(item.label)}</td>
                          <td style={{ padding: "6px 0", color: "#6a6a7a", textAlign: "right" }}>
                            {item.input_tokens.toLocaleString("pt-BR")} / {item.output_tokens.toLocaleString("pt-BR")}
                          </td>
                          <td style={{ padding: "6px 0", fontWeight: 600, color: "#111116", textAlign: "right" }}>
                            ${item.cost_usd < 0.001 && item.cost_usd > 0 ? item.cost_usd.toFixed(6) : item.cost_usd.toFixed(4)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}
            </>
          )}
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
        initialCarryOver={carryOverPrefill}
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
