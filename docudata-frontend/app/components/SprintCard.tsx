"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type {
  GeneratedDoc,
  Ingestion,
  SprintDocType,
  SprintWithStatus,
} from "../lib/api";
import { reabrirAvaliacaoSemanal } from "../lib/api";
import { DOC_TYPES, docTypeLabel } from "../lib/doc_types";
import { ds, cardStyle } from "../lib/ds";
import { Button } from "./ds";
import { useAuth } from "./AuthGuard";
import SprintChecklist, { ChecklistBars, type ChecklistItem } from "./sprints/SprintChecklist";
import SprintMenu, { type SprintMenuAction } from "./sprints/SprintMenu";

type SprintGenType = "repasse_semanal";

interface Props {
  sprint: SprintWithStatus;
  /** Sprint em andamento (a mais recente iniciada): aparece aberta e marcada como "Atual". */
  isCurrent: boolean;
  ingestions: Ingestion[];
  docs: GeneratedDoc[];
  generating: boolean;
  onOpenSprintDoc: (tipo: SprintDocType, sprintNumero: number) => void;
  onOpenPlanning: (sprint: SprintWithStatus) => void;
  onUploadLivre: (sprintNumero: number) => void;
  onGenerateSprintDoc: (tipoDoc: SprintGenType, sprintNumero: number) => void;
  onOpenRetroModal: (sprintNumero: number) => void;
  onAddManualDoc: (sprintNumero: number) => void;
  onExportGdocs: (docId: string) => void;
  exportingDocId: string | null;
  onDeleteDoc: (docId: string) => void;
  onMoveDoc: (docId: string, sprintNumber: number | null) => void;
  onSaveDocContent: (docId: string, content: string) => Promise<void>;
  onDeleteIngestion: (ingestionId: string) => void;
  onMoveIngestion: (ingestionId: string, sprintNumber: number) => void;
  onDeleteSprint: (sprintId: string) => void;
  onSprintUpdated?: (updated: SprintWithStatus) => void;
  onOpenAvaliacaoSemanal?: (sprint: SprintWithStatus) => void;
}

// ---------- styles ----------

const muted: React.CSSProperties = {
  color: "#8a948e",
  fontSize: 13,
  marginLeft: 4,
};

const textBtn: React.CSSProperties = {
  background: "none",
  border: "none",
  padding: 0,
  cursor: "pointer",
  fontFamily: "inherit",
  fontSize: 13,
  fontWeight: 600,
  color: ds.text2,
};

const monoMeta: React.CSSProperties = { fontFamily: ds.fontMono, fontSize: 12, color: ds.muted };

const confirmPanel: React.CSSProperties = {
  padding: "16px 18px",
  background: "rgba(62,224,111,0.055)",
  borderRadius: 12,
  border: "1px solid rgba(62,224,111,0.17)",
};

const confirmField: React.CSSProperties = {
  display: "flex",
  gap: 8,
  fontSize: 13,
  color: "#c3cbc6",
  marginBottom: 8,
  lineHeight: 1.5,
};

const confirmFieldLabel: React.CSSProperties = {
  flexShrink: 0,
  fontWeight: 700,
  color: "#f2f5f3",
  minWidth: 72,
};

const confirmActions: React.CSSProperties = {
  display: "flex",
  gap: 8,
  justifyContent: "flex-end",
  marginTop: 14,
};

const detailBox: React.CSSProperties = {
  padding: 18,
  background: "rgba(62,224,111,0.055)",
  borderRadius: 12,
  border: "1px solid rgba(62,224,111,0.17)",
};

const subTitleStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#8a948e",
  margin: 0,
  marginBottom: 10,
};

const tagStyle: React.CSSProperties = {
  background: "rgba(177,151,252,0.10)",
  color: "#b197fc",
  borderRadius: 5,
  padding: "2px 9px",
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
};

const docRow: React.CSSProperties = {
  background: "#0d1711",
  border: "1px solid rgba(62,224,111,0.2)",
  borderRadius: 10,
  padding: "12px 14px",
  fontSize: 13,
};

const docHeader: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 8,
};

const markdownContainer: React.CSSProperties = {
  marginTop: 12,
  background: "rgba(62,224,111,0.055)",
  border: "1px solid rgba(62,224,111,0.2)",
  borderRadius: 8,
  padding: "16px 20px",
  lineHeight: 1.7,
  color: "#c3cbc6",
  fontSize: 13,
};

