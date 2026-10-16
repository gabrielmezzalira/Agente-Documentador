"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { GeneratedDoc } from "../../lib/api";
import { docTypeLabel } from "../../lib/doc_types";
import { ds, innerStyle } from "../../lib/ds";
import { Button, Chip, Input, Textarea } from "../ds";

interface Props {
  doc: GeneratedDoc;
  expanded: boolean;
  exporting: boolean;
  exportError?: string;
  onToggleExpand: () => void;
  onExport: () => void;
  onDelete: () => void;
  onMove: (sprint: number) => void;
  onSaveContent: (content: string) => Promise<void>;
}

const actionBtn = (danger = false): React.CSSProperties => ({
  padding: "7px 11px", borderRadius: 8, fontSize: 12.5, fontFamily: "inherit", cursor: "pointer", background: "none",
  border: `1px solid ${danger ? ds.redLine : ds.border}`, color: danger ? ds.red : ds.text2, whiteSpace: "nowrap",
});

/** Linha de documento gerado (protótipo 08): título, sprint, data e ações. */
export default function DocRow({ doc, expanded, exporting, exportError, onToggleExpand, onExport, onDelete, onMove, onSaveContent }: Props) {
  const [moving, setMoving] = useState(false);
  const [moveTo, setMoveTo] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [editErr, setEditErr] = useState("");
  const titulo = docTypeLabel(doc.doc_type);

  async function salvar() {
    if (!draft.trim()) { setEditErr("O documento não pode ficar vazio."); return; }
    setSaving(true);
    setEditErr("");
    try {
      await onSaveContent(draft);
      setEditing(false);
    } catch (e) {
      setEditErr(e instanceof Error ? e.message : "Erro ao salvar edição.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ ...innerStyle, padding: "14px 18px", display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="ds-doc-row" style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) auto", gap: 12, alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0, flexWrap: "wrap" }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: ds.white }}>{titulo}</span>
          {doc.sprint_number != null && <Chip tone="green">Sprint {doc.sprint_number}</Chip>}
          <span style={{ fontFamily: ds.fontMono, fontSize: 11.5, color: ds.muted }}>{new Date(doc.created_at).toLocaleDateString("pt-BR")}</span>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <button
            type="button"
            className="ds-row-link"
            aria-expanded={expanded}
            style={actionBtn()}
            onClick={() => { if (expanded) { setEditing(false); setEditErr(""); } onToggleExpand(); }}
          >
            {expanded ? "Fechar" : "Ver"}
          </button>
          <button type="button" className="ds-row-link" style={actionBtn()} onClick={() => navigator.clipboard.writeText(doc.content)}>Copiar</button>
          <button
            type="button"
            className="ds-row-link"
            style={actionBtn()}
            onClick={() => { if (!expanded) onToggleExpand(); setEditing(true); setDraft(doc.content); setEditErr(""); }}
          >
            Editar
          </button>
          <button type="button" className="ds-row-link" style={{ ...actionBtn(), opacity: exporting ? 0.6 : 1 }} disabled={exporting} onClick={onExport}>
            {exporting ? "Exportando…" : "Google Docs"}
          </button>
          <button type="button" className="ds-row-link" style={actionBtn()} onClick={() => { setMoving(true); setMoveTo(""); }}>Mover sprint</button>
          <button type="button" style={actionBtn(true)} onClick={() => { if (confirm(`Excluir o documento "${titulo}"?`)) onDelete(); }}>Excluir</button>
        </div>
      </div>
      {exportError && <span role="alert" style={{ fontSize: 12, color: ds.red }}>{exportError}</span>}

      {moving && (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <label htmlFor={`mover-${doc.id}`} style={{ fontSize: 13, color: ds.muted }}>Mover para sprint</label>
          <Input id={`mover-${doc.id}`} type="number" min={1} value={moveTo} onChange={(e) => setMoveTo(e.target.value)} style={{ width: 80, height: 34 }} autoFocus />
          <Button
            variant="active"
            size="sm"
            onClick={() => { const n = parseInt(moveTo); if (!isNaN(n) && n > 0) { onMove(n); setMoving(false); } }}
          >
            Confirmar
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setMoving(false)}>Cancelar</Button>
        </div>
      )}

      {expanded && editing && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <Textarea
            aria-label={`Conteúdo de ${titulo}`}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={saving}
            autoFocus
            style={{ minHeight: 260, fontFamily: ds.fontMono, fontSize: 13 }}
          />
          {editErr && <span role="alert" style={{ fontSize: 12, color: ds.red }}>{editErr}</span>}
          <div style={{ display: "flex", gap: 8 }}>
            <Button variant="primary" size="sm" disabled={saving} onClick={salvar}>{saving ? "Salvando…" : "Salvar"}</Button>
            <Button variant="ghost" size="sm" disabled={saving} onClick={() => { setEditing(false); setEditErr(""); }}>Cancelar</Button>
          </div>
        </div>
      )}

      {expanded && !editing && (
        <div className="ds-markdown" style={{ padding: "18px 20px", borderRadius: 10, background: "rgba(0,0,0,0.25)", border: `1px solid ${ds.border}`, lineHeight: 1.75, color: ds.text2, fontSize: 14 }}>
          <ReactMarkdown>{doc.content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
