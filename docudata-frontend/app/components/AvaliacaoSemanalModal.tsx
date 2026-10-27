"use client";

import { useEffect, useState } from "react";
import {
  listPendenciasAvaliacao,
  submitAvaliacao,
  confirmarAvaliacaoSemanal,
  type PendenciaAvaliacao,
} from "../lib/api";
import { ds } from "../lib/ds";
import { Modal, Button, ErrorNotice } from "./ds";
import { perguntas } from "../lib/perguntasAvaliacao";

interface Props {
  sprintId: string;
  sprintNumero: number;
  modoTrabalho: "ATRIBUICAO" | "PULL";
  onClose: () => void;
  onCompleted: () => void;
}

type Respostas = [number, number, number, number, number, number];
const RESPOSTAS_VAZIAS: Respostas = [-1, -1, -1, -1, -1, -1];

export default function AvaliacaoSemanalModal({ sprintId, sprintNumero, modoTrabalho, onClose, onCompleted }: Props) {
  const [pendencias, setPendencias] = useState<PendenciaAvaliacao[] | null>(null);
  const [avaliando, setAvaliando] = useState<PendenciaAvaliacao | null>(null);
  const [respostas, setRespostas] = useState<Respostas>(RESPOSTAS_VAZIAS);
  const [reaproveitadaDe, setReaproveitadaDe] = useState<string | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    carregarPendencias();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function carregarPendencias() {
    try {
      const data = await listPendenciasAvaliacao(sprintId);
      setPendencias(data);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao carregar pendências");
    }
  }

  function iniciarAvaliacao(p: PendenciaAvaliacao) {
    setAvaliando(p);
    setRespostas(RESPOSTAS_VAZIAS);
    setReaproveitadaDe(undefined);
    setErr("");
  }

  function reaproveitar(p: PendenciaAvaliacao) {
    if (!p.ultima_avaliacao_outro_projeto) return;
    const a = p.ultima_avaliacao_outro_projeto;
    setRespostas([a.resposta_1, a.resposta_2, a.resposta_3, a.resposta_4, a.resposta_5, a.resposta_7]);
    setReaproveitadaDe(a.avaliacao_id);
  }

  async function salvar() {
    if (!avaliando || respostas.includes(-1)) {
      setErr("Responda todas as 6 perguntas antes de salvar.");
      return;
    }
    setSaving(true);
    setErr("");
    try {
      await submitAvaliacao({
        operacional_id: avaliando.operacional_id,
        sprint_id: sprintId,
        resposta_1: respostas[0],
        resposta_2: respostas[1],
        resposta_3: respostas[2],
        resposta_4: respostas[3],
        resposta_5: respostas[4],
        resposta_7: respostas[5],
        reaproveitada_de: reaproveitadaDe,
      });
      setAvaliando(null);
      await carregarPendencias();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erro ao salvar avaliação");
    } finally {
      setSaving(false);
    }
  }

  async function confirmar() {
    setConfirming(true);
    setErr("");
    try {
      await confirmarAvaliacaoSemanal(sprintId);
      onCompleted();
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Ainda há avaliações pendentes");
    } finally {
      setConfirming(false);
    }
  }

  const chipRow: React.CSSProperties = { display: "flex", gap: 6, marginTop: 8, marginBottom: 18 };
  const chipBtn = (active: boolean): React.CSSProperties => ({
    width: 38, height: 38, borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
    border: active ? `1px solid ${ds.green}` : `1px solid ${ds.innerBorder}`,
    background: active ? ds.green : ds.inner,
    color: active ? "#04120a" : ds.text,
  });

  return (
    <Modal title={`Avaliação Semanal — Sprint ${sprintNumero}`} onClose={onClose} width={520}>
      <div style={{ color: ds.text }}>
        {err && <div style={{ marginBottom: 14 }}><ErrorNotice>{err}</ErrorNotice></div>}

        {!avaliando && pendencias && pendencias.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <p style={{ fontSize: 13, color: ds.muted, margin: 0 }}>{pendencias.length} pendente(s):</p>
            {pendencias.map((p) => (
              <button key={p.operacional_id} onClick={() => iniciarAvaliacao(p)}
                style={{ textAlign: "left", padding: "11px 14px", border: `1px solid ${ds.innerBorder}`, borderRadius: 10, background: ds.inner, color: ds.text, fontSize: 14, fontFamily: "inherit", cursor: "pointer" }}>
                {p.nome}
              </button>
            ))}
          </div>
        )}

        {!avaliando && pendencias && pendencias.length === 0 && (
          <div>
            <p style={{ fontSize: 13, color: ds.green, marginTop: 0, marginBottom: 16 }}>✓ Todas as avaliações desta sprint estão completas.</p>
            <Button variant="primary" onClick={confirmar} disabled={confirming} style={{ opacity: confirming ? 0.6 : 1 }}>
              {confirming ? "Confirmando..." : "Confirmar Avaliação Semanal"}
            </Button>
          </div>
        )}

        {avaliando && (
          <div>
            <p style={{ fontSize: 15, fontWeight: 600, color: ds.white, marginTop: 0, marginBottom: 14 }}>{avaliando.nome}</p>

            {avaliando.ultima_avaliacao_outro_projeto && !reaproveitadaDe && (
              <div style={{ background: ds.violetSoft, border: `1px solid ${ds.violetLine}`, borderRadius: 10, padding: 12, marginBottom: 18, fontSize: 12.5, color: ds.text2 }}>
                Reaproveitar avaliação de {avaliando.ultima_avaliacao_outro_projeto.project_name} em{" "}
                {new Date(avaliando.ultima_avaliacao_outro_projeto.criado_em).toLocaleDateString("pt-BR")}?{" "}
                <button onClick={() => reaproveitar(avaliando)} style={{ color: ds.violet, fontWeight: 600, fontSize: 12.5, fontFamily: "inherit", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                  Usar essas respostas
                </button>
              </div>
            )}

            {perguntas(modoTrabalho).map((pergunta, i) => (
              <div key={i}>
                <label style={{ fontSize: 13.5, fontWeight: 500, color: ds.text2 }}>{pergunta}</label>
                <div style={chipRow}>
                  {[0, 1, 2, 3, 4, 5].map((n) => (
                    <button key={n} type="button" style={chipBtn(respostas[i] === n)}
                      onClick={() => setRespostas((prev) => { const next = [...prev] as Respostas; next[i] = n; return next; })}>
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            ))}

            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <Button variant="primary" onClick={salvar} disabled={saving} style={{ opacity: saving ? 0.6 : 1 }}>
                {saving ? "Salvando..." : "Salvar avaliação"}
              </Button>
              <Button variant="secondary" onClick={() => setAvaliando(null)}>
                Voltar
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