const tinyBtn: React.CSSProperties = {
  background: "#0d1711",
  color: "#c3cbc6",
  border: "1px solid rgba(62,224,111,0.2)",
  borderRadius: 7,
  padding: "5px 11px",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
};

const tinyBtnDanger: React.CSSProperties = {
  ...tinyBtn,
  background: "rgba(255,107,107,0.10)",
  color: "#ff6b6b",
  border: "1px solid rgba(255,107,107,0.30)",
};

// ---------- component ----------
export default function SprintCard({
  sprint,
  isCurrent,
  ingestions,
  docs,
  generating,
  onOpenSprintDoc,
  onOpenPlanning,
  onUploadLivre,
  onGenerateSprintDoc,
  onOpenRetroModal,
  onAddManualDoc,
  onExportGdocs,
  exportingDocId,
  onDeleteDoc,
  onMoveDoc,
  onSaveDocContent,
  onDeleteIngestion,
  onMoveIngestion,
  onDeleteSprint,
  onSprintUpdated,
  onOpenAvaliacaoSemanal,
}: Props) {
  const cargo = useAuth()?.cargo ?? "lider";
  const [expanded, setExpanded] = useState(false);
  const [reabrindo, setReabrindo] = useState(false);

  async function handleReabrir() {
    if (!confirm(
      `Reabrir o fechamento da Sprint ${sprint.numero}?\n\n` +
      `A pontuação travada desta sprint é apagada e ela volta a ficar em aberto, ` +
      `para o gerente corrigir o Kanban e confirmar de novo. ` +
      `As respostas do questionário NÃO são apagadas.`
    )) return;
    setReabrindo(true);
    try {
      await reabrirAvaliacaoSemanal(sprint.id);
      window.location.reload();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao reabrir o fechamento.");
    } finally {
      setReabrindo(false);
    }
  }
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const [expandedSourcesId, setExpandedSourcesId] = useState<string | null>(null);
  const [expandedIngId, setExpandedIngId] = useState<string | null>(null);
  const [pendingGen, setPendingGen] = useState<SprintGenType | null>(null);
  const [movingIngId, setMovingIngId] = useState<string | null>(null);
  const [moveIngSprint, setMoveIngSprint] = useState<string>("");
  const [movingDocId, setMovingDocId] = useState<string | null>(null);
  const [moveDocSprint, setMoveDocSprint] = useState<string>("");
  const [editingDocId, setEditingDocId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState("");
  const [commitsExpanded, setCommitsExpanded] = useState(false);
  const [commitRepositoryFilter, setCommitRepositoryFilter] = useState("todos");

  const commits = ingestions.filter((item) => item.tipo_documentacao === "commit");
  const commitRepositories = Array.from(new Set(
    commits
      .map((item) => item.source_repository_full_name ?? item.extracted_content?._meta_repository)
      .filter((nome): nome is string => Boolean(nome))
  )).sort();
  const filteredCommits = commitRepositoryFilter === "todos"
    ? commits
    : commits.filter((item) =>
        (item.source_repository_full_name ?? item.extracted_content?._meta_repository) === commitRepositoryFilter
      );

  function confirmGenerate() {
    if (pendingGen) {
      onGenerateSprintDoc(pendingGen, sprint.numero);
      setPendingGen(null);
    }
  }

  const pendingMeta = pendingGen ? DOC_TYPES[pendingGen] : null;
  const temRetro = docs.some((d) => d.doc_type === "retrospectiva");
  const avaliacaoPendente =
    sprint.elegiveis_avaliacao_count > 0 && sprint.avaliados_count < sprint.elegiveis_avaliacao_count;

  type ExtractedContent = NonNullable<Ingestion["extracted_content"]>;

  function renderIngestionChips(content: ExtractedContent | undefined | null) {
    if (!content) return null;
    const tarefas = content.tarefas?.length ?? 0;
    const decisoes = content.decisoes?.length ?? 0;
    const problemas = content.problemas?.length ?? 0;
    const tecnologias = content.tecnologias ?? [];
    const parts: string[] = [];
    if (tarefas > 0) parts.push(`📋 ${tarefas}`);
    if (decisoes > 0) parts.push(`🧭 ${decisoes}`);
    if (problemas > 0) parts.push(`⚠️ ${problemas}`);
    if (tecnologias.length > 0) {
      const techStr = tecnologias.slice(0, 3).join(", ") + (tecnologias.length > 3 ? "…" : "");
      parts.push(`🔧 ${techStr}`);
    }
    if (parts.length === 0) return null;
    return (
      <p style={{ color: "#8a948e", fontSize: 11, margin: "4px 0 0", lineHeight: 1.4 }}>
        {parts.join("  ·  ")}
      </p>
    );
  }

  function renderIngestionDetail(content: ExtractedContent | undefined | null) {
    if (!content) return null;
    const sections = [
      { label: "Tarefas", items: content.tarefas ?? [] },
      { label: "Decisões", items: content.decisoes ?? [] },
      { label: "Problemas", items: content.problemas ?? [] },
      { label: "Próximos passos", items: content.proximos_passos ?? [] },
      { label: "Tecnologias", items: content.tecnologias ?? [] },
    ].filter((s) => s.items.length > 0);
    if (sections.length === 0) return null;
    return (
      <div style={{ marginTop: 8, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 8 }}>
        {sections.map(({ label, items }) => (
          <div key={label} style={{ marginBottom: 6 }}>
            <span style={{ fontWeight: 700, fontSize: 11, color: "#8a948e" }}>{label}:</span>
            <ul style={{ margin: "2px 0 0 16px", padding: 0 }}>
              {items.map((item, i) => (
                <li key={i} style={{ fontSize: 11, color: "#c3cbc6", lineHeight: 1.5 }}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  }

  // Sprint fechada começa recolhida em uma linha; a atual começa aberta (DESIGN.md · Densidade).
  const [open, setOpen] = useState(isCurrent);

  const checklist: ChecklistItem[] = [
    {
      key: "planning", label: "Planning", state: sprint.tem_planning ? "done" : "pending",
      count: sprint.tem_planning ? "1/1" : "0/1", onClick: () => onOpenPlanning(sprint), title: "Abrir Planning",
    },
    {
      key: "review", label: "Review", state: sprint.tem_review ? "done" : "pending",
      count: sprint.tem_review ? "1/1" : "0/1", onClick: () => onOpenSprintDoc("review", sprint.numero), title: "Registrar Review",
    },
    {
      key: "retro", label: "Retrospectiva", state: temRetro ? "done" : "pending",
      count: temRetro ? "1/1" : "0/1", onClick: () => onOpenRetroModal(sprint.numero), title: "Gerar Retrospectiva",
    },
    ...(cargo !== "operacional"
      ? [{
          key: "avaliacao", label: "Avaliação",
          state: (sprint.avaliacao_completa_em || (sprint.elegiveis_avaliacao_count > 0 && !avaliacaoPendente) ? "done" : "pending") as ChecklistItem["state"],
          count: `${sprint.avaliados_count}/${sprint.elegiveis_avaliacao_count}`,
          onClick: () => onOpenAvaliacaoSemanal?.(sprint), title: "Avaliação Semanal",
        }]
      : []),
    {
      key: "dailys", label: "Dailys", state: sprint.dailys_count > 0 ? "done" : "optional",
      count: sprint.dailys_count > 0 ? String(sprint.dailys_count) : "opcional",
      onClick: () => onOpenSprintDoc("daily", sprint.numero), title: "Registrar Daily",
    },
  ];

  const menuActions: SprintMenuAction[] = [
    { label: "Upload livre", onSelect: () => onUploadLivre(sprint.numero) },
    ...((cargo === "lider" || cargo === "owner") && sprint.avaliacao_completa_em
      ? [{
          label: reabrindo ? "Reabrindo…" : "Reabrir fechamento",
          onSelect: handleReabrir,
          disabled: reabrindo,
          title: "Apaga a pontuação travada desta sprint para o gerente corrigir o Kanban e confirmar de novo. As respostas do questionário são mantidas.",
        }]
      : []),
    {
      label: "Excluir sprint",
      danger: true,
      onSelect: () => {
        if (confirm(`Excluir Sprint ${sprint.numero} e TUDO associado a ela (tasks, ingestões e documentos gerados)? Esta ação é irreversível.`))
          onDeleteSprint(sprint.id);
      },
    },
  ];

  const ingestaoMeta = `${sprint.ingestions_count} ingestões · ${sprint.docs_gerados_count} docs`;
  const statusLabel = isCurrent ? null : sprint.avaliacao_completa_em ? "Fechada" : "Em aberto";

  // Linha única da sprint fechada (protótipo 03, "Sprint 1 · Fechada").
  if (!open) {
    return (
      <div style={cardStyle}>
        <div style={{ padding: "20px 28px", display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
          <span style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.02em", color: ds.white }}>Sprint {sprint.numero}</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: sprint.avaliacao_completa_em ? ds.muted : ds.amber }}>{statusLabel}</span>
          <ChecklistBars items={checklist} />
          <span style={monoMeta}>{ingestaoMeta}</span>
          <button type="button" className="ds-text-btn" onClick={() => setOpen(true)} aria-expanded={false} style={{ ...textBtn, marginLeft: "auto" }}>
            Ver detalhes ▾
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", gap: 22 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em", color: ds.white }}>Sprint {sprint.numero}</h3>
            {isCurrent ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 600, color: ds.green }}>
                <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: "50%", background: ds.green, boxShadow: `0 0 8px ${ds.green}` }} />
                Atual
              </span>
            ) : (
              <span style={{ fontSize: 12, fontWeight: 600, color: sprint.avaliacao_completa_em ? ds.muted : ds.amber }}>{statusLabel}</span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <span style={monoMeta}>{ingestaoMeta}</span>
            <button type="button" className="ds-text-btn" style={textBtn} aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
              {expanded ? "Recolher detalhes" : "Detalhes"}
            </button>
            {!isCurrent && (
              <button type="button" className="ds-text-btn" style={{ ...textBtn, color: ds.muted }} onClick={() => { setOpen(false); setExpanded(false); }}>
                Recolher ▴
              </button>
            )}
            <SprintMenu actions={menuActions} sprintNumero={sprint.numero} />
          </div>
        </div>

        <SprintChecklist items={checklist} />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap", paddingTop: 18, borderTop: "1px solid rgba(255,255,255,0.07)" }}>
          <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.text2 }}>
            Previsto {sprint.previsto} pts
            {sprint.surgiu_na_sprint > 0 && ` · ${sprint.planejado_no_inicio} planejados + ${sprint.surgiu_na_sprint} surgiram na sprint`}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Button variant="secondary" onClick={() => onAddManualDoc(sprint.numero)}>+ Documento</Button>
            <Button
              variant={pendingGen === "repasse_semanal" ? "active" : "primary"}
              aria-expanded={pendingGen === "repasse_semanal"}
              onClick={() => setPendingGen(pendingGen === "repasse_semanal" ? null : "repasse_semanal")}
            >
              Gerar Repasse Semanal
            </Button>
          </div>
        </div>

      {/* Painel de confirmação com explicação */}
      {pendingMeta && (
        <div style={confirmPanel}>
          <h4 style={{ fontSize: 15, fontWeight: 700, color: "#f2f5f3", margin: "0 0 12px" }}>
            {pendingMeta.label} — Sprint {sprint.numero}
          </h4>
          <div style={confirmField}>
            <span style={confirmFieldLabel}>O quê</span>
            <span>{pendingMeta.o_que}</span>
          </div>
          <div style={confirmField}>
            <span style={confirmFieldLabel}>Pra quê</span>
            <span>{pendingMeta.pra_que}</span>
          </div>
          <div style={confirmField}>
            <span style={confirmFieldLabel}>Quando</span>
            <span>{pendingMeta.quando}</span>
          </div>
          <div style={confirmField}>
            <span style={confirmFieldLabel}>Fontes</span>
            <span>{pendingMeta.fontes}</span>
          </div>
          <div style={confirmActions}>
            <Button variant="ghost" size="sm" onClick={() => setPendingGen(null)}>Cancelar</Button>
            <Button variant="primary" size="sm" onClick={confirmGenerate} disabled={generating}>
              {generating ? "Gerando…" : "Confirmar e gerar"}
            </Button>
          </div>
        </div>
      )}

      {expanded && (
        <div style={detailBox}>
          {/* DOCS GERADOS DA SPRINT — destaque */}
          <p style={subTitleStyle}>Documentos desta sprint ({docs.length})</p>
          {docs.length === 0 ? (
            <p style={{ color: "#8a948e", fontSize: 13, margin: "0 0 14px" }}>
              Nenhum documento gerado para esta sprint ainda.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 18 }}>
              {docs.map((d) => (
                <div key={d.id} style={docRow}>
                  <div style={docHeader}>
                    <span style={{ fontWeight: 600, color: "#f2f5f3" }}>
                      {docTypeLabel(d.doc_type)}
                      <span style={{ color: "#8a948e", fontWeight: 400, marginLeft: 8 }}>
                        {new Date(d.created_at).toLocaleDateString("pt-BR")}
                      </span>
                    </span>
                    <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                      <button
                        style={tinyBtn}
                        onClick={() => {
                          const closing = expandedDocId === d.id;
                          setExpandedDocId(closing ? null : d.id);
                          if (closing && editingDocId === d.id) { setEditingDocId(null); setEditError(""); }
                        }}
                      >
                        {expandedDocId === d.id ? "Fechar" : "Ver"}
                      </button>
                      <button
                        style={tinyBtn}
                        onClick={() => navigator.clipboard.writeText(d.content)}
                      >
                        Copiar
                      </button>
                      <button
                        style={tinyBtn}
                        onClick={() => {
                          setExpandedDocId(d.id);
                          setEditingDocId(d.id);
                          setEditDraft(d.content);
                          setEditError("");
                        }}
                      >
                        Editar
                      </button>
                      <button
                        style={{ ...tinyBtn, opacity: exportingDocId === d.id ? 0.6 : 1 }}
                        onClick={() => onExportGdocs(d.id)}
                        disabled={exportingDocId === d.id}
                      >
                        {exportingDocId === d.id ? "Exportando…" : "Google Docs"}
                      </button>
                      <button
                        style={tinyBtn}
                        onClick={() => { setMovingDocId(d.id); setMoveDocSprint(""); }}
                      >
                        Mover sprint
                      </button>
                      <button
                        style={tinyBtnDanger}
                        onClick={() => {
                          if (confirm("Excluir este documento?")) onDeleteDoc(d.id);
                        }}
                      >
                        Excluir
                      </button>
                    </div>
                  </div>
                  {movingDocId === d.id && (
                    <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 8 }}>
                      <span style={{ fontSize: 12, color: "#8a948e" }}>Mover para sprint:</span>
                      <input
                        type="number"
                        min={1}
                        value={moveDocSprint}
                        onChange={(e) => setMoveDocSprint(e.target.value)}
                        style={{ width: 60, padding: "4px 8px", border: "1px solid rgba(62,224,111,0.2)", borderRadius: 6, fontSize: 13 }}
                        autoFocus
                      />
                      <button
                        style={{ ...tinyBtn, background: "rgba(62,224,111,0.12)", color: "#3ee06f", borderColor: "rgba(62,224,111,0.35)" }}
                        onClick={() => {
                          const n = parseInt(moveDocSprint);
                          if (!isNaN(n) && n > 0) { onMoveDoc(d.id, n); setMovingDocId(null); }
                        }}
                      >
                        Confirmar
                      </button>
                      <button style={tinyBtn} onClick={() => setMovingDocId(null)}>Cancelar</button>
                    </div>
                  )}
                  {expandedDocId === d.id && editingDocId === d.id && (
                    <div style={{ marginTop: 12 }}>
                      <textarea
                        style={{
                          width: "100%",
                          minHeight: 260,
                          border: "1px solid rgba(62,224,111,0.2)",
                          borderRadius: 8,
                          padding: "12px 14px",
                          fontSize: 13,
                          fontFamily: "monospace",
                          lineHeight: 1.6,
                          boxSizing: "border-box",
                          resize: "vertical",
                        }}
                        value={editDraft}
                        onChange={(e) => setEditDraft(e.target.value)}
                        disabled={savingEdit}
                        autoFocus
                      />
                      {editError && (
                        <p style={{ color: "#ff6b6b", fontSize: 12, marginTop: 6 }}>{editError}</p>
                      )}
                      <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                        <button
                          style={{ ...tinyBtn, background: "rgba(62,224,111,0.12)", color: "#3ee06f", borderColor: "rgba(62,224,111,0.35)", opacity: savingEdit ? 0.6 : 1 }}
                          disabled={savingEdit}
                          onClick={async () => {
                            if (!editDraft.trim()) { setEditError("O documento não pode ficar vazio."); return; }
                            setSavingEdit(true);
                            setEditError("");
                            try {
                              await onSaveDocContent(d.id, editDraft);
                              setEditingDocId(null);
                            } catch (e) {
                              setEditError(e instanceof Error ? e.message : "Erro ao salvar edição.");
                            } finally {
                              setSavingEdit(false);
                            }
                          }}
                        >
                          {savingEdit ? "Salvando…" : "Salvar"}
                        </button>
                        <button
                          style={tinyBtn}
                          disabled={savingEdit}
                          onClick={() => { setEditingDocId(null); setEditError(""); }}
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}
                  {expandedDocId === d.id && editingDocId !== d.id && (
                    <div style={markdownContainer}>
                      <ReactMarkdown>{d.content}</ReactMarkdown>
                    </div>
                  )}
                  {ingestions.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <button
                        style={{ background: "none", border: "none", padding: 0, fontSize: 11, color: "#b197fc", cursor: "pointer", fontWeight: 600 }}
                        onClick={() => setExpandedSourcesId(expandedSourcesId === d.id ? null : d.id)}
                      >
                        {expandedSourcesId === d.id ? "ocultar fontes ▲" : `ver fontes (${ingestions.length} ingestão${ingestions.length !== 1 ? "ões" : ""}) ▼`}
                      </button>
                      {expandedSourcesId === d.id && (
                        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
                          {ingestions.map((ing) => (
                            <div key={ing.id} style={{ background: "rgba(62,224,111,0.055)", border: "1px solid rgba(62,224,111,0.2)", borderRadius: 8, padding: "8px 12px" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                                <span style={{ fontWeight: 600, fontSize: 12, color: "#f2f5f3" }}>{ing.file_name}</span>
                                {ing.tipo_documentacao && (
                                  <span style={tagStyle}>{ing.tipo_documentacao}</span>
                                )}
                              </div>
                              {ing.extracted_content?.resumo && (
                                <p style={{ color: "#8a948e", margin: "4px 0 0", fontSize: 11, lineHeight: 1.5 }}>
                                  {ing.extracted_content.resumo}
                                </p>
                              )}
                              {renderIngestionChips(ing.extracted_content)}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* COMMITS — recolhido por padrão para sprints com histórico extenso */}
          {(() => {
            if (commits.length === 0) return (
              <p style={{ fontSize: 11, color: "#5d6661", margin: "14px 0 0", fontStyle: "italic" }}>
                Nenhum commit sincronizado neste projeto.
              </p>
            );
            return (
              <section
                aria-label={`Commits da Sprint ${sprint.numero}`}
                style={{ marginTop: 18, marginBottom: 18, border: "1px solid rgba(62,224,111,0.2)", borderRadius: 10, overflow: "hidden" }}
              >
                <button
                  type="button"
                  aria-expanded={commitsExpanded}
                  aria-controls={`commits-sprint-${sprint.id}`}
                  onClick={() => setCommitsExpanded((aberto) => !aberto)}
                  style={{
                    width: "100%",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 10,
                    padding: "11px 12px",
                    border: "none",
                    background: commitsExpanded ? "rgba(62,224,111,0.055)" : "#0d1711",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <span style={{ ...subTitleStyle, margin: 0 }}>
                    Commits ({commits.length})
                    <span style={{ ...muted, fontWeight: 400, marginLeft: 6, textTransform: "none", letterSpacing: 0 }}>
                      — GitHub App e legado
                    </span>
                  </span>
                  <span style={{ color: "#c3cbc6", fontSize: 12, fontWeight: 700, flexShrink: 0 }}>
                    {commitsExpanded ? "Recolher ▲" : "Expandir ▼"}
                  </span>
                </button>
                {commitsExpanded && (
                  <div id={`commits-sprint-${sprint.id}`} style={{ padding: "0 12px 12px", background: "rgba(62,224,111,0.055)" }}>
                    {commitRepositories.length > 1 && (
                    <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 8, padding: "10px 0 8px" }}>
                      {commitRepositoryFilter !== "todos" && (
                        <span style={{ color: "#8a948e", fontSize: 11 }}>{filteredCommits.length} exibido(s)</span>
                      )}
                      <select
                        aria-label="Filtrar commits por repositório"
                        value={commitRepositoryFilter}
                        onChange={(event) => setCommitRepositoryFilter(event.target.value)}
                        style={{ border: "1px solid rgba(62,224,111,0.2)", borderRadius: 7, padding: "5px 8px", color: "#c3cbc6", background: "#0d1711", fontSize: 11 }}
                      >
                        <option value="todos">Todos os repositórios</option>
                        {commitRepositories.map((nome) => <option key={nome} value={nome}>{nome}</option>)}
                      </select>
                    </div>
                    )}
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {filteredCommits.map((ing) => {
                    const meta = ing.extracted_content ?? {};
                    const sha = ing.source_commit_sha ?? meta._meta_commit_sha ?? (ing.file_name ?? "").replace("commit:", "");
                    const hash = sha.slice(0, 7);
                    const autor = meta._meta_autor ?? "Autor não identificado";
                    const autorLogin = meta._meta_autor_login;
                    const committer = meta._meta_committer;
                    const pusher = meta._meta_pusher ?? meta._meta_sender;
                    const branch = ing.source_branch ?? meta._meta_branch;
                    const repository = ing.source_repository_full_name ?? meta._meta_repository ?? "Origem não registrada (legado)";
                    const commitUrl = ing.source_url ?? meta._meta_commit_url;
                    const msg = meta._meta_commit_msg?.split("\n")[0] ?? meta.resumo ?? "";
                    const when = new Date(meta._meta_data_commit ?? ing.created_at).toLocaleString("pt-BR", {
                      day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
                    });
                    return (
                      <div key={ing.id} style={{
                        padding: "10px 12px", background: "rgba(62,224,111,0.055)",
                        border: "1px solid rgba(62,224,111,0.2)", borderRadius: 7, fontSize: 12,
                      }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 5 }}>
                          <span style={{ color: repository.includes("legado") ? "#8a948e" : "#c3cbc6", fontWeight: 700 }}>{repository}</span>
                          <span style={{ color: "#3ee06f", fontSize: 11, fontWeight: 700 }}>✓ Processado</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                          {commitUrl ? (
                            <a href={commitUrl} target="_blank" rel="noreferrer" style={{ color: "#b197fc", fontWeight: 700, flexShrink: 0, textDecoration: "none", fontFamily: "monospace" }}>{hash}</a>
                          ) : (
                            <code style={{ color: "#b197fc", fontWeight: 700, flexShrink: 0 }}>{hash}</code>
                          )}
                          {branch && (
                            <span style={{ background: "rgba(177,151,252,0.10)", color: "#b197fc", borderRadius: 4, padding: "1px 6px", fontWeight: 600, flexShrink: 0 }}>
                              {branch}
                            </span>
                          )}
                          <span style={{ color: "#c3cbc6", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {msg}
                          </span>
                          <span style={{ color: "#8a948e", flexShrink: 0 }}>
                            {autor}{autorLogin ? ` (@${autorLogin})` : ""}
                          </span>
                          <span style={{ color: "#8a948e", flexShrink: 0 }}>{when}</span>
                          <button
                            style={{ ...tinyBtn, fontSize: 11, padding: "2px 7px", flexShrink: 0 }}
                            onClick={() => { setMovingIngId(ing.id); setMoveIngSprint(""); }}
                          >
                            Mover
                          </button>
                          <button
                            style={{ ...tinyBtnDanger, fontSize: 11, padding: "2px 7px", flexShrink: 0 }}
                            onClick={() => { if (confirm("Excluir este commit?")) onDeleteIngestion(ing.id); }}
                          >
                            ✕
                          </button>
                        </div>
                        {meta.resumo && (
                          <p style={{ color: "#8a948e", fontSize: 11, lineHeight: 1.5, margin: "6px 0 0 0" }}>{meta.resumo}</p>
                        )}
                        {renderIngestionChips(meta)}
                        {(committer || pusher || ing.source_diff_stat) && (
                          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", color: "#8a948e", fontSize: 10, marginTop: 5 }}>
                            {committer && committer !== autor && <span>Committer: {committer}</span>}
                            {pusher && <span>Push por: {pusher}</span>}
                            {ing.source_diff_stat && <span>Alterações: {ing.source_diff_stat}</span>}
                          </div>
                        )}
                        {movingIngId === ing.id && (
                          <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 6 }}>
                            <span style={{ fontSize: 12, color: "#8a948e" }}>Mover para sprint:</span>
                            <input
                              type="number"
                              min={1}
                              value={moveIngSprint}
                              onChange={(e) => setMoveIngSprint(e.target.value)}
                              style={{ width: 60, padding: "4px 8px", border: "1px solid rgba(62,224,111,0.2)", borderRadius: 6, fontSize: 13 }}
                              autoFocus
                            />
                            <button
                              style={{ ...tinyBtn, background: "rgba(62,224,111,0.12)", color: "#3ee06f", borderColor: "rgba(62,224,111,0.35)" }}
                              onClick={() => {
                                const n = parseInt(moveIngSprint);
                                if (!isNaN(n) && n > 0) { onMoveIngestion(ing.id, n); setMovingIngId(null); }
                              }}
                            >
                              Confirmar
                            </button>
                            <button style={tinyBtn} onClick={() => setMovingIngId(null)}>Cancelar</button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                    </div>
                  </div>
                )}
              </section>
            );
          })()}

          {/* INGESTÕES — material bruto, secundário */}
          <p style={subTitleStyle}>
            Ingestões da sprint ({ingestions.filter((i) => i.tipo_documentacao !== "commit").length})
            <span style={{
              ...muted,
              fontWeight: 400,
              marginLeft: 6,
              textTransform: "none",
              letterSpacing: 0,
            }}>
              — material bruto que alimenta as docs
            </span>
          </p>
          {ingestions.filter((i) => i.tipo_documentacao !== "commit").length === 0 ? (
            <p style={{ color: "#8a948e", fontSize: 13, margin: 0 }}>
              Nenhuma ingestão nesta sprint.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {ingestions.filter((i) => i.tipo_documentacao !== "commit").map((ing) => {
                const isIngExpanded = expandedIngId === ing.id;
                const content = ing.extracted_content;
                const hasDetails = content && (
                  (content.tarefas?.length ?? 0) > 0 ||
                  (content.decisoes?.length ?? 0) > 0 ||
                  (content.problemas?.length ?? 0) > 0 ||
                  (content.proximos_passos?.length ?? 0) > 0 ||
                  (content.tecnologias?.length ?? 0) > 0
                );
                return (
                  <div
                    key={ing.id}
                    style={{
                      background: "#0d1711",
                      border: "1px solid rgba(62,224,111,0.2)",
                      borderRadius: 8,
                      padding: "10px 12px",
                      fontSize: 13,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <span style={{ fontWeight: 600 }}>{ing.file_name}</span>
                      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                        {ing.tipo_documentacao && (
                          <span style={tagStyle}>{ing.tipo_documentacao}</span>
                        )}
                        <button
                          style={{ ...tinyBtn, fontSize: 11, padding: "3px 8px" }}
                          onClick={() => { setMovingIngId(ing.id); setMoveIngSprint(""); }}
                        >
                          Mover
                        </button>
                        <button
                          style={{ ...tinyBtnDanger, fontSize: 11, padding: "3px 8px" }}
                          onClick={() => { if (confirm("Excluir esta ingestão?")) onDeleteIngestion(ing.id); }}
                        >
                          Excluir
                        </button>
                      </div>
                    </div>
                    {movingIngId === ing.id && (
                      <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 6 }}>
                        <span style={{ fontSize: 12, color: "#8a948e" }}>Mover para sprint:</span>
                        <input
                          type="number"
                          min={1}
                          value={moveIngSprint}
                          onChange={(e) => setMoveIngSprint(e.target.value)}
                          style={{ width: 60, padding: "4px 8px", border: "1px solid rgba(62,224,111,0.2)", borderRadius: 6, fontSize: 13 }}
                          autoFocus
                        />
                        <button
                          style={{ ...tinyBtn, background: "rgba(62,224,111,0.12)", color: "#3ee06f", borderColor: "rgba(62,224,111,0.35)" }}
                          onClick={() => {
                            const n = parseInt(moveIngSprint);
                            if (!isNaN(n) && n > 0) { onMoveIngestion(ing.id, n); setMovingIngId(null); }
                          }}
                        >
                          Confirmar
                        </button>
                        <button style={tinyBtn} onClick={() => setMovingIngId(null)}>Cancelar</button>
                      </div>
                    )}
                    {content?.resumo && (
                      <p style={{ color: "#8a948e", margin: "4px 0 0", fontSize: 12, lineHeight: 1.5 }}>
                        {content.resumo}
                      </p>
                    )}
                    {renderIngestionChips(content)}
                    {hasDetails && (
                      <button
                        onClick={() => setExpandedIngId(isIngExpanded ? null : ing.id)}
                        style={{
                          background: "none",
                          border: "none",
                          padding: "3px 0 0",
                          fontSize: 11,
                          color: "#b197fc",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                      >
                        {isIngExpanded ? "ocultar detalhes ▲" : "ver detalhes ▼"}
                      </button>
                    )}
                    {isIngExpanded && renderIngestionDetail(content)}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  );
}
