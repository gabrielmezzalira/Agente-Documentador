"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Chip, ErrorNotice, Field, Input, Modal, Select, Textarea } from "./ds";
import { useAuth } from "./AuthGuard";
import { NIVEIS, rotuloNivel } from "../lib/regua";
import {
  criarProposta,
  decidirProposta,
  listarPropostas,
  type PropostaMelhoria,
  type StatusProposta,
  type Subarea,
} from "../lib/api";

interface Props {
  projectId: string;
  subarea?: Subarea;
  /** Chamado depois de aprovar, para o Kanban recarregar a task nova. */
  onAprovada?: () => void;
}

const ROTULO_STATUS: Record<StatusProposta, string> = {
  pendente: "Pendente",
  adiada: "Adiada",
  aprovada: "Aprovada",
  recusada: "Recusada",
};
const TOM_STATUS: Record<StatusProposta, "neutral" | "amber" | "green" | "red"> = {
  pendente: "neutral",
  adiada: "amber",
  aprovada: "green",
  recusada: "red",
};

const painel: React.CSSProperties = {
  background: "rgba(62,224,111,0.12)", border: "1px solid rgba(62,224,111,0.35)", borderRadius: 10,
  padding: "12px 16px", marginBottom: 14,
};
const linha: React.CSSProperties = {
  background: "#0d1711", border: "1px solid rgba(62,224,111,0.35)", borderRadius: 7, padding: "8px 12px",
};

