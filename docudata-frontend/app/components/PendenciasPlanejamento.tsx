"use client";

import { useState } from "react";
import { Button, Input } from "./ds";
import { ds } from "../lib/ds";
import { updateContrato, type FuncionalidadeResponse, type Project } from "../lib/api";

/**
 * Aviso fixo no topo do projeto enquanto o planejamento estiver incompleto:
 * funcionalidades sem sprint alvo e prazo do projeto sem datas. Não tem botão
 * de fechar: some sozinho quando tudo estiver preenchido.
 */
export default function PendenciasPlanejamento({
  project, funcionalidades, onVerSemSprint, onProjectUpdated,
}: {
  project: Project;
  funcionalidades: FuncionalidadeResponse[];
  onVerSemSprint: () => void;
  onProjectUpdated: (p: Project) => void;
}) {
  const semSprint = funcionalidades.filter((f) => !f.sprint_alvo);
  const semPrazo = !project.data_inicio || !project.data_fim_contratada;
  const [inicio, setInicio] = useState(project.data_inicio ?? "");
  const [fim, setFim] = useState(project.data_fim_contratada ?? "");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  if (semSprint.length === 0 && !semPrazo) return null;

  async function salvarPrazo(e: React.FormEvent) {
    e.preventDefault();
    if (!inicio || !fim) { setErro("Preencha o início e o fim do projeto."); return; }
    if (fim < inicio) { setErro("O fim não pode ser antes do início."); return; }
    setSalvando(true);
    setErro("");
    try {
      onProjectUpdated(await updateContrato(project.id, { data_inicio: inicio, data_fim_contratada: fim }));
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Não foi possível salvar o prazo.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <section
      role="status"
      aria-label="Planejamento incompleto"
      style={{ display: "flex", flexDirection: "column", gap: 14, padding: "18px 20px", margin: "-8px 0 18px", borderRadius: 12, border: `1px solid ${ds.amberLine}`, background: ds.amberSoft }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <strong style={{ fontSize: 14.5, color: ds.white }}>Complete o planejamento do projeto</strong>
        <span style={{ fontSize: 13, lineHeight: 1.5, color: ds.text2 }}>
          Sem sprint alvo e sem prazo não dá para acompanhar se o projeto está no ritmo. Este aviso some quando tudo estiver preenchido.
        </span>
      </div>

      {semSprint.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap", paddingTop: 12, borderTop: `1px solid ${ds.amberLine}` }}>
          <span style={{ fontSize: 13.5, color: ds.text }}>
            <strong style={{ fontFamily: ds.fontMono, color: ds.amber }}>{semSprint.length}</strong>{" "}
            {semSprint.length === 1 ? "funcionalidade sem sprint alvo" : "funcionalidades sem sprint alvo"}
            <span style={{ color: ds.muted }}>
              {" · "}{semSprint.slice(0, 4).map((f) => f.id_funcional || f.titulo).join(", ")}{semSprint.length > 4 ? "…" : ""}
            </span>
          </span>
          <Button size="sm" variant="secondary" onClick={onVerSemSprint}>Definir sprints</Button>
        </div>
      )}

      {semPrazo && (
        <form onSubmit={salvarPrazo} style={{ display: "flex", alignItems: "flex-end", gap: 10, flexWrap: "wrap", paddingTop: 12, borderTop: `1px solid ${ds.amberLine}` }}>
          <span style={{ fontSize: 13.5, color: ds.text, flex: "1 1 220px", alignSelf: "center" }}>Prazo total do projeto não definido</span>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: ds.muted }}>
            Início
            <Input type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} style={{ height: 34, width: 160 }} />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: ds.muted }}>
            Fim contratado
            <Input type="date" value={fim} onChange={(e) => setFim(e.target.value)} style={{ height: 34, width: 160 }} />
          </label>
          <Button size="sm" variant="primary" type="submit" disabled={salvando}>{salvando ? "Salvando…" : "Salvar prazo"}</Button>
          {erro && <span role="alert" style={{ flexBasis: "100%", fontSize: 12.5, color: ds.red }}>{erro}</span>}
        </form>
      )}
    </section>
  );
}
