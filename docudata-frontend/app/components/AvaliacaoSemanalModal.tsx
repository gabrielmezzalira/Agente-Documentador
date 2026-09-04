"use client";

import { useEffect, useState } from "react";
import {
  listPendenciasAvaliacao,
  submitAvaliacao,
  confirmarAvaliacaoSemanal,
  type PendenciaAvaliacao,
} from "../lib/api";

const PERGUNTAS = [
  "Entregou o que se comprometeu dentro do combinado nesta sprint?",
  "A qualidade da entrega precisou de pouca ou nenhuma correção?",
  "A pessoa destravou sozinha antes de te escalar?",
  "A comunicação da entrega foi clara a ponto de você não precisar perguntar?",
  "Ajudou, desbloqueou ou ensinou outro membro nesta sprint?",
  "Evoluiu em relação a onde estava no começo do ciclo?",
  "Trouxe algo além do que foi pedido?",
];

interface Props {
  sprintId: string;
  sprintNumero: number;
  onClose: () => void;
  onCompleted: () => void;
}

type Respostas = [number, number, number, number, number, number, number];
const RESPOSTAS_VAZIAS: Respostas = [-1, -1, -1, -1, -1, -1, -1];

export default function AvaliacaoSemanalModal({ sprintId, sprintNumero, onClose, onCompleted }: Props) {
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
    setRespostas([a.resposta_1, a.resposta_2, a.resposta_3, a.resposta_4, a.resposta_5, a.resposta_6, a.resposta_7]);
    setReaproveitadaDe(a.avaliacao_id);
  }

  async function salvar() {
    if (!avaliando || respostas.includes(-1)) {
      setErr("Responda todas as 7 perguntas antes de salvar.");
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
        resposta_6: respostas[5],
        resposta_7: respostas[6],
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

  const overlaySt: React.CSSProperties = { position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 };
  const boxSt: React.CSSProperties = { background: "#fff", borderRadius: 16, padding: 28, width: 480, maxHeight: "80vh", overflowY: "auto" };
  const chipRow: React.CSSProperties = { display: "flex", gap: 6, marginTop: 6, marginBottom: 16 };
  const chipBtn = (active: boolean): React.CSSProperties => ({
    width: 36, height: 36, borderRadius: 8, border: active ? "2px solid #111116" : "1px solid #e4e4ea",
    background: active ? "#111116" : "#fff", color: active ? "#fff" : "#111116", fontWeight: 700, cursor: "pointer",
  });

  return (
    <div style={overlaySt} onClick={onClose}>
      <div style={boxSt} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Avaliação Semanal — Sprint {sprintNumero}</h2>

        {err && <p style={{ color: "#dc2626", fontSize: 13, marginBottom: 12 }}>{err}</p>}

        {!avaliando && pendencias && pendencias.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <p style={{ fontSize: 13, color: "#64748b" }}>{pendencias.length} pendente(s):</p>
            {pendencias.map((p) => (
              <button key={p.operacional_id} onClick={() => iniciarAvaliacao(p)}
                style={{ textAlign: "left", padding: "10px 14px", border: "1px solid #e4e4ea", borderRadius: 8, background: "#fff", cursor: "pointer" }}>
                {p.nome}
              </button>
            ))}
          </div>
        )}

        {!avaliando && pendencias && pendencias.length === 0 && (
          <div>
            <p style={{ fontSize: 13, color: "#16a34a", marginBottom: 16 }}>✓ Todas as avaliações desta sprint estão completas.</p>
            <button onClick={confirmar} disabled={confirming}
              style={{ padding: "10px 16px", borderRadius: 8, background: "#111116", color: "#fff", border: "none", fontWeight: 600 }}>
              {confirming ? "Confirmando..." : "Confirmar Avaliação Semanal"}
            </button>
          </div>
        )}

        {avaliando && (
          <div>
            <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>{avaliando.nome}</p>

            {avaliando.ultima_avaliacao_outro_projeto && !reaproveitadaDe && (
              <div style={{ background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: 8, padding: 10, marginBottom: 16, fontSize: 12 }}>
                Reaproveitar avaliação de {avaliando.ultima_avaliacao_outro_projeto.project_name} em{" "}
                {new Date(avaliando.ultima_avaliacao_outro_projeto.criado_em).toLocaleDateString("pt-BR")}?{" "}
                <button onClick={() => reaproveitar(avaliando)} style={{ color: "#0284c7", fontWeight: 600, background: "none", border: "none", cursor: "pointer" }}>
                  Usar essas respostas
                </button>
              </div>
            )}

            {PERGUNTAS.map((pergunta, i) => (
              <div key={i}>
                <label style={{ fontSize: 13, fontWeight: 500 }}>{pergunta}</label>
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
              <button onClick={salvar} disabled={saving}
                style={{ padding: "10px 16px", borderRadius: 8, background: "#111116", color: "#fff", border: "none", fontWeight: 600 }}>
                {saving ? "Salvando..." : "Salvar avaliação"}
              </button>
              <button onClick={() => setAvaliando(null)} style={{ padding: "10px 16px", borderRadius: 8, background: "none", border: "1px solid #e4e4ea", cursor: "pointer" }}>
                Voltar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