export default function PropostasMelhoria({ projectId, subarea, onAprovada }: Props) {
  const auth = useAuth();
  const ehPta = subarea === "pta";
  const ehOperacional = auth?.cargo === "operacional";

  const [propostas, setPropostas] = useState<PropostaMelhoria[]>([]);
  const [erroLista, setErroLista] = useState("");

  const carregar = useCallback(() => {
    if (!ehPta) return;
    listarPropostas(projectId)
      .then((d) => { setPropostas(d); setErroLista(""); })
      .catch((e) => setErroLista(e instanceof Error ? e.message : "Erro ao buscar propostas"));
  }, [projectId, ehPta]);

  useEffect(() => { carregar(); }, [carregar]);

  // modal do candidato
  const [aberto, setAberto] = useState(false);
  const [titulo, setTitulo] = useState("");
  const [valor, setValor] = useState("");
  const [esforco, setEsforco] = useState<number>(NIVEIS[0]);
  const [enviando, setEnviando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState("");
  const [aviso, setAviso] = useState("");
  const gatilho = useRef<HTMLButtonElement>(null);

  // decisão do PM
  const [recusandoId, setRecusandoId] = useState<string | null>(null);
  const [motivo, setMotivo] = useState("");
  const [decidindoId, setDecidindoId] = useState<string | null>(null);
  const [erroDecisao, setErroDecisao] = useState("");

  useEffect(() => {
    if (!aberto) return;
    // O Modal foca o botão de fechar ao montar; o primeiro campo é o destino útil.
    const t = setTimeout(() => document.getElementById("proposta-titulo")?.focus(), 0);
    return () => clearTimeout(t);
  }, [aberto]);

  if (!ehPta) return null;

  function fechar() {
    setAberto(false);
    setErroEnvio("");
    setTimeout(() => gatilho.current?.focus(), 0);
  }

  async function enviar() {
    setEnviando(true);
    setErroEnvio("");
    try {
      await criarProposta(projectId, { titulo: titulo.trim(), valor_cliente: valor.trim(), esforco });
      setTitulo(""); setValor(""); setEsforco(NIVEIS[0]);
      setAberto(false);
      setAviso("Proposta enviada. O gerente vai avaliar.");
      carregar();
      setTimeout(() => gatilho.current?.focus(), 0);
    } catch (e) {
      setErroEnvio(e instanceof Error ? e.message : "Erro ao enviar a proposta");
    } finally {
      setEnviando(false);
    }
  }

  async function decidir(p: PropostaMelhoria, acao: "aprovar" | "recusar" | "adiar") {
    if (acao === "recusar" && !motivo.trim()) {
      setErroDecisao("Informe o motivo da recusa.");
      return;
    }
    setDecidindoId(p.id);
    setErroDecisao("");
    try {
      await decidirProposta(p.id, acao, acao === "recusar" ? motivo : undefined);
      setRecusandoId(null);
      setMotivo("");
      carregar();
      if (acao === "aprovar") onAprovada?.();
    } catch (e) {
      setErroDecisao(e instanceof Error ? e.message : "Erro ao decidir a proposta");
    } finally {
      setDecidindoId(null);
    }
  }

  if (ehOperacional) {
    return (
      <section aria-label="Propor melhoria" style={{ marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <button
            ref={gatilho}
            type="button"
            onClick={() => { setAviso(""); setAberto(true); }}
            style={{
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.14)", borderRadius: 10,
              height: 38, padding: "0 16px", fontSize: 13.5, fontWeight: 600, color: "#f2f5f3", cursor: "pointer", fontFamily: "inherit",
            }}
          >
            Propor melhoria
          </button>
          {aviso && <span role="status" style={{ fontSize: 12.5, color: "#7cf0a0" }}>{aviso}</span>}
        </div>

        {erroLista && <div style={{ marginTop: 8 }}><ErrorNotice>{erroLista}</ErrorNotice></div>}

        {propostas.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: "#c3cbc6", margin: "0 0 8px" }}>Minhas propostas</p>
            <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 6 }}>
              {propostas.map((p) => (
                <li key={p.id} style={{ ...linha, border: "1px solid rgba(255,255,255,0.14)", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ flex: 1, minWidth: 0, fontSize: 13, color: "#c3cbc6" }}>
                    {p.titulo} <span style={{ color: "#8a948e" }}>· {rotuloNivel(p.esforco)}</span>
                    {p.status === "recusada" && p.motivo && (
                      <span style={{ display: "block", fontSize: 12, color: "#ff6b6b", marginTop: 4 }}>Motivo: {p.motivo}</span>
                    )}
                  </span>
                  <Chip tone={TOM_STATUS[p.status]}>{ROTULO_STATUS[p.status]}</Chip>
                </li>
              ))}
            </ul>
          </div>
        )}

        {aberto && (
          <Modal
            title="Propor melhoria"
            onClose={fechar}
            width={520}
            footer={
              <>
                <Button variant="ghost" type="button" onClick={fechar}>Cancelar</Button>
                <Button variant="primary" type="button" onClick={enviar} disabled={enviando || titulo.trim().length < 3 || !valor.trim()}>
                  {enviando ? "Enviando..." : "Enviar proposta"}
                </Button>
              </>
            }
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Field label="Título" htmlFor="proposta-titulo" required hint="De 3 a 200 caracteres.">
                <Input id="proposta-titulo" value={titulo} maxLength={200} onChange={(e) => setTitulo(e.target.value)} />
              </Field>
              <Field label="Valor para o cliente" htmlFor="proposta-valor" required hint="O que o cliente ganha com essa melhoria.">
                <Textarea id="proposta-valor" rows={4} value={valor} maxLength={2000} onChange={(e) => setValor(e.target.value)} />
              </Field>
              <Field label="Esforço" htmlFor="proposta-esforco" required>
                <Select id="proposta-esforco" value={esforco} onChange={(e) => setEsforco(Number(e.target.value))}>
                  {NIVEIS.map((n) => <option key={n} value={n}>{rotuloNivel(n)}</option>)}
                </Select>
              </Field>
              {erroEnvio && <div role="alert"><ErrorNotice>{erroEnvio}</ErrorNotice></div>}
            </div>
          </Modal>
        )}
      </section>
    );
  }

  const abertas = propostas.filter((p) => p.status === "pendente" || p.status === "adiada");
  if (abertas.length === 0 && !erroLista) return null;

  return (
    <section aria-label="Propostas de melhoria" style={painel}>
      <p style={{ fontSize: 13, fontWeight: 700, color: "#3ee06f", margin: "0 0 8px" }}>
        Propostas de melhoria ({abertas.length})
      </p>
      {erroLista && <ErrorNotice>{erroLista}</ErrorNotice>}
      {erroDecisao && <div role="alert" style={{ marginBottom: 8 }}><ErrorNotice>{erroDecisao}</ErrorNotice></div>}
      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        {abertas.map((p) => {
          const ocupado = decidindoId === p.id;
          return (
            <li key={p.id} style={linha}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <strong style={{ fontSize: 13, color: "#f2f5f3" }}>{p.titulo}</strong>
                <Chip>{rotuloNivel(p.esforco)}</Chip>
                {p.status === "adiada" && <Chip tone="amber">Adiada</Chip>}
              </div>
              <p style={{ fontSize: 12, color: "#8a948e", margin: "4px 0 0" }}>Proposta de {p.operacional_nome ?? "candidato"}</p>
              <p style={{ fontSize: 12.5, color: "#c3cbc6", margin: "6px 0 0" }}>
                <strong>Valor para o cliente:</strong> {p.valor_cliente}
              </p>
              {recusandoId === p.id ? (
                <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                  <Field label="Motivo da recusa" htmlFor={`motivo-${p.id}`} required>
                    <Textarea id={`motivo-${p.id}`} rows={2} value={motivo} maxLength={1000} autoFocus onChange={(e) => setMotivo(e.target.value)} />
                  </Field>
                  <div style={{ display: "flex", gap: 8 }}>
                    <Button variant="danger" size="sm" type="button" disabled={ocupado} onClick={() => decidir(p, "recusar")}>
                      {ocupado ? "Recusando..." : "Confirmar recusa"}
                    </Button>
                    <Button variant="ghost" size="sm" type="button" onClick={() => { setRecusandoId(null); setMotivo(""); setErroDecisao(""); }}>
                      Cancelar
                    </Button>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                  <Button variant="primary" size="sm" type="button" disabled={ocupado} onClick={() => decidir(p, "aprovar")}>Aprovar</Button>
                  <Button variant="danger" size="sm" type="button" disabled={ocupado} onClick={() => { setRecusandoId(p.id); setMotivo(""); setErroDecisao(""); }}>Recusar</Button>
                  {p.status === "pendente" && (
                    <Button variant="secondary" size="sm" type="button" disabled={ocupado} onClick={() => decidir(p, "adiar")}>Deixar para depois</Button>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
