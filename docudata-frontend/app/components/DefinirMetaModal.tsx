"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, Chip, ErrorNotice, Modal, Select } from "./ds";
import { ds } from "../lib/ds";
import { definirMetaSprint, getMetaSprint, listFuncionalidades, type AcompProjeto, type FuncionalidadeResponse } from "../lib/api";

/** Define a meta de funcionalidades da sprint atual ou de uma próxima. Só lista funcionalidades ainda não entregues. */
export default function DefinirMetaModal({ projeto, onClose, onSalvo }: { projeto: AcompProjeto; onClose: () => void; onSalvo: () => void }) {
  const sprints = useMemo(
    () => [
      ...(projeto.sprint_atual && !projeto.sprint_atual.fechada ? [{ id: projeto.sprint_atual.id, numero: projeto.sprint_atual.numero, atual: true }] : []),
      ...projeto.proximas_sprints.filter((s) => !s.fechada).map((s) => ({ id: s.id, numero: s.numero, atual: false })),
    ],
    [projeto],
  );
  const [sprintId, setSprintId] = useState(sprints[0]?.id ?? "");
  const [funcs, setFuncs] = useState<FuncionalidadeResponse[] | null>(null);
  const [marcadas, setMarcadas] = useState<Set<string>>(new Set());
  const [carregando, setCarregando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [erroFuncs, setErroFuncs] = useState("");
  const [metaDe, setMetaDe] = useState("");
  const [iniciais, setIniciais] = useState<Set<string>>(new Set());

  // A meta só vale para a sprint para a qual foi carregada: ao trocar de sprint não há janela com a lista anterior.
  const metaCarregada = metaDe !== "" && metaDe === sprintId;
  const sprintEhAtual = sprints.find((s) => s.id === sprintId)?.atual ?? false;
  // % de tasks e "planejada" só existem no JSON do acompanhamento para a sprint atual.
  const dadosAtual = useMemo(() => {
    const m = new Map<string, { pct: number | null; planejada: boolean }>();
    for (const f of projeto.meta.funcionalidades) m.set(f.id, { pct: f.pct_tasks, planejada: f.planejada_na_sprint });
    for (const f of projeto.planejadas_fora_da_meta) m.set(f.id, { pct: null, planejada: true });
    return m;
  }, [projeto]);

  useEffect(() => {
    let vivo = true;
    listFuncionalidades(projeto.id)
      .then((l) => { if (vivo) setFuncs(l); })
      .catch((e) => { if (vivo) setErroFuncs(e instanceof Error ? e.message : "Erro ao buscar funcionalidades"); });
    return () => { vivo = false; };
  }, [projeto.id]);

  useEffect(() => {
    if (!sprintId) return;
    let vivo = true;
    setCarregando(true);
    setMarcadas(new Set());
    setIniciais(new Set());
    setErro("");
    getMetaSprint(sprintId)
      .then((m) => { if (vivo) { setMarcadas(new Set(m.funcionalidade_ids)); setIniciais(new Set(m.funcionalidade_ids)); setMetaDe(sprintId); } })
      .catch((e) => { if (vivo) setErro(e instanceof Error ? e.message : "Erro ao buscar a meta da sprint"); })
      .finally(() => { if (vivo) setCarregando(false); });
    return () => { vivo = false; };
  }, [sprintId]);

  // Entregue = concluída e aprovada. As que já estão na meta continuam visíveis para poderem sair.
  const abertas = (funcs ?? []).filter((f) => !(f.status === "concluida" && f.aprovada_em) || iniciais.has(f.id));

  function alternar(id: string) {
    setMarcadas((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
  }

  async function salvar() {
    setSalvando(true);
    setErro("");
    try {
      await definirMetaSprint(sprintId, [...marcadas]);
      onSalvo();
      onClose();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao salvar a meta da sprint");
      setSalvando(false);
    }
  }

  return (
    <Modal
      title={`Definir meta · ${projeto.nome ?? "Projeto"}`}
      width={640}
      onClose={onClose}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Cancelar</Button>
        <Button variant="primary" disabled={salvando || carregando || !metaCarregada || funcs === null || !sprintId} onClick={salvar}>{salvando ? "Salvando..." : "Salvar meta"}</Button>
      </>}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {sprints.length === 0 ? (
          <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Nenhuma sprint aberta para definir meta.</p>
        ) : (
          <>
            <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, color: ds.muted }}>
              Sprint
              <Select value={sprintId} onChange={(e) => setSprintId(e.target.value)} disabled={salvando}>
                {sprints.map((s) => <option key={s.id} value={s.id}>{s.atual ? `Sprint ${s.numero} (atual)` : `Sprint ${s.numero}`}</option>)}
              </Select>
            </label>
            {(funcs === null || carregando) && !erro && !erroFuncs && <p role="status" style={{ margin: 0, color: ds.muted }}>Carregando...</p>}
            {funcs !== null && metaCarregada && abertas.length === 0 && <p style={{ margin: 0, fontSize: 14, color: ds.muted }}>Nenhuma funcionalidade pendente neste projeto.</p>}
            {funcs !== null && metaCarregada && (
              <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                {abertas.map((f) => {
                  const d = sprintEhAtual ? dadosAtual.get(f.id) : undefined;
                  return (
                    <li key={f.id}>
                      <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14, color: ds.text2, cursor: "pointer", flexWrap: "wrap" }}>
                        <input type="checkbox" checked={marcadas.has(f.id)} onChange={() => alternar(f.id)} disabled={salvando} />
                        <span style={{ fontFamily: ds.fontMono, color: ds.muted }}>{f.id_funcional}</span>
                        <span style={{ flex: "1 1 160px" }}>{f.titulo}</span>
                        <span style={{ fontSize: 12, color: ds.muted }}>{f.prioridade}</span>
                        {d?.pct != null && <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{Math.round(d.pct)}% tasks</span>}
                        {d?.planejada && <Chip tone="green">planejada nesta sprint</Chip>}
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}
        {erroFuncs && <ErrorNotice>{erroFuncs}</ErrorNotice>}
        {erro && <ErrorNotice>{erro}</ErrorNotice>}
      </div>
    </Modal>
  );
}
