"use client";

import { useCallback, useEffect, useState } from "react";
import { ds } from "../../lib/ds";
import { TIPO_REUNIAO_LABEL, getTranscricao, listReunioes, nivelDoCargo, reanalisarReuniao, type Reuniao, type Transcricao } from "../../lib/discovery";
import { Button, Card, Chip, EmptyState, ErrorNotice, Modal } from "../ds";
import { ANALISE_LABEL, ANALISE_TONE } from "./requisitoTones";

const fmt = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

/** Aba "Reuniões": as reuniões recebidas do Agente, com status da análise; transcrição e reanálise são de gerente ou acima. */
export default function ReunioesTab({ projectId, cargo }: { projectId: string; cargo: string | undefined }) {
  const [reunioes, setReunioes] = useState<Reuniao[] | null>(null);
  const [error, setError] = useState("");
  const [transcricao, setTranscricao] = useState<{ reuniao: Reuniao; dados: Transcricao } | null>(null);
  const [ocupada, setOcupada] = useState<string | null>(null);
  const [aviso, setAviso] = useState("");
  const gerente = nivelDoCargo(cargo) >= 1;

  const carregar = useCallback(() => {
    listReunioes(projectId).then(setReunioes).catch((e: Error) => setError(e.message));
  }, [projectId]);

  useEffect(() => { carregar(); }, [carregar]);

  async function verTranscricao(r: Reuniao) {
    setOcupada(r.id);
    setError("");
    try {
      setTranscricao({ reuniao: r, dados: await getTranscricao(r.id) });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao buscar a transcrição");
    } finally {
      setOcupada(null);
    }
  }

  async function reanalisar(r: Reuniao) {
    setOcupada(r.id);
    setError("");
    setAviso("");
    try {
      await reanalisarReuniao(r.id);
      setAviso("Reanálise agendada. Atualize a lista em alguns instantes.");
      carregar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao reanalisar");
    } finally {
      setOcupada(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 760 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
            <h2 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em", color: ds.white }}>Reuniões</h2>
            <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>{reunioes?.length ?? 0} reuniões</span>
          </div>
          <p style={{ fontSize: 14, lineHeight: 1.55, color: ds.muted, textWrap: "pretty" }}>
            Cada reunião encerrada no Agente Diagnóstico chega aqui e é analisada em segundo plano. A transcrição integral só aparece para gerente ou acima e já vem com chaves e senhas ocultadas.
          </p>
        </div>
        <Button onClick={carregar}>Atualizar</Button>
      </div>

      {error && <ErrorNotice>{error}</ErrorNotice>}
      {aviso && <p role="status" style={{ fontSize: 13.5, color: ds.green }}>{aviso}</p>}
      {!reunioes && !error && <p style={{ color: ds.muted }}>Carregando…</p>}
      {reunioes && reunioes.length === 0 && <EmptyState>Nenhuma reunião recebida ainda. Vincule este projeto no Agente Diagnóstico e encerre uma sessão de discovery.</EmptyState>}

      {reunioes && reunioes.length > 0 && (
        <Card>
          {reunioes.map((r, i) => (
            <div key={r.id} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 20, alignItems: "center", padding: "18px 28px", borderTop: i > 0 ? `1px solid ${ds.border}` : "none" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 16, fontWeight: 600, color: ds.white }}>{TIPO_REUNIAO_LABEL[r.tipo]}</span>
                  <Chip tone={ANALISE_TONE[r.analise_status]} dot>{ANALISE_LABEL[r.analise_status]}</Chip>
                </span>
                <span style={{ fontFamily: ds.fontMono, fontSize: 12, color: ds.muted }}>
                  {fmt(r.ocorrida_em ?? r.created_at)} · origem {r.origem}
                  {r.fonte_session_id && <> · sessão {r.fonte_session_id.slice(0, 8)}</>}
                </span>
              </div>
              {gerente && (
                <div style={{ display: "flex", gap: 8 }}>
                  <Button size="sm" disabled={ocupada === r.id} onClick={() => verTranscricao(r)}>Ver transcrição</Button>
                  <Button size="sm" disabled={ocupada === r.id} onClick={() => reanalisar(r)}>Reanalisar</Button>
                </div>
              )}
            </div>
          ))}
        </Card>
      )}

      {transcricao && (
        <Modal title={`Transcrição · ${TIPO_REUNIAO_LABEL[transcricao.reuniao.tipo]}`} onClose={() => setTranscricao(null)} footer={<Button variant="primary" onClick={() => setTranscricao(null)}>Fechar</Button>}>
          {transcricao.dados.redigida && <p style={{ fontSize: 12.5, color: ds.amber, marginBottom: 12 }}>Trechos sensíveis foram ocultados automaticamente.</p>}
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: ds.fontSans, fontSize: 14, lineHeight: 1.65, color: ds.text2 }}>{transcricao.dados.conteudo}</pre>
        </Modal>
      )}
    </div>
  );
}
