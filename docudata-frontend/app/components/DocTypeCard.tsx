"use client";

import { useRef, useState } from "react";
import type { DocTypeMeta } from "../lib/doc_types";
import type { Ingestion, SprintWithStatus } from "../lib/api";
import { ds, innerStyle, labelStyle } from "../lib/ds";
import { Button, Select } from "./ds";

/** Tile compacto do tipo de documento (protótipo 08): nome, situação e "Gerar →". */
export default function DocTypeCard({
  meta, status, selected, onSelect,
}: {
  meta: DocTypeMeta;
  /** Ex.: "Não gerado" ou "Gerado em 05/10/2026". */
  status: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      style={{
        ...innerStyle,
        padding: 18, display: "flex", flexDirection: "column", gap: 14,
        ...(selected ? { borderColor: ds.greenLine, background: ds.greenSoft } : null),
      }}
    >
      <span style={{ fontSize: 15, fontWeight: 600, color: ds.white }}>{meta.label}</span>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 12, color: ds.muted }}>{status}</span>
        <button
          type="button"
          aria-expanded={selected}
          onClick={onSelect}
          style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontFamily: "inherit", color: ds.green, fontSize: 13, fontWeight: 600 }}
        >
          {selected ? "Fechar" : "Gerar →"}
        </button>
      </div>
    </div>
  );
}

interface PanelProps {
  meta: DocTypeMeta;
  sprints: SprintWithStatus[];
  ingestions: Ingestion[];
  generating: boolean;
  onGenerate: (key: string, sprintNumero?: number, ingestionId?: string) => void;
  /** Para ata_reuniao: além de selecionar ingestão existente, permite subir PDF inline. */
  onUploadAndGenerate?: (sprintNumero: number, file: File) => void;
}

/** Painel de geração do tipo selecionado: explicação + campos + botão. */
export function DocTypeGeneratePanel({ meta, sprints, ingestions, generating, onGenerate, onUploadAndGenerate }: PanelProps) {
  const [sprintNumero, setSprintNumero] = useState<number>(sprints[0]?.numero ?? 1);
  const [ingestionId, setIngestionId] = useState<string>(ingestions[0]?.id ?? "");
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [pdfName, setPdfName] = useState<string | null>(null);

  function handleGenerate() {
    const file = fileRef.current?.files?.[0] ?? null;
    if (meta.scope === "sprint") onGenerate(meta.key, sprintNumero);
    else if (meta.scope === "ingestion") {
      // Se o usuário subiu um PDF e o handler de upload está disponível, usa o upload
      if (file && onUploadAndGenerate) onUploadAndGenerate(sprintNumero, file);
      else onGenerate(meta.key, undefined, ingestionId);
    } else onGenerate(meta.key);
  }

  const bloqueado = generating || (meta.scope === "ingestion" && !ingestionId && !pdfName);
  const sprintSelect = (
    <Select aria-label="Sprint" value={sprintNumero} onChange={(e) => setSprintNumero(Number(e.target.value))} style={{ width: 160, height: 40, fontSize: 13.5 }}>
      {sprints.length === 0
        ? <option value={1}>Sprint 1</option>
        : sprints.map((s) => <option key={s.id} value={s.numero}>Sprint {s.numero}</option>)}
    </Select>
  );

  return (
    <div style={{ ...innerStyle, padding: "20px 22px", display: "flex", flexDirection: "column", gap: 16 }}>
      <span style={{ fontSize: 16, fontWeight: 700, color: ds.white }}>{meta.label}</span>
      <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "80px minmax(0,1fr)", rowGap: 8, columnGap: 12, fontSize: 13.5, lineHeight: 1.55 }}>
        {([["O quê", meta.o_que], ["Pra quê", meta.pra_que], ["Quando", meta.quando], ["Fontes", meta.fontes]] as const).map(([k, v]) => (
          <div key={k} style={{ display: "contents" }}>
            <dt style={{ ...labelStyle, paddingTop: 3 }}>{k}</dt>
            <dd style={{ margin: 0, color: ds.text2 }}>{v}</dd>
          </div>
        ))}
      </dl>

      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12, paddingTop: 16, borderTop: `1px solid ${ds.border}` }}>
        {meta.scope === "sprint" && sprintSelect}

        {meta.scope === "ingestion" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1, minWidth: 260 }}>
            {ingestions.length === 0 ? (
              <span style={{ color: ds.muted, fontSize: 13 }}>Nenhuma ingestão disponível.</span>
            ) : (
              <Select aria-label="Ingestão existente" value={ingestionId} onChange={(e) => setIngestionId(e.target.value)} style={{ maxWidth: 420, height: 40, fontSize: 13.5 }}>
                {ingestions.map((ing) => (
                  <option key={ing.id} value={ing.id}>Sprint {ing.sprint_number} · {ing.file_name}</option>
                ))}
              </Select>
            )}
            {onUploadAndGenerate && (
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <label style={{ fontSize: 13, color: ds.muted }}>
                  ou subir transcrição (PDF){" "}
                  <input ref={fileRef} type="file" accept="application/pdf" onChange={(e) => setPdfName(e.target.files?.[0]?.name ?? null)} style={{ fontSize: 12, color: ds.text2 }} />
                </label>
                {pdfName && sprintSelect}
              </div>
            )}
          </div>
        )}

        <Button variant="primary" onClick={handleGenerate} disabled={bloqueado} style={{ marginLeft: "auto" }}>
          {generating ? "Gerando…" : "Gerar documento"}
        </Button>
      </div>
    </div>
  );
}
