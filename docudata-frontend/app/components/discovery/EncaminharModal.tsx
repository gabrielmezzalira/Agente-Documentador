"use client";

import { useState } from "react";
import { ds } from "../../lib/ds";
import { encaminharProjeto } from "../../lib/discovery";
import { Button, ErrorNotice, Field, Modal, Textarea } from "../ds";

interface Props {
  projectId: string;
  projectName: string;
  onClose: () => void;
  /** Chamado depois de encaminhar, com a subárea de destino. */
  onDone: (destino: "dados" | "dev") => void;
}

/** Bifurcação do projeto de Produto: ele sai da subárea e continua em Dados ou Dev, levando todo o contexto. */
export default function EncaminharModal({ projectId, projectName, onClose, onDone }: Props) {
  const [destino, setDestino] = useState<"dados" | "dev">("dados");
  const [motivo, setMotivo] = useState("");
  const [promover, setPromover] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function confirmar() {
    setBusy(true);
    setError("");
    try {
      await encaminharProjeto(projectId, { destino, motivo: motivo.trim() || undefined, promover_validados: promover });
      onDone(destino);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao encaminhar");
      setBusy(false);
    }
  }

  return (
    <Modal
      title={`Encaminhar · ${projectName}`}
      onClose={onClose}
      width={560}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button variant="primary" disabled={busy} onClick={confirmar}>{busy ? "Encaminhando…" : `Encaminhar para ${destino === "dados" ? "Dados" : "Dev"}`}</Button>
        </>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <p style={{ fontSize: 14, lineHeight: 1.6, color: ds.muted }}>
          O projeto deixa a subárea de Produto e continua em Dados ou Dev, com requisitos, reuniões e histórico. A decisão fica registrada.
        </p>
        {error && <ErrorNotice>{error}</ErrorNotice>}

        <div role="radiogroup" aria-label="Destino" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {([["dados", "Dados", "Analytics, pipelines e IA"], ["dev", "Dev", "Software e repositórios"]] as const).map(([valor, rotulo, desc]) => {
            const sel = destino === valor;
            return (
              <label key={valor} style={{ display: "flex", flexDirection: "column", gap: 2, padding: "12px 16px", borderRadius: 12, cursor: "pointer", background: sel ? ds.greenSoft : ds.inner, border: `1px solid ${sel ? ds.greenLine : ds.innerBorder}` }}>
                <input type="radio" name="destino" value={valor} checked={sel} onChange={() => setDestino(valor)} style={{ position: "absolute", opacity: 0, pointerEvents: "none" }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: sel ? ds.green : ds.text }}>{rotulo}</span>
                <span style={{ fontSize: 12.5, color: ds.muted }}>{desc}</span>
              </label>
            );
          })}
        </div>

        <Field label="Motivo (opcional)" htmlFor="enc-motivo"><Textarea id="enc-motivo" rows={2} value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={500} /></Field>

        <label style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 14, color: ds.text2, cursor: "pointer" }}>
          <input type="checkbox" checked={promover} onChange={(e) => setPromover(e.target.checked)} style={{ marginTop: 4, accentColor: ds.green }} />
          <span>
            Promover os requisitos validados a funcionalidades antes de encaminhar
            <span style={{ display: "block", fontSize: 12.5, color: ds.muted }}>Só os já validados entram; repetir é seguro.</span>
          </span>
        </label>
      </div>
    </Modal>
  );
}
