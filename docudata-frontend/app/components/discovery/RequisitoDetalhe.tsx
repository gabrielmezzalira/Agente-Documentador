"use client";

import { useCallback, useEffect, useState } from "react";
import { ds, innerStyle } from "../../lib/ds";
import {
  PRIORIDADE_LABEL, STATUS_LABEL, acoesDisponiveis, getRequisito, patchRequisito, podeEditar,
  podePromover, promoverRequisito,
  type AcaoStatus, type Prioridade, type RequisitoDetalhe as Detalhe,
} from "../../lib/discovery";
import { Button, Chip, ErrorNotice, Field, Input, SectionLabel, Select, Textarea } from "../ds";
import { PRIORIDADE_TONE, STATUS_TONE } from "./requisitoTones";

const fmt = (iso: string) => new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });

interface Props {
  requisitoId: string;
  cargo: string | undefined;
  /** Avisa a lista para recarregar depois de qualquer alteração. */
  onChanged: () => void;
}

/** Detalhe do requisito: descrição, critérios, evidências, histórico e ações (revisar, validar, rejeitar, editar, promover). */
export default function RequisitoDetalhe({ requisitoId, cargo, onChanged }: Props) {
  const [req, setReq] = useState<Detalhe | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [acaoComMotivo, setAcaoComMotivo] = useState<AcaoStatus | null>(null);
  const [motivo, setMotivo] = useState("");
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState({ titulo: "", descricao: "", criterios: "", prioridade: "should" as Prioridade });

  const carregar = useCallback(() => {
    getRequisito(requisitoId).then(setReq).catch((e: Error) => setError(e.message));
  }, [requisitoId]);

  useEffect(() => { carregar(); }, [carregar]);

  async function executar(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      setAcaoComMotivo(null);
      setMotivo("");
      setEditando(false);
      carregar();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setBusy(false);
    }
  }

  function aplicarAcao(acao: AcaoStatus) {
    if (acao.exigeMotivo && !acaoComMotivo) { setAcaoComMotivo(acao); return; }
    void executar(() => patchRequisito(requisitoId, { status: acao.para, motivo: motivo.trim() || undefined }));
  }

  function abrirEdicao(r: Detalhe) {
    setForm({ titulo: r.titulo, descricao: r.descricao ?? "", criterios: r.criterios_aceite.join("\n"), prioridade: r.prioridade_sugerida });
    setEditando(true);
  }

  if (!req) return error ? <ErrorNotice>{error}</ErrorNotice> : <p style={{ color: ds.muted, fontSize: 13 }}>Carregando…</p>;

  const acoes = acoesDisponiveis(req.status, cargo);
  const bloco: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 10 };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22, padding: "4px 28px 26px" }}>
      {error && <ErrorNotice>{error}</ErrorNotice>}

      {editando ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Field label="Título" htmlFor="rq-titulo"><Input id="rq-titulo" value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} maxLength={200} /></Field>
          <Field label="Descrição" htmlFor="rq-desc"><Textarea id="rq-desc" rows={3} value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} maxLength={4000} /></Field>
          <Field label="Critérios de aceite" htmlFor="rq-crit" hint="Um critério por linha."><Textarea id="rq-crit" rows={4} value={form.criterios} onChange={(e) => setForm({ ...form, criterios: e.target.value })} /></Field>
          <Field label="Prioridade sugerida" htmlFor="rq-prio">
            <Select id="rq-prio" value={form.prioridade} onChange={(e) => setForm({ ...form, prioridade: e.target.value as Prioridade })}>
              {(Object.keys(PRIORIDADE_LABEL) as Prioridade[]).map((p) => <option key={p} value={p}>{PRIORIDADE_LABEL[p]}</option>)}
            </Select>
          </Field>
          <div style={{ display: "flex", gap: 10 }}>
            <Button
              variant="primary"
              disabled={busy || form.titulo.trim().length < 3}
              onClick={() => executar(() => patchRequisito(requisitoId, {
                titulo: form.titulo.trim(),
                descricao: form.descricao.trim(),
                criterios_aceite: form.criterios.split("\n").map((c) => c.trim()).filter(Boolean),
                prioridade_sugerida: form.prioridade,
              }))}
            >
              {busy ? "Salvando…" : "Salvar alterações"}
            </Button>
            <Button variant="ghost" onClick={() => setEditando(false)}>Cancelar</Button>
          </div>
        </div>
      ) : (
        <>
          {req.descricao && <p style={{ fontSize: 15, lineHeight: 1.7, color: ds.text2, textWrap: "pretty" }}>{req.descricao}</p>}
          {req.justificativa && (
            <div style={bloco}>
              <SectionLabel>Justificativa</SectionLabel>
              <p style={{ fontSize: 14, lineHeight: 1.6, color: ds.muted }}>{req.justificativa}</p>
            </div>
          )}
          {req.criterios_aceite.length > 0 && (
            <div style={bloco}>
              <SectionLabel>Critérios de aceite</SectionLabel>
              <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                {req.criterios_aceite.map((c, i) => (
                  <li key={i} style={{ ...innerStyle, padding: "10px 14px", fontSize: 14, lineHeight: 1.55, color: ds.text2 }}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {req.conflito && <ErrorNotice>Este requisito tem conflito com outra reunião. Revise antes de validar.</ErrorNotice>}
      {req.motivo_decisao && (
        <div style={bloco}>
          <SectionLabel>Motivo da decisão</SectionLabel>
          <p style={{ fontSize: 14, color: ds.muted }}>{req.motivo_decisao}</p>
        </div>
      )}

      <div style={bloco}>
        <SectionLabel>Evidências · {req.evidencias.length}</SectionLabel>
        {req.evidencias.length === 0 ? (
          <p style={{ fontSize: 13, color: ds.dim }}>Sem evidências registradas.</p>
        ) : (
          req.evidencias.map((ev) => (
            <blockquote key={ev.id} style={{ ...innerStyle, margin: 0, padding: "12px 16px" }}>
              <p style={{ fontSize: 14, lineHeight: 1.6, color: ds.text, fontStyle: "italic" }}>&ldquo;{ev.trecho}&rdquo;</p>
              <p style={{ marginTop: 6, fontFamily: ds.fontMono, fontSize: 11.5, color: ds.muted }}>
                {ev.speaker ?? "Falante não identificado"}
                {ev.confianca != null && <> · confiança {Math.round(ev.confianca * 100)}%</>}
              </p>
            </blockquote>
          ))
        )}
      </div>

      {req.transicoes.length > 0 && (
        <details style={bloco}>
          <summary style={{ cursor: "pointer", listStyle: "none" }}><SectionLabel>Histórico · {req.transicoes.length} ▾</SectionLabel></summary>
          <ol style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
            {req.transicoes.map((t) => (
              <li key={t.id} style={{ fontSize: 13, color: ds.muted, display: "flex", gap: 10, flexWrap: "wrap" }}>
                <span style={{ fontFamily: ds.fontMono, fontSize: 12 }}>{fmt(t.timestamp)}</span>
                <span style={{ color: ds.text2 }}>{t.campo === "status" ? `${STATUS_LABEL[t.de as keyof typeof STATUS_LABEL] ?? t.de} → ${STATUS_LABEL[t.para as keyof typeof STATUS_LABEL] ?? t.para}` : "Edição"}</span>
                {t.autor && <span>· {t.autor}</span>}
                {t.motivo && <span>· {t.motivo}</span>}
              </li>
            ))}
          </ol>
        </details>
      )}

      {acaoComMotivo && (
        <div style={{ ...innerStyle, padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          <Field label={`Motivo para ${acaoComMotivo.rotulo.toLowerCase()}`} htmlFor="rq-motivo" required>
            <Textarea id="rq-motivo" rows={2} value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={1000} autoFocus />
          </Field>
          <div style={{ display: "flex", gap: 10 }}>
            <Button variant={acaoComMotivo.para === "rejeitado" ? "danger" : "primary"} disabled={busy || !motivo.trim()} onClick={() => aplicarAcao(acaoComMotivo)}>
              {busy ? "Salvando…" : `Confirmar: ${acaoComMotivo.rotulo}`}
            </Button>
            <Button variant="ghost" onClick={() => { setAcaoComMotivo(null); setMotivo(""); }}>Cancelar</Button>
          </div>
        </div>
      )}

      {!editando && !acaoComMotivo && (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", paddingTop: 16, borderTop: `1px solid ${ds.border}` }}>
          <Chip tone={STATUS_TONE[req.status]} dot>{STATUS_LABEL[req.status]}</Chip>
          <Chip tone={PRIORIDADE_TONE[req.prioridade_sugerida]}>{PRIORIDADE_LABEL[req.prioridade_sugerida]}</Chip>
          <span style={{ flex: 1 }} />
          {acoes.map((a) => (
            <Button key={a.para} variant={a.para === "rejeitado" ? "danger" : a.para === "validado" ? "primary" : "secondary"} disabled={busy} onClick={() => aplicarAcao(a)}>
              {a.rotulo}
            </Button>
          ))}
          {podeEditar(req.status, cargo) && <Button onClick={() => abrirEdicao(req)} disabled={busy}>Editar</Button>}
          {podePromover(req, cargo) && (
            <Button variant="active" disabled={busy} onClick={() => executar(() => promoverRequisito(requisitoId))}>Promover a funcionalidade</Button>
          )}
          {req.funcionalidade_id && <Chip tone="green">Já promovido</Chip>}
        </div>
      )}
    </div>
  );
}
